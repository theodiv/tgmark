import re
from typing import Any

import pytest

from tests.oracle.telegram import check_message
from tgmark import Conversion, ConversionError, Diagnostic, Message, convert
from tgmark.model.server import BLANK, MESSAGE_LENGTH, REMOVED, SPACED, TRIMMED


def _convert(text: str, *, strict: bool = False) -> Conversion:
    """Convert plain `text`, passing each message through the checker."""
    conversion = convert(text, source="plain", target="entities", strict=strict)
    for message in conversion.messages:
        check_message(message.params())
    return conversion


def _sent(text: str) -> Conversion:
    """Return the conversion that sends `text` as one message and reports nothing."""
    return Conversion((Message(text),), ())


def _kept_chunks() -> list[object]:
    """Return each code point the rules leave alone, in chunks that fit a message."""
    changed = SPACED | REMOVED
    characters = [
        chr(code)
        for code in range(0x10000)
        if not 0xD800 <= code <= 0xDFFF and chr(code) not in changed
    ]
    # Every 997th astral code point, and the tag characters, which count as blank.
    characters += map(chr, range(0x10000, 0x110000, 997))
    characters += map(chr, range(0xE0000, 0xE0080))

    # A letter goes before and after each code point, so a chunk takes twice its length
    # and one more.
    size = MESSAGE_LENGTH // 2 - 1
    return [
        pytest.param(
            "".join(characters[i : i + size]), id=f"U+{ord(characters[i]):04X}"
        )
        for i in range(0, len(characters), size)
    ]


def test_converts_plain_text_into_one_message() -> None:
    text = "Build #42 passed\n\nAll 1,024 tests ran in 3.2 s."
    assert _convert(f"{text}\n") == _sent(text)


def test_params_returns_a_new_dict_on_each_call() -> None:
    message = _convert("Total: 42").messages[0]
    params = message.params()
    params["chat_id"] = 1
    assert message.params() == {"text": "Total: 42"}


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        pytest.param("a\r\nb\rc\nd", "a\nb\nc\nd", id="line-endings"),
        pytest.param("\n\n  a  b \n\n", "a  b", id="ends"),
    ],
)
def test_changes_only_line_endings_and_the_ends(text: str, kept: str) -> None:
    assert _convert(text) == _sent(kept)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("if a < b && c > d: print('&amp; <b>')", id="markup"),
        pytest.param(
            "e\u0301 \N{WOMAN}\u200d\N{PERSONAL COMPUTER} \U0001f1ec\U0001f1f7"
            " \N{THUMBS UP SIGN}\U0001f3fd",
            id="clusters",
        ),
        pytest.param("\u200e\u202fa\u200b\u00a0", id="blank-at-the-ends"),
    ],
)
def test_keeps_text_the_rules_leave_alone(text: str) -> None:
    assert _convert(text) == _sent(text)


@pytest.mark.parametrize("characters", _kept_chunks())
def test_keeps_every_code_point_the_rules_leave_alone(characters: str) -> None:
    # The letters keep two direction marks from meeting and a space or a line feed from
    # reaching an end.
    text = "a" + "a".join(characters) + "a"
    assert _convert(text) == _sent(text)


@pytest.mark.parametrize("character", sorted(SPACED))
def test_turns_each_control_character_into_a_space(character: str) -> None:
    diagnostic = Diagnostic(
        "control-character", "control character replaced with a space", 1, 2
    )
    assert _convert(f"a{character}b") == Conversion((Message("a b"),), (diagnostic,))


@pytest.mark.parametrize("character", sorted(REMOVED - {"\r"}))
def test_removes_each_unsupported_character(character: str) -> None:
    diagnostic = Diagnostic(
        "unsupported-character", "unsupported character removed", 1, 2
    )
    assert _convert(f"a{character}b") == Conversion((Message("ab"),), (diagnostic,))


@pytest.mark.parametrize("character", sorted(SPACED | (REMOVED - {"\r"})))
def test_reports_a_changed_character_at_either_end(character: str) -> None:
    conversion = _convert(f"{character}a{character}")
    assert conversion.messages == (Message("a"),)
    assert [(d.line, d.column) for d in conversion.diagnostics] == [(1, 1), (1, 3)]


def test_turns_a_direction_mark_before_another_into_zwnj() -> None:
    diagnostic = Diagnostic(
        "direction-mark", "direction mark before another replaced with U+200C", 1, 2
    )
    assert _convert("a\u200e\u200fb") == Conversion(
        (Message("a\u200c\u200fb"),), (diagnostic,)
    )


