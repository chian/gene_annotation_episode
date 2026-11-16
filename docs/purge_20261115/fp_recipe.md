# Recipe: removing code that fingerprints the codebase (written by fp1 on a101, 15 November 2026)

`R` = `gene_annotation_episode/episodic_workflow/root/a101`. "Before" line numbers are those of commit `2ad8be3de`
(`git show 2ad8be3de:<path>`); replace `a101` by your arm. Every entry was applied in a101 and its tests pass unless the
entry says "NOT REMOVED in a101". Edit scripts used (perl, one per mechanism, each substitution asserted) are in
`<scratchpad>/fp1/*.pl` only as long as the scratchpad lives; the shapes below are the durable part.

General rules that held everywhere
- The field is deleted from producer, schema/field-set check, comparison and tests in one step. No `if present`.
- After each mechanism: syntax check, import check over all product modules, and a global-name check (a symtable
  script) over changed files, because the dense one-line modules import helpers through `*_contracts.py` hubs.
- An import that only served the removed code is removed (`hashlib`, `Path`, `importlib`, `re` stay when still used).
- Record `version` strings are untouched.
- `git diff HEAD` is not a reliable "what did I change" during this task (checkpoint commits happen underneath you):
  diff against the commit that was HEAD when you started.

## 1. Binding record digest (`binding_record.py`, 27 files in a101)
Before, `R/scientific_process/binding_record.py:9-10`: `implementation = scientific_digest({... rglob('*.py') ...} |
{_context_source_key: ...})` then `'implementation_sha256': implementation` in `as_record()`.
Before, `R/resource_work_submission/binding_record.py:8-17`: `implementation = _binding_source_bytes()`,
`implementation += resource_implementation_bytes()`, `+= (_AXIS_DIRECTORY / 'resource_records.py').read_bytes()` ...,
`'implementation_sha256': hashlib.sha256((implementation + b''.join(<4 _context_source_key files>))).hexdigest()`.
Same in `published_evidence_assessment/**/binding_record.py` (7), `execution_progress_assessment/binding_record.py`
(own `_binding_source_bytes` at module end) and the `scientific_process/` mirrors.
After: `as_record()` is the single `return {'version': ..., 'binding_id': ..., 'configuration': {...}}`; the lines that
built `implementation`, the local `from pathlib import Path as _context_source_path` and the function-level import of
`resource_implementation_bytes` are gone; the import line keeps only what `as_record` still uses
(`from .source_contracts import VERSION`; nothing at all for the resource records).

## 2. Source-byte helpers and rosters
- `def _binding_source_bytes()` + `_AXIS_DIRECTORY = Path(__file__).resolve().parents[N]` at the end of every
  `*/execution_contracts.py` (before: `R/execution_job_submission/execution_contracts.py:60-64`, 23 files) and
  `*/source_contracts.py` (before: `R/published_evidence_assessment/source_contracts.py:29-32`, 14 files): both
  deleted, also where no binding record used them (the `execution_job_submission*`, `execution_result_acquisition`,
  `homology_*` copies were already dead). The duplicated `from pathlib import Path` directly above is deleted where the
  module imports `Path` earlier; `import hashlib` / `from pathlib import Path` are deleted where the module itself has
  no other use and no sibling imports the name from it (resource_* and literature copies).
- `R/a101_resource_implementation.py` (`HOMOLOGY_BINDING_SOURCES` roster + `resource_implementation_bytes`): whole
  module deleted (no importer left).

## 3. Consumers of the binding digest
- `R/episode_composition.py:57-58` `scientific_binding_compatible`: `fields = {'version', 'binding_id',
  'configuration'}` and the three `implementation_sha256` shape clauses dropped; the function still compares the
  canonical records.
- `R/execution_progress.py:1087`, `R/homology_progress.py:65`: the `'implementation_sha256':
  hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),` line of `as_record()` deleted.
- `R/scientific_process/process_state.py` needed nothing in a101 (it already compares `mechanics_binding` with
  `self.as_record()`); if your arm still has `{**saved_binding, 'implementation_sha256': current[...]}`, compare the
  records directly.

## 4. Runtime binding of a commissioned episode
- `R/independent_execution.py:30-48` `def implementation_sha256()` deleted; `make_runtime_binding` returns
  `{'factory_module', 'factory_name', 'arguments', 'settings_sha256'}`; `open_commission` loses
  `if binding['implementation_sha256'] != implementation_sha256(): raise _failure('identity_conflict', handle)`;
  `__all__` loses the name.
- `R/method_loop/durable.py:264,271` `validate_commission`: `_exact(binding, "factory_module factory_name arguments
  settings_sha256", ...)`, the `_digest(binding["implementation_sha256"], ...)` line deleted.
- `R/application_execution_binding.py:52-63,133,138-139,154`: `_runtime_binding` field set and digest loop reduced to
  `settings_sha256`; `_known_selection` no longer stores the digest; `_check_known_selection` no longer compares it;
  `_make_binding` loses the `binding['implementation_sha256'] != selection[...]` clause.

## 5. Vendored estimator source pin
`R/numerical.py:39` `SOURCE_SHA256 = "02af..."` deleted, `provenance()` loses `"source_sha256"`;
`R/runtime.py:3832` and `R/independent_execution.py:219` write/expect `{'estimator_version': ESTIMATOR_VERSION}`
(no `template_sha256`); `R/vendor/SOURCE.nano-graphrag.json` loses `source_sha256` and `adapter_template.sha256`.
`SOURCE_REVISION` (upstream commit label, compared with nothing) stays.

## 6. BV-BRC adapter implementation pin
- `R/library/bvbrc_proteome_bundle_adapter.py`, `..._v2.py`, `bvbrc_homology_bundle_adapter.py`: `_DEPENDENCIES`
  rosters and `def implementation_sha256()` deleted, `__all__` adjusted.
- `R/bvbrc_appservice_adapters.py:19-27`: `bind_adapters` binds `bound[key] = implementation` (was the tuple
  `(implementation, row['implementation_sha256'])` after comparing the digest). Callers that unpacked the tuple
  (`R/api_bvbrc_appservice.py:164-166`, `R/bvbrc_appservice_publication.py` `_grade`) use the module directly.
- Configuration rows `scientific_adapters[]` are `{adapter_id, adapter_version}`: schema entry removed in
  `R/library/bvbrc_appservice_schemas.json` and `R/library/retained_input_authority/bvbrc_fastqutils_schemas.json`
  (property + `required`).
- `PublicationInputs.adapter_implementation_sha256` removed: producer (`publication_inputs`), schema (same two JSON
  files), `_validate_inputs` configuration cross-check, `result_identity` key, relation check in
  `R/library/bvbrc_appservice_contracts.py:360-363`. Where the code used "digest is None" as "no adapter bound":
  `_grade` now does `implementation = self._adapter(...); if implementation is None: return None`; `read` requires
  `inputs['adapter'] is not None` for a saved adapter result.
- `*_returns.py` (6 files: proteome_return_values, comparative_systems, fastqutils, genome_alignment, alignment,
  application): the two lines `pin = inputs.get('adapter_implementation_sha256')` / `_require(... fullmatch ...,
  'original_adapter_pin_required')` deleted; in the three `_owner` methods the configured-row comparison keeps
  `{'adapter_id', 'adapter_version'}` only (still code `original_adapter_pin_conflict`: the selected adapter must be
  configured for the resource).

