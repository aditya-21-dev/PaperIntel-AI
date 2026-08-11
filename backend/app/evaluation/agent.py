"""Module 9: run bounded, deterministic benchmark cases against PaperIntel."""

from __future__ import annotations

from collections import defaultdict
from time import perf_counter
from typing import Any

from app.compliance.agent import ComplianceAgent
from app.integration.agent import IntegratedAnalysisAgent
from app.logic.agent import LogicAgent
from app.planning.agent import ImprovementPlanningAgent
from app.planning.search import SearchPlanner
from app.reasoning.agent import ReasoningAgent
from app.services.knowledge_engine import KnowledgeEngine
from app.services.pdf_parser import PDFParser

from . import benchmarks


class SystemEvaluationAgent:
    """Evaluate existing modules without changing their algorithms or input data."""

    def __init__(
        self,
        pdf_parser: PDFParser | None = None,
        knowledge_engine: KnowledgeEngine | None = None,
        reasoning_agent: ReasoningAgent | None = None,
        logic_agent: LogicAgent | None = None,
        compliance_agent: ComplianceAgent | None = None,
        planning_agent: ImprovementPlanningAgent | None = None,
        integration_agent: IntegratedAnalysisAgent | None = None,
    ) -> None:
        self._pdf_parser = pdf_parser or PDFParser()
        self._knowledge = knowledge_engine or KnowledgeEngine()
        self._reasoning = reasoning_agent or ReasoningAgent()
        self._logic = logic_agent or LogicAgent()
        self._compliance = compliance_agent or ComplianceAgent()
        self._planning = planning_agent or ImprovementPlanningAgent()
        self._integration = integration_agent or IntegratedAnalysisAgent()

    def run(self) -> dict[str, Any]:
        """Run all repository-maintained Module 9 benchmark cases once."""
        started = perf_counter()
        modules = [
            self.evaluate_pdf_extraction(),
            self.evaluate_knowledge_representation(),
            self.evaluate_reasoning(),
            self.evaluate_logical_verification(),
            self.evaluate_compliance(),
            self.evaluate_planning(),
            self.evaluate_integrated_analysis(),
        ]
        measured = [item for item in modules if item['status'] == 'MEASURED']
        total_cases = sum(item['case_count'] for item in measured)
        passed_cases = sum(item['passed_cases'] for item in measured)
        integration = next(item for item in modules if item['id'] == 'module_8')
        return {
            'success': True,
            'title': 'SYSTEM EVALUATION',
            'status': 'COMPLETE',
            'benchmark': {
                'description': 'Small deterministic cases maintained with the repository. Scores are calculated only from declared ground truth.',
                'module_count': len(modules), 'case_count': total_cases,
            },
            'modules': modules,
            'summary': {
                'status': 'MEASURED', 'case_count': total_cases, 'passed_cases': passed_cases,
                'failed_cases': total_cases - passed_cases,
                'success_rate': _ratio(passed_cases, total_cases),
                'execution_time_ms': _milliseconds(started),
                'end_to_end_success_rate': integration['metrics']['success_rate'],
            },
        }

    def evaluate_pdf_extraction(self, cases: tuple[dict[str, Any], ...] | None = None) -> dict[str, Any]:
        cases = cases if cases is not None else benchmarks.pdf_extraction_cases()
        annotated = [case for case in cases if isinstance(case.get('ground_truth'), dict)]
        if not annotated:
            return _not_evaluated('module_2', 'PDF Processing', 'Ground-truth extraction annotations are unavailable.')
        started = perf_counter()
        field_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        case_results: list[dict[str, Any]] = []
        for case in annotated:
            actual = self._pdf_parser.parse(benchmarks.build_pdf_bytes(case['pages']))
            actual_fields = _extraction_fields(actual)
            expected = case['ground_truth']
            matches = all(actual_fields.get(field, set()) == values for field, values in expected.items())
            case_results.append({'id': case['id'], 'passed': matches})
            for field, values in expected.items():
                field_result = _set_metrics(actual_fields.get(field, set()), values)
                for name in ('true_positives', 'false_positives', 'false_negatives'):
                    field_counts[field][name] += field_result[name]
        field_metrics = {
            field: _metrics_from_counts(**counts)
            for field, counts in sorted(field_counts.items())
        }
        overall = _combine_metrics(field_metrics.values())
        return _measured(
            'module_2', 'PDF Processing', case_results, started,
            {**overall, 'field_metrics': field_metrics},
            'Exact-field matching against annotated, generated PDF fixtures.',
        )

    def evaluate_knowledge_representation(self) -> dict[str, Any]:
        started = perf_counter()
        actual_values: list[bool] = []
        expected_values: list[bool] = []
        case_results: list[dict[str, Any]] = []
        for case in benchmarks.knowledge_cases():
            knowledge_base, validation = self._knowledge.build(case['input'])
            facts = {fact['predicate']: fact['value'] for fact in knowledge_base['propositional_facts']}
            expected = case['expected_facts']
            passed = validation['valid'] and all(facts.get(name) is value for name, value in expected.items())
            case_results.append({'id': case['id'], 'passed': passed})
            actual_values.extend(facts.get(name) for name in expected)
            expected_values.extend(expected.values())
        metrics = _boolean_metrics(actual_values, expected_values)
        return _measured('module_3', 'Knowledge Representation', case_results, started, metrics, 'Propositional facts compared with declared structured-paper truth.')

    def evaluate_reasoning(self) -> dict[str, Any]:
        started = perf_counter()
        expected_labels: list[str] = []
        actual_labels: list[str] = []
        rule_checks = 0
        rule_passes = 0
        case_results: list[dict[str, Any]] = []
        for case in benchmarks.reasoning_cases():
            knowledge_base, _ = self._knowledge.build(case['input'])
            forward = self._reasoning.forward_reason(knowledge_base)
            backward = self._reasoning.backward_reason(case['goal'], knowledge_base)
            actual_label = _reasoning_status(backward)
            expected_labels.append(case['expected_status'])
            actual_labels.append(actual_label)
            expected_derived = case['expected_derived']
            actual_derived = {fact['predicate'] for fact in forward['derived_facts']}
            rule_checks += len(expected_derived)
            rule_passes += len(expected_derived & actual_derived)
            case_results.append({
                'id': case['id'], 'passed': actual_label == case['expected_status'] and expected_derived <= actual_derived,
                'expected_status': case['expected_status'], 'actual_status': actual_label,
            })
        metrics = _classification_metrics(actual_labels, expected_labels)
        metrics['rule_execution_correctness'] = _ratio(rule_passes, rule_checks) if rule_checks else None
        metrics['rule_execution_checks'] = rule_checks
        return _measured('module_4', 'Rule-based Reasoning', case_results, started, metrics, 'Backward conclusions and expected forward rule derivations are compared with known cases.')

    def evaluate_logical_verification(self) -> dict[str, Any]:
        started = perf_counter()
        expected_labels: list[str] = []
        actual_labels: list[str] = []
        case_results: list[dict[str, Any]] = []
        for case in benchmarks.logic_cases():
            knowledge_base, _ = self._knowledge.build(case['input'])
            if case['operation'] == 'inconsistent_consistency':
                knowledge_base = benchmarks.contradictory_knowledge_base(knowledge_base)
            result = self._logic.consistency(knowledge_base) if case['operation'].endswith('consistency') else self._logic.prove(knowledge_base, case['query'])
            actual = result['status']
            expected = case['expected_status']
            actual_labels.append(actual)
            expected_labels.append(expected)
            case_results.append({'id': case['id'], 'passed': actual == expected, 'expected_status': expected, 'actual_status': actual})
        return _measured('module_5', 'Logical Verification', case_results, started, _classification_metrics(actual_labels, expected_labels), 'Resolution and consistency results are compared with known logical outcomes.')

    def evaluate_compliance(self) -> dict[str, Any]:
        started = perf_counter()
        expected_labels: list[str] = []
        actual_labels: list[str] = []
        expected_constraint_labels: list[str] = []
        actual_constraint_labels: list[str] = []
        totals = defaultdict(int)
        case_results: list[dict[str, Any]] = []
        for case in benchmarks.compliance_cases():
            knowledge_base, _ = self._knowledge.build(case['input'])
            result = self._compliance.analyze(knowledge_base, case['requirements'])
            actual = result['status']
            expected = case['expected_status']
            expected_labels.append(expected)
            actual_labels.append(actual)
            grouped = result['constraints']
            actual_constraints = {
                item['constraint_name']: item['status']
                for group in grouped.values() for item in group
            }
            expected_constraints = case['expected_constraints']
            expected_constraint_labels.extend(expected_constraints.values())
            actual_constraint_labels.extend(actual_constraints.get(name, 'MISSING') for name in expected_constraints)
            solver = result.get('solver') or {}
            for name in ('constraint_checks', 'propagation_steps', 'backtracking_steps', 'nodes_visited'):
                totals[name] += int(solver.get(name, 0))
            totals['forward_checking_operations'] += sum(1 for item in result.get('solver_trace', []) if item.get('event_type') == 'FORWARD_CHECK')
            totals['mrv_selections'] += sum(1 for item in result.get('solver_trace', []) if item.get('event_type') == 'VARIABLE_SELECTED')
            passed = (
                actual == expected and result['requirements_consistent'] is case['expected_requirements_consistent']
                and all(actual_constraints.get(name) == status for name, status in expected_constraints.items())
            )
            case_results.append({'id': case['id'], 'passed': passed, 'expected_status': expected, 'actual_status': actual})
        metrics = {
            'classification': _classification_metrics(actual_labels, expected_labels),
            'constraint_classification': _classification_metrics(actual_constraint_labels, expected_constraint_labels),
            'solver_statistics': dict(totals),
        }
        return _measured('module_6', 'CSP Compliance', case_results, started, metrics, 'Compliance status, declared constraint classes, and requirement consistency are checked against known cases.')

    def evaluate_planning(self) -> dict[str, Any]:
        started = perf_counter()
        methods = ('ucs', 'astar')
        records: dict[str, list[dict[str, Any]]] = {method: [] for method in methods}
        case_results: list[dict[str, Any]] = []
        for case in benchmarks.planning_cases():
            results: dict[str, dict[str, Any]] = {}
            timings: dict[str, float] = {}
            for method in methods:
                result, elapsed = self._run_planning_case(case, method)
                results[method], timings[method] = result, elapsed
                passed = result['status'] == case['expected_status'] and result['total_cost'] == case['expected_cost']
                records[method].append({'case_id': case['id'], 'result': result, 'elapsed_ms': elapsed, 'passed': passed})
                case_results.append({'id': f"{case['id']}:{method}", 'passed': passed, 'expected_status': case['expected_status'], 'actual_status': result['status']})
        by_method = {method: _planning_method_metrics(items) for method, items in records.items()}
        comparisons = [
            {
                'case_id': case['id'],
                'ucs': _planning_comparison(records['ucs'], case['id']),
                'astar': _planning_comparison(records['astar'], case['id']),
            }
            for case in benchmarks.planning_cases()
        ]
        return _measured('module_7', 'Search Improvement Planning', case_results, started, {'by_method': by_method, 'comparisons': comparisons}, 'UCS and A* run the same plan-found and no-solution cases; all reported costs and counts are measured.')

    def evaluate_integrated_analysis(self) -> dict[str, Any]:
        started = perf_counter()
        case_results: list[dict[str, Any]] = []
        for case in benchmarks.integration_cases():
            result = self._integration.run(case['input'], case['requirements'])
            actual = result.get('overall_assessment', {}).get('status')
            passed = result.get('success') is True and result.get('analysis_status') == 'COMPLETE' and actual == case['expected_status']
            case_results.append({'id': case['id'], 'passed': passed, 'expected_status': case['expected_status'], 'actual_status': actual})
        result = _measured(
            'module_8', 'Integrated Analysis', case_results, started,
            {'success_rate': _ratio(sum(item['passed'] for item in case_results), len(case_results))},
            'Module 8 assessments are checked end to end against expected deterministic outcomes.',
        )
        return result

    def _run_planning_case(self, case: dict[str, Any], method: str) -> tuple[dict[str, Any], float]:
        started = perf_counter()
        if case['kind'] == 'compliance':
            knowledge_base, _ = self._knowledge.build(case['input'])
            compliance = self._compliance.analyze(knowledge_base, case['requirements'])
            result = self._planning.plan(compliance, method)
        else:
            result = SearchPlanner().solve(case['problem'], method)
        return result, _milliseconds(started)


