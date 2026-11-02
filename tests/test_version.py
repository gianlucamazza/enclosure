from importlib.metadata import version

import enclosure


def test_version_matches_metadata():
    assert enclosure.__version__ == version("enclosure")
