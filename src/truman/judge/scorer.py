"""EngagementScorer — the Judge Layer.

Maps a SimulationResult's metrics onto the goal's weighted success criteria to
produce a composite score in [0, 1], decides whether the threshold is met, and
generates actionable feedback for the Worker's next revision. This is Truman's
immutable evaluator (the autoresearch discipline): the same scoring function
judges every iteration, so scores are comparable across the loop.
"""

from __future__ import annotations

from truman.goal.schema import GoalConfig
from truman.judge.verdict import JudgeVerdict
from truman.sim.result import SimulationResult


class EngagementScorer:
    def score(self, goal: GoalConfig, result: SimulationResult) -> JudgeVerdict:
        per_criterion: dict[str, float] = {}
        weighted_sum = 0.0
        for crit in goal.criteria:
            value = float(result.metrics.get(crit.metric, 0.0))
            per_criterion[crit.name] = round(value, 4)
            weighted_sum += crit.weight * value
        composite = round(weighted_sum / goal.total_weight, 4)
        threshold_met = composite >= goal.threshold

        weaknesses = self._weaknesses(result)
        feedback = self._feedback(goal, result, composite, threshold_met, weaknesses)
        return JudgeVerdict(
            score=composite,
            threshold=goal.threshold,
            threshold_met=threshold_met,
            per_criterion=per_criterion,
            feedback=feedback,
            weaknesses=weaknesses,
        )

    def _weaknesses(self, result: SimulationResult) -> list[str]:
        unengaged = [aid for aid, pp in result.per_persona.items() if not pp["engaged"]]
        out: list[str] = []
        if unengaged:
            out.append(f"{len(unengaged)} persona(s) did not engage: {', '.join(sorted(unengaged))}.")
        if result.metrics.get("avg_engagement", 0.0) < 0.5:
            out.append("Average engagement is low — the hook is not compelling enough.")
        return out

    def _feedback(
        self,
        goal: GoalConfig,
        result: SimulationResult,
        composite: float,
        threshold_met: bool,
        weaknesses: list[str],
    ) -> str:
        if threshold_met:
            return f"Threshold met (score {composite} >= {goal.threshold}). Deliver."
        ask = "Broaden audience coverage by adding interest-matched angles. "
        return (
            f"Score {composite} < threshold {goal.threshold}. "
            + ask
            + (" ".join(weaknesses) if weaknesses else "")
        ).strip()
