"""Telegram Bot API markup converter for HTML, Markdown, and plain text.

Public surface
--------------
- `convert`: converts text into messages that the Bot API server keeps as sent.
- `Conversion`: the messages and the diagnostics of one conversion.
- `Message`: one message's text and its Bot API parameters.
- `Diagnostic`: a condition lenient mode repaired or dropped, and where it starts.
- `TGMarkError`: root of the exception hierarchy.
- `ConversionError`: raised in strict mode for the earliest such condition.
"""

from tgmark.conversion import Conversion, Diagnostic, Message, convert
from tgmark.exceptions import ConversionError, TGMarkError

__version__ = "0.0.0"

__all__ = [
    "Conversion",
    "ConversionError",
    "Diagnostic",
    "Message",
    "TGMarkError",
    "convert",
]
