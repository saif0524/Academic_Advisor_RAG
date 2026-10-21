"""Chat service — conversation flow via AIAdvisorAgent (FC22–FC24, FC27–FC28,
FC34) — wired: the agent zone is live.

Flow per turn: resolve/verify the session → validate any FC23 decision proof
→ persist the user turn (FC34) → `AIAdvisorAgent.process_query` (classify →
route → deterministic tools → summarize) → persist the assistant turn →
map the FC23 proposal, if any, into the reply contract."""
from typing import List, Optional

from agent.errors import LLMError
from database.errors import RecordNotFoundError
from server.errors import InvalidRequestError, NotWiredError
from server.schemas.chat import (
    ChatHistoryMessage,
    ChatHistoryResponse,
    ChatMessageReply,
    ChatMessageRequest,
    ChatSessionSummary,
    ChatSessionsResponse,
    PendingAction,
)


class ChatService:
    """Wiring: `advisor_agent` (agent/llm graph) + `sql_db_manager` (FC34)."""

    def __init__(self, advisor_agent, sql_db_manager) -> None:
        self._advisor_agent = advisor_agent
        self._sql_db_manager = sql_db_manager

    def send_message(self, student_id: str, request: ChatMessageRequest) -> ChatMessageReply:
        """One turn (FC22): persist → agent → persist → reply.

        FC37/FC23: `confirmed_action_id`/`cancelled_action_id` must reference
        an open, student- and session-owned pending action — the agent runs
        the deterministic executor only for a validated decision. LLM
        failures surface as 503 `llm_unavailable` (never a fabricated answer).
        """
        if self._sql_db_manager is None:
            raise RuntimeError("SQLDatabaseManager missing — cannot persist (FC34)")
        if self._advisor_agent is None:
            raise NotWiredError(
                "Chat is not wired yet: needs AIAdvisorAgent (agent/llm).")

        session_id = self._resolve_session(student_id, request.session_id)
        self._validate_decision(student_id, session_id, request)

        # FC34: store the user turn before the agent runs (honest trace even
        # when the model fails; the failure then surfaces as 503).
        self._sql_db_manager.append_chat_message(session_id, student_id, "user", request.message)
        result = self._advisor_agent.process_query(
            student_id, request.message, session_id=session_id,
            confirmed_action_id=request.confirmed_action_id,
            cancelled_action_id=request.cancelled_action_id,
        )
        reply_text = result.get("reply") or ""
        self._sql_db_manager.append_chat_message(
            session_id, student_id, "assistant", reply_text)

        pending = result.get("pending_action")
        return ChatMessageReply(
            session_id=result.get("session_id") or session_id,
            student_id=student_id,
            reply=reply_text,
            pending_action=PendingAction(**pending) if pending else None,
        )

    def list_sessions(self, student_id: str) -> ChatSessionsResponse:
        """Sessions view for the drawer's history list (FC34, FC35)."""
        rows = self._sql_db_manager.list_chat_sessions(student_id)
        summaries = [ChatSessionSummary(**row) for row in rows]
        return ChatSessionsResponse(results=summaries, count=len(summaries))

    def get_history(self, student_id: str, session_id: Optional[str] = None) -> ChatHistoryResponse:
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
        except RecordNotFoundError:
            raise
        messages: List[ChatHistoryMessage] = [
            ChatHistoryMessage(role=row["role"], content=row["content"], created_at=row["created_at"])
            for row in rows
        ]
        pending = self._sql_db_manager.get_open_pending_action(session_id)
        pending_action = PendingAction(
            action_id=pending["action_id"], action_type=pending["action_type"],
            description=pending["description"],
        ) if pending else None
        return ChatHistoryResponse(
            session_id=session_id, student_id=student_id, messages=messages,
            pending_action=pending_action,
        )

    # ------------------------------------------------------------ plumbing

    def _resolve_session(self, student_id: str, session_id: Optional[str]) -> str:
        """FC27/FC34: an explicit unknown/foreign session is a 404 — never a
        silent switch; otherwise continue (or open) the active session."""
        if session_id:
            if not self._sql_db_manager.chat_session_exists(student_id, session_id):
                raise RecordNotFoundError(
                    f"Chat session {session_id!r} not found for student {student_id!r}")
            return session_id
        return self._sql_db_manager.ensure_chat_session(student_id)

    def _validate_decision(self, student_id: str, session_id: str, request: ChatMessageRequest) -> None:
        """FC23/FC37 gate: the decision proof must reference an OPEN pending
        action owned by this student and this session."""
        action_id = request.confirmed_action_id or request.cancelled_action_id
        if not action_id:
            return
        action = self._sql_db_manager.get_pending_action(action_id)
        if action is None:
            raise RecordNotFoundError(f"Pending action {action_id!r} not found")
        if action["student_id"] != student_id or action["session_id"] != session_id:
            raise InvalidRequestError(
                "That proposal belongs to a different student or conversation.")
        if action["status"] != "open":
            raise InvalidRequestError(
                f"That proposal was already resolved ({action['status']}).")