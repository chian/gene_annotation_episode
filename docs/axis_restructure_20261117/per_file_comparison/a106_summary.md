# A106 per-file comparison against 7e662ea29

Scope: the 86 baseline rows of `docs/verification_20261116/results_per_file.tsv` under
`gene_annotation_episode/episodic_workflow/root/a106/`. Per-row detail: `a106.tsv`.
Compared on 2026-11-18. Each current file ran alone through `tools/one_workflow.sh --slot pf106`
(`runs/pf106_t00` to `runs/pf106_t21`, empty HOME, blocked proxy).

Record line numbers in `a106.tsv` count the header as line 1. `HEAD` differs from the baseline only by the
P1 rename (`a106/scientific_process` to `a106/perturbation_evidence`); everything after it is uncommitted, so
diffs were taken against `HEAD`.

## Counts

| | Baseline | Now (files that had a baseline row) |
|---|---|---|
| Test files | 86 | 19 |
| Tests | 1911 | 578 |
| Passed | 1868 | 578 |
| Failed | 9 | 0 |
| Errors | 0 | 0 |
| Skipped | 34 | 0 |

| Status | Files | Baseline tests in those files |
|---|---|---|
| same | 14 | 548 |
| changed | 5 | 38 |
| retired (recorded) | 43 | 868 |
| retired-unrecorded | 24 | 457 (346 of them covered by partial records; 111 have no row) |
| regression | 0 | |

