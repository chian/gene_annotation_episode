# r4a: causes for the 187 unrecorded failure groups in top-level `tests/` (380 cases, 80 messages)

Base: HEAD acb5e2386, slot `r4a`, runs `runs/claude_r4a_001` .. `041` (one test file per launcher run, empty HOME in
`runs/claude_r4a_homes/NNN`, proxy blocked). `R/` = `gene_annotation_episode/episodic_workflow/root/`.
Companion: `r4a_causes.tsv` (one row per message, 80 rows, 380 cases, every row has a cause).
Edits: 13 test files under `tests/`, +33/-17. No product file, no file outside `tests/`, nothing retired, nothing committed.

Every one of the 80 messages has a recorded cause. 81 of the 380 cases now pass; 13 more had their wiring fixed and
now stop at a product defect that was already recorded.

## Causes

| id | Cause | Class | Cases | Evidence | Action | Scientific? |
|---|---|---|---|---|---|---|
| P1 | The handle check compares the saved request with an environment that lacks the two workflow keys `prepare_job` now adds. | product_defect | 70 (protein structure 61, RNA structure 9) | `gene_annotation_episode/native_lifecycle.py:156-158`; `R/library/native_protein_structure_preparation.py:292-295`; `R/library/native_rna_structure_local.py:25-28,101-104`; the BLAST locals include the keys (`R/library/native_blast_local.py:91-93`) | left failing; add the two keys to the expected environment | no |
| P3 | Role-only binding lookups. Root `ExecutionServiceFactory` binds `launch`, `launch_api` and `results` at several homes, and the literature families bind `literature` at several; `for_role` then raises. The run ends `source_failed` before its first decision. | product_defect | 42 | `R/episode_bindings.py:450-458`; `R/decision_information.py:32`; `R/composition_information.py:110` (r2f C07); also `R/execution_planning.py:40`, `R/child_delivery.py:349-366`, `R/episode_services.py:325`, `R/workflow_molecular_operands.py:107`; axis copies pass the path (`R/a101/runtime.py:2006`) | left failing. Two tests make the same role-only call themselves (`tests/test_bvbrc_appservice_compact_custody.py:79`, `tests/test_macs2_peak_execution.py:678`); fixing those alone cannot pass while the product lookups remain | no |
| P4 | Two `BindingContext` classes. `molecular_reference_privacy` accepts only the top-level class, so every source the root `Workflow` received from alphafold, encode, screen or jaspar is denied. Seen from the other side, top-level `molecular_measurement_tools` requires the top-level class and the root reader requires the root class. | product_defect | 39 (alphafold 14, encode 8, molecular 13, screen 2, jaspar 2) | `gene_annotation_episode/molecular_reference_privacy.py:259-262` against `enrichr_reference_privacy.py:179-183`, which accepts both; `gene_annotation_episode/molecular_measurement_tools.py:643,660`; `R/library/molecular_sequence_input_bindings.py:15,54` | left failing (r2a owner question 5) | no |
| P2 | The shared root builds the a102 BV-BRC data service but reloads retained responses as the top-level `SourceSnapshot`; a102 readers reject that class. | product_defect | 34 (data recovery 32, forwarded boundaries 2) | `gene_annotation_episode/api_services.py:117` (re-pointed in f29225f0a; was `.api_bvbrc`); `R/api_service_custody.py:13,64`; `R/a102/bvbrc_data_readers.py:392-393` | left failing; the shared root has no `api_bvbrc` of its own, so this needs an owner choice | no |
| Q1 | Retained capture plans carry `policy.wall_seconds: null`; the closed policy check allows two keys only. The result worker reports the same code. | unclear (r2a cause 7) | 33 (publication 23, worker 10) | four `capture-plan.json` under `R/a107/tests/fixtures/infernal_preparation/capture`; `R/library/native_infernal_preparation_acquisition.py:119-121`, identical at 078b77668 | left failing; owner question | yes |
| W1 | Tests built the top-level `Store` for the a102 service; a102 catches only its own `ContractError`. | test_wiring | 29 | `R/a102/bvbrc_data_publication.py:245-250`; `R/a102/api_bvbrc.py:446-451` | fixed | no |
| W2 | Test built top-level `SourceSnapshot` objects for the a102 minhash service. | test_wiring | 25 | `tests/test_api_bvbrc_minhash.py:18`; `R/a102/api_bvbrc_minhash.py:176,221` | fixed; 1 case left behind P2 | no |
| Q3 | Root literature repositories combined with the a105 service binding (r2b K22), plus one implementation-digest pin. | test_wiring / unclear | 17 | `tests/test_literature_cell_possession.py:16,18,64,70`; `R/a105/library/literature_optical_storage.py:59` | left failing; axis choice in an A105-family test | yes |
| W4 | Hand-built `Workflow.__new__` doubles lack collaborators the resolver reads. The product read `self.tools` already at 078b77668, so this predates the reorganisation. | test_wiring | 14 | `R/report_validation.py:117-139`; `R/outcome_receipts.py:116`; `R/workflow_setup.py:108,124,215` | fixed in 4 files | no |
| P5 | Stale import of `validate_pending` from `root.waiting`; it lives in `root.wait_events`. | product_defect | 13 | `gene_annotation_episode/molecular_measurement_tools.py:645`; `R/wait_events.py:199`; same line in `atac_differential_result_receipts.py:1250`, `chromatin_interaction_result_receipts.py:1082`, `macs2_peak_request_binding.py:202` | left failing; four import lines outside `tests/` (import-line exception applies) | no |
| W3 | Tests imported `NativeTimingInformation` and `ResourceToolEstimator` from the top-level duplicates. | test_wiring | 11 | `R/run_execution.py:14-15,129,177` | fixed; the 11 cases now fail for P3 | no |
| Q2 | A105 reading rule rejects the fixture reading (r2b K27). | unclear | 8 | `R/literature_controlled_response_storage.py:541` | left failing; owner question | yes |
| W5 | Test built the top-level `BindingContext` for root `FluxBalanceReturns`. | test_wiring | 7 | `R/flux_balance_returns.py:18,54` | fixed | no |
| C16 | Root `ExecutionEpisodes` has no `_match_request` (r2e C16). | product_defect | 5 | `R/execution_episodes.py:29`; `R/tests/test_flux_balance_execution_inputs_704.py:81` | left failing | no |
| S1 | A returned invalid or failed tool outcome is an observed outcome. It raises no `ActionFailure` and, without a completion slot, counts as unfinished. | stale_test | 5 | `R/episode_completion.py:22-30,270-279`; `R/task_actions.py:151,174`; same at 078b77668; AGENTS.md | left failing; iterator rule | yes |
| W7 | Graders patched on the top-level modules; the registry imports three of them from `root.library`. | test_wiring | 4 | `R/tool_scientific_operations.py:289,504,528,545`; `R/tool_result_grading.py:27` | fixed | no |
| S6 | Invalid outcomes carry `exception_type`, `message`, `detail`; tests compare the whole feedback dict. | stale_test | 4 | `R/direct_tool_execution.py:709-711`; 078b77668 `tools.py:1679-1683` | left failing; compare category and code | no |
| W6 | `use()` and `calculate()` exist only in the a107 and a110 copies. | test_wiring | 3 | `R/library/component_source_identity.py` (TOOLS and catalog only); `R/a107/component_source_identity.py:94,239` | fixed with explicit per-axis modules | no |
| K07 | Helper test modules parked in `tests_parked/tests/` (r2b K07). | test_wiring | 3 | `tests/test_bvbrc_compact_family_returns.py:281` | left failing; owner decision | no |
| - | Environment | environment | 5 | `skill_client_not_installed` 2: `gene_annotation_episode/acquisition.py:60-63` needs `~/.codex/plugins/cache/openai-curated-remote/life-science-research` (present in the real home, version 1.0.3; runs use an empty HOME). `sklearn` 1: not installed, not in `pyproject.toml`. ViennaRNA 1: `R/a107/tests/fixtures/rna_structure_producer_357/native-site/RNA` missing. T1 1: see "Intermittent" | left failing | no |
| - | Single stale tests | stale_test | 5 | S2 identity assertion on `local_outcome_preview` (`tests/test_batch_publication_history.py:130`, `R/decision_information.py:153-156`). S3 failed form delivery is always deferred (`R/episode_admission.py:43,52,204`). S4 `work_timeout` key removed (fixed). S5 `query_coverage` is a grading cell, not in the source artifact (`R/tool_scientific_operations.py:296-308`), 2 cases | S4 fixed; others left | S3 yes |
| - | Single others | product_defect / unclear | 4 | P6 `gene_annotation_episode/local_example/worker.py:8` and `service.py:198` import `..execution_timing`, now only `R/execution_timing.py`; the worker dies at import. C03m export credit projection after scorer retirement (`gene_annotation_episode/export.py:597-624`). Open-mapping tool schema against the closed-transport test (`R/library/protein_disorder_result_contracts.py:61`, `tests/test_runtime.py:544`). Sync `ChildEpisodeUnit` does not absorb `ReportDeliveryError` (`R/method_loop/episode.py:1809-1844`, `tests/test_runtime.py:807-818`) | left failing | C03m yes |

