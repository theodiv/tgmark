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
from tgmark.model.server import MESSAGE_LENGTH
from tgmark.parse.decoding import decode_bytes, replace_surrogates
from tgmark.parse.plain import read_plain

# The values `source` and `target` take.
SOURCES = ("plain",)
TARGETS = ("entities",)


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
    text: str | bytes,
    *,
    source: Literal["plain"],
    target: Literal["entities"],
    max_length: int | None = None,
    max_parts: int | None = None,
    strict: bool = False,
) -> Conversion:
    """Convert `text` into Telegram messages that the Bot API server keeps as sent.

    Lenient mode repairs or drops what the server would refuse or change and reports
    each repair or drop as a diagnostic; strict mode raises at the earliest instead, for
    a caller that refuses input that would not arrive unchanged. Text longer than one
    message splits into several, each ending at the best break that fits. The options
    are keyword-only so that a new option never changes the meaning of an existing call.

    Args:
        text: The text to convert: a `str`, or `bytes` in the encoding their byte order
            mark names, UTF-8, UTF-16BE, or UTF-16LE, else in UTF-8. Diagnostics count
            lines and columns in the decoded text, from just past the mark.
        source: The format of `text`: `plain` reads every character as written.
        target: The form of each message: `entities` sends its text with no parse mode.
        max_length: The most code points the text of each message keeps, from 1 to
            4,096; `None` for 4,096, the server's limit.
        max_parts: The most messages to return, 1 or more; `None` for no cap. The text
            past the last of them is dropped.
        strict: Whether to raise `ConversionError` instead of repairing or dropping.

    Raises:
        TypeError: If `text` is neither a `str` nor `bytes`, `source` or `target` is not
            a `str`, `max_length` or `max_parts` is neither an `int` nor `None`, or
            `strict` is not a `bool`.
        ValueError: If `source` or `target` names a format other than those above, or
            `max_length` or `max_parts` is out of its range.
        ConversionError: If `strict` is set and lenient mode would repair or
            drop anything.
    """
    _check_arguments(text, source, target, max_length, max_parts, strict)

    valid, decoding = (
        decode_bytes(text) if isinstance(text, bytes) else replace_surrogates(text)
    )
    formatted, lowering = lower_document(read_plain(valid))
    parts, fitting = fit_text(
        formatted,
        max_length=MESSAGE_LENGTH if max_length is None else max_length,
        max_parts=max_parts,
    )

    notices = sorted((*decoding, *lowering, *fitting), key=lambda n: n.position)
    if strict and notices:
        raise _error(notices[0])

    return Conversion(
        messages=tuple(Message(part.text) for part in parts),
        diagnostics=tuple(_diagnostic(notice) for notice in notices),
    )


def _check_arguments(
    text: object,
    source: object,
    target: object,
    max_length: object,
    max_parts: object,
    strict: object,
) -> None:
    """Raise for an argument of `convert` of the wrong type or value."""
    if not isinstance(text, (str, bytes)):
        raise TypeError(f"text must be str or bytes, not {type(text).__name__}")
    _check_choice("source", source, SOURCES)
    _check_choice("target", target, TARGETS)
    _check_count("max_length", max_length, MESSAGE_LENGTH)
    _check_count("max_parts", max_parts, None)
    if not isinstance(strict, bool):
        raise TypeError(f"strict must be bool, not {type(strict).__name__}")


def _check_choice(name: str, value: object, choices: tuple[str, ...]) -> None:
    """Raise unless `value`, the argument called `name`, is one of `choices`."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str, not {type(value).__name__}")
    if value not in choices:
        alternatives = " or ".join(f"'{choice}'" for choice in choices)
        raise ValueError(f"{name} must be {alternatives}")


def _check_count(name: str, value: object, highest: int | None) -> None:
    """Raise unless `value`, the argument called `name`, is `None` or a count.

    A count is an `int` from 1 up to `highest`, or with no upper bound when `highest` is
    `None`. A `bool` is refused although it is an `int`, since `True` would read as 1.
    """
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be int or None, not {type(value).__name__}")
    if highest is None and value < 1:
        raise ValueError(f"{name} must be at least 1")
    if highest is not None and not 1 <= value <= highest:
        raise ValueError(f"{name} must be from 1 to {highest}")


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
