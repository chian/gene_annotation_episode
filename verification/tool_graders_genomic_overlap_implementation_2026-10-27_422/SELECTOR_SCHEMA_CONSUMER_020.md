# Selected-result schema consumer

Additive 2026-10-27 refinement of 019. The pure information module also exports
`genomic_overlap_result_selector_schema() -> dict`. It returns the unchanged G1
Selector and only definitions reachable from that selector, with a local `$id`
so references remain valid when embedded in the results assignment schema.
It does not carry unrelated sheet, component or worker definitions into the
commissioning contract. It changes neither accepted operands nor scientific
calculations.

Both `describe_genomic_overlap_result` and
`ExecutionEpisodes.assignment_schema('results')` consume that same helper.
Workload 438 owns the helper and its pure validation tests. Root owns the
assignment-schema consumer; workload 437 verifies actual commissioning through
the shared Workflow. Pure schema tests alone do not establish that integration.
