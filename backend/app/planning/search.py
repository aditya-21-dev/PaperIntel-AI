"""Uniform-cost and A* state-space search for hypothetical paper improvements."""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass
from itertools import count
from typing import Any

from app.compliance.models import Constraint

from .models import ImprovementAction, PaperState


@dataclass(frozen=True)
class GoalEvaluation:
    reached: bool
    violated: tuple[Constraint, ...]
    unresolved: tuple[Constraint, ...]


@dataclass(frozen=True)
class PlanningProblem:
    """Classical planning problem: initial state, actions, goal test, and path cost."""

    initial_state: PaperState
    actions: tuple[ImprovementAction, ...]
    constraints: tuple[Constraint, ...]

    def goal_evaluation(self, state: PaperState) -> GoalEvaluation:
        values = state.to_dict()
        violated: list[Constraint] = []
        unresolved: list[Constraint] = []
        for constraint in self.constraints:
            if any(variable not in values for variable in constraint.variables):
                unresolved.append(constraint)
                continue
            scoped = {variable: values[variable] for variable in constraint.variables}
            if not constraint.is_satisfied(scoped):
                violated.append(constraint)
        return GoalEvaluation(not violated and not unresolved, tuple(violated), tuple(unresolved))


class SearchPlanner:
    """Bounded graph search with duplicate-state detection and explainable events."""

    def __init__(
        self,
        max_states: int = 250,
        max_depth: int = 12,
        max_seconds: float = 2.0,
        max_trace_events: int = 500,
    ) -> None:
        if max_states < 1 or max_depth < 0 or max_seconds <= 0 or max_trace_events < 1:
            raise ValueError('Search limits must be positive, with a non-negative maximum depth.')
        self.max_states = max_states
        self.max_depth = max_depth
        self.max_seconds = max_seconds
        self.max_trace_events = max_trace_events

    def solve(self, problem: PlanningProblem, method: str = 'astar') -> dict[str, Any]:
        method = method.casefold()
        if method not in {'ucs', 'astar'}:
            raise ValueError("Search method must be 'ucs' or 'astar'.")
        self._trace_events: list[dict[str, Any]] = []
        started = time.monotonic()
        initial_goal = problem.goal_evaluation(problem.initial_state)
        self._trace({
            'event': 'INITIAL_STATE_EVALUATED',
            'state': problem.initial_state.to_dict(),
            'violated_constraints': [constraint.id for constraint in initial_goal.violated],
            'unresolved_constraints': [constraint.id for constraint in initial_goal.unresolved],
        })
        if initial_goal.reached:
            self._trace({'event': 'GOAL_TEST', 'reached': True, 'violated_constraints': [], 'unresolved_constraints': []})
            self._trace({'event': 'NO_IMPROVEMENT_NEEDED', 'state': problem.initial_state.to_dict()})
            return self._no_improvement_result(problem, method)
        agenda: list[tuple[int, int, int, PaperState, tuple[tuple[ImprovementAction, PaperState, PaperState], ...]]] = []
        sequence = count()
        initial_heuristic = self._heuristic(problem, problem.initial_state, method)
        heapq.heappush(agenda, (initial_heuristic, 0, next(sequence), problem.initial_state, ()))
        best_cost: dict[PaperState, int] = {problem.initial_state: 0}
        states_explored = 0
        depth_limit_reached = False

        while agenda:
            if time.monotonic() - started >= self.max_seconds:
                return self._limited_result(problem, method, states_explored, 'maximum_execution_time_reached')
            _, path_cost, _, state, path = heapq.heappop(agenda)
            if path_cost != best_cost.get(state):
                self._trace({'event': 'STATE_PRUNED', 'reason': 'superseded_by_lower_cost_path', 'state': state.to_dict()})
                continue
            if states_explored >= self.max_states:
                return self._limited_result(problem, method, states_explored, 'maximum_states_explored')

            states_explored += 1
            self._trace({'event': 'STATE_EXPANDED', 'state': state.to_dict(), 'path_cost': path_cost, 'depth': len(path)})
            goal = problem.goal_evaluation(state)
            self._trace({
                'event': 'GOAL_TEST', 'reached': goal.reached,
                'violated_constraints': [constraint.id for constraint in goal.violated],
                'unresolved_constraints': [constraint.id for constraint in goal.unresolved],
            })
            if goal.reached:
                self._trace({'event': 'GOAL_REACHED', 'state': state.to_dict(), 'total_cost': path_cost, 'depth': len(path)})
                return self._found_result(problem, method, state, path, path_cost, states_explored)

            accepted_successor = False
            for action in problem.actions:
                self._trace({'event': 'ACTION_CONSIDERED', 'action_id': action.id, 'action_name': action.name, 'state': state.to_dict()})
                if not action.is_applicable(state):
                    self._trace({'event': 'STATE_PRUNED', 'reason': 'preconditions_not_met', 'action_id': action.id})
                    continue
                successor = action.apply(state)
                self._trace({'event': 'ACTION_APPLIED', 'action_id': action.id, 'state_before': state.to_dict(), 'state_after': successor.to_dict()})
                if successor == state:
                    self._trace({'event': 'STATE_PRUNED', 'reason': 'unchanged_successor', 'action_id': action.id})
                    continue
                next_depth = len(path) + 1
                if next_depth > self.max_depth:
                    depth_limit_reached = True
                    self._trace({'event': 'STATE_PRUNED', 'reason': 'maximum_depth_reached', 'action_id': action.id})
                    continue
                next_cost = path_cost + action.cost
                if next_cost >= best_cost.get(successor, float('inf')):
                    self._trace({'event': 'STATE_PRUNED', 'reason': 'duplicate_or_higher_cost_state', 'action_id': action.id, 'state': successor.to_dict()})
                    continue
                best_cost[successor] = next_cost
                heuristic = self._heuristic(problem, successor, method)
                priority = next_cost + heuristic if method == 'astar' else next_cost
                heapq.heappush(agenda, (priority, next_cost, next(sequence), successor, (*path, (action, state, successor))))
                accepted_successor = True
            if not accepted_successor:
                self._trace({'event': 'BACKTRACK', 'state': state.to_dict(), 'reason': 'no_unpruned_successors'})

        if depth_limit_reached:
            return self._limited_result(problem, method, states_explored, 'maximum_search_depth_reached')
        return self._no_solution_result(problem, method, states_explored)

    def _heuristic(self, problem: PlanningProblem, state: PaperState, method: str) -> int:
        if method == 'ucs':
            return 0
        goal = problem.goal_evaluation(state)
        lower_bounds: list[int] = []
        for constraint in goal.violated:
            costs = [
                action.cost for action in problem.actions
                if set(action.affected_variables) & set(constraint.variables)
            ]
            if costs:
                lower_bounds.append(min(costs))
        estimate = max(lower_bounds, default=0)
        self._trace({
            'event': 'HEURISTIC_CALCULATED', 'state': state.to_dict(), 'estimate': estimate,
            'violated_constraints': [constraint.id for constraint in goal.violated],
            'reason': 'maximum of per-constraint minimum modeled action costs, ignoring prerequisites',
        })
        return estimate

    def _found_result(
        self,
        problem: PlanningProblem,
        method: str,
        state: PaperState,
        path: tuple[tuple[ImprovementAction, PaperState, PaperState], ...],
        total_cost: int,
        states_explored: int,
    ) -> dict[str, Any]:
        return self._result(
            success=True, status='PLAN_FOUND', algorithm='A*' if method == 'astar' else 'Uniform-Cost Search',
            problem=problem, final_state=state, path=path, total_cost=total_cost,
            states_explored=states_explored,
            explanation='The following hypothetical plan is predicted to satisfy every modeled requirement if its suggested changes are successfully applied. Projected state — the paper has not been modified.',
        )

    def _no_improvement_result(self, problem: PlanningProblem, method: str) -> dict[str, Any]:
        return self._result(
            success=True, status='NO_IMPROVEMENT_NEEDED', algorithm='A*' if method == 'astar' else 'Uniform-Cost Search',
            problem=problem, final_state=problem.initial_state, path=(), total_cost=0,
            states_explored=0,
            explanation='The current paper state already satisfies every modeled requirement, so no hypothetical improvement action is needed. Projected state — the paper has not been modified.',
        )

    def _no_solution_result(self, problem: PlanningProblem, method: str, states_explored: int) -> dict[str, Any]:
        return self._result(
            success=True, status='NO_SOLUTION', algorithm='A*' if method == 'astar' else 'Uniform-Cost Search',
            problem=problem, final_state=problem.initial_state, path=(), total_cost=0,
            states_explored=states_explored,
            explanation='No solution was found using the currently modeled actions and constraints. This does not mean the paper cannot be fixed in reality. Projected state — the paper has not been modified.',
        )

    def _limited_result(self, problem: PlanningProblem, method: str, states_explored: int, reason: str) -> dict[str, Any]:
        self._trace({'event': 'SEARCH_LIMIT_REACHED', 'reason': reason})
        return self._result(
            success=False, status='SEARCH_LIMIT_REACHED', algorithm='A*' if method == 'astar' else 'Uniform-Cost Search',
            problem=problem, final_state=problem.initial_state, path=(), total_cost=0,
            states_explored=states_explored,
            explanation='Search stopped at a configured safety limit, so no optimal or complete plan is reported. Projected state — the paper has not been modified.',
        )

    def _result(
        self,
        *,
        success: bool,
        status: str,
        algorithm: str,
        problem: PlanningProblem,
        final_state: PaperState,
        path: tuple[tuple[ImprovementAction, PaperState, PaperState], ...],
        total_cost: int,
        states_explored: int,
        explanation: str,
    ) -> dict[str, Any]:
        final_goal = problem.goal_evaluation(final_state)
        explanation = explanation.replace(
            ''.join(chr(codepoint) for codepoint in (226, 8364, 8221)),
            '\u2014',
        )
        return {
            'success': success,
            'status': status,
            'algorithm': algorithm,
            'initial_state': problem.initial_state.to_dict(),
            'actions': [self._planned_action(action, before, after) for action, before, after in path],
            'available_actions': [action.to_dict() for action in problem.actions],
            'total_cost': total_cost,
            'final_state': final_state.to_dict(),
            'states_explored': states_explored,
            'search_depth': len(path),
            'remaining_violations': [constraint.to_dict() for constraint in final_goal.violated],
            'unresolved_constraints': [constraint.to_dict() for constraint in final_goal.unresolved],
            'heuristic': {
                'name': 'maximum_minimum_action_cost',
                'admissible': True,
                'description': 'For each currently violated constraint, use the cheapest modeled action that can affect one of its variables, ignoring prerequisites; take the maximum. Any complete plan must eventually pay at least that action cost for every violation, while the maximum avoids double-counting actions that resolve multiple constraints.',
            },
            'limits': {
                'max_states': self.max_states, 'max_depth': self.max_depth,
                'max_seconds': self.max_seconds, 'max_trace_events': self.max_trace_events,
            },
            'explanation': explanation,
            'trace': self._trace_events,
        }

    @staticmethod
    def _planned_action(action: ImprovementAction, before: PaperState, after: PaperState) -> dict[str, Any]:
        before_values = before.to_dict()
        after_values = after.to_dict()
        return {
            **action.to_dict(),
            'state_before': before_values,
            'state_after': after_values,
            'estimated_effect': {
                variable: {'from': before_values.get(variable), 'to': after_values.get(variable)}
                for variable in action.affected_variables
                if before_values.get(variable) != after_values.get(variable)
            },
        }

    def _trace(self, event: dict[str, Any]) -> None:
        event = {'step': len(self._trace_events) + 1, **event}
        if len(self._trace_events) < self.max_trace_events:
            self._trace_events.append(event)
        elif len(self._trace_events) == self.max_trace_events:
            self._trace_events.append({
                'step': len(self._trace_events) + 1,
                'event': 'TRACE_TRUNCATED', 'max_events': self.max_trace_events,
            })
