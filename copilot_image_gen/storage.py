"""
storage.py — Cross-platform image storage for the image generation MCP server.

Handles all file I/O and path management. Uses pathlib.Path throughout for
macOS + Windows compatibility. Creates directories lazily on first image save.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path

from .config import get_images_dir


def _slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug[:max_length].rstrip("_")


class ImageStorage:
    """Manages session-scoped image directories and file persistence."""

    def __init__(self, base_dir: Path | None = None):
        self._base_dir = base_dir or get_images_dir()
        self._session_dir: Path | None = None
        self._session_meta: dict = {}
        self._image_count: int = 0

    @property
    def session_dir(self) -> Path | None:
        return self._session_dir

    def _ensure_session_dir(self, first_prompt: str) -> Path:
        """Create the session directory on first image save."""
        if self._session_dir is not None:
            return self._session_dir

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slugify(first_prompt)
        dir_name = f"{timestamp}_{slug}" if slug else timestamp

        self._session_dir = self._base_dir / dir_name
        self._session_dir.mkdir(parents=True, exist_ok=True)

        self._session_meta = {
            "created_at": datetime.now().isoformat(),
            "images": [],
        }
        return self._session_dir

    def save_image(
        self,
        image_data: bytes,
        prompt: str,
        conversation_id: str = "",
        extension: str = ".png",
    ) -> Path:
        """Save an image to the session directory. Returns the absolute file path."""
        session_dir = self._ensure_session_dir(prompt)

        self._image_count += 1
        slug = _slugify(prompt, max_length=40)
        filename = f"{self._image_count:03d}_{slug}{extension}" if slug else f"{self._image_count:03d}_image{extension}"

        file_path = session_dir / filename
        file_path.write_bytes(image_data)

        self._session_meta.setdefault("conversation_id", conversation_id)
        self._session_meta["images"].append({
            "file": filename,
            "prompt": prompt,
            "created_at": datetime.now().isoformat(),
        })
        self._write_session_json()

        return file_path

    def _write_session_json(self):
        """Write session metadata to session.json."""
        if self._session_dir is None:
            return
        meta_path = self._session_dir / "session.json"
        meta_path.write_text(json.dumps(self._session_meta, indent=2))

    def reset(self):
        """Reset for a new session (new directory on next save)."""
        self._session_dir = None
        self._session_meta = {}
        self._image_count = 0