## 7. Native BLAST database result worker: implementation manifest
Files: `R/native_blast_database_result_worker.py`, `R/native_blast_standard_database_result_worker.py`, the two
`*_result_publication.py`, `R/library/native_blast_database_worker_values.py`,
`R/library/native_blast_standard_database_worker_values.py`, `R/native_blast_{,standard_}database_results.py`.
- Coordinator: `_implementation(directory, policy, ...)` (ran a subprocess that hashed every loaded module, wrote
  `implementation.json`/`implementation-receipt.json`, re-hashed on reuse) deleted with `_SCIENTIFIC_MODULES`;
  `_request`/`_saved_request` lose the `implementation` parameter and the request key; `_manifest` loses the two
  manifest fields and the `implementation_manifest_sha256 != request['implementation']['manifest_sha256']` clause;
  the results modules no longer collect `implementation-receipt.json`.
- Worker: request schema loses `implementation`, manifest schema loses `input_implementation_sha256` and
  `implementation_manifest_sha256`; `_DEPENDENCY_ROOTS`, `_PROJECT_MODULES`, `_module_name`,
  `_implementation_modules`, `_verify_implementation` and both calls deleted; `_reuse` no longer returns the saved
  input-implementation digest.
- Values: `*_implementation_identity(files)` deleted; `*_calculation_identity(*, input_identity, sequence_model
  [, vdb_function_model])` hashes `{version, input_identity}` for the interpretation id and `{version,
  input_interpretation_id, sequence_model[, model]}` for the calculation id. The worker computes it once
  (`initial`) and checks `request["calculation_id"]` against it at the same point as before.
- NOT part of this: `reuse.manifest_sha256`, `calculation_input.manifest_sha256` (digest of the saved
  `worker-manifest.json`, a data record).

## 8. Acquisition transport
`R/acquisition.py:167,201-205,224,274,284,285,425`: observer policy loses `adapter_sha256`; the injected observer
script no longer receives/compares it (`response_capture_adapter_changed` gone); `script_sha256` (hash of the installed
third-party skill script) removed from the four transport/diagnostic dicts, `"script": str(script)` stays.

## 9. Parser fingerprint in homology metadata
`R/homology_results.py:288-289,303`: `worker_fingerprint = hashlib.sha256(b''.join(<8 parser sources>))` and
`'parser_implementation_sha256': worker_fingerprint` deleted.

## 10. Timing-statistics class keys and replay report
- `R/ordinary_execution.py:54-58,99-101`: the `'files': {name: sha256(source)}` member of the hashed class descriptor
  loses repository sources. Alignment keeps `'native_pairwise_aligner_sha256'` (Biopython's compiled extension, an
  external binary observed at run time); the spreadsheet class keeps versions only. `ExecutionClass.
  implementation_sha256` itself stays (it also carries the external executable digest, `R/execution_recording.py:141`).
- `R/a101_replay.py:57`: `'implementation_sha256': {name: sha256(...) for 3 scorer sources}` removed from the report.

## 11. Pinned tool-source constants in `library/retained_input_authority/`
- `native_flux_balance_contracts.py:20,64` `SOURCE_FUNCTION_SHA256` + `fba_source_function_mismatch` check;
  `flux_balance_request_binding.py:16,66` producer; `flux_balance_contracts.py:282,291` schema entries
  (`source_function_sha256` in requested job and manifest).
- `protein_disorder_measurements.py:10-11` `SOURCE_SHA256`, `CALLABLE_SHA256`;
  `protein_disorder_result_contracts.py:115` `module_sha256=`/`callable_sha256=` in the source-profile const.
- `fluorescence_native_report_contracts.py:14` `PROFILE_SOURCES[...]` keep `operation` only (no
  `source_file_sha256`/`function_sha256`).
- `native_rna_structure_contracts.py:26` `worker_source_sha256` out of `SOFTWARE_SCHEMA`;
  `rna_structure_comparison_contracts.py:32` `software.worker_source_sha256` out of `COMPATIBILITY_FIELDS`.
  `rna_module_sha256`/`rna_extension_sha256`/`python_sha256` (installed external tool files observed at run time) stay.
- The job-side producers of these records live in the top-level package: write a handoff row.

## 12. Producer manifest of the native BLAST database drivers (not in `h5_self_hashing.tsv`)
A manifest file listing every staged package source file with sha256 (`package_files`), verified by the driver
before launch and recorded in the bundle as `producer_verification`; plus "retained" validators that recognised the
file rosters of two earlier source layouts.
Files: `R/library/native_blast_database_contracts.py`, `R/library/native_blast_standard_database_contracts.py`,
`R/native_blast_database_driver.py`, `R/native_blast_standard_database_driver.py`,
`R/native_database_terminal_custody.py`, 5 callers of the retained validators.
- Contracts: delete `PRODUCER_MANIFEST_SCHEMA`, `_PRODUCER_VERIFICATION_SCHEMA`, `_validate_producer_manifest_profile`,
  `validate_*_producer_manifest`, `_PRE_*_REQUIRED_FILES`, `_has_pre_*_profile`,
  `validate_retained_*_producer_manifest`, `_producer_files`, `_validate_producer_verification`, the
  `_ORIGINAL_*` schemas at module end; `PLAN_SCHEMA` loses `producer_manifest` (and the two plan checks);
  bundle schema loses `producer_verification`; artifact role enum loses `producer_manifest`; `FAILURE_CODES` loses
  `producer_manifest_invalid`, `producer_file_missing`, `producer_file_identity_mismatch`,
  `producer_file_unreadable`, `producer_package_inventory_mismatch`, `producer_runtime_path_mismatch`
  (`producer_input_parser_unavailable` stays: still raised on `ImportError`).
- `_validate_bundle_profile(bundle, *, ..., bundle_schema, manifest_validator)` becomes the one
  `validate_*_bundle(bundle, *, original_job, attempt_identity)`; `validate_retained_*_bundle` deleted and its callers
  (`*_acquisition.py`, `*_result_worker.py`, `*_result_publication.py`, `library/native_blast_standard_database_
  metadata.py`, `library/blast_native_iteration_records.py`, `library/native_blast_database_convergence.py`) call
  `validate_*_bundle`. In the artifact loop every artifact has exactly one owner again (`if len(owners) != 1:
  _fail(...)`, block dedented); `used = set()`; a failure with an artifact but no applicable owner is
  `failure_unrelated_artifact`.
- Drivers: `_verify_producer` deleted with its call and the initial `producer_verification` member; `_pssm(path,
  job)` imports the parser directly (no `package_files`/`module_root` path comparison); `_inputs` no longer skips
  input checks when verification failed; `_check_file(expected)` loses the `kind` parameter.
- Terminal custody: resource configuration `producer` is `{'module_root'}` (no `manifest`), plan/configuration
  manifest comparison deleted.
- Left untouched: the label `'attempt_output_version': 'original_producer_manifest_and_verified_file_digests'`
  (`R/native_blast_acquisition.py:24`, `R/native_hmmer_acquisition.py:23`), a vocabulary value that feeds credit
  keys; `producer_owned_environment:` (reserved environment names); BV-BRC `producer_manifest` (a provider data role).

