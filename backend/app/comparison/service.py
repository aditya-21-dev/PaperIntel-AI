"""Compare two stored Module 8 analyses without rerunning Modules 3–7."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class AnalysisComparisonError(ValueError):
    """Raised when a comparison request is invalid."""


class AnalysisNotFoundError(LookupError):
    """Raised when one or both stored analyses cannot be located."""


class AnalysisComparisonMismatchError(AnalysisComparisonError):
    """Raised when two analyses do not belong to the same paper."""


READINESS_ORDER = (
    'READY',
    'COMPLIANT',
    'NEEDS_IMPROVEMENT',
    'INCOMPLETE',
    'ANALYSIS_ERROR',
)
STRUCTURAL_FACTS = (
    'PaperHasAbstract',
    'PaperHasKeywords',
    'PaperHasIntroduction',
    'PaperHasMethodology',
    'PaperHasResults',
    'PaperHasConclusion',
    'PaperHasReferences',
    'PaperHasFigures',
    'PaperHasTables',
)
NUMERIC_COMPLIANCE_VARIABLES = (
    ('page_count', 'PageCount'),
    ('abstract_length', 'AbstractLength'),
    ('keyword_count', 'KeywordCount'),
    ('reference_count', 'ReferenceCount'),
)


def compare_stored_analyses(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compare two persisted analyses belonging to the same paper."""
    analysis_a = _require_analysis(before, 'analysis_a')
    analysis_b = _require_analysis(after, 'analysis_b')
    if analysis_a['analysis_id'] == analysis_b['analysis_id']:
        return _same_analysis_result(analysis_a)

    paper_a = analysis_a.get('paper_id')
    paper_b = analysis_b.get('paper_id')
    if not isinstance(paper_a, str) or not isinstance(paper_b, str) or paper_a != paper_b:
        raise AnalysisComparisonMismatchError('Both analyses must belong to the same stored paper.')

    changes = _metric_changes(analysis_a, analysis_b)
    compliance_changes = _compliance_changes(analysis_a, analysis_b)
    logical_changes = _logical_changes(analysis_a, analysis_b)
    structural_changes = _structural_changes(analysis_a, analysis_b)
    improvement_plan_changes = _improvement_plan_changes(analysis_a, analysis_b)
    improvement_summary = _improvement_summary(
        changes,
        compliance_changes,
        logical_changes,
        structural_changes,
        improvement_plan_changes,
        analysis_a,
        analysis_b,
    )
    overall_result = _overall_result(
        changes,
        compliance_changes,
        logical_changes,
        structural_changes,
        improvement_plan_changes,
        analysis_a,
        analysis_b,
    )

    return {
        'paper_id': paper_a,
        'analysis_a': analysis_a['analysis_id'],
        'analysis_b': analysis_b['analysis_id'],
        'analysis_a_created_at': analysis_a.get('created_at'),
        'analysis_b_created_at': analysis_b.get('created_at'),
        'changes': changes,
        'compliance_changes': compliance_changes,
        'logical_changes': logical_changes,
        'structural_changes': structural_changes,
        'improvement_plan_changes': improvement_plan_changes,
        'improvement_summary': improvement_summary,
        'overall_result': overall_result,
    }


