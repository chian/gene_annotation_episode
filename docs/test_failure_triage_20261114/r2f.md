# r2f: top-level `tests/` long tail (round two)

Scope: rows of `runs/claude_summary_20261114_03_all/groups.tsv` with `directory_list == tests`, minus the messages owned
by r2a/r2b and the ledger artefacts: 508 rows, 880 cases, 112 test files that still exist. Per-message causes are in
`r2f_causes.tsv` (join on the `message` column); per-file causes for the tail are in `r2f_tail_by_file.tsv`.
"Verified by run" means a launcher run in a fresh run directory (`runs/claude_r2_r2f_NNN`); everything else was read
from the junit traceback, the test and the product code. Pre-reorganisation code is `078b77668`.

## A. Causes diagnosed by the lead (565 cases, 28 files)

| id | cause | class | cases / files | evidence | action | scientific? |
|---|---|---|---|---|---|---|
| C01 | Retained genomic-overlap fixture plans and sealed bundles carry `policy.wall_seconds: null`; every current `Policy` schema forbids the key, so `validate_genomic_overlap_run_plan` rejects the fixture before any test logic | stale_test (fixture of a removed record version) | 169: test_native_genomic_overlap_capture 71, test_genomic_overlap_result_worker 63, test_native_genomic_overlap_preparation 22, test_genomic_overlap_worker_runtime 13 | `root/library/native_genomic_overlap_job_schema.py:20-23` (`additionalProperties: False`, no `wall_seconds`); `b5d7c94e2:gene_annotation_episode/native_genomic_overlap_contracts.py:37-41` required it, `078b77668` already did not; fixture `a103/tests/fixtures/genomic_overlap/native_capture/fixtures/three/plan.json` (sha matches `FIXTURE_PINS.json`) and `native/bundle.json` both have the key | left failing: `bundle.json` is sealed original bytes and the plan digest is bound into it, so no test-side adaptation is possible | yes - owner question 1 |
| C02 | Synthetic software binding half-rewritten (driver module on the new path, implementation modules on the flat path) and `BindingContext` imported from the top-level module while the product checks the root class | test_wiring | 66: test_genomic_overlap_operands | `root/library/genomic_overlap_job_validation.py:82-86`; `root/library/genomic_overlap_operands.py:13,34`; original test at `078b77668` used one consistent layout | fixed (2 lines) | no |
| C03 | Categorical annotation scorer is retired: `CreditPolicy` / `project_credit` raise, `softened_hypervolume` needs explicit `HypervolumeParameters` | stale_test | 49: test_credit 28, test_context_credit 7, test_library_credit 7, test_credit_integration_arithmetic 3, test_scientific_hypervolume_runtime 1, test_investigation_progress 1, test_runtime 1, test_annotation_score_separation 1 | `gene_annotation_episode/credit.py:1-5,33-51,91`; identical at `b5d7c94e2` and `078b77668`, so these tests were already failing before the reorganisation | retired 12 tests in the four files nobody else holds; the other four files are modified by another agent, so the same retirement is recommended but not applied (37 cases) | yes, but the product decision is already made |
| C03m | Same retired scorer used as one incidental assertion (`project_credit(store).credit == 0` or unchanged) inside tests of current behaviour | stale_test (one assertion) | 11: test_material_intake 4, test_gzip_prefix 3, test_packed_materials 2, test_reasoning_contexts 1, test_state_query 1 | e.g. `tests/test_reasoning_contexts.py:59`, `tests/test_state_query.py:202,209` | left failing - owner question 2 | yes |
| C04 | Synthetic FBA software pins in the flat layout while argv uses the current `DRIVER_MODULE` | test_wiring | 41: test_flux_balance_native_capture_697 | `root/library/native_flux_balance_contracts.py:46-54,116-119` | fixed (pin paths) | no |
| C05 | `RfamBatchHTTP.__init__` no longer takes `timeout_seconds` | stale_test | 40: test_rfam_batch_transport | `gene_annotation_episode/rfam_batch_transport.py:39-40`; removed in `dfe3e6091` together with the connection timeout | fixed: argument dropped at 6 call sites, `test_invalid_timeout` (7 cases) retired | no |
| C06 | Shared-root `EpisodeReturnRecords` lost `decision_witnesses`, `source_admission_before`, `file_admission_before`, `_results_assignment` | product_defect | 38: test_episode_return_admission (also 2 in test_resource_result_receipt_preparation, tail) | `root/episode_return_records.py` is 295 lines; `078b77668:gene_annotation_episode/episode_return_records.py` is 519 and defines them at 127-351; all nine axis copies keep them; root callers: `root/protein_structure_action_records.py:713,717`, `root/molecular_result_saved.py:58`, `root/bvbrc_minhash_host.py:101`, six `root/library/*_tools.py` | left failing. Minimal repair: restore lines 127-351 of the pre-reorganisation class into the root copy | no (plumbing), but it is product code |
| C07 | `child_options` calls `episode_bindings.for_role(name)`; with the default literature families the role `literature` has several path bindings, so the first decision raises `LookupError: episode_role_requires_parent:literature`, recorded as `source_failed` with zero actions | product_defect | 23: test_runtime 22, test_annotation_score_separation 1 (inferred) - plus most `run_workflow`-based tail files, see B | `root/composition_information.py:110` vs `aXXX/composition_information.py:144` (`for_child(source.path, name)`) in all nine axis copies; `root/episode_bindings.py:450-459`; archived traceback in `runs/claude_r2_r2f_001/tmp/.../run/archive/*.json` | left failing. Minimal repair: `for_role(name)` -> `for_child(source.path, name)` at line 110 | no |
| C08 | (a) test job policy of 20 GiB exceeds the 5 GiB environment bound; (b) the grading worker is launched as `-m ...root.library.native_infernal_result_worker`, a module that exists only under `root/a107/` | environment + product_defect | 22: test_native_infernal_publication | (a) `gene_annotation_episode/workflow_budget.py:118-121`; (b) `root/library/native_infernal_result_publication.py:225`, worker stderr `No module named ...root.library.native_infernal_result_worker` in `runs/claude_r2_r2f_011` | (a) fixed in the test (`POLICY` 5 GiB); (b) left failing - the only copy is in another axis, so rule 1 forbids re-pointing | no |
| C09 | Shared helper `a101/tests/test_blast_result_views.py::published` builds `ToolRegistry(store)` with no run directory, so the a101 `PublicClients` has no `access_dir` | test_wiring (shared helper) | 20: test_alignment_site_action_records (also 3 in test_alignment_site_publication, tail) | `root/a101/acquisition.py:314`; helper line 29 | left failing: helper belongs with r2a's `ToolRegistry(store)` fix; it needs `run_directory=` there | no |
| C10 | `_controls` requires the prepared handle metadata to equal `native_lifecycle._metadata(policy)` exactly, but `prepare_job` adds `local_resources`, `cpu_threads`, `whole_workflow_budget` and `enforcement.cpu` | product_defect (predates the reorganisation) | 19: test_fluorescence_worker_preparation | `root/library/native_fluorescence_preparation.py:165-168`; `gene_annotation_episode/native_lifecycle.py:124-127`; same two pieces at `078b77668` | left failing; read from code only | no |
| C11 | Test imports top-level `ContractError` / `AcquisitionError`, a102 raises its own classes (known cause) | test_wiring | 18: test_api_bvbrc | `root/a102/api_bvbrc.py:23,26`; `tests/test_api_bvbrc.py:12,17` | not edited (file is modified by another agent): import both names from `...root.a102.acquisition` / `...root.a102.domain` | no |
| C12 | Capacity-ledger artefact (`local_resource_limits_exceed_environment_bounds` from a 20 GiB definition left in the shared run directory) | environment (known artefact) | 16: test_tool_attribution | `root/a102/local_resources.py:163`; run 009 alone: 15 pass | none; the one remaining failure is `AttributeError: module ...root.scoring has no attribute received_axis_task_credit` (r2b) | no |
| C13 | Top-level `episode_bindings.BindingContext` vs the root class the product checks | test_wiring | 16: test_practical_receipt_information | `root/practical_receipt_information.py:16,170`; `gene_annotation_episode/episode_bindings.py:52` is a second class | fixed (import) | no |
| C14 | `ClosedRecord` imported from the top-level `method_loop` package; product checks `root.method_loop.ClosedRecord` (same root cause as r2a's `EpisodeRequest.message` message) | test_wiring | 15 + 8: test_episode_completion, test_episode_admission | `root/episode_completion.py:12,126`; `root/episode_admission.py:13,228` | fixed (imports in both files) | no |
| C15 | Three test_episode_completion tests fail on behaviour once C14 is fixed | stale_test 1, unclear 2 | 1 in the original results, 3 after the fix | `test_failed_execution_c4_input_is_null_and_cannot_stage` forbids credit projection for a failed execution, but `root/episode_admission.py:184-188` projects it and so did `078b77668:gene_annotation_episode/episode_admission.py:260-266`; the other two: `controller_input` is None for a `delivery_failed` admission (`tests/test_episode_completion.py:72`), and `unavailable_binding` is raised before `completion_child_admission_conflict` | left failing - owner question 3 | yes (crediting of failed work) |
| C16 | `monkeypatch.setattr(runtime, "run_workflow", ...)` targets a name that moved to `root/run_execution.py` | test_wiring | 1: test_material_intake | `tests/test_material_intake.py:331`; `root/run_execution.py:28` | not edited (file is modified by another agent) | no |

## B. Tail diagnosed by three read-only helpers (309 cases, 84 files; row per file and message in `r2f_tail_by_file.tsv`)

Grouped by cause family. Counts are failing cases. Rows marked (run) were re-checked by me with a launcher run.

| family | class | cases | files | evidence / note | action |
|---|---|---|---|---|---|
| C07 again: `for_role('literature')` LookupError ends every default-binding `run_workflow` run as `source_failed` | product_defect | 55 | test_runtime_decision_exchanges 11, test_runtime_history 10, test_wait_target_failures 7, test_episode_yield_reports 6, test_scientific_child_credit 5, test_runtime_expectations 4, test_runtime_catalog_recovery 4, test_tool_knowledge 2, test_episode_waiting_runtime 1, test_episode_credit 1, others | (run) archives of runs 013-016 hold the same LookupError; in test_wait_target_failures 4 tests instead archive `RuntimeError: coroutine raised StopIteration` (scripted provider exhausted) - not traced further | left failing |
| Two `method_loop` packages / two `BindingContext` classes: tests build values from the top-level copy, root code checks its own class | test_wiring | 37 | test_application_execution_binding 12, test_episode_admission 8, test_owned_child_waiting 4, test_molecular_sequence_input_bindings 4, test_episode_source_checkpoint 3, test_decision_history 2, test_molecular_publication_custody 2, test_wait_target_failures 1, test_assembled_runtime_ports 1 | `root/method_loop/` added in `dfe3e6091`; 50 top-level test files still import top-level `method_loop`, 55 import top-level `episode_bindings` | fixed in 4 files (run); test_application_execution_binding and test_assembled_runtime_ports are held by another agent (line 7 of each needs the root import) |
| `build_tools` now requires `run_directory` | stale_test | 31 | test_actual_tool_retriever 10, test_pdf_text_ranges 7, test_actual_tool_retriever_runtime 6, test_semantic_actual_tool_retrieval_runtime 4, test_ncbi_contact_configuration 3, test_ordinary_execution_statistics 1 | `root/tool_configuration.py:39` | fixed in 2 files (run); test_pdf_text_ranges then hits a stale helper setting (`local_resources.cpu_threads` in `root/tests/live_a106_workflow.py`, rejected by `gene_annotation_episode/local_resources.py:62-65`); others not edited (held by another agent or need `reopen_tools`) |
| 20 GiB test policies against the 5 GiB bound | stale_test / environment | 25 | test_native_protein_structure_preparation 15, test_native_infernal_execution 8, test_local_resource_capacity 1, test_local_job_configuration 1 | product `_POLICY` for protein structure is 5 GiB; infernal execution binds the retained 20 GiB request (`root/library/native_infernal_local.py:94`) so it cannot be lowered (run 030, reverted) | protein structure already changed by another agent; rest left failing |
| `wall_seconds` in retained fixtures or test arguments (same removal as C01) | stale_test | 19 | test_minimap2_grader 6, test_native_infernal_execution 4, test_native_infernal_acquisition 4, test_protein_structure_publication 3, test_chromatin_interaction_contracts 1, test_fluorescence_local_routing 1 | retained receipts/plans keep `policy.wall_seconds: null`; `LocalJobPolicy` has no such field | left failing - owner question 1 |
| `ExecutionEpisodes.roles` / `entry_roles` removed (replaced by `bound_execution_tool_contracts`) | stale_test | 16 | test_bvbrc_genome_alignment_tool_info 14, test_bvbrc_proteome_catalog_integration 2 | `root/resource_tool_information.py:82` | left failing (rewrite, not a one-line change) |
| `HMMER529_ATTEMPT` required at run time | environment | 15 | test_fluorescence_workflow 12, test_fluorescence_native_runtime 2, test_fluorescence_native_report_execution 1 | see C | left failing |
| Job-slot / CPU-thread ceilings removed from the capacity ledger | stale_test | 10 | test_local_resource_capacity 9, test_workflow_window_scope 1 | `gene_annotation_episode/defaults.toml:49-53` | left failing (tests of a removed ceiling: retirement candidates) |
| Adapter digest pinned from a different copy than the one bound | test_wiring | 10 | test_bvbrc_fastqutils_tool_info 8, test_bvbrc_application_returns 1, test_live_a106_binding 1 | `appservice_adapter_implementation_conflict`; 3 pin sites (`tests/test_bvbrc_fastqutils_tool_info.py:9,25`, `tests/test_bvbrc_application_returns.py:15`, `tests/test_live_a106_binding.py:11-12,142-143`) | left failing; import the adapter from `root.library` (a106 case needs the owner's intent) |
| Timeout arguments removed from the BV-BRC analysis client | stale_test | 7 | test_bvbrc_appservice_task_info 6, test_bvbrc_analysis_transport 1 | `gene_annotation_episode/bvbrc_analysis_transport.py:56-57,234` | fixed (run) |
| Wrong per-axis copy picked by the rewrite | test_wiring | about 30 | test_macs2_peak_execution 7 (a101 `PracticalState` rejects MACS2 jobs), test_bvbrc_minhash_* 5 (fixed in the helper, run), test_bvbrc_data_transport 4, test_component_native_return_instructions 5, test_alignment_site_publication 3, test_resource_result_receipt_preparation 2, single cases | per-file targets in the TSV | 5 fixed; rest left failing with the target named |
| Expectation older than a deliberate product change that predates the reorganisation | stale_test | about 25 | test_execution_launch_prompt_delivery 5, test_infernal_decision_presentation 6, test_reference_resolution 3, test_native_event_information 2 and others | each row names the product line and revision | left failing |
| Worker source-closure walk meets imports of moved modules and packages without `__init__.py` | product_defect | 3 | test_atac_differential_result_preparation 2, test_macs2_peak_components 1 | `gene_annotation_episode/native_atac_differential_preparation.py:48-71`; 11 dangling imports in shared code listed in the TSV | left failing |
| `ToolRegistry.catalog()` raised ModuleNotFoundError through `root/library/macs2_peak_tools.py:16,18` | product_defect | 2 | test_rna_evidence, test_operational_feedback | already corrected in the working tree by another agent after the run | none |
| Untracked inputs | environment | 5 | test_native_rna_structure_driver 2 (ViennaRNA site under `verification/`), test_infernal_preparation_result_views 1 (71 of 90 sheets), ledger artefacts 2 | | left failing |
| Unclear | unclear | 9 | test_detached_workflow 4, test_native_adapter_limits 3 (`service_did_not_initialize`), pytest internal error 2 | what was checked is in the TSV | left failing |

Implementation-digest pins of the A105 family (`*_dependency_mismatch`): none met in this cluster.

**Live request warning.** `tests/test_sequence_support_739.py` (line 404-412) patches `client._http`, but `addgene_sequences` takes the
authenticated path whenever a stored Addgene credential exists (`gene_annotation_episode/acquisition.py:918-921`), so the earlier
full run made one real authenticated Addgene request from this machine. I did not rerun that file. It should not be run again
until the credential lookup is patched in the test.

## C. Skipped tests in shard `toptests_b` (780)

| reason | count | files | condition | can repository material satisfy it? |
|---|---|---|---|---|
| requires bounded529 | 539 | test_addgene_sequence_facts 82, test_restriction_mapping_selection_734 78, test_circular_dichroism_contracts 76, test_restriction_mapping_references_731 62, test_flux_balance_result_worker_698 52, test_circular_dichroism_tools 41, test_addgene_sequence_returns 37, test_flux_balance_input_versions_708 34, test_restriction_mapping_declarations_733 28, test_flux_balance_assignment_702 17, test_restriction_mapping_jobs_726 16, test_restriction_mapping_publication_725 16 | module-level `skipif("HMMER529_ATTEMPT" not in os.environ)` | The variable is set only by `tests/bounded_execution/run_checks.py:446`, the old packet-529 runner (stages a frozen source/dependency snapshot under git-ignored `verification/`, 20 GiB handle). In 9 of the 12 files the variable is never read again, so the tests need nothing outside the repository (the audit calls them "needlessly gated"); 3 files (698, 726, 725) only write an output file into that directory. Satisfiable only by exporting the variable or removing the gate - neither done |
| application/native work requires bounded529 | 101 | test_native_flux_balance_producer_688 | same variable, used as a real attempt directory: reads `source_pins_before.json`, `stdlib_pins_before.json`, `dependency_pins_before.json`, `binary_pins_before.json`, `native_library_pins_before.json`, `dependencies/` | No. Only the packet-529 runner produces those files |
| application checks require bounded529 | 69 | test_flux_balance_result_projection_693 | same gate; writes `projection693-recorded-examples.json` into the directory; fixtures are tracked under `a110/tests/fixtures/flux_balance` | Yes in principle (any writable directory), not as configured |
| selected Cobra work requires the bounded runner | 46 | test_flux_balance_model_tools | same variable checked in a module fixture; cobra and optlang are installed in `.venv` | Yes in principle, not as configured |
| explicit selected genuine runtime/source/manifest execution only (+ glyco variant) | 7 + 2 | test_molecular_sequence_native | `HMMER_NATIVE_ORACLE_MOLECULAR_NATIVE(_V2)=1` plus `HMMER_NATIVE_ORACLE_MOLECULAR_DEPLOYMENT_FILE` / `..._GLYCO_DEPLOYMENT_FILE` | No. Deployment JSON files exist only in git-ignored `verification/tool_graders_hmmer_map_verification_2026-10-28_529/molecular_sequence_inputs_*/` |
| explicit selected native finite-driver verification within bounded529 only | 5 | test_molecular_sequence_driver | `HMMER_NATIVE_ORACLE_MOLECULAR_DRIVER_NATIVE=1`, `HMMER529_ATTEMPT`, both deployment files | No |
| genuine CLI controls require an explicitly selected pinned deployment | 5 | test_molecular_sequence_protease_private | `HMMER_NATIVE_ORACLE_PROTEASE_CLI_DEPLOYMENT` (a v3 deployment JSON) | No (only under `verification/.../protease_inputs_239/`) |
| Historical PMC supplement calibration fixtures not installed | 2 | test_literature_image_integration, test_source_custody_contracts (helper `tests/test_literature_assets.py:30-35`) | `validation/cases/dataset_unknown_candidate/supplement-audit/cloud-acquisition.json` in an ancestor directory | No. `validation/` does not exist; no such file anywhere in the checkout. Retirement candidates (depend on material that no longer exists) |
| user systemd/cgroup boundary unavailable | 1 | test_local_jobs | fixture probe `run_local_job` raised `local_job_boundary_unavailable` | Machine condition, not repository material; the reason inside the launcher was not traced |
| Explicit opt-in: a cgroup OOM test ... | 1 | test_local_jobs | `GENE_EPISODE_TEST_OOM=1` | Yes (pure opt-in), deliberately destructive |
| requires the explicitly selected built LUMPY executable and digest | 1 | test_lumpy_native_vcf_workflow | `HMMER_NATIVE_ORACLE_LUMPY`, `..._SHA256` | No LUMPY build in the repository (`software/` holds only bedtools) |
| requires explicit bounded genuine HOMER workflow selection | 1 | test_homer_motif_workflow | `HMMER_NATIVE_ORACLE_HOMER_WORKFLOW=1`, `HMMER529_ATTEMPT`, `HMMER_NATIVE_ORACLE_HOMER_DEPLOYMENT` | No |

## D. Edits and reruns

Edited (test files only, 22 files including one deletion; no product file touched): test_genomic_overlap_operands, test_flux_balance_native_capture_697,
test_rfam_batch_transport, test_practical_receipt_information, test_episode_admission, test_episode_completion,
test_native_infernal_publication, test_owned_child_waiting, test_decision_history, test_episode_source_checkpoint,
test_actual_tool_retriever, test_pdf_text_ranges, test_phylogeny_raxml_inputs, test_bvbrc_codon_tree_matrix_population,
test_decision_provider_frames, test_api_bvbrc_minhash, test_bvbrc_appservice_task_info, test_bvbrc_analysis_transport;
tests removed from test_context_credit, test_scientific_hypervolume_runtime, test_investigation_progress;
test_credit_integration_arithmetic.py deleted. 13 tests retired (19 failing cases), rows appended to `retired.tsv`.

| file | before (passed/total) | after | run |
|---|---|---|---|
| test_genomic_overlap_operands | 7/73 | 73/73 | 010 |
| test_flux_balance_native_capture_697 | 0/43 | 41/43 (2 FileNotFoundError, r2b) | 003 |
| test_rfam_batch_transport | 0/40 | 33/33 | 004 |
| test_practical_receipt_information | 5/21 | 21/21 | 005 |
| test_episode_admission | 3/11 | 11/11 | 006 |
| test_episode_completion | 2/18 | 15/18 | 007 |
| test_investigation_progress | 16/17 | 16/16 | 008 |
| test_native_infernal_publication | 5/27 | 5/27 (now fails on the missing worker module; 91 s instead of 3 s) | 011 |
| test_owned_child_waiting | 6/10 | 10/10 | 017 |
| test_decision_history | 31/34 | 33/34 | 018 |
| test_episode_source_checkpoint | 28/31 | 30/31 | 019 |
| test_actual_tool_retriever | 0/10 | 10/10 | 020 |
| test_pdf_text_ranges | 0/7 | 0/7 (next cause: helper setting) | 021 |
| test_phylogeny_raxml_inputs | 25/26 | 26/26 | 022 |
| test_bvbrc_codon_tree_matrix_population | 20/21 | 21/21 | 023 |
| test_decision_provider_frames | 7/8 | 8/8 | 024 |
| test_api_bvbrc_minhash (helper) | 12/88 | 48/88 | 025 |
| test_bvbrc_minhash_prospective_custody / metadata_custody (helper users) | 0/47, 1/26 | 0/47, 1/26 (IndexError rows of other owners) | 026, 027 |
| test_bvbrc_appservice_task_info | 11/17 | 17/17 | 028 |
| test_bvbrc_analysis_transport | 17/18 | 18/18 | 029 |
| unchanged controls: test_scientific_findings, test_finding_subject_feedback (use the helpers kept in test_scientific_hypervolume_runtime) | 16/17, 5/7 | 16/17, 5/7 | 031, 032 |
| test_tool_attribution (no edit, fresh run directory) | 0/16 | 15/16 | 009 |

`tests/test_context_credit.py` and `tests/test_scientific_hypervolume_runtime.py` now hold only helpers that nine other test
files import; run alone they collect no tests (pytest exit code 5, runs 033 and 034). They were not renamed because the
importing files include ones held by other agents.

Run timing: single diagnostic run expected under 10 s, actual 9 s; first batch of 8 files expected about 45 s, actual 102 s;
test_runtime expected about 30 s, actual 39 s; four `run_workflow` files expected about 60 s, actual 96 s; batch of 13 expected
3-4 min, actual 81 s; last batch of 5 actual 15 s; test_native_infernal_publication expected under 60 s, actual 91 s.

## E. Owner questions

1. Retained fixtures of the pre-2026-11-04 record version (`policy.wall_seconds: null`; also 20 GiB policies bound into
   retained requests): 169 + 19 + 8 cases across genomic overlap, infernal, minimap2, protein structure, chromatin. Regenerate
   them with the current drivers, or should current code read the historical records? No reader exists today.
2. Incidental `project_credit(store).credit == 0` assertions in five otherwise current test files (11 cases): delete the
   assertion, or wait for a numerical scorer?
3. `test_failed_execution_c4_input_is_null_and_cannot_stage` forbids crediting a failed execution; the product (before and
   after the reorganisation) projects credit for it, in line with AGENTS.md. Retire the test?
4. Four files held by another agent still carry 37 cases of the retired categorical scorer (test_credit 28, test_library_credit 7,
   test_annotation_score_separation 1, test_runtime 1): same retirement as applied elsewhere?
5. Scientific rows in the tail, not touched: test_published_axis_workflow (A108 retained source is now Markdown),
   test_protein_phylogeny_native_and_retained (support-meaning rule), test_genomic_overlap_inputs (`Source.source_ref` no longer
   required, retained contract still requires it), test_default_scientific_binding and test_scientific_child_credit
   (explicit task-credit declarations).
6. Product repairs that would clear the most cases and are outside what this round may change: C07 (one call, about 78
   cases), C06 (restore four methods, 40 cases), C10 (19), C08b (22), the source-closure walk (3).

## F. Basis

Verified by launcher runs: every "fixed" row in D; C07 for test_runtime and four tail files (archived tracebacks); C08 both
parts; C12; the second cause in test_pdf_text_ranges; the infernal-execution policy binding. Read from code and junit only:
C01, C03, C06, C09, C10, C11, C15 and all tail rows not listed in D. The three helpers' rows were not re-derived by me
except where a run is cited.
