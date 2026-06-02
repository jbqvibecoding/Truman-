"""Shared base for "content"-style verticals (M5 + M6).

The 7 content verticals (viral / landing page / cold email / SEO / sales
script / PRD doc / PDP page) all share the same shape: a structured artifact
generated from a topic pool of angles, scored on 3-4 audience-reaction metrics
that improve monotonically as more angles are incorporated.

A concrete vertical specifies its config (`ContentSpec`) and gets a working
Vertical implementation back. This keeps the 7 files thin and consistent
without duplicating ~150 lines of boilerplate each.

The structurally-different SoftwareEngVertical (M5.1) and AdCreativeVertical
(M0) are NOT built from this base — they have richer mechanics.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from worldseed.dm.providers.mock import MockDMProvider
from worldseed.models.config_schema import EffectConfig, SceneConfig
from worldseed.protocol.dm import DMContext, DMResponse

from truman.agents.base import CandidateArtifact
from truman.goal.schema import GoalConfig
from truman.judge.verdict import JudgeVerdict
from truman.research.base import ResearchBrief
from truman.sim.personas import Persona, build_personas, build_personas_llm, topic_pool

# Engagement cutoff: below this the persona "skips" the artifact and emits no
# DM-judged effect. Keeps offline mock runs progressively-improving.
_APPEAL_CUTOFF = 0.2


@dataclass(frozen=True)
class ContentSpec:
    """A concrete content vertical's identity + parameterization."""

    name: str                       # vertical key e.g. "viral_content"
    artifact_kind: str              # e.g. "tweet", "landing_page"
    fields: list[str]               # structured artifact field keys
    default_cohort: str | None      # built-in cohort name (or None to use topic pool)
    primary_topic_keys: list[str] = field(default_factory=lambda: ["topic"])
    metric_keys: list[str] = field(default_factory=lambda: ["engagement", "reach", "sentiment"])
    action_name: str = "react"
    # Optional: weight to scale composite metric (sum to 1.0 is conventional)
    metric_weights: dict[str, float] = field(default_factory=dict)
    # Human-readable description for prompts / scene
    description: str = "Content optimization vertical."


def _primary(goal: GoalConfig, spec: ContentSpec) -> str:
    scene = goal.scene or {}
    for k in spec.primary_topic_keys:
        if scene.get(k):
            return str(scene[k])
    return "content"


def _render(spec: ContentSpec, fields: dict) -> str:
    parts: list[str] = []
    for k in spec.fields:
        v = fields.get(k, "")
        if isinstance(v, list):
            v = " · ".join(str(x) for x in v)
        parts.append(f"{k}: {v}")
    return "\n".join(parts)


