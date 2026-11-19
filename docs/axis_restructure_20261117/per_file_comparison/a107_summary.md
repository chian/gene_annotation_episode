# A107 per-file comparison with the 7e662ea29 baseline (18 November 2026)

Scope: the 93 rows of `docs/verification_20261116/results_per_file.tsv` under
`gene_annotation_episode/episodic_workflow/root/a107/`. One row each in `a107.tsv`.

Method: every current counterpart and every current A107 test file was run alone through
`tools/one_workflow.sh --slot pf107` (empty HOME, proxies blocked, no bytecode, `eatmydata`), run directories
`runs/pf107_cmp_01` .. `runs/pf107_cmp_24`. Test ids were compared with the baseline JUnit files
(`runs/claude_f4a_s0..3/junit`). Each cited record was checked against the 7e662ea29 source of the file.
Code and tests were not changed.

## Counts per status

| status | files | baseline tests (passed / failed) | now |
|---|---|---|---|
| same | 11 | 553 (553 / 0) | 553 passed |
| changed | 3 | 500 (499 / 1) | 146 passed in 3 files |
| retired (record cited) | 76 | 1,079 (1,048 / 31) | - |
| retired-unrecorded | 3 | 29 (29 / 0) | - |
| regression | 0 | - | - |
| total | 93 | 2,161 (2,129 / 32 / 0 errors) | 699 passed, 0 failed, 0 errors in 14 files |

Retired, by record:

| group | files | baseline tests | record |
|---|---|---|---|
| top-level duplicate trees (`a107/execution_progress_assessment`, `a107/hpc_work_planning`) | 28 | 306 | `runs/claude_ablate/a107_retired.tsv:2-29` |
| head tests deleted as fake (`scientific_process/...`, renamed `partner_presence_evidence/...`) | 27 | 305 | `runs/claude_ablate/a107_fake_tests.tsv:2-24, 26-29` (+ `a107_retired.tsv:31`) |
| head HPC tests runnable only through the deleted runner protocol | 6 | 66 | `a107_retired.tsv:38-43` |
| `a107/tests` files deleted as fake | 12 | 368 | `a107_fake_tests.tsv:30-36, 38-41, 43` (+ `a107_retired.tsv:34-37`) |
| `tests/test_private_reconstruction.py` | 1 | 12 | `a107_retired.tsv:30` |
| recorded only in prose (see below) | 2 | 22 | `runs/claude_ablate/a107_results.md:91, 108` |

## Regressions

None. No test that passed at the baseline fails or errors now. All 730 tests in the 24 current files pass.

The 32 baseline failures (8 `test_launch_connected` cases in 4 files, 7 in `test_literature_partner_native_integration`,
9 in `test_literature_partner_integration`, 2 in `test_literature_partner_defined_integration`, 5 in
`test_literature_partner_assessments`, 1 in `test_literature_structural_scalar_contexts`) were all in tests deleted as
fake or with a duplicate tree. None was fixed; none remains.

## Retired-unrecorded files

No record names these three deletions. Reasons below are worked out from git and the code.

1. `a107/tests/test_native_thread_metadata.py` (3 passed at the baseline).
   - Tested: `LocalResources` treats a supplied `cpu_threads` setting as inert descriptor metadata (2 cases);
     `native.resume_start` rejects a released handle whose `whole_workflow_budget` window differs, before any event
     registration (1 case).
   - Reason: fake test. Both tests run on canned host probes: the `capacity` fixture (monkeypatched
     `_resource_id`/`_boot`/`_process_start`, `native._properties`/`_control`) and a `prepared` fixture whose
     `native._control`/`_properties` are lambdas returning `SimpleNamespace`. The byte-identical A110 copy is recorded
     as fake at `runs/claude_ablate/a110_fake_tests.tsv:116`; A107 has no row.
   - Timing: 3 passed in `runs/claude_ablate/a107_results.md:109`; absent from `runs/fx107b_tools/collect1.txt` (13:49
     on 18 November).
   - The code under test still exists (`episode_support/jobs/local_execution/partner_presence_evidence/native_lifecycle.py`,
     `gene_annotation_episode/local_resources.py`).
