"""
transport/signalr_ws.py — SignalR JSON over WebSocket transport.

Implements the TransportBase interface for Microsoft's Copilot backend.
Handles SignalR protocol framing (record separator 0x1e), handshake,
keepalive pings, and message parsing.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
from typing import Any, Generator

import websocket

from ..config import (
    WS_HOST,
    WS_PATH_TEMPLATE,
    REQUIRED_ORIGIN,
    WS_CONNECT_TIMEOUT_SECONDS,
    WS_PING_INTERVAL_SECONDS,
    IMAGE_GEN_TIMEOUT_SECONDS,
    get_ws_url_params,
)
from ..models import SignalRMessage
from . import TransportBase

RECORD_SEPARATOR = "\x1e"


def _log(msg: str):
    print(msg, file=sys.stderr, flush=True)


class SignalRTransport(TransportBase):
    """SignalR JSON protocol over WebSocket for Copilot backend."""

    def __init__(self):
        self._ws: websocket.WebSocket | None = None
        self._connected = False

    def connect(
        self,
        oid: str,
        tid: str,
        access_token: str,
        conversation_id: str = "",
        session_id: str = "",
        request_id: str = "",
    ) -> None:
        params = get_ws_url_params(
            access_token,
            conversation_id=conversation_id,
            session_id=session_id,
            request_id=request_id,
        )
        path = WS_PATH_TEMPLATE.format(oid=oid, tid=tid)
        query = urllib.parse.urlencode(params)
        url = f"wss://{WS_HOST}{path}?{query}"

        self._ws = websocket.WebSocket(enable_multithread=True)

        _log("  Connecting to Copilot backend...")
        self._ws.connect(
            url,
            timeout=WS_CONNECT_TIMEOUT_SECONDS,
            origin=REQUIRED_ORIGIN,
        )

        self._signalr_handshake()
        self._connected = True
        _log("  Connected.")

    def _signalr_handshake(self):
        """Perform the SignalR JSON protocol handshake."""
        handshake = json.dumps({"protocol": "json", "version": 1}) + RECORD_SEPARATOR
        self._ws.send(handshake)

        response = self._ws.recv()
        frames = response.split(RECORD_SEPARATOR)
        for frame in frames:
            frame = frame.strip()
            if not frame:
                continue
            data = json.loads(frame)
            if "error" in data and data["error"]:
                raise ConnectionError(f"SignalR handshake error: {data['error']}")

    def send_message(self, payload: dict[str, Any]) -> None:
        if not self._ws or not self._connected:
            raise ConnectionError("Transport not connected")

        message = json.dumps(payload) + RECORD_SEPARATOR
        self._ws.send(message)

    def receive_messages(self, timeout: float = 0) -> Generator[SignalRMessage, None, None]:
        if not self._ws or not self._connected:
            raise ConnectionError("Transport not connected")

        effective_timeout = timeout if timeout > 0 else IMAGE_GEN_TIMEOUT_SECONDS
        start_time = time.time()
        self._ws.settimeout(effective_timeout)

        while True:
            elapsed = time.time() - start_time
            if elapsed >= effective_timeout:
                raise TimeoutError(
                    f"Image generation timed out after {effective_timeout:.0f}s"
                )

            remaining = effective_timeout - elapsed
            self._ws.settimeout(min(remaining, WS_PING_INTERVAL_SECONDS + 5))

            try:
                raw = self._ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            except websocket.WebSocketConnectionClosedException:
                self._connected = False
                raise ConnectionError("WebSocket connection closed unexpectedly")

            if not raw:
                continue

            frames = raw.split(RECORD_SEPARATOR)
            for frame in frames:
                frame = frame.strip()
                if not frame:
                    continue

                try:
                    data = json.loads(frame)
                except json.JSONDecodeError:
                    continue

                message = self._parse_signalr_message(data)

                # Type 6 = keepalive ping — respond with pong
                if message.type == 6:
                    self._send_pong()
                    continue

                yield message

                # Type 2 or 3 = completion
                if message.type in (2, 3):
                    return

    def _send_pong(self):
        """Respond to a SignalR keepalive ping."""
        try:
            pong = json.dumps({"type": 6}) + RECORD_SEPARATOR
            self._ws.send(pong)
        except Exception:
            pass

    def _parse_signalr_message(self, data: dict) -> SignalRMessage:
        """Parse a raw JSON dict into a SignalRMessage."""
        return SignalRMessage(
            type=data.get("type", 0),
            target=data.get("target", ""),
            arguments=data.get("arguments", []),
            result=data.get("result", {}),
            error=data.get("error"),
            raw=data,
        )

    def close(self) -> None:
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected
