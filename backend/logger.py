"""
Structured logging for Football Predictor API.

- JSON formatter in production (LOG_FORMAT=json)
- Human-readable coloured formatter in development
- Rotating file handler: ./logs/app.log (10 MB, 5 backups)
- Request-scoped request_id via contextvars
"""

import logging
import logging.handlers
import os
import sys
import json
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

from config import LOG_FORMAT, LOG_LEVEL, LOG_FILE

# ── Request-ID context ────────────────────────────────────────────────────────
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def set_request_id(req_id: str | None = None) -> str:
    rid = req_id or str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    return _request_id_var.get()


# ── JSON formatter ────────────────────────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


# ── Human-readable formatter ──────────────────────────────────────────────────

_LEVEL_COLORS = {
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[1;31m", # bold red
}
_RESET = "\033[0m"


class DevFormatter(logging.Formatter):
    """Coloured, human-readable formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelname, "")
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%H:%M:%S"
        )
        rid = get_request_id()
        rid_str = f" [{rid[:8]}]" if rid else ""
        msg = record.getMessage()
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)
        return (
            f"{color}{ts} {record.levelname:<8}{_RESET} "
            f"{record.module}:{record.lineno}{rid_str} — {msg}"
        )


# ── Setup ─────────────────────────────────────────────────────────────────────

def _setup_logging() -> None:
    """Configure root logger once at import time."""
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # Don't add handlers more than once (hot-reload guard)
    if root.handlers:
        return

    use_json = LOG_FORMAT.lower() == "json"
    formatter: logging.Formatter = (
        JsonFormatter() if use_json else DevFormatter()
    )

    # stdout handler
    stdout_h = logging.StreamHandler(sys.stdout)
    stdout_h.setFormatter(formatter)
    root.addHandler(stdout_h)

    # Rotating file handler
    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        file_h = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_h.setFormatter(formatter)
        root.addHandler(file_h)
    except Exception as exc:
        root.warning("Could not open log file %s: %s", LOG_FILE, exc)

    # Quieten noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


_setup_logging()


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (standard library Logger)."""
    return logging.getLogger(name)
