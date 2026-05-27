"""MockResearcher — deterministic offline research brief.

Its `recommended_angles` are the simulation topic pool (same pool the personas
are drawn from), ordered so that progressively adopting them broadens audience
coverage. This keeps the offline loop reproducible and improving.
"""

from __future__ import annotations

from truman.goal.schema import GoalConfig
from truman.research.base import ResearchBrief
from truman.sim.personas import topic_pool


class MockResearcher:
    def research(self, goal: GoalConfig) -> ResearchBrief:
        primary = goal.scene.get("topic")
        angles = topic_pool(primary, size=6)
        return ResearchBrief(
            summary=(
                f"Offline research brief for goal: {goal.goal!r}. "
                f"Audience responds to concrete, interest-matched hooks."
            ),
            audience_insights=[
                f"Segments care about distinct themes: {', '.join(angles)}.",
                "Generic headlines underperform; interest-matched angles convert.",
            ],
            competitor_examples=[
                f"Top performers lead with '{angles[0]}' and stack secondary hooks.",
            ],
            recommended_angles=angles,
            raw={"primary_topic": primary, "pool": angles},
        )
