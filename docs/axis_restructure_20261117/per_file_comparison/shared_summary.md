# Shared (non-axis) per-file comparison against 7e662ea29

Compared on 18 November 2026. Scope: the 596 rows of `docs/verification_20261116/results_per_file.tsv` whose path is
not under `root/a101` … `root/a110`: top-level `tests/` (510), `root/tests/` (85) and
`root/execution_monitoring/tests/` (1). One row per baseline file is in `shared.tsv`; current test files with no
baseline row in this scope are in `shared_new_files.tsv`; the dangling-name scan is in `dangling_names.tsv`.

Method. Baseline test ids and outcomes were read from the baseline run's JUnit files (`runs/claude_f4a_s0..3`); they
reproduce the baseline table for all 596 files (two files count subtests in their totals). Every current test file outside the axis folders (428 files) ran in
its own pytest process through `tools/one_workflow.sh --slot pfshred` (`runs/pfshred_run1`, 1,147 s, empty HOME,
proxy to a closed port, loopback excluded from the proxy as in the baseline runner; without that exclusion four
loopback HTTP cases of `tests/test_sequence_support_739.py` fail). Ids were compared test by test; each missing test
was looked up in `retired_tests.tsv` and `retired_fake_tests.tsv` by file and function. Files with no record were
worked out from `git show 7e662ea29:<file>`, the current tree, and a run of a copy of the baseline file from
`runs/pfshred_restore/` (`runs/pfshred_run2`, `runs/pfshred_run3`). No source or test file was changed.

## Counts

| | Baseline | Now (same paths) |
|---|---|---|
| Test files | 596 | 79 (all in `tests/`) |
| Tests | 17,519 | 2,743 |
| Passed | 16,625 | 2,742 |
| Failed | 650 | 0 |
| Errors | 242 | 0 |
| Skipped | 2 | 1 |

| Status | Files | Baseline tests | Tests now |
|---|---|---|---|
| same | 53 | 1,978 | 1,978 |
| changed | 26 | 1,123 | 765 |
| retired (recorded) | 479 | 13,219 | 0 |
| retired-unrecorded | 38 | 1,199 | 0 |
| regression | 0 | | |

All 892 baseline failing tests of this scope are gone, none now passes: 864 were in recorded retired files, 20 in
one retired-unrecorded file (`test_atac_differential_result_receipts.py`), 8 were deleted as fakes from four files
that remain (`test_gzip_prefix`, `test_molecular_sequence_input_bindings`, `test_tool_knowledge`,
`test_durable_episode`).

## Regressions

None. No test that passed at the baseline fails or errors now in a file that still exists.

## Behaviour changes found that the retirement tables do not record

1. `gene_annotation_episode/local_resources.py` was replaced by the unified version: `VERSION` changed from
   `shared_local_resources_v1` to `shared_local_resources_v3`, and a memory limit above the environment bound now
   raises `local_resource_limits_exceed_environment_bounds` where the baseline clamped it. The test that pinned the
   version (`root/tests/test_shared_local_resource_admission.py::test_defaults_and_exact_reopening_have_only_resource_dimensions`)
   was deleted without a record; run from a copy of the baseline file it now fails on the version string.
2. `LocalJobPolicy.from_config` no longer reads packaged defaults: missing `memory_bytes`/`scratch_bytes` raise
   `local_job_setting_required`. `tests/test_local_job_configuration.py` and `tests/test_local_jobs.py` were rewritten
   to match (one test replaced by two; same ids elsewhere with new parameters). An intended removal of a default, not
   written in either table.
3. `Store.reasoning_view`, `Store.references`, `Store.commit_reasoning` and `export_annotation` now require an explicit
   scope. `tests/test_export.py`, `tests/test_state.py` and `tests/test_state_query.py` pass it; their results are the
   same. It belongs to the typed Store scope work (`runs/claude_ablate/contract_done.md`, C1); the test records do
   not mention it.
4. `api_selected_effects`: the top-level module was deleted and the surviving a106 copy has a different interface
   (`read(invocation=…)`, baseline `read(original_job_owner=…)`); 6 of the 36 deleted tests fail against it and nothing
   imports the copy now.

