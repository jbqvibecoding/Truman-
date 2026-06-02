"""Six binary check_kind executors + dispatcher.

Each checker takes an EvalQuestion, the candidate artifact, and the latest
simulation metrics, and returns `bool`. Mock mode is fully deterministic;
`llm_judge` defers an Anthropic call only when mode == "llm".

Field path syntax (used by length/regex/llm_judge config["field"]):
  - "content"            → artifact.content
  - "fields.hook"        → artifact.fields["hook"]
  - "fields"             → join all artifact.fields values as one string
  - omitted              → artifact.content (the safe default)
"""

from __future__ import annotations

import re

from truman.agents.base import CandidateArtifact
from truman.eval.schema import CheckKind, EvalQuestion

_OPS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _get_field(artifact: CandidateArtifact, path: str | None) -> str:
    """Resolve a dotted field path against the artifact; return joined string."""
    if not path or path == "content":
        return artifact.content or ""
    if path == "fields":
        return " ".join(str(v) for v in (artifact.fields or {}).values())
    if path.startswith("fields."):
        key = path.split(".", 1)[1]
        return str((artifact.fields or {}).get(key, ""))
    return str(getattr(artifact, path, "") or "")


# ─── individual checkers ─────────────────────────────────────────────────────


def _check_regex(eval_q: EvalQuestion, artifact: CandidateArtifact) -> bool:
    text = _get_field(artifact, eval_q.config.get("field")).lower()
    forbid = [str(s).lower() for s in eval_q.config.get("forbid", [])]
    require = [str(s).lower() for s in eval_q.config.get("require", [])]
    pattern = eval_q.config.get("pattern")
    if any(f in text for f in forbid):
        return False
    if require and not any(r in text for r in require):
        return False
    if pattern and not re.search(pattern, text, flags=re.IGNORECASE):
        return False
    return True


def _check_length(eval_q: EvalQuestion, artifact: CandidateArtifact) -> bool:
    text = _get_field(artifact, eval_q.config.get("field"))
    n = len(text)
    lo = int(eval_q.config.get("min", 0))
    hi = int(eval_q.config.get("max", 10_000_000))
    return lo <= n <= hi


def _check_range(eval_q: EvalQuestion, metrics: dict[str, float]) -> bool:
    metric = eval_q.config.get("metric")
    op = eval_q.config.get("op", ">=")
    value = float(eval_q.config.get("value", 0.0))
    if not metric or op not in _OPS:
        return False
    actual = float(metrics.get(metric, 0.0) or 0.0)
    return _OPS[op](actual, value)


def _check_code(eval_q: EvalQuestion, artifact: CandidateArtifact) -> bool:
    """Lightweight code-quality checks (no subprocess in v1).

    Supported config["check"]:
      - "no_todo"       — passes iff text has no TODO/FIXME/XXX markers
      - "no_debug"      — passes iff text has no debug prints (print(/console.log)
      - "valid_python"  — passes iff text compiles as Python (compile())
    """
    text = _get_field(artifact, eval_q.config.get("field"))
    kind = eval_q.config.get("check", "no_todo")
    if kind == "no_todo":
        return not re.search(r"\b(TODO|FIXME|XXX)\b", text)
    if kind == "no_debug":
        return not re.search(r"\bprint\s*\(|console\.log\s*\(", text)
    if kind == "valid_python":
        try:
            compile(text, "<eval>", "exec")
        except SyntaxError:
            return False
        return True
    return False


