import pytest

from tgmark.model.document import Document, LineBreak, Node, Position, Text
from tgmark.parse.plain import read_plain


@pytest.mark.parametrize(
    ("text", "nodes"),
    [
        pytest.param("", (), id="empty"),
        pytest.param("ab", (Text("ab", Position(1, 1)),), id="one-line"),
        pytest.param(
            "ab\ncd",
            (
                Text("ab", Position(1, 1)),
                LineBreak(Position(1, 3)),
                Text("cd", Position(2, 1)),
            ),
            id="line-feed",
        ),
        pytest.param(
            "a\rb",
            (
                Text("a", Position(1, 1)),
                LineBreak(Position(1, 2)),
                Text("b", Position(2, 1)),
            ),
            id="carriage-return",
        ),
        pytest.param(
            "a\r\nb",
            (
                Text("a", Position(1, 1)),
                LineBreak(Position(1, 2)),
                Text("b", Position(2, 1)),
            ),
            id="crlf",
        ),
        pytest.param(
            "\n\r\na\n",
            (
                LineBreak(Position(1, 1)),
                LineBreak(Position(2, 1)),
                Text("a", Position(3, 1)),
                LineBreak(Position(3, 2)),
            ),
            id="blank-lines",
        ),
        # Python's str.splitlines() also ends a line at these; a reader does not.
        pytest.param(
            "\t\x0b\x0c\x1c\x85\u2028\u2029",
            (Text("\t\x0b\x0c\x1c\x85\u2028\u2029", Position(1, 1)),),
            id="no-other-endings",
        ),
    ],
)
def test_reads_a_text_run_per_line_and_a_break_per_line_ending(
    text: str, nodes: tuple[Node, ...]
) -> None:
    assert read_plain(text) == Document(nodes)
