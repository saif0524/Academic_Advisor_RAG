"""DatabaseManager ABC (§4 of the domain model)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DatabaseManager(ABC):
    """Base contract: connect/disconnect lifecycle + a generic escape hatch."""

    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string
        self.is_connected: bool = False

    @abstractmethod
    def connect(self) -> bool:
        """Open the store; idempotent. Returns True when connected."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the store; idempotent."""

    @abstractmethod
    def execute_query(self, query: Any, params: Any = None) -> Any:
        """Backend-generic query execution for callers with explicit needs."""