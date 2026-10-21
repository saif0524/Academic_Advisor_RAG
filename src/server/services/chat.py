"""Chat service — conversation flow via AIAdvisorAgent (FC22–FC24, FC27–FC28, FC34).

Wired now: history reads (FC34, SQLite-backed). One-turn sends still need the
agent zone (`AIAdvisorAgent`, monorepo outline step 4) and stay 501
`not_wired` — the agent classifies intent, routes SQLite vs Chroma (FC33),
enforces the FC23 confirmation gate, and summarizes; none of that exists yet.
"""
from typing import Any, List, Optional

from database.errors import RecordNotFoundError
from server.errors import NotWiredError
from server.schemas.chat import ChatHistoryMessage, ChatHistoryResponse, ChatMessageReply, ChatMessageRequest


class ChatService:
    """Wiring: `advisor_agent` (agent/llm — step 4) + `sql_db_manager` (FC34)."""

    def __init__(self, advisor_agent: Any, sql_db_manager: Any) -> None:
        self._advisor_agent = advisor_agent
        self._sql_db_manager = sql_db_manager

    def send_message(
        self, student_id: str, request: ChatMessageRequest
    ) -> ChatMessageReply:
        """One turn: → `AIAdvisorAgent.process_query` (FC22). UNWIRED.

        `request.confirmed_action_id` (FC23) must be present to resume a
        pending action; the agent-side interrupt enforces confirm-before-acting.
        Session continuity and multi-turn clarification are agent-owned
        (FC27–FC28); every turn persists via `sql_db_manager` (FC34).
        """
        if self._sql_db_manager is None:
            raise RuntimeError("SQLDatabaseManager missing — cannot persist (FC34)")
        if self._advisor_agent is None:
            raise NotWiredError(
                "Chat is not wired yet: needs AIAdvisorAgent (agent/llm — monorepo outline step 4)."
            )
        session_id = request.session_id or self._sql_db_manager.ensure_chat_session(student_id)
        reply = self._advisor_agent.process_query(student_id, request.message)
        return ChatMessageReply(
            session_id=session_id,
            student_id=student_id,
            reply=reply,
            pending_action=None,  # agent fills proposals (FC23) once wired
        )

    def get_history(
        self, student_id: str, session_id: Optional[str] = None
    ) -> ChatHistoryResponse:
        """Persisted advising history (FC34) — read from SQLite, never app memory.

        Omitted session id continues the student's active session (FC27);
        an explicit unknown session id is a 404, never an empty answer.
        """
        if self._sql_db_manager is None:
            raise RuntimeError("SQLDatabaseManager missing — history lives in SQLite (FC34)")
        if session_id is None:
            session_id = self._sql_db_manager.ensure_chat_session(student_id)
        try:
            rows = self._sql_db_manager.get_chat_history(student_id, session_id)
        except RecordNotFoundError as exc:
            raise _http_not_found(exc)
        messages: List[ChatHistoryMessage] = [
            ChatHistoryMessage(role=row["role"], content=row["content"], created_at=row["created_at"])
            for row in rows
        ]
        return ChatHistoryResponse(session_id=session_id, student_id=student_id, messages=messages)


def _http_not_found(exc: RecordNotFoundError) -> RecordNotFoundError:
    return exc  # database.errors.RecordNotFoundError is the handled 404 type