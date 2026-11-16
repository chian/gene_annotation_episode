# fp1 — a101: code that fingerprints the codebase removed (15–16 November 2026)

Area: `gene_annotation_episode/episodic_workflow/root/a101/` (`R/` below). Brief: `FP_BRIEF.md`. Recipe for the sibling
arms: `fp_recipe.md`. Deleted tests: `fp1_deleted_tests.tsv`. Comparison base: commit `2ad8be3de` (HEAD when this task
started; checkpoint commits 4, 5 and 6 were made underneath the task, so `git diff HEAD` does not show the whole change).

## Outcome in one paragraph
Every mechanism in the a101 rows of `h5_self_hashing.tsv` is removed, plus one mechanism the inventory does not
contain (the producer manifest of the native BLAST database drivers, 315 matching lines in 32 files). Two further mechanisms that the
inventory also does not contain are NOT removed and are listed under "Left for decision": the copied-source runtime
record of the HMMER preparation worker, and the worker-intent/driver-runtime formats in
`library/retained_input_authority/` whose job-side producer is the top-level package. Until those are decided, a101
still contains code that records and compares digests of this repository's Python source (about 170 sites, 26 files).

Change against `2ad8be3de`: 150 files (141 modified, 9 deleted), 298 lines added, 14,431 removed — product code 121 files, +239 −1,599; tests and fixtures 29 files, +59 −12,832, of which 12,074 lines are one deleted orphan fixture.

## Removed, by class
Counts are lines matching the named tokens in the whole area (product, tests, fixtures) at `2ad8be3de` → now, as
`lines/files`.

### Class 1 — runtime-computed binding identity
- `implementation_sha256` (all uses, classes 1 and 2 together): 136/70 → 7/4 (the 7 are the kept
  `ExecutionClass.implementation_sha256`, see "Kept").
- `_binding_source_bytes`, `_AXIS_DIRECTORY`, `_context_source_key`: 198/65 → 0. `as_record()` of 27
  `binding_record.py` files no longer computes or carries the digest; the helper and its directory constant are
  deleted from 37 `*/execution_contracts.py` / `*/source_contracts.py` files (13 of those copies had no caller).
- `resource_implementation_bytes`, `HOMOLOGY_BINDING_SOURCES`: 23/11 → 0; module `a101_resource_implementation.py`
  deleted.
- Consumers: `scientific_binding_compatible` (`episode_composition.py`), `as_record()` of `execution_progress.py` and
  `homology_progress.py`, `independent_execution.implementation_sha256()` with the runtime-binding field in
  `make_runtime_binding` / `open_commission` / `method_loop/durable.py::validate_commission` /
  `application_execution_binding.py` (field set, selection, two comparisons).
- `parser_implementation_sha256`, `worker_fingerprint` (`homology_results.py`): 4/2 → 0.
- Repository sources taken out of the two hashed timing-class descriptors (`ordinary_execution.py`) and the three
  scorer-source digests out of the replay report (`a101_replay.py`).

### Class 2 — worker/job implementation manifests
- Native BLAST database result worker (`request.implementation`, `input_implementation_sha256`,
  `implementation_manifest_sha256`, `_implementation_modules`, `_verify_implementation`,
  `*_implementation_identity`): 119/15 → 0 real uses (3 unrelated `extractor['implementation']` name strings match the
  grep). The coordinator's inventory subprocess `_implementation` and its `implementation.json` /
  `implementation-receipt.json` files are gone; `*_calculation_identity` takes `input_identity`, `sequence_model`
  (and `vdb_function_model`) only.
- BV-BRC adapter pin (`adapter_implementation_sha256`: 21/11 → 0; plus `implementation_sha256()` and the
  `_DEPENDENCIES` rosters of 3 adapters, the `bind_adapters` comparison, configuration rows and 2 JSON schemas).
- Acquisition observer `adapter_sha256` and transport `script_sha256`: 11/4 → 2/2 (two retained captured fixtures).
- Producer manifest of the native BLAST database drivers (NOT in the inventory): `producer_verification`,
  `producer_manifest`, `package_files`, `_verify_producer`, `_producer_files`, `PRODUCER_MANIFEST*`,
  `validate_retained_{native,standard}*`, `_PRE_*REQUIRED_FILES`, six `producer_*` failure codes: 315/32 → 32/9 (the
  32 are BV-BRC's unrelated provider data role `producer_manifest` and the two `attempt_output_version` labels, see
  "Kept"). `library/native_blast_database_contracts.py` 1,107 → 943 lines,
  `library/native_blast_standard_database_contracts.py` 1,173 → 982 lines.

