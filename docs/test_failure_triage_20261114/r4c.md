# r4c: a101/tests failures with no recorded cause (final run `claude_tests_final_20261114_05`)

Work list: `runs/claude_summary_final_20261114_05/unrecorded_r4c.tsv` — 71 groups, 251 failing cases, 19 distinct
messages, 14 test modules, all in `gene_annotation_episode/episodic_workflow/root/a101/tests`.
Per-message causes: `r4c_causes.tsv` (19 rows, sums to 251). Every row has a cause.

Result: 72 of the 251 cases now pass through test-side fixes; 179 are left failing with a recorded cause
(121 product gap, 53 missing untracked input, 3 product defect, 2 stale test). The same fixes also cleared 81
further cases in the same files that carried other recorded causes (see "Recorded causes that were wrong").

Paths: `A` = `gene_annotation_episode/episodic_workflow/root/a101`, `T` = `A/tests`.

## Causes

| # | Cause | Class | Cases (work list) | Evidence | Action | Scientific? |
|---|---|---|---|---|---|---|
| R1 | r2a cause 5, confirmed as this failure. The tests call root `ExecutionServiceFactory` and pass its descriptors (binding id `root_execution_job_submission`) to `a101.runtime.Workflow`. a101's private table only knows `execution_job_submission...` ids, so composition raises `unavailable_binding`. a101 has no `execution_service_setup`, `execution_episodes` or `execution_binding_catalogue`, and no product code in a101 constructs `EpisodeApplicationServices` | product_defect | 121 (113 setup errors + 8 failures; 6 modules: `test_native_hmmer_preparation_nested_workflow` 76, `test_blast_native_execution_workflow` 19, `test_native_blast_masking_workflow` 12, `test_native_mask_conversion_workflow_641` 9, `test_native_blast_utility_workflow_634` 3, `test_hmmer_model_format_workflow` 2) | All 121 tracebacks have `path = 'root_execution_job_submission'` -> `LookupError: private_episode_binding_not_defined` (`A/private_binding_factories.py:10`) -> `A/episode_composition.py:144,177`, called from `A/runtime.py:1146`. Root record id: `root/execution_job_submission/episode.py:105`; a101 record id: `A/execution_job_submission/binding_record.py:8`. Test call sites e.g. `T/test_native_blast_masking_workflow.py:25,116,185-189` | Left failing. Needs an a101 service factory (product) or an owner decision that these tests drive the root `Workflow` (r2a owner question 2). Behind it, read only: the same tests build root `ExecutionEpisodes` as `owner` and put a 20 GiB policy in the resources (R5 would follow) | No |
| R2 | The test reads retained grading output from the git-ignored `verification/tool_graders_hmmer_preparation_results_2026-10-26_273/check003/temporary/`. That directory no longer exists: `check003` holds only `intent.json`, `junit.xml`, `receipt.json` and logs (directory changed 2026-10-30). Nothing tracked provides it | environment | 53 (`test_native_hmmer_preparation_returns`: consensus_simple 49, hmmconvert/binary 3, hmmpress/index 1) | `T/test_native_hmmer_preparation_returns.py:38,67-75`; `.gitignore:12` (`/verification/`); `git ls-files verification` is empty | Left failing, nothing faked. What is needed: `test_all26_modes_retain_grade_{7,11,17}` (`grading/native-hmmer-preparation-grading/{prepared,grading}.json` and `store/artifacts`), about 3.4 MB. A full copy survives, also untracked, under `verification/tool_graders_hmmer_model_formats_2026-10-27_511/check003/source_snapshot/verification/tool_graders_hmmer_preparation_results_2026-10-26_273/check003/temporary` (41 MB). Diagnostic with the path temporarily pointed there: 53 pass, 1 fails for R4 (run 018); with R4 fixed 54/54 (run 019). Path restored afterwards. OWNER QUESTION 1 | No |
| R3 | r2c C05 in a file it did not cover: the test imported the top-level `gene_annotation_episode.domain.ContractError`; `a101_investigation` raises `a101.domain.ContractError`, so `pytest.raises` never matched | test_wiring | 2 (`test_a101_investigation`) | `T/test_a101_investigation.py:11`; `A/a101_investigation.py:106,127` | Fixed (import line). Run 008: both pass | No |
| R4 | The per-form authentication snapshot is shared only when the context is exactly `root.receiving_context.BindingContext` (the class all a101 code uses, 33 imports). The test built contexts from the top-level `gene_annotation_episode.episode_bindings.BindingContext`, so the facts were read 6 times instead of once | test_wiring | 1 (`test_blast_native_return_admission`) + 1 hidden behind R2 | `A/form_reference_validation.py:15,61`; `A/episode_bindings.py:51`; `T/test_blast_native_return_admission.py:17` | Fixed: import re-pointed to `a101.episode_bindings.BindingContext` (same class object) in that file (run 009: 39 passed) and in `T/test_native_hmmer_preparation_returns.py:20` (verified in run 019) | No |
| R5 | r2c C04, for policies that belong to the test itself. The test asks 20 GiB for its own grading / result worker job; `workflow_budget.native_budget` refuses anything above the 5 GiB environment bound, the worker never starts, preparation returns no sheet, and the test then fails on the missing sheet with five different messages. No product code and no retained record pins this value: `validate_original_bundle` checks only the shape of the policy, and the retained bundles do not contain it | stale_test | 69 (`test_blast_pairwise_publication` 27, `test_native_blast_hsp_sites` 21, `test_native_hmmer_publication` 20, `test_native_blast_masking_host_returns` 1) | `gene_annotation_episode/workflow_budget.py:35,118-121`. Runs 001-004: every worker receipt / saved `prepared.json` is `whole_workflow_budget_unavailable` (reason `native_request_exceeds_environment_bounds`): 55, 24, 36 and 7 records. Precedent written by the original author, same situation: `T/test_native_blast_masking_results_616.py:362-364` | Fixed: the three test-owned policies now use `workflow_budget.ENVIRONMENT_BOUNDS['memory_bytes']` (`T/test_blast_pairwise_publication.py`, `T/test_native_hmmer_publication.py`, `HostCase` in `T/test_native_blast_masking_host_returns.py`). All 69 pass. Not applied to the shared `POLICY` of `T/test_native_blast_masking_invocation.py`, nor to retained plans | No (resource request; no assertion changed) |
| R6 | r2c C10: `native_driver_runtime._source_closure` cannot resolve imports of the moved `a101/library` modules, so the result worker preparation fails with `native_dependency_unavailable` | product_defect | 3 (`test_native_hmmer_preparation_results`) | `A/native_driver_runtime.py:203-214`; saved `prepared.json` and `projection-failure.json` of run 007 carry `native_dependency_unavailable` for all three, including the artifact-only case, whose injected grading failure is followed by the real projection worker | Left failing (product; options in r2c C10). The retained plan behind it carries a 20 GiB policy, so r2c C04 follows | No |
| R7 | The test fills model-verdict claim fields (`family`, `activity`) of `initial_report()` and `report_schema()`. Both return only the host-recorded fields (`records`, `sequence_credit`); the claims exist only in `legacy_report_schema`. Code identical at 078b77668, so these two failed before the reorganisation | stale_test | 2 (`test_a101_investigation`, `KeyError: 'family'`) | `A/a101_investigation.py:35-62`; `git show 078b77668:gene_annotation_episode/a101_investigation.py` lines 91-102; `git show 078b77668:tests/test_a101_investigation.py` lines 90, 111 | Left failing. OWNER QUESTION 2 | Yes (which report contract is tested) |

