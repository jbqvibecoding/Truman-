"""Pluggability gate: the ad_creative vertical runs end-to-end via the same loop."""

from __future__ import annotations

import pytest

from truman.goal.schema import GoalConfig, SuccessCriterion
from truman.orchestrator.loop import TrumanEngine
from truman.verticals.registry import available, get_vertical


def _ad_goal() -> GoalConfig:
    return GoalConfig(
        goal="Maximize CTR/ROAS for our budget travel app's short-form video ad.",
        vertical="ad_creative",
        artifact_kind="ad_creative",
        threshold=0.55,
        max_iterations=6,
        persona_count=6,
        seed=42,
        criteria=[
            SuccessCriterion(name="ctr", metric="ctr", weight=0.4),
            SuccessCriterion(name="dwell", metric="avg_dwell", weight=0.2),
            SuccessCriterion(name="sentiment", metric="sentiment_ratio", weight=0.2),
            SuccessCriterion(name="roas", metric="roas_proxy", weight=0.2),
        ],
        scene={"product": "budget travel", "platform": "tiktok"},
    )


def test_registry_exposes_both_verticals():
    assert {"headline", "ad_creative"}.issubset(set(available()))
    assert get_vertical("ad_creative").name == "ad_creative"


@pytest.mark.asyncio
async def test_ad_creative_loop_improves_and_delivers():
    result = await TrumanEngine(_ad_goal(), mode="mock").run()
    rows = result.ledger.records

    assert len(rows) >= 2
    scores = [r.score for r in rows]
    assert all(b > a for a, b in zip(scores, scores[1:]))  # strictly improving
    assert result.final_verdict.threshold_met
    assert rows[-1].status == "delivered"

    # Evaluator produced the ad metrics.
    assert {"ctr", "dwell", "sentiment", "roas"} <= set(result.final_verdict.per_criterion)

    # Creative agents produced a structured ad (not just a string).
    f = result.final_artifact.fields
    assert {"title", "hook", "script", "storyboard"} <= set(f)
    assert f["title"] and f["hook"] and f["script"]


@pytest.mark.asyncio
async def test_ad_creative_is_deterministic():
    a = await TrumanEngine(_ad_goal(), mode="mock").run()
    b = await TrumanEngine(_ad_goal(), mode="mock").run()
    assert a.final_artifact.content == b.final_artifact.content
    assert [r.score for r in a.ledger.records] == [r.score for r in b.ledger.records]
