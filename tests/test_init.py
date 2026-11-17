import re
from importlib.resources import files

import tgmark
from tgmark import __version__


def test_version_reads_release_or_release_candidate() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:rc\d+)?", __version__) is not None


def test_exports_the_public_api() -> None:
    assert tgmark.__all__ == [
        "Conversion",
        "ConversionError",
        "Diagnostic",
        "Message",
        "TGMarkError",
        "convert",
    ]
    assert all(hasattr(tgmark, name) for name in tgmark.__all__)


def test_ships_its_type_marker() -> None:
    assert files("tgmark").joinpath("py.typed").is_file()
