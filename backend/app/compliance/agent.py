"""Map Module 3 knowledge bases to CSP variables and explain publication compliance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.knowledge_engine import validate_knowledge_base

from .models import CSPProblem, CSPValidationError, CSPVariable, Constraint
from .profiles import SECTION_NAMES, resolve_profile
from .solver import CSPSolver


class ComplianceInputError(ValueError):
    """Raised for invalid paper data or profile input before CSP construction."""


@dataclass(frozen=True)
class MappedValue:
    value: bool | int | str | None
    known: bool
    evidence: dict[str, Any] | None


FACT_VARIABLES = {
    'PaperHasAbstract': 'AbstractPresent',
    'PaperHasKeywords': 'KeywordsPresent',
    'PaperHasIntroduction': 'IntroductionPresent',
    'PaperHasMethodology': 'MethodologyPresent',
    'PaperHasResults': 'ResultsPresent',
    'PaperHasConclusion': 'ConclusionPresent',
    'PaperHasReferences': 'ReferencesPresent',
    'PaperHasFigures': 'FiguresPresent',
    'PaperHasTables': 'TablesPresent',
}


class ComplianceAgent:
    """Stateless Module 6 agent; requirements are compiled into data-defined CSP constraints."""

    def __init__(self, solver: CSPSolver | None = None) -> None:
        self._solver = solver or CSPSolver()

    def analyze(self, knowledge_base: dict[str, Any], profile_spec: object | None = None) -> dict[str, Any]:
        profile = resolve_profile(profile_spec)
        mapped = self.map_paper(knowledge_base)
        problem = self.build_problem(mapped, profile)

        requirement_solver = self._solver.solve(problem, max_solutions=1)
        direct = self._direct_validation(problem, mapped)
        if requirement_solver['limit_reached']:
            return self._base_result(
                'LIMIT_EXCEEDED', profile, mapped, problem, direct, requirement_solver,
                requirements_consistent=None,
            )
        if requirement_solver['solutions_found'] == 0:
            return self._base_result(
                'NO_SOLUTION', profile, mapped, problem, direct, requirement_solver,
                requirements_consistent=False,
            )

        known_assignment = {name: item.value for name, item in mapped.items() if item.known}
        paper_solver = self._solver.solve(problem, known_assignment, max_solutions=1)
        violated = direct['violated']
        unknown = direct['unknown']
        status = 'NON_COMPLIANT' if violated else 'INCOMPLETE' if unknown else 'COMPLIANT'
        return self._base_result(
            status, profile, mapped, problem, direct, requirement_solver, requirements_consistent=True,
            paper_solver=paper_solver,
            possible_configurations=paper_solver['solutions'],
        )

    def validate(self, knowledge_base: dict[str, Any], profile_spec: object | None = None) -> dict[str, Any]:
        """Evaluate observed paper values only; this endpoint intentionally does not search."""
        profile = resolve_profile(profile_spec)
        mapped = self.map_paper(knowledge_base)
        problem = self.build_problem(mapped, profile)
        direct = self._direct_validation(problem, mapped)
        status = 'NON_COMPLIANT' if direct['violated'] else 'INCOMPLETE' if direct['unknown'] else 'COMPLIANT'
        return {
            'success': True,
            'status': status,
            'profile': profile,
            'variables': self._variable_output(problem, mapped),
            'constraints': direct,
            'violations': direct['violated'],
            'requirements_consistent': 'NOT_CHECKED',
            'solver': None,
            'solver_trace': [],
        }

    def map_paper(self, knowledge_base: dict[str, Any]) -> dict[str, MappedValue]:
        validation = validate_knowledge_base(knowledge_base)
        if not validation['valid']:
            raise ComplianceInputError('Knowledge base validation failed before compliance analysis.')
        facts = {
            fact.get('predicate'): fact for fact in knowledge_base.get('propositional_facts', [])
            if isinstance(fact, dict) and isinstance(fact.get('predicate'), str)
        }
        mapped: dict[str, MappedValue] = {}
        for predicate, variable in FACT_VARIABLES.items():
            fact = facts.get(predicate)
            if isinstance(fact, dict) and isinstance(fact.get('value'), bool):
                mapped[variable] = MappedValue(fact['value'], True, fact.get('evidence'))
            else:
                mapped[variable] = MappedValue(None, False, None)

        entities = knowledge_base.get('entities', {})
        paper = knowledge_base.get('paper', {})
        attributes = paper.get('attributes', {}) if isinstance(paper, dict) else {}
        page_count = attributes.get('page_count') if isinstance(attributes, dict) else None
        mapped['PageCount'] = self._number_value(page_count, 'paper.attributes.page_count')
        abstracts = entities.get('abstracts') if isinstance(entities, dict) else None
        abstract_word_count = None
        if isinstance(abstracts, list) and abstracts:
            attributes = abstracts[0].get('attributes') if isinstance(abstracts[0], dict) else None
            abstract_word_count = attributes.get('word_count') if isinstance(attributes, dict) else None
        if isinstance(abstract_word_count, int) and abstract_word_count >= 0:
            mapped['AbstractLength'] = self._number_value(abstract_word_count, 'entities.abstracts.attributes.word_count')
        elif mapped['AbstractPresent'].known and mapped['AbstractPresent'].value is False:
            mapped['AbstractLength'] = MappedValue(0, True, mapped['AbstractPresent'].evidence)
        else:
            mapped['AbstractLength'] = MappedValue(None, False, None)

        for entity_group, variable in (
            ('keywords', 'KeywordCount'), ('references', 'ReferenceCount'), ('authors', 'AuthorCount'),
        ):
            group = entities.get(entity_group) if isinstance(entities, dict) else None
            if isinstance(group, list):
                mapped[variable] = MappedValue(len(group), True, {
                    'source_module': 'knowledge_engine', 'source_field': f'entities.{entity_group}',
                })
            else:
                mapped[variable] = MappedValue(None, False, None)
        author_count = mapped['AuthorCount']
        mapped['AuthorInformationPresent'] = MappedValue(
            bool(author_count.value) if author_count.known else None,
            author_count.known,
            author_count.evidence,
        )

        positions = self._section_positions(entities)
        for section, position in positions.items():
            mapped[f'{section}Position'] = position
        return mapped

    def build_problem(self, mapped: dict[str, MappedValue], profile: dict[str, Any]) -> CSPProblem:
        requirements = profile['requirements']
        variables = {
            name: CSPVariable(name, self._domain_for(name, value, requirements), value.evidence)
            for name, value in mapped.items()
        }
        constraints: list[Constraint] = []

        def add(name: str, variable_names: tuple[str, ...], operator: str, expected: Any, explanation: str) -> None:
            constraints.append(Constraint(
                id=f'C{len(constraints) + 1:03d}', name=name, variables=variable_names,
                operator=operator, expected=expected, severity='ERROR', explanation=explanation,
            ))

        numeric_rules = (
            ('min_pages', 'PageCount', 'GREATER_THAN_OR_EQUAL', 'The paper must meet the minimum page count.'),
            ('max_pages', 'PageCount', 'LESS_THAN_OR_EQUAL', 'The paper must not exceed the maximum page count.'),
            ('min_abstract_words', 'AbstractLength', 'GREATER_THAN_OR_EQUAL', 'The abstract is below the required word count.'),
            ('max_abstract_words', 'AbstractLength', 'LESS_THAN_OR_EQUAL', 'The abstract exceeds the maximum word count.'),
            ('min_keywords', 'KeywordCount', 'GREATER_THAN_OR_EQUAL', 'The paper requires more keywords.'),
            ('min_references', 'ReferenceCount', 'GREATER_THAN_OR_EQUAL', 'The paper requires more references.'),
            ('max_references', 'ReferenceCount', 'LESS_THAN_OR_EQUAL', 'The paper exceeds the maximum reference count.'),
        )
        for key, variable, operator, explanation in numeric_rules:
            if key in requirements:
                add(key, (variable,), operator, requirements[key], explanation)
        boolean_rules = (
            ('abstract_required', 'AbstractPresent', 'The target venue requires an abstract.'),
            ('keywords_required', 'KeywordsPresent', 'The target venue requires keywords.'),
            ('figures_required', 'FiguresPresent', 'The target venue requires at least one figure.'),
            ('tables_required', 'TablesPresent', 'The target venue requires at least one table.'),
            ('author_information_required', 'AuthorInformationPresent', 'The target venue requires author information.'),
        )
        for key, variable, explanation in boolean_rules:
            if requirements.get(key) is True:
                add(key, (variable,), 'EQUALS', True, explanation)
        required_sections = requirements.get('required_sections', [])
        if required_sections:
            variables_for_sections = tuple(f'{SECTION_NAMES[item.casefold()]}Present' for item in required_sections)
            add('required_sections', variables_for_sections, 'ALL_EQUALS', True, 'The paper must include every required structural section.')
        if requirements.get('methodology_requires_results'):
            add('methodology_requires_results', ('MethodologyPresent', 'ResultsPresent'), 'IMPLIES', {'if': True, 'then': True}, 'A methodology section requires a results section for this profile.')
        if requirements.get('results_requires_methodology'):
            add('results_requires_methodology', ('ResultsPresent', 'MethodologyPresent'), 'IMPLIES', {'if': True, 'then': True}, 'A results section requires a methodology section for this profile.')
        for index, pair in enumerate(requirements.get('required_section_order', []), start=1):
            first, second = (SECTION_NAMES[item.casefold()] for item in pair)
            add(f'section_order_{index}', (f'{first}Position', f'{second}Position'), 'ORDERED', None, f'{first} must appear before {second}.')
        return CSPProblem(variables, tuple(constraints))

    def _direct_validation(self, problem: CSPProblem, mapped: dict[str, MappedValue]) -> dict[str, list[dict[str, Any]]]:
        assignment = {name: item.value for name, item in mapped.items() if item.known}
        grouped: dict[str, list[dict[str, Any]]] = {'satisfied': [], 'violated': [], 'unknown': []}
        for constraint in problem.constraints:
            status, actual = constraint.evaluate_partial(assignment)
            result = {
                'constraint_id': constraint.id,
                'constraint_name': constraint.name,
                'status': status,
                'actual': actual,
                'expected': constraint.expected_notation(),
                'difference': self._difference(constraint, actual, status),
                'severity': constraint.severity,
                'explanation': self._explanation(constraint, actual, status),
                'evidence': [mapped[variable].evidence for variable in constraint.variables if mapped[variable].evidence],
            }
            grouped[{'SATISFIED': 'satisfied', 'VIOLATED': 'violated', 'UNKNOWN': 'unknown'}[status]].append(result)
        return grouped

    @staticmethod
    def _number_value(value: object, source_field: str) -> MappedValue:
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return MappedValue(value, True, {'source_module': 'knowledge_engine', 'source_field': source_field})
        return MappedValue(None, False, None)

    @staticmethod
    def _section_positions(entities: object) -> dict[str, MappedValue]:
        positions: dict[str, MappedValue] = {
            name: MappedValue(None, False, None) for name in SECTION_NAMES.values()
        }
        sections = entities.get('sections') if isinstance(entities, dict) else None
        if not isinstance(sections, list):
            return positions
        for index, section in enumerate(sections, start=1):
            title = section.get('name') if isinstance(section, dict) else None
            if not isinstance(title, str):
                continue
            canonical = SECTION_NAMES.get(title.casefold())
            if canonical and not positions[canonical].known:
                positions[canonical] = MappedValue(index, True, {
                    'source_module': 'knowledge_engine', 'source_field': 'entities.sections', 'section': title,
                })
        return positions

    @staticmethod
    def _domain_for(name: str, mapped: MappedValue, requirements: dict[str, Any]) -> tuple[bool | int | str, ...]:
        if name.endswith('Present'):
            return (False, True)
        relevant_limits = [value for key, value in requirements.items() if key.startswith(('min_', 'max_')) and isinstance(value, int)]
        observed = mapped.value if mapped.known and isinstance(mapped.value, int) else 0
        if name.endswith('Position'):
            maximum = max(8, observed)
        else:
            maximum = max(30, observed, *relevant_limits)
        maximum = min(maximum, 500)
        domain = tuple(range(0, maximum + 1))
        if mapped.known and isinstance(mapped.value, int) and mapped.value not in domain:
            return tuple(sorted((*domain, mapped.value)))
        return domain

    @staticmethod
    def _difference(constraint: Constraint, actual: Any, status: str) -> int | None:
        if status != 'VIOLATED' or not isinstance(actual, int) or not isinstance(constraint.expected, int):
            return None
        if constraint.operator in {'LESS_THAN', 'LESS_THAN_OR_EQUAL'}:
            return actual - constraint.expected + (1 if constraint.operator == 'LESS_THAN' else 0)
        if constraint.operator in {'GREATER_THAN', 'GREATER_THAN_OR_EQUAL'}:
            return constraint.expected - actual + (1 if constraint.operator == 'GREATER_THAN' else 0)
        return None

    @staticmethod
    def _explanation(constraint: Constraint, actual: Any, status: str) -> str:
        if status == 'UNKNOWN':
            return f'{constraint.explanation} The required paper information is not available, so this constraint remains unresolved.'
        if status == 'SATISFIED':
            return f'{constraint.explanation} Actual value: {actual}; requirement: {constraint.expected_notation()}.'
        return f'{constraint.explanation} Actual value: {actual}; requirement: {constraint.expected_notation()}.'

    @staticmethod
    def _variable_output(problem: CSPProblem, mapped: dict[str, MappedValue]) -> dict[str, dict[str, Any]]:
        return {
            name: {
                'value': item.value,
                'known': item.known,
                'domain': list(problem.variables[name].domain),
                'evidence': item.evidence,
            }
            for name, item in mapped.items()
        }

    def _base_result(
        self,
        status: str,
        profile: dict[str, Any],
        mapped: dict[str, MappedValue],
        problem: CSPProblem,
        direct: dict[str, list[dict[str, Any]]],
        requirements_solver: dict[str, Any],
        requirements_consistent: bool | None,
        paper_solver: dict[str, Any] | None = None,
        possible_configurations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        solver = self._aggregate_solver_metrics(requirements_solver, paper_solver)
        return {
            'success': status != 'LIMIT_EXCEEDED',
            'status': status,
            'profile': profile,
            'requirements_consistent': requirements_consistent,
            'variables': self._variable_output(problem, mapped),
            'constraints': direct,
            'violations': direct['violated'],
            'possible_configurations': possible_configurations or [],
            'solver': solver,
            'solver_phases': {
                'requirements': self._solver_metrics(requirements_solver),
                'paper_assignment': self._solver_metrics(paper_solver) if paper_solver else None,
            },
            'solver_trace': self._combined_trace(requirements_solver, paper_solver),
        }

    @staticmethod
    def _solver_metrics(result: dict[str, Any]) -> dict[str, Any]:
        return {
            'solutions_found': result['solutions_found'],
            'backtracking_steps': result['backtracking_steps'],
            'constraint_checks': result['constraint_checks'],
            'propagation_steps': result['propagation_steps'],
            'nodes_visited': result['nodes_visited'],
            'limit_reached': result['limit_reached'],
            'conflicts': result['conflicts'],
        }

    def _aggregate_solver_metrics(
        self,
        requirements_solver: dict[str, Any],
        paper_solver: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Expose the total CSP work while retaining each phase separately above."""
        runs = [requirements_solver, *([paper_solver] if paper_solver else [])]
        primary = paper_solver or requirements_solver
        conflicts: list[dict[str, Any]] = []
        for run in runs:
            for conflict in run['conflicts']:
                if conflict not in conflicts:
                    conflicts.append(conflict)
        return {
            'solutions_found': primary['solutions_found'],
            'backtracking_steps': sum(run['backtracking_steps'] for run in runs),
            'constraint_checks': sum(run['constraint_checks'] for run in runs),
            'propagation_steps': sum(run['propagation_steps'] for run in runs),
            'nodes_visited': sum(run['nodes_visited'] for run in runs),
            'limit_reached': any(run['limit_reached'] for run in runs),
            'conflicts': conflicts,
        }

    @staticmethod
    def _combined_trace(
        requirements_solver: dict[str, Any],
        paper_solver: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Keep the two deterministic solve phases distinguishable in one expandable trace."""
        trace: list[dict[str, Any]] = []
        phases = [('REQUIREMENTS', requirements_solver)]
        if paper_solver:
            phases.append(('PAPER_ASSIGNMENT', paper_solver))
        for phase, result in phases:
            for event in result['trace']:
                trace.append({
                    **event,
                    'step': len(trace) + 1,
                    'phase': phase,
                    'phase_step': event.get('step'),
                })
        return trace
