"""SoftwareEngVertical — GitHub-issue-to-mergeable-PR (PRD §2 domain A).

Artifact: a code patch describing files to change + a summary. The evaluator
DM scores it on 5 weighted dimensions (correctness 35 / tests 25 / quality 20
/ security 10 / performance 10) so a goal `threshold ≥ 0.9` enforces the
"merge-ready" bar from the PRD §2.2 table.

Mock mode is fully deterministic and progressively-improving: each revision
adds one more "concern" (null check / test case / docstring / type hint /
sanitize input / cache hit) so the 5 dims rise monotonically. LLM mode uses
Claude to actually rewrite the patch.

For safety we **do not** spawn subprocess pytest in v1 — the evaluator is a
heuristic over patch contents (presence of test markers, absence of TODOs,
type hints, secret-pattern regex, etc.). The PRD M5.1 risk notes this; real
sandboxed pytest is M5.1.1.
"""

from __future__ import annotations


from worldseed.dm.providers.mock import MockDMProvider
from worldseed.models.config_schema import EffectConfig, SceneConfig
from worldseed.protocol.dm import DMContext, DMResponse

from truman.agents.base import CandidateArtifact
from truman.goal.schema import GoalConfig
from truman.judge.verdict import JudgeVerdict
from truman.research.base import ResearchBrief
from truman.sim.personas import Persona, build_personas, build_personas_llm

# Concerns the worker adds progressively each iteration; presence of each
# pushes one dimension up.
_CONCERNS = [
    "null check on input",
    "unit test for edge case",
    "type hint for return value",
    "input sanitization",
    "cache hit for repeated call",
    "docstring with example",
]
DIMS = ["correctness", "tests", "quality", "security", "performance"]


def _primary(goal: GoalConfig) -> str:
    return goal.scene.get("issue_title") or goal.scene.get("repo") or "fix"


# ─── Research ─────────────────────────────────────────────────────────────


class MockSWResearcher:
    def research(self, goal: GoalConfig) -> ResearchBrief:
        return ResearchBrief(
            summary=f"Offline analysis of issue: {goal.goal}",
            audience_insights=["Senior reviewers care about correctness + tests; security-folk catch secret leaks."],
            competitor_examples=["Common pattern: minimum-diff fix + unit test + clear summary."],
            recommended_angles=list(_CONCERNS),
            raw={"primary": _primary(goal)},
        )


class LLMSWResearcher:
    def __init__(self, model: str | None = None) -> None:
        self._model = model

    def research(self, goal: GoalConfig) -> ResearchBrief:
        from truman.llm.runtime import complete, extract_json

        prompt = (
            "Analyze this software-engineering issue and return JSON: "
            f'{{"summary": str, "audience_insights": [str], "competitor_examples": [str], '
            f'"recommended_angles": [3-6 concerns to address]}}\n\n'
            f"Issue: {goal.goal}\n"
            f"Repo context: {goal.scene}"
        )
        data = {}
        try:
            data = extract_json(complete(
                [{"role": "system", "content": "You are a code reviewer. JSON only."},
                 {"role": "user", "content": prompt}],
                model=self._model, temperature=0.3, max_tokens=600,
            )) or {}
        except Exception:
            pass
        angles = [str(a) for a in data.get("recommended_angles", [])] or list(_CONCERNS)
        return ResearchBrief(
            summary=str(data.get("summary", "")),
            audience_insights=list(data.get("audience_insights", [])),
            competitor_examples=list(data.get("competitor_examples", [])),
            recommended_angles=angles,
            raw={"response": data},
        )


# ─── Creative (patch writer) ───────────────────────────────────────────────


def _render_patch(summary: str, concerns: list[str]) -> str:
    lines = [f"# {summary}", "def fix(input_):"]
    for c in concerns:
        # Translate each concern into a representative line that the heuristic
        # evaluator can pattern-match. These tokens are intentional — they're
        # the signal the DM uses to assign dim scores.
        if "null" in c:
            lines.append("    if input_ is None: raise ValueError('input required')")
        elif "test" in c:
            lines.append("    # def test_fix(): assert fix('x') == 'x'  # unit test added")
        elif "type hint" in c:
            lines.append("    result: str = str(input_)")
        elif "sanitiz" in c:
            lines.append("    if any(ch in input_ for ch in '<>&'): input_ = input_.replace('<','')")
        elif "cache" in c:
            lines.append("    from functools import lru_cache  # cached path")
        elif "docstring" in c:
            lines.append('    """Fix the bug. Example: fix("x") -> "x"."""')
        else:
            lines.append(f"    # {c}")
    lines.append("    return result if 'result' in dir() else str(input_)")
    return "\n".join(lines)