Error/failure codes that can no longer be raised and are gone from code and code tables:
`appservice_adapter_implementation_conflict`, `appservice_publication_adapter_configuration_conflict`,
`publication_adapter_binding_conflict`, `original_adapter_pin_required`, `response_capture_adapter_changed`,
`native_blast_database_implementation_inventory_failed`, `native_blast_database_implementation_identity_conflict`,
`native_blast_database_implementation_changed` (and the three standard-database equivalents),
`fba_source_function_mismatch`; from the two bundle `FAILURE_CODES` tables `producer_manifest_invalid`,
`producer_file_missing`, `producer_file_identity_mismatch`, `producer_file_unreadable`,
`producer_package_inventory_mismatch`, `producer_runtime_path_mismatch`; and the contract-violation codes raised only
by the deleted manifest/verification validators.

### Class 3 — pinned source constants
`SOURCE_SHA256`, `template_sha256`, `CALLABLE_SHA256`, `callable_sha256`, `SOURCE_FUNCTION_SHA256`,
`source_function_sha256`, `source_file_sha256`, `worker_source_sha256`: 18/11 → 0. In detail: the vendored estimator
pin (`numerical.py`, `provenance()`, settings `binding_versions.controller`, two digests in
`vendor/SOURCE.nano-graphrag.json`); flux balance (constant, producer, 2 schema entries, check); protein disorder
(2 constants and the `module_sha256`/`callable_sha256` members of the source-profile const); fluorescence
`PROFILE_SOURCES` (`source_file_sha256`, `function_sha256`); RNA structure `worker_source_sha256` (software schema
and comparison compatibility list).

### Class 4 — tests and fixtures
- 4 test files deleted (36 tests) and 1 helper directory (3 files); 21 further tests/cases deleted from 6 files;
  3 tests kept with the digest half removed and renamed. List with reasons: `fp1_deleted_tests.tsv`.
- 21 test files modified in total (the 6 with deleted cases, the 3 with a renamed test, and 12 edited only to drop the
  removed fields/arguments or to pass the deployment directory explicitly).
