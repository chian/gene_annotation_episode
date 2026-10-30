# check049: one initial-custody assertion failure

This records the identified FACS prepared-Workflow assertion defect and its
narrow test correction. It does not claim whole-operation completion or alter
the original user assignment, production behavior, or the running check049.

## Proven cause

The unexpected reference is
`artifact_b28b7e7e6b70661dfee15d5290c4bca097ca145f721c4fbc4de73ad1d1660b8b`.
Its retained file contains exactly the eight UTF-8 bytes `ACGTACGT`, without a
newline. Its SHA-256 is the suffix of that reference. The saved first root and
scientific decision contexts both identify this as the caller's ordinary DNA
target: molecule `dna`, length `8`, unit `nt`, with no child reports yet.

The preexisting fixture explicitly supplies this sequence to
`Store.create_problem(raw_sequence='ACGTACGT', molecule='dna')` and to the
scientific assignment's `context.supplied_sequence`. Its selected scope and
`configuration.initial_refs` include the resulting target input record.
Contract020 explicitly permits the supplied artifacts and the ordinary supplied
target as initial knowledge. The original goal preserves supplied sequences and
their identities; there is no unrequested scientific result involved here.

The exact source path is:

1. `materials.create_problem` registers the raw caller material, parses it, and
   puts the target input's `sequence_ref`, `source_ref`, and material reference
   into the selected subject record.
2. `Workflow.build` passes that selected subject and the explicit configured
   initial references to `EpisodeReceipts.receive(..., kind='initial')`.
3. `EpisodeReceipts.receive` follows `Store._refs` forward references. Both the
   input's `sequence_ref` and caller source's `artifact_ref`/`text_ref` resolve to
   the same eight-byte artifact. Collection members are skipped.
4. `EpisodeReceipts.known(baseline=True)` includes those original initial
   receipts. The scientific child's receipt inheritance freezes the parent's
   prefix, and its assignment independently selects the same target evidence.
5. The fixture's `target_record_refs` query uses `inputs UNION records` before
   Workflow construction. Artifact metadata lives in the separate `artifacts`
   table, so that query omitted this explicitly supplied target artifact.

The expected stored MIME type is `application/octet-stream`: initial material
registration uses `Store.artifact`'s default, and its `INSERT OR IGNORE` preserves
the first metadata row when sequence parsing registers identical bytes as
`text/x-sequence`. This MIME conclusion is from the full source path; the host
did not inspect the database. The bounded saved-case check asserts the actual
stored metadata.

`TRACE_001.json` retains the exact failure record, source/JSON pins, declared
inputs, and target/source relationships. The six inspected production files
match the running check049's frozen source bytes.

## Correction

`tests/fluorescence_prepared_workflow_support.py` now has one `TARGET_SEQUENCE`
declaration used by the existing target construction and scientific assignment.
`assert_initial_input_custody` derives just that declared sequence's artifact
reference from its bytes, requires it to be present, and adds it to the original
bounded upper set of target records and supplied fluorescence files. It never
derives allowed references from actual receipts or all retained artifacts.

The original failing test calls that helper and checks the target record's
sequence reference and exact retained bytes. All other preexisting test
functions, including the no-unrequested-artifact assertions, remain unchanged.
Production source and the check049 snapshot/history were not edited.

## Focused bounded verification for the coordinator

No application imports, tests, database inspection, or native work ran on the
host. Only source/JSON/byte inspection, hashing, and stdlib AST checks ran.
The corrected runtime assertion remains unverified until the coordinator runs
the following selected check after check049 has closed.

Selector:

`tests/test_fluorescence_prepared_workflow.py::test_initial_input_custody_from_closed_saved_case`

Use the existing bounded529 runner with the existing591 dependencies. Supply the
closed original case through `--support-tree`:

`verification/tool_graders_hmmer_map_verification_2026-10-28_529/check049_fluorescence_prepared_workflow/temporary/pytest/fluorescence-prepared595-perform_facs_cell_sorting0`

Supply `--test-env` with this value (the runner expands `{snapshot}`):

```text
HMMER_NATIVE_ORACLE_FLUORESCENCE_SAVED_CASE={snapshot}/verification/tool_graders_hmmer_map_verification_2026-10-28_529/check049_fluorescence_prepared_workflow/temporary/pytest/fluorescence-prepared595-perform_facs_cell_sorting0
```

This test has no `prepared_case` fixture dependency. It reads the copied original
declarations and the original root's initial receipt rows from SQLite opened
`mode=ro&immutable=1`, requiring a yielded root and a checkpointed database. It
does not depend on another test's success marker. The check:

- reproduces the old assertion's exact extra set as the one supplied sequence
  artifact;
- executes the same corrected helper used by the full Workflow test;
- checks the original artifact's stored type, length, hash and bytes;
- rejects an added reference to the actual original result-sheet artifact;
- verifies unchanged database bytes and writes
  `temporary/SAVED_INITIAL_CUSTODY_602.json` in the new bounded attempt.

Expected result: one passed focused test, no new Workflow run, native job,
action, or observation. That is an expectation, not a reported pass.

The historical first full Workflow test remains failed in check049. This saved
check verifies the repaired initial-custody assertion only; it does not claim
that the original test's later numerical/return assertions executed, nor that
the whole operation is complete. The original prepared Workflow selector is
still available if the coordinator identifies a further need to execute it:

`tests/test_fluorescence_prepared_workflow.py::test_real_v2_resource_custody_and_shared_cells_reach_both_parents[facs-prepared]`

## Static verification

AST parsing passes for both edited files. Comparison with the untouched
check049 source snapshot confirms the fixture body and all original tests except
the failing initial-custody assertion function are unchanged. The support
fixture's only behavioral-text substitution is using the identical named target
sequence in its two original input declarations. Final source hashes and the
full changed/unchanged function lists are in `STATIC_CHECKS_002.json`.
