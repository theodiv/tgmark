"""Input made valid text: `bytes` decoded, and each lone surrogate replaced.

This module alone makes input valid text, so every later stage reads a `str` that
encodes as UTF-8.
"""

import codecs
import re
from collections.abc import Iterator

from tgmark.model.diagnostics import LONE_SURROGATE, UNDECODABLE_BYTES, Notice
from tgmark.model.document import locate

# Each byte order mark that names an encoding, with that encoding and the built-in error
# handler under which its decoder passes each code unit it refuses through as a
# surrogate; and the same for bytes that open with no mark.
_MARKS = (
    (codecs.BOM_UTF8, "utf-8", "surrogateescape"),
    (codecs.BOM_UTF16_BE, "utf-16-be", "surrogatepass"),
    (codecs.BOM_UTF16_LE, "utf-16-le", "surrogatepass"),
)
_UNMARKED = (b"", "utf-8", "surrogateescape")

_SURROGATE = re.compile("[\ud800-\udfff]")
_SURROGATES = re.compile("[\ud800-\udfff]+")


def decode_bytes(data: bytes) -> tuple[str, tuple[Notice, ...]]:
    """Return `data` decoded, and a notice for each byte sequence its encoding refuses.

    A byte order mark that opens `data` names its encoding and goes, being no part of
    the text: UTF-8, UTF-16BE, or UTF-16LE, the marks the WHATWG Encoding Standard
    sniffs. Without one, `data` is UTF-8, whatever the locale. Each byte sequence the
    encoding refuses becomes one U+FFFD per maximal subpart, as the Unicode Standard
    recommends and `bytes.decode` with `errors="replace"` gives.
    """
    mark, encoding, handler = next(
        (choice for choice in _MARKS if data.startswith(choice[0])), _UNMARKED
    )
    body = data[len(mark) :]
    try:
        return body.decode(encoding), ()
    except UnicodeDecodeError:
        return _replace_refused(body, encoding, handler)


def replace_surrogates(text: str) -> tuple[str, tuple[Notice, ...]]:
    """Return `text` with each surrogate replaced, and a notice for each replacement.

    No UTF-8 encoder accepts a surrogate, and the server refuses invalid UTF-8
    (tdutils/td/utils/utf8.cpp, check_utf8()). A high surrogate before a low one counts
    as two, since a `str` holds code points, not UTF-16 code units.
    """
    offsets = [match.start() for match in _SURROGATE.finditer(text)]
    if not offsets:
        return text, ()

    notices = tuple(Notice(LONE_SURROGATE, place) for place in locate(text, offsets))
    return _SURROGATE.sub("\N{REPLACEMENT CHARACTER}", text), notices


def _replace_refused(
    body: bytes, encoding: str, handler: str
) -> tuple[str, tuple[Notice, ...]]:
    """Return `body` decoded, each refused sequence made U+FFFD, and a notice for each.

    Valid input never comes here, so it costs one strict decode. Here the decoder runs
    under `handler` instead, which marks every refused code unit in linear time; a
    handler of the package's own would have to be registered, and the registry is
    global state.
    """
    texts: list[str] = []
    offsets: list[int] = []
    length = 0
    for kept, replaced in _stretches(body, encoding, handler):
        length += len(kept)
        offsets += range(length, length + len(replaced))
        length += len(replaced)
        texts += (kept, replaced)

    text = "".join(texts)
    notices = tuple(Notice(UNDECODABLE_BYTES, place) for place in locate(text, offsets))
    return text, notices


def _stretches(body: bytes, encoding: str, handler: str) -> Iterator[tuple[str, str]]:
    """Yield each stretch the encoding keeps, decoded, and the U+FFFD that follow it.

    A run of the surrogates that `handler` passes through can hold several refused
    sequences, so it becomes the U+FFFD that decoding its bytes alone gives. Alone they
    decode as in place: the byte after the run starts a character, which no refused
    sequence reaches into.
    """
    decoder = codecs.getincrementaldecoder(encoding)(handler)
    marked = decoder.decode(body)
    start = 0
    for match in _SURROGATES.finditer(marked):
        refused = match.group().encode(encoding, handler)
        yield marked[start : match.start()], refused.decode(encoding, "replace")
        start = match.end()
    # The decoder holds back a sequence that the end of `body` leaves unfinished.
    yield marked[start:], decoder.getstate()[0].decode(encoding, "replace")
