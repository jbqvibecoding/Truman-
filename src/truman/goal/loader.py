"""Load a GoalConfig from a YAML file."""

from __future__ import annotations

from pathlib import Path

import yaml

from truman.goal.schema import GoalConfig


def load_goal(path: str | Path) -> GoalConfig:
    """Parse + validate a goal YAML file into a GoalConfig."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return GoalConfig.model_validate(raw)