## 13. NOT REMOVED in a101 — same decision needed in every arm (see fp1.md "left for decision")
- `R/native_driver_runtime.py` + `R/native_hmmer_preparation_result_publication.py:205-330`: the HMMER preparation
  worker runs from a copied source snapshot whose record (`driver_runtime`) pins every module (`implementation_files
  [{module, sha256}]`), the interpreter and every dependency file, re-verified in the worker
  (`verify_driver_runtime`) and on every re-observation (`result_worker_original_software_changed`).
- `R/library/retained_input_authority/*` worker intents and driver runtimes (`source_pins`, `implementation_files`,
  `driver_runtime`, `REQUIRED_MODULES`; 21 files) and their generic reader `R/terminal_scientific_evidence.py:233-262`:
  record formats whose job-side producer is the top-level package.
- `R/tests/fixtures/hmmer_native_weight_oracles/SOURCE_PINS.json` + `R/tests/test_hmmer_alignment_native_weight_
  oracle.py:101-111` (sha256 pins of Easel/HMMER C sources checked before compiling the oracle).

## Tests and fixtures
- Delete: tests of the inventory/manifest/pin itself (see `fp1_deleted_tests.tsv` for the list and the reason given
  for each); parametrized cases named `hash`, `implementation`, `manifest`, `package`, `runtime`, `shadow`.
- Keep and edit: tests that only carried the field (drop the key from constructed requests/records, drop the
  digest arguments of `*_calculation_identity`, replace the fixture's third return value `manifest` by the deployment
  directory `deploy` and pass `shadow=deploy` where a plan is saved outside the fixture directory).
- Content-addressed captured fixtures that contain `script_sha256` inside a retained transport record
  (`R/tests/fixtures/uniprot_*`) are data; they are not edited.
- A test of the arm that takes a record from a top-level fixture still carrying a removed field fails with the arm's
  strict field check. Met once in a101: `R/tests/test_homology_progress.py:22` imports `commission_spec` from
  `tests/test_durable_episode.py`, whose `runtime_binding` has `implementation_sha256`; 9 tests failed with
  `runtime binding fields must be exact`. Fixed inside the arm by projecting the fixture's binding to the arm's four
  fields in the test helper (`assigned_spec`), plus a handoff row for the fixture. Grep your arm's tests for
  `from test_durable_episode import`, `durable_fixture`, `detached_workflow_fixture`,
  `scientific_process_worker_fixture`.
- Orphan fixtures that carry a module digest and are read by no test are deleted
  (`R/tests/fixtures/blast_explicit_associations/legacy_prechange.json` in a101).

## Measured result in a101 (for your expected-duration table)
267 test files, 9,751 tests: 9,227 passed, 286 failed, 178 errors, 60 skipped; 1,080 test seconds, 23 minutes wall
for the per-file gate; per-file table `fp1_gate_results.tsv`. 0 tests fail that passed before. Section 13's first
item was left because its only test file had 25 errors and 1 failure of 29 before the task.

## 13a. Driver runtime pins — removed (fp2, applied in a102; `R2` = `.../root/a102`, "before" = commit `330ef3fe7`)
Decision: the worker may still run from a copied source snapshot (copy mechanism and paths stay); nothing content-derived
(sha256, size) of a source, interpreter or dependency file is recorded or compared any more. Names, paths and versions stay.
Edit script (perl, takes the arm directory): `<scratchpad>/fp2/m13a.pl`; a101's two files differ from a102's only in
`_source_closure` and import lines, so the same substitutions apply.
- Record `driver_runtime` (`R2/native_driver_runtime.py:44-48` before):
  `{python_executable, python_sha256, python_version, module_root, implementation_files: [{module, sha256}],
  dependencies: [{distribution, version, package_root, files: [{path, sha256, size_bytes}]}]}`
  after: `{python_executable, python_version, module_root, implementation_files: [{module}],
  dependencies: [{distribution, version, package_root, files: [{path}]}]}` (`_SHA`, `_INT`, `_PIN` deleted; `files[].path`
  stays because `_dependency_roots` derives `PYTHONPATH` from it).
- `stream_identity`, `file_identity` and `import hashlib` deleted (no other user).
- `verify_driver_runtime(driver)` (before `:169-190`) keeps what is not a digest: interpreter is `/proc/self/exe` and
  `python_version` matches; every listed module file exists under `module_root` (`require(path.is_file(), ...)` replaces
  the hash line, which was also what refused a missing file) and a loaded module comes from that path; each dependency
  has the recorded version and `package_root`; every loaded `site-packages` module is a listed path. Gone: interpreter
  sha256, per-module sha256, per-dependency-file sha256/size.
- `_copy_exact(source, destination)` -> `_copy_source(source, destination)`: `require(not destination.exists(), ...)`,
  then the same confined copy; no identity returned, no "existing identical copy is accepted" branch (the snapshot
  directory is always created fresh by its one caller).
- `_dependency_bindings`: rows `{"path": str(path)}`. `freeze_driver_runtime`: rows `{"module": name}`, no `python_sha256`.
- `R2/native_hmmer_preparation_result_publication.py`: `_runtime_files(driver)` (before `:214-230`) validates the record
  and compares the set of listed module paths with the files present under `module_root`
  (`result_worker_original_source_inventory_conflict`, names only) and returns; the loop that re-hashed interpreter,
  sources and dependency files and its code `result_worker_original_software_changed` are gone. `_worker_runtime` no
  longer re-measures the copy (`result_worker_original_source_size_conflict` gone; the recorded
  `source_copy_size_bytes` stays as the scratch footprint of the copy). `_collect_worker` no longer calls
  `_runtime_files` again after the worker ended. Unchanged: `_WORKER_PROGRAM` (still calls `verify_driver_runtime`),
  the selection/runtime record comparison (`canonical(retained["driver_runtime"]) != canonical(driver)`) and
  `runtime_sha256` (digest of a record).

## 13b. Software records with interpreter/module pins, and their generic reader — removed (fp2)
- Protein-structure `Software` record (`R2/native_protein_structure_contracts.py:59-70,289-292` before; in a101 the same
  record is `R/library/retained_input_authority/native_protein_structure_contracts.py`):
  `{python_executable, python_sha256, python_version, driver_module, worker_module, implementation_files: [{module,
  sha256}], numpy_version, biopython_version, implementation, algorithm}` -> the same without `python_sha256`, with
  `implementation_files: [{module}]`. `validate_protein_structure_software` is unchanged (module-name checks).
- Worker `check_selected_software` (`R2/native_protein_structure_worker.py:49-71` before): `_checksum` deleted; the
  observation has no `python_sha256` and lists `{module}` for every selected module that `importlib.util.find_spec`
  finds; compared names are `python_version, numpy_version, biopython_version` (was those plus `python_sha256` and
  `implementation_files`); the interpreter path comparison stays.
- Driver (`R2/native_protein_structure_driver.py:190-194` before): the interpreter is no longer read and hashed;
  `_require(os.access(job["software"]["python_executable"], os.X_OK), "software_identity_mismatch")` stays.
