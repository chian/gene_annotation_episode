# r4d: causes for the failure groups whose message is too generic to carry one (final run `claude_tests_final_20261114_05`)

Work list: `runs/claude_summary_final_20261114_05/unrecorded_r4d.tsv` — 141 groups, 314 failing cases, 23 distinct
messages, 68 test files. Diagnosis and recording only: no repository file was edited, nothing retired, nothing committed.
Companion: `r4d_causes.tsv`, one row per work-list row (141 rows, 314 cases; `test_module`, `test` and `message`
are identical to the work list, checked with `diff`). Each row names its cause id and the line where the test failed.

Every row has a cause. 23 causes: 16 are a cause an earlier report already described (cited below, and confirmed for
these tests), 7 are new (D03 partly, D04, D06, D11, D13, D18, D22).

Paths: `R/` = `gene_annotation_episode/episodic_workflow/root/`. "Original" = `078b77668`.

## Result by classification

| Class | Cases | Causes |
|---|---|---|
| test_wiring | 131 | D12 104, D10 23, D13 2, D17 1, D19 1 |
| stale_test | 129 | D01 79, D05 37, D23 6, D22 3, D04 1, D09 1, D11 1, D18 1 |
| product_defect | 48 | D14 24, D16 17, D02 5, D15 1, D21 1 |
| unclear | 5 | D07 2, D06 1, D08 1, D20 1 |
| environment | 1 | D03 |

184 of the 314 cases no longer fail for the recorded cause, because other agents edited the tests after the final run:
D01 (79, r4c) and D19 (1, r4a) now pass, and the D12 import line (104, r4a) removed the `IndexError`; 3 of those
104 pass and 101 now stop at the next layer (see D12).

## Causes

