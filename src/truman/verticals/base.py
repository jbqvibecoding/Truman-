"""Vertical interface — the pluggability seam.

A Vertical bundles the scenario-specific pieces the generic recursive loop
needs: which research/creative providers to use, how to generate the audience,
how to build the WorldSeed scene, how each persona decides, which DM judges the
reactions, and how to turn the simulation into metrics. The orchestrator loop
stays vertical-agnostic and selects a Vertical by `goal.vertical`.

`mode` is "mock" (offline) or "llm" (real Anthropic). `model` is an optional
model id. Both are threaded into every factory so a vertical returns the right
implementation for the run.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from worldseed.models.config_schema import SceneConfig

    from truman.agents.base import CandidateArtifact, WorkerProvider
    from truman.goal.schema import GoalConfig
    from truman.research.base import ResearchProvider
    from truman.sim.personas import Persona


@runtime_checkable
class Vertical(Protocol):
    name: str

    def make_research(self, mode: str, model: str | None) -> ResearchProvider: ...

    def make_creative(self, mode: str, model: str | None) -> WorkerProvider: ...

    def make_personas(self, goal: GoalConfig, mode: str, model: str | None) -> list[Persona]: ...

    def make_decider(self, mode: str, model: str | None): ...

    def make_dm(self, mode: str, model: str | None): ...

    def build_scene(self, goal: GoalConfig, artifact: CandidateArtifact) -> SceneConfig: ...

    def compute_metrics(
        self,
        personas: list[Persona],
        per_persona: dict[str, dict],
        artifact_state: dict,
        events: list[dict],
    ) -> dict[str, float]: ...
