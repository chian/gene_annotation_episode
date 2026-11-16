# rec1: reconciliation of the shared root (15 November 2026)

Area: everything under `gene_annotation_episode/episodic_workflow/root/` outside `a101`..`a110` (6,411 Python files:
6,273 product modules, the rest tests and test helpers). Two edits outside the area were named in the task or needed
by it and are listed under "Outside the area".

## Read this first

1. **A current execution path had been deleted and is restored.** The first shared-root pass removed
   `BVBRCAppServiceHost.execute_locked` together with `legacy_cached_download` (one hunk of 142 removed lines in
   `root/bvbrc_appservice_host.py`). `root/api_service_operations.py:66` still calls it, so every BV-BRC AppService
   operation would have raised `AttributeError`. I restored the method verbatim from a0d9f1666 (it is byte-identical to
   the a102 copy apart from one import path). The file's diff against a0d9f1666 is now only the 67 intended deletions.
2. **Three other live paths were broken by earlier deletions and are fixed**: the literature definition lists and
   record algorithms still named two deleted files (`literature_assay_grading_legacy_cells_v1.json`,
   `library/literature_saved_adapter_definitions.py`; `descriptor_operand_bytes` would raise `FileNotFoundError` for
   every assay-grading population binding); `ScientificToolLibrary.supports_tool_info` and `catalog(tool_info=...)`
   were still used at three sites; `practical_outcome_view(control_version=...)` was still passed at one.
3. **The stub change is measured**: all 132 per-home test files that use the edited shared stubs pass (1,976
   passed, a101-a104, a106, a107, a110, run `claude_rec1_120`). When I started, a101-a103 still read the removed
   workflow attributes; another agent removed those reads while I worked.
4. **Not done**: the multi-version sites proot listed as "not established" (`literature_a105_worksheet` VERSION /
   VERSION_V2, `protein_structure_operands` GRADING_SCHEMA / _V2, blast-utility job v2/v3 in
   `local_execution_validation.py`, the `getattr(..., None)` defaults, the 17 unreachable `received_report_prefix`
   guards). I traced none of them to a writer; they are as proot left them.

## Verified by running / by reading

By running (launcher, slot `rec1`, runs `runs/claude_rec1_001`..`125`):
- import check over all 6,273 non-axis product modules, 7 batches: `{}` each (runs 014-020); the 8 modules edited
  afterwards again: `{}` (run 116);
- `pytest --collect-only` over `root/tests` and the one shared-root home test: 1,730 collected, 0 errors (run 021);
- every test file under `root/tests` plus the home test, one file per launcher run (88 files, 668 s);
- the dangling-name scan over the area and over the whole package and `tests/` (runs 003, 013, 118);
- per-home tests that use shared root helpers: 132 files using the edited stubs, 150 files using the others;
- `tests/test_bvbrc_appservice_host.py` (8 passed, run 126): it drives AppService operations through
  `APIServiceExecution.execute`, so it reaches the restored `execute_locked`;
- `tests/test_bvbrc_appservice_custody.py` and `tests/test_bvbrc_genome_alignment_retained_records.py` before and
  after my fixture edits there; the inputs, associations and tool_info files of that family after only.

By reading only: the transport rule in `task_action_contracts._recorded_assignment_transport`; the a103 question in
`scientific_process/report_validation.py`; that nothing loads the deleted fixture files; that no writer of
`execution_status_v1` or of a missing `root_action_boundary` exists.

## Task 1: shared test stubs

Brought to the current form: `monitor_task_behavior.py` (two stub workflows get `pending_work`; expected saved result
carries `pending_work_after_action`), `monitor_credit_behavior.py` (`execution_status_v2` with `suspension`),
`hpc_prediction_task_behavior.py`, `hpc_planning_allocation_task_behavior.py`, `hpc_allocation_parent_exchange.py`,
`hpc_prediction_parent_exchange.py`, `hpc_launch_task_checks.py` (also two exact saved-result comparisons),
`test_private_binding_identity.py`. No stub passes `wait_inputs_version`, `completed_action_inputs_version` or
`episode_branch_lifecycle` any more.

Result: 132 per-home files using these stubs: 1,976 passed, 0 failed. The other 150 per-home files that use any
shared root helper: 1,610 passed, 4 failed, 30 errors. The 4 are a103's own
`scientific_process/tests/test_scientific_head_task.py:99` (row sent to pa103). The 30 errors
(`local_resource_binding_conflict`, a107 and a110) came from running 150 files in one process:
`a110/tests/test_private_reconstruction.py` alone passes 12 of 12 (run 122); I did not rerun the two a107 files alone.