## Changed files (26)

All still pass every remaining test. 362 of the 363 removed tests are recorded (298 as fakes in
`retired_fake_tests.tsv`, 64 in `retired_tests.tsv`); rows cited per file in `shared.tsv`.

| File | Baseline | Now | Cause |
|---|---|---|---|
| tests/test_atac_differential_calculations.py | 95/0 | 92/0 | 3 read the deleted root/tests/fixtures tree |
| tests/test_atac_differential_inputs.py | 51/0 | 33/0 | 18, same cause |
| tests/test_atac_differential_scores.py | 36/0 | 31/0 | 5, same cause |
| tests/test_atac_reference_observations.py | 55/0 | 44/0 | 11, same cause |
| tests/test_vcf_result_measurements.py | 74/0 | 67/0 | 7, same cause |
| tests/test_variant_provider_acquisition.py | 175/0 | 160/0 | 15 used the publisher fixture on the deleted root ToolRegistry |
| tests/test_numerical.py | 15/0 | 11/0 | 4 tested APIs removed in the yield_control switch; rest retargeted to yield_control |
| tests/test_local_job_configuration.py | 7/0 | 10/0 | 1 retired (CLI capabilities command); 1 replaced by 2 new functions, unrecorded (item 2 above) |
| tests/test_calibrated_signal_inputs.py | 58/0 | 48/0 | 10 fakes |
| tests/test_chemistry_evidence.py | 24/0 | 19/0 | 5 fakes |
| tests/test_durable_episode.py | 19/1 | 8/0 | 12 fakes (incl. the baseline failure) |
| tests/test_esm_gene_embeddings.py | 48/0 | 46/0 | 2 fakes |
| tests/test_execution_memory_forensics.py | 20/0 | 19/0 | 1 fake |
| tests/test_fixed_target_seed_runtime.py | 13/0 | 12/0 | 1 fake |
| tests/test_gzip_prefix.py | 2/1 | 2/0 | 1 fake (the baseline failure) |
| tests/test_liftover_measurements.py | 42/0 | 10/0 | 32 fakes |
| tests/test_molecular_reference_privacy.py | 77/0 | 1/0 | 76 fakes |
| tests/test_molecular_sequence_driver.py | 16/0 | 12/0 | 4 fakes |
| tests/test_molecular_sequence_input_bindings.py | 113/4 | 3/0 | 114 fakes (incl. the 4 baseline failures) |
| tests/test_native_driver_runtime.py | 10/0 | 1/0 | 9 fakes |
| tests/test_native_execution_events.py | 49/0 | 48/0 | 1 fake |
| tests/test_native_lifecycle.py | 6/0 | 4/0 | 2 fakes |
| tests/test_tool_attribution.py | 16/0 | 15/0 | 1 fake |
| tests/test_tool_knowledge.py | 3/2 | 3/0 | 2 fakes (the baseline failures) |
| tests/test_ucsc_acquisition_receipts.py | 89/0 | 65/0 | 24 fakes |
| tests/test_workflow_window_scope.py | 2/0 | 1/0 | 1 fake |

(passed/failed; errors are 0 in every row.)

## Same-result files whose text was edited (11 of the 53)

Paths only (imports or fixture locations moved to `episode_support/` or `tests/fixtures/`):
`test_biopython_pairwise_grader`, `test_cmalign_graders`, `test_intervention_normalized_cfu_units`,
`test_intervention_xml_units`, `test_ncbi_gene_native_737`, `test_prodigal_grader`, `test_sequence_support_739`.
Call changes: `test_export`, `test_state`, `test_state_query` (explicit scope, item 3), `test_local_jobs`
(both limits supplied, item 2).

## Retired, recorded (479 files, 13,219 baseline tests)

