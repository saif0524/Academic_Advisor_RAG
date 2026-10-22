"""Chat routes (FC22–FC24, FC27–FC28, FC34–FC35)."""
from typing import Optional

import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

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


@router.post("/messages/stream")
def send_message_stream(
    payload: ChatMessageRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """FC39: `POST /chat/messages` as newline-delimited JSON events —
    `check` (each deterministic FC29–FC32 result as it runs), `token`
    (answer text), `done` (final reply + FC23 proposal), or `error`."""
    events = service.send_message_stream(student.student_id, payload)
    return StreamingResponse(
        (json.dumps(event) + "\n" for event in events),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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