## Task 2: shared root product code

- `execution_status_v1` removed: `progress_observations.py` has one `_EPISODE_STATUS` schema (v2 with `suspension`);
  `library/progress_information_credit.py:59` accepts only v2. The only writer is `method_loop/durable.py:640`.
- Non-owned branch lifecycle removed from 155 home `from_child_*.py` copies (the `owned` variable and both
  alternatives; the unused import in 44; `admit_unowned_return` in 2). `saved_run_assembly.py` refuses settings
  without the owned lifecycle instead of passing `None` on.
- `workflow_setup.py:57`: `root_action_boundary` must be the current version (`None` was accepted; the writer,
  `run_execution.py:301`, always writes it). Not in the list of decisions; say if you want it back.
- `wait_inputs_version` / `completed_action_inputs_version`: no reader is left in the shared root. I kept the two
  constructor parameters and their single-value checks, as the axis copies have them.
- `unproven_replay`, `_unproven_direct_response_index`, `recorded_transport`: 0 occurrences.
- `_recorded_assignment_transport` follows the rule: a request saved under the exchange protocol without the proof
  returns; any other request without a valid proof raises.
- `scientific_process/report_validation.py`: the a102 row was already applied. a103 needs no wiring:
  `a103_investigation.measurement_report_schema()` is built from `report_schema()`'s own two fields (`records`,
  `context_credit`), so a current a103 report already takes the `resolve_measurement_report` branch, which validates
  the form and recomputes the credit. That matches how a102 and a104 current forms are resolved there.
- From rows: `library/bvbrc_appservice_bundle_values.py` unconditional capped-download check;
  `library/molecular_sequence_result_contracts.py` drops `protease_kinetics_components_v1` (mirrors the top-level
  copy); `library/flux_balance_result_receipts.py` drops `control_version=`.

## Task 3: rows and named files

Every row addressed to proot, prootlib, rootlib, roothomes, proothomes or root-shared was checked against the
current files (by grep per symbol, and by the scan for the 64 ptop rows about deleted modules). Open ones applied:
- `test_execution_local_file_sources.py`: fixture saves `pending_work_after_action`; altered-outcome cases start from
  the saved form; manifest `schema_version` 2. 43 passed / 31 failed -> 67 / 7. The 7 call
  `ExecutionEpisodes.execute` / `.fact_sources`, which the shared-root class does not have (not purge-related).
- `test_annotation_task_boundaries.py`: restored 3 tests (7 cases) of current behaviour in the current form:
  returned tool status x5 (stub with `pending_work`), saved completed model call (direct request with the proof),
  pending exchange request (no proof, as written by `task_decision.py:139-147`). 5 passed -> 12 passed.
- `library/bvbrc_genome_alignment_retained_records.py:274`: accepts only `{url, byte_range, max_bytes}` with
  `max_bytes` equal to the selected argument.
- `test_native_lumpy_execution.py`, `test_lumpy_execution_registration.py`: fake software uses the current
  `_REQUIRED_MODULES` (registration had gone 31 passed -> 31 errors; now 31 passed / 1 failed as before the purge).
- `test_api_rfam_service.py`: 37 passed / 9 failed before the purge, 4 / 41 after it, now 44 / 1. The top-level
  `api_rfam.py` no longer accepts a submission snapshot without the HTTP wire capture, so the fake client records
  one; the resource configurations no longer carry a transport timeout; the timeout test now asserts the refusal.
- `test_native_rna_structure_results_integration.py`: `native=` dropped; two cases deleted (see the TSV).
- `scientific_head_boundaries.py:149`: tautological `scientific_binding_compatible(d, d)` assertion deleted.
- `fluorescence_prepared_workflow_support.py`, `test_bvbrc_genome_alignment_host.py`, `saved_worker_identity_checks.py`,
  `test_native_genomic_overlap_shared.py`: already deleted by others; nothing imports them.

## Task 4

`a101/tests/fixtures/masking_native/ORACLE_MANIFEST.json` and `ORACLE_CASES_001.json` deleted (directory mode
restored to 555). Left behind: `ORACLE_MANIFEST.sha256`, a checksum of the deleted manifest, and
`FORMAT_OBSERVATIONS.json`; no Python file names either.

## Task 5: dangling names

