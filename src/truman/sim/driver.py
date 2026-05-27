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


class PersonaDecider:
    """Deterministic engagement model used in offline/mock mode."""

    def intensity(self, persona: Persona, headline: str) -> float:
        h = headline.lower()
        topics = persona.interested_topics or []
        matched = sum(1 for t in topics if t.lower() in h)
        topic_score = matched / len(topics) if topics else 0.0
        bias_score = (persona.sentiment_bias + 1.0) / 2.0  # -> [0, 1]
        raw = 0.3 * bias_score + 0.7 * topic_score
        return round(MAX_INTENSITY * raw, 3)

    def decide(self, persona: Persona, headline: str) -> dict:
        score = self.intensity(persona, headline)
        if score >= ENGAGE_CUTOFF:
            return {
                "action": "react",
                "params": {"sentiment": f"{persona.stance} reaction", "intensity": score},
                "intensity": score,
                "engaged": True,
            }
        return {"action": "scroll_past", "params": {}, "intensity": 0.0, "engaged": False}


class SimulationRunner:
    def __init__(self, dm_provider, decider: PersonaDecider | None = None) -> None:
        self._dm = dm_provider
        self._decider = decider or PersonaDecider()

    async def run(
        self,
        goal: GoalConfig,
        artifact: CandidateArtifact,
        personas: list[Persona],
    ) -> SimulationResult:
        scene = build_scene_config(goal, artifact)
        engine = WorldEngine(config=scene, dm_provider=self._dm)

        for p in personas:
            engine.register_agent(p.agent_id, properties=p.to_props(), character=p.to_character())

        per_persona: dict[str, dict] = {}
        for p in personas:
            decision = self._decider.decide(p, artifact.content)
            per_persona[p.agent_id] = {
                "engaged": decision["engaged"],
                "intensity": decision["intensity"],
                "action": decision["action"],
                "reaction": decision["params"].get("sentiment", ""),
            }
            engine.submit(p.agent_id, decision["action"], decision["params"])

        await engine.step_async()

        artifact_entity = engine.state.get("artifact")
        engagement_state = float(artifact_entity.get("engagement_score")) if artifact_entity else 0.0
        events = [e.to_dict() for e in engine.event_log.get_events(0)]

        metrics = self._metrics(personas, per_persona)
        return SimulationResult(
            artifact=artifact,
            per_persona=per_persona,
            events=events,
            metrics=metrics,
            engagement_score_state=engagement_state,
        )

    def _metrics(self, personas: list[Persona], per_persona: dict[str, dict]) -> dict[str, float]:
        n = len(personas) or 1
        intensities = [pp["intensity"] for pp in per_persona.values()]
        avg_engagement = sum(intensities) / n / MAX_INTENSITY
        engaged = [p for p in personas if per_persona[p.agent_id]["engaged"]]
        positive_ratio = len(engaged) / n
        total_inf = sum(p.influence_weight for p in personas) or 1.0
        reach = sum(p.influence_weight for p in engaged) / total_inf
        return {
            "avg_engagement": round(avg_engagement, 4),
            "positive_ratio": round(positive_ratio, 4),
            "reach": round(reach, 4),
        }
