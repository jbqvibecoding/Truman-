"""Simulator-vs-real-KPI calibration (Pearson correlation + suggestions).

This is the "M7" of the PRD roadmap: feed real post-deployment KPIs back to
Truman so the simulator can be tuned. v1 is scaffolding — the math is real
(plain Pearson r, no SciPy required) but the data path requires users to
record real KPIs first (see `feedback.recorder`).

Suggestions are heuristic — "if real CTR > sim CTR consistently, the
simulator's bias is underweighted". Concrete tuning of the underlying mock
deciders / DMs is the user's responsibility (PRD §10 backflow risk).
"""

from __future__ import annotations

import math

from truman.feedback.models import CalibrationReport, RealKPI


def compute_correlation(pairs: list[tuple[float, float]]) -> float | None:
    """Pearson r over (x, y) pairs. Returns None for n < 3 or zero variance."""
    n = len(pairs)
    if n < 3:
        return None
    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in pairs)
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def calibration_report(history: list[RealKPI]) -> CalibrationReport:
    """Aggregate per-metric Pearson r across recorded sim/real pairs."""
    n = len(history)
    if n < 3:
        return CalibrationReport(
            n_samples=n,
            suggestions=[f"Need at least 3 samples to compute correlations (have {n})."],
            confidence="low",
        )

    metric_keys = sorted({k for r in history for k in r.sim_metrics} & {k for r in history for k in r.real_metrics})
    per_metric: dict[str, float] = {}
    for key in metric_keys:
        pairs = [
            (float(r.sim_metrics.get(key, 0.0)), float(r.real_metrics.get(key, 0.0)))
            for r in history
            if key in r.sim_metrics and key in r.real_metrics
        ]
        r_val = compute_correlation(pairs)
        if r_val is not None:
            per_metric[key] = round(r_val, 4)

    suggestions = suggest_simulator_tweaks(history, per_metric)
    confidence = "low" if n < 10 else ("medium" if n < 30 else "high")
    return CalibrationReport(
        n_samples=n, per_metric_pearson_r=per_metric,
        suggestions=suggestions, confidence=confidence,
    )


def suggest_simulator_tweaks(
    history: list[RealKPI],
    per_metric_r: dict[str, float],
) -> list[str]:
    """Translate correlations + sim-vs-real direction into actionable hints."""
    out: list[str] = []
    if not history:
        return out

    # Per-metric average direction: positive => sim underestimates real.
    avg_dir: dict[str, float] = {}
    for key in per_metric_r:
        diffs = [
            float(r.real_metrics.get(key, 0.0)) - float(r.sim_metrics.get(key, 0.0))
            for r in history if key in r.sim_metrics and key in r.real_metrics
        ]
        if diffs:
            avg_dir[key] = sum(diffs) / len(diffs)

    for key, r_val in per_metric_r.items():
        if r_val < 0.3:
            out.append(
                f"⚠️  '{key}' weak correlation (r={r_val:.2f}) — the simulator is "
                "not predictive yet for this metric; consider richer persona variance or "
                "domain-specific evaluator signals."
            )
        if abs(r_val) >= 0.3 and key in avg_dir:
            direction = avg_dir[key]
            if direction > 0.05:
                out.append(
                    f"📈 '{key}': real > sim by avg {direction:+.3f} — increase the mock "
                    "evaluator's positive-bias coefficient (or loosen its engagement cutoff)."
                )
            elif direction < -0.05:
                out.append(
                    f"📉 '{key}': real < sim by avg {direction:+.3f} — decrease the mock "
                    "evaluator's positive-bias coefficient (or tighten the engagement cutoff)."
                )
            else:
                out.append(f"✅ '{key}': r={r_val:.2f}, mean-aligned. Calibration looks OK.")

    if not out:
        out.append("No actionable signal yet — record more samples and re-run.")
    return out
