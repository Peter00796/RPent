"""The run sandbox: which paths the agent's file tools may read and write.

The sandbox is ALWAYS ON. There is no off switch — permissiveness is a
declared profile (see ``configs/sandbox/unrestricted.yaml``), never the
absence of mechanism. Until :func:`set_sandbox` is called every check fails
closed, so forgetting to initialise it denies everything instead of leaking.

Design (see docs/harness/02-decisions.md):

- **Profiles are data, not an enum.** ``--sandbox <name>`` loads
  ``configs/sandbox/<name>.yaml``; ``--sandbox path/to/file.yaml`` loads a
  one-off profile. The code never special-cases a profile name. The three
  canonical arms (``none`` / ``memory`` / ``full``) are ordinary files that
  happen to carry the experiment's semantics.
- **Profile = shape, env = binding.** Profiles reference placeholders
  (``{output_dir}``, ``{memory_common}``, ``{memory_env}``,
  ``{staging_root}``, ``{repo_root}``) that :func:`default_bindings` resolves
  per run, so one ``memory.yaml`` serves every environment.
- **Config declares intent; code owns invariants.** ``write_denied`` (the
  harness-owned evidence files inside the output dir — ``states.json``,
  ``tool_calls.jsonl``, the world maps…) is NOT configurable: it is
  registered from ``ARTIFACT_LAYOUT`` via :func:`add_write_protection`. An
  agent that could rewrite its own evidence log would make every attribution
  claim worthless.
- **Checks run on ``Path.resolve()`` output** — symlinks are followed and the
  macOS case-insensitivity trap is neutralised — and denials return a
  structured error carrying ``allowed_roots`` so the model learns the
  boundary in one call instead of probing.

Known limit: the ``claude_code`` / ``codex`` planners run external CLI agents
with their own filesystem access; this sandbox governs the in-process tool
layer only.

The active policy is a module global, mirroring ``get_output_dir()``: one run
per process. The resolved policy is dumped into the run's ``sandbox.json`` so
the run is attributable to the exact boundary that was live.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path

from rpent.utils.config import (
    get_memory_common_dir,
    get_memory_env_dir,
    get_repo_root,
    get_staging_dir,
)

#: Directory holding the named profiles shipped with the repo.
PROFILE_DIR_RELATIVE = Path("configs") / "sandbox"

_ALLOWED_PROFILE_KEYS = {"name", "description", "read_roots", "write_roots"}


class SandboxDenied(Exception):
    """A file-tool access outside the active sandbox."""

    def __init__(self, message: str, allowed_roots: tuple[str, ...] = ()):
        super().__init__(message)
        self.allowed_roots = allowed_roots

    def as_error(self) -> dict:
        """The structured tool result for a denial (house style: tools return
        error dicts, they do not raise into the agent loop)."""
        out: dict = {"error": str(self)}
        if self.allowed_roots:
            out["allowed_roots"] = list(self.allowed_roots)
        return out


@dataclass(frozen=True)
class SandboxPolicy:
    """One run's resolved file-access boundary."""

    name: str
    source: str            # profile file the policy was loaded from
    source_sha256: str     # hash of that file's bytes
    description: str
    read_roots: tuple[Path, ...]
    write_roots: tuple[Path, ...]
    #: Harness-owned paths inside the write roots that stay read-only to the
    #: agent. Code-owned — never loaded from the profile file.
    write_denied: tuple[Path, ...] = ()
    #: True when the profile references {staging_root}; drives the opt-in
    #: resource sync.
    uses_staging: bool = False

    def check_read(self, p: Path) -> None:
        r = p.resolve()
        if not any(r == root or r.is_relative_to(root) for root in self.read_roots):
            raise SandboxDenied(
                f"read denied: {p} is outside the run sandbox "
                f"(profile '{self.name}')",
                allowed_roots=tuple(str(x) for x in self.read_roots),
            )

    def check_write(self, p: Path) -> None:
        r = p.resolve()
        if not any(r == root or r.is_relative_to(root) for root in self.write_roots):
            raise SandboxDenied(
                f"write denied: {p} is outside the run sandbox "
                f"(profile '{self.name}')",
                allowed_roots=tuple(str(x) for x in self.write_roots),
            )
        for d in self.write_denied:
            if r == d or r.is_relative_to(d):
                raise SandboxDenied(
                    f"write denied: {p} is a harness-owned run artifact and "
                    "is read-only to the agent",
                )

    def can_read(self, p: Path) -> bool:
        """Boolean form of :meth:`check_read`, for capability probes."""
        try:
            self.check_read(p)
        except SandboxDenied:
            return False
        return True

    def fingerprint(self) -> dict:
        """What goes into the run's sandbox.json: the exact live boundary."""
        return {
            "profile": self.name,
            "source": self.source,
            "source_sha256": self.source_sha256,
            "description": self.description,
            "read_roots": [str(p) for p in self.read_roots],
            "write_roots": [str(p) for p in self.write_roots],
            "write_denied": [str(p) for p in self.write_denied],
            "uses_staging": self.uses_staging,
        }


# ---------------------------------------------------------------------------
# Active policy (one run per process, like get_output_dir)
# ---------------------------------------------------------------------------

_POLICY: SandboxPolicy | None = None

#: Where init_run_sandbox dumped the fingerprint; add_write_protection re-dumps
#: there so the recorded boundary always matches the live one (the write_denied
#: list is registered by the toolkit AFTER the initial dump).
_FINGERPRINT_PATH: Path | None = None


