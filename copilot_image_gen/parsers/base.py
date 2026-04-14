"""
parsers/base.py — Abstract response parser interface (ISP).

Defines the contract for parsing backend responses. Each parser handles
a specific response format (e.g., image generation events). New formats
can be added without modifying existing parsers (OCP).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import ImageGenResult, ProgressEvent, SignalRMessage


class ResponseParser(ABC):
    """Abstract parser for extracting structured data from backend responses."""

    @abstractmethod
    def parse_progress(self, message: SignalRMessage) -> ProgressEvent | None:
        """Extract a progress event from a message, or None if not a progress message."""

    @abstractmethod
    def parse_image(self, message: SignalRMessage) -> ImageGenResult | None:
        """Extract an image result from a message, or None if not an image message."""

    @abstractmethod
    def is_completion(self, message: SignalRMessage) -> bool:
        """Check if this message signals the end of the generation."""

    @abstractmethod
    def parse_error(self, message: SignalRMessage) -> str | None:
        """Extract an error message, or None if not an error."""