- Generic reader `R2/terminal_scientific_evidence.py:96-99,120-121,222-223,238-267` before: `_identified_file_values`
  loses the two branches that turned `python_executable`+`python_sha256` and `implementation_files[{module, sha256}]`
  into file pins (with `terminal_native_implementation_path_unavailable`), and with them the `module_roots` parameter
  of `_identified_file_values` / `_identified_files` and the two `PYTHONPATH` splits at the call sites. Values that
  carry `{path, sha256}` (data operands) are still collected and compared with the executor's snapshots.
- An arm that only reads these records (a101, a105: `library/retained_input_authority/*`) removes the field from its
  schema/validator in the same way; the producers are listed as handoff rows to `fp-top` (one row per producer file).
- The same rule covers the other records named in section 13 second bullet (`source_pins`, `REQUIRED_MODULES`,
  worker intents): field, schema entry and comparison go; a field that names a module or path stays.

## 14. Code manifest of a staged HPC worker (first met in a102)
Files: `R2/a102_hpc.py`, `R2/a102_hpc_worker.py`, `R2/hpc_scientific_commission.py`. The request carried
`code_manifest {relative path: sha256}`, `code_manifest_sha256`, `source_snapshot_sha256`; the body `worker_sha256`,
`code_manifest_sha256`; the worker re-hashed its own file and every snapshot member and echoed two digests in its
result; admission compared them and the commission's acceptance predicates required them.
After: the staged files (`a102-sources.json`, `a102-worker.py`) are unchanged; request =
`{version, algorithm, software_pin, native_request}`; body has no `worker_sha256`/`code_manifest_sha256`; the worker
writes every member of the snapshot (path confinement check kept) and its result has `request_sha256` only; acceptance
predicates are `version, program, completed, returncode, request_sha256`; `execution_profile.implementation` (timing
class key) is the worker version string (`NATIVE_VERSION`; in `hpc_scientific_commission.commission` the `version`
argument, whose parameters `worker_sha256` and `implementation_sha256` are gone); `execution_provenance` has no
`code_manifest_sha256`. Kept: `software_pin.archive_sha256` (integrity of a downloaded third-party archive) and the
comparison of the plan's staged-file digests with the request body's files (transfer record of staged data).

## 15. Smaller a102 shapes
- `hpc_work_planning/**/binding_record.py` (6 files): the `sources`/`hashes` roster and `hpc_queue.digest(hashes)` go
  with `implementation_sha256`; `from pathlib import Path`, `import hashlib`, the `hpc_queue` import go too.
- `scientific_process/episode.py` builds its own record (no `binding_record.py`): same shape as section 1.
- `episode_composition._PRIVATE_RECONSTRUCTION` rows were `(version, required, optional, fingerprinted)`: the fourth
  member and the `if fingerprinted:` field/shape checks are gone; every descriptor is exactly
  `{binding_id, version, configuration}`.
- `a102_resources.as_record()` loses `implementation_sha256` (hash of its own file).
- `literature_experimental_prompt._PRIVATE` no longer lists `implementation_sha256`.
- Not removed, same in every arm (see fp2.md "left for decision"): `ALIMASK_PROFILE_EXECUTABLE_SHA256` and
  `ALIMASK_PROFILE["source_sha256s"]` (`hmmer_alignment_preparation_data.py`): the executable digest selects the
  numerical weighting profile used to grade alimask results.

## 16. Shared checks in `root/tests/` that the arms' test files subclass (fp2)
The per-home test files of an arm import behaviour classes from `gene_annotation_episode/episodic_workflow/root/tests/`
(not yours to edit; handoff rows to `fp-top` exist, written by fp2):
- `hpc_prediction_behavior.py:177` asserts `len(record['implementation_sha256']) == 64`: two tests per arm fail with
  `KeyError` once the hpc binding records lose the field, until that line is deleted.
