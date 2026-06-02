"""Tests for M4: Evolution Changelog renderer + exporter + loop wiring."""

from __future__ import annotations

import json

import pytest

from truman.agents.base import CandidateArtifact
from truman.changelog import (
    ChangelogView,
    export,
    field_diff,
    render_html,
    render_markdown,
    render_summary,
)
from truman.goal.schema import GoalConfig, SuccessCriterion
from truman.orchestrator.ledger import IterationRecord, Ledger


def _art(iteration: int, content: str, parent: int | None = None, **fields) -> CandidateArtifact:
    return CandidateArtifact(
        iteration=iteration, kind="x", content=content,
        rationale=f"v{iteration}", fields=fields, parent_iteration=parent,
    )


# ─── field_diff ─────────────────────────────────────────────────────────────


def test_field_diff_baseline_has_added_keys():
    child = _art(0, "first", title="A", hook="B")
    diff = field_diff(None, child)
    assert "content" in diff
    assert diff["content"]["old"] is None
    assert diff["content"]["new"] == "first"
    assert diff["fields.title"]["old"] is None
    assert diff["fields.title"]["new"] == "A"


def test_field_diff_only_changed_keys():
    parent = _art(0, "v0", title="A", hook="B")
    child = _art(1, "v1", title="A", hook="B-revised", parent=0)
    diff = field_diff(parent, child)
    assert "content" in diff
    assert "fields.hook" in diff
    assert "fields.title" not in diff


def test_field_diff_no_changes():
    parent = _art(0, "same", title="X")
    child = _art(1, "same", title="X", parent=0)
    assert field_diff(parent, child) == {}


# ─── ChangelogView.from_run ─────────────────────────────────────────────────


def _build_view():
    goal = GoalConfig(
        goal="Test changelog",
        vertical="headline",
        criteria=[SuccessCriterion(name="c", metric="avg_engagement", weight=1.0)],
        threshold=0.6,
    )
    ledger = Ledger()
    ledger.append(IterationRecord(
        iteration=0, artifact_content="hello",
        score=0.3, threshold=0.6, status="kept",
        feedback="improve", description="baseline",
        per_eval={"e1": False, "e2": True}, cost_tokens=100, parent_iteration=None,
    ))
    ledger.append(IterationRecord(
        iteration=1, artifact_content="hello world", parent_iteration=0,
        score=0.75, threshold=0.6, status="delivered",
        feedback="threshold met", description="added detail",
        per_eval={"e1": True, "e2": True}, cost_tokens=150,
    ))
    history = [_art(0, "hello", title="A"), _art(1, "hello world", title="A-rev", parent=0)]
    return ChangelogView.from_run(goal, ledger, history)


def test_view_aggregates_run():
    view = _build_view()
    assert len(view.entries) == 2
    assert view.delivered is True
    assert view.final_score == 0.75
    assert view.total_cost_tokens == 250
    # diffs computed
    e1 = view.entries[1]
    assert "content" in e1.diff
    assert "fields.title" in e1.diff


# ─── renderers ──────────────────────────────────────────────────────────────


def test_render_markdown_includes_iterations_and_emoji():
    md = render_markdown(_build_view())
    assert "# Evolution Changelog" in md
    assert "## Timeline" in md
    assert "🟡 kept" in md and "✅ delivered" in md
    assert "iteration 0" in md.lower() or "Iteration 0" in md
    assert "e1" in md and "e2" in md  # per-eval names rendered
    assert "0.3000" in md or "0.3" in md  # score formatting


def test_render_summary_short_and_informative():
    s = render_summary(_build_view())
    assert s.count("\n") <= 8  # truly a summary
    assert "Delivered" in s or "✅" in s
    assert "0.300" in s and "0.750" in s  # first → last score
    assert "Evals" in s


def test_render_html_self_contained():
    h = render_html(_build_view())
    assert h.startswith("<!doctype html>")
    assert "<style>" in h
    assert "Evolution Changelog" in h
    assert "delivered" in h.lower()


# ─── export dispatcher ─────────────────────────────────────────────────────


def test_export_writes_each_format(tmp_path):
    view = _build_view()
    md_path = export(view, "md", tmp_path / "out.md")
    json_path = export(view, "json", tmp_path / "out.json")
    html_path = export(view, "html", tmp_path / "out.html")
    sum_path = export(view, "summary", tmp_path / "out.txt")
    assert md_path.read_text().startswith("# Evolution Changelog")
    assert html_path.read_text().startswith("<!doctype html>")
    assert "Delivered" in sum_path.read_text() or "✅" in sum_path.read_text()
    data = json.loads(json_path.read_text())
    assert data["delivered"] is True
    assert len(data["entries"]) == 2
    assert data["vertical"] == "headline"


def test_export_unknown_format_raises(tmp_path):
    with pytest.raises(ValueError, match="Unknown changelog format"):
        export(_build_view(), "pdf", tmp_path / "x.pdf")


# ─── e2e via TrumanEngine ──────────────────────────────────────────────────


def test_e2e_artifact_history_populated_and_changelog_renders():
    """Run ad_creative_evals.yaml end-to-end; render the changelog."""
    import asyncio

    from truman.goal.loader import load_goal
    from truman.orchestrator.loop import TrumanEngine

    goal = load_goal("examples/ad_creative_evals.yaml")
    result = asyncio.run(TrumanEngine(goal, mode="mock").run())

    # artifact_history matches ledger length
    assert len(result.artifact_history) == len(result.ledger.records)
    # each artifact corresponds to its ledger row
    for art, rec in zip(result.artifact_history, result.ledger.records):
        assert art.iteration == rec.iteration

    view = ChangelogView.from_run(goal, result.ledger, result.artifact_history)
    md = render_markdown(view)
    assert "✅ delivered" in md
    assert "ad_hook_short" in md  # per-eval ids appear in markdown
    summary = render_summary(view)
    assert "Delivered" in summary or "✅" in summary
