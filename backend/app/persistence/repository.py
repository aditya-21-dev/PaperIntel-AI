"""MongoDB repository for Module 11; AI modules remain database-independent."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError


MAX_PAGE_SIZE = 100
STORED_ANALYSIS_FIELDS = frozenset({
    'success', 'analysis_status', 'paper', 'module_statuses', 'knowledge_analysis',
    'reasoning_analysis', 'logical_verification', 'compliance_analysis',
    'improvement_plan', 'cross_module_findings', 'cross_module_inconsistencies',
    'overall_assessment', 'evidence', 'explanations', 'report', 'failed_module',
    'completed_modules', 'not_run_modules', 'error',
})


class PersistenceConfigurationError(RuntimeError):
    """Raised when persistence was requested without a configured MongoDB URI."""


class PersistenceUnavailableError(RuntimeError):
    """Raised when a configured MongoDB server cannot complete an operation."""


class PersistenceValidationError(ValueError):
    """Raised before invalid or unsafe application data reaches MongoDB."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _public_timestamp(value: object) -> str | None:
    if not isinstance(value, datetime):
        return None
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def _safe_filename(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersistenceValidationError('A document filename is required for persistence.')
    filename = value.replace('\\', '/').rsplit('/', maxsplit=1)[-1].strip()
    if not filename or len(filename) > 255:
        raise PersistenceValidationError('The document filename is invalid for persistence.')
    return filename


def _safe_value(value: object) -> Any:
    """Deep-copy JSON-like data while rejecting MongoDB operator and path keys."""
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, list):
        return [_safe_value(item) for item in value]
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or key.startswith('$') or '.' in key:
                raise PersistenceValidationError('Stored object keys cannot use MongoDB operator or path syntax.')
            safe[key] = _safe_value(item)
        return safe
    raise PersistenceValidationError('Persistence accepts only JSON-compatible data.')


def _require_identifier(value: object, name: str) -> str:
    if not isinstance(value, str) or not 8 <= len(value) <= 64 or not value.replace('-', '').replace('_', '').isalnum():
        raise PersistenceValidationError(f'{name} must be a clean application identifier.')
    return value


def paper_document(structured_document: object) -> dict[str, Any]:
    """Select safe Module 2 fields; never store the original PDF or temporary paths."""
    if not isinstance(structured_document, dict):
        raise PersistenceValidationError('A Module 2 structured-paper object is required.')
    document = structured_document.get('document')
    metadata = structured_document.get('metadata')
    if not isinstance(document, dict) or not isinstance(metadata, dict):
        raise PersistenceValidationError('Structured paper document and metadata are required.')
    file_size = document.get('file_size')
    page_count = document.get('page_count')
    if not isinstance(file_size, int) or isinstance(file_size, bool) or file_size < 0:
        raise PersistenceValidationError('Structured paper file_size must be a non-negative integer.')
    if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count < 1:
        raise PersistenceValidationError('Structured paper page_count must be a positive integer.')
    return {
        'paper_id': uuid4().hex,
        'filename': _safe_filename(document.get('filename')),
        'file_size': file_size,
        'page_count': page_count,
        'metadata': _safe_value(metadata),
        'created_at': _utc_now(),
    }


def analysis_document(paper_id: object, analysis: object) -> dict[str, Any]:
    """Store the existing Module 8 response shape, excluding runtime persistence metadata."""
    identifier = _require_identifier(paper_id, 'paper_id')
    if not isinstance(analysis, dict):
        raise PersistenceValidationError('A Module 8 analysis object is required.')
    if not isinstance(analysis.get('analysis_status'), str) or not isinstance(analysis.get('overall_assessment'), dict):
        raise PersistenceValidationError('The supplied result is not a valid Module 8 analysis.')
    stored = {name: _safe_value(analysis[name]) for name in STORED_ANALYSIS_FIELDS if name in analysis}
    return {
        'analysis_id': uuid4().hex,
        'paper_id': identifier,
        'created_at': _utc_now(),
        **stored,
    }