The 19 surviving files hold exactly the 578 ids that `runs/placement_tests/a106_before_ids.txt` lists for them
(the list's other 5 ids are the new `test_ncbi_sra_file_custody.py`).

## Regressions

None. Every test that still exists passes.

The 9 baseline failures are all gone, none by a repair of the code that failed:
- 5 in `published_evidence_assessment/tests/test_a106_final_selection_feedback.py` (`KeyError: 'detail'`): the
  file was deleted (retired-unrecorded, below).
- 2 in `tests/test_literature_perturbation_assessments.py` (`record_selection` missing): the test was rewritten
  off the old binding, so the failing path is no longer exercised (changed, unrecorded, below).
- 1 in `tests/test_literature_perturbation_summary_integration.py`: retired, `a106_retired.tsv:20`.
- 1 in `tests/test_literature_perturbation_covariance_meanings.py`: retired, `a106_retired.tsv:19`.

## Changed files

| Baseline file | Baseline | Now | Cause | Recorded |
|---|---|---|---|---|
| `tests/test_canonical_workflow_resources.py` | 4/4/0/0 | 2/2/0/0 | `test_actual_registry_constructor_uses_authenticated_run_resources` and `test_original_native_memory_bound_rejects_oversized_request_without_launch` removed (SimpleNamespace stand-ins) | No. The same two tests are recorded for a101 (`a101_fake_tests.tsv:146-147`) and a105 (`a105_fake_tests.tsv:12-13`); A106 has no row |
| `tests/test_literature_perturbation_assessments.py` | 5/3/2/0 | 5/5/0/0 | Body rewritten from the deleted old literature binding to the repositories; the 2 baseline failures pass because their failing path went with the old binding | No (only a plan in `a106_needs.md`) |
| `tests/test_literature_intervention_storage.py` | 5/5/0/0 | 4/4/0/0 | 1 test retired (old runner credit admission) | Yes, `a106_retired.tsv:23` |
| `tests/test_literature_a106_subscore.py` | 12/12/0/0 | 10/10/0/0 | 1 parametrized test (2 ids) retired; the `commissioned()` helper was also rewritten | Retirement yes, `a106_retired.tsv:24`; helper rewrite no |
| `tests/test_literature_perturbation_covariance_meanings.py` | 12/11/1/0 | 9/9/0/0 | 4 tests retired, 1 new test keeps half of one of them | Yes, `a106_retired.tsv:19`, `retired_tests.tsv:383-385` |

## Unrecorded changes inside files counted as same or changed

These keep their ids and pass, but what they exercise changed and no record says so:
- `test_literature_perturbation_assessments.py`, `test_literature_perturbation_interpretation_basis.py`,
  `test_literature_perturbation_missing_amount_unit.py`, `test_literature_perturbation_covariance_meanings.py`:
  the tests that went through the old literature binding (`binding.execute`, `binding.facts`,
  `binding.validate_report`, `binding.received_form_references`) now call the repositories directly
  (`LiteraturePerturbationRepository.populate`, the `returned_form` helper, `projection.receive_cells`). Scripts:
  `runs/fx106_scan/edit_assess.py`, `edit_basis.py`, `edit_unit.py`, `edit_cov.py`. The binding-level return and
  receipt path of the ported literature binding is tested nowhere in A106.
- `test_literature_a106_subscore.py`: `commissioned()` used to save a `runtime_episodes` row for the head's
  original commission; it now gives the context the role `perturbation_evidence`. The saved-ancestor lookup in
  `episode_support/literature/storage/literature_subscore_storage.py:44-58` (the branch a literature child takes)
  is no longer tested here.

## Retired-unrecorded files (24)

"Needs list" means the file is named only in the "Old-design tests" list of
`runs/claude_ablate/a106_needs.md:19-23`, which gives no reason. Full text per file is in `a106.tsv`.

| Baseline file (under `a106/`) | Baseline | Tests with no row | Only mention | What it tested; reason it went |
|---|---|---|---|---|
| `published_evidence_assessment/tests/test_a106_final_selection_feedback.py` | 6/1/5/0 | 6 | needs list; `a106_retired.tsv:6` still says "Not retired: moved" | `literature.a106.finalize` feedback through the old `LiteratureEpisode`; that binding, the registry and `WorkflowServices` were deleted |
| `scientific_process/tests/test_scientific_task.py` | 11/11/0/0 | 1 | none | `assignment_schema` of the head on `object.__new__(binding)`; imported the deleted `a106/runtime`; same test recorded as fake for a101 |
| `tests/test_actual_literature_registry.py` | 4/4/0/0 | 4 | needs list | Schema ownership and current work in the a106 `EpisodeBindingRegistry`/`WorkflowServices`/`Journal`; all deleted |
| `tests/test_actual_private_registry.py` | 17/17/0/0 | 17 | none | Construction of the whole A106 family into the old registry; registry apparatus deleted. It was 2 passed, 15 failed after the ablation and was deleted with those failures unresolved |
| `tests/test_literature_perturbation_integration.py` | 9/9/0/0 | 3 | needs list; `retired_tests.tsv:521` indirectly | `literature.perturbation.populate` through the old binding (exact typed subset, no source reread, unrelated source rejected); old binding deleted |
| `tests/test_literature_perturbation_summary_integration.py` | 5/4/1/0 | 4 | needs list | Summary operation through the old binding (saved exact subset, receipt before decoding graph bytes, DDL-free discovery); old binding deleted |
| `tests/test_literature_private_boundaries.py` | 112/112/0/0 | 7 | none | Each literature home's old `LiteratureEpisode` keeping assignment and goal private to its role; homes are now declarative |
| `tests/test_private_literature_progress.py` | 42/42/0/0 | 14 | needs list | Commissioned `literature_task` credit units, continuation settings, invented initial credit rejected; old per-home binding deleted |
| `tests/test_private_literature_tracking_projection.py` | 4/4/0/0 | 4 | needs list | `literature_experimental_prompt._safe` body filter; module deleted |
| `tests/test_private_head_credit_selector.py` | 7/7/0/0 | 7 | none | Old head credit selector (changed identity, missing or invalid original A106 task rejected); head rewritten for episode_runtime |
| `tests/test_private_api_credit_ownership.py` | 68/68/0/0 | 5 | none | `APIServiceExecution` credit protocol and per-home credit callback; both deleted |
| `tests/test_private_api_summary_ownership.py` | 26/26/0/0 | 3 | none | `APIServiceExecution` summary callbacks and per-home `OperationalSummary`; both deleted |
| `tests/test_private_api_report_boundaries.py` | 22/22/0/0 | 3 | needs list | `BVBRCAppServiceHost` empty completion roles for unknown roles; a106 host deleted |
| `tests/test_private_operational_live_prefixes.py` | 52/52/0/0 | 4 | needs list | Role guard of the old per-home `ExecutionEpisode` on `object.__new__`; old execution mixins deleted |
| `tests/test_private_operational_return_boundaries.py` | 24/24/0/0 | 4 | needs list | Old per-home `ExecutionEpisode` child actions, catalogue, empty initial refs; old execution mixins deleted |
| `tests/test_original_input_guard_admission.py` | 7/7/0/0 | 2 | needs list | Old `ExecutionEpisode` rejecting a structure-derived wrapper input; old execution mixins and `execution_input_versions` deleted |
| `tests/test_original_inherited_return_guard.py` | 2/2/0/0 | 2 | needs list | `EpisodeReturnRecords` (`original_return_`); `episode_return_records` deleted |
| `tests/test_original_prepared_assignment_guard.py` | 2/2/0/0 | 2 | needs list | `EpisodeReturnRecords` (`prepared_original_`); `episode_return_records` deleted |
| `tests/test_original_prepared_unicode_guard.py` | 3/3/0/0 | 3 | needs list | `retained_input_authority/prepared_results`; `retained_input_authority` deleted |
| `tests/test_retained_protein_owner_identity.py` | 8/8/0/0 | 8 | none | `retained_input_authority/retained_protein_owner`; `retained_input_authority` deleted |
| `tests/test_retained_publication_receipts.py` | 3/3/0/0 | 3 | needs list | a106 `EpisodeReceipts` admitting an incoming publication without a producer; `episode_receipts` deleted |
| `tests/test_private_scientific_form_validators.py` | 12/12/0/0 | 3 | none for the third function (`retired_tests.tsv:373-374` cover the other two) | Old head mixin `from_parent.ScientificAssignment._invocation`; mixin deleted |
| `tests/test_protected_reference_boundaries.py` | 5/5/0/0 | 1 | none | `ToolRegistry.retained_molecular_reference_access`; the guard no longer exists in the tree |
| `tests/test_no_count_resource_admission.py` | 6/6/0/0 | 1 | none (`a106_fake_tests.tsv:26` says it was kept) | `workflow_budget.native_budget` bounds with a SimpleNamespace policy; its imports from `test_canonical_workflow_resources` were removed |

All reasons in this table are worked out from the `HEAD` test source and the current tree, not taken from a record.

## Current test files with no baseline row

| File | Result | Note |
|---|---|---|
| `gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/execution_job_submission/api_job_execution/tests/test_api_job_runtime.py` | 6/6/0/0 | New, untracked; tests the rewritten API-job binding |
| `gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/execution_result_acquisition/tests/test_result_acquisition_runtime.py` | 5/5/0/0 | New, untracked; tests the rewritten results binding (34 s) |
| `gene_annotation_episode/episodic_workflow/episode_support/acquisition/sequence_and_context_sources/perturbation_evidence/tests/test_ncbi_sra_file_custody.py` | 5/5/0/0 | New; written in `a106/tests` after the baseline and moved out by placement, so it is no longer under `root/a106/` |

`a106/perturbation_evidence/tests/test_episode_runtime_head.py` was written and deleted after the baseline
(`a106_fake_tests.tsv:39`, `retired_tests.tsv:363`).

## Things the comparison shows that the counts do not

- Only the two files above test the A106 bindings now. The rewritten head (`episode.py`, `credit.py`,
  `runtime_source.py`), the monitor (`execution_progress_assessment/episode.py`) and the literature binding
  (`literature_binding.py`, `literature_credit.py`, `literature_source.py`) have no test under `root/a106/`.
- Checks that the deleted tests covered and that still exist in the rewritten code, now without an A106 test:
  `original_axis_finding_task_required` (`perturbation_evidence/credit.py:13,19`),
  `literature_commissioned_credit_capacity_invalid` (`published_evidence_assessment/literature_credit.py:290`),
  `literature_task_credit_commission_mismatch` (`episode_support/literature/grading/literature_task_credit.py:274`).
  `gene_annotation_episode/workflow_budget.py` `native_budget` is called by no test file in the tree.
- Read from the code, not run: the ported literature binding passes its own role to the sheet repositories
  (`literature_source.py:191`), so the A106 judgment in `literature_subscore_storage.py:44-58` takes the
  saved-ancestor branch, which reads the table `runtime_episodes`. I found no module in `gene_annotation_episode/`,
  `episode_runtime/` or `method_loop/` that creates that table (the deleted a106 journal did). The tests that used
  to write that row were rewritten to avoid the branch, so nothing would catch a failure there. This needs a run
  to confirm.
- A106 has no rows in `docs/axis_restructure_20261117/retired_fake_tests.tsv`. Its fake-test and runner
  retirements are recorded only in `runs/claude_ablate/a106_fake_tests.tsv` and `a106_retired.tsv`, under the
  disposable `runs/` directory. `a106_retired.tsv:6` is out of date (the file it calls "moved" was later deleted).
