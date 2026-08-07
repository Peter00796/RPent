"""Opt-in sync of the legacy priors payload into the staging dir.

History: this used to pull ``RLinf/RPent-memory`` over ``resources/<env>/``
on EVERY run, with ``local_dir`` set so it overwrote what was there — which
made the sync the delivery mechanism for exactly the per-cell priors the
prompt cleansing removed, and clobbered any locally curated state (see
docs/harness/04-open-issues.md, issue 1).

Now: nothing syncs unless the active sandbox profile references
``{staging_root}`` (only ``configs/sandbox/full.yaml`` does), the target is
``.staging/<env>/`` rather than ``resources/``, and an existing staging copy
is reused rather than re-downloaded. ``HF_HUB_OFFLINE=1`` still forces a dry
run. The decoupled memory library under ``memory/`` is never touched by any
sync.
"""
from __future__ import annotations

import os

from rpent.utils.config import get_staging_dir
from rpent.utils.logging import get_logger

RESOURCES_HF_REPO = os.environ.get("RPENT_RESOURCES_HF_REPO", "RLinf/RPent-memory")

logger = get_logger("resources")


def ensure_staged_priors(env_name: str, *, enabled: bool) -> None:
    """Sync the legacy priors payload into staging, only when asked.

    ``enabled`` comes from the sandbox policy (``uses_staging``): the sync
    happens iff the run's profile actually exposes the staging root. A
    failed or partial sync raises instead of warning — a comparison arm
    running on a silently partial payload measures nothing.
    """
    staging = get_staging_dir(env_name)
    if not enabled:
        return
    if os.environ.get("HF_HUB_OFFLINE") == "1":
        logger.info("HF_HUB_OFFLINE=1: using staged priors at %s as-is", staging)
        return
    if staging.exists() and any(staging.iterdir()):
        logger.info("staged priors already present at %s; not re-syncing", staging)
        return

    from huggingface_hub import snapshot_download

    logger.info("syncing '%s' from '%s' into %s", env_name, RESOURCES_HF_REPO, staging)
    snapshot_download(
        repo_id=RESOURCES_HF_REPO,
        repo_type="dataset",
        local_dir=str(staging.parent),
        allow_patterns=[f"{env_name}/**"],
    )
