"""Field-level diff between two CandidateArtifacts.

Returns a dict whose keys are the union of artifact field paths, mapped to
{"old": ..., "new": ...}. Only keys whose values changed are included. The
"content" string is included separately if it changed.
"""

from __future__ import annotations

from typing import Any

from truman.agents.base import CandidateArtifact


def _equal(a: Any, b: Any) -> bool:
    if isinstance(a, list) and isinstance(b, list):
        return a == b
    return a == b


def field_diff(parent: CandidateArtifact | None, child: CandidateArtifact) -> dict[str, dict]:
    """Return a {key: {old, new}} diff of artifact content + fields.

    If parent is None (iteration 0), every child key is "added" (old == None).
    """
    diffs: dict[str, dict] = {}
    parent_content = parent.content if parent else None
    if not _equal(parent_content, child.content):
        diffs["content"] = {"old": parent_content, "new": child.content}

    parent_fields = (parent.fields if parent else {}) or {}
    child_fields = child.fields or {}
    keys = set(parent_fields) | set(child_fields)
    for key in sorted(keys):
        old = parent_fields.get(key)
        new = child_fields.get(key)
        if not _equal(old, new):
            diffs[f"fields.{key}"] = {"old": old, "new": new}
    return diffs


def diff_summary(diffs: dict[str, dict]) -> str:
    """Compact one-liner: '3 fields changed: fields.title, fields.hook, …'."""
    if not diffs:
        return "no changes"
    keys = list(diffs.keys())
    if len(keys) <= 3:
        return f"{len(keys)} field(s) changed: {', '.join(keys)}"
    return f"{len(keys)} field(s) changed: {', '.join(keys[:3])}, …"
