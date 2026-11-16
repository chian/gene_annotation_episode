# fp4 — a107: code that fingerprints the codebase removed (16 November 2026)

Area: `gene_annotation_episode/episodic_workflow/root/a107/` (`R/` below). Brief: `FP_BRIEF.md`; shapes: `fp_recipe.md`
(section 17 added by this task). Comparison base: commit `9fc7d3e54` (all edits uncommitted in the working tree). No git
add/commit, no sub-agents, one launcher command at a time (slot `fp4`). The task was interrupted once by an API usage
limit and resumed from the working tree.

## Outcome
Every mechanism of the recipe that exists in a107 was removed, plus two a107-only ones (the code manifest of three
staged HPC workers and the registered source-path rosters of the information readers). One family decided REMOVE is
**not finished** (worker-intent source/interpreter/stdlib pins of six native preparation modules, see "Not done").
Nothing is left for decision.

Change against `9fc7d3e54`: 144 files, +370 −6,621 lines; 139 modified, 5 deleted (2 roster modules, 3 orphan
fixture files). Tests deleted: 0 (`fp4_deleted_tests.tsv` has a header only).

How: three-way merge from a102 (`330ef3fe7` → `9fc7d3e54`, `a102`→`a107`) for the 80 a107 files with a same-path
a102 counterpart: 34 merged clean (diffs read, all taken), 46 had conflicts. Of those, 40 resolved to "ours" with
a102's hunks applied — the conflicting hunks were only a107-vs-a102 formatting/imports, the fingerprint lines then
removed by scripted edits (binding records, hubs, episode imports) — and 6 resolved by hand (`independent_execution.py`,
`runtime.py`, the two BLAST database contracts/drivers pairs, `native_protein_structure_contracts.py`); the four BLAST
database files now equal a102's result exactly after the arm rename. The rest by scripted exact-match edits, one perl
script per mechanism in `<scratchpad>/fp4/` (`m1.pl` … `m17.pl`, each substitution asserted).

## Removed, by class (site counts `lines/files`, `9fc7d3e54` → now, `git grep` over the area)
Full table: `<scratchpad>/fp4/counts_table.tsv`.

### Class 1 — runtime-computed binding identity
- `implementation_sha256` 134/71 → 6/3 (the 6 are the kept `ExecutionClass.implementation_sha256`, see "Kept").
- 54 `binding_record.py` that carried the digest (14 published-evidence with `_binding_source_bytes` + roster, 8
  execution job/result records with a ~40-name roster hashed through `execution_contracts.digest`, 8 hpc records
  with `hpc_queue.digest` rosters, 1 scientific-process record hashing every `.py` of the arm, plus progress/prediction
  records): field, roster and the imports that only served it gone (recipe 1, 15).
- Hubs: `_binding_source_bytes` 54/34 → 0, `_AXIS_DIRECTORY` 60/46 → 0, `_implementation_path` 1 → 0 (14
  `contracts.py` lose helper + `import hashlib`/`Path`; 18 `execution_contracts.py` lose the trailing
  `from pathlib import Path` + constant; their first `Path` import stays because siblings import it from the hub).
- Consumers: `episode_composition.scientific_binding_compatible` field set; `private_reconstruction_protocol.py`,
  `private_execution_hpc_reconstruction.py` (42 catalog rows lose `fingerprinted`), `private_scientific_literature_
  reconstruction.py` (15 rows) — every descriptor is exactly `{binding_id, version, configuration}`;
  `independent_execution.implementation_sha256()` + runtime-binding field + `identity_conflict` check;
  `method_loop/durable.validate_commission`; `application_execution_binding.py`; `execution_progress.as_record`;
  `ordinary_execution.py` repository sources in the timing-class descriptor;
  `library/literature_source_presentation._TRACKING` no longer lists the name.
