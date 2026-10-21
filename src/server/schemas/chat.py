"""Chat contracts — assistant conversation (FC22–FC24, FC27–FC28, FC34)."""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class PendingAction(BaseModel):
    """An assistant-proposed action awaiting explicit user confirmation (FC23).

    The UI (components/classes confirm dialogs) turns this into a second POST
    carrying `confirmed_action_id`; the agent resumes the action only then.
    """

    action_id: str
    # One of FC23's action kinds: add_class, change_class_status, change_major,
    # change_concentration, change_degree.
    action_type: str = Field(examples=["add_class"])
    description: str = Field(
        description="Human-readable summary of what will happen if confirmed."
    )


class ChatMessageRequest(BaseModel):
    """Send one user message to the assistant (FC22)."""

    message: str = Field(min_length=1, description="Free-text student message.")
    session_id: Optional[str] = Field(
        default=None,
        description="Ongoing session id; omitted starts/continues the active session (FC27).",
    )
    confirmed_action_id: Optional[str] = Field(
        default=None,
        description="Proof of explicit user confirmation for a pending_action (FC23).",
    )
    cancelled_action_id: Optional[str] = Field(
        default=None,
        description="Explicit cancellation of a pending_action (FC23) — no action taken.",
    )


class ChatMessageReply(BaseModel):
    """Assistant reply for one turn — may carry a pending confirmation (FC23)."""

    session_id: str
    student_id: str
    reply: str
    pending_action: Optional[PendingAction] = Field(
        default=None, description="Present when the assistant proposes an action (FC23)."
    )


class ChatHistoryMessage(BaseModel):
    """One persisted turn (FC34 — history lives in SQLite, never app memory)."""

    role: Literal["user", "assistant"]
    content: str
    created_at: Optional[datetime] = None


class ChatHistoryResponse(BaseModel):
    """Persisted advising history for a session (FC34)."""

    session_id: str
    student_id: str
    messages: List[ChatHistoryMessage]
    pending_action: Optional[PendingAction] = Field(
        default=None,
        description="The session's newest open proposal (FC23 durability across reloads).",
    )


class ChatSessionSummary(BaseModel):
    """One conversation in the drawer's history list (FC34 view; FC35)."""

    session_id: str
    title: str = Field(description="First user message (truncated) — never synthesized.")
    created_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None


class ChatSessionsResponse(BaseModel):
    """The student's advising conversations (FC34 view)."""

    results: List[ChatSessionSummary] = Field(default_factory=list)
    count: int = 0