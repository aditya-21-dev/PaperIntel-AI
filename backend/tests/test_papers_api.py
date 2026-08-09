from unittest.mock import patch

import fitz
from fastapi.testclient import TestClient

from app.services.pdf_parser import PDFParsingError
from main import MAX_UPLOAD_SIZE, app, pdf_parser


def make_pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), 'A Test Paper Title', fontsize=18)
    page.insert_text((72, 108), 'Abstract', fontsize=12)
    page.insert_text((72, 130), 'A short abstract for endpoint testing.', fontsize=10)
    result = document.tobytes()
    document.close()
    return result


def test_process_pdf_returns_structured_json() -> None:
    client = TestClient(app)
    with patch.object(pdf_parser, 'parse', wraps=pdf_parser.parse) as parse:
        response = client.post(
            '/api/papers/process',
            files={'file': ('test-paper.pdf', make_pdf_bytes(), 'application/pdf')},
        )

    assert response.status_code == 200
    assert isinstance(parse.call_args.args[0], bytes)
    payload = response.json()
    assert payload['success'] is True
    assert payload['document']['filename'] == 'test-paper.pdf'
    assert payload['document']['page_count'] == 1
    assert payload['metadata']['abstract'].startswith('A short abstract')
    assert 'statistics' in payload


def test_invalid_file_is_rejected() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/papers/process',
        files={'file': ('notes.txt', b'not a PDF', 'text/plain')},
    )

    assert response.status_code == 400
    assert 'PDF' in response.json()['detail']


def test_corrupted_pdf_is_handled() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/papers/process',
        files={'file': ('broken.pdf', b'%PDF-not-a-real-document', 'application/pdf')},
    )

    assert response.status_code == 422


def test_parser_failure_stays_in_memory() -> None:
    client = TestClient(app)
    with patch.object(pdf_parser, 'parse', side_effect=PDFParsingError('simulated parse failure')) as parse:
        response = client.post(
            '/api/papers/process',
            files={'file': ('failure.pdf', make_pdf_bytes(), 'application/pdf')},
        )

    assert response.status_code == 422
    assert isinstance(parse.call_args.args[0], bytes)


def test_file_larger_than_limit_is_rejected() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/papers/process',
        files={'file': ('large.pdf', b'%PDF-' + b'x' * MAX_UPLOAD_SIZE, 'application/pdf')},
    )

    assert response.status_code == 413
