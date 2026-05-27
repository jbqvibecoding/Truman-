"""Build an in-memory WorldSeed SceneConfig for a simulation run.

WorldSeed's WorldEngine accepts a SceneConfig object directly (no YAML file),
so Truman constructs the scene dynamically from the goal + candidate artifact.
Personas are registered at runtime by the driver (not baked into `agents`).

The scene models a social feed with one piece of content. Personas take a
DM-judged `react` action (carrying their computed `intensity`) or the
mechanical `scroll_past`. The DM increments `artifact.engagement_score`.
"""

from __future__ import annotations

from worldseed.models.config_schema import SceneConfig

from truman.agents.base import CandidateArtifact
from truman.goal.schema import GoalConfig

MAX_INTENSITY = 10.0


def build_scene_config(goal: GoalConfig, artifact: CandidateArtifact) -> SceneConfig:
    """Construct a validated SceneConfig for the given artifact."""
    description = (
        f"A social feed shows one piece of content. Goal: {goal.goal} "
        f"The audience reacts based on how well it matches their interests."
    )
    scene_dict = {
        "scene": {
            "id": "truman_sim",
            "description": description,
            "dm_knowledge": (
                "Engagement intensity is provided on each react action as the "
                "`intensity` parameter (0-10). Increment artifact.engagement_score "
                "by that amount. Higher intensity = stronger engagement."
            ),
            "max_ticks": None,
            "max_dm_calls": None,
        },
        "narrator": False,
        "entities": [
            {"id": "feed", "type": "space"},
            {
                "id": "artifact",
                "type": "content",
                "content": artifact.content,
                "engagement_score": 0.0,
                "constraints": {"engagement_score": {"min": 0}},
            },
        ],
        "actions": {
            "react": {
                "description": "React to the headline shown in the feed.",
                "params": [
                    {"name": "sentiment", "type": "free_text", "required": True},
                    {"name": "intensity", "type": "number", "required": True},
                ],
                "dm": {
                    "hint": (
                        "The reacting persona engaged with the content. Increment "
                        "artifact.engagement_score by the action's `intensity` value, "
                        "and emit a 'reaction' event summarizing the sentiment."
                    ),
                    "allowed_ops": ["increment", "emit_event"],
                    "max_effects": 3,
                },
            },
            "scroll_past": {
                "description": "Ignore the headline and scroll past without engaging.",
                "params": [],
            },
        },
        "perception": {"visibility": []},
    }
    return SceneConfig.model_validate(scene_dict)
