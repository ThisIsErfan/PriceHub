"""The single response envelope every endpoint returns.

Mirrors the pricing-copilot backend so a consumer of both APIs sees one shape:

    {"success": bool, "message": str, "responseCode": int, "data": <any>}
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

# Prices/purity come back as Decimal and timestamps as datetime — Starlette's
# JSONResponse (plain json.dumps) can't serialize either. jsonable_encoder turns
# datetime into ISO-8601; we override Decimal → str so exact price precision is
# preserved (float would round large rial amounts). Applied to EVERY response so
# no endpoint can 500 on an unencodable value.
_CUSTOM_ENCODERS = {Decimal: str}


def envelope(success: bool, message: str, code: int, data: Any = None) -> JSONResponse:
    """Build the uniform JSON envelope with a matching HTTP status code."""
    payload = {
        "success": success,
        "message": message,
        "responseCode": code,
        "data": data,
    }
    return JSONResponse(
        status_code=code,
        content=jsonable_encoder(payload, custom_encoder=_CUSTOM_ENCODERS),
    )


def ok(data: Any = None, message: str = "OK") -> JSONResponse:
    """200 success envelope."""
    return envelope(True, message, 200, data)