2. `a107/tests/test_retained_molecular_contracts.py` (16 passed at the baseline).
   - Tested: A107's private molecular-sequence result contracts: retained publication bytes (payload, read order,
     rejection of changed length/digest/metadata), the protease assay context schema and error identities, the
     calibrated-signal selection schema, primer operand forms, duplicate references and missing source files.
   - Reason: the modules under test were deleted from A107. `a107/molecular_sequence_result_contracts.py` and
     `a107/library/{calibrated_signal_selection,primer_placement_result_contracts,protease_assay_context,molecular_publication_bytes}.py`
     have no row in `runs/placement_plan/placement.tsv` and no file in the tree. Their only non-test importers were the
     molecular-sequence execution stack, whose driver was deleted in the second port (`a107_results.md:108`).
   - Not a fake test (no stand-ins). It went with the code.
   - Timing: collected at 13:49 (`runs/fx107b_tools/collect1.txt:712-727`), absent at 17:41
     (`runs/placement_move/a107_collect_before`).
   - The generic contracts remain in `gene_annotation_episode/` (`molecular_sequence_result_contracts.py`,
     `primer_placement_result_contracts.py`, `calibrated_signal_contracts.py`).
3. `a107/tests/test_retained_native_request_contracts.py` (10 passed at the baseline).
   - 2 cases are recorded in prose (`a107_results.md:112`: the lumpy/macs2 request-binding check went with those
     bindings). The deletion of the file with its other 8 cases has no record.
   - The 8 tested: saved control JSON keeps duplicate-key, NaN/Infinity and encoding failures and preserves nested
     nulls and array order (5); a saved seal retains failed and not-run outcomes (2); original control bytes
     authenticate digest and request without path reads (1).
   - Reason: `a107/library/{lumpy_request_contracts,macs2_request_contracts,atac_control_json}.py` were deleted from
     A107 (no placement row, no file). Their only non-test importers were the deleted lumpy/macs2 request bindings and
     `library/received_execution_information/historical_*`.
   - Not a fake test. It went with the code. `atac_execution_contracts.py` survives at
     `episode_support/forms/expression_and_perturbation/` without this test.
   - Timing: collected at 13:49 (`collect1.txt:728-735`), absent at 17:41.

## Changed files

| baseline file | baseline | now | cause |
|---|---|---|---|
| `tests/test_literature_structural_scalar_contexts.py` | 135 (134 / 1) | 132 passed | 3 fake cases deleted (`a107_fake_tests.tsv:42`), including the one baseline failure |
| `tests/test_local_resource_count_free.py` | 6 passed | 5 passed | 1 fake test deleted, **unrecorded for A107** (the A110 copy is at `a110_fake_tests.tsv:143`): `test_capacity_quantities_admit_multiple_rows_without_count_gate` and its `capacity` fixture |
| `tests/test_private_literature_tasks.py` | 359 passed | 9 passed in `test_literature_partner_population.py` | 175 cases with the 7 duplicate homes (`a107_retired.tsv:32-33`); 161 fake cases (`a107_fake_tests.tsv:44`); 14 presentation cases deleted and 9 population cases moved (prose only, `a107_results.md:103, 110`) |

## Gaps in the records

- **A107 has no rows in the documented record.** `docs/axis_restructure_20261117/retired_tests.tsv` and
  `retired_fake_tests.tsv` contain none of the A107 retirements above. They exist only in
  `runs/claude_ablate/a107_retired.tsv` and `a107_fake_tests.tsv`, under the disposable `runs/` directory. The one A107
  row in the documented record is `retired_tests.tsv:364` (`a107/tests/test_head_cycle.py`, created and removed after
  the baseline).
