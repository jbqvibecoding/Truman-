"""Eval utilities — robust JSON parsing + the Eval-Guide condensed prompt.

`safe_extract_json_with_retry` is ported from MiroFish
(`backend/app/services/simulation_config_generator.py:434-481`): some LLM
responses wrap JSON in prose / fences / markdown; we strip + retry rather than
fail the whole recommend pass on a single malformed reply.

`EVAL_GUIDE_SYSTEM_PROMPT` is the condensed binary-Eval golden rule used by the
LLM Recommender's system prompt (mirrors `docs/eval-guide.md`).
"""

from __future__ import annotations

from typing import Any, Callable

from truman.llm.runtime import extract_json


def safe_extract_json_with_retry(
    call_fn: Callable[[], str],
    max_retries: int = 2,
) -> Any:
    """Call `call_fn`, extract JSON, retry up to `max_retries` times on failure.

    Returns the parsed JSON (dict/list) or None if all attempts fail. The caller
    decides the fallback (typically: use the deterministic mock recommender).
    """
    for _ in range(max_retries + 1):
        try:
            text = call_fn()
        except Exception:
            continue
        data = extract_json(text)
        if data is not None:
            return data
    return None


EVAL_GUIDE_SYSTEM_PROMPT = """You design binary (yes/no) Evals for an AI auto-research loop.

GOLDEN RULES (MANDATORY):
1. Every Eval MUST be a yes/no question — never a 1-10 scale, never a "rate it" prompt.
2. Recommend EXACTLY 3-6 evals. Too many invites gaming; too few is undertrained.
3. Each Eval must be INDEPENDENT — no two evals measuring the same dimension.
4. Each Eval must be OBSERVABLE — answerable stably by one of:
   - llm_judge (subjective but binary judgment by an LLM)
   - regex (forbidden/required keyword match)
   - length (character/word count in a range)
   - range (a continuous metric like ctr clears a threshold)
   - code (code runs / tests pass)
   - composed (AND/OR of sub-evals)
5. Prefer simpler check_kinds: regex > length > range > llm_judge > code > composed.
6. Output ONLY JSON; never include prose or fences.

Reject and rewrite any quality scale ("how good is it"); rephrase as a specific
yes/no contract ("does it contain a number AND a verb AND fewer than 30 words?").
"""
