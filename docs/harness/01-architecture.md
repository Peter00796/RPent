# Architecture as it stands

## Process topology (unchanged by this work)

Three **service subprocesses**, spawned by `robots/libero/__init__.py::_init_runtime`:

```
┌─ rpent main process ─────────────────────────────────────┐
│  planner ──── HTTPS ────► LLM API (remote)               │
│     │ calls tools                                        │
│  LiberoToolkit / LiberoPrimitives                        │
└─────┬──────────┬──────────┬──────────────────────────────┘
      │ HTTP     │ HTTP     │ HTTP  (127.0.0.1, random ports)
  env_server  vla_server  sam3_server      ← all need GPU
  (MuJoCo)    (Pi0.5)     (SAM 3.0)
```

The planner is **not** a service; it runs in-process. `--env-endpoint` /
`--vla-endpoint` / `--sam3-endpoint` attach to already-running services instead of
spawning them.

## Startup order (`rpent/cli/main.py`)

```
parse_config → init_output_dir → ensure_resources (HF sync — see 04, issue 1)
  → build_planner            ← chat model is CONSTRUCTED HERE, deliberately
  → render system + user prompts
  → env_spec.init_runtime    ← the three GPU servers boot here
  → get_toolkit              ← resets env, dumps step 0
  → planner.solve
```

Prompts render **before** the servers boot so `--interactive` can accept typing during
the slow GPU load. The chat model is built in `build_planner`, before the servers, so a
bad `--model` fails in a second rather than after minutes of loading.

## Tool layer: `robots/libero/tools/`

| Module | Contents |
|---|---|
`agent_tools.py` | **The 14 `@tool` functions. Each tool's description is its docstring.** |
`schemas.py` | **Pydantic input models. Each argument's description is its `Field(description=...)`.** |
`context.py` | `LiberoContext` — delivered via `ToolRuntime`; `advance()` owns per-action bookkeeping |
`databus.py` | Append-only entity readings, staleness, identity/collision conflicts |
`catalog.py` | Tool kinds + the advancing-primitive name set (imports nothing from the package) |
`primitives.py` | `LiberoPrimitives` core: env/policy handles, obs cache, `_step_env`, `_vlm_chunk` |
`motion.py` | `MotionMixin` — 6 scripted OSC primitives, no VLM call |
`vla.py` | `VlaMixin` — `pi0_pick` / `pi0_doubled`, the only code that calls Pi0.5 |
`perception.py` | `SegmentMixin` + `view_camera_meta` / `back_project` handlers |
`geometry.py` | Pure math: `_mask_to_world`, `_principal_axes`, `world_extent`, `compare_extent` |
`state.py` | `states.json` dump/read, recipe export, `view_driver_state` |
`artifacts.py` | The run-artifact path layout (`ARTIFACT_LAYOUT` is the single source) |
`legacy_specs.py` | Migration shim: renders the native tools back into Anthropic dicts |

**Two files hold everything the model reads about a LIBERO tool**: `tool_docs.py`
(descriptions, authored as structured template fields — what / need / returns / when /
how / failure_modes — and rendered deterministically; `agent_tools.py` injects the
rendered string via `@tool(description=...)`, its docstrings are dev notes) and
`schemas.py` (argument descriptions). That is deliberate — it is the surface that gets
hashed, diffed, and linted (`tests/harness/test_tool_docs.py`). The template and
renderer live in `rpent/tools/tool_docs.py`, which also holds the common tools'
entries; content was migrated verbatim from the pre-migration docstrings.

### The 14 tools by kind

```
state       view_driver_state
motion      move_to  move_pose  rotate_wrist  rotate_pitch  release  set_gripper
vla         pi0_pick  pi0_doubled
perception  view_camera_meta  segment  back_project  world_extent  compare_extent
```

Plus 5 environment-independent tools from `rpent/tools/langchain_common.py`:
`read_text_file`, `write_text_file`, `list_dir`, `finish`, `read_image`. Total 19.

### Dispatch depth

A tool call goes: `ToolNode` → the `@tool` function → `ctx.advance(name, args,
ctx.primitives.<method>)` → the primitive. Two hops. There is no name-string `getattr`
dispatch, no `partial`, no `execute_tool` lookup table — those were the five-hop chain
this refactor removed.

## Planner layer

| File | Role |
|---|---|
`rpent/planner/deep_agent.py` | `DeepAgentPlanner` on LangChain `create_agent` |
`rpent/planner/middleware.py` | `MIDDLEWARE_ORDER` + `TranscriptMiddleware` + `ToolCallLogMiddleware` |
`rpent/tools/tool_log.py` | `tool_calls.jsonl` writer/reader; **stdlib only**, so diagnostics can read a run without the agent framework |
`rpent/planner/api_loop.py` | The pre-existing pydantic-ai planner, untouched |
`rpent/planner/claude_code.py`, `codex.py` | External CLI-agent planners, untouched |

`MIDDLEWARE_ORDER` is a declared list, outermost first — a different order is a
different method, so it is recorded rather than implicit. Implemented:
`ModelCallLimitMiddleware` (prebuilt, turn budget), `TranscriptMiddleware`,
`ToolCallLogMiddleware`. Named but not implemented: `InjectionLedgerMiddleware`,
`GateMiddleware`, `ProvenanceMiddleware`, `CompactionMiddleware`.

Useful hooks on `AgentMiddleware` (langchain 1.3): `before_agent` / `after_agent`,
`before_model` / `after_model`, `wrap_model_call(request, handler)` — where `request`
carries `messages`, `system_message` and `tools`, i.e. exactly what reaches the
provider, making it the anchor for injection accounting — and
`wrap_tool_call(request, handler)`, where `request` carries `tool_call`, `tool`,
`state` and `runtime`, making it the anchor for gates.

