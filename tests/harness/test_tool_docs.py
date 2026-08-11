"""Lint the model-facing tool description surface.

Plain script, not pytest, like the other harness tests:

    PYTHONPATH=. python tests/harness/test_tool_docs.py

What it enforces (the mechanism half of the description template — the
template itself is documented in :mod:`rpent.tools.tool_docs`):

1. every docs entry is well-formed (allowed keys, ``what`` present);
2. no rendered description advertises a prior — no ``resources/`` paths,
   ``results_*`` globs, guide/calibration files, or "past recipe" phrasing;
3. no dangling tool references — a backticked name must be a tool that exists
   on the surface (or a whitelisted non-tool term);
4. the legacy ``TOOLS_SPEC`` descriptions are byte-identical to the rendered
   docs (single source, no drift);
5. if langchain is installed, the native tools' ``.description`` matches too.

The LIBERO docs module is loaded BY FILE PATH so the whole rendered LIBERO
surface lints without importing the tool layer (and its langchain dependency).
The stdlib part therefore runs anywhere; check 5 auto-skips where langchain is
absent (e.g. the local Mac) and runs on the box.
"""
import importlib.util
import re
import sys

sys.path.insert(0, ".")

from rpent.tools import tool_docs  # noqa: E402
from rpent.tools.common import TOOLS_SPEC  # noqa: E402


def _load_by_path(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


libero_docs = _load_by_path(
    "libero_tool_docs", "robots/libero/tools/tool_docs.py"
)

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


# The full model-facing tool surface: 14 LIBERO + 5 common, plus the two
# resident-session tools (reset_episode, view_attempt_call) that ship only
# under --resident. Kept by hand so a rename or removal breaks this test
# visibly instead of leaving dangling references in descriptions.
KNOWN_TOOL_NAMES = {
    # state
    "view_driver_state",
    # motion
    "move_to", "move_pose", "rotate_wrist", "rotate_pitch", "release", "set_gripper",
    # vla
    "pi0_pick", "pi0_doubled",
    # perception
    "view_camera_meta", "segment", "back_project", "world_extent", "compare_extent",
    # resident session (conditional surface)
    "reset_episode",
    # common
    "read_text_file", "write_text_file", "list_dir", "finish", "read_image",
    "view_attempt_call",
}

# Backticked terms in descriptions that are legitimately not tool names
# (argument names and returned-field names quoted in the prose).
NON_TOOL_TERMS = {"path", "max_chars", "world_xyz", "steps", "entity", "shape",
                  "reason", "attempt_NN/"}

# A hit on any of these in a rendered description is a prior leak: it either
# advertises that priors exist or hands the model the path to them.
FORBIDDEN_PATTERNS = [
    r"resources/",
    r"results_\w*",
    r"env_calibration",
    r"guides/",
    r"past recipe",
    r"memory file",
    r"memory librar",
    r"MEMORY\.md",
]

# --- 1+2+3: the structured docs and their rendered surface -------------------
LIBERO_EXPECTED = KNOWN_TOOL_NAMES - {
    "read_text_file", "write_text_file", "list_dir", "finish", "read_image",
    "view_attempt_call",
}
check(
    set(libero_docs.LIBERO_TOOL_DOCS) == LIBERO_EXPECTED,
    "LIBERO_TOOL_DOCS names disagree with the known surface: "
    f"{sorted(set(libero_docs.LIBERO_TOOL_DOCS) ^ LIBERO_EXPECTED)}",
)

RENDERED_SURFACE = list(tool_docs.iter_rendered()) + [
    (name, libero_docs.render_description(name))
    for name in libero_docs.LIBERO_TOOL_DOCS
]

for name, text in RENDERED_SURFACE:
    for pat in FORBIDDEN_PATTERNS:
        check(
            re.search(pat, text, re.IGNORECASE) is None,
            f"{name}: forbidden pattern {pat!r} in rendered description",
        )
    for ref in re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", text):
        check(
            ref in KNOWN_TOOL_NAMES or ref in NON_TOOL_TERMS,
            f"{name}: dangling backtick reference `{ref}` (not a known tool)",
        )

# --- 4: legacy TOOLS_SPEC renders from the same source -----------------------
for spec in TOOLS_SPEC:
    check(
        spec["description"] == tool_docs.render_description(spec["name"]),
        f"TOOLS_SPEC[{spec['name']}]: description drifted from tool_docs",
    )
    for pat in FORBIDDEN_PATTERNS:
        check(
            re.search(pat, str(spec), re.IGNORECASE) is None,
            f"TOOLS_SPEC[{spec['name']}]: forbidden pattern {pat!r} in spec",
        )

# --- 5: native LangChain surface, where importable ---------------------------
try:
    from rpent.tools import langchain_common
except ImportError:
    print("SKIP native-surface check (langchain not installed here)")
else:
    pairs = [
        (langchain_common.read_text_file, "read_text_file"),
        (langchain_common.write_text_file, "write_text_file"),
        (langchain_common.list_dir, "list_dir"),
        (langchain_common.finish, "finish"),
        (langchain_common.read_image, "read_image"),
        (langchain_common.read_image_text_only, "read_image_text_only"),
        (langchain_common.view_attempt_call, "view_attempt_call"),
    ]
    for t, key in pairs:
        check(
            t.description == tool_docs.render_description(key),
            f"native {t.name}: description drifted from tool_docs[{key!r}]",
        )
    try:
        from robots.libero.tools import agent_tools
    except Exception as exc:  # heavy env deps may be absent off-box
        print(f"SKIP LIBERO native-surface check ({type(exc).__name__}: {exc})")
    else:
        for t in agent_tools.LIBERO_TOOLS:
            check(
                t.description == libero_docs.render_description(t.name),
                f"native {t.name}: description drifted from LIBERO_TOOL_DOCS",
            )
        # The resident tool is not on LIBERO_TOOLS (conditional surface) but
        # its description renders from the same source.
        for t in agent_tools.RESIDENT_TOOLS:
            check(
                t.description == libero_docs.render_description(t.name),
                f"native {t.name}: description drifted from LIBERO_TOOL_DOCS",
            )

if FAILURES:
    print(f"FAIL ({len(FAILURES)}):")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print(f"OK — {len(tool_docs.COMMON_TOOL_DOCS)} common + "
      f"{len(libero_docs.LIBERO_TOOL_DOCS)} LIBERO docs entries, "
      f"{len(TOOLS_SPEC)} legacy specs linted")
