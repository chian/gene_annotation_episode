# r2a: shared-interface cluster (2,458 cases, 14 messages, 975 group rows)

Scope: every `groups.tsv` row whose message contains one of the eight strings in the assignment.
Companion files: `r2a_causes.tsv` (one row per message), `r2a_rerun.tsv` (before/after per rerun file).
Edits are test files only (154 files, +432/-402). No product file was edited. Nothing was retired.

The assignment guessed "a few shared fixtures". That holds for only part of the cluster. The two largest causes
are product interface changes that every test file meets directly at its own call site.

## Causes

| # | Cause | Class | Cases (group rows) | Evidence | Action | Scientific? |
|---|---|---|---|---|---|---|
| 1 | Kernel copy split. Tests import `EpisodeGoal`/`EpisodeRequest` from the top-level `method_loop`, but wrap the message in a `Record` whose `ClosedRecord` base is a private copy. The `isinstance` check fails. No top-level `ClosedRecord` subclass exists any more. | test_wiring | 995 (383) | `method_loop/episode.py:399`; `root/task_values.py:3,25`; `root/a101/runtime.py:25,131`; `tests/test_bvbrc_appservice_custody.py:90` alone carried 383 cases | Fixed: 32 files re-pointed to `root.method_loop` (2 a101 files to `a101.method_loop`). 0 cases with this message remain. | no |
| 2 | `ToolRegistry.__init__` now requires `clients` or `run_directory`; the pre-reorganisation default `PublicClients()` is gone. Tests call `ToolRegistry(store)`. | stale_test | 893 (437) | `root/tool_registry.py:68-69,80-81`; `git show 078b77668:gene_annotation_episode/tools.py` (`self.clients = clients or PublicClients()`); passing sibling `root/tests/test_default_root_tools_constructor.py:24-27` | Fixed: `run_directory=<store>.path / 'tool-run'` added at 291 call sites in 113 files (`tests/*.py`, `root/tests/*.py`; fixture directories untouched). 0 cases remain. | no |
| 3a | Fixture API resources carry a `timeout` key that fresh construction refuses (rfam_batch, bvbrc_data). | stale_test | 66 | `gene_annotation_episode/api_services.py:86-91`; `root/execution_service_setup.py:126-131`; AGENTS.md "no elapsed-time ... cutoffs" | Fixed: key dropped at `tests/test_rfam_batch_returns.py:133` and `tests/bvbrc_episode_fixture.py:34`. | no |
| 3b | Enrichr cannot be built fresh at all: the same `timeout` key is refused at fresh construction and required by the Enrichr configuration validator. | product_defect | 87 | `root/enrichr_publication_metadata.py:29-30`; `gene_annotation_episode/api_enrichr.py:121`; `root/tests/test_root_enrichr_publication_metadata.py:107` (required fields are not defaulted) | Left failing. I removed the key, saw `enrichr_configuration_invalid` (44 errors), and restored it. Owner question 1. | no |
| 4 | `prepare_scientific_binding` gained a required `episode_type`; the old code hard-wired `ScientificProcessEpisodes`. | test_wiring | 131 (36) | `gene_annotation_episode/scientific_process_setup.py:8-11`; `git show 078b77668:` same file line 21 | Fixed in 28 files. Root and `tests/` use `root.scientific_process.episode.ScientificProcessEpisodes`; a101 tests use a101's own setup module and `ScientificProcessEpisode`. The a101 cases then fail for cause 5. | no |
| 5 | a101 tests hand root `ExecutionServiceFactory` output to `a101.runtime.Workflow`. a101 rejects the root services class by exact type and does not know root binding ids. a101, a105 and a108 have no private `execution_service_setup`; the other six axes do. | product_defect | 75 (22), plus the 121 a101 cases released by cause 4 | `root/a101/runtime.py:1136-1137`; `root/a101/private_binding_factories.py:8-10` (`KeyError: 'root_execution_job_submission'`); `root/a101/episode_composition.py:177`; pre-reorganisation test imported one shared `Workflow` and factory | Left failing. Owner question 2. | no |
| 6 | Hand-built `SimpleNamespace` workflow doubles lack `job_episode_options` (a108 also `permits_common_action`). | test_wiring | 74 (4) | `root/a105/scientific_process/decision_inputs.py:23`; `root/a108/published_evidence_assessment/decision_inputs.py:20` and `task_decision.py:78`; sibling doubles `root/a108/tests/improvement_parent_checks.py:70` | Fixed in 2 files: a105 14/14 pass (was 2), a108 62/62 pass (was 0). | no (presentation plumbing; no assertion touched) |
| 7 | Retained run plans carry `policy.wall_seconds: null` (16 plans); the closed policy schema allows only `memory_bytes` and `scratch_bytes`. The mismatch predates the reorganisation. | unclear | 74 (15) | `root/library/native_protein_structure_job_schema.py:96-99`; `root/a102/tests/fixtures/protein_structure_capture_392/FILLED_CAPTURE_EXAMPLES_001.json`; `git show 078b77668:gene_annotation_episode/native_protein_structure_contracts.py` line 313 | Left failing. Owner question 3. | yes: decides which retained records are admissible |
| 8 | Test constant used a 20 GiB launch policy; the root library copy fixes it at 5 GiB and keeps 20 GiB only for recorded plans. | stale_test | 61 (15) | `root/library/native_protein_structure_preparation.py:83,559`; `root/library/native_protein_structure_job_schema.py:21-23`; the file's own case at line 218 expects any other policy to raise | Fixed `tests/test_native_protein_structure_preparation.py:37`: 4 to 19 passing. The other 61 cases now fail for a product defect (see below). | no |
| 9 | The automated re-pointing commit rewrote historical module-name string constants to the current names. | test_wiring | 2 (1) | `root/tests/protein_saved_module_identity_checks.py:11-12`; `git show 22c1bab66`; product `_RECORDED_MODULE_PAIRS` at `job_schema.py:12-14` | Fixed: restored the two names from `dfe3e6091`; 9/9 pass. | no |

