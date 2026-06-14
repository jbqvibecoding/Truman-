# Migration Guide — bringing this branch's modules to another project

> **Branch**: `claude/truman-goal-driven-ai-7qLIb`
> **Status**: 100/100 tests green · ruff clean · 8 commits since `608d327` (MVP slice)
> **Audience**: anyone (you, a future Claude session, a different team) who wants to
> port the M1–M8 modules from this branch to a different repo, project, or language.

This branch shipped the **PRD v2.0 platform**: 7 modules that turn Truman from
"a goal-driven recursive engine for headlines" into "a goal-driven recursive
engine for any AI deliverable, with binary evals + persona simulation +
evolution changelog + 8 verticals + real-data backflow + deploy adapters."

This document is the canonical recipe for moving any subset (or all) of it to
another project.

---

## 1 · What's in scope (full inventory)

### 1.1 New packages (6 new directories, ~47 files)

| Package | Path | Files | Role |
| --- | --- | --- | --- |
| **Eval Engine** | `src/truman/eval/` | 7 | EvalQuestion + 6 check_kinds (regex / length / range / code / llm_judge / composed) + EvalRunner + EvalRecommender + template library |
| **Persona Library** | `src/truman/personas/library/` | 4 (+ `personas/__init__.py`) | 8 cohorts × 52 segment archetypes + deterministic loader + CSV / JSON upload |
| **Changelog** | `src/truman/changelog/` | 5 | `field_diff` + `ChangelogView` + 4 renderers (md / summary / html / json) |
| **Verticals** | `src/truman/verticals/` | 9 new (1 `_content_base` + `software_eng` + 7 content specializations) | M5 + M6 application-domain expansion |
| **Feedback / Calibration** | `src/truman/feedback/` | 5 | TSV history + Pearson r + tuning suggestions + synthesizer |
| **Deploy Adapters** | `src/truman/deploy/` | 6 | `DeployAdapter` Protocol + `LocalFile` (works) + `MetaAds` / `GitHubPR` / `Notion` (dry-run) |

### 1.2 Existing files extended (10)
| File | Change |
| --- | --- |
| `src/truman/goal/schema.py` | + `evals: list[EvalQuestion]`, `budget_tokens`, `plateau_window` |
| `src/truman/judge/scorer.py` | Dual-path: binary if `goal.evals`, else v1 continuous |
| `src/truman/orchestrator/loop.py` | Inject `EvalRunner`; budget / plateau stop conditions; `artifact_history` |
| `src/truman/orchestrator/ledger.py` | `per_eval` / `cost_tokens` / `parent_iteration` + `to_tsv` extension |
| `src/truman/sim/result.py` | `per_eval` field |
| `src/truman/verticals/registry.py` | 10 vertical self-registrations |
| `src/truman/verticals/headline.py` & `ad_creative.py` | Cohort dispatcher hook |
| `src/truman/cli.py` | 5 new subcommands: `recommend` / `changelog` / `record-kpi` / `calibrate` / `deploy` |

### 1.3 Tests — 6 files / **100 cases all green**
`tests/test_eval_engine.py` · `test_persona_library.py` · `test_changelog.py` · `test_new_verticals.py` · `test_feedback_and_deploy.py` (plus `test_verticals.py` from earlier).

### 1.4 Examples — 9 new YAMLs
`examples/ad_creative_evals.yaml` · `software_eng_issue.yaml` · `viral_content_post.yaml` · `landing_page.yaml` · `cold_email.yaml` · `seo_article.yaml` · `sales_script.yaml` · `prd_doc.yaml` · `pdp_page.yaml`

### 1.5 Docs — 3 files
- `docs/PRD.md` — platform-level v2.0 PRD
- `docs/PRD-ad-creative-vertical.md` — vertical-level reference
- `docs/eval-guide.md` — Binary Eval golden rule + good/bad eval examples

### 1.6 Commit history (carry these hashes — they're the audit trail)

| Hash | Milestone |
| --- | --- |
| `f7feddb` | Pluggable vertical registry + AdCreative vertical |
| `398b9ae` | v1 AdCreative PRD doc |
| `3648a4c` | v2 Platform PRD + Eval Guide docs |
| `d0e9946` | **M1 + M2**: Eval Engine + persona-count recommender |
| `cf2d309` | **M3**: Persona Library |
| `13dc666` | **M4**: Evolution Changelog |
| `23bce30` | **M5 + M6**: 8 new verticals |
| `90aa6bd` | **M7 + M8**: Feedback + Deploy |

