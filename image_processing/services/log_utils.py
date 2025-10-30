import json
import logging
import os
from datetime import datetime


_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'logs', 'image_ai.log')
_LOG_PATH = os.path.normpath(_LOG_PATH)
os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)


logger = logging.getLogger("image_ai")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(_LOG_PATH, encoding="utf-8")
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def _write(kind: str, provider: str, **kwargs):
    record = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "kind": kind,
        "provider": provider or "",
        **kwargs,
    }
    try:
        logger.info(json.dumps(record, ensure_ascii=False))
    except Exception:
        pass


def log_ai_request(provider: str, endpoint: str, payload_meta: dict | None = None):
    _write("request", provider, endpoint=endpoint, payload_meta=payload_meta or {})


def log_ai_response(provider: str, status: int, latency_ms: int, extra: dict | None = None):
    _write("response", provider, status=status, latency_ms=latency_ms, extra=extra or {})


def log_ai_error(provider: str, status: int | None, message: str, extra: dict | None = None):
    _write("error", provider, status=status, message=message, extra=extra or {})
