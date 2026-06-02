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
        """Two-path scorer: v2 binary evals if present, else v1 continuous criteria.

        When `goal.evals` is non-empty, `result.per_eval` is expected to have been
        populated by the orchestrator's EvalRunner; we aggregate booleans by
        weight. The continuous `goal.criteria` path is preserved unchanged so all
        existing tests stay green.
        """
        if goal.evals:
            return self._score_evals(goal, result)
        return self._score_criteria(goal, result)

    def _score_criteria(self, goal: GoalConfig, result: SimulationResult) -> JudgeVerdict:
        per_criterion: dict[str, float] = {}
        weighted_sum = 0.0
        for crit in goal.criteria:
            value = float(result.metrics.get(crit.metric, 0.0))
            per_criterion[crit.name] = round(value, 4)
            weighted_sum += crit.weight * value
        composite = round(weighted_sum / goal.total_weight, 4)
        threshold_met = composite >= goal.threshold

        weaknesses = self._weaknesses(goal, result, per_criterion)
        feedback = self._feedback(goal, result, composite, threshold_met, weaknesses)
        return JudgeVerdict(
            score=composite, threshold=goal.threshold, threshold_met=threshold_met,
            per_criterion=per_criterion, feedback=feedback, weaknesses=weaknesses,
        )

    def _score_evals(self, goal: GoalConfig, result: SimulationResult) -> JudgeVerdict:
        per_eval = result.per_eval or {}
        per_criterion: dict[str, float] = {}
        weighted_sum = 0.0
        for q in goal.evals:
            passed = bool(per_eval.get(q.id, False))
            per_criterion[q.id] = 1.0 if passed else 0.0
            weighted_sum += q.weight * (1.0 if passed else 0.0)
        composite = round(weighted_sum / goal.total_eval_weight, 4)
        threshold_met = composite >= goal.threshold

        failed = [q for q in goal.evals if not per_eval.get(q.id, False)]
        weaknesses: list[str] = []
        if failed:
            names = ", ".join(f"{q.id} ('{q.prompt[:60]}…')" if len(q.prompt) > 60 else f"{q.id} ('{q.prompt}')" for q in failed[:5])
            weaknesses.append(f"{len(failed)} eval(s) failed: {names}.")
        feedback = self._eval_feedback(goal, composite, threshold_met, failed)
        return JudgeVerdict(
            score=composite, threshold=goal.threshold, threshold_met=threshold_met,
            per_criterion=per_criterion, feedback=feedback, weaknesses=weaknesses,
        )

    def _eval_feedback(self, goal: GoalConfig, composite: float, met: bool, failed: list) -> str:
        if met:
            return f"Threshold met (score {composite} >= {goal.threshold}). Deliver."
        if not failed:
            return f"Score {composite} < threshold {goal.threshold}. Tighten the weakest signals."
        bullets = "; ".join(f"{q.id}: {q.prompt}" for q in failed[:5])
        return (
            f"Score {composite} < threshold {goal.threshold}. Fix these failing Evals — {bullets}"
        )

    def _weaknesses(
        self,
        goal: GoalConfig,
        result: SimulationResult,
        per_criterion: dict[str, float],
    ) -> list[str]:
        """Vertical-agnostic: unengaged audience + the weakest criterion vs threshold."""
        out: list[str] = []
        unengaged = [aid for aid, pp in result.per_persona.items() if not pp["engaged"]]
        if unengaged:
            out.append(f"{len(unengaged)} persona(s) did not engage: {', '.join(sorted(unengaged))}.")
        below = {name: v for name, v in per_criterion.items() if v < goal.threshold}
        if below:
            worst = min(below, key=below.get)
            out.append(f"Weakest metric '{worst}' = {below[worst]} (below threshold {goal.threshold}).")
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
