"""PRDVertical — product requirements doc optimized for clarity (PRD §2 F)."""

from __future__ import annotations

from truman.verticals._content_base import ContentSpec, ContentVertical


_SPEC = ContentSpec(
    name="prd_doc",
    artifact_kind="prd",
    fields=["title", "user_stories", "acceptance_criteria", "edge_cases", "body"],
    default_cohort="prd_readers",
    primary_topic_keys=["feature", "topic"],
    metric_keys=["clarity", "coverage", "ambiguity_score"],
    description="PRD doc with goal / user stories / acceptance criteria / edge cases.",
)


class PRDVertical(ContentVertical):
    def __init__(self) -> None:
        super().__init__(_SPEC)
