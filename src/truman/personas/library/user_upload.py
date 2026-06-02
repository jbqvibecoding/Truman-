"""User-uploaded persona ingestion (CSV / JSON).

Users can plug in their own audience definitions instead of (or alongside)
the built-in cohorts. The required fields are minimal — we fill in safe
defaults for anything missing so a sparse CSV still produces valid Persona
instances.

CSV columns (header row required, order-free):
  name, bio, persona, mbti, country, profession, interested_topics,
  stance, sentiment_bias, influence_weight

`interested_topics` is a "|"-separated list. Missing columns get defaults.

JSON: an array of objects with the same keys (interested_topics is a list).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from truman.sim.personas import Persona


_REQUIRED_OR_DEFAULTED = {
    "name": "user_persona",
    "bio": "",
    "persona": "",
    "mbti": "ENFP",
    "country": "US",
    "profession": "user",
    "stance": "neutral",
}


def _as_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _parse_topics(v: Any) -> list[str]:
    if v is None:
        return ["general"]
    if isinstance(v, list):
        return [str(t).strip().lower() for t in v if str(t).strip()] or ["general"]
    s = str(v).strip()
    if not s:
        return ["general"]
    # Accept | , or ; as separators.
    for sep in ["|", ",", ";"]:
        if sep in s:
            return [t.strip().lower() for t in s.split(sep) if t.strip()] or ["general"]
    return [s.lower()]


def _row_to_persona(row: dict[str, Any], idx: int) -> Persona:
    name = str(row.get("name") or _REQUIRED_OR_DEFAULTED["name"])
    aid = f"upload_{idx + 1}_{name.replace(' ', '_')}"
    return Persona(
        agent_id=aid,
        name=name,
        bio=str(row.get("bio") or _REQUIRED_OR_DEFAULTED["bio"]),
        persona=str(row.get("persona") or _REQUIRED_OR_DEFAULTED["persona"]),
        mbti=str(row.get("mbti") or _REQUIRED_OR_DEFAULTED["mbti"]),
        country=str(row.get("country") or _REQUIRED_OR_DEFAULTED["country"]),
        profession=str(row.get("profession") or _REQUIRED_OR_DEFAULTED["profession"]),
        interested_topics=_parse_topics(row.get("interested_topics")),
        stance=str(row.get("stance") or _REQUIRED_OR_DEFAULTED["stance"]),
        sentiment_bias=_as_float(row.get("sentiment_bias"), 0.0),
        influence_weight=_as_float(row.get("influence_weight"), 1.0),
        extra={"source": "user_upload"},
    )


def load_personas_from_csv(path: str | Path) -> list[Persona]:
    p = Path(path)
    if not p.exists():
        msg = f"Persona CSV not found: {p}"
        raise FileNotFoundError(msg)
    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return []
    return [_row_to_persona(r, i) for i, r in enumerate(rows)]


def load_personas_from_json(path: str | Path) -> list[Persona]:
    p = Path(path)
    if not p.exists():
        msg = f"Persona JSON not found: {p}"
        raise FileNotFoundError(msg)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        msg = f"Persona JSON must be a list of objects, got {type(data).__name__}"
        raise ValueError(msg)
    return [_row_to_persona(d, i) for i, d in enumerate(data) if isinstance(d, dict)]
