"""AutoResearch Layer contracts.

Reuses autoresearch's discipline (a research step that feeds the production
loop) rather than its ML code. A provider gathers market/audience/competitor
insight into a structured ResearchBrief consumed by the Planner and Worker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from truman.goal.schema import GoalConfig


@dataclass
class ResearchBrief:
    summary: str
    audience_insights: list[str] = field(default_factory=list)
    competitor_examples: list[str] = field(default_factory=list)
    recommended_angles: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ResearchProvider(Protocol):
    def research(self, goal: GoalConfig) -> ResearchBrief:
        ...
