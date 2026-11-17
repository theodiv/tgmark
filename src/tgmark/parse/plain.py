"""Plain text read into the document tree.

Plain text has no markup, so nothing in it is interpreted: each line becomes a text run
and each line ending a line break. A carriage return ends a line as a line feed does,
alone or before one, since the server drops carriage returns (td/telegram/misc.cpp,
clean_input_string()) and would run together the two lines one separates.
"""

from tgmark.model.document import LINE_ENDING, Document, LineBreak, Node, Position, Text


def read_plain(text: str) -> Document:
    """Return the document of `text`: a text run per line, a break per line ending."""
    nodes: list[Node] = []
    line = 1
    start = 0
    for match in LINE_ENDING.finditer(text):
        if match.start() > start:
            nodes.append(Text(text[start : match.start()], Position(line, 1)))
        nodes.append(LineBreak(Position(line, match.start() - start + 1)))
        line += 1
        start = match.end()
    if start < len(text):
        nodes.append(Text(text[start:], Position(line, 1)))

    return Document(tuple(nodes))