- a107-specific (new recipe section 17): `library/execution_initial_information/information_sources.py` and
  `library/received_execution_information/received_reader_sources.py` (`SOURCE_PATHS` rosters of ~2,000 registered
  paths each + `implementation_record()` hashing them) deleted; `FactoryInformationReaders` loses the
  `implementation_record` field, its validation/re-hash loop (`initial_information_reader_implementation_changed`,
  `..._source_custody_required`) and the `implementation` member of `as_record`; `ReceivedExecutionSetup` loses
  `source_record` and the `implementation` member of its reader record (the reader-record comparison stays; its code
  `received_execution_reader_implementation_changed` is still raised when the configuration record changes).

### Class 2 — worker/job implementation manifests
- Native BLAST database result workers (recipe 7) and producer manifest of the BLAST database drivers (recipe 12):
  merged from a102; `implementation_identity` 19/4 → 0, `_verify_implementation` 6/2 → 0, `producer_verification`
  20/4 → 0, `package_files` 10/4 → 0, `producer_manifest` 100/20 → 34/14 (remaining: BV-BRC provider role, the
  `original_producer_manifest_and_verified_file_digests` vocabulary value, as in a101/a102).
- BV-BRC adapter pin (recipe 6): `adapter_implementation_sha256` 21/10 → 0 — `bvbrc_appservice_adapters`,
  `api_bvbrc_appservice`, `bvbrc_appservice_publication`, `bvbrc_appservice_contracts`, six `*_returns.py`
  (`original_adapter_pin_required` gone; `_owner` compares `{adapter_id, adapter_version}`), schema entries in
  `bvbrc_appservice_schemas.json` and `library/received_execution_information/bvbrc_fastqutils_schemas.json`.
- Acquisition observer `adapter_sha256` 4 → 0 and transport `script_sha256` 4 → 0 (recipe 8).
- Code manifest of staged HPC workers (recipe 14; a107 has three): `a103_hpc.py` + `a103_hpc_worker.py`,
  `component_axis_native_hpc.py` + `component_axis_native_worker.py`, `a107_genomic_detection_hpc.py`, and
  `hpc_scientific_commission.py` (merged). Request loses `code_manifest`, `code_manifest_sha256`,
  `source_snapshot_sha256`; body loses `worker_sha256`, `code_manifest_sha256`; the logical-work digests no longer
  include the manifest; workers write every snapshot member (path confinement kept) and echo no source digests;
  admission no longer compares them; the timing-class `implementation` is the worker version. `code_manifest` 21/6 → 0,
  `worker_sha256` 11/6 → 0.
- Driver runtime (recipe 13a, merged): `native_driver_runtime.py`, `native_hmmer_preparation_result_publication.py`.
- Software records (recipe 13b): protein structure (`native_protein_structure_contracts.py`, merged) and generic reader
  `terminal_scientific_evidence.py` (merged); a107 readers of the top-level driver records:
  `library/atac_execution_contracts._DRIVER` (shared by ATAC, MACS2, LUMPY requests) and
  `library/chromatin_interaction_contracts` `SoftwareBinding`/`ImplementationFile`/`DependencyFile` lose
  `python_sha256`, module `sha256`, dependency file `sha256`/`size_bytes`; RNA structure software record
  (`native_rna_structure_contracts`, `rna_structure_comparison_contracts`, `rna_structure_contracts`,
  `native_rna_structure_worker`) loses `python_sha256` and `worker_source_sha256` (the worker hashed its own file) and
  `rna_structure_comparison_calculations._RECOGNIZED_SOFTWARE` loses the pinned worker-source digest
  (`software.worker_source_sha256` out of `COMPATIBILITY_FIELDS`). `worker_source_sha256` 6/5 → 0,
  `python_sha256` 19/12 → 4/3.

