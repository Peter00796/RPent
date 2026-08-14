# Operations

## Git

Branch: `refactor/langchain-native-tools`. Remotes:

```
origin       https://github.com/RLinf/RPent.git        (upstream)
zhejiang-d   git@github.com:Peter00796/RPent.git       (the working fork)
```

**SSH to github is blocked** on this machine — port 22 gets intercepted to
`198.18.0.165` (a VPN/proxy range) and times out. HTTPS works, and `gh` is already
configured as the git credential helper, so push with the HTTPS URL:

```bash
git push https://github.com/Peter00796/RPent.git refactor/langchain-native-tools
```

`git remote set-url zhejiang-d https://github.com/Peter00796/RPent.git` would make
`git push zhejiang-d` work directly.

## Remote box

```bash
ssh guangdong-b-is.cloud.infini-ai.com          # host is-ddcsxug6m5wqynst-devmachine-0
```

Log archives:

| path | what |
|---|---|
`/mnt/user_dir/pengyanxin/rpent_refactor/logs` | **new** framework (deepagents), 11 runs + `run_newframe_t*.out` |
`/mnt/user_dir/pengyanxin/rpent_setup/rpent/logs` | **pre-refactor** runs, 156 entries |

Shell quoting gotcha when running python remotely: single quotes inside an
already-single-quoted `ssh '...'` argument terminate it. Base64 the script instead:

```bash
B=$(base64 < script.py | tr -d '\n')
ssh HOST "cd DIR && echo $B | base64 -d > /tmp/s.py && python3 /tmp/s.py"
```

## Running a cell

```bash
rpent --env libero --suite libero_object_swap --task 2 --seed 0 \
  --planner deepagents --model deepseek-v4-flash --no-images --max-turns 30
```

- `DEEPSEEK_API_KEY` must be set. `--base-url` overrides the endpoint
  (default `https://api.deepseek.com/v1`); `https://api.deepseek.com/beta` enables
  strict schema validation if tool arguments ever drift.
- `--no-images` is **required** for a text-only planner. Without it the model gets
  image bytes and the request fails; `read_image` also advertises itself honestly
  only under this flag.
- `--planner {api,deepagents,claude_code,codex}`. The last three are untouched by
  this work; `api` still runs through `legacy_specs.py`.

## Checking a finished run

```bash
python3 - <<'PY'
import json
d = "PATH/TO/RUN"
st = json.load(open(f"{d}/states.json"))
print("terminated at:", [e["step_idx"] for e in st if e.get("libero_terminated")])
for r in open(f"{d}/tool_calls.jsonl"):            # every call, incl. read-only
    r = json.loads(r); print(r["seq"], r["tool"], r["args"])
print(json.load(open(f"{d}/analysis/entities.json"))["entities"].keys())
PY
```

**Audit for prior leakage** — grep the run log for reads that should not happen:

```bash
grep 'read_text_file' run.log | grep -E 'results_.*_pert|env_calibration'
```

Any hit means the run consumed a per-cell answer or the memorised calibration table,
and its result does not measure the harness. Until issue 1 in `04-open-issues.md` is
implemented, this grep is the only check.

## Regression tests

In [`tests/harness/`](../../tests/harness/). They are plain scripts, not pytest:

```bash
PYTHONPATH=. python tests/harness/test_shape.py       # geometry vs synthetic ground truth
PYTHONPATH=. python tests/harness/test_databus.py     # readings, staleness, conflicts, concurrency
PYTHONPATH=. python tests/harness/test_deep_agent.py  # planner end-to-end with a scripted model
```

`test_deep_agent.py` drives the real planner, real middleware, real native tools and a
real `LiberoContext` — only the chat model and the env primitives are fakes, so it
needs no API key and no GPU. It is the fastest way to know the planner still works.

`retro.py` replays the geometry tools over pre-refactor runs and expects them under
`tests/harness/realdata/` (not committed, ~429 MB; fetch from the box).
`audit_descriptions.py` is currently broken — see `04-open-issues.md`.

Dependencies for the tests: `langchain>=1.3.14`, `langchain-deepseek`, `numpy`,
`imageio`, `scipy`. `langchain-anthropic` only if checking the image-block conversion
path.

