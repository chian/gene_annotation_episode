# fp6 — a105: code that fingerprints the codebase removed (16 November 2026)

Area: `gene_annotation_episode/episodic_workflow/root/a105/` (`R/` below). Brief: `FP_BRIEF.md`. Shapes: `fp_recipe.md`
(sections 1-19 followed; a105 additions appended as section 20). Deleted tests: `fp6_deleted_tests.tsv` (none). Per-file
gate table: `fp6_gate_results.tsv`. Comparison base: commit `06214e132` (HEAD when the task started). Checkpoint 14
(`933d65ad4`) was committed underneath the task and already contains part of this work, so `git diff HEAD` does not show
the whole change. No git add/commit, no sub-agents, one launcher command at a time (slot `fp6`).

## Outcome
Every a105 row of `h5_self_hashing.tsv` (116) and `pa105_self_hashing.txt` is handled. Removed: binding digests,
literature hub helpers and roster modules, the runtime-binding digest, the vendored-estimator pin, the acquisition
observer/transport digests, the tool-source pins (FBA source function, protein disorder, fluorescence report profiles,
RNA worker source, Biomni protease file/function), the BV-BRC adapter pin (schema and relation check), and
13a/13b/19 pins in the `library/retained_input_authority` readers. Also removed: the ordinary molecular worker-selection
pins and the ITC software-observation file digests.
The three sibling suspects were carried over with a105 producer evidence. Nothing is left for decision. One family is
kept on purpose (the protease deployment manifest, see "Kept"). The A105 grading rules in AGENTS.md are untouched:
no grader, subscoring sheet, `investigation_finding`, credit or iterator code was edited.

Change against `06214e132`: 73 files (70 modified, 3 deleted), +125 −1,208 lines. No test or fixture edited or deleted.

How it was done:
- Three-way merges (`git merge-file`, arm name replaced) for the 42 a105 files that have the same relative path as a
  file changed by a104 (`49dee49e6→06214e132`), a107 (`9fc7d3e54→6737ddfe8`) or a102 (`330ef3fe7→9fc7d3e54`). For each
  file I used the sibling whose pre-task version is closest to a105's.
  - 7 merged clean and were taken after reading each diff: `application_execution_binding.py`,
    `composition_information.py`, `decision_history.py`, `method_loop/durable.py`, `numerical.py`,
    `vendor/SOURCE.nano-graphrag.json` (all from a102) and `runtime.py` (from a107).
  - 4 had small conflicts and were resolved by hand: `independent_execution.py` (took the removal),
    `ordinary_execution.py` (kept a105's version without a102's alignment class), `episode_composition.py` (a105
    one-line form) and `component_assessment_dependencies.py` (only a docstring conflict; nothing to do).
  - The 28 literature binding records and hubs, `scientific_process/binding_record.py`, `episode.py` and
    `acquisition.py` differ in shape from every sibling. I edited them with asserted perl (`<scratchpad>/fp6/m1.pl`
    for the hubs, `m2.pl` for the binding records, and one-off `r()` substitutions).
- `library/retained_input_authority/`:
  - 8 files are byte-identical (after the rename) to a101's pre-fp1 files. They were merged clean from fp1
    (`2ad8be3de→f4d2a97c8`).
  - 5 files were merged clean from a104 or a107.
  - The rest I edited by hand to the a107/a101 shape. After Checkpoint 14, the 13 changed reader files equal a101's
    (fpf) apart from line layout and one docstring.

## Removed, by class
Counts are `lines/files` over tracked files of the area, `06214e132` → now.

### Class 1 — runtime-computed binding identity
- `implementation_sha256` 44/27 → 7/5. What remains is the kept `ExecutionClass.implementation_sha256` and two
  `_TRACKING` name filters.
- 15 binding records no longer compute or carry the digest: 14 literature records and `scientific_process/
  binding_record.py`. Records are `{version, binding_id, configuration}`, the shape the shared-root catalogue now
  requires (handoff row 479, applied).
- 14 hubs (`**/source_contracts.py`) lose `_implementation_path`, `_AXIS_DIRECTORY` and `_binding_source_bytes`, plus
  `import hashlib` and `from pathlib import Path`. `scientific_process/scientific_contracts.py` loses `hashlib` and
  `Path`, which were re-exported only for the binding record.
- Deleted modules (no importer left in the repository):
  - `R/implementation_sources.py`
  - `R/runtime_assets.py` (fingerprinted `bvbrc_appservice_schemas.json` only to feed the digests)
  - `R/scientific_process/.../source_evidence_examination/implementation_sources.py` (and its README row)
