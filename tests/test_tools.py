from pathlib import Path

import pytest

from enclosure.netpin import resolve_args
from enclosure.tools import _http, _safe, format_thought, subject_tools


def test_thought_keeps_observation_inference_and_next_step():
    text = format_thought(
        "The notice says the alert is in effect.",
        "That contradicts the earlier status. I have not checked a second source.",
        "Open the same notice once more, then stop.",
    )
    assert "Observation: The notice says the alert is in effect." in text
    assert "Inference: That contradicts" in text
    assert text.strip().endswith("stop.")


def test_fetch_url_keeps_https_and_the_host():
    assert _http("https://www.ercot.com/services/comm/mkt_notices/detail") == (
        "https://www.ercot.com/services/comm/mkt_notices/detail"
    )


def test_curl_pins_every_host_to_the_ministry():
    args = resolve_args(["-sS", "https://news.example/story"], "10.89.0.2")
    assert "--resolve" in args
    assert "news.example:443:10.89.0.2" in args
    assert "news.example:80:10.89.0.2" in args
    assert args[-2:] == ["-sS", "https://news.example/story"]
    assert resolve_args(["-sS", "https://news.example/story"], "") == [
        "-sS",
        "https://news.example/story",
    ]


def _tool_names(tools) -> set[str]:
    return {tool.__qualname__.split(".<locals>")[0] for tool in tools}


def test_empty_desk_does_not_offer_colleagues():
    names = _tool_names(subject_tools())
    assert "ask" not in names
    assert "post" not in names


def test_occupied_desk_offers_colleagues():
    from enclosure.scenario import load_spec
    from enclosure.social import build_cast

    spec = load_spec(
        Path(__file__).resolve().parents[1] / "scenarios" / "wire" / "grid.yaml",
        treatment="T2",
    )
    names = _tool_names(subject_tools(cast=build_cast(spec, "one_party")))
    assert {"ask", "post"} <= names


def test_desk_path_cannot_leave_home():
    assert _safe("DESK") == "/home/agent/DESK"
    with pytest.raises(ValueError):
        _safe("/etc/passwd")
    with pytest.raises(ValueError):
        _safe("/home/agent/../../etc/passwd")
