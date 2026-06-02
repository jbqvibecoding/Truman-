"""Renderers for the Evolution Changelog: markdown / summary / html.

Three formats:
- `render_markdown` — full timeline + per-iteration sections (best for PRs, docs)
- `render_summary` — 4-6 line Slack-ready summary
- `render_html` — self-contained HTML with inline CSS for direct browser viewing
"""

from __future__ import annotations

import html as html_lib
from typing import Any

from truman.changelog.diff import diff_summary
from truman.changelog.models import ChangelogEntryView, ChangelogView


_STATUS_EMOJI = {"delivered": "✅", "kept": "🟡", "rejected": "🔴"}


# ─── Markdown ───────────────────────────────────────────────────────────────


def render_markdown(view: ChangelogView) -> str:
    goal = view.goal
    threshold = getattr(goal, "threshold", 0.0)
    vertical = getattr(goal, "vertical", "unknown")

    lines: list[str] = []
    lines.append(f"# Evolution Changelog — {vertical}")
    lines.append("")
    lines.append(f"**Goal**: {getattr(goal, 'goal', '')}")
    lines.append(
        f"**Outcome**: {'✅ DELIVERED' if view.delivered else '🔴 NOT DELIVERED'} · "
        f"final score `{view.final_score:.4f}` / threshold `{threshold:.2f}` · "
        f"{len(view.entries)} iteration(s) · cost `{view.total_cost_tokens}` tokens"
    )
    lines.append("")
    lines.append("## Timeline")
    lines.append("")
    lines.append("| Iter | Status | Score | Δ vs parent | Key change |")
    lines.append("| --- | --- | --- | --- | --- |")
    for e in view.entries:
        emoji = _STATUS_EMOJI.get(e.status, "·")
        parent = f"iter {e.parent_iteration}" if e.parent_iteration is not None else "baseline"
        change = diff_summary(e.diff)
        lines.append(
            f"| {e.iteration} | {emoji} {e.status} | "
            f"{e.score:.4f} | {parent} | {change} |"
        )
    lines.append("")

    lines.append("## Per-iteration details")
    lines.append("")
    for e in view.entries:
        lines.extend(_render_entry_markdown(e))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_entry_markdown(e: ChangelogEntryView) -> list[str]:
    emoji = _STATUS_EMOJI.get(e.status, "·")
    out: list[str] = []
    out.append(f"### {emoji} Iteration {e.iteration} — `{e.status}` · score `{e.score:.4f}`")
    out.append("")
    if e.parent_iteration is not None:
        out.append(f"_Revised from iteration {e.parent_iteration}._")
    else:
        out.append("_Baseline._")
    out.append("")
    if e.rationale:
        out.append(f"**Rationale**: {e.rationale}")
        out.append("")
    if e.per_eval:
        out.append("**Per-Eval**:")
        for k, v in e.per_eval.items():
            mark = "✅" if v else "❌"
            out.append(f"  - {mark} `{k}`")
        out.append("")
    if e.diff:
        out.append("**Changes**:")
        for key, change in e.diff.items():
            old_str = _truncate(_pretty(change.get("old")))
            new_str = _truncate(_pretty(change.get("new")))
            out.append(f"  - `{key}`: ~~{old_str}~~ → **{new_str}**")
        out.append("")
    if e.feedback and e.status != "delivered":
        out.append(f"**Judge feedback**: {e.feedback}")
        out.append("")
    return out


# ─── Summary (Slack-style) ──────────────────────────────────────────────────


def render_summary(view: ChangelogView) -> str:
    if not view.entries:
        return "No iterations recorded."
    first = view.entries[0]
    last = view.entries[-1]
    headline = (
        f"{_STATUS_EMOJI.get(last.status, '·')} "
        f"{'Delivered' if view.delivered else 'Did not deliver'} "
        f"in {len(view.entries)} iteration(s) — "
        f"{first.score:.3f} → {last.score:.3f}"
    )
    failed_evals = [k for k, v in last.per_eval.items() if not v]
    passed_evals = [k for k, v in last.per_eval.items() if v]
    diff_keys: set[str] = set()
    for e in view.entries:
        diff_keys.update(e.diff.keys())

    lines = [headline]
    if view.entries:
        threshold = getattr(view.goal, "threshold", 0.0)
        lines.append(f"Threshold: {threshold:.2f}  ·  cost: {view.total_cost_tokens} tokens")
    if passed_evals or failed_evals:
        lines.append(f"Evals: ✅ {len(passed_evals)} passed, ❌ {len(failed_evals)} failed")
    if failed_evals:
        lines.append(f"Failed: {', '.join(failed_evals[:5])}")
    if diff_keys:
        keys = sorted(diff_keys)
        suffix = "…" if len(keys) > 4 else ""
        lines.append(f"Changes touched: {', '.join(keys[:4])}{suffix}")
    return "\n".join(lines)


