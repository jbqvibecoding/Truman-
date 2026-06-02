"""TrumanEngine — the recursive feedback loop (the master controller).

Implements the goal-driven master/criteria loop fused with autoresearch's
keep/reject ledger:

    research -> plan -> generate candidate
    loop:
        simulate (WorldSeed) -> judge -> record in ledger
        if score >= threshold: deliver, stop
        else: feed judge feedback back to the worker -> revise
    stop on threshold or max_iterations.

Mode "mock" runs fully offline (deterministic). Mode "llm" swaps in the
LiteLLM-backed research/worker and WorldSeed's real DM judge.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from truman.agents.base import CandidateArtifact
from truman.agents.planner import Planner
from truman.eval.runner import EvalRunner
from truman.goal.schema import GoalConfig
from truman.judge.scorer import EngagementScorer
from truman.judge.verdict import JudgeVerdict
from truman.orchestrator.ledger import IterationRecord, Ledger
from truman.research.base import ResearchBrief
from truman.sim.driver import SimulationRunner
from truman.sim.personas import Persona
from truman.verticals.registry import get_vertical


@dataclass
class RunResult:
    ledger: Ledger
    final_artifact: CandidateArtifact
    final_verdict: JudgeVerdict
    brief: ResearchBrief
    personas: list[Persona] = field(default_factory=list)

    @property
    def delivered(self) -> bool:
        return self.final_verdict.threshold_met


def _budget_exhausted(goal: GoalConfig, ledger: Ledger) -> bool:
    """Stop when cumulative cost crosses the user's token budget (None = off)."""
    if goal.budget_tokens is None:
        return False
    return ledger.cumulative_cost() >= goal.budget_tokens


def _plateau_hit(goal: GoalConfig, ledger: Ledger) -> bool:
    """Stop when no score in the last `plateau_window` rows beat the best earlier.

    None / unset disables. Requires at least window+1 records to fire — this
    keeps the first few iterations free to explore.
    """
    w = goal.plateau_window
    if w is None or w <= 0:
        return False
    scores = [r.score for r in ledger.records]
    if len(scores) < w + 1:
        return False
    best_before = max(scores[:-w])
    return max(scores[-w:]) <= best_before


class TrumanEngine:
    def __init__(self, goal: GoalConfig, mode: str = "mock", model: str | None = None) -> None:
        self.goal = goal
        self.mode = mode
        self.model = model
        self._vertical = get_vertical(goal.vertical)
        self._researcher = self._vertical.make_research(mode, model)
        self._worker = self._vertical.make_creative(mode, model)
        self._planner = Planner()
        self._scorer = EngagementScorer()
        self._runner = SimulationRunner(
            self._vertical.make_dm(mode, model),
            decider=self._vertical.make_decider(mode, model),
            scene_builder=self._vertical.build_scene,
            metrics_fn=self._vertical.compute_metrics,
        )
        self._eval_runner = EvalRunner(mode=mode, model=model)

    def run_sync(self) -> RunResult:
        return asyncio.run(self.run())

    async def run(self) -> RunResult:
        goal = self.goal
        brief = self._researcher.research(goal)
        plan = self._planner.plan(goal, brief)
        personas = self._vertical.make_personas(goal, self.mode, self.model)

        ledger = Ledger()
        artifact = self._worker.create(goal, brief, plan)
        verdict: JudgeVerdict | None = None
        best = -1.0

        for _ in range(goal.max_iterations):
            result = await self._runner.run(goal, artifact, personas)
            # v2: if binary evals are configured, run them and populate the
            # result so the scorer takes the binary path.
            if goal.evals:
                result.per_eval = await self._eval_runner.run_async(
                    goal.evals, artifact, result.metrics,
                )
            verdict = self._scorer.score(goal, result)

            if verdict.threshold_met:
                status = "delivered"
            elif verdict.score > best:
                status = "kept"
            else:
                status = "rejected"
            best = max(best, verdict.score)

            ledger.append(
                IterationRecord(
                    iteration=artifact.iteration,
                    artifact_content=artifact.content,
                    score=verdict.score,
                    threshold=goal.threshold,
                    status=status,
                    feedback=verdict.feedback,
                    description=artifact.rationale,
                    per_eval=dict(result.per_eval),
                    parent_iteration=artifact.parent_iteration,
                )
            )

            if verdict.threshold_met:
                break
            # v2 stop conditions: budget cap or plateau before next revise.
            if _budget_exhausted(goal, ledger) or _plateau_hit(goal, ledger):
                break
            artifact = self._worker.revise(goal, brief, plan, artifact, verdict)

        assert verdict is not None  # max_iterations >= 1 guaranteed by schema
        return RunResult(
            ledger=ledger,
            final_artifact=artifact,
            final_verdict=verdict,
            brief=brief,
            personas=personas,
        )
