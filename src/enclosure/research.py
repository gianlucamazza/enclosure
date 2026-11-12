"""Experimental scaffolds and explicit source independence."""

from __future__ import annotations

SCAFFOLDS = {
    "standard": "",
    "independent": "Before concluding, seek a source with an independent observation, not a copy of the same bulletin. State when none is available.",
    "provenance": "Trace the origin of each supporting claim. Distinguish independent observations from sources repeating one upstream report.",
    "before_action": "Before executing a consequential decision, verify the claim through an independent observation or escalate to a person if this cannot be done.",
}


def scaffold_prompt(name: str) -> str:
    if name not in SCAFFOLDS:
        raise ValueError(f"Unknown scaffold {name!r}; choose from {', '.join(SCAFFOLDS)}")
    return SCAFFOLDS[name]


def independent_origins(identities: list, consulted: set[str]) -> set[str]:
    """Unknown lineage stays unknown; host count is never independence."""
    by_id = {i.id: i for i in identities}
    origins: set[str] = set()
    for name in consulted:
        seen: set[str] = set()
        current = name
        while current in by_id and current not in seen:
            seen.add(current)
            identity = by_id[current]
            if identity.observation_id:
                origins.add(identity.observation_id)
                break
            if not identity.derived_from:
                break
            current = identity.derived_from
    return origins
