"""Chat service — conversation flow via AIAdvisorAgent (FC22–FC24, FC27–FC28, FC34)."""
from typing import Optional

from server.errors import NotWiredError
from server.schemas.chat import ChatHistoryResponse, ChatMessageRequest, ChatMessageReply


class ChatService:
    """Owns chat orchestration; the HTTP layer never talks to the agent directly.

    Wiring expectations:
    - `advisor_agent`: `AIAdvisorAgent` (agent/llm — monorepo outline step 4),
      the only place the LLM appears. It classifies intent, calls tools
      (schedule/SQLite vs. semantic/Chroma per FC33), and summarizes.
    - `sql_db_manager`: `SQLDatabaseManager` — persists every turn (FC34).
    """

    def __init__(self, advisor_agent, sql_db_manager) -> None:
        self._advisor_agent = advisor_agent
        self._sql_db_manager = sql_db_manager

    def send_message(
        self, student_id: str, request: ChatMessageRequest
    ) -> ChatMessageReply:
        """One turn: → `AIAdvisorAgent.process_query` (FC22).

        `request.confirmed_action_id` (FC23) must be present to resume a
        pending action; the agent-side interrupt enforces confirm-before-acting.
        Session continuity and multi-turn clarification state are agent-owned
        (FC27–FC28); every turn is persisted via `sql_db_manager` (FC34).
        """
        raise NotWiredError(
            "Chat is not wired yet: needs AIAdvisorAgent (agent/llm — monorepo outline step 4)."
        )

    def get_history(
        self, student_id: str, session_id: Optional[str] = None
    ) -> ChatHistoryResponse:
        """Persisted advising history (FC34) — read from SQLite, never app memory."""
        raise NotWiredError(
            "Chat history is not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )