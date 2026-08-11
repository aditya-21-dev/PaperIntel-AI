"""Small, safe structured logging helpers for PaperIntel's HTTP application."""

from __future__ import annotations

import json
import logging
from typing import Any


LOGGER_NAME = 'paperintel'
_LEVELS = {'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'}


def configure_logging(level_name: str) -> logging.Logger:
    """Configure one JSON-line logger without changing the process root logger."""
    level = level_name.upper()
    if level not in _LEVELS:
        raise ValueError(f'LOG_LEVEL must be one of {sorted(_LEVELS)}.')
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, level))
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)
    return logger


def log_event(logger: logging.Logger, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    """Emit metadata only; callers must not pass request bodies, secrets, or paper text."""
    payload = {'event': event, **{key: value for key, value in fields.items() if value is not None}}
    logger.log(level, json.dumps(payload, sort_keys=True, default=str, separators=(',', ':')))
