# fp2 — a102: code that fingerprints the codebase removed; six untraced suspects settled (15–16 November 2026)

Area: `gene_annotation_episode/episodic_workflow/root/a102/` (`R/` below). Brief: `FP_BRIEF.md`; shapes: `fp_recipe.md`
(sections 13a, 13b, 14, 15, 16 and "Measured result in a102" were added by this task). Deleted tests:
`fp2_deleted_tests.tsv` (none). Per-file test table: `fp2_gate_results.tsv`. Comparison base: commit `330ef3fe7`
(checkpoints 6, 7 and 8 were committed underneath the task; six files changed after checkpoint 8 are uncommitted:
`composition_information.py`, `decision_history.py`, `runtime.py`, `scientific_process/tests/head_checks.py`,
`tests/resource_task_checks.py`, `tests/source_family_checks.py`). No git add/commit by me, no sub-agents, one
launcher command at a time (slot `fp2`).

## Outcome
Every a102 row of `h5_self_hashing.tsv` is handled, plus four mechanisms the inventory does not contain: the producer
manifest of the native BLAST database drivers, the code manifest of the staged structural-comparison HPC worker
(a102 only), the driver-runtime pins of the HMMER preparation result worker (recipe 13a) and the interpreter/module
pins of the protein-structure software record with their generic reader (recipe 13b). Nothing in a102 product code
hashes, records or compares Python source of this repository any more. One item is left for decision (alimask
profile, same as a101). 22 tests that passed before fail now; none of them can be fixed inside a102 — they sit in
a102 test files that subclass shared checks under `root/tests/` (details and handoffs below).

Change against `330ef3fe7`: 149 files modified, 0 deleted, +295 −1,725 lines — product `.py` 144 files (+290 −1,704),
2 JSON files (+2 −21), 3 test helper modules (+3 −0).

How it was done: three-way merge from a101 (`2ad8be3de` → a101 now, arm name replaced) for every same-path file and,
because a102 keeps most library modules at the arm root, for every same-basename file: 22 files merged without
conflict (20 changed), 12 more merged after resolving 24 conflict hunks by hand (all "take a101's removal", with
a102's own import lines kept; 9 of the 12 changed). The other a101 changes either have no a102 counterpart (15
`library/retained_input_authority` files and 27 files under `tests/`) or sit in files that differ too much to merge (binding records,
contracts hubs, `runtime.py`, `independent_execution.py`, `episode_composition.py`); those and everything specific
to a102 were done by scripted exact-match edits, one perl script per mechanism in `<scratchpad>/fp2/`
(`m1.pl` … `m13b.pl`, `s4.pl`–`s6b.pl`, `t1.pl`; each substitution asserted).

## Removed, by class
Counts are `lines/files` matching the token in tracked files of the area, `330ef3fe7` → now (`git grep`).

### Class 1 — runtime-computed binding identity
- `implementation_sha256`: 112/60 → 6/3 (the 6 are the kept `ExecutionClass.implementation_sha256`, see "Kept").
- `_binding_source_bytes` 126/96 → 0; `_AXIS_DIRECTORY` 144/76 → 0; `_implementation_path` 43/29 → 0;
  `rglob('*.py')` 2/2 → 0.
- 36 `binding_record.py` no longer compute or carry the digest: 14 published-evidence, 10 resource, 6 progress
  assessment (with their private `_binding_source_bytes`), 6 `hpc_work_planning/**` (a102 shape: a `sources`/`hashes`
  roster of up to 30 named files fed to `hpc_queue.digest`). `scientific_process/episode.py::as_record` no longer
  hashes every `.py` of the arm. The helper and its directory constant are gone from 54 hubs (18
  `execution_contracts.py`, 12 `contracts.py`, 10 `resource_contracts.py`, 14 `source_contracts.py`) and from 12
  `episode.py` import lists; `import hashlib` / `from pathlib import Path` deleted in the 24 hubs where nothing else
  used them.
