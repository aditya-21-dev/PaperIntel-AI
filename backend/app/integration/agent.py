"""Module 8 orchestration for the existing PaperIntel AI pipeline.

This module deliberately contains no new inference, CSP, or search algorithm.
It invokes Modules 3--7, preserves their native results, and creates a small,
evidence-backed report that correlates those results.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from app.compliance.agent import ComplianceAgent
from app.logic.agent import LogicAgent
from app.observability import log_event
from app.planning.agent import ImprovementPlanningAgent
from app.reasoning.agent import ReasoningAgent
from app.services.knowledge_engine import KnowledgeAgent


MODULES: tuple[tuple[str, str], ...] = (
    ('module_3', 'Module 3'),
    ('module_4', 'Module 4'),
    ('module_5', 'Module 5'),
    ('module_6', 'Module 6'),
    ('module_7', 'Module 7'),
)

# This is a shared data mapping used to compare the values emitted by Modules 3
# and 6. It does not evaluate either representation.
FACT_TO_COMPLIANCE_VARIABLE = {
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
logger = logging.getLogger('paperintel.integration')


class IntegrationInputError(ValueError):
    """Raised when the Module 8 request cannot safely start the pipeline."""


class ModuleExecutionError(RuntimeError):
    """Wrap a module failure with the response information Module 8 needs."""

    def __init__(self, module: str, cause: Exception | str) -> None:
        self.module = module
        self.cause = str(cause) or type(cause).__name__
        super().__init__(self.cause)


class IntegratedAnalysisAgent:
    """Call Modules 3--7 and aggregate their already-computed evidence."""

    def __init__(
        self,
        knowledge_agent: KnowledgeAgent | None = None,
        reasoning_agent: ReasoningAgent | None = None,
        logic_agent: LogicAgent | None = None,
        compliance_agent: ComplianceAgent | None = None,
        planning_agent: ImprovementPlanningAgent | None = None,
    ) -> None:
        self._knowledge = knowledge_agent or KnowledgeAgent()
        self._reasoning = reasoning_agent or ReasoningAgent()
        self._logic = logic_agent or LogicAgent()
        self._compliance = compliance_agent or ComplianceAgent()
        self._planning = planning_agent or ImprovementPlanningAgent()

    def run(
        self,
        paper: dict[str, Any],
        requirements: object | None = None,
        options: object | None = None,
    ) -> dict[str, Any]:
        """Run the established pipeline over one Module 2 structured paper."""
        self._validate_input(paper, requirements, options)
        selected_options = deepcopy(options) if isinstance(options, dict) else {}
        statuses = self._initial_statuses()
        results: dict[str, Any] = {}

        try:
            knowledge_base, validation = self._knowledge.perceive(paper)
            if not validation.get('valid'):
                raise ValueError('Knowledge-base validation failed.')
            results['knowledge_base'] = knowledge_base
            results['knowledge_validation'] = validation
            self._complete(statuses, 'module_3')
        except Exception as exc:  # Existing modules expose several validation exception types.
            return self._failure('Module 3', exc, statuses, results)

        paper_id = knowledge_base['paper']['id']
        reasoning_goal = self._goal_from_options(selected_options, paper_id)
        logical_query = selected_options.get('logical_query', reasoning_goal)
        planning_options = self._planning_options(selected_options)

        try:
            forward = self._reasoning.forward_reason(knowledge_base)
            backward = self._reasoning.backward_reason(reasoning_goal, knowledge_base)
            if forward.get('success') is not True or backward.get('success') is not True:
                raise ValueError(forward.get('error') or backward.get('error') or 'Reasoning reached a safety limit.')
            results['reasoning'] = {'forward': forward, 'backward': backward, 'goal': reasoning_goal}
            self._complete(statuses, 'module_4')
        except Exception as exc:
            return self._failure('Module 4', exc, statuses, results)

        try:
            model_checking = self._logic.model_check(
                knowledge_base,
                logical_query,
                bool(selected_options.get('include_models', False)),
            )
            resolution = self._logic.prove(knowledge_base, logical_query)
            consistency = self._logic.consistency(knowledge_base)
            if not isinstance(model_checking, dict) or not isinstance(resolution, dict) or not isinstance(consistency, dict):
                raise ValueError('Logical verification returned an invalid result.')
            results['logical_verification'] = {
                'query': logical_query,
                'model_checking': model_checking,
                'resolution': resolution,
                'consistency': consistency,
            }
            self._complete(statuses, 'module_5')
        except Exception as exc:
            return self._failure('Module 5', exc, statuses, results)

        try:
            compliance = self._compliance.analyze(knowledge_base, requirements)
            if not isinstance(compliance, dict) or not isinstance(compliance.get('constraints'), dict):
                raise ValueError('Compliance analysis returned an invalid result.')
            results['compliance'] = compliance
            self._complete(statuses, 'module_6', self._module_result_status(compliance))
        except Exception as exc:
            return self._failure('Module 6', exc, statuses, results)

        try:
            improvement_plan = self._planning.plan(compliance, **planning_options)
            if not isinstance(improvement_plan, dict) or not isinstance(improvement_plan.get('actions'), list):
                raise ValueError('Improvement planning returned an invalid result.')
            results['improvement_plan'] = improvement_plan
            self._complete(statuses, 'module_7', self._module_result_status(improvement_plan))
        except Exception as exc:
            return self._failure('Module 7', exc, statuses, results)

        return self._complete_analysis(statuses, results)

    @staticmethod
    def _validate_input(paper: object, requirements: object | None, options: object | None) -> None:
        if not isinstance(paper, dict):
            raise IntegrationInputError('paper must be a Module 2 structured-paper object.')
        if requirements is not None and not isinstance(requirements, dict):
            raise IntegrationInputError('requirements must be an object when supplied.')
        if options is not None and not isinstance(options, dict):
            raise IntegrationInputError('options must be an object when supplied.')

    @staticmethod
    def _goal_from_options(options: dict[str, Any], paper_id: str) -> dict[str, Any]:
        goal = options.get('reasoning_goal')
        if goal is None:
            return {'predicate': 'CoreStructureComplete', 'arguments': [paper_id], 'value': True}
        if not isinstance(goal, dict):
            raise IntegrationInputError('options.reasoning_goal must be an object when supplied.')
        return deepcopy(goal)

    @staticmethod
    def _planning_options(options: dict[str, Any]) -> dict[str, Any]:
        method = options.get('planning_method', options.get('method', 'astar'))
        if not isinstance(method, str) or method.casefold() not in {'astar', 'ucs'}:
            raise IntegrationInputError("options.planning_method must be 'astar' or 'ucs'.")
        result: dict[str, Any] = {'method': method}
        for name in ('max_states', 'max_depth', 'max_seconds', 'action_costs'):
            if name in options:
                result[name] = options[name]
        return result

    @staticmethod
    def _initial_statuses() -> list[dict[str, Any]]:
        return [
            {'id': identifier, 'module': module, 'status': 'NOT_RUN', 'result_status': None}
            for identifier, module in MODULES
        ]

    @staticmethod
    def _complete(statuses: list[dict[str, Any]], identifier: str, result_status: str = 'COMPLETE') -> None:
        entry = next(item for item in statuses if item['id'] == identifier)
        entry.update({'status': 'COMPLETE', 'result_status': result_status})

    @staticmethod
    def _module_result_status(result: dict[str, Any]) -> str:
        status = result.get('status')
        return status if isinstance(status, str) else 'COMPLETE'

    def _failure(
        self,
        failed_module: str,
        error: Exception,
        statuses: list[dict[str, Any]],
        results: dict[str, Any],
    ) -> dict[str, Any]:
        failed_id = next(identifier for identifier, module in MODULES if module == failed_module)
        failed_entry = next(item for item in statuses if item['id'] == failed_id)
        safe_message = self._safe_error_message(error)
        log_event(
            logger, 'module_execution_failed', level=logging.WARNING,
            module=failed_module, error_type=type(error).__name__,
        )
        failed_entry.update({'status': 'FAILED', 'result_status': type(error).__name__, 'error': safe_message})
        completed = [item['module'] for item in statuses if item['status'] == 'COMPLETE']
        not_run = [item['module'] for item in statuses if item['status'] == 'NOT_RUN']
        partial = self._partial_sections(results)
        return {
            'success': False,
            'analysis_status': 'PARTIAL_ANALYSIS',
            'failed_module': failed_module,
            'completed_modules': completed,
            'not_run_modules': not_run,
            'error': {
                'type': type(error).__name__,
                'message': safe_message,
            },
            'module_statuses': statuses,
            **partial,
            'overall_assessment': {
                'status': 'ANALYSIS_ERROR',
                'meaning': 'A required module failed, so this response is a partial analysis and is not a complete paper assessment.',
                'reasons': [f'{failed_module} did not complete.'],
            },
            'evidence': self._partial_evidence(results),
            'explanations': [
                {
                    'finding': 'Partial analysis only.',
                    'source_module': failed_module,
                    'explanation': safe_message,
                },
            ],
        }

    @staticmethod
    def _safe_error_message(error: Exception) -> str:
        message = str(error).replace('\n', ' ').strip()
        return message[:300] or 'The module could not complete its analysis.'

    def _complete_analysis(self, statuses: list[dict[str, Any]], results: dict[str, Any]) -> dict[str, Any]:
        knowledge = self._knowledge_analysis(results['knowledge_base'], results['knowledge_validation'])
        reasoning = results['reasoning']
        logical = results['logical_verification']
        compliance = results['compliance']
        plan = results['improvement_plan']
        inconsistencies = self._cross_module_inconsistencies(results['knowledge_base'], compliance)
        cross_findings = self._cross_module_findings(reasoning, logical, compliance, plan)
        evidence = self._evidence(results['knowledge_base'], logical, compliance, plan, cross_findings)
        assessment = self._overall_assessment(logical, compliance, plan, inconsistencies)
        paper = self._paper_summary(results['knowledge_base'])
        report = self._report(paper, knowledge, reasoning, logical, compliance, plan, assessment, cross_findings, evidence, inconsistencies)
        return {
            'success': True,
            'analysis_status': 'COMPLETE',
            'paper': paper,
            'module_statuses': statuses,
            'knowledge_analysis': knowledge,
            'reasoning_analysis': reasoning,
            'logical_verification': logical,
            'compliance_analysis': compliance,
            'improvement_plan': {
                **plan,
                'projected_state_notice': 'The projected state is hypothetical. The paper has not been modified.',
            },
            'cross_module_findings': cross_findings,
            'cross_module_inconsistencies': inconsistencies,
            'overall_assessment': assessment,
            'evidence': evidence,
            'explanations': [item['explanation'] for item in cross_findings],
            'report': report,
        }

    @staticmethod
    def _paper_summary(knowledge_base: dict[str, Any]) -> dict[str, Any]:
        paper = knowledge_base['paper']
        attributes = paper.get('attributes', {})
        return {
            'id': paper.get('id'),
            'name': paper.get('name'),
            'filename': attributes.get('filename'),
            'page_count': attributes.get('page_count'),
            'source_module': 'Module 3',
            'evidence': paper.get('evidence'),
        }

    @staticmethod
    def _knowledge_analysis(knowledge_base: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
        entities = knowledge_base.get('entities', {})
        facts = knowledge_base.get('propositional_facts', [])
        relationships = knowledge_base.get('relationships', [])
        structural_facts = [
            fact for fact in facts
            if isinstance(fact, dict) and fact.get('predicate', '').startswith('PaperHas')
        ]
        sections = [
            {'id': item.get('id'), 'name': item.get('name'), 'evidence': item.get('evidence')}
            for item in entities.get('sections', [])
            if isinstance(item, dict)
        ]
        return {
            'summary': {
                'entity_counts': {name: len(items) for name, items in entities.items() if isinstance(items, list)},
                'fact_count': len(facts),
                'relationship_count': len(relationships),
                'validation': validation,
            },
            'paper_structure': sections,
            'important_facts': structural_facts,
            'evidence_references': [fact.get('evidence') for fact in structural_facts if isinstance(fact.get('evidence'), dict)],
            # Detailed graph evidence remains available without duplicating every entity.
            'knowledge_trace': {
                'relationships': relationships,
                'evidence': knowledge_base.get('evidence', []),
            },
        }

    @staticmethod
    def _cross_module_inconsistencies(knowledge_base: dict[str, Any], compliance: dict[str, Any]) -> list[dict[str, Any]]:
        facts = {
            item.get('predicate'): item
            for item in knowledge_base.get('propositional_facts', [])
            if isinstance(item, dict) and isinstance(item.get('predicate'), str)
        }
        variables = compliance.get('variables', {})
        conflicts: list[dict[str, Any]] = []
        for predicate, variable in FACT_TO_COMPLIANCE_VARIABLE.items():
            fact = facts.get(predicate)
            result = variables.get(variable) if isinstance(variables, dict) else None
            if not isinstance(fact, dict) or not isinstance(fact.get('value'), bool) or not isinstance(result, dict):
                continue
            module_6_known = result.get('known') is True
            module_6_value = result.get('value') if module_6_known else 'UNKNOWN'
            if not module_6_known or result.get('value') is not fact['value']:
                conflicts.append({
                    'type': 'CROSS_MODULE_DATA_INCONSISTENCY',
                    'affected_field': variable,
                    'severity': 'HIGH' if module_6_known else 'MEDIUM',
                    'source_modules': ['Module 3', 'Module 6'],
                    'values': {
                        'Module 3': fact['value'],
                        'Module 6': module_6_value,
                    },
                    'evidence': {
                        'module_3': fact.get('evidence'),
                        'module_6': result.get('evidence'),
                    },
                    'explanation': f'Module 3 represents {predicate} as {fact["value"]}, while Module 6 represents {variable} as {module_6_value}.',
                })
        return conflicts

    @staticmethod
    def _cross_module_findings(
        reasoning: dict[str, Any],
        logical: dict[str, Any],
        compliance: dict[str, Any],
        plan: dict[str, Any],
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        backward = reasoning['backward']
        resolution = logical['resolution']
        if backward.get('established') and resolution.get('status') == 'ENTAILED':
            goal = resolution.get('query_notation') or backward.get('goal')
            findings.append({
                'finding': f'{goal} is supported by rule-based reasoning and logically verified.',
                'source_modules': ['Module 4', 'Module 5'],
                'evidence': {
                    'backward_supporting_facts': backward.get('supporting_facts', []),
                    'reasoning_rule': backward.get('rule_used'),
                    'verification': 'resolution',
                },
                'explanation': 'The backward-chaining goal was established and the same logical query was entailed by propositional resolution.',
            })

        actions = plan.get('actions', []) if isinstance(plan.get('actions'), list) else []
        for violation in compliance.get('constraints', {}).get('violated', []):
            if not isinstance(violation, dict):
                continue
            matching_actions = [
                {'id': action.get('id'), 'name': action.get('name'), 'explanation': action.get('explanation')}
                for action in actions
                if isinstance(action, dict)
                and set(action.get('affected_variables', [])) & set(_constraint_variables(violation, compliance))
            ]
            finding = {
                'finding': f"{violation.get('constraint_name', 'A publication requirement')} is violated.",
                'source_modules': ['Module 6'],
                'evidence': {
                    'source_constraint': violation.get('constraint_id'),
                    'actual': violation.get('actual'),
                    'required': violation.get('expected'),
                    'evidence': violation.get('evidence', []),
                },
                'explanation': violation.get('explanation', 'A selected publication requirement is violated.'),
            }
            if matching_actions:
                finding['source_modules'].append('Module 7')
                finding['recommended_actions'] = matching_actions
                finding['explanation'] = f"{finding['explanation']} Module 7 selected a hypothetical action that affects this modeled requirement."
            findings.append(finding)
        return findings

    @staticmethod
    def _evidence(
        knowledge_base: dict[str, Any],
        logical: dict[str, Any],
        compliance: dict[str, Any],
        plan: dict[str, Any],
        findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for fact in knowledge_base.get('propositional_facts', []):
            if isinstance(fact, dict) and fact.get('value') is True:
                evidence.append({
                    'finding': fact.get('predicate'),
                    'source_module': 'Module 3',
                    'evidence': fact.get('evidence'),
                })
        resolution = logical.get('resolution', {})
        evidence.append({
            'finding': resolution.get('query_notation'),
            'source_module': 'Module 5',
            'verification': 'resolution',
            'status': resolution.get('status'),
            'proof_steps': resolution.get('proof_steps', []),
        })
        for violation in compliance.get('constraints', {}).get('violated', []):
            if isinstance(violation, dict):
                evidence.append({
                    'finding': violation.get('constraint_name'),
                    'source_module': 'Module 6',
                    'source_constraint': violation.get('constraint_id'),
                    'evidence': {
                        'actual': violation.get('actual'),
                        'required': violation.get('expected'),
                        'source_evidence': violation.get('evidence', []),
                    },
                })
        for action in plan.get('actions', []):
            if isinstance(action, dict):
                evidence.append({
                    'finding': action.get('name'),
                    'source_module': 'Module 7',
                    'evidence': {'estimated_effect': action.get('estimated_effect'), 'cost': action.get('cost')},
                })
        return evidence

    @staticmethod
    def _overall_assessment(
        logical: dict[str, Any],
        compliance: dict[str, Any],
        plan: dict[str, Any],
        inconsistencies: list[dict[str, Any]],
    ) -> dict[str, Any]:
        compliance_status = compliance.get('status')
        plan_status = plan.get('status')
        consistent = logical.get('consistency', {}).get('consistent')
        reasons: list[str] = []
        if inconsistencies:
            reasons.append('Cross-module data inconsistencies require review.')
            status = 'INCOMPLETE'
        elif compliance_status in {'INCOMPLETE', 'LIMIT_EXCEEDED', 'NO_SOLUTION'} or plan_status in {'INCOMPLETE', 'SEARCH_LIMIT_REACHED'}:
            reasons.append('Required information or a complete modeled compliance path is unavailable.')
            status = 'INCOMPLETE'
        elif compliance_status == 'NON_COMPLIANT' or consistent is False:
            reasons.append('At least one modeled requirement is violated or the knowledge base is logically inconsistent.')
            status = 'NEEDS_IMPROVEMENT'
        elif compliance_status == 'COMPLIANT' and plan_status == 'NO_IMPROVEMENT_NEEDED' and consistent is True:
            reasons.append('All modeled publication constraints are satisfied, the knowledge base is consistent, and no modeled improvement is needed.')
            status = 'READY'
        elif compliance_status == 'COMPLIANT':
            reasons.append('All modeled publication constraints are satisfied.')
            status = 'COMPLIANT'
        else:
            reasons.append('The module outputs do not support a complete readiness conclusion.')
            status = 'INCOMPLETE'
        return {
            'status': status,
            'meaning': {
                'READY': 'All modeled constraints are satisfied, logical consistency was confirmed, and no modeled improvement is needed.',
                'COMPLIANT': 'All selected publication constraints are satisfied by the observed paper values.',
                'NEEDS_IMPROVEMENT': 'A modeled problem needs attention; recommendations are hypothetical and do not modify the paper.',
                'INCOMPLETE': 'Required information is unknown, a safety limit was reached, requirements conflict, or module outputs disagree.',
                'ANALYSIS_ERROR': 'A required module failed, so the response is only a partial analysis.',
            }[status],
            'reasons': reasons,
            'compliance_status': compliance_status,
            'planning_status': plan_status,
            'logical_consistency': consistent,
        }

    @staticmethod
    def _report(
        paper: dict[str, Any],
        knowledge: dict[str, Any],
        reasoning: dict[str, Any],
        logical: dict[str, Any],
        compliance: dict[str, Any],
        plan: dict[str, Any],
        assessment: dict[str, Any],
        findings: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
        inconsistencies: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            'executive_summary': {
                'status': assessment['status'],
                'reasons': assessment['reasons'],
                'projected_state_notice': 'The projected state is hypothetical. The paper has not been modified.',
            },
            'paper_overview': paper,
            'structural_findings': knowledge['important_facts'],
            'knowledge_based_findings': findings,
            'logical_verification': {
                'resolution_status': logical['resolution'].get('status'),
                'model_checking_status': logical['model_checking'].get('status'),
                'consistency_status': logical['consistency'].get('status'),
            },
            'publication_compliance': {
                'status': compliance.get('status'),
                'satisfied': compliance.get('constraints', {}).get('satisfied', []),
                'violated': compliance.get('constraints', {}).get('violated', []),
                'unknown': compliance.get('constraints', {}).get('unknown', []),
            },
            'detected_problems': {
                'compliance_violations': compliance.get('constraints', {}).get('violated', []),
                'cross_module_inconsistencies': inconsistencies,
            },
            'recommended_improvement_plan': {
                'status': plan.get('status'),
                'algorithm': plan.get('algorithm'),
                'actions': plan.get('actions', []),
                'total_cost': plan.get('total_cost'),
                'projected_state': plan.get('final_state'),
            },
            'evidence': evidence,
            'reasoning_trace': {
                'forward': reasoning['forward'].get('reasoning_trace', []),
                'backward': reasoning['backward'].get('reasoning_trace', []),
                'logical_proof': logical['resolution'].get('proof_steps', []),
                'compliance_constraints': compliance.get('solver_trace', []),
                'search_trace': plan.get('trace', []),
            },
            'overall_assessment': assessment,
        }

    def _partial_sections(self, results: dict[str, Any]) -> dict[str, Any]:
        knowledge_base = results.get('knowledge_base')
        sections: dict[str, Any] = {
            'paper': self._paper_summary(knowledge_base) if isinstance(knowledge_base, dict) else None,
            'knowledge_analysis': self._knowledge_analysis(knowledge_base, results.get('knowledge_validation', {})) if isinstance(knowledge_base, dict) else None,
            'reasoning_analysis': results.get('reasoning'),
            'logical_verification': results.get('logical_verification'),
            'compliance_analysis': results.get('compliance'),
            'improvement_plan': results.get('improvement_plan'),
        }
        return sections

    @staticmethod
    def _partial_evidence(results: dict[str, Any]) -> list[dict[str, Any]]:
        knowledge_base = results.get('knowledge_base')
        if not isinstance(knowledge_base, dict):
            return []
        return [
            {'finding': fact.get('predicate'), 'source_module': 'Module 3', 'evidence': fact.get('evidence')}
            for fact in knowledge_base.get('propositional_facts', [])
            if isinstance(fact, dict) and fact.get('value') is True
        ]


def _constraint_variables(violation: dict[str, Any], compliance: dict[str, Any]) -> list[str]:
    """Recover a violation's affected variables from Module 6's serialized CSP data."""
    name = violation.get('constraint_name')
    requirements = compliance.get('profile', {}).get('requirements', {})
    mapping = {
        'max_pages': ['PageCount'], 'min_pages': ['PageCount'],
        'max_abstract_words': ['AbstractLength'], 'min_abstract_words': ['AbstractLength'],
        'abstract_required': ['AbstractPresent'], 'keywords_required': ['KeywordsPresent'],
        'min_keywords': ['KeywordCount'], 'min_references': ['ReferenceCount'],
        'max_references': ['ReferenceCount'], 'figures_required': ['FiguresPresent'],
        'tables_required': ['TablesPresent'], 'author_information_required': ['AuthorCount'],
    }
    if isinstance(name, str) and name in mapping:
        return mapping[name]
    if name == 'required_sections' and isinstance(requirements, dict):
        return [f'{section}Present' for section in requirements.get('required_sections', []) if isinstance(section, str)]
    return []
