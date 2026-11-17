"""Input text made fit for UTF-8: each lone surrogate becomes U+FFFD.

A `str` can hold a surrogate code point, which no UTF-8 encoder accepts and which the
server refuses as invalid UTF-8 (tdutils/td/utils/utf8.cpp, check_utf8()), so each one
is replaced before a reader sees the text. A high surrogate before a low one counts as
two, since a `str` holds code points, not UTF-16 code units.
"""

import re

from tgmark.model.diagnostics import LONE_SURROGATE, Notice
from tgmark.model.document import locate

_SURROGATE = re.compile("[\ud800-\udfff]")


def replace_surrogates(text: str) -> tuple[str, tuple[Notice, ...]]:
    """Return `text` with each surrogate replaced, and a notice for each replacement."""
    offsets = [match.start() for match in _SURROGATE.finditer(text)]
    if not offsets:
        return text, ()

    notices = tuple(Notice(LONE_SURROGATE, place) for place in locate(text, offsets))
    return _SURROGATE.sub("\N{REPLACEMENT CHARACTER}", text), notices
