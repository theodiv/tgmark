import unicodedata

import pytest

from tests.support.segmentation import NEWEST, Unicode, load

# The running Python's Unicode version, whose characters `unicodedata` knows, and the
# newest, whose characters current readers' devices show.
_VERSIONS = sorted({unicodedata.unidata_version, NEWEST})


@pytest.fixture(scope="session", params=_VERSIONS)
def reference(request: pytest.FixtureRequest) -> Unicode:
    """Return the rules of the running Python's Unicode version, then the newest."""
    return load(request.param)


@pytest.fixture(scope="session")
def references() -> tuple[Unicode, ...]:
    """Return the rules of the running Python's Unicode version and the newest."""
    return tuple(load(version) for version in _VERSIONS)
