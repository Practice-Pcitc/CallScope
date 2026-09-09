"""Structured, allowlisted operational logs; never log input, source or exceptions."""

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "time": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            "request_id": request_id_context.get(),
        }
        for key in (
            "run_id",
            "provider",
            "model",
            "duration_ms",
            "status",
            "attempt",
            "input_tokens",
            "output_tokens",
            "error_type",
        ):
            if hasattr(record, key):
                data[key] = getattr(record, key)
        return json.dumps(data, ensure_ascii=False)


logger = logging.getLogger("callscope")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False
