# A104 per-file comparison with 7e662ea29 (18 November 2026)

Scope: the 87 rows of `docs/verification_20261116/results_per_file.tsv` whose path is under
`gene_annotation_episode/episodic_workflow/root/a104/` (2,107 tests: 2,041 passed, 66 failed, 0 errors, 0 skipped).
Per-file rows: `a104.tsv` in this folder. Every current file was run alone through
`tools/one_workflow.sh --slot pf104` with an empty HOME and a blocked proxy; run directories
`runs/pf104_01_*` .. `runs/pf104_18_*` (each holds `junit.xml` and `stdout.log`). No source or test file was changed.

None of the 87 baseline paths exists any more. All 87 files are still at `befe24f6e` (HEAD, with
`scientific_process` renamed `evolutionary_history_evidence`); every later change is uncommitted, so "checked at
HEAD" below means compared with `git show HEAD:<path>`.

## Counts per status

| status | files | baseline tests | now |
|---|---|---|---|
| same | 5 | 77 passed | 77 passed |
| changed | 4 | 55 passed | 48 passed |
| retired (recorded) | 76 | 1,947 (1,881 passed, 66 failed) | none |
| retired-unrecorded | 2 | 28 passed | none |
| regression | 0 | | |

Of the 2,041 tests that passed at the baseline, 125 still exist and pass (77 same + 48 in the changed files).

The 76 recorded retirements are:
- 26 files (257 tests) in the deleted top-level duplicate trees (`a104/execution_progress_assessment`,
  `a104/hpc_work_planning`): `runs/claude_ablate/a104_retired.tsv` lines 2-27. Each was checked at HEAD to differ
  from its head-subtree copy only in the home path. Those head copies were retired later (next item).
- 29 head files (342 tests, `scientific_process/` at the baseline): fake tests
  (`runs/claude_ablate/a104_fake_tests.tsv` lines 2-79, shared helpers in
  `docs/axis_restructure_20261117/retired_fake_tests.tsv`) and tests of the deleted per-axis runner
  (`a104_retired.tsv` lines 28-50, 58).
- 21 files (1,348 tests) in `a104/tests`: fake tests (`a104_fake_tests.tsv` lines 80-174), cases for deleted
  duplicate homes (`a104_retired.tsv` line 59) and tests of the deleted per-axis runner (`a104_retired.tsv` lines
  51-57). The one baseline-failing file, `tests/proteome_partner/test_proteome_saved_host.py` (66 failed), is here:
  all nine of its functions were deleted as fake tests, so no passing test was lost with it.

## Regressions

None. No test that passed at the baseline now fails or errors: all 125 surviving tests and the 26 new tests pass.

## Retired-unrecorded files

1. `a104/tests/test_a104_evolutionary_episode.py` (22 passed at the baseline).
   - Recorded: 3 fake tests (`a104_fake_tests.tsv` lines 114-116).
   - Not validly recorded: the other 19 cases. They passed after the head port (`a104_results.md` line 78); the
     whole file was then deleted with the old runner. The only record is the prose list in
     `runs/claude_ablate/a104_results.md` line 115 ("Deleted tests (their subject was deleted)"), and that reason
     is wrong for most of them.
   - What the code shows: the file imported `a104_tools.catalog`, `a104_characterization.clade_sheet` and
     `a104_investigation`, which were deleted, so it could no longer be imported. But 14 of the 19 cases tested
     only code that still exists, and a 15th had one assertion on the deleted catalog:
     `prepare_request`, `request_body`, `native_body`, `commission`, `import_result`, `independent_marker_basis`
     (now `episode_support/jobs/hpc/evolutionary_history_evidence/hpc.py`), `validate_request`,
     `alignment_correspondence`, `tree_summary` (`.../hpc_worker.py`, byte-identical to the baseline module),
     `A104EvolutionaryCredit`, `A104PanelIdentityCredit`, `A104AlignmentSuitabilityCredit`, `A104RobustnessCredit`,
     `combine_received_task_progress` (`episode_support/grading/evolutionary_history_evidence/credit.py`).
   - Consequence: no current test file imports this axis's `hpc.py`, `hpc_worker.py` or `credit.py`. These are
     real tests (real Store, recorded YjeH inputs) of retained scientific code, lost without a true reason on record.