Also fixed while verifying R5, not a work-list message: `T/test_native_blast_hsp_sites.py:131-135` patched
`"gene_annotation_episode." + target` for five functions that now live in `A/native_blast_result_worker.py` and
`A/library/{blast_report_collection,blast_pairwise_results,blast_hsp_site_calculators}.py` (the copies a101 product code
imports). Targets re-pointed; the guard test passes (run 014).

## Recorded causes that were wrong (found by rerunning)
In the files fixed by R5, 81 further failing cases were outside my work list because their message matched a cause
recorded for another cluster. They had the same cause, R5 (one also needed the patch-target fix above), and now
pass. Some of those records were right (r2c: "blocked by C04"). Others were wrong joins on a generic message, e.g.
in `test_native_blast_masking_host_returns`: `TypeError: 'NoneType' object is not subscriptable` (recorded r2d,
product_defect, "pin owner question"), `IndexError: list index out of range` (r2f, product_defect),
`StopIteration` (r2e, stale_test), `AttributeError: 'NoneType' ... startswith` (r2f); and the single case of
`test_native_blast_masking_generated_partial_admission` (r2d, product_defect), which uses `HostCase`.
A generic message shared with another module does not carry that module's cause.

## Before / after (11 files rerun: 7 edited, 4 dependents)

