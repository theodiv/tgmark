"""Grapheme cluster boundaries a cut may use, so that no cut splits a character.

The rule reads only `unicodedata` and the fixed sets below: the package ships none of
Unicode's property files, which would add their license to its own.
"""

import unicodedata
from collections.abc import Iterable


def _chars(*spans: int | tuple[int, int]) -> frozenset[str]:
    codes: list[Iterable[int]] = [
        range(span[0], span[1] + 1) if isinstance(span, tuple) else (span,)
        for span in spans
    ]
    return frozenset(chr(code) for group in codes for code in group)


# The general categories of marks, which attach to the character before them
# (GB9, GB9a).
_MARKS = frozenset({"Mn", "Mc", "Me"})

# The characters that attach to the character before them without being marks: the
# joiner U+200D, and the characters of GraphemeBreakProperty.txt, Extend and
# SpacingMark, whose category is not a mark's, the emoji modifiers among them
# (GB9, GB9a).
_ATTACHING = _chars(
    0x0E33,
    0x0EB3,
    0x200C,
    0x200D,
    (0xFF9E, 0xFF9F),
    (0x1F3FB, 0x1F3FF),
    (0xE0020, 0xE007F),
)

# The characters assigned after Unicode 14.0.0, up to 18.0.0, that attach to the
# character before them (GraphemeBreakProperty.txt, Extend and SpacingMark), for a
# Python whose `unicodedata` predates them.
_ADDED_ATTACHING = _chars(
    (0x05C8, 0x05C9),
    0x0897,
    (0x0B53, 0x0B54),
    0x0CF3,
    0x0ECE,
    (0x1ACF, 0x1AF0),
    (0x10D69, 0x10D6D),
    (0x10ECB, 0x10ECF),
    (0x10EF0, 0x10EFF),
    0x11241,
    (0x113B8, 0x113C0),
    0x113C2,
    0x113C5,
    (0x113C7, 0x113CA),
    (0x113CC, 0x113D0),
    0x113D2,
    (0x113E1, 0x113E2),
    (0x11B60, 0x11B67),
    0x11DF0,
    (0x11F00, 0x11F01),
    0x11F03,
    (0x11F34, 0x11F3A),
    (0x11F3E, 0x11F42),
    0x11F5A,
    0x13440,
    (0x13447, 0x13455),
    (0x1611E, 0x1612F),
    (0x1D127, 0x1D128),
    (0x1D250, 0x1D252),
    (0x1D25B, 0x1D25C),
    0x1D25F,
    (0x1D280, 0x1D281),
    0x1E08F,
    (0x1E4EC, 0x1E4EF),
    (0x1E5EE, 0x1E5EF),
    0x1E6E3,
    0x1E6E6,
    (0x1E6EE, 0x1E6EF),
    0x1E6F5,
)

# The characters that attach to the character after them: the joiner U+200D (GB11), and
# the prepend characters of every Unicode version from 14.0.0 to 18.0.0
# (GraphemeBreakProperty.txt, Prepend; GB9b).
_JOINING = _chars(
    (0x0600, 0x0605),
    0x06DD,
    0x070F,
    (0x0890, 0x0891),
    0x08E2,
    0x0D4E,
    0x200D,
    0x110BD,
    0x110CD,
    (0x111C2, 0x111C3),
    0x113D1,
    0x1193F,
    0x11941,
    0x11A3A,
    (0x11A84, 0x11A89),
    0x11D46,
    0x11F02,
)

# The linkers that a combining class of 9 does not mark: the letters 18.0.0 links to the
# consonant after them, and the viramas assigned after 14.0.0
# (DerivedCoreProperties.txt, InCB=Linker; GB9c).
_LINKERS = _chars(0x1CF5, 0x1CF6, 0x11A3A, 0x113D0, 0x11F42)