def set_sandbox(policy: SandboxPolicy) -> None:
    global _POLICY
    _POLICY = policy


def clear_sandbox() -> None:
    global _POLICY, _FINGERPRINT_PATH
    _POLICY = None
    _FINGERPRINT_PATH = None


def active_policy() -> SandboxPolicy | None:
    return _POLICY


def add_write_protection(paths) -> None:
    """Register harness-owned artifacts as agent-read-only.

    Called by the env toolkit once the artifact layout is known. No-op when
    no policy is set (everything is already denied fail-closed).
    """
    global _POLICY
    if _POLICY is None:
        return
    merged = {*_POLICY.write_denied, *(Path(p).resolve() for p in paths)}
    _POLICY = replace(_POLICY, write_denied=tuple(sorted(merged)))
    # Keep the recorded fingerprint equal to the live boundary: a
    # sandbox.json with an empty write_denied while protection is active
    # would misdescribe the run (found on the first gen-0 sweep).
    if _FINGERPRINT_PATH is not None:
        _FINGERPRINT_PATH.write_text(json.dumps(_POLICY.fingerprint(), indent=2))


def memory_exposed(env_name: str) -> bool:
    """Does the active sandbox expose the memory library?

    This is what the prompt layer keys its variants on — a capability read
    off the live policy, never a profile name, so prompt and enforcement
    cannot disagree.
    """
    if _POLICY is None:
        return False
    return _POLICY.can_read(get_memory_common_dir()) or _POLICY.can_read(
        get_memory_env_dir(env_name)
    )


def check_read(p: Path) -> None:
    if _POLICY is None:
        raise SandboxDenied(
            "sandbox not initialised: no file access is available "
            "(main.py sets it from --sandbox; call set_sandbox() in scripts)",
        )
    _POLICY.check_read(p)


def check_write(p: Path) -> None:
    if _POLICY is None:
        raise SandboxDenied(
            "sandbox not initialised: no file access is available "
            "(main.py sets it from --sandbox; call set_sandbox() in scripts)",
        )
    _POLICY.check_write(p)


# ---------------------------------------------------------------------------
# Profile loading
# ---------------------------------------------------------------------------

def default_bindings(env_name: str, output_dir) -> dict[str, str]:
    """The placeholder → real-path map for this run.

    Profiles stay environment-agnostic; everything env- or run-specific
    enters here.
    """
    return {
        "output_dir": str(Path(output_dir).resolve()),
        "repo_root": str(get_repo_root()),
        "memory_common": str(get_memory_common_dir()),
        "memory_env": str(get_memory_env_dir(env_name)),
        "staging_root": str(get_staging_dir(env_name)),
    }


def init_run_sandbox(profile: str, env_name: str, output_dir) -> SandboxPolicy:
    """Load the profile, activate it, and dump the fingerprint into the run.

    ``{output_dir}/sandbox.json`` records the exact boundary that was live —
    profile name, source hash, and the resolved absolute roots — so every
    run is attributable to its input surface.
    """
    global _FINGERPRINT_PATH
    policy = load_profile(profile, default_bindings(env_name, output_dir))
    set_sandbox(policy)
    fp = Path(output_dir) / "sandbox.json"
    fp.write_text(json.dumps(policy.fingerprint(), indent=2))
    _FINGERPRINT_PATH = fp
    return policy


def _profile_path(name_or_path: str) -> Path:
    candidate = Path(name_or_path)
    if candidate.suffix in (".yaml", ".yml"):
        if not candidate.exists():
            raise FileNotFoundError(f"sandbox profile file not found: {candidate}")
        return candidate
    profile_dir = get_repo_root() / PROFILE_DIR_RELATIVE
    p = profile_dir / f"{name_or_path}.yaml"
    if not p.exists():
        available = sorted(x.stem for x in profile_dir.glob("*.yaml"))
        raise FileNotFoundError(
            f"unknown sandbox profile '{name_or_path}'; available: {available} "
            f"(or pass a path to a .yaml file)"
        )
    return p


def load_profile(name_or_path: str, bindings: dict[str, str]) -> SandboxPolicy:
    """Load a profile file, interpolate the bindings, resolve every root."""
    import yaml

    path = _profile_path(name_or_path)
    raw_bytes = path.read_bytes()
    data = yaml.safe_load(raw_bytes)
    if not isinstance(data, dict):
        raise ValueError(f"sandbox profile {path} is not a mapping")
    unknown = set(data) - _ALLOWED_PROFILE_KEYS
    if unknown:
        raise ValueError(f"sandbox profile {path}: unknown keys {sorted(unknown)}")
    for key in ("name", "read_roots", "write_roots"):
        if key not in data:
            raise ValueError(f"sandbox profile {path}: missing '{key}'")

    def interpolate(template: str) -> Path:
        try:
            return Path(template.format(**bindings)).resolve()
        except KeyError as exc:
            raise ValueError(
                f"sandbox profile {path}: unknown placeholder {exc} in "
                f"{template!r}; known: {sorted(bindings)}"
            ) from None

    raw_text = raw_bytes.decode("utf-8")
    return SandboxPolicy(
        name=str(data["name"]),
        source=str(path),
        source_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        description=str(data.get("description", "")),
        read_roots=tuple(interpolate(t) for t in data["read_roots"]),
        write_roots=tuple(interpolate(t) for t in data["write_roots"]),
        uses_staging="{staging_root}" in raw_text,
    )
