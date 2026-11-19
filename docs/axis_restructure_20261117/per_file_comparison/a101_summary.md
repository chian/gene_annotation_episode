# A101 per-file comparison with the 7e662ea29 baseline (18 November 2026)

Scope: the 267 rows of `docs/verification_20261116/results_per_file.tsv` under
`gene_annotation_episode/episodic_workflow/root/a101/` (9,963 tests: 9,439 passed, 286 failed, 178 errors, 60 skipped).
Per-file table: `a101.tsv` (counts are tests/passed/failed/errors, from each run's JUnit totals as in the baseline).

Run: every current file in its own launcher process (slot `pf101`, `eatmydata`, empty HOME, blocked proxy), 185 files,
`runs/pf101_cmp/results.tsv`, JUnit per file in `runs/pf101_cmp/f_NNNN/junit.xml`. Outcomes were compared per test id
with the baseline JUnit files (`runs/claude_f4a_s0..3/junit`), not only per count. Comparison inputs and scripts:
`runs/pf101_cmp/analysis/`.

## Counts per status

| status | files | baseline t/p/f/e | current t/p/f/e |
|---|---|---|---|
| same | 137 | 5842/5748/37/57 | 5842/5748/37/57 |
| changed | 39 | 2134/2087/45/0 | 1803/1801/2/0 |
| retired | 80 | 1737/1415/168/96 | - |
| retired-unrecorded | 11 | 250/189/36/25 | - |
| regression | 0 | | |

- same: identical test ids and identical outcome per id. The 94 tests that still fail or error in these files (37 + 57)
  have the same first message line as at the baseline.
- changed: 331 cases removed; every removed function has a record row (fake-test rows in
  `runs/claude_ablate/a101_fake_tests.tsv` / `a101_more_fake_all.tsv` / `a101_more_fake2.tsv`, retirements in
  `runs/claude_ablate/a101_retired.tsv` and `docs/axis_restructure_20261117/retired_tests.tsv`). 42 of the removed cases
  were failing at the baseline. Every remaining id keeps its baseline outcome, with one exception (next section).
  `test_canonical_workflow_resources.py` is now `tests/test_canonical_workflow_resources_sequence_homology_evidence.py`.
- retired: the file is gone and every baseline case is covered by a record row (cited per file in `a101.tsv`).

## Regressions

None. No test that passed at the baseline fails or errors now.

## One baseline failure now passes, with no record

`test_blast_native_iteration_records.py::test_source_derived_positive_passes_actual_313_and_311_without_search_scope`
(baseline cause `recorded_extractor_module_name_wrong`). The placement code move rewrote the hard-coded extractor module
string at `episode_support/records/similarity_search/sequence_homology_evidence/blast_native_iteration_records.py:450`
to the module's real dotted path, so it now equals the test's `native.__name__`. The move's own runs show it
(`runs/placement_move/a101_before.txt` 40 failed, `runs/placement_move/a101v_tests1` 39 failed) but nothing names it.
The saved convergence record's `evidence.extractor.module` value therefore differs from its baseline value.

## Retired files without a complete record (11 files, 72 unrecorded cases; 38 passed at the baseline)

The other cases of these files are recorded (rows cited in `a101.tsv`).

Real tests of code that still exists (decide: restore or record):

- `tests/test_blast_result_views.py`: 4 cases, all passing at the baseline and after the fake deletions
  (`runs/claude_ablate/a101_s4.tsv`). They run `blast_result_views.read_blast_hsp` over a real Store, ToolRegistry and
  `NCBIBlastService.publish` on an offline snapshot (bounded alignment window with gaps and reverse coordinates;
  unreceived HSP permission; scope and native-record integrity; missing alignment stays unknown). The reader and the
  service still exist under `episode_support/`. The file was dropped when the old runner left the axis: its module-level
  imports of the a101 `episode_bindings` / `episode_services` copies stopped resolving, and those imports served only the
  one fake test.
- `tests/test_blast_utility_episode_wiring_632.py`: 1 case
  (`test_typed_numeric_relationships_and_native_identity_references_are_validated`), passing. It validates the
  blast-utility sequences/status report schemas from `blast_utility_fact_sources()` with `communication.validate_form`;
  both still exist. The file's other imports (`root.execution_episodes`, a101 `episode_journal`, `numerical`,
  `episode_bindings`) were deleted; this test did not use them.

Tests of code that is deleted, where no record names the removal:

- `tests/test_bvbrc_proteome_private_route.py`: 7 cases in 5 functions, passing. Pure checks of A101's BV-BRC
  GenomeComparison route (`get_application_spec` / `prepare_application('GenomeComparison')`, `bind_adapters`). The a101
  copies of `bvbrc_appservice_adapters`, `api_bvbrc_appservice`, `api_service_execution` and
  `library/bvbrc_application_definitions` are deleted; the surviving shared
  `episode_support/acquisition/service_calls/bvbrc_application_definitions.py` declares only Homology. The A101
  GenomeComparison preparation these tests covered no longer exists in this axis.
- `tests/test_homology_progress.py`: 17 cases in 6 functions, passing. `a101/homology_progress.HomologyProgressProvider`
  (status observation, retained log windows, job-dependency records of the private homology family). The module and
  `a101/state.py` are deleted (listed in `runs/claude_ablate/a101_delete_paths.txt`; family described in
  `runs/claude_ablate/a101_needs.md` N5).