class MockSWCreativeWorker:
    def create(self, goal: GoalConfig, brief: ResearchBrief, plan: str) -> CandidateArtifact:
        angles = brief.recommended_angles[:1] or _CONCERNS[:1]
        summary = f"baseline fix for: {goal.goal}"
        fields = {
            "patch": _render_patch(summary, angles),
            "files_changed": ["src/fix.py"],
            "summary": summary,
            "concerns": list(angles),
        }
        return CandidateArtifact(
            iteration=0, kind="code_patch",
            content=f"{summary}\n{fields['patch']}",
            rationale="Baseline patch addresses first concern.",
            fields=fields,
        )

    def revise(self, goal, brief, plan, previous: CandidateArtifact, verdict: JudgeVerdict) -> CandidateArtifact:
        n = min(previous.iteration + 2, len(brief.recommended_angles))
        angles = brief.recommended_angles[:n] or _CONCERNS[:n]
        summary = f"revised fix v{previous.iteration + 1} for: {goal.goal}"
        fields = {
            "patch": _render_patch(summary, angles),
            "files_changed": ["src/fix.py", "tests/test_fix.py"] if any("test" in a for a in angles) else ["src/fix.py"],
            "summary": summary,
            "concerns": list(angles),
        }
        return CandidateArtifact(
            iteration=previous.iteration + 1, kind="code_patch",
            content=f"{summary}\n{fields['patch']}",
            rationale=f"Revised addressing: {verdict.feedback}",
            parent_iteration=previous.iteration, fields=fields,
        )


class LLMSWCreativeWorker:
    def __init__(self, model: str | None = None) -> None:
        self._model = model

    def _gen(self, instruction: str, plan: str) -> dict:
        from truman.llm.runtime import complete, extract_json

        prompt = (
            f"{plan}\n\n{instruction}\n\n"
            "Return strict JSON: "
            '{"patch": str (Python code), "files_changed": [str], "summary": str (1 line)}'
        )
        data = extract_json(complete(
            [{"role": "system", "content": "You are a senior engineer writing minimum-diff patches. JSON only."},
             {"role": "user", "content": prompt}],
            model=self._model, temperature=0.4, max_tokens=1000,
        )) or {}
        return {
            "patch": str(data.get("patch", "")),
            "files_changed": list(data.get("files_changed", [])),
            "summary": str(data.get("summary", "")),
            "concerns": [],
        }

    def create(self, goal, brief, plan) -> CandidateArtifact:
        f = self._gen(f"Write a patch for: {goal.goal}", plan)
        return CandidateArtifact(0, "code_patch", f.get("summary", "") + "\n" + f.get("patch", ""),
                                 "LLM baseline patch.", fields=f)

    def revise(self, goal, brief, plan, previous, verdict):
        instr = (
            f"Improve this patch (current: {previous.fields.get('patch', '')[:600]}).\n"
            f"Reviewer feedback: {verdict.feedback}\nWeaknesses: {'; '.join(verdict.weaknesses)}"
        )
        f = self._gen(instr, plan)
        return CandidateArtifact(
            previous.iteration + 1, "code_patch",
            f.get("summary", "") + "\n" + f.get("patch", ""),
            f"Revised: {verdict.feedback}", parent_iteration=previous.iteration, fields=f,
        )


# ─── Decider (reviewer persona) ────────────────────────────────────────────


REVIEW_CUTOFF = 0.2


def _patch_appeal(persona: Persona, patch: str) -> float:
    """How likely this reviewer is to engage given their profile."""
    has_test = "def test_" in patch or "unit test added" in patch
    has_type = "type hint" in patch.lower() or ": str" in patch
    bias = (persona.sentiment_bias + 1.0) / 2.0
    role_topics = [t.lower() for t in persona.interested_topics]
    quality_signal = 0.0
    if has_test and ("test" in t for t in role_topics):
        quality_signal += 0.3
    if has_type and any("quality" in t or "best" in t or "architecture" in t for t in role_topics):
        quality_signal += 0.2
    if any("security" in t for t in role_topics) and "sanitiz" in patch.lower():
        quality_signal += 0.3
    return min(1.0, 0.3 * bias + 0.4 + quality_signal)


