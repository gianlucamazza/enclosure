from enclosure.provenance import manifest


def test_manifest_detects_changed_inputs(tmp_path):
    (tmp_path / "scenario.yaml").write_text("one")
    a = manifest(tmp_path, "scenario.yaml", "prompt", "vm")
    (tmp_path / "scenario.yaml").write_text("two")
    b = manifest(tmp_path, "scenario.yaml", "prompt changed", "vm")
    assert a["scenario_sha256"] != b["scenario_sha256"]
    assert a["prompt_sha256"] != b["prompt_sha256"]
    assert a["commit"] == "unknown"


def test_runtime_capture_uses_running_container_not_tag(monkeypatch):
    import asyncio
    from types import SimpleNamespace as NS

    from enclosure.provenance import running_images

    class Environment:
        async def connection(self):
            return NS(container="running-controller")

    def inspect(command, **kwargs):
        assert command == ["docker", "inspect", "--format", "{{.Image}}", "running-controller"]
        return NS(returncode=0, stdout="sha256:immutable\n")

    monkeypatch.setattr("enclosure.provenance.subprocess.run", inspect)
    result = asyncio.run(running_images({"default": Environment()}))
    assert result["services"]["default"]["image_id"] == "sha256:immutable"
