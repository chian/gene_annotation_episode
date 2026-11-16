# fpt — top-level package, `tests/`, `examples/`, `tools/`: code that fingerprints the codebase removed (16 November 2026)

Area: `gene_annotation_episode/*.py` and its non-`episodic_workflow` data (`*.json`, `vendor/`, `local_example/`),
`tests/`, `examples/`, `tools/` (only where a tool reads a removed field). Brief `FP_BRIEF.md`, shapes `fp_recipe.md`.
"Before" = `e458da27c` (Checkpoint 15). Checkpoints 16–20 and two later commits were made underneath the task and
contain part of this work; diff against `e458da27c`. Slot `fpt`, one launcher command at a time, no sub-agents, no git
writes.

Change against `e458da27c` in the area: 80 files (77 `.py`, 2 schema JSON, 1 vendor JSON), all edits mine. One file
outside the named area: the repository-root `method_loop/durable.py` (vendored package used by the top-level package
and by `tests/`): `validate_commission` no longer requires `runtime_binding.implementation_sha256` (2 lines, the
same edit the shared-root copy got). Without it handoff row 436 (fixture `commission_spec`) could not be applied.
Process note: two of the first text edits (`bvbrc_appservice_adapters.py`, `bvbrc_appservice_preparation.py`) were
made with the host `python3` as a text-replacement tool, outside the launcher; every later edit used perl/asserted
substitutions. No Python test or product code ran outside the launcher.

## Removed, by class
### Class 1 — runtime-computed binding identity
- Runtime binding digest: `method_loop/durable.validate_commission` (above); test fixtures that produced/compared it:
  `tests/test_durable_episode.commission_spec`, `tests/durable_fixture.open_commission`,
  `tests/detached_workflow_fixture` and `tests/scientific_process_worker_fixture` (`implementation_sha256()` helpers
  that hashed their own source deleted, `identity_conflict` clause dropped), `test_application_execution_binding`
  (`custom_binding`, the `known_factory` double, monkeypatch of the deleted `reconstruction.implementation_sha256`),
  `test_episode_admission`, `test_episode_commissions`, `test_bvbrc_appservice_compact_custody`.
- `ordinary_execution.py` timing-class descriptors: the `files` digests of `sequence_ops`, `sequence_worker`,
  `spreadsheet_tools`, `spreadsheet_worker` removed (recipe 10); `native_pairwise_aligner_sha256` (Biopython's
  compiled extension, external, observed) stays.
### Class 2 — worker/job implementation manifests and pins
- BV-BRC adapter pin (recipe 6, top-level half; rows 426, 427, 475): `bvbrc_appservice_adapters.bind_adapters` binds
  the module (no digest comparison, no tuple); `bvbrc_appservice_preparation.result_catalog` uses the module;
  `bvbrc_appservice_contracts` `publication_adapter_binding_conflict` relation check deleted;
  `bvbrc_appservice_schemas.json` and `bvbrc_fastqutils_schemas.json`: `scientific_adapters[]` rows are
  `{adapter_id, adapter_version}`, `PublicationInputs` has no `adapter_implementation_sha256` (property + required);
  `bvbrc_fastqutils_returns`: `original_adapter_pin_required` check gone, `_owner` compares `{adapter_id,
  adapter_version}` (code `original_adapter_pin_conflict` stays). `bvbrc_fastqutils_schemas.json` is now identical
  (canonical JSON) to the shared-root copy. 12 tests edited (configuration rows / publication inputs without digest).
- Acquisition transport (recipe 8): observer policy `adapter_sha256` + the observer's re-hash of the capture adapter
  (`response_capture_adapter_changed`), and `script_sha256` (4 dicts) removed from `acquisition.py`.
- `hpc_scientific_commission.commission` (rows 451, 476): parameters `worker_sha256`, `implementation_sha256` and the
  two acceptance predicates gone; `execution_profile.implementation` is the `version` argument.
  `tests/test_scientific_hpc_environment.py`: commission call and the component-worker request (row 491: no
  `code_manifest`, `code_manifest_sha256`, `source_snapshot_sha256`).
