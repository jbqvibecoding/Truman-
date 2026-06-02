"""Format dispatcher: write a ChangelogView to disk in any supported format."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from truman.changelog.models import ChangelogView
from truman.changelog.renderer import render_html, render_markdown, render_summary


def export(view: ChangelogView, fmt: str, path: str | Path) -> Path:
    """Render `view` in `fmt` and write it to `path`. Returns the path."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = _render(view, fmt)
    p.write_text(text, encoding="utf-8")
    return p


def _render(view: ChangelogView, fmt: str) -> str:
    fmt = fmt.lower()
    if fmt in ("md", "markdown"):
        return render_markdown(view)
    if fmt == "summary":
        return render_summary(view)
    if fmt == "html":
        return render_html(view)
    if fmt == "json":
        return json.dumps(_view_to_dict(view), ensure_ascii=False, indent=2)
    msg = f"Unknown changelog format {fmt!r}. Supported: md, markdown, summary, html, json"
    raise ValueError(msg)


def _view_to_dict(view: ChangelogView) -> dict[str, Any]:
    goal = view.goal
    return {
        "goal": getattr(goal, "goal", ""),
        "vertical": getattr(goal, "vertical", ""),
        "threshold": getattr(goal, "threshold", 0.0),
        "delivered": view.delivered,
        "final_score": view.final_score,
        "total_cost_tokens": view.total_cost_tokens,
        "entries": [asdict(e) if is_dataclass(e) else e for e in view.entries],
    }