class MockSWDecider:
    def decide(self, persona: Persona, artifact: CandidateArtifact) -> dict:
        patch = (artifact.fields or {}).get("patch", "") if artifact.fields else artifact.content
        concerns = (artifact.fields or {}).get("concerns", []) if artifact.fields else []
        dims = _dim_scores(patch, concerns)
        appeal = _patch_appeal(persona, patch)
        if appeal < REVIEW_CUTOFF:
            return {"action": "ignore", "params": {}, "intensity": 0.0, "engaged": False}
        # Pass the 5-dim score in action params so the DM doesn't need to
        # re-read world_state (which WorldSeed doesn't expose as a flat dict).
        params = {"score": round(appeal, 4), "reaction": "reviewed patch"}
        for d in DIMS:
            params[f"dim_{d}"] = round(dims[d], 4)
        return {
            "action": "review",
            "params": params,
            "intensity": round(appeal, 4),
            "engaged": True,
        }


class LLMSWDecider:
    """Persona plays a code reviewer; the DM Evaluator turns the qualitative
    review into the 5 dimensional scores."""

    def __init__(self, model: str | None = None) -> None:
        self._model = model
        self._fallback = MockSWDecider()

    def decide(self, persona: Persona, artifact: CandidateArtifact) -> dict:
        from truman.llm.runtime import complete, extract_json

        patch = artifact.fields.get("patch", "") if artifact.fields else artifact.content
        prompt = (
            f"You are: {persona.persona}\n"
            f"Review this patch and answer JSON: {{review: <one line>, accept: bool}}\n\n"
            f"Patch:\n{patch[:1200]}"
        )
        try:
            data = extract_json(complete(
                [{"role": "system", "content": "You are a code reviewer. JSON only."},
                 {"role": "user", "content": prompt}],
                model=self._model, temperature=0.5, max_tokens=200,
            )) or {}
            if data.get("accept", False):
                return {"action": "review",
                        "params": {"reaction": str(data.get("review", ""))[:120], "score": None},
                        "intensity": None, "engaged": True}
        except Exception:
            return self._fallback.decide(persona, artifact)
        return {"action": "ignore", "params": {}, "intensity": 0.0, "engaged": False}


# ─── Evaluator DM (5-dimension scoring) ────────────────────────────────────


def _dim_scores(patch: str, concerns: list[str]) -> dict[str, float]:
    """Heuristic 5-dim score from patch contents — strictly improves with the
    progressive concerns added each revision."""
    patch_lower = patch.lower()
    n_concerns = len(concerns)
    has_test = "def test_" in patch or "unit test added" in patch_lower or "tests/test_" in patch
    has_type = ": str" in patch or "type hint" in patch_lower
    has_sanitize = "sanitiz" in patch_lower or "replace(" in patch_lower
    has_cache = "lru_cache" in patch_lower or "cache" in patch_lower
    has_doc = '"""' in patch or "example:" in patch_lower
    has_null = "valueerror" in patch_lower or "is none" in patch_lower
    no_todo = "TODO" not in patch and "FIXME" not in patch
    # Each dim is the sum of relevant signals, clamped to [0,1].
    return {
        "correctness": round(min(1.0, 0.4 + (0.2 if has_null else 0) + (0.1 * min(n_concerns, 4))), 4),
        "tests": round(min(1.0, 0.2 + (0.6 if has_test else 0.0) + (0.05 * n_concerns)), 4),
        "quality": round(min(1.0, 0.3 + (0.25 if has_type else 0.0) + (0.2 if has_doc else 0.0) + (0.1 if no_todo else 0.0)), 4),
        "security": round(min(1.0, 0.3 + (0.6 if has_sanitize else 0.0) + (0.1 if no_todo else 0.0)), 4),
        "performance": round(min(1.0, 0.3 + (0.5 if has_cache else 0.0) + (0.05 * n_concerns)), 4),
    }


class MockSWEvaluatorDM(MockDMProvider):
    async def judge(self, context: DMContext) -> DMResponse:
        # The decider passes the 5 dim scores as action params (see
        # MockSWDecider). The DM aggregates them by incrementing per-dim
        # counters on the artifact entity; metrics_fn divides by the number
        # of engaged reviewers to recover the per-reviewer mean.
        p = context.action.params or {}
        dims = {d: float(p.get(f"dim_{d}", 0.0) or 0.0) for d in DIMS}
        weighted_total = sum({
            "correctness": 0.35, "tests": 0.25, "quality": 0.20,
            "security": 0.10, "performance": 0.10,
        }[d] * dims[d] for d in DIMS)

        effects = [
            EffectConfig(operator="increment", target=f"artifact.{d}", by=round(dims[d], 4))
            for d in DIMS
        ]
        effects.append(EffectConfig(
            operator="emit_event", type="review",
            detail=f"{context.action.agent_id}: weighted={weighted_total:.3f} dims={dims}",
            scope="global", ttl=2,
        ))
        return DMResponse(narrative=f"{context.action.agent_id} reviewed; weighted={weighted_total:.3f}.", effects=effects)