- Consumers: `episode_composition.py` (field set of the scientific descriptor; the 53-row `_PRIVATE_RECONSTRUCTION`
  table loses its `fingerprinted` member and the two `if fingerprinted:` checks), `a102_resources.py::as_record`,
  `execution_progress.py::as_record`, `independent_execution.implementation_sha256()` with the runtime-binding field
  in `make_runtime_binding` / `open_commission`, `method_loop/durable.py::validate_commission`,
  `application_execution_binding.py` (field set, selection, two comparisons), the repository sources in the two
  timing-class descriptors of `ordinary_execution.py`, the name in `literature_experimental_prompt._PRIVATE`.

### Class 2 — worker/job implementation manifests
- Native BLAST database result workers (`request.implementation`, `input_implementation_sha256`,
  `implementation_manifest_sha256`, coordinator `_implementation` subprocess with `implementation.json` /
  `implementation-receipt.json`, `_SCIENTIFIC_MODULES`, `_DEPENDENCY_ROOTS`, `_PROJECT_MODULES`,
  `_implementation_modules`, `_verify_implementation`, `*_implementation_identity`): `implementation_identity`
  19/4 → 0, `_verify_implementation` 6/2 → 0. `*_calculation_identity` takes `input_identity`, `sequence_model`
  (and `vdb_function_model`). In a102 these functions are inline in the two `*_result_worker.py` (a101 keeps them in
  `library/*_worker_values.py`).
- Producer manifest of the native BLAST database drivers (not in the inventory): `producer_manifest` 66/8 → 3/3,
  `producer_verification` 20/4 → 0, `package_files` 10/4 → 0; shape exactly as recipe section 12. The a102 copies
  compared the running module paths with literal `…/root/a101/…` paths, so the verification could never succeed here.
- BV-BRC adapter pin: `adapter_implementation_sha256` 11 lines → 0; `implementation_sha256()` of the homology, MSA
  and MetaCATS adapters with two `_DEPENDENCIES` rosters; `bind_adapters` binds the module (no tuple, no comparison);
  two schema entries in `bvbrc_appservice_schemas.json`.
- Acquisition observer `adapter_sha256` 4/1 → 0 and transport `script_sha256` 4/1 → 0.
- Code manifest of the staged HPC worker (a102 only, recipe 14): `code_manifest` 13/3 → 0, `worker_sha256` 6/3 → 0
  (`a102_hpc.py`, `a102_hpc_worker.py`, `hpc_scientific_commission.py`). The snapshot file is still staged and
  unpacked; request, body, worker result, acceptance predicates, admission check and `execution_provenance` no longer
  carry or compare source digests; the timing-class key `execution_profile.implementation` is the worker version.
- Driver runtime of the HMMER preparation result worker (recipe 13a, decided): `native_driver_runtime.py` (−42 +17)
  and `native_hmmer_preparation_result_publication.py`. Record: no `python_sha256`, `implementation_files [{module}]`,
  dependency `files [{path}]`. `verify_driver_runtime` keeps interpreter path/version, module-file presence and
  loaded path, dependency version/root, "loaded site-packages module is listed"; hashes nothing. `_copy_exact` →
  `_copy_source`. `_runtime_files` keeps the path-inventory comparison only; `result_worker_original_software_changed`
  and the size re-check `result_worker_original_source_size_conflict` are gone, as is the re-check after the worker
  ended.
- Protein-structure software record and generic reader (recipe 13b, decided): `python_sha256` 18/13 → 7/7 (the 7 are
  fixture files read only by a top-level test, handed off). `native_protein_structure_contracts.py` (typed record and
  schema), `native_protein_structure_worker.py::check_selected_software` (`_checksum` deleted; compares versions and
  interpreter path), `native_protein_structure_driver.py:192` (no interpreter hash),
  `terminal_scientific_evidence.py::_identified_file_values` (the two pin branches and the `module_roots` parameter).