- Consumers:
  - `scientific_process/invocation_state.restore_closed_process` now uses the a104 shape (no saved-hash substitution;
    code `scientific_closed_implementation_identity_invalid` gone).
  - `episode_composition.scientific_binding_compatible`: field set and the three digest clauses.
  - `independent_execution`: `implementation_sha256()`, the runtime-binding field, the `identity_conflict` check and
    `__all__`.
  - `method_loop/durable.validate_commission` and `application_execution_binding.py` (merged).
  - `ordinary_execution.py`: the spreadsheet timing class no longer hashes the adapter or worker sources.

### Class 2 — worker/job implementation manifests and software-record pins
- Acquisition (recipe 8): the observer `adapter_sha256` and `response_capture_adapter_changed` are gone, and
  `script_sha256` is gone from three transport/diagnostic dicts.
- BV-BRC adapter pin (recipe 6): the schema entries (`scientific_adapters[].implementation_sha256` and
  `PublicationInputs.adapter_implementation_sha256`) are out of `bvbrc_appservice_schemas.json`. The relation check
  (`publication_adapter_binding_conflict`) is out of `bvbrc_appservice_contracts.py`.
- 13a/13b readers (`library/retained_input_authority`):
  - ATAC `_DRIVER`, which `esm`, `lumpy` and `macs2` use through `driver_runtime_schema`.
  - RNA software record (`python_sha256`, `worker_source_sha256`) and `COMPATIBILITY_FIELDS`.
  - Protein-structure `Software`/`ImplementationFile`.
  - Genomic-overlap `SoftwareBinding`/`ImplementationFile`/`python_observed`.
  - FBA `FBASoftware` (`SoftwareFile {path}`).
  - NMF software `FILE_SCHEMA {path}`.
  - Fluorescence software `PIN_SCHEMA {path}`.
- Section 19 readers: worker-intent pins are `{path}` in `native_expression_nmf_preparation`,
  `native_flux_balance_preparation._pin`, `native_fluorescence_preparation._pin`, and the
  `atac_differential_result_receipts` / `chromatin_interaction_result_receipts` `pin()` functions.
- Ordinary molecular worker selection (`molecular_measurement_tools.py`): a104 shape. Python is `{path}`,
  implementation files are `[{path}]`, there is no re-hash, and code `molecular_tool_original_software_changed_before_
  dispatch` becomes `..._unavailable_before_dispatch`. The protease closure check compares paths, not this
  repository's source bytes.
- ITC in-process software observation (`itc_binding_fit._file`, `itc_binding_contracts`): file rows are `{path}`.

### Class 3 — pinned source constants
`SOURCE_.*SHA256` 22/11 → 0. The pins removed:
- Vendored estimator (`numerical.py`, `runtime.py`, `independent_execution.py`, two fields of
  `vendor/SOURCE.nano-graphrag.json`).
- `SOURCE_FUNCTION_SHA256` + `fba_source_function_mismatch`, with the job/manifest schema fields and the producer.
- `protein_disorder_measurements.SOURCE_SHA256`/`CALLABLE_SHA256` and `module_sha256`/`callable_sha256` in the
  profile.
- `fluorescence_native_report_contracts.PROFILE_SOURCES` now keep `operation` only.
- Biomni protease: `BIOCHEMISTRY_SOURCE_SHA256`, `PROTEASE_FUNCTION_SHA256`, `SOURCE_FILE_SHA256`,
  `SOURCE_FUNCTION_SHA256`, `_deployment(source_sha256=)` + `original_source_pin_required`, the `inspect.getsource`
  digest + `original_callable_identity_mismatch` on it, `source_identity.sha256`, and the two digests in
  `SOURCE_METHOD`.

`template_sha256` 2/2 → 0. `CALLABLE_SHA256` 2/2 → 0.

### Class 4 — tests and fixtures
None deleted or edited: no a105 test asserts the identity mechanism or carries a removed field (`git grep` of the
removed names over a105 test code finds none).

## Suspects carried over
| suspect | a105 evidence | result |
|---|---|---|
| `runtime.py` completed action whose decision has no `pending_work` | 17 directories save a decision (`saved = {'context': context`); the same 17 add `pending_work` (set comparison equal) | removed (clean merge from a107) |
| `decision_history._tables` | `runtime_estimation_contexts` created by `episode_journal.py:66`, the other two by `episode_completion.py:137,142`; `CompletionLedger` built by every `Workflow` (`runtime.py:1055`) | removed (clean merge) |
| `composition_information.restricted_root` default | `Workflow.__init__` refuses any other value (`runtime.py:1007-1009`) | strict read after the path conditions (clean merge) |

