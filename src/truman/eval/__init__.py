"""Eval Engine — binary yes/no evaluations on candidate artifacts.

The Eval Engine implements PRD v2.0's first differentiator: every Eval is a
binary (yes/no) question scored stably and aggregated by weight. See
`docs/eval-guide.md` for the golden rule + good/bad eval examples.

Public surface (import these here):
- `EvalQuestion` / `CheckKind` / `EvalRecommendation` — the schema

For the heavier components import them directly from the submodule to avoid
pulling the agents package at goal-schema import time:
    from truman.eval.runner import EvalRunner
    from truman.eval.recommender import MockEvalRecommender, LLMEvalRecommender, build_recommender
    from truman.eval.templates import built_in_templates, recommended_persona_count
"""

from truman.eval.schema import CheckKind, EvalQuestion, EvalRecommendation

__all__ = ["CheckKind", "EvalQuestion", "EvalRecommendation"]
