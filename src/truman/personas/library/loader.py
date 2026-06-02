"""Load cohorts and materialize them into deterministic Persona lists.

`load_cohort(name)` fetches a built-in cohort by name. `build_personas_from_cohort`
distributes `count` personas across the cohort's segments (round-robin), then
samples each persona's attributes deterministically from the segment's pools
using a seeded RNG so the same (cohort, count, seed) always yields the same
personas — the autoresearch reproducibility discipline.
"""

from __future__ import annotations

import random

from truman.personas.library.cohorts import COHORTS, Cohort, SegmentArchetype
from truman.sim.personas import Persona


def available_cohorts() -> list[str]:
    return sorted(COHORTS)


def load_cohort(name: str) -> Cohort:
    if name not in COHORTS:
        msg = f"Unknown cohort {name!r}. Available: {', '.join(available_cohorts())}"
        raise ValueError(msg)
    return COHORTS[name]


def _weighted_choice(items: list[str], weights: list[float], rng: random.Random) -> str:
    """Pick one item by weights (no numpy)."""
    total = sum(weights) or 1.0
    pick = rng.random() * total
    cum = 0.0
    for item, w in zip(items, weights):
        cum += w
        if pick <= cum:
            return item
    return items[-1]


def _persona_from_segment(
    seg: SegmentArchetype,
    segment_idx: int,
    persona_idx: int,
    rng: random.Random,
) -> Persona:
    mbti = rng.choice(seg.mbti_pool) if seg.mbti_pool else "ENFP"
    country = rng.choice(seg.country_pool) if seg.country_pool else "US"
    profession = rng.choice(seg.profession_pool) if seg.profession_pool else "user"
    topics = list(seg.interest_topics[:3]) if seg.interest_topics else ["general"]
    if len(topics) > 2:
        topics = rng.sample(topics, k=min(3, len(topics)))

    lo, hi = seg.sentiment_bias_range
    sentiment_bias = round(rng.uniform(lo, hi), 3)
    wlo, whi = seg.influence_weight_range
    influence_weight = round(rng.uniform(wlo, whi), 3)

    stances = list(seg.stance_dist.keys())
    weights = list(seg.stance_dist.values())
    stance = _weighted_choice(stances, weights, rng) if stances else "neutral"

    aid = f"{seg.label}_{persona_idx + 1}".replace(" ", "_")
    name = f"{seg.label} #{persona_idx + 1}"
    bio = (
        f"A {profession} from {country} in the {seg.label} segment, interested in "
        f"{', '.join(topics)}."
    )
    persona_desc = (
        f"{name} — {seg.description} {mbti} {profession}, "
        f"{'positive' if sentiment_bias >= 0 else 'critical'} stance, "
        f"{stance} toward the topic."
    )
    return Persona(
        agent_id=aid,
        name=name,
        bio=bio,
        persona=persona_desc,
        mbti=mbti,
        country=country,
        profession=profession,
        interested_topics=topics,
        stance=stance,
        sentiment_bias=sentiment_bias,
        influence_weight=influence_weight,
        extra={"cohort_segment": seg.label, "segment_idx": segment_idx},
    )


def build_personas_for_scene(
    scene: dict,
    count: int,
    seed: int = 0,
) -> list[Persona] | None:
    """Dispatcher: returns personas if `scene` specifies a cohort or upload.

    Priority: user_upload_json > user_upload_csv > cohort > None (caller falls
    back to the deterministic / LLM generators in `sim/personas.py`).
    """
    from truman.personas.library.user_upload import (
        load_personas_from_csv,
        load_personas_from_json,
    )

    if not scene:
        return None
    if scene.get("persona_upload_json"):
        return load_personas_from_json(scene["persona_upload_json"])[:count] or None
    if scene.get("persona_upload_csv"):
        return load_personas_from_csv(scene["persona_upload_csv"])[:count] or None
    cohort_name = scene.get("cohort")
    if cohort_name:
        return build_personas_from_cohort(cohort_name, count, seed)
    return None


def build_personas_from_cohort(
    cohort: Cohort | str,
    count: int,
    seed: int = 0,
) -> list[Persona]:
    """Materialize `count` personas across the cohort's segments (round-robin).

    Distribution is roughly uniform across segments; remainder personas go to
    the first few segments. Each persona is sampled from its segment's pools
    using `random.Random(seed + persona_idx)` so each persona is independent
    yet the whole list is deterministic in (cohort, count, seed).
    """
    if isinstance(cohort, str):
        cohort = load_cohort(cohort)
    if count < 1:
        return []
    segs = cohort.segments
    if not segs:
        return []
    personas: list[Persona] = []
    per_segment_counters: dict[int, int] = {i: 0 for i in range(len(segs))}
    for i in range(count):
        seg_idx = i % len(segs)
        seg = segs[seg_idx]
        # Per-persona RNG so reordering count doesn't shuffle earlier personas.
        rng = random.Random(seed * 1009 + i * 17 + seg_idx)
        p = _persona_from_segment(seg, seg_idx, per_segment_counters[seg_idx], rng)
        personas.append(p)
        per_segment_counters[seg_idx] += 1
    return personas
