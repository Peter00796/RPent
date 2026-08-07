"""User prompt section bodies for a concrete LIBERO evaluation cell."""

from __future__ import annotations

CELL = """- suite:      {{suite}}
- task:       {{task}}
- seed:       {{seed}}
- output_dir: {{output_dir}}
- audit:      {{output_dir}}/{{recipe_tag}}.json
- recipe:     {{output_dir}}/recipe_{{recipe_tag}}.jsonl"""


MODE = """Perception-isolated, single attempt. You cannot see images; localize with
`segment`, `back_project`, `world_extent` and `compare_extent`, and register each
entity you localize. Every coordinate you command must come from a tool result in
this episode."""


BEGIN = """`view_driver_state({"step":0})`, run the perception pass, and only then plan
and execute."""

#: Used instead of BEGIN when the sandbox exposes the memory library.
BEGIN_MEMORY = """consult the memory library for technique — never for values. Then
`view_driver_state({"step":0})`, run the perception pass, and only then plan
and execute."""
