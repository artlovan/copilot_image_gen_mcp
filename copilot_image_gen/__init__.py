"""Copilot Image Generation MCP Server."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("copilot-image-gen-mcp")
except PackageNotFoundError:
    __version__ = "dev"