# ─── HTML ───────────────────────────────────────────────────────────────────


def render_html(view: ChangelogView) -> str:
    goal = view.goal
    threshold = getattr(goal, "threshold", 0.0)
    vertical = getattr(goal, "vertical", "unknown")
    rows_html: list[str] = []
    for e in view.entries:
        emoji = _STATUS_EMOJI.get(e.status, "·")
        change = diff_summary(e.diff)
        rows_html.append(
            f"<tr>"
            f"<td>{e.iteration}</td>"
            f"<td>{emoji} {html_lib.escape(e.status)}</td>"
            f"<td>{e.score:.4f}</td>"
            f"<td>{html_lib.escape(change)}</td>"
            f"</tr>"
        )

    details_html: list[str] = []
    for e in view.entries:
        emoji = _STATUS_EMOJI.get(e.status, "·")
        evals_li = "".join(
            f"<li class='{'pass' if v else 'fail'}'>{'✅' if v else '❌'} {html_lib.escape(k)}</li>"
            for k, v in e.per_eval.items()
        )
        diffs_li = "".join(
            f"<li><code>{html_lib.escape(k)}</code>: <del>{html_lib.escape(_truncate(_pretty(c['old'])))}</del> → "
            f"<ins>{html_lib.escape(_truncate(_pretty(c['new'])))}</ins></li>"
            for k, c in e.diff.items()
        )
        details_html.append(
            f"<section><h3>{emoji} Iteration {e.iteration} — {html_lib.escape(e.status)} · "
            f"score {e.score:.4f}</h3>"
            f"<p><em>{html_lib.escape(e.rationale)}</em></p>"
            f"{('<h4>Per-Eval</h4><ul>' + evals_li + '</ul>') if evals_li else ''}"
            f"{('<h4>Changes</h4><ul>' + diffs_li + '</ul>') if diffs_li else ''}"
            f"</section>"
        )

    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Evolution Changelog — {html_lib.escape(vertical)}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 920px; margin: 2em auto; padding: 0 1em; color: #1c1c1e; }}
h1 {{ border-bottom: 2px solid #007aff; padding-bottom: .4em; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
th, td {{ border: 1px solid #d1d1d6; padding: .5em; text-align: left; }}
th {{ background: #f2f2f7; }}
section {{ margin: 1.5em 0; padding: 1em; border-left: 4px solid #007aff; background: #f9f9fb; }}
li.pass {{ color: #34c759; }}
li.fail {{ color: #ff3b30; }}
del {{ background: #ffe5e5; text-decoration: line-through; padding: 0 4px; }}
ins {{ background: #d6f5d6; text-decoration: none; padding: 0 4px; }}
code {{ background: #eef; padding: 1px 4px; border-radius: 3px; font-size: .92em; }}
.summary {{ font-size: 1.1em; padding: .5em 0; }}
</style></head><body>
<h1>Evolution Changelog — {html_lib.escape(vertical)}</h1>
<p class='summary'><strong>Goal</strong>: {html_lib.escape(getattr(goal, 'goal', ''))}</p>
<p class='summary'><strong>Outcome</strong>: {'✅ DELIVERED' if view.delivered else '🔴 NOT DELIVERED'} ·
final score <code>{view.final_score:.4f}</code> / threshold <code>{threshold:.2f}</code> ·
{len(view.entries)} iteration(s) · cost <code>{view.total_cost_tokens}</code> tokens</p>
<h2>Timeline</h2>
<table><thead><tr><th>Iter</th><th>Status</th><th>Score</th><th>Key change</th></tr></thead>
<tbody>{''.join(rows_html)}</tbody></table>
<h2>Per-iteration details</h2>
{''.join(details_html)}
</body></html>"""


# ─── helpers ────────────────────────────────────────────────────────────────


def _pretty(v: Any) -> str:
    if v is None:
        return "∅"
    if isinstance(v, str):
        return v
    if isinstance(v, (list, dict)):
        import json as _json
        return _json.dumps(v, ensure_ascii=False)
    return str(v)


def _truncate(s: str, n: int = 80) -> str:
    s = s.replace("\n", " ⏎ ")
    return s if len(s) <= n else s[: n - 1] + "…"
