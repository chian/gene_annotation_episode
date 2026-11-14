# r2e: a106, a107, a108, a110, root/tests, root/execution_monitoring/tests, root/homology_job_submission/tests

`R` = `gene_annotation_episode/episodic_workflow/root`. Source of counts: junit of runs `..._03_a106_a107` and `..._03_rest`
(1,734 failing cases; `homology_job_submission/tests` has none). Per-message join table: `r2e_causes.tsv` (120 messages, sums to 1,734).
Of the 1,734: 213 belong to r2b (import/path messages), 387 to r2a (shared fixtures), 465 carry the two ledger messages, 669 are mine.
Retired tests: 0. Product code edited: none.

How each statement was established: **[run]** = seen in a launcher run of mine (runs `runs/claude_r2_r2e_NNN`), **[probe]** = a run with
the disposable plugin `runs/claude_r2_r2e_scripts/r2e_probe.py` that prints locals at the failing frame (changes no behaviour),
**[read]** = read in code/git only, **[other run]** = taken from another agent's finished run directory.

## Causes

| # | Cause | Class | Cases (run 03) and groups | Evidence | Action | Scientific? |
|---|---|---|---|---|---|---|
| C1 | `GENE_DIRECT_TASK_PHASE` is never set. The `selected` fixture computes the phase from the code (`decision_source_type` on the binding: own task type -> `connected`, else `baseline`) and then asserts the environment says the same. | environment | 280 setup errors: `test_direct_private_tasks` (a107 132, a110 124), `test_direct_yield_identity` (a107 16, a110 8) | `R/a107/tests/direct_private_tasks.py:132-135`, same lines in a110. Only these two lines in the whole tree mention the name (tracked files and a full-tree grep outside `runs/`, `.venv`, `.git`); `git log -S` finds only dfe3e6091. `DIRECT_TEST_PORTS.md` describes a before/after port, so the setter was the command line of that procedure. [read] With `env GENE_DIRECT_TASK_PHASE=connected`: a107 130/2 and 16/0, a110 122/2 and 8/0 [other run: `runs/claude_triage_triage_a_08..11`]; the 4 left are `AttributeError: module ... has no attribute 'prepare_request'` (r2b family). | Left failing: no value faked, no skip. Needed: `GENE_DIRECT_TASK_PHASE=connected` in the environment of these four files in both axes. Nothing in the repository supplies it. `baseline` cannot occur in this tree (every one of the 8 classes computes `connected`). | No |
| C2 | Digest pin. | unclear (owner question) | 38: a106 `test_literature_optical_storage` | `R/a106/library/literature_optical_storage.py:55-57` (`_PINNED`), check at `:84-85`. Current sha256 of `literature_optical_inputs.py` 63fdc853..., `_validation.py` 59805105..., `_calculations.py` a090e091... ; none equals its pin. At 078b77668 only the calculations pin (1242c0e5...) equals the original file. [read] | Not edited. One pin site met. | Yes |
| C3 | Test imports the top-level `gene_annotation_episode.domain.ContractError`; a107 and a110 raise their own class (`a107/domain.py` is byte-identical to the top-level file but a distinct class object), so `pytest.raises(ContractError, ...)` never matched. | test_wiring (known family) | 138 in run 03: a107 `test_literature_partner_storage` 51, `_native_storage` 23, `_defined_storage` 9, `test_a107_experiment_identity_roles` 7; a110 `test_literature_reaction_storage` 38, `test_literature_reaction_meanings` 4, `test_a110_experiment_identity_roles` 3, `test_component_hpc_plan_admission` 3. Plus second layer after C4: a107 `test_literature_partner_assessments` 5, a110 `test_literature_reaction_assessments` 5, `test_literature_reaction_integration` 3 | First traceback of each group ends inside a `with pytest.raises(ContractError` block. [run] | Fixed in 12 test files: `ContractError` (and `canonical`/`obj`/`validate_schema`/`identity` where they are called under `raises`) imported from the axis `domain`. | No |
| C4 | `rate_population=True` passed to `LiteratureEpisode`; a106, a107 and a110 configurations have no such option. | stale_test | 11 in run 03 (a106) and 46+ behind the ledger message in a107/a110 (rerun 04 shows 38 a107 + 38 a110) | `R/a106|a107|a110/published_evidence_assessment/configuration.py:7`; a106 catalog adds the rate operations unconditionally (`library/literature_source_population_catalog.py:13-16`); `R/a107/tests/literature_task_checks.py:100` asserts `not hasattr(binding, 'rate_population')`; a106 sibling `test_literature_perturbation_integration.py:92` already calls without it. [read] | Fixed: keyword removed at 20 call sites in 10 test files. | No |
| C5 | After C4: a workflow test registers only the literature head binding. The original single `LiteratureEpisodes` was split into seven private bindings; the head declares child role `literature_strategy`, so `Workflow.__init__` fails. | test_wiring, not resolved | 23 now visible: a107 13 (`partner_native_integration` 6, `partner_integration` 4, `partner_defined_integration` 2, `structural_scalar_contexts` 1), a110 10 (`native_integration_129` 6, `reaction_integration` 2, `meanings_integration` 1, `native_primary_129` 1) | `KeyError: 'literature_strategy'` at `R/a107/runtime.py` (`children[self.grains[role]] = ...`). Registering all seven a107 bindings as peers instead fails with `received_report_field_conflict:received_report_sources` (`R/a107/episode_bindings.py:311`). [run, trial reverted] | a107/a110 left failing: I found no supported way to compose the split tree under an annotation root. a106: the seven-binding composition assembles, so the two a106 tests now use `create_binding_tree` (they then reach C6). | No |
| C6 | a106 only, behind C5: the scripted root commission of a `literature` child is rejected with `literature_original_task_credit_required`. The rule does not exist at 078b77668. | stale_test | 2: a106 `test_literature_perturbation_summary_integration::test_summary_operation_in_ordinary_child...`, `test_literature_perturbation_covariance_meanings::test_ordinary_child_parent...` | `R/a106/published_evidence_assessment/goal.py:55-59`; feedback printed by the probe. [probe] | Left failing: the tests would have to commission with a `literature_task` credit declaration. | Yes (credit rule) |
| C7 | a106 perturbation unit enums gained `CFU_per_initial_OD_per_mL` and `per_h` in dfe3e6091. The "legacy 55/56 field" schema variants are derived from the current schema, so the frozen fixtures differ and the registered-source check rejects the frozen schemas of saved forms. | product_defect (owner question) | 3: a106 `test_literature_perturbation_interpretation_basis` 2 (1 was hidden behind C4), `test_literature_perturbation_covariance_meanings::test_registered_legacy55_and56...` 1 | Probe diff: `endpoint_unit.enum` 8 vs 6, `unit.enum` 73 vs 61; `R/a106/library/literature_perturbation_storage.py:275,291`; `R/a106/communication.py:596-600`. [probe] | Not edited. | Yes (which saved report schemas are admitted) |
| C8 | Commit 22c1bab66 (automated re-pointing) rewrote string literals that deliberately name the pre-reorganisation module recorded in saved artefacts. | test_wiring | 26: root `test_fluorescence_module_identity` 15, `test_blast_producer_identity` 2 of 4, `test_lumpy_saved_driver_identity` 4, `test_protein_saved_module_identity` 2; a107 `test_received_worker_source_routes` 2; a106 `test_retained_amount_identity` 1 | `git show 22c1bab66 -- <file>` shows only these literal lines changed; the retained plan has `argv[4] == 'gene_annotation_episode.native_fluorescence_driver'`. [read, run] | Fixed: literals restored in 5 files (each file is now identical to its pre-22c1bab66 text). The protein file had already been restored by another agent; I only verified 9/9. | No |
| C9 | The mandated `--basetemp=runs/<run>/tmp` puts `tmp_path` inside the repository root, which the test declares as the producer `module_root`; the driver rejects a manifest inside its inventory root. | environment | 2: root `test_blast_producer_identity[runtime_self]`, `[runtime_wrong_entry]` | `R/library/native_blast_database_driver.py:218-219`; probe prints `INSIDE True`, manifest validation otherwise passes. [probe] | Left failing. Would pass with a temp directory outside the checkout, which AGENTS.md forbids. | No |
| C10 | Retained fixture carries a three-field job policy (`wall_seconds: null`); the current schema allows exactly `memory_bytes` and `scratch_bytes`. | stale_test | 16 setup errors: root `test_native_genomic_overlap_shared` | Probe: `['policy'] Additional properties are not allowed ('wall_seconds' was unexpected)`; fixture `R/tests/fixtures/genomic_overlap/native_work/WORKED_EXAMPLE_NATIVE_CONTRACT.json` (`plan.policy`, `batch_manifest.policy`, `assignment.constraints.allocation`); schema `R/library/native_genomic_overlap_job_schema.py:9-22`. [probe] | Not edited: the test file is being edited by another agent. Proposed: drop `wall_seconds` from the fixture's three policy blocks. | No |
| C11 | Every a108 private composer starts with a dead `if source.workflow.is_job_source(source): pass`; the test treats any `is_job_source` call as dispatch to the unclaimed composer. | product_defect | 15: a108 `test_private_instruction_service_port::test_default_service_uses_actual_private_static_composer` (all 15 homes) | `R/a108/**/task_instructions.py:5-6` (15 files, all with `pass` as the body). Test and code are from the same commit. [read] | Left failing. Repair: delete the two dead lines in the 15 files (product). | No |
| C12 | The presenter rebuilds state through canonical JSON (sorted object keys); the renderer emits tool argument rows in dict order. The test compares against the renderer applied to the insertion-ordered fixture. | stale_test | 16: a108 `test_root_delivery` (14 + 2) | Probe diff is only the order of four `arguments.*` rows; `R/a108/decision_context.py:17-18`. a101 `test_root_delivery` fails the same way. [probe] | Left failing: no independent evidence for either order. Proposed: compare with the renderer applied to `json.loads(canonical(state))`. | No |
| C13 | a110 "historical" masking/utility readers require policy keys exactly `{memory_bytes, scratch_bytes}`; the authentic saved plans (content-addressed fixtures) carry `wall_seconds`. | product_defect (owner question) | 5: a110 `test_saved_masking_utility_readers` | `R/a110/library/received_execution_information/historical_native_blast_masking_contracts.py:199-201`, `historical_native_blast_utility_contracts.py:426`; fixtures under `R/a110/tests/fixtures/masking_utility_saved_readers/`. [read] | Not edited. | Reads of saved results, not grading |
| C14 | `R/received_fact_declaration.py` picks an axis parser from `child.assignment['selection']` and raises for a child without one; the test expects root redelivery "without axis inference". | unclear (owner question) | 8: root `test_root_saved_report_redelivery` (6 + 2 regex) | `R/received_fact_declaration.py:6-22`, `R/scientific_process_records.py:137-144`, `R/episode_return_records.py:154-160`. Root has its own parser at `R/episode_contract_information.py:244`. Test and code are from the same commit. [read] | Not edited. | Report redelivery acceptance |
| C15 | Product now calls `receipts.read(..., historical=...)`; the stub is `lambda *_`. | test_wiring | 9: root `test_fluorescence_episode_routing` | `R/library/execution_progress.py:275-284`; stub at `R/tests/test_fluorescence_episode_routing.py:520`. [read] | Not edited (file modified by another agent). Proposed: `lambda *_, historical=False: deepcopy(body)`. | No |
| C16 | The root-level `ResourceEpisodes` and `ExecutionEpisodes` are shells: the binding methods of the original classes are gone, so they fail root's own `EpisodeBinding` protocol. | product_defect | 22: root `test_launch_instruction_runtime` 9, `test_rna_structure_results_prompt` 8, `test_execution_local_file_sources` 3, `test_execution_closed_credit` 1, `test_resource_selected_adapter_return` 1 | `R/resource_episodes.py` (69 lines: `__init__`, `configuration`, `as_record` + 6 custody methods) against 22 methods at 078b77668; `R/execution_episodes.py:29` has 3 own methods against 126; no `instructions`/`fact_sources`/`credit_view` in root or `root/library`. `R/episode_bindings.py:302-303`. [read] | Not edited. Owner decision: restore the methods or retire the root monolith and these tests. | `credit_view`/`validate_report` are among the missing methods |
| C17 | The tests request the Lumpy local-job policy memory, above the launcher bound. | environment | 7: root `test_native_lumpy_execution` | `gene_annotation_episode/workflow_budget.py:117-121` (`native_request_exceeds_environment_bounds`), bound 5 GiB at `:35`. [read] | Left failing. | No |
| C18 | `a104.episode_bindings.BindingContext` is the root class (imported), so the fixture precondition "foreign axis class is distinct" is false. | unclear (owner question) | 7: root `test_root_enrichr_controlled_receipts` | `R/a104/episode_bindings.py:51`; a101, a105, a106, a108 import it too; a102, a103, a107, a110 define their own. [read] | Not edited. | No |
| C19 | `yield.py` was renamed `yield_estimator.py` (commit 5cafe5c43); fixtures still name the old module. | stale_test | 36 mine: `execution_monitoring/tests/test_monitor_source_identity` 18, a107 `test_native_input_yield_ownership` 6, a110 `test_native_yield_ownership` 12 (plus 27 r2b `FileNotFoundError ... yield.py` in the same monitor file) | Probe diff is only `...yield.ExecutionEpisodeYield...` vs `...yield_estimator...`; `R/execution_monitoring/binding_identity.py:8`. [probe, run] | Fixed: module name updated in `expected_members.json` and the two `*_yield_baseline.json`. | No |
| C20 | A test builds tool registries of two axes (a108 and a105) in one process; the second meets the first one's local-resource binding. | environment (ledger family, but reproduces for a file alone) | 5 in rerun 04: a108 `test_original_molecular_material_port` 3, `test_original_enrichr_material_port` 1, `test_original_enrichr_publication_guard` 1 | `R/a105/local_resources.py:117,143` reached from `R/a105/tools.py:60`. [other run: rerun 04; not re-run by me] | Not edited. | No |
| C21 | The worker double returns metadata without `policy`/`verified_cgroup`; publication requires the verified 20 GiB cgroup (same requirement at 078b77668). | test_wiring, not resolved | 5 setup errors: a107 `test_information_rna_custody` | `R/a107/tests/test_information_rna_custody.py:42`; `R/a107/rna_structure_comparison_publication.py:183-187`. [read] | Left failing: the double would have to assert a verified 20 GiB cgroup that never existed. | No |
| C22 | a106 `_receive_form` asks `episode_bindings.for_child` when the binding has `child_report_receiver_for_binding`; the double lacked it. | test_wiring | 4: a106 `test_private_literature_messages` | `R/a106/report_receiving.py:6-12`. [run] | Fixed: `for_child` added to the double. | No |
| C23 | Product reads a new provider `api_execution.application_returns`; the double lacked it. | test_wiring | 2: root `test_api_service_result_ordering` | `R/execution_scientific_returns.py:182`. [run] | Fixed. | No |
| C24 | a106 `facts(context, {'committed_record_refs': [second]})` returns cells of three sheets (the revised-away first, the committed second, another experiment's); `validate_report` then needs `services.record_selection`. | unclear | 2: a106 `test_literature_perturbation_assessments` | Probe prints the three sheet refs; `R/a106/published_evidence_assessment/to_parent.py:112-116` adds `current_sheet_refs`; this code and the test are unchanged from 078b77668, so I could not tell what changed. [probe] | Not edited. | Yes (what is reported) |
| C25 | `R/task_selection.py:12` indexes `path[-1]` before validating (empty path -> `IndexError`), and `:12-14` returns the legacy annotation binding for a root-level `improvement` path where the test expects `episode_role_not_bound:improvement`. | product_defect (1) + unclear (1) | 2: root `test_root_task_declaration` | [read] | Not edited. | No |
| C26 | `_report_source_bindings` returns a tuple; the test compares with a list. | stale_test | 2: root `test_root_binding_owners` | junit diff shows only `[` vs `(`. [read] | Left failing. | No |
| C27 | `a110_legacy_v2_125.json` pins record ids from when subject/construct literals were typed `assay`. | stale_test (owner question) | 1: a110 `test_literature_reaction_meanings::test_portable_old_v2...` | Probe: only `assayed_subject_ref`, `construct_ref` and the sheet id differ; test, fixture and `LITERAL_REFERENCE_TYPES` are identical at 078b77668, so it failed before the reorganisation; sibling `test_a110_experiment_identity_roles` (7/7) asserts the new roles. [probe] | Left failing. | Evidence identity |
| C28-C33 | Single cases: `test_scientific_catalog_operation` (patched instance attribute not called; unclear), `test_signed_evidence_root` (patch target `root.scoring.received_axis_task_credit` does not exist; defined in `R/axis_return_admission.py:8`, `R/returns.py:23`; test_wiring, file owned by another agent), `test_monitor_credit_factory[a106]` (a106 factory needs `as_record()['configuration']`; test_wiring), `test_atac_differential_execution_integration` (see import note below; product_defect), a108 `test_scientific_presentation_fields` (patched the unused module-level `yield_table`; **fixed**), `test_lumpy_execution_registration` (local catalog is `exec_command` only; stale_test), `test_native_genomic_overlap_shared` `genomic_overlap_software_binding` (not traced; unclear), a110 `test_literature_reaction_integration` prompt text (`REFERENCE_PARENT_TASK` not in the rendered parent prompt; not traced; unclear). | see left | 7 in run 03 + 1 second layer | [read], [run] for the fixed one | 1 fixed, 7 left | No, except the prompt text |

Not in the table (6 of my 669): root `test_chromatin_interaction_execution_information` 2 (regex mismatch whose actual message is r2a's `public_client_run_directory_required`), a107/a110 `test_implicit_annotation_parent` 1 each (actual message was the ledger one; both files pass 84/84 in rerun 04), root `test_private_binding_identity[a103]` 2 (known `legacy_parent_for_path` cause).
The table accounts for 663 + these 6 = 669.

Further second-layer results after the ledger cleared (rerun 04) that are not in run 03:
- root `test_bvbrc_minhash_commission_replay` 31 x `IndexError`: `tests/test_api_bvbrc_minhash.py:18` builds top-level `acquisition.SourceSnapshot` objects while lines 19-20 were re-pointed to `R/a102/api_bvbrc_minhash`, whose `isinstance` check uses `R/a102/acquisition.SourceSnapshot` (a different class); the primitive answers `bvbrc_minhash_response_required`, no record is published, the helper indexes an empty list. test_wiring. [probe] File is outside my directories and modified by another agent.
- root `test_execution_tool_contract_declarations` 2: top-level `ContractError` against `R/a102/api_bvbrc.py:360` raising `a102.domain.ContractError` (C3 family). File modified by another agent.
- a107 `test_literature_partner_integration` 4: `saved partner evidence must not be reinterpreted`; `R/a107/published_evidence_assessment/source_operations.py:43,96` now builds `_Sources` (text-witness materialisation) before the saved replay. Scientific (replay of saved evidence); not edited.
- a107 `test_literature_partner_native_integration` 6: the catalog stub ignored the product's `_accept_legacy_quotes=True` (`source_operations.py:53`). **Fixed** (stub keeps both saved catalogs).
- a110 `test_literature_reaction_graph_origin_129` 6 and `native_integration_129` 2: `binding.services.literature_reaction_repository()`; the accessor is on the binding (`R/a110/published_evidence_assessment/reaction_records.py:6`, used so by `R/a110/tests/literature_task_checks.py:295`). **Fixed.**
- a107/a110 `test_private_reconstruction` 1 each: directories with `episode.py` now include `.` and `annotation_improvement`, which the reconstruction catalog does not cover. unclear.
- a107 `test_received_api_role_discovery` 4: binding has no `received_report_sources` (3) and `received_execution_original_factory_required` (1, same as round-one cause C of triage_a). Not edited.

Import note for r2b / owner (met while tracing C31): `R/a101/annotation_improvement/task.py:60,63` and `R/a104|a106/annotation_improvement/task.py:66`
use one-dot imports (`from .providers import ModelCallError`, `from .episode_source_failure import record_source_failure`) although both modules
are one level up (`R/a101/episode_source_failure.py`). The atac worker source closure follows them and stops with `native_dependency_unavailable`.

## Reaches outside services
Not run by me and should not be run without review:
- `R/tests/test_addgene_selected_process_path.py`: builds a real `PublicClients(ncbi_email=None)` with an Addgene `sequence_support` assignment (line 118); `urlopen` is patched only inside individual tests (lines 256, 402).
- `R/tests/test_default_root_tools_constructor.py`: builds a default `ToolRegistry` with real `PublicClients` (constructor assertions only; not verified that nothing connects).
I found no ssh/remote launch or home-directory credential read in the test files of my seven directories (grep for PublicClients, addgene, home/expanduser, netrc, ssh, alcf, urlopen, requests, credential). I did not audit product code for network use.
My 75 runs before the rule were in the old form (real home, no proxy block); all were literature storage/integration, identity, yield and monitor tests with scripted providers. The final 38-file batch was rerun in the new form with identical results, so nothing changed because of the empty home or the blocked proxy.

## Runs
Launcher only, slot `r2e`, one file per run. Runs 001-074 old form; from 075 on `runs/claude_r2_r2e_NNN/run` with empty `runs/claude_r2_r2e_NNN/home` and the proxy prefix
(the launcher refuses an existing run directory, so the home is a sibling of the launcher directory, not inside it).
Run 015 was a scratch test under `runs/` that stalled on directory scanning; I stopped my own unit and removed the file.
Final batch: expected 175 s (measured_03), actual 171 s wall for 38 files.

| File | run 03 pass/fail | rerun 04 pass/fail | now pass/fail |
|---|---|---|---|
| `a106/tests/test_literature_perturbation_covariance_meanings.py` | 7/7 | - | 12/2 |
| `a106/tests/test_literature_perturbation_summary_integration.py` | 2/3 | - | 4/1 |
| `a106/tests/test_private_literature_messages.py` | 44/4 | - | 48/0 |
| `a106/tests/test_retained_amount_identity.py` | 9/1 | - | 10/0 |
| `a106/tests/test_literature_perturbation_assessments.py` | 3/2 | - | 3/2 |
| `a106/tests/test_literature_perturbation_interpretation_basis.py` | 11/2 | - | 11/2 |
| `a106/tests/test_literature_perturbation_missing_amount_unit.py` | 15/23 | - | 38/0 |
| `a107/tests/test_a107_experiment_identity_roles.py` | 5/10 | - | 12/3 |
| `a107/tests/test_literature_partner_defined_storage.py` | 8/9 | - | 17/0 |
| `a107/tests/test_literature_partner_native_storage.py` | 20/23 | - | 43/0 |
| `a107/tests/test_literature_partner_storage.py` | 15/51 | - | 66/0 |
| `a107/tests/test_literature_structural_scalar_contexts.py` | 132/3 | 132/3 | 134/1 |
| `a107/tests/test_literature_partner_defined_integration.py` | 2/2 | 2/2 | 2/2 |
| `a107/tests/test_literature_partner_integration.py` | 0/10 | 0/10 | 1/9 |
| `a107/tests/test_literature_partner_native_integration.py` | 0/13 | 0/13 | 6/7 |
| `a107/tests/test_literature_partner_assessments.py` | 0/5 | 0/5 | 0/5 |
| `a107/tests/test_received_worker_source_routes.py` | 12/2 | - | 14/0 |
| `a107/tests/test_native_input_yield_ownership.py` | 12/6 | - | 18/0 |
| `a107/tests/test_a107_requirement_experiment_binding.py` | 0/7 | 0/7 | 7/0 |
| `a108/tests/test_scientific_presentation_fields.py` | 5/1 | - | 6/0 |
| `a110/tests/test_a110_experiment_identity_roles.py` | 4/3 | - | 7/0 |
| `a110/tests/test_component_hpc_plan_admission.py` | 2/3 | - | 5/0 |
| `a110/tests/test_literature_reaction_meanings.py` | 13/5 | - | 17/1 |
| `a110/tests/test_literature_reaction_storage.py` | 9/38 | - | 47/0 |
| `a110/tests/test_literature_reaction_integration.py` | 0/7 | 0/7 | 3/4 |
| `a110/tests/test_literature_reaction_native_primary_129.py` | 0/1 | 0/1 | 0/1 |
| `a110/tests/test_literature_reaction_meanings_integration.py` | 0/1 | 0/1 | 0/1 |
| `a110/tests/test_literature_reaction_native_integration_129.py` | 0/11 | 0/11 | 5/6 |
| `a110/tests/test_literature_reaction_assessments.py` | 0/5 | 0/5 | 5/0 |
| `a110/tests/test_literature_reaction_graph_origin_129.py` | 0/6 | 0/6 | 6/0 |
| `a110/tests/test_native_yield_ownership.py` | 0/12 | - | 12/0 |
| `a110/tests/test_a110_experimental_finding_binding.py` | 0/8 | 0/8 | 8/0 |
| `tests/test_fluorescence_module_identity.py` | 1/15 | - | 16/0 |
| `tests/test_blast_producer_identity.py` | 7/4 | - | 9/2 |
| `tests/test_lumpy_saved_driver_identity.py` | 9/4 | - | 13/0 |
| `tests/test_api_service_result_ordering.py` | 4/2 | - | 6/0 |
| `tests/test_protein_saved_module_identity.py` | 7/2 | - | 9/0 |
| `execution_monitoring/tests/test_monitor_source_identity.py` | 1/45 | - | 46/0 |

Totals for these 38 files: run 03 359 passed / 356 failed; now 666 passed / 49 failed. The 49: C5 23, C6 2, C7 3, C24 2, C9 2, C27 1,
a107 replay 4, a110 prompt text 1, and 11 r2b import cases (`a107.literature_partner_calculations` 8, `test_literature_experimental_prompt_delivery` 3).

## Edits (`git diff --stat`, tests and fixtures only)
```
 ..._literature_perturbation_covariance_meanings.py |  7 ++---
 ..._literature_perturbation_summary_integration.py | 11 +++++--
 .../a106/tests/test_private_literature_messages.py |  4 ++-
 .../a106/tests/test_retained_amount_identity.py    |  4 +--
 .../a107_native_input_yield_baseline.json          | 12 ++++----
 .../tests/test_a107_experiment_identity_roles.py   |  2 +-
 .../tests/test_literature_partner_assessments.py   |  2 +-
 .../test_literature_partner_defined_integration.py |  4 +--
 .../test_literature_partner_defined_storage.py     |  2 +-
 .../tests/test_literature_partner_integration.py   |  4 +--
 .../test_literature_partner_native_integration.py  |  9 +++---
 .../test_literature_partner_native_storage.py      |  2 +-
 .../a107/tests/test_literature_partner_storage.py  |  2 +-
 .../test_literature_structural_scalar_contexts.py  |  4 +--
 .../tests/test_received_worker_source_routes.py    |  4 +--
 .../tests/test_scientific_presentation_fields.py   |  3 +-
 .../a110_native_yield_baseline.json                | 24 +++++++--------
 .../tests/test_a110_experiment_identity_roles.py   |  2 +-
 .../tests/test_component_hpc_plan_admission.py     |  2 +-
 .../tests/test_literature_reaction_assessments.py  |  2 +-
 .../test_literature_reaction_graph_origin_129.py   |  4 +--
 .../tests/test_literature_reaction_integration.py  |  6 ++--
 .../tests/test_literature_reaction_meanings.py     |  2 +-
 ...est_literature_reaction_meanings_integration.py |  4 +--
 ...t_literature_reaction_native_integration_129.py | 10 +++---
 .../test_literature_reaction_native_primary_129.py |  2 +-
 .../a110/tests/test_literature_reaction_storage.py |  2 +-
 .../expected_members.json                          | 36 +++++++++++-----------
 .../root/tests/blast_producer_identity_checks.py   |  2 +-
 .../tests/fluorescence_module_identity_checks.py   |  4 +--
 .../root/tests/test_api_service_result_ordering.py |  3 +-
 .../root/tests/test_lumpy_saved_driver_identity.py |  2 +-
 32 files changed, 96 insertions(+), 87 deletions(-)
```