- 1 orphan fixture deleted: `R/tests/fixtures/blast_explicit_associations/legacy_prechange.json` (a "captured before
  H1 edit" snapshot carrying `module_sha256`; no test reads it).

## Kept, with reason
- `R/run_statistics.py:65,81-82` `ExecutionClass.implementation_sha256`, set at `R/execution_recording.py:141`
  (digest of the external BLAST/HMMER executable from the resource configuration) and read at
  `R/execution_memory.py:219`: digest of an external executable recorded as the compatibility key of timing
  statistics. `R/ordinary_execution.py:55` keeps `native_pairwise_aligner_sha256` (Biopython's compiled extension) for
  the same reason; the repository sources were taken out of both class descriptors.
- `R/numerical.py:39,69` `SOURCE_REVISION`: upstream commit label of the vendored estimator, compared with nothing.
- `R/library/retained_input_authority/native_rna_structure_contracts.py:26` `python_sha256`, `rna_module_sha256`,
  `rna_extension_sha256`: installed external tool files observed at run time by the worker.
- All `manifest_sha256` that remain (141 sites): digest of a saved `worker-manifest.json` / database manifest, a data
  record. All remaining `fingerprint` (35), `read_bytes()).hexdigest()` (37) and `source_sha256` (112) sites hash
  requests, schemas, artifacts, receipts or sequence/alignment source files.
- `R/tests/fixtures/uniprot_native/P0AAW1.transport.json` and `R/tests/fixtures/uniprot_publication/c2/c2c8…c952`
  still contain `script_sha256`: retained transport records of a past acquisition; the second is stored under the
  sha256 of its own bytes, so it cannot be edited without breaking its address.
- `R/native_blast_acquisition.py:24`, `R/native_hmmer_acquisition.py:23`: the value
  `'original_producer_manifest_and_verified_file_digests'` of `attempt_output_version`. It is a vocabulary value of
  result provenance, not a digest; the same field's other value is used as a credit key
  (`attempt_output_version_unverified`, `*/credit.py:181-198`), so it is left unrenamed.
- `producer_input_parser_unavailable` (still raised when the PSSM parser cannot be imported),
  `producer_owned_environment:` (reserved environment names), BV-BRC `producer_manifest` (a provider data role).

## Left for decision
1. **HMMER preparation worker runtime** — `R/native_driver_runtime.py` (15 sites: `_DRIVER` schema :46-48,
   `verify_driver_runtime` :169-190, `_copy_exact`, `_dependency_bindings`, `freeze_driver_runtime` :288-314) and
   `R/native_hmmer_preparation_result_publication.py` (39 sites: `_runtime_files` :210-225,
   `_worker_runtime` :228-282, `_worker_selection` :296-330, worker bootstrap :45-60). The result worker runs from a
   copied source snapshot; the record pins every copied module (`implementation_files[{module, sha256}]`), the
   interpreter and every file of every dependency distribution, re-verified inside the worker and at every
   re-observation (`result_worker_original_software_changed`, `result_worker_original_source_inventory_conflict`,
   `result_worker_original_source_size_conflict`). Self-contained in a101 (only importer of `native_driver_runtime`).
   Not removed because the digests are the content of the snapshot-and-verify design (dependency record mode,
   exclusions, copy footprint), so removing them means deciding whether the worker still runs from a copied snapshot,
   and because its test file cannot verify a rewrite: `R/tests/test_native_hmmer_preparation_result_publication.py`
   had 3 passed, 1 failed, 25 errors before this task and has the same now.
2. **Worker intents and driver runtimes in `R/library/retained_input_authority/`** — 22 files, 111 sites
   (`source_pins`, `implementation_files`, `driver_runtime`, `REQUIRED_MODULES`/`required_modules`, `python_sha256`):
   `native_{atac_differential,chromatin_interaction,expression_nmf,fluorescence,flux_balance,genomic_overlap,
   protein_structure}_contracts.py`, `native_{expression_nmf,fluorescence,flux_balance}_preparation.py`,
   `{atac_differential,chromatin_interaction}_result_receipts.py:444-495`, `native_{lumpy,macs2_peak}_execution.py`,
   `{lumpy,macs2_peak}_request_binding.py`, `esm_gene_embedding_contracts.py`, and their generic reader
   `R/terminal_scientific_evidence.py:245-257` (+ the key name at `R/scientific_process_prompt.py:625`). These validate
   records written by job-side drivers and workers of the top-level package (`gene_annotation_episode.native_*_driver`,
   `*_result_worker`); removing the fields only in a101 makes a101 refuse the records current jobs write. They need
   one decision applied to the top-level producers and every arm's copy together.
3. **Pinned external executable digest that selects a scientific profile** —
   `R/library/hmmer_alignment_preparation_data.py:73,144` and `R/library/hmmer_alignment_preparation_calculations.py:119`
   (`ALIMASK_PROFILE_EXECUTABLE_SHA256`): not source (a compiled alimask binary), but a hard-coded constant compared
   with the observed executable; it decides whether the retained alimask weighting profile applies, i.e. what is graded.
4. **Native weight oracle test** — `R/tests/fixtures/hmmer_native_weight_oracles/SOURCE_PINS.json` (sha256 of 40
   Easel/HMMER C sources and 2 harness sources) checked at
   `R/tests/test_hmmer_alignment_native_weight_oracle.py:101-111` before compiling the oracle. The file needs a staged
   Easel tree and compiler from the environment and errors here before and after (57 errors), so an edit could not
   be verified.

## Gate (measured)
1. **Syntax / imports.** 2,186 `.py` files parsed, 0 syntax errors (`runs/claude_fp1_401`). Import check over all
   1,871 product modules of the area prints `{}` (`runs/claude_fp1_402`). A symtable check of the 138 changed `.py`
   files reports 0 global names referenced but not bound (`runs/claude_fp1_403`).
2. **Tests.** All 267 test files of the area run once, one file per launcher run, isolated form
   (`runs/claude_fp1_100` … `_366`, one rerun `_400`; logs `runs/claude_fp1_homes/NNN.log`; table
   `runs/claude_inputs/purge/fp1_gate_results.tsv`, same columns as `rec2_gate_results.tsv`). 0 collection errors.

   | | files | collected | passed | failed | errors | skipped | test seconds |
   |---|---|---|---|---|---|---|---|
   | before (`rec2_gate_results.tsv`) | 271 | 9,808 | 9,284 | 286 | 178 | 60 | 1,157 |
   | expected, written down before the run | 267 | 9,751 | 9,227 | 286 | 178 | 60 | about 1,150 |
   | measured | 267 | 9,751 | 9,227 | 286 | 178 | 60 | 1,080 (23 min wall) |

   The 57 fewer tests are the 36 in the four deleted files and the 21 deleted cases (`fp1_deleted_tests.tsv`).
   Per-test comparison with the previous logs (`runs/claude_rec2_<run id>/stdout.log`): **0 tests fail now that did
   not fail before.** Six files changed their counts, all by deletion: `test_native_blast_database_contracts.py`
   84→83, `test_native_blast_database_driver.py` 58→49, `test_native_blast_standard_database_driver.py` 56→49,
   `test_native_blast_standard_database_result_worker.py` 26→25, `test_private_descriptor_reopening.py` 7→6,
   `test_remaining30_terminal_resource_binding.py` 5→3.
   One regression appeared in the first full run and was fixed: `R/tests/test_homology_progress.py` 26 passed → 17
   passed / 9 failed (`runtime binding fields must be exact`). Cause: the test takes its commission from the
   top-level fixture `tests/test_durable_episode.py::commission_spec`, whose `runtime_binding` still carries
   `implementation_sha256`. Fix inside the area: `assigned_spec` projects the fixture's binding to the arm's four
   fields (`R/tests/test_homology_progress.py:96-98`); rerun 26 passed (`runs/claude_fp1_400`).
   The set of failing files is identical to the previous one (36 files, all failing before this task; 3 more files
   exit 5 with no test collected, before and after): the 36 are the rows with a failed or error count in
   `fp1_gate_results.tsv`.
3. **Site counts**: next section.

## Site counts for the greps of the brief (lines/files, whole area incl. tests and fixtures)
| grep | before | after | what remains |
|---|---|---|---|
| `implementation_sha256` | 136/70 | 7/4 | `ExecutionClass.implementation_sha256` (external executable / version digest), see Kept |
| `implementation_record` | 0/0 | 0/0 |  |
| `_binding_source_bytes` | 89/63 | 0/0 |  |
| `SOURCE_PATHS` | 0/0 | 0/0 |  |
| `manifest_sha256` | 202/45 | 141/39 | digests of saved worker/database manifests (data) |
| `_verify_implementation` | 8/3 | 0/0 |  |
| `adapter_sha256` | 4/1 | 0/0 |  |
| `script_sha256` | 7/4 | 2/2 | two retained captured transport fixtures |
| `fingerprint` | 37/13 | 35/12 | request and schema digests; prose in two instruction files |
| `SOURCE_.*SHA256` | 12/7 | 0/0 |  |
| `CALLABLE_SHA256` | 2/2 | 0/0 |  |
| `template_sha256` | 2/2 | 0/0 |  |
| `read_bytes()).hexdigest()` | 54/35 | 37/27 | artifact, request, receipt, database and executable files; one Biopython extension |
| `resource_implementation_bytes` | 21/11 | 0/0 |  |
| `_context_source_key` | 30/28 | 0/0 |  |
| `source_pins` | 30/11 | 30/11 | Left for decision 2 and 4; 4 census data fixtures |
| `module_sha256` | 4/4 | 2/2 | `rna_module_sha256` (installed ViennaRNA module), see Kept |
| `callable_sha256` | 1/1 | 0/0 |  |
| `source_function_sha256` | 4/3 | 0/0 |  |
| `implementation_identity` | 27/9 | 0/0 |  |
| `worker_fingerprint` | 2/1 | 0/0 |  |
| `source_sha256` | 116/38 | 112/34 | alignment/sequence source files and native receipts (data) |
| `rglob('\*.py')` | 2/2 | 0/0 |  |

## Handoffs
Written (rows 426-432 and 436 of `handoffs.tsv`): to `rec5` — three top-level tests that build BV-BRC adapter configuration
rows with `implementation_sha256()` through the a101 test factory; one that builds `PublicationInputs` with
`adapter_implementation_sha256`; a general row listing every removed a101 name for tests that reach a101 through a
parametrized package name; to `ptop` — job-side producers of `source_function_sha256` (flux balance) and
`worker_source_sha256` (RNA structure); to `rec5,ptop` — operator configuration/plans carrying the producer manifest;
to `proot,prootlib` — the shared-root copies of the producer-manifest mechanism; to `rec5` — the top-level fixture
`tests/test_durable_episode.py::commission_spec` (runtime binding with `implementation_sha256`).
Open: by the end of this task `rec5` (shared root, top-level package, `tests/`) had already delivered its report
(commit message of checkpoint 5), and `ptop`/`proot`/`prootlib` name areas, not running agents; rows 426-432 and 436 are therefore
not applied by anyone yet. The top-level tests they name are outside a101's gate.
Addressed to this area for this task: none (checked at the end). The 12 older rows addressed to `pa101` predate this
task and concern other removals; they were not re-checked here.
