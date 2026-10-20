"""FastAPI app factory + lifespan for the advisor HTTP API (proposed FC-new-rest-api).

Thin adapter over the agent/database/core zones (`server → {agent, database,
core}`); nothing in `agent`/`database`/`core` may import this package.
Structure & rules: `.pi/skills/fastapi/SKILL.md`,
`docs/2026-10-19-src-monorepo-structure.md` §server.

Run from the repo root:
    PYTHONPATH=src python -m uvicorn server.app:app --reload
    PYTHONPATH=src python -m server.app
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server import dependencies
from server.errors import register_exception_handlers
from server.routers import audits, chat, classes, courses, degrees, plans, students
from server.schemas.common import HealthResponse

_API_TAGS = [
    {"name": "chat", "description": "AI advising assistant (FC22–FC24; multi-turn FC27–FC28; history FC34)"},
    {"name": "courses", "description": "Course discovery — keyword (FC8/FC10 → SQLite) and semantic (FC9 → Chroma) search, details and sections (FC11–FC12)"},
    {"name": "classes", "description": "Classes on the student profile — bookmark (FC13), add (FC14), remove (FC20), status (FC21)"},
    {"name": "plans", "description": "Degree plans — major/spec (FC1), generate (FC2/FC25), edit/versions/revert (FC3–FC5), multiple plans (FC6), compare (FC26)"},
    {"name": "degrees", "description": "Degree catalog — explore (FC15), requirements (FC18)"},
    {"name": "students", "description": "Profile & identity — pre-auth student (FC36), major/history (FC1, FC7), selected degree & progress (FC16–FC17, FC19)"},
    {"name": "audits", "description": "Deterministic audits (FC24) running safeguards FC29–FC32 in code"},
]


@dataclass(frozen=True)
class ServerSettings:
    """Env-tunable server settings (FC36: no auth; CORS is dev plumbing)."""

    cors_origins: List[str]
    host: str
    port: int

    @classmethod
    def from_env(cls) -> "ServerSettings":
        raw_origins = os.getenv("ADVISOR_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
        return cls(
            cors_origins=[o.strip() for o in raw_origins.split(",") if o.strip()],
            host=os.getenv("ADVISOR_HOST", "127.0.0.1"),
            port=int(os.getenv("ADVISOR_PORT", "8000")),
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Init the single agent graph + db set on startup; disconnect on shutdown.

    Instance construction lives only in `dependencies.initialize_state()` —
    one wiring point per the fastapi skill.
    """
    dependencies.initialize_state()
    yield
    dependencies.shutdown_state()


def create_app(settings: Optional[ServerSettings] = None) -> FastAPI:
    """Build and configure the advisor FastAPI app (factory for tests + prod)."""
    settings = settings or ServerSettings.from_env()

    app = FastAPI(
        title="Academic AI Advisor API",
        version="0.1.0",
        description=(
            "HTTP surface for the Academic AI Advisor: deterministic planning/audit "
            "engine (FC2, FC24–FC26, FC29–FC32), RAG course/degree search (FC8–FC12, FC15/FC18), "
            "and the confirm-first conversational assistant (FC22–FC24, FC27–FC28). "
            "Scaffold state (proposed FC-new-rest-api): unwired endpoints return 501 'not_wired'."
        ),
        lifespan=lifespan,
        openapi_tags=_API_TAGS,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["health"],
        operation_id="get_health",
    )
    def health() -> HealthResponse:
        """Liveness probe — carries no student or academic data."""
        return HealthResponse(status="ok", version=app.version)

    for router in (
        chat.router,
        courses.router,
        classes.router,
        plans.router,
        degrees.router,
        students.router,
        audits.router,
    ):
        app.include_router(router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=app.state.settings.host, port=app.state.settings.port)