def _check_llm_judge_mock(eval_q: EvalQuestion, artifact: CandidateArtifact) -> bool:
    """Deterministic stand-in for `llm_judge` in mock mode.

    Heuristic: PASS iff the artifact field is at least minimally substantive
    AND shares at least one keyword with the prompt (case-insensitive). This
    keeps mock runs reproducible and discriminating — empty / off-topic
    artifacts fail, rich ones pass.
    """
    text = _get_field(artifact, eval_q.config.get("field")).lower()
    if len(text) < 10:
        return False
    # Pull "content words" out of the prompt (drop stop words + punctuation).
    stop = {
        "is", "the", "a", "an", "does", "of", "with", "or", "and", "in", "on",
        "to", "for", "it", "this", "that", "be", "by", "do", "are", "as", "at",
        "between", "any", "all", "less", "fewer", "than", "first", "second",
        "third", "include", "have", "has", "use", "used", "must", "should",
        "one", "two", "three", "specific", "specifically", "without",
    }
    words = re.findall(r"[a-zA-Z一-鿿]+", eval_q.prompt.lower())
    keywords = [w for w in words if len(w) > 3 and w not in stop]
    if not keywords:
        return len(text) >= 30
    overlap = sum(1 for k in keywords if k in text)
    # require at least 20% overlap with prompt content words
    return overlap >= max(1, len(keywords) // 5)


async def _check_llm_judge_real(
    eval_q: EvalQuestion, artifact: CandidateArtifact, model: str | None
) -> bool:
    """Single async Anthropic call: ask the binary question, parse JSON."""
    from truman.llm.runtime import _bare_model, extract_json, get_async_client

    field_text = _get_field(artifact, eval_q.config.get("field"))
    client = get_async_client()
    system = (
        "You answer a single yes/no question about a piece of content. "
        "Be strict, literal, and consistent. Output ONLY JSON of the form "
        '{"pass": true} or {"pass": false}.'
    )
    user = (
        f"QUESTION (answer yes/no): {eval_q.prompt}\n\n"
        f"CONTENT:\n{field_text}\n\n"
        'Reply with strict JSON: {"pass": true|false}'
    )
    try:
        resp = await client.messages.create(
            model=_bare_model(model),
            max_tokens=40,
            temperature=0.0,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        data = extract_json(text) or {}
        return bool(data.get("pass", False))
    except Exception:
        return _check_llm_judge_mock(eval_q, artifact)


async def _check_composed(
    eval_q: EvalQuestion,
    artifact: CandidateArtifact,
    metrics: dict[str, float],
    mode: str,
    model: str | None,
) -> bool:
    op = (eval_q.config.get("op") or "AND").upper()
    sub_specs = eval_q.config.get("evals") or []
    sub_qs: list[EvalQuestion] = []
    for spec in sub_specs:
        sub_qs.append(EvalQuestion(**spec) if isinstance(spec, dict) else spec)
    if not sub_qs:
        return False
    results = [await check_one(q, artifact, metrics, mode, model) for q in sub_qs]
    return all(results) if op == "AND" else any(results)


# ─── dispatcher ──────────────────────────────────────────────────────────────


async def check_one(
    eval_q: EvalQuestion,
    artifact: CandidateArtifact,
    metrics: dict[str, float] | None,
    mode: str = "mock",
    model: str | None = None,
) -> bool:
    """Apply one EvalQuestion and return a binary pass/fail.

    Catches all exceptions and returns False so one malformed eval never breaks
    the whole batch — this matches autoresearch's "immutable evaluator" spirit:
    the run continues, but a broken eval doesn't gain a free pass.
    """
    metrics = metrics or {}
    try:
        if eval_q.check_kind == CheckKind.REGEX:
            return _check_regex(eval_q, artifact)
        if eval_q.check_kind == CheckKind.LENGTH:
            return _check_length(eval_q, artifact)
        if eval_q.check_kind == CheckKind.RANGE:
            return _check_range(eval_q, metrics)
        if eval_q.check_kind == CheckKind.CODE:
            return _check_code(eval_q, artifact)
        if eval_q.check_kind == CheckKind.LLM_JUDGE:
            if mode == "llm":
                return await _check_llm_judge_real(eval_q, artifact, model)
            return _check_llm_judge_mock(eval_q, artifact)
        if eval_q.check_kind == CheckKind.COMPOSED:
            return await _check_composed(eval_q, artifact, metrics, mode, model)
    except Exception:
        return False
    return False
