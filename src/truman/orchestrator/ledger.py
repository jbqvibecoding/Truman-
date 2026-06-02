"""Iteration ledger — autoresearch's append-only experiment log.

Mirrors autoresearch's results.tsv shape (candidate / score / status /
description): one row per iteration recording whether the candidate was kept,
rejected, or delivered. The ledger is the audit trail of the recursive loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IterationRecord:
    iteration: int
    artifact_content: str
    score: float
    threshold: float
    status: str  # "kept" | "rejected" | "delivered"
    feedback: str = ""
    description: str = ""
    # v2 extensions (default-valued for backward compat)
    per_eval: dict[str, bool] = field(default_factory=dict)
    cost_tokens: int = 0
    parent_iteration: int | None = None


@dataclass
class Ledger:
    records: list[IterationRecord] = field(default_factory=list)

    def append(self, record: IterationRecord) -> None:
        self.records.append(record)

    @property
    def best_score(self) -> float:
        return max((r.score for r in self.records), default=0.0)

    def cumulative_cost(self) -> int:
        return sum(r.cost_tokens for r in self.records)

    def to_tsv(self) -> str:
        # Surface per_eval as a JSON-encoded column so the schema stays stable
        # across goals with different eval sets (autoresearch results.tsv shape).
        import json as _json
        header = "iteration\tscore\tthreshold\tstatus\tcost_tokens\tper_eval\tdescription"
        rows = [
            f"{r.iteration}\t{r.score:.4f}\t{r.threshold:.4f}\t{r.status}\t"
            f"{r.cost_tokens}\t{_json.dumps(r.per_eval, ensure_ascii=False)}\t{r.description}"
            for r in self.records
        ]
        return "\n".join([header, *rows])
