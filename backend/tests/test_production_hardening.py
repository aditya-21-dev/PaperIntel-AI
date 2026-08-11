"""Module 10 API safety and configuration-regression tests."""

from unittest.mock import patch

import fitz
from fastapi.testclient import TestClient

from main import app, pdf_parser


def blank_pdf_bytes() -> bytes:
    document = fitz.open()
    try:
        document.new_page()
        return document.tobytes()
    finally:
        document.close()


def test_health_response_has_no_runtime_configuration_and_sets_request_id() -> None:
    response = TestClient(app).get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'healthy', 'service': 'PaperIntel AI API'}
    assert len(response.headers['x-request-id']) == 16
    assert 'MONGO_URI' not in response.text


def test_validation_and_upload_errors_are_structured_and_safe() -> None:
    client = TestClient(app)
    malformed = client.post('/api/analysis/run', json=['not-an-object'])
    empty = client.post('/api/papers/process', files={
        'file': ('blank.pdf', blank_pdf_bytes(), 'application/pdf'),
    })

    assert malformed.status_code == 422
    assert malformed.json() == {'detail': 'Invalid request data.', 'error_code': 'VALIDATION_ERROR'}
    assert empty.status_code == 422
    assert empty.json()['error_code'] == 'REQUEST_ERROR'
    assert 'extractable text' in empty.json()['detail']


def test_unexpected_processing_failure_does_not_expose_exception_details() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    with patch.object(pdf_parser, 'parse', side_effect=RuntimeError('C:\\private\\paper.pdf')):
        response = client.post('/api/papers/process', files={
            'file': ('safe-name.pdf', b'%PDF-safe', 'application/pdf'),
        })

    assert response.status_code == 500
    assert response.json() == {
        'detail': 'An unexpected server error occurred.',
        'error_code': 'INTERNAL_ERROR',
    }
    assert 'private' not in response.text


def test_database_health_remains_safe_when_mongodb_is_not_configured() -> None:
    with patch('main.MONGO_URI', ''):
        response = TestClient(app).get('/health/database')

    assert response.status_code == 503
    assert response.json() == {'database': 'MongoDB', 'status': 'not configured'}
