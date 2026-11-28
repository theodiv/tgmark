"""Telegram Bot API markup converter for HTML, Markdown, and plain text."""

from tgmark.conversion import Conversion, Diagnostic, Message, convert
from tgmark.exceptions import ConversionError, TGMarkError

__version__ = "0.1.0"

__all__ = [
    "Conversion",
    "ConversionError",
    "Diagnostic",
    "Message",
    "TGMarkError",
    "convert",
]
