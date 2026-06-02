"""PDPVertical — ecommerce product detail page optimized for add-to-cart (PRD §2 G)."""

from __future__ import annotations

from truman.verticals._content_base import ContentSpec, ContentVertical


_SPEC = ContentSpec(
    name="pdp_page",
    artifact_kind="pdp",
    fields=["title", "bullets", "detail", "faq", "badges"],
    default_cohort="ecommerce_shoppers",
    primary_topic_keys=["product", "category", "topic"],
    metric_keys=["value_clarity", "trust_signals", "friction_score"],
    description="Ecommerce PDP: title / bullets / detail / FAQ / trust badges.",
)


class PDPVertical(ContentVertical):
    def __init__(self) -> None:
        super().__init__(_SPEC)
