"""Diagnostic records and the conditions they report.

Each condition has a code, which callers filter by and which never changes once
released; a name, as a noun phrase; and an outcome, what lenient mode does instead. A
diagnostic's message joins the name and the outcome, and strict mode's error the name
and the position, so both describe one condition, each in its own terms.
"""

from dataclasses import dataclass

from tgmark.model.document import Position
from tgmark.model.server import MESSAGE_LENGTH


@dataclass(frozen=True)
class Condition:
    """A condition in the input that lenient mode repairs or drops.

    Attributes:
        code: The code callers see, such as `control-character`.
        name: The condition as a noun phrase, such as `control character`.
        outcome: What lenient mode does instead, such as `replaced with a space`.
    """

    code: str
    name: str
    outcome: str


@dataclass(frozen=True)
class Notice:
    """One condition found in the input.

    Attributes:
        condition: The condition.
        position: Where it starts in the input.
    """

    condition: Condition
    position: Position


LONE_SURROGATE = Condition(
    code="lone-surrogate",
    name="lone surrogate",
    outcome="replaced with U+FFFD",
)
CONTROL_CHARACTER = Condition(
    code="control-character",
    name="control character",
    outcome="replaced with a space",
)
UNSUPPORTED_CHARACTER = Condition(
    code="unsupported-character",
    name="unsupported character",
    outcome="removed",
)
DIRECTION_MARK = Condition(
    code="direction-mark",
    name="direction mark before another",
    outcome="replaced with U+200C",
)
BLANK_TEXT = Condition(
    code="blank-text",
    name="blank text",
    outcome="not sent",
)
TEXT_TOO_LONG = Condition(
    code="text-too-long",
    name=f"text over {MESSAGE_LENGTH} code points",
    outcome="not sent",
)
