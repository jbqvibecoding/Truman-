"""ColdEmailVertical — outbound email subject + body optimized for reply (PRD §2 D / E)."""

from __future__ import annotations

from truman.verticals._content_base import ContentSpec, ContentVertical


_SPEC = ContentSpec(
    name="cold_email",
    artifact_kind="email",
    fields=["subject", "opener", "body", "cta"],
    default_cohort="email_audiences",
    primary_topic_keys=["product", "offer", "topic"],
    metric_keys=["open_rate", "reply_rate", "meeting_book_rate"],
    description="Cold email subject + body with one clear ask, no fluff.",
)


class ColdEmailVertical(ContentVertical):
    def __init__(self) -> None:
        super().__init__(_SPEC)
