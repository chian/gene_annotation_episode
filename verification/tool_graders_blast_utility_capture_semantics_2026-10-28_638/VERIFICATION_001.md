# Capture-reporting correction verification — 638/001

The prospective captured-byte discriminator and shared completeness helper are implemented and verified. The frozen implementation contract is unchanged. This records implementation evidence; it does not replace the user goal.

## Changes and consumer trace

- `native_blast_utility_contracts.py` defines the one pure `native_blast_utility_output_completeness(bundle, measured)` authority. Validation accepts exactly the original fields or those fields plus `output_completeness_basis: "captured_bytes"`. A missing field keeps the original complete-on-zero / partial-on-nonzero meaning; validation never inserts the field. Invalid literals and forged occurrence completeness are rejected.
- `native_blast_utility_driver.py` puts the discriminator only in newly created bundles and calls that same helper for measured output occurrences. Missing/unmeasurable outputs remain unknown; nonzero native exits remain failures.
- `blast_utility_contracts.py` adds the three closed failure codes `output_writer_not_closed`, `output_completeness_unestablished` and `native_outcome_unavailable` alongside the existing inventory code.
- `blast_database_extraction.py` distinguishes actual incomplete inventory, unclosed writer, partial/unknown occurrence and unavailable native outcome. The final unclosed native row receives the output-completeness qualification. `_complete_capture` is unchanged and remains conservative for legacy records.
- Acquisition `_selected_files`, `_validate_saved` and original capture validation preserve the original bundle and its optional discriminator. The local reservation, practical operation `_utility_validation`, `_validate_utility_validation` and `_utility_completed_outputs` preserve original custody and require native success for successful practical completion.
- Inspection consumes the common outcome/capture helpers. Preparation preserves native failure separately from captured file inventory; `project_prepared_blast_database` still rejects a failed preparation. Complete capture does not establish database validity or native integrity.
- `qualified_utility_context`, result-worker original parsing and saved projection, publication receipt validation, result views, `NativeBLASTUtilityResults` and `NativeBLASTUtilityReturns` were read through their affected consumers. They preserve original fields/values and selected grants; saved receipt/publication validation does not reparse native outputs. No edits to these consumer files were needed.
- The producer628 failed-output test now expects the explicit captured-byte basis. Root additionally authorized only the stale practical630 assertion correction exposed by verification: expect that same discriminator and complete captured bytes while retaining failed native state, zero practical credit and absent completion proof. The 38 new638 cases verify legacy and prospective meanings, incorrect discriminators/completeness, missing files, writer closure, independent qualifications, partial final rows, failed preparation rejection and saved-only native diagnostic replay.

## Actual checks

All application imports and tests ran through the existing runner529 with check005 dependencies. Policy: 20 GiB RAM, 4 GiB scratch, zero swap and no wall cap. Native/library/module and retained-fixture audits are clean. No new production change was made after the full-suite snapshot.

| Attempt | Actual result |
| --- | --- |
| check098_blast_utility_capture_semantics | Exit 4; zero tests. The launcher received `tests/` prefixes although it expects basenames. Receipt preserved. |
| check098b_blast_utility_capture_semantics | 472 passed, 1 stale practical630 assertion failed; 354.92 seconds pytest, 358.354017174 seconds service wall time. All 38 new638 cases passed. |
| check098c_blast_utility_practical_assertion | Only the corrected failed test rerun: 1 passed in 3.35 seconds, exit 0. |

Thus all 473 selected case identities have passing verification after the test expectation correction, with the original failed checks preserved rather than rewritten. Full-suite observed scratch was 675,438,592 bytes. Source/dependency/stdlib/binary pins were unchanged for each attempt; module imports and executable mappings stayed within the runner's recorded closure. Exact receipts, per-file counts and current-code pins are in `VERIFICATION_001.json`.

## Concrete outcomes and limits

The retained check096 integrity attempt exited **1**, with a closed writer and complete inventory: stdout **759 bytes**, stderr **0 bytes**. Its legacy bundle still labels both streams partial and its frozen publication still contains the historical `output_inventory_incomplete` failure. Exact saved-only replay under the corrected code returns that original publication unchanged, with native readers, workers and original-path acquisition forbidden.

A controlled new producer reusing those unchanged native diagnostics retains both streams as **complete captured bytes**, preserves native exit **1**, and publishes `native_nonzero_exit` plus `semantic_validation_unavailable`, without false capture/inventory failures. Integrity scope and checked/population counts remain unknown/null. This verifies reporting from real retained diagnostics; it is not a new native execution or a successful integrity check.

A controlled failed database build exits **7** with fully captured family files and complete inventory. Its result remains `compatibility: unverified`, and the requested prepared-database projection is **unavailable**, with no manifest and a `preparation_not_successful` qualification. A partial final sequence row retains its **8** valid symbols while withholding the unestablished effective range and complete-selection claim.

All 28 retained check096 closure files (369,860 bytes) were compared against their original hashes and remain unchanged. The original check096 workflow was not rerun and no database was rebuilt. No network acquisition, model call, local database search or HPC job was performed. Native database-integrity success and unrelated unfinished tool/resource paths remain unverified. Source versions, scoring, credit, continuation, grants and execution choices were not changed.
