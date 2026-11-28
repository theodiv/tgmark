"""The server's character rules applied to formatted text, with a notice per change."""

import re
from collections.abc import Iterable

from tgmark.model.diagnostics import (
    CONTROL_CHARACTER,
    DIRECTION_MARK,
    UNSUPPORTED_CHARACTER,
    Notice,
)
from tgmark.model.formatted import FormattedText, join
from tgmark.model.server import DIRECTION_MARKS, MARK_REPLACEMENT, REMOVED, SPACED


def _any_of(characters: Iterable[str]) -> str:
    """Return a character class that matches any of `characters`."""
    return "[" + "".join(f"\\U{ord(char):08x}" for char in sorted(characters)) + "]"


_SPACED = re.compile(_any_of(SPACED))
_REMOVED = re.compile(_any_of(REMOVED))
_MARK_BEFORE_MARK = re.compile(
    f"{_any_of(DIRECTION_MARKS)}(?={_any_of(DIRECTION_MARKS)})"
)


def clean(formatted: FormattedText) -> tuple[FormattedText, tuple[Notice, ...]]:
    """Return `formatted` with the server's character rules applied, and a notice each.

    The rules run in the server's order: control characters become spaces and the
    characters the server removes go, then direction marks change, so two marks that
    only a removed character kept apart are caught as the server catches them.

    Returns:
        The cleaned text, and a notice for each character changed, rule by rule.
    """
    spaced, spacing = _space(formatted)
    kept, removal = _remove(spaced)
    marked, marking = _mark(kept)
    return marked, (*spacing, *removal, *marking)


def _space(formatted: FormattedText) -> tuple[FormattedText, tuple[Notice, ...]]:
    """Return `formatted` with each control character the server spaces made a space."""
    notices = tuple(
        Notice(CONTROL_CHARACTER, formatted.position(match.start()))
        for match in _SPACED.finditer(formatted.text)
    )
    if not notices:
        return formatted, ()

    return FormattedText(_SPACED.sub(" ", formatted.text), formatted.runs), notices


def _remove(formatted: FormattedText) -> tuple[FormattedText, tuple[Notice, ...]]:
    """Return `formatted` without the characters the server removes."""
    starts = [match.start() for match in _REMOVED.finditer(formatted.text)]
    if not starts:
        return formatted, ()

    notices = tuple(
        Notice(UNSUPPORTED_CHARACTER, formatted.position(start)) for start in starts
    )
    # Each piece runs from just past one removed character to the next, so the
    # characters after a removal keep the positions they had.
    bounds = zip(
        [0, *(start + 1 for start in starts)],
        [*starts, len(formatted.text)],
        strict=True,
    )
    return join(formatted.slice(start, end) for start, end in bounds), notices


def _mark(formatted: FormattedText) -> tuple[FormattedText, tuple[Notice, ...]]:
    """Return `formatted` with each direction mark before another made U+200C."""
    notices = tuple(
        Notice(DIRECTION_MARK, formatted.position(match.start()))
        for match in _MARK_BEFORE_MARK.finditer(formatted.text)
    )
    if not notices:
        return formatted, ()

    text = _MARK_BEFORE_MARK.sub(MARK_REPLACEMENT, formatted.text)
    return FormattedText(text, formatted.runs), notices