- Driver runtime (13a, rows 447–449, 464, 481, 483): `native_atac_differential_contracts._DRIVER` is
  `{python_executable, python_version, module_root, implementation_files:[{module}], dependencies:[{…, files:[{path}]}]}`;
  `native_atac_differential_software`: `_copy_exact` deleted, `_copy_source` copies and accepts an existing copy only
  when its bytes equal the source and it is read-only (owner staging rule), `_dependency_bindings` rows `{path}`,
  `freeze_driver_runtime` without `python_sha256`; `native_atac_differential_driver.verify_driver_runtime`:
  interpreter/module/dependency-file digests gone, module file existence + loaded path + versions + listed
  site-packages kept. MACS2 `_MACS` runtime pins (external) unchanged.
- Chromatin software record (13b, rows 465, 488): `chromatin_interaction_contracts` schema (`SoftwareBinding` without
  `python_sha256`, `ImplementationFile {module}`, `DependencyFile {path}`), `native_chromatin_interaction_driver`
  checks file existence instead of hashing. HiC native runtime (external) unchanged.
- ESM (rows 474, 477): `esm_gene_embedding_tools.esm_worker_implementation_files` gives `{path}` rows for driver
  modules/dependency files plus the `{path, sha256}` checkpoint pins (model data); `_worker_control` compares
  `python` with `{path}`.
- Worker-selection record `ordinary_molecular_execution_v1` (rows 478, 487): `molecular_measurement_tools` writes
  `python {path}` and `implementation_files [{path}]` for repository-worker operations and the ESM driver;
  `verify_unstarted_software` checks existence for `{path}` rows and keeps the digest check only for `{path,
  sha256}` rows (the operator-configured protease deployment pins and the ESM checkpoint data pins); any other row
  shape is refused. New code for a missing repository file: `molecular_tool_original_software_unavailable_before_dispatch`.
  Reader `macs2_peak_tools` accepts the path-only record (merged from the shared root).
- Calculator control records (`vcf_result_tools`, `reference_edit_outcome_tools`): `implementation` (sha256+size of
  their own two files), `_CONTROL_KEYS` member and `implementation_conflict` check gone (merged from shared root).
- ITC (row 486): `itc_binding_fit._file` returns `{path}`; `itc_binding_contracts` closes files to `('path',)`
  (now byte-identical to a105's copies).
- Protease deployment manifest (row 490): `molecular_sequence_native._manifest` refuses a manifest row under
  `<import_root>/gene_annotation_episode/` (`molecular_sequence_repository_file_in_manifest`); `_imports` skips loaded
  repository modules; `execution_receipt.helper_file` is `{path}` (both the v1/v2 and v3 paths — the helper is a
  repository file that the manifest may no longer list); `molecular_measurement_tools` protease closure check
  requires each worker source to exist in exactly one import root (no manifest lookup).
### Class 3 — pinned source constants (`SOURCE_[A-Z_]*SHA256` 38/14 → 0/0)
Three-way merge of fpr's shared-root change (`9fc7d3e54` → `HEAD`) into the 17 top-level copies (16 clean, 1 conflict
in the chromatin `_DEFINITIONS` line resolved by hand keeping the top-level `driver_module` const), every merged diff
read: `glycosylation_measurements` (`SOURCE_SHA256`, per-operation `callable_sha256`, `source_profile` members),
`protein_disorder_measurements` + `_result_contracts` (`SOURCE_SHA256`, `CALLABLE_SHA256`), `circular_dichroism_
measurements` (`source_function_sha256`), `protease_kinetics_measurements` (`SOURCE_FILE_SHA256`,
`SOURCE_FUNCTION_SHA256`, `native_source_conflict` module check, `source_identity.sha256`), `protease_kinetics_tools`,
`molecular_sequence_native` (four constants, per-operation callable digests, `inspect.getsource` digest,
`_deployment(source_sha256=)`, `original_source_pin_required`), readers `orf_measurements`,
`primer_placement_measurements`; `molecular_sequence_ordinary._deployment` and `molecular_measurement_tools` callers.
`vendor/SOURCE.nano-graphrag.json`: `source_sha256` and `adapter_template.sha256` (recipe 5).
### Class 4 — tests, fixtures, tools
- Deleted/renamed: 8 parametrised cases deleted, 1 converted, 3 renamed (`fpt_deleted_tests.tsv`).
- Fixtures converted to the current record form (no test deleted for carrying a field): ATAC (`test_atac_differential_
  operands.make_assignment` — row 483, `test_native_atac_differential_contracts.fake_software`, `test_macs2_peak_
  execution.fake_software`, `test_native_driver_runtime`), chromatin/genomic-overlap operands, ESM deployment,
  fluorescence `pin` (row 489), FBA (`_680`, `_687`, `_697`: no `source_function_sha256`, software files `{path}`,
  model input keeps its data pin), RNA (`worker_source_sha256` out), protease (`source_identity` without sha256; the
  deployment module pin is an arbitrary configured digest), molecular native/ordinary, glyco/disorder/numerical
  unused constant imports, `test_fluorescence_worker_preparation` (patch of deleted `_verify_pins`), intervention
  tests (a106 adapters no longer have `implementation_sha256`).