Codes that can no longer be raised and are gone (each 1+ → 0 by grep): `appservice_adapter_implementation_conflict`,
`appservice_publication_adapter_configuration_conflict`, `publication_adapter_binding_conflict`,
`original_adapter_pin_required`, `response_capture_adapter_changed`, the three
`native_blast_database_implementation_*` and three standard-database equivalents, `*implementation_files_required`,
six `producer_*` failure codes (out of both `FAILURE_CODES` tables), `result_worker_original_software_changed`,
`result_worker_original_source_size_conflict`, `terminal_native_implementation_path_unavailable`, five
`a102_hpc_*` (`source_snapshot_conflict`, `source_snapshot_membership_conflict`, `staged_worker_conflict`,
`staged_implementation_conflict`, `code_manifest_conflict`).

### Class 3 — pinned source constants
`SOURCE_SHA256` 6/3 → 0 and `template_sha256` 2/2 → 0: the vendored estimator pin (`numerical.py`, `provenance()`,
`binding_versions.controller` in `runtime.py` and `independent_execution.py`) and the two digests in
`vendor/SOURCE.nano-graphrag.json`. a102 has no `library/retained_input_authority/` and none of the flux-balance /
disorder / fluorescence / RNA constants of recipe section 11.

### Class 4 — tests and fixtures
- 0 tests deleted: no a102 test file mentioned a removed field (grep over the 137 test `.py` files before starting).
- 3 a102-owned check modules edited: their Workflow doubles now set `root_action_boundary` (suspect 6 below).
- No fixture edited. `tests/fixtures/protein_structure_result_worker_393/fixtures/*.json` (7 files) still carry
  `python_sha256` and `implementation_files[].sha256` with top-level module names; only
  `tests/test_protein_structure_selection.py:14` (top-level) reads them — handoff row written.

## The six suspects (rec3.md section 3)
| suspect | current producer of the older/absent form | result |
|---|---|---|
| `blast_database_grader.py` binding lists omitted → accession matching (`:880-895`, `:1115-1130`) | yes: `tools.py:2002-2005` (`ToolRegistry._import_blast`, NCBI BLAST API import) → `blast_graders.py:54-56` calls `build_database_sheet` without `description_bindings` / `sequence_identity_bindings` | kept |
| `runtime.py:2904` saved decision without `literature_numerical_contracts` | yes: `runtime.py:1003-1005` saves the key only when `freeze_literature_numerical_contracts` returns a value; it returns `None` when the decision context is not a `literature_experimental_task_v1` (`runtime.py:2847-2855`) | kept |
| `bvbrc_appservice_publication.py:241-248` ("Older saved adapter semantics stay fixed") | yes: the homology adapter `bvbrc_homology_bundle_adapter.py:29-30` is installed (`bvbrc_appservice_adapters.py:11-15`) and is not one of the two adapters named in the condition, so its results with missing requirements take this branch | kept |
| `runtime.py:620-631` completed action whose decision has no `pending_work` | none: every one of the 69 a102 directories that save a decision also adds `pending_work` before saving (`runtime.py:968-972` and 68 home copies; set comparison of the two directory lists: equal) | removed: the `elif packet is not None` branch is gone, `decision_context['pending_work']` is read unconditionally |
| `decision_history.py` query built from the tables present | none in product code: `runtime_estimation_contexts` is created by `Journal` (`episode_journal.py:67`), the other two by `CompletionLedger` (`episode_completion.py:137-145`), built by every `Workflow` (`runtime.py:1910`); the callers are `runtime.py:1223,1319` and the home copies. Only producer of the absent form: shared test fixtures in `root/tests/` | removed: `_tables` deleted, the three joins unconditional; shared fixtures handed off (20 tests) |
| `composition_information.restricted_root` None default | none in product code (`Workflow.__init__` refuses any other value, `runtime.py:1853-1855`); only test doubles omitted the attribute | removed: strict attribute read, evaluated after the path conditions (`composition_information.py:57-60`); the three a102-owned doubles fixed (`scientific_process/tests/head_checks.py:86`, `tests/resource_task_checks.py:152`, `tests/source_family_checks.py:65`) |