## Before / after for every file run both times (passed/failed)

| file | final run | after | note |
|---|---|---|---|
| `tests/test_api_bvbrc_data_v2.py` | 24/28 | 52/0 | W1 |
| `tests/test_api_bvbrc.py` | 28/1 | 29/0 | W1 |
| `tests/test_api_bvbrc_minhash.py` | 48/40 | 87/1 | W2; left: P2 |
| `tests/test_runtime_recorded_admission.py` | 42/8 | 50/0 | W4 |
| `tests/test_library_targets.py` | 9/2 | 11/0 | W4 |
| `tests/test_library_scope_ownership.py` | 7/9 | 10/6 | W4; left: retired scorer |
| `tests/test_native_read_mapping.py` | 6/3 | 6/3 | W4; all 3 now retired scorer |
| `tests/test_flux_balance_ordinary_returns.py` | 6/8 | 14/0 | W5 |
| `tests/test_component_source_identity.py` | 15/5 | 20/0 | W6, plus the a110 fixture path at line 362 |
| `tests/test_tool_grading_publication.py` | 14/10 | 17/7 | W7; left: 6 machine-bound 20 GiB constant, 1 `blast_graders` import |
| `tests/test_sequence_derivation_publication.py` | 9/1 | 10/0 | W7 |
| `tests/test_rna_evidence.py` | 3/2 | 4/1 | S4; left: `gene_annotation_episode.tools` (r2b K29) |
| `tests/test_native_timing_information_runtime.py` | 1/6 | 1/6 | W3; now P3 |
| `tests/test_spreadsheet_timing_learning.py` (dependent) | 1/5 | 1/5 | W3; now P3 |
| `tests/test_native_mapping_bounds.py` (not edited) | 0/1 | 1/0 | T1 |

