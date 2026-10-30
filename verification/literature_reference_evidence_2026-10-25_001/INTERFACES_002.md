# Additive precision to interface001 before coding delegation

The calculator signature additionally requires `reference_condition` and
`test_condition`. It must match each selected arm to that exact expected
condition, not simply compare whichever rows share an arm label.

The exact public definitions are in
`gene_annotation_episode/literature_experimental_contracts.py`.
`RATE_UNITS` supplies physical dimensions and explicit base-unit multipliers.
`RATE_UNIT_ALIASES` performs only declared spelling normalization; raw units
remain in the source row. Unknown amount/concentration relationships never
create a reaction volume.

Duplicate representation identity is `(source_ref,artifact_ref,row_number)`.
Identical numeric values in different source rows do not establish identity.
The calculator may collapse exact repeated copies of one identity only after
checking the complete row is identical. Conflicting values under one identity
produce an unavailable conflict result. Several different identities selected
for one arm are unresolved repeated summaries; do not average or infer sampling
relationships. Preserve the full raw rows for repair.

These are source-level statistics and summaries. They do not yet implement
all source-evidence scoring components. `annotation_credit` and
`molecule_specific_product_rate` remain null in this un-attributed rate route.
Neither null is a zero, and neither is used to stop an episode.