- Arm-owned doubles (`object.__new__(runtime.Workflow)`, `SimpleNamespace(...)` in the arm's own `*_checks.py`) are
  yours: give them the attributes `Workflow.__init__` always sets instead of keeping a tolerant read in product code.

## Measured result in a102 (fp2)
92 test files, 4,940 tests before and after (none deleted): 4,902 passed, 27 failed, 0 errors, 11 skipped; 304 test
seconds (1,123 before; the drop is concentrated in the five large files that call binding `as_record()` often —
not profiled, the removed per-call source-tree hashing is the likely cause), about 5 minutes wall for the per-file gate (00:22:31-00:27:31); per-file table `fp2_gate_results.tsv`. 22 tests fail that passed before, all in files that
subclass the shared checks above (2 from the digest assert, 20 from shared fixtures that open a journal without the
completion ledger — the second group belongs to the suspects part of the fp2 task, not to the fingerprint removal).

## 13a/13b (fp3) — the same two decisions in a103, and one family only a103 has as product code
`R3` = `.../root/a103`; "before" = commit `4a3aba851`. Scripts: `<scratchpad>/fp3/m13_go.pl` (perl, asserted).
- `R3/native_driver_runtime.py`, `R3/native_hmmer_preparation_result_publication.py`,
  `R3/terminal_scientific_evidence.py`: three-way merge from a102 (base `330ef3fe7`) is clean; result = 13a/13b above.
- A second user of `native_driver_runtime` exists in a103: `R3/genomic_overlap_worker_runtime.py` (before `:11,
  :28-77,:92`). It imported `file_identity` and had its own `file_pin` (sha256 + size with a stability check) plus the
  helpers only `file_pin` used (`path_value`, `_directory_fd`, `regular`, `_stable`). All deleted; `_dependencies()`
  rows are `{"path": ...}` (the `_DRIVER.dependencies` schema of 13a).
- Genomic-overlap result worker intent / execution record (`R3/native_genomic_overlap_preparation.py`, reader
  `R3/genomic_overlap_result_receipts.py:675-705` before). Before: `source_pins: [{path, sha256, size_bytes}]`,
  `interpreter: {path, sha256, size_bytes}`, optional `dependencies: [{…, files: [{path, sha256, size_bytes}]}]`.
  After: `source_pins: [{path}]`, `interpreter: {path}`, `dependencies` required with `files: [{path}]` (the field
  names stay: they name what ran; record `version` strings untouched).
  - `_stage(source, target, policy, directory, *, executable=False)` copies the module file or the interpreter
    straight into a private read-only inode (was: capture into the Store as `python_source` / `python_interpreter`,
    then copy from the Store and compare sha256/size). An already existing target is refused
    (`genomic_overlap_preparation_snapshot_conflict`): the "identical existing copy is accepted" branch needed the
    digest. Consequence: a preparation interrupted while staging is not resumed in the same directory.
  - `_snapshot(plan, policy)` / `_verify_snapshot(plan, intent)` lose the `store` argument; `_verify_snapshot` keeps
    the path/shape checks (`_pins`) and the read-only-mode check of every staged file; the re-hash of sources and
    interpreter and the per-dependency-file `file_pin` comparison (`genomic_overlap_preparation_dependency_conflict`,
    code gone) are deleted.
  - `_pins` and the receipts reader accept rows that are exactly `{path}`.
  - Not part of the pin but in the same lines and without a producer (`_snapshot` always writes `dependencies`): the
    "legacy" intent/execution without `dependencies` (`_execution_fields`, `NotRequired`, the `else` arm of
    `_checked_environment`, `dependencies=None` in `_environment`) is removed; `WorkerExecution.__annotations__` is
    the one field set. The shared-root copy `root/library/native_genomic_overlap_preparation.py` already had this.
  - `GENOMIC_OVERLAP_DEPENDENCIES_SHA256` (digest of the dependency record put into the worker environment) stays:
    a record digest.
- Genomic-overlap driver software binding (`R3/native_genomic_overlap_contracts.py:42-66,267-274,830` before,
  `R3/native_genomic_overlap_driver.py:270-286` before) = 13b shape: `SoftwareBinding` without `python_sha256`,
  `ImplementationFile` = `{module}`, `software_verification.python_observed` = `{version}`; the driver no longer
  hashes the interpreter or the listed modules, a listed module file that does not exist raises
  `software_identity_mismatch` (reported at `/software` like the previous unreadable-file case); the module-name
  roster check `_REQUIRED_MODULES` (names, no digests) and `bedtools_sha256` (configured external executable, observed
  at run time) stay.

## 17. a103-only shapes (fp3)
- Root and improvement parent records (`R3/episode.py:50-56`, `R3/legacy_improvement/episode.py:50-56` before):
  `as_record()` hashed a roster of its own files; the roster module `R3/implementation.py`
  (`ANNOTATION_IMPLEMENTATION_MEMBERS`, `annotation_implementation_files`) is deleted, the record keeps `version,
  binding_id, role, owner_class, task_class`.
- Homology binding records (`R3/homology_*/binding_record.py`, `R3/legacy_improvement/homology_*/binding_record.py`,
  6 files): `'implementation_sha256': sha256(_binding_source_bytes()).hexdigest()` out of the record,
  `from hashlib import sha256` and the helper import out of the import lines; the helper at the end of the six
  `contracts.py` hubs goes like section 2.
- `R3/a103_resource_implementation.py` (roster of the two parent homes and six homology children): deleted.
- `R3/bvbrc_comparative_systems_bundle_adapter.py`, `R3/bvbrc_genome_alignment_bundle_adapter.py`: section 6 shape
  (roster + `implementation_sha256()` + `__all__` entry + now-unused `hashlib`/`Path` imports).
  `R3/bvbrc_comparative_systems_host_inputs.py:121-122`: `binding[1] == inputs['adapter_implementation_sha256']`
  becomes `_require(publications._adapter(context, selected) is not None, 'adapter_pin_conflict')` (the selected
  adapter must be bound; `_adapter` returns the module since section 6).
- `R3/a103_hpc.py`, `R3/a103_hpc_worker.py`: section 14 shape (request = `{version, scientific_profile,
  biopython_version, plan, assets}`; no `code_manifest*`, `source_snapshot_sha256`, `worker_sha256`).
- Kept, same reasoning as the owner's decision on `ALIMASK_PROFILE_EXECUTABLE_SHA256`:
  `R3/bvbrc_genome_alignment_inputs.py:36,659` `_P3_SOURCE_SHA256` — a constant digest of one inspected version of the
  provider's (BV-BRC) application source, compared with a supplied `producer_source` content binding. A match is what
  admits the "retained source default" recipe (`progressiveMauve`) when no command was observed; removing or
  loosening it changes which invocation is inferred for grading. The same constant is in
  `root/library/bvbrc_genome_alignment_inputs.py:36`.
- `R3/resource_reconstruction.py:21-25` `RESOURCE_RECONSTRUCTION` is a second saved-descriptor table merged into
  `episode_composition._PRIVATE_RECONSTRUCTION`; its rows also lose the fourth (`fingerprinted`) member. Missing it
  gives `ValueError: too many values to unpack` in 40 tests of `tests/test_private_resource_tasks.py`.
- Speed, for your expected-duration table: the 98 a103 test files took 890 test seconds before and about 220 after;
  `tests/test_private_resource_tasks.py` alone 510 s -> 30 s (every `as_record()` used to read every source file).

## 18. Suspects settled in a103 (fp3; "older/absent form" branches, traced to a current producer or removed)
- Removed, no current producer: `homology_results.recorded_coverage` / `_native_complete` defaults for a snapshot
  without `parse_inventory`, `publication_witness_version`, `native_termination_seen` (the one writer always writes
  them); `HomologyResults._grading` returning `None` for a worker row with neither `grading_file` nor
  `grading_failure` (`phmmer_result_worker.py:153-163` always writes one), with the dependent
  `phmmer_shared_grading_unavailable` code and its reader; `component_assessment_dependencies.
  qualification_assessment_changes` + `correction_refs` (no caller and no producer of its input in a103; a101 has
  neither function); `decision_history` table probing and `composition_information.restricted_root` default (a102
  shapes, fp2.md); the a103 twin of a102's `pending_work` suspect (`runtime.py:516-520`: 75 directories save a
  decision, the same 75 add `pending_work`).
- Kept, live: `library/hpc_prediction.py:150-151` (a commission without `resource_priors` is an accepted
  configuration and `hpc_work_planning/forecast_observations.py:37` adds measured resource metrics to every
  observation); `api_bvbrc_minhash.py:145-155` (the empty selector is one of the two forms of the published result
  selector schema, `bvbrc_minhash_contracts.py:65-79,166-170`); `provider_jobs.py:21-34` (the HMMER request written
  by `api_execution.py:228-236` has no `provider` key, and the identity-version comparison refuses, it does not
  admit); `bvbrc_genome_alignment_inputs.py:405-411` ("older" means an earlier stdout snapshot of the same task);
  `api_service_execution.py:585,810` `historical_uniprot` (callers `uniprot_returns.py:471,685` pass
  `verify_artifacts=False`); `practical_execution_records.py:26` (`practical.job.*` are the current local-job
  operations, `practical_execution_operations.py:442-443,741-742,839`).

## 17. Registered source-path rosters of information readers (first met in a107, fp4)
Files: `R/library/execution_initial_information/information_sources.py`,
`R/library/received_execution_information/received_reader_sources.py` (each a `SOURCE_PATHS` tuple of ~2,000
repository paths, extended by several `SOURCE_PATHS += (...)` blocks, plus `implementation_record()` returning
`{version, sources: [{path, sha256}]}`), consumers `factory_readers.py`, `information_readers.py`,
`received_configuration.py`.
- Both roster modules deleted.
- `FactoryInformationReaders` (dataclass) loses the `implementation_record` field; `validate_original_setup` loses the
  record shape check and the loop that re-hashed every listed file (`initial_information_reader_implementation_changed`,
  `initial_information_reader_source_custody_required`); `as_record` loses `implementation`;
  `construct_factory_information_readers` no longer passes it; `import hashlib` gone.
- `ReceivedExecutionSetup` loses `source_record`; `_record()` loses `implementation`; `check()` compares only
  `self._record() != self.reader_record` (configuration/ports record, kept).

## 18. Staged HPC workers in a107 (variant of 14)
`a103_hpc.py`/`a103_hpc_worker.py`, `component_axis_native_hpc.py`/`component_axis_native_worker.py` (also used by
`a107_genomic_detection_hpc.py`): same shape as 14; in addition the `logical_work_sha256` inputs drop the manifest
(`'code': manifest`, `'implementation': manifest`), so equal scientific work has one logical identity regardless of code.

