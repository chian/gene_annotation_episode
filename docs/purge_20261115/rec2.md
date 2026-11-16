# rec2 — a101 brought to the state of the closed arms (15 November 2026)

Area: `gene_annotation_episode/episodic_workflow/root/a101/` (`A` below). Start: checkpoint e5c5ff9b6, a101 unmodified.
No sub-agents, one launcher command at a time (slot `rec2`), no git add/commit.

## 1. Result
- `Workflow` accepts only `wait_inputs_binding_v2`, `completed_action_inputs_binding_v1`, `received_progress_order_v1`,
  the owned branch lifecycle and the current root action boundary (constructor defaults); reopening a run whose saved
  settings lack them raises the existing `unsupported_*` errors (`A/runtime.py:1005-1038,3643-3650`).
- `pending_work_after_action` is written unconditionally; only `execution_status_v2` is accepted; no `unproven_replay`,
  `_unproven_direct_response_index`, `recorded_transport`, old assignment decoder or non-owned report delivery remains.
- Every registration requires `binding_path` and `commissioning_parent` (`A/episode_bindings.py:153-160`); all 40 binding
  homes declare both (the other three `episode.py` files define no binding).
- Transport rule kept as in a104/a107: `_recorded_assignment_transport` (`A/runtime.py:311-319`) accepts a
  decision-exchange request saved without the proof and refuses a direct request without a valid one. Writers:
  exchange request `A/runtime.py:752` (protocol marker, no proof), direct request `A/runtime.py:764-767` and the same
  lines in the 42 home files that save a direct request.
- Size against the checkpoint: 206 product Python files edited (+687 / -1,581 lines), 33 test Python files edited
  (+63 / -198), 3 files deleted by me (2 `library/*.ownership.json`, 1 test file). Two fixture files under
  `tests/fixtures/masking_native/` (`ORACLE_CASES_001.json`, `ORACLE_MANIFEST.json`) were deleted by another agent while
  I worked; no Python file names them.

