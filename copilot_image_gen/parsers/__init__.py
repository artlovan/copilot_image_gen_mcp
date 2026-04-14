"""
parsers/__init__.py — Response parser package.

Exports the parser interface and concrete implementations.
"""

from .base import ResponseParser
from .image_gen import ImageGenParser

__all__ = ["ResponseParser", "ImageGenParser"]
