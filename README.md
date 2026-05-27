# Truman — A Goal-Driven Recursive AI System

> AI that doesn't just *complete a task* — it **simulates the world's reaction**,
> **judges** the result against quantitative criteria, and **recursively
> re-iterates** until the simulated outcome beats a threshold.

```
Goal → AutoResearch → Planner → Workers → Simulation → Judge → Feedback Loop
  → Worker Re-iteration → (score ≥ threshold) → Deliver
```

Truman organically combines four projects:

| Layer | Source project | Role |
|---|---|---|
| **Goal** | `goal-driven` | Master/criteria control: loop until success criteria are met. |
| **AutoResearch + Recursive Loop** | `autoresearch` | Fixed immutable evaluator, candidate→measure→keep/reject, append-only ledger. |
| **Simulation + Judge** | `WorldSeed` | Tick-based world engine (`WorldEngine`) + LLM "DM" judge (`DMProvider`). |
| **Simulation (audience) + scoring** | `MiroFish` | Persona-at-scale generation + reaction/report → numeric score. |

**WorldSeed is the engine backbone.** Truman builds a `SceneConfig` in memory from
LLM/seed-generated personas, registers them as WorldSeed agents, drives ticks with
`step_async()` (so the DM judges each reaction and mutates engagement state), then a
scorer maps the simulated reactions onto the goal's criteria. Below threshold → the
judge's feedback is fed back to the worker, which revises → repeat.

## Architecture (layers → modules)

```
src/truman/
  goal/         Goal Layer — Goal + SuccessCriteria + threshold
  research/     AutoResearch Layer — market/audience insight (mock + LLM)
  agents/       Planner + Workers — produce/revise candidate artifacts
  sim/          Simulation Layer — wraps WorldSeed WorldEngine; personas
  judge/        Judge Layer — WorldSeed DM + composite scorer
  orchestrator/ Recursive Feedback Loop — master/criteria loop + ledger
  llm/          LiteLLM runtime (default Anthropic Claude)
```

## Install (dev)

```bash
uv venv --python 3.11 .venv && . .venv/bin/activate
uv pip install -e ".[dev]"                     # Truman + its deps (pulls worldseed[dm])
uv pip install -e "/home/user/WorldSeed[dm]"   # re-pin worldseed EDITABLE (must be last)
```

> Install `worldseed` editable **last**. WorldSeed's `dm/prompt.py` reads a
> repo-relative `shared/languages.json` at import time, which is only present in
> an editable (source-tree) install — required for `--llm` mode. Offline mock
> mode works either way.

## Run

Offline (deterministic, no network — the runnable MVP slice):

```bash
python -m truman run examples/headline_engagement.yaml
```

With real LLMs (LiteLLM, default Anthropic Claude; needs API keys):

```bash
python -m truman run examples/headline_engagement.yaml --llm --model anthropic/claude-sonnet-4-5
```

Validate a goal config:

```bash
python -m truman validate examples/headline_engagement.yaml
```

## Test

```bash
pytest -q        # fully offline; uses WorldSeed's MockDMProvider
```

The end-to-end gate (`tests/test_loop_mock.py`) asserts the loop **re-iterates**, the
score **strictly improves** across iterations, it **stops on the threshold** (not budget),
and the run is **deterministic**.

## Defining a goal

A goal is a *result*, not a task:

```yaml
goal: "Write a headline that maximizes audience engagement for our budget travel app."
artifact_kind: text_headline
threshold: 0.65          # composite score to beat
max_iterations: 6
persona_count: 6
seed: 42
criteria:
  - { name: engagement, metric: avg_engagement, weight: 0.7 }
  - { name: reach,      metric: positive_ratio, weight: 0.3 }
scene:
  topic: "budget travel"
```

New verticals (ad creative, GameFi economy, startup/VC sim, viral content) are pluggable:
supply a different goal + criteria (and, later, a different persona/scene spec).