2. `a104/tests/test_no_count_resource_admission.py` (6 passed at the baseline).
   - Recorded: 5 fake tests (`a104_fake_tests.tsv` lines 148-152).
   - Unrecorded: `test_native_request_with_multiple_threads_retains_one_cpu_whole_window` was kept and passed
     (`a104_results.md` lines 95, 114), then the file disappeared before the placement step (absent from
     `runs/placement_tests/a104_before.txt`).
   - Reason worked out: the same test in the a101 and a105 copies is recorded as fake because it passes
     `SimpleNamespace(memory_bytes=1024)` as the job policy to `workflow_budget.native_budget`
     (`runs/claude_ablate/a101_fake_tests.tsv` line 363, `a105_fake_tests.tsv` line 73). The a104 copy has no row.

## Changed files

| baseline file | now | what went |
|---|---|---|
| `tests/test_a104_blast_utility_reader_views.py` 46 | 44 passed | 2 fake tests, recorded (`a104_fake_tests.tsv` lines 118-119) |
| `tests/test_a104_relationship_correspondence.py` 4 | 1 passed | 3 fake tests, recorded (`a104_fake_tests.tsv` lines 107-110); their subject `a104_interpretation.py` is deleted |
| `tests/test_canonical_workflow_resources.py` 4 | 2 passed | 2 tests deleted, **unrecorded for a104** |
| `tests/test_resource_policy_reopening.py` 1 | 1 passed | test rewritten and retargeted, **unrecorded** |

Unrecorded changes in detail:
- `test_canonical_workflow_resources.py` (now `tests/test_canonical_workflow_resources_evolutionary_history_evidence.py`):
  `test_actual_registry_constructor_uses_authenticated_run_resources` and
  `test_original_native_memory_bound_rejects_oversized_request_without_launch` are gone with no a104 row. The same
  two tests in the a101 and a105 copies are recorded as fake (SimpleNamespace stand-ins):
  `runs/claude_ablate/a101_fake_tests.tsv` lines 146-147, `a105_fake_tests.tsv` lines 12-13.
  Consequence: the `native_request_exceeds_environment_bounds` rejection in `workflow_budget.native_budget` has no
  test anywhere in the tree now.
- `test_resource_policy_reopening.py` (now `tests/test_resource_policy_reopening_evolutionary_history_evidence.py`):
  the baseline test used the fake `resources` fixture of `test_no_count_resource_admission` over the a104 copy of
  `local_resources.py` and asserted version `shared_local_resources_v2`. It now builds
  `gene_annotation_episode.local_resources.LocalResources` directly and asserts `shared_local_resources_v3`. The
  a104 copy is deleted; the shared module was changed in the working tree from v1 to v3 (settings validated before
  storage is opened; memory above the launcher bound now raises `local_resource_limits_exceed_environment_bounds`
  instead of being reduced to the bound). The count-field rejection is still asserted. Neither the rewrite nor the
  v3 change has a row in the restructure records.

## Recorded retirements whose record is weak

