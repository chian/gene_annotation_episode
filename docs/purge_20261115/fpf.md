# fpf — fingerprint removal finished in a101 and a103 (16 November 2026)

Area: `gene_annotation_episode/episodic_workflow/root/a101/` and `.../root/a103/` only. Brief: `FP_BRIEF.md`, recipe
`fp_recipe.md` (13a, 13b, 14-19). Comparison base: commit `6737ddfe8` (HEAD at start). Checkpoint 13 (`06214e132`) was
committed underneath this task and contains 5 of my a101 files (`composition_information.py`, `decision_history.py`,
`native_driver_runtime.py`, `native_hmmer_preparation_result_publication.py`, `terminal_scientific_evidence.py`); the
rest is uncommitted. Diff against `6737ddfe8`: 21 files, +104 −189 (20 in a101, 1 in a103). No sub-agents, one launcher
command at a time (slot `fpf`), no git writes. Deleted tests: none (`fpf_deleted_tests.tsv` has a header only).

## a101

### 13a — driver-runtime pins (three-way merge from a102, base `330ef3fe7`, theirs `9fc7d3e54`, a102→a101)
- `native_driver_runtime.py` (clean merge): record `driver_runtime` = `{python_executable, python_version, module_root,
  implementation_files: [{module}], dependencies: [{distribution, version, package_root, files: [{path}]}]}`;
  `_SHA`/`_INT`/`_PIN`, `stream_identity`, `file_identity`, `import hashlib` gone; `verify_driver_runtime` keeps
  interpreter path/version, module-file presence/loaded path, dependency version/root and "loaded site-packages module
  is listed"; `_copy_exact` → `_copy_source` (fresh destination: its one caller always creates the snapshot directory
  fresh and already refuses a pre-existing incomplete one, `result_worker_runtime_original_work_incomplete`).
- `native_hmmer_preparation_result_publication.py` (clean merge): `_runtime_files` compares module paths only;
  `result_worker_original_software_changed`, `result_worker_original_source_size_conflict` and the post-worker re-check
  are gone.

