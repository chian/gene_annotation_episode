# A103 per-file comparison against the 7e662ea29 baseline (2026-11-18)

Scope: the 98 baseline rows of `docs/verification_20261116/results_per_file.tsv` under
`gene_annotation_episode/episodic_workflow/root/a103/`. One row each in `a103.tsv` (this folder).
Each current file ran in its own pytest process through `tools/one_workflow.sh --slot pf103`
(empty HOME, blocked proxy); logs in `runs/pf103-01-*` to `runs/pf103-21-*`.

## Counts per status

| Status | Files | Baseline tests in those files |
|---|---|---|
| same | 1 | 2 |
| changed | 3 | 69 (54 remain, 15 gone) |
| retired | 93 | 4,256 |
| retired-unrecorded | 1 | 4 |
| regression | 0 | - |
| total | 98 | 4,331 (4,330 passed, 1 failed at baseline) |

Of the 4,331 baseline tests, 56 still exist and pass (2 + 6 + 37 + 11). The 1 baseline failure
(`test_a103_context.py::test_runtime_parent_receives_exact_component_operands_from_automatic_grading`)
was retired with a record, so no baseline failure remains.

The 93 retired files:

| Recorded reason | Files | Tests | Record |
|---|---|---|---|
| duplicate top-level tree deleted | 40 | 641 | `runs/claude_ablate/a103_retired.tsv` lines 2-15, 40-83 |
| legacy-root child tree (homology_job_monitoring) deleted | 1 | 45 | same file, lines 16-39 |
| drove the old Workflow/task layer, superseded by episode_runtime | 50 | 3,559 | same file, lines 84-132, 144 |
| fake tests (scripted stand-ins) | 2 | 11 | `runs/claude_ablate/a103_fake_tests.tsv` lines 3-13 |

## Regressions

None that reproduces. No test that passed at the baseline fails or errors now in a repeatable way.

One intermittent failure was seen and is not counted as a regression:
`episode_support/jobs/local_execution/gene_context_evidence/tests/test_operational_configuration.py::test_actual_native_receipt_and_machine_bounds`
failed in the first of 4 full-file runs (`runs/pf103-04-operational_configuration`) with
`AcquisitionError: local_job_boundary_unavailable`, raised at `native_lifecycle.py:312` in `resume_start`
(the transient unit was seen failed/inactive/not-found before its ready file appeared). The user journal for
that second shows the `gene-local-job-*` unit Starting, then Stopping/Stopped, while three other slots
(pf101, pf104, pf105) were starting workflows. It passed alone (`runs/pf103-18-...-rerun`) and in the next
three full-file runs (`runs/pf103-19`, `-20`, `-21`). `resume_start` is identical to 7e662ea29 apart from
import paths, so the cause is the start handshake under concurrent load, not the restructure. It is a real
test that launches `/bin/true` through the launcher, so it can fail again when several slots run at once.

## Retired-unrecorded

`gene_annotation_episode/episodic_workflow/root/a103/tests/test_homology_no_count_admission.py` (4 tests).
- 1 test is recorded: `test_launch_schema_allows_positive_selected_threads_without_count_maximum`,
  `runs/claude_ablate/a103_retired.tsv` line 142 (built legacy homology children through the deleted
  `homology_service_setup`).
- The other 3, `test_selected_threads_still_require_a_positive_integer[0]`, `[-1]`, `[True]`, have no record.
  They were still collected in `runs/fx103_collect1` and were gone, with the file, by `runs/rp103-collect-1`.
- Reason, from the code: they checked that a103 `HomologyJobs.order` rejects a non-positive or boolean `cpu`
  and writes no order row. The `HomologyJobs` class was deleted from the a103 copy of `homology_jobs.py` as a
  symbol no ported a103 episode reaches (`runs/rp103-remove-2/workflow-result.json` line 32; the file
  `episode_support/jobs/similarity_search/gene_context_evidence/homology_jobs.py` went from 555 to 64 lines),
  so the test had nothing left to test. The same check still runs against the a101 copy
  (`episode_support/jobs/similarity_search/sequence_homology_evidence/tests/test_homology_no_count_admission.py`).

## Changes inside surviving files that have no record row

These are in the three `changed` rows. Each is a deletion or an in-place edit that the retirement TSVs do not list.

1. `test_hpc_calculations.py` (7 -> 6): `test_shared_monitor_valuation_retains_possible_success_and_zero_wait_credit`
   is gone. Only prose covers it (`runs/claude_ablate/a103_results.md` line 39: "the rest drove the old runner").
   That reason does not match the baseline source: the test called only `hpc_prediction` and
   `hpc_monitoring.choose_schedule`. The a103 copy of `choose_schedule` was later deleted as unused
   (`runs/rp103-remove-2/workflow-result.json` line 33); the a102, a104 and a107 copies still have it.
2. `test_operational_configuration.py` (24 -> 11): 12 cases are recorded fakes; the 13th,
   `test_route_recommendation_uses_resources_not_count`, went when `compare_routes` was deleted from the a103
   copy of `execution_guidance.py` as unused (`runs/rp103-remove-1/workflow-result.json` line 36). No record row.
