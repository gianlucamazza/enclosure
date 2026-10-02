"""Every same-host link the Ministry emits resolves to a live page."""

import re
from pathlib import Path
from urllib.parse import urlparse

from enclosure.scenario import apply_scenario, load_spec
from enclosure.world import World

ROOT = Path(__file__).resolve().parents[1] / "scenarios"
HREF = re.compile(r"""(?:href|action)=["']([^"']+)["']""", re.I)


def _pages(treatment: str):
    for path in sorted(ROOT.rglob("*.yaml")):
        spec = load_spec(path, treatment=treatment)
        world = World()
        apply_scenario(world, spec)
        yield path.name, world


def test_live_pages_do_not_link_to_missing_paths():
    missing = []
    for treatment in ("T0", "T2"):
        for name, world in _pages(treatment):
            for doc in world.live_docs("http"):
                if not doc.host:
                    continue
                for raw in HREF.findall(doc.body):
                    if raw.startswith("#") or raw.startswith("mailto:"):
                        continue
                    parsed = urlparse(raw)
                    host = (parsed.hostname or doc.host).lower()
                    if parsed.hostname and host != doc.host:
                        continue
                    path = parsed.path or "/"
                    if world.http_get(host, path) is None:
                        missing.append(f"{name} {treatment} {doc.host}{doc.path} -> {raw}")
    assert missing == []
