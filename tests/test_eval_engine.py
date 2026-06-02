"""Tests for the Eval Engine: 6 check_kinds + Runner + Recommender + scorer."""

from __future__ import annotations

import asyncio

import pytest

from truman.agents.base import CandidateArtifact
from truman.eval.checkers import check_one
from truman.eval.recommender import MockEvalRecommender, build_recommender
from truman.eval.runner import EvalRunner
from truman.eval.schema import CheckKind, EvalQuestion, EvalRecommendation
from truman.eval.templates import built_in_templates, recommended_persona_count
from truman.goal.schema import GoalConfig, SuccessCriterion
from truman.judge.scorer import EngagementScorer
from truman.orchestrator.loop import TrumanEngine
from truman.sim.result import SimulationResult


def _q(id_, kind, **cfg):
    return EvalQuestion(id=id_, prompt=f"is {id_} ok?", check_kind=kind, config=cfg, weight=1.0)


def _artifact(content="hello world", **fields) -> CandidateArtifact:
    return CandidateArtifact(iteration=0, kind="x", content=content, fields=fields)


# ─── 6 check_kinds: one pass + one fail each ─────────────────────────────────


@pytest.mark.parametrize(
    "eval_q, artifact, metrics, expected",
    [
        # regex
        (_q("r_pass", CheckKind.REGEX, field="content", forbid=["spam"]),
         _artifact(content="clean copy"), {}, True),
        (_q("r_fail", CheckKind.REGEX, field="content", forbid=["spam"]),
         _artifact(content="this is spam"), {}, False),
        (_q("r_req", CheckKind.REGEX, field="content", require=["buy", "try"]),
         _artifact(content="please try our product"), {}, True),
        (_q("r_req_fail", CheckKind.REGEX, field="content", require=["buy"]),
         _artifact(content="just looking"), {}, False),
        # length
        (_q("l_pass", CheckKind.LENGTH, field="content", min=5, max=20),
         _artifact(content="medium len"), {}, True),
        (_q("l_fail", CheckKind.LENGTH, field="content", min=50, max=200),
         _artifact(content="too short"), {}, False),
        # range
        (_q("rg_pass", CheckKind.RANGE, metric="ctr", op=">=", value=0.5),
         _artifact(), {"ctr": 0.7}, True),
        (_q("rg_fail", CheckKind.RANGE, metric="ctr", op=">=", value=0.5),
         _artifact(), {"ctr": 0.3}, False),
        (_q("rg_missing", CheckKind.RANGE, metric="missing", op=">=", value=0.5),
         _artifact(), {}, False),
        # code
        (_q("c_pass", CheckKind.CODE, field="content", check="no_todo"),
         _artifact(content="clean code"), {}, True),
        (_q("c_fail", CheckKind.CODE, field="content", check="no_todo"),
         _artifact(content="# TODO: refactor later"), {}, False),
        (_q("c_py", CheckKind.CODE, field="content", check="valid_python"),
         _artifact(content="def f(x): return x + 1"), {}, True),
        (_q("c_py_bad", CheckKind.CODE, field="content", check="valid_python"),
         _artifact(content="def f(x: oops"), {}, False),
        # llm_judge (mock mode: deterministic keyword-overlap heuristic)
        (EvalQuestion(id="lj_pass", prompt="Does the text discuss budget travel?",
                      check_kind=CheckKind.LLM_JUDGE, config={"field": "content"}, weight=1.0),
         _artifact(content="Stop scrolling if you care about budget travel today"), {}, True),
        (EvalQuestion(id="lj_fail", prompt="Does the text discuss budget travel?",
                      check_kind=CheckKind.LLM_JUDGE, config={"field": "content"}, weight=1.0),
         _artifact(content="x"), {}, False),
    ],
)
def test_check_kinds(eval_q, artifact, metrics, expected):
    assert asyncio.run(check_one(eval_q, artifact, metrics, mode="mock")) is expected