### Class 3 — pinned source constants
`SOURCE_[A-Z_]*SHA256` 14/6 → 0: vendored estimator pin (`numerical.py`, `runtime.py`, `independent_execution.py`,
`vendor/SOURCE.nano-graphrag.json` two fields; recipe 5); `SOURCE_FUNCTION_SHA256` and `source_function_sha256`
(FBA: constant + `fba_source_function_mismatch`, job and manifest schema fields, producer in
`flux_balance_request_binding.py`, comparisons in `library/flux_balance_readers.py:855` and
`library/flux_balance_result_worker.py:137`); `library/molecular_deployment_contracts.py` `SOURCE_SHA256`,
`GLYCO_SOURCE_SHA256` (hard-coded digests of the selected tool source) with `original_source_pin_required` and the
`source_sha256=` argument (`molecular_sequence_ordinary.py:42`). The deployment record's `module` file pin itself stays
(observed file of the deployment, no constant). `template_sha256` 2 → 0.

### Class 4 — tests and fixtures
- 0 tests deleted (no a107 test is about the identity mechanism).
- Edited: `tests/test_retained_native_request_contracts.py` (driver record without interpreter/module/dependency
  digests).
- Deleted orphan fixture set `tests/fixtures/rfam/old_workflow/` (3 files; `history.json` carried
  `implementation_sha256`; no test in the repository reads `tests/fixtures/rfam` of a107).

