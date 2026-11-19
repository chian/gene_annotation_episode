# A102 per-file comparison with 7e662ea29 (18 November 2026)

Scope: the 92 rows of `docs/verification_20261116/results_per_file.tsv` whose path is under
`gene_annotation_episode/episodic_workflow/root/a102/` (4,940 tests: 4,924 passed, 5 failed, 11 skipped).
Per-file rows: `a102.tsv` in this folder. Current files were each run alone through
`tools/one_workflow.sh --slot pf102` with an empty HOME and a blocked proxy; run directories
`runs/pf102_cmp/f_0001` .. `f_0012` (file list `runs/pf102_cmp/files.txt`). No source or test file was changed.

## Counts per status

| status | files | baseline tests | now |
|---|---|---|---|
| same | 3 | 21 passed | 21 passed |
| changed | 1 | 44 passed | 20 passed |
| retired (recorded) | 85 | 4,604 (4,588 passed, 5 failed, 11 skipped) | none |
| retired-unrecorded | 3 | 271 passed | none |
| regression | 0 | | |

The 85 recorded retirements are: 34 files (500 tests) in the deleted top-level duplicate trees
(`a102/execution_job_submission`, `execution_progress_assessment`, `hpc_work_planning`), each checked at 7e662ea29
to differ from its `scientific_process/` counterpart only in the home-path lines; 37 head files (605 tests,
`scientific_process/` renamed `structural_homology_evidence/` by 5ec913e4c) retired with the old runner and as
fake tests; 14 files (3,499 tests) in `a102/tests` and `a102/library/tests`. The 5 baseline failures
(`test_a102_parent_coordination` 1, `test_literature_structure_integration` 4) and the 11 baseline skips
(`test_a102_native_workflow` 10, `test_a102_resource_workflow` 1) are all in retired files.

Of the 4,924 tests that passed at the baseline, 41 still exist and pass (21 same + 20 in the changed file).

## Regressions

None. Every test that exists now passes: 41 tests in the 4 baseline files that survive and 34 tests in 8 new files.

## Retired with no record (to be recorded)

All three belong to the A102 literature structural sheet (former A111: geometry and local fit of a deposited
structure model that a publication names). Their source modules were deleted with them, and none of the tested
functions exists anywhere in the tree now, so this is removed episode behaviour, not only removed tests.

| baseline file | baseline | what it tested | stated reason |
|---|---|---|---|
| `a102/tests/test_literature_structure_inputs.py` | 172 passed | `a102/literature_structure_inputs.py`: `read_structure_inputs`, `structure_population_schema` (reader of coordinate CIF and validation XML: exact atom selection, model/alt/insertion identity, RSCC join, byte custody of literals) | Deleted in the A102 reachability prune of 18 November because no ported binding imports the module (`runs/rp102-reach4/stdout.log`, `rp102-reach5/stdout.log`: module, `literature_structure_types` and the test listed UNREACHED). Last recorded state 172 passed (`runs/claude_ablate/a102_results.md` line 99). |
| `a102/tests/test_literature_structure_calculations.py` | 62 passed | `a102/literature_structure_calculations.py`: `populate_source_geometry` (six conditional geometry/local-fit components, inclusive thresholds, bounds under missing members, overflow/underflow handling) | Same prune (`runs/rp102-reach2/stdout.log`, `rp102-reach3/stdout.log`: module and test UNREACHED; gone by `rp102-reach4`). Last recorded state 62 passed (`a102_results.md` line 98). |
| `a102/tests/test_literature_structure_storage.py` | 37 passed | `a102/literature_structure_storage.py`: `LiteratureStructureRepository`, `structure_cells_schema` (populate with source receipts, scope, page lineage, atomic publication, saved-only replay, typed return rows) | 5 cases are recorded as fake (`runs/claude_ablate/a102_fake_tests.tsv` line 58). The other 32 have no row: the module imported the deleted old-runner `a102.communication` / `episode_bindings` (collection error at `a102_results.md` line 100) and was then deleted in the same prune (`rp102-reach2`, `rp102-reach3`). |

Why the modules became unreachable: at the baseline the A102 literature bindings reached them through
`structural_sheet_operations.py` (in each `published_evidence_assessment` home) and `a102_literature_bindings.py`.
The ported `structural_homology_evidence/published_evidence_assessment/literature_binding.py` has no structural
sheet operation; its credit is `A102StructuralCredit` over received records.

## Changed file: unrecorded parts

