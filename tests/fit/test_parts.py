import unicodedata

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.support.segmentation import Unicode
from tgmark.fit.parts import fit_text
from tgmark.model.diagnostics import BLANK_TEXT, CLUSTER_TOO_LONG, TRUNCATED, Notice
from tgmark.model.document import Position
from tgmark.model.formatted import FormattedText, Run
from tgmark.model.server import BLANK, MESSAGE_LENGTH, TRIMMED

# The pieces generated texts are made of: words, every kind of place to cut, clusters of
# every kind the cut rule tells apart, and blank characters.
_PIECES = (
    "a",
    "Total",
    "42",
    " ",
    "  ",
    "\n",
    "\n\n",
    " \n ",
    ".",
    "!",
    "?",
    ")",
    '"',
    "\u2026",
    "\u3002",
    "\u6f22\u5b57",
    "e\u0301",
    "\u0308",
    "\N{WOMAN}\u200d\N{PERSONAL COMPUTER}",
    "\N{THUMBS UP SIGN}\U0001f3fd",
    "\U0001f1ec\U0001f1f7",
    "\U0001f1ec",
    "\u1100\u1161\u11a8",
    "\uac00",
    "\u0915\u094d\u0937",
    "\u0915\u094d\u200d\u0937",
    "\u0e01\u0e33",
    "\u0600",
    "\u200d",
    "\u200e",
    "\U0001d4b3",
    "\u00a0",
    "\u3000",
    "\u2800",
    "\u200b",
)


def _at(text: str) -> FormattedText:
    """Return `text` as one run that starts at line 1, column 1."""
    return FormattedText.at(text, Position(1, 1))


def _fit(
    text: str, max_length: int = MESSAGE_LENGTH, max_parts: int | None = None
) -> tuple[list[str], list[tuple[str, int]]]:
    """Return the texts of the parts of `text`, and each notice's code and offset.

    The text is one run from column 1, so a column is the offset of its character plus
    1, line feeds and all.
    """
    parts, notices = fit_text(_at(text), max_length=max_length, max_parts=max_parts)
    return (
        [part.text for part in parts],
        [(notice.condition.code, notice.position.column - 1) for notice in notices],
    )


def test_trims_spaces_and_line_feeds_at_both_ends_without_a_notice() -> None:
    parts, notices = fit_text(
        _at(" \n a b \n "), max_length=MESSAGE_LENGTH, max_parts=None
    )
    assert parts == (FormattedText.at("a b", Position(1, 4)),)
    assert notices == ()


@pytest.mark.parametrize("text", ["", " \n \n"])
def test_makes_no_message_of_text_that_trims_to_nothing(text: str) -> None:
    assert _fit(text) == ([], [])


def test_makes_no_message_of_blank_text() -> None:
    assert fit_text(
        _at(" \u00a0\u200b\n"), max_length=MESSAGE_LENGTH, max_parts=None
    ) == (
        (),
        (Notice(BLANK_TEXT, Position(1, 2)),),
    )


@pytest.mark.parametrize("unit", ["a", "\N{GRINNING FACE}"])
def test_makes_one_message_of_text_at_the_limit(unit: str) -> None:
    text = unit * MESSAGE_LENGTH
    assert _fit(text) == ([text], [])


def test_splits_text_one_code_point_past_the_limit() -> None:
    parts, notices = fit_text(
        _at("a" * (MESSAGE_LENGTH + 1)), max_length=MESSAGE_LENGTH, max_parts=None
    )
    assert parts == (
        _at("a" * MESSAGE_LENGTH),
        FormattedText.at("a", Position(1, MESSAGE_LENGTH + 1)),
    )
    assert notices == ()


