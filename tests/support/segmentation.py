"""Grapheme cluster boundaries as UAX #29 defines them at each Unicode version.

Each version's rules run on that version's own property data, read from its files in
`tests/data/unicode/`, so the boundaries never depend on the running Python's
`unicodedata`. The rule that keeps an Indic conjunct whole, GB9c, first appears in
15.1.0, and 18.0.0 drops the consonant it required before the linker.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable

# The versions with files in tests/data/unicode/: each one a supported Python ships, and
# the newest.
VERSIONS = ("14.0.0", "15.0.0", "15.1.0", "16.0.0", "17.0.0", "18.0.0")
NEWEST = VERSIONS[-1]

# The Grapheme_Cluster_Break values, each stored as its index here.
BREAK_VALUES = (
    "Other",
    "CR",
    "LF",
    "Control",
    "Extend",
    "ZWJ",
    "Regional_Indicator",
    "Prepend",
    "SpacingMark",
    "L",
    "V",
    "T",
    "LV",
    "LVT",
)
_CR, _LF, _CONTROL, _EXTEND, _ZWJ, _REGIONAL, _PREPEND, _SPACING = range(1, 9)
_L, _V, _T, _LV, _LVT = range(9, 14)

# The Indic_Conjunct_Break values, each stored as its index here.
CONJUNCT_VALUES = ("None", "Linker", "Consonant", "Extend")
_LINKER, _CONSONANT, _CONJUNCT_EXTEND = range(1, 4)

# The pairs of Hangul syllable parts that stay together (GB6, GB7, GB8).
_HANGUL = frozenset(
    {
        *((_L, after) for after in (_L, _V, _LV, _LVT)),
        *((before, after) for before in (_LV, _V) for after in (_V, _T)),
        *((before, _T) for before in (_LVT, _T)),
    }
)

# The states of GB9c and GB11, each reached by the characters named.
_CONSONANT_SEEN, _LINKED = 1, 2
_PICTOGRAPH_SEEN, _PICTOGRAPH_JOINED = 1, 2

_CODE_POINTS = 0x110000


@dataclass(frozen=True)
class Unicode:
    """The grapheme cluster rules of one Unicode version, with its property data.

    Attributes:
        version: The Unicode version, such as `15.1.0`.
        breaks: The Grapheme_Cluster_Break value of each code point, as an index into
            `BREAK_VALUES`.
        pictographic: 1 for each code point that is Extended_Pictographic, 0 for any
            other.
        conjunct: The Indic_Conjunct_Break value of each code point, as an index into
            `CONJUNCT_VALUES`; `None` throughout before 15.1.0, which lacks
            the property.
    """

    version: str
    breaks: bytes
    pictographic: bytes
    conjunct: bytes

    def boundaries(self, text: str) -> frozenset[int]:
        """Return each offset inside `text` where this version allows a boundary.

        The rules run in the order UAX #29 gives them, and the first that applies
        decides; GB9c, GB11, GB12, and GB13 look further back than the pair at the
        offset, so a state carries what they need from one character to the next.
        """
        rule = _conjunct_rule(self.version)
        found = set()
        previous = 0
        regional = 0
        pictograph = 0
        conjunct = 0
        for offset, char in enumerate(text):
            code = ord(char)
            value = self.breaks[code]
            joined = _joined(previous, value)
            if joined is None:
                joined = (
                    (conjunct == _LINKED and self.conjunct[code] == _CONSONANT)
                    or (
                        pictograph == _PICTOGRAPH_JOINED
                        and self.pictographic[code] == 1
                    )
                    or (value == _REGIONAL == previous and regional % 2 == 1)
                )
            if offset and not joined:
                found.add(offset)

            regional = regional + 1 if value == _REGIONAL else 0
            pictograph = _pictograph_state(pictograph, value, self.pictographic[code])
            conjunct = rule(conjunct, self.conjunct[code])
            previous = value

        return frozenset(found)


def load(version: str) -> Unicode:
    """Return the rules of `version`, with the property data of its files.

    Raises:
        FileNotFoundError: If `tests/data/unicode/` holds no files of `version`.
    """
    breaks = bytearray(_CODE_POINTS)
    for first, last, fields in _entries(_path("GraphemeBreakProperty", version)):
        breaks[first : last + 1] = bytes([BREAK_VALUES.index(fields[0])]) * (
            last - first + 1
        )

    pictographic = bytearray(_CODE_POINTS)
    for first, last, fields in _entries(_path("emoji-data", version)):
        if fields[0] == "Extended_Pictographic":
            pictographic[first : last + 1] = b"\x01" * (last - first + 1)

    conjunct = bytearray(_CODE_POINTS)
    if _number(version) >= (15, 1):
        for first, last, fields in _entries(_path("DerivedCoreProperties", version)):
            if fields[0] == "InCB":
                conjunct[first : last + 1] = bytes(
                    [CONJUNCT_VALUES.index(fields[1])]
                ) * (last - first + 1)

    return Unicode(version, bytes(breaks), bytes(pictographic), bytes(conjunct))


def cases(version: str) -> tuple[tuple[str, frozenset[int]], ...]:
    """Return each case of the `GraphemeBreakTest.txt` of `version`.

    Returns:
        Each case's text, and the offsets inside it where the file marks a boundary;
        the file also marks both ends, which are left out, as `Unicode.boundaries`
        leaves them out.

    Raises:
        FileNotFoundError: If `tests/data/unicode/` holds no test file of `version`.
    """
    found = []
    text = _path("GraphemeBreakTest", version).read_text(encoding="utf-8")
    for line in text.splitlines():
        tokens = line.partition("#")[0].split()
        if not tokens:
            continue

        chars: list[str] = []
        breaks = set()
        for token in tokens[1:-1]:
            if token == "\N{DIVISION SIGN}":
                breaks.add(len(chars))
            elif token != "\N{MULTIPLICATION SIGN}":
                chars.append(chr(int(token, 16)))
        found.append(("".join(chars), frozenset(breaks)))

    return tuple(found)


def _path(name: str, version: str) -> Traversable:
    """Return the file `name` of `version` in `tests/data/unicode/`."""
    return (
        files("tests") / "data" / "unicode" / f"{name}_{version.replace('.', '_')}.txt"
    )


def _entries(path: Traversable) -> Iterator[tuple[int, int, tuple[str, ...]]]:
    """Yield the first and last code point and the other fields of each data line."""
    for line in path.read_text(encoding="utf-8").splitlines():
        data = line.partition("#")[0].strip()
        if data:
            fields = tuple(field.strip() for field in data.split(";"))
            first, _, last = fields[0].partition("..")
            yield int(first, 16), int(last or first, 16), fields[1:]


def _number(version: str) -> tuple[int, ...]:
    """Return `version` as a tuple of numbers, which compare as versions do."""
    return tuple(int(part) for part in version.split("."))


def _joined(previous: int, value: int) -> bool | None:
    """Return whether the rules up to GB9b keep two characters together.

    Returns:
        `True` or `False` from the first rule up to GB9b that applies to the pair of
        Grapheme_Cluster_Break values, or `None` when none applies.
    """
    if previous == _CR and value == _LF:
        return True
    if _CONTROL in (previous, value) or {previous, value} & {_CR, _LF}:
        return False
    if (previous, value) in _HANGUL or value in (_EXTEND, _ZWJ, _SPACING):
        return True
    if previous == _PREPEND:
        return True
    return None


def _pictograph_state(state: int, value: int, pictographic: int) -> int:
    """Return the GB11 state after a character, from the state before it."""
    if pictographic:
        return _PICTOGRAPH_SEEN
    if state == _PICTOGRAPH_SEEN and value == _EXTEND:
        return _PICTOGRAPH_SEEN
    if state == _PICTOGRAPH_SEEN and value == _ZWJ:
        return _PICTOGRAPH_JOINED
    return 0


def _no_conjuncts(state: int, conjunct: int) -> int:
    """Return the GB9c state of a version without GB9c: never linked."""
    return 0


def _consonant_led(state: int, conjunct: int) -> int:
    """Return the GB9c state of 15.1.0 to 17.0.0 after a character.

    These versions keep a consonant whole with a consonant, linkers, and extenders
    before it, once a linker is among them.
    """
    if conjunct == _CONSONANT:
        return _CONSONANT_SEEN
    if state and conjunct == _LINKER:
        return _LINKED
    if state and conjunct == _CONJUNCT_EXTEND:
        return state
    return 0


def _linker_led(state: int, conjunct: int) -> int:
    """Return the GB9c state of 18.0.0 on, which needs only a linker and extenders."""
    if conjunct == _LINKER:
        return _LINKED
    if state == _LINKED and conjunct == _CONJUNCT_EXTEND:
        return _LINKED
    return 0


def _conjunct_rule(version: str) -> Callable[[int, int], int]:
    """Return the function that steps the GB9c state of `version`."""
    number = _number(version)
    if number < (15, 1):
        return _no_conjuncts
    if number < (18, 0):
        return _consonant_led
    return _linker_led
