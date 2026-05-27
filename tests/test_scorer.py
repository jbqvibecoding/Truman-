"""Judge layer: composite score == weighted criteria, threshold logic."""

from __future__ import annotations

from truman.agents.base import CandidateArtifact
from truman.goal.schema import GoalConfig, SuccessCriterion
from truman.judge.scorer import EngagementScorer
from truman.sim.result import SimulationResult


def _goal(threshold: float) -> GoalConfig:
    return GoalConfig(
        goal="t",
        threshold=threshold,
        criteria=[
            SuccessCriterion(name="engagement", metric="avg_engagement", weight=0.7),
            SuccessCriterion(name="reach", metric="positive_ratio", weight=0.3),
        ],
    )


def _result(avg: float, pos: float) -> SimulationResult:
    return SimulationResult(
        artifact=CandidateArtifact(iteration=0, kind="text_headline", content="x"),
        per_persona={"a": {"engaged": pos > 0, "intensity": avg * 10, "action": "react", "reaction": ""}},
        metrics={"avg_engagement": avg, "positive_ratio": pos},
    )


def test_composite_is_weighted_average():
    verdict = EngagementScorer().score(_goal(0.5), _result(avg=0.8, pos=1.0))
    # 0.7*0.8 + 0.3*1.0 = 0.86
    assert abs(verdict.score - 0.86) < 1e-6
    assert verdict.threshold_met
    assert verdict.per_criterion == {"engagement": 0.8, "reach": 1.0}


def test_threshold_not_met_gives_feedback():
    verdict = EngagementScorer().score(_goal(0.9), _result(avg=0.2, pos=0.3))
    assert not verdict.threshold_met
    assert "threshold" in verdict.feedback.lower()
