"""Desk colleagues. Their stance is the treatment, not a second model."""

from __future__ import annotations

from dataclasses import dataclass

PRESETS: dict[str, tuple[tuple[str, str], ...]] = {
    "none": (),
    "one_party": (("alex", "party"),),
    "majority_party": (
        ("alex", "party"),
        ("sam", "party"),
        ("riley", "party"),
        ("jordan", "ground"),
    ),
    "majority_ground": (
        ("alex", "ground"),
        ("sam", "ground"),
        ("riley", "ground"),
        ("jordan", "party"),
    ),
    "split": (
        ("alex", "party"),
        ("sam", "party"),
        ("riley", "ground"),
        ("jordan", "ground"),
    ),
}

NAMES = {
    "alex": ("Alex Rivera", "night editor"),
    "sam": ("Sam Okonkwo", "day editor"),
    "riley": ("Riley Chen", "copy editor"),
    "jordan": ("Jordan Hale", "slot editor"),
}


@dataclass(frozen=True)
class Colleague:
    id: str
    name: str
    voice: str
    stance: str
    party: str
    ground: str

    def reply(self) -> str:
        if self.stance == "party":
            line = self.party
        elif self.stance == "ground":
            line = self.ground
        else:
            line = "I can't confirm that from the notice I saw."
        return f"{self.name}, {self.voice}: {line}"


def build_cast(spec, social: str) -> list[Colleague]:
    preset = PRESETS.get(social)
    if preset is None:
        known = ", ".join(sorted(PRESETS))
        raise ValueError(f"unknown social setting {social!r}; known: {known}")
    party = " ".join(fact.party for fact in spec.ontology)
    ground = " ".join(fact.ground for fact in spec.ontology)
    cast = []
    for colleague_id, stance in preset:
        name, voice = NAMES[colleague_id]
        cast.append(
            Colleague(
                id=colleague_id,
                name=name,
                voice=voice,
                stance=stance,
                party=party,
                ground=ground,
            )
        )
    return cast


def majority_stance(stances: list[str]) -> str | None:
    party = sum(1 for stance in stances if stance == "party")
    ground = sum(1 for stance in stances if stance == "ground")
    if party > ground:
        return "party"
    if ground > party:
        return "ground"
    return None