| id | Cause | Class | Cases | How confirmed for these tests | Proposed fix | Scientific? |
|---|---|---|---|---|---|---|
| D12 | r2e second-layer note = r4a W2. `tests/test_api_bvbrc_minhash.py:18` built top-level `acquisition.SourceSnapshot` objects for the a102 minhash service, whose check uses `a102.acquisition.SourceSnapshot` (`R/a102/api_bvbrc_minhash.py:176,221`). The primitive answers `bvbrc_minhash_response_required`, the launch publishes no record, and the shared helper `handoff()` indexes an empty `record_refs` (`tests/test_bvbrc_minhash_metadata_custody.py:96`) | test_wiring | 104: `test_bvbrc_minhash_prospective_custody` 47, root `test_bvbrc_minhash_commission_replay` 31, `test_bvbrc_minhash_metadata_custody` 25, `test_api_bvbrc_minhash` 1 (regex) | Run. With that one import line changed, the `IndexError` is gone in runs 046, 049, 053, 054 | Already applied by another agent. 101 cases now fail at the next layer: r2f C06 `BVBRCMinhashHost` has no `source_admission_before` (`R/bvbrc_minhash_host.py:101`; 68 cases, product); `R/tests/test_bvbrc_minhash_commission_replay.py:79` patches the removed module `gene_annotation_episode.api_bvbrc_minhash` (22 cases, test-side: re-point to the a102 module); `KeyError: 'source_ref'` 9 and `ExecutionEpisodes` has no `prepare_assignment` 2, not traced | No |
| D01 | r4c R5. The test asks 20 GiB for its own grading or result worker job; the 5 GiB environment bound refuses it (`gene_annotation_episode/workflow_budget.py:35,118-121`), no sheet is returned, and the test indexes or counts an empty result | stale_test | 79: `test_native_blast_hsp_sites` 33, `test_blast_pairwise_publication` 25, `test_native_hmmer_publication` 16, `test_native_blast_masking_host_returns` 4, `test_native_blast_masking_generated_partial_admission` 1 | Run. With r4c's edits all five files pass (runs 003, 005, 006, 007, 009: 55, 54, 1, 8, 37 passed) | Already applied by r4c | No |
| D05 | r2d C2, now the first failure. The scripted root commission of the literature child has no `literature_task` credit declaration and is rejected with `literature_original_task_credit_required` (`R/a105/scientific_process/published_evidence_assessment/goal.py:61`). No child is created, the script is out of step, the run ends `source_failed` with zero actions | stale_test | 37 in 22 a105 files (list in the TSV) | Run. Feedback printed by the provider probe for 33; read from the saved `runtime_model_calls` request for `concentration_window_binding_281` (3) and `measurement_comparison_binding_268` (1), whose provider the probe does not wrap (runs 010-034) | Owner question 1. Add `literature_task` and `proposed_annotation_ref` to the scripted child assignment and expect credit 0, as `test_literature_assay_integration` does | Yes (A105 credit rule) |
| D14 | r4a P3 = r2f C07. Role-only binding lookups on the first root decision: `for_role` raises `episode_role_requires_parent:<role>` (`R/episode_bindings.py:450-458`) from `R/composition_information.py:110` (role `literature`) or `R/decision_information.py:32` (role `launch`). The run ends `source_failed` before the script is reached | product_defect | 24: `test_episode_receipts` 6, `test_bvbrc_data_episode_path` 5, root `test_native_infernal_results_integration` 4, `test_runtime_decision_exchanges` 3, `test_runtime` 2, `test_image_evidence` 2, `test_bvbrc_appservice_custody` 1, `test_episode_waiting_runtime` 1 | Run. Source-failure probe for every test (runs 048, 051, 057, 058, 060, 067, 068); saved archive for `test_bvbrc_appservice_custody` (run 050) | None test-side. Product: path-aware lookup at both lines | No |
| D10 | r2e C5, unresolved. The test registers only the literature head binding; the head declares child role `literature_strategy`, which has no grain (`R/a107/runtime.py:1182`, `R/a110/runtime.py:864`) | test_wiring | 23: a107 13, a110 10 | Junit frame, and runs 037-044 (same `KeyError`, 13 + 10) | None known; r2e's attempt with seven peer bindings fails with `received_report_field_conflict`. Owner question 5 | No |
| D16 | r4a P4. Two `BindingContext` classes: `gene_annotation_episode/molecular_reference_privacy.py:259-261` accepts only the top-level class, so a source the root `Workflow` itself received is denied and the expected specific code is never reached | product_defect | 17: `test_encode_tools` 13, `test_molecular_result_facts` 2, `test_molecular_publication_custody` 1, `test_provider_acquisition_receipts` 1 | Encode by run (076, 077): the received result is `reference_denied` for a root-class context, and the saved second action is `encode_metadata_not_received` with `source_ref` null. The other 4 from the junit actual message (`molecular_tool_invalid_context`, `alphafold_file_metadata_not_received`), which is the message r4a traced | None test-side | No |
| D23 | r2a machine-bound constants. The test expects the recorded local job policy to be the `defaults.toml` 20 GiB; inside the launcher it is capped to 5 GiB (`gene_annotation_episode/local_resources.py:85-91`) | stale_test | 6: `test_tool_grading_publication` | Read (junit message and code); still failing in run 069 | `tests/test_tool_grading_publication.py:99`: compare with `min(20 * 1024**3, ENVIRONMENT_BOUNDS["memory_bytes"])`. Owner question 6 | No |
| D02 | r4c R6 = r2c C10. The result worker's source closure cannot resolve the moved `a101/library` imports and fails with `native_dependency_unavailable` (`R/a101/native_driver_runtime.py:203-214`) | product_defect | 5: `test_native_hmmer_preparation_results` | Saved records of run 008: every one of these tests has `prepared.json` and `projection-failure.json` with that code; none has a budget code | None test-side. The retained plans carry 20 GiB, so r2c C04 follows | No |
| D22 | The test calls `source.locate` with no permitted record refs; the tool answers `source_location_inputs_not_bound` (`gene_annotation_episode/source_locations.py:33-36`). Check and test are the same in the original | stale_test | 3: `test_pdf_text_ranges` | Run 079 (tool-outcome probe, 3 of 3) | `tests/test_pdf_text_ranges.py:57-59`: pass `permitted_record_refs=[source["id"]]`, as `tests/test_alignment_site_publication.py:69` does | No |
| D07 | r2d section 3.2. A saved pre-reorganisation descriptor is refused with `unavailable_binding` where the test expects `identity_conflict` (`R/a105/episode_composition.py:142-155`) | unclear | 2: `test_literature_missing_input_semantics_156` | Read (junit actual message); still failing in run 026 | Owner question 2 | No |
| D13 | r2f C13 family. The shared `Fixture` builds contexts with the top-level `BindingContext` (`tests/test_fluorescence_returns.py:18,116`); `R/library/fluorescence_operands.py:10,26` requires the root class and raises `fluorescence_input_invalid_context` | test_wiring | 2: root `test_fluorescence_episode_routing` | Run 075 (probe prints the context class and the stack) | `tests/test_fluorescence_returns.py:18`: import `BindingContext` from `R/receiving_context` | No |
| D03 | `PublicClients(skill_root=None)` reads the installed skill client under the home directory (`R/a101/acquisition.py:74-83`); the run used an empty HOME, so `skill_client_not_installed` replaces the expected code. The client exists in the real home | environment | 1: a101 `test_blast_binding` | Read (junit actual message); same as r2c and r4a's environment row | Owner question 4 | No |
| D04 | The test puts `map_reconstruction_context` on `native_rows[0]`, the population row; the exact-row population check runs first and gives `input_decoding_invalid` (`R/a101/library/hmmer_preparation_result_views.py:754-755`, `hmmer_alignment_input_validation.py:767-777`) before the placement check at `:768-770` | stale_test | 1: a101 `test_hmmer_alignment_map_context` | Run 080 (probe). Views, validator and test are the same in the original, so it predates the reorganisation | Owner question 2 | No |
| D06 | Not D05. At the first lookup the return-contract information for `literature_ion_discrimination_cells` lists the cell property `formula_code`, which the test forbids (`R/a105/tests/test_literature_ion_discrimination_binding_199.py:459`) | unclear | 1 | Run 070 (probe: reference present once, `formula_code` twice). Assertion, profile and renderer exist unchanged in the original; why the property is listed was not established | Owner question 3 | Prompt content |
| D08 | r2d RC. The populate that must complete returns `literature_rate_observation_sheet_required` | unclear | 1: `test_literature_reported_curve_binding_231` | Run 071 (outcome probe) | None (r2d owner question) | Yes (A105 sheet) |
| D09 | r2e C6, the a106 form of D05 | stale_test | 1: a106 `test_literature_perturbation_summary_integration` | Run 036 (feedback printed) | Owner question 1 | Yes |
| D11 | The stub `interrupted(url, *, byte_range=None)` does not accept `max_bytes`, which `gene_annotation_episode/api_bvbrc_appservice.py:71` passes; it raises `TypeError`, which is recorded as `api_selected_primitive_failed`, so no `KeyboardInterrupt` reaches the test. Same in the original | stale_test | 1: root `test_bvbrc_genome_alignment_host` | Runs 072 (outcome) and 073 (`TypeError` printed) | `R/tests/test_bvbrc_genome_alignment_host.py:516-518`: accept and forward `max_bytes`, as `tests/test_bvbrc_appservice_acquisition_records.py:54-55` does | No |
| D15 | r4a P2. Root custody reloads the response as the top-level `SourceSnapshot`; the a102 reader answers `bvbrc_invalid_snapshot` | product_defect | 1: `test_bvbrc_data_recovery` | Saved `outcome.json` of both result actions (run 052) | None test-side | No |
| D17 | r2f tail row. The receiver is built with the top-level `BindingContext`; `R/library/molecular_sequence_input_bindings.py:54` requires the root class (`invalid_context`) | test_wiring | 1: `test_molecular_publication_custody` | Read only; still failing in run 061 | r2f's proposal (`tests/test_molecular_publication_custody.py:21`), not unambiguous because of D16 | No |
| D18 | Resolves one unclear case of r2f C15. For a foreign `return_id`, `load_return_admission` raises `unavailable_binding` (`R/episode_admission.py:62-66`) before the comparison that gives `completion_child_admission_conflict`. Same in the original | stale_test | 1: `test_episode_completion` | Run 078 (raise-site probe) | Owner question 2 | No |
| D19 | r4a W5. Top-level `BindingContext` against `R/flux_balance_returns.py:18,54` | test_wiring | 1: `test_flux_balance_ordinary_returns` | Run 059: 14 of 14 pass with r4a's edit | Already applied by r4a | No |
| D20 | r4a Q1 = r2a cause 7. Retained capture plan carries `policy.wall_seconds: null`; the closed policy check rejects it first | unclear | 1: `test_native_infernal_preparation_result_publication` | Read (junit actual message); still failing in run 063 | Owner question (r4a) | Yes |
| D21 | r2f C08(b). The grading worker is launched from `root.library`, but the module exists only under `R/a107` | product_defect | 1: `test_native_infernal_publication` | Worker stderr retained in run 064: `No module named ...root.library.native_infernal_result_worker` | None test-side | No |

