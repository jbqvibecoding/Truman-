"""Vertical registry — name -> Vertical instance.

Verticals self-register at import time. Adding a new vertical is a single new
module plus one `register(...)` call — no changes to the orchestrator loop.
"""

from __future__ import annotations

from truman.verticals.base import Vertical

_REGISTRY: dict[str, Vertical] = {}


def register(vertical: Vertical) -> None:
    _REGISTRY[vertical.name] = vertical


def get_vertical(name: str) -> Vertical:
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY)) or "(none)"
        msg = f"Unknown vertical {name!r}. Available: {available}"
        raise KeyError(msg)
    return _REGISTRY[name]


def available() -> list[str]:
    return sorted(_REGISTRY)


def _bootstrap() -> None:
    from truman.verticals.ad_creative import AdCreativeVertical
    from truman.verticals.headline import HeadlineVertical

    register(HeadlineVertical())
    register(AdCreativeVertical())


_bootstrap()
