"""Persona library + cohort templates (PRD v2.0 M3).

Lives alongside `truman.sim.personas` (the original Persona dataclass + the
build_personas / build_personas_llm generators). This subpackage provides the
richer per-vertical cohort archetypes and a CSV/JSON upload path so users
can plug in their own audience definitions.

  - `library.cohorts.COHORTS` — 6 built-in cohorts
  - `library.loader.load_cohort(name)` — fetch one
  - `library.loader.build_personas_from_cohort(cohort, count, seed)` — generator
  - `library.user_upload.load_personas_from_csv(path)` / `_from_json(path)` — uploads
"""
