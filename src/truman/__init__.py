"""Truman — a Goal-Driven Recursive AI System.

Goal → AutoResearch → Planner → Workers → Simulation → Judge → Feedback Loop
  → Worker Re-iteration → (score >= threshold) → Deliver.

The engine does not just complete a task: it simulates real-world reaction
(audiences/markets), judges the result against quantitative success criteria,
and recursively re-iterates until the simulated outcome beats a threshold.
"""

from truman.goal.schema import GoalConfig, SuccessCriterion
from truman.orchestrator.loop import RunResult, TrumanEngine

__all__ = ["GoalConfig", "SuccessCriterion", "TrumanEngine", "RunResult"]
