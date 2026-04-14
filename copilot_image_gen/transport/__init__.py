"""
transport/base.py — Abstract transport interface (DIP).

Defines the contract that all transport implementations must fulfill.
The session layer depends on this abstraction, not concrete transports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generator

from ..models import SignalRMessage


class TransportBase(ABC):
    """Abstract base class for Copilot backend communication."""

    @abstractmethod
    def connect(
        self,
        oid: str,
        tid: str,
        access_token: str,
        conversation_id: str = "",
        session_id: str = "",
        request_id: str = "",
    ) -> None:
        """Establish connection to the backend.

        Args:
            oid: User object ID from JWT claims.
            tid: Tenant ID from JWT claims.
            access_token: Valid Bearer token for the target resource.
            conversation_id: Existing conversation ID for multi-turn.
            session_id: Session ID for the connection.
            request_id: Request/correlation ID for the connection.

        Raises:
            ConnectionError: If connection cannot be established.
        """

    @abstractmethod
    def send_message(self, payload: dict[str, Any]) -> None:
        """Send a message through the transport.

        Args:
            payload: The message payload to send.

        Raises:
            ConnectionError: If the transport is not connected.
        """

    @abstractmethod
    def receive_messages(self, timeout: float = 90.0) -> Generator[SignalRMessage, None, None]:
        """Yield messages from the backend until completion or timeout.

        Args:
            timeout: Maximum seconds to wait for messages.

        Yields:
            SignalRMessage instances as they arrive.

        Raises:
            TimeoutError: If no completion message within timeout.
            ConnectionError: If the connection drops.
        """

    @abstractmethod
    def close(self) -> None:
        """Close the transport connection. Safe to call multiple times."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the transport is currently connected."""
