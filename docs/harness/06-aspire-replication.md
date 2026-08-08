# ASPIRE replication checklist (arXiv 2607.00272, read 2026-08-08)

What the paper actually specifies, what we implement, and where we deviate —
so the replication claim is auditable. We replicate the METHOD on our stack
(LIBERO + our tool API), not their benchmark numbers (their env is CaP-X on
MuJoCo Playground; APIs differ by construction).

## Algorithm 1, symbol by symbol → `rpent/cap/loop.py`

| paper | ours | status |
|---|---|---|
| P⁰ executed on S_dbg first | round 1 candidates (no parents) | ✅ superset (K initial candidates, they imply 1 + "15 example programs" flavor) |
| S_dbg = 15 perturbed configs (seeds 51-65) | `--debug-seeds 51,52,...` — must solve ALL | ✅ mechanism; count is a cost knob (we start 3, they used 15) |
| ProposeRepairs(M, τ, **Top3(ℋ)**, ℒ, ℋ) | parents = top-3 of population + failure evidence; siblings get distinct-strategy instruction | ✅ after top-2→top-3 fix |
| full history ℋ in context | only Top3 + this round's siblings | ⚠ deviation: they run Opus 4.6 @1M ctx; our flash cannot carry ℋ. Documented, revisit with a bigger coder |
| r = score on S_dbg | seeds-solved dominates, env-steps progress tie-break (`_score`, mechanical) | ✅ their r is success-rate; ours is rate-dominant lexicographic |
| keep P*, return it even if r* < θ | freeze `best.py` on budget exhaustion | ✅ after fix (was: return nothing) |
| θ threshold | all-debug-seeds-pass (θ=1.0) | ✅ special case |
| Execute(P*, S_val) | held-out eval: frozen file, plain runs, seeds 1-N | ✅ protocol; run manually |
| ExtractValidatedPatterns → ℒ | observe/synthesize/gate over the debug episodes | ✅ ours is stricter (five checks, provenance, ledger); theirs is coordinator judgment |
| coordinator audits API policy | admission rule + sandbox | ✅ analogous |

## Their evidence engine ↔ our evidence layer

Per-primitive trace {invoked API, inputs/outputs, status, RGB keyframes
before/after, overlays} = `tool_calls.jsonl` + replay. Convergent design,
built independently. Their trace engine ablation is the paper's biggest
effect: **14% → 62%** macro-avg from adding it (evolution adds 62% → 72%).
The evidence layer is the main course; search is dessert. This ranks our
engineering priorities for us.

## Numbers that externally validate our standing bets

- **Skill-library scaling** (LIBERO-Pro Long, zero-shot): N=0 → 4.7%,
  N=25 → 13.7%, N=50 → 21.5%, N=90 → 30.5%. A generational growth curve —
  the thesis our gate/memory loop exists to measure, in their data.
- **Cross-embodiment transfer** (sim skills → real YAM robot, different API):
  skills as IN-CONTEXT GUIDANCE, agent re-adapts through execution feedback —
  soda-can 13/20→19/20 with tokens 61.9M→6.6M. This is exactly the
  `memory/common` design: technique transfers, values re-derive.
- **CaP-Agent0 baseline** ("regenerates a separate program per seed with
  test-time reasoning and retries") is structurally our TURN-LOOP arm's
  cousin: per-episode test-time reasoning. Their dichotomy (amortized program
  vs per-seed reasoning) is our A/B, run without shared perception. Ours
  holds the tool layer constant across arms — that is the gap we occupy.

## Known deviations, all deliberate

1. Coder model: flash (theirs: Opus 4.6 / GPT-5.5-xhigh). Cost structure of
   CaP favors upgrading the coder later — out-of-loop tokens only.
2. Debug set size 3 vs 15; eval seeds 10 vs 50 initially — single 4090,
   episodes are serial. Protocol identical, scale dialed by GPU budget.
3. No BEHAVIOR/Robosuite; LIBERO only.
4. Full-history conditioning truncated to Top3+siblings (context).
5. Our API includes a frozen VLA primitive (`pi0_pick`) — theirs has no
   learned policy inside the API. Deliberate: the hybrid arm is our fork.

## Faithful-run recipe (when the GPU frees)

```bash
python -m rpent.cap --suite libero_object_swap --task 3 \
  --debug-seeds 51,52,53 --k 3 --max-attempts 3          # ≤27 episodes
# then held-out, frozen program:
for S in 1 2 3 4 5 6 7 8 9 10; do
  python -m rpent.cli.main --env libero --suite libero_object_swap --task 3 \
    --seed $S --planner program \
    --program-file programs/libero_object_swap/t3/solve.py --no-images; done
```