Script: `runs/claude_inputs/purge/rec1_work/dangling.py` (static, AST). It reports imports of missing repository modules,
`from X import name` and `alias.name` where the module binds no such name (including imports inside functions),
`monkeypatch.setattr` targets, literal `import_module` names, and keywords passed to a function, class or
`Class.method` whose definition lacks the parameter. It cannot see attributes of objects, `__import__` literals, or
module names held in strings; I found those cases by other means (names removed since a0d9f1666 that are still
called; path literals that no longer exist) and by the test runs.

Shared root: 51 findings at first, 13 now. Fixed: 3 imports in `episode_services.py`, `library/execution_progress.py`,
`library/macs2_peak_presentation.py`, `library/molecular_result_facts.py`, `library/restriction_mapping_publication.py`,
`library/genomic_context_tool_registry.py`, `library/flux_balance_result_receipts.py`, and 25 sites in 13 test files
(`tool_info=`, `episode_type=`, `runtime.<moved name>`, `_CURRENT_REQUIRED_MODULES`, `native=`,
`project_process_result`, `scientific_process_prompt`); two unloaded saved source copies deleted
(`tests/fixtures/bvbrc/frozen_composition/`).

The 13 left all predate the purge and need a placement decision, not an import path:
- `library/flux_balance_tools.py:311` imports `gene_annotation_episode.flux_balance_model_execution`; the function
  exists only in `a110/flux_balance_model_execution.py`.
- `library/molecular_result_recognition.py:23,26` and `library/molecular_value_presentation.py:32,35` import
  `protein_phylogeny_result_views` / `protein_conservation_result_views`; they exist only in a104.
- `literature_a105_aggregation_storage.py:56`, `literature_a106_subscore_storage.py:270`,
  `literature_a108_aggregation_storage.py:52` import `require_attribution`, `bind_contribution` from
  `root_axis_scalars`, which the reorganisation moved to the axes. `returns.axis_contribution_readers` uses the axis
  repositories, so these three shared-root methods are unreachable from it.
- `tests/live_a105_database_workflow.py:65`, `tests/live_a106_workflow.py:106` import `root.literature_episodes`,
  which does not exist.

Elsewhere: 113 findings (a101 23, a104 36, a106 17, a107 7, a108 3, a110 5, top-level 2, `tests/` 20; none in a102,
a103, a105). Full list: `runs/claude_inputs/purge/rec1_dangling.tsv`. The one with the widest effect is
`gene_annotation_episode/api_services.py:103` and `tool_information.py:153` importing the missing
`gene_annotation_episode.api_uniprot`: it fails 9 tests in 7 of my gate files.

Also predating the purge, found by the path-literal check: `library/native_flux_balance_preparation.py:38,322` names
the worker module `gene_annotation_episode.flux_balance_result_worker` and
`library/native_blast_standard_database_contracts.py:99,621` names
`gene_annotation_episode.native_blast_standard_database_driver`; neither file exists outside the axes.
`scientific_process/definition_inputs.py:326` lists `root/a106/a106_work_report.py`, which does not exist.

## Gate

Import check `{}`; collection 1,730 tests, 0 errors. Test files: 88 files, 1,380 passed, 214 failed, 133 errors,
1 skipped; 56 files clean, 32 failing. Per file: `runs/claude_inputs/purge/rec1_gate_results.tsv` (with the count
before the purge and the run number). Before the purge the same directory had 116 files: 1,881 passed, 287 failed,
183 errors.

Failing files and cause (counts are passed/failed/errors):
- Missing `gene_annotation_episode.api_uniprot` (top level): `test_addgene_selected_process_path` 0/1/0,
  `test_bvbrc_alignment_tool_info` 118/1/0, `test_bvbrc_phylogeny_tool_info` 66/1/0,
  `test_native_rna_structure_results_integration` 0/1/0; part of `test_bvbrc_data_library` 1/4/0,
  `test_execution_tool_contract_declarations` 2/4/0 (other 2: a102 `bvbrc_operation_request_version_conflict`),
  `test_root_episode_boundary` 1/4/0 (other 2: `DID NOT RAISE RuntimeError`, stub lacks `for_child`).
