"""Cross-resource response contracts (Pydantic v2)."""
from typing import List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Machine-readable failure detail ("errors come with a reason")."""

    code: str = Field(description="Stable error code, e.g. 'not_found'.")
    message: str = Field(description="Human-readable explanation of the failure.")
    details: Optional[List[str]] = Field(
        default=None, description="Optional per-item details, e.g. failed constraint checks."
    )


class ErrorResponse(BaseModel):
    """Envelope for all non-2xx responses: `{"error": {...}}`."""

    error: ErrorDetail


class HealthResponse(BaseModel):
    """Liveness payload — contains no student or academic data."""

    status: str = Field(examples=["ok"])
    version: str = Field(examples=["0.1.0"])