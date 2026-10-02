import pytest

from enclosure.tools import _http, _safe


def test_fetch_url_keeps_https_and_the_host():
    assert _http("https://www.ercot.com/services/comm/mkt_notices/detail") == (
        "https://www.ercot.com/services/comm/mkt_notices/detail"
    )


def test_desk_path_cannot_leave_home():
    assert _safe("DESK") == "/home/agent/DESK"
    with pytest.raises(ValueError):
        _safe("/etc/passwd")
    with pytest.raises(ValueError):
        _safe("/home/agent/../../etc/passwd")
