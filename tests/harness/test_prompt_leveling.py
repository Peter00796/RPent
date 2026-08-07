"""The leveled prompt: capability-truthful, prior-free under `none`.

Plain script, not pytest, like the other harness tests:

    PYTHONPATH=. python tests/harness/test_prompt_leveling.py

The invariant under test: the rendered prompt never instructs a read the
sandbox would refuse, and never NAMES what the sandbox blocks — a verbal
prohibition is an advertisement, so the prior-free prompt must read as if
the prior files never existed. Pure-string imports only; runs anywhere.
"""
import re
import sys

sys.path.insert(0, ".")

from robots.libero.prompt_bundle import system_prompt, user_prompt  # noqa: E402
from rpent.context.prompt_utils import format_prompt  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL':4}  {label}"
          + (f"\n        {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


VARS = {
    "output_dir": "/tmp/run",
    "recipe_tag": "cell_t0",
    "suite": "libero_object_swap",
    "task": "0",
    "seed": "0",
    "memory_common": "/repo/memory/common",
    "memory_env": "/repo/memory/libero",
}


def render(memory: bool) -> str:
    return (format_prompt(system_prompt(memory=memory), variables=VARS)
            + "\n" + format_prompt(user_prompt(memory=memory), variables=VARS))


# Naming any of these is a prior leak, in EVERY variant: the sandbox blocks
# them, so the prompt must not acknowledge they exist.
LEAKS_ALWAYS = [
    r"resources/",
    r"results_\w*",
    r"env_calibration",
    r"guides?/",
    r"hybrid_guide",
    r"MEMORY\.md",
]
# Under the prior-free variant the library itself must be unmentioned too.
LEAKS_PRIOR_FREE = [r"memor(y|ies)", r"skill librar"]

print("=== prior-free variant (memory=False) ===")
none_text = render(memory=False)
for pat in LEAKS_ALWAYS + LEAKS_PRIOR_FREE:
    check(f"no /{pat}/", re.search(pat, none_text, re.IGNORECASE) is None)
check("no verbal file prohibitions (Do NOT read)",
      re.search(r"do not read", none_text, re.IGNORECASE) is None)
check("workflow starts at the initial-state inspection",
      "INSPECT THE INITIAL STATE" in none_text)

print("\n=== memory variant (memory=True) ===")
mem_text = render(memory=True)
for pat in LEAKS_ALWAYS:
    check(f"no /{pat}/", re.search(pat, mem_text, re.IGNORECASE) is None)
check("library step present and points at the sandboxed roots",
      "/repo/memory/common" in mem_text and "/repo/memory/libero" in mem_text)
check("library framed as technique, not values",
      "take the technique" in mem_text.lower())
check("still no verbal file prohibitions",
      re.search(r"do not read", mem_text, re.IGNORECASE) is None)

print("\n=== both variants ===")
check("variants differ only by the library material",
      len(mem_text) > len(none_text))
for text, tag in ((none_text, "none"), (mem_text, "memory")):
    check(f"{tag}: single-attempt regime intact", "SINGLE-ATTEMPT" in text)
    check(f"{tag}: measure-don't-recall intact", "Measure, do not recall" in text)
    check(f"{tag}: no unresolved {{{{placeholders}}}}", "{{" not in text)

if failures:
    print(f"\nFAILED ({len(failures)}): {failures}")
    sys.exit(1)
print("\nOK — leveled prompt is capability-truthful and prior-silent")
