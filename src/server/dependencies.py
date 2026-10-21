"""DI providers — the single place all server-facing instances come from.

Per the fastapi skill: routes receive every service, manager, and agent
through these providers (`Depends`); controllers never construct services and
routers never touch db managers. Tests override providers with
`app.dependency_overrides` — or, for store-location tests, set the
ADVISOR_* environment variables before the app boots (lifespan reads them).

Wired state (agent zone live — monorepo outline step 4): SQLDatabaseManager
(FC33/FC34) + VectorDatabaseManager (FC9/FC33) with reload seeding + the
AIAdvisorAgent graph (FC22–FC24, FC27–FC28) — chat send answers real turns
(ADVISOR_LLM_PROVIDER=ollama default, stub offline). The §2 plan generator
(FC2/FC25/FC26) remains unbuilt — plan writes stay 501 `not_wired`.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, Header

from agent.llm import AIAdvisorAgent, LLMConfig
from agent.errors import LLMError
from database.errors import RecordNotFoundError
from database.seed import DEFAULT_STUDENT_ID, seed_chroma, seed_sqlite
from database.sql.sqlite_manager import SQLDatabaseManager
from database.vector.chroma_manager import VectorDatabaseManager
from database.vector.embeddings import get_embedding_function
from server.schemas.students import StudentIdentity
from server.services.audit import AuditService
from server.services.chat import ChatService
from server.services.classes import ClassService
from server.services.courses import CourseService
from server.services.degrees import DegreeService
from server.services.plans import PlanService
from server.services.students import StudentService

_logger = logging.getLogger("server")

# Dev fallback identity (FC36 — auth is out of scope: the pre-authenticated
# student id comes from the X-Student-ID header; the default matches the
# seeded demo student from data/student-demo.json — re-exported as the shared
# constant in database.seed).


class ServerState:
    """Process-lifetime holder — one agent graph and one db set per process."""

    def __init__(self) -> None:
        self.sql_db_manager: Optional[SQLDatabaseManager] = None   # FC33, FC34
        self.vector_db_manager: Optional[VectorDatabaseManager] = None  # FC9, FC33
        self.advisor_agent: Optional[Any] = None                   # AIAdvisorAgent (FC22–FC24)


_state = ServerState()


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def initialize_state() -> None:
    """Construct the single db set + agent (app lifespan).

    Single construction point — nothing else in the app may instantiate these.
    The advisor_agent remains None until the agent/llm zone exists (outline
    step 4): chat send keeps answering 501 `not_wired`.
    """
    data_dir = Path(_env("ADVISOR_DATA_DIR", str(Path(__file__).resolve().parents[2] / "data")))
    seed_mode = _env("ADVISOR_SEED_MODE", "reload")  # product decision: reload every startup

    sql = SQLDatabaseManager(_env("ADVISOR_SQLITE_PATH", "var/advisor.db"))
    sql.connect()
    vector = VectorDatabaseManager(
        _env("ADVISOR_CHROMA_PATH", "var/chroma"),
        embedding_function=get_embedding_function(_env("ADVISOR_EMBEDDING_FUNCTION", "onnx")),
    )
    vector.connect()
    if seed_mode == "reload":
        seed_sqlite(sql, data_dir=data_dir)
        seed_chroma(vector, data_dir=data_dir)
    elif seed_mode != "off":
        raise ValueError(f"Unknown ADVISOR_SEED_MODE {seed_mode!r}: use 'reload' or 'off'")

    _state.sql_db_manager = sql
    _state.vector_db_manager = vector
    # FC22–FC24: the advisor graph goes live here (ollama provider by
    # default; 'stub' for offline tests/demos — never a live model in tests).
    llm_config = LLMConfig.from_env()
    _state.advisor_agent = AIAdvisorAgent.build(sql, vector, llm_config)
    _logger.info("advisor server wired (sqlite=%s, chroma=%s, seed=%s, llm=%s/%s)",
                 _env("ADVISOR_SQLITE_PATH", "var/advisor.db"),
                 _env("ADVISOR_CHROMA_PATH", "var/chroma"), seed_mode,
                 llm_config.provider, llm_config.model or "stubs")


def shutdown_state() -> None:
    """Mirror of initialize_state(): disconnect constructed managers."""
    if _state.sql_db_manager is not None:
        _state.sql_db_manager.disconnect()
        _state.sql_db_manager = None
    if _state.vector_db_manager is not None:
        _state.vector_db_manager.disconnect()
        _state.vector_db_manager = None
    _state.advisor_agent = None


# ---------------------------------------------------------------- providers

def get_sql_db_manager() -> SQLDatabaseManager:
    """SQLDatabaseManager (FC33 — students, sections, enrollments, plans, chat)."""
    return _state.sql_db_manager  # type: ignore[return-value]


def get_vector_db_manager() -> VectorDatabaseManager:
    """VectorDatabaseManager (FC33 — descriptions, catalog, degrees for FC9/FC35)."""
    return _state.vector_db_manager  # type: ignore[return-value]


def get_advisor_agent():
    """AIAdvisorAgent (FC22–FC24) — the agent/llm graph (built in lifespan)."""
    return _state.advisor_agent


def get_current_student(
    x_student_id: Optional[str] = Header(default=None, alias="X-Student-ID"),
) -> StudentIdentity:
    """Pre-authenticated student session (FC36). No auth flows, ever.

    Identity is the header value, falling back to ADVISOR_DEFAULT_STUDENT_ID
    (then the seeded demo student) in local development.
    """
    student_id = x_student_id or os.getenv("ADVISOR_DEFAULT_STUDENT_ID", DEFAULT_STUDENT_ID)
    return StudentIdentity(student_id=student_id)


# ------------------------------------------------- service providers (per resource)

def get_chat_service(
    advisor_agent: Any = Depends(get_advisor_agent),
    sql_db_manager: Any = Depends(get_sql_db_manager),
) -> ChatService:
    return ChatService(advisor_agent=advisor_agent, sql_db_manager=sql_db_manager)


def get_course_service(
    sql_db_manager: Any = Depends(get_sql_db_manager),
    vector_db_manager: Any = Depends(get_vector_db_manager),
) -> CourseService:
    return CourseService(sql_db_manager=sql_db_manager, vector_db_manager=vector_db_manager)


def get_class_service(
    sql_db_manager: Any = Depends(get_sql_db_manager),
) -> ClassService:
    return ClassService(sql_db_manager=sql_db_manager)


def get_plan_service(
    sql_db_manager: Any = Depends(get_sql_db_manager),
) -> PlanService:
    return PlanService(sql_db_manager=sql_db_manager)


def get_degree_service(
    sql_db_manager: Any = Depends(get_sql_db_manager),
    vector_db_manager: Any = Depends(get_vector_db_manager),
) -> DegreeService:
    return DegreeService(sql_db_manager=sql_db_manager, vector_db_manager=vector_db_manager)


def get_student_service(
    sql_db_manager: Any = Depends(get_sql_db_manager),
) -> StudentService:
    return StudentService(sql_db_manager=sql_db_manager)


def get_audit_service(
    sql_db_manager: Any = Depends(get_sql_db_manager),
    vector_db_manager: Any = Depends(get_vector_db_manager),
) -> AuditService:
    return AuditService(sql_db_manager=sql_db_manager, vector_db_manager=vector_db_manager)