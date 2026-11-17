import re

import pytest

from tests.oracle.telegram import check_message
from tgmark.model.server import (
    BLANK,
    DIRECTION_MARKS,
    MARK_REPLACEMENT,
    MESSAGE_LENGTH,
    REMOVED,
    SPACED,
    TRIMMED,
)


def _changed(sent: str, kept: str) -> str:
    """Return the pattern of the checker's failure when the server keeps `kept`."""
    start = next(
        (index for index, (s, k) in enumerate(zip(sent, kept, strict=False)) if s != k),
        min(len(sent), len(kept)),
    )
    difference = f"sent {sent[start:]!r}, kept {kept[start:]!r}"
    return re.escape(f"from code point {start}: {difference}")


@pytest.mark.parametrize("character", sorted(SPACED))
def test_server_turns_each_spaced_character_into_a_space(character: str) -> None:
    sent = f"a{character}b"
    with pytest.raises(AssertionError, match=_changed(sent, "a b")):
        check_message({"text": sent})


@pytest.mark.parametrize("character", sorted(REMOVED))
def test_server_removes_each_removed_character(character: str) -> None:
    sent = f"a{character}b"
    with pytest.raises(AssertionError, match=_changed(sent, "ab")):
        check_message({"text": sent})


@pytest.mark.parametrize("first", sorted(DIRECTION_MARKS))
@pytest.mark.parametrize("second", sorted(DIRECTION_MARKS))
def test_server_replaces_a_direction_mark_that_another_follows(
    first: str, second: str
) -> None:
    sent = f"a{first}{second}b"
    kept = f"a{MARK_REPLACEMENT}{second}b"
    with pytest.raises(AssertionError, match=_changed(sent, kept)):
        check_message({"text": sent})


@pytest.mark.parametrize("mark", sorted(DIRECTION_MARKS))
def test_server_keeps_a_direction_mark_that_no_other_follows(mark: str) -> None:
    check_message({"text": f"a{mark}b{mark}"})


@pytest.mark.parametrize("character", sorted(TRIMMED))
def test_server_trims_each_trimmed_character_from_both_ends(character: str) -> None:
    sent = f"{character}a{character}"
    with pytest.raises(AssertionError, match=_changed(sent, "a")):
        check_message({"text": sent})


@pytest.mark.parametrize("character", sorted(BLANK - set(TRIMMED)))
def test_server_keeps_other_blank_characters_at_the_ends(character: str) -> None:
    check_message({"text": f"{character}a{character}"})


@pytest.mark.parametrize("character", sorted(BLANK - set(TRIMMED)))
def test_server_refuses_a_text_of_blank_characters(character: str) -> None:
    with pytest.raises(AssertionError, match="text must be non-empty"):
        check_message({"text": character * 2})


# The characters on each side of a blank character or range are not blank.
@pytest.mark.parametrize(
    "character",
    [
        "\u009f",
        "\u00a1",
        "\u167f",
        "\u1681",
        "\u180d",
        "\u180f",
        "\u1fff",
        "\u2010",
        "\u2030",
        "\u205e",
        "\u2060",
        "\u27ff",
        "\u2801",
        "\u2fff",
        "\u3001",
        "\ufefe",
        "\uff00",
        "\ufffb",
        "\ufffd",
        "\U000dffff",
        "\U000e0080",
    ],
)
def test_server_keeps_a_text_of_a_character_that_is_not_blank(character: str) -> None:
    check_message({"text": character})


def test_server_keeps_a_text_of_message_length() -> None:
    check_message({"text": "a" * MESSAGE_LENGTH})


def test_server_refuses_a_text_one_code_point_over_message_length() -> None:
    with pytest.raises(AssertionError, match="message is too long"):
        check_message({"text": "a" * (MESSAGE_LENGTH + 1)})