@pytest.mark.parametrize(
    ("text", "max_length", "parts"),
    [
        pytest.param(
            "one\ntwo\n\nthree four", 15, ["one\ntwo", "three four"], id="paragraph"
        ),
        pytest.param("One. Two\nThree", 12, ["One. Two", "Three"], id="line"),
        pytest.param(
            "One two. Three four", 15, ["One two.", "Three four"], id="sentence"
        ),
        pytest.param(
            'He said "Stop!" Then left',
            20,
            ['He said "Stop!"', "Then left"],
            id="sentence-in-quotes",
        ),
        pytest.param(
            "\u6f22\u5b57\u3067\u3059\u3002\u6b21\u3067\u3059\u3002",
            6,
            ["\u6f22\u5b57\u3067\u3059\u3002", "\u6b21\u3067\u3059\u3002"],
            id="sentence-without-a-space",
        ),
        pytest.param(
            "\u300c\u306f\u3044\u3002\u300d\u6b21\u3067\u3059\u3002",
            5,
            ["\u300c\u306f\u3044\u3002\u300d", "\u6b21\u3067\u3059\u3002"],
            id="sentence-in-brackets-without-a-space",
        ),
        pytest.param("one two three", 10, ["one two", "three"], id="word"),
        pytest.param("a b c d", 5, ["a b c", "d"], id="last-word"),
        pytest.param("abcdef", 4, ["abcd", "ef"], id="cluster"),
    ],
)
def test_cuts_at_the_most_preferred_place_that_fits(
    text: str, max_length: int, parts: list[str]
) -> None:
    assert _fit(text, max_length) == (parts, [])


def test_drops_only_the_spaces_and_line_feeds_at_a_cut() -> None:
    parts, notices = fit_text(_at("ab \n \ncd"), max_length=3, max_parts=None)
    assert parts == (_at("ab"), FormattedText.at("cd", Position(1, 7)))
    assert notices == ()


@pytest.mark.parametrize(
    "cluster",
    [
        pytest.param("e\u0301", id="combining-mark"),
        pytest.param("\N{THUMBS UP SIGN}\U0001f3fd", id="skin-tone"),
        pytest.param("\N{WOMAN}\u200d\N{PERSONAL COMPUTER}", id="zwj-sequence"),
        pytest.param("\U0001f1ec\U0001f1f7", id="flag"),
        pytest.param("\U0001f1ec\U0001f1f7\U0001f1eb", id="flag-and-indicator"),
        pytest.param("\u1100\u1161\u11a8", id="hangul-jamo"),
        pytest.param("\u0915\u094d\u0937", id="conjunct"),
    ],
)
def test_keeps_a_cluster_whole_at_a_cut(cluster: str) -> None:
    assert _fit(f"ab{cluster}", 3) == (["ab", cluster], [])


def test_keeps_a_space_with_the_mark_it_carries() -> None:
    assert _fit("ab \u0301cd", 3) == (["a", "b \u0301", "cd"], [])


@pytest.mark.parametrize(
    ("text", "max_length", "parts", "offsets"),
    [
        pytest.param(
            "\U0001f1ec\U0001f1f7", 1, ["\U0001f1ec", "\U0001f1f7"], [1], id="flag"
        ),
        pytest.param(
            "e\u0301\u0301\u0301", 2, ["e\u0301", "\u0301\u0301"], [2], id="marks"
        ),
        # Any cut before the space would leave it at the start of a message, which the
        # server trims, so the mark loses it whichever cut is taken.
        pytest.param(
            "e\u0301 \u0301x", 3, ["e\u0301", "\u0301x"], [3], id="space-with-a-mark"
        ),
    ],
)
def test_cuts_a_cluster_longer_than_the_limit_with_a_notice(
    text: str, max_length: int, parts: list[str], offsets: list[int]
) -> None:
    notices = [("cluster-too-long", offset) for offset in offsets]
    assert _fit(text, max_length) == (parts, notices)


def test_never_ends_a_message_before_its_first_character_that_is_not_blank() -> None:
    text = "\u3000\u3000\n\nabc def"
    assert _fit(text, 7) == (["\u3000\u3000\n\nabc", "def"], [])


