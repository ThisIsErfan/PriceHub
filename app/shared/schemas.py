"""The single response envelope every endpoint returns.

Mirrors the pricing-copilot backend so a consumer of both APIs sees one shape:

    {"success": bool, "message": str, "responseCode": int, "data": <any>}
"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


def envelope(success: bool, message: str, code: int, data: Any = None) -> JSONResponse:
    """Build the uniform JSON envelope with a matching HTTP status code."""
    return JSONResponse(
        status_code=code,
        content={
            "success": success,
            "message": message,
            "responseCode": code,
            "data": data,
        },
    )


def ok(data: Any = None, message: str = "OK") -> JSONResponse:
    """200 success envelope."""
    return envelope(True, message, 200, data)
