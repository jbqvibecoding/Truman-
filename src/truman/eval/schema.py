"""Eval schema — `EvalQuestion`, `CheckKind`, `EvalRecommendation`.

These are the canonical Pydantic models used by every layer (GoalConfig,
EvalRunner, EvalRecommender, scorer). Backwards-compatible with v1 continuous
`SuccessCriterion`: a goal can have either field non-empty (or both).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class CheckKind(str, Enum):
    LLM_JUDGE = "llm_judge"
    REGEX = "regex"
    LENGTH = "length"
    RANGE = "range"
    CODE = "code"
    COMPOSED = "composed"


class EvalQuestion(BaseModel):
    """A single binary (yes/no) check applied to a candidate artifact.

    The golden rule (see docs/eval-guide.md): the prompt is a YES/NO question,
    never a 1-10 scale. `check_kind` picks the executor; `config` carries the
    executor-specific parameters.
    """

    id: str
    prompt: str
    check_kind: CheckKind
    config: dict = Field(default_factory=dict)
    weight: float = 1.0
    category: str = "default"

    @field_validator("weight")
    @classmethod
    def _weight_nonneg(cls, v: float) -> float:
        if v < 0:
            msg = f"weight must be >= 0, got {v}"
            raise ValueError(msg)
        return v


class EvalRecommendation(BaseModel):
    """Output of an Eval Recommender — what to measure AND how many to simulate.

    The user's product UI surfaces this to the user, who can edit any field
    before kicking off the auto-research loop.
    """

    evals: list[EvalQuestion]
    recommended_persona_count: int = Field(ge=1, le=200)
    rationale: str = ""
