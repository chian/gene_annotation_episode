# fpr — shared root: code that fingerprints the codebase removed (16 November 2026)

Area: `gene_annotation_episode/episodic_workflow/root/` outside `a101`..`a110` (`R/` below): `R/*.py`, `R/library/`,
`R/method_loop/`, `R/vendor/`, the non-arm homes, `R/tests/`. Brief: `FP_BRIEF.md`; shapes: `fp_recipe.md` (section 19
added by this task). Comparison base: commit `9fc7d3e54` (checkpoints 10 and 11 were committed underneath the task and
contain part of this work; diff against `9fc7d3e54`, not `HEAD`). Slot `fpr`, one launcher command at a time, no
sub-agents, no git writes. The task was interrupted once by a usage limit before any edit; the baseline test run
(`runs/claude_fpr_001..086`) was taken before the first edit and is the "before" of every comparison below.

## Outcome
Every inventory row of the area (`h5_self_hashing.tsv`, 298 rows) is handled, plus recipe 12 (producer manifest),
13a (driver runtime), 13b (protein-structure software record, terminal reader), the code manifest of the staged
component worker (14 shape), the whole-tree source streams of the two saved binding catalogues, and two calculator
control records. Change against `9fc7d3e54`: 141 files (137 modified, 4 deleted), +340 −9,157 lines (the 4 deleted
files are the source-roster modules `definition_inputs.py`, 8,700 lines); `R/tests` 11 files, +18 −36.

NOT finished (decided REMOVE; listed as handoff rows, see "Not done"): the worker-intent source/interpreter pins of the
six native preparation families (same open item as fp4), and the top-level-produced worker-selection record.

## Removed, by class (lines/files in the area, `9fc7d3e54` → now; full table `<scratchpad>/fpr/counts_after.tsv`)
### Class 1 — runtime-computed binding identity (`implementation_sha256` 153/82 → 2/2, the external-executable `ExecutionClass` field)
- 24 `*/binding_identity.py` (roster of up to 42 files hashed per `as_record()`), `scientific_process/binding_record.py`
  with its roster module `scientific_process/definition_inputs.py` (deleted), the literature aggregate record in three
  copies (`published_evidence_assessment/record_algorithm.py`, `aggregate_records.py`; roster modules
  `definition_inputs.py` ×3 deleted), `library/resource_binding_records.implementation_fingerprint` with four rosters,
  `library/execution_progress.as_record`.
- Consumers: `resource_binding_catalogue.saved_family`, `scientific_process/saved_identity.restore_closed_process`
  (compares records directly; `scientific_closed_implementation_identity_invalid` gone),
  `saved_private_binding_catalogue._rows` and both catalogue source records (whole-tree `.py` stream:
  `sources`, `implementation_sha256`, `source_identity_kind`), `commissioned_reopening.implementation_sha256()`
  with `make_runtime_binding`/`open_commission`, `application_execution_binding` (merged from a102),
  `method_loop/durable.validate_commission` (merged), `literature_text_values._TRACKING`,
  `library/native_phmmer_preparation` `parser_implementation_sha256` (recipe 9).
