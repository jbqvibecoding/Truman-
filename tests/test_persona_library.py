"""Tests for M3: Persona Library + Cohort templates + user-upload."""

from __future__ import annotations

import csv
import json

import pytest

from truman.personas.library import (
    available_cohorts,
    build_personas_for_scene,
    build_personas_from_cohort,
    load_cohort,
    load_personas_from_csv,
    load_personas_from_json,
)
from truman.sim.personas import Persona


def test_available_cohorts_complete():
    names = set(available_cohorts())
    assert {"ad_segments", "social_segments", "us_swing_voters",
            "developer_personas", "ecommerce_shoppers", "email_audiences",
            "b2b_buyers", "prd_readers"} <= names


def test_load_cohort_segments():
    c = load_cohort("ad_segments")
    assert c.name == "ad_segments"
    assert len(c.segments) == 5
    labels = [s.label for s in c.segments]
    assert "小红书用户" in labels
    assert "TikTok用户" in labels
    assert "美国宝妈" in labels
    assert "Web3 Degens" in labels
    assert "GenZ" in labels


def test_load_cohort_unknown_raises():
    with pytest.raises(ValueError, match="Unknown cohort"):
        load_cohort("nonexistent_cohort")


def test_build_personas_from_cohort_deterministic():
    a = build_personas_from_cohort("ad_segments", count=10, seed=42)
    b = build_personas_from_cohort("ad_segments", count=10, seed=42)
    assert len(a) == 10
    assert len(b) == 10
    for x, y in zip(a, b):
        assert x.agent_id == y.agent_id
        assert x.mbti == y.mbti
        assert x.country == y.country
        assert x.sentiment_bias == y.sentiment_bias


def test_build_personas_from_cohort_distribution():
    # 10 personas across 5 segments → 2 per segment
    personas = build_personas_from_cohort("ad_segments", count=10, seed=1)
    seg_counts: dict[str, int] = {}
    for p in personas:
        label = p.extra.get("cohort_segment")
        seg_counts[label] = seg_counts.get(label, 0) + 1
    assert sum(seg_counts.values()) == 10
    # Round-robin → roughly balanced (each segment got 2)
    assert all(c == 2 for c in seg_counts.values())


def test_build_personas_all_cohorts_smoke():
    """Every built-in cohort must produce valid Personas without crashing."""
    for name in available_cohorts():
        personas = build_personas_from_cohort(name, count=6, seed=7)
        assert len(personas) == 6
        for p in personas:
            assert isinstance(p, Persona)
            assert p.agent_id and p.name
            assert -1.0 <= p.sentiment_bias <= 1.0
            assert p.influence_weight > 0
            assert p.stance in {"enthusiast", "neutral", "skeptic"}


def test_build_personas_for_scene_cohort_path():
    scene = {"cohort": "developer_personas"}
    personas = build_personas_for_scene(scene, count=5, seed=0)
    assert personas is not None
    assert len(personas) == 5
    # all developer-cohort segments are dev-y
    for p in personas:
        assert p.profession in {
            "junior engineer", "bootcamp grad", "intern",
            "senior engineer", "tech lead", "staff engineer",
            "principal engineer", "architect", "director of eng",
            "SRE", "devops engineer", "platform engineer",
            "security engineer", "appsec", "pentester", "auditor",
        }


def test_build_personas_for_scene_no_directive_returns_none():
    # No cohort, no upload → caller falls back to legacy builders
    assert build_personas_for_scene({}, count=5, seed=0) is None
    assert build_personas_for_scene({"product": "x"}, count=5, seed=0) is None
    assert build_personas_for_scene(None, count=5, seed=0) is None


# ─── user upload ─────────────────────────────────────────────────────────────


def test_load_personas_from_csv(tmp_path):
    p = tmp_path / "personas.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["name", "bio", "persona", "mbti", "country", "profession",
                        "interested_topics", "stance", "sentiment_bias", "influence_weight"],
        )
        w.writeheader()
        w.writerow({
            "name": "Alice", "bio": "Travel blogger", "persona": "Adventurer",
            "mbti": "ENFP", "country": "US", "profession": "creator",
            "interested_topics": "travel|food|culture",
            "stance": "enthusiast", "sentiment_bias": "0.5", "influence_weight": "1.4",
        })
        w.writerow({
            "name": "Bob", "bio": "", "persona": "",
            "mbti": "", "country": "", "profession": "",
            "interested_topics": "", "stance": "", "sentiment_bias": "", "influence_weight": "",
        })
    personas = load_personas_from_csv(p)
    assert len(personas) == 2
    assert personas[0].name == "Alice"
    assert personas[0].interested_topics == ["travel", "food", "culture"]
    assert personas[0].sentiment_bias == 0.5
    # Bob: defaults filled in
    assert personas[1].mbti == "ENFP"
    assert personas[1].country == "US"
    assert personas[1].interested_topics == ["general"]


def test_load_personas_from_json(tmp_path):
    p = tmp_path / "personas.json"
    p.write_text(json.dumps([
        {"name": "C1", "interested_topics": ["budget travel", "deals"],
         "sentiment_bias": 0.3, "influence_weight": 1.2},
        {"name": "C2", "interested_topics": ["family", "kids"],
         "sentiment_bias": -0.2, "influence_weight": 0.9},
    ]), encoding="utf-8")
    personas = load_personas_from_json(p)
    assert len(personas) == 2
    assert personas[0].interested_topics == ["budget travel", "deals"]
    assert personas[1].sentiment_bias == -0.2


def test_load_personas_csv_not_found_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_personas_from_csv(tmp_path / "missing.csv")


def test_build_personas_for_scene_uses_csv(tmp_path):
    p = tmp_path / "audience.csv"
    with p.open("w", encoding="utf-8") as f:
        f.write("name,interested_topics\nUploadedUser,vacation|deals\n")
    out = build_personas_for_scene({"persona_upload_csv": str(p)}, count=5, seed=0)
    assert out is not None
    assert len(out) == 1  # only one row in CSV
    assert out[0].name == "UploadedUser"


# ─── Integration: cohort flows through TrumanEngine ─────────────────────────


def test_cohort_personas_flow_through_engine():
    """Setting scene.cohort makes the engine generate cohort-derived personas."""
    import asyncio

    from truman.eval.schema import CheckKind, EvalQuestion
    from truman.goal.schema import GoalConfig
    from truman.orchestrator.loop import TrumanEngine

    goal = GoalConfig(
        goal="Test cohort flow through engine.",
        vertical="ad_creative",
        artifact_kind="ad_creative",
        threshold=0.5,
        max_iterations=2,
        persona_count=5,
        seed=42,
        evals=[
            EvalQuestion(id="hook_len", prompt="hook length OK?",
                         check_kind=CheckKind.LENGTH,
                         config={"field": "fields.hook", "min": 1, "max": 200},
                         weight=1.0),
        ],
        scene={"product": "test", "cohort": "ad_segments"},
    )
    result = asyncio.run(TrumanEngine(goal, mode="mock").run())
    # personas came from the cohort
    labels = {p.extra.get("cohort_segment") for p in result.personas}
    # at least 2 distinct segments populated (round-robin over 5 segments × 5 picks)
    assert len(labels) >= 2
    # All persona ids carry the segment prefix our loader builds
    for p in result.personas:
        assert p.extra.get("cohort_segment")
