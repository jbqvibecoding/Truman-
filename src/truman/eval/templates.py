"""Eval templates — per-vertical seed library + cohort archetype metadata.

The deterministic mock Eval Recommender pulls from these templates so its
output is reproducible. The taxonomy + cohort labels are lightly ported from
MiroFish (`oasis_profile_generator.py:156-180` for the entity-type spirit and
`simulation_config_generator.py:597-609` for the sample-size heuristic).

Keep this file dependency-free (no LLM imports, no runtime side effects) so it
can be loaded at module import time without cost.
"""

from __future__ import annotations

from truman.eval.schema import CheckKind, EvalQuestion

# ─── Cohort archetypes (lightweight; full library is M3) ────────────────────
# Used by the recommender to estimate "how many personas roughly cover the
# target audience" for each vertical. Keep names aligned with PRD §4.3.2.
COHORT_ARCHETYPES: dict[str, list[str]] = {
    "ad_creative": ["小红书用户", "TikTok用户", "美国宝妈", "Web3 Degens", "GenZ"],
    "headline": ["news reader", "busy parent", "casual scroller", "industry pro"],
    "viral_content": ["Reddit user", "Twitter user", "小红书 女生", "Web3 KOL", "黑粉", "路人"],
}


def _q(id_: str, prompt: str, kind: CheckKind, weight: float = 1.0, **cfg) -> EvalQuestion:
    return EvalQuestion(id=id_, prompt=prompt, check_kind=kind, config=cfg or {}, weight=weight)


_HEADLINE_TEMPLATES: list[EvalQuestion] = [
    _q("hl_len", "Is the headline between 30 and 90 characters?",
       CheckKind.LENGTH, weight=0.25, field="content", min=30, max=90),
    _q("hl_no_banned", "Does the headline avoid banned filler words "
       "['game-changer', 'best part', \"here's the kicker\", 'revolutionary']?",
       CheckKind.REGEX, weight=0.25,
       field="content", forbid=["game-changer", "best part", "here's the kicker", "revolutionary"]),
    _q("hl_concrete", "Does the headline contain a number, a specific entity, or a sensory detail?",
       CheckKind.LLM_JUDGE, weight=0.25, field="content"),
    _q("hl_engagement", "Does the simulated avg_engagement metric clear 0.5?",
       CheckKind.RANGE, weight=0.25, metric="avg_engagement", op=">=", value=0.5),
]


_AD_CREATIVE_TEMPLATES: list[EvalQuestion] = [
    _q("ad_hook_short", "Is the hook 12 words or fewer (so it fits the first 2 seconds)?",
       CheckKind.LENGTH, weight=0.2, field="fields.hook", min=1, max=80),
    _q("ad_cta_present", "Does the script mention a clear call-to-action verb "
       "(try, buy, get, download, sign up, learn)?",
       CheckKind.REGEX, weight=0.15,
       field="fields.script", require=["try", "buy", "get", "download", "sign up", "learn"]),
    _q("ad_no_filler", "Does the creative avoid filler ['game-changer', \"here's the kicker\"]?",
       CheckKind.REGEX, weight=0.1, field="content",
       forbid=["game-changer", "here's the kicker"]),
    _q("ad_specific", "Does the title contain a number or a concrete benefit phrase?",
       CheckKind.LLM_JUDGE, weight=0.2, field="fields.title"),
    _q("ad_ctr", "Does the simulated CTR clear 0.6?",
       CheckKind.RANGE, weight=0.2, metric="ctr", op=">=", value=0.6),
    _q("ad_sentiment", "Does the simulated sentiment_ratio clear 0.5?",
       CheckKind.RANGE, weight=0.15, metric="sentiment_ratio", op=">=", value=0.5),
]


_GENERIC_TEMPLATES: list[EvalQuestion] = [
    _q("gn_len", "Is the artifact between 50 and 2000 characters?",
       CheckKind.LENGTH, weight=0.4, field="content", min=50, max=2000),
    _q("gn_clarity", "Does the artifact open with a concrete, specific first sentence?",
       CheckKind.LLM_JUDGE, weight=0.3, field="content"),
    _q("gn_no_filler", "Does the artifact avoid filler phrases ['game-changer', 'best part']?",
       CheckKind.REGEX, weight=0.3, field="content",
       forbid=["game-changer", "best part"]),
]


_TEMPLATES: dict[str, list[EvalQuestion]] = {
    "headline": _HEADLINE_TEMPLATES,
    "ad_creative": _AD_CREATIVE_TEMPLATES,
}


def built_in_templates(vertical: str) -> list[EvalQuestion]:
    """Return a small seed list of binary Evals for a vertical.

    The mock recommender uses these directly; the LLM recommender uses them as
    few-shot examples in its system prompt.
    """
    # Return fresh copies so callers can mutate without affecting the library.
    seed = _TEMPLATES.get(vertical, _GENERIC_TEMPLATES)
    return [q.model_copy(deep=True) for q in seed]


# ─── Persona-count recommendation heuristic ──────────────────────────────────
# Ported from MiroFish's simulation_config_generator.py:597-609 (the
# `agents_per_hour` range): roughly 2 personas per audience segment, floored
# at 5 and capped at 20 so mock runs stay cheap and llm runs stay fast.

def recommended_persona_count(vertical: str, scene: dict | None) -> int:
    segments = (scene or {}).get("audience_segments") or COHORT_ARCHETYPES.get(vertical, [])
    if segments:
        return max(5, min(20, len(segments) * 2))
    return {"headline": 6, "ad_creative": 6, "viral_content": 8}.get(vertical, 6)