## Kept, with reason
- `run_statistics.py:65,81-82`, `ordinary_execution.py:70`, `execution_memory.py:219` `ExecutionClass.
  implementation_sha256`: the timing-class key (versions only now).
- `library/literature_experimental_prompt.py:73` and its `prompts/` copy: `_TRACKING` lists the name (a presentation
  filter).
- `literature_controlled_response_storage.implementation_descriptor` / `literature_gel_storage.implementation_descriptor`
  (cells-schema digest, versions), `implementation_dependencies` (contract version strings), and the "source closure"
  checks (literature source records). These are the A105 grading records; they are unchanged.
- `native_atac_differential_contracts._MACS` (`python_sha256`, `macs2_sha256`, file pins of the external MACS2
  install), `rna_module_sha256`/`rna_extension_sha256` and `native_blast_vdb_utility_execution` runtime files: external
  executables observed at run time.
- Protease deployment record (`molecular_sequence_native.py` `_pin_schema`, `_manifest`, `_exact_file`,
  `_selected_file`, `_imports`, `_library_records`; `molecular_sequence_result_worker._software`;
  `protease_kinetics_measurements._native_request` pins): the operator-supplied deployment's file pins and
  `software_files` manifest. This follows a107, which kept the deployment record's `module` pin in
  `molecular_deployment_contracts`. Note for the coordinator: that manifest also lists the a105 helper modules inside
  the deployment's import roots, and the worker checks imported files against it. If the deployment record itself is
  to go, it is about 150 lines over 7 files plus the top-level producer. No a105 test exercises it.
- `scientific_tool_library._file_sha256` (tool index JSON), `schema_fingerprint` users, `manifest_sha256` (6 sites:
  receipts and library manifests), `source_sha256` (47) and `read_bytes()).hexdigest()` (15): data.

## Gate (measured, after the last product edit)
1. Syntax: 1,469 `.py` files of the area, 0 errors (`runs/claude_fp6_003`). Undefined-name check of the 67 changed
   `.py` files: 0 undefined. The unused imports reported are re-export hubs plus a pre-existing `version` import in
   `ordinary_execution.py`; the `hashlib` my change left unused was removed. Import check over all 1,284 product
   modules prints `{}` (`runs/claude_fp6_002`).
2. Tests: all 178 test files, one file per launcher run, in isolated form (`runs/claude_fp6_101..278`, logs
   `runs/claude_fp6_homes/101..278.log`), 10:30:48–10:47:42. 0 collection errors.

   | | files | tests | passed | failed | errors | test seconds |
   |---|---|---|---|---|---|---|
   | before (rec4 rows; cr1 for 19 controlled-response files) | 178 | 5,632 | 5,577 | 55 | 0 | 952 |
   | expected, written down before launching (`<scratchpad>/fp6/expected.txt`) | 178 | 5,632 | 5,577 | 55 | 0 | well under 952 |
   | measured | 178 | 5,632 | **5,577** | **55** | 0 | 893 (17 min wall) |

   - Per-file counts are identical for all 178 files.
   - The 55 failing test IDs are identical before and after (`diff` of the FAILED lines: equal). They are in 31 files
     and are pre-existing (assertion/IndexError failures in literature integration tests, e.g.
     `test_literature_reported_curve_binding_231.py` 6).
   - **0 tests that passed before fail now.** No test is awaiting shared test fixes (row 482: shared helpers fixed in
     Checkpoint 14).
   - Test seconds fell only 6%: a105's slow files (gel and controlled-response storage) do not build binding records.
   - Edited code that no a105 test names, so it is covered only by the syntax, name and import checks:
     `molecular_sequence_native`, `protease_kinetics_*`, `molecular_measurement_tools`, `itc_binding_*`,
     `independent_execution`, `application_execution_binding`, `scientific_process/invocation_state`, all edited
     `library/retained_input_authority` readers, and `ordinary_execution`.
3. Site counts (lines/files, whole area, `06214e132` → now):