| Recorded reason | Files | Baseline tests |
|---|---|---|
| imports the deleted root library (`root/library`) | 183 | 6,562 |
| built on the deleted old root runner apparatus | 77 | 2,240 |
| fake tests (`retired_fake_tests.tsv`) | 76 | 1,397 |
| exercises the deleted generic `scientific_process` role / old root runner | 30 | 682 |
| drives the deleted root `tool_registry` / `tool_configuration` | 28 | 496 |
| imports other deleted code (deleted with the old root design) | 21 | 608 |
| imports a deleted test helper module | 8 | 55 |
| read inputs from the deleted `root/tests/fixtures` tree | 7 | 473 |
| other recorded reasons | 49 | 706 |

For the root-library group only 9 files (606 tests) had a same-named twin in an axis folder at the baseline; those
twins now live in `episode_support/` (named in `shared.tsv`). Name-level indicator, not a proof of equivalence: for
31 of the 183 files (1,058 tests) every module the file imported and that is now missing has a same-named module in
the current tree, and for another 88 files (3,265 tests) some do. The same count for the other recorded groups is
27 files (803 tests) and 162 files (3,883 tests). So a recorded retirement here often means the test went while a
copy of the code it covered stayed.

## Retired without a record (38 files, 1,199 baseline tests)

Full reasoning and evidence per file are in `shared.tsv`. 30 files have no row at all; 8 have rows for some functions
only (marked "partly").

Deleted although the code is unchanged in place; a copy of the baseline file passes in full now (71 tests):

| File | Baseline | From the baseline copy now |
|---|---|---|
| root/tests/test_local_policy_script_boundary.py | 1/0 | 1 passed |
| root/tests/test_shared_emdb_responses.py | 24/0 | 24 passed |
| root/tests/test_shared_molecular_provider_responses.py | 30/0 | 30 passed (with its `fixtures/hpa` input restored) |
| root/tests/test_shared_native_cpu_metadata.py | 7/0 | 7 passed |
| root/tests/test_shared_scientific_finding_contracts.py | 9/0 | 9 passed |

Checks of the standing resource rules, lost:

| File | Baseline | Reason |
|---|---|---|
| root/tests/test_shared_local_resource_admission.py (partly) | 17/0 | 5 functions recorded as fakes. The 3 unrecorded ones are real: thread-count and process-count settings are rejected (8 cases, still pass from the copy) and the capacity definition has only byte dimensions (now fails: version v1 → v3, item 1). |
| tests/test_scientific_hpc_environment.py (partly) | 4/0 | 1 function recorded as fake. The 2 unrecorded ones checked that the shared scientific HPC commission installs no thread ceilings; top-level `hpc_scientific_commission.py` was deleted, a copy is at `episode_support/jobs/hpc/`, untested. |

Top-level or root module deleted, copies kept in `episode_support/`, the only test deleted:

