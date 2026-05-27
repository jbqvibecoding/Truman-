"""Reaction DM provider — the in-simulation judge of each persona reaction.

This is the WorldSeed DMProvider used while the simulation runs. It judges each
`react` action and emits effects that mutate world state (engagement_score).

- mock mode: deterministic — reads the persona-supplied `intensity` parameter.
- llm mode: WorldSeed's LiteLLMDMProvider judges the reaction text via LiteLLM
  + Instructor (default Anthropic Claude), deciding the engagement increment.
"""

from __future__ import annotations

from worldseed.dm.providers.mock import MockDMProvider
from worldseed.models.config_schema import EffectConfig
from worldseed.protocol.dm import DMContext, DMResponse

from truman.llm.runtime import default_model


class TrumanReactionDM(MockDMProvider):
    """Deterministic DM: applies the intensity carried on the react action."""

    async def judge(self, context: DMContext) -> DMResponse:
        params = context.action.params or {}
        intensity = float(params.get("intensity", 0) or 0)
        sentiment = params.get("sentiment", "reacted")
        agent = context.action.agent_id
        return DMResponse(
            narrative=f"{agent} engages with the content ({sentiment}).",
            effects=[
                EffectConfig(operator="increment", target="artifact.engagement_score", by=intensity),
                EffectConfig(
                    operator="emit_event",
                    type="reaction",
                    detail=f"{agent}: {sentiment} (intensity {intensity})",
                    scope="global",
                    ttl=2,
                ),
            ],
        )


def build_reaction_dm(mode: str = "mock", model: str | None = None):
    """Factory: return the DM provider appropriate for the run mode."""
    if mode == "llm":
        from worldseed.dm.providers.llm import LiteLLMDMProvider

        return LiteLLMDMProvider(model=model or default_model())
    return TrumanReactionDM()
