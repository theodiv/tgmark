import pytest

from tgmark.fit.parts import fit_text
from tgmark.model.diagnostics import BLANK_TEXT, TEXT_TOO_LONG, Notice
from tgmark.model.document import Position
from tgmark.model.formatted import FormattedText
from tgmark.model.server import MESSAGE_LENGTH


def _at(text: str) -> FormattedText:
    """Return `text` as one run that starts at line 1, column 1."""
    return FormattedText.at(text, Position(1, 1))


def test_trims_spaces_and_line_feeds_at_both_ends_without_a_notice() -> None:
    parts, notices = fit_text(_at(" \n a b \n "))
    assert parts == (FormattedText.at("a b", Position(1, 4)),)
    assert notices == ()


@pytest.mark.parametrize("text", ["", " \n \n"])
def test_makes_no_message_of_text_that_trims_to_nothing(text: str) -> None:
    assert fit_text(_at(text)) == ((), ())


def test_makes_no_message_of_blank_text() -> None:
    assert fit_text(_at(" \u00a0\u200b\n")) == (
        (),
        (Notice(BLANK_TEXT, Position(1, 2)),),
    )


@pytest.mark.parametrize("unit", ["a", "\N{GRINNING FACE}"])
def test_makes_one_message_of_text_at_the_limit(unit: str) -> None:
    text = unit * MESSAGE_LENGTH
    assert fit_text(_at(text)) == ((_at(text),), ())


def test_makes_no_message_of_text_past_the_limit() -> None:
    assert fit_text(_at(" " + "a" * (MESSAGE_LENGTH + 1))) == (
        (),
        (Notice(TEXT_TOO_LONG, Position(1, MESSAGE_LENGTH + 2)),),
    )