| File | before passed / failing | after passed / failing | runs |
|---|---|---|---|
| test_blast_pairwise_publication | 3 / 52 | 55 / 0 | 001, 013 |
| test_native_blast_hsp_sites | 0 / 54 | 54 / 0 | 002, 014 |
| test_native_hmmer_publication | 1 / 36 | 37 / 0 | 003, 015 |
| test_native_blast_masking_host_returns | 2 / 6 | 8 / 0 | 004, 025 |
| test_a101_investigation | 4 / 4 | 6 / 2 (R7) | 005, 008 |
| test_blast_native_return_admission | 38 / 1 | 39 / 0 | 006, 009 |
| test_native_hmmer_preparation_returns | 1 / 53 | 1 / 53 (R2; same failing set) | 020 |
| test_native_hmmer_preparation_results (imports `SavedReturns`) | 10 / 8 | 10 / 8 (same failing set) | 007, 022 |
| test_native_blast_masking_generated_partial_admission (uses `HostCase`) | 0 / 1 | 1 / 0 | 023, 026 |
| test_native_blast_masking_saved_status_623 (uses `HostCase`) | 0 / 1 | 1 / 0 | 024, 027 |
| test_hmmer_native_result_views (imports `selector`; passed before) | 13 / 0 | 13 / 0 | 017 |
| total | 72 / 216 | 225 / 63 | |

No test that passed before fails now. Not rerun: the six R1 workflow files (untouched, still stop at setup).

## Edits
7 files under `a101/tests/`, +19 -11, no product file, nothing retired, no skip or conditional added:
`test_a101_investigation.py` (1 import), `test_blast_native_return_admission.py` (1 import),
`test_native_hmmer_preparation_returns.py` (1 import), `test_blast_pairwise_publication.py` and
`test_native_hmmer_publication.py` (policy constant + import), `test_native_blast_masking_host_returns.py`
(policy bound inside `HostCase`), `test_native_blast_hsp_sites.py` (5 patch targets).

## Runs
27 launcher runs, slot `r4c`, `runs/claude_r4c_001` .. `_027`, one test file each, empty home in
`runs/claude_r4c_homes/NNN`, proxy variables as given. Expected against actual: diagnostics 001-007 about 88 s
(measured times), actual 48 s; reruns 010-012 expected 3-15 min because the workers now start, actual 84 s;
013-017 expected 2 min, actual 111 s; 020-027 expected 3 min, actual 92 s; 008, 009, 018, 019 expected 25 s,
actual 20 s.
- Intermittent, seen once: in run 011 one of 54 local jobs failed with `local_job_boundary_unavailable`, reason
  `service_did_not_initialize` (`A/native_lifecycle.py:287-293`: the systemd unit was reported failed, inactive or
  not found before its ready file appeared). The same case passed in runs 010, 013 and 014. Not traced.
- The scratchpad directory is shared by all agents of this session. Another agent overwrote my `run.sh` there
  while my loop was reading it; bash then executed a fragment of the other script. Its command had a redirect
  to `/out_.txt`, which failed, so nothing ran, and run 007 itself had already completed normally. No stray run
  directory or process resulted (checked). I moved my helpers to a private subdirectory afterwards.
- Run 018/019 used a temporary edit of one path constant (R2 diagnostic); the constant is restored and the only
  remaining difference in that file is the R4 import line.

## Owner questions
1. R2: restore `check003/temporary` of verification packet 273, or move the three needed gradings (about 3.4 MB)
   into `a101/tests/fixtures/`? The only surviving copy sits inside another untracked verification directory.
2. R7: should `test_a101_investigation` exercise the host-recorded report (`records`, `sequence_credit`) or the
   legacy model-verdict claims? As written it cannot pass against either.
3. R1 is r2a's owner question 2 (a101 service factory against driving the root `Workflow`), now 121 cases.
4. R5 leaves r2c's question 1 open where 20 GiB is in product code or in retained plans; I changed only policies
   that the test itself owns.

## Verified by running versus inferred
- Run: R2 (diagnostic 018/019), R3, R4, R5 (receipt tallies and all "now pass" figures), R6 outcome codes (saved
  records of run 007), every before/after number, the patch-target fix.
- Read only: R1 beyond the traceback (absence of an a101 factory from listing and grep; what fails next after a
  factory exists); R6 mechanism (taken from r2c C10, only the code location re-read); R7 "failed before the
  reorganisation" (identical code and test at 078b77668; that revision cannot be run here).
- Not established: why one local job did not initialise in run 011.
