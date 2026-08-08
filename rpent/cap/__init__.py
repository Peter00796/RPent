"""Code-as-Policy on the RPent harness (the ASPIRE replication, arXiv 2607.00272).

The split that makes this cheap here:

- **In-loop** (`--planner program`): a run executes a FIXED Python program
  against the tool layer — zero LLM calls inside the episode. Because the
  program's API functions are the same tool handlers behind ``ctx.advance``,
  every call lands in ``tool_calls.jsonl``, the replay rebuilds the episode,
  and the sandbox still governs file access. ASPIRE's per-primitive
  multimodal trace engine is our existing evidence layer, for free.
- **Out-of-loop** (:mod:`.loop`): the coding agent lives BETWEEN episodes,
  exactly as in ASPIRE — write program, run an episode on a debug seed, read
  the evidence digest, revise, repeat; freeze the program when the debug
  seeds pass; evaluate the frozen program on held-out seeds.

Two stores, two legitimacy rules: a per-task program is a per-cell POLICY
ARTIFACT and lives under ``programs/`` — its legitimacy comes from the
seed-split protocol (learned on debug seeds, measured on held-out seeds),
never from the memory library's admission rule. The memory library keeps
holding transferable technique, which program synthesis consumes as
in-context guidance — the same role ASPIRE's skill library plays.
"""