Note on suspect 6: the shared root reads the attribute first (`root/composition_information.py:43`); a102 reads it
last, so a double for a non-root source needs no boundary. With the attribute read first, 8 more a102 tests failed in
shared fixtures (measured in the first pass, runs `claude_fp2_101..192`).

## Kept, with reason
- `run_statistics.py:65,81-82` `ExecutionClass.implementation_sha256`, written at `ordinary_execution.py:60,99`, read
  at `execution_memory.py:219`: compatibility key of timing statistics; after this task it hashes versions and the
  digest of Biopython's compiled aligner (`ordinary_execution.py:55`, an external binary observed at run time), not
  repository sources.
- `a102_native_setup.py:17-24` `PINS[...]['archive_sha256']` and its checks (`a102_native_setup.py:36`,
  `a102_hpc_worker.py:48,90`): integrity of the US-align / Foldseek archives downloaded from the network at install
  time ("downloaded files" in the brief). Flagged because the US-align archive is a source tarball; removing the
  check would make the installer accept any bytes from the URL.
- `a102_tools.py:116,412` and `a102_native_setup.py:49` (`a102_native_software_identity_changed`): digest of the
  configured external executable, observed at binding time and re-observed before use; no constant.
- `a102_hpc.py:225-228` comparison of the plan's staged-file digests with the request body's files: transfer record
  of staged data (it also covers the request JSON); no stored code identity is involved.
- `native_blast_*` / `native_hmmer_*` software `expected_sha256` / `observed_sha256`
  (`software_identity_mismatch`, `executed_software_identity_conflict`): external BLAST/HMMER executables from the
  resource configuration, unchanged, same as a101.
- `scientific_tool_library.py:191`, `a102_structural_catalog.py:47,80-82`, `bvbrc_application_definitions.py:223`,
  all remaining `manifest_sha256` (35), `source_sha256` (59), `fingerprint` (42), `read_bytes()).hexdigest()` (17)
  sites: library snapshots, catalog entries, third-party app specs, requests, schemas, receipts, sequence files.
- `native_blast_acquisition.py:27`, `native_hmmer_acquisition.py:23`, `native_protein_structure_results.py:69`: the
  vocabulary value `original_producer_manifest_and_verified_file_digests` (credit key, as in a101).
- `vendor/SOURCE.infrastructure.json`, `method_loop/SOURCE.json`, `method_loop/LOCAL_PATCHES.json`: provenance
  documents that list sha256 of vendored/target source files; no code reads them; a101 left them too. They are not
  product code or tests; say so if they should go.
- `waiting.completed_action_context` still accepts `pending_at_selection=None` (`waiting.py:630-632`, the same loop
  validates `pending_after_action`); no a102 caller passes None any more.

## Left for decision
1. `hmmer_alignment_preparation_data.py:75-76,111,146-147` and `hmmer_alignment_preparation_calculations.py:124-129`:
   `ALIMASK_PROFILE_EXECUTABLE_SHA256` (hard-coded digest of the alimask executable) and
   `ALIMASK_PROFILE["source_sha256s"]` (digests of HMMER/Easel C sources). The executable digest decides whether the
   retained weighting profile and `effective_pb_config` apply, i.e. how alimask results are graded; removing it
   changes grading, not only identity refusal. Same in a101 (fp1.md item 3) and every arm.

## Gate (measured)
1. Syntax: 3,113 `.py` files parsed, 0 syntax errors; symtable check of the 147 changed `.py` files: 0 global names
   referenced but not bound (`runs/claude_fp2_301`). Import check over all 2,976 product modules prints `{}`
   (`runs/claude_fp2_302`). Both after the last product edit.
