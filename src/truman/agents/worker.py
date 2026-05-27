"""LLMWorker — real artifact generation/revision via LiteLLM (`--llm` mode)."""

from __future__ import annotations

from truman.agents.base import CandidateArtifact
from truman.goal.schema import GoalConfig
from truman.judge.verdict import JudgeVerdict
from truman.llm.runtime import complete
from truman.research.base import ResearchBrief


class LLMWorker:
    def __init__(self, model: str | None = None) -> None:
        self._model = model

    _SYSTEM = (
        "You are a sharp direct-response copywriter. Output ONLY the headline text — one short, "
        "punchy line under ~90 characters. No keyword-stuffing, no lists, no quotes, no preamble."
    )

    def _gen(self, instruction: str, plan: str) -> str:
        text = complete(
            [
                {"role": "system", "content": self._SYSTEM},
                {"role": "user", "content": f"{plan}\n\n{instruction}"},
            ],
            model=self._model,
            temperature=0.8,
            max_tokens=80,
        )
        line = text.strip().splitlines()[0].strip() if text.strip() else ""
        return line.strip('"').strip()

    def create(self, goal: GoalConfig, brief: ResearchBrief, plan: str) -> CandidateArtifact:
        instruction = f"Write a first {goal.artifact_kind} for: {goal.goal}"
        return CandidateArtifact(
            iteration=0,
            kind=goal.artifact_kind,
            content=self._gen(instruction, plan),
            rationale="LLM baseline.",
        )

    def revise(
        self,
        goal: GoalConfig,
        brief: ResearchBrief,
        plan: str,
        previous: CandidateArtifact,
        verdict: JudgeVerdict,
    ) -> CandidateArtifact:
        instruction = (
            f"Improve this {goal.artifact_kind}:\n{previous.content!r}\n\n"
            f"Judge feedback: {verdict.feedback}\n"
            f"Weaknesses: {'; '.join(verdict.weaknesses)}\n"
            "Rewrite it to score higher."
        )
        return CandidateArtifact(
            iteration=previous.iteration + 1,
            kind=goal.artifact_kind,
            content=self._gen(instruction, plan),
            rationale=f"Revised per feedback: {verdict.feedback}",
            parent_iteration=previous.iteration,
        )
