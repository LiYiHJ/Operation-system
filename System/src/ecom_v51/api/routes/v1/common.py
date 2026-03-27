from __future__ import annotations

from typing import Any, Dict, Tuple
from uuid import uuid4

from flask import Request, jsonify, request


def get_trace_id(req: Request | None = None) -> str:
    req = req or request
    header_value = str(req.headers.get("X-Trace-Id") or "").strip()
    return header_value or f"trc_{uuid4().hex[:20]}"


def envelope(*, data: Any = None, error: Dict[str, Any] | None = None, status_code: int = 200, trace_id: str | None = None) -> Tuple[Any, int]:
    payload = {
        "success": error is None,
        "traceId": trace_id or get_trace_id(),
        "data": data if error is None else None,
        "error": error,
    }
    return jsonify(payload), status_code


def ok(data: Any = None, *, trace_id: str | None = None, status_code: int = 200):
    return envelope(data=data, trace_id=trace_id, status_code=status_code)


def fail(code: str, message: str, *, details: Dict[str, Any] | None = None, status_code: int = 400, trace_id: str | None = None):
    error = {
        "code": code,
        "message": message,
        "details": details or {},
    }
    return envelope(error=error, trace_id=trace_id, status_code=status_code)
