"""Memory Hole: retroactive rewrite of live world documents."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit

from enclosure.workspace import maybe_sync
from enclosure.world import World

HoleMode = Literal["world_only", "deep"]


def memory_hole(
    world: World,
    fact_id: str,
    mode: HoleMode = "world_only",
) -> dict:
    """Withdraw a Party fact from every live locator that carried it.

    world_only: restore the last version of each locator that did not carry
    the fact (or 404 if none). The subject's earlier observations stay in
    its transcript — that is the inconsistency test.

    deep: also rewrite filesystem copies whose origin is a holed HTTP doc.
    """
    fact = world.get_fact(fact_id)
    if fact is None:
        raise KeyError(f"unknown fact: {fact_id}")

    touched: list[dict] = []
    for doc in world.live_docs_with_fact(fact_id):
        predecessor = world.latest_without_fact(doc.channel, doc.host, doc.path, fact_id)
        if predecessor is not None:
            world.make_live(predecessor.id)
            action = "restored"
            restored_id = predecessor.id
        else:
            world.unlive(doc.id)
            action = "unlived"
            restored_id = None
        record = {
            "locator": {
                "channel": doc.channel,
                "host": doc.host,
                "path": doc.path,
            },
            "holed_id": doc.id,
            "holed_version": doc.version,
            "action": action,
            "restored_id": restored_id,
        }
        if mode == "deep":
            record["deep_fs"] = _hole_derived_fs(world, doc, fact_id)
        touched.append(record)

    world.set_fact_injected(fact_id, False)
    synced = maybe_sync(world)
    event = world.log(
        "memory_hole",
        {"fact_id": fact_id, "mode": mode, "touched": touched, "synced": synced},
    )
    return {
        "fact_id": fact_id,
        "mode": mode,
        "event_id": event.id,
        "touched": touched,
        "still_injected": False,
        "synced": synced,
    }


def _hole_derived_fs(world: World, http_doc, fact_id: str) -> list[str]:
    rewritten: list[str] = []
    for fs_doc in world.live_docs("fs"):
        origin = urlsplit(fs_doc.origin or "")
        if (
            origin.scheme not in {"http", "https"}
            or origin.hostname != http_doc.host
            or (origin.path or "/") != http_doc.path
        ):
            continue
        predecessor = world.latest_without_fact("fs", None, fs_doc.path, fact_id)
        # If this file is a saved copy of the holed page, blank or restore.
        if predecessor is not None:
            world.make_live(predecessor.id)
        else:
            world.unlive(fs_doc.id)
        rewritten.append(fs_doc.path)
    return rewritten
