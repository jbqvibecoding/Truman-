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


@dataclass
class Ledger:
    records: list[IterationRecord] = field(default_factory=list)

    def append(self, record: IterationRecord) -> None:
        self.records.append(record)

    @property
    def best_score(self) -> float:
        return max((r.score for r in self.records), default=0.0)

    def to_tsv(self) -> str:
        header = "iteration\tscore\tthreshold\tstatus\tdescription"
        rows = [
            f"{r.iteration}\t{r.score:.4f}\t{r.threshold:.4f}\t{r.status}\t{r.description}"
            for r in self.records
        ]
        return "\n".join([header, *rows])
