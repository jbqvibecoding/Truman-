"""Reaction DM provider — the in-simulation judge of each persona reaction.

This is the WorldSeed DMProvider used while the simulation runs. It judges each
`react` action and emits effects that mutate world state (engagement_score).
WorldSeed's DMProvider is a structural Protocol, so any object exposing
``async judge(context) -> DMResponse`` works.

- mock mode: TrumanReactionDM — deterministic, reads the persona-supplied
  `intensity` parameter.
- llm mode: AnthropicReactionDM — the judge reads the reaction sentiment and
  rates engagement (0-10) with a real LLM (Anthropic SDK, OAuth or API key).
  This is the "judge learns the reward function" layer.
"""

from __future__ import annotations

from worldseed.dm.providers.mock import MockDMProvider
from worldseed.models.config_schema import EffectConfig
from worldseed.protocol.dm import DMContext, DMResponse


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


class AnthropicReactionDM:
    """LLM judge: rates how strongly the reacting persona engaged (0-10)."""

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

        params = context.action.params or {}
        sentiment = params.get("sentiment", "reacted")
        agent = context.action.agent_id
        system = (
            "You are an audience-engagement analyst. Given an audience member's reaction to a "
            "piece of content, rate how strongly they engaged on a 0-10 scale "
            "(0 = ignored it, 5 = mild interest, 10 = viral-level enthusiasm). Output strict JSON only."
        )
        user = (
            f"Content / world state:\n{context.world_state}\n\n"
            f'Audience member "{agent}" reacted: "{sentiment}"\n\n'
            'Return JSON: {"engagement": <number 0-10>, "reason": "<short>"}'
        )
        score = 0.0
        reason = ""
        try:
            resp = await self._aclient().messages.create(
                model=_bare_model(self._model),
                max_tokens=120,
                temperature=0.3,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
            data = extract_json(text) or {}
            score = float(data.get("engagement", 0) or 0)
            reason = str(data.get("reason", ""))
        except Exception as e:  # noqa: BLE001 — never let a judge call crash the tick
            reason = f"judge error: {e}"
        score = max(0.0, min(10.0, score))
        return DMResponse(
            narrative=f"{agent} engages ({sentiment}); judged engagement {score}/10.",
            effects=[
                EffectConfig(operator="increment", target="artifact.engagement_score", by=score),
                EffectConfig(
                    operator="emit_event",
                    type="reaction",
                    detail=f"{agent}: {sentiment} -> {score}/10 ({reason})",
                    scope="global",
                    ttl=2,
                ),
            ],
        )


def build_reaction_dm(mode: str = "mock", model: str | None = None):
    """Factory: return the DM provider appropriate for the run mode."""
    if mode == "llm":
        return AnthropicReactionDM(model)
    return TrumanReactionDM()
