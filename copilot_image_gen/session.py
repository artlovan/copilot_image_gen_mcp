"""
session.py — Image generation session orchestrator.

Manages conversation state, coordinates transport and parser,
handles multi-turn image generation (same ConversationId across turns,
new WebSocket connection per turn).
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from typing import Any

from .auth import decode_jwt, get_cached_account, get_token
from .config import (
    ALLOWED_MESSAGE_TYPES,
    BASE_OPTIONS_SETS,
    CLIENT_INFO,
    IMAGE_GEN_OPTIONS_SETS,
    IMAGE_GEN_TIMEOUT_SECONDS,
)
from .models import (
    AccountInfo,
    ConversationState,
    GenerationStatus,
    ImageGenRequest,
    ImageGenResult,
    Orientation,
    ProgressEvent,
)
from .parsers.image_gen import ImageGenParser
from .storage import ImageStorage
from .transport import TransportBase
from .transport.signalr_ws import SignalRTransport


def _log(msg: str):
    if sys.stderr is None:
        return
    try:
        print(msg, file=sys.stderr, flush=True)
    except (OSError, UnicodeError, ValueError):
        # Runtime diagnostics must never fail image generation.
        pass


class ImageGenSession:
    """Orchestrates image generation across multiple turns."""

    def __init__(
        self,
        transport: TransportBase | None = None,
        parser: ImageGenParser | None = None,
        storage: ImageStorage | None = None,
    ):
        self._transport = transport or SignalRTransport()
        self._parser = parser or ImageGenParser()
        self._storage = storage or ImageStorage()
        self._state = ConversationState()
        self._account: AccountInfo | None = None

    @property
    def state(self) -> ConversationState:
        return self._state

    @property
    def account(self) -> AccountInfo | None:
        return self._account

    def generate_image(self, request: ImageGenRequest) -> ImageGenResult:
        """Generate an image. Blocks until complete.

        For refinements, reuses the existing ConversationId so the backend
        has context of previous images.

        Args:
            request: The image generation request.

        Returns:
            ImageGenResult with image data and file path.

        Raises:
            ConnectionError: If auth or connection fails.
            TimeoutError: If image generation times out.
            RuntimeError: If the backend returns an error.
        """
        self._state.status = GenerationStatus.CONNECTING

        # Get auth token
        token = get_token(silent=True)
        if not token:
            self._state.status = GenerationStatus.ERROR
            raise ConnectionError(
                "Not signed in. Use the sign_in tool first."
            )

        # Extract user info from token
        claims = decode_jwt(token)
        oid = claims.get("oid", "")
        tid = claims.get("tid", "")
        if not oid or not tid:
            self._state.status = GenerationStatus.ERROR
            raise ConnectionError("Token missing oid/tid claims")

        self._account = AccountInfo(
            name=claims.get("name", ""),
            upn=claims.get("upn", ""),
            oid=oid,
            tid=tid,
        )

        # Each turn gets a fresh WebSocket connection
        try:
            self._transport.close()
        except Exception:
            pass

        # Generate IDs for this turn
        request_id = str(uuid.uuid4())
        conversation_id = self._state.conversation_id

        self._transport = SignalRTransport()
        self._transport.connect(
            oid, tid, token,
            conversation_id=conversation_id,
            session_id=self._state.session_id,
            request_id=request_id,
        )

        # Build and send the chat message
        self._state.status = GenerationStatus.GENERATING
        chat_payload = self._build_chat_payload(request, request_id)
        self._transport.send_message(chat_payload)

        # Collect responses
        image_result = None
        error_msg = None

        _log(f"  Generating image for: {request.prompt[:60]}...")

        for message in self._transport.receive_messages():
            # Check for errors first
            err = self._parser.parse_error(message)
            if err:
                error_msg = err
                if self._parser.is_completion(message):
                    break
                continue

            # Check for image BEFORE progress — a single message can contain both
            img = self._parser.parse_image(message)
            if img:
                image_result = img

            # Check for progress (informational only, don't skip image check)
            progress = self._parser.parse_progress(message)
            if progress and progress.text and not img:
                _log(f"  Progress: {progress.text[:80]}")

            # Extract conversation ID from completion messages
            if self._parser.is_completion(message):
                item = message.raw.get("item", {})
                conv_id = item.get("conversationId", "")
                if conv_id:
                    self._state.conversation_id = conv_id
                    if image_result:
                        image_result.conversation_id = conv_id
                break

        # Close transport for this turn
        self._transport.close()

        # Handle results
        if error_msg and not image_result:
            self._state.status = GenerationStatus.ERROR
            raise RuntimeError(f"Image generation failed: {error_msg}")

        if not image_result:
            self._state.status = GenerationStatus.ERROR
            raise RuntimeError("No image received from backend")

        # Save the image
        file_path = self._storage.save_image(
            image_data=image_result.image_data,
            prompt=request.prompt,
            conversation_id=image_result.conversation_id or self._state.conversation_id,
        )
        image_result.file_path = str(file_path)

        # Update state
        if image_result.conversation_id:
            self._state.conversation_id = image_result.conversation_id
        self._state.turn_count += 1
        self._state.last_image_path = str(file_path)
        self._state.last_prompt = request.prompt
        self._state.is_start_of_session = False
        self._state.status = GenerationStatus.COMPLETE

        _log(f"  ✅ Image saved: {file_path}")
        return image_result

    def new_session(self):
        """Reset for a new conversation. Next generate_image starts fresh."""
        try:
            self._transport.close()
        except Exception:
            pass
        self._state = ConversationState()
        self._storage.reset()

    def _build_chat_payload(self, request: ImageGenRequest, request_id: str) -> dict[str, Any]:
        """Build the SignalR chat invocation payload."""
        session_id = self._state.session_id

        options_sets = BASE_OPTIONS_SETS + IMAGE_GEN_OPTIONS_SETS

        message = {
            "author": "user",
            "inputMethod": "Keyboard",
            "text": request.prompt,
            "messageType": "Chat",
            "requestId": request_id,
            "experienceType": "Default",
            "locale": "en-us",
            "entityAnnotationTypes": [
                "People", "File", "Event", "External",
                "ExternalMessageExtension", "Email", "TeamsMessage",
            ],
            "locationInfo": {
                "timeZoneOffset": -4,
                "timeZone": "America/New_York",
            },
            "adaptiveCards": [],
            "clientPreferences": {},
        }

        return {
            "type": 4,
            "invocationId": str(self._state.turn_count),
            "target": "chat",
            "arguments": [
                {
                    "source": "officeweb",
                    "optionsSets": options_sets,
                    "allowedMessageTypes": ALLOWED_MESSAGE_TYPES,
                    "isStartOfSession": self._state.is_start_of_session,
                    "sessionId": session_id,
                    "clientCorrelationId": request_id,
                    "traceId": request_id,
                    "message": message,
                    "clientInfo": CLIENT_INFO,
                    "plugins": [{"Id": "BingWebSearch", "Source": "BuiltIn"}],
                    "tone": "Magic",
                    "disconnectBehavior": "continue",
                    "streamingMode": "ConciseWithPadding",
                    "isSbsSupported": True,
                    "renderReferencesBehindEOS": True,
                    "spokenTextMode": "None",
                    "extraExtensionParameters": {},
                    "options": {},
                    "sliceIds": [],
                    "threadLevelGptId": {},
                    "previousMessages": [],
                }
            ],
        }

    def _new_conversation_id(self) -> str:
        """Generate a conversation ID matching the backend's format."""
        return f"51D|BingProdChatHub|{uuid.uuid4().hex[:32]}"
