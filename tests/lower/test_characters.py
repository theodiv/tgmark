import pytest

from tgmark.lower.characters import clean
from tgmark.model.diagnostics import (
    CONTROL_CHARACTER,
    DIRECTION_MARK,
    UNSUPPORTED_CHARACTER,
    Notice,
)
from tgmark.model.document import Position
from tgmark.model.formatted import FormattedText
from tgmark.model.server import REMOVED, SPACED


def _at(text: str) -> FormattedText:
    """Return `text` as one run that starts at line 1, column 1."""
    return FormattedText.at(text, Position(1, 1))


@pytest.mark.parametrize("character", sorted(SPACED))
def test_turns_each_control_character_into_a_space(character: str) -> None:
    assert clean(_at(f"a{character}b")) == (
        _at("a b"),
        (Notice(CONTROL_CHARACTER, Position(1, 2)),),
    )


@pytest.mark.parametrize("character", sorted(REMOVED))
def test_removes_each_unsupported_character(character: str) -> None:
    formatted, notices = clean(_at(f"a{character}bc{character}"))
    assert formatted.text == "abc"
    assert notices == (
        Notice(UNSUPPORTED_CHARACTER, Position(1, 2)),
        Notice(UNSUPPORTED_CHARACTER, Position(1, 5)),
    )
    # The characters after a removal keep their own positions.
    assert [formatted.position(offset) for offset in range(3)] == [
        Position(1, 1),
        Position(1, 3),
        Position(1, 4),
    ]


def test_removes_a_text_of_unsupported_characters_whole() -> None:
    formatted, notices = clean(_at("\u2028\u2029"))
    assert formatted == FormattedText("", ())
    assert len(notices) == 2


def test_turns_each_direction_mark_but_the_last_of_a_run_into_zwnj() -> None:
    assert clean(_at("a\u200e\u200f\u200eb\u200fc")) == (
        _at("a\u200c\u200c\u200eb\u200fc"),
        (
            Notice(DIRECTION_MARK, Position(1, 2)),
            Notice(DIRECTION_MARK, Position(1, 3)),
        ),
    )


def test_turns_direction_marks_that_a_removed_character_kept_apart() -> None:
    formatted, notices = clean(_at("\u200e\u2028\u200f"))
    assert formatted.text == "\u200c\u200f"
    assert notices == (
        Notice(UNSUPPORTED_CHARACTER, Position(1, 2)),
        Notice(DIRECTION_MARK, Position(1, 1)),
    )


def test_keeps_a_text_the_rules_leave_alone() -> None:
    text = _at("a\n \u200eb\x7f\x85\u00a0\N{GRINNING FACE}")
    assert clean(text) == (text, ())
