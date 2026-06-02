"""Deployment integration adapters (PRD v2.0 M8, scaffolding).

This package provides the seam where Truman's delivered artifacts plug into
the systems that actually ship them: Meta Ads, GitHub PRs, Notion, or just
the local filesystem.

v1 ships:
- `LocalFileAdapter` — fully functional: writes the delivered artifact +
  changelog (Markdown + JSON) into `out/<run_id>/`
- `MetaAdsAdapter` / `GitHubPRAdapter` / `NotionAdapter` — dry-run by default
  (they print the payload they WOULD send). Going live requires
  the relevant environment credential AND explicit `--live` opt-in.

The contract is `DeployAdapter` (Protocol); registering a new target = one
new module + one entry in `_ADAPTERS`.
"""

from truman.deploy.base import DeployAdapter, DeployResult
from truman.deploy.github_pr import GitHubPRAdapter
from truman.deploy.local_file import LocalFileAdapter
from truman.deploy.meta_ads import MetaAdsAdapter
from truman.deploy.notion import NotionAdapter

_ADAPTERS: dict[str, type] = {
    "local": LocalFileAdapter,
    "meta_ads": MetaAdsAdapter,
    "github_pr": GitHubPRAdapter,
    "notion": NotionAdapter,
}


def available_targets() -> list[str]:
    return sorted(_ADAPTERS)


def get_adapter(target: str) -> DeployAdapter:
    if target not in _ADAPTERS:
        msg = f"Unknown deploy target {target!r}. Available: {', '.join(available_targets())}"
        raise ValueError(msg)
    return _ADAPTERS[target]()


__all__ = [
    "DeployAdapter", "DeployResult",
    "GitHubPRAdapter", "LocalFileAdapter", "MetaAdsAdapter", "NotionAdapter",
    "available_targets", "get_adapter",
]
