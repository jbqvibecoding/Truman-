"""Goal Layer — the system input is a RESULT, not a task.

A goal is defined by natural-language intent + quantitative success criteria
+ a threshold the simulated outcome must beat. This encodes the goal-driven
philosophy: loop until the criteria are met.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class SuccessCriterion(BaseModel):
    """One scored dimension of success.

    `metric` is a key produced by the Judge into SimulationResult.metrics
    (e.g. "avg_engagement", "positive_ratio").
    """

    name: str
    metric: str
    weight: float = 1.0


class GoalConfig(BaseModel):
    """A complete goal specification loaded from YAML."""

    goal: str
    vertical: str = "headline"
    artifact_kind: str = "text_headline"
    criteria: list[SuccessCriterion] = Field(min_length=1)
    threshold: float = 0.7
    max_iterations: int = 5
    persona_count: int = 6
    ticks_per_sim: int = 3
    scene: dict = Field(default_factory=dict)
    seed: int = 0

    @field_validator("threshold")
    @classmethod
    def _threshold_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            msg = f"threshold must be in [0, 1], got {v}"
            raise ValueError(msg)
        return v

    @property
    def total_weight(self) -> float:
        return sum(c.weight for c in self.criteria) or 1.0
