"""Path resolution and environment-variable configuration."""
from __future__ import annotations

import os
from pathlib import Path


# ============================================================================
# Repository / package roots
# ============================================================================

def get_repo_root() -> Path:
    """Return the RPent repository root directory.

    Resolution: ``RPENT_REPO_ROOT`` env var, then the parent of
    the ``rpent/`` package directory.
    """
    env = os.environ.get("RPENT_REPO_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    # config.py lives at <repo>/rpent/utils/config.py
    return Path(__file__).resolve().parents[2]


# ============================================================================
# Paths derived from the repo root  (callable so tests can override)
# ============================================================================

def get_resources_dir(env_name: str) -> Path:
    """Return the per-env resources directory (memory + reference corpora)."""
    return get_repo_root() / "resources" / env_name


def get_memory_dir(env_name: str) -> Path:
    """Return the persistent, cross-run memory directory for an env.

    Legacy location under ``resources/`` — still handed to the external
    CLI planners (claude_code/codex). The sandboxed planners use the
    decoupled library below.
    """
    return get_resources_dir(env_name) / "memory"


# ============================================================================
# The decoupled memory library (see configs/sandbox/*.yaml)
# ============================================================================

def get_memory_common_dir() -> Path:
    """Cross-environment harness memory: transferable operating wisdom."""
    return get_repo_root() / "memory" / "common"


def get_memory_env_dir(env_name: str) -> Path:
    """Per-environment memory library."""
    return get_repo_root() / "memory" / env_name


def get_staging_dir(env_name: str) -> Path:
    """Where the legacy priors payload syncs to (``--sandbox full`` only).

    Deliberately NOT ``resources/`` — the sync must never overwrite curated
    local state again.
    """
    return get_repo_root() / ".staging" / env_name


def get_pi05_checkpoint_path() -> str:
    return os.environ.get("PI05_CHECKPOINT_PATH", "")


def get_libero_type() -> str:
    return os.environ.get("LIBERO_TYPE", "pro")


def get_rlinf_repo_path() -> Path | None:
    """Return the configured RLinf checkout path, or *None*."""
    env = os.environ.get("RPENT_RLINF_ROOT") or os.environ.get("RLINF_REPO_PATH")
    if env:
        return Path(env).expanduser().resolve()
    return None
