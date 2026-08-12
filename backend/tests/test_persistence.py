"""Module 11 validation, serialization, and unavailable-database tests."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo.errors import ServerSelectionTimeoutError

from app.persistence.repository import (
    PersistenceUnavailableError,
    PersistenceValidationError,
    analysis_document,
    paper_document,
    public_document,
)
from main import app, get_persistence


def structured_paper() -> dict:
    return {
        'document': {'filename': 'saved-paper.pdf', 'file_size': 4096, 'page_count': 4},
        'metadata': {'title': 'Saved Paper', 'authors': ['A. Researcher'], 'abstract': 'A saved abstract.', 'keywords': ['ai']},
    }


def integrated_analysis() -> dict:
    return {
        'success': True, 'analysis_status': 'COMPLETE', 'paper': {'id': 'paper_001'},
        'module_statuses': [], 'overall_assessment': {'status': 'READY'},
        'knowledge_analysis': {}, 'reasoning_analysis': {}, 'logical_verification': {},
        'compliance_analysis': {}, 'improvement_plan': {}, 'evidence': [], 'report': {},
    }


def structured_paper_for_analysis() -> dict:
    return {
        'document': {'filename': 'integrated-history.pdf', 'file_size': 4096, 'page_count': 5},
        'metadata': {
            'title': 'Integrated History Paper', 'title_confidence': 'high',
            'authors': ['A. Researcher'], 'authors_confidence': 'high',
            'abstract': 'A structured abstract.', 'abstract_word_count': 120,
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


def test_persistence_documents_are_safe_serializable_and_exclude_pdf_binary() -> None:
    paper = paper_document(structured_paper())
    analysis = analysis_document(paper['paper_id'], integrated_analysis())
    serialized = public_document({'_id': ObjectId(), **paper})

    assert len(paper['paper_id']) == 32
    assert paper['filename'] == 'saved-paper.pdf'
    assert 'pdf_bytes' not in paper
    assert analysis['paper_id'] == paper['paper_id']
    assert analysis['analysis_status'] == 'COMPLETE'
    assert '_id' not in serialized
    assert isinstance(serialized['created_at'], str)


def test_persistence_rejects_unsafe_or_incomplete_documents() -> None:
    invalid = structured_paper()
    invalid['document']['filename'] = 'C:/temporary/../paper.pdf'
    invalid['metadata'] = {'$where': 'unsafe'}

    with pytest.raises(PersistenceValidationError):
        paper_document(invalid)
    with pytest.raises(PersistenceValidationError):
        analysis_document('not valid!', integrated_analysis())
    with pytest.raises(PersistenceValidationError):
        analysis_document('a' * 32, {'analysis_status': 'COMPLETE'})


def test_missing_or_unavailable_mongodb_is_never_reported_as_connected() -> None:
    get_persistence.cache_clear()
    with patch('main.MONGO_URI', ''):
        response = TestClient(app).get('/api/papers')
    assert response.status_code == 503
    assert 'not configured' in response.json()['detail']

    get_persistence.cache_clear()
    with patch('main.MONGO_URI', 'mongodb://unavailable.invalid:27017'), patch(
        'main.get_mongo_client', side_effect=ServerSelectionTimeoutError('unavailable'),
    ):
        with pytest.raises(PersistenceUnavailableError):
            get_persistence()
    get_persistence.cache_clear()


def test_integrated_analysis_returns_the_real_result_with_explicit_unsaved_status() -> None:
    get_persistence.cache_clear()
    with patch('main.MONGO_URI', ''):
        response = TestClient(app).post('/api/analysis/run', json={'paper': structured_paper_for_analysis()})
    get_persistence.cache_clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] is True
    assert payload['persistence']['status'] == 'NOT_CONFIGURED'
    assert 'not saved' in payload['persistence']['message']
