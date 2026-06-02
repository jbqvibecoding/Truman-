"""Goal Layer — the system input is a RESULT, not a task.

A goal is defined by natural-language intent + quantitative success criteria
+ a threshold the simulated outcome must beat. This encodes the goal-driven
philosophy: loop until the criteria are met.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from truman.eval.schema import EvalQuestion


class SuccessCriterion(BaseModel):
    """One scored dimension of success (v1 continuous-metric path).

    `metric` is a key produced by the Judge into SimulationResult.metrics
    (e.g. "avg_engagement", "positive_ratio"). For the new v2 binary path,
    use `evals` instead (see EvalQuestion).
    """

    name: str
    metric: str
    weight: float = 1.0


class GoalConfig(BaseModel):
    """A complete goal specification loaded from YAML."""

    goal: str
    vertical: str = "headline"
    artifact_kind: str = "text_headline"
    criteria: list[SuccessCriterion] = Field(default_factory=list)
    evals: list[EvalQuestion] = Field(default_factory=list)  # v2 binary path
    threshold: float = 0.7
    max_iterations: int = 5
    persona_count: int = 6
    ticks_per_sim: int = 3
    scene: dict = Field(default_factory=dict)
    seed: int = 0
    # v2 stop-condition knobs (None = disabled)
    budget_tokens: int | None = None
    plateau_window: int | None = None

    @field_validator("threshold")
    @classmethod
    def _threshold_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            msg = f"threshold must be in [0, 1], got {v}"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def _at_least_one_dimension(self):
        if not self.criteria and not self.evals:
            msg = "GoalConfig requires at least one of `criteria` (v1, continuous) or `evals` (v2, binary)."
            raise ValueError(msg)
        return self

    @property
    def total_weight(self) -> float:
        return sum(c.weight for c in self.criteria) or 1.0

    @property
    def total_eval_weight(self) -> float:
        return sum(q.weight for q in self.evals) or 1.0