def _require_analysis(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AnalysisComparisonError(f'{label} must be a stored analysis object.')
    analysis_id = value.get('analysis_id')
    paper_id = value.get('paper_id')
    if not isinstance(analysis_id, str) or not isinstance(paper_id, str):
        raise AnalysisNotFoundError(f'{label} is missing a valid analysis_id or paper_id.')
    return value


def _same_analysis_result(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        'paper_id': analysis['paper_id'],
        'analysis_a': analysis['analysis_id'],
        'analysis_b': analysis['analysis_id'],
        'analysis_a_created_at': analysis.get('created_at'),
        'analysis_b_created_at': analysis.get('created_at'),
        'changes': [],
        'compliance_changes': {
            'resolved': [],
            'newly_violated': [],
            'unchanged': [],
            'constraints_resolved_count': 0,
            'newly_violated_count': 0,
        },
        'logical_changes': {'changed': [], 'unchanged': [], 'insufficient_data': True},
        'structural_changes': [],
        'improvement_plan_changes': {
            'before_status': _plan_status(analysis),
            'after_status': _plan_status(analysis),
            'before_actions': _plan_action_names(analysis),
            'after_actions': _plan_action_names(analysis),
            'summary': 'The same stored analysis was selected for both sides of the comparison.',
        },
        'improvement_summary': {
            'message': 'Both selections refer to the same stored analysis, so no version differences exist.',
            'overall_assessment_before': _overall_status(analysis),
            'overall_assessment_after': _overall_status(analysis),
            'compliance_status_before': _compliance_status(analysis),
            'compliance_status_after': _compliance_status(analysis),
        },
        'overall_result': 'UNCHANGED',
    }


def _metric_changes(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    before_paper = before.get('paper') if isinstance(before.get('paper'), dict) else {}
    after_paper = after.get('paper') if isinstance(after.get('paper'), dict) else {}
    page_before = before_paper.get('page_count')
    page_after = after_paper.get('page_count')
    if _comparable(page_before) and _comparable(page_after) and page_before != page_after:
        changes.append(_numeric_change('page_count', page_before, page_after, before, after, 'PageCount'))

    for field, variable in NUMERIC_COMPLIANCE_VARIABLES:
        if field == 'page_count':
            continue
        value_before = _compliance_variable_value(before, variable)
        value_after = _compliance_variable_value(after, variable)
        if _comparable(value_before) and _comparable(value_after) and value_before != value_after:
            changes.append(_numeric_change(field, value_before, value_after, before, after, variable))

    compliance_before = _compliance_status(before)
    compliance_after = _compliance_status(after)
    if compliance_before and compliance_after and compliance_before != compliance_after:
        changes.append({
            'field': 'compliance_status',
            'before': compliance_before,
            'after': compliance_after,
            'change': None,
            'direction': _readiness_direction(compliance_before, compliance_after, {
                'COMPLIANT': 4,
                'NON_COMPLIANT': 2,
                'INCOMPLETE': 1,
                'LIMIT_EXCEEDED': 1,
                'NO_SOLUTION': 1,
            }),
        })

    overall_before = _overall_status(before)
    overall_after = _overall_status(after)
    if overall_before and overall_after and overall_before != overall_after:
        changes.append({
            'field': 'overall_assessment',
            'before': overall_before,
            'after': overall_after,
            'change': None,
            'direction': _readiness_direction(overall_before, overall_after, {
                item: len(READINESS_ORDER) - index for index, item in enumerate(READINESS_ORDER)
            }),
        })

    keyword_before = _important_fact_value(before, 'PaperHasKeywords')
    keyword_after = _important_fact_value(after, 'PaperHasKeywords')
    if isinstance(keyword_before, bool) and isinstance(keyword_after, bool) and keyword_before != keyword_after:
        changes.append({
            'field': 'keywords_present',
            'before': keyword_before,
            'after': keyword_after,
            'change': None,
            'direction': _boolean_improvement(keyword_before, keyword_after),
        })

    return changes


def _numeric_change(
    field: str,
    before: int,
    after: int,
    before_analysis: dict[str, Any],
    after_analysis: dict[str, Any],
    variable: str,
) -> dict[str, Any]:
    direction = _numeric_direction(before, after, before_analysis, after_analysis, variable)
    return {
        'field': field,
        'before': before,
        'after': after,
        'change': after - before,
        'direction': direction,
    }


def _numeric_direction(
    before: int,
    after: int,
    before_analysis: dict[str, Any],
    after_analysis: dict[str, Any],
    variable: str,
) -> str:
    before_status = _constraint_status_for_variable(before_analysis, variable)
    after_status = _constraint_status_for_variable(after_analysis, variable)
    if before_status == 'VIOLATED' and after_status == 'SATISFIED':
        return 'IMPROVED'
    if before_status == 'SATISFIED' and after_status == 'VIOLATED':
        return 'REGRESSED'
    if before == after:
        return 'UNCHANGED'

    constraint = _constraint_for_variable(before_analysis, variable) or _constraint_for_variable(after_analysis, variable)
    expected = constraint.get('expected') if isinstance(constraint, dict) else None
    if isinstance(expected, str):
        if expected.startswith('<=') and after < before:
            return 'IMPROVED'
        if expected.startswith('<=') and after > before:
            return 'REGRESSED'
        if expected.startswith('>=') and after > before:
            return 'IMPROVED'
        if expected.startswith('>=') and after < before:
            return 'REGRESSED'
    return 'NEUTRAL'


def _compliance_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_map = _constraint_status_map(before)
    after_map = _constraint_status_map(after)
    if not before_map and not after_map:
        return {
            'resolved': [],
            'newly_violated': [],
            'unchanged': [],
            'constraints_resolved_count': 0,
            'newly_violated_count': 0,
            'insufficient_data': True,
        }

    resolved: list[dict[str, Any]] = []
    newly_violated: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    for constraint_id, status_before in before_map.items():
        status_after = after_map.get(constraint_id)
        if status_after is None:
            continue
        entry = {
            'constraint_id': constraint_id,
            'constraint_name': _constraint_name(before, after, constraint_id),
            'before': status_before,
            'after': status_after,
        }
        if status_before == 'VIOLATED' and status_after == 'SATISFIED':
            resolved.append(entry)
        elif status_before == 'SATISFIED' and status_after == 'VIOLATED':
            newly_violated.append(entry)
        elif status_before == status_after:
            unchanged.append(entry)

    return {
        'resolved': resolved,
        'newly_violated': newly_violated,
        'unchanged': unchanged,
        'constraints_resolved_count': len(resolved),
        'newly_violated_count': len(newly_violated),
        'insufficient_data': False,
    }


def _logical_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_logical = before.get('logical_verification') if isinstance(before.get('logical_verification'), dict) else {}
    after_logical = after.get('logical_verification') if isinstance(after.get('logical_verification'), dict) else {}
    if not before_logical and not after_logical:
        return {'changed': [], 'unchanged': [], 'insufficient_data': True}

    changed: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    for label, path in (
        ('resolution', ('resolution', 'status')),
        ('model_checking', ('model_checking', 'status')),
        ('consistency', ('consistency', 'status')),
    ):
        value_before = _nested_get(before_logical, path)
        value_after = _nested_get(after_logical, path)
        if not isinstance(value_before, str) or not isinstance(value_after, str):
            continue
        entry = {'field': label, 'before': value_before, 'after': value_after}
        if value_before != value_after:
            changed.append(entry)
        else:
            unchanged.append(entry)

    return {
        'changed': changed,
        'unchanged': unchanged,
        'insufficient_data': not changed and not unchanged,
    }


def _structural_changes(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    before_facts = _important_facts_map(before)
    after_facts = _important_facts_map(after)
    if not before_facts and not after_facts:
        return []

    changes: list[dict[str, Any]] = []
    for predicate in STRUCTURAL_FACTS:
        value_before = before_facts.get(predicate)
        value_after = after_facts.get(predicate)
        if not isinstance(value_before, bool) or not isinstance(value_after, bool):
            continue
        if value_before == value_after:
            continue
        changes.append({
            'field': predicate.replace('PaperHas', '').lower(),
            'before': value_before,
            'after': value_after,
            'direction': _boolean_improvement(value_before, value_after),
        })
    return changes


def _improvement_plan_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_status = _plan_status(before)
    after_status = _plan_status(after)
    before_actions = _plan_action_names(before)
    after_actions = _plan_action_names(after)

    if before_status is None and after_status is None:
        return {
            'before_status': None,
            'after_status': None,
            'before_actions': [],
            'after_actions': [],
            'summary': 'Improvement-plan data is unavailable in both analyses.',
            'insufficient_data': True,
        }

    summary = _plan_change_summary(before_status, after_status, before_actions, after_actions)
    return {
        'before_status': before_status,
        'after_status': after_status,
        'before_actions': before_actions,
        'after_actions': after_actions,
        'summary': summary,
        'insufficient_data': False,
    }


def _plan_change_summary(
    before_status: str | None,
    after_status: str | None,
    before_actions: list[str],
    after_actions: list[str],
) -> str:
    if before_status in {'PLAN_FOUND', 'SEARCH_LIMIT_REACHED'} and after_status == 'NO_IMPROVEMENT_NEEDED':
        if before_actions:
            return 'Previous improvement requirements are no longer detected.'
        return 'The later analysis reports that no improvement plan is required.'
    if before_actions and not after_actions and after_status == 'NO_IMPROVEMENT_NEEDED':
        return 'Previous improvement requirements are no longer detected.'
    if before_actions != after_actions:
        return 'The recommended improvement actions changed between analyses.'
    if before_status != after_status:
        return f'Improvement-plan status changed from {before_status} to {after_status}.'
    return 'The improvement plan is unchanged between analyses.'


def _improvement_summary(
    changes: list[dict[str, Any]],
    compliance_changes: dict[str, Any],
    logical_changes: dict[str, Any],
    structural_changes: list[dict[str, Any]],
    improvement_plan_changes: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    messages: list[str] = []
    resolved = compliance_changes.get('constraints_resolved_count', 0)
    newly_violated = compliance_changes.get('newly_violated_count', 0)
    if resolved:
        messages.append(f'{resolved} previously violated constraint{"s" if resolved != 1 else ""} are now satisfied.')
    if newly_violated:
        messages.append(f'{newly_violated} previously satisfied constraint{"s" if newly_violated != 1 else ""} are now violated.')

    for item in changes:
        if item.get('field') == 'page_count' and isinstance(item.get('before'), int) and isinstance(item.get('after'), int):
            messages.append(f'Page count changed from {item["before"]} to {item["after"]}.')
        if item.get('field') == 'abstract_length' and isinstance(item.get('before'), int) and isinstance(item.get('after'), int):
            messages.append(f'Abstract length changed from {item["before"]} to {item["after"]} words.')

    if improvement_plan_changes.get('summary'):
        messages.append(improvement_plan_changes['summary'])

    if not messages and not changes and not structural_changes and compliance_changes.get('insufficient_data'):
        message = 'Insufficient comparable stored data is available to summarize changes.'
    elif not messages:
        message = 'No material differences were detected in the comparable stored fields.'
    else:
        message = ' '.join(messages)

    return {
        'message': message,
        'overall_assessment_before': _overall_status(before),
        'overall_assessment_after': _overall_status(after),
        'compliance_status_before': _compliance_status(before),
        'compliance_status_after': _compliance_status(after),
        'resolved_constraints': resolved,
        'new_violations': newly_violated,
        'structural_change_count': len(structural_changes),
        'logical_change_count': len(logical_changes.get('changed', [])),
    }


def _overall_result(
    changes: list[dict[str, Any]],
    compliance_changes: dict[str, Any],
    logical_changes: dict[str, Any],
    structural_changes: list[dict[str, Any]],
    improvement_plan_changes: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
) -> str:
    comparable_present = any([
        changes,
        not compliance_changes.get('insufficient_data'),
        not logical_changes.get('insufficient_data'),
        structural_changes,
        not improvement_plan_changes.get('insufficient_data'),
    ])
    if not comparable_present:
        return 'INSUFFICIENT_DATA'

    improved_signals = 0
    regressed_signals = 0

    resolved = compliance_changes.get('constraints_resolved_count', 0)
    newly_violated = compliance_changes.get('newly_violated_count', 0)
    improved_signals += resolved
    regressed_signals += newly_violated

    for item in changes + structural_changes:
        direction = item.get('direction')
        if direction == 'IMPROVED':
            improved_signals += 1
        elif direction == 'REGRESSED':
            regressed_signals += 1

    overall_before = _overall_status(before)
    overall_after = _overall_status(after)
    if overall_before in READINESS_ORDER and overall_after in READINESS_ORDER:
        if READINESS_ORDER.index(overall_after) < READINESS_ORDER.index(overall_before):
            improved_signals += 1
        elif READINESS_ORDER.index(overall_after) > READINESS_ORDER.index(overall_before):
            regressed_signals += 1

    compliance_before = _compliance_status(before)
    compliance_after = _compliance_status(after)
    if compliance_before == 'NON_COMPLIANT' and compliance_after == 'COMPLIANT':
        improved_signals += 1
    elif compliance_before == 'COMPLIANT' and compliance_after == 'NON_COMPLIANT':
        regressed_signals += 1

    plan_before = _plan_status(before)
    plan_after = _plan_status(after)
    if plan_before in {'PLAN_FOUND', 'SEARCH_LIMIT_REACHED'} and plan_after == 'NO_IMPROVEMENT_NEEDED':
        improved_signals += 1
    elif plan_before == 'NO_IMPROVEMENT_NEEDED' and plan_after in {'PLAN_FOUND', 'SEARCH_LIMIT_REACHED'}:
        regressed_signals += 1

    for item in logical_changes.get('changed', []):
        if item.get('after') in {'ENTAILED', 'CONSISTENT'} and item.get('before') not in {'ENTAILED', 'CONSISTENT'}:
            improved_signals += 1
        if item.get('before') in {'ENTAILED', 'CONSISTENT'} and item.get('after') not in {'ENTAILED', 'CONSISTENT'}:
            regressed_signals += 1

    if improved_signals == 0 and regressed_signals == 0:
        return 'UNCHANGED'
    if improved_signals > 0 and regressed_signals > 0:
        return 'MIXED'
    if improved_signals > regressed_signals:
        return 'IMPROVED'
    if regressed_signals > improved_signals:
        return 'REGRESSED'
    return 'UNCHANGED'


def _constraint_status_map(analysis: dict[str, Any]) -> dict[str, str]:
    compliance = analysis.get('compliance_analysis')
    if not isinstance(compliance, dict):
        return {}
    constraints = compliance.get('constraints')
    if not isinstance(constraints, dict):
        return {}
    result: dict[str, str] = {}
    for bucket in ('satisfied', 'violated', 'unknown'):
        for item in constraints.get(bucket, []):
            if isinstance(item, dict) and isinstance(item.get('constraint_id'), str):
                result[item['constraint_id']] = bucket.upper() if bucket != 'unknown' else 'UNKNOWN'
                if bucket == 'satisfied':
                    result[item['constraint_id']] = 'SATISFIED'
                elif bucket == 'violated':
                    result[item['constraint_id']] = 'VIOLATED'
    return result


def _constraint_name(before: dict[str, Any], after: dict[str, Any], constraint_id: str) -> str:
    for analysis in (before, after):
        compliance = analysis.get('compliance_analysis')
        if not isinstance(compliance, dict):
            continue
        constraints = compliance.get('constraints')
        if not isinstance(constraints, dict):
            continue
        for bucket in ('satisfied', 'violated', 'unknown'):
            for item in constraints.get(bucket, []):
                if isinstance(item, dict) and item.get('constraint_id') == constraint_id:
                    name = item.get('constraint_name')
                    if isinstance(name, str):
                        return name
    return constraint_id


def _constraint_for_variable(analysis: dict[str, Any], variable: str) -> dict[str, Any] | None:
    compliance = analysis.get('compliance_analysis')
    if not isinstance(compliance, dict):
        return None
    constraints = compliance.get('constraints')
    if not isinstance(constraints, dict):
        return None
    all_items: list[dict[str, Any]] = []
    for bucket in ('satisfied', 'violated', 'unknown'):
        for item in constraints.get(bucket, []):
            if isinstance(item, dict):
                all_items.append(item)
    # First pass: named match — check constraint_name before falling back to int heuristic.
    for item in all_items:
        if variable == 'PageCount' and item.get('constraint_name') in {'max_pages', 'min_pages'}:
            return item
        if variable == 'AbstractLength' and item.get('constraint_name') in {'max_abstract_words', 'min_abstract_words'}:
            return item
        if variable == 'ReferenceCount' and item.get('constraint_name') in {'min_references', 'max_references'}:
            return item
        if variable == 'KeywordCount' and item.get('constraint_name') == 'min_keywords':
            return item
    return None



def _constraint_status_for_variable(analysis: dict[str, Any], variable: str) -> str | None:
    constraint = _constraint_for_variable(analysis, variable)
    if not isinstance(constraint, dict):
        return None
    status = constraint.get('status')
    return status if isinstance(status, str) else None


def _compliance_variable_value(analysis: dict[str, Any], variable: str) -> int | None:
    compliance = analysis.get('compliance_analysis')
    if not isinstance(compliance, dict):
        return None
    variables = compliance.get('variables')
    if not isinstance(variables, dict):
        return None
    entry = variables.get(variable)
    if not isinstance(entry, dict) or entry.get('known') is not True:
        return None
    value = entry.get('value')
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _important_facts_map(analysis: dict[str, Any]) -> dict[str, bool]:
    knowledge = analysis.get('knowledge_analysis')
    if not isinstance(knowledge, dict):
        return {}
    facts = knowledge.get('important_facts')
    if not isinstance(facts, list):
        return {}
    result: dict[str, bool] = {}
    for fact in facts:
        if isinstance(fact, dict) and isinstance(fact.get('predicate'), str) and isinstance(fact.get('value'), bool):
            result[fact['predicate']] = fact['value']
    return result


def _important_fact_value(analysis: dict[str, Any], predicate: str) -> bool | None:
    value = _important_facts_map(analysis).get(predicate)
    return value if isinstance(value, bool) else None


def _compliance_status(analysis: dict[str, Any]) -> str | None:
    compliance = analysis.get('compliance_analysis')
    if not isinstance(compliance, dict):
        return None
    status = compliance.get('status')
    return status if isinstance(status, str) else None


def _overall_status(analysis: dict[str, Any]) -> str | None:
    assessment = analysis.get('overall_assessment')
    if not isinstance(assessment, dict):
        return None
    status = assessment.get('status')
    return status if isinstance(status, str) else None


def _plan_status(analysis: dict[str, Any]) -> str | None:
    plan = analysis.get('improvement_plan')
    if not isinstance(plan, dict):
        return None
    status = plan.get('status')
    return status if isinstance(status, str) else None


def _plan_action_names(analysis: dict[str, Any]) -> list[str]:
    plan = analysis.get('improvement_plan')
    if not isinstance(plan, dict):
        return []
    actions = plan.get('actions')
    if not isinstance(actions, list):
        return []
    names: list[str] = []
    for action in actions:
        if isinstance(action, dict) and isinstance(action.get('name'), str):
            names.append(action['name'])
    return names


def _nested_get(value: dict[str, Any], path: tuple[str, ...]) -> object | None:
    current: object = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _comparable(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _readiness_direction(before: str, after: str, ordering: dict[str, int]) -> str:
    if before == after:
        return 'UNCHANGED'
    before_rank = ordering.get(before)
    after_rank = ordering.get(after)
    if before_rank is None or after_rank is None:
        return 'NEUTRAL'
    if after_rank > before_rank:
        return 'IMPROVED'
    if after_rank < before_rank:
        return 'REGRESSED'
    return 'UNCHANGED'


def _boolean_improvement(before: bool, after: bool) -> str:
    if before == after:
        return 'UNCHANGED'
    if after and not before:
        return 'IMPROVED'
    if before and not after:
        return 'REGRESSED'
    return 'NEUTRAL'
