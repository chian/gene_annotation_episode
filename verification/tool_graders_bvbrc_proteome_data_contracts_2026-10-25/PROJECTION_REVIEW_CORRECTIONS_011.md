# Saved projection corrections, 2026-10-25

This adds to FACT_CONTRACT_001 and PROJECTION_OWNERSHIP_009. It changes no
scientific formula, native observation, episode behavior, or scope row.

The first projection implementation used a generic number-or-null CellFact
schema. Its actual projector copied validated B4 states, but the field schema
itself permitted a missing/invalid state with a number. The schema now requires
a finite number when state is value and null for all other states. Source
schema semantics remain enforced separately from communication's grammar.

The first implementation also projected every provider-created requirement
with an empty scope. Consequently a missing requested target could attach its
requirement to unrelated available fields. Generated failures now retain actual
track/association/row scope when such a saved target exists. A nonexistent row
does not gain invented saved identity. Independent of that scientific scope,
each generated request failure attaches only to its own requested field, plus
its explicitly requested status field. The all-requirements/qualifications
facts still expose the complete requested set. Existing source requirements
retain their original scope unchanged.

The new projector's public function signatures are unchanged. Exact saved
reprojection still rejects foreign request failures and never reparses native
bytes or calls scientific calculators. The test correction in
projection_pytest_002 was a detached-schema test reaching the old property path;
its failed receipt is retained. Run003 passed120 tests across fact contracts,
saved projection and the provider resolution suite then present. This is
synthetic/pure integration evidence, not service execution or episode admission.
