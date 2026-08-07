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
