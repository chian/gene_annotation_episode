# A110 per-file comparison with the 7e662ea29 baseline (18 November 2026)

Scope: the 95 baseline rows of `docs/verification_20261116/results_per_file.tsv` under
`gene_annotation_episode/episodic_workflow/root/a110/` (1,458 tests: 1,438 passed, 20 failed, 0 errors).
Table: `a110.tsv` in this folder, one row per baseline row.

## Result

| status | files | tests at baseline |
|---|---|---|
| same | 0 | 0 |
| changed | 1 | 6 |
| retired (every test covered by a record) | 70 | 988 |
| retired-unrecorded (at least one test has no record) | 24 | 464 (367 of them with no record) |
| regression | 0 | 0 |

- One baseline file still exists: `tests/test_local_resource_count_free.py`, moved to
  `episode_support/jobs/local_execution/biochemical_feasibility_evidence/tests/`. 6 -> 5 tests, all 5 pass;
  the sixth was deleted as fake (recorded).
- No regression: no test that passed at the baseline fails or errors now. Every current test file in scope passes.
- Of the 1,458 baseline tests: 5 still run and pass; 1,086 are covered by a fake-test or retirement record;
  **367 were deleted with no record that names them** (24 files).
- None of the 20 baseline failures was fixed. All 20 were deleted as fake or retired with their file
  (8 in four `test_launch_connected.py` files, 4 in `test_literature_reaction_integration.py`, 6 in
  `test_literature_reaction_native_integration_129.py`, 1 each in `test_literature_reaction_meanings_integration.py`
  and `test_literature_reaction_native_primary_129.py`).

## Regressions

None.

## Retired with no record

### A. Reaction-population code and its tests, deleted together (7 files, 283 tests)

These tests were real, passed at the baseline, and still passed at the last recorded sweep
(`runs/claude_ablate/a110_results.md`, r2110 table; `runs/claude_r2110_t7/stdout.log`: 296 passed, 1 failed).
They were deleted afterwards together with the code they tested. No record of that step exists.

| baseline file | tests with no record | code under test (now absent from the tree) |
|---|---|---|
| `tests/test_literature_reaction_calculations.py` | 69 of 69 | `a110/library/literature_reaction_calculations.py` (`populate_reaction_constraints`, `FORMULAS`), `a110/literature_experimental_contracts.py` |
| `tests/test_literature_reaction_inputs.py` | 120 of 120 | `a110/library/literature_reaction_inputs.py` (`read_reaction_inputs`, `reaction_population_schema`) |
| `tests/test_literature_reaction_native_inputs_129.py` | 27 of 27 | `a110/library/literature_reaction_native_inputs.py` (`read_native_reaction_selection`), `literature_assay_inputs.py` |
| `tests/test_literature_reaction_native_identity_129.py` | 4 of 4 | `a110/library/literature_reaction_native_inputs.py`, `reaction_native_observations.py` |
| `tests/test_literature_reaction_storage.py` | 46 of 47 | `a110/literature_reaction_storage.py` (`LiteratureReactionRepository`), `library/reaction_population_contracts.py`, `library/reaction_report_contracts.py` |
| `tests/test_literature_reaction_meanings.py` | 15 of 17 | `a110/library/literature_reaction_meanings.py`, `literature_reaction_storage.py` |
| `tests/test_received_selector_boundaries.py` | 2 of 8 | `a110/protein_structure_selection.py` (a shared copy exists at `episode_support/readers/protein_structure/protein_structure_selection.py`; no test names its selector functions) |

Stated reason (worked out from run output, not from a record): a reachability prune of `root/a110` on
18 November (slot `rp110`, about 14:53-15:18) deleted every A110 module that no A110 binding (`home.py`,
`episode.py` under `biochemical_feasibility_evidence/`) and no non-test code outside A110 imports, and the test
files that tested only those modules. Evidence: `runs/rp110-scan3/stdout.log` and `runs/rp110-scan4/stdout.log`
list the modules as "UNREACHABLE from non-test code"; `runs/rp110-scan5/stdout.log` no longer lists them;
`runs/rp110-test1/stdout.log` shows 27 tests left where the previous sweep had 297.

This is a removed behaviour, not only removed tests: reading, calculating, storing and replaying A110 reaction
populations (reaction-constraint calculations, native reaction inputs, the reaction repository over the shared
Store) no longer exists anywhere in the tree. `populate_reaction_constraints`, `read_reaction_inputs`,
`read_native_reaction_selection` and `LiteratureReactionRepository` are not found under `gene_annotation_episode/`,
`tests/` or `episode_runtime/`. The current A110 literature binding
(`biochemical_feasibility_evidence/published_evidence_assessment/literature_binding.py`, 66 lines) offers source
acquisition and instruction text only.

### B. Head-subtree tests deleted with the old runner (17 files, 84 tests with no record)

`runs/claude_ablate/a110_results.md` (r2110 section) says "all other former a110 test files: deleted, tested the
deleted design; each listed in a110_retired.tsv with its reason". `a110_retired.tsv` has no row for these files.
Their fake tests are recorded; the remaining tests are not.