def test_composed_and_or():
    sub_pass = _q("s1", CheckKind.LENGTH, field="content", min=1, max=100).model_dump()
    sub_fail = _q("s2", CheckKind.REGEX, field="content", forbid=["hello"]).model_dump()
    art = _artifact(content="hello world")

    q_and = _q("and", CheckKind.COMPOSED, op="AND", evals=[sub_pass, sub_fail])
    q_or = _q("or", CheckKind.COMPOSED, op="OR", evals=[sub_pass, sub_fail])

    assert asyncio.run(check_one(q_and, art, {}, mode="mock")) is False
    assert asyncio.run(check_one(q_or, art, {}, mode="mock")) is True


# ─── EvalRunner ──────────────────────────────────────────────────────────────


def test_eval_runner_returns_id_keyed_bools():
    evals = [
        _q("e1", CheckKind.LENGTH, field="content", min=1, max=100),  # pass
        _q("e2", CheckKind.RANGE, metric="ctr", op=">=", value=0.5),  # pass
        _q("e3", CheckKind.REGEX, field="content", forbid=["hello"]),  # fail
    ]
    runner = EvalRunner(mode="mock")
    result = runner.run(evals, _artifact(content="hello world"), {"ctr": 0.6})
    assert result == {"e1": True, "e2": True, "e3": False}


def test_composite_score_weighted():
    evals = [
        EvalQuestion(id="a", prompt="?", check_kind=CheckKind.REGEX, weight=0.5),
        EvalQuestion(id="b", prompt="?", check_kind=CheckKind.REGEX, weight=0.3),
        EvalQuestion(id="c", prompt="?", check_kind=CheckKind.REGEX, weight=0.2),
    ]
    score = EvalRunner.composite_score(evals, {"a": True, "b": False, "c": True})
    assert score == 0.7  # (0.5 + 0.2) / 1.0


# ─── Recommender ────────────────────────────────────────────────────────────


def _ad_goal_with_evals():
    return GoalConfig(
        goal="Maximize CTR for our travel app ad.",
        vertical="ad_creative",
        criteria=[SuccessCriterion(name="dummy", metric="ctr", weight=1.0)],
        scene={"product": "budget travel", "audience_segments":
               ["小红书用户", "TikTok用户", "美国宝妈", "Web3 Degens", "GenZ"]},
    )


def test_mock_recommender_shape_and_persona_count():
    goal = _ad_goal_with_evals()
    rec = MockEvalRecommender().recommend(goal)
    assert isinstance(rec, EvalRecommendation)
    assert 3 <= len(rec.evals) <= 6
    # all binary check_kinds, ids unique
    assert len({q.id for q in rec.evals}) == len(rec.evals)
    # MiroFish heuristic: ~2 per segment, floored 5, capped 20
    assert 5 <= rec.recommended_persona_count <= 20
    assert rec.recommended_persona_count == 10  # 5 segments × 2
    assert rec.rationale


def test_recommended_persona_count_fallback():
    # No scene → falls back to vertical's archetype cohort (5 ad segments × 2 = 10)
    assert recommended_persona_count("ad_creative", None) == 10
    # 6 social archetypes → 12
    assert recommended_persona_count("viral_content", None) == 12
    # Unknown vertical without scene → terminal dict default
    assert recommended_persona_count("unknown_vertical", None) == 6
    # 3 segments → max(5, 6) = 6
    assert recommended_persona_count("x", {"audience_segments": ["a", "b", "c"]}) == 6
    # 20 segments → min(20, 40) = 20 (capped)
    assert recommended_persona_count("x", {"audience_segments": list("abcdefghijklmnopqrst")}) == 20


def test_build_recommender_factory():
    assert isinstance(build_recommender("mock"), MockEvalRecommender)
    from truman.eval.recommender import LLMEvalRecommender
    assert isinstance(build_recommender("llm"), LLMEvalRecommender)


def test_llm_recommender_imports():
    # Just import-level smoke; the LLM path requires Anthropic credentials.
    from truman.eval.recommender import LLMEvalRecommender
    rec = LLMEvalRecommender(model=None)
    assert rec is not None


# ─── Templates ──────────────────────────────────────────────────────────────


