"""Formatted text split into messages that fit, with the edges trimmed."""

import re
import unicodedata
from bisect import bisect_right
from dataclasses import dataclass

from tgmark.fit.graphemes import boundaries
from tgmark.model.diagnostics import BLANK_TEXT, CLUSTER_TOO_LONG, TRUNCATED, Notice
from tgmark.model.formatted import FormattedText
from tgmark.model.server import BLANK, TRIMMED

# A run of the characters the server trims from the edges of a text.
_TRIMMED_RUN = re.compile(f"[{TRIMMED}]+")

# The marks that end a sentence before a space, and the ideographic and fullwidth ones
# that end a sentence with no space after them.
_SENTENCE_ENDS = frozenset(
    ".!?"
    "\N{GREEK QUESTION MARK}\N{ARMENIAN FULL STOP}\N{ARABIC QUESTION MARK}"
    "\N{ARABIC FULL STOP}\N{DEVANAGARI DANDA}\N{DEVANAGARI DOUBLE DANDA}"
    "\N{MYANMAR SIGN SECTION}\N{ETHIOPIC FULL STOP}\N{HORIZONTAL ELLIPSIS}"
    "\N{DOUBLE EXCLAMATION MARK}\N{INTERROBANG}\N{DOUBLE QUESTION MARK}"
    "\N{QUESTION EXCLAMATION MARK}\N{EXCLAMATION QUESTION MARK}"
    "\N{IDEOGRAPHIC FULL STOP}\N{FULLWIDTH EXCLAMATION MARK}"
    "\N{FULLWIDTH FULL STOP}\N{FULLWIDTH QUESTION MARK}"
    "\N{HALFWIDTH IDEOGRAPHIC FULL STOP}"
)
_SPACELESS_END = re.compile(
    "[\N{IDEOGRAPHIC FULL STOP}\N{FULLWIDTH EXCLAMATION MARK}"
    "\N{FULLWIDTH QUESTION MARK}\N{HALFWIDTH IDEOGRAPHIC FULL STOP}]"
)

# The quotation marks that may close a sentence after its last mark, besides closing
# brackets and final quotation marks.
_QUOTES = frozenset("\"'")

# The kinds of places a cut may fall, in order of preference.
_PARAGRAPH, _LINE, _SENTENCE, _WORD = range(4)


@dataclass(frozen=True)
class _Cuts:
    """The places a cut may fall in a text, from the one pass that finds them all."""

    flags: bytes
    ends: tuple[tuple[int, ...], ...]
    starts: tuple[tuple[int, ...], ...]


def fit_text(
    formatted: FormattedText, *, max_length: int, max_parts: int | None
) -> tuple[tuple[FormattedText, ...], tuple[Notice, ...]]:
    """Return the text of each message `formatted` makes, and the notices of changes.

    Each message's text holds at most `max_length` code points, never ends before its
    first character that is not blank, and ends at the best cut that fits. A cut drops
    the spaces and line feeds at it, which the server would trim from the edges of both
    messages anyway. A grapheme cluster longer than `max_length` is cut at the limit,
    with a notice at each such cut. Blank characters share a message with other text,
    which the server requires, so only a run of them longer than `max_length`, or one
    with no other text after it, is dropped. Text past `max_parts` messages is
    dropped too.

    Returns:
        The texts of the messages, and a notice for each cut inside a cluster and for
        each stretch of text dropped.
    """
    text = formatted.text
    end = len(text.rstrip(TRIMMED))
    start = len(text) - len(text.lstrip(TRIMMED))
    cuts = _find_cuts(text) if end - start > max_length else None
    parts: list[FormattedText] = []
    notices: list[Notice] = []
    while start < end:
        if max_parts is not None and len(parts) == max_parts:
            notices.append(Notice(TRUNCATED, formatted.position(start)))
            break

        kept = _first_kept(text, start, end)
        if kept == end:
            notices.append(Notice(BLANK_TEXT, formatted.position(start)))
            break

        limit = start + max_length
        if cuts is None or end <= limit:
            parts.append(formatted.slice(start, end))
            break

        if kept >= limit:
            dropped = _blank_run_end(text, cuts, start, kept, max_length)
            notices.append(Notice(BLANK_TEXT, formatted.position(start)))
            if not cuts.flags[dropped]:
                notices.append(Notice(CLUSTER_TOO_LONG, formatted.position(dropped)))
            start = _skip_trimmed(text, dropped)
            continue

        part_end, next_start, inside = _cut(text, cuts, start, kept, limit)
        if inside:
            notices.append(Notice(CLUSTER_TOO_LONG, formatted.position(limit)))
        parts.append(formatted.slice(start, part_end))
        start = _skip_trimmed(text, next_start)

    return tuple(parts), tuple(notices)


