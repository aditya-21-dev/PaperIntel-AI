"""Module 7 agent: convert Module 6 output into an explainable search problem."""

from __future__ import annotations

import logging
from typing import Any

from app.compliance.agent import ComplianceAgent, MappedValue
from app.compliance.models import CSPValidationError
from app.compliance.profiles import resolve_profile
from app.observability import log_event

from .actions import build_improvement_actions
from .models import PaperState, StateValue
from .search import PlanningProblem, SearchPlanner


logger = logging.getLogger('paperintel.planning')


class PlanningInputError(ValueError):
    """Raised when the planner is not given a usable Module 6 compliance result."""


class ImprovementPlanningAgent:
    """A stateless, in-memory problem-solving agent for hypothetical improvements."""

    def build_problem(
        self,
        compliance_result: dict[str, Any],
        action_costs: object | None = None,
    ) -> tuple[PlanningProblem, dict[str, Any]]:
        self._validate_compliance_result(compliance_result)
        profile = self._profile_from_result(compliance_result['profile'])
        mapped: dict[str, MappedValue] = {}
        state_values: dict[str, StateValue] = {}
        for name, details in compliance_result['variables'].items():
            value = details.get('value')
            known = details.get('known') is True and self._is_state_value(value)
            evidence = details.get('evidence') if isinstance(details.get('evidence'), dict) else None
            mapped[name] = MappedValue(value if known else None, known, evidence)
            if known:
                state_values[name] = value
        csp_problem = ComplianceAgent().build_problem(mapped, profile)
        state = PaperState.from_dict(state_values)
        actions = build_improvement_actions(state, profile['requirements'], action_costs)
        return PlanningProblem(state, actions, csp_problem.constraints), profile

    def plan(
        self,
        compliance_result: dict[str, Any],
        method: str = 'astar',
        *,
        max_states: int = 250,
        max_depth: int = 12,
        max_seconds: float = 2.0,
        action_costs: object | None = None,
    ) -> dict[str, Any]:
        problem, profile = self.build_problem(compliance_result, action_costs)
        context = self._module_6_context(compliance_result, profile)
        if compliance_result.get('requirements_consistent') is False or compliance_result.get('status') == 'NO_SOLUTION':
            return self._non_search_result(
                'NO_SOLUTION', method, problem, context,
                'The selected requirement set is internally inconsistent, so no improvement plan can make a paper compliant with it.',
            )
        if context['status'] == 'LIMIT_EXCEEDED':
            return self._non_search_result(
                'INCOMPLETE', method, problem, context,
                'Module 6 reached its own safety limit, so no reliable compliance-reaching plan is generated from its incomplete result.',
            )
        if context['unknown_constraints']:
            return self._non_search_result(
                'INCOMPLETE', method, problem, context,
                'Module 6 reports required information as unknown. No reliable compliance-reaching plan is generated until those values are available; unknown information is not treated as a violation.',
            )
        planner = SearchPlanner(max_states=max_states, max_depth=max_depth, max_seconds=max_seconds)
        result = planner.solve(problem, method)
        if result['status'] in {'NO_SOLUTION', 'SEARCH_LIMIT_REACHED'}:
            log_event(
                logger, 'planning_search_not_completed', level=logging.WARNING,
                algorithm=result['algorithm'], status=result['status'], states_explored=result['states_explored'],
            )
        return {
            **result,
            'profile': profile,
            'module_6': context,
            'cost_model': self._cost_model(problem),
        }

    @staticmethod
    def _is_state_value(value: object) -> bool:
        return isinstance(value, (bool, int, str)) and not (isinstance(value, int) and not isinstance(value, bool) and value < 0)

    @staticmethod
    def _validate_compliance_result(compliance_result: object) -> None:
        if not isinstance(compliance_result, dict):
            raise PlanningInputError('A Module 6 compliance result object is required.')
        if not isinstance(compliance_result.get('profile'), dict) or not isinstance(compliance_result.get('variables'), dict):
            raise PlanningInputError('The Module 6 result must include profile and variable data.')
        if not isinstance(compliance_result.get('constraints'), dict):
            raise PlanningInputError('The Module 6 result must include grouped constraint results.')
        for name, details in compliance_result['variables'].items():
            if not isinstance(name, str) or not isinstance(details, dict) or not isinstance(details.get('known'), bool):
                raise PlanningInputError('The Module 6 variable representation is invalid.')

    @staticmethod
    def _profile_from_result(profile_result: dict[str, Any]) -> dict[str, Any]:
        requirements = profile_result.get('requirements')
        if not isinstance(requirements, dict):
            raise PlanningInputError('The Module 6 profile does not contain requirements.')
        profile_id = 'generic_research_paper' if profile_result.get('id') == 'generic_research_paper' else 'custom'
        try:
            return resolve_profile({
                'profile_id': profile_id,
                'name': profile_result.get('name'),
                'venue': profile_result.get('venue'),
                'requirements': requirements,
            })
        except CSPValidationError as exc:
            raise PlanningInputError(f'The Module 6 profile is invalid: {exc}') from None

    @staticmethod
    def _module_6_context(compliance_result: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        constraints = compliance_result['constraints']
        return {
            'status': compliance_result.get('status'),
            'requirements_consistent': compliance_result.get('requirements_consistent'),
            'profile': profile,
            'violations': constraints.get('violated', []),
            'unknown_constraints': constraints.get('unknown', []),
        }

    @staticmethod
    def _non_search_result(
        status: str,
        method: str,
        problem: PlanningProblem,
        context: dict[str, Any],
        explanation: str,
    ) -> dict[str, Any]:
        return {
            'success': True,
            'status': status,
            'algorithm': 'A*' if method.casefold() == 'astar' else 'Uniform-Cost Search',
            'profile': context['profile'],
            'module_6': context,
            'initial_state': problem.initial_state.to_dict(),
            'actions': [],
            'available_actions': [action.to_dict() for action in problem.actions],
            'cost_model': ImprovementPlanningAgent._cost_model(problem),
            'total_cost': 0,
            'final_state': problem.initial_state.to_dict(),
            'states_explored': 0,
            'search_depth': 0,
            'remaining_violations': [],
            'unresolved_constraints': [],
            'heuristic': None,
            'limits': None,
            'explanation': explanation,
            'trace': [],
        }

    @staticmethod
    def _cost_model(problem: PlanningProblem) -> dict[str, Any]:
        return {
            'unit': 'relative_planning_cost',
            'action_costs': {action.name: action.cost for action in problem.actions},
            'explanation': 'Configurable relative planning estimates used to choose a lower-cost hypothetical plan; they are not measurements of actual human effort.',
        }
