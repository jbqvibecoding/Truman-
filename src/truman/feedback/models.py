"""Data classes for real-KPI ingestion + calibration reports."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RealKPI:
    """A single (delivered artifact → real-world KPI) datapoint."""

    run_id: str
    recorded_at: str                                  # ISO-8601 timestamp
    sim_metrics: dict[str, float] = field(default_factory=dict)   # what Truman predicted
    real_metrics: dict[str, float] = field(default_factory=dict)  # what really happened


@dataclass
class CalibrationReport:
    """Output of calibration: per-metric correlation + suggestions."""

    n_samples: int
    per_metric_pearson_r: dict[str, float] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    confidence: str = "low"  # "low" / "medium" / "high" based on n_samples
