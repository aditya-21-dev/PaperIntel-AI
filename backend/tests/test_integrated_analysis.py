"""Module 8 integration tests using the real Modules 3--7 services."""

from copy import deepcopy
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.integration.agent import IntegratedAnalysisAgent
from app.services.knowledge_engine import KnowledgeEngine
from main import app, integration_agent


def structured_paper(*, pages: int = 7, abstract_words: int = 300) -> dict:
    return {
        'document': {'filename': 'integrated-paper.pdf', 'file_size': 4096, 'page_count': pages},
        'metadata': {
            'title': 'Integrated Analysis Paper', 'title_confidence': 'high',
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


def strict_requirements() -> dict:
    return {
        'profile_id': 'custom',
        'venue': 'Integrated Test Venue',
        'requirements': {
            'max_pages': 6,
            'max_abstract_words': 250,
            'keywords_required': True,
            'required_sections': ['Introduction', 'Methodology', 'Results', 'Conclusion'],
            'min_references': 15,
        },
    }


def test_complete_pipeline_reuses_real_module_services_and_preserves_traces() -> None:
    result = IntegratedAnalysisAgent().run(structured_paper(), strict_requirements())

    assert result['success'] is True
    assert result['analysis_status'] == 'COMPLETE'
    assert result['overall_assessment']['status'] == 'NEEDS_IMPROVEMENT'
    assert [item['status'] for item in result['module_statuses']] == ['COMPLETE'] * 5
    assert result['reasoning_analysis']['forward']['derived_facts']
    assert result['reasoning_analysis']['backward']['established'] is True
    assert result['logical_verification']['resolution']['status'] == 'ENTAILED'
    assert result['logical_verification']['consistency']['status'] == 'CONSISTENT'
    assert result['compliance_analysis']['status'] == 'NON_COMPLIANT'
    assert result['improvement_plan']['status'] == 'PLAN_FOUND'
    assert result['improvement_plan']['projected_state_notice'] == 'The projected state is hypothetical. The paper has not been modified.'
    assert result['report']['reasoning_trace']['search_trace']


def test_evidence_provenance_and_compliance_plan_correlation_are_preserved() -> None:
    result = IntegratedAnalysisAgent().run(structured_paper(), strict_requirements())

    page_evidence = next(item for item in result['evidence'] if item['source_module'] == 'Module 6' and item['source_constraint'] == 'C001')
    assert page_evidence['evidence']['actual'] == 7
    assert page_evidence['evidence']['required'] == '<= 6'
    assert any(
        item.get('recommended_actions')
        for item in result['cross_module_findings']
        if item['evidence'].get('source_constraint') == 'C001'
    )
    proof = next(item for item in result['evidence'] if item['source_module'] == 'Module 5')
    assert proof['verification'] == 'resolution'
    assert proof['status'] == 'ENTAILED'


def test_overall_ready_status_is_deterministic_for_a_compliant_paper() -> None:
    result = IntegratedAnalysisAgent().run(structured_paper(pages=5, abstract_words=100))

    assert result['compliance_analysis']['status'] == 'COMPLIANT'
    assert result['improvement_plan']['status'] == 'NO_IMPROVEMENT_NEEDED'
    assert result['overall_assessment']['status'] == 'READY'


def test_cross_module_inconsistency_is_explicitly_reported() -> None:
    knowledge_base, validation = KnowledgeEngine().build(structured_paper())
    assert validation['valid'] is True
    compliance = IntegratedAnalysisAgent()._compliance.analyze(knowledge_base, strict_requirements())
    contradictory = deepcopy(compliance)
    contradictory['variables']['AbstractPresent']['known'] = False
    contradictory['variables']['AbstractPresent']['value'] = None

    conflicts = IntegratedAnalysisAgent()._cross_module_inconsistencies(knowledge_base, contradictory)

    conflict = next(item for item in conflicts if item['affected_field'] == 'AbstractPresent')
    assert conflict['values'] == {'Module 3': True, 'Module 6': 'UNKNOWN'}
    assert conflict['source_modules'] == ['Module 3', 'Module 6']


def test_module_3_failure_returns_transparent_partial_analysis() -> None:
    agent = IntegratedAnalysisAgent()
    with patch.object(agent._knowledge, 'perceive', side_effect=ValueError('knowledge unavailable')):
        result = agent.run(structured_paper())

    assert result['success'] is False
    assert result['analysis_status'] == 'PARTIAL_ANALYSIS'
    assert result['failed_module'] == 'Module 3'
    assert result['completed_modules'] == []
    assert result['not_run_modules'] == ['Module 4', 'Module 5', 'Module 6', 'Module 7']


def test_module_4_failure_returns_module_3_partial_result() -> None:
    agent = IntegratedAnalysisAgent()
    with patch.object(agent._reasoning, 'forward_reason', side_effect=RuntimeError('reasoning unavailable')):
        result = agent.run(structured_paper())

    assert result['success'] is False
    assert result['failed_module'] == 'Module 4'
    assert result['completed_modules'] == ['Module 3']
    assert result['knowledge_analysis'] is not None


def test_module_5_failure_returns_transparent_partial_analysis() -> None:
    agent = IntegratedAnalysisAgent()
    with patch.object(agent._logic, 'model_check', side_effect=RuntimeError('logic unavailable')):
        result = agent.run(structured_paper())

    assert result['success'] is False
    assert result['failed_module'] == 'Module 5'
    assert result['completed_modules'] == ['Module 3', 'Module 4']
    assert result['reasoning_analysis']['forward']['success'] is True


def test_module_6_failure_returns_transparent_partial_analysis() -> None:
    agent = IntegratedAnalysisAgent()
    with patch.object(agent._compliance, 'analyze', side_effect=RuntimeError('compliance unavailable')):
        result = agent.run(structured_paper())

    assert result['success'] is False
    assert result['failed_module'] == 'Module 6'
    assert result['completed_modules'] == ['Module 3', 'Module 4', 'Module 5']


def test_module_7_failure_returns_transparent_partial_analysis() -> None:
    agent = IntegratedAnalysisAgent()
    with patch.object(agent._planning, 'plan', side_effect=RuntimeError('planning unavailable')):
        result = agent.run(structured_paper())

    assert result['success'] is False
    assert result['failed_module'] == 'Module 7'
    assert result['completed_modules'] == ['Module 3', 'Module 4', 'Module 5', 'Module 6']
    assert result['compliance_analysis']['status'] == 'COMPLIANT'


def test_integrated_analysis_api_runs_the_real_pipeline() -> None:
    client = TestClient(app)
    response = client.post('/api/analysis/run', json={
        'paper': structured_paper(),
        'requirements': strict_requirements(),
        'options': {'planning_method': 'ucs'},
    })

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] is True
    assert payload['improvement_plan']['algorithm'] == 'Uniform-Cost Search'
    assert payload['report']['publication_compliance']['violated']
