"""
server.py — MCP server for Copilot image generation.

Exposes tools for generating and refining images via Microsoft Copilot's
backend. Uses FastMCP for the MCP protocol over stdio.
"""

from __future__ import annotations

import sys

from fastmcp import FastMCP

from .auth import get_cached_account, get_token
from .models import ImageGenRequest, Orientation
from .session import ImageGenSession

# ── MCP Server Setup ────────────────────────────────────────────────────────

mcp = FastMCP(
    "Copilot Image Generation",
    instructions=(
        "This server generates images using Microsoft Copilot. "
        "Use 'generate_image' for new images and 'refine_image' to modify "
        "the last generated image. Images are saved to ~/.copilot-images/ "
        "and the file path is returned. Sign in first with 'sign_in' if needed."
    ),
)

# Global session (one per MCP server process = one per CLI session)
_session = ImageGenSession()


def _log(msg: str):
    print(msg, file=sys.stderr, flush=True)


# ── MCP Tools ───────────────────────────────────────────────────────────────

@mcp.tool()
def generate_image(prompt: str, orientation: str = "landscape") -> str:
    """Generate an image from a text prompt.

    Blocks until the image is ready (typically 15-30 seconds).
    The image is saved to ~/.copilot-images/{session}/{NNN}_{slug}.png

    Args:
        prompt: Text description of the image to generate.
        orientation: "landscape", "portrait", or "square" (default: landscape).

    Returns:
        The absolute file path of the saved image, or an error message.
    """
    try:
        orient = Orientation(orientation.lower())
    except ValueError:
        orient = Orientation.LANDSCAPE

    request = ImageGenRequest(
        prompt=prompt,
        orientation=orient,
        conversation_id=_session.state.conversation_id or None,
        is_refinement=False,
    )

    try:
        result = _session.generate_image(request)
        return f"Image saved to: {result.file_path}"
    except ConnectionError as e:
        return f"Connection error: {e}"
    except TimeoutError as e:
        return f"Timeout: {e}"
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        _log(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"


@mcp.tool()
def refine_image(prompt: str) -> str:
    """Refine the last generated image with additional instructions.

    Uses the same conversation context, so the server remembers
    the previous image and applies your changes to it.

    Args:
        prompt: What to change about the current image.

    Returns:
        The absolute file path of the new image, or an error message.
    """
    if not _session.state.conversation_id:
        return (
            "No active image session. Use generate_image first to create "
            "an image, then use refine_image to modify it."
        )

    request = ImageGenRequest(
        prompt=prompt,
        orientation=Orientation.LANDSCAPE,
        conversation_id=_session.state.conversation_id,
        is_refinement=True,
    )

    try:
        result = _session.generate_image(request)
        return f"Refined image saved to: {result.file_path}"
    except ConnectionError as e:
        return f"Connection error: {e}"
    except TimeoutError as e:
        return f"Timeout: {e}"
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        _log(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"


@mcp.tool()
def sign_in() -> str:
    """Sign in to Microsoft 365 for image generation.

    Opens a browser window for authentication. Required once before
    generating images. Credentials are cached for future sessions.

    Returns:
        Sign-in result with account name, or error message.
    """
    token = get_token(silent=False)
    if not token:
        return "Sign-in failed. Please try again."

    account = get_cached_account()
    if account.name:
        return f"Signed in as {account.name} ({account.upn})"
    return "Signed in successfully."


@mcp.tool()
def new_session() -> str:
    """Start a fresh image generation session.

    Discards the current conversation context. Previous images won't be
    available for refinement. New images go to a new session directory.

    Returns:
        Confirmation message.
    """
    _session.new_session()
    return "New session started. Previous conversation context cleared."


# ── Entry Point ─────────────────────────────────────────────────────────────

def main():
    _log("Starting Copilot Image Generation MCP server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
