"""Truman CLI: `truman run`, `truman validate`, and `truman recommend`."""

from __future__ import annotations

import argparse
import json
import sys

from truman.goal.loader import load_goal
from truman.orchestrator.loop import TrumanEngine


def _cmd_validate(args: argparse.Namespace) -> int:
    goal = load_goal(args.goal)
    print("Goal config is valid.\n")
    print(goal.model_dump_json(indent=2))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    goal = load_goal(args.goal)
    if args.max_iterations is not None:
        goal.max_iterations = args.max_iterations
    if args.persona_count is not None:
        goal.persona_count = args.persona_count
    if args.threshold is not None:
        goal.threshold = args.threshold
    if args.budget_tokens is not None:
        goal.budget_tokens = args.budget_tokens
    mode = "llm" if args.llm else "mock"
    engine = TrumanEngine(goal, mode=mode, model=args.model)
    result = engine.run_sync()

    print(f"\n=== Truman run ({mode} mode) — goal: {goal.goal!r} ===\n")
    print(result.ledger.to_tsv())
    print()
    v = result.final_verdict
    print(f"Final score: {v.score:.4f} (threshold {v.threshold:.2f}) "
          f"-> {'DELIVERED' if v.threshold_met else 'NOT MET'}")
    print(f"Per-criterion: {v.per_criterion}")
    print(f"\nDelivered artifact (iteration {result.final_artifact.iteration}):")
    print(f"  {result.final_artifact.content}")
    return 0 if result.delivered else 1


def _cmd_recommend(args: argparse.Namespace) -> int:
    """Print AI-recommended binary Evals + persona_count for a goal config.

    The user is expected to review / edit these before running. CLI flags
    `--persona-count` / `--threshold` (when later running) override the
    recommendation, per the PRD priority: CLI > yaml > recommender > default.
    """
    from truman.eval.recommender import build_recommender

    goal = load_goal(args.goal)
    mode = "llm" if args.llm else "mock"
    rec = build_recommender(mode, args.model).recommend(goal)

    payload = {
        "vertical": goal.vertical,
        "goal": goal.goal,
        "recommended_persona_count": rec.recommended_persona_count,
        "yaml_persona_count": goal.persona_count,
        "rationale": rec.rationale,
        "evals": [q.model_dump(mode="json") for q in rec.evals],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="truman", description="Goal-Driven Recursive AI System")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run the recursive loop on a goal config")
    p_run.add_argument("goal", help="Path to a goal YAML file")
    p_run.add_argument("--llm", action="store_true", help="Use real LLM providers (default: offline mock)")
    p_run.add_argument("--model", default=None, help="LiteLLM model id (default: anthropic Claude)")
    p_run.add_argument("--max-iterations", type=int, default=None, dest="max_iterations")
    p_run.add_argument("--persona-count", type=int, default=None, dest="persona_count")
    p_run.add_argument("--threshold", type=float, default=None, help="Override the success threshold")
    p_run.add_argument("--budget-tokens", type=int, default=None, dest="budget_tokens",
                       help="Stop the loop once cumulative LLM cost reaches this many tokens")
    p_run.set_defaults(func=_cmd_run)

    p_val = sub.add_parser("validate", help="Validate a goal config")
    p_val.add_argument("goal", help="Path to a goal YAML file")
    p_val.set_defaults(func=_cmd_validate)

    p_rec = sub.add_parser("recommend",
                           help="Print AI-recommended binary Evals + persona count for a goal")
    p_rec.add_argument("goal", help="Path to a goal YAML file")
    p_rec.add_argument("--llm", action="store_true",
                       help="Use the LLM recommender (default: deterministic mock)")
    p_rec.add_argument("--model", default=None, help="LiteLLM model id (LLM mode only)")
    p_rec.set_defaults(func=_cmd_recommend)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
