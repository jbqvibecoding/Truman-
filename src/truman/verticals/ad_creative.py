"""AdCreativeVertical — AI ad-creative evolution system.

A second, self-contained vertical that validates Truman's pluggability:

  Goal (CTR/ROAS/conversion)
   -> Research agents   (analyze TikTok/Meta viral ads -> angles/hooks)
   -> Creative agents   (title / hook / video script / storyboard 分镜)
   -> Simulation agents (5 segments: 小红书 / TikTok / 美国宝妈 / Web3 Degens / GenZ)
   -> Evaluator         (predict CTR / dwell / comment sentiment + ROAS proxy)
   -> recursive optimize until composite >= threshold.

Research and Creative are deliberately thin: they conform to the existing
ResearchProvider / WorkerProvider Protocols so an external multi-agent team can
be plugged in later without touching the loop. Personas REUSE the generic
generator (the 5 segments are passed via goal.scene). The Evaluator is a
WorldSeed DM provider that predicts the per-reaction signals.

mock mode is fully offline and deterministic; llm mode uses real Anthropic calls.
"""

from __future__ import annotations

from worldseed.dm.providers.mock import MockDMProvider
from worldseed.models.config_schema import EffectConfig, SceneConfig
from worldseed.protocol.dm import DMContext, DMResponse

from truman.agents.base import CandidateArtifact
from truman.goal.schema import GoalConfig
from truman.judge.verdict import JudgeVerdict
from truman.research.base import ResearchBrief
from truman.sim.personas import Persona, build_personas, build_personas_llm, topic_pool

MAX_DWELL = 30.0  # seconds; normalizer for the dwell metric
APPEAL_CUTOFF = 0.25  # below this the persona skips the ad


def _primary(goal: GoalConfig) -> str | None:
    return goal.scene.get("product") or goal.scene.get("topic")


def _render(fields: dict) -> str:
    return (
        f"{fields.get('title', '')}\n"
        f"Hook: {fields.get('hook', '')}\n"
        f"Script: {fields.get('script', '')}"
    ).strip()


def _make_fields(angles: list[str]) -> dict:
    primary = angles[0] if angles else "your product"
    extras = ", ".join(angles[1:]) or "made for you"
    return {
        "title": f"{primary.title()} — {extras}",
        "hook": f"Stop scrolling if you care about {primary}.",
        "script": f"Open on {primary}. Beats: {', '.join(angles)}. Close on a clear CTA: try it today.",
        "storyboard": [f"Shot {i + 1}: {a}" for i, a in enumerate(angles)],
    }


# ─────────────────────────── Research agents (pluggable) ───────────────────────────


class MockAdResearcher:
    def research(self, goal: GoalConfig) -> ResearchBrief:
        angles = topic_pool(_primary(goal), size=6)
        return ResearchBrief(
            summary=f"Offline ad research for {goal.goal!r}: winning angles for the target segments.",
            audience_insights=[f"Each segment is hooked by a different angle: {', '.join(angles)}."],
            competitor_examples=["Top TikTok/Meta ads open with a pattern-interrupt hook, then stack proof."],
            recommended_angles=angles,
            raw={"primary": _primary(goal), "pool": angles},
        )