def _find_cuts(text: str) -> _Cuts:
    """Return every place a cut may fall in `text`, in one pass over it.

    A run of spaces and line feeds is a place to cut only where the cluster rule allows
    a cut at both its ends, since the cut drops the run: a space that carries a mark
    stays with the text after it.
    """
    flags = boundaries(text)
    places: tuple[list[tuple[int, int]], ...] = ([], [], [], [])
    for match in _TRIMMED_RUN.finditer(text):
        run_start, run_end = match.span()
        if run_start == 0 or run_end == len(text):
            continue
        if not (flags[run_start] and flags[run_end]):
            continue

        feeds = match.group().count("\n")
        if feeds >= 2:
            kind = _PARAGRAPH
        elif feeds == 1:
            kind = _LINE
        elif _ends_sentence(text, run_start):
            kind = _SENTENCE
        else:
            kind = _WORD
        places[kind].append((run_start, run_end))

    # A sentence end with no space after it makes a cut that drops nothing.
    places[_SENTENCE].extend(
        (offset, offset) for offset in _spaceless_ends(text) if flags[offset]
    )
    places[_SENTENCE].sort()

    return _Cuts(
        flags,
        tuple(tuple(place[0] for place in kind) for kind in places),
        tuple(tuple(place[1] for place in kind) for kind in places),
    )


def _ends_sentence(text: str, offset: int) -> bool:
    """Return whether a sentence ends just before `offset`.

    The last mark of a sentence may be followed by closing brackets and quotation
    marks, as in `(It works!)`.
    """
    index = offset - 1
    while index > 0 and _closes(text[index]):
        index -= 1
    return text[index] in _SENTENCE_ENDS


def _spaceless_ends(text: str) -> list[int]:
    """Return the offset past each ideographic or fullwidth sentence end.

    The offsets leave out a sentence end with a space or a line feed after it, which
    a run already marks, and one at the end of the text.
    """
    offsets = []
    for match in _SPACELESS_END.finditer(text):
        offset = match.end()
        while offset < len(text) and _closes(text[offset]):
            offset += 1
        if offset < len(text) and text[offset] not in TRIMMED:
            offsets.append(offset)
    return offsets


def _closes(char: str) -> bool:
    """Return whether `char` may close a sentence after its last mark."""
    return char in _QUOTES or unicodedata.category(char) in ("Pe", "Pf")


def _cut(
    text: str, cuts: _Cuts, start: int, kept: int, limit: int
) -> tuple[int, int, bool]:
    """Return where the message from `start` ends and where the text after it starts.

    The message takes the last place of the most preferred kind that ends past `kept`
    and at or before `limit`. Without one, it ends at the last offset in that span where
    the cluster rule allows a cut that no space or line feed adjoins, and failing that
    at `limit`, inside a cluster.

    Returns:
        The end of the message, the start of the text after it, and whether the cut
        falls inside a cluster.
    """
    for ends, starts in zip(cuts.ends, cuts.starts, strict=True):
        index = bisect_right(ends, limit) - 1
        if index >= 0 and ends[index] > kept:
            return ends[index], starts[index], False

    for offset in range(limit, kept, -1):
        if (
            cuts.flags[offset]
            and text[offset - 1] not in TRIMMED
            and text[offset] not in TRIMMED
        ):
            return offset, offset, False

    end = limit
    while end > start and text[end - 1] in TRIMMED:
        end -= 1
    return end, limit, True


def _blank_run_end(
    text: str, cuts: _Cuts, start: int, kept: int, max_length: int
) -> int:
    """Return where to end a run of blank characters too long for one message.

    The run from `start` ends at the last offset up to `kept` where the cluster rule
    allows a cut both there and past the spaces and line feeds after it, so the blank
    characters that share a cluster with `kept` start the next message with it. When
    there is no such offset, or the next message could still not reach `kept`, the run
    ends at `kept`, inside its cluster.
    """
    next_start = kept
    for offset in range(kept, start, -1):
        if text[offset] not in TRIMMED:
            next_start = offset
        if kept - next_start >= max_length:
            break
        if cuts.flags[offset] and cuts.flags[next_start]:
            return offset
    return kept


def _first_kept(text: str, start: int, end: int) -> int:
    """Return the offset of the first character from `start` that is not blank.

    Returns:
        The offset, or `end` when every character before it is blank.
    """
    for offset in range(start, end):
        if text[offset] not in BLANK:
            return offset
    return end


def _skip_trimmed(text: str, offset: int) -> int:
    """Return the offset of the first character from `offset` the server keeps."""
    match = _TRIMMED_RUN.match(text, offset)
    return match.end() if match else offset