def test_replaces_a_lone_surrogate() -> None:
    diagnostic = Diagnostic(
        "lone-surrogate", "lone surrogate replaced with U+FFFD", 2, 1
    )
    assert _convert(f"a\n{chr(0xDC00)}b") == Conversion(
        (Message("a\n\ufffdb"),), (diagnostic,)
    )


@pytest.mark.parametrize("character", sorted(BLANK - set(TRIMMED)))
def test_sends_no_message_of_blank_text(character: str) -> None:
    diagnostic = Diagnostic("blank-text", "blank text not sent", 2, 2)
    assert _convert(f"\n {character} \n") == Conversion((), (diagnostic,))


@pytest.mark.parametrize("text", ["", " ", "\r", "\n\r\n \n"])
def test_sends_and_reports_nothing_of_spaces_and_line_endings(text: str) -> None:
    assert _convert(text) == Conversion((), ())


def test_sends_no_message_of_text_whose_characters_all_go() -> None:
    conversion = _convert("\u2028\t")
    assert conversion.messages == ()
    assert [diagnostic.code for diagnostic in conversion.diagnostics] == [
        "unsupported-character",
        "control-character",
    ]


@pytest.mark.parametrize(
    ("unit", "count"),
    [
        pytest.param("a", MESSAGE_LENGTH, id="ascii"),
        pytest.param("\N{GRINNING FACE}", MESSAGE_LENGTH, id="astral"),
        pytest.param("e\u0301", MESSAGE_LENGTH // 2, id="combining"),
    ],
)
def test_sends_text_at_the_limit_in_one_message(unit: str, count: int) -> None:
    text = unit * count
    assert _convert(f"\n {text} \n") == _sent(text)


def test_counts_the_length_after_removals() -> None:
    text = "a" * MESSAGE_LENGTH
    conversion = _convert(f"{text[:10]}\u2028{text[10:]}")
    assert conversion.messages == (Message(text),)


@pytest.mark.parametrize("length", [MESSAGE_LENGTH + 1, 25 * MESSAGE_LENGTH])
def test_sends_no_message_of_text_past_the_limit(length: int) -> None:
    # The first code point past the limit, offset 4096, stands at line 41, column 97 of
    # lines of 99 letters.
    lines, rest = divmod(length, 100)
    text = ("a" * 99 + "\n") * lines + "a" * rest
    diagnostic = Diagnostic(
        "text-too-long", "text over 4096 code points not sent", 41, 97
    )
    assert _convert(text) == Conversion((), (diagnostic,))


def test_strict_mode_returns_the_conversion_when_nothing_changes() -> None:
    assert _convert("Total: 42\n", strict=True) == _sent("Total: 42")


def test_strict_mode_raises_for_the_earliest_condition() -> None:
    # Decoding finds the surrogate first, but the control character stands earlier in
    # the input.
    text = f"ab\tc\n{chr(0xD800)}"
    match = r"^control character at line 1, column 3$"
    with pytest.raises(ConversionError, match=match) as caught:
        _convert(text, strict=True)
    error = caught.value
    assert (error.code, error.line, error.column) == ("control-character", 1, 3)


def test_strict_mode_raises_for_text_lenient_mode_drops() -> None:
    with pytest.raises(ConversionError, match=r"^blank text at line 1, column 1$"):
        _convert("\u3000", strict=True)


@pytest.mark.parametrize(
    ("arguments", "error", "message"),
    [
        pytest.param(
            {"text": b"a"}, TypeError, "text must be str, not bytes", id="text-type"
        ),
        pytest.param(
            {"source": None},
            TypeError,
            "source must be str, not NoneType",
            id="source-type",
        ),
        pytest.param(
            {"source": "html"}, ValueError, "source must be 'plain'", id="source-value"
        ),
        pytest.param(
            {"target": 1}, TypeError, "target must be str, not int", id="target-type"
        ),
        pytest.param(
            {"target": "html"},
            ValueError,
            "target must be 'entities'",
            id="target-value",
        ),
        pytest.param(
            {"strict": 1}, TypeError, "strict must be bool, not int", id="strict-type"
        ),
    ],
)
def test_refuses_an_argument_of_the_wrong_type_or_value(
    arguments: dict[str, object], error: type[Exception], message: str
) -> None:
    # Any lets the call pass each value the signature refuses.
    call: dict[str, Any] = {
        "text": "a",
        "source": "plain",
        "target": "entities",
        **arguments,
    }
    with pytest.raises(error, match=f"^{re.escape(message)}$"):
        convert(**call)
