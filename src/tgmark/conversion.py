"""Conversion of text into Telegram messages: `convert` and the types it returns.

This module alone wires the stages together, `parse`, then `lower`, then `fit`, so no
domain imports another. The domains report each condition they repair or drop as a
foundation record, which this module maps onto `Diagnostic`; in strict mode it raises
for the record at the earliest position instead.
"""

from dataclasses import dataclass
from typing import Any, Literal

from tgmark.exceptions import ConversionError
from tgmark.fit.parts import fit_text
from tgmark.lower.table import lower_document
from tgmark.model.diagnostics import Notice
from tgmark.parse.decoding import replace_surrogates
from tgmark.parse.plain import read_plain

# The values `source` and `target` take.
_SOURCES = ("plain",)
_TARGETS = ("entities",)


@dataclass(frozen=True)
class Diagnostic:
    """A condition in the input that lenient mode repaired or dropped.

    Attributes:
        code: The condition's code, such as `control-character`, which never changes
            once released.
        message: The condition and what lenient mode did instead, in one clause that
            never quotes the input.
        line: The line where the condition starts in the input, counted from 1.
        column: The column in that line, counted from 1 in code points.
    """

    code: str
    message: str
    line: int
    column: int


@dataclass(frozen=True)
class Message:
    """One Telegram message, as the Bot API server keeps it.

    Attributes:
        text: The text of the message.
    """

    text: str

    # The parameters' values differ in type from one name to the next, so `Any` lets
    # them unpack into the keyword arguments of any Bot API client.
    def params(self) -> dict[str, Any]:
        """Return the message's parameters for the Bot API's `sendMessage` method.

        Each call returns a new `dict`, so a caller can add `chat_id` and the other
        parameters of the call to it.
        """
        return {"text": self.text}


@dataclass(frozen=True)
class Conversion:
    """What converting a text produced: its messages and its diagnostics.

    Attributes:
        messages: The messages, in input order; empty when nothing remains to send.
        diagnostics: Each condition lenient mode repaired or dropped, in input order.
    """

    messages: tuple[Message, ...]
    diagnostics: tuple[Diagnostic, ...]


def convert(
    text: str,
    *,
    source: Literal["plain"],
    target: Literal["entities"],
    strict: bool = False,
) -> Conversion:
    """Convert `text` into Telegram messages that the Bot API server keeps as sent.

    Lenient mode repairs or drops what the server would refuse or change and reports
    each repair or drop as a diagnostic; strict mode raises at the earliest instead, for
    a caller that refuses input that would not arrive unchanged. The options are
    keyword-only so that a new option never changes the meaning of an existing call.

    Args:
        text: The text to convert.
        source: The format of `text`: `plain` reads every character as written.
        target: The form of each message: `entities` sends its text with no parse mode.
        strict: Whether to raise `ConversionError` instead of repairing or dropping.

    Raises:
        TypeError: If `text`, `source`, or `target` is not a `str`, or `strict` is not
            a `bool`.
        ValueError: If `source` or `target` names a format other than those above.
        ConversionError: If `strict` is set and lenient mode would repair or
            drop anything.
    """
    _check_arguments(text, source, target, strict)

    valid, decoding = replace_surrogates(text)
    formatted, lowering = lower_document(read_plain(valid))
    parts, fitting = fit_text(formatted)

    notices = sorted((*decoding, *lowering, *fitting), key=lambda n: n.position)
    if strict and notices:
        raise _error(notices[0])

    return Conversion(
        messages=tuple(Message(part.text) for part in parts),
        diagnostics=tuple(_diagnostic(notice) for notice in notices),
    )


def _check_arguments(
    text: object, source: object, target: object, strict: object
) -> None:
    """Raise for an argument of `convert` of the wrong type or value."""
    if not isinstance(text, str):
        raise TypeError(f"text must be str, not {type(text).__name__}")
    _check_choice("source", source, _SOURCES)
    _check_choice("target", target, _TARGETS)
    if not isinstance(strict, bool):
        raise TypeError(f"strict must be bool, not {type(strict).__name__}")


def _check_choice(name: str, value: object, choices: tuple[str, ...]) -> None:
    """Raise unless `value`, the argument called `name`, is one of `choices`."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str, not {type(value).__name__}")
    if value not in choices:
        alternatives = " or ".join(f"'{choice}'" for choice in choices)
        raise ValueError(f"{name} must be {alternatives}")


def _diagnostic(notice: Notice) -> Diagnostic:
    """Return the diagnostic that reports `notice`."""
    condition = notice.condition
    return Diagnostic(
        code=condition.code,
        message=f"{condition.name} {condition.outcome}",
        line=notice.position.line,
        column=notice.position.column,
    )


def _error(notice: Notice) -> ConversionError:
    """Return the error strict mode raises for `notice`."""
    line, column = notice.position.line, notice.position.column
    return ConversionError(
        f"{notice.condition.name} at line {line}, column {column}",
        code=notice.condition.code,
        line=line,
        column=column,
    )
