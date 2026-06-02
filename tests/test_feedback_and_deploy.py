"""Tests for M7 (feedback / calibration) + M8 (deploy adapters)."""

from __future__ import annotations

import asyncio

import pytest

from truman.deploy import (
    GitHubPRAdapter,
    LocalFileAdapter,
    MetaAdsAdapter,
    NotionAdapter,
    available_targets,
    get_adapter,
)
from truman.feedback import (
    calibration_report,
    compute_correlation,
    record_real_kpi,
)
from truman.feedback.mock_data import synth
from truman.feedback.recorder import load_history
from truman.goal.loader import load_goal
from truman.orchestrator.loop import TrumanEngine


# ─── M7 — Feedback / Calibration ────────────────────────────────────────────


def test_compute_correlation_basic():
    pairs = [(0.1, 0.15), (0.3, 0.32), (0.5, 0.55), (0.7, 0.69), (0.9, 0.94)]
    r = compute_correlation(pairs)
    assert r is not None
    assert r > 0.95  # near-perfect positive correlation


def test_compute_correlation_too_few_samples():
    assert compute_correlation([(0.1, 0.2), (0.3, 0.4)]) is None


def test_compute_correlation_zero_variance_returns_none():
    pairs = [(0.5, 0.4), (0.5, 0.5), (0.5, 0.6), (0.5, 0.7)]
    # All xs identical → no variance
    assert compute_correlation(pairs) is None


def test_record_and_load_kpi(tmp_path):
    p = tmp_path / "feedback.tsv"
    record_real_kpi("run-A", {"ctr": 0.4}, {"ctr": 0.45}, path=p)
    record_real_kpi("run-B", {"ctr": 0.5, "dwell": 0.6}, {"ctr": 0.55, "dwell": 0.62}, path=p)
    rows = load_history(p)
    assert len(rows) == 2
    assert rows[0].run_id == "run-A"
    assert rows[0].sim_metrics["ctr"] == 0.4
    assert rows[1].real_metrics["dwell"] == 0.62


def test_calibration_report_synth_data_strong_correlation():
    history = synth(n=40, noise=0.05, seed=42)
    report = calibration_report(history)
    assert report.n_samples == 40
    assert report.confidence in {"medium", "high"}
    # Strong correlation expected on all three synthetic metrics
    for metric in ("ctr", "dwell", "sentiment"):
        assert metric in report.per_metric_pearson_r
        assert report.per_metric_pearson_r[metric] > 0.8


def test_calibration_report_low_sample_warning():
    history = synth(n=2, seed=1)
    report = calibration_report(history)
    assert report.n_samples == 2
    assert report.confidence == "low"
    assert any("3 samples" in s for s in report.suggestions)


def test_calibration_suggestions_detect_direction():
    """Synth data has real_ctr > sim_ctr by ~0.07 — calibrator should flag it."""
    history = synth(n=30, noise=0.02, seed=7)
    report = calibration_report(history)
    suggestions = " ".join(report.suggestions)
    # The synth has +0.07 bias on ctr → "real > sim" suggestion fires
    assert "ctr" in suggestions
    assert "real > sim" in suggestions or "increase" in suggestions


# ─── M8 — Deploy adapters ──────────────────────────────────────────────────


def test_available_targets_contains_all_four():
    assert set(available_targets()) == {"local", "meta_ads", "github_pr", "notion"}


def test_get_adapter_unknown_raises():
    with pytest.raises(ValueError, match="Unknown deploy target"):
        get_adapter("aws_s3")


def test_local_adapter_is_live():
    assert LocalFileAdapter().is_live() is True


def test_external_adapters_not_live_without_creds(monkeypatch):
    # Ensure env is clean of platform credentials.
    for var in ["META_ADS_TOKEN", "META_AD_ACCOUNT_ID", "GH_TOKEN", "GITHUB_TOKEN",
                "NOTION_TOKEN", "NOTION_DATABASE_ID"]:
        monkeypatch.delenv(var, raising=False)
    assert MetaAdsAdapter().is_live() is False
    assert GitHubPRAdapter().is_live() is False
    assert NotionAdapter().is_live() is False


def _run_for_deploy(yaml_path: str):
    goal = load_goal(yaml_path)
    return goal, asyncio.run(TrumanEngine(goal, mode="mock").run())


def test_local_adapter_writes_artifact_and_changelog(tmp_path):
    goal, run = _run_for_deploy("examples/ad_creative_evals.yaml")
    adapter = LocalFileAdapter(base_dir=tmp_path)
    result = adapter.export(run, goal, dry_run=False)
    assert result.dry_run is False
    out_dir = list(tmp_path.iterdir())[0]
    assert (out_dir / "artifact.md").read_text().startswith("#")
    assert (out_dir / "artifact.json").exists()
    assert "# Evolution Changelog" in (out_dir / "changelog.md").read_text()
    assert (out_dir / "changelog.json").exists()


def test_local_adapter_dry_run_does_not_write(tmp_path):
    goal, run = _run_for_deploy("examples/ad_creative_evals.yaml")
    adapter = LocalFileAdapter(base_dir=tmp_path)
    result = adapter.export(run, goal, dry_run=True)
    assert result.dry_run is True
    assert "[dry-run]" in result.payload_summary
    # No directory was created
    assert list(tmp_path.iterdir()) == []


def test_meta_ads_dry_run_payload_has_creative_fields(monkeypatch):
    monkeypatch.delenv("META_ADS_TOKEN", raising=False)
    goal, run = _run_for_deploy("examples/ad_creative_evals.yaml")
    result = MetaAdsAdapter().export(run, goal, dry_run=True)
    assert result.dry_run is True
    payload = result.extra["payload"]
    assert "ad_account_id" in payload
    assert "creative" in payload
    assert "title" in payload["creative"]
    # is_live False because env clean
    assert result.extra["is_live_capable"] is False


def test_github_pr_dry_run_payload_for_software_eng():
    goal, run = _run_for_deploy("examples/software_eng_issue.yaml")
    result = GitHubPRAdapter().export(run, goal, dry_run=True)
    assert result.dry_run is True
    assert "title" in result.extra
    assert "body" in result.extra
    assert "patch" in result.extra["body"].lower() or "def " in result.extra["body"]


def test_notion_dry_run_payload(monkeypatch):
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    goal, run = _run_for_deploy("examples/ad_creative_evals.yaml")
    result = NotionAdapter().export(run, goal, dry_run=True)
    payload = result.extra["payload"]
    assert "parent_database" in payload
    assert payload["properties"]["Vertical"] == "ad_creative"
