"""Evidence replay: reconstruct a finished run from its disk artifacts alone.

The replay is generated OFFLINE from ``{output_dir}`` — never from live
process state — because it doubles as the completeness test of the evidence
record: if the timeline cannot be reconstructed from the artifacts, the
record has a hole, and the fix is to record more, not to peek at memory.

    python -m rpent.replay <run_dir>          -> <run_dir>/replay.html

Layout:

- :mod:`.loader`   — join ``tool_calls.jsonl`` (ground truth, seq-ordered)
  with the transcript (per-turn reasoning) and ``states.json`` into one
  timeline of :class:`~rpent.replay.loader.Call` entries.
- :mod:`.project`  — world xyz -> pixel via the stored world maps (nearest
  neighbour; no camera math, no new rendering). Any 3D coordinate becomes a
  dot on the image the planner was reasoning about.
- :mod:`.render`   — ONE RENDERER PER TOOL (``REGISTRY``): each tool knows
  how to draw its own evidence. Adding a tool = adding a function and a
  registry line.
- :mod:`.html`     — a single self-contained ``replay.html`` beside the
  artifacts; images are referenced relatively, markers are SVG overlays, no
  server and no CDN.

Citation anchors: every call renders as ``id="seq-N"`` and every env step as
``id="step-N"``, so ``replay.html#seq-17`` is a stable evidence deep link —
the token format that memory proposals and the promotion gate cite.
"""
