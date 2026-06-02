"""NotionAdapter — dry-run only in v1.

Real Notion page creation requires NOTION_TOKEN + a parent database id.
v1 prints the page properties + content blocks that WOULD be sent.
"""

from __future__ import annotations

import json
import os
from typing import Any

from truman.deploy.base import DeployResult


class NotionAdapter:
    name = "notion"

    def is_live(self) -> bool:
        return bool(os.environ.get("NOTION_TOKEN") and os.environ.get("NOTION_DATABASE_ID"))

    def export(self, run: Any, goal: Any, dry_run: bool = True) -> DeployResult:
        artifact = run.final_artifact
        fields = artifact.fields or {}
        page = {
            "parent_database": os.environ.get("NOTION_DATABASE_ID", "<unset>"),
            "properties": {
                "Title": fields.get("title", artifact.content[:60]),
                "Vertical": goal.vertical,
                "Score": round(run.final_verdict.score, 4),
                "Delivered": run.delivered,
            },
            "content_blocks": [
                {"type": "heading_1", "text": fields.get("title", "Truman artifact")},
                {"type": "paragraph", "text": artifact.content},
            ],
        }
        return DeployResult(
            target=self.name,
            dry_run=True,
            payload_summary=f"[dry-run] would create Notion page: {json.dumps(page, ensure_ascii=False)[:240]}…",
            extra={"payload": page, "is_live_capable": self.is_live()},
        )