- `tests/audit_a106_workflow.py`: the run source-snapshot pin check (`source-pins.json`, `--verify-snapshot`,
  `source_snapshot_files/_mismatches`) removed (the launcher no longer writes the pins).
  `tests/run_semantic_retrieval_samples.py`: `script_sha256` of itself removed (the output-file manifest is data).
- `tools/a104_audit_case.py`: no longer reads the removed `worker_sha256` of a104 HPC results.

## Kept, with reason (file:line)
- `run_statistics.py:65,81-82`, `ordinary_execution.py:60,99`, `execution_memory.py:219` `ExecutionClass.
  implementation_sha256`: timing-class key; now versions + Biopython's compiled aligner (external, observed).
- `native_atac_differential_contracts.py:125` `_MACS`, `native_atac_differential_driver.py:204`,
  `native_atac_differential_software.py:153`: MACS2 runtime pins (external, operator-configured).
- `molecular_measurement_tools.py:267,305` protease `python {path, sha256}` and `implementation_files` = configured
  Biomni deployment runtime and manifest (external; row 490 "unchanged"); `molecular_sequence_tools.py:187-252`
  `source_sha256` = configured deployment module digest (configuration presentation).
- `restriction_mapping_native.py:141` `dictionary_file`/`native_source_file`: Biopython files observed at run time,
  no constant.
- `case_execution.py:296-330` `source_sha256` of a caller-supplied policy file snapshotted into the run directory and
  compared on resume within the same run (run-input custody, not repository state). Listed here, not changed.
- `document_tools.py:37`, `local_example/*` executable digests (external), `hpc_campaign`/`hpc_allocation`
  `manifest_sha256` (staged-file transfer records), `schema_information_text.schema_fingerprint` (data schema).
- `vendor/SOURCE.infrastructure.json` and repository-root `method_loop/SOURCE.json`, `LOCAL_PATCHES.json`: left for the
  tree-wide pass, as instructed (the shared-root copies were cleaned in commit `02bf9c8e6`, the top-level ones not).
- Not converted, tests only: `tests/test_actual_tool_retriever_runtime.py:69` still builds selection v2 and the old
  retrieval output; every test of the file stops first on the missing `gene_annotation_episode.api_uniprot`, so a
  conversion cannot be checked.

## Left for decision
None from the fingerprint removal. One question of placement: `molecular_measurement_tools.verify_unstarted_software`
now distinguishes two closed row shapes (`{path}` repository files → existence; `{path, sha256}` configured
external/data pins → digest). If the owner wants the protease/ESM pins verified elsewhere, the second branch goes.

