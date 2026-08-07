"""The promotion gate: an evidence pipeline between generations.

Nothing enters the memory library except through here, and nothing here
takes an agent's word for anything — every claim must cite the run record,
and the gate resolves each citation against the artifacts before a human
sees the proposal.

The layered digestion (each layer reads the one below, never raw hearsay):

    run record                 tool_calls.jsonl / states.json / transcript
      └─ observe    (LLM, per run, LIBRARY-BLIND)   → observations/*.md
      └─ synthesize (LLM, per sweep, sees the full library + ledger)
                                                    → proposals/*.md + HARNESS_REVIEW.md
      └─ gate review (host, pure code)              → report.html + verdicts.yaml
      └─ human edits verdicts.yaml                  ← the interrupt
      └─ gate apply                                 → memory/  (commit = generation k+1)
      └─ gate ledger (any time)                     → consumption record per entry

Proposal verbs: ``add`` / ``revise`` / ``evict`` / ``endorse``. Touching an
existing entry demands more evidence than adding one — wide at the door,
strict on tenure, eviction by refutation.

The iron rule against hearsay: proposal evidence grounds to
``run:<name>#seq=N`` tokens (resolved straight into ``tool_calls.jsonl``),
never to observation files. Observations are the synthesizer's index, not
evidence.

Everything except :mod:`.observe` / :mod:`.synthesize` is stdlib+yaml and
runs anywhere, like the replay layer it builds on.
"""
