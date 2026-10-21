"""Chat controller (FC22–FC24, FC27–FC28, FC34)."""
from typing import Optional

from server.schemas.chat import ChatHistoryResponse, ChatMessageRequest, ChatMessageReply
from server.schemas.students import StudentIdentity
from server.services.chat import ChatService


def send_message(
    student: StudentIdentity, payload: ChatMessageRequest, service: ChatService
) -> ChatMessageReply:
    """Wrap `ChatService.send_message`; confirmed_action_id (FC23) travels through."""
    return service.send_message(student.student_id, payload)


def get_history(
    student: StudentIdentity, session_id: Optional[str], service: ChatService
) -> ChatHistoryResponse:
    """Wrap `ChatService.get_history` (FC34)."""
    return service.get_history(student.student_id, session_id)