Paths written `root/...` are under `gene_annotation_episode/episodic_workflow/`.

## Product defects found while fixing (not edited)

- **Protein-structure handle check.** `gene_annotation_episode/native_lifecycle.py:157-158` adds
  `GENE_EPISODE_WORKFLOW_BUDGET_FILE` and `GENE_EPISODE_WORKFLOW_SLOT` to the request environment.
  `_check_handle` (`root/library/native_protein_structure_preparation.py:292-295`) compares against the
  environment without them and raises `original_commission_mismatch` (61 cases). Confirmed by a diagnostic run.
- **Missing module.** `gene_annotation_episode/tool_information.py:153` and `api_services.py` import
  `gene_annotation_episode.api_uniprot`, which exists only as nine per-axis copies (90 cases in 14 files).
  The repair needs an axis choice, so it is outside the import-line exception.
- **Two `BindingContext` classes.** `gene_annotation_episode/molecular_measurement_tools.py:643,660` type-checks
  against the top-level `episode_bindings.BindingContext`; root builds `root.receiving_context.BindingContext`
  (`molecular_tool_invalid_context`, 13 cases). 26 module names exist both at top level and in root; root product
  code imports none of the top-level copies; 96 test files still import the top-level `BindingContext`.

## Rerun results

235 files rerun to completion (every edited test file, files importing an edited helper, and the 19 other files
that carried a cluster message).

| | passed | failed | errors | skipped | files with no failure |
|---|---|---|---|---|---|
| before (run 03) | 2,067 | 1,861 | 2,162 | 245 | 19 |
| after | 3,737 | 1,633 | 719 | 245 | 64 |

- 115 files changed counts; none lost a passing test; 45 files went from failing to fully passing.
- By directory, passed before to after: `tests/` 1,452 to 2,939 (162 files); `root/tests` 132 to 215 (30);
  `a101/tests` 165 to 184 (29); `a105/tests` 298 to 317 (11); `a108/tests` 0 to 62 (1).
- Previously passing files that use an edited helper still pass: `a101/tests/test_bvbrc_proteome_bundle_v2_resolution.py`
  (29), `a104/tests/test_homology_family_public_resume.py` (4), `a107/tests/test_retained_molecular_contracts.py` (16),
  `tests/test_bvbrc_comparative_systems_sheet.py` (43), `tests/test_bvbrc_proteome_document_selection.py` (34).
