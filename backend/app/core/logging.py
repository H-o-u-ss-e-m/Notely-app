"""Logs applicatifs : format texte (dev) ou JSON structure, avec request_id.

Regle : ne jamais logger de traces (strokes), de texte reconnu, d'e-mails ni de tokens.
Logger des identifiants, des durees et des compteurs.
"""
import contextvars
import json
import logging
import os
import sys

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_EXTRA_FIELDS = ("job_id", "user_id", "latency_ms", "status_code", "method", "path")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
            "request_id": request_id_var.get(),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k in _EXTRA_FIELDS})
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def setup_logging() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    env = os.getenv("ENV", "dev").lower()
    fmt = os.getenv("LOG_FORMAT", "text" if env == "dev" else "json").lower()
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RequestIdFilter())
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s [%(request_id)s]: %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