- `root.execution_episodes.ExecutionEpisodes` lacks the method the test calls (`prepare_assignment`, `initialize`,
  `facts`, `credit_view`, `fact_sources`, `execute`, `entry_roles`, `yield_controller`):
  `test_api_rfam_service` 44/1/0, `test_bvbrc_proteome_directional_returns` 1/7/0,
  `test_execution_episodes_family` 1/13/0, `test_execution_local_file_sources` 67/7/0,
  `test_execution_recorded_results_assignment` 0/26/0, `test_fluorescence_episode_routing` 22/15/0, rest of
  `test_bvbrc_data_library`; `test_resource_selected_adapter_return` 0/1/0 is the same for `ResourceEpisodes.validate_report`.
- `test_execution_closed_credit` 0/1/40: fixture configures an Enrichr transport timeout, refused by
  `api_services.validate_fresh_service_configuration`.
- `test_atac_differential_execution_integration` 7/1/7, `test_atac_differential_result_receipts` 35/0/20: the shared
  fixture in `tests/test_native_atac_differential_contracts.py` pins the top-level copy's `REQUIRED_MODULES`; the root
  library requires its own (`native_dependency_unavailable`).
- `test_bvbrc_minhash_commission_replay` 0/30/0: imports the missing `gene_annotation_episode.api_bvbrc_minhash`.
- `test_native_infernal_preparation_nested_workflow` 0/6/42, `test_native_infernal_preparation_results_integration`
  0/40/0: read a file under `verification/tool_graders_infernal_preparation_*` that is not there.
- `test_launch_instruction_runtime` 3/9/0, `test_native_infernal_preparation_reference_visibility` 0/2/19:
  `TypeError: complete_episode_binding_required`.
- `test_private_binding_identity` 67/5/0: a105, a106, a108 still read `episode_branch_lifecycle` in
  `report_sources` (3; these passed before I dropped the attribute from the stub); a103 stub lacks
  `legacy_parent_for_path` (2, as before the purge).
- `test_signed_evidence_root` 24/7/0 (was 21/10): missing top-level helper
  `test_scientific_process_return_records` (3), `'source_failed' == 'yield_stop'` (3), `0 == 3` (1).
- `test_root_saved_report_redelivery` 2/8/0: `scientific_process_selection_invalid` inside
  `validate_saved_fact_form` (6), two unmatched error patterns.
- One cause each, same counts as before the purge, not examined further: `test_expression_nmf_execution_integration`
  0/0/5 (`KeyError 'NMF488_SOFTWARE'`), `test_lumpy_execution_registration` 31/1/0 (`StopIteration`),
  `test_monitor_credit_factory` 7/1/0 (`KeyError 'configuration'`), `test_native_lumpy_execution` 45/7/0
  (`original_attempt_mismatch`), `test_protein_structure_source_boundaries` 22/1/0, `test_root_enrichr_controlled_receipts`
  8/7/0, `test_root_task_declaration` 10/2/0.

## Outside the area

- `tests/test_bvbrc_appservice_custody.py`: `SavedRecords.child` saves the direct request with its transport proof
  (57 passed / 21 failed -> 77 / 1; the 1 is `tests/bvbrc_episode_fixture.py:165` `YieldParameters(100, 50)`).
- `tests/test_bvbrc_genome_alignment_retained_records.py:154,162`: capped call and argument, required by the
  validator change (retained_records 50 passed / 3 failed -> 53 / 0; after only: inputs 70 passed, associations 30
  passed, tool_info 0 passed / 4 failed, which was 0 / 14 before the purge).
- The two a101 fixture files (task 4).

## Counts

Product files edited 179 (155 of them the `from_child_*.py` copies); test and helper files edited 27 in `root/tests`
and 2 in `tests/`; files deleted 4 (2 saved source copies, 417 lines; 2 a101 fixtures); tests deleted 2 cases,
restored 7 cases, 1 rewritten to assert the refusal. `rec1_deleted_tests.tsv` lists the deletions.

## Handoff rows written

To pa101/pa102/pa103 (removed workflow attributes; later marked satisfied), pa101/pa102/pa103/pa105/pa106/pa108
(non-owned lifecycle; open for a105, a106, a108), pa101/pa102/pa103 (`execution_status_v1` in
`library/progress_information_credit.py` and `episode_monitoring.py`), ptop (`episode_progress_credit.py:59`),
ptests (`bvbrc_episode_fixture.py:165`; note of my two edits), pa103 (`test_scientific_head_task.py:99`).

Not a purge item, noticed: `root/runs/shared-execution/memory.sqlite3` is untracked run output inside the source
tree (written 12 November through `gene_annotation_episode/execution_memory.py:65`).
