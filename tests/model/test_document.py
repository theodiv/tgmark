import pytest

from tgmark.model.document import Position, locate


@pytest.mark.parametrize(
    ("text", "offsets", "places"),
    [
        pytest.param("ab", [0, 1], [(1, 1), (1, 2)], id="one-line"),
        pytest.param("a\nb", [1, 2], [(1, 2), (2, 1)], id="line-feed"),
        pytest.param("a\rb", [1, 2], [(1, 2), (2, 1)], id="carriage-return"),
        pytest.param("a\r\nb", [1, 2, 3], [(1, 2), (1, 3), (2, 1)], id="crlf"),
        pytest.param("\n\r\n\ra", [4], [(4, 1)], id="every-ending"),
        pytest.param("\N{GRINNING FACE}a", [1], [(1, 2)], id="astral"),
        pytest.param("a\x0b\x0c\x85\u2028b", [5], [(1, 6)], id="no-other-endings"),
    ],
)
def test_locates_each_offset_by_line_and_column(
    text: str, offsets: list[int], places: list[tuple[int, int]]
) -> None:
    assert locate(text, offsets) == tuple(Position(*place) for place in places)


def test_positions_order_line_first() -> None:
    positions = [Position(2, 1), Position(1, 9), Position(1, 3)]
    assert sorted(positions) == [Position(1, 3), Position(1, 9), Position(2, 1)]