## Hard-won gotchas

### An exhaustive matrix can be flattened by one uncontrolled confound

`10_task` t4's second resident round ran a systematic placement matrix and got
**uniformly false** back. The natural reading — the checker is broken — was
wrong. The matrix was flattened by an uncontrolled variable: an OSC
placement-drag singularity displacing the object 4–5 cm during release, which
affected *every* cell of the matrix equally and therefore looked like no signal
at all rather than like interference.

**A uniform negative across a systematic sweep is evidence of a confound at
least as often as it is evidence of absence.** Before concluding "nothing
works", check whether something is acting on every arm of the sweep alike.

### 150 turns is systematically short for long-horizon resident work, and budget death costs the notes

Across three of the four cells in the resident campaign, the first 150-turn
round produced no solve and — more expensively — **no `resident_notes.md`**,
because notes are written near the end and a run that dies on its budget dies
before writing them. The 300-turn second rounds produced both solves and notes.

The consequence is worse than a lost cell: **the distillation material is gone
too.** What survives a budget death is only the `reset_episode` reasons and the
raw transcript, not the model's own curated recipe. Budget long-horizon resident
sessions at 300 turns, and treat notes-before-budget-exhaustion as the thing
being protected.

### ⚠ The same cell name exists in every sweep — the time window IS the arm

`logs/` is flat and run directories are named
`{timestamp}_{suite}_t{task}_s{seed}`. **The arm appears nowhere in the name.**
By 2026-08-14, `libero_object_swap_t5_s0` had four directories — one each from
the 50-turn generation 7 sweep, full-benchmark gen 0, gen 1, and gen 1b — plus
separate `run_rep_*` repeat logs for other arms entirely.

**Selecting by cell name alone silently gives you a different arm's result.**
This cost a two-person cross-check a two-cell disagreement on gen 0 (38 vs the
correct 40) before it was traced: one side's glob had swept in `run_rep_none*`
directories, which overwrote the real cells by name.

Rules that avoid it:

- **Filter by time window first, then by name.** Each sweep's window is its
  boundary: gen 0 is 08-13 09:29 onward; gen 1 begins at its first cell,
  `20260814-02:23:08`. Confirm the window's edges against the neighbouring
  sweep's first and last directory rather than assuming.
- **Confirm the arm from `sandbox.json`**, not from the plan or the folder name.
  It records the profile and the source hash actually in force.
- **Assert no duplicates before counting.** Strip the timestamp, sort, and check
  for repeats; a duplicate cell inside one arm's set means the window is wrong
  or a cell was re-run, and either way the count is not yet trustworthy.

This is the same failure class as the wiped `/tmp` that made a mining step
silently no-op, the editable install that resolved imports to the wrong tree,
and the hardcoded LaTeX cross-references that were correct when written and
wrong later: **all of them return a plausible answer instead of an error.** The
only defence that has ever worked here is checking an artifact rather than
trusting that a step did what it was named for.



- **`agent_tools.py` must not gain `from __future__ import annotations`.** It breaks
  `ToolRuntime` injection silently, and only at dispatch time. See `02-decisions.md`.
- **A turn's tool calls run concurrently in one process.** Anything doing
  read-modify-write on a shared file needs a lock — this already bit
  `segments/segment_NN_XX.json` (fixed with `O_CREAT|O_EXCL`), and both `databus` and
  `tool_log` use module locks for it.
- **Per-run append-only files must be wiped at episode start.** `tool_calls.jsonl` and
  `analysis/entities.json` join `states.json` in both wipe paths; a leftover makes the
  new episode read as a continuation of the previous one.
- **macOS filesystems are case-insensitive.** A path typo differing only in case
  resolves to the same directory. During this work an `rm -rf` on a mis-cased path
  deleted the entire project tree; it was recoverable only because everything was
  pushed. Push before any destructive command, and prefer `git clean` / targeted
  deletes over `rm -rf` on an absolute path.
- **`states.json` records only advancing primitives.** On the run examined, 27 tool
  calls happened and `states.json` held 6. Use `tool_calls.jsonl` for anything about
  perception or file reads.
