# Partial aggregate prerequisites

The compatible-map identity/fraction cells have the specific precondition from
177: observed_conflict gives state conflict; incomplete_geometry gives state
missing. Retain the underlying reasons, but do not upgrade these conditional
cells to invalid/conflict solely because an unavailable graph-count operand has
that state. This is absence of the required compatible map. Independent graph
counts, unions and per-block cells keep their own states.

Multiple-block HSP gap-run totals require usable strings and proven boundary
continuity. Known invalid/conflicting prerequisites remain invalid/conflicting,
with all reasons, instead of being flattened to missing. Include both axes'
trace-occupied count inputs and native boundary endpoints in the gap-run cell
inputs, in addition to the string count operands. This makes actual coordinate
and length-bound prerequisites explicit and adds to002's operand list. A single
usable block needs no coordinate-boundary proof for its gap-run count.
