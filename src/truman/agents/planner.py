"""Planner — turns goal + research brief into a short generation strategy.

Kept lightweight: it distills the brief's recommended angles into an ordered
plan string that the Worker consumes. (The recursive intelligence lives in the
simulate→judge→revise loop, not in elaborate up-front planning.)
"""

from __future__ import annotations

from truman.goal.schema import GoalConfig
from truman.research.base import ResearchBrief


class Planner:
    def plan(self, goal: GoalConfig, brief: ResearchBrief) -> str:
        angles = ", ".join(brief.recommended_angles) or "the core value proposition"
        return (
            f"Goal: {goal.goal}\n"
            f"Artifact: {goal.artifact_kind}\n"
            f"Lead with the strongest angle; progressively incorporate: {angles}."
        )