| baseline file (under `scientific_process/`) | homes | tests with no record, per file | what they tested |
|---|---|---|---|
| `.../execution_progress_assessment/tests/test_credit_behavior.py` | 3 | 3 of 8 | old monitor binding refuses a missing, zero or infinite information unit; inherited from the deleted shared helper `root/tests/monitor_credit_behavior.py` |
| `.../execution_progress_assessment/tests/test_progress_task.py` | 3 | 4 of 9 | old `MonitorEpisode`: invalid executed operations keep an invalid outcome; yield settings and descriptor |
| `.../execution_progress_assessment/tests/test_prompt_behavior.py` | 3 | 1 of 9 | old monitor prompt renderer keeps requested facts and omits unrequested ones |
| `hpc_work_planning/{,hpc_allocation_execution/,hpc_resource_prediction/}tests/test_calculation_connections.py` | 3 | 5 of 5 | old `HPCEpisode` uses the axis model and ledger scorer, authenticates its ledger, replays completed observations |
| `hpc_work_planning/{,hpc_allocation_execution/}tests/test_planning_allocation_behavior.py` | 2 | 13 of 19 | old HPC planning/allocation binding: plan replay, launch reservation, missing handoff repair, shared obligation credit, ready-result credit |
| `hpc_work_planning/hpc_resource_prediction/tests/test_prediction_behavior.py` | 1 | 13 of 13 | old prediction binding: parent authentication, candidate identity, validation/training separation, model mathematics, report credit |
| `hpc_work_planning/hpc_resource_prediction/tests/test_prediction_prompt.py` | 1 | 5 of 18 | old prediction prompt rendering: candidate identity bytes, provider frames, requested report facts |
| `hpc_work_planning/hpc_resource_prediction/tests/test_prediction_task.py` | 1 | 1 of 10 | old prediction task keeps original exception identities |

Stated reason: all of these drove the old per-axis runner (`a110.episode_bindings.BindingContext`, `a110.runtime`,
the old `MonitorEpisode`/`HPCEpisode` classes), mostly through shared helpers in `root/tests/` that are now deleted.
The runner was deleted and the axis rebuilt on `episode_runtime` on 18 November (r2110). The rebuilt bindings have
new tests (listed below), but no record establishes which of the old behaviours were carried over. The same shells
in A102 are recorded in `docs/axis_restructure_20261117/retired_tests.tsv` (rows 322-344); A110 has no such rows.

Code that these tests reached and that still exists without a test naming it:
`explicit_positive_monitoring_information_unit_required`
(`episode_support/grading/biochemical_feasibility_evidence/progress_information_credit.py`);
`monitor_observation_expands_requested_fields` and `monitor_progress_not_received`
(`episode_support/jobs/service_calls/biochemical_feasibility_evidence/monitor_runtime.py`).

## Record defects found while checking

- `docs/axis_restructure_20261117/retired_tests.tsv` has no A110 row; `retired_fake_tests.tsv` has 57 A110 rows
  (inherited shared-helper checks only). All other A110 records are in `runs/claude_ablate/a110_retired.tsv` (54 rows)
  and `runs/claude_ablate/a110_fake_tests.tsv` (155 rows), which sit in the disposable `runs/` directory.
- `a110_retired.tsv` rows 2-29 say of each duplicate-tree file "the head subtree copy of this file is retained
  and run". All 28 head-subtree copies were deleted later.
- `a110_results.md` says every other deleted file is listed in `a110_retired.tsv`; 17 are not (group B).
- `library/tests/test_hpc_calculations.py` (7 tests) is recorded as retired because its shared helper imported
  deleted runner code. The calculation code it tested still exists
  (`episode_support/jobs/hpc/biochemical_feasibility_evidence/hpc_prediction.py`, `hpc_resource_prediction.py`,
  identical to the A103 copy apart from the axis name). A103 and A104 kept a standalone port of these checks
  (`episode_support/jobs/hpc/gene_context_evidence/tests/test_hpc_calculations.py`, 6 tests); A110 has none.

## Current test files with no baseline row

All run on 18 November, each in its own pytest process (`runs/pf110_cmp_1` .. `runs/pf110_cmp_8`).

| file | tests | passed | failed | errors |
|---|---|---|---|---|
| `root/a110/biochemical_feasibility_evidence/execution_job_submission/local_job_execution/tests/test_local_job_runtime.py` | 5 | 5 | 0 | 0 |
| `root/a110/biochemical_feasibility_evidence/execution_result_acquisition/tests/test_result_acquisition_runtime.py` | 4 | 4 | 0 | 0 |
| `root/a110/biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/tests/test_allocation_runtime.py` | 4 | 4 | 0 | 0 |
| `root/a110/biochemical_feasibility_evidence/hpc_work_planning/tests/test_hpc_runtime.py` | 2 | 2 | 0 | 0 |
| `root/a110/biochemical_feasibility_evidence/tests/test_axis_runtime.py` | 4 | 4 | 0 | 0 |
| `root/a110/biochemical_feasibility_evidence/tests/test_head_runtime.py` | 4 | 4 | 0 | 0 |
| `episode_support/jobs/service_calls/biochemical_feasibility_evidence/tests/test_monitor_report_facts.py` (moved from `a110/library/tests/`) | 1 | 1 | 0 | 0 |

Total new: 7 files, 24 tests, all pass. With the moved baseline file (5 tests) A110 now has 8 test files and 29 tests.

## How the comparison was made

- Baseline paths use `a110/scientific_process/...`; commit 97308b94c renamed that folder to
  `a110/biochemical_feasibility_evidence/...` with identical per-file results (README, step P1-A110).
- Per-test ids at that commit come from the junit files of `runs/claude_ax_a110_s0` .. `s3` (1,458 ids, equal to
  the baseline total). Each id was matched against the record rows; "N of M" counts in `a110.tsv` are id counts.
- Row numbers cited in `a110.tsv` are line numbers in the cited file, with the header as row 1.
- Everything after 97308b94c is uncommitted, so git shows only that files were deleted, not when or why. Order of
  events was taken from `runs/claude_ablate/a110_results.md` and from run directories (`claude_ab110_*`,
  `claude_pt110_*`, `claude_r2110_*`, `rp110-*`, `placement_move/a110_*`, `placement_tests/a110_*`).
- No source or test file was changed.
