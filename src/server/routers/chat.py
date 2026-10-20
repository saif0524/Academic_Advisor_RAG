"""Chat routes (FC22–FC24, FC27–FC28, FC34)."""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from server.controllers import chat as chat_controller
from server.dependencies import get_chat_service, get_current_student
from server.schemas.chat import ChatHistoryResponse, ChatMessageRequest, ChatMessageReply
from server.schemas.common import ErrorResponse
from server.schemas.students import StudentIdentity
from server.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/messages",
    response_model=ChatMessageReply,
    responses={501: {"model": ErrorResponse}},
    operation_id="send_chat_message",
)
def send_message(
    payload: ChatMessageRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: ChatService = Depends(get_chat_service),
) -> ChatMessageReply:
    """Send one message to the AI advising assistant (FC22).

    Carries `session_id` for multi-turn context (FC27–FC28) and
    `confirmed_action_id` proving the user confirmed a proposed action (FC23) —
    unconfirmed assistant actions are rejected agent-side.
    """
    return chat_controller.send_message(student, payload, service)


@router.get(
    "/messages",
    response_model=ChatHistoryResponse,
    responses={501: {"model": ErrorResponse}},
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