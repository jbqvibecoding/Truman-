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
from truman.agents.mock_worker import MockWorker
from truman.agents.planner import Planner
from truman.goal.schema import GoalConfig
from truman.judge.reaction_dm import build_reaction_dm
from truman.judge.scorer import EngagementScorer
from truman.judge.verdict import JudgeVerdict
from truman.orchestrator.ledger import IterationRecord, Ledger
from truman.research.base import ResearchBrief
from truman.research.mock_researcher import MockResearcher
from truman.sim.driver import SimulationRunner
from truman.sim.personas import Persona, build_personas


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


class TrumanEngine:
    def __init__(self, goal: GoalConfig, mode: str = "mock", model: str | None = None) -> None:
        self.goal = goal
        self.mode = mode
        self.model = model
        if mode == "llm":
            from truman.agents.worker import LLMWorker
            from truman.research.llm_researcher import LLMResearcher

            self._researcher = LLMResearcher(model)
            self._worker = LLMWorker(model)
        else:
            self._researcher = MockResearcher()
            self._worker = MockWorker()
        self._planner = Planner()
        self._scorer = EngagementScorer()
        self._runner = SimulationRunner(build_reaction_dm(mode, model))

    def run_sync(self) -> RunResult:
        return asyncio.run(self.run())

    async def run(self) -> RunResult:
        goal = self.goal
        brief = self._researcher.research(goal)
        plan = self._planner.plan(goal, brief)
        personas = build_personas(goal.scene.get("topic"), goal.persona_count, goal.seed)

        ledger = Ledger()
        artifact = self._worker.create(goal, brief, plan)
        verdict: JudgeVerdict | None = None
        best = -1.0

        for _ in range(goal.max_iterations):
            result = await self._runner.run(goal, artifact, personas)
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
                )
            )

            if verdict.threshold_met:
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