## 2. Method
- Same-path twins: `git merge-file --diff3` per file, base = twin at a0d9f1666 with the arm name replaced, ours = a101,
  theirs = twin now. a104: 108 files (65 clean and applied after reading the whole diff, 7 already equal, 36 with
  conflicts resolved by hand; in most of those a101's side already carried the change). a107 on top: 148 files.
- Because a101 keeps many modules under `library/` that the other arms keep at their top level, I repeated the merge
  with the closest same-named file of any arm or of the shared root (`library/` and top-level files: 254 candidates,
  35 clean and applied; home files against a104 and a107: 758 candidates).
- For conflicts I replayed the twin's edit script onto a101's text where its base lines occur verbatim exactly once,
  and listed every twin-removed line still present in a101 (about 60 conflict regions, with repeats); each was read and either applied by
  hand or recorded in section 5. Scripts: scratchpad `rec2/{merge,merge2,merge3}.sh`, `autoresolve.py`, `leftover.py`.
- a101-only shapes (runtime structure, `child_exchange` / `scientific_admission` tuples, `admit_unowned_return`,
  `for_context_role`, `process_state.py`, `decision_waiting.py`, `received_outcomes.py`) were edited by hand.

## 3. Removed (product code; lines / files at the checkpoint -> now)
| item | before | now |
|---|---|---|
| `wait_inputs_version == 'wait_inputs_binding_v2'` branches | 47 / 45 | 0 |
| `completed_action_inputs_version is None` / `in {None, ...}` | 47 / 44 | 0 |
| `wait_inputs_binding_v1` | 3 / 1 | 0 |
| `unproven_replay` | 45 / 44 | 0 |
| `_unproven_direct_response_index` | 84 / 84 | 0 |
| `recorded_transport` | 86 / 43 | 0 |
| `_legacy_episode_assignments` and the old decoder in `_decode_recorded_action_response` | 12 / 1 | 0 |
| `legacy_grouped_v1` (and the SQL path that rebuilt progress order) | 2 / 1 | 0 |
| `episode_branch_lifecycle ==` branches | 31 / 23 | 0 |
| `episode_branch_lifecycle !=` early returns | 4 / 1 | 1 (the constructor refusal) |
| `execution_status_v1` (schema alternative, credit reader) | 2 sites | 0 |
| `admit_unowned_return` (22 functions) and the `owned` flag | 73 / 26 | 0 |
| path-less binding lookups (`binding_path is None`, `getattr(..., 'binding_path', None)`) | 8 / 1 | 1 (the registration check) |
| `scientific_process_episodes_v5..v9` descriptor versions | 4 / 1 | 0 |
| name-only tool library (`supports_tool_info`, `resolve`, `retrieve`, `freeze(tool_info=)`, `VERSION` v1, v1 retrieval request and instructions) | 11 / 6 | 0 |
| `window_size` / `subsample_size` (numerical.py, runtime.py) | 10 / 2 | 0 (39 lines left are the vendored estimator and BLAST option names) |
| table upgrades (`ALTER TABLE`, `PRAGMA table_info`) | 7 / 4 | 1 (see section 4) |
| `restore_saved_process` and the saved-implementation projection in `restore_closed_process` | 3 files | 0 |
| `include_identities` / `wait_inputs_v1` / `WaitInputsV1` | 7 / 2 | 0 |
| retired count limits in `local_resources.py` (`max_running_jobs`, `cpu_threads`, `_saved_limits`) | 1 file | 0 |
| `root_action_boundary` accepting `None` | 1 | 0 |

Also removed, each following the edit a closed arm or the shared root made to its copy: old never-dispatched handle
tolerance and optional `cpu_quota_percent` / `capacity_reservation` in `native_lifecycle.py`; `files_to_stage` in
`hpc_result_receipts.py`; standard-database `calculations_v1` and worker manifest v1 (3 modules); BLAST grading
`*_grading_v1` and `archived_values` reads (`native_blast_hsp_views.py`, `native_blast_result_publication.py`); markerless
pairwise results (`library/biopython_pairwise_grader.py`); the hmmsim incomplete-record tolerance
(`library/native_hmmer_preparation_contracts.py`); `include_map_context`; uncapped download identity
(`library/bvbrc_appservice_{contracts,readers,bundle_values}.py`, `api_bvbrc_appservice.py`); the array/header response
form of the BV-BRC data decoder (`library/bvbrc_data_{readers,views,fields,schema}.py`); assignments without
`resource_id` (`execution_progress.py`); table-existence tolerance in `local_return_history.py`; `ungraded` alignment
results (`library/alignment_site_action_records.py`, `alignment_site_native.py`); `parse_uniprot` and
`uniprot_pagination` in `acquisition.py` (no caller); `_sequence_symbols`; the old sealed worker-request form in
`native_hmmer_preparation_result_publication._worker_selection`; `commissions.failure` column upgrade
(`method_loop/durable.py`); about 30 narrating comments and docstrings; 2 `library/*.ownership.json`.

Product changes that are stricter than a104 (say if any should be relaxed): `root_action_boundary` must be current
(as a105); `capacity_reservation` is required on a submitted handle (as a107); `restore_saved_process` and the
implementation-hash substitution in `restore_closed_process` are gone (as a107); the `durable.py` column upgrade is
removed although all other arms still carry it.

## 4. Kept as live (current writer)
- Run settings: `A/runtime.py:3830-3834` writes all five versions on every new run.
- `execution_status_v2`: `A/method_loop/durable.py:638`.
- Transport proof and protocol marker: `A/runtime.py:752,764-767`.
- `orders.search_mode` in `A/homology_jobs.py:131`: added at creation when the caller supplies search modes
  (`create`, line 130); not an upgrade of an existing table.
- `native_blast_database_result_worker_manifest_v1` / `_v2`: per-program forms, both written at
  `A/native_blast_database_result_worker.py:540`.
- `legacy_uniprot_records`: `A/tools.py:2272`.
- `provider_jobs.py:24` `unsupported_historical_hmmer_request`: label of a refusal; nothing older is accepted.
- Three tests hash product module files (`tests/test_native_blast_database_result_worker.py:210`,
  `test_native_blast_standard_database_result_worker.py:21`, `test_private_native_implementation_dependencies.py:24`)
  to build a worker request for `_verify_implementation` (`A/native_blast_database_result_worker.py:308`,
  `A/native_blast_standard_database_result_worker.py:115`), which is current code.
- `tests/fixtures/bvbrc_original/verification/...`: captured BV-BRC service responses read by
  `tests/test_api_bvbrc_data_v2.py:33` and `test_bvbrc_data_readers.py:19`; both files pass (26 and 70).
- `tests/test_hmmer_artifact_data.py`, `test_native_blast_masking_results_616.py`, `test_native_hmmer_publication.py`
  hold no tests but are imported as helpers by five test files.

## 5. Remains and why
1. Thirteen readers still treat `pending_work_after_action` as optional when comparing a saved action result
   (`local_file_capture_results.py:225`, `api_service_execution.py:860`, eleven `library/retained_input_authority/*`
   receipt and request-binding modules). a104 has the same; the shared root made `local_file_capture_results` strict.
   I did not establish for each reader that every row it reads is written by a path that adds the field.
2. `shared_information.py:91` infers a recipient for records that do not name one (same in a104 and a107); writers at
   lines 215, 223 and 242 name it. Not removed: the no-parent case was not traced.
3. Self-hashing (`implementation_sha256`, `binding_record.py` source lists): 107 lines in 58 files, the same order as
   a104 (141 / 65) and a107 (125 / 68). Not part of this step.
4. `LEGACY_EVIDENCE_SLOT` (`A/scientific_process_records.py:25` and 21 more lines): the completeness check found no
   writer and left the choice to the owner; untouched.
5. Error codes and field names containing `legacy` (`legacy_preparation_context_forbidden`, `legacy_custody_variant`,
   `legacy_nonnegative_difference_percentage_points`): names of current records, not removed.
6. `docs/`, `knowledge/`, `*_instruction_library/` Markdown: not swept.

## 6. Tests changed with the step
- Stub workflows supply `pending_work`: `scientific_process/tests/test_scientific_task.py:32`,
  `tests/test_literature_task_connections.py:33`, `tests/test_operational_task_connections.py:36`, two
  `execution_progress_assessment/tests/test_progress_task.py`.
- Saved direct request carries the proof: `tests/bvbrc_controlled_saved_records.py:84` (default `encoded=True`).
- `freeze(tool_info=True)` dropped (5 files); `YieldParameters(100, 50)` -> `YieldParameters()` (5 files);
  calculator stubs accept `_retain_correspondence` (3 sites); the feature-sequence fixture builds the Solr envelope.
- Seven assertions about where code lives removed from five test files (the tests stay).
- Deleted: 1 file and 6 tests or parametrised cases, `rec2_deleted_tests.tsv`.

## 7. Earlier deletions checked
95 a101 test-tree Python files were deleted between a0d9f1666 and the checkpoint (71 outside `fixtures/`). 70 have a
recorded whole-file reason; `tests/blast_pairwise_fixture.py` is a helper whose users' tests are listed. None had
tests as methods of a class. The three rows that say "0 tests removed, none left"
(`test_hmmer_alignment_input_native_oracle`, `test_native_hmmer_preparation_result_worker`,
`test_native_hmmer_preparation_returns`) depended on the deleted saved check-run fixtures
(`hmmer_preparation_capture/check005`, `RETAINED:check002`) through imported helpers. Nothing restored.

## 8. Verification
Run:
- Import check over all 1,872 a101 product modules: `{}` (`runs/claude_rec2_008`, after the last product edit).
- Collection of all a101 tests: 9,808 collected, 0 errors (`runs/claude_rec2_009`).
- Every a101 test file once, one launcher run per file (`runs/claude_rec2_g1_*`, 272 files, 1,124 s); 17 files run
  again after fixes (`g2_*`, `g3_001`). Latest result per file: `rec2_gate_results.tsv`.
  Totals over 271 files: 9,284 passed, 286 failed, 178 errors, 60 skipped; 232 files pass, 3 hold only helpers (no tests), 36 have failures.
- Per-test comparison with the junit files of the last full runs (`runs/claude_tests_final_2026111*`, tree
  a0d9f1666; `runs/claude_rec2_cmp2`): 0 tests that passed there fail now; 0 failing tests are new. 9,804 of the 9,808
  tests existed there with 9,198 passed / 368 failed, so 82 that failed then pass now.
- No a101 test fails inside the shared stubs under `root/tests/`: the nine per-home
  `execution_progress_assessment` test files pass (73 tests).
Read only: the writer of each kept form (section 4); that removed names have no user outside a101 (grep over
`gene_annotation_episode/`, `tests/`, `tools/`); the reasons of the earlier deletions.
Not measured: results at the checkpoint itself. The comparison baseline is a0d9f1666; the six files the earlier
agent reported after its passes have the same or better counts now.

## 9. Files with failures (all failed or errored the same way at a0d9f1666)
| file | failing now (baseline) | most frequent cause |
|---|---|---|
| `tests/test_blast_archive_member_digest.py` | 2 (failed 2, error 0; at baseline failed 2, error 0) | 2x assert {'schema': 'b... 'json2', ...} == {'schema': 'b... 'json2', ...} |
| `tests/test_blast_binding.py` | 5 (failed 5, error 0; at baseline failed 5, error 0) | 2x AssertionError: assert (1 == 0) |
| `tests/test_blast_native_iteration_records.py` | 1 (failed 1, error 0; at baseline failed 1, error 0) | 1x AssertionError: assert {'origin': 'n...RGED!\n', ...} == {'origin': 'n...RGED!\n', ...} |
| `tests/test_blast_preparation_publication_653.py` | 19 (failed 19, error 0; at baseline failed 19, error 0) | 19x ValueError: native_blast_utility_original_driver_request_conflict |
| `tests/test_blast_report_collection.py` | 1 (failed 1, error 0; at baseline failed 1, error 0) | 1x AssertionError: assert [{'hit_index'...{}, ...}, ...] == [{'hit_index'...{}, ...}, ...] |
| `tests/test_blast_utility_capture_semantics_638.py` | 1 (failed 1, error 0; at baseline failed 1, error 0) | 1x ValueError: native_blast_utility_original_driver_request_conflict |
| `tests/test_blast_utility_collection_repair_659.py` | 5 (failed 3, error 2; at baseline failed 3, error 2) | 3x ValueError: native_blast_utility_original_driver_request_conflict |
| `tests/test_blast_utility_episode_wiring_632.py` | 24 (failed 24, error 0; at baseline failed 24, error 0) | 14x AttributeError: 'ExecutionEpisodes' object has no attribute 'fact_sources' |
| `tests/test_blast_utility_result_views_629.py` | 1 (failed 1, error 0; at baseline failed 1, error 0) | 1x AssertionError: assert {'artifacts',...missing', ...} == {'artifacts',...missing', ...} |
| `tests/test_blast_vdb_episode_consumers_671.py` | 32 (failed 32, error 0; at baseline failed 32, error 0) | 21x AttributeError: 'ExecutionEpisodes' object has no attribute 'assignment_schema'. |
| `tests/test_blast_vdb_function_census_relations.py` | 25 (failed 25, error 0; at baseline failed 25, error 0) | 24x AssertionError: assert {'schema': 'b...', ...}], ...} == {'feature_com...2}, ...}, ...} |
| `tests/test_blast_vdb_native_context_668.py` | 1 (failed 1, error 0; at baseline failed 1, error 0) | 1x ValueError: native_blast_utility_original_driver_request_conflict |
| `tests/test_bvbrc_homology_tool_info.py` | 11 (failed 11, error 0; at baseline failed 11, error 0) | 9x ValueError: appservice_adapter_implementation_conflict |
| `tests/test_hmmer_alignment_input_episode_path.py` | 9 (failed 9, error 0; at baseline failed 9, error 0) | 9x TypeError: episode_service_factory_must_return_EpisodeApplicationServices |
| `tests/test_hmmer_alignment_map_context.py` | 5 (failed 5, error 0; at baseline failed 5, error 0) | 4x AssertionError: assert (['map'] == ['reader', 'map'] |
| `tests/test_hmmer_alignment_map_episode_path.py` | 3 (failed 3, error 0; at baseline failed 3, error 0) | 3x TypeError: episode_service_factory_must_return_EpisodeApplicationServices |
| `tests/test_hmmer_alignment_native_weight_oracle.py` | 57 (failed 0, error 57; at baseline failed 0, error 57) | 57x failed on setup with "Failed: HMMER_NATIVE_ORACLE_EASEL_DIR must name an explicitly staged native verification |
| `tests/test_hmmer_model_format_workflow.py` | 2 (failed 2, error 0; at baseline failed 2, error 0) | 2x method_loop.durable.DurableExecutionError: unavailable_binding (path root_execution_job_submission) |
| `tests/test_native_blast_database_acquisition.py` | 5 (failed 5, error 0; at baseline failed 5, error 0) | 5x ModuleNotFoundError: No module named 'test_native_blast_database_episode_binding' |
| `tests/test_native_blast_database_tool_info.py` | 1 (failed 1, error 0; at baseline failed 1, error 0) | 1x AssertionError: assert [{'descriptio...hpc'}]}, ...}] == [{'name': 'na...turns.', ...}] |
| `tests/test_native_blast_masking_invocation.py` | 5 (failed 5, error 0; at baseline failed 5, error 0) | 4x AssertionError: actual invocation must use bounded529 runner assert None |
| `tests/test_native_blast_masking_workflow.py` | 12 (failed 0, error 12; at baseline failed 0, error 12) | 12x failed on setup with "method_loop.durable.DurableExecutionError: unavailable_binding" (path root_execution_job_submission) |
| `tests/test_native_blast_preparation_649.py` | 1 (failed 1, error 0; at baseline failed 1, error 0) | 1x ValueError: native_blast_utility_original_driver_request_conflict |
| `tests/test_native_blast_standard_database_acquisition.py` | 6 (failed 6, error 0; at baseline failed 6, error 0) | 6x ModuleNotFoundError: No module named 'test_native_blast_standard_database_episode_binding' |
| `tests/test_native_blast_standard_database_tool_info.py` | 1 (failed 1, error 0; at baseline failed 1, error 0) | 1x assert [{'descriptio...rces': 'hpc'}] == [{'name': 'na...ic episode.'}] |
| `tests/test_native_blast_utility_practical_630.py` | 28 (failed 28, error 0; at baseline failed 28, error 0) | 27x ValueError: native_blast_utility_original_driver_request_conflict |
| `tests/test_native_blast_utility_producer_628.py` | 23 (failed 23, error 0; at baseline failed 23, error 0) | 23x ValueError: native_blast_utility_original_driver_request_conflict |
| `tests/test_native_blast_utility_workflow_634.py` | 3 (failed 0, error 3; at baseline failed 0, error 3) | 3x failed on setup with "method_loop.durable.DurableExecutionError: unavailable_binding" (path root_execution_job_submission) |
| `tests/test_native_blast_vdb_function_metadata.py` | 5 (failed 5, error 0; at baseline failed 5, error 0) | 2x AssertionError: assert {'schema': 'b...0, ...}], ...} == {'assignment_...', ...}], ...} |
| `tests/test_native_hmmer_preparation_local.py` | 14 (failed 14, error 0; at baseline failed 14, error 0) | 14x ValueError: native_hmmer_preparation_original_driver_request_conflict |
| `tests/test_native_hmmer_preparation_nested_workflow.py` | 76 (failed 6, error 70; at baseline failed 6, error 70) | 70x failed on setup with "method_loop.durable.DurableExecutionError: unavailable_binding" (path root_execution_job_submission) |
| `tests/test_native_hmmer_preparation_result_publication.py` | 26 (failed 1, error 25; at baseline failed 1, error 25) | 25x failed on setup with "ValueError: native_dependency_unavailable" |
| `tests/test_native_hmmer_preparation_tool_info.py` | 2 (failed 2, error 0; at baseline failed 2, error 0) | 1x AssertionError: assert 'unsupported' in 'Convert supplied profile HMMs to native HMMER binary format. |
| `tests/test_native_hmmer_preparation_workflow.py` | 36 (failed 36, error 0; at baseline failed 36, error 0) | 36x TypeError: episode_service_factory_must_return_EpisodeApplicationServices |
| `tests/test_native_mask_conversion_640.py` | 7 (failed 7, error 0; at baseline failed 7, error 0) | 7x ValueError: native_blast_masking_original_driver_request_conflict |
| `tests/test_native_mask_conversion_workflow_641.py` | 9 (failed 0, error 9; at baseline failed 0, error 9) | 9x failed on setup with "method_loop.durable.DurableExecutionError: unavailable_binding" (path root_execution_job_submission) |

## 10. Handoffs
Written: none (no removed name is used outside a101). Addressed to a101 and applied: row 353 (`freeze(tool_info=)`),
row 369 (delete `test_original_protein_form_contracts.py`), rows 415-417 from rec1 (run-setting reads, non-owned
lifecycle and `admit_unowned_return`, `execution_status_v1`).
