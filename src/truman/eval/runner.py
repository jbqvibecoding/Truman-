"""EvalRunner — apply all evals to a candidate, return id → bool.

Mirrors MiroFish's parallel-evaluation pattern from
`oasis_profile_generator.py:851-1014` (ThreadPoolExecutor for parallel persona
generation): we use `asyncio.gather` so the LLM-backed `llm_judge` calls run
concurrently rather than serially. Deterministic checks (regex/length/range/
code/composed) are cheap and run instantly.
"""

from __future__ import annotations

import asyncio

from truman.agents.base import CandidateArtifact
from truman.eval.checkers import check_one
from truman.eval.schema import EvalQuestion


class EvalRunner:
    def __init__(self, mode: str = "mock", model: str | None = None) -> None:
        self._mode = mode
        self._model = model

    async def run_async(
        self,
        evals: list[EvalQuestion],
        artifact: CandidateArtifact,
        metrics: dict[str, float] | None = None,
    ) -> dict[str, bool]:
        if not evals:
            return {}
        results = await asyncio.gather(
            *(check_one(q, artifact, metrics, self._mode, self._model) for q in evals)
        )
        return {q.id: bool(r) for q, r in zip(evals, results)}

    def run(
        self,
        evals: list[EvalQuestion],
        artifact: CandidateArtifact,
        metrics: dict[str, float] | None = None,
    ) -> dict[str, bool]:
        """Sync wrapper for tests / one-off use; prefer `run_async` in the loop."""
        return asyncio.run(self.run_async(evals, artifact, metrics))

    @staticmethod
    def composite_score(evals: list[EvalQuestion], per_eval: dict[str, bool]) -> float:
        """Weighted aggregate of binary results in [0, 1].

        composite = Σ(weight_i × passed_i) / Σ(weight_i)
        """
        total = sum(q.weight for q in evals) or 1.0
        passed = sum(q.weight for q in evals if per_eval.get(q.id, False))
        return round(passed / total, 4)