| File | Baseline | Surviving code and its tests now |
|---|---|---|
| tests/test_execution_inventory.py | 22/0 | `episode_support/jobs/execution_inventory.py`; no test. Baseline file retargeted at it: 22 passed. |
| tests/test_run_statistics.py | 4/0 | `episode_support/calculations/run_statistics.py`; no test. Retargeted: 4 passed. |
| tests/test_api_selected_effects.py | 36/0 | `episode_support/acquisition/service_calls/api_selected_effects.py`; nothing imports it. Retargeted: 30 passed, 6 failed (item 4). |
| tests/test_api_bvbrc_appservice.py | 53/0 | four axis copies of `api_bvbrc_appservice.py`; no test |
| tests/test_bvbrc_analysis_protocol.py (partly) | 79/0 | `bvbrc_analysis_protocol.py` (shared + 2 axis copies); 2 functions recorded, 24 not |
| tests/test_bvbrc_analysis_transport.py | 18/0 | four axis copies of `bvbrc_analysis_transport.py`; no test |
| tests/test_bvbrc_application_definitions.py (partly) | 55/0 | `bvbrc_application_definitions.py` (shared + 2 axis copies); 1 function recorded, 16 not; no test |
| tests/test_bvbrc_appservice_contracts.py (partly) | 35/0 | `bvbrc_appservice_contracts.py` (shared + 3 axis copies); 1 function recorded, 15 not |
| tests/test_bvbrc_appservice_readers.py | 58/0 | four axis copies of `bvbrc_appservice_readers.py`; no test |
| tests/test_bvbrc_appservice_task_info.py | 16/0 | same transport copies; no test |
| tests/test_bvbrc_appservice_tool_info.py | 13/0 | four axis copies of `bvbrc_appservice_tool_info.py`; no test |
| tests/test_bvbrc_contract_validation_reuse.py | 10/0 | contracts copies; its helper file `test_bvbrc_appservice_contracts.py` is gone too |
| tests/test_minimap2_grader.py | 19/0 | five axis copies of `minimap2_grader.py`; no test |
| tests/test_ncbi_entrez_acquisition.py | 126/0 | eight axis copies of `ncbi_entrez_acquisition.py`; no test |
| tests/test_ncbi_sra_acquisition.py (partly) | 146/0 | two axis copies of `ncbi_sra_acquisition.py`; 1 function recorded as fake, 39 not |
| tests/test_spreadsheet_tools.py | 7/0 | nine axis copies of `spreadsheet_tools.py`; no test |
| root/tests/test_intervention_table_units.py | 10/0 | `episode_support/literature/readers/literature_intervention_table.py`; no test |
| root/tests/test_native_infernal_contracts.py | 34/0 | `gene_annotation_episode/native_infernal_contracts.py` and `episode_support/tools/similarity_search/native_infernal_tool_info.py`; no test of the tool info |
| root/tests/test_root_shared_tool_parsers.py | 20/0 | `blast_search.py` copy is covered by six other files; `rfam_discovery` and `provider_jobs` have no test |
| root/tests/test_root_tool_parser_custody.py | 19/0 | `infernal_search_inputs.py`, `infernal_search_grader.py` copies; no test. `uniprot_response_custody` exists nowhere. |
| root/tests/test_terminal_profile_dispatch.py | 3/0 | six axis copies of `terminal_scientific_evidence.py`; no test |

Duplicate of a test that survives for the other copy of the code:

| File | Baseline | Surviving twin |
|---|---|---|
| root/tests/test_native_blast_contracts.py | 57/0 | `episode_support/forms/similarity_search/tests/test_native_blast_contracts.py`, 57 passed |
| root/tests/test_native_hmmer_contracts.py | 38/0 | `episode_support/forms/similarity_search/tests/test_native_hmmer_contracts.py`, 38 passed |
| root/tests/test_molecular_private_driver_saved.py | 4/0 | the same four functions in `tests/test_molecular_sequence_driver.py` |

Code and test both gone, nothing references the code now:

| File | Baseline | Subject |
|---|---|---|
| tests/test_protease_kinetics_result_contracts.py | 88/0 | `protease_kinetics_result_contracts` (6 copies at the baseline, none now) |
| root/tests/test_root_enrichr_publication_metadata.py | 35/0 | `root/enrichr_publication_metadata.py` |
| root/tests/test_retained_file_read.py | 19/0 | `root/library/retained_file_read.py` |
| root/tests/test_shared_native_operation_lock.py | 6/0 | `gene_annotation_episode/native_operation_lock.py` |
| root/tests/test_atac_differential_result_receipts.py (partly) | 35/0/20 errors | old root ATAC receipt admission; 8 functions recorded as fakes, 2 not |
| root/tests/test_private_prompt_transport.py (partly) | 21/0 | each axis's deleted `providers` module; 2 functions recorded as fakes, 1 not |
| root/tests/test_default_root_tools_constructor.py | 1/0 | old root `tool_configuration.build_tools` / `ToolRegistry` |

## Current test files with no baseline row in this scope (349)

Results for all are in `shared_new_files.tsv`: 13,756 tests, 13,660 passed, 39 failed, 57 errors.

- 339 came from axis baseline rows (moved to `episode_support/` or `tests/`); they belong to the axis reports. 14 of
  them fail or collect nothing, all of A101 origin. 11 have the same counts as their A101 baseline row. Three differ:
  `test_hmmer_alignment_map_context.py` 36/35/1/0 (baseline 46/41/5/0), `test_blast_utility_result_views_629.py`
  44/43/1/0 (46/45/1/0), `test_hmmer2_upstream_fixtures.py` 0 collected (baseline: 1 test, skipped).
