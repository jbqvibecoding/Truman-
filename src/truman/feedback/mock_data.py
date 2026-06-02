"""Synthetic (sim, real) datapoints for testing the calibration pipeline.

The synthesizer produces a correlated set of pairs with a controllable noise
floor so calibrator tests can assert "r is in the expected band".
"""

from __future__ import annotations

import random

from truman.feedback.models import RealKPI


def synth(n: int = 30, noise: float = 0.1, seed: int = 0) -> list[RealKPI]:
    """Generate `n` (sim, real) datapoints where real ≈ sim + noise + bias.

    Returns a list of RealKPI with sim_metrics + real_metrics populated for
    a representative metric set (ctr, dwell, sentiment).
    """
    rng = random.Random(seed)
    out: list[RealKPI] = []
    for i in range(n):
        ctr_sim = round(rng.uniform(0.1, 0.9), 4)
        dwell_sim = round(rng.uniform(0.1, 0.9), 4)
        sent_sim = round(rng.uniform(0.1, 0.9), 4)
        # Real values are correlated with sim plus Gaussian-ish noise + a
        # small positive bias for ctr (simulator under-predicts).
        ctr_real = round(max(0.0, min(1.0, ctr_sim + 0.07 + rng.uniform(-noise, noise))), 4)
        dwell_real = round(max(0.0, min(1.0, dwell_sim + rng.uniform(-noise, noise))), 4)
        sent_real = round(max(0.0, min(1.0, sent_sim - 0.05 + rng.uniform(-noise, noise))), 4)
        out.append(RealKPI(
            run_id=f"synth_{i + 1}",
            recorded_at=f"2026-01-{(i % 28) + 1:02d}T00:00:00+00:00",
            sim_metrics={"ctr": ctr_sim, "dwell": dwell_sim, "sentiment": sent_sim},
            real_metrics={"ctr": ctr_real, "dwell": dwell_real, "sentiment": sent_real},
        ))
    return out