def _extraction_fields(result: dict[str, Any]) -> dict[str, set[Any]]:
    metadata = result.get('metadata', {})
    return {
        'title': {metadata['title']} if metadata.get('title') else set(),
        'authors': set(metadata.get('authors', [])),
        'abstract': {metadata['abstract']} if metadata.get('abstract') else set(),
        'keywords': set(metadata.get('keywords', [])),
        'sections': {item.get('title') for item in result.get('sections', []) if item.get('title')},
        'references': {item.get('number') for item in result.get('references', []) if item.get('number') is not None},
        'figures': {item.get('number') for item in result.get('figures', []) if item.get('number') is not None},
        'tables': {item.get('number') for item in result.get('tables', []) if item.get('number') is not None},
    }


def _reasoning_status(result: dict[str, Any]) -> str:
    if result.get('established') is True:
        return 'ESTABLISHED'
    if result.get('status') == 'unknown':
        return 'UNSUPPORTED'
    return 'NOT_ESTABLISHED'


def _planning_method_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    plan_cases = [item for item in records if item['result']['status'] == 'PLAN_FOUND']
    no_solution_cases = [item for item in records if item['result']['status'] == 'NO_SOLUTION']
    return {
        'case_count': len(records), 'passed_cases': sum(item['passed'] for item in records),
        'plan_success_rate': _ratio(len(plan_cases), len(records)),
        'no_solution_detection_rate': _ratio(len(no_solution_cases), 1),
        'states_explored': sum(item['result']['states_explored'] for item in records),
        'search_depth': max((item['result']['search_depth'] for item in records), default=0),
        'total_path_cost': sum(item['result']['total_cost'] for item in records),
        'execution_time_ms': round(sum(item['elapsed_ms'] for item in records), 3),
    }


