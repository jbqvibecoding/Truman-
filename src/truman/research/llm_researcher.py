"""LLMResearcher — real research via LiteLLM (used in `--llm` mode).

Mirrors the intent of MiroFish's ontology/insight extraction: turn the goal
into audience insights, competitor examples, and recommended angles.
"""

from __future__ import annotations

import json

from truman.goal.schema import GoalConfig
from truman.llm.runtime import complete
from truman.research.base import ResearchBrief

_PROMPT = """You are a market/audience research analyst.
Goal: {goal}
Artifact kind: {kind}
Scene/context: {scene}

Return STRICT JSON with keys:
  summary (string),
  audience_insights (array of short strings),
  competitor_examples (array of short strings),
  recommended_angles (array of 4-6 short keyword angles, ordered by impact).
JSON only, no prose."""


class LLMResearcher:
    def __init__(self, model: str | None = None) -> None:
        self._model = model

    def research(self, goal: GoalConfig) -> ResearchBrief:
        content = complete(
            [
                {"role": "user", "content": _PROMPT.format(
                    goal=goal.goal, kind=goal.artifact_kind, scene=json.dumps(goal.scene)
                )}
            ],
            model=self._model,
            temperature=0.4,
            max_tokens=600,
        )
        data = _safe_json(content)
        return ResearchBrief(
            summary=data.get("summary", content[:200]),
            audience_insights=list(data.get("audience_insights", [])),
            competitor_examples=list(data.get("competitor_examples", [])),
            recommended_angles=[str(a) for a in data.get("recommended_angles", [])],
            raw={"response": content},
        )


def _safe_json(text: str) -> dict:
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}
