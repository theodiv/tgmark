from tgmark.model.diagnostics import LONE_SURROGATE, Notice
from tgmark.model.document import Position
from tgmark.parse.decoding import replace_surrogates


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
