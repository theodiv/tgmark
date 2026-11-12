import re

from tgmark import __version__


def test_version_reads_release_or_release_candidate() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:rc\d+)?", __version__) is not None
