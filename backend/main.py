import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.services.pdf_parser import EmptyPDFError, PDFParser, PDFParsingError, PasswordProtectedPDFError

load_dotenv(Path(__file__).with_name('.env'))

MONGO_URI = os.getenv('MONGO_URI', '').strip()
DATABASE_NAME = os.getenv('DATABASE_NAME', 'paperintel_ai').strip() or 'paperintel_ai'
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv('FRONTEND_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')
    if origin.strip()
]

app = FastAPI(title='PaperIntel AI API', version='0.1.0')
MAX_UPLOAD_SIZE = 20 * 1024 * 1024
ALLOWED_PDF_MIME_TYPES = {'application/pdf', 'application/x-pdf'}
pdf_parser = PDFParser()

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=['GET', 'POST'],
    allow_headers=['*'],
)


@lru_cache
def get_mongo_client() -> MongoClient:
    if not MONGO_URI:
        raise RuntimeError('MONGO_URI is not configured.')

    return MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )


@app.get('/')
def root() -> dict[str, str]:
    return {'message': 'PaperIntel AI Backend is running'}


@app.get('/health')
def health_check() -> dict[str, str]:
    return {'status': 'healthy', 'service': 'PaperIntel AI API'}


def _safe_display_filename(filename: str | None) -> str:
    """Keep a filename for display only; never use user input as a filesystem path."""
    if not filename:
        return 'uploaded-paper.pdf'
    return filename.replace('\\', '/').rsplit('/', maxsplit=1)[-1] or 'uploaded-paper.pdf'


def _validate_upload_metadata(file: UploadFile) -> str:
    filename = _safe_display_filename(file.filename)
    if not filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Only PDF files (.pdf) are accepted.',
        )

    mime_type = (file.content_type or '').split(';', maxsplit=1)[0].strip().lower()
    if mime_type not in ALLOWED_PDF_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='The uploaded file must have a PDF MIME type.',
        )
    return filename


@app.post('/api/papers/process')
async def process_paper(file: UploadFile | None = File(default=None)) -> dict:
    """Validate and process one PDF without persisting the uploaded document."""
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='A PDF file is required.',
        )

    try:
        filename = _validate_upload_metadata(file)
        content = await file.read(MAX_UPLOAD_SIZE + 1)
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail='The PDF must not exceed 20 MB.',
            )
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='The uploaded PDF is empty.',
            )
        if b'%PDF-' not in content[:1024]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='The uploaded file is not a valid PDF document.',
            )

        # The upload limit keeps this bounded to 20 MB. Parsing the validated bytes avoids
        # creating an application-owned PDF file or directory that would need later cleanup.
        extracted_document = pdf_parser.parse(content)
        extracted_document['document'].update({'filename': filename, 'file_size': len(content)})
        return {'success': True, **extracted_document}
    except HTTPException:
        raise
    except PasswordProtectedPDFError:
            raise HTTPException(
            status_code=422,
            detail='This PDF is password-protected and cannot be processed.',
        ) from None
    except EmptyPDFError:
            raise HTTPException(
            status_code=422,
            detail='This PDF contains no extractable text.',
        ) from None
    except PDFParsingError:
            raise HTTPException(
            status_code=422,
            detail='The PDF could not be parsed. It may be corrupted or unsupported.',
        ) from None
    finally:
        # Starlette may use a spooled temporary upload internally. Closing UploadFile releases
        # that resource on successful requests as well as all validation and parsing failures.
        await file.close()


@app.get('/health/database')
def database_health_check():
    """Verify the configured MongoDB server is reachable without exposing credentials."""
    if not MONGO_URI:
        return JSONResponse(
            status_code=503,
            content={'database': 'MongoDB', 'status': 'not configured'},
        )

    try:
        client = get_mongo_client()
        client[DATABASE_NAME].command('ping')
    except (PyMongoError, RuntimeError):
        return JSONResponse(
            status_code=503,
            content={'database': 'MongoDB', 'status': 'unavailable'},
        )

    return {'database': 'MongoDB', 'status': 'connected'}


@app.on_event('shutdown')
def close_mongo_connection() -> None:
    if get_mongo_client.cache_info().currsize:
        get_mongo_client().close()
        get_mongo_client.cache_clear()