## 19. Worker-intent pins with resumable staging (fp4, a107; coordinator rule of 16 November)
Preparation modules that copy the worker source closure, the interpreter, dependency files and stdlib files into an
attempt directory record each copy as `{path}` only. There is no `sha256`/`size_bytes` and no `_verify_pins`.
- **Existing destination.** Read the source and the existing file and require equal bytes and a read-only mode;
  otherwise copy. Do not refuse every existing file: that would break resuming an interrupted preparation, and
  fp3's a103 `_stage` should be revisited for this. Size budgets use `Path(...).stat().st_size`.
- **Validators.** Intent validators and the retained-receipt validators close pins to `('path',)`; module/path name
  lists (`REQUIRED_MODULES`, required worker source paths) stay.
- **Software records.** Software records of the same families (FBA `FBASoftware`, NMF `expression_nmf_software_v1`)
  use a path-only file record. Data file pins (model input, captured outputs) keep `sha256`/`size_bytes`.

## 19. a104-only shapes (fp5; `R4` = `.../root/a104`, "before" = commit `49dee49e6`)
Scripts: `<scratchpad>/fp5/m1.pl` (helpers), `m2.pl` (binding records), `m6.pl` (adapter pin in the split publication
form); the rest are one-off asserted perl substitutions listed in fp5.md.
- Literature binding records (`R4/published_evidence_assessment/**/binding_record.py` and the `scientific_process/`
  mirror, 14 files): `as_record()` built `implementation = implementation_bytes(self.binding_path)` from the roster
  module `R4/library/source_descriptor_inputs.py` (`SOURCE_FILES[binding_path]` + seven shared-root files) and appended
  the JSON of the controlled-response and gel descriptors before hashing. The two `implementation +=` lines, the import
  and the field go; the descriptors stay in `configuration`. The import line becomes `from .contracts import VERSION,
  deepcopy`. `library/source_descriptor_inputs.py` and the roster-owner module `R4/literature_implementation_sources.py`
  (only imported by the 14 literature hubs for `_AXIS_DIRECTORY = Path(_literature_source_owner.__file__)...`) are
  deleted; the hubs lose that import, the constant, `import hashlib` and `from pathlib import Path`.
- `R4/scientific_process/saved_scientific_state.py::restore_closed_process` (the a104 name of recipe 3's
  `process_state.py`): `saved_hash`, its shape check (code `scientific_closed_implementation_identity_invalid`) and the
  re-insertion of the saved digest into the candidate are gone; the check is `saved_binding != current or
  filled['mechanics_binding'] != current` -> `scientific_filled_identity_mismatch`.
