# memory/libero — LIBERO environment memory

Environment-specific knowledge for LIBERO: embodiment invariants measured
once (e.g. which eef axis the fingers close along vs `rotate_wrist`), fixture
behaviours, environment-wide conventions no tool reports. Anything true
across environments belongs in `memory/common/`; anything specific to one
task cell (a coordinate, an object identification, a `max_chunks` that
worked) is never admitted at all.

Same governance as `memory/common/`: agents write proposals to
`{output_dir}/memory_proposals/`, only the promotion gate writes here, every
entry carries provenance frontmatter, refuted entries are evicted. See
`memory/common/README.md` and `docs/harness/02-decisions.md`.

Deliberately decoupled from `resources/libero/` (the upstream priors payload,
now synced to `.staging/` only under `--sandbox full`): this library holds
what the harness grew and can defend with measurements, nothing inherited.
