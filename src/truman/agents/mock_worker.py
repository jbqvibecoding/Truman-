"""MockWorker — deterministic, offline artifact producer.

Baseline: a headline leading with the primary topic. Each revision appends the
next recommended angle from the brief (which are pool topics), progressively
covering more of the simulated audience's interests. This makes the simulated
engagement — and therefore the judge score — rise strictly across iterations,
which is exactly what the recursive-loop test asserts.
"""

from __future__ import annotations

from truman.agents.base import CandidateArtifact
from truman.goal.schema import GoalConfig
from truman.judge.verdict import JudgeVerdict
from truman.research.base import ResearchBrief


class MockWorker:
    def _headline(self, goal: GoalConfig, angles: list[str]) -> str:
        primary = angles[0] if angles else (goal.scene.get("topic") or "your next trip")
        hook = ": " + ", ".join(angles[1:]) if len(angles) > 1 else ""
        return f"Discover {primary}{hook} — made for you."

    def create(self, goal: GoalConfig, brief: ResearchBrief, plan: str) -> CandidateArtifact:
        angles = brief.recommended_angles[:1] or [goal.scene.get("topic") or "travel"]
        return CandidateArtifact(
            iteration=0,
            kind=goal.artifact_kind,
            content=self._headline(goal, angles),
            rationale="Baseline: lead with the primary angle.",
            parent_iteration=None,
        )

    def revise(
        self,
        goal: GoalConfig,
        brief: ResearchBrief,
        plan: str,
        previous: CandidateArtifact,
        verdict: JudgeVerdict,
    ) -> CandidateArtifact:
        # Incorporate one more angle than the previous iteration used.
        n_angles = min(previous.iteration + 2, len(brief.recommended_angles))
        angles = brief.recommended_angles[:n_angles] or [goal.scene.get("topic") or "travel"]
        return CandidateArtifact(
            iteration=previous.iteration + 1,
            kind=goal.artifact_kind,
            content=self._headline(goal, angles),
            rationale=f"Revised to address: {verdict.feedback}",
            parent_iteration=previous.iteration,
        )
