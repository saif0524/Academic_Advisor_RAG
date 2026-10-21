"""Chat routes (FC22–FC24, FC27–FC28, FC34–FC35)."""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from server.controllers import chat as chat_controller
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


@router.post(
    "/messages",
    response_model=ChatMessageReply,
    operation_id="send_chat_message",
)
def send_message(
    payload: ChatMessageRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: ChatService = Depends(get_chat_service),
) -> ChatMessageReply:
    """Send one message to the AI advising assistant (FC22; wired).

    Carries `session_id` for multi-turn context (FC27–FC28) and
    `confirmed_action_id`/`cancelled_action_id` proving the user decided a
    proposed action (FC23) — the executor runs only on explicit decisions.
    """
    return chat_controller.send_message(student, payload, service)


@router.get(
    "/sessions",
    response_model=ChatSessionsResponse,
    operation_id="list_chat_sessions",
)
def list_sessions(
    student: StudentIdentity = Depends(get_current_student),
    service: ChatService = Depends(get_chat_service),
) -> ChatSessionsResponse:
    """The student's advising conversations (FC34 view; drawer history list)."""
    return chat_controller.list_sessions(student, service)


@router.get(
    "/messages",
    response_model=ChatHistoryResponse,
    operation_id="get_chat_history",
)
def get_history(
    session_id: Optional[str] = Query(
        None, description="Session to read; omitted returns the active session (FC27)."
    ),
    student: StudentIdentity = Depends(get_current_student),
    service: ChatService = Depends(get_chat_service),
) -> ChatHistoryResponse:
    """Persisted advising history for the student (FC34 — stored in SQLite)."""
    return chat_controller.get_history(student, session_id, service)