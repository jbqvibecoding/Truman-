"""LiteLLM runtime wrapper.

A thin seam so every real LLM call (research, workers, persona generation)
goes through one place, with the model selectable and defaulting to Anthropic
Claude. The in-simulation DM judge uses WorldSeed's own LiteLLMDMProvider.
"""

from __future__ import annotations

import os

DEFAULT_MODEL = "anthropic/claude-sonnet-4-5"


def default_model() -> str:
    return os.environ.get("TRUMAN_MODEL", DEFAULT_MODEL)


def complete(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> str:
    """Single-shot text completion via LiteLLM. Used only in `--llm` mode."""
    import litellm

    resp = litellm.completion(
        model=model or default_model(),
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""