2. Tests: all 92 test files, one file per launcher run, isolated form, after the last edit (`runs/claude_fp2_401..492`,
   logs `runs/claude_fp2_homes/401..492.log`). Expected, written down before the first run
   (`<scratchpad>/fp2/expected.txt`): 92 files, 4,940 tests = 4,924 passed + 5 failed + 11 skipped.
   Measured: 92 files, 4,940 tests = **4,902 passed, 27 failed, 0 errors, 11 skipped**; 0 collection errors; 304 test
   seconds (1,123 before), 5 minutes wall.
   - Pre-existing failures, unchanged (5): `tests/test_a102_parent_coordination.py` (1),
     `tests/test_literature_structure_integration.py` (4).
   - Passed before, fail now (22), per-test comparison with `runs/claude_rec3_a102f_001..092`:
     - 20 × `sqlite3.OperationalError: no such table: runtime_decision_effects` — suspect 5. The shared fixtures
       `root/tests/hpc_launch_task_checks.py:39`, `hpc_planning_allocation_task_behavior.py:179`,
       `hpc_prediction_prompt_behavior.py:136` open a journal without the completion ledger. Affected:
       `test_fresh_and_saved_decision_keep_full_launch_payload[*]` (8), 
       `test_private_decision_dispatch_saved_replay_and_selected_presentation[*]` (8),
       `test_actual_decision_dispatch_and_saved_replay_keep_private_presentation[*]` (4) in 10 a102 files. Verified
       fix: with a ledger built for every a102 journal (verification-only pytest plugin kept in the scratchpad, not in
       the repository; runs `claude_fp2_501..510`) the 10 files pass completely, 204 passed, 0 failed.
     - 2 × `KeyError: 'implementation_sha256'` — `root/tests/hpc_prediction_behavior.py:177` asserts the digest
       length; affected `test_saved_description_config_and_prediction_goal` in the two a102
       `hpc_resource_prediction/tests/test_prediction_behavior.py`.
     Both groups need an edit in `root/tests/`, which is outside this area: handoff rows written. If a green a102
     gate is wanted before `fp-top` acts, suspect 5 can be put back with `git diff 330ef3fe7 -- R/decision_history.py`
     reversed (20 of the 22).
   - Intermediate passes: `claude_fp2_101..192` (first full pass: 505 failed, almost all from a102-owned doubles
     without `root_action_boundary`), `claude_fp2_201..205` (the five files using the fixed doubles: all pass).
3. Site counts before → after for every grep of the brief: table in "Removed" above; the full list is
   `<scratchpad>/fp2/counts_table.tsv`. Tokens of the brief with 0 sites before and after in a102:
   `implementation_record`, `SOURCE_PATHS`, `CALLABLE_SHA256`, `resource_implementation_bytes`, `_context_source_key`,
   `source_pins`, `module_sha256`, `callable_sha256`, `source_function_sha256`, `worker_fingerprint`,
   `REQUIRED_MODULES`.

Not verified by running: the native BLAST database drivers/workers, `a102_hpc*`, the HMMER preparation result worker
and the protein-structure worker/driver have no test in a102 (a101 has tests for the BLAST database code these edits were merged from, a102 has none;
the a102-only edits to `a102_hpc*`, `native_driver_runtime.py`, `native_protein_structure_*` and
`terminal_scientific_evidence.py` are covered only by the syntax, bound-name and import checks). Tests outside a102
were not run.

## Handoffs
- Applied: none were addressed to `fp2`. Older rows to `pa102` (354, 415–417, 425) are already in effect (checked by
  grep).
- Written (16 rows `fp2 → fp-top`, `handoffs.tsv` lines 437–452): the digest assert at
  `root/tests/hpc_prediction_behavior.py:177`; the three shared fixtures without a completion ledger; three notices
  (annotation-root doubles need `root_action_boundary`; hand-saved decisions need `pending_work`; the list of forms
  gone from a102 for parametrized tests); the 7 protein-structure fixtures read by
  `tests/test_protein_structure_selection.py:14`; one row per shared-root / top-level producer file of the 13a and 13b
  records (`root/library/native_protein_structure_{job_schema,contracts,worker,driver}.py`,
  `root/terminal_scientific_evidence.py`, `native_atac_differential_{contracts,software}.py` in both places,
  `root/library/native_driver_runtime_verification.py`, `root/library/native_hmmer_preparation_result_publication.py`);
  the top-level `hpc_scientific_commission.py` with its caller and test; the operator configuration of the
  protein-structure software record.
