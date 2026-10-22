"""Dependency providers — the one place server objects are created.

`initialize_state()` runs once at startup (app lifespan): it opens SQLite and
Chroma, reseeds them from `data/`, and builds the advisor agent. Routes get
services through the `get_*` providers below via `Depends`, which tests can
swap with `app.dependency_overrides`.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import Depends, Header

from agent.llm import AIAdvisorAgent, LLMConfig
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


class ServerState:
    """The single db set + agent shared by every request."""

    def __init__(self) -> None:
        self.sql_db_manager: Optional[SQLDatabaseManager] = None
        self.vector_db_manager: Optional[VectorDatabaseManager] = None
        self.advisor_agent: Optional[AIAdvisorAgent] = None


_state = ServerState()


def initialize_state() -> None:
    """Connect the databases, seed them, and build the agent (app startup)."""
    default_data_dir = Path(__file__).resolve().parents[2] / "data"
    data_dir = Path(os.getenv("ADVISOR_DATA_DIR", str(default_data_dir)))
    seed_mode = os.getenv("ADVISOR_SEED_MODE", "reload")
    sqlite_path = os.getenv("ADVISOR_SQLITE_PATH", ".runtime/advisor.db")
    chroma_path = os.getenv("ADVISOR_CHROMA_PATH", ".runtime/chroma")

    sql = SQLDatabaseManager(sqlite_path)
    sql.connect()
    vector = VectorDatabaseManager(
        chroma_path,
        embedding_function=get_embedding_function(os.getenv("ADVISOR_EMBEDDING_FUNCTION", "onnx")),
    )
    vector.connect()

    if seed_mode == "reload":
        seed_sqlite(sql, data_dir=data_dir)
        seed_chroma(vector, data_dir=data_dir)
    elif seed_mode != "off":
        raise ValueError(f"Unknown ADVISOR_SEED_MODE {seed_mode!r}: use 'reload' or 'off'")

    llm_config = LLMConfig.from_env()
    _state.sql_db_manager = sql
    _state.vector_db_manager = vector
    _state.advisor_agent = AIAdvisorAgent.build(sql, vector, llm_config)
    _logger.info("advisor server ready (sqlite=%s, chroma=%s, seed=%s, llm=%s/%s)",
                 sqlite_path, chroma_path, seed_mode,
                 llm_config.provider, llm_config.model or "stubs")


def shutdown_state() -> None:
    """Disconnect everything `initialize_state()` opened (app shutdown)."""
    if _state.sql_db_manager is not None:
        _state.sql_db_manager.disconnect()
    if _state.vector_db_manager is not None:
        _state.vector_db_manager.disconnect()
    _state.sql_db_manager = None
    _state.vector_db_manager = None
    _state.advisor_agent = None


# ---------------------------------------------------------------- providers

def get_sql_db_manager() -> SQLDatabaseManager:
    return _state.sql_db_manager  # type: ignore[return-value]


def get_vector_db_manager() -> VectorDatabaseManager:
    return _state.vector_db_manager  # type: ignore[return-value]


def get_advisor_agent() -> AIAdvisorAgent:
    return _state.advisor_agent  # type: ignore[return-value]


def get_current_student(
    x_student_id: Optional[str] = Header(default=None, alias="X-Student-ID"),
) -> StudentIdentity:
    """Auth is out of scope (FC36): trust the X-Student-ID header, else the demo student."""
    student_id = x_student_id or os.getenv("ADVISOR_DEFAULT_STUDENT_ID", DEFAULT_STUDENT_ID)
    return StudentIdentity(student_id=student_id)


def get_chat_service(agent=Depends(get_advisor_agent), sql=Depends(get_sql_db_manager)) -> ChatService:
    return ChatService(advisor_agent=agent, sql_db_manager=sql)


def get_course_service(sql=Depends(get_sql_db_manager), vector=Depends(get_vector_db_manager)) -> CourseService:
    return CourseService(sql_db_manager=sql, vector_db_manager=vector)


def get_class_service(sql=Depends(get_sql_db_manager)) -> ClassService:
    return ClassService(sql_db_manager=sql)


def get_plan_service(sql=Depends(get_sql_db_manager)) -> PlanService:
    return PlanService(sql_db_manager=sql)


def get_degree_service(sql=Depends(get_sql_db_manager), vector=Depends(get_vector_db_manager)) -> DegreeService:
    return DegreeService(sql_db_manager=sql, vector_db_manager=vector)


def get_student_service(sql=Depends(get_sql_db_manager)) -> StudentService:
    return StudentService(sql_db_manager=sql)


def get_audit_service(sql=Depends(get_sql_db_manager), vector=Depends(get_vector_db_manager)) -> AuditService:
    return AuditService(sql_db_manager=sql, vector_db_manager=vector)
