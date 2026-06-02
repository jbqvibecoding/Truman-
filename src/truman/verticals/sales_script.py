"""SalesScriptVertical — B2B sales script optimized for meeting conversion (PRD §2 E)."""

from __future__ import annotations

from truman.verticals._content_base import ContentSpec, ContentVertical


_SPEC = ContentSpec(
    name="sales_script",
    artifact_kind="sales_script",
    fields=["opener", "pain_dx", "solution", "objection_handling", "cta"],
    default_cohort="b2b_buyers",
    primary_topic_keys=["product", "buyer_industry", "topic"],
    metric_keys=["pain_recognition", "cta_clarity", "pushback_score"],
    description="B2B sales script: opener / pain diagnostic / solution / objection handling / CTA.",
)


class SalesScriptVertical(ContentVertical):
    def __init__(self) -> None:
        super().__init__(_SPEC)
