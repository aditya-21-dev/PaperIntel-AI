from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.services.knowledge_engine import KnowledgeAgent, KnowledgeEngine, validate_knowledge_base
from main import app, knowledge_agent


@pytest.fixture
def module_2_document() -> dict:
    """Representative Module 2 output; this test module never parses a PDF."""
    return {
        'success': True,
        'document': {'filename': 'knowledge-paper.pdf', 'file_size': 2048, 'page_count': 3},
        'metadata': {
            'title': 'Knowledge Engineering for Research Papers',
            'title_confidence': 'high',
            'authors': ['Alice Smith', 'Bob Jones'],
            'authors_confidence': 'medium',
            'abstract': 'This paper describes deterministic knowledge representation.',
            'abstract_word_count': 7,
            'keywords': ['knowledge base', 'propositional logic'],
        },
        'sections': [
            {'number': '1', 'title': 'Introduction', 'text': 'Prior work is discussed in [1].', 'page_start': 1, 'page_end': 1},
            {'number': '2', 'title': 'Methodology', 'text': 'The method is deterministic [1, 2].', 'page_start': 1, 'page_end': 2},
            {'number': '3', 'title': 'Results', 'text': 'Figure 1 and Table 1 show the findings.', 'page_start': 2, 'page_end': 2},
            {'number': '4', 'title': 'Conclusion', 'text': 'The approach is explainable.', 'page_start': 3, 'page_end': 3},
        ],
        'references': [
            {'number': 1, 'text': 'A. Author. Knowledge systems. 2024.'},
            {'number': 2, 'text': 'B. Author. Deterministic agents. 2023.'},
        ],
        'figures': [{'number': 1, 'caption': 'Knowledge flow', 'page': 2, 'detected_from': 'caption'}],
        'tables': [{'number': 1, 'caption': 'Knowledge facts', 'page': 2, 'detected_from': 'caption'}],
        'statistics': {},
        'warnings': [],
    }


@pytest.fixture(autouse=True)
def clear_global_knowledge_agent():
    knowledge_agent.clear()
    yield
    knowledge_agent.clear()


def test_creates_unique_entities_and_preserves_evidence(module_2_document: dict) -> None:
    knowledge_base, validation = KnowledgeEngine().build(module_2_document)

    all_entities = [knowledge_base['paper']]
    for group in knowledge_base['entities'].values():
        all_entities.extend(group)

    assert validation == {'valid': True, 'errors': []}
    assert len({entity['id'] for entity in all_entities}) == len(all_entities)
    assert [author['name'] for author in knowledge_base['entities']['authors']] == ['Alice Smith', 'Bob Jones']
    assert knowledge_base['entities']['citations']
    assert all(item['evidence']['source_module'] == 'pdf_parser' for item in all_entities)


def test_creates_section_reference_figure_and_table_relationships(module_2_document: dict) -> None:
    knowledge_base, _ = KnowledgeEngine().build(module_2_document)
    predicates = {relationship['predicate'] for relationship in knowledge_base['relationships']}

    assert {'has_section', 'has_reference', 'has_figure', 'has_table', 'contains_citation', 'appears_in', 'precedes', 'follows'} <= predicates
    assert any(relationship['logical_form'].startswith('HasSection(') for relationship in knowledge_base['relationships'])
    assert any(relationship['predicate'] == 'contains_figure' for relationship in knowledge_base['relationships'])
    assert any(relationship['predicate'] == 'contains_table' for relationship in knowledge_base['relationships'])


def test_creates_controlled_propositional_facts(module_2_document: dict) -> None:
    knowledge_base, _ = KnowledgeEngine().build(module_2_document)
    facts = {fact['predicate']: fact for fact in knowledge_base['propositional_facts']}

    assert facts['PaperHasAbstract']['value'] is True
    assert facts['PaperHasMethodology']['value'] is True
    assert facts['PaperHasReferences']['value'] is True
    assert facts['PaperHasFigures']['value'] is True
    assert facts['PaperHasTables']['value'] is True
    assert facts['PaperHasAbstract']['evidence']['source_field'] == 'metadata.abstract'


def test_agent_queries_exact_facts(module_2_document: dict) -> None:
    agent = KnowledgeAgent()
    knowledge_base, validation = agent.perceive(module_2_document)

    assert validation['valid'] is True
    assert agent.query_fact('PaperHasAbstract', [knowledge_base['paper']['id']])['found'] is True
    assert agent.query_fact('PaperHasConclusion', [knowledge_base['paper']['id']])['fact']['value'] is True
    assert agent.query_fact('PaperHasAbstract', ['paper_missing']) == {'found': False, 'fact': None}


def test_validation_detects_invalid_and_missing_relationship_entities(module_2_document: dict) -> None:
    knowledge_base, _ = KnowledgeEngine().build(module_2_document)
    invalid = deepcopy(knowledge_base)
    invalid['relationships'].append({
        'subject': 'section_missing',
        'predicate': 'unknown_predicate',
        'object': 'reference_missing',
        'evidence': {},
    })

    validation = validate_knowledge_base(invalid)

    assert validation['valid'] is False
    assert {error['code'] for error in validation['errors']} >= {'undefined_relationship_predicate', 'missing_relationship_entity'}


def test_knowledge_base_and_query_api(module_2_document: dict) -> None:
    client = TestClient(app)
    create_response = client.post('/api/papers/knowledge-base', json=module_2_document)

    assert create_response.status_code == 200
    payload = create_response.json()
    assert payload['success'] is True
    paper_id = payload['knowledge_base']['paper']['id']

    query_response = client.post('/api/knowledge/query', json={
        'predicate': 'PaperHasAbstract',
        'arguments': [paper_id],
    })
    assert query_response.status_code == 200
    assert query_response.json()['fact']['value'] is True
