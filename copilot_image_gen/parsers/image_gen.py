"""
parsers/image_gen.py — Parser for Copilot image generation responses.

Extracts images from AdaptiveCard payloads delivered via SignalR.
The image data arrives as base64-encoded PNGs embedded in ImageSet
elements within AdaptiveCard body.
"""

from __future__ import annotations

import base64
import re
from typing import Any

from ..models import ImageGenResult, ProgressEvent, SignalRMessage
from .base import ResponseParser


class ImageGenParser(ResponseParser):
    """Parses image generation events from Copilot's SignalR responses."""

    def parse_progress(self, message: SignalRMessage) -> ProgressEvent | None:
        if message.type != 1:
            return None

        args = message.arguments
        if not args:
            return None

        msg_data = args[0] if isinstance(args[0], dict) else {}
        messages = msg_data.get("messages", [])

        for msg in messages:
            msg_type = msg.get("messageType", "")
            if msg_type != "Progress":
                continue

            text = msg.get("text", "")
            content_origin = msg.get("contentOrigin", "")

            progress_list = msg.get("contentGenerationProgressList", [])
            poll_url = ""
            file_token = ""
            if progress_list:
                poll_url = progress_list[0].get("pollUrl", "")
                file_token = progress_list[0].get("fileToken", "")

            return ProgressEvent(
                text=text,
                content_origin=content_origin,
                poll_url=poll_url,
                file_token=file_token,
            )

        return None

    def parse_image(self, message: SignalRMessage) -> ImageGenResult | None:
        if message.type != 1:
            return None

        args = message.arguments
        if not args:
            return None

        msg_data = args[0] if isinstance(args[0], dict) else {}
        messages = msg_data.get("messages", [])

        for msg in messages:
            adaptive_cards = msg.get("adaptiveCards", [])
            for card in adaptive_cards:
                image_data = self._extract_image_from_card(card)
                if image_data:
                    return ImageGenResult(
                        image_data=image_data,
                        content_type="image/png",
                        prompt=msg.get("text", ""),
                        conversation_id=msg_data.get("conversationId", ""),
                    )

        return None

    def _extract_image_from_card(self, card: dict) -> bytes | None:
        """Recursively search an AdaptiveCard for base64 image data."""
        body = card.get("body", [])
        for element in body:
            result = self._search_element_for_image(element)
            if result:
                return result
        return None

    def _search_element_for_image(self, element: dict) -> bytes | None:
        """Search a single AdaptiveCard element (and children) for image data."""
        elem_type = element.get("type", "")

        # ImageSet contains images array
        if elem_type == "ImageSet":
            for img in element.get("images", []):
                data = self._decode_image_url(img.get("url", ""))
                if data:
                    return data

        # Direct Image element
        if elem_type == "Image":
            data = self._decode_image_url(element.get("url", ""))
            if data:
                return data

        # Recurse into containers
        for child_key in ("body", "items", "columns"):
            children = element.get(child_key, [])
            for child in children:
                if isinstance(child, dict):
                    result = self._search_element_for_image(child)
                    if result:
                        return result

        return None

    def _decode_image_url(self, url: str) -> bytes | None:
        """Decode a data URI (data:image/png;base64,...) to raw bytes."""
        if not url or not url.startswith("data:"):
            return None

        match = re.match(r"data:[^;]+;base64,(.+)", url, re.DOTALL)
        if not match:
            return None

        try:
            return base64.b64decode(match.group(1))
        except Exception:
            return None

    def is_completion(self, message: SignalRMessage) -> bool:
        # SignalR type 2 = invocation completion
        if message.type == 2:
            return True

        # Also check for type 3 (error completion)
        if message.type == 3:
            return True

        return False

    def parse_error(self, message: SignalRMessage) -> str | None:
        # Type 3 = error
        if message.type == 3:
            return message.error or "Unknown error"

        # Type 2 with error in result
        if message.type == 2:
            result = message.result
            if result.get("value") != "Success" and result.get("error"):
                return result["error"]

        # Check for error in type 1 messages
        if message.type == 1 and message.arguments:
            msg_data = message.arguments[0] if isinstance(message.arguments[0], dict) else {}
            messages = msg_data.get("messages", [])
            for msg in messages:
                if msg.get("messageType") == "Error":
                    return msg.get("text", "Unknown error")

        return None
