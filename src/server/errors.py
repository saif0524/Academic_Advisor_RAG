"""Error envelope + global exception handlers for the advisor HTTP API.

Domain failures must never surface as generic 500s:
- `NotWiredError` → 501 `not_wired` (backing zone not built; no fake data)
- database lookup misses → 404 `not_found` (grounded-answers rule)
- `InvalidRequestError` → 422 `validation_failed` (e.g. FC16 misalignment)
- TODO (core zone): FC29–FC32 ValidationFailure → 409/422 per-check detail
"""
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from database.errors import RecordNotFoundError
from server.schemas.common import ErrorDetail, ErrorResponse


class NotWiredError(Exception):
    """Raised by services whose backing component doesn't exist yet.

    Maps to HTTP 501 so the frontend renders an explicit "feature not wired"
    state instead of guessing at empty/fabricated data (grounded-answers-only
    rule in AGENTS.md).
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidRequestError(Exception):
    """A semantically invalid request for an otherwise well-formed payload.

    Used where validation needs store context the Pydantic layer doesn't have
    (e.g. FC16: a degree not aligned to the student's major) → 422.
    """

    def __init__(self, message: str, details: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


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
        return JSONResponse(
            status_code=501,
            content=error_envelope("not_wired", exc.message),
        )

    @app.exception_handler(RecordNotFoundError)
    async def record_not_found_handler(request: Request, exc: RecordNotFoundError) -> JSONResponse:
        # Empty lookups answer 404 — never fabricated filler (AGENTS.md rule).
        return JSONResponse(
            status_code=404,
            content=error_envelope("not_found", exc.message),
        )

    @app.exception_handler(InvalidRequestError)
    async def invalid_request_handler(request: Request, exc: InvalidRequestError) -> JSONResponse:
        # FC16-style semantic validation failures carry their reason in details.
        return JSONResponse(
            status_code=422,
            content=error_envelope("validation_failed", exc.message, exc.details),
        )