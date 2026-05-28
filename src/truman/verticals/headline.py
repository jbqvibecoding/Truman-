"""HeadlineVertical — the default vertical (content/headline engagement).

Pure delegation to the original implementations so behaviour is unchanged; this
is what proves the loop became generic without regressing the existing demo.
"""

from __future__ import annotations

from truman.agents.base import CandidateArtifact
from truman.agents.mock_worker import MockWorker
from truman.goal.schema import GoalConfig
from truman.judge.reaction_dm import build_reaction_dm
from truman.sim.driver import LLMPersonaDecider, PersonaDecider, SimulationRunner
from truman.sim.personas import Persona, build_personas, build_personas_llm
from truman.sim.scene_builder import build_scene_config


class HeadlineVertical:
    name = "headline"

    def make_research(self, mode: str, model: str | None):
        if mode == "llm":
            from truman.research.llm_researcher import LLMResearcher

            return LLMResearcher(model)
        from truman.research.mock_researcher import MockResearcher

        return MockResearcher()

    def make_creative(self, mode: str, model: str | None):
        if mode == "llm":
            from truman.agents.worker import LLMWorker

            return LLMWorker(model)
        return MockWorker()

    def make_personas(self, goal: GoalConfig, mode: str, model: str | None) -> list[Persona]:
        if mode == "llm":
            return build_personas_llm(goal, goal.persona_count, model)
        return build_personas(goal.scene.get("topic"), goal.persona_count, goal.seed)

    def make_decider(self, mode: str, model: str | None):
        return LLMPersonaDecider(model) if mode == "llm" else PersonaDecider()

    def make_dm(self, mode: str, model: str | None):
        return build_reaction_dm(mode, model)

    def build_scene(self, goal: GoalConfig, artifact: CandidateArtifact):
        return build_scene_config(goal, artifact)

    def compute_metrics(self, personas, per_persona, artifact_state, events):
        return SimulationRunner._default_metrics(personas, per_persona, artifact_state, events)
