"""Formatted text fitted into messages: the edges trimmed, blank text dropped.

The edges lose their spaces and line feeds, as the server trims them, so the length held
to the limit is the length the server counts. Text over the limit is not sent, since no
message may pass it.
"""

from tgmark.model.diagnostics import BLANK_TEXT, TEXT_TOO_LONG, Notice
from tgmark.model.formatted import FormattedText
from tgmark.model.server import BLANK, MESSAGE_LENGTH, TRIMMED


def fit_text(
    formatted: FormattedText,
) -> tuple[tuple[FormattedText, ...], tuple[Notice, ...]]:
    """Return the text of each message `formatted` makes, and a notice of text dropped.

    Text that trims to nothing makes no message and no notice, since only spaces and
    line feeds go. Text of blank characters alone makes no message either, since the
    server refuses it, and text over the limit makes none.

    Returns:
        The texts of the messages, and a notice for any text dropped.
    """
    text = formatted.text
    start = len(text) - len(text.lstrip(TRIMMED))
    end = len(text.rstrip(TRIMMED))
    if start >= end:
        return (), ()

    part = formatted.slice(start, end)
    if all(character in BLANK for character in part.text):
        return (), (Notice(BLANK_TEXT, part.position(0)),)
    if len(part.text) > MESSAGE_LENGTH:
        return (), (Notice(TEXT_TOO_LONG, part.position(MESSAGE_LENGTH)),)

    return (part,), ()
