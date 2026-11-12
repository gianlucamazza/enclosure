from enclosure.provenance import manifest


def test_manifest_detects_changed_inputs(tmp_path):
    (tmp_path / "scenario.yaml").write_text("one")
    a = manifest(tmp_path, "scenario.yaml", "prompt", "vm")
    (tmp_path / "scenario.yaml").write_text("two")
    b = manifest(tmp_path, "scenario.yaml", "prompt changed", "vm")
    assert a["scenario_sha256"] != b["scenario_sha256"]
    assert a["prompt_sha256"] != b["prompt_sha256"]
    assert a["commit"] == "unknown"
