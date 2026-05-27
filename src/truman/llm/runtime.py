"""LLM runtime — Anthropic SDK wrapper.

A single seam for every real LLM call (research, workers, persona generation,
the DM judge). Credentials are read from the environment so nothing is
embedded in code:

  - ANTHROPIC_OAUTH_TOKEN (or TRUMAN_OAUTH_TOKEN): Claude OAuth bearer token;
    sent with the `oauth-2025-04-20` beta header.
  - ANTHROPIC_API_KEY: standard API key.

Default model is overridable via TRUMAN_MODEL or per call. Provider prefixes
like "anthropic/" are stripped so LiteLLM-style ids still work.
"""

from __future__ import annotations

import json
import os
from typing import Any

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_OAUTH_BETA = "oauth-2025-04-20"


def default_model() -> str:
    return os.environ.get("TRUMAN_MODEL", DEFAULT_MODEL)


def _bare_model(model: str | None) -> str:
    m = model or default_model()
    return m.split("/", 1)[1] if m.startswith("anthropic/") else m


def _auth_kwargs() -> dict[str, Any]:
    tok = os.environ.get("ANTHROPIC_OAUTH_TOKEN") or os.environ.get("TRUMAN_OAUTH_TOKEN")
    if tok:
        return {"auth_token": tok, "default_headers": {"anthropic-beta": _OAUTH_BETA}}
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return {"api_key": key}
    msg = "No Anthropic credentials: set ANTHROPIC_OAUTH_TOKEN or ANTHROPIC_API_KEY."
    raise RuntimeError(msg)


def get_client():
    import anthropic

    return anthropic.Anthropic(**_auth_kwargs())


def get_async_client():
    import anthropic

    return anthropic.AsyncAnthropic(**_auth_kwargs())


def _split_messages(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    convo = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
    return system, convo


def complete(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> str:
    """Single-shot text completion via the Anthropic SDK."""
    import anthropic

    client = get_client()
    system, convo = _split_messages(messages)
    resp = client.messages.create(
        model=_bare_model(model),
        max_tokens=max_tokens,
        temperature=temperature,
        system=system or anthropic.NOT_GIVEN,
        messages=convo or [{"role": "user", "content": ""}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")


def extract_json(text: str) -> Any:
    """Best-effort JSON extraction from an LLM reply (handles ``` fences)."""
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1]
        if s.endswith("```"):
            s = s[: -3]
    s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Fall back to the first balanced object or array.
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start, end = s.find(open_c), s.rfind(close_c)
        if start != -1 and end > start:
            try:
                return json.loads(s[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None