`a102/tests/test_operational_configuration.py` (44 passed) is now
`episode_support/jobs/local_execution/structural_homology_evidence/tests/test_operational_configuration.py` (20 passed).
The 24 removed cases are recorded (`runs/claude_ablate/a102_retired.tsv` line 43: 1 case; `a102_fake_tests.tsv`
lines 59-67: 9 functions, 23 cases). Two things are not covered by those records:

1. Edited input in 4 kept cases, ids and expected results unchanged: `test_current_settings_reject_invalid[boolean]`
   and `test_rejected_custom_initialization_preserves_all_existing_bytes[{new,empty_database,saved_current}-boolean]`
   pass `{'memory_bytes': True}` where the baseline passed `{'cpu_threads': True}`. Cause: A102's private
   `local_resources.py` (`shared_local_resources_v2`, `cpu_threads` a configured limit) was deleted and the test
   now imports `gene_annotation_episode.local_resources`, which changed since the baseline from v1 to
   `shared_local_resources_v3` (byte resources only; a `cpu_threads` setting is rejected as
   `invalid_local_resource_settings`). A102 local capacity therefore changed from v2 to v3. No row in the cited
   records states this.
2. Recorded cause does not match the test: `a102_fake_tests.tsv` line 61 lists
   `test_actual_native_receipt_and_machine_bounds` as fake (functions replaced by test lambdas). At 7e662ea29 it
   replaces nothing: it runs `/bin/true` through A102's `native_lifecycle.run_blocking` and asserts the verified
   cgroup `memory_max`, `memory_swap_max == 0` and a one-CPU quota. A102's `native_lifecycle.py` still exists
   (`episode_support/jobs/local_execution/structural_homology_evidence/`) with no such check; A103 kept the same
   test in its own `test_operational_configuration.py`.

## Recorded retirement whose reason is doubtful

`a102/library/tests/test_hpc_calculations.py` (7 passed): `docs/axis_restructure_20261117/retired_tests.tsv` lines
315-321 call it "old runner HPC checks". The 7 tests were calculation checks of A102's `hpc_prediction`,
`hpc_resource_prediction` and `hpc_monitoring`; those modules still exist in
`episode_support/jobs/hpc/structural_homology_evidence/`. The seven checks (measured resources against a fixed
validation set, censored survival quantiles, one physical attempt under two record ids, accounting units, forecast
portfolio value, conditioning, monitor valuation) have no direct counterpart now; the new `test_hpc_runtime.py` and
`test_allocation_runtime.py` reach `hpc_prediction` only through model fit and plan building. A103 and A104 kept a
rewritten `test_hpc_calculations.py` for their copies.

## Current test files with no baseline row (new)

All under `gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/`; 34 tests, all pass.

| file | result | run |
|---|---|---|
| `execution_job_submission/api_job_execution/tests/test_api_job_receipts.py` | 1 passed | `runs/pf102_cmp/f_0005` |
| `execution_job_submission/local_job_execution/tests/test_local_job_runtime.py` | 5 passed | `f_0006` |
| `execution_result_acquisition/tests/test_result_acquisition_runtime.py` | 4 passed | `f_0007` |
| `hpc_work_planning/hpc_allocation_execution/tests/test_allocation_runtime.py` | 7 passed | `f_0008` |
| `hpc_work_planning/tests/test_hpc_runtime.py` | 3 passed | `f_0009` |
| `published_evidence_assessment/tests/test_literature_link.py` | 4 passed | `f_0010` |
| `resource_work_submission/tests/test_resource_work_link.py` | 6 passed | `f_0011` |
| `tests/test_runtime_continuation.py` | 4 passed | `f_0012` |

## Where the records are

- Every A102 retirement and fake-test record except 30 rows lives only under `runs/claude_ablate/`
  (`a102_retired.tsv`, `a102_fake_tests.tsv`), which is disposable output. `docs/axis_restructure_20261117/`
  holds 30 A102 rows in `retired_tests.tsv` (lines 315-344) and none in `retired_fake_tests.tsv`.
- `a102_retired.tsv` and `a102_fake_tests.tsv` name head files by their `structural_homology_evidence/` path; the
  baseline names them `scientific_process/`. `a102.tsv` gives the mapping per row.
- Not test files, so not rows: `a102/tests/fixtures/bvbrc` (243 files), `fixtures/literature_structure` (3) and
  `fixtures/protein_structure_result_worker_393` (9) were noted as left in place in
  `runs/placement_tests/a102_after.txt` ("no test or module reads them") and are deleted now, with no later record.