3. `test_operational_configuration.py::test_current_settings_reject_invalid[boolean]`: the input changed from
   `{'cpu_threads': True}` to `{'memory_bytes': True}`. At the baseline a103 had a private `local_resources.py`
   with a `cpu_threads` limit (default 1). That copy is gone; a103 now uses the shared
   `gene_annotation_episode.local_resources`, which limits only `memory_bytes` and `scratch_bytes`. So a103 no
   longer has a configured local CPU-thread limit, and `cpu_threads = 1` sits unread in
   `episode_support/configuration/gene_context_evidence/defaults.toml`. The only note is "now on the shared
   Store" (`a103_results.md` line 33).
4. `test_a103_context.py::test_parent_recomputes_original_scope_and_credit_reads_have_no_grading_side_effect`
   lost its 4 `NativeEvidenceRootCredit` assertions (root credit equals the A103 credit; A101 and A102
   components are 0) because `root/evidence_root` was deleted. Prose only (`a103_results.md` line 41).
5. `test_a103_context.py::test_protein_domain_traits_lift_to_original_nucleotide_codons` now passes
   `scope={'subject_refs':[target]}` to the `ToolRegistry` call. No record found.

## Where the records are

- Every a103 retirement and fake-test record is in `runs/claude_ablate/` (`a103_retired.tsv`, 143 rows;
  `a103_fake_tests.tsv`, 23 rows; `a103_results.md`). `docs/axis_restructure_20261117/retired_tests.tsv` and
  `retired_fake_tests.tsv` contain no a103 file rows. `runs/` is the disposable, git-ignored area.
- The 40 duplicate-tree rows say their head copy "remains". Each of those head copies was retired later in the
  same file (lines 84-123), so the wording is out of date; `a103.tsv` cites both lines for each.
- `test_a103_real_detection.py` (2 tests, 26.5 s at baseline) is recorded as fake for its scripted
  parent/decision fixture. It imported the real detection, homology-results and native-lifecycle code, so the
  owner may want to confirm that classification.

## Current test files with no baseline row (new tests)

13 files, 49 tests, all pass.

| File | Tests | Result | Run |
|---|---|---|---|
| episode_support/jobs/service_calls/gene_context_evidence/tests/test_monitor_commissioned_report_form.py | 5 | 5 passed | runs/pf103-05-monitor_commissioned_report_form |
| root/a103/gene_context_evidence/execution_job_submission/api_job_execution/tests/test_api_job_receipts.py | 1 | 1 passed | runs/pf103-06-api_job_receipts |
| root/a103/gene_context_evidence/execution_job_submission/api_job_execution/tests/test_appservice_api_job.py | 4 | 4 passed | runs/pf103-07-appservice_api_job |
| root/a103/gene_context_evidence/execution_job_submission/local_job_execution/tests/test_local_job_runtime.py | 5 | 5 passed | runs/pf103-08-local_job_runtime |
| root/a103/gene_context_evidence/execution_progress_assessment/tests/test_monitor_runtime.py | 1 | 1 passed | runs/pf103-09-monitor_runtime |
| root/a103/gene_context_evidence/execution_result_acquisition/tests/test_appservice_result_acquisition.py | 2 | 2 passed | runs/pf103-10-appservice_result_acquisition |
| root/a103/gene_context_evidence/execution_result_acquisition/tests/test_result_acquisition_runtime.py | 4 | 4 passed | runs/pf103-11-result_acquisition_runtime |
| root/a103/gene_context_evidence/hpc_work_planning/hpc_allocation_execution/tests/test_allocation_runtime.py | 3 | 3 passed | runs/pf103-12-allocation_runtime |
| root/a103/gene_context_evidence/hpc_work_planning/tests/test_hpc_runtime.py | 3 | 3 passed | runs/pf103-13-hpc_runtime |
| root/a103/gene_context_evidence/published_evidence_assessment/tests/test_literature_link.py | 2 | 2 passed | runs/pf103-14-literature_link |
| root/a103/gene_context_evidence/resource_work_submission/tests/test_resource_work_link.py | 6 | 6 passed | runs/pf103-15-resource_work_link |
| root/a103/gene_context_evidence/tests/test_head_runtime.py | 4 | 4 passed | runs/pf103-16-head_runtime |
| root/a103/gene_context_evidence/tests/test_report_form_and_received_files.py | 9 | 9 passed | runs/pf103-17-report_form_and_received_files |

Paths are relative to `gene_annotation_episode/episodic_workflow/`.

Surviving baseline files, for reference:

| Baseline file (under root/a103/) | Now (under episode_support/) | Baseline | Now |
|---|---|---|---|
| library/tests/test_hpc_calculations.py | jobs/hpc/gene_context_evidence/tests/test_hpc_calculations.py | 7 passed | 6 passed |
| tests/test_a103_channels.py | tools/tests/test_a103_channels.py | 2 passed | 2 passed |
| tests/test_a103_context.py | grading/gene_context_evidence/tests/test_a103_context.py | 37 passed, 1 failed | 37 passed |
| tests/test_operational_configuration.py | jobs/local_execution/gene_context_evidence/tests/test_operational_configuration.py | 24 passed | 11 passed (1 intermittent failure in 1 of 4 runs) |
