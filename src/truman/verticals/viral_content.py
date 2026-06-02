"""ViralContentVertical — short-form social posts optimized for spread (PRD §2 C)."""

from __future__ import annotations

from truman.verticals._content_base import ContentSpec, ContentVertical


_SPEC = ContentSpec(
    name="viral_content",
    artifact_kind="social_post",
    fields=["headline", "hook", "body", "hashtags"],
    default_cohort="social_segments",
    primary_topic_keys=["topic", "subject"],
    metric_keys=["share_rate", "argue_rate", "remix_rate", "sentiment_ratio"],
    description="Viral short-form content across Reddit / X / 小红书 / Web3 audiences.",
)


class ViralContentVertical(ContentVertical):
    def __init__(self) -> None:
        super().__init__(_SPEC)
