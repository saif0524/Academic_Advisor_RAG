"""Chat routes (FC22–FC24, FC27–FC28, FC34–FC35)."""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from server.dependencies import get_chat_service, get_current_student
from server.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageReply,
    ChatSessionsResponse,
)
from server.schemas.students import StudentIdentity
from server.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages")
def send_message(
    payload: ChatMessageRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: ChatService = Depends(get_chat_service),
) -> ChatMessageReply:
    """Send one message to the AI advising assistant (FC22).

    Carries `session_id` for multi-turn context (FC27–FC28) and
    `confirmed_action_id`/`cancelled_action_id` proving the user decided a
    proposed action (FC23) — the executor runs only on explicit decisions.
    """
    return service.send_message(student.student_id, payload)


@router.post("/sessions", status_code=201)
def create_session(
    student: StudentIdentity = Depends(get_current_student),
    service: ChatService = Depends(get_chat_service),
) -> ChatHistoryResponse:
    """Start a new empty conversation (drawer "New chat")."""
    return service.create_session(student.student_id)


@router.get("/sessions")
def list_sessions(
    student: StudentIdentity = Depends(get_current_student),
    service: ChatService = Depends(get_chat_service),
) -> ChatSessionsResponse:
    """The student's advising conversations (FC34 view; drawer history list)."""
    return service.list_sessions(student.student_id)


@router.get("/messages")
def get_history(
    session_id: Optional[str] = Query(
        None, description="Session to read; omitted returns the active session (FC27)."
    ),
    student: StudentIdentity = Depends(get_current_student),
    service: ChatService = Depends(get_chat_service),
) -> ChatHistoryResponse:
    """Persisted advising history for the student (FC34 — stored in SQLite)."""
    return service.get_history(student.student_id, session_id)