def _planning_comparison(records: list[dict[str, Any]], case_id: str) -> dict[str, Any]:
    record = next(item for item in records if item['case_id'] == case_id)
    result = record['result']
    return {
        'status': result['status'], 'states_explored': result['states_explored'],
        'execution_time_ms': record['elapsed_ms'], 'path_cost': result['total_cost'],
        'search_depth': result['search_depth'],
    }


def _not_evaluated(identifier: str, name: str, reason: str) -> dict[str, Any]:
    return {
        'id': identifier, 'module': name, 'status': 'NOT_EVALUATED', 'reason': reason,
        'case_count': 0, 'passed_cases': 0, 'failed_cases': 0, 'execution_time_ms': None,
        'metrics': {}, 'cases': [],
    }


def _measured(
    identifier: str, name: str, cases: list[dict[str, Any]], started: float,
    metrics: dict[str, Any], description: str,
) -> dict[str, Any]:
    passed = sum(item['passed'] for item in cases)
    return {
        'id': identifier, 'module': name, 'status': 'MEASURED', 'reason': description,
        'case_count': len(cases), 'passed_cases': passed, 'failed_cases': len(cases) - passed,
        'execution_time_ms': _milliseconds(started), 'metrics': metrics, 'cases': cases,
    }


def _milliseconds(started: float) -> float:
    return round((perf_counter() - started) * 1000, 3)


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _set_metrics(actual: set[Any], expected: set[Any]) -> dict[str, Any]:
    true_positive = len(actual & expected)
    false_positive = len(actual - expected)
    false_negative = len(expected - actual)
    return _metrics_from_counts(true_positive, false_positive, false_negative)


