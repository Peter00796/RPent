"""The tool-description template: structured fields, deterministic rendering.

Single source of truth for the common tools' model-facing descriptions, and the
shared template/renderer for every other tool package
(:mod:`robots.libero.tools.tool_docs` holds the LIBERO entries). Both tool
substrates consume the rendered string — the legacy Anthropic dicts in
:mod:`rpent.tools.common` (``TOOLS_SPEC``) and the native LangChain tools in
:mod:`rpent.tools.langchain_common` — so the two surfaces cannot drift.

Template (all fields optional except ``what``):

    what           one sentence, verb-first: what the tool does
    need           PRECONDITIONS only — what must already be true or have
                   happened before the call. Never restate arguments; argument
                   descriptions live in the input schema and nowhere else.
    returns        what comes back and how to read it — field semantics,
                   units, and which returned fields to trust when.
    when           local selection guidance — when to pick this tool over a
                   sibling. Never a workflow position ("after the READY
                   CHECK"): procedure ordering is owned by the system prompt.
    how            usage semantics for THIS tool's call forms. No multi-step
                   procedures spanning other tools — that is how recipes creep
                   back into tool descriptions.
    failure_modes  what goes wrong and how it surfaces (structured error,
                   truncation marker, silent overwrite). Quantitative caveats
                   here must have measurement backing.

Hard constraints, enforced by ``tests/harness/test_tool_docs.py``:

- no filesystem paths outside the run sandbox (no ``resources/``,
  ``results_*``, guide or calibration paths — advertising a prior is a leak);
- no per-cell constants;
- a capability that varies with a runtime flag gets a separate docs entry per
  variant (see ``read_image`` / ``read_image_text_only``), never a static
  superset description.

This module is stdlib-only on purpose: the legacy substrate must stay
importable without any agent framework installed.
"""
from __future__ import annotations

_ALLOWED_KEYS = ("what", "need", "returns", "when", "how", "failure_modes")

_LABELS = {
    "need": "Need",
    "returns": "Returns",
    "when": "When to use",
    "how": "How to use",
    "failure_modes": "Failure modes",
}

#: ``read_image_text_only`` exists because under ``--no-images`` the tool
#: cannot do what the normal description promises, so it advertises the truth
#: instead. Keeping the original wording would spend the model's turns
#: discovering that a described capability does not exist — worse, in a
#: single-attempt episode, than telling it up front. The tool is kept rather
#: than dropped because the system prompt still instructs image inspection, so
#: a call is likely and the result should redirect rather than fail as an
#: unknown tool.
COMMON_TOOL_DOCS: dict[str, dict[str, object]] = {
    "read_text_file": {
        "what": "Read a UTF-8 text file.",
        "when": (
            "re-read files under the run's working directory — JSON artifacts "
            "or notes you saved earlier."
        ),
        "failure_modes": [
            'returns {"error": ...} if the path is missing or is a directory',
            (
                "content beyond max_chars is cut with a trailing "
                "[TRUNCATED ...] marker"
            ),
            (
                "a path outside this run's sandbox is refused with "
                '{"error": ..., "allowed_roots": [...]}'
            ),
        ],
    },
    "write_text_file": {
        "what": "Write a UTF-8 text file (creates parent directories).",
        "when": (
            "save the working recipe JSONL as you go, and the final audit "
            "JSON before calling finish."
        ),
        "failure_modes": [
            (
                "silently overwrites an existing file — read it first if "
                "unsure what is there"
            ),
            (
                "a path outside this run's sandbox, or a harness-owned run "
                "artifact (states.json, tool_calls.jsonl, the image/world "
                "dumps), is refused with a structured error"
            ),
        ],
    },
    "list_dir": {
        "what": "List the files in a directory (non-recursive).",
        "when": (
            "inspect the run's working directory; omit path to list exactly "
            "that."
        ),
        "failure_modes": [
            'returns {"error": ...} if the directory does not exist',
            (
                "a directory outside this run's sandbox is refused with "
                '{"error": ..., "allowed_roots": [...]}'
            ),
        ],
    },
    "finish": {
        "what": (
            "Declare the run finished — success, failure, or stuck — and halt "
            "the agent loop."
        ),
        "need": (
            "all artifacts (recipe, audit) already written; nothing can be "
            "saved after finish."
        ),
    },
    "read_image": {
        "what": "Read a local image path returned by an RPent tool as visual input.",
        "need": "an image path produced by an earlier tool call in this run.",
        "failure_modes": [
            "returns a plain-text error if the path does not exist",
            "a path outside this run's sandbox is refused with a structured error",
        ],
    },
    "read_image_text_only": {
        "what": (
            "DISABLED in this run: image input is off (text-only model), so "
            "this tool cannot return visual content and looking at a PNG is "
            "not available to you."
        ),
        "when": (
            "never — localize objects with `segment` (SAM3 text prompt -> "
            "world_xyz) and `back_project`, and read scalar state from "
            "`view_driver_state`."
        ),
    },
}


def render_doc(doc: dict) -> str:
    """Render one structured docs entry into the model-facing description.

    ``what`` leads unlabeled; the optional fields follow in template order,
    one block each, lists joined with ``"; "``. Multi-line values embed as-is.
    """
    lines = [str(doc["what"])]
    for key in ("need", "returns", "when", "how", "failure_modes"):
        value = doc.get(key)
        if not value:
            continue
        if isinstance(value, (list, tuple)):
            value = "; ".join(str(v) for v in value)
        lines.append(f"{_LABELS[key]}: {value}")
    return "\n".join(lines)


def render_description(name: str) -> str:
    """Render a COMMON tool's docs entry (LIBERO entries render in their own
    package via :func:`render_doc`)."""
    return render_doc(COMMON_TOOL_DOCS[name])


def iter_rendered() -> list[tuple[str, str]]:
    """All common (name, rendered description) pairs — the lintable surface."""
    return [(name, render_description(name)) for name in COMMON_TOOL_DOCS]


def validate_docs(docs: dict, where: str) -> None:
    """Fail loudly on a malformed entry; call at import in each docs module."""
    for name, doc in docs.items():
        unknown = set(doc) - set(_ALLOWED_KEYS)
        if unknown:
            raise ValueError(f"{where}[{name!r}]: unknown keys {sorted(unknown)}")
        if not str(doc.get("what", "")).strip():
            raise ValueError(f"{where}[{name!r}]: 'what' is required")


validate_docs(COMMON_TOOL_DOCS, "COMMON_TOOL_DOCS")