def test_built_in_templates_per_vertical():
    assert len(built_in_templates("headline")) == 4
    assert len(built_in_templates("ad_creative")) == 6
    assert len(built_in_templates("unknown_vertical")) == 3  # generic fallback
    # all are EvalQuestion with binary check_kinds
    for q in built_in_templates("ad_creative"):
        assert isinstance(q, EvalQuestion)
        assert q.check_kind in {
            CheckKind.LENGTH, CheckKind.REGEX, CheckKind.RANGE,
            CheckKind.LLM_JUDGE, CheckKind.CODE, CheckKind.COMPOSED,
        }


# ─── Scorer dual-path ───────────────────────────────────────────────────────


def test_scorer_binary_path_with_evals():
    """When goal.evals is set, scorer must use the binary path."""
    goal = GoalConfig(
        goal="x", vertical="headline",
        evals=[
            EvalQuestion(id="a", prompt="?", check_kind=CheckKind.REGEX, weight=0.6),
            EvalQuestion(id="b", prompt="?", check_kind=CheckKind.REGEX, weight=0.4),
        ],
        threshold=0.5,
    )
    result = SimulationResult(
        artifact=_artifact(),
        per_persona={"p1": {"engaged": True}},
        per_eval={"a": True, "b": False},
    )
    verdict = EngagementScorer().score(goal, result)
    assert verdict.score == 0.6
    assert verdict.threshold_met is True
    assert verdict.per_criterion == {"a": 1.0, "b": 0.0}
    # feedback names the failing eval
    assert "b" in verdict.feedback or "Threshold met" in verdict.feedback


def test_scorer_continuous_path_backward_compat():
    """When goal.evals is empty, scorer falls back to v1 criteria path."""
    goal = GoalConfig(
        goal="x", vertical="headline",
        criteria=[SuccessCriterion(name="eng", metric="avg_engagement", weight=1.0)],
        threshold=0.5,
    )
    result = SimulationResult(
        artifact=_artifact(),
        per_persona={"p1": {"engaged": True}},
        metrics={"avg_engagement": 0.7},
    )
    verdict = EngagementScorer().score(goal, result)
    assert verdict.score == 0.7
    assert verdict.threshold_met is True


# ─── End-to-end via the orchestrator loop ────────────────────────────────────


@pytest.mark.asyncio
async def test_ad_creative_evals_e2e_delivers():
    """The new binary-eval yaml run delivers and emits per_eval in the ledger."""
    from truman.goal.loader import load_goal

    goal = load_goal("examples/ad_creative_evals.yaml")
    result = await TrumanEngine(goal, mode="mock").run()

    assert result.final_verdict.threshold_met
    assert result.ledger.records[-1].status == "delivered"
    # per_eval populated for every iteration
    for record in result.ledger.records:
        assert set(record.per_eval) == {q.id for q in goal.evals}
    # final delivered iteration must pass at least the 3 "structural" evals
    final = result.ledger.records[-1].per_eval
    assert final["ad_hook_short"] is True
    assert final["ad_cta_present"] is True
    assert final["ad_no_filler"] is True


def test_goal_config_requires_criteria_or_evals():
    with pytest.raises(Exception):  # noqa: PT011 — pydantic ValidationError
        GoalConfig(goal="x", vertical="headline")  # neither criteria nor evals


def test_goal_config_evals_only_is_valid():
    goal = GoalConfig(
        goal="x", vertical="headline",
        evals=[EvalQuestion(id="e1", prompt="?", check_kind=CheckKind.REGEX, weight=1.0)],
    )
    assert goal.evals and not goal.criteria


# ─── Persona-count priority (CLI > yaml > recommender > default) ────────────


def test_yaml_persona_count_wins_over_recommendation():
    goal = GoalConfig(
        goal="x", vertical="ad_creative",
        criteria=[SuccessCriterion(name="c", metric="ctr", weight=1.0)],
        persona_count=3,
        scene={"audience_segments": ["a", "b", "c", "d", "e"]},
    )
    # Recommender suggests 10 but user explicitly set 3 → goal.persona_count wins
    rec = MockEvalRecommender().recommend(goal)
    assert rec.recommended_persona_count == 10
    assert goal.persona_count == 3  # user's value preserved