## Suspects carried over from a102 (fp2 "Suspects")
- `runtime.py` pending-work-absent branch: removed. All 61 a107 directories that save a decision also add
  `pending_work` (set comparison of the two directory lists equal, except `library/decision_source_exchange.py`, which
  saves the decision prepared by the calling home's `decision_inputs`).
- `decision_history._tables`: removed (merged), the three joins unconditional.
- `composition_information.restricted_root`: strict attribute read after the path conditions (merged).
- Suspects fp2 kept (blast grader binding lists, `literature_numerical_contracts`, older adapter semantics): untouched.

## Kept, with reason
- `run_statistics.py:65,81-82` / `ordinary_execution.py:60,99` / `execution_memory.py:219`
  `ExecutionClass.implementation_sha256`: timing-statistics key; now hashes versions and Biopython's compiled aligner
  (external binary observed at run time).
- `hmmer_alignment_preparation_data.py` `ALIMASK_PROFILE_EXECUTABLE_SHA256` / `source_sha256s`: decided KEEP
  (selects scientific grading).
- `library/atac_execution_contracts._MACS` and LUMPY `NATIVE_RUNTIME` pins, `rna_module_sha256`/`rna_extension_sha256`:
  external tool files observed at run time.
- Staged-file digest comparisons in `a103_hpc.py:141`, `component_axis_native_hpc.py:207` (transfer record of staged
  data, as a102), `hpc_campaign.py` staged-file digests.
- Remaining `manifest_sha256` (34), `source_sha256` (137), `fingerprint` (52), `read_bytes()).hexdigest()` (16):
  data records, receipts, captured inputs, sequence files.
- `vendor/SOURCE.*.json`, `method_loop/SOURCE.json`: left for the tree-wide pass (only the two recipe-5 fields
  removed).

## Not done (decided REMOVE, not finished in this task)
Worker-intent pins of the native preparation families — copied source snapshot, interpreter copy, dependency files and
stdlib files recorded as `{path, sha256, size_bytes}` and re-verified (`_copy_exact`, `_verify_pins`, `file_pin`) before
and after the worker runs; the intent validators require exactly that pin shape; the retained-receipt validators
re-check them:
- `library/native_atac_differential_preparation.py:57-107,134`, `library/native_chromatin_interaction_preparation.py:
  60-115`, `native_expression_nmf_preparation.py:41-103` (+ `expression_nmf_runtime.py:153-180`),
  `native_fluorescence_preparation.py:30-59`, `library/native_flux_balance_preparation.py:131-240`,
  `library/native_genomic_overlap_preparation.py:187-400,686` (`_CURRENT_REQUIRED_SOURCE_PATHS`),
  `library/native_received_worker_sources.py`;
- receipt validators `library/atac_differential_result_receipts.py:630-640`,
  `library/chromatin_interaction_result_receipts.py:588-597`, `genomic_overlap_result_receipts.py:481-483`;
- `library/received_execution_information/historical_native_genomic_overlap_contracts.py:24,403-408`
  (`python_sha256` of the top-level driver's software binding, compared with the driver's own verification record —
  needs the producer change in the same step; `library/received_execution_information/historical_flux_balance_contracts
  .py:126-127` `FBASoftware` pins likewise).
Shape to apply (recipe 13a): keep the copies and paths, record `{path}` only, delete `_verify_pins`, make
`_copy_exact` a fresh-destination copy, drop `sha256`/`size_bytes` from the intent validators and receipt checks.

## Gate (measured)
1. Syntax: 2,914 `.py` files of the area parsed, 0 syntax errors; bound-name/unused-import check over the 136 changed
   `.py` files: no new undefined name (the one reported, `independent_execution.py` `options`, is identical at
   `9fc7d3e54`), the only new unused import is `Path` in 18 `execution_contracts.py`, kept because sibling modules
   import it from there (`runs/claude_fp4_005`). Import check over all 2,793 product modules prints `{}`
   (`runs/claude_fp4_006`). Both after the last edit.
2. Tests: all 93 test files, one file per launcher run, isolated form, after the last edit (`runs/claude_fp4_101..193`,
   logs `runs/claude_fp4_homes/101..193.log`, 10:00:48–10:04:01). Expected, written down before launching
   (`<scratchpad>/fp4/expected.txt`, from `rec4_gate_results.tsv`): 93 files, 2,161 tests = 2,129 passed + 32 failed,
   ~1,084 test seconds. Measured: 93 files, 2,161 tests = **2,129 passed, 32 failed, 0 errors, 0 skipped**,
   0 collection errors, 125 test seconds, 3 min 13 s wall. Per-test comparison with `runs/claude_rec4_461..553`: the
   32 failing test IDs are identical before and after; **0 tests passed before and fail now**.
   - Pre-existing failures (unchanged): the four `*/execution_job_submission/tests/test_launch_connected.py` under
     `hpc_work_planning` (2 each), `tests/test_literature_partner_assessments.py` (5),
     `test_literature_partner_defined_integration.py` (2), `test_literature_partner_integration.py` (9),
     `test_literature_partner_native_integration.py` (7), `test_literature_structural_scalar_contexts.py` (1).
   - Awaiting shared test fixes (`decision_history` journal without ledger; `hpc_prediction_behavior.py:177`): none in
     a107 — no a107 test file failed for either reason.
   - Duration: `tests/test_received_api_restoration.py` took 811 s before and 18 s now; the other large drops are in
     files that call binding `as_record()` (removed per-call source hashing, including the ~2,000-path reader rosters).
     Not profiled.
   Not covered by an a107 test: the staged HPC workers, BLAST database drivers/workers, HMMER preparation result
   worker, protein-structure and RNA-structure workers (syntax, bound-name and import checks only).
3. Site counts: see "Removed" and `<scratchpad>/fp4/counts_table.tsv`. Tokens with 0 sites before and after:
   `worker_fingerprint`, `CALLABLE_SHA256`, `callable_sha256`, `resource_implementation_bytes`, `_context_source_key`.
   Unchanged because they belong to "Not done": `source_pins` 47/9, `_source_closure` 20/10, `current_worker_sources`
   5/3, `REQUIRED_MODULES` 10/5 (module-name lists, kept by rule), `module_sha256` 9/6 (external RNA module).

## Handoffs
- Applied: none were addressed to `fp4`.
- Written (4 rows `fp4 → fp-top`, `handoffs.tsv` lines 463–466): shared FBA driver/contracts stop writing
  `source_function_sha256`; top-level ATAC driver/contracts/software stop writing/checking driver-runtime digests;
  top-level chromatin driver/contracts same; top-level tests using `SOURCE_SHA256` of the molecular deployment copies.
- Not re-written (already rows 437–452 from fp2): shared `root/tests/` fixtures without a completion ledger and the
  digest assert in `root/tests/hpc_prediction_behavior.py:177`.

## Second pass (after Checkpoint 11): worker-intent pins finished
The "Not done" family above is now removed. I made the edits with scripted exact-match changes (`<scratchpad>/fp4/m19*.pl`).
Rule applied (coordinator): an already staged file is accepted when its bytes equal the bytes to be staged, and
refused when they differ. No digest is involved, and an interrupted preparation still resumes.
- **Copy helper.** `_copy_exact` in `library/native_atac_differential_preparation.py`,
  `library/native_chromatin_interaction_preparation.py` and `expression_nmf_runtime.py` no longer computes a file
  identity. It copies, compares bytes with an existing copy (which must be read-only) and returns `{path}`.
  Dependency rows are `{path}`. `_verify_pins` (the re-hash before and after the worker) is deleted with its 2 calls
  in each of ATAC, chromatin, NMF and FBA.
- **Genomic overlap** (`library/native_genomic_overlap_preparation.py`): `_stage(source, target, ...)` copies the
  selected file directly; it no longer captures into the Store and compares sha256/size. It byte-compares an existing
  staged file and keeps the read-only check. Pins are `{path}`. `_verify_snapshot(plan, intent)` keeps the path/shape
  and read-only checks, and the dependency re-pin loop is gone. The `_CURRENT_REQUIRED_SOURCE_PATHS` name list stays.
- **NMF** (`native_expression_nmf_preparation.py`): `runtime_files` are `{path}`; the intent validator accepts
  exactly `{path}`. The driver software record `expression_nmf_software_v1` (`native_expression_nmf_contracts.py`
  `FILE_SCHEMA`) is `{path}`. `verify_expression_nmf_software` checks that each listed file exists instead of
  re-hashing it. The interpreter path/version, distribution versions and unbound-import checks stay. The test helper
  `tests/support/expression_nmf/fixture_helpers.py` builds the path-only record.
- **FBA:**
  - `library/native_flux_balance_preparation.py`: `_pin` is `{path}`; the selected-runtime re-hash is gone; the
    scratch budget uses `stat().st_size`; `runtime_files` are `{path}`.
  - `FBASoftware` (`historical_flux_balance_contracts.py`) has `python`, `implementation_files`, `runtime_files`
    and `solver_runtime_files` as `SoftwareFile {path}`. `model_input.file` keeps its data `FilePin`.
- **Fluorescence (reader only):** `native_fluorescence_preparation._pin` accepts exactly `{path}`.
- **Receipt validators:** `library/atac_differential_result_receipts.py`,
  `library/chromatin_interaction_result_receipts.py` and `genomic_overlap_result_receipts.py` check pins as `{path}`.
- **Genomic overlap software binding** (`historical_native_genomic_overlap_contracts.py`): no `python_sha256`;
  `ImplementationFile` is `{module}`; `python_observed` is `{version}`. `bedtools_sha256` stays (external
  executable).

Gate (after the last edit):
- Syntax: 2,914 files, 0 errors. Bound-name check: nothing new except an unused `file_pin` import, which I removed
  (`runs/claude_fp4_201`).
- Import check over all 2,793 modules: `{}` (`runs/claude_fp4_202`).
- Tests: all 93 files, one per launcher run (`runs/claude_fp4_301..393`, 10:09:09–10:12:28). Expected: same as the
  first pass. Measured: 2,129 passed, 32 failed, 0 errors, 0 skipped, 133 test seconds. The 32 failing IDs are
  identical to the first pass (and to rec4), so 0 tests newly fail.
- `fp4_gate_results.tsv` now holds this pass.
- No a107 test runs these preparation functions; the edits are covered by the syntax, bound-name and import checks
  only.

Remaining sites in these files are names, paths or external tools: `_MACS`/LUMPY native runtime pins and
`bedtools_sha256` (external), `GENOMIC_OVERLAP_DEPENDENCIES_SHA256` (record digest).

Handoffs: 3 new rows `fp4 → fp-top` (`handoffs.tsv` lines 467–469):
- shared `root/library/native_fluorescence_preparation.py`;
- FBA software record and shared preparation, plus its operator configuration;
- operator configuration of the NMF software record.
The genomic-overlap shared producers were already listed by fp3 (rows 457–459).
