"""The document tree lowered into formatted text, each node in its Telegram form.

The server's character rules run over the whole text once every node is lowered, since
the rule for direction marks looks at a mark's neighbor, which can stand in the
next node.
"""

from tgmark.lower.characters import clean
from tgmark.model.diagnostics import Notice
from tgmark.model.document import Document, LineBreak, Node, Text
from tgmark.model.formatted import FormattedText, join


def lower_document(document: Document) -> tuple[FormattedText, tuple[Notice, ...]]:
    """Return the formatted text of `document`, with a notice per character changed."""
    forms = (FormattedText.at(_form(node), node.position) for node in document.nodes)
    return clean(join(forms))


def _form(node: Node) -> str:
    """Return the Telegram form of `node`: a text run's characters, or a line feed."""
    match node:
        case Text(value=value):
            return value
        case LineBreak():  # pragma: no branch  # Node holds no other type
            return "\n"
