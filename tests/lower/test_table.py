from tgmark.lower.table import lower_document
from tgmark.model.diagnostics import CONTROL_CHARACTER, DIRECTION_MARK, Notice
from tgmark.model.document import Document, LineBreak, Position, Text
from tgmark.model.formatted import FormattedText, Run


def test_lowers_text_runs_and_line_breaks_with_their_positions() -> None:
    document = Document(
        (
            Text("ab", Position(1, 1)),
            LineBreak(Position(1, 3)),
            Text("c", Position(2, 1)),
        )
    )
    runs = (Run(0, Position(1, 1)), Run(2, Position(1, 3)), Run(3, Position(2, 1)))
    assert lower_document(document) == (FormattedText("ab\nc", runs), ())


def test_applies_the_character_rules_across_nodes() -> None:
    document = Document(
        (Text("a\u200e", Position(1, 1)), Text("\u200f\tb", Position(1, 3)))
    )
    formatted, notices = lower_document(document)
    assert formatted.text == "a\u200c\u200f b"
    assert notices == (
        Notice(CONTROL_CHARACTER, Position(1, 4)),
        Notice(DIRECTION_MARK, Position(1, 2)),
    )


def test_lowers_an_empty_document_to_empty_text() -> None:
    assert lower_document(Document(())) == (FormattedText("", ()), ())