def _make_fields(spec: ContentSpec, angles: list[str]) -> dict:
    """Distribute the angles across the spec's field slots progressively."""
    out: dict = {}
    primary = angles[0] if angles else "topic"
    for i, k in enumerate(spec.fields):
        if k == "storyboard" or k.endswith("_list"):
            out[k] = list(angles)
        elif k == "subject":
            out[k] = f"{primary.title()} — practical for you"
        elif k == "hook" or k == "opener":
            out[k] = f"Stop scrolling if you care about {primary}."
        elif k == "headline" or k == "title":
            out[k] = f"{primary.title()} — {', '.join(angles[1:]) or 'made for you'}"
        elif k == "cta":
            out[k] = "Try it today" if not angles else f"Try {primary} today"
        elif k == "body" or k == "script" or k == "content":
            out[k] = (
                f"Open on {primary}. Beats: {', '.join(angles)}. "
                "Close on a clear CTA: try it today."
            )
        elif k == "meta":
            out[k] = f"Quick guide to {primary} covering {', '.join(angles)}."
        elif k == "outline":
            out[k] = [f"H2: {a}" for a in angles[:4]]
        elif k == "faq":
            out[k] = [f"Q: What about {a}? A: yes, see below." for a in angles[:3]]
        elif k == "bullets":
            out[k] = [f"- {a}" for a in angles]
        elif k == "pain_dx":
            out[k] = f"You're dealing with {angles[i % len(angles)] if angles else primary}."
        elif k == "solution":
            out[k] = f"Here's how we fix it via {', '.join(angles)}."
        elif k == "objection_handling":
            out[k] = [f"If they say '{a} too risky', reply with proof." for a in angles[:2]]
        elif k == "user_stories":
            out[k] = [f"As a user I want {a} so that I can succeed." for a in angles[:3]]
        elif k == "acceptance_criteria":
            out[k] = [f"Given {a}, when invoked, then it works." for a in angles[:3]]
        elif k == "edge_cases":
            out[k] = [f"What if {a} is empty?" for a in angles[:3]]
        elif k == "badges":
            out[k] = [a for a in angles[:3]]
        elif k == "detail":
            out[k] = f"Detail: covers {', '.join(angles)}."
        else:
            out[k] = ", ".join(angles[: max(1, len(angles) // 2)]) or primary
    return out


# ─── Research + Creative (mock + llm) ────────────────────────────────────


class _MockResearcher:
    def __init__(self, spec: ContentSpec) -> None:
        self._spec = spec

    def research(self, goal: GoalConfig) -> ResearchBrief:
        primary = _primary(goal, self._spec)
        angles = topic_pool(primary, size=6)
        return ResearchBrief(
            summary=f"Offline research for {self._spec.name}: {goal.goal!r}.",
            audience_insights=[f"Angles to cover for {primary}: {', '.join(angles)}."],
            competitor_examples=[f"Top examples in {self._spec.name} lead with a hook + proof."],
            recommended_angles=angles,
            raw={"primary": primary},
        )


class _LLMResearcher:
    def __init__(self, spec: ContentSpec, model: str | None) -> None:
        self._spec = spec
        self._model = model

    def research(self, goal: GoalConfig) -> ResearchBrief:
        from truman.llm.runtime import complete, extract_json

        prompt = (
            f"Vertical: {self._spec.name} ({self._spec.description})\n"
            f"Goal: {goal.goal}\nScene: {goal.scene}\n\n"
            'Return strict JSON: {"summary": str, "audience_insights": [str], '
            '"competitor_examples": [str], "recommended_angles": [4-6 short keywords]}'
        )
        data: dict = {}
        try:
            data = extract_json(complete(
                [{"role": "system", "content": "You are an audience-research strategist. JSON only."},
                 {"role": "user", "content": prompt}],
                model=self._model, temperature=0.4, max_tokens=600,
            )) or {}
        except Exception:
            pass
        angles = [str(a) for a in data.get("recommended_angles", [])] or topic_pool(_primary(goal, self._spec), 6)
        return ResearchBrief(
            summary=str(data.get("summary", "")),
            audience_insights=list(data.get("audience_insights", [])),
            competitor_examples=list(data.get("competitor_examples", [])),
            recommended_angles=angles,
            raw={"response": data},
        )


class _MockWorker:
    def __init__(self, spec: ContentSpec) -> None:
        self._spec = spec

    def create(self, goal: GoalConfig, brief: ResearchBrief, plan: str) -> CandidateArtifact:
        angles = brief.recommended_angles[:1] or [_primary(goal, self._spec)]
        fields = _make_fields(self._spec, angles)
        return CandidateArtifact(
            iteration=0, kind=self._spec.artifact_kind,
            content=_render(self._spec, fields),
            rationale=f"{self._spec.name}: baseline — single angle.",
            fields=fields,
        )

    def revise(self, goal, brief, plan, previous: CandidateArtifact, verdict: JudgeVerdict) -> CandidateArtifact:
        n = min(previous.iteration + 2, len(brief.recommended_angles))
        angles = brief.recommended_angles[:n] or [_primary(goal, self._spec)]
        fields = _make_fields(self._spec, angles)
        return CandidateArtifact(
            iteration=previous.iteration + 1, kind=self._spec.artifact_kind,
            content=_render(self._spec, fields),
            rationale=f"{self._spec.name}: revised per feedback — {verdict.feedback}",
            parent_iteration=previous.iteration, fields=fields,
        )


class _LLMWorker:
    def __init__(self, spec: ContentSpec, model: str | None) -> None:
        self._spec = spec
        self._model = model
        self._fallback = _MockWorker(spec)

    def _gen(self, instruction: str, plan: str) -> dict:
        from truman.llm.runtime import complete, extract_json

        fields_doc = ", ".join(f'"{k}"' for k in self._spec.fields)
        prompt = (
            f"{plan}\n\n{instruction}\n\n"
            f"Return strict JSON with these keys: {{{fields_doc}}}."
        )
        try:
            data = extract_json(complete(
                [{"role": "system", "content": f"You are a content creator for {self._spec.name}. JSON only."},
                 {"role": "user", "content": prompt}],
                model=self._model, temperature=0.8, max_tokens=900,
            )) or {}
        except Exception:
            return {}
        return {k: data.get(k, "") for k in self._spec.fields}

    def create(self, goal, brief, plan) -> CandidateArtifact:
        fields = self._gen(f"Write the first {self._spec.artifact_kind} for: {goal.goal}", plan)
        if not any(fields.values()):
            return self._fallback.create(goal, brief, plan)
        return CandidateArtifact(
            0, self._spec.artifact_kind, _render(self._spec, fields),
            f"{self._spec.name}: LLM baseline.", fields=fields,
        )

    def revise(self, goal, brief, plan, previous, verdict):
        instr = (
            f"Improve this {self._spec.artifact_kind} (current: {previous.fields}). "
            f"Feedback: {verdict.feedback}. Rewrite to score higher."
        )
        fields = self._gen(instr, plan)
        if not any(fields.values()):
            return self._fallback.revise(goal, brief, plan, previous, verdict)
        return CandidateArtifact(
            previous.iteration + 1, self._spec.artifact_kind, _render(self._spec, fields),
            f"{self._spec.name}: revised per feedback.",
            parent_iteration=previous.iteration, fields=fields,
        )


# ─── Decider + Evaluator (mock + llm) ────────────────────────────────────


def _appeal(persona: Persona, artifact: CandidateArtifact) -> float:
    """Mock appeal heuristic: bias + persona-topic match + richness signal.

    The richness signal (artifact length / 250 chars capped at 1.0) gives the
    deterministic mock a way to register monotonic improvement even when the
    cohort's interest topics don't lexically match the worker's topic pool —
    each iteration adds one more angle so the artifact text grows.
    """
    text = " ".join(str(v) for v in (artifact.fields or {"_": artifact.content}).values()).lower()
    topics = persona.interested_topics or []
    matched = sum(1 for t in topics if t.lower() in text)
    topic_score = matched / len(topics) if topics else 0.0
    bias_score = (persona.sentiment_bias + 1.0) / 2.0
    richness = min(1.0, len(text) / 250.0)
    return 0.25 * bias_score + 0.35 * topic_score + 0.40 * richness


class _MockDecider:
    def decide(self, persona: Persona, artifact: CandidateArtifact) -> dict:
        appeal = _appeal(persona, artifact)
        if appeal < _APPEAL_CUTOFF:
            return {"action": "skip", "params": {}, "intensity": 0.0, "engaged": False}
        return {
            "action": "react",
            "params": {
                "appeal": round(appeal, 4),
                "sentiment": round(2 * appeal - 1, 4),
                "reaction": f"{persona.stance} reaction",
            },
            "intensity": round(appeal, 4),
            "engaged": True,
        }


class _LLMDecider:
    def __init__(self, spec: ContentSpec, model: str | None) -> None:
        self._spec = spec
        self._model = model
        self._mock = _MockDecider()

    def decide(self, persona: Persona, artifact: CandidateArtifact) -> dict:
        from truman.llm.runtime import complete, extract_json

        prompt = (
            f"You are: {persona.persona}\nReact to this {self._spec.artifact_kind}:\n{artifact.content[:600]}\n\n"
            'Return JSON: {"engage": true|false, "reaction": "<one short phrase>"}'
        )
        try:
            data = extract_json(complete(
                [{"role": "system", "content": "You role-play an audience member. JSON only."},
                 {"role": "user", "content": prompt}],
                model=self._model, temperature=0.7, max_tokens=120,
            )) or {}
            if data.get("engage"):
                return {"action": "react",
                        "params": {"reaction": str(data.get("reaction", ""))[:80]},
                        "intensity": None, "engaged": True}
        except Exception:
            return self._mock.decide(persona, artifact)
        return {"action": "skip", "params": {}, "intensity": 0.0, "engaged": False}


class _MockEvaluatorDM(MockDMProvider):
    """Generic 3-metric evaluator DM for content verticals.

    Reads `appeal / sentiment` from the action params and increments one
    counter per metric_key in spec. The mock decider provides appeal already,
    keeping mock runs offline-deterministic.
    """

    def __init__(self, spec: ContentSpec) -> None:
        super().__init__()
        self._spec = spec

    async def judge(self, context: DMContext) -> DMResponse:
        p = context.action.params or {}
        appeal = float(p.get("appeal", 0.0) or 0.0)
        sentiment = float(p.get("sentiment", 0.0) or 0.0)
        # Each metric key gets an increment derived from appeal. Sentiment is
        # added separately for the sentiment-style metric.
        effects: list[EffectConfig] = []
        for mkey in self._spec.metric_keys:
            if mkey in ("sentiment_ratio", "sentiment"):
                effects.append(EffectConfig(
                    operator="increment", target=f"artifact.{mkey}_total",
                    by=round(max(0.0, sentiment), 4),
                ))
            else:
                effects.append(EffectConfig(
                    operator="increment", target=f"artifact.{mkey}_total",
                    by=round(appeal, 4),
                ))
        effects.append(EffectConfig(
            operator="emit_event", type="reaction",
            detail=f"{context.action.agent_id}: appeal={appeal:.2f} sentiment={sentiment:.2f}",
            scope="global", ttl=2,
        ))
        return DMResponse(narrative=f"{context.action.agent_id} engaged.", effects=effects)


class _LLMEvaluatorDM:
    """Mirror of MockEvaluatorDM for LLM mode — for v1 we just call the mock
    since deciders already return appeal."""

    def __init__(self, spec: ContentSpec, model: str | None) -> None:
        self._mock = _MockEvaluatorDM(spec)

    async def judge(self, context: DMContext) -> DMResponse:
        return await self._mock.judge(context)


# ─── Scene + metrics ───────────────────────────────────────────────────────


def _scene(spec: ContentSpec, goal: GoalConfig, artifact: CandidateArtifact) -> SceneConfig:
    f = artifact.fields or {}
    # Flatten string-coercible fields into the artifact entity for the DM to see.
    entity_props = {"id": "artifact", "type": spec.artifact_kind}
    for k in spec.fields:
        v = f.get(k, "")
        if isinstance(v, list):
            v = "\n".join(str(x) for x in v)
        entity_props[k] = str(v)[:2000]
    counters = {f"{m}_total": 0.0 for m in spec.metric_keys}
    entity_props.update(counters)
    entity_props["constraints"] = {f"{m}_total": {"min": 0} for m in spec.metric_keys}

    return SceneConfig.model_validate({
        "scene": {
            "id": f"truman_{spec.name}_sim",
            "description": spec.description + f" Goal: {goal.goal}",
            "dm_knowledge": "Record per-reaction appeal + sentiment; increment counters.",
            "max_ticks": None, "max_dm_calls": None,
        },
        "narrator": False,
        "entities": [
            {"id": "feed", "type": "space"},
            entity_props,
        ],
        "actions": {
            "react": {
                "description": f"React to the {spec.artifact_kind}.",
                "params": [
                    {"name": "appeal", "type": "number", "required": False},
                    {"name": "sentiment", "type": "number", "required": False},
                    {"name": "reaction", "type": "free_text", "required": False},
                ],
                "dm": {"hint": "Record appeal + sentiment.",
                       "allowed_ops": ["increment", "emit_event"], "max_effects": 6},
            },
            "skip": {"description": "Skip without engaging.", "params": []},
        },
        "perception": {"visibility": []},
    })


def _metrics(spec: ContentSpec, personas, per_persona, artifact_state, events) -> dict[str, float]:
    n = max(1, len(personas))
    out: dict[str, float] = {}
    for m in spec.metric_keys:
        total = float(artifact_state.get(f"{m}_total", 0.0) or 0.0)
        out[m] = round(total / n, 4)
    return out


# ─── Vertical factory ────────────────────────────────────────────────────


class ContentVertical:
    """A reusable Vertical implementation parameterized by ContentSpec."""

    def __init__(self, spec: ContentSpec) -> None:
        self.spec = spec
        self.name = spec.name

    def make_research(self, mode, model):
        return _LLMResearcher(self.spec, model) if mode == "llm" else _MockResearcher(self.spec)

    def make_creative(self, mode, model):
        return _LLMWorker(self.spec, model) if mode == "llm" else _MockWorker(self.spec)

    def make_personas(self, goal: GoalConfig, mode: str, model: str | None) -> list[Persona]:
        from truman.personas.library import build_personas_for_scene
        scene = dict(goal.scene or {})
        if self.spec.default_cohort and "cohort" not in scene and "persona_upload_csv" not in scene:
            scene.setdefault("cohort", self.spec.default_cohort)
        cohort_personas = build_personas_for_scene(scene, goal.persona_count, goal.seed)
        if cohort_personas:
            return cohort_personas
        if mode == "llm":
            return build_personas_llm(goal, goal.persona_count, model)
        return build_personas(_primary(goal, self.spec), goal.persona_count, goal.seed)

    def make_decider(self, mode, model):
        return _LLMDecider(self.spec, model) if mode == "llm" else _MockDecider()

    def make_dm(self, mode, model):
        return _LLMEvaluatorDM(self.spec, model) if mode == "llm" else _MockEvaluatorDM(self.spec)

    def build_scene(self, goal, artifact) -> SceneConfig:
        return _scene(self.spec, goal, artifact)

    def compute_metrics(self, personas, per_persona, artifact_state, events):
        return _metrics(self.spec, personas, per_persona, artifact_state, events)