@pytest.mark.parametrize(
    ("text", "parts", "dropped"),
    [
        pytest.param(
            "ab" + "\u3000" * 6 + "cd",
            ["ab\u3000\u3000", "cd"],
            4,
            id="up-to-the-text",
        ),
        pytest.param(
            "ab" + "\u3000" * 6 + "\u0301x",
            ["ab\u3000\u3000", "\u3000\u0301x"],
            4,
            id="up-to-the-cluster-of-the-text",
        ),
        pytest.param(
            "ab" + "\u3000" * 5 + " \u0301x",
            ["ab\u3000\u3000", "\u3000 \u0301x"],
            4,
            id="up-to-a-space-that-carries-a-mark",
        ),
    ],
)
def test_drops_a_run_of_blank_characters_longer_than_the_limit(
    text: str, parts: list[str], dropped: int
) -> None:
    assert _fit(text, 4) == (parts, [("blank-text", dropped)])


def test_drops_a_blank_run_whole_when_the_text_after_it_cannot_take_its_end() -> None:
    # Each joiner attaches to the character on either side, so the six of them form one
    # cluster with the letter, longer than a message.
    text = "ab" + "\u3000" * 6 + "\u200d" * 6 + "x"
    assert _fit(text, 4) == (
        ["ab\u3000\u3000", "x"],
        [("blank-text", 4), ("cluster-too-long", 14)],
    )


def test_drops_the_text_past_max_parts_with_a_notice() -> None:
    assert _fit("a b c d e", 1, 2) == (["a", "b"], [("truncated", 4)])


def test_counts_only_messages_toward_max_parts() -> None:
    text = "ab" + "\u3000" * 6 + "cd"
    assert _fit(text, 4, 2) == (["ab\u3000\u3000", "cd"], [("blank-text", 4)])


@settings(max_examples=1000, deadline=None, database=None)
@given(
    text=st.lists(st.sampled_from(_PIECES), max_size=40).map("".join),
    max_length=st.integers(1, 40),
    max_parts=st.none() | st.integers(1, 6),
)
def test_fits_any_text_into_parts_that_rebuild_it(
    references: tuple[Unicode, ...],
    text: str,
    max_length: int,
    max_parts: int | None,
) -> None:
    formatted = FormattedText(text, (Run(0, Position(1, 1)),) if text else ())
    parts, notices = fit_text(formatted, max_length=max_length, max_parts=max_parts)
    # One run from column 1 makes each column the offset of its character plus 1.
    starts = [part.position(0).column - 1 for part in parts]
    ends = [start + len(part.text) for start, part in zip(starts, parts, strict=True)]
    noticed = {(notice.condition, notice.position.column - 1) for notice in notices}
    split = [offset for condition, offset in noticed if condition == CLUSTER_TOO_LONG]

    assert max_parts is None or len(parts) <= max_parts
    for start, end, part in zip(starts, ends, parts, strict=True):
        assert part.text == text[start:end]
        assert len(part.text) <= max_length
        assert part.text.strip(TRIMMED) == part.text
        assert set(part.text) - BLANK

    # Between two parts lie only the spaces and line feeds a cut drops, or text that a
    # notice reports dropped from its first character the server would keep. Each cut
    # is the offsets on either side of what it drops, and the span a notice of a split
    # cluster may name.
    cuts = [
        ({end, start}, end, start) for end, start in zip(ends, starts[1:], strict=False)
    ]
    for before, after in zip([0, *ends], [*starts, len(text)], strict=True):
        assert before <= after
        dropped = [
            offset for offset in range(before, after) if text[offset] not in TRIMMED
        ]
        if not dropped:
            continue
        if any(text[offset] not in BLANK for offset in dropped):
            assert after == len(text)
            assert (TRUNCATED, dropped[0]) in noticed
        else:
            assert {(BLANK_TEXT, dropped[0]), (TRUNCATED, dropped[0])} & noticed
        if before == 0 < after < len(text):
            cuts.append(({after}, before, after))
        if 0 < before < after == len(text):
            cuts.append(({before}, before, after))

    # Each cut keeps every cluster whole, as the running Python's Unicode version and
    # the newest define clusters, unless a notice reports the cut.
    graphemes = getattr(unicodedata, "iter_graphemes", None)
    whole = [reference.boundaries(text) for reference in references]
    if graphemes is not None:
        whole.append(frozenset(segment.start for segment in graphemes(text)))
    for offsets, low, high in cuts:
        if not any(low <= offset <= high for offset in split):
            assert all(offsets <= boundaries for boundaries in whole)