Sum over the 14 edited or dependent rows above the last: passed 213 to 312, failed 128 to 30.

Dependents that import an edited helper, not edited themselves:
`test_alignment_site_action_records` 65/0 to 65/0, `test_alignment_site_publication` 8/0 to 8/0,
`test_scientific_interpretation_accounts` 1/0 to 1/0, `test_bvbrc_data_recovery` 10/33 to 10/33,
`test_bvbrc_forwarded_report_boundaries` 0/2 to 0/2, `test_batch_publication_history` 4/4 to 4/4,
`test_native_mapping_runtime` 0/4 to 0/4, `test_self_mapping_dependencies` 0/3 to 0/3,
`test_bvbrc_minhash_metadata_custody` 1/25 to 3/23, `test_bvbrc_minhash_prospective_custody` 0/47 to 0/47,
`R/tests/test_bvbrc_minhash_commission_replay.py` 0/31 to 0/31. The last three moved from `IndexError` to a next
layer (`'BVBRCMinhashHost' object has no attribute 'source_admission_before'`, 68 cases; stale dotted target
`gene_annotation_episode.api_bvbrc_minhash`, 22), not diagnosed. No file lost a passing test.

## Intermittent native-job failure (T1)

A native tool sometimes returns `status: failed` with code `local_job_boundary_unavailable`, phase `local_preflight`,
reason `service_did_not_initialize` (`gene_annotation_episode/native_lifecycle.py`). I read this from the retained
stores with `sqlite3`. It hit four of my runs and disappeared on rerun:

