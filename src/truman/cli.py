"""Truman CLI: `truman run <goal.yaml>` and `truman validate <goal.yaml>`."""

from __future__ import annotations

import argparse
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="truman", description="Goal-Driven Recursive AI System")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run the recursive loop on a goal config")
    p_run.add_argument("goal", help="Path to a goal YAML file")
    p_run.add_argument("--llm", action="store_true", help="Use real LLM providers (default: offline mock)")
    p_run.add_argument("--model", default=None, help="LiteLLM model id (default: anthropic Claude)")
    p_run.add_argument("--max-iterations", type=int, default=None, dest="max_iterations")
    p_run.set_defaults(func=_cmd_run)

    p_val = sub.add_parser("validate", help="Validate a goal config")
    p_val.add_argument("goal", help="Path to a goal YAML file")
    p_val.set_defaults(func=_cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