## Test-side fixes someone can apply later (none applied, none verified by applying)

1. D11: `R/tests/test_bvbrc_genome_alignment_host.py:516-518` — `def interrupted(url, *, max_bytes, byte_range=None)`, forward `max_bytes` to `actual_download`.
2. D13: `tests/test_fluorescence_returns.py:18` — import `BindingContext` from `gene_annotation_episode.episodic_workflow.root.receiving_context`. Shared helper: rerun every file that imports `Fixture`.
3. D22: `tests/test_pdf_text_ranges.py:57-59` — add `permitted_record_refs=[source["id"]]` to the `source.locate` call.
4. D12 next layer: `R/tests/test_bvbrc_minhash_commission_replay.py:79` — patch target to `gene_annotation_episode.episodic_workflow.root.a102.api_bvbrc_minhash`.
5. D23: `tests/test_tool_grading_publication.py:99` — expected value bounded by `workflow_budget.ENVIRONMENT_BOUNDS["memory_bytes"]`, if the owner accepts the r4c R5 precedent.

Not test-side: D02, D14, D15, D16, D21 (product); D10 (no supported composition known).

## Owner questions

1. D05 and D09 (38 cases): which `literature_task` credit declaration should each scripted A105/A106 commission carry? This is r2d C2, still open, and now the first failure of these tests.
2. D04, D18, D07 (4 cases): an earlier check refuses with a different code than the test expects. Which code is intended? D04 and D18 behave the same in the original.
3. D06: should the return-contract information for `literature_ion_discrimination_cells` list `formula_code`?
4. D03: should tests that read the installed skill client run with the real HOME, or should the client be staged and passed as `skill_root`?
5. D10 (23 cases): how should a107/a110 tests compose the split literature tree under an annotation root?
6. D23: is the 20 GiB default in `defaults.toml` still the expected recorded policy when the launcher bound is 5 GiB (r2c question 1)?

