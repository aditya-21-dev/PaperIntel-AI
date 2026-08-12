"""Module 12 comparison tests using stored Module 8 analysis shapes."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.comparison.service import (
    AnalysisComparisonMismatchError,
    compare_stored_analyses,
)
from app.integration.agent import IntegratedAnalysisAgent
from main import app


def strict_requirements() -> dict:
    return {
        'profile_id': 'custom',
        'venue': 'Comparison Test Venue',
        'requirements': {
            'max_pages': 6,
            'max_abstract_words': 250,
            'keywords_required': True,
            'required_sections': ['Introduction', 'Methodology', 'Results', 'Conclusion'],
            'min_references': 15,
        },
    }


def structured_paper(*, pages: int = 7, abstract_words: int = 300) -> dict:
    return {
        'document': {'filename': 'comparison-paper.pdf', 'file_size': 4096, 'page_count': pages},
        'metadata': {
            'title': 'Comparison Paper', 'title_confidence': 'high',
            'authors': ['A. Researcher'], 'authors_confidence': 'high',
            'abstract': 'Structured abstract.', 'abstract_word_count': abstract_words,
            'keywords': ['reasoning', 'planning'],
        },
        'sections': [
            {'number': '1', 'title': 'Introduction', 'text': 'Context.', 'page_start': 1, 'page_end': 1},
            {'number': '2', 'title': 'Methodology', 'text': 'Method.', 'page_start': 2, 'page_end': 2},
            {'number': '3', 'title': 'Results', 'text': 'Results.', 'page_start': 3, 'page_end': 3},
            {'number': '4', 'title': 'Conclusion', 'text': 'Conclusion.', 'page_start': 4, 'page_end': 4},
        ],
        'references': [{'number': index, 'text': f'Reference {index}'} for index in range(1, 21)],
        'figures': [], 'tables': [], 'statistics': {}, 'warnings': [],
    }


def stored_analysis(*, paper_id: str, analysis_id: str, pages: int = 7, abstract_words: int = 300) -> dict:
    result = IntegratedAnalysisAgent().run(structured_paper(pages=pages, abstract_words=abstract_words), strict_requirements())
    return {
        'analysis_id': analysis_id,
        'paper_id': paper_id,
        'created_at': '2026-08-11T10:00:00Z',
        **result,
    }


def test_compare_two_valid_analyses_reports_material_changes() -> None:
    before = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisaaaaaaaaaaaaaaaaaaaaaaaa', pages=7, abstract_words=300)
    after = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisbbbbbbbbbbbbbbbbbbbbbbbbbbbb', pages=5, abstract_words=100)

    comparison = compare_stored_analyses(before, after)

    assert comparison['paper_id'] == 'paper12345678901234567890123456789012'
    assert comparison['overall_result'] == 'IMPROVED'
    assert comparison['compliance_changes']['constraints_resolved_count'] >= 1
    assert any(item['field'] == 'page_count' for item in comparison['changes'])
    assert comparison['improvement_summary']['compliance_status_before'] == 'NON_COMPLIANT'
    assert comparison['improvement_summary']['compliance_status_after'] == 'COMPLIANT'


def test_compare_analyses_from_different_papers_is_rejected() -> None:
    before = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisaaaaaaaaaaaaaaaaaaaaaaaa')
    after = stored_analysis(paper_id='paper98765432109876543210987654321098', analysis_id='analysisbbbbbbbbbbbbbbbbbbbbbbbbbbbb')

    with pytest.raises(AnalysisComparisonMismatchError):
        compare_stored_analyses(before, after)


def test_compare_missing_analysis_via_api_returns_not_found() -> None:
    with patch('main.get_persistence') as get_repository:
        repository = get_repository.return_value
        repository.get_analysis.side_effect = lambda analysis_id: {
            'analysisaaaaaaaaaaaaaaaaaaaaaaaa': stored_analysis(
                paper_id='paper12345678901234567890123456789012',
                analysis_id='analysisaaaaaaaaaaaaaaaaaaaaaaaa',
            ),
        }.get(analysis_id)
        response = TestClient(app).get('/api/analyses/compare/analysisaaaaaaaaaaaaaaaaaaaaaaaa/analysismissingmissingmissingmissingmi')

    assert response.status_code == 404
    assert 'not found' in response.json()['detail']


def test_compare_same_analysis_with_itself_is_unchanged() -> None:
    analysis = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisaaaaaaaaaaaaaaaaaaaaaaaa')

    comparison = compare_stored_analyses(analysis, analysis)

    assert comparison['overall_result'] == 'UNCHANGED'
    assert comparison['changes'] == []


def test_compare_improved_paper_classification() -> None:
    before = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisaaaaaaaaaaaaaaaaaaaaaaaa', pages=7)
    after = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisbbbbbbbbbbbbbbbbbbbbbbbbbbbb', pages=5, abstract_words=100)

    comparison = compare_stored_analyses(before, after)

    assert comparison['overall_result'] == 'IMPROVED'
    assert comparison['improvement_plan_changes']['after_status'] == 'NO_IMPROVEMENT_NEEDED'


def test_compare_regressed_paper_classification() -> None:
    before = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisaaaaaaaaaaaaaaaaaaaaaaaa', pages=5, abstract_words=100)
    after = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisbbbbbbbbbbbbbbbbbbbbbbbbbbbb', pages=7, abstract_words=300)

    comparison = compare_stored_analyses(before, after)

    assert comparison['overall_result'] == 'REGRESSED'
    assert comparison['compliance_changes']['newly_violated_count'] >= 1


def test_compare_mixed_changes_when_one_constraint_improves_and_another_regresses() -> None:
    before = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisaaaaaaaaaaaaaaaaaaaaaaaa', pages=7, abstract_words=100)
    after = deepcopy(stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisbbbbbbbbbbbbbbbbbbbbbbbbbbbb', pages=5, abstract_words=300))
    after['compliance_analysis']['constraints']['violated'] = deepcopy(before['compliance_analysis']['constraints']['violated'])
    after['compliance_analysis']['constraints']['satisfied'] = []
    after['compliance_analysis']['status'] = 'NON_COMPLIANT'
    after['overall_assessment']['status'] = 'NEEDS_IMPROVEMENT'

    comparison = compare_stored_analyses(before, after)

    assert comparison['overall_result'] == 'MIXED'


def test_compare_unchanged_analyses() -> None:
    before = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisaaaaaaaaaaaaaaaaaaaaaaaa', pages=5, abstract_words=100)
    after = deepcopy(before)
    after['analysis_id'] = 'analysisbbbbbbbbbbbbbbbbbbbbbbbbbbbb'

    comparison = compare_stored_analyses(before, after)

    assert comparison['overall_result'] == 'UNCHANGED'


def test_compare_insufficient_data_when_comparable_fields_are_missing() -> None:
    before = {'analysis_id': 'analysisaaaaaaaaaaaaaaaaaaaaaaaa', 'paper_id': 'paper12345678901234567890123456789012'}
    after = {'analysis_id': 'analysisbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'paper_id': 'paper12345678901234567890123456789012'}

    comparison = compare_stored_analyses(before, after)

    assert comparison['overall_result'] == 'INSUFFICIENT_DATA'
    assert comparison['compliance_changes']['insufficient_data'] is True


def test_compliance_comparison_reports_resolved_and_new_violations() -> None:
    before = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisaaaaaaaaaaaaaaaaaaaaaaaa', pages=7)
    after = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisbbbbbbbbbbbbbbbbbbbbbbbbbbbb', pages=5, abstract_words=100)

    comparison = compare_stored_analyses(before, after)

    assert comparison['compliance_changes']['constraints_resolved_count'] >= 2
    assert comparison['compliance_changes']['newly_violated_count'] == 0
    assert comparison['improvement_summary']['resolved_constraints'] >= 2


def test_improvement_plan_comparison_detects_no_longer_required_plan() -> None:
    before = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisaaaaaaaaaaaaaaaaaaaaaaaa', pages=7)
    after = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisbbbbbbbbbbbbbbbbbbbbbbbbbbbb', pages=5, abstract_words=100)

    comparison = compare_stored_analyses(before, after)

    assert before['improvement_plan']['status'] == 'PLAN_FOUND'
    assert after['improvement_plan']['status'] == 'NO_IMPROVEMENT_NEEDED'
    assert 'no longer detected' in comparison['improvement_plan_changes']['summary'].lower()


def test_api_comparison_endpoint_returns_structured_result() -> None:
    before = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisaaaaaaaaaaaaaaaaaaaaaaaa', pages=7)
    after = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisbbbbbbbbbbbbbbbbbbbbbbbbbbbb', pages=5, abstract_words=100)
    with patch('main.get_persistence') as get_repository:
        repository = get_repository.return_value
        repository.get_analysis.side_effect = lambda analysis_id: {
            before['analysis_id']: before,
            after['analysis_id']: after,
        }.get(analysis_id)
        response = TestClient(app).get(f"/api/analyses/compare/{before['analysis_id']}/{after['analysis_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] is True
    assert payload['comparison']['overall_result'] == 'IMPROVED'
    assert payload['comparison']['analysis_a'] == before['analysis_id']


def test_comparison_result_is_json_serializable() -> None:
    before = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisaaaaaaaaaaaaaaaaaaaaaaaa', pages=7)
    after = stored_analysis(paper_id='paper12345678901234567890123456789012', analysis_id='analysisbbbbbbbbbbbbbbbbbbbbbbbbbbbb', pages=5, abstract_words=100)

    comparison = compare_stored_analyses(before, after)
    with patch('main.get_persistence') as get_repository:
        repository = get_repository.return_value
        repository.get_analysis.side_effect = lambda analysis_id: {
            before['analysis_id']: before,
            after['analysis_id']: after,
        }.get(analysis_id)
        response = TestClient(app).get(f"/api/analyses/compare/{before['analysis_id']}/{after['analysis_id']}")

    assert response.status_code == 200
    assert response.json()['comparison']['overall_result'] == comparison['overall_result']