class MongoAnalysisRepository:
    """One repository bound to one existing PyMongo database and its collections."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._papers: Collection = database['papers']
        self._analyses: Collection = database['analyses']
        self._indexes_ready = False

    def ensure_indexes(self) -> None:
        if self._indexes_ready:
            return
        try:
            self._papers.create_index([('paper_id', ASCENDING)], unique=True, name='paper_id_unique')
            self._papers.create_index([('created_at', DESCENDING)], name='papers_created_at_desc')
            self._analyses.create_index([('analysis_id', ASCENDING)], unique=True, name='analysis_id_unique')
            self._analyses.create_index([('paper_id', ASCENDING), ('created_at', DESCENDING)], name='analyses_paper_created_at_desc')
        except PyMongoError as exc:
            raise PersistenceUnavailableError('MongoDB indexes could not be prepared.') from exc
        self._indexes_ready = True

    def save_paper(self, structured_document: object) -> dict[str, Any]:
        document = paper_document(structured_document)
        self.ensure_indexes()
        try:
            self._papers.insert_one(document)
        except PyMongoError as exc:
            raise PersistenceUnavailableError('Paper metadata could not be saved to MongoDB.') from exc
        return self._serialize_paper(document)

    def get_paper(self, paper_id: object) -> dict[str, Any] | None:
        identifier = _require_identifier(paper_id, 'paper_id')
        try:
            document = self._papers.find_one({'paper_id': identifier})
        except PyMongoError as exc:
            raise PersistenceUnavailableError('Paper metadata could not be read from MongoDB.') from exc
        return self._serialize_paper(document) if document else None

    def list_papers(self, limit: int = 50) -> list[dict[str, Any]]:
        limit = self._limit(limit)
        try:
            records = self._papers.find(
                {},
                {'_id': 0, 'paper_id': 1, 'filename': 1, 'file_size': 1, 'page_count': 1, 'metadata.title': 1, 'created_at': 1},
            ).sort('created_at', DESCENDING).limit(limit)
            return [self._serialize_paper(item) for item in records]
        except PyMongoError as exc:
            raise PersistenceUnavailableError('Paper history could not be read from MongoDB.') from exc

    def save_analysis(self, paper_id: object, analysis: object) -> dict[str, Any]:
        document = analysis_document(paper_id, analysis)
        self.ensure_indexes()
        try:
            if self._papers.count_documents({'paper_id': document['paper_id']}, limit=1) != 1:
                raise PersistenceValidationError('The specified paper_id does not exist.')
            self._analyses.insert_one(document)
        except PersistenceValidationError:
            raise
        except PyMongoError as exc:
            raise PersistenceUnavailableError('Analysis could not be saved to MongoDB.') from exc
        return self._serialize_analysis(document)

    def get_analysis(self, analysis_id: object) -> dict[str, Any] | None:
        identifier = _require_identifier(analysis_id, 'analysis_id')
        try:
            document = self._analyses.find_one({'analysis_id': identifier})
        except PyMongoError as exc:
            raise PersistenceUnavailableError('Analysis could not be read from MongoDB.') from exc
        return self._serialize_analysis(document) if document else None

    def list_paper_analyses(self, paper_id: object, limit: int = 50) -> list[dict[str, Any]]:
        identifier = _require_identifier(paper_id, 'paper_id')
        limit = self._limit(limit)
        try:
            records = self._analyses.find(
                {'paper_id': identifier},
                {'_id': 0, 'analysis_id': 1, 'paper_id': 1, 'created_at': 1, 'success': 1, 'analysis_status': 1, 'overall_assessment': 1},
            ).sort('created_at', DESCENDING).limit(limit)
            return [self._serialize_analysis(item) for item in records]
        except PyMongoError as exc:
            raise PersistenceUnavailableError('Analysis history could not be read from MongoDB.') from exc

    @staticmethod
    def _limit(value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= MAX_PAGE_SIZE:
            raise PersistenceValidationError(f'limit must be an integer between 1 and {MAX_PAGE_SIZE}.')
        return value

    @staticmethod
    def _serialize_paper(document: dict[str, Any]) -> dict[str, Any]:
        result = {key: deepcopy(value) for key, value in document.items() if key != '_id'}
        created_at = _public_timestamp(result.get('created_at'))
        if created_at:
            result['created_at'] = created_at
        return result

    @staticmethod
    def _serialize_analysis(document: dict[str, Any]) -> dict[str, Any]:
        result = {key: deepcopy(value) for key, value in document.items() if key != '_id'}
        created_at = _public_timestamp(result.get('created_at'))
        if created_at:
            result['created_at'] = created_at
        return result


def public_document(document: dict[str, Any]) -> dict[str, Any]:
    """Expose serialization for driver-level integration checks without leaking `_id`."""
    result = {key: deepcopy(value) for key, value in document.items() if key != '_id' and not isinstance(value, ObjectId)}
    created_at = _public_timestamp(result.get('created_at'))
    if created_at:
        result['created_at'] = created_at
    return result
