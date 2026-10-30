# Lane 1 implementation boundary

This lane implements the accepted PLAN and additive contracts 001 and 002 in
`verification/tool_graders_rna_structure_plan_2026-10-26_349/`. Neither fixed RNA
row is complete through this lane. No registration, native execution, Store
binding, prompt, credit or accounting file is owned here.

The four production files were absent before creation. Ownership:

* `rna_structure_contracts.py`: closed input, model shape, topology, native,
  sheet, parameter and component validators; fixed codes; pure sequence
  normalization and association helpers shared by readers and later producers.
* `rna_structure_topology.py`: `parse_rna_topology`, exact nested pair/stem/region
  construction, with no pairing subset for invalid or unsupported input.
* `rna_structure_native.py`: declared JSON/legacy byte readers and the two sheet
  populators. No prose feature reader, native execution or I/O.
* `rna_structure_calculations.py`: the five accepted pure calculation functions;
  separate topology, ordered composition and native energy components.

Consumers are later native worker and result grading lanes. All functions
operate on supplied data only. Structural coordinates, immediate relationships,
original input, unknown versus invalid values, and recorded model identities
follow contract001. Absent native bytes follow contract002. Model shape checks
do not establish executable compatibility or native deployment.

The exact public function signatures are those in contract001 with the
contract002 nullable arguments and pure model shape exports. Additional pure
helpers will be documented in their docstrings. Structure keys produced by
this lane use the original record key plus `:structure`; parsed native keys are
retained and cross-checked against their associated energy records.

Verification uses four dedicated new test modules and full fixture inputs and
outputs in this packet. It runs through `local_jobs.run_local_job`, with
20 GiB RAM, 4 GiB scratch, no wall-time limit, and project Python `-B`.
Synthetic JSON, retained published numeric examples, and any later native or
episode verification remain separate claims. No ViennaRNA installation or call
is part of this lane.

Before native-reader implementation, root was asked to resolve the lack of a
record identity when both inputs are unavailable and in the legacy three-line
format. No synthetic original identity will be invented while that is pending.

## Additive resolution after interface review

Root's planning `CONTRACT_ADDENDUM_003.md` and `CONTRACT_ADDENDUM_004.md`
resolved the preceding pending note. The implemented signatures are:

```python
parse_rna_native_record(raw: bytes | None, *, format: str, expected_mode: str,
    record_key: str, expected_sequence: str | None = None) -> dict
parse_biomni_rna_prediction_text(raw: bytes, *, record_key: str,
    expected_sequence: str) -> dict
populate_rna_prediction_sheet(native: dict, *, record_key: str,
    original_input: dict | None, model_metadata: dict | None,
    subject_binding: dict | None) -> dict
populate_rna_feature_sheet(native: dict, *, record_key: str,
    original_input: dict | None, model_metadata: dict | None,
    subject_binding: dict | None) -> dict
```

The caller passes the original job's record key. Legacy parsing additionally
requires the independently supplied original sequence; the JSON format does
not accept that legacy-only argument. A missing legacy context has its own
`rna_legacy_context_missing` issue. Missing native bytes have null digest and
byte count; actual empty bytes have their actual digest and zero byte count.
All present original/native record keys must agree with the original job key.
An absent native artifact and invalid original container can therefore produce
an invalid sheet with a real job identity and no fabricated scientific fields.

Additional pure helpers exported for later producers/consumers are:
`analyze_rna_input_sequence`, `make_rna_structure`, `sequence_pair_rows`,
`native_uncertainty`, `no_native_uncertainty`, `unavailable_energy`, `issue`,
`validate_rna_issue`, `validate_rna_subject_binding` and
`validate_rna_native_parse`. The accepted input/model/topology/native/sheet/
parameter/component validators and five calculator signatures are unchanged.
The fixed reason vocabulary is `RNA_ISSUE_CODES` with concrete meanings in
`RNA_ISSUE_MEANINGS`; metric sets and units are named constants, not interpreted
formula definitions.

## Additive issue-path validation correction

After check003, root accepted tightening `Issue.field` from closed-root and
escape-syntax checks to the declared nested member grammar and canonical
nonnegative array-index syntax. Unknown child fields and nonnumeric array
indices are rejected. The validator does **not** receive an instance and does
not claim that the addressed field exists or that an index is in range: an
issue may identify an expected missing field. Selection paths use
`/selector/projection/...`; file paths use `/files/{index}/...`. A whole-manifest
failure can have `field=null` and `artifact_role=null`. No new root vocabulary
was added, and earlier receipts remain unchanged.

Root subsequently accepted planning `CONTRACT_ADDENDUM_005.md`. Its exact
SavedRNAInput scalar members are admitted under `/selector/saved_input`, and
the RNAParameters grammar under `/selector/parameters`. Unknown members,
including model-execution parameters in the calculation-only selector, remain
invalid. This only validates diagnostic path names. Actual saved-descriptor,
original-receipt and subject authentication belongs to the delivery host; this
lane neither validates those records nor claims their integration.
