from tgmark.model.document import Position
from tgmark.model.formatted import FormattedText, Run, join


def _two_lines() -> FormattedText:
    """Return `ab` from line 1 and `cd` from line 3, joined by a line feed."""
    return join(
        [
            FormattedText.at("ab", Position(1, 1)),
            FormattedText.at("\n", Position(1, 3)),
            FormattedText.at("cd", Position(3, 5)),
        ]
    )


def test_joins_parts_with_their_runs_moved_past_the_parts_before() -> None:
    runs = (Run(0, Position(1, 1)), Run(2, Position(1, 3)), Run(3, Position(3, 5)))
    assert _two_lines() == FormattedText("ab\ncd", runs)


def test_maps_each_offset_to_the_position_of_its_character() -> None:
    text = _two_lines()
    assert [text.position(offset) for offset in range(5)] == [
        Position(1, 1),
        Position(1, 2),
        Position(1, 3),
        Position(3, 5),
        Position(3, 6),
    ]


def test_slice_starts_its_first_run_where_the_slice_starts() -> None:
    runs = (Run(0, Position(1, 2)), Run(1, Position(1, 3)), Run(2, Position(3, 5)))
    assert _two_lines().slice(1, 4) == FormattedText("b\nc", runs)


def test_slice_from_a_run_start_keeps_that_run() -> None:
    assert _two_lines().slice(3, 5) == FormattedText("cd", (Run(0, Position(3, 5)),))


def test_empty_text_holds_no_runs() -> None:
    assert _two_lines().slice(2, 2) == FormattedText("", ())
    assert FormattedText.at("", Position(1, 1)) == FormattedText("", ())
    assert join([]) == FormattedText("", ())
