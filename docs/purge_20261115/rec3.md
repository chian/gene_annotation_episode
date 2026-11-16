# rec3 — a102 and a103 brought to the current form (15 November 2026)

Area: `gene_annotation_episode/episodic_workflow/root/a102/` and `.../root/a103/` (`R/` below is
`gene_annotation_episode/episodic_workflow/root/`). One agent, no sub-agents, one launcher command at a time
(slot `rec3`). No git add/commit. Starting point: checkpoint e5c5ff9b6 plus the uncommitted work found on top of it
(92 files in a102, 2 in a103); a copy of that starting state is the reference for every count below.

Method: for each file with a same-path twin in a107 or a104 a three-way merge was computed (base = twin at
a0d9f1666 with the arm name replaced, ours, theirs = the twin now). Merges without conflict were applied after
reading the aggregated differences (a102: 65 from a107 + 3 from a104; a103: 66 + 12). Files with conflicts
(about 190 per arm, mostly because the arms' task files are laid out differently) were not merged; the twin's
removed lines still present in ours were used as a to-do list and done by exact-match scripted edits. Files that
were identical in a102 and a103 before the purge were compared with each other and made equal where one earlier
agent had removed a form and the other had not.

## 1. Removed

Counts are lines in `.py` files matching the pattern, starting state -> now.

| what | a102 | a103 |
|---|---|---|
| reads of `wait_inputs_version` outside `Workflow.__init__` (incl. `=None` test doubles) | 91 -> 0 | 91 -> 0 |
| `completed_action_inputs_version is None / is not None / in {None, ...}` | 89 -> 0 | 101 -> 0 |
| `wait_inputs_binding_v1` | 3 -> 0 | 0 |
| `episode_branch_lifecycle ==` / `!=` branches (the one left is the constructor refusal) | 31 -> 1 | 25 -> 1 |
| non-owned report delivery: `admit_unowned_return`, `or not owned else`, `if owned else` | 60 -> 0 | 47 -> 0 |
| `supports_tool_info` | 0 | 10 -> 0 |
| path-less branches in `episode_bindings.py` (`register` x2, `_child_binding` x2, `for_path`, `for_child`) | 6 -> 0 | 6 -> 0 |
| `execution_status_v1` | 4 -> 0 | 5 -> 0 |
| `ALTER TABLE` / `PRAGMA table_info` upgrades | 3 -> 0 | 13 -> 1 (create-time, see 3) |
| asserts on `__module__` of product objects in tests | 25 -> 0 | 23 -> 0 |
| "20 GiB" sentences | 0 | 5 -> 0 (+ `knowledge/sequence-translation.md` in both arms) |

Product code, both arms unless stated:

- `runtime.py` `Workflow`: accepts only `wait_inputs_binding_v2`, `completed_action_inputs_binding_v1`,
  `received_progress_order_v1`, the owned lifecycle and `root_action_boundary == ROOT_BOUNDARY_VERSION` (None is
  refused); `assemble_workflow` requires all five settings members. `pending_work_after_action` is written
  unconditionally (runtime plus 67 a102 / 75 a103 home `task.py`, a102 `operations.py`,
  `annotation_improvement/operations.py`). Completion evidence capture, waiting support with identities and local
  return history, owned recovery, pending delivery and the owned close check are unconditional
  (a102 `continuation.py`, `decision_waiting.py` and their `annotation_improvement` copies; 8 a103 `yield_estimator.py`).
- Non-owned report delivery: the second half of `Workflow.selected`'s `report`, `admit_unowned_return` in 18 a102 and
  12 a103 `from_child_*.py`, and its member in the `child_message_owners.exchange_for_child` tuples (3 a102,
  2 a103 modules; a103 `runtime.py` tests `len(child_exchange) == 3`). a103 `_parent_name_EPISODE_BRANCH_LIFECYCLE` gone.
- `episode_bindings.py`: `register` requires `binding_path` and `commissioning_parent`; `_child_binding`, `for_path`
  and `for_child` have no lookup of bindings without a path (a102 = the a104 form; a103 keeps its two predefined
  parents, see 2). Established first: all 67 a102 and 73 a103 registry homes declare both members.
- Controller layouts: `_category_yield_parameters` reads only the saved controller settings the program writes
  (`{cost, uncertainty_alpha}`); the versioned caller layouts `existing_yield_controller_explicit_*_v1/v2/v3` had no
  writer in either arm. `numerical.py` `YieldParameters` has only `uncertainty_alpha` (a107 form); `window_size` /
  `subsample_size` gone from `numerical.py` and the two `runtime.py` readers.
- Optional effects table: `_decision_rejection` no longer tolerates a missing `runtime_decision_effects`
  (`CompletionLedger.__init__` always creates it, `episode_completion.py:142`).
- Implementation-digest tolerance of the scientific process: `restore_saved_process`, the saved-hash branch of
  `restore_closed_process`, `scientific_binding_compatible` (a102 `scientific_process/saved_scientific_state.py` = a107
  form, a103 `scientific_process/from_parent.py`, both `episode_composition.py`, both `runtime.py` `build`).
- Tool library, a103: the name-only snapshot mode (`scientific_tool_library_v1`, `supports_tool_info`, `resolve(names)`,
  `retrieve`, `INFO_VERSION`, retrieval request v1, `output_schema`); `scientific_tool_library.py` and
  `scientific_tool_retrieval.py` are now the a102 files; callers in `runtime.py`, `scientific_process_reports.py`,
  `scientific_process/operations.py`.
- Waiting inputs: `WaitInputs.capture` has no `include_identities`; only `wait_inputs_v2` is produced
  (`wait_estimation_inputs.py`, callers).
- `execution_status_v1`: `episode_monitoring.py`, `library/progress_information_credit.py`.
- Database upgrades: `method_loop/durable.py` (`commissions.failure`), a103 `episode_journal.py` (credit-column rebuild,
  two added columns), `episode_receipts.py` (`received_report_prefix`).
- Native families (twin removals and the a102/a103 cross-comparison): BLAST standard-database calculations v1 and
  worker manifest v1 (`native_blast_standard_database_calculators.py`, `_result_worker.py`, `_result_publication.py`),
  `_HISTORICAL_OPERATION_SCHEMA` (`native_blast_utility_contracts.py`), markerless pairwise results
  (`biopython_pairwise_grader.py`), pairwise sources proved by an old tool operation (`alignment_site_native.py`),
  `files_to_stage` plans (`hpc_result_receipts.py`), assignments without a resource id (`execution_progress.py`),
  `readable_record_versions` and binding-less receipts (`literature_rate_storage.py`), `parse_uniprot` /
  `uniprot_pagination` (`acquisition.py`), optional `include_map_context` (`native_hmmer_preparation_result_worker.py`,
  `_result_publication.py`), shared-information records without a recipient (`shared_information.py`), BLAST
  observations without `shared_projection` and the label `legacy_saved_native_reported` (`blast_result_views.py`),
  the BV-BRC array/header profile and `qualified_request` (`bvbrc_data_readers.py`, `bvbrc_data_schema.py` = the
  `R/library` files; a103 `bvbrc_comparative_systems_data_inputs.py`). a103 only, already done in a102: uncapped
  download forms (`api_bvbrc_appservice.py`, `bvbrc_appservice_contracts.py`, `_readers.py`, `_bundle_values.py`,
  `_tool_info.py`, `bvbrc_appservice_schemas.json` now requires `max_bytes`), retained BLAST grading v1
  (`native_blast_hsp_views.py`, `native_blast_result_publication.py`, `native_blast_result_worker.py`), hmmsim
  old-record tolerance (`native_hmmer_preparation_contracts.py`), calibration-less extractions
  (`hmmer_preparation_result_views.py`). a102 only: `max_running_jobs` setting key (`local_resources.py`).
- Data: 12 `library/*.ownership.json` (6 per arm, 620 lines, no reader).
- `literature_publisher_binding.py` / `snapshot_graph` / `SavedBindingGraph`: neither arm has a copy (grep: 0).

Tests and fixtures of the arms, changed in the same step:

- Deleted: `test_runtime_build_uses_private_monitor_task` in 7 `test_progress_task.py` (6 a102, 1 a103) — see
  `rec3_deleted_tests.tsv`. 25 a102 and 23 a103 location-assert lines removed from tests that also check behaviour
  (`*_task_checks.py`, `test_private_*_tasks.py`, `head_checks.py`, `test_scientific_head_task.py`,
  `test_homology_monitor_task.py`, `test_source_instruction_service.py`); two a103 descriptor asserts that compare a
  recorded dotted name were kept.
- Test doubles: `wait_inputs_version=None, completed_action_inputs_version=None` replaced by `pending_work` in 7 a102
  and 8 a103 test modules; two expectations now include `pending_work_after_action`
  (a103 `test_scientific_head_task.py:99`, `tests/api_task_checks.py:315`).

## 2. Kept as live (writer traced)

- Transport rule: a decision-exchange request saved without the transport proof is accepted; only a direct request
  without a valid proof is refused — a102 `runtime.py:415`, a103 `runtime.py:350` (unchanged).
- The five settings members: written by a102 `runtime.py:5623-5627`, a103 `runtime.py:4311-4315`.
  `annotation_child_roles` absent: the writer omits it when the caller passes None (a102 `runtime.py:5633`, a103 `:4321`).
- a103 `legacy_parent_for_path` (`runtime.py:2069`), `legacy_parent_types` (`homology_service_setup.py:3`),
  `legacy_request_assembler` (`runtime.py:3678-3682`), `legacy_entry` (`episode_bindings.py:406`),
  `legacy_parent_must_remain_unbound` (`task_state.py:64`, `legacy_improvement/task_state.py:64`): the predefined
  annotation and improvement parents (`a103/episode.py:17`, `legacy_improvement/episode.py:17`) are never registry
  bindings; `legacy_parent_for_path` returns them for a path whose last role is not a registry role, and is how
  `Workflow.build` (`runtime.py:3871,3904`), the credit view and the homology child selection (`:2083`) find them.
  The homes `legacy_annotation` and `a103/legacy_improvement` stay.
- `_live_original_runtime` / `_live_original_runtime_prompt` (a102 561, a103 745 files): only the import alias of the
  arm's current module (`from ...a10N import runtime as _live_original_runtime`). Left.
- a103 `homology_jobs.py:131` `ALTER TABLE orders ADD COLUMN search_mode`: runs inside registry creation when
  `search_modes` is given; it is the create-time shape, not an upgrade.
- `legacy_uniprot_records` (`uniprot_native.py:870`): called by the current UniProt import (a102 `tools.py:2400,2454`,
  a103 `tools.py:2314,2368`). a102 `a102_structural_catalog.py:84` `legacy_records`: a field of the catalog written
  by `prepare_catalog`, called from `a102_structural_workflow.py:140`.
- `provider_jobs.py:24` `unsupported_historical_hmmer_request`, `sequence_masking_contracts.py:333`
  `legacy_custody_variant`, `blast_database_preparation.py:198` `legacy_preparation_context_forbidden`,
  `literature_rate_storage.py:855`: names of current refusals.

## 3. What remains and why

- `composition_information.restricted_root` reads `root_action_boundary` with a None default: the arms' and the shared
  test doubles omit the attribute; `Workflow` itself refuses None.
- `decision_history.py:186-271` builds its query from the tables present (`runtime_decision_effects`,
  `runtime_completion_slots`, `runtime_estimation_contexts`); identical in a104/a107; not changed because the
  journal-only tests open a store without a ledger. Other `sqlite_master` checks are for tables created on first use.
- Of the seven a102 native-family sites: three removed or shown live above (`blast_result_views.py`,
  `bvbrc_data_readers.py`, the two refusal names); `native_blast_vdb_function_metadata.py:168` and
  `native_database_terminal_custody.py:122` are docstring sentences only; `blast_database_grader.py:791,892,1126`
  (binding lists omitted select "legacy accession matching") is NOT traced to the end — its callers choose the sheet
  version by the arguments they pass and I did not follow every caller.
- Not traced: a102 `runtime.py:2913` (saved decision without `literature_numerical_contracts`),
  `bvbrc_appservice_publication.py:259`, a102 `runtime.py:613-642` (completed action without pending-work support),
  the a103 suspects of pa103 section 5 (`library/hpc_prediction.py:151`, `component_assessment_dependencies.py:71`,
  `homology_results.py:184,384`, `api_bvbrc_minhash.py:151`, `provider_jobs.py:1`, `bvbrc_genome_alignment_inputs.py:405`,
  `api_service_execution.py` `historical_uniprot`, `practical_execution_records.py:26`).
- `LEGACY_EVIDENCE_SLOT` (owner's choice per h5 section 4), self-hashing (`implementation_sha256` producers), and the
  history narration in comments (about 25 inventory prose lines still present) were not part of this step.
- `Workflow` still stores `wait_inputs_version`, `completed_action_inputs_version`, `progress_receipt_order` and
  `episode_branch_lifecycle` after checking them (as a104/a107 do); nothing in either arm reads them.

## 4. Handoffs

- Applied (rec1 rows 415-417 and its 22:00 update): version attributes no longer read in homes, non-owned branches
  removed, `execution_status_v1` removed, a103 head-task expectation corrected.
- Written: one NOTICE row `rec3 -> ptests,rec1` listing the ten current-only forms that outside tests driving a102
  or a103 through a parametrized package name must now use. No file under `R/tests/` was edited.

## 5. Gate

Verified by running (launcher slot `rec3`, one command at a time):

- Compile of every `.py` in both arms: 0 syntax errors (`runs/claude_rec3_011`).
- Import check after the last edit: `{}` over all 2,976 a102 product modules (`runs/claude_rec3_012`) and all 3,264
  a103 product modules (`runs/claude_rec3_013`).
- Every test file of each arm, one file per launcher run, isolated form, run twice: once after the main edits
  (`runs/claude_rec3_a102r1_*`, `..._a103r1_*`) and again after the last edit (`..._a102f_001..092`, `..._a103f_001..098`).
  Collection errors: 0 in every run.

| arm | files | passed | failed | skipped | errors |
|---|---|---|---|---|---|
| a102, final run | 92 | 4,924 | 5 | 11 | 0 |
| a103, final run | 98 | 4,329 | 2 | 0 | 0 |

Failing files, with cause:

- `a102/tests/test_a102_parent_coordination.py` (1): `DurableExecutionError: unavailable_binding`. Failed before the
  purge and at the earlier agent's hand-back (cause recorded in `docs/test_failure_triage_20261114/r4b_causes.tsv`).
- `a102/tests/test_literature_structure_integration.py` (4 of 4): two `unavailable_binding`, two
  `assert (0.0 == 0 and 0 == 1)`. Same four failed before.
- `a103/tests/test_a103_context.py::test_runtime_parent_receives_exact_component_operands_from_automatic_grading` (1):
  its stand-in workflow has no `shared_information_repository`. Failed before (pa103).
- `a103/tests/test_a103_real_detection.py::test_real_complete_search_scoped_absence_unknown_and_cooccurrence` (1, final
  run only): the real native job's systemd unit did not start (`local_job_boundary_unavailable`, reason
  `service_did_not_initialize`). The file passed 2 of 2 in the first full run and in two reruns right after the final
  run (`runs/claude_rec3_a103redo_001`, `_002`); not reproducible, no product file it uses changed between the runs.

Against the starting state: no test that passed before fails now. a102 has 6 fewer cases and a103 1 fewer (the deleted
`test_runtime_build_uses_private_monitor_task`); a103 is 4,330 passed + 1 failed with the rerun, against pa103's
4,331 + 1. No failure is inside the shared stubs: all per-home files that use `R/tests/` stubs pass.

Verified by reading only: every writer trace in sections 1 and 2; that no test under `tests/` or `R/tests/` names a
removed a102/a103 form literally (grep). Tests outside the two arms were NOT run.

Size of this step against the starting state (fixtures excluded): a102 168 files changed (16 test modules), 6 deleted,
1,204 lines removed, 444 added; a103 189 files changed (16 test modules), 6 deleted, 1,285 lines removed, 506 added.

Repository state: I made no git add or commit. Someone else committed checkpoint d7c6cf6f9 while this work was in
progress; it contains most of the edits above. Six files I changed after it are uncommitted: a102 `local_resources.py`,
`native_hmmer_preparation_result_publication.py`, `native_hmmer_preparation_result_worker.py`, `native_lifecycle.py`,
`shared_information.py`; a103 `shared_information.py`. The final test runs include them.
