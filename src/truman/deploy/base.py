"""DeployAdapter Protocol + DeployResult dataclass.

Adapters are stateless. `is_live()` returns False whenever the adapter can
only do a dry-run (e.g. credentials missing). For safety the CLI defaults to
dry_run=True even when the adapter is live; the user must explicitly opt in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from truman.orchestrator.loop import RunResult


@dataclass
class DeployResult:
    target: str
    dry_run: bool
    payload_summary: str
    url_or_path: str | None = None
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class DeployAdapter(Protocol):
    name: str

    def is_live(self) -> bool:
        """True iff the adapter can actually call the external API.

        Implementations should return False if credentials are missing.
        """
        ...

    def export(self, run: RunResult, goal: Any, dry_run: bool = True) -> DeployResult:
        """Send the delivered artifact to the target (or print a dry-run)."""
        ...