### 1.7 External dependencies — **no new PyPI packages added by this branch**
Everything builds on Truman's existing deps:
`worldseed[dm]` (which brings `litellm` + `instructor`) · `pydantic >=2.10` ·
`PyYAML >=6.0` · `anthropic` · dev: `pytest`, `pytest-asyncio`.

---

## 2 · Three migration strategies

### Strategy 1 — Same `Truman-` repo, different branch / worktree (zero friction)

```bash
cd <target-worktree>
git fetch origin claude/truman-goal-driven-ai-7qLIb

# A) full merge:
git merge origin/claude/truman-goal-driven-ai-7qLIb

# B) or just the M3-M8 commits:
git cherry-pick cf2d309^..90aa6bd
```

**Pros**: one command, deps + docs + tests come with it.
**Cons**: resolve any conflicts manually if the target branch has diverged.

### Strategy 2 — A different Python project (recommended: install Truman as an editable library)

#### 2a — Install Truman as a library (easiest to upgrade later)

```bash
# In the target project:
pip install -e /path/to/Truman-
# Or in pyproject.toml (uv):
# [tool.uv.sources]
# truman = { path = "/path/to/Truman-", editable = true }
```

Target-project imports:

```python
from truman.eval import EvalQuestion, CheckKind
from truman.eval.runner import EvalRunner
from truman.eval.recommender import MockEvalRecommender, LLMEvalRecommender
from truman.personas.library import load_cohort, build_personas_from_cohort
from truman.changelog import ChangelogView, render_markdown, export
from truman.feedback import calibration_report, record_real_kpi
from truman.deploy import get_adapter, available_targets
```

Or via subprocess:
```python
subprocess.run(["python", "-m", "truman", "recommend", "goal.yaml"], check=True)
```

#### 2b — Copy modules into the target project (full control / fork)

1. Copy the 5 new packages: `src/truman/{eval, personas, changelog, feedback, deploy}/`
2. Copy `src/truman/verticals/{_content_base, software_eng, viral_content, landing_page, cold_email, seo_article, sales_script, prd_doc, pdp_page}.py`
3. Apply the 10 existing-file diffs as a patch:
   ```bash
   git format-patch f7feddb~..HEAD -- \
     src/truman/goal/ \
     src/truman/judge/ \
     src/truman/orchestrator/ \
     src/truman/sim/ \
     src/truman/cli.py \
     src/truman/verticals/registry.py \
     src/truman/verticals/headline.py \
     src/truman/verticals/ad_creative.py
   ```
4. Bring the 6 test files in `tests/`.
5. Global rename `truman.` → `<your-namespace>.`.

**Tradeoff**: full control vs. manual merging of future Truman updates.

### Strategy 3 — A non-Python project (TS / Rust / Go) via subprocess or HTTP

#### 3a — CLI subprocess (simplest, no extra service)

Every CLI subcommand prints JSON (when relevant). TypeScript example:

```typescript
const { stdout } = await execAsync(
  "python -m truman recommend examples/ad_creative_ctr.yaml"
);
const { evals, recommended_persona_count, rationale } = JSON.parse(stdout);
```

JSON-shaped CLI subcommands:
- `truman recommend <yaml>` → EvalRecommendation JSON
- `truman changelog <yaml> --format json` → ChangelogView JSON
- `truman calibrate --path <tsv>` → CalibrationReport JSON
- `truman deploy <yaml> --target <t>` → DeployResult JSON
- `truman run <yaml>` → ledger TSV + summary

#### 3b — HTTP wrapper (~80 lines of FastAPI, follow-up work)

Endpoints to expose:
```
POST /recommend     body: goal yaml          → EvalRecommendation JSON
POST /run           body: goal yaml          → RunResult JSON
POST /changelog     body: goal yaml + format → markdown / html / json
POST /calibrate     body: TSV history        → CalibrationReport JSON
POST /deploy        body: goal + target      → DeployResult JSON
```

---

## 3 · Recommended bootstrap (if target form is still undecided)

**Step 1 — Get it running standalone first** (no migration yet):

```bash
git clone <truman url> && cd Truman-
git checkout claude/truman-goal-driven-ai-7qLIb
uv venv && source .venv/bin/activate && uv pip install -e .
python -m pytest -q                       # expect: 100/100 passed
python -m truman recommend examples/ad_creative_ctr.yaml
python -m truman run examples/ad_creative_evals.yaml
python -m truman changelog examples/ad_creative_evals.yaml --format summary
```

**Step 2 — Pick a strategy** from §2 once the target's form is clear.