### Class 2 — worker/job implementation manifests
- Native BLAST database result workers and publications (recipe 7; merged from a102, conflicts all "take a102's
  removal"): `implementation_identity` 21/6 → 1/1 (a test fixture key, see Kept), `_verify_implementation` 6/2 → 0,
  `implementation_manifest` 26/4 → 0; results modules no longer collect `implementation-receipt.json`.
- Producer manifest of the native BLAST database drivers (recipe 12; merged from a102):
  `producer_verification` 16/3 → 0, `package_files` 8/3 → 0, `validate_retained_*_bundle` and the
  `PRODUCER_MANIFEST*`/retained-profile code gone from both contracts modules, `native_database_terminal_custody`
  producer is `{module_root}`. Remaining `producer_manifest` 40/17 are BV-BRC's provider data role and the
  `attempt_output_version` vocabulary value (as a101/a102).
- BV-BRC adapter pin (recipe 6, shared-root side): `implementation_sha256()` + `_DEPENDENCIES`/`_ROOT_DEPENDENCIES`/
  `_implementation_path` out of 17 adapter modules and `bvbrc_phylogeny_bundle_projection`; publication inputs,
  `_validate_inputs`, `_grade`, `read`, `result_identity` (merged from a102, conflict resolved keeping the shared root's
  proteome-v2 `validate_result_selector` call); 6 `*_returns.py`; `bvbrc_comparative_systems_host_inputs`
  (`adapter_pin_conflict` → `adapter_unbound`); `analysis_contract.py` ×3; `library/bvbrc_fastqutils_schemas.json`
  (a101's after-version). `adapter_implementation_sha256` 25/13 → 0/0.
- Driver runtime (13a): `library/native_atac_differential_contracts._DRIVER`, `native_atac_differential_software`
  (`_copy_source`, `_dependency_bindings` `{path}`, `freeze_driver_runtime` without `python_sha256`),
  `native_driver_runtime_verification` (no file_identity comparisons), `native_hmmer_preparation_result_publication`
  (merged; `result_worker_original_software_changed` / `_source_size_conflict` gone), `native_lumpy_execution`
  (module-name set), ESM worker selection (`esm_gene_embedding_tools`).
- Software records (13b): `library/native_protein_structure_{contracts,job_schema,worker,driver}.py`,
  `terminal_scientific_evidence._identified_file_values` (merged); RNA `worker_source_sha256` (worker, job schema,
  two contracts, `_RECOGNIZED_SOFTWARE`) 6/5 → 0.
- Component worker code manifest (14 shape): `code_manifest` 9/2 → 0, `worker_sha256` 4/2 → 0.
- Calculator control records: `vcf_result_tools`, `reference_edit_outcome_tools` (`implementation`,
  `implementation_conflict`).
### Class 3 — pinned source constants (`SOURCE_.*SHA256` 32/13 → 2/1)
`numerical.SOURCE_SHA256` with `run_execution`/`saved_binding_reconstruction` `template_sha256` and two digests in
`vendor/SOURCE.nano-graphrag.json` (recipe 5); flux balance `SOURCE_FUNCTION_SHA256`/`source_function_sha256`
(constant, two producers, schema ×2, reader, driver manifest; `fba_source_function_mismatch` gone) 9/8 → 0; declared
Biomni source digests in CD, protease kinetics (+ `native_source_conflict` module check and `source_identity.sha256`),
glycosylation, protein disorder (+ const schema, received-values projection), fluorescence `PROFILE_SOURCES`;
`molecular_sequence_native` (four constants, per-operation callable digests, `inspect.getsource` digest,
`original_source_pin_required`), with readers `orf_measurements`, `primer_placement_measurements`.
`callable_sha256` 6/4 → 0, `source_function_sha256`/`function_sha256`/`source_file_sha256` → 0.
### Class 4 — tests and fixtures
0 tests deleted, 1 renamed (`fpr_deleted_tests.tsv`). Edited: the four shared helpers of task item 2, two BV-BRC
tests (adapter rows without digest; `scientific_adapters[key] is adapter`), two lumpy tests and one ATAC test
(13a driver record), `model_transport_support.requested_descriptor` (runtime binding without digest), the orphan
schema copy `tests/fixtures/bvbrc/appservice_execution_contract/CONTRACT_SCHEMA.json` (read by nothing; two schema
entries dropped).

## Task items
1. Handoff rows applied (shared root / `R/tests`): fp1 row to `proot,prootlib` (producer manifest); fp2/fp3 rows 437
   and 453 (digest assert), 438 and 454 (completion ledger), 443-449 / 457-458 shared-root producers of 13a/13b
   (applied except genomic overlap, see Not done), 450 caller side of `hpc_scientific_commission`; fp4 row 463 (FBA).
   Notice rows 439-442, 455-456, 462 checked: no shared test double drives an annotation-root source without the
   boundary; the only hand-saved decision row in `R/tests` (`test_annotation_task_boundaries.py`) passes before and
   after. Left for `fp-top2` (top-level package / `tests/`): fp1 rows 426-432, 436; fp2 444/448/449 top-level halves,
   450 (`gene_annotation_episode/hpc_scientific_commission.py`), 451, 452; fp3 459; fp4 464, 465, 466.
2. Shared test helpers fixed. The 12 a102 test files that failed on them (fp2.md) now pass in full: 230 passed,
   0 failed (`runs/claude_fpr_201..212`).
3. a102 suspects carried over: `decision_history._tables` deleted, joins unconditional; `workflow_values` pending-work
   branch removed (159 directories save a decision, the same 159 add `pending_work`: set comparison equal);
   `composition_information.restricted_root` already read the attribute strictly in the shared root (nothing to do).

## Kept, with reason
- `execution_recording.py:124` `ExecutionClass(implementation_sha256=configuration['executable']['sha256'])`: external
  executable digest (as a101/a102); `tests/test_root_native_receipt_admission.py:66` constructs that class.
- `library/bvbrc_genome_alignment_inputs.py:36,659` `_P3_SOURCE_SHA256`: same reasoning as fp3 (selects the inferred
  progressiveMauve recipe used for grading; analogous to the alimask decision).
- `library/native_atac_differential_contracts._MACS`, `_copy_exact` (lumpy native files), molecular-sequence
  deployment file pins and software manifests, BLAST/HMMER `expected_sha256`: operator-configured pins of external
  tools/executables, not hard-coded and not this repository's source (same as a101/a102 for executables).
- RNA `python_sha256`, `rna_module_sha256`, `rna_extension_sha256`: observed at run time (as fp1).
- `tests/test_root_registry_lineage.py:26` key `'implementation_identity'`: a fixture descriptor field name, no digest.
- `tests/fixtures/tool_parser_custody/uniprot/P0AAW1.transport.json` `script_sha256`: retained captured transport.
- `vendor/SOURCE.*.json`, `method_loop/SOURCE.json`: left for the tree-wide pass (recipe-5 fields removed).
- `hpc_campaign.build_plan`, `esm_gene_embedding_worker:196`, `native_hmmer_local:42`, `rna_evidence:55`,
  `method_loop/durable.py:572`: `Path(__file__)` locates or stages files, nothing hashed.
- `literature_controlled_response_inputs` `implementation_dependencies`: version strings, no digest.

## Not done (decided REMOVE; handoff rows written)
- Worker-intent pins of the native preparation families (`source_pins`, `_copy_exact`, `_verify_pins`,
  `_verify_snapshot`, copied-interpreter `python_sha256`) in `library/native_{atac_differential,chromatin_interaction,
  genomic_overlap,expression_nmf,fluorescence,flux_balance}_preparation.py`, `native_source_snapshot.py`,
  receipt validators, and the genomic-overlap / chromatin software records (fp3 rows 457-458 point to a103
  after-shapes; a three-way merge into `R/library` conflicts in 10 hunks). `source_pins` 55/9 unchanged,
  `python_sha256` 30/25 → 15/14.
- Worker-selection record `ordinary_molecular_execution_v1` (top-level producer `molecular_measurement_tools.py`
  hashes repository worker sources and the interpreter; shared-root readers only check its field set): needs one step
  across the top-level package and `R/library`.

## Gate (measured)
1. Syntax: 6,403 `.py` files of the area parsed, 0 syntax errors; symtable check of the 131 changed `.py` files: 0
   undefined global names; imports my edits left unused removed (`runs/claude_fpr_101`). Import check over all 6,267
   product modules of the area (5 launcher runs, `runs/claude_fpr_102_0..4`): `{}` each.
2. Tests, every file of `R/tests` (85) plus `R/execution_monitoring/tests` (1), one file per launcher run, isolated
   form, after the last product edit (`runs/claude_fpr_301..386`, logs `runs/claude_fpr_homes/NNN.log`, table
   `fpr_gate_results.tsv`). 0 collection errors.

   | | files | tests | passed | failed | errors | skipped | test seconds |
   |---|---|---|---|---|---|---|---|
   | before (`runs/claude_fpr_001..086`, taken before the first edit) | 86 | 1,637 | 1,386 | 166 | 84 | 1 | 609 |
   | expected (written before, `<scratchpad>/fpr/gate_expected.txt`) | 86 | 1,637 | 1,385 | | | 1 | about 610 |
   | measured | 86 | 1,637 | 1,382 | 155 | 99 | 1 | 131 |

   (rec5's last table: 86 files, 1,383 passed, 162 failed, 91 errors.) The drop in test seconds is
   `test_bvbrc_proteome_directional_returns.py` (478 s → 2 s, it now errors in setup) — see below.
   Passed before, fail now (4), none caused by a shared-root defect; each needs the top-level half of a mechanism
   whose shared-root half was removed here:
   - `test_bvbrc_proteome_directional_returns.py::test_owner_version_remains_required` (renamed from
     `..._and_original_pin_remain_required`): the top-level `bind_adapters` / `bvbrc_appservice_schemas.json` still
     require `implementation_sha256` in configuration rows (`contract_shape_invalid`). Handoff to fp-top2.
     MEASURED: with the top-level half emulated (verification-only plugin
     `<scratchpad>/fpr/plugin/fpr_toplevel_adapter_plugin.py`: `bind_adapters` binds the module, the two schema
     entries and the relation check dropped, `bvbrc_appservice_preparation.result_catalog` uses the module; run
     `claude_fpr_404`) the file gives its baseline result: 1 passed (this test), the same 7 failed with the same
     pre-existing cause (`ExecutionEpisodes` has no attribute `facts`), 478 s.
   - `test_atac_differential_execution_integration.py::test_only_exact_resource_mode_and_software_are_advertised`,
     `::test_private_atac_artifact_denial_precedes_store_fallback`,
     `::test_version_checks_accept_only_original_received_selected_bams`: the top-level fixture
     `tests/test_atac_differential_operands.make_assignment` still writes the pinned driver record, refused by the
     13a schema. With that fixture change emulated (verification-only plugin, run `claude_fpr_402`) the file gives
     exactly its baseline result: 10 passed, the same 5 failed. Handoff to fp-top2.
   Pre-existing failures unchanged: the 30 files with failures before (rows of `fpr_gate_results.tsv`).
3. Site counts before → after for every grep of the brief: see the Removed section and
   `<scratchpad>/fpr/counts_after.tsv`; tokens with 0 sites before and after: `implementation_record`,
   `_binding_source_bytes`, `SOURCE_PATHS`, `adapter_sha256`, `resource_implementation_bytes`, `_context_source_key`.
   `fingerprint` 87/25 → 75/19, `read_bytes()).hexdigest()` 48/44 → 14/13, `manifest_sha256` 84/24 → 38/22,
   `source_sha256` 163/62 → 150/53 (remaining: data records, request/schema digests, sequence files).

## Handoffs
Written: 10 rows `fpr → fp-top2 / fp-a105 / fpr2 / arms` (end of `handoffs.tsv`): top-level BV-BRC adapter binding,
schemas, contract relation check and `bvbrc_appservice_preparation` tuple unpacking; `hpc_scientific_commission`
signature; ESM worker selection; worker-selection record (not done, coordinated); a105 catalogue descriptors; a notice
listing the top-level tests that touch removed shared-root names; top-level copies of 13a/13b/RNA records; the ATAC
fixture; the not-done worker-intent family; applied shared-helper fixes (notice to arms).

## Pass 2 (after Checkpoint 14, `933d65ad4`): worker-intent pins and the worker-selection record
Merge source a107 `9fc7d3e54` → `6737ddfe8` (fp4 second pass); the shared-root files diverge too far for
`git merge-file`/`patch`, so the a107 shape was applied by scripted exact-match edits (`<scratchpad>/fpr/w1.pl`–`w7.pl`).
Change against `933d65ad4`: 23 files, +69 −171. Rule: an already staged file is accepted when its bytes equal the
bytes to be staged (and it is read-only), refused when they differ.
- Copy helpers (`library/native_atac_differential_preparation.py`, `native_chromatin_interaction_preparation.py`,
  `native_source_snapshot.py` — the last also serves NMF and fluorescence): no `file_identity`; byte comparison with an
  existing copy; return `{path}`; dependency rows `{path}`. `_verify_pins` and its 2 calls deleted in ATAC, chromatin,
  NMF, fluorescence and FBA.
- Genomic overlap: `_stage(source, target, ...)` copies the selected file's bytes (no Store capture, no sha256/size
  comparison), byte-compares an existing staged file; pins `{path}`; `_pins` closes to `('path',)`;
  `_verify_snapshot(plan, intent)` keeps path/shape and read-only checks, the dependency re-pin loop (and its
  `retained_file_pin` import, code `genomic_overlap_preparation_dependency_conflict`) are gone. Software record (13b):
  `SoftwareBinding` without `python_sha256`, `ImplementationFile {module}`, `python_observed {version}`; the driver
  checks module file existence instead of hashing; `bedtools_sha256` (external) stays.
- NMF / fluorescence / FBA: stdlib `runtime_files` are `{path}`; intent validators accept exactly `{path}`; software
  records `expression_nmf_software_v1` (`FILE_SCHEMA`), `fluorescence_software_v1` (`PIN_SCHEMA`, `_pin`) and
  `FBASoftware` (new `SoftwareFile {path}`; `model_input.file` keeps its data `FilePin`) are path-only and their
  verifiers (`native_fluorescence_driver`, `native_flux_balance_driver`) check file existence; FBA scratch budgets use
  `stat().st_size`.
- Chromatin software record: `SoftwareBinding` without `python_sha256`, `ImplementationFile {module}`,
  `DependencyFile {path}`; producer and `verify_software` no longer hash; HiC native runtime (external) unchanged.
- Receipt validators (`library/atac_result_worker_receipts.py`, `chromatin_result_worker_receipts.py`,
  `genomic_overlap_result_receipts.py`): pins closed to `('path',)`.
- Worker-selection record (shared-root side): `macs2_peak_tools` accepts `python {path}` and `implementation_files
  [{path}]`; the other readers use only `python.path` and the field names. Top-level producer/verifier: handoff row
  (updates the pass-1 "not done" row). Unchanged: `protease_kinetics_native`'s operator-configured deployment pins.
- `tests/live_a106_workflow.py` (manual launcher): `source-pins.json` and `launcher_sha256` no longer written (the
  source snapshot copy stays).
Counts (pass 1 → pass 2): `python_sha256` 15/14 → 8/8 (RNA observed interpreter, external MACS2 runtime and its
checks, test fixtures), `file_identity` 422/111 → 402/111, `read_bytes()).hexdigest()` 14/13 → 13/12; `source_pins`
51/9 are field names only.

Gate (after the last edit): syntax 6,403 files, 0 errors, 0 undefined names in the changed files
(`runs/claude_fpr_501`); import check over 6,267 modules `{}` in each of 5 runs (`runs/claude_fpr_502_0..4`).
Tests: all 86 files, one per launcher run (`runs/claude_fpr_601..686`, `fpr_gate_results.tsv` now holds pass 1 and
pass 2 side by side). Expected: pass-1 outcome per test. Measured: 1,637 tests, 1,360 passed, 140 failed, 136 errors,
1 skipped, 128 test seconds. Per-test against pass 1: 22 tests that passed fail now, all in
`test_fluorescence_episode_routing.py` (`invalid_fluorescence_contract`): the file takes its software record from the
top-level fixture `tests/test_native_fluorescence_contracts.pin`, which still writes sha256/size_bytes. With that
fixture change emulated (verification-only plugin, run `claude_fpr_701`) the file gives exactly its pass-1 result
(22 passed, the same 15 failed). Handoff to fp-top2. No test passes now that failed before. No shared helper that a102
or a107 tests subclass was touched in this pass, so no arm test files were rerun.

Handoffs (pass 2, 3 rows at the end of `handoffs.tsv`): top-level worker-selection producer/verifier; top-level
producers and configurations of the six families' software records and intents; the fluorescence fixture.
