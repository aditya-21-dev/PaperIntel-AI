"""Build data-defined improvement actions from a Module 6 requirement profile."""

from __future__ import annotations

from typing import Any

from .models import Condition, ImprovementAction, PaperState, StateEffect


SECTION_VARIABLES = {
    'Introduction': 'IntroductionPresent',
    'Methodology': 'MethodologyPresent',
    'Results': 'ResultsPresent',
    'Conclusion': 'ConclusionPresent',
}


# These are relative planning estimates, not measurements of human effort.  Keeping
# them together lets callers safely tune the optimization objective without putting
# policy into either search algorithm.
DEFAULT_ACTION_COSTS = {
    'ReducePageCount': 4,
    'DevelopPaperScope': 5,
    'ReduceAbstractLength': 2,
    'DevelopAbstract': 3,
    'AddReferences': 3,
    'CurateReferenceList': 3,
    'AddKeywords': 1,
    'PrepareAbstract': 3,
    'PrepareRequiredFigure': 5,
    'PrepareRequiredTable': 5,
    'ProvideAuthorInformation': 1,
    'CompleteIntroductionSection': 4,
    'CompleteMethodologySection': 4,
    'CompleteResultsSection': 4,
    'CompleteConclusionSection': 4,
    'DevelopResultsSection': 4,
    'DevelopMethodologySection': 4,
}


def resolve_action_costs(overrides: object | None = None) -> dict[str, int]:
    """Return validated configured costs for the currently modeled action types."""
    if overrides is None:
        return dict(DEFAULT_ACTION_COSTS)
    if not isinstance(overrides, dict):
        raise ValueError('action_costs must be an object mapping modeled action names to positive integer costs.')
    if not all(isinstance(name, str) for name in overrides):
        raise ValueError('Each action_costs key must be a modeled action name.')
    unknown = sorted(set(overrides) - set(DEFAULT_ACTION_COSTS))
    if unknown:
        raise ValueError(f'action_costs contains unsupported modeled action names: {unknown}.')
    configured = dict(DEFAULT_ACTION_COSTS)
    for name, cost in overrides.items():
        if not isinstance(name, str) or not isinstance(cost, int) or isinstance(cost, bool) or not 1 <= cost <= 100:
            raise ValueError('Each action cost must be an integer between 1 and 100.')
        configured[name] = cost
    return configured


def build_improvement_actions(
    state: PaperState,
    requirements: dict[str, Any],
    action_costs: object | None = None,
) -> tuple[ImprovementAction, ...]:
    """Create only actions that affect values represented in the current paper state.

    Costs are configurable planning estimates, not measurements of actual human effort.
    Actions describe hypothetical changes and never alter a document or source knowledge base.
    """
    state_values = state.to_dict()
    costs = resolve_action_costs(action_costs)
    actions: list[ImprovementAction] = []

    def add(
        name: str,
        preconditions: tuple[Condition, ...],
        effects: tuple[StateEffect, ...],
        explanation: str,
    ) -> None:
        if not effects:
            return
        actions.append(ImprovementAction(
            id=f'A{len(actions) + 1:03d}', name=name, preconditions=preconditions,
            effects=effects, cost=costs[name],
            affected_variables=tuple(effect.variable for effect in effects), explanation=explanation,
        ))

    def numeric_limit(
        requirement: str,
        variable: str,
        condition: str,
        name: str,
        explanation: str,
    ) -> None:
        target = requirements.get(requirement)
        if variable in state_values and isinstance(target, int) and not isinstance(target, bool):
            add(name, (Condition(variable, condition, target),), (StateEffect(variable, 'SET', target),), explanation)

    numeric_limit('max_pages', 'PageCount', 'GREATER_THAN', 'ReducePageCount', 'Reduce the paper length to the permitted page limit.')
    numeric_limit('min_pages', 'PageCount', 'LESS_THAN', 'DevelopPaperScope', 'Develop substantive material until the minimum page count is met.')
    numeric_limit('max_abstract_words', 'AbstractLength', 'GREATER_THAN', 'ReduceAbstractLength', 'Condense the abstract to the permitted word limit without generating replacement text.')
    numeric_limit('min_abstract_words', 'AbstractLength', 'LESS_THAN', 'DevelopAbstract', 'Develop the abstract until it reaches the required minimum word count.')
    numeric_limit('min_references', 'ReferenceCount', 'LESS_THAN', 'AddReferences', 'Identify and add suitable real references until the minimum reference count is met.')
    numeric_limit('max_references', 'ReferenceCount', 'GREATER_THAN', 'CurateReferenceList', 'Curate the reference list to the permitted maximum without inventing citations.')
    numeric_limit('min_keywords', 'KeywordCount', 'LESS_THAN', 'AddKeywords', 'Add relevant keywords until the required keyword count is met.')

    if requirements.get('abstract_required') is True and 'AbstractPresent' in state_values:
        effects = [StateEffect('AbstractPresent', 'SET', True)]
        if 'AbstractLength' in state_values and state_values['AbstractLength'] == 0:
            effects.append(StateEffect('AbstractLength', 'SET', max(1, requirements.get('min_abstract_words', 1))))
        add('PrepareAbstract', (Condition('AbstractPresent', 'EQUALS', False),), tuple(effects), 'Prepare an abstract that meets the selected publication requirements.')

    if requirements.get('keywords_required') is True and 'KeywordsPresent' in state_values:
        effects = [StateEffect('KeywordsPresent', 'SET', True)]
        if 'KeywordCount' in state_values:
            effects.append(StateEffect('KeywordCount', 'SET', max(1, requirements.get('min_keywords', 1))))
        add('AddKeywords', (Condition('KeywordsPresent', 'EQUALS', False),), tuple(effects), 'Add relevant paper keywords; this plan does not generate keyword text.')

    for requirement, variable, name, explanation in (
        ('figures_required', 'FiguresPresent', 'PrepareRequiredFigure', 'Prepare an appropriate figure required by the venue.'),
        ('tables_required', 'TablesPresent', 'PrepareRequiredTable', 'Prepare an appropriate table required by the venue.'),
        ('author_information_required', 'AuthorInformationPresent', 'ProvideAuthorInformation', 'Provide the required author information.'),
    ):
        if requirements.get(requirement) is True and variable in state_values:
            add(name, (Condition(variable, 'EQUALS', False),), (StateEffect(variable, 'SET', True),), explanation)

    for section in requirements.get('required_sections', []):
        variable = SECTION_VARIABLES.get(section)
        if variable and variable in state_values:
            add(
                f'Complete{section}Section', (Condition(variable, 'EQUALS', False),),
                (StateEffect(variable, 'SET', True),),
                f'Add or complete the required {section} section; this is a planning suggestion only.',
            )

    if requirements.get('methodology_requires_results') and {'MethodologyPresent', 'ResultsPresent'} <= set(state_values):
        add(
            'DevelopResultsSection',
            (Condition('MethodologyPresent', 'EQUALS', True), Condition('ResultsPresent', 'EQUALS', False)),
            (StateEffect('ResultsPresent', 'SET', True),),
            'Develop a results section because the selected profile requires results when methodology is present.',
        )
    if requirements.get('results_requires_methodology') and {'MethodologyPresent', 'ResultsPresent'} <= set(state_values):
        add(
            'DevelopMethodologySection',
            (Condition('ResultsPresent', 'EQUALS', True), Condition('MethodologyPresent', 'EQUALS', False)),
            (StateEffect('MethodologyPresent', 'SET', True),),
            'Develop a methodology section because the selected profile requires it when results are present.',
        )
    return tuple(actions)
