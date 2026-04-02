"""
Logging configuration for HostFlow.

Strategy:
  - local/staging: human-readable format with colours (via uvicorn default)
  - production:    JSON-structured logs to stdout — picked up by Railway / Fly / Render
                   log aggregators without extra tooling

Usage:
    from app.core.logging_config import configure_logging
    configure_logging()   # call once in lifespan, before anything else logs

All application code should use standard logging:
    import logging
    logger = logging.getLogger(__name__)
    logger.info("message", extra={"key": "value"})  # extra fields in JSON output
"""
import json
import logging
import sys
from datetime import datetime, timezone


class _JSONFormatter(logging.Formatter):
    """
    Emits one JSON object per log line.

    Fields always present:
        ts       — ISO 8601 UTC timestamp
        level    — log level name
        logger   — logger name (module path)
        msg      — formatted message
        exc      — exception info (only when an exception is attached)

    Any `extra` dict passed to logger.info(..., extra={...}) is merged in at
    the top level, which makes structured queries easy in log aggregators.
    """

    _RESERVED = {
        "args", "created", "exc_info", "exc_text", "filename", "funcName",
        "levelname", "levelno", "lineno", "message", "module", "msecs",
        "msg", "name", "pathname", "process", "processName", "relativeCreated",
        "stack_info", "taskName", "thread", "threadName",
    }

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        payload: dict = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.message,
        }

        # Merge any extra fields the caller supplied
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    """
    Configure the root logger.

    Args:
        level:     Log level string — DEBUG, INFO, WARNING, ERROR.
        json_logs: True → JSON formatter (production).
                   False → default uvicorn-style text (local/staging).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    if json_logs:
        handler.setFormatter(_JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Replace all existing handlers (uvicorn may have added its own)
    root.handlers.clear()
    root.addHandler(handler)

    # Quieten noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # we log requests ourselves
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if level.upper() == "DEBUG" else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
