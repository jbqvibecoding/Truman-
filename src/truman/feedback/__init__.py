"""Real-data backflow + Simulator calibration (PRD v2.0 M7, scaffolding).

This package is the seam where real-world KPIs (real CTR / real reply rate /
real PR-merge ratio) are recorded against delivered artifacts so the simulator
can be calibrated. v1 ships:

- `RealKPI` + `CalibrationReport` data classes
- `record_real_kpi(...)` — append to a TSV (the integration target is any
  real attribution system: Meta Ads Reporting API, GA4, Mixpanel, GitHub PR
  metrics, etc.)
- `compute_correlation` + `calibration_report` — Pearson r between sim
  metrics and real KPIs
- `mock_data.synth(n)` — synthesize (sim, real) pairs for testing

A real production backflow loop is out of scope until users provide real
post-deployment KPI data; the contract is in place so plugging in a real
attribution source requires no changes to Truman's core engine.
"""

from truman.feedback.calibrator import (
    calibration_report,
    compute_correlation,
    suggest_simulator_tweaks,
)
from truman.feedback.models import CalibrationReport, RealKPI
from truman.feedback.recorder import history_path, record_real_kpi

__all__ = [
    "CalibrationReport",
    "RealKPI",
    "calibration_report",
    "compute_correlation",
    "history_path",
    "record_real_kpi",
    "suggest_simulator_tweaks",
]