**Step 3 — Bring the knowledge assets too**:
- this `MIGRATION.md`
- `docs/PRD.md`, `docs/PRD-ad-creative-vertical.md`, `docs/eval-guide.md`
- all 9 `examples/*.yaml`
- the design plan at `/root/.claude/plans/goal-driven-autoresearch-mirofish-world-serialized-eagle.md` if you have access to that Claude session's plans directory

Code without docs is a maintenance liability.

---

## 4 · End-to-end migration verification checklist

After porting, run each of these on the target. All eight should pass for a
clean migration.

| # | Command | Expected |
| --- | --- | --- |
| 1 | `python -m pytest -q` | `100 passed` |
| 2 | `python -m truman validate examples/ad_creative_evals.yaml` | `Goal config is valid.` + JSON dump |
| 3 | `python -m truman recommend examples/ad_creative_ctr.yaml` | JSON with 3–6 evals + `recommended_persona_count` + `rationale` |
| 4 | `python -m truman run examples/ad_creative_evals.yaml` | exit 0; ledger TSV ends with a `delivered` row |
| 5 | `python -m truman changelog examples/ad_creative_evals.yaml --format summary` | `✅ Delivered in N iteration(s) — A → B` |
| 6 | `python -m truman record-kpi r1 --sim ctr=0.3 --real ctr=0.35 --path /tmp/t.tsv` | `Recorded: /tmp/t.tsv` |
| 7 | `python -m truman calibrate --path /tmp/t.tsv` | JSON with `per_metric_pearson_r` |
| 8 | `python -m truman deploy examples/ad_creative_evals.yaml --target local --live` | Files written to `out/<run_id>/{artifact,changelog}.{md,json}` |

If all eight pass, migration is complete.

---

## 5 · Module-by-module gotchas

### Eval Engine
- `EvalQuestion.config` shape is `check_kind`-dependent; consult `eval/checkers.py` for each kind's expected keys.
- `_check_llm_judge_real` defers Anthropic SDK import to runtime; mock mode has zero LLM imports at module load.
- The recommender's persona-count heuristic is `max(5, min(20, len(audience_segments) * 2))` — MiroFish-ported, in `eval/templates.py`.

### Persona Library
- `Persona.extra["cohort_segment"]` carries the segment label for cohort-derived personas — keep this if you write your own cohort dispatcher.
- CSV / JSON upload uses defaults from `_REQUIRED_OR_DEFAULTED` in `user_upload.py`; missing columns are filled in silently.

### Changelog
- Depends on `IterationRecord` having `per_eval`, `cost_tokens`, `parent_iteration` (added in M1).
- Depends on `RunResult` having `artifact_history` (parallel to `ledger.records`; loop ensures `len(artifact_history) == len(ledger.records)`).

### Verticals
- Content verticals (viral / landing / cold-email / SEO / sales / PRD / PDP) are tiny specializations of `_content_base.ContentVertical`; you mostly want to pull the base + the spec dicts.
- `SoftwareEngVertical` is independent (5-dim weighted evaluator); decider passes dim scores via action params so the DM doesn't need to parse `world_state`.

### Feedback / Calibration
- Recorder writes append-only TSV at `data/feedback.tsv` by default; override `path` in tests.
- Pearson r returns `None` for n<3 or zero variance — callers should guard against this.

### Deploy
- `LocalFileAdapter.is_live()` is always True (filesystem is always there).
- External adapters: `MetaAdsAdapter` / `GitHubPRAdapter` / `NotionAdapter` always dry-run in v1 even when credentials are present — going live is a deliberate follow-up.
- `DeployResult.extra["payload"]` carries the structured payload that would have been sent.

---

## 6 · License & credits

This branch's work is owned by the same author/license as Truman's mainline.
The design philosophy borrows from:
- **autoresearch** (immutable evaluator + append-only ledger discipline)
- **MiroFish** (`oasis_profile_generator.py` persona taxonomy + sample-size heuristic)
- **goal-driven** (recursive-control loop)
- **WorldSeed** (simulation engine backbone)

No new third-party PyPI packages were added — see `pyproject.toml`.

---

## 7 · Questions / fork-friendly extensions

PRs welcome. The architecture is deliberately seam-rich so each module can be
forked / replaced independently:
- New `check_kind`? Add to `eval/schema.py::CheckKind` + one async function in `eval/checkers.py`.
- New cohort? Add to `personas/library/cohorts.py::COHORTS`.
- New vertical? One file in `verticals/<name>.py` + one `register(...)` call in `verticals/registry.py`.
- New deploy target? One class implementing `DeployAdapter` + one entry in `deploy/__init__.py::_ADAPTERS`.
- New eval recommendation strategy? Subclass `MockEvalRecommender` or `LLMEvalRecommender`.

Good luck with the migration.
