"""Personas — the simulated audience.

Ported in spirit from MiroFish's OasisAgentProfile + its rule-based fallback
(oasis_profile_generator.py): rich persona fields plus Truman extensions
(stance, sentiment_bias, influence_weight). The mock generator is fully
deterministic from a seed so the recursive loop is reproducible; the LLM
generator (build_personas_llm) mirrors MiroFish's prompt for real runs.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

# Base topic keywords appended to the primary goal topic to form the pool.
# Personas are assigned topics round-robin over the pool, and the Worker's
# revisions append pool topics into the artifact — so coverage (and thus
# simulated engagement) rises monotonically across iterations.
_BASE_TOPICS = ["deals", "tips", "family", "adventure", "luxury", "solo"]

_MBTIS = ["INTJ", "ENFP", "ISTP", "ESFJ", "INFP", "ENTJ"]
_COUNTRIES = ["US", "UK", "JP", "BR", "DE", "IN"]
_PROFESSIONS = ["student", "engineer", "parent", "creator", "retiree", "founder"]
_STANCES = ["enthusiast", "skeptic", "neutral"]


def topic_pool(primary_topic: str | None, size: int = 6) -> list[str]:
    """Build a deterministic, de-duplicated topic pool led by the primary topic."""
    primary = (primary_topic or "travel").strip().lower()
    pool: list[str] = [primary]
    for t in _BASE_TOPICS:
        if t not in pool:
            pool.append(t)
        if len(pool) >= size:
            break
    return pool[:size]


@dataclass
class Persona:
    """A simulated audience member."""

    agent_id: str
    name: str
    bio: str
    persona: str
    mbti: str
    country: str
    profession: str
    interested_topics: list[str]
    stance: str
    sentiment_bias: float  # -1..1
    influence_weight: float = 1.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_props(self) -> dict[str, Any]:
        """WorldSeed agent entity properties (engine-visible state)."""
        return {
            "location": "feed",
            "engaged": False,
            "last_intensity": 0.0,
            "stance": self.stance,
        }

    def to_character(self) -> dict[str, Any]:
        """WorldSeed character card (free-form; never read by the engine)."""
        return {
            "name": self.name,
            "personality": self.persona,
            "bio": self.bio,
            "mbti": self.mbti,
            "country": self.country,
            "profession": self.profession,
            "interested_topics": self.interested_topics,
            "stance": self.stance,
        }


def build_personas(primary_topic: str | None, count: int, seed: int) -> list[Persona]:
    """Deterministically generate `count` personas from a seed (offline/mock)."""
    pool = topic_pool(primary_topic, size=6)
    rng = random.Random(seed)
    personas: list[Persona] = []
    for i in range(count):
        topics = [pool[(2 * i) % len(pool)], pool[(2 * i + 1) % len(pool)]]
        bias = round(rng.uniform(-0.6, 0.9), 3)
        mbti = _MBTIS[i % len(_MBTIS)]
        country = _COUNTRIES[i % len(_COUNTRIES)]
        profession = _PROFESSIONS[i % len(_PROFESSIONS)]
        stance = _STANCES[i % len(_STANCES)]
        name = f"persona_{i + 1}"
        bio = f"A {profession} from {country} interested in {', '.join(topics)}."
        persona_desc = (
            f"{name} is a {mbti} {profession}. They care about {topics[0]} and {topics[1]}, "
            f"and tend to be a {stance} who reacts {'positively' if bias >= 0 else 'critically'}."
        )
        personas.append(
            Persona(
                agent_id=name,
                name=name,
                bio=bio,
                persona=persona_desc,
                mbti=mbti,
                country=country,
                profession=profession,
                interested_topics=topics,
                stance=stance,
                sentiment_bias=bias,
                influence_weight=1.0,
            )
        )
    return personas