# The parts of Hangul syllables, the Kirat Rai vowel signs joining as Hangul vowels do
# (GraphemeBreakProperty.txt, L, V, and T; GB6, GB7, GB8).
_LEADING = _chars((0x1100, 0x115F), (0xA960, 0xA97C))
_VOWELS = _chars((0x1160, 0x11A7), (0xD7B0, 0xD7C6), 0x16D63, (0x16D67, 0x16D6A))
_TRAILING = _chars((0x11A8, 0x11FF), (0xD7CB, 0xD7FB))
_SYLLABLES = range(0xAC00, 0xD7A4)
_TRAILS = 28

# The regional indicators, which pair into flags (GB12, GB13).
_REGIONAL = _chars((0x1F1E6, 0x1F1FF))

# The bits of a class, each a property the rule reads from a character, and the Hangul
# part above them.
_ATTACHES = 1 << 0
_JOINS = 1 << 1
_LINKS = 1 << 2
_LETTER = 1 << 3
_PAIRS = 1 << 4
_CR = 1 << 5
_LF = 1 << 6
_PART = 7
_L, _V, _T, _LV, _LVT = range(1, 6)

# The pairs of Hangul parts that stay together.
_HANGUL_PAIRS = frozenset(
    {
        *((_L, after) for after in (_L, _V, _LV, _LVT)),
        *((before, after) for before in (_LV, _V) for after in (_V, _T)),
        *((before, _T) for before in (_LVT, _T)),
    }
)


def classify(char: str) -> int:
    """Return the class of `char`: a bit for each property the rule reads from it.

    Two characters of one class get the same verdict at every offset, which lets a test
    check one character of each class in place of every code point.
    """
    category = unicodedata.category(char)
    kind = 0
    if category in _MARKS or char in _ATTACHING or char in _ADDED_ATTACHING:
        kind |= _ATTACHES
        # Only marks carry a combining class of 9, which viramas have.
        if unicodedata.combining(char) == 9:
            kind |= _LINKS
    if char in _JOINING:
        kind |= _JOINS
    if char in _LINKERS:
        kind |= _LINKS
    # A code point unassigned in the running Python may be a consonant in a later
    # version, so it counts as a letter.
    if category[0] == "L" or category == "Cn":
        kind |= _LETTER
    if char in _REGIONAL:
        kind |= _PAIRS
    if char == "\r":
        kind |= _CR
    if char == "\n":
        kind |= _LF
    return kind | _hangul(char) << _PART


def boundaries(text: str) -> bytes:
    """Return a flag per offset of `text`, 1 where a cut keeps every cluster whole.

    The flags run from offset 0 to `len(text)`, both ends included and set, so a cut at
    an offset is allowed exactly when its flag is 1. Where `unicodedata` cannot settle a
    boundary, the rule refuses it: a refused boundary costs at most a shorter message,
    while a cut inside a cluster splits what a reader sees as one character. Every
    supported Python refuses each cut that its own Unicode version or 18.0.0 forbids.
    """
    flags = bytearray(b"\x01" * (len(text) + 1))
    before = 0
    linked = False
    regional = 0
    for offset, char in enumerate(text):
        kind = classify(char)
        if offset and (
            kind & _ATTACHES
            or before & _JOINS
            or (before & _CR and kind & _LF)
            or (linked and kind & _LETTER)
            or (before >> _PART, kind >> _PART) in _HANGUL_PAIRS
            or (kind & _PAIRS and regional % 2 == 1)
        ):
            flags[offset] = 0

        linked = bool(kind & _LINKS) or (linked and bool(kind & _ATTACHES))
        regional = regional + 1 if kind & _PAIRS else 0
        before = kind

    return bytes(flags)


def _hangul(char: str) -> int:
    """Return the part of a Hangul syllable sequence that `char` is, or 0 for none."""
    if char in _LEADING:
        return _L
    if char in _VOWELS:
        return _V
    if char in _TRAILING:
        return _T
    if ord(char) in _SYLLABLES:
        return _LV if (ord(char) - _SYLLABLES.start) % _TRAILS == 0 else _LVT
    return 0