- Not completed: `tests/test_bvbrc_proteome_host_integration.py` (first test ran 8.5 minutes and failed; I stopped my
  own run) and `tests/test_atac_differential_operands.py` (pytest INTERNALERROR after 19 tests: a failing test at
  lines 203-205 patches `Path.stat`/`resolve` globally, which breaks pytest's own failure reporting).
- Not run: `root/tests/test_addgene_selected_process_path.py` (see "Reaches outside services").

Durations, expected (from `measured_03.tsv`, when most tests failed at setup) against actual: first 3 files 10 s
against 57 s; 23-file sample 131 s against 15 min 16 s; 139-file batch 1,188 s against about 30 min; last 19 files
270 s against 7 min 44 s. Unblocked tests do real work and the machine load average was about 34 on 12 cores.

## Remaining failures in the rerun files (2,352 cases, classified briefly, not chased)

| Cases | Class | What |
|---|---|---|
| 232 | test_wiring | Dotted-string targets still at pre-move paths, e.g. `monkeypatch.setattr('gene_annotation_episode.' + module + ...)` in `tests/test_native_infernal_preparation_returns.py:279-290` (54; all 8 modules now in `root/library`), `a101/tests/test_native_hmmer_preparation_returns.py:243-248` (54), `tests/test_native_infernal_returns.py:176-182` (43), `a101/tests/test_blast_native_return_admission.py:177-182` (39), `tests/test_rfam_batch_returns.py:258-259` (23) |
| 198 | product_defect | Cause 5 (a101 `unavailable_binding` 121, plus the original message in files not edited) |
| 176 | product_defect / stale_test | Cause 3b Enrichr (136), plus `tests/test_rfam_report_publication_returns.py:96` (39) and one dependent: same `timeout` key, file already modified by another agent so I did not edit it |
| 152 | stale_test or product_defect | Root `ExecutionEpisodes` lacks `prepare_assignment`, `execute`, `fact_sources`, `credit_view`, `facts`, `initialize`, `assignment_schema` that it had before (`git show 078b77668:gene_annotation_episode/execution_episodes.py` lines 1468, 2759, 3556, 4716) |
| 135 | see causes 7 and 8 | Protein-structure `invalid_schema` (74) and `original_commission_mismatch` (61) |
| 116 | environment | Files missing: `verification/tool_graders_infernal_preparation_...` (108, untracked directory), `validation/calibration/rhea-stoichiometry.entity` (6) |
| 103 | stale_test (scientific) | `categorical_annotation_scoring_retired_use_original_snapshot_for_historical_replay` at `gene_annotation_episode/credit.py:34` in 19 files |
| 99 | test_wiring | Other missing names: `'Workflow' object has no attribute 'tools'` on hand-built doubles, `root.runtime` has no `TypedReportContract` / `_category_yield_parameters`, `validate_pending` not in `root.waiting` |
| 96 | product_defect / test_wiring | Binding context and parent-role mismatches: `complete_episode_binding_required`, `episode_role_requires_parent:launch_api`, `molecular_tool_invalid_context`, `flux_balance_return_binding_context_required` |
| 90 | product_defect | Missing `gene_annotation_episode.api_uniprot` (above) |
| 87 | owner question (known) | Implementation-digest pins: `product_coupling_prospective_dependency_mismatch` (64, `a105/library/literature_product_coupling_storage.py`), `measurement_validation_prospective_dependency_mismatch` (22, `a105/library/literature_measurement_validation_storage.py`), `literature_optical_implementation_dependency_mismatch` (1, `a105/library/literature_optical_storage.py`) |
| 87 | test_wiring | Sibling test modules no longer importable (`test_contract_information_runtime_059`, `test_native_blast_standard_database_episode_binding`, ...) |
| 62 | stale_test | Machine-bound constants: `assert 5368709120 == (20 * (1024 ** 3))`, `whole_workflow_budget_unavailable` in a101, `KeyError: 'job_slots'` |
| 28 | stale_test | `explicit_root_task_credit_required` (`root/default_scientific_binding.py:21`): `run_workflow` without `resume` now needs explicit root task credit; 12 files |
| 19 | environment | Environment variables not set: `HMMER529_ATTEMPT` (14), `NMF488_SOFTWARE` (5) |
| 672 | not analysed | 292 plain assertion mismatches over 150 sites; 380 others, largest `IndexError` in three `bvbrc_minhash` custody files (103, unchanged from before), `bvbrc_invalid_snapshot` (27 + 42) |

Same root cause as cause 2 but a different message, so outside this cluster: 13 `build_tools(...)` calls without
`run_directory` in `tests/test_application_execution_binding.py:312,318`, `tests/test_ncbi_contact_configuration.py:53,64,70,122`,
`tests/test_live_a106_binding.py:85,129`, `tests/test_ordinary_execution_statistics.py:100`,
`tests/test_actual_tool_retriever_runtime.py:53`, `tests/run_semantic_retrieval_samples.py:50`,
`root/tests/live_a106_workflow.py:134`, `root/tests/live_a105_database_workflow.py:117`.

Same rewrite as cause 9 in four more helpers (not edited, not reached by this cluster's messages):
`root/tests/blast_producer_identity_checks.py` (`OLD`), `root/tests/fluorescence_module_identity_checks.py`
(`OLD_DRIVER`, `OLD_WORKER`), `root/tests/fluorescence_original_intent.py` (`WORKER_MODULE`),
`root/tests/test_lumpy_saved_driver_identity.py` (`LEGACY`).

## Reaches outside services

- `tests/test_sequence_support_739.py`: never edited and never run by me.
- `root/tests/test_addgene_selected_process_path.py`: not run. Line 118 builds
  `ToolRegistry(store, clients=PublicClients(ncbi_email=None))` for Addgene acquisition and `urlopen` is patched
  only inside some tests (lines 256, 402). I could not show it safe.
- Runs 0001 to 0087 (82 files, including the two runs I stopped) started before the rule and used the real home with no proxy. Afterwards I checked
  them by reading: the files that build a real-client registry without a socket guard execute only local tools
  (`sequence.*`, `material.*`, `source.read`, `state.query`, `reads.map`, `library.*`, `genes.predict`); the four
  `public.*` uses go through stub clients or are rejected by schema before any call. A search of those run logs for
  network errors found only synthetic `HTTP Error 429/302: native failure` raised by test fakes. This is inspection,
  not proof.
- Cause 2's fix makes 291 call sites build a real `PublicClients`, as the product does. A test that executes a
  `public.*` tool without a stub was previously stopped by the constructor error and would now reach the network.
  The suite runner should keep the blocked-proxy prefix.
- Runs 0088 onwards used the empty home and blocked proxy. The home directory is
  `runs/claude_r2_r2a_homes/NNNN`, a sibling of the run directory, because the launcher refuses a run directory
  that already exists. No result changed because of the empty home or proxy; the two environment-variable failures
  above are gated regardless.

## Owner questions

1. Enrichr: should fresh construction accept `timeout`, or should the Enrichr configuration stop requiring it?
   Today no fresh Enrichr service can be built (87 cases here, 136 in the rerun files).
2. a101: should a101 get its own `execution_service_setup` like the six other axes, or should these a101 tests
   drive the root `Workflow`? About 200 cases.
3. Protein structure: are retained plans with `wall_seconds: null` still admissible (schema change), or are the
   packet-392 fixtures to be regenerated? 74 cases. Scientific.
4. Protein structure launch policy: the root library copy says 5 GiB, the a102 and other axis copies still say
   20 GiB. I aligned the top-level test with the root copy it imports; confirm that is the intended copy.
5. Top-level duplicates: 26 modules exist both at top level and in root and root product code imports none of the
   top-level ones. Which copy should tests exercise?

## Verified by running versus inferred

- Run: every before/after number; causes 1, 2, 3a, 4, 6, 8, 9 (fix applied and rerun); cause 3b (both failure
  messages observed); cause 7 (diagnostic printed `Additional properties are not allowed ('wall_seconds' was
  unexpected)`); the handle-check environment mismatch (diagnostic printed the two extra keys).
- Read only: cause 5's a101 design gap (the two failure points were observed in runs; the missing module is from
  listing the axis directories); the remaining-failure classes in the table above (message and deepest frame only).
