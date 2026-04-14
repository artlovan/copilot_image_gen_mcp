"""
models.py — Data classes for the image generation MCP server.

Pure data structures with no behavior. Used across all modules for
type-safe message passing.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Orientation(Enum):
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    SQUARE = "square"


class GenerationStatus(Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    GENERATING = "generating"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ImageGenRequest:
    """A request to generate or refine an image."""
    prompt: str
    orientation: Orientation = Orientation.LANDSCAPE
    conversation_id: str | None = None
    is_refinement: bool = False


@dataclass
class ImageGenResult:
    """The result of an image generation request."""
    image_data: bytes
    content_type: str = "image/png"
    file_path: str | None = None
    prompt: str = ""
    conversation_id: str = ""


@dataclass
class ProgressEvent:
    """A progress update during image generation."""
    text: str
    content_origin: str = ""
    poll_url: str = ""
    file_token: str = ""


@dataclass
class SignalRMessage:
    """A parsed SignalR protocol message."""
    type: int
    target: str = ""
    arguments: list[Any] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    """Tracks the state of an image generation conversation."""
    conversation_id: str = ""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    turn_count: int = 0
    status: GenerationStatus = GenerationStatus.IDLE
    last_image_path: str | None = None
    last_prompt: str = ""
    is_start_of_session: bool = True
    created_at: float = field(default_factory=time.time)


@dataclass
class AccountInfo:
    """Cached user account information from JWT claims."""
    name: str = ""
    upn: str = ""
    oid: str = ""
    tid: str = ""

    def is_empty(self) -> bool:
        return not self.oid
