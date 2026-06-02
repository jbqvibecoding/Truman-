"""EvalRecommender — AI suggests Evals + a persona count from a goal.

The deterministic `MockEvalRecommender` mirrors MiroFish's
`simulation_config_generator.py:597-609` heuristic (~2 personas per audience
segment, floored at 5, capped at 20) and reuses the per-vertical seed library
in `templates.py`. The `LLMEvalRecommender` mirrors the LLM-orchestration
pattern from MiroFish's `simulation_config_generator.py:243-379` (single
structured JSON call), with robust retry via `utils.safe_extract_json_with_retry`.

Both return the same `EvalRecommendation` shape: evals + persona count +
rationale. The user can edit any field downstream — see PRD §4.2.5.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from truman.eval.schema import EvalQuestion, EvalRecommendation
from truman.eval.templates import (
    COHORT_ARCHETYPES,
    built_in_templates,
    recommended_persona_count,
)

if TYPE_CHECKING:
    from truman.goal.schema import GoalConfig


class MockEvalRecommender:
    """Offline deterministic recommender: template-driven, no LLM call."""

    def recommend(self, goal: GoalConfig) -> EvalRecommendation:
        seed = built_in_templates(goal.vertical)
        # Cap at 6 to honour the golden rule (3-6 evals; > 6 invites gaming).
        evals = seed[:6]
        persona_count = recommended_persona_count(goal.vertical, goal.scene)
        segments = (goal.scene or {}).get("audience_segments") or COHORT_ARCHETYPES.get(goal.vertical, [])
        rationale = (
            f"Seeded {len(evals)} binary Evals from the '{goal.vertical}' template library "
            f"(see docs/eval-guide.md golden rule). Recommended persona_count={persona_count} "
            f"≈ 2 × |segments|={len(segments)} (MiroFish heuristic; floored at 5, capped at 20)."
        )
        return EvalRecommendation(
            evals=evals,
            recommended_persona_count=persona_count,
            rationale=rationale,
        )


class LLMEvalRecommender:
    """Real LLM recommender: single structured Anthropic call + retry."""

    def __init__(self, model: str | None = None) -> None:
        self._model = model
        self._fallback = MockEvalRecommender()

    def _build_prompt(self, goal: GoalConfig) -> tuple[str, str]:
        from truman.eval.utils import EVAL_GUIDE_SYSTEM_PROMPT

        seed = built_in_templates(goal.vertical)
        seed_json = json.dumps(
            [q.model_dump(mode="json") for q in seed[:3]],
            ensure_ascii=False, indent=2,
        )
        segments = (goal.scene or {}).get("audience_segments") or COHORT_ARCHETYPES.get(goal.vertical, [])
        baseline = recommended_persona_count(goal.vertical, goal.scene)
        user = (
            f"Vertical: {goal.vertical}\n"
            f"Goal: {goal.goal}\n"
            f"Scene context: {json.dumps(goal.scene or {}, ensure_ascii=False)}\n"
            f"Known audience segments ({len(segments)}): {segments}\n\n"
            f"Few-shot seed evals for this vertical (as inspiration, you can replace):\n{seed_json}\n\n"
            "Recommend 3-6 binary EvalQuestions for this goal.\n"
            "Each item: id (short, snake_case), prompt (yes/no question), "
            'check_kind (one of: "llm_judge","regex","length","range","code","composed"), '
            "config (executor-specific), weight (sum to ~1.0), category.\n\n"
            f"Also recommend `recommended_persona_count` (integer in [5, 20]); a sensible default "
            f"for this scene is ~{baseline} (~2 per segment). You can adjust based on goal complexity.\n\n"
            "Return strict JSON of the shape:\n"
            '{"evals":[...], "recommended_persona_count": N, "rationale": "1-2 sentences"}'
        )
        return EVAL_GUIDE_SYSTEM_PROMPT, user

    def recommend(self, goal: GoalConfig) -> EvalRecommendation:
        from truman.eval.utils import safe_extract_json_with_retry
        from truman.llm.runtime import complete

        system, user = self._build_prompt(goal)

        def _call() -> str:
            return complete(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                model=self._model,
                temperature=0.3,
                max_tokens=1500,
            )

        data = safe_extract_json_with_retry(_call, max_retries=2)
        if not isinstance(data, dict):
            return self._fallback.recommend(goal)

        try:
            evals = [EvalQuestion(**e) for e in (data.get("evals") or [])][:6]
        except Exception:
            return self._fallback.recommend(goal)
        if not evals:
            return self._fallback.recommend(goal)

        baseline = recommended_persona_count(goal.vertical, goal.scene)
        try:
            count = int(data.get("recommended_persona_count", baseline))
        except (TypeError, ValueError):
            count = baseline
        count = max(5, min(20, count))

        return EvalRecommendation(
            evals=evals,
            recommended_persona_count=count,
            rationale=str(data.get("rationale", "")).strip()
            or f"LLM recommended {len(evals)} evals; persona_count={count}.",
        )


def build_recommender(mode: str, model: str | None = None):
    """Factory: mock vs llm. Mirrors `judge.reaction_dm.build_reaction_dm`."""
    return LLMEvalRecommender(model) if mode == "llm" else MockEvalRecommender()
