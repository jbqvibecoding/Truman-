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
    # Each new vertical is one import + one register() call.
    from truman.verticals.ad_creative import AdCreativeVertical
    from truman.verticals.cold_email import ColdEmailVertical
    from truman.verticals.headline import HeadlineVertical
    from truman.verticals.landing_page import LandingPageVertical
    from truman.verticals.pdp_page import PDPVertical
    from truman.verticals.prd_doc import PRDVertical
    from truman.verticals.sales_script import SalesScriptVertical
    from truman.verticals.seo_article import SEOVertical
    from truman.verticals.software_eng import SoftwareEngVertical
    from truman.verticals.viral_content import ViralContentVertical

    register(HeadlineVertical())
    register(AdCreativeVertical())
    register(SoftwareEngVertical())
    register(ViralContentVertical())
    register(LandingPageVertical())
    register(ColdEmailVertical())
    register(SEOVertical())
    register(SalesScriptVertical())
    register(PRDVertical())
    register(PDPVertical())


_bootstrap()
