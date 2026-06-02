"""E2E tests for M5 + M6 new verticals — each example yaml runs to completion."""

from __future__ import annotations

import pytest

from truman.goal.loader import load_goal
from truman.orchestrator.loop import TrumanEngine
from truman.verticals.registry import available, get_vertical


# Verticals registered at import time (M5 + M6).
NEW_VERTICALS = [
    "software_eng", "viral_content", "landing_page", "cold_email",
    "seo_article", "sales_script", "prd_doc", "pdp_page",
]


def test_all_new_verticals_registered():
    avail = set(available())
    for name in NEW_VERTICALS:
        assert name in avail, f"{name} missing from registry"


@pytest.mark.parametrize("name", NEW_VERTICALS)
def test_vertical_has_full_seven_piece_interface(name):
    v = get_vertical(name)
    # Each vertical must implement the seven-piece interface.
    assert hasattr(v, "make_research")
    assert hasattr(v, "make_creative")
    assert hasattr(v, "make_personas")
    assert hasattr(v, "make_decider")
    assert hasattr(v, "make_dm")
    assert hasattr(v, "build_scene")
    assert hasattr(v, "compute_metrics")
    assert v.name == name


@pytest.mark.parametrize(
    "yaml_path",
    [
        "examples/software_eng_issue.yaml",
        "examples/viral_content_post.yaml",
        "examples/landing_page.yaml",
        "examples/cold_email.yaml",
        "examples/seo_article.yaml",
        "examples/sales_script.yaml",
        "examples/prd_doc.yaml",
        "examples/pdp_page.yaml",
    ],
)
def test_example_yaml_loads_and_runs_mock(yaml_path):
    """Every new example yaml must load + run through the loop in mock mode.

    We don't require strict-delivery here (some thresholds intentionally test
    plateau/budget behaviour in future tests), but the run must complete
    without exceptions and produce at least 1 ledger row.
    """
    goal = load_goal(yaml_path)
    result = TrumanEngine(goal, mode="mock").run_sync()
    assert len(result.ledger.records) >= 1
    assert len(result.artifact_history) == len(result.ledger.records)
    # Score is a finite number
    assert 0.0 <= result.final_verdict.score <= 1.0


@pytest.mark.parametrize(
    "yaml_path",
    [
        # These three should deliver within max_iterations in mock mode.
        "examples/software_eng_issue.yaml",
        "examples/viral_content_post.yaml",
        "examples/landing_page.yaml",
    ],
)
def test_high_confidence_yamls_deliver(yaml_path):
    goal = load_goal(yaml_path)
    result = TrumanEngine(goal, mode="mock").run_sync()
    assert result.delivered, (
        f"{yaml_path} did not deliver; final score "
        f"{result.final_verdict.score:.4f} / threshold {goal.threshold}"
    )
    assert result.ledger.records[-1].status == "delivered"


def test_software_eng_produces_five_dim_metrics():
    """SoftwareEngVertical must emit the 5 PRD-defined dimensions in metrics."""
    goal = load_goal("examples/software_eng_issue.yaml")
    result = TrumanEngine(goal, mode="mock").run_sync()
    # All five dims appear in per_criterion (since goal uses criteria, not evals).
    for dim in ["correctness", "tests", "quality", "security", "performance"]:
        assert dim in result.final_verdict.per_criterion, f"{dim} missing"


def test_content_vertical_uses_default_cohort():
    """Content verticals default to a cohort even when scene.cohort is unset."""
    from truman.personas.library import COHORTS

    # viral_content's spec.default_cohort is social_segments → personas should
    # carry segment metadata.
    goal = load_goal("examples/viral_content_post.yaml")
    # Scene doesn't set cohort explicitly, but the vertical injects it.
    result = TrumanEngine(goal, mode="mock").run_sync()
    cohort_labels = {p.extra.get("cohort_segment") for p in result.personas}
    # All personas in this run came from social_segments → some label populated
    assert any(label for label in cohort_labels), (
        "Expected cohort_segment metadata on personas (vertical should pick default cohort)"
    )
    # And the labels are drawn from the social_segments cohort
    expected = {s.label for s in COHORTS["social_segments"].segments}
    overlap = cohort_labels & expected
    assert overlap, f"Expected social_segments labels, got {cohort_labels}"
