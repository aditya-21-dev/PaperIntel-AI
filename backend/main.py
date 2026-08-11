import os
import logging
import uuid
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.compliance.agent import ComplianceAgent, ComplianceInputError
from app.compliance.models import CSPValidationError
from app.compliance.profiles import available_profiles
from app.evaluation.agent import SystemEvaluationAgent
from app.integration.agent import IntegratedAnalysisAgent, IntegrationInputError
from app.logic.agent import LogicAgent, LogicInputError
from app.logic.models import FormulaValidationError
from app.observability import configure_logging, log_event
from app.planning.agent import ImprovementPlanningAgent, PlanningInputError
from app.reasoning.agent import ReasoningAgent
from app.services.knowledge_engine import KnowledgeAgent, KnowledgeBaseInputError, KnowledgeEngine
from app.services.pdf_parser import EmptyPDFError, PDFParser, PDFParsingError, PasswordProtectedPDFError

load_dotenv(Path(__file__).with_name('.env'))


def _environment_value(name: str, default: str, allowed: set[str]) -> str:
    value = os.getenv(name, default).strip().casefold() or default
    if value not in allowed:
        raise RuntimeError(f'{name} must be one of {sorted(allowed)}.')
    return value


def _positive_integer_environment(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f'{name} must be an integer between {minimum} and {maximum}.') from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f'{name} must be an integer between {minimum} and {maximum}.')
    return value


def _boolean_environment(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(default)).strip().casefold()
    if raw in {'1', 'true', 'yes', 'on'}:
        return True
    if raw in {'0', 'false', 'no', 'off'}:
        return False
    raise RuntimeError(f'{name} must be a Boolean value.')


APP_ENV = _environment_value('APP_ENV', 'development', {'development', 'testing', 'production'})
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').strip().upper() or 'INFO'
API_DOCS_ENABLED = _boolean_environment('ENABLE_API_DOCS', APP_ENV != 'production')
MAX_UPLOAD_SIZE_MB = _positive_integer_environment('MAX_UPLOAD_SIZE_MB', 20, 1, 100)
logger = configure_logging(LOG_LEVEL)
MONGO_URI = os.getenv('MONGO_URI', '').strip()
DATABASE_NAME = os.getenv('DATABASE_NAME', 'paperintel_ai').strip() or 'paperintel_ai'
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv('FRONTEND_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')
    if origin.strip()
]
if not FRONTEND_ORIGINS or '*' in FRONTEND_ORIGINS:
    raise RuntimeError('FRONTEND_ORIGINS must contain one or more explicit origins; wildcard origins are not permitted.')


@asynccontextmanager
async def application_lifespan(_: FastAPI):
    """Release the optional MongoDB client cleanly when the API stops."""
    yield
    if get_mongo_client.cache_info().currsize:
        get_mongo_client().close()
        get_mongo_client.cache_clear()


app = FastAPI(
    title='PaperIntel AI API',
    version='0.1.0',
    docs_url='/docs' if API_DOCS_ENABLED else None,
    redoc_url='/redoc' if API_DOCS_ENABLED else None,
    lifespan=application_lifespan,
)
MAX_UPLOAD_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_PDF_MIME_TYPES = {'application/pdf', 'application/x-pdf'}
pdf_parser = PDFParser()
knowledge_agent = KnowledgeAgent()
reasoning_agent = ReasoningAgent()
logic_agent = LogicAgent()
compliance_agent = ComplianceAgent()
planning_agent = ImprovementPlanningAgent()
evaluation_agent = SystemEvaluationAgent()
integration_agent = IntegratedAnalysisAgent(
    knowledge_agent,
    reasoning_agent,
    logic_agent,
    compliance_agent,
    planning_agent,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=['GET', 'POST'],
    allow_headers=['*'],
    expose_headers=['X-Request-ID'],
)