def _metrics_from_counts(true_positives: int, false_positives: int, false_negatives: int) -> dict[str, Any]:
    """Calculate precision/recall/F1 from counts without assuming matched sets."""
    precision = _ratio(true_positives, true_positives + false_positives)
    recall = _ratio(true_positives, true_positives + false_negatives)
    return {
        'precision': precision, 'recall': recall,
        'f1': round(2 * precision * recall / (precision + recall), 4) if precision is not None and recall is not None and precision + recall else 0.0,
        'true_positives': true_positives, 'false_positives': false_positives, 'false_negatives': false_negatives,
    }


def _combine_metrics(metrics: Any) -> dict[str, Any]:
    values = list(metrics)
    totals = {name: sum(item[name] for item in values) for name in ('true_positives', 'false_positives', 'false_negatives')}
    return _metrics_from_counts(**totals)


def _boolean_metrics(actual: list[bool], expected: list[bool]) -> dict[str, Any]:
    true_positive = sum(observed and truth for observed, truth in zip(actual, expected))
    false_positive = sum(observed and not truth for observed, truth in zip(actual, expected))
    false_negative = sum(not observed and truth for observed, truth in zip(actual, expected))
    correct = sum(observed is truth for observed, truth in zip(actual, expected))
    metrics = _metrics_from_counts(true_positive, false_positive, false_negative)
    return {'accuracy': _ratio(correct, len(expected)), **metrics, 'case_count': len(expected)}


def _classification_metrics(actual: list[str], expected: list[str]) -> dict[str, Any]:
    labels = sorted(set(actual) | set(expected))
    per_label = {}
    for label in labels:
        true_positive = sum(a == label and e == label for a, e in zip(actual, expected))
        false_positive = sum(a == label and e != label for a, e in zip(actual, expected))
        false_negative = sum(a != label and e == label for a, e in zip(actual, expected))
        per_label[label] = _metrics_from_counts(true_positive, false_positive, false_negative)
    correct = sum(a == e for a, e in zip(actual, expected))
    return {
        'accuracy': _ratio(correct, len(expected)),
        'macro_precision': round(sum(item['precision'] or 0 for item in per_label.values()) / len(per_label), 4) if per_label else None,
        'macro_recall': round(sum(item['recall'] or 0 for item in per_label.values()) / len(per_label), 4) if per_label else None,
        'macro_f1': round(sum(item['f1'] for item in per_label.values()) / len(per_label), 4) if per_label else None,
        'per_class': per_label,
    }