- run 009 `test_native_read_mapping` (2 tests), clean in run 013;
- run 035 `test_alignment_site_publication` (1 test), 8/0 in run 040;
- run 036 `test_alignment_site_action_records` (45 errors), 65/0 in run 041;
- run 038 `test_self_mapping_dependencies` (1 test), not rerun.

Other slots were running at the time. `test_native_mapping_bounds` failed this way in the final run and passes alone
(run 025); its retained log truncates the feedback, so that match is inferred. Any file that launches native jobs can
show spurious failures of this kind in a sharded run.

## Process leak in `tests/test_durable_episode.py` (read only, not run)

The test is `test_worker_closure_keeps_a_commissioned_descendant_executing` (lines 321-351).

- The parent worker's first action commissions and starts a descendant `method_loop.durable_worker`
  (`tests/durable_fixture.py`, `descendant_spec` branch). Workers are spawned detached with `start_new_session=True`
  (`method_loop/durable.py:577-580`).
- The descendant's first action blocks reading the FIFO `descendant_gate`
  (`durable_fixture.py`: `Path(arguments["gate"]).open("rb", buffering=0).read(1)`).
- The test fails at line 332, `envelope = returned(store, parent)`, with `DurableExecutionError: unavailable_binding`
  from `method_loop/durable.py:661-680`: the fixture factory has no `receiver_snapshot`, and the parent owns an
  unacknowledged descendant commission.
- The only writer to the FIFO is `release_gate(gate)` at line 348, with no `try/finally`. It is never reached, so the
  descendant waits forever. It is in its own session, so pytest's exit does not end it, and it stays in the
  launcher's control group.

The same unguarded pattern is in the gated tests at lines 180, 202 and 419; they pass today. The second failing test
of that file (`test_failures_remain_typed_and_preserve_actual_partial_or_closed_work`, `TimeoutError`) has no gate.
Proposed test-side repair, not applied because the file may not be run: release the gate in a `finally`, and give the
fixture factory the `receiver_snapshot` the kernel requires.

## Owner questions

1. P3: may the root role-only lookups be changed to path lookups as the axis copies do? This is the largest blocker
   for `run_workflow`-based tests in `tests/`.
2. P4: which `BindingContext` should top-level modules accept? `enrichr_reference_privacy` accepts both;
   `molecular_reference_privacy` and `molecular_measurement_tools` accept one.
3. P2: should the shared root get its own `api_bvbrc`, or should root custody build the snapshot class of the service
   it calls?
4. Q1: are retained plans with `policy.wall_seconds: null` admissible, or are the fixtures to be regenerated?
5. S1 and S3: confirm that tests expecting `ActionFailure` for a returned failure, and `delivery_failed` with a staged
   completion, are to be rewritten to the current rules.
6. P1, P5, P6: seven product lines outside `tests/` with unambiguous repairs; who applies them?

## Durations

41 launcher runs, 291 s in total. Each file ran at or below its measured time in the final results (longest:
`test_detached_job_service` 31 s against 31.5 s; `test_native_read_mapping` 17 s against 21.9 s). The batch of 11
dependents was expected at about 80 s and took 57 s.

## Verified by running versus inferred

- Run: every before/after number; W1 to W7 and S4 (fix applied, file rerun); P3 (archived `LookupError` in runs 001,
  005, 006, 026, 027); P4 for alphafold and encode (reader returned `reference_denied`, runs 016 and 017); P6
  (`supervisor.log` of run 024); T1.
- Read only: P1 for RNA structure (r2a ran the protein case); P2 (class mismatch traced through three files); P4 for
  screen, jaspar and the molecular tools; P5 (the import error is in the traceback; the three status mismatches in
  the same file are attributed to it); Q1 for 9 of the 10 worker cases (one shows the code); Q2, Q3, C16, K07 (earlier
  reports, checked against the current files); all S rows; the two `test_runtime` singles; the durable leak.