| grep | before | after |
|---|---|---|
| `implementation_sha256` | 44/27 | 7/5 |
| `_binding_source_bytes` | 42/28 | 0/0 |
| `_AXIS_DIRECTORY` | 54/14 | 0/0 |
| `implementation_record`, `SOURCE_PATHS`, `_verify_implementation` | 0/0 | 0/0 |
| `adapter_sha256` / `script_sha256` | 3/1, 3/1 | 0/0 |
| `SOURCE_.*SHA256` | 22/11 | 0/0 |
| `CALLABLE_SHA256` / `callable_sha256` | 2/2, 1/1 | 0/0 |
| `template_sha256` | 2/2 | 0/0 |
| `source_function_sha256` | 5/4 | 0/0 |
| `worker_source_sha256` | 2/2 | 0/0 |
| `python_sha256` | 7/5 | 1/1 (`_MACS`, external) |
| `module_sha256` | 3/3 | 2/2 (`rna_module_sha256`, external) |
| `rglob('*.py')` | 2/1 | 0/0 |
| `fingerprint` | 79/31 | 48/15 (schema/data digests, prose) |
| `manifest_sha256` | 6/5 | 6/5 (data) |
| `source_pins` | 24/5 | 24/5 (field name; rows are `{path}`) |
| `implementation_files` / `driver_runtime` | 41/16, 15/6 | 41/16, 15/6 (names/paths) |
| `source_sha256` | 56/25 | 47/18 (data) |
| `read_bytes()).hexdigest()` | 27/14 | 15/10 (data, external executables) |

## Handoffs
- Applied: row 479 (`fpr → fp-a105`, binding-record shape for the shared catalogue) and row 482 (shared helpers fixed;
  no a105 file failed for that reason).
- Written (`handoffs.tsv`, last two rows):
  - `fp6 → fp-top`: the top-level Biomni protease pins in `molecular_sequence_native.py`,
    `protease_kinetics_{measurements,tools}.py`, `molecular_measurement_tools.py` and
    `tests/test_protease_kinetics_measurements.py`.
  - `fp6 → fp-top,fpr`: the ITC `_file` digests in the top-level and shared-root `itc_binding_fit.py` /
    `itc_binding_contracts.py`.
- Already covered by earlier rows: the FBA, RNA, ATAC, fluorescence and NMF producers, and the ordinary molecular
  worker selection (row 478).

## Second pass (after Checkpoint 16): protease deployment manifest no longer pins this repository
The owner decided to remove this. The manifest's external entries stay; the entries and checks for this repository go.
- `R/molecular_sequence_native.py`:
  - New `_repository_file(path, roots)`: a path under `<import_root>/gene_annotation_episode/`.
  - `_manifest` refuses such a row (`repository_file_in_manifest`).
  - `_imports` skips loaded modules whose file is a repository file: they are neither looked up in the manifest nor
    listed in `imported_files`.
  - `execution_receipt.helper_file` is `{path}`.
  - Kept: external pins (interpreter, stdlib, Biomni module, numpy/scipy/matplotlib files and METADATA),
    `software_files_file` and `software_files_ref`.
- `R/molecular_sequence_result_worker._software` uses the same `_manifest`/`_imports` and needs no edit, so its
  `adapter_imported_files` hold external files only. `R/molecular_sequence_execution_contracts.py`,
  `protease_kinetics_measurements.py` and `protease_kinetics_tools.py` also need no edit: they validate external pins
  and field names only.
- `R/molecular_measurement_tools.py` protease closure check: each worker source must exist at
  `<import_root>/gene_annotation_episode/episodic_workflow/root/a105/<name>` in exactly one root. It used to have to be
  listed in the manifest.

Gate:
- Syntax: 1,469 files, 0 errors; 0 undefined names in changed files (`runs/claude_fp6_004`).
- Import check over 1,284 modules: `{}` (`runs/claude_fp6_005`).
- No a105 test file imports `molecular_sequence_native`, `molecular_sequence_result_worker`,
  `molecular_measurement_tools` or `protease_kinetics_*`, so no test file applies. No shared hub was touched, so no full
  pass was run.
- Smoke run instead (`runs/claude_fp6_006`, script `<scratchpad>/fp6/smoke_manifest.py`):
  - A manifest of the 111 external files loaded by the interpreter is accepted.
  - Adding `molecular_sequence_native.py` to it is refused with `molecular_sequence_repository_file_in_manifest`.
  - `_imports` observes 114 modules, 0 of them repository modules.

Handoff: one row `fp6 → fp-top` (last row of `handoffs.tsv`) gives the exact manifest/receipt shape the top-level
producer and the operator configuration must emit.