## Verified by running versus read only

- Run: D01, D02, D04, D05, D06, D08, D09, D10, D11, D12, D13, D14, D15, D18, D19, D21, D22, and the encode rows of D16.
- Read only (junit message plus code, and the earlier report): D03, D07, D17, D20, D23, and 4 rows of D16.
- Inferred, not exercised: "predates the reorganisation" for D04, D11, D18, D22 (identical code and test in the original; that revision cannot be run here).
- Not established: why `formula_code` is listed (D06); the mechanism behind D08 (taken from r2d).

## Runs

83 launcher runs in slot `r4d`, `runs/claude_r4d_000` .. `_082`, empty HOME under `runs/claude_r4d_homes/NNN`, proxy
blocked. Scripts and print-only probes: `runs/claude_r4d_scripts/`.
- 000, 001, 081, 082: read-only text processing of junit and the work list.
- 002-069: each of the 68 affected test files once, with two print-only probes. Expected about 15 min, actual 684 s.
  `test_bvbrc_genome_alignment_host` and `test_hmmer_alignment_map_context` were narrowed with `-k` to the listed test.
- 070-080: 11 narrowed diagnostic runs with further print-only probes (074 failed to load its probe and was repeated as 075).

Probes wrap a function for the duration of a test and print; none changes a return value or an exception.

## Deviations and limits

- Before reading the launcher rule closely I ran three short `python3` commands outside the launcher (two tallies of the
  work-list TSV, one junit extraction that crashed). They read files only and started no workflow. Everything after that
  went through the launcher.
- The tree moved under these runs. Runs 002-069 used the tree of 2026-11-14 13:35-13:47, runs 070-082 the tree of
  2026-11-15 10:03-10:13; other agents were editing tests in between. "Now passes" figures describe those moments.
- The final run's temporary directories were already removed, so saved records come from my reruns, not from the final
  run itself. For runs 002-069 the product code was the final run's (only test files were modified). At 10:04 on
  2026-11-15 another agent changed one import line in each of 12 product files (commit 985da562f, the `validate_pending`
  import of r4a P5 and similar); none of them is a module the conclusions of runs 070-080 rest on (read, not tested).
- `test_native_infernal_results_integration` has 4 work-list cases; in my rerun 5 parameters show the D14 source failure
  and 1 fails on an import, because another agent edited that file after the final run.