- **Recorded only in prose** (`runs/claude_ablate/a107_results.md`, second-port table), with no TSV row:
  - `library/tests/test_hpc_calculations.py`, 7 tests (line 91): shell over the deleted shared
    `root/tests/hpc_calculation_behavior`.
  - `tests/test_molecular_sequence_ordinary_primer_owner.py`, 15 tests (line 108): drove the deleted
    `molecular_sequence_ordinary`.
  - `tests/test_genuine_result_worker_boundaries.py`, the 6 non-fake cases (line 94): FBA / genomic-overlap result
    workers and receipts deleted.
  - `tests/test_private_literature_tasks.py`, 14 presentation cases (line 110).
  - `tests/test_retained_native_request_contracts.py`, 2 lumpy/macs2 binding cases (line 112).
- **Statements in `a107_retired.tsv` that no longer hold:**
  - Rows 2-29 say the head copy under `partner_presence_evidence/` keeps the same tests. Every one of those head
    copies was deleted later (27 as fake, 6 with the runner protocol).
  - Rows 38-43 say the HPC calculation logic stays covered by `library/tests/test_hpc_calculations.py`. That file was
    deleted later, so `episode_support/jobs/hpc/partner_presence_evidence/hpc_prediction.py` and
    `hpc_resource_prediction.py` have no calculation test. The A103 and A104 copies have their own rewritten
    `test_hpc_calculations.py`.
- `a107_results.md` lines 107 and 109 still show `test_local_resource_count_free.py` at 6 and
  `test_native_thread_metadata.py` at 3; both changed after that table was written.

## Same files

11 files moved from `a107/tests/` to `episode_support/<function>/tests/` with identical test ids and all passing.
Test-body edits besides import paths, all from the move to the shared Store and A107's `LiteratureContext`:

- `store.validate_scope()` now receives `{'subject_refs': store.problem()['subject_refs']}` in
  `test_a107_reference_cds_witnesses.py`, `test_component_identity_regions.py` and the three `*_storage.py` files.
- `LiteratureContext` replaces the deleted `episode_bindings.BindingContext` (one positional argument fewer) in the
  three `*_storage.py` files.
- `test_component_identity_regions.py` reads its fixtures from
  `episode_support/tools/sequence_and_context_sources/tests/fixtures/a107_evaluation`.

## Current test files with no baseline row

All pass. Paths are relative to `gene_annotation_episode/episodic_workflow/`.

| file | tests | passed |
|---|---|---|
| `root/a107/partner_presence_evidence/execution_job_submission/api_job_execution/tests/test_api_job_receipts.py` | 1 | 1 |
| `root/a107/partner_presence_evidence/execution_job_submission/api_job_execution/tests/test_appservice_api_job.py` | 4 | 4 |
| `root/a107/partner_presence_evidence/execution_job_submission/local_job_execution/tests/test_local_job_runtime.py` | 5 | 5 |
| `root/a107/partner_presence_evidence/execution_result_acquisition/tests/test_appservice_result_acquisition.py` | 2 | 2 |
| `root/a107/partner_presence_evidence/execution_result_acquisition/tests/test_result_acquisition_runtime.py` | 4 | 4 |
| `root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/tests/test_allocation_runtime.py` | 3 | 3 |
| `root/a107/partner_presence_evidence/hpc_work_planning/tests/test_commissioned_report_form.py` | 3 | 3 |
| `root/a107/partner_presence_evidence/hpc_work_planning/tests/test_hpc_runtime.py` | 2 | 2 |
| `root/a107/partner_presence_evidence/published_evidence_assessment/tests/test_literature_link.py` | 2 | 2 |
| `episode_support/jobs/service_calls/partner_presence_evidence/tests/test_monitor_commissioned_report_form.py` (was `a107/library/tests/`) | 5 | 5 |
| total | 31 | 31 |

`episode_support/literature/inputs/tests/test_literature_partner_population.py` (9 passed) is not new behaviour: it
holds the 9 population cases of the baseline `tests/test_private_literature_tasks.py`, with the same ids.
