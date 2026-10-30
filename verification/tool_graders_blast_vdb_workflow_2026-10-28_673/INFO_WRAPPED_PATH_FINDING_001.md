# Retained authentic info path-field defect

The original `info` Workflow check closed terminal/quiescent with rc0, and its
current assertions passed. This does **not** establish the complete selected
path's semantic correctness: review of the retained verification values found
wrapped path fragments returned as complete selected/resolved path values.
No operation-link proposal for `native.blast_vdb_cmd.info` is made here.

The original attempt is
`verification/tool_graders_hmmer_map_verification_2026-10-28_529/check131_vdb_workflow673_info`;
its unit is `gene-local-job-551215dd4b28475095828125dd0e6a80.service`.
Its original CASE and Store are beneath
`temporary/pytest/vdb-workflow673-info0`. Preserve that directory and original
receipt; any repair must use retained native evidence instead of repeating the
helper. The measured full test call was 615.2627529650927 seconds.

The helper executed once and returned 0. Original stdout is 423 bytes, SHA256
`cb65d0f9b71a60a74dcbabb602dcd86cdc29e6b5d65c2d0ec3d7c7235c174e0a`.
`VERIFIED_VALUES.json` records this exact retained native lexeme for both
`vdb_selected_inputs` and `vdb_resolved_paths` (leading space/newline preserved
in the JSON):

```text
 
/home/chia/repos/gene_annotation_episode/verification/tool_graders_blast_vdb_
fixture_acquisition_2026-10-28_658/retained/fixture/ERR3487613
```

The returned field values are two strings:

```json
[
  "/home/chia/repos/gene_annotation_episode/verification/tool_graders_blast_vdb_",
  "fixture_acquisition_2026-10-28_658/retained/fixture/ERR3487613"
]
```

The actual selected absolute operand is their concatenation, one path. Neither
fragment is an additional selected archive or resolved path. Both returned
fields have `missing_reason=null` and `value_basis=native_reported`. The latter
field's declared unit is `paths`; the former's is `native_input_tokens`.

The exact parser interface is
`gene_annotation_episode.blast_vdb_utility_inputs._vdb_info(text, oid)`, whose
`close()` joins each native block with newlines and sets `value=lexeme.split()`.
`parse_blast_vdb_inspection` publishes those fields with complete status when
no other failures occur. The contract's `_FIELD_TYPES` in
`blast_vdb_utility_contracts.py` means "Selected invocation strings" for
`vdb_selected_inputs` and "Resolved VDB selection" for `vdb_resolved_paths`.
Its info validator checks typed fields and duplicate/conflict relationships,
but does not identify this wrapping ambiguity. The test's list assertion also
mirrors `native_lexeme.split()`, so its pass cannot prove that semantic claim.

Valid retained results remain useful: native sequence count is 20; total
unclipped length is 5,000 nt; longest and native integer average are both
250 nt. CSRA inputs, reference sequence count, and reference total bases are
null with `native_field_absent`, not zero. Typed immediate/root admission,
publication equality, context authentication, deliberate artifact grants,
one observation per action, acquisition gain 2, and exact practical future
gain 0 passed. Saved replay preserved the Store and 202 protected files with
execution/acquisition/native parsing forbidden, using the documented existing
canonical-byte read adapter. These successful checks do not erase the defect.

Evidence consists of the original attempt's `receipt.json`,
`case_reports.jsonl`, `execution_audit.json`, and the original case's
`VERIFIED_VALUES.json` and `SAVED_REPLAY.json`. Source/dependency/stdlib/binary
pins were unchanged; no outside modules or unbound mappings were observed;
native files and original 658 fixtures were unchanged. The production defect
has been reported to root, which owns any production repair. No helper retry,
Store rewrite, inferred path, or completion increment is authorized by this
finding.
