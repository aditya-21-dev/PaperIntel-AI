import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.logic.agent import LogicAgent, LogicInputError
from app.logic.models import FormulaValidationError
from app.reasoning.agent import ReasoningAgent
from app.services.knowledge_engine import KnowledgeAgent, KnowledgeBaseInputError
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
knowledge_agent = KnowledgeAgent()
reasoning_agent = ReasoningAgent()
logic_agent = LogicAgent()

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


@app.post('/api/papers/knowledge-base')
def generate_knowledge_base(structured_document: dict) -> dict:
    """Transform Module 2 output into a deterministic, in-memory paper knowledge base."""
    try:
        knowledge_base, validation = knowledge_agent.perceive(structured_document)
    except KnowledgeBaseInputError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None

    return {
        'success': validation['valid'],
        'knowledge_base': knowledge_base,
        'validation': validation,
    }


@app.post('/api/knowledge/query')
def query_knowledge_base(query: dict) -> dict:
    """Look up an exact propositional fact from the current or supplied knowledge base."""
    predicate = query.get('predicate')
    arguments = query.get('arguments')
    supplied_knowledge_base = query.get('knowledge_base')
    if not isinstance(predicate, str) or not isinstance(arguments, list) or not all(isinstance(arg, str) for arg in arguments):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='A predicate string and an arguments list of entity IDs are required.',
        )
    if supplied_knowledge_base is not None and not isinstance(supplied_knowledge_base, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='knowledge_base must be an object when supplied.')
    try:
        return knowledge_agent.query_fact(predicate, arguments, supplied_knowledge_base)
    except LookupError:
        raise HTTPException(status_code=404, detail='No knowledge base is available. Generate one first.') from None


@app.get('/api/reasoning/rules')
def list_reasoning_rules() -> dict:
    """Return the controlled Module 4 rule base for transparent UI display."""
    return {'rules': ReasoningAgent.rules()}


@app.post('/api/reasoning/forward')
def run_forward_reasoning(request: dict) -> dict:
    """Derive every conclusion supported by the supplied Module 3 knowledge base."""
    knowledge_base = request.get('knowledge_base')
    if not isinstance(knowledge_base, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='A Module 3 knowledge_base object is required.')
    try:
        return reasoning_agent.forward_reason(knowledge_base)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@app.post('/api/reasoning/backward')
def run_backward_reasoning(request: dict) -> dict:
    """Attempt to establish one goal from the supplied Module 3 knowledge base and rule base."""
    knowledge_base = request.get('knowledge_base')
    goal = request.get('goal')
    if not isinstance(knowledge_base, dict) or not isinstance(goal, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='A Module 3 knowledge_base and a goal object are required.')
    try:
        return reasoning_agent.backward_reason(goal, knowledge_base)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


def _logic_request(request: dict, require_query: bool = True) -> tuple[dict, object | None]:
    knowledge_base = request.get('knowledge_base') if isinstance(request, dict) else None
    query = request.get('query') if isinstance(request, dict) else None
    if not isinstance(knowledge_base, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='A Module 3 knowledge_base object is required.')
    if require_query and not isinstance(query, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='A structured logical query is required.')
    return knowledge_base, query


@app.post('/api/logic/model-check')
def run_model_check(request: dict) -> dict:
    """Semantically verify a query in every model satisfying Module 3/4 facts."""
    knowledge_base, query = _logic_request(request)
    include_models = request.get('include_models', False)
    if not isinstance(include_models, bool):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='include_models must be Boolean when supplied.')
    try:
        return logic_agent.model_check(knowledge_base, query, include_models)
    except (LogicInputError, FormulaValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@app.post('/api/logic/resolution')
def run_resolution(request: dict) -> dict:
    """Verify a query through bounded propositional resolution and return its proof trace."""
    knowledge_base, query = _logic_request(request)
    try:
        return logic_agent.resolution(knowledge_base, query)
    except (LogicInputError, FormulaValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@app.post('/api/logic/prove')
def prove_logical_query(request: dict) -> dict:
    """Expose the Module 5 propositional theorem-proving operation explicitly."""
    knowledge_base, query = _logic_request(request)
    try:
        return logic_agent.prove(knowledge_base, query)
    except (LogicInputError, FormulaValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@app.post('/api/logic/consistency')
def check_logical_consistency(request: dict) -> dict:
    """Use resolution to determine whether the Module 3/4 propositional KB is satisfiable."""
    knowledge_base, _ = _logic_request(request, require_query=False)
    try:
        return logic_agent.consistency(knowledge_base)
    except (LogicInputError, FormulaValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


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
