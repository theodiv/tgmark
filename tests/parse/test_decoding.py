import codecs

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from tgmark.model.diagnostics import LONE_SURROGATE, UNDECODABLE_BYTES, Notice
from tgmark.model.document import Position, locate
from tgmark.parse.decoding import decode_bytes, replace_surrogates

# The byte order marks that name an encoding, each with the encoding it names.
_MARKS = (
    (codecs.BOM_UTF8, "utf-8"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
)

# The pieces generated input is made of: characters in each encoding, lone surrogates,
# truncated and overlong sequences, and bytes UTF-8 never allows.
_PIECES = (
    *(
        text.encode(encoding, "surrogatepass")
        for text in ("a", "\r\n", "\u00e9", "\N{GRINNING FACE}", "\ud83d", "\ude00")
        for encoding in ("utf-8", "utf-16-be", "utf-16-le")
    ),
    b"\xf0\x9f\x98",
    b"\xe2\x82",
    b"\xc0\xaf",
    b"\x80",
    b"\xff",
    b"\x00",
)


def _undecodable(*places: tuple[int, int]) -> tuple[Notice, ...]:
    """Return a notice of undecodable bytes at each line and column of `places`."""
    return tuple(Notice(UNDECODABLE_BYTES, Position(*place)) for place in places)


def test_keeps_a_text_without_surrogates() -> None:
    text = "a\r\nb\N{GRINNING FACE}\N{REPLACEMENT CHARACTER}"
    assert replace_surrogates(text) == (text, ())


def test_replaces_each_surrogate_with_a_notice_at_its_position() -> None:
    # A high surrogate before a low one is two code points of a str, so two notices.
    text = f"a{chr(0xDFFF)}\r\nb{chr(0xD83D)}{chr(0xDE00)}"
    assert replace_surrogates(text) == (
        "a\ufffd\r\nb\ufffd\ufffd",
        (
            Notice(LONE_SURROGATE, Position(1, 2)),
            Notice(LONE_SURROGATE, Position(2, 2)),
            Notice(LONE_SURROGATE, Position(2, 3)),
        ),
    )


@pytest.mark.parametrize(
    ("mark", "encoding"),
    [pytest.param(mark, encoding, id=encoding) for mark, encoding in _MARKS],
)
def test_decodes_bytes_in_the_encoding_their_mark_names(
    mark: bytes, encoding: str
) -> None:
    text = "Total: 42 \N{GRINNING FACE}\r\nnext"
    assert decode_bytes(mark + text.encode(encoding)) == (text, ())


def test_decodes_unmarked_bytes_as_utf8() -> None:
    text = "Café \N{GRINNING FACE}"
    assert decode_bytes(text.encode()) == (text, ())


def test_never_guesses_utf16_without_a_mark() -> None:
    # A NUL follows each character, which UTF-8 decodes as a character of its own.
    assert decode_bytes("Hi".encode("utf-16-le")) == ("H\x00i\x00", ())


@pytest.mark.parametrize(
    ("data", "text"),
    [
        pytest.param(codecs.BOM_UTF8 * 2 + b"a", "﻿a", id="utf-8"),
        pytest.param(
            codecs.BOM_UTF16_LE * 2 + "a".encode("utf-16-le"), "﻿a", id="utf-16-le"
        ),
    ],
)
def test_keeps_a_second_mark_as_a_character(data: bytes, text: str) -> None:
    assert decode_bytes(data) == (text, ())


@pytest.mark.parametrize(
    ("data", "text", "notices"),
    [
        # The UTF-32LE mark opens with the UTF-16LE one, so its last two bytes read as
        # U+0000, and so does the upper half of each code unit after it.
        pytest.param(
            codecs.BOM_UTF32_LE + "Hi".encode("utf-32-le"),
            "\x00H\x00i\x00",
            (),
            id="utf-32-le",
        ),
        # The UTF-32BE mark names no encoding, so it reads as UTF-8, which refuses its
        # last two bytes.
        pytest.param(
            codecs.BOM_UTF32_BE + "Hi".encode("utf-32-be"),
            "\x00\x00\ufffd\ufffd\x00\x00\x00H\x00\x00\x00i",
            _undecodable((1, 3), (1, 4)),
            id="utf-32-be",
        ),
    ],
)
def test_recognizes_no_utf32_mark(
    data: bytes, text: str, notices: tuple[Notice, ...]
) -> None:
    assert decode_bytes(data) == (text, notices)


# The Unicode Standard's examples of U+FFFD substitution of maximal subparts, at version
# 18.0.0 (Section 3.9.6, Tables 3-8 to 3-11).
@pytest.mark.parametrize(
    ("data", "text"),
    [
        pytest.param(
            bytes.fromhex("C0 AF E0 80 BF F0 81 82 41"),
            "\ufffd" * 8 + "A",
            id="non-shortest-forms",
        ),
        pytest.param(
            bytes.fromhex("ED A0 80 ED BF BF ED AF 41"),
            "\ufffd" * 8 + "A",
            id="surrogates",
        ),
        pytest.param(
            bytes.fromhex("F4 91 92 93 FF 41 80 BF 42"),
            "\ufffd" * 5 + "A" + "\ufffd" * 2 + "B",
            id="other",
        ),
        pytest.param(
            bytes.fromhex("E1 80 E2 F0 91 92 F1 BF 41"),
            "\ufffd" * 4 + "A",
            id="truncated",
        ),
    ],
)
def test_replaces_each_maximal_subpart_with_one_character(
    data: bytes, text: str
) -> None:
    columns = [offset + 1 for offset, char in enumerate(text) if char == "\ufffd"]
    places = [(1, column) for column in columns]
    assert decode_bytes(data) == (text, _undecodable(*places))


@pytest.mark.parametrize(
    ("mark", "encoding"),
    [pytest.param(mark, encoding, id=encoding) for mark, encoding in _MARKS[1:]],
)
@pytest.mark.parametrize(
    "surrogates",
    [
        pytest.param("\ud83d", id="high"),
        pytest.param("\ude00", id="low"),
        pytest.param("\ude00\ud83d", id="low-before-high"),
        pytest.param("\ud83d\ud83d", id="two-highs"),
    ],
)
def test_replaces_each_lone_surrogate_of_utf16(
    mark: bytes, encoding: str, surrogates: str
) -> None:
    data = mark + f"{surrogates}Hi".encode(encoding, "surrogatepass")
    places = [(1, column) for column in range(1, len(surrogates) + 1)]
    assert decode_bytes(data) == (
        "\ufffd" * len(surrogates) + "Hi",
        _undecodable(*places),
    )


@pytest.mark.parametrize(
    ("data", "text"),
    [
        pytest.param(b"Smile \xf0\x9f\x98", "Smile \ufffd", id="utf-8"),
        pytest.param(
            codecs.BOM_UTF16_LE + "Hi".encode("utf-16-le") + b"!",
            "Hi\ufffd",
            id="stray-byte",
        ),
        pytest.param(
            codecs.BOM_UTF16_LE + "Hi\ud83d".encode("utf-16-le", "surrogatepass"),
            "Hi\ufffd",
            id="high-surrogate",
        ),
        # A high surrogate and the stray byte after it make one sequence, as
        # `errors="replace"` reads them.
        pytest.param(
            codecs.BOM_UTF16_LE
            + "Hi\ud83d".encode("utf-16-le", "surrogatepass")
            + b"!",
            "Hi\ufffd",
            id="high-surrogate-and-stray-byte",
        ),
    ],
)
def test_replaces_an_unfinished_sequence_at_the_end(data: bytes, text: str) -> None:
    assert decode_bytes(data) == (text, _undecodable((1, len(text))))


def test_keeps_a_replacement_character_of_the_input_without_a_notice() -> None:
    data = "a\ufffd".encode() + b"\xff"
    assert decode_bytes(data) == ("a\ufffd\ufffd", _undecodable((1, 3)))


def test_places_each_notice_by_the_lines_of_the_decoded_text() -> None:
    # A lone surrogate follows an astral character, which takes one column, then opens
    # the line after each kind of line ending.
    text = "\N{GRINNING FACE}\udc00\r\n\udc00b\r\udc00c\n\udc00"
    data = codecs.BOM_UTF16_LE + text.encode("utf-16-le", "surrogatepass")
    assert decode_bytes(data) == (
        "\N{GRINNING FACE}\ufffd\r\n\ufffdb\r\ufffdc\n\ufffd",
        _undecodable((1, 2), (2, 1), (3, 1), (4, 1)),
    )


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"", id="empty"),
        *(pytest.param(mark, id=encoding) for mark, encoding in _MARKS),
    ],
)
def test_decodes_no_text_from_empty_input_or_a_mark_alone(data: bytes) -> None:
    assert decode_bytes(data) == ("", ())


@settings(max_examples=500, deadline=None, database=None)
@given(
    marked=st.sampled_from(((b"", "utf-8"), *_MARKS)),
    body=st.binary(max_size=40)
    | st.lists(st.sampled_from(_PIECES), max_size=20).map(b"".join),
)
def test_replaces_what_the_encoding_refuses_as_errors_replace_does(
    marked: tuple[bytes, str], body: bytes
) -> None:
    mark, encoding = marked
    # Unmarked input that opens with a mark reads as marked input, and a U+FFFD that the
    # input holds is text, which no notice reports.
    assume(mark or not body.startswith(tuple(known for known, _ in _MARKS)))
    assume("\ufffd" not in body.decode(encoding, "ignore"))
    text = body.decode(encoding, "replace")
    offsets = [offset for offset, char in enumerate(text) if char == "\ufffd"]
    notices = tuple(Notice(UNDECODABLE_BYTES, place) for place in locate(text, offsets))
    assert decode_bytes(mark + body) == (text, notices)