@app.middleware('http')
async def log_api_request(request: Request, call_next):
    """Attach a correlation ID and record safe request metadata without logging bodies."""
    request_id = uuid.uuid4().hex[:16]
    request.state.request_id = request_id
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        log_event(
            logger, 'api_request_failed', level=logging.ERROR,
            request_id=request_id, method=request.method, path=request.url.path,
            error_type=type(exc).__name__, duration_ms=round((perf_counter() - started) * 1000, 3),
        )
        raise
    response.headers['X-Request-ID'] = request_id
    log_event(
        logger, 'api_request_completed',
        level=logging.WARNING if response.status_code >= 500 else logging.INFO,
        request_id=request_id, method=request.method, path=request.url.path,
        status_code=response.status_code, duration_ms=round((perf_counter() - started) * 1000, 3),
    )
    return response


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Avoid reflecting request payloads or framework internals in validation responses."""
    log_event(
        logger, 'api_request_validation_failed', level=logging.WARNING,
        request_id=getattr(request.state, 'request_id', None), path=request.url.path,
        validation_error_count=len(exc.errors()),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={'detail': 'Invalid request data.', 'error_code': 'VALIDATION_ERROR'},
    )


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Keep expected client failures structured while preserving safe endpoint messages."""
    log_event(
        logger, 'api_request_rejected', level=logging.WARNING if exc.status_code >= 400 else logging.INFO,
        request_id=getattr(request.state, 'request_id', None), path=request.url.path,
        status_code=exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={'detail': exc.detail, 'error_code': 'REQUEST_ERROR'},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    """Return no stack traces, credentials, or filesystem details to API clients."""
    log_event(
        logger, 'api_unexpected_error', level=logging.ERROR,
        request_id=getattr(request.state, 'request_id', None), path=request.url.path,
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={'detail': 'An unexpected server error occurred.', 'error_code': 'INTERNAL_ERROR'},
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
        log_event(logger, 'pdf_processing_failed', level=logging.WARNING, reason='password_protected')
        raise HTTPException(
            status_code=422,
            detail='This PDF is password-protected and cannot be processed.',
        ) from None
    except EmptyPDFError:
        log_event(logger, 'pdf_processing_failed', level=logging.WARNING, reason='empty_pdf')
        raise HTTPException(
            status_code=422,
            detail='This PDF contains no extractable text.',
        ) from None
    except PDFParsingError:
        log_event(logger, 'pdf_processing_failed', level=logging.WARNING, reason='parse_error')
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


def _compliance_inputs(request: dict) -> tuple[dict, object | None]:
    if not isinstance(request, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Compliance input must be an object.')
    knowledge_base = request.get('knowledge_base')
    if not isinstance(knowledge_base, dict):
        structured_document = request.get('structured_document')
        if not isinstance(structured_document, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='A Module 3 knowledge_base or Module 2 structured_document object is required.',
            )
        try:
            knowledge_base, validation = KnowledgeEngine().build(structured_document)
        except KnowledgeBaseInputError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
        if not validation['valid']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='The supplied structured document could not form a valid knowledge base.')

    profile = request.get('profile')
    if profile is None and 'requirements' in request:
        raw_requirements = request.get('requirements')
        if isinstance(raw_requirements, dict) and 'requirements' in raw_requirements:
            profile = raw_requirements
        else:
            profile = {
                'profile_id': request.get('profile_id', 'custom'),
                'name': request.get('profile_name'),
                'venue': request.get('venue'),
                'requirements': raw_requirements,
            }
    return knowledge_base, profile


@app.get('/api/compliance/profiles')
def list_compliance_profiles() -> dict:
    """List the small controlled baseline profile; custom profiles are supplied per request."""
    return {'profiles': available_profiles()}


@app.post('/api/compliance/csp')
def run_compliance_csp(request: dict) -> dict:
    """Build a paper-compliance CSP, propagate it, and search for valid configurations."""
    knowledge_base, profile = _compliance_inputs(request)
    try:
        return compliance_agent.analyze(knowledge_base, profile)
    except (ComplianceInputError, CSPValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@app.post('/api/compliance/validate')
def validate_compliance_constraints(request: dict) -> dict:
    """Evaluate observed paper values against declarative requirements without search."""
    knowledge_base, profile = _compliance_inputs(request)
    try:
        return compliance_agent.validate(knowledge_base, profile)
    except (ComplianceInputError, CSPValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


def _planning_limits(request: dict) -> tuple[int, int, float]:
    max_states = request.get('max_states', 250)
    max_depth = request.get('max_depth', 12)
    max_seconds = request.get('max_seconds', 2.0)
    if not isinstance(max_states, int) or isinstance(max_states, bool) or not 1 <= max_states <= 1000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='max_states must be an integer between 1 and 1000.')
    if not isinstance(max_depth, int) or isinstance(max_depth, bool) or not 0 <= max_depth <= 30:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='max_depth must be an integer between 0 and 30.')
    if not isinstance(max_seconds, (int, float)) or isinstance(max_seconds, bool) or not 0 < max_seconds <= 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='max_seconds must be a number greater than 0 and no more than 10.')
    return max_states, max_depth, float(max_seconds)


@app.post('/api/planning/search')
def search_improvement_plan(request: dict) -> dict:
    """Search hypothetical improvement states from a Module 6 result or existing paper input."""
    if not isinstance(request, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Planning input must be an object.')
    method = request.get('method', 'astar')
    if not isinstance(method, str) or method.casefold() not in {'ucs', 'astar'}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="method must be 'ucs' or 'astar'.")
    max_states, max_depth, max_seconds = _planning_limits(request)
    compliance_result = request.get('compliance_result')
    if compliance_result is None:
        knowledge_base, profile = _compliance_inputs(request)
        try:
            compliance_result = compliance_agent.analyze(knowledge_base, profile)
        except (ComplianceInputError, CSPValidationError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    try:
        return planning_agent.plan(
            compliance_result,
            method,
            max_states=max_states,
            max_depth=max_depth,
            max_seconds=max_seconds,
            action_costs=request.get('action_costs'),
        )
    except (PlanningInputError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@app.post('/api/analysis/run')
def run_integrated_analysis(request: dict) -> dict:
    """Run Modules 3--7 once and return Module 8's explainable unified report."""
    if not isinstance(request, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Integrated analysis input must be an object.')
    paper = request.get('paper')
    if not isinstance(paper, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='paper must be a Module 2 structured-paper object.',
        )
    try:
        return integration_agent.run(
            paper,
            request.get('requirements'),
            request.get('options'),
        )
    except (IntegrationInputError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@app.post('/api/evaluation/run')
def run_system_evaluation() -> dict:
    """Execute Module 9's maintained deterministic benchmarks in memory."""
    started = perf_counter()
    result = evaluation_agent.run()
    result['api_response_time_ms'] = round((perf_counter() - started) * 1000, 3)
    return result


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
