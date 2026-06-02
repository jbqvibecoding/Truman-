"""SEOVertical — long-form article optimized for search intent (PRD §2 D)."""

from __future__ import annotations

from truman.verticals._content_base import ContentSpec, ContentVertical


_SPEC = ContentSpec(
    name="seo_article",
    artifact_kind="article",
    fields=["title", "meta", "outline", "body", "faq"],
    default_cohort=None,  # use topic-pool personas; SEO is intent-driven not segment-driven
    primary_topic_keys=["keyword", "topic"],
    metric_keys=["keyword_coverage", "intent_match", "dwell_estimate"],
    description="SEO article matching search intent with intro / outline / body / FAQ.",
)


class SEOVertical(ContentVertical):
    def __init__(self) -> None:
        super().__init__(_SPEC)
