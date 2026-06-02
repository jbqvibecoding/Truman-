"""Evolution Changelog (PRD v2.0 §4.6).

The third differentiator of Truman: every delivered artifact comes with a
full audit trail of "what changed / why / how it scored" across all
iterations, exportable as markdown / json / a one-paragraph summary.

Public API:
- `field_diff(a, b)` — field-level diff between two CandidateArtifacts
- `ChangelogView` — aggregated view of (ledger, artifact_history, goal)
- `render_markdown(view)`, `render_summary(view)`, `render_html(view)`
- `export(view, fmt, path)` — convenience exporter
"""

from truman.changelog.diff import field_diff
from truman.changelog.exporter import export
from truman.changelog.models import ChangelogEntryView, ChangelogView
from truman.changelog.renderer import render_html, render_markdown, render_summary

__all__ = [
    "ChangelogEntryView",
    "ChangelogView",
    "export",
    "field_diff",
    "render_html",
    "render_markdown",
    "render_summary",
]