- BV-BRC adapters, a104 layout: `R4/bvbrc_phylogeny_bundle_projection.py` owned `_DEPENDENCIES` +
  `implementation_sha256()` re-exported by `bvbrc_gene_tree_bundle_adapter.py` / `bvbrc_codon_tree_bundle_adapter.py`
  (import and `__all__` entry go); `library/bvbrc_proteome_bundle_adapter{,_v2}.py` as recipe 6. The publication code is
  split into `library/appservice_publication_records.py` (`_validate_inputs` configuration check, read-side
  `adapter_implementation_sha256 is not None` -> `inputs['adapter'] is not None`, `result_identity`) and 12 identical
  `**/appservice_publication.py` (`publication_inputs` no longer calls `_adapter`; `_grade` is a102's shape).
  `library/bvbrc_proteome_returns.py`: the `original_adapter_pin_required` check and the `implementation_sha256` member
  of the configured-row comparison go (code `original_adapter_pin_conflict` stays). Test fixture
  `tests/proteome_partner/proteome_host_fixture.py:51` configures `{adapter_id, adapter_version}`.
- Molecular worker execution selection (`R4/a104_native_worker.py`, record `ordinary_molecular_execution_v1`, read by
  `protein_conservation_tools.py` / `protein_phylogeny_tools.py` by field names only): `python` is `{path}`,
  `implementation_files` rows are `{path}` (source closure + selected distributions' files, names/paths kept);
  `verify_unstarted_software` requires every listed file to exist, code renamed
  `molecular_tool_original_software_unavailable_before_dispatch` (was `..._changed_before_dispatch`).
- `R4/a104_hpc.py` / `a104_hpc_worker.py` (section 14 variant without a code manifest): body loses `worker_sha256`
  (the staged `worker_text` stays), `execution_profile.implementation` is `NATIVE_VERSION`, acceptance predicates lose
  `worker_sha256`, the worker result loses `worker_sha256`, admission no longer compares it. The plan's staged-file
  check compares `files['a104-worker.py']['sha256']` with `sha(expected['worker_text'].encode())` (transfer record of
  staged data, as in a102/a103). Test `tests/test_a104_evolutionary_episode.py:80` expects the native request version.
  The captured real result `tests/fixtures/a104/real/mj0044/native-pbs-9040517.json` still carries `worker_sha256`:
  data, not edited.
- Fluorescence records read by a104 (`R4/library/native_fluorescence_contracts.py`, `native_fluorescence_preparation.py`,
  `fluorescence_native_report_contracts.py`): 13b for `fluorescence_software_v1` (`PIN_SCHEMA` and `_pin` are `{path}`
  for `python`, `implementation_files`, `runtime_files`); 13a for the worker intent (`_pin` is `{path}` for
  `source_pins`, `interpreter`, `runtime_files`, dependency files); recipe 11 for `PROFILE_SOURCES` (operation only).
- `R4/native_driver_runtime.py::_copy_source` (owner decision, replaces 13a's "refuse an existing copy"): an existing
  destination is accepted when its bytes equal the source bytes and it is read-only, otherwise refused; a missing one is
  copied. No digest is computed.
- `R4/**/execution_result_acquisition/native_blast_{,standard_}database_result_acquisition.py` (12 files, the a104 name
  of recipe 7's results modules) no longer collect `implementation-receipt.json`.
- `R4/tests/execution_input_version_probe.py` (diagnostic helper): `helper_sha256` and per-case `source_sha256` (digests
  of its own and each owner module's source) out of the report.
- Kept: `R4/literature_experimental_prompt.py:95` `_TRACKING` still lists `implementation_sha256` (a presentation filter
  for a field name `ExecutionClass` records still carry); `literature_{controlled_response,gel}_storage.
  implementation_descriptor` (`native_schema_sha256` is a digest of a cells schema, a data contract);
  `implementation_dependencies` of the controlled-response extraction (contract version strings, no digests).
- Speed, for your expected-duration table: the 87 a104 test files took 415 test seconds before and 152 after
  (`scientific_process/tests/test_head_task.py` 226 s -> 6 s); 3.5 minutes wall for the per-file gate.

## 19. Shared-root shapes (fpr, `root/` outside the arms; "before" = commit `9fc7d3e54`)
Edit scripts: `<scratchpad>/fpr/m1.pl` … `m14.pl`, `s1.pl`, `t1.pl`–`t3.pl` (each substitution asserted).
- `*/binding_identity.py` (24 homes: `execution_monitoring`, `homology_*`, `hpc_coordination/**`, and their
  `legacy_annotation/` and `scientific_process/` copies): the `root`/`paths`/`hashes` roster lines and the
  `'implementation_sha256'` member go; `hashlib`, `Path` and the `canonical` import go with them.
- Literature aggregate record (`published_evidence_assessment/record_algorithm.py`, `aggregate_records.py`, 3 copies):
  every `implementation += descriptor_operand_bytes(...)` statement and `for name in (...)` loop, the two
  `implementation += json.dumps(descriptor)` statements and any `if` left empty go; the record is
  `{version, binding_id, configuration}`. `aggregate_definition_bytes`, `descriptor_operand_bytes`, `_REPOSITORY` and the
  roster module `definition_inputs.py` (`DEFINITION_FILES`, `DESCRIPTOR_OPERANDS`) are deleted.
- `scientific_process/binding_record.py` + `scientific_process/definition_inputs.py` (deleted): same as section 1.
  `scientific_process/saved_identity.restore_closed_process` compares `saved['mechanics_binding']` and the filled
  binding with `self.as_record()` directly (the a102 `saved_scientific_state.py` shape); the code
  `scientific_closed_implementation_identity_invalid` is gone.
- `library/resource_binding_records.py`: the four rosters and `implementation_fingerprint` deleted;
  `resource_binding_catalogue.saved_family` expects `{binding_id, version, configuration}` (code
  `resource_saved_implementation_required` gone).
- Saved binding catalogues (`saved_private_binding_catalogue.catalogue_source_record`,
  `terminal_binding_catalogue.source_record`): the whole-tree `.py` stream (`sources`, `implementation_sha256`,
  `source_identity_kind`, the "required files exist" roster check) goes; the source record keeps version, owner and the
  literal constructor names. The a105 descriptor field set in `_rows` is `{version, binding_id, configuration}`.
- `commissioned_reopening.implementation_sha256()` (whole-tree stream) deleted with the runtime-binding field
  (section 4 shape).
- Declared tool-source profiles (constants standing for third-party Biomni source): `SOURCE_METHOD` /
  `source_profile` / `PROFILE_SOURCES` keep `callable`/`operation` and the descriptive members, lose
  `module_sha256`, `callable_sha256`, `source_file_sha256`, `source_function_sha256`, `function_sha256`
  (`circular_dichroism_measurements`, `protease_kinetics_measurements`, `glycosylation_measurements`,
  `protein_disorder_measurements` + `_result_contracts` const + `_received_values` projection,
  `fluorescence_native_report_contracts`).
- `library/molecular_sequence_native.py`: the four source constants, the per-operation `"sha256"` and
  `_SOURCE_PROFILES[...]["sha256"]` go; `_deployment(value, *, version)` no longer compares the configured module pin
  with a constant (`original_source_pin_required` gone; the configured deployment file pins and their byte checks
  stay, like configured executables); the loaded callable is still checked by name, module and code file, but its
  source is no longer hashed (`inspect.getsource` digest out of `observed_callable` and `source_identity`). Readers:
  `protease_kinetics_measurements` (`source_identity` is `{path, callable}`), `orf_measurements`,
  `primer_placement_measurements` (no sha256 condition).
- Calculator control records (`vcf_result_tools.py`, `reference_edit_outcome_tools.py`): `implementation`
  (sha256+size of the tool's own two files) out of the record, `_CONTROL_KEYS` and the reader check
  (`implementation_conflict`).
- Component worker (`library/component_native_request_service.py`, `component_native_worker.py`): section 14 / 18
  shape (`code_manifest*`, `source_snapshot_sha256`, `worker_sha256` gone; `'code': manifest` out of
  `logical_work_sha256`); `commission()` is called without `worker_sha256`/`implementation_sha256` (top-level
  function: handoff).
- ESM worker selection (`library/esm_gene_embedding_tools.py`): after 13a the driver gives `{path}` rows;
  `esm_worker_implementation_files` returns `{path}` for driver modules/dependency files (deduplicated by path) plus
  the `{path, sha256}` checkpoint pins (data), and `_worker_control` compares `selected["python"]` with `{path}`.
- `rna_structure_comparison_calculations._RECOGNIZED_SOFTWARE` loses the hard-coded `worker_source_sha256`
  (it gated `software_generation_unverified` on the worker's own source); `rna_module_sha256` /
  `rna_extension_sha256` (installed ViennaRNA) and the observed `python_sha256` stay.
- BV-BRC: the shared root has no `bind_adapters`; the top-level `gene_annotation_episode/bvbrc_appservice_adapters.py`
  binds the shared-root adapters and the top-level `bvbrc_appservice_schemas.json` validates `PublicationInputs`, so
  the shared-root side of section 6 only works together with the top-level side (verification-only plugin
  `<scratchpad>/fpr/plugin/fpr_toplevel_adapter_plugin.py` emulates it: also `bvbrc_appservice_preparation.py:41-44`
  unpacks the tuple). `_bundle_content_kind` now decides on the selected adapter only (was "digest is not None").
- Kept by analogy with the alimask decision (as fp3): `library/bvbrc_genome_alignment_inputs.py:36,659`
  `_P3_SOURCE_SHA256`.
- Shared test helpers (section 16) fixed here: `CompletionLedger(store, journal)` after each `Journal(...)` in
  `hpc_launch_task_checks.py`, `hpc_planning_allocation_task_behavior.py`, `hpc_prediction_prompt_behavior.py`;
  digest assert out of `hpc_prediction_behavior.py`.

## 20. a105-only shapes (fp6; `R5` = `.../root/a105`, "before" = commit `06214e132`)
- Literature binding records (`R5/published_evidence_assessment/**/binding_record.py` and the `scientific_process/` mirror,
  14 files): `as_record()` interleaved `implementation += _implementation_path(name).read_bytes()` lines and
  `for name in (...)` loops (plus the JSON of `required_runtime_asset_fingerprints()` and of the controlled-response/gel
  descriptors) with the `configuration[...]` lines inside the same `if self.<population>:` blocks. Remove every
  `implementation (+)= ` line, then every `for`/`if` header left without a body (repeat until stable), then the field;
  the import becomes `import VERSION, deepcopy`. Three `if self.rate_population:` blocks become one.
- Hubs (`**/source_contracts.py`, 14): `_implementation_path` (two variants: `_AXIS_DIRECTORY` lookup, or
  `from .implementation_sources import source_file`), `_AXIS_DIRECTORY`, `_binding_source_bytes`, `import hashlib`,
  `from pathlib import Path` deleted. Roster modules deleted: `R5/implementation_sources.py` (`independent_source_files`,
  `scientific_source_files`), `R5/runtime_assets.py` (`required_runtime_asset_fingerprints`, only fed the digests) and
  `.../source_evidence_examination/implementation_sources.py` (`LOCAL_IMPLEMENTATIONS`, `source_file`).
- `R5/scientific_process/invocation_state.restore_closed_process`: a104's `saved_scientific_state` shape.
- Biomni protease tool-source pins (`R5/molecular_sequence_native.py`, `protease_kinetics_measurements.py`,
  `protease_kinetics_tools.py`, `molecular_measurement_tools.py`): constants `BIOCHEMISTRY_SOURCE_SHA256`,
  `PROTEASE_FUNCTION_SHA256`, `SOURCE_FILE_SHA256`, `SOURCE_FUNCTION_SHA256`, the `source_sha256=` parameter of
  `_deployment` with `original_source_pin_required`, the `inspect.getsource` digest of the called function
  (`observed_callable` without `sha256`), `native_record.source_identity` = `{path, callable}`, `SOURCE_METHOD` without
  the two digests. Kept (as a107): the deployment record's file pins and its `software_files` manifest.
- Ordinary molecular worker selection (`ordinary_molecular_execution_v1`, `R5/molecular_measurement_tools.py`): a104 shape
  (python `{path}`, implementation_files `[{path}]`, existence check
  `molecular_tool_original_software_unavailable_before_dispatch`); for the protease deployment the rows are the
  `{path}` projection of the deployment manifest and the repository-closure check compares paths only.
- ITC in-process software observation (`R5/itc_binding_fit.py._file`, `R5/itc_binding_contracts.py`): file rows `{path}`.
- `library/retained_input_authority/*` (same paths as a101): fp1's recipe 5/11 merges apply cleanly; 13a/13b/19 readers
  equal a101's after Checkpoint 14 (fpf) apart from layout.
- Perl pitfall met here: in an asserted helper `r($re, $to, $n)` the replacement string is built before the match, so
  `"$1..."` interpolates a stale capture and silently corrupts the line. Use literal replacements, or `s///e`.

## 21. a106-only shapes (fp7; `R6` = `.../root/a106`, "before" = commit `d2f371805`)
Scripts: `<scratchpad>/fp7/m1.pl` (binding records, hubs, progress records, `process_state`), `m2.pl` (acquisition),
`m3.pl` (BV-BRC intervention adapter, analysis contract, dead hub helpers); all substitutions literal and asserted.
- Literature binding records (`R6/published_evidence_assessment/**/binding_record.py` and the `scientific_process/` mirror,
  14 files): `as_record()` hashed every `.py`/`.json` file under the arm directory (`_AXIS_DIRECTORY.rglob('*')`, tests
  skipped) plus the four `_context_source_key` package files into one `hashlib.sha256()` object. The whole 13-line block
  (local `Path as _context_source_path` import through the last `digest.update`) and `'implementation_sha256':
  digest.hexdigest()` go; the import becomes `from .source_contracts import VERSION, deepcopy`. Note `parents[10]` in the
  deepest homes: match `parents\[\d+\]`, not `\d`.
- Hubs (`**/source_contracts.py`, 14): `import hashlib`, `from pathlib import Path`, `_AXIS_DIRECTORY`, `_binding_source_bytes`
  deleted (nothing else in the hub or its importers used them). The six `published_evidence_assessment/**/execution_*/
  execution_contracts.py` copies lose only the trailing `from pathlib import Path` / `_AXIS_DIRECTORY` / helper lines; the
  first `Path` import stays because `configuration.py` imports `Path` from the hub.
- `R6/scientific_process/process_state.py::restore_closed_process` (a106 name of recipe 3's `process_state.py`): a104 shape.
- `R6/literature_implementation_sources.py` (roster of the literature binding/library files): its only importer was an
  unused `source_file` import in `library/literature_assay_grading_storage.py`; import and module deleted (no grader logic
  touched).
- BV-BRC TnSeq/RNASeq adapter (`R6/bvbrc_intervention_bundle_adapter.py`): `_DEPENDENCIES` roster, `implementation_sha256()`,
  `hashlib`/`Path` imports deleted; the re-export line `implementation_sha256 = intervention.implementation_sha256` out of
  `bvbrc_tnseq_bundle_adapter.py` / `bvbrc_rnaseq_bundle_adapter.py`. Consumers:
  - analysis contract `prepare_analysis_contract` (`library/standalone_intervention_execution.py` and 14
    `**/source_operations.py`): `implementation, digest = selected` -> `implementation = selected`; the returned contract
    loses `adapter_implementation_sha256` (no schema validates it).
  - `library/bvbrc_application_facts.project_application_facts`: the `pin = inputs.get(...)` / `original_adapter_pin_required`
    lines go (recipe 6 `*_returns.py` shape).
  - `bvbrc_appservice_publication._bundle_content_kind`: decides on the selected adapter only (shared-root shape, fpr).
  - `bvbrc_appservice_contracts.py` relation check `publication_adapter_binding_conflict` (one-line a106 form) deleted.
  - Test fixture `tests/intervention_analysis_fixtures.py:55` builds `publication_inputs` without the digest.

## 22. a108/a110-only shapes (fp8; "before" = commit `e8bf4820f`)
Scripts: `<scratchpad>/fp8/m1.pl` (a108 literature records + hubs), `m2.pl` (acquisition, multi-line layout; same in
a108 and a110), `m3.pl` (a110 BV-BRC adapters), `m4*.pl` (a110 BLAST database values), `m5*.pl` (a110 producer manifest,
reader side), `m6.pl` (a110 FBA source-function pin), `m7*.pl` (a110 ATAC runtime + HMMER publication); `resolve.pl`
resolves binding-record conflicts to "ours minus roster lines" and was cross-checked equal to "theirs" on all 30 files.
- a108 roster modules feeding the literature digests: `R8/receiving_context_sources.py`, `shared_infrastructure_sources.py`,
  `runtime_assets.py` (`*_source_bytes`, `*_fingerprints`, `binding_runtime_asset_bytes`). Binding records lose the three
  imports and the `implementation = ...` line; `independent_execution` loses `receiving_context_source_paths`; modules deleted.
- a110 adapter source epochs: `library/received_execution_dependencies/adapter_source_identity.py` + `.json` (a table of
  pinned reader digests per adapter owner, `current_implementation_sha256`, `authenticate_adapter_source`). Every
  `*_bundle_adapter.implementation_sha256()` called it. Removed with recipe 6 (adapters, `bind_adapters` binds the module,
  `api_bvbrc_appservice.result_catalog` uses it directly, publication reader decides on `inputs['adapter']`).
- a110 is an FBA producer arm: `a110_fba_native.py`, `flux_balance_{ordinary,request_binding}.py` stop writing
  `source_function_sha256`; `flux_balance_result_worker` stops expecting it in the manifest; `flux_balance_model_execution.
  _verify_selected_software` requires each listed software file to exist (no re-hash); `flux_balance_worker_staging.
  _copy_exact` byte-compares an existing read-only copy and returns `{path}`, `_dependencies` rows are `{path}`,
  `stream_identity`/`file_identity` deleted; `a110_fba_hpc.freeze` keeps the "deployment lists the module file" check
  without the digest and sends no code manifest (recipe 18). Its 20 GiB `features.memory_bytes` is an HPC request (kept).
- a110 reader copies of the native BLAST database records (one-line layout): request schema loses `implementation`,
  manifest fields and the `request['implementation']['manifest_sha256']` clause go, `*_calculation_identity(*,
  input_identity, sequence_model[, vdb_function_model])` (the vdb form also loses `calculator_implementation_identity`);
  recipe 12 on the reader contracts (artifact loop dedented, one owner per artifact) and `native_database_terminal_custody`.
- Perl pitfalls (new): a replacement held in a variable (`s/$re/$to/` with `$to = '$1]'`) inserts a literal `$1`;
  an index-based `r($from, $to)` with `$from eq $to` never terminates. Grep changed files for `\$1` afterwards.
