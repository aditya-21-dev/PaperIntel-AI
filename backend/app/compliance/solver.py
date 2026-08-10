"""Generic finite-domain propagation, forward checking, MRV, and backtracking for Module 6."""

from __future__ import annotations

from copy import deepcopy
from itertools import product
from typing import Any

from .models import CSPProblem, Constraint, value_sort_key


class CSPSolver:
    """Solve declarative CSPs with generalized arc consistency before MRV backtracking."""

    def __init__(self, max_nodes: int = 2500, max_trace_events: int = 500) -> None:
        self.max_nodes = max_nodes
        self.max_trace_events = max_trace_events
        self._reset()

    def solve(
        self,
        problem: CSPProblem,
        initial_assignment: dict[str, bool | int | str] | None = None,
        max_solutions: int = 1,
    ) -> dict[str, Any]:
        if max_solutions < 1:
            raise ValueError('max_solutions must be at least one.')
        self._reset()
        domains = {name: set(variable.domain) for name, variable in problem.variables.items()}
        assignment = dict(initial_assignment or {})
        for variable, value in assignment.items():
            if variable not in domains:
                raise ValueError(f'Initial assignment references unknown variable {variable!r}.')
            if value not in domains[variable]:
                self._conflict('assignment_outside_domain', variable=variable, value=value)
                return self._result([], domains, limit_reached=False)
            before = self._domain_list(domains[variable])
            domains[variable] = {value}
            self._trace({'event': 'initial_assignment', 'variable': variable, 'value': value, 'domain_before': before})

        if not self._propagate(problem, domains, assigned_variables=set(assignment)):
            return self._result([], domains, limit_reached=False)

        solutions: list[dict[str, bool | int | str]] = []
        self._search(problem, domains, solutions, max_solutions, depth=0)
        return self._result(solutions, domains, limit_reached=self._limit_reached)

    def _reset(self) -> None:
        self._trace_events: list[dict[str, Any]] = []
        self._conflicts: list[dict[str, Any]] = []
        self._constraint_checks = 0
        self._propagation_steps = 0
        self._backtracking_steps = 0
        self._nodes_visited = 0
        self._limit_reached = False

    def _search(
        self,
        problem: CSPProblem,
        domains: dict[str, set[bool | int | str]],
        solutions: list[dict[str, bool | int | str]],
        max_solutions: int,
        depth: int,
    ) -> None:
        if len(solutions) >= max_solutions or self._limit_reached:
            return
        self._nodes_visited += 1
        if self._nodes_visited > self.max_nodes:
            self._limit_reached = True
            self._trace({'event': 'search_limit_reached', 'max_nodes': self.max_nodes})
            return
        if all(len(domain) == 1 for domain in domains.values()):
            solution = {name: next(iter(domain)) for name, domain in domains.items()}
            if self._all_constraints_satisfied(problem, solution):
                solutions.append(solution)
                self._trace({'event': 'solution_found', 'assignment': solution, 'depth': depth})
            return

        variable = self._select_mrv(problem, domains)
        before = self._domain_list(domains[variable])
        ordered_values = self._order_values_lcv(problem, variable, domains)
        self._trace({
            'event': 'variable_selected', 'variable': variable, 'heuristic': 'MRV_with_degree_tiebreaker',
            'domain_before': before, 'ordered_values': ordered_values, 'depth': depth,
        })
        for value in ordered_values:
            if len(solutions) >= max_solutions or self._limit_reached:
                return
            branch_domains = deepcopy(domains)
            branch_domains[variable] = {value}
            self._trace({'event': 'value_selected', 'variable': variable, 'value': value, 'depth': depth})
            before_solutions = len(solutions)
            if self._forward_check(problem, branch_domains, variable):
                self._search(problem, branch_domains, solutions, max_solutions, depth + 1)
            if len(solutions) == before_solutions and not self._limit_reached:
                self._backtracking_steps += 1
                self._trace({'event': 'backtrack', 'variable': variable, 'value': value, 'depth': depth})

    def _forward_check(
        self,
        problem: CSPProblem,
        domains: dict[str, set[bool | int | str]],
        assigned_variable: str,
    ) -> bool:
        """Prune neighbouring domains immediately after a search assignment."""
        self._trace({'event': 'forward_check_started', 'variable': assigned_variable})
        return self._propagate(problem, domains, assigned_variables={assigned_variable})

    def _propagate(
        self,
        problem: CSPProblem,
        domains: dict[str, set[bool | int | str]],
        assigned_variables: set[str] | None = None,
    ) -> bool:
        """AC-style propagation: prune unsupported values and revisit affected constraints."""
        affected = {name: [] for name in problem.variables}
        for index, constraint in enumerate(problem.constraints):
            for variable in constraint.variables:
                affected[variable].append(index)
        queue = (
            sorted({index for variable in assigned_variables or set() for index in affected[variable]})
            if assigned_variables
            else list(range(len(problem.constraints)))
        )
        queued = set(queue)
        while queue:
            constraint_index = queue.pop(0)
            queued.discard(constraint_index)
            constraint = problem.constraints[constraint_index]
            self._trace({
                'event': 'constraint_checked', 'constraint_id': constraint.id,
                'constraint_name': constraint.name, 'variables': list(constraint.variables),
            })
            for variable in constraint.variables:
                before = set(domains[variable])
                viable = {
                    value for value in before
                    if self._has_support(constraint, variable, value, domains)
                }
                if not viable:
                    domains[variable] = set()
                    self._conflict('empty_domain', constraint_id=constraint.id, variable=variable)
                    self._trace({'event': 'conflict_detected', 'constraint_id': constraint.id, 'variable': variable, 'reason': 'empty_domain'})
                    return False
                if viable != before:
                    domains[variable] = viable
                    self._propagation_steps += 1
                    self._trace({
                        'event': 'domain_reduced', 'constraint_id': constraint.id, 'variable': variable,
                        'domain_before': self._domain_list(before), 'domain_after': self._domain_list(viable),
                    })
                    for neighbor_index in affected[variable]:
                        if neighbor_index not in queued:
                            queue.append(neighbor_index)
                            queued.add(neighbor_index)
        return True

    def _has_support(
        self,
        constraint: Constraint,
        variable: str,
        value: bool | int | str,
        domains: dict[str, set[bool | int | str]],
    ) -> bool:
        other_variables = [candidate for candidate in constraint.variables if candidate != variable]
        other_domains = [self._domain_list(domains[candidate]) for candidate in other_variables]
        for candidate_values in product(*other_domains):
            values = {variable: value, **dict(zip(other_variables, candidate_values))}
            self._constraint_checks += 1
            if constraint.is_satisfied(values):
                return True
        return False

    def _select_mrv(self, problem: CSPProblem, domains: dict[str, set[bool | int | str]]) -> str:
        candidates = [name for name, domain in domains.items() if len(domain) > 1]

        def key(name: str) -> tuple[int, int, str]:
            degree = sum(1 for constraint in problem.constraints if name in constraint.variables and len(constraint.variables) > 1)
            return len(domains[name]), -degree, name

        return min(candidates, key=key)

    def _order_values_lcv(
        self,
        problem: CSPProblem,
        variable: str,
        domains: dict[str, set[bool | int | str]],
    ) -> list[bool | int | str]:
        """Least-constraining-value ordering based on viable neighbour-domain values."""
        neighboring = [constraint for constraint in problem.constraints if variable in constraint.variables]
        scores: list[tuple[int, tuple[str, str], bool | int | str]] = []
        for value in self._domain_list(domains[variable]):
            simulated = deepcopy(domains)
            simulated[variable] = {value}
            remaining = 0
            for constraint in neighboring:
                for neighbor in constraint.variables:
                    if neighbor == variable:
                        continue
                    remaining += sum(
                        1 for candidate in simulated[neighbor]
                        if self._has_support(constraint, neighbor, candidate, simulated)
                    )
            scores.append((-remaining, value_sort_key(value), value))
        return [value for _, _, value in sorted(scores)]

    def _all_constraints_satisfied(self, problem: CSPProblem, assignment: dict[str, bool | int | str]) -> bool:
        for constraint in problem.constraints:
            self._constraint_checks += 1
            if not constraint.is_satisfied({variable: assignment[variable] for variable in constraint.variables}):
                return False
        return True

    def _trace(self, event: dict[str, Any]) -> None:
        event_types = {
            'initial_assignment': 'VALUE_ASSIGNED',
            'variable_selected': 'VARIABLE_SELECTED',
            'value_selected': 'VALUE_ASSIGNED',
            'constraint_checked': 'CONSTRAINT_CHECKED',
            'domain_reduced': 'DOMAIN_REDUCED',
            'conflict_detected': 'CONFLICT_DETECTED',
            'backtrack': 'BACKTRACK',
            'solution_found': 'SOLUTION_FOUND',
            'forward_check_started': 'FORWARD_CHECK',
        }
        event = {
            'step': len(self._trace_events) + 1,
            'event_type': event_types.get(event.get('event'), str(event.get('event', '')).upper()),
            **event,
        }
        if len(self._trace_events) < self.max_trace_events:
            self._trace_events.append(event)
        elif len(self._trace_events) == self.max_trace_events:
            self._trace_events.append({
                'step': len(self._trace_events) + 1,
                'event': 'trace_truncated', 'event_type': 'TRACE_TRUNCATED', 'max_events': self.max_trace_events,
            })

    def _conflict(self, conflict_type: str, **details: Any) -> None:
        conflict = {'type': conflict_type, **details}
        if conflict not in self._conflicts:
            self._conflicts.append(conflict)

    @staticmethod
    def _domain_list(domain: set[bool | int | str]) -> list[bool | int | str]:
        return sorted(domain, key=value_sort_key)

    def _result(
        self,
        solutions: list[dict[str, bool | int | str]],
        domains: dict[str, set[bool | int | str]],
        limit_reached: bool,
    ) -> dict[str, Any]:
        return {
            'success': not limit_reached,
            'solutions': solutions,
            'solutions_found': len(solutions),
            'domains': {name: self._domain_list(domain) for name, domain in domains.items()},
            'constraint_checks': self._constraint_checks,
            'propagation_steps': self._propagation_steps,
            'backtracking_steps': self._backtracking_steps,
            'nodes_visited': self._nodes_visited,
            'limit_reached': limit_reached,
            'conflicts': self._conflicts,
            'trace': self._trace_events,
        }
