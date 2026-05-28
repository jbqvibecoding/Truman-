"""SimulationResult — the output of one simulation run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from truman.agents.base import CandidateArtifact


@dataclass
class SimulationResult:
    """What the simulated world did with one candidate artifact."""

    artifact: CandidateArtifact
    per_persona: dict[str, dict[str, Any]]  # agent_id -> {engaged, intensity, action, reaction}
    events: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    # Snapshot of the `artifact` entity's properties after the tick (the
    # authoritative state the DM wrote). Verticals read whatever counters they
    # incremented (e.g. engagement_score, or clicks/dwell_total/sentiment_total).
    artifact_state: dict[str, Any] = field(default_factory=dict)