## Handoff rows (fingerprint agents, rows 426–491, addressed to fp-top, fp-top2, rec5, ptests or ptop)
| row | from → to | status |
|---|---|---|
| 426, 427 | fp1 → rec5 | applied (3 tool-info tests, acquisition records) |
| 428 | fp1 → rec5 | applied where a top-level test carried a listed field (BV-BRC, runtime binding); no other a101-driven top-level test failed |
| 429 | fp1 → ptop | not applicable: no top-level FBA producer exists (FBA lives in `root/library`, done by fpr); top-level FBA tests converted |
| 430 | fp1 → ptop | not applicable for product (RNA worker only in `root/library`); RNA tests converted |
| 431 | fp1 → rec5,ptop | not applicable: nothing in the area writes a BLAST database plan/configuration (`producer_manifest` only as a vocabulary value in one test) |
| 436 | fp1 → rec5 | applied (`commission_spec`, plus `method_loop/durable.py`); a101 test passes (26 passed); handoff to fp1 to delete its projection |
| 437, 438, 453, 454 | fp2/fp3 → fp-top | done by fpr (row 482); files outside this area |
| 439–441, 455, 456, 462, 471 | notices | checked by the gate: no top-level test regressed for those reasons |
| 442 | fp2 → fp-top | not applicable here: fixtures live in the a102 tree; the only reader `tests/test_protein_structure_selection.py` passes (2/2); handoff to fp-a102 |
| 443–450, 457, 458, 463, 467, 468 (shared part), 472, 473 | → fp-top | shared-root files: done by fpr passes 1–2; no top-level copy exists for protein structure, RNA, genomic overlap, NMF, fluorescence, FBA |
| 451, 476 | fp2/fpr → fp-top/2 | applied |
| 452, 459, 469, 468 (configuration) | → fp-top | not applicable: no operator resource configuration is in the repository (`examples/*.json` carry none of these records) |
| 460 | fp3 notice | kept (`_P3_SOURCE_SHA256` is shared root, not here) |
| 464, 465, 481, 483, 488 | fp4/fpr → fp-top/2 | applied for the top-level ATAC and chromatin copies and the ATAC fixture |
| 466 | fp4 → fp-top | applied |
| 470 | fp5 → fp-top,fpr | test half applied (`tests/test_native_fluorescence_contracts.pin`); shared record done by fpr |
| 474, 477 | fpf/fpr → fp-top/2 | applied |
| 475 | fpr → fp-top2 | applied |
| 478, 487 | fpr → fp-top2 | applied (protease deployment exception kept, as the row says) |
| 479 | fpr → fp-a105 | not mine |
| 480 | fpr notice | applied: every listed test that constructs a removed field was converted |
| 482, 484 | fpr notices | not mine |
| 485 | fp6 → fp-top | applied |
| 486 | fp6 → fp-top,fpr | top-level half applied (shared-root half: commit `8f48b6c80`) |
| 489 | fpr → fp-top2 | applied |
| 490 | fp6 → fp-top | applied (top-level producer; no operator configuration file in the repository) |
| 491 | fp8 → fp-top | applied |
Written (4 rows at the end of `handoffs.tsv`): fpr (shared-root `_copy_source` refuses equal existing copies),
fp1 (projection in `a101/tests/test_homology_progress.py` now a no-op), fp-a102 (protein-structure fixtures),
fp-a106 (dead `source-pins.json` line in `test_a106_workflow_audit.py`).

## Gate (measured)
1. Syntax: 857 `.py` files (`gene_annotation_episode/*.py`, `local_example`, `tests/`, `examples/`, `tools/`,
   `method_loop/`), 0 errors. Bound-name check over the 77 changed `.py` files against their `e458da27c` versions:
   no undefined name; unused imports only those that existed before minus the ones removed (`runs/claude_fpt_037`).
   Import check over all 290 top-level product modules (`gene_annotation_episode.*` outside `episodic_workflow`,
   without `__main__`, plus `local_example.*` and repository-root `method_loop.*`): `{}` (`runs/claude_fpt_038`).
2. Tests: all 510 files of `tests/` (without `test_bvbrc_proteome_host_integration.py`), one per launcher run,
   isolated form (`runs/claude_fpt_101..610`, logs `runs/claude_fpt_homes/NNN.log`, 10:59–11:42, 43 min wall).
   0 collection errors. Expected (written before, `<scratchpad>/fpt/EXPECTED.txt`): 510 files, ~15,882 tests,
   ~15,230 passed, 2,000–2,600 test seconds, 40–50 min.

   | | files | tests | passed | failed | errors | skipped | test s |
   |---|---|---|---|---|---|---|---|
   | before (rec5 final+fix1+fix2) | 510 | 15,889 | 15,233 | 497 | 158 | 1 | 2,586 |
   | gate as run | 510 | 15,868 | 15,165 | 544 | 158 | 1 | 2,074 |
   | after the post-gate fixes (7 files re-run, `claude_fpt_021..028`) | 510 | 15,868 | 15,231 | 478 | 158 | 1 | 2,080 |

   Test count: −8 deleted cases +1 converted; −14 because the junit of two files (`test_phylogeny_formats.py`,
   `test_chromatin_interaction_contracts.py`) no longer lists subtests as testcases (all 14 pass). Passed:
   15,233 − 7 deleted passing cases + 19 newly passing (`test_scientific_process_provenance` 14,
   `test_pdf_text_ranges` 4, `test_tool_attribution` 1) − 14 subtests = 15,231.
   Passed before, failed in the gate (66), all fixed or transient:
   - `test_decision_history.py` (11): the shared root's `decision_history` now joins the completion-ledger tables
     unconditionally (fpr); the fixture opened a Journal without `CompletionLedger` → fixture builds it, 33/33.
   - `test_macs2_peak_execution.py` (41): fixture appended a driver module row with `sha256` (my 13a change) →
     fixed, 58 passed / 9 failed = before.
   - `test_intervention_analysis.py` (2), `test_intervention_execution_contract.py` (2),
     `test_intervention_native_quantity_kind.py` (9): a106 adapters lost `implementation_sha256()` during the gate
     (other agent) → digests dropped from the tests, 14/2/18 passed = before.
   - `test_native_adapter_limits.py` (1): `local_job_boundary_unavailable` once; re-run 9/9 (transient).
   Pre-existing failures unchanged: the 84 failing files of `rec5.md` minus those now clean
   (`test_scientific_process_provenance`, `test_tool_attribution`); per-file table `fpt_gate_results.tsv`.
