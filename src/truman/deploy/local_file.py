"""LocalFileAdapter — the one truly-functional deploy target.

Writes the delivered artifact + the Evolution Changelog (markdown + JSON) to
`out/<run_id>/` so users can review them, attach them to PRs, etc. No
external service required.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from truman.deploy.base import DeployResult


class LocalFileAdapter:
    name = "local"

    def __init__(self, base_dir: str | Path = "out") -> None:
        self.base_dir = Path(base_dir)

    def is_live(self) -> bool:
        return True  # local filesystem is always available

    def export(self, run: Any, goal: Any, dry_run: bool = True) -> DeployResult:
        from truman.changelog import ChangelogView, render_markdown
        from truman.changelog.exporter import _view_to_dict

        run_id = _make_run_id(getattr(goal, "vertical", "x"))
        out_dir = self.base_dir / run_id
        if dry_run:
            preview = (
                f"[dry-run] would write to {out_dir}/: "
                f"artifact.md, artifact.json, changelog.md, changelog.json"
            )
            return DeployResult(target=self.name, dry_run=True, payload_summary=preview)

        out_dir.mkdir(parents=True, exist_ok=True)
        # Artifact (markdown + json)
        artifact = run.final_artifact
        art_md = _artifact_to_markdown(artifact, goal)
        (out_dir / "artifact.md").write_text(art_md, encoding="utf-8")
        (out_dir / "artifact.json").write_text(json.dumps({
            "iteration": artifact.iteration,
            "kind": artifact.kind,
            "content": artifact.content,
            "fields": artifact.fields,
            "rationale": artifact.rationale,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        # Changelog (markdown + json)
        view = ChangelogView.from_run(goal, run.ledger, run.artifact_history)
        (out_dir / "changelog.md").write_text(render_markdown(view), encoding="utf-8")
        (out_dir / "changelog.json").write_text(json.dumps(_view_to_dict(view), ensure_ascii=False, indent=2),
                                                encoding="utf-8")

        return DeployResult(
            target=self.name, dry_run=False,
            payload_summary=f"Wrote artifact + changelog to {out_dir}",
            url_or_path=str(out_dir.resolve()),
        )


def _artifact_to_markdown(artifact: Any, goal: Any) -> str:
    lines = [
        f"# {getattr(goal, 'vertical', 'artifact')} — iteration {artifact.iteration}",
        "",
        f"**Goal**: {getattr(goal, 'goal', '')}",
        f"**Kind**: {artifact.kind}",
        f"**Rationale**: {artifact.rationale}",
        "",
        "## Content",
        "",
        "```",
        artifact.content,
        "```",
        "",
    ]
    if artifact.fields:
        lines.append("## Fields")
        lines.append("")
        for k, v in artifact.fields.items():
            lines.append(f"### {k}")
            lines.append("")
            if isinstance(v, list):
                for item in v:
                    lines.append(f"- {item}")
            else:
                lines.append(str(v))
            lines.append("")
    return "\n".join(lines)


def _make_run_id(vertical: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", vertical)[:32]
    return f"{safe}_{int(time.time())}"
