# U06 source and consumer findings

Read-only planning evidence,2026-10-26. The accompanying SOURCE_PINS_001.json
records the examined current files. Line numbers below describe that snapshot;
historical reports are not proof of current implementation.

## Exact defect and original boundary

1. `research/tool_grader_goal_2026-10-24/PROGRESS_UPDATE_081.json`, work_item_states
   U06, explicitly retains the native-path versus semantic-census equality gap.
   U03/live native input and resource coverage remains separate; U05 keeps all
   remaining fixed 308 rows. This planner changes none of those records.
2. 327/PROPOSED_PLAN_001.md, lines317–328 and1093–1097, explicitly froze the
   initial limitation. It requires original native path/semantic identity to
   remain separate and calls for a separately reviewed association-aware
   scientific sheet before naming-case population correction is available.
3. 302/SHARED_SEQUENCE_PORT.md and 303/CONTRACT_001.md establish the existing
   sequence-target-only adapter and original optional calculation_context.
   They prohibit rewriting native request fields and retain release/scope/count
   qualifications. U06 is a narrow extension to that exact boundary.

## Current source path

| Relevant implementations and consumers examined | Actual finding / consumer |
| --- | --- |
| blast_report_collection.py, JSON search construction and tabular section parsing | JSON search_target.db and table Database header remain literal normalized.search.database. The parser does not authenticate semantic population identity. |
| blast_database_grader.py: _calculation_context, _database_profile, _build_database_sheet, build_database_sheet, calculate_database_probabilities | _database_profile lines795–800 compare original database/db with identity.value. Profile database/release/scope/count unit and counts are separately checked. calculate_database_probabilities consumes saved group masses and database_representation; formula and row names need no change. |
| blast_sequence_database.py: _validate, populate_blast_sequence_database_sheet, _admit, _rows, calculate_blast_sequence_database_components | Exact source/native equality in _admit protects original fields. At line642, the calculator passes only reporting and semantic database_identity. There is no supplied association port. _rows constructs full original SearchKey locators. |
| native_blast_standard_database_metadata.py: _resolve, _prepare_metadata, derive_standard_blast_database_search_binding, qualify_standard_blast_sequence_metadata, populate_standard_blast_database_sheets, saved metadata/sequence/sheet validators | Derivation accepts exact joined native_paths or identity.value at line824, then retains the explicit population-equality-unproven issue at852. Sequence metadata only passes the old profile. Saved validators enforce exact old sheet keys/schema and must receive a new explicit branch. |
| native_blast_database_metadata.py: schemas/registry, _lower_payload, validate_native_blast_database_metadata_payload, prepare_native_blast_database_inputs, _derive_binding, _sequence_units, populate_native_blast_database_sheets | Native-six _derive_binding already accepts operand or semantic spelling. PSI/DELTA sequence metadata flows both to direct saved sequence sheets and iteration.sequence_metadata; both handoffs must retain the new relation. Existing source/descriptor/document custody is reusable. |
| blast_iteration_inputs.py: _validate, populate_blast_iteration_sheet; blast_iteration_calculators.py: _roles, _stage, _dependency, _search, calculate_blast_iteration_components | Exact sequence_metadata key sets and v2-only target_contexts conditions need a new explicit v3 branch. _dependency forwards metadata into the sequence populator and is the actual PSI/DELTA calculation path. Direct saved sequence population alone would not fix integration. |
| native_blast_standard_database_contracts.py: database schemas, _database, registry, validation, _compile | One selected declared population can have an ordered list of native paths. `-db` is the exact joined list. Standard metadata tuple enum is closed; adding only a shared registry entry is insufficient. |
| native_blast_database_result_worker.py: _sheet_binding, calculate_native_blast_database_sheets, _sequence_rows, _sequence_quality_source, _implementation_modules, _reuse | PSI/DELTA calculations come from iteration. The new association needs saved source validation on this path. _sequence_quality_source currently requires inner sheet v2 for a record locator; v3 must preserve that verified relationship. Worker source closure must include the new modules. |
| native_blast_standard_database_calculators.py: _calculate and _sequence_rows; result_worker.py: request/descriptor definitions, implementation closure, _reuse | Standard uses the direct sequence calculator. Numeric rows copy current weights/counts. Its saved validator is called before calculator use. Descriptor enums derive from contracts; implementation closure has an explicit module list. |
| native_blast_database_result_publication.py: source authority, module list, _request, saved request branch; standard publication: source authority, _request and worker module acquisition | Captured input authority is episode-receipt-based. Native-six has an explicit host scientific module list in addition to worker closure. Both ordinary sequence host requests use reuse=None;347's episode-accessible saved selector belongs to VDB only. |
| Both result_views selectors, tool_info construction and result row projections | Standard selector descriptors derive from its contracts tuple list. Native-six sequence_database consumer already permits an explicit schema_id. Existing numerical families and no-confidence claims remain suitable; no new return family or observation score is needed. |

No installed capability is inferred from any descriptor or inventory entry.
The seven affected rows retain their separate authentic native/live-resource
qualifications. Resource routing remains the selected HPC child. Pure parsing/
calculation on retained bytes is not a local database BLAST execution.

## Why338/350/347 are preserved

Read338's census section, accepted contract/addenda001–008 and acceptance;
350 HANDOFF_001/ROOT_REVIEW_001 and the complete current _census_issues;
347 HANDOFF_001 plus selected trace passages. Relevant source facts:

- `native_blast_database_metadata._vdb_dataset_matches` validates a dataset's
  selected path against selected native_paths, or its accession/alias value
  against selected semantic identity. It separately checks manifest/release
  facts and selected filters. It does not call _database_profile.
- `blast_vdb_function_inputs._census_issues`, lines706–735, compares explicit
  dataset keys, identifier, selected_input, nonempty snapshot and filters.
  The identifier and selected_input are separate fields already. A path in the
  selected_input field is not compared with identifier.value.
-338 requires exact selected dataset set and selection controls for correction.
  Its full enumerated targets, annotation snapshot, identity proofs and source
  dependence graph have different meanings from the sequence census profile.
-350 preserves optional dependency uncertainty and rejects contradictory actual
  sample relations. None of those rules establishes a path-to-population alias.
-347 reports synthetic selected-child/worker/requested-return evidence and
  explicitly leaves authentic VDB execution/deployment separately unverified.
  Its packet and source were read-only for 361. A failed broad run remains a
  failed historical run; later targeted passes do not erase it.

Thus changing VDB census equality to repair the shared sequence naming defect
would weaken a different scientific contract. The proposed affected-mode list
is based on actual consuming functions, not a generic BLAST label.

## Verification not performed by this planner

No production code or tests were written or changed; no test suite, native
analysis, API call, acquisition, installation or model request was executed.
Numerical fractions in PLAN_001 are algebraic proposed oracles using the existing
kernel, not claimed runtime results. Only planning files under361 were created.
No status/inventory or fixed row was changed. Full authority text/current AGENTS,
episode/time/practical documents and TASK_AND_STEERING were read; the immutable
purpose and all sixteen principles were reread before formulating the proposal.