## Run artifacts

```
{output_dir}/
  states.json              one entry per ENV STEP (advancing primitives only)
  tool_calls.jsonl         one line per TOOL CALL, including read-only ones
  analysis/entities.json   the entity databus (append-only readings)
  camera_meta.json  wrist_meta/
  world/ world_hi/ world_wrist/ world_wrist_hi/     per-pixel world xyz maps
  depths/ depths_wrist/                              metric depth
  images/ images_cam/ images_cam_hi/ images_wrist/ images_wrist_hi/
  segments/                one JSON + overlay per segment call
  action_videos/           per-action clips (explicit flag, not dashboard state)
  {recipe_tag}.json        the audit the agent writes
  recipe_{recipe_tag}.jsonl
```

`states.json` is keyed by env step; `tool_calls.jsonl` is keyed by call sequence and
records `step_idx_before` / `step_idx_after`, so "did this call advance the
environment" is computed from the log rather than declared in it. High-resolution world
maps keep only the last 5 steps.

## Evidence replay (`rpent/replay/`)

```bash
PYTHONPATH=. python -m rpent.replay <run_dir>     # -> <run_dir>/replay.html
python scripts/replay_run_3d.py <run_dir>          # -> 3D point-cloud slider
```

Rebuilds a finished run as a turn-by-turn timeline — reasoning text, then
each tool call's card — from the DISK ARTIFACTS ALONE, which makes it double
as the completeness test of the evidence record (a `record gaps` warning
means the logs are missing something, and the fix is to record more).
`loader.py` joins `tool_calls.jsonl` (ground truth) with the transcript
(reasoning); `render.py` holds ONE RENDERER PER TOOL (`REGISTRY` — adding a
tool means adding a function); `project.py` turns any recorded world-xyz
into a dot on the recorded camera image by nearest-neighbour lookup in the
stored world maps (no camera math; occluded points are reported, not drawn).
Every call anchors as `#seq-N`, which is the evidence deep-link format that
memory proposals and the promotion gate cite. Stdlib + numpy only.

## Promotion gate (`rpent/gate/`)

```bash
python -m rpent.gate observe    RUN...   # per-run, LIBRARY-BLIND observations (LLM)
python -m rpent.gate synthesize RUN...   # sweep-wide proposals + HARNESS_REVIEW.md (LLM)
python -m rpent.gate review     RUN... --proposals <dir>   # five checks -> report + verdicts
#   human edits verdicts.yaml            <- the interrupt
python -m rpent.gate apply      verdicts.yaml               # the ONLY writer of memory/
python -m rpent.gate ledger     RUN...   # consumption track record per entry
```

Layered digestion: observers see exactly what one run recorded (independent
accounts — support is counted from independent discovery); the synthesizer
sees everything (observations, outcomes, the CURRENT library, the ledger)
and triages each issue cluster into ``add`` / ``revise`` / ``evict`` /
``endorse``, plus a human-facing memo for what a memory entry cannot fix.
Evidence grounds to ``run:<name>#seq=N`` tokens resolved straight into
``tool_calls.jsonl`` (never to observation files), and the gate report deep
links every citation into that run's ``replay.html``. The five checks:
contract/citation resolution, number-traceability against cited records,
per-cell-answer naming (against the cited runs' ``object_names``), scope
vocabulary, dedup/support counting. Consumption in the ledger is read
mechanically from ``read_text_file`` records, never from strategy notes.
Everything except the two LLM stages is stdlib+yaml
(`tests/harness/test_gate.py` runs the whole chain locally).

## Code-as-policy arm (`rpent/cap/`, ASPIRE replication)

```bash
python -m rpent.cap --suite libero_object_swap --task 3 --debug-seed 51   # write/run/debug/freeze
python -m rpent.cli.main ... --planner program --program-file programs/<suite>/t3/solve.py
```

The ASPIRE cycle (arXiv 2607.00272) on this harness: the coding agent lives
BETWEEN episodes. In-loop, ``--planner program`` executes a fixed program
with zero LLM calls; the program's API functions are the tool handlers bound
to the run's context, so the evidence layer (tool_calls.jsonl, replay,
sandbox, databus) is identical across policy forms — the CaP arm and the
tool-loop arm differ only in who decides the next call, which is what makes
the A/B interpretable. Out-of-loop, ``rpent.cap.loop`` feeds the coding
agent the API doc (rendered from tool_docs + schemas), the memory library
(the skill-library role), and each attempt's recorded digest + traceback,
then freezes the program on debug-seed success (hash into ``program.json``).
Frozen programs live under ``programs/`` — per-cell POLICY artifacts,
legitimate via the seed-split protocol, never admitted to the memory
library. `tests/harness/test_cap.py` covers namespace safety and the
executor locally.

## Prompt layer

`robots/libero/prompts/system.py` sections, assembled by
`robots/libero/prompt_bundle.py`:

```
ROLE_AND_EVALUATION   regime: perception-isolated, blind planner, single attempt
EVIDENCE_DISCIPLINE   measure don't recall; register entities; verify with geometry
MECHANICS             facts no tool reports and that hold in every scene
RUNTIME               artifact paths
GOAL
RULES                 Rule 0..4
LOCALIZATION          the four channels and which question each answers
PERCEPTION_ALGORITHM  agentview = identity, wrist = geometry refine
WORKFLOW_STEPS        8 numbered steps
OUTPUT_DISCIPLINE
```

`PROVEN_LEVERS` and `KEY_HYPERPARAMETERS` were **deleted** — see `02-decisions.md` for
the admission rule that removed them. The system prompt is now 21,517 chars against
36,891 before, with no coordinate-level constants remaining.
