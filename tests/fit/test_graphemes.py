import itertools
from collections.abc import Iterable

import pytest

from tests.support.segmentation import BREAK_VALUES, CONJUNCT_VALUES, Unicode, cases
from tgmark.fit.graphemes import boundaries, classify

# Every code point but the surrogates, which decoding replaces before the rule runs.
_CODE_POINTS = (*range(0xD800), *range(0xE000, 0x110000))


def _allowed(text: str) -> frozenset[int]:
    """Return each offset inside `text` where the rule allows a cut."""
    flags = boundaries(text)
    return frozenset(offset for offset in range(1, len(text)) if flags[offset])


def _violations(reference: Unicode, texts: Iterable[str]) -> list[str]:
    """Return each text where the rule allows a cut that `reference` forbids."""
    return [
        " ".join(f"{ord(char):04X}" for char in text)
        for text in texts
        if _allowed(text) - reference.boundaries(text)
    ]


@pytest.fixture(scope="module")
def classes() -> tuple[int, ...]:
    return tuple(classify(chr(code)) for code in _CODE_POINTS)


def test_allows_a_cut_only_where_the_test_file_breaks(reference: Unicode) -> None:
    found = cases(reference.version)
    assert [text for text, breaks in found if _allowed(text) - breaks] == []


def test_allows_a_cut_only_where_unicode_breaks_at_every_code_point(
    reference: Unicode, classes: tuple[int, ...]
) -> None:
    # Two characters of one class and the same properties get the same verdicts from
    # both the rule and the reference, so one of each stands for every code point.
    chars: dict[tuple[int, int, int, int], str] = {}
    for code, kind in zip(_CODE_POINTS, classes, strict=True):
        key = (
            kind,
            reference.breaks[code],
            reference.pictographic[code],
            reference.conjunct[code],
        )
        chars.setdefault(key, chr(code))

    def having(values: Iterable[str]) -> list[str]:
        wanted = set(values)
        return [
            char
            for char in chars.values()
            if BREAK_VALUES[reference.breaks[ord(char)]] in wanted
            or CONJUNCT_VALUES[reference.conjunct[ord(char)]] in wanted
        ]

    consonants, linkers = having({"Consonant"}), having({"Linker"})
    extenders = having({"Extend", "Linker"})
    joiners, regional = having({"ZWJ"}), having({"Regional_Indicator"})
    pictographs = [char for char in chars.values() if reference.pictographic[ord(char)]]
    # Pairs reach every rule but those that look further back: GB9c on conjuncts,
    # GB11 on emoji sequences, and GB12 and GB13 on runs of regional indicators.
    shapes = [
        (chars.values(), chars.values()),
        (linkers, consonants),
        (linkers, extenders, consonants),
        (consonants, linkers, consonants),
        (consonants, linkers, extenders, consonants),
        (consonants, extenders, linkers, consonants),
        (pictographs, joiners, pictographs),
        (pictographs, having({"Extend"}), joiners, pictographs),
        (regional, regional, regional),
        (regional, regional, regional, regional),
    ]
    texts = ("".join(text) for shape in shapes for text in itertools.product(*shape))
    assert _violations(reference, texts) == []


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("ab", id="letters"),
        pytest.param("12", id="digits"),
        pytest.param("\u4e2d\u6587", id="ideographs"),
        pytest.param("\N{GRINNING FACE}\N{GRINNING FACE}", id="emoji"),
        pytest.param("\uac00\ub098", id="hangul-syllables"),
        pytest.param("e\u0301e", id="after-a-mark"),
        pytest.param("\u0915\u094d ", id="after-a-virama-before-a-space"),
        pytest.param("\r\r", id="carriage-returns"),
    ],
)
def test_allows_a_cut_between_two_clusters(text: str) -> None:
    assert boundaries(text)[len(text) - 1] == 1


@pytest.mark.parametrize(
    ("text", "offset"),
    [
        pytest.param("e\u0301", 1, id="combining-mark"),
        pytest.param("\N{THUMBS UP SIGN}\U0001f3fd", 1, id="skin-tone"),
        pytest.param("\N{WOMAN}\u200d\N{PERSONAL COMPUTER}", 2, id="zwj-sequence"),
        pytest.param("\U0001f1ec\U0001f1f7", 1, id="flag"),
        pytest.param("\U0001f1ec\U0001f1f7\U0001f1eb\U0001f1f7", 3, id="second-flag"),
        pytest.param("\u1100\u1161", 1, id="hangul-jamo"),
        pytest.param("\u0915\u094d\u0937", 2, id="conjunct"),
        pytest.param("\u0915\u094d\u200d\u0937", 3, id="conjunct-with-zwj"),
        pytest.param("\u0600\u0661", 1, id="prepend"),
        pytest.param("\r\n", 1, id="crlf"),
        # Kawi, which Python 3.11's Unicode version lacks.
        pytest.param("\U00011f12\U00011f42\U00011f12", 2, id="kawi-conjunct"),
    ],
)
def test_refuses_a_cut_inside_a_cluster(text: str, offset: int) -> None:
    assert boundaries(text)[offset] == 0


def test_flags_both_ends_of_a_text() -> None:
    assert boundaries("ab") == b"\x01\x01\x01"
    assert boundaries("") == b"\x01"
