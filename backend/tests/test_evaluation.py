"""Module 9 tests for deterministic benchmark evaluation and reporting."""

import pytest
from fastapi.testclient import TestClient

from app.evaluation.agent import SystemEvaluationAgent, _set_metrics
from app.evaluation.benchmarks import (
    compliance_cases,
    integration_cases,
    knowledge_cases,
    logic_cases,
    pdf_extraction_cases,
    planning_cases,
    reasoning_cases,
)
from main import app


@pytest.fixture(scope='module')
def report() -> dict:
    return SystemEvaluationAgent().run()


def test_benchmark_datasets_are_small_and_include_declared_expected_results() -> None:
    assert len(pdf_extraction_cases()) == 1
    assert pdf_extraction_cases()[0]['ground_truth']['sections'] == {'Introduction', 'Methodology'}
    assert all(case['expected_facts'] for case in knowledge_cases())
    assert all(case['expected_status'] for cases in (reasoning_cases(), logic_cases(), compliance_cases(), planning_cases(), integration_cases()) for case in cases)


def test_metric_calculation_uses_actual_mismatch_counts() -> None:
    metrics = _set_metrics({'correct', 'unexpected'}, {'correct', 'missing'})

    assert metrics == {
        'precision': 0.5, 'recall': 0.5, 'f1': 0.5,
        'true_positives': 1, 'false_positives': 1, 'false_negatives': 1,
    }


def test_missing_ground_truth_is_not_evaluated() -> None:
    result = SystemEvaluationAgent().evaluate_pdf_extraction(({'id': 'unannotated'},))

    assert result['status'] == 'NOT_EVALUATED'
    assert result['reason'] == 'Ground-truth extraction annotations are unavailable.'


def test_module_level_evaluation_returns_measured_actual_results(report: dict) -> None:
    modules = {module['id']: module for module in report['modules']}

    assert report['title'] == 'SYSTEM EVALUATION'
    assert all(module['status'] == 'MEASURED' for module in modules.values())
    assert modules['module_2']['metrics']['field_metrics']['title']['f1'] == 1.0
    assert modules['module_4']['metrics']['accuracy'] == 1.0
    assert modules['module_5']['metrics']['per_class']['INCONSISTENT']['recall'] == 1.0
    assert modules['module_6']['metrics']['constraint_classification']['accuracy'] == 1.0
    assert modules['module_6']['metrics']['solver_statistics']['constraint_checks'] > 0


def test_search_and_end_to_end_evaluation_include_comparisons(report: dict) -> None:
    modules = {module['id']: module for module in report['modules']}
    planning = modules['module_7']['metrics']

    assert planning['by_method']['ucs']['no_solution_detection_rate'] == 1.0
    assert planning['by_method']['astar']['states_explored'] > 0
    assert all(item['ucs']['path_cost'] == item['astar']['path_cost'] for item in planning['comparisons'])
    assert modules['module_8']['metrics']['success_rate'] == 1.0
    assert report['summary']['end_to_end_success_rate'] == 1.0


def test_evaluation_api_returns_structured_report_and_measured_response_time() -> None:
    response = TestClient(app).post('/api/evaluation/run')

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] is True
    assert payload['summary']['case_count'] > 0
    assert payload['api_response_time_ms'] > 0
    assert any(item['module'] == 'Integrated Analysis' for item in payload['modules'])
