# Scientific process return fixtures

These files are synthetic compatibility specimens, not historical run artifacts
or scientific measurements.

`literal-legacy-form-schema.json` is an exact byte copy of the reviewed planning
specimen at `verification/scientific_process_return_boundary_plan_2026-10-24/literal-legacy-form-schema.json`
(SHA-256 `6db9bce2b5a6526b4f3000166eed409fe3675e72cdcd266e392ec7a261fcd308`).
It independently fixes the original v1 row/v2 selection keys and literal
`annotation_distinction` slot. Tests never build it with current report_sources.

`literal-process-options.json` contains independent invented process bodies.
Tests freeze these with the actual process-library implementation; a separately
created current fixture uses `evidence_axis`. The original fixture bytes are
never rewritten. Tool fixtures likewise freeze explicit synthetic contracts,
with same-name resource variants to test exact pair qualification.
