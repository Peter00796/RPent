# memory/common — cross-environment harness memory

Transferable operating wisdom only: evidence discipline, self-debugging
procedures, how to acquire and cross-check 3D geometric evidence. If an entry
mentions a specific environment, scene, object instance, or coordinate, it
does not belong here.

Admission is gated, not manual:

- Agents never write here. A run's proposals go to
  `{output_dir}/memory_proposals/`; the promotion gate validates them
  (provenance present, admission rule satisfied, cited artifacts recomputed)
  before anything lands in this library.
- Every entry must carry provenance frontmatter: which run produced it, which
  measurement supports it, which artifact paths to recompute it from. An
  entry refuted by later measurement is evicted, not edited.
- The admission rule is the two-dimensional table in
  `docs/harness/02-decisions.md`: instance-varying + tool-measurable values
  are never admitted (measure them per run); per-cell answers are never
  admitted (that is the cheat the benchmark excludes).

This library is versioned by git: a generation of the grown harness is a
commit, and generation diffs are the attribution record.