class LLMAdResearcher:
    def __init__(self, model: str | None = None) -> None:
        self._model = model

    def research(self, goal: GoalConfig) -> ResearchBrief:
        import json

        from truman.llm.runtime import complete, extract_json

        prompt = (
            "Analyze what makes TikTok/Meta ads go viral for this goal and return angles.\n"
            f"Goal: {goal.goal}\nContext: {json.dumps(goal.scene)}\n\n"
            'Return STRICT JSON: {"summary": str, "audience_insights": [str], '
            '"competitor_examples": [str], "recommended_angles": [4-6 short lowercase keyword angles]}'
        )
        try:
            data = extract_json(
                complete(
                    [
                        {"role": "system", "content": "You are a performance-ads strategist. JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    model=self._model,
                    temperature=0.4,
                    max_tokens=600,
                )
            ) or {}
        except Exception:
            data = {}
        angles = [str(a) for a in data.get("recommended_angles", [])] or topic_pool(_primary(goal), 6)
        return ResearchBrief(
            summary=str(data.get("summary", "")),
            audience_insights=list(data.get("audience_insights", [])),
            competitor_examples=list(data.get("competitor_examples", [])),
            recommended_angles=angles,
            raw={"response": data},
        )


# ─────────────────────────── Creative agents (pluggable) ───────────────────────────


class MockAdCreativeWorker:
    def create(self, goal: GoalConfig, brief: ResearchBrief, plan: str) -> CandidateArtifact:
        angles = brief.recommended_angles[:1] or [_primary(goal) or "product"]
        fields = _make_fields(angles)
        return CandidateArtifact(
            iteration=0,
            kind="ad_creative",
            content=_render(fields),
            rationale="Baseline ad: single lead angle.",
            fields=fields,
        )

    def revise(self, goal, brief, plan, previous: CandidateArtifact, verdict: JudgeVerdict) -> CandidateArtifact:
        n = min(previous.iteration + 2, len(brief.recommended_angles))
        angles = brief.recommended_angles[:n] or [_primary(goal) or "product"]
        fields = _make_fields(angles)
        return CandidateArtifact(
            iteration=previous.iteration + 1,
            kind="ad_creative",
            content=_render(fields),
            rationale=f"Revised ad addressing: {verdict.feedback}",
            parent_iteration=previous.iteration,
            fields=fields,
        )


class LLMAdCreativeWorker:
    def __init__(self, model: str | None = None) -> None:
        self._model = model

    def _gen(self, instruction: str, plan: str) -> dict:
        from truman.llm.runtime import complete, extract_json

        prompt = (
            f"{plan}\n\n{instruction}\n\n"
            'Return STRICT JSON for a short-form video ad: '
            '{"title": str, "hook": str (first 2 seconds), "script": str (<=60 words), '
            '"storyboard": [3-5 short shot descriptions]}'
        )
        data = extract_json(
            complete(
                [
                    {"role": "system", "content": "You are a viral short-form ad creative director. JSON only."},
                    {"role": "user", "content": prompt},
                ],
                model=self._model,
                temperature=0.85,
                max_tokens=600,
            )
        ) or {}
        return {
            "title": str(data.get("title", "")),
            "hook": str(data.get("hook", "")),
            "script": str(data.get("script", "")),
            "storyboard": list(data.get("storyboard", [])),
        }

    def create(self, goal: GoalConfig, brief: ResearchBrief, plan: str) -> CandidateArtifact:
        fields = self._gen(f"Write the first ad creative for: {goal.goal}", plan)
        return CandidateArtifact(0, "ad_creative", _render(fields), "LLM baseline ad.", fields=fields)

    def revise(self, goal, brief, plan, previous: CandidateArtifact, verdict: JudgeVerdict) -> CandidateArtifact:
        instruction = (
            f"Improve this ad creative (current fields: {previous.fields}).\n"
            f"Judge feedback: {verdict.feedback}\nWeaknesses: {'; '.join(verdict.weaknesses)}\n"
            "Rewrite it to lift CTR, dwell, and sentiment."
        )
        fields = self._gen(instruction, plan)
        return CandidateArtifact(
            previous.iteration + 1, "ad_creative", _render(fields),
            f"Revised per feedback: {verdict.feedback}", parent_iteration=previous.iteration, fields=fields,
        )


# ─────────────────────────── Simulation: deciders ───────────────────────────


def _appeal(persona: Persona, artifact: CandidateArtifact) -> float:
    text = " ".join(str(v) for v in (artifact.fields or {"_": artifact.content}).values()).lower()
    topics = persona.interested_topics or []
    matched = sum(1 for t in topics if t.lower() in text)
    topic_score = matched / len(topics) if topics else 0.0
    bias_score = (persona.sentiment_bias + 1.0) / 2.0
    return 0.3 * bias_score + 0.7 * topic_score


class MockAdDecider:
    """Deterministic: derive click/dwell/sentiment from interest-match appeal."""

    def decide(self, persona: Persona, artifact: CandidateArtifact) -> dict:
        appeal = _appeal(persona, artifact)
        if appeal >= APPEAL_CUTOFF:
            return {
                "action": "watch",
                "params": {
                    "click_prob": round(appeal, 4),
                    "dwell_seconds": round(MAX_DWELL * appeal, 4),
                    "sentiment": round(2 * appeal - 1, 4),
                    "reaction": f"{persona.stance} about {', '.join(persona.interested_topics)}",
                },
                "intensity": round(appeal, 4),
                "engaged": True,
            }
        return {"action": "skip", "params": {}, "intensity": 0.0, "engaged": False}


class LLMAdDecider:
    """Persona decides watch/skip + a qualitative reaction; the Evaluator predicts numbers."""

    def __init__(self, model: str | None = None) -> None:
        self._model = model
        self._fallback = MockAdDecider()

    def decide(self, persona: Persona, artifact: CandidateArtifact) -> dict:
        from truman.llm.runtime import complete, extract_json

        system = "You role-play a target-audience viewer reacting to a short video ad. JSON only."
        user = (
            f"You are: {persona.persona}\nInterests: {', '.join(persona.interested_topics)}. "
            f"Stance: {persona.stance}.\n\nThe ad:\n{artifact.content}\n\n"
            'Do you watch/click or skip? Return JSON: '
            '{"watch": true or false, "reaction": "<one short phrase>"}'
        )
        try:
            data = extract_json(
                complete([{"role": "system", "content": system}, {"role": "user", "content": user}],
                         model=self._model, temperature=0.7, max_tokens=120)
            ) or {}
        except Exception:
            return self._fallback.decide(persona, artifact)
        if bool(data.get("watch", False)):
            reaction = str(data.get("reaction", "")).strip() or "interested"
            return {"action": "watch", "params": {"reaction": reaction}, "intensity": None, "engaged": True}
        return {"action": "skip", "params": {}, "intensity": 0.0, "engaged": False}


# ─────────────────────────── Evaluator (DM provider) ───────────────────────────


def _signal_effects(click: float, dwell: float, sentiment: float, agent: str, reaction: str) -> list[EffectConfig]:
    return [
        EffectConfig(operator="increment", target="artifact.clicks", by=round(click, 4)),
        EffectConfig(operator="increment", target="artifact.dwell_total", by=round(dwell, 4)),
        EffectConfig(operator="increment", target="artifact.sentiment_total", by=round(max(0.0, sentiment), 4)),
        EffectConfig(
            operator="emit_event", type="reaction",
            detail=f"{agent}: {reaction} (click={click:.2f}, dwell={dwell:.1f}s, sent={sentiment:.2f})",
            scope="global", ttl=2,
        ),
    ]


class MockAdEvaluatorDM(MockDMProvider):
    """Deterministic Evaluator: records the click/dwell/sentiment the decider supplied."""

    async def judge(self, context: DMContext) -> DMResponse:
        p = context.action.params or {}
        click = float(p.get("click_prob", 0) or 0)
        dwell = float(p.get("dwell_seconds", 0) or 0)
        sentiment = float(p.get("sentiment", 0) or 0)
        agent = context.action.agent_id
        return DMResponse(
            narrative=f"{agent} watched the ad.",
            effects=_signal_effects(click, dwell, sentiment, agent, str(p.get("reaction", "reacted"))),
        )


class LLMAdEvaluatorDM:
    """LLM Evaluator: predicts CTR/dwell/sentiment from the viewer's reaction + the ad."""

    def __init__(self, model: str | None = None) -> None:
        self._model = model
        self._client = None

    def _aclient(self):
        if self._client is None:
            from truman.llm.runtime import get_async_client

            self._client = get_async_client()
        return self._client

    async def judge(self, context: DMContext) -> DMResponse:
        from truman.llm.runtime import _bare_model, extract_json

        p = context.action.params or {}
        reaction = str(p.get("reaction", "watched"))
        agent = context.action.agent_id
        system = (
            "You are an ad-performance evaluator. Given a viewer's reaction to a short video ad, "
            "predict click_prob (0-1), dwell_seconds (0-30), and sentiment (-1..1). JSON only."
        )
        user = (
            f"Ad / world state:\n{context.world_state}\n\n"
            f'Viewer "{agent}" reacted: "{reaction}"\n\n'
            'Return JSON: {"click_prob": <0-1>, "dwell_seconds": <0-30>, "sentiment": <-1..1>}'
        )
        click = dwell = sentiment = 0.0
        try:
            resp = await self._aclient().messages.create(
                model=_bare_model(self._model), max_tokens=120, temperature=0.3,
                system=system, messages=[{"role": "user", "content": user}],
            )
            text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
            data = extract_json(text) or {}
            click = max(0.0, min(1.0, float(data.get("click_prob", 0) or 0)))
            dwell = max(0.0, min(MAX_DWELL, float(data.get("dwell_seconds", 0) or 0)))
            sentiment = max(-1.0, min(1.0, float(data.get("sentiment", 0) or 0)))
        except Exception:
            pass
        return DMResponse(
            narrative=f"{agent} watched the ad (predicted CTR {click:.2f}).",
            effects=_signal_effects(click, dwell, sentiment, agent, reaction),
        )


# ─────────────────────────── Scene + metrics ───────────────────────────


def build_ad_scene(goal: GoalConfig, artifact: CandidateArtifact) -> SceneConfig:
    f = artifact.fields or {}
    return SceneConfig.model_validate(
        {
            "scene": {
                "id": "truman_ad_sim",
                "description": (
                    f"A short-form video ad is shown to target-audience viewers. Goal: {goal.goal} "
                    "Each viewer watches/clicks or skips; the evaluator predicts CTR, dwell, sentiment."
                ),
                "dm_knowledge": (
                    "If a watch action carries click_prob/dwell_seconds/sentiment params, record them. "
                    "Otherwise predict them (click_prob 0-1, dwell_seconds 0-30, sentiment -1..1) from the reaction."
                ),
                "max_ticks": None,
                "max_dm_calls": None,
            },
            "narrator": False,
            "entities": [
                {"id": "feed", "type": "space"},
                {
                    "id": "artifact",
                    "type": "ad_creative",
                    "title": str(f.get("title", "")),
                    "hook": str(f.get("hook", "")),
                    "script": str(f.get("script", "")),
                    "clicks": 0.0,
                    "dwell_total": 0.0,
                    "sentiment_total": 0.0,
                    "constraints": {
                        "clicks": {"min": 0},
                        "dwell_total": {"min": 0},
                        "sentiment_total": {"min": 0},
                    },
                },
            ],
            "actions": {
                "watch": {
                    "description": "Watch/click the ad and react to it.",
                    "params": [
                        {"name": "click_prob", "type": "number", "required": False},
                        {"name": "dwell_seconds", "type": "number", "required": False},
                        {"name": "sentiment", "type": "number", "required": False},
                        {"name": "reaction", "type": "free_text", "required": False},
                    ],
                    "dm": {
                        "hint": "Record or predict the viewer's click_prob, dwell, and sentiment.",
                        "allowed_ops": ["increment", "emit_event"],
                        "max_effects": 5,
                    },
                },
                "skip": {"description": "Skip the ad without engaging.", "params": []},
            },
            "perception": {"visibility": []},
        }
    )


def ad_metrics(personas: list[Persona], per_persona: dict, artifact_state: dict, events: list) -> dict[str, float]:
    n = len(personas) or 1
    clicks = float(artifact_state.get("clicks", 0.0) or 0.0)
    dwell = float(artifact_state.get("dwell_total", 0.0) or 0.0)
    sentiment = float(artifact_state.get("sentiment_total", 0.0) or 0.0)
    ctr = clicks / n
    avg_dwell = dwell / (n * MAX_DWELL)
    sentiment_ratio = sentiment / n
    roas_proxy = ctr * sentiment_ratio * avg_dwell
    return {
        "ctr": round(ctr, 4),
        "avg_dwell": round(avg_dwell, 4),
        "sentiment_ratio": round(sentiment_ratio, 4),
        "roas_proxy": round(roas_proxy, 4),
    }


# ─────────────────────────── Vertical wiring ───────────────────────────


class AdCreativeVertical:
    name = "ad_creative"

    def make_research(self, mode: str, model: str | None):
        return LLMAdResearcher(model) if mode == "llm" else MockAdResearcher()

    def make_creative(self, mode: str, model: str | None):
        return LLMAdCreativeWorker(model) if mode == "llm" else MockAdCreativeWorker()

    def make_personas(self, goal: GoalConfig, mode: str, model: str | None) -> list[Persona]:
        from truman.personas.library import build_personas_for_scene

        # New (M3): cohort or user-upload personas take priority over the
        # built-in topic-pool generators.
        cohort_personas = build_personas_for_scene(goal.scene or {}, goal.persona_count, goal.seed)
        if cohort_personas:
            return cohort_personas
        if mode == "llm":
            return build_personas_llm(goal, goal.persona_count, model)
        return build_personas(_primary(goal), goal.persona_count, goal.seed)

    def make_decider(self, mode: str, model: str | None):
        return LLMAdDecider(model) if mode == "llm" else MockAdDecider()

    def make_dm(self, mode: str, model: str | None):
        return LLMAdEvaluatorDM(model) if mode == "llm" else MockAdEvaluatorDM()

    def build_scene(self, goal: GoalConfig, artifact: CandidateArtifact) -> SceneConfig:
        return build_ad_scene(goal, artifact)

    def compute_metrics(self, personas, per_persona, artifact_state, events):
        return ad_metrics(personas, per_persona, artifact_state, events)
