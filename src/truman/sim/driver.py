"""Simulation driver — wraps WorldSeed's WorldEngine.

PersonaDecider computes each persona's reaction to the artifact (offline,
deterministic). SimulationRunner registers personas as WorldSeed agents,
submits their actions, advances the engine with `step_async()` (so the DM
judges the reactions and mutates engagement state), then reads back the
result. The same runner works with a mock DM (offline) or the real
LiteLLMDMProvider — only the dm_provider differs.
"""

from __future__ import annotations

from worldseed.world import WorldEngine

from truman.agents.base import CandidateArtifact
from truman.goal.schema import GoalConfig
from truman.sim.personas import Persona
from truman.sim.result import SimulationResult
from truman.sim.scene_builder import MAX_INTENSITY, build_scene_config

ENGAGE_CUTOFF = 3.0  # intensity below this => the persona scrolls past


class LLMPersonaDecider:
    """Each persona decides via a real LLM whether to engage with the artifact.

    Produces only a qualitative reaction (engage + sentiment); the engagement
    magnitude is left to the Judge (the DM). Falls back to the deterministic
    decider if an LLM call fails, so one bad response never breaks the run.
    """

    def __init__(self, model: str | None = None) -> None:
        self._model = model
        self._fallback = PersonaDecider()

    def decide(self, persona: Persona, artifact: CandidateArtifact) -> dict:
        from truman.llm.runtime import complete, extract_json

        system = "You role-play a social-media user deciding whether to engage with a post. Output strict JSON only."
        user = (
            f"You are this person:\n{persona.persona}\n"
            f"Interests: {', '.join(persona.interested_topics)}. Stance: {persona.stance}.\n\n"
            f'You scroll past and see this content: "{artifact.content}"\n\n'
            "Will you engage (like/comment/share) or scroll past? Be honest to your persona.\n"
            'Return JSON: {"engage": true or false, "sentiment": "<one short phrase of your reaction>"}'
        )
        try:
            text = complete(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                model=self._model,
                temperature=0.7,
                max_tokens=120,
            )
            data = extract_json(text) or {}
            engage = bool(data.get("engage", False))
            sentiment = str(data.get("sentiment", "")).strip() or ("interested" if engage else "not interested")
        except Exception:
            return self._fallback.decide(persona, artifact)
        if engage:
            return {"action": "react", "params": {"sentiment": sentiment}, "intensity": None, "engaged": True}
        return {"action": "scroll_past", "params": {}, "intensity": 0.0, "engaged": False}


class PersonaDecider:
    """Deterministic engagement model used in offline/mock mode."""

    def intensity(self, persona: Persona, artifact: CandidateArtifact) -> float:
        h = artifact.content.lower()
        topics = persona.interested_topics or []
        matched = sum(1 for t in topics if t.lower() in h)
        topic_score = matched / len(topics) if topics else 0.0
        bias_score = (persona.sentiment_bias + 1.0) / 2.0  # -> [0, 1]
        raw = 0.3 * bias_score + 0.7 * topic_score
        return round(MAX_INTENSITY * raw, 3)

    def decide(self, persona: Persona, artifact: CandidateArtifact) -> dict:
        score = self.intensity(persona, artifact)
        if score >= ENGAGE_CUTOFF:
            return {
                "action": "react",
                "params": {"sentiment": f"{persona.stance} reaction", "intensity": score},
                "intensity": score,
                "engaged": True,
            }
        return {"action": "scroll_past", "params": {}, "intensity": 0.0, "engaged": False}


class SimulationRunner:
    """Vertical-agnostic simulation driver.

    The scene construction and metric computation are injected by the active
    vertical (`scene_builder`, `metrics_fn`); they default to the headline
    engagement behaviour so existing callers keep working.
    """

    def __init__(
        self,
        dm_provider,
        decider=None,
        scene_builder=None,
        metrics_fn=None,
    ) -> None:
        self._dm = dm_provider
        self._decider = decider or PersonaDecider()
        self._scene_builder = scene_builder or build_scene_config
        self._metrics_fn = metrics_fn or self._default_metrics

    async def run(
        self,
        goal: GoalConfig,
        artifact: CandidateArtifact,
        personas: list[Persona],
    ) -> SimulationResult:
        scene = self._scene_builder(goal, artifact)
        engine = WorldEngine(config=scene, dm_provider=self._dm)

        for p in personas:
            engine.register_agent(p.agent_id, properties=p.to_props(), character=p.to_character())

        per_persona: dict[str, dict] = {}
        for p in personas:
            decision = self._decider.decide(p, artifact)
            per_persona[p.agent_id] = {
                "engaged": decision["engaged"],
                "intensity": decision["intensity"],
                "action": decision["action"],
                "reaction": decision["params"].get("sentiment", ""),
            }
            engine.submit(p.agent_id, decision["action"], decision["params"])

        await engine.step_async()

        artifact_entity = engine.state.get("artifact")
        artifact_state = dict(artifact_entity.to_full_dict()) if artifact_entity else {}
        events = [e.to_dict() for e in engine.event_log.get_events(0)]

        metrics = self._metrics_fn(personas, per_persona, artifact_state, events)
        return SimulationResult(
            artifact=artifact,
            per_persona=per_persona,
            events=events,
            metrics=metrics,
            artifact_state=artifact_state,
        )

    @staticmethod
    def _default_metrics(
        personas: list[Persona],
        per_persona: dict[str, dict],
        artifact_state: dict,
        events: list[dict],
    ) -> dict[str, float]:
        """Headline engagement metrics (default vertical)."""
        n = len(personas) or 1
        engagement_state = float(artifact_state.get("engagement_score", 0.0) or 0.0)
        avg_engagement = engagement_state / (n * MAX_INTENSITY)
        engaged = [p for p in personas if per_persona[p.agent_id]["engaged"]]
        positive_ratio = len(engaged) / n
        total_inf = sum(p.influence_weight for p in personas) or 1.0
        reach = sum(p.influence_weight for p in engaged) / total_inf
        return {
            "avg_engagement": round(avg_engagement, 4),
            "positive_ratio": round(positive_ratio, 4),
            "reach": round(reach, 4),
        }
