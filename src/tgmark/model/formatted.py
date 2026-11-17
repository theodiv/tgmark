"""Telegram's formatted text, with each run of it mapped back to the input.

The later stages report diagnostics, such as text dropped past a limit, that name an
input position, so the text carries its positions along. One position per run rather
than per character keeps the cost to the number of runs: one for each line, and one more
for each character removed from it.
"""

from bisect import bisect_left, bisect_right
from collections.abc import Iterable
from dataclasses import dataclass

from tgmark.model.document import Position


@dataclass(frozen=True)
class Run:
    """A stretch of formatted text whose characters stand one for one in the input.

    The characters of a run sit on one line of the input at consecutive columns, so the
    position of each follows from the run's own.

    Attributes:
        start: Where the run starts in the text.
        position: The input position of the run's first character.
    """

    start: int
    position: Position


def _run_start(run: Run) -> int:
    """Return where `run` starts, the key its text's runs are ordered by."""
    return run.start


@dataclass(frozen=True)
class FormattedText:
    """Text bound for a message, with the runs that map it back to the input.

    Attributes:
        text: The text.
        runs: The runs, in order of `start`; the first starts at 0, and an empty text
            has none.
    """

    text: str
    runs: tuple[Run, ...]

    @classmethod
    def at(cls, text: str, position: Position) -> "FormattedText":
        """Return `text` as one run, its first character standing at `position`."""
        return cls(text, (Run(0, position),) if text else ())

    def position(self, offset: int) -> Position:
        """Return the input position of the character at `offset`."""
        run = self.runs[bisect_right(self.runs, offset, key=_run_start) - 1]
        return Position(run.position.line, run.position.column + offset - run.start)

    def slice(self, start: int, end: int) -> "FormattedText":
        """Return the text from `start` up to `end`, with the runs that map it."""
        if start >= end:
            return FormattedText("", ())

        first = bisect_right(self.runs, start, key=_run_start)
        last = bisect_left(self.runs, end, key=_run_start)
        runs = (
            Run(0, self.position(start)),
            *(Run(run.start - start, run.position) for run in self.runs[first:last]),
        )
        return FormattedText(self.text[start:end], runs)


def join(parts: Iterable[FormattedText]) -> FormattedText:
    """Return `parts` as one text, each part's runs moved past the parts before it."""
    texts: list[str] = []
    runs: list[Run] = []
    length = 0
    for part in parts:
        texts.append(part.text)
        runs.extend(Run(run.start + length, run.position) for run in part.runs)
        length += len(part.text)

    return FormattedText("".join(texts), tuple(runs))
