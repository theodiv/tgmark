import pytest

from tests.support.segmentation import (
    BREAK_VALUES,
    CONJUNCT_VALUES,
    NEWEST,
    VERSIONS,
    cases,
    load,
)


@pytest.mark.parametrize("version", VERSIONS)
def test_finds_the_boundaries_of_every_case_of_the_version(version: str) -> None:
    unicode = load(version)
    found = cases(version)
    assert found
    assert [text for text, breaks in found if unicode.boundaries(text) != breaks] == []


@pytest.mark.parametrize(
    ("version", "char", "properties"),
    [
        pytest.param("14.0.0", "\U00011a3a", ("Prepend", 0, "None"), id="prepend"),
        pytest.param("17.0.0", "\U00011a3a", ("Other", 0, "None"), id="other"),
        pytest.param("18.0.0", "\U00011a3a", ("Other", 0, "Linker"), id="linker"),
        pytest.param("18.0.0", "\U0001f600", ("Other", 1, "None"), id="pictographic"),
        pytest.param("15.1.0", "\u0915", ("Other", 0, "Consonant"), id="consonant"),
        pytest.param("15.0.0", "\u0915", ("Other", 0, "None"), id="no-conjuncts"),
    ],
)
def test_loads_the_properties_of_the_version(
    version: str, char: str, properties: tuple[str, int, str]
) -> None:
    unicode = load(version)
    code = ord(char)
    assert (
        BREAK_VALUES[unicode.breaks[code]],
        unicode.pictographic[code],
        CONJUNCT_VALUES[unicode.conjunct[code]],
    ) == properties


@pytest.mark.parametrize(
    ("version", "boundaries"),
    [
        # Before 18.0.0, GB9c needs a consonant before the linker.
        pytest.param("17.0.0", frozenset({1}), id="consonant-led"),
        pytest.param(NEWEST, frozenset(), id="linker-led"),
    ],
)
def test_keeps_a_lone_linker_with_the_consonant_after_it(
    version: str, boundaries: frozenset[int]
) -> None:
    assert load(version).boundaries("\u094d\u0915") == boundaries
