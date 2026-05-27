"""Phase-2 gate: the in-memory SceneConfig integration with WorldSeed."""

from __future__ import annotations

from worldseed.dm.providers.mock import MockDMProvider
from worldseed.models.config_schema import SceneConfig
from worldseed.world import WorldEngine

from truman.agents.base import CandidateArtifact
from truman.goal.schema import GoalConfig, SuccessCriterion
from truman.sim.personas import build_personas
from truman.sim.scene_builder import build_scene_config


def _goal() -> GoalConfig:
    return GoalConfig(
        goal="test",
        criteria=[SuccessCriterion(name="engagement", metric="avg_engagement", weight=1.0)],
        scene={"topic": "budget travel"},
    )


def test_build_scene_config_validates():
    artifact = CandidateArtifact(iteration=0, kind="text_headline", content="Hello world")
    cfg = build_scene_config(_goal(), artifact)
    assert isinstance(cfg, SceneConfig)
    assert "react" in cfg.actions
    assert "scroll_past" in cfg.actions
    # artifact entity carries the content + a numeric engagement_score
    art = next(e for e in cfg.entities if e.id == "artifact")
    assert art.properties["content"] == "Hello world"
    assert art.properties["engagement_score"] == 0.0


def test_worldengine_constructs_and_registers_personas():
    artifact = CandidateArtifact(iteration=0, kind="text_headline", content="Cheap flights")
    cfg = build_scene_config(_goal(), artifact)
    engine = WorldEngine(config=cfg, dm_provider=MockDMProvider())
    personas = build_personas("budget travel", count=6, seed=42)
    for p in personas:
        engine.register_agent(p.agent_id, properties=p.to_props(), character=p.to_character())
    registered = set(engine.get_registered_agents())
    assert {p.agent_id for p in personas}.issubset(registered)
    assert engine.state.get("artifact") is not None


def test_personas_are_deterministic():
    a = build_personas("budget travel", count=6, seed=42)
    b = build_personas("budget travel", count=6, seed=42)
    assert [p.interested_topics for p in a] == [p.interested_topics for p in b]
    assert [p.sentiment_bias for p in a] == [p.sentiment_bias for p in b]
