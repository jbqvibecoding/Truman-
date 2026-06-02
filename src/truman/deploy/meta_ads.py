"""MetaAdsAdapter — dry-run only in v1.

Real Meta Marketing API calls require an access token + ad account id; v1
prints the payload that WOULD be POSTed to /v1/act/ads. The shape mirrors
the actual API for an easy live cutover later.
"""

from __future__ import annotations

import json
import os
from typing import Any

from truman.deploy.base import DeployResult


class MetaAdsAdapter:
    name = "meta_ads"

    def is_live(self) -> bool:
        # Live mode requires both creds; without them we can only dry-run.
        return bool(os.environ.get("META_ADS_TOKEN") and os.environ.get("META_AD_ACCOUNT_ID"))

    def export(self, run: Any, goal: Any, dry_run: bool = True) -> DeployResult:
        artifact = run.final_artifact
        fields = artifact.fields or {}
        payload = {
            "ad_account_id": os.environ.get("META_AD_ACCOUNT_ID", "<unset>"),
            "name": fields.get("title") or fields.get("headline") or "Truman delivered",
            "creative": {
                "title": fields.get("title", ""),
                "hook": fields.get("hook", ""),
                "script": fields.get("script", ""),
                "storyboard": fields.get("storyboard", []),
            },
            "audience_segments": (goal.scene or {}).get("audience_segments", []),
            "predicted_metrics": run.final_verdict.per_criterion,
        }
        # In v1 we never actually call the API — even when is_live() is True.
        # The live cutover is a follow-up; safety > velocity.
        return DeployResult(
            target=self.name,
            dry_run=True,
            payload_summary=f"[dry-run] would POST /v1/act/ads with: {json.dumps(payload, ensure_ascii=False)[:240]}…",
            extra={"payload": payload, "is_live_capable": self.is_live()},
        )