### 13b — software records with interpreter/module pins and the generic reader
- `terminal_scientific_evidence.py` (merge, 1 conflict resolved keeping a101's `original_context` lines): the two
  branches turning `python_sha256` / `implementation_files[{module, sha256}]` into file pins, the `module_roots`
  parameter and both `PYTHONPATH` splits are gone (`terminal_native_implementation_path_unavailable` gone).
  `library/retained_input_authority/terminal_scientific_evidence.py` only re-exports the root module.
- `library/retained_input_authority/native_protein_structure_contracts.py` (clean merge from a107): no
  `python_sha256`, `ImplementationFile` = `{module}`.
- `.../native_atac_differential_contracts.py:74` `_DRIVER` (also used by LUMPY, MACS2 request bindings and the ESM
  deployment record via `driver_runtime_schema`): 13a shape. `_MACS` (MACS2 external tool record) kept as in a107.
- `.../chromatin_interaction_contracts.py:173` (clean merge from a107): `SoftwareBinding` without `python_sha256`,
  `ImplementationFile` `{module}`, `DependencyFile` `{path}`.
- `.../native_genomic_overlap_contracts.py:27`: `ImplementationFile` `{module}`, `SoftwareBinding` without
  `python_sha256`, `python_observed` = `{version}` (a101 has no `python_expected` comparison).
- `.../native_rna_structure_contracts.py:26`: `python_sha256` out of `SOFTWARE_SCHEMA` (as a107); `rna_module_sha256`,
  `rna_extension_sha256` (installed ViennaRNA files) stay.
- `.../native_fluorescence_contracts.py:39,86-88`: `PIN_SCHEMA` and `_pin` are exactly `{path}` (python,
  implementation_files, runtime_files of `fluorescence_software_v1`; same as fp5 in a104).
- `.../flux_balance_contracts.py:270-274`: `FBASoftware` uses `SoftwareFile {path}` for python, implementation_files,
  runtime_files, solver_runtime_files (a107 shape); `FilePin` stays for the model-input data file.
- `.../native_expression_nmf_contracts.py:26,52`: `FILE_SCHEMA` `{path}`, size check gone.

### Section 19 — worker-intent pins (a101 only reads these records)
- `.../atac_differential_result_receipts.py:491-492`, `.../chromatin_interaction_result_receipts.py:449-450` (clean
  merges from a107): intent pins closed to `('path',)`.
- `.../native_fluorescence_preparation.py:31-32` (clean merge): `_pin` exactly `{path}`.
- `.../native_flux_balance_preparation.py:44-45`: `_pin` exactly `{path}` (no `File` record built from the digest).
- `.../native_expression_nmf_preparation.py:3,23`: pins exactly `{path}`; docstring no longer claims "exact pins".
- Module/path name lists (`REQUIRED_MODULES`, `_REQUIRED_MODULES`, required worker source paths) stay.
- a101 has no producer/copier of these intents (no `_copy_exact`/`_verify_pins`/`file_pin` copy of the preparation
  families), so the "existing destination" rule has no object here.

### 14-16 (a102-only shapes)
No a101 counterpart: a101 has no staged HPC worker, no `hpc_work_planning` binding records, no `_PRIVATE_RECONSTRUCTION`
`fingerprinted` member, no `*_resources.as_record` digest (`git grep implementation_sha256|fingerprinted|code_manifest|
worker_sha256` in a101 finds only the kept `ExecutionClass.implementation_sha256` and one comment). No a101 Workflow
double needed `root_action_boundary` (no test failed for it).

### Suspects carried over (fp2/fp3)
- `runtime.py:478-482`: the `elif packet is not None` branch with `pending_at_selection=None` is gone,
  `decision_context['pending_work']` is read unconditionally. Evidence: 44 a101 directories save a decision; 42 add
  `pending_work` before saving; the other two are `library/` (`decision_source_exchange.py`, which saves the decision
  prepared by the calling home, as fp4 found in a107) and `tests/` (`test_blast_native_return_admission.py:164` saves a
  `redeliver_report` decision with request `{}`; it still passes, the branch is not reached).
- `decision_history._tables` (clean merge): the three joins unconditional. Producers: `episode_journal.py:67`,
  `episode_completion.py:137-142`.
- `composition_information.restricted_root` (clean merge): strict read after the path conditions
  (`Workflow.__init__` refuses any other value, `runtime.py:1010-1012`).
- Also applied handoff row 461 (fp3 → fp1): `homology_results.py` three-way merge from a103 (`4a3aba851` → now; import
  conflict resolved to a101's imports): `recorded_coverage` / `_native_complete` read `parse_inventory`,
  `publication_witness_version`, `native_termination_seen` without defaults; `_grading` never returns `None`; the
  `phmmer_shared_grading_unavailable` block and the `hmmer_shared_paired_aliases_v1` re-reading of saved gradings are
  gone; unused `source_tool_gradings` import removed. Producers checked in a101: the only snapshot writer
  (`homology_results.py:340-350`) always writes the three fields; `phmmer_result_worker.py:155-159` always writes
  `grading_file` or `grading_failure`. Left as in a103: `homology_results.py:506` (`'grading_error_count' in
  snapshot.get('parse_inventory', {})`).

### Kept (decided KEEP)
`ALIMASK_PROFILE_EXECUTABLE_SHA256` (`library/hmmer_alignment_preparation_*`), test-oracle
`tests/fixtures/hmmer_native_weight_oracles/SOURCE_PINS.json`, `_MACS` and LUMPY `NATIVE_RUNTIME` external tool pins,
`ExecutionClass.implementation_sha256`, `native_blast_vdb_utility_execution.py` runtime files (external NCBI VDB
files), data `FilePin`s, `vendor/SOURCE.*.json` / `method_loop/SOURCE.json` (left for later).
`tests/test_native_hmmer_preparation_result_publication.py:51-69` hashes the copied snapshot inside the test to check
its own copy; it does not use a product pin and was left.

## a103

### `_stage` resumes (recipe 19 rule) — `native_genomic_overlap_preparation.py:265-282`
fp3's `_require(not os.path.lexists(target), ...)` is gone. Inside the target's directory: `_read(parent, name)`; if a
staged file exists it must have exactly the bytes of the source (`genomic_overlap_preparation_snapshot_conflict`
otherwise) and be read-only (`genomic_overlap_preparation_snapshot_mutable`), then it is accepted; otherwise the scratch
budget is checked (only for bytes actually copied, so a resumed file is not counted twice) and the file is copied as
before. No digest. Verified by a probe run through the launcher (`runs/claude_fpf_005`, script
`<scratchpad>/fpf/probe_stage.py`): fresh copy 0o444; second call with equal bytes accepted (no extra file); accepted
again with the snapshot directories made 0o555; changed source refused with `..._snapshot_conflict`; writable staged
copy refused with `..._snapshot_mutable`.

### Other staging/reuse sites fp3 changed
- `native_driver_runtime._copy_source` refuses an existing destination, but its one caller
  (`native_hmmer_preparation_result_publication._worker_runtime:254-266`) creates the snapshot directory fresh and
  already refuses a pre-existing incomplete one (`result_worker_runtime_original_work_incomplete`, unchanged by fp3);
  the former identical-copy branch of `_copy_exact` was unreachable. Left as decided in 13a.
- `a103_hpc_worker.py` writes snapshot members with `write_bytes` (overwrites, no refusal). Nothing to fix.
- `genomic_overlap_worker_runtime.py` no longer copies anything (dependency records only).

### Section 19 in a103
Already complete from fp3: `git grep` finds no `python_sha256`, `_copy_exact`, `_verify_pins`, `file_pin`, sha256 in
`source_pins`/`interpreter`/dependency rows; the only intent family is genomic overlap; `REQUIRED_MODULES` is a name list.

## Site counts (lines/files, `6737ddfe8` → now, `git grep`)
| token | a101 | a103 |
|---|---|---|
| `python_sha256` | 13/8 → 1/1 (`_MACS`, kept) | 0 → 0 |
| `stream_identity` | 3/2 → 1/1 (unrelated code name `bundle_stream_identity_conflict`) | 1/1 → 1/1 (BLAST utility data) |
| `_copy_exact` | 3/2 → 1/1 (a test name `..._copy_exactly_...`) | 0 → 0 |
| `module_roots` | 9/1 → 0 | 0 → 0 |
| `result_worker_original_software_changed`, `..._source_size_conflict`, `terminal_native_implementation_path_unavailable` | 1/1 each → 0 | 0 → 0 |
| `def _tables`, `pending_at_selection=None`, `getattr(workflow, 'root_action_boundary'` | 1/1 each → 0 | 0 → 0 |
| `phmmer_shared_grading_unavailable` | 2/1 → 0 | 0 → 0 |
| `os.path.lexists(target)` | 0 → 0 | 1/1 → 0 |
| `source_pins` / `driver_runtime` / `implementation_files` / `REQUIRED_MODULES` | 30/11, 52/10, 33/16, 9/4 → 30/11, 51/10, 32/15, 9/4 (field and record names stay; rows are path/module only) | unchanged 11/2, 25/4, 10/5, 2/1 |

## Gate (measured, after the last edit)
1. Syntax: a101 2,185 files, a103 3,412 files, 0 syntax errors. Bound-name / unused-import check over the changed
   files (20 a101, 1 a103) compared with `6737ddfe8`: no new undefined name, no new unused import
   (`runs/claude_fpf_001`, `_002`).
2. Import check over all product modules: a101 1,870 modules `{}` (`runs/claude_fpf_003`); a103 3,262 modules `{}`
   (`runs/claude_fpf_004`).
3. Tests, one file per launcher run, isolated form (`runs/claude_fpf_101..198` a103, `_201..467` a101; logs
   `runs/claude_fpf_homes/NNN.log`; junit in each run dir; table `fpf_gate_results.tsv` with the previous values per
   file). Expected values were written before launching (`<scratchpad>/fpf/expected.txt`).

   | arm | | files | collected | passed | failed | errors | skipped | seconds (per-file wall sum) |
   |---|---|---|---|---|---|---|---|---|
   | a103 | before (fp3, `claude_fp3_201..298`) | 98 | 4,331 | 4,308 | 23 | 0 | 0 | 214 |
   | a103 | expected | 98 | 4,331 | 4,308 | 23 | 0 | 0 | ~214 |
   | a103 | measured | 98 | 4,331 | **4,330** | **1** | 0 | 0 | 282 |
   | a101 | before (fp1, `fp1_gate_results.tsv`) | 267 | 9,751 | 9,227 | 286 | 178 | 60 | 1,080 |
   | a101 | expected | 267 | 9,751 | 9,227 | 286 | 178 | 60 | ~1,080 |
   | a101 | measured | 267 | 9,751 | **9,227** | **286** | **178** | **60** | 1,083 |

   Per-test comparison (FAILED/ERROR ids from the `-rfE` logs): **0 tests fail now that passed before, in either arm.**
   - a103: 22 tests that failed in fp3's pass now pass: the 20 `no such table: runtime_decision_effects` and the 2
     `KeyError: 'implementation_sha256'` tests — the shared `root/tests/` fixes landed meanwhile (not my change). So
     "awaiting shared test fixes": none. Still failing (pre-existing): `tests/test_a103_context.py::
     test_runtime_parent_receives_exact_component_operands_from_automatic_grading`.
   - a101: the failing set is identical to fp1's (36 files, same ids). Note: cr1 changed 4 a101 controlled-response
     modules after fp1's gate; the comparison still shows no difference.

## Edited code that no test executes (measured)
A second pass of all 267 a101 test files with a verification-only line tracer (`sys.monitoring` pytest plugin kept in
the scratchpad, `runs/claude_fpf_501..767`) recorded which changed lines run in the test processes (subprocess workers
are not traced; continuation lines of a multi-line statement never register):
- Never imported by any a101 test process: `terminal_scientific_evidence.py`, `.../atac_differential_result_receipts.py`,
  `.../chromatin_interaction_contracts.py`, `.../chromatin_interaction_result_receipts.py`,
  `.../native_atac_differential_contracts.py`, `.../native_expression_nmf_contracts.py`,
  `.../native_expression_nmf_preparation.py`, `.../native_flux_balance_preparation.py`,
  `.../native_rna_structure_contracts.py`.
- Imported but the changed function bodies not run: `runtime.py:478-480` (completed-action pending-work context),
  `native_hmmer_preparation_result_publication.py` (all 9 changed lines; its test file errors before reaching them, as
  before), `native_driver_runtime.py` (`verify_driver_runtime`, `_copy_source`, `freeze_driver_runtime` bodies; only
  module-level schema lines run), `.../native_fluorescence_preparation.py` `_pin`, `.../native_fluorescence_contracts.py`
  `_pin`, `homology_results.py` (`recorded_coverage`, `_native_complete`, `_grading`, the grading loop),
  `decision_history.py` query bodies of `_attempt_rows`/`_observations` (only 2 of 14 changed lines ran),
  `composition_information.py:60` (the boundary clause).
- Executed: module-level schema changes in `flux_balance_contracts.py`, `native_genomic_overlap_contracts.py`,
  `native_protein_structure_contracts.py` (import-time only).
- a103: no a103 test executes `native_genomic_overlap_preparation._stage`; covered only by the probe above.

## Handoffs
- Applied: row 461 (fp3 → fp1, `homology_results.py`). No rows addressed to `fpf`.
- Written (`fpf → fp-top`, `handoffs.tsv` lines 472-474): RNA-structure software `python_sha256` producers in
  `root/library` (row 430 covered only `worker_source_sha256`); shared ATAC/chromatin/NMF worker-intent producers
  (`native_*_preparation.py`, `native_source_snapshot.py`) with the resumable-staging rule; ESM deployment driver record
  producer (`gene_annotation_episode/esm_gene_embedding_tools.py:226`), validated by a101 through the ATAC
  `driver_runtime_schema`. Not repeated: protein structure (443-445), ATAC/chromatin driver (447-449, 464-465), HMMER
  publication (450), genomic overlap (457-459), FBA (463, 468), fluorescence (467, 470), NMF software config (469).

## Left for decision
None.
