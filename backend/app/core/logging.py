"""Application logging setup (foundation requirement §13).

Consistent, structured-enough console logging for startup, database
connectivity and API errors. Never log secrets, credentials or tokens:
callers pass labels (e.g. db engine kind), not URLs with passwords.
"""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False

FORMAT = "%(asctime)s %(levelname)-7s %(name)s :: %(message)s"
DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root + app loggers once (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(FORMAT, datefmt=DATEFMT))
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _CONFIGURED = True


def log_db_event(logger: logging.Logger, event: str, *, engine_label: str) -> None:
    """Log a database lifecycle event without credentials."""
    logger.info("database %s (engine=%s)", event, engine_label)
