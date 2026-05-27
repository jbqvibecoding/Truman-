"""JudgeVerdict — the evaluator's structured judgment of a simulation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class JudgeVerdict:
    score: float
    threshold: float
    threshold_met: bool
    per_criterion: dict[str, float] = field(default_factory=dict)
    feedback: str = ""
    weaknesses: list[str] = field(default_factory=list)
