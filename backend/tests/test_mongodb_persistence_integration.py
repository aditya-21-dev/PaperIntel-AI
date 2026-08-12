"""Opt-in Module 11 tests that use a real, isolated MongoDB test database."""

import os
from uuid import uuid4

import pytest
from pymongo import MongoClient

from app.persistence.repository import MongoAnalysisRepository


pytestmark = pytest.mark.mongodb


@pytest.fixture(scope='module')
def repository() -> MongoAnalysisRepository:
    uri = os.getenv('MONGO_TEST_URI', '').strip()
    database_prefix = os.getenv('MONGO_TEST_DATABASE', '').strip()
    if not uri or not database_prefix:
        pytest.skip('Set MONGO_TEST_URI and MONGO_TEST_DATABASE to run real MongoDB integration tests.')
    client = MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
    client.admin.command('ping')
    database_name = f'{database_prefix}_paperintel_{uuid4().hex}'
    try:
        repository = MongoAnalysisRepository(client[database_name])
        repository.ensure_indexes()
        yield repository
    finally:
        client.drop_database(database_name)
        client.close()


def structured_paper() -> dict:
    return {
        'document': {'filename': 'integration-paper.pdf', 'file_size': 5120, 'page_count': 5},
        'metadata': {'title': 'MongoDB Integration Paper', 'authors': ['A. Researcher'], 'abstract': 'Abstract.', 'keywords': ['persistence']},
    }


def analysis() -> dict:
    return {
        'success': True, 'analysis_status': 'COMPLETE', 'paper': {'id': 'paper_001'},
        'module_statuses': [], 'overall_assessment': {'status': 'READY'},
        'knowledge_analysis': {}, 'reasoning_analysis': {}, 'logical_verification': {},
        'compliance_analysis': {}, 'improvement_plan': {}, 'evidence': [], 'report': {},
    }


def test_real_mongodb_paper_analysis_and_history_round_trip(repository: MongoAnalysisRepository) -> None:
    paper = repository.save_paper(structured_paper())
    stored_paper = repository.get_paper(paper['paper_id'])
    stored_analysis = repository.save_analysis(paper['paper_id'], analysis())
    loaded_analysis = repository.get_analysis(stored_analysis['analysis_id'])
    history = repository.list_paper_analyses(paper['paper_id'])

    assert stored_paper is not None and stored_paper['paper_id'] == paper['paper_id']
    assert stored_analysis['paper_id'] == paper['paper_id']
    assert loaded_analysis is not None and loaded_analysis['analysis_id'] == stored_analysis['analysis_id']
    assert history[0]['analysis_id'] == stored_analysis['analysis_id']
    assert '_id' not in loaded_analysis and '_id' not in stored_paper
