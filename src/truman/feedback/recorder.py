"""Record real-world KPIs for delivered artifacts (TSV append-only).

Pattern follows autoresearch's results.tsv discipline: append-only,
human-readable, easy to diff. The expected workflow is:

  1. Truman delivers an artifact (assigned a run_id via the orchestrator).
  2. The artifact is deployed to production (Meta Ads / GitHub / etc.).
  3. After enough time elapses, real KPIs are fetched from the platform's
     attribution API and recorded here via `record_real_kpi(...)`.
  4. Periodically, `calibrator.calibration_report(history_path())` is run
     to compute per-metric correlation between simulator predictions and
     real KPIs, surfacing simulator tweaks.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

from truman.feedback.models import RealKPI


def history_path(base: str | Path = "data") -> Path:
    """Default location of the feedback TSV. Caller can override for tests."""
    return Path(base) / "feedback.tsv"


def record_real_kpi(
    run_id: str,
    sim_metrics: dict[str, float],
    real_metrics: dict[str, float],
    path: str | Path | None = None,
    recorded_at: str | None = None,
) -> Path:
    """Append one row to the feedback TSV. Returns the path written to.

    The row is `run_id\tts\tsim_metrics_json\treal_metrics_json` (the JSON
    blobs keep the schema stable across goals with different metric sets).
    """
    p = Path(path) if path else history_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    new_file = not p.exists()
    ts = recorded_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with p.open("a", encoding="utf-8") as f:
        if new_file:
            f.write("run_id\trecorded_at\tsim_metrics\treal_metrics\n")
        f.write(
            f"{run_id}\t{ts}\t"
            f"{json.dumps(sim_metrics, ensure_ascii=False)}\t"
            f"{json.dumps(real_metrics, ensure_ascii=False)}\n"
        )
    return p


def load_history(path: str | Path | None = None) -> list[RealKPI]:
    """Parse a feedback TSV back into RealKPI objects."""
    p = Path(path) if path else history_path()
    if not p.exists():
        return []
    out: list[RealKPI] = []
    with p.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            try:
                sim = json.loads(row.get("sim_metrics") or "{}")
                real = json.loads(row.get("real_metrics") or "{}")
            except json.JSONDecodeError:
                continue
            out.append(RealKPI(
                run_id=row.get("run_id", ""),
                recorded_at=row.get("recorded_at", ""),
                sim_metrics=sim,
                real_metrics=real,
            ))
    return out
