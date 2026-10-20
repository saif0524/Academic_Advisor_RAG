"""Error envelope + global exception handlers for the advisor HTTP API.

Domain failures from `core/errors.py` (constraint rejections, FC29–FC32) are
mapped to HTTP status codes here — they must never surface as generic 500s.
Scaffold status: only `NotWiredError` (501) is registered; the core-mapping
handler is TODO until `src/core/` exists (monorepo outline step 2).
"""
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from server.schemas.common import ErrorDetail, ErrorResponse


class NotWiredError(Exception):
    """Raised by scaffold services whose backing component doesn't exist yet.

    Maps to HTTP 501 so the frontend renders an explicit "feature not wired"
    state instead of guessing at empty/fabricated data (grounded-answers-only
    rule in AGENTS.md).
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def error_envelope(
    code: str, message: str, details: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Build the `{"error": {...}}` body shared by all non-2xx responses."""
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return body.model_dump(exclude_none=True)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach app-wide exception handlers. Called once from `create_app()`."""

    @app.exception_handler(NotWiredError)
    async def not_wired_handler(request: Request, exc: NotWiredError) -> JSONResponse:
        # TODO(FC-new-rest-api): when `core/errors.py` lands, register handlers
        # next to this one mapping ValidationFailure (FC29–FC32 rejections) to
        # 409/422 with per-check detail, and catalog/lookup misses to 404.
        return JSONResponse(
            status_code=501,
            content=error_envelope("not_wired", exc.message),
        )