- `tests/test_original_inherited_return_guard.py` (2), `tests/test_original_prepared_assignment_guard.py` (2): whole
  files, passing. `a101/episode_return_records.EpisodeReturnRecords` custody checks over the a101
  BindingContext/Store/method_loop copies, deleted with A101's private runner (`a101_needs.md` N12). The files appear
  only in `runs/claude_ablate/old_root_broken_importers.tsv`.
- `tests/test_original_prepared_unicode_guard.py` (3): whole file, passing.
  `library/retained_input_authority/prepared_results.validate_results_preparation` and
  `prepared_record_identity.digest`; the `retained_input_authority` tree is deleted.
- `tests/test_api_bvbrc_data_v2.py`: 1 case (`test_actual_host_assignment_schema_embeds_both_request_versions`),
  passing. Built `APIServiceExecution.__new__` of the deleted `a101/api_service_execution`; same cause as the file's 15
  recorded rows, but this function has no row.
- `tests/test_native_hmmer_preparation_result_publication.py`: 24 cases in 6 functions (1 passed, 23 errors at the
  baseline). `a101/native_hmmer_preparation_result_publication` is deleted.
- `tests/test_native_blast_database_acquisition.py`: 5 cases, all failing at the baseline;
  `tests/test_native_blast_standard_database_acquisition.py`: 6 cases, all failing at the baseline. They reached the
  deleted `capture_*_bundle` modules through `SyntheticHost(tmp_path, monkeypatch)` of deleted top-level test modules.

## In-place edits to surviving tests (same ids and outcomes; no record)

Found by comparing each surviving test function's body with the baseline (`runs/pf101_cmp/analysis/fnbody.tsv`).

- `test_blast_shared_sheet_projection.py`: 4 tests now pass an explicit scope where the baseline passed `scope=None` or
  none, because `blast_result_views.blast_hsp_facts` gained a required `scope` parameter (baseline:
  `blast_hsp_facts(store, references)`).
- `test_native_blast_fact_forms.py::test_all_registered_sources_compile_and_admit`: the two baseline assertions
  (`_compile_form(...) == schema`, `TypedReportContract(...).admit(payload).as_record() == payload`) are replaced by one
  (`boundary.validate_form(payload, schema, resolver()) == payload`).
- `test_blast_preparation_views_650.py::test_stored_list_count_uses_exact_file_subject_and_no_implicit_artifact_grants`:
  one assertion dropped (`NativeBLASTUtilityReturns._references(...) == [SOURCE]`; that module is deleted).
- `test_blast_vdb_capture_failure_674.py`: two tests call a file-local `result_selector` in place of a helper from a
  deleted test module (same arguments).

Seen while tracing the first item, not audited further: `blast_result_views._original_hsp` no longer calls
`validate_standard_blast_database_observation` / `validate_native_blast_database_observation` before raising its
`..._biological_reference_unavailable` error (the two result-publication modules are deleted).

## Current test files with no baseline row (9 files, 29 tests, all pass)

| file | tests/passed/failed/errors |
|---|---|
| `root/a101/sequence_homology_evidence/tests/test_runtime_head_controller.py` | 3/3/0/0 |
| `root/a101/sequence_homology_evidence/tests/test_runtime_head_link.py` | 2/2/0/0 |
| `root/a101/sequence_homology_evidence/execution_job_submission/api_job_execution/tests/test_api_job_receipts.py` | 1/1/0/0 |
| `root/a101/sequence_homology_evidence/execution_job_submission/hpc_job_execution/tests/test_runtime_link.py` | 2/2/0/0 |
| `root/a101/sequence_homology_evidence/execution_job_submission/local_job_execution/tests/test_local_job_runtime.py` | 3/3/0/0 |
| `root/a101/sequence_homology_evidence/execution_result_acquisition/tests/test_result_acquisition_runtime.py` | 4/4/0/0 |
| `root/a101/sequence_homology_evidence/published_evidence_assessment/tests/test_literature_link.py` | 3/3/0/0 |
| `root/a101/sequence_homology_evidence/resource_work_submission/tests/test_resource_work_link.py` | 6/6/0/0 |
| `episode_support/jobs/service_calls/sequence_homology_evidence/tests/test_monitor_commissioned_report_form.py` | 5/5/0/0 |

## Where the records are

- A101's fake-test deletions (452 rows) and runner retirements (21 rows) are recorded only under `runs/`
  (`runs/claude_ablate/a101_fake_tests.tsv`, `a101_more_fake_all.tsv`, `a101_more_fake2.tsv`, `a101_retired.tsv`).
  `docs/axis_restructure_20261117/retired_fake_tests.tsv` has no A101 row and `retired_tests.tsv` has 35.
- `runs/claude_ablate/a101_retired.tsv` row 18 names five files in one cell (glob-discovered cases of deleted homes).
- The fake row for `scientific_process/tests/test_private_scientific_connection.py` names its first test by a later
  name (`test_shared_runtime_constructs_declared_private_scientific_task`; baseline name
  `test_original_runtime_constructs_declared_private_scientific_task`).
- Three files collect no tests now as at the baseline (`test_hmmer_artifact_data.py`,
  `test_native_blast_masking_results_616.py`, `test_native_hmmer_publication.py`); `test_hmmer2_upstream_fixtures.py`
  is kept for its helpers only (its one skipped test is a recorded fake row).
