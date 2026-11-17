"""The document tree the readers build, and positions in the input.

Each node carries the position of its first character, so a diagnostic about any
character in it can name where the input's author wrote that character.
"""

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

    Attributes:
        line: The line, counted from 1.
        column: The column in that line, counted from 1 in code points; an astral
            character takes one column, as it takes one index of a `str`.
    """

    line: int
    column: int


@dataclass(frozen=True)
class Text:
    """A run of characters that stand one for one on one line of the input.

    Attributes:
        value: The characters, holding no line ending.
        position: The position of the first character.
    """

    value: str
    position: Position


@dataclass(frozen=True)
class LineBreak:
    """A line ending of the input.

    Attributes:
        position: The position of the line ending's first character.
    """

    position: Position


Node: TypeAlias = Text | LineBreak


@dataclass(frozen=True)
class Document:
    """The input as a reader reads it.

    Attributes:
        nodes: The text runs and line breaks, in input order.
    """

    nodes: tuple[Node, ...]


def locate(text: str, offsets: Iterable[int]) -> tuple[Position, ...]:
    """Return the position of the character at each of `offsets` in `text`.

    The line starts are found once for all the offsets, and then each offset takes
    one bisection.
    """
    starts = [0, *(match.end() for match in LINE_ENDING.finditer(text))]
    positions = []
    for offset in offsets:
        index = bisect_right(starts, offset) - 1
        positions.append(Position(index + 1, offset - starts[index] + 1))

    return tuple(positions)
