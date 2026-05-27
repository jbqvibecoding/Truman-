"""Worker layer contracts — the producers of candidate artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from truman.goal.schema import GoalConfig
    from truman.judge.verdict import JudgeVerdict
    from truman.research.base import ResearchBrief


@dataclass
class CandidateArtifact:
    """A single produced artifact (e.g. a headline) at one iteration."""

    iteration: int
    kind: str
    content: str
    rationale: str = ""
    parent_iteration: int | None = None


@runtime_checkable
class WorkerProvider(Protocol):
    """Produces and revises artifacts toward the goal."""

    def create(self, goal: GoalConfig, brief: ResearchBrief, plan: str) -> CandidateArtifact:
        """Produce the first candidate."""
        ...

    def revise(
        self,
        goal: GoalConfig,
        brief: ResearchBrief,
        plan: str,
        previous: CandidateArtifact,
        verdict: JudgeVerdict,
    ) -> CandidateArtifact:
        """Produce an improved candidate using judge feedback."""
        ...
