"""DI providers — the single place all server-facing instances come from.

Per the fastapi skill: routes receive every service, manager, and agent
through these providers (`Depends`); controllers never construct services and
routers never touch db managers. Tests swap implementations via
`app.dependency_overrides` — never by monkeypatching class internals.

Scaffold state (proposed FC-new-rest-api): manager/agent slots are None until
`database/` (outline step 3) and `agent/llm/` (outline step 4) exist. Unwired
service methods raise `NotWiredError` → HTTP 501 envelope.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

from fastapi import Depends, Header

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
# student id comes from the X-Student-ID header; locally this fallback keeps
# the UI working before a client header is wired).
DEFAULT_STUDENT_ID = "STU-2026-9941"

class ServerState:
    """Process-lifetime holder — one agent graph and one db set per process."""

    def __init__(self) -> None:
        # TODO(FC-new-rest-api): populated by initialize_state() below.
        self.sql_db_manager: Optional[Any] = None    # SQLDatabaseManager (FC33, FC34)
        self.vector_db_manager: Optional[Any] = None # VectorDatabaseManager (FC9, FC33)
        self.advisor_agent: Optional[Any] = None     # AIAdvisorAgent (FC22–FC24)


_state = ServerState()


def initialize_state() -> None:
    """Construct the single agent graph + db connection set (app lifespan).

    Single construction point — nothing else in the app may instantiate these.
    TODO(FC-new-rest-api), monorepo outline steps 3–4:
        _state.sql_db_manager = SQLDatabaseManager(...)
        _state.vector_db_manager = VectorDatabaseManager(...)  # + ingest via database/seed.py
        _state.advisor_agent = AIAdvisorAgent(...)
    Each construction should log once (below) until wired.
    """
    _logger.warning(
        "advisor server scaffold: manager/agent zones not built yet "
        "(core=step2, database=step3, agent.llm=step4 in docs/planning/2026-10-19-src-monorepo-structure.md)"
    )


def shutdown_state() -> None:
    """Mirror of initialize_state(): TODO — .disconnect() populated managers."""
    return None


# ---------------------------------------------------------------- providers

def get_sql_db_manager() -> Optional[Any]:
    """SQLDatabaseManager (FC33 — students, sections, enrollments, plans, chat)."""
    return _state.sql_db_manager


def get_vector_db_manager() -> Optional[Any]:
    """VectorDatabaseManager (FC33 — descriptions, catalog, degrees for FC9/FC35)."""
    return _state.vector_db_manager


def get_advisor_agent() -> Optional[Any]:
    """AIAdvisorAgent (FC22–FC24) — the only LLM entry point; created once."""
    return _state.advisor_agent


def get_current_student(
    x_student_id: Optional[str] = Header(default=None, alias="X-Student-ID"),
) -> StudentIdentity:
    """Pre-authenticated student session (FC36). No auth flows, ever.

    Identity is the header value, falling back to ADVISOR_DEFAULT_STUDENT_ID
    (then DEFAULT_STUDENT_ID) in local development.
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