class LLMSWEvaluatorDM:
    def __init__(self, model: str | None = None) -> None:
        self._model = model
        self._mock = MockSWEvaluatorDM()

    async def judge(self, context: DMContext) -> DMResponse:
        # In v1 we fall back to the deterministic dim scorer for safety.
        # A real LLM judge would call out here.
        return await self._mock.judge(context)


# ─── Scene + metrics ───────────────────────────────────────────────────────


def build_sw_scene(goal: GoalConfig, artifact: CandidateArtifact) -> SceneConfig:
    f = artifact.fields or {}
    concerns_list = ", ".join(f.get("concerns", []) or [])
    return SceneConfig.model_validate({
        "scene": {
            "id": "truman_sw_review",
            "description": f"Code review of a patch for: {goal.goal}",
            "dm_knowledge": "Score the patch on correctness/tests/quality/security/performance; one number each.",
            "max_ticks": None, "max_dm_calls": None,
        },
        "narrator": False,
        "entities": [
            {"id": "feed", "type": "space"},
            {
                "id": "artifact", "type": "code_patch",
                "summary": str(f.get("summary", "")),
                "patch": str(f.get("patch", ""))[:4000],  # length cap for state
                "concerns_list": concerns_list,
                # 5-dim counters (accumulate per reviewer)
                "correctness": 0.0, "tests": 0.0, "quality": 0.0, "security": 0.0, "performance": 0.0,
                "constraints": {d: {"min": 0} for d in DIMS},
            },
        ],
        "actions": {
            "review": {
                "description": "Review the patch and emit a per-dim score.",
                "params": [
                    {"name": "score", "type": "number", "required": False},
                    {"name": "reaction", "type": "free_text", "required": False},
                    *[{"name": f"dim_{d}", "type": "number", "required": False} for d in DIMS],
                ],
                "dm": {"hint": "Aggregate the 5 dim scores into per-dim counters.",
                       "allowed_ops": ["increment", "emit_event"], "max_effects": 6},
            },
            "ignore": {"description": "Skip this patch (low signal).", "params": []},
        },
        "perception": {"visibility": []},
    })


def sw_metrics(personas, per_persona, artifact_state, events) -> dict[str, float]:
    """Average per-reviewer 5-dim score → composite (matches PRD's 5-dim grader)."""
    n = max(1, sum(1 for p in personas if per_persona.get(p.agent_id, {}).get("engaged")))
    dims = {d: round(float(artifact_state.get(d, 0.0) or 0.0) / n, 4) for d in DIMS}
    weights = {"correctness": 0.35, "tests": 0.25, "quality": 0.20, "security": 0.10, "performance": 0.10}
    composite = round(sum(weights[d] * dims[d] for d in DIMS), 4)
    return {**dims, "merge_score": composite}


# ─── Vertical wiring ───────────────────────────────────────────────────────


class SoftwareEngVertical:
    name = "software_eng"

    def make_research(self, mode, model):
        return LLMSWResearcher(model) if mode == "llm" else MockSWResearcher()

    def make_creative(self, mode, model):
        return LLMSWCreativeWorker(model) if mode == "llm" else MockSWCreativeWorker()

    def make_personas(self, goal: GoalConfig, mode: str, model: str | None) -> list[Persona]:
        from truman.personas.library import build_personas_for_scene
        # Default cohort for this vertical is developer_personas; user can override
        # via scene.cohort or persona upload.
        scene = dict(goal.scene or {})
        scene.setdefault("cohort", "developer_personas")
        cohort_personas = build_personas_for_scene(scene, goal.persona_count, goal.seed)
        if cohort_personas:
            return cohort_personas
        if mode == "llm":
            return build_personas_llm(goal, goal.persona_count, model)
        return build_personas(_primary(goal), goal.persona_count, goal.seed)

    def make_decider(self, mode, model):
        return LLMSWDecider(model) if mode == "llm" else MockSWDecider()

    def make_dm(self, mode, model):
        return LLMSWEvaluatorDM(model) if mode == "llm" else MockSWEvaluatorDM()

    def build_scene(self, goal: GoalConfig, artifact: CandidateArtifact) -> SceneConfig:
        return build_sw_scene(goal, artifact)

    def compute_metrics(self, personas, per_persona, artifact_state, events):
        return sw_metrics(personas, per_persona, artifact_state, events)
