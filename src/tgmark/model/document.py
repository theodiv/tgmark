"""The document tree the readers build, and positions in the input."""

import re
from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TypeAlias

# A line ends at a line feed, a carriage return, or a carriage return and a line feed.
LINE_ENDING = re.compile(r"\r\n?|\n")


@dataclass(frozen=True, order=True)
class Position:
    """A place in the input: a line and a column.

    Positions order as the text runs, line first, so sorting diagnostics by position
    puts them in input order.
    """

    line: int
    column: int


@dataclass(frozen=True)
class Text:
    """A run of characters that stand one for one on one line of the input."""

    value: str
    position: Position


@dataclass(frozen=True)
class LineBreak:
    """A line ending of the input."""

    position: Position


Node: TypeAlias = Text | LineBreak


@dataclass(frozen=True)
class Document:
    """The input as a reader reads it."""

    nodes: tuple[Node, ...]


def locate(text: str, offsets: Iterable[int]) -> tuple[Position, ...]:
    """Return the position of the character at each of `offsets` in `text`.

    Each call scans `text` once, however many offsets it takes.
    """
    starts = [0, *(match.end() for match in LINE_ENDING.finditer(text))]
    positions = []
    for offset in offsets:
        index = bisect_right(starts, offset) - 1
        positions.append(Position(index + 1, offset - starts[index] + 1))

    return tuple(positions)
