"""LandingPageVertical — first-screen landing page optimized for conversion (PRD §2 D)."""

from __future__ import annotations

from truman.verticals._content_base import ContentSpec, ContentVertical


_SPEC = ContentSpec(
    name="landing_page",
    artifact_kind="landing_page",
    fields=["headline", "subheadline", "hook", "bullets", "cta", "faq"],
    default_cohort="ecommerce_shoppers",
    primary_topic_keys=["product", "offering", "topic"],
    metric_keys=["scroll_depth", "cta_click_rate", "form_completion_rate"],
    description="Landing page above-the-fold + body for conversion-driven funnels.",
)


class LandingPageVertical(ContentVertical):
    def __init__(self) -> None:
        super().__init__(_SPEC)
