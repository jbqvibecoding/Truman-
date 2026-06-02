"""ChangelogView — aggregated view of one Truman run's evolution.

Built from a Ledger + the per-iteration artifact_history + the GoalConfig
(for context like vertical / threshold / eval prompts). Renderers consume
this view rather than the raw RunResult so the rendering layer doesn't have
to re-derive structure on every call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from truman.agents.base import CandidateArtifact
    from truman.goal.schema import GoalConfig
    from truman.orchestrator.ledger import IterationRecord, Ledger


@dataclass
class ChangelogEntryView:
    """One iteration's contribution to the changelog (ledger row + diff)."""

    iteration: int
    parent_iteration: int | None
    status: str  # kept | rejected | delivered
    score: float
    threshold: float
    per_eval: dict[str, bool]
    cost_tokens: int
    feedback: str
    rationale: str
    content_before: str | None
    content_after: str
    diff: dict[str, dict]
    fields: dict


@dataclass
class ChangelogView:
    """Aggregated view of a Truman run's evolution, ready to render."""

    goal: Any  # GoalConfig
    entries: list[ChangelogEntryView] = field(default_factory=list)
    final_score: float = 0.0
    delivered: bool = False
    total_cost_tokens: int = 0

    @classmethod
    def from_run(
        cls,
        goal: GoalConfig,
        ledger: Ledger,
        artifact_history: list[CandidateArtifact],
    ) -> ChangelogView:
        """Build the view by pairing each IterationRecord with its artifact."""
        from truman.changelog.diff import field_diff

        # Map iteration -> artifact for quick lookup.
        by_iter: dict[int, CandidateArtifact] = {a.iteration: a for a in artifact_history}

        entries: list[ChangelogEntryView] = []
        for record in ledger.records:
            artifact = by_iter.get(record.iteration)
            if artifact is None:
                continue
            parent = by_iter.get(record.parent_iteration) if record.parent_iteration is not None else None
            entries.append(_entry_from_record(record, artifact, parent, field_diff))

        return cls(
            goal=goal,
            entries=entries,
            final_score=ledger.records[-1].score if ledger.records else 0.0,
            delivered=any(r.status == "delivered" for r in ledger.records),
            total_cost_tokens=sum(r.cost_tokens for r in ledger.records),
        )


def _entry_from_record(
    record: IterationRecord,
    artifact: CandidateArtifact,
    parent: CandidateArtifact | None,
    diff_fn,
) -> ChangelogEntryView:
    diff = diff_fn(parent, artifact)
    return ChangelogEntryView(
        iteration=record.iteration,
        parent_iteration=record.parent_iteration,
        status=record.status,
        score=record.score,
        threshold=record.threshold,
        per_eval=dict(record.per_eval),
        cost_tokens=record.cost_tokens,
        feedback=record.feedback,
        rationale=record.description or artifact.rationale,
        content_before=parent.content if parent else None,
        content_after=artifact.content,
        diff=diff,
        fields=dict(artifact.fields or {}),
    )