3. Shared-root / arm files that waited on this area (after the last product edit):
   `root/tests/test_atac_differential_execution_integration.py` 10 passed, 5 failed (fpr baseline: 10/5);
   `root/tests/test_fluorescence_episode_routing.py` 22 passed, 15 failed (fpr pass 1: 22/15);
   `root/tests/test_bvbrc_proteome_directional_returns.py` 1 passed, 7 failed (`ExecutionEpisodes.facts`,
   pre-existing), 456 s (fpr baseline 1/7, 478 s); `a101/tests/test_homology_progress.py` 26 passed;
   `a106/tests/test_a106_workflow_audit.py` 2 passed; `tests/test_live_a106_binding.py` 8 passed.
4. Site counts (lines/files, area, `e458da27c` → now): `implementation_sha256` 54/33 → 10/7 (ExecutionClass and its
   tests); `SOURCE_[A-Z_]*SHA256` 38/14 → 0; `CALLABLE_SHA256` 4/3 → 0; `callable_sha256` 5/3 → 0;
   `adapter_implementation_sha256` 13/10 → 0; `adapter_sha256` 4/1 → 0; `script_sha256` 5/2 → 0;
   `python_sha256` 26/17 → 10/10 (MACS2 runtime, RNA observed interpreter in tests); `worker_source_sha256` 2/2 → 0;
   `source_function_sha256` 7/5 → 0; `worker_sha256` 3/2 → 0; `code_manifest` 3/2 → 0; `_verify_pins` 1/1 → 0;
   `module_sha256` 5/5 → 2/2 (`rna_module_sha256`, external); `_copy_exact` 3/2 → 1/1 (a test name);
   `manifest_sha256` 5/4 → 3/2 (HPC staged files); `source_sha256` 56/28 → 46/21 (data records);
   `read_bytes()).hexdigest()` 53 → 36 (data, external files); `fingerprint` 5/4 → 5/4 (schema/data, docs).
   0 before and after: `implementation_record`, `_binding_source_bytes`, `SOURCE_PATHS`, `_verify_implementation`,
   `template_sha256`.

## The 10 test-side / unfinished files of `rec5.md`
| file | now | action |
|---|---|---|
| `test_scientific_process_provenance.py` | 35/35 | converted to `scientific_process_selection_v3` with a one-tool `resolve_tool_info` stand-in (a real tool library cannot be frozen: `tool_information.workflow_execution_catalogs` imports the missing `api_uniprot`) |
| `test_tool_attribution.py` | 16/16 | patch target corrected to `root.credit.received_axis_task_credit` (the name `scoring` reaches through `credit.project_collection_credit`) |
| `test_pdf_text_ranges.py` | 4 passed, 3 failed | patch target corrected to `root.tool_documents.pdf_native`; the 3 remaining cases: `source.locate` on the extracted text returns `invalid` — cause not established |
| `test_durable_episode.py` | 19/1 | not converted: the fixture factory needs a `receiver_snapshot` reader (`method_loop/durable.py:667-677`); its semantics for this fixture were not established |
| `test_detached_workflow.py` | 0/4 | not established: the parent run ends `source_failed` with 0 actions; `runtime_source_failures` records `selected_operation_failed` / `AssertionError` (scripted provider), traceback not retained |
| `test_episode_completion.py` (1), `test_native_infernal_execution.py`, `test_intervention_received_score_operands.py`, `test_native_reaction_render_129.py`, `test_protein_phylogeny_native_and_retained.py` | unchanged | not worked on (causes as in `rec5.md`; no scientific expectation edited) |