These rows have status `retired` because a record names the file and its reason holds against the code, but the
final deletion is written only as prose in `runs/claude_ablate/a104_results.md` lines 115-119 ("Deleted tests
(their subject was deleted)"), not as a TSV row. 23 files are affected.

No TSV row at all for the tests concerned (162 tests):
- `tests/test_monitor_hpc_presentation_policy.py`: 40 (whole file; old provider policy and prompt renderers, deleted)
- `tests/test_a104_results_preservation.py`: 54 remaining after fakes and duplicate-home cases
- `tests/test_a104_protected_reference_guards.py`: 30 remaining after duplicate-home cases
- `tests/test_a104_non_hpc_results_preservation.py`: 27 remaining
- `tests/test_a104_installed_result_readers.py`: 6 remaining
- `tests/test_a104_resume_adapter.py`: 1 (whole file; `tools/a104_resume_science.py` deleted)
- `tests/test_a104_appservice_saved_owner.py`: 1 remaining
- head `test_prompt_behavior.py` x3: 1 remaining each

A TSV row gives the cause ("shared helper builds the deleted per-axis runner", `a104_retired.tsv` lines 34-57) but
says "left in place"; the tests then passed again after the head port and their deletion is prose only (255 tests):
head `test_calculation_connections.py` x3 (15), `test_planning_allocation_behavior.py` x2 (26),
`test_prediction_behavior.py` (13), `test_prediction_prompt.py` (5); `tests/test_a104_native_execution_private.py`
(24), `test_a104_native_parent_contracts.py` (18), `test_a104_non_hpc_launch.py` (4),
`test_direct_native_parent_contracts.py` (20), `test_a104_results_boundaries.py` (6),
`test_source_presentation_policy.py` (124).

For each of these the subject was checked: the old per-home episode classes (`episode.py` under every head home
except `published_evidence_assessment`), `a104/runtime.py`, `episode_bindings.py`, `episode_journal.py`,
`episode_receipts.py`, `providers.py`, `decision_context.py`, `numerical.py`, `method_loop/` and the prompt modules
no longer exist under any name. Their replacement tests are the new files below.

Other notes:
- `test_credit_behavior.py` x3: `test_original_unit_validation_is_retained` (3 cases per file) has no row of its
  own; it is covered only by the whole-file row of the shared helper
  (`docs/axis_restructure_20261117/retired_fake_tests.tsv` line 1300).
- `library/tests/test_hpc_calculations.py` is `same` (7 passed), but it is a rewrite: the shared helper's seven
  test bodies were inlined as module-level functions (ids lost the `TestHpcCalculations::` prefix). The bodies match
  the helper at HEAD apart from module lookups. No a104 record of the rewrite was found.
- `runs/claude_ablate/a104_results.md` lines 35, 39 and 46 call three files "not in baseline"; all three have
  baseline rows (46, 76 and 4 tests).

## New test files in scope (no baseline row)

All under `gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/`; untracked; each run
alone (`runs/pf104_10_*` .. `runs/pf104_18_*`). 26 tests, 26 passed.

| file | tests | passed | failed | errors |
|---|---|---|---|---|
| `execution_job_submission/api_job_execution/tests/test_api_job_receipts.py` | 1 | 1 | 0 | 0 |
| `execution_job_submission/api_job_execution/tests/test_appservice_api_job.py` | 4 | 4 | 0 | 0 |
| `execution_job_submission/local_job_execution/tests/test_local_job_runtime.py` | 5 | 5 | 0 | 0 |
| `execution_result_acquisition/tests/test_appservice_result_acquisition.py` | 2 | 2 | 0 | 0 |
| `execution_result_acquisition/tests/test_result_acquisition_runtime.py` | 4 | 4 | 0 | 0 |
| `hpc_work_planning/hpc_allocation_execution/tests/test_allocation_runtime.py` | 3 | 3 | 0 | 0 |
| `hpc_work_planning/tests/test_hpc_runtime.py` | 2 | 2 | 0 | 0 |
| `published_evidence_assessment/tests/test_literature_link.py` | 4 | 4 | 0 | 0 |
| `tests/test_runtime_head_link.py` | 1 | 1 | 0 | 0 |

A tenth new file, `evolutionary_history_evidence/tests/test_runtime_bindings.py`, was written and removed during the
restructure; it is recorded in `docs/axis_restructure_20261117/retired_tests.tsv` lines 296 and 362.