- 10 have no baseline row of the same file name. Six are named in axis reports
  (`test_ncbi_sra_file_custody.py` 5 passed, `test_monitor_report_facts.py` 1 passed,
  `test_monitor_commissioned_report_form.py` ×3, 5 passed each, `test_literature_partner_population.py` 9 passed).
  Four are new in this scope:

| File | Tests | Passed |
|---|---|---|
| episode_runtime/tests/test_journal_and_progress.py | 5 | 5 |
| gene_annotation_episode/episodic_workflow/root/tests/test_axes.py | 1 | 1 |
| gene_annotation_episode/episodic_workflow/root/tests/test_credit.py | 13 | 13 |
| gene_annotation_episode/episodic_workflow/root/tests/test_instruction_library_folders.py | 33 | 33 |

## Dangling-name scan

Own read-only check (`runs/pfshred_tools/dangling_scan.py`; it reuses the binding tables of
`runs/claude_inputs/la/dangling.py` with a resolver for the current layout, and adds module-path strings, data files
and third-party imports). Scanned: 3,938 Python files and 1,682 text/data files under `gene_annotation_episode/`,
`episode_runtime/`, `yield_control/`, `method_loop/`, `tests/`, `tools/`; 27,452 import statements, 13,053 references
to repository modules. A control file with ten deliberately broken references was reported in full.

- Imports and from-imports of repository modules, module attributes, patch targets, `import_module` literals:
  **0 dangling** (the baseline list had 121).
- `dangling_names.tsv` has 107 rows, none of them an import of a repository module:
  - 3 introduced since the baseline:
    `gene_annotation_episode/molecular_sequence_execution_contracts.py:21` `ADAPTER_MODULE =
    'gene_annotation_episode.molecular_sequence_execution_driver'` (module deleted; the string still builds the
    requested argv at line 134); `tools/a103_report_cases.py:46` names the deleted `root.a103.phmmer_result_worker`;
    the docstring of `root/a105/experimental_activity_evidence/tests/test_runtime_bindings.py` names
    `gene_annotation_episode.yield_control` (the package is `yield_control`).
  - 7 module-path strings that were already dangling at the baseline, now in `episode_support/`:
    `native_fluorescence_contracts.py:21` (`gene_annotation_episode.native_fluorescence_driver`),
    `native_protein_structure_contracts.py:51,52,149,150` (`…native_protein_structure_driver` / `_worker`), and the
    `-m` argument in the two `native_hmmer_result_publication.py` copies (`root.a104` / `root.a103`
    `.native_hmmer_result_worker`).
  - 92 dotted paths in data files, all already there at the baseline with absent targets: 84 in
    `tests/fixtures/a102/protein_structure_result_worker_393/fixtures/*.json`, 3 in a coupled-redox fixture, 4 in
    `native-blast-database.md` knowledge files, 1 in an a103 fixture README.
  - 5 imports of third-party modules not installed in `.venv` and not declared dependencies: `torch`, `esm`
    (`esm_gene_embedding_worker.py`), `sklearn` ×2 (`native_expression_nmf_driver.py`), `matplotlib` (a vendored
    fixture script).
- Examined and left out because they are identifiers, not module references: the reserved decision names
  `episode_runtime.progress_origin` / `progress_reference` / `progress_receipt.`, the three export format names in
  `gene_annotation_episode/export.py`, a `startswith` prefix in `tests/test_calibrated_signal_measurements.py`, and a
  module a test writes into its own temporary module root (`tests/test_native_driver_runtime.py`).

## Run records

`runs/pfshred_run1` (current files, one process each: `units_done.tsv`, `junit/`, `logs/`), `runs/pfshred_run2`
(copies of the 38 unrecorded baseline files), `runs/pfshred_run3` (three copies retargeted at surviving modules),
`runs/pfshred_dg01`, `runs/pfshred_dg02` (scan), `runs/pfshred_tools/` (scripts, `overrides.tsv`),
`runs/pfshred_out/` (drafts), `runs/pfshred_restore/` (baseline copies; disposable).
