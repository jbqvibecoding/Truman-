"""End-to-end gate (offline): the recursive loop must improve and stop on threshold."""

from __future__ import annotations

import pytest

from truman.goal.schema import GoalConfig, SuccessCriterion
from truman.orchestrator.loop import TrumanEngine


def _goal() -> GoalConfig:
    return GoalConfig(
        goal="Write a headline that maximizes audience engagement for our budget travel app.",
        artifact_kind="text_headline",
        threshold=0.65,
        max_iterations=6,
        persona_count=6,
        seed=42,
        criteria=[
            SuccessCriterion(name="engagement", metric="avg_engagement", weight=0.7),
            SuccessCriterion(name="reach", metric="positive_ratio", weight=0.3),
        ],
        scene={"topic": "budget travel"},
    )


@pytest.mark.asyncio
async def test_loop_improves_and_stops_on_threshold():
    result = await TrumanEngine(_goal(), mode="mock").run()
    rows = result.ledger.records

    # 1. Re-iteration happened.
    assert len(rows) >= 2

    # 2. Scores strictly improve across iterations (judge feedback works).
    scores = [r.score for r in rows]
    assert scores == sorted(scores)
    assert all(b > a for a, b in zip(scores, scores[1:]))
    assert scores[-1] > scores[0]

    # 3. It stopped because the threshold was met (not budget exhaustion).
    assert result.final_verdict.threshold_met
    assert result.final_verdict.score >= _goal().threshold
    assert rows[-1].status == "delivered"


@pytest.mark.asyncio
async def test_loop_is_deterministic():
    a = await TrumanEngine(_goal(), mode="mock").run()
    b = await TrumanEngine(_goal(), mode="mock").run()
    assert a.final_artifact.content == b.final_artifact.content
    assert [r.score for r in a.ledger.records] == [r.score for r in b.ledger.records]
