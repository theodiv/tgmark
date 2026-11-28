"""Diagnostic records and the conditions they report."""

from dataclasses import dataclass

from tgmark.model.document import Position


@dataclass(frozen=True)
class Condition:
    """A condition in the input that lenient mode repairs or drops."""

    code: str
    name: str
    outcome: str


@dataclass(frozen=True)
class Notice:
    """One condition found in the input."""

    condition: Condition
    position: Position


UNDECODABLE_BYTES = Condition(
    code="undecodable-bytes",
    name="undecodable bytes",
    outcome="replaced with U+FFFD",
)
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
CLUSTER_TOO_LONG = Condition(
    code="cluster-too-long",
    name="grapheme cluster over the length limit",
    outcome="split between messages",
)
TRUNCATED = Condition(
    code="truncated",
    name="text past the message cap",
    outcome="not sent",
)
