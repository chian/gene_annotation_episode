# fp5 — a104: code that fingerprints the codebase removed; the sibling suspects carried over (16 November 2026)

Area: `gene_annotation_episode/episodic_workflow/root/a104/` (`R/` below). Brief: `FP_BRIEF.md`. Shapes: `fp_recipe.md`
(sections 1-18 followed; a104 additions appended as section 19). Deleted tests: `fp5_deleted_tests.tsv` (none).
Per-file gate table: `fp5_gate_results.tsv`. Comparison base: commit `49dee49e6` (HEAD when the task started;
checkpoint 11, `6a2a8a7df`, was committed underneath the task and contains part of it, so `git diff HEAD` does not show
the change). No git add/commit by me, no sub-agents, one launcher command at a time (slot `fp5`).

## Outcome
Every a104 row of `h5_self_hashing.tsv` (185) and of `pa104_self_hashing.txt` (101) is handled: 173 inventory texts are
gone, 1 file is gone, 11 texts remain and are kept (listed under "Kept"). Also removed, not in the inventory: the
producer manifest of the native BLAST database drivers (recipe 12), the driver-runtime pins of the HMMER preparation
result worker (13a), the protein-structure and fluorescence software-record pins and the fluorescence worker-intent pins
(13a/13b), the molecular worker execution-selection pins (`a104_native_worker.py`) and the source digests of a test
diagnostic. The three sibling suspects (`pending_work`, `decision_history._tables`, `restricted_root`) are carried over
with the same producer evidence, and the two `homology_results.py` suspects settled by fp3 came with the clean merge
(a104's file and its producers are byte-identical to a103's before). Nothing in a104 product code or tests now hashes,
records or compares Python source of this repository. Kept by the owner's decisions: `ALIMASK_PROFILE_EXECUTABLE_SHA256`.

Change against `49dee49e6`: 175 files (173 modified, 2 deleted), +339 −1,680 lines — product `.py` 170 files
(+334 −1,655), 2 JSON files (+2 −21), 3 test files (+3 −4). No test deleted, no fixture edited.

How it was done: three-way merges (`git merge-file`, arm name replaced) for the 93 a104 files with the same relative
path as a file changed in a102 or a103 for this task, taking the sibling whose pre-task file is closest: 26 clean
(applied after reading each diff), 67 with conflicts. Of the conflicting ones, 59 were dense binding records, hubs and
`episode.py` files whose a104 form differs from both siblings (the 26 `episode.py` needed nothing: a104 never imported
the helper there); the rest were done by asserted perl scripts on the a104 shape (`<scratchpad>/fp5/m1.pl` helpers, `m2.pl` binding records), and `independent_execution.py`,
`terminal_scientific_evidence.py`, `native_blast_standard_database_result_publication.py` were resolved by hand to the
removal side (scratchpad `take.pl`), keeping a104's own lines. `a104_hpc*.py`, `episode_composition.py`,
`execution_progress.py`, `literature_experimental_prompt.py` were edited directly (a104 shape, see below). Everything
else specific to a104 was done with one-off asserted perl substitutions.

## Removed, by class
Counts are `lines/files` matching the token in tracked files of the area, `49dee49e6` -> now.

### Class 1 — runtime-computed binding identity
- `implementation_sha256` 146/67 -> 8/5 (the 8 are the kept `ExecutionClass.implementation_sha256` and one presentation
  filter, see "Kept").
- 27 binding records no longer compute or carry the digest: 14 literature (`published_evidence_assessment/**` and the
  `scientific_process/` mirror; a104 shape: `library/source_descriptor_inputs.implementation_bytes(binding_path)` plus
  the JSON of the controlled-response and gel descriptors), 6 progress assessment (own `_binding_source_bytes` with the
  seven shared-root context files), 6 hpc (`sources`/`hashes` roster -> `hpc_queue.digest`), `scientific_process/
  binding_record.py` (`rglob('*.py')` of the arm + context files). Records are `{version, binding_id, configuration}`.
- `_binding_source_bytes` 69/63 -> 0 and `_AXIS_DIRECTORY` 61/61 -> 0: 49 helper definitions (32 dead ones in
  `binding_record.py`, 14 literature `contracts.py`, 3 homology `message_contracts.py`) and 47 constants
  (binding_roles, hubs); `from pathlib import Path` / `import hashlib` deleted where nothing else used them (52 binding
  records/roles, 14 literature hubs, 7 trailing duplicates). Deleted modules: `R/library/source_descriptor_inputs.py`
  (roster `SOURCE_FILES` + `implementation_bytes`) and `R/literature_implementation_sources.py` (roster
  `LITERATURE_BINDING_SOURCES*` + `source_file`, imported only for the hubs' `_AXIS_DIRECTORY`; no other importer in the
  repository).
- Consumers: `episode_composition.scientific_binding_compatible` (field set and the three digest-shape clauses),
  `scientific_process/saved_scientific_state.restore_closed_process` (`{**saved_binding, 'implementation_sha256': ...}`
  substitution, `saved_hash` shape check, re-insertion into the candidate: now `saved_binding != current or
  filled['mechanics_binding'] != current`), `execution_progress.as_record` (hash of its own file),
  `independent_execution.implementation_sha256()` with `make_runtime_binding` / `open_commission` / `__all__`,
  `method_loop/durable.validate_commission`, `application_execution_binding.py` (clean merge), repository sources out of
  the two timing-class descriptors of `ordinary_execution.py` (clean merge), `homology_results.py`
  `parser_implementation_sha256` / `worker_fingerprint` (clean merge).

### Class 2 — worker/job implementation manifests
- Native BLAST database result workers (clean merges from a102): `implementation_identity` 20/5 -> 0,
  `_verify_implementation` 6/2 -> 0; the 12 `**/execution_result_acquisition/native_blast_{,standard_}database_result_
  acquisition.py` no longer collect `implementation-receipt.json`; `native_blast_standard_database_result_publication.py`
  keeps a104's two manifest versions (`_MANIFEST_ROLES`), field set without the two digests.
- Producer manifest of the native BLAST database drivers (clean merges): `producer_verification` 20/4 -> 0,
  `package_files` 10/4 -> 0, `producer_manifest` 91/13 -> 28/8 (BV-BRC provider data role and the
  `attempt_output_version` labels remain).
- BV-BRC adapter pin: `implementation_sha256()` and `_DEPENDENCIES` of `bvbrc_phylogeny_bundle_projection.py`
  (re-exported by the gene-tree and codon-tree adapters), `bvbrc_homology_bundle_adapter.py` (clean merge),
  `library/bvbrc_proteome_bundle_adapter{,_v2}.py`; `bind_adapters` binds the module; `PublicationInputs.
  adapter_implementation_sha256` out of the 12 `appservice_publication.py` copies, `library/appservice_publication_
  records.py`, `library/bvbrc_proteome_returns.py` and `bvbrc_appservice_schemas.json` (clean merge).
- Acquisition `adapter_sha256` 4/1 -> 0, `script_sha256` 4/1 -> 0 (clean merge).
- `a104_hpc.py` / `a104_hpc_worker.py`: `worker_sha256` 8/4 -> 1/1 (the 1 is a captured real result fixture, data).
- 13a: `native_driver_runtime.py` (clean merge from a103) and `native_hmmer_preparation_result_publication.py` (clean
  merge from a102); `python_sha256` 8/4 -> 0. `_copy_source` follows the owner's staging decision: an existing staged
  copy is accepted when its bytes equal the source bytes (and it is read-only), refused otherwise.
- 13a/13b in a104's library (reader of records produced in the shared root): `library/native_protein_structure_
  contracts.py` (Software without `python_sha256`, `ImplementationFile` = `{module}`), `library/native_fluorescence_
  contracts.py` (`fluorescence_software_v1` pins `{path}`), `library/native_fluorescence_preparation.py` (worker-intent
  pins `{path}`), `terminal_scientific_evidence.py` (clean-merge shape: no software pins, no `module_roots`).
- Molecular worker execution selection (`a104_native_worker.py`, a104 only): `python` `{path}`, `implementation_files`
  `[{path}]`; `verify_unstarted_software` requires the listed files to exist.

Codes that can no longer be raised and are gone: `appservice_adapter_implementation_conflict`,
`appservice_publication_adapter_configuration_conflict`, `publication_adapter_binding_conflict`,
`original_adapter_pin_required`, `response_capture_adapter_changed`, the `native_blast_{,standard_}database_
implementation_*` codes, the six `producer_*` bundle failure codes, `result_worker_original_software_changed`,
`result_worker_original_source_size_conflict`, `terminal_native_implementation_path_unavailable`,
`scientific_closed_implementation_identity_invalid`, `invalid_fluorescence_pin`; `molecular_tool_original_software_
changed_before_dispatch` is now `molecular_tool_original_software_unavailable_before_dispatch` (what it checks).

### Class 3 — pinned source constants
`SOURCE_SHA256` / `template_sha256` of the vendored estimator (`numerical.py`, `runtime.py`, `independent_execution.py`,
two digests in `vendor/SOURCE.nano-graphrag.json`): `SOURCE_.*SHA256` 6 -> 0 lines, `template_sha256` 2/2 -> 0.
`library/fluorescence_native_report_contracts.py:14` `PROFILE_SOURCES` keep `operation` only (no
`source_file_sha256` / `function_sha256`).

### Class 4 — tests and fixtures
No test deleted. Edited: `tests/proteome_partner/proteome_host_fixture.py:51` (configured adapter row without the
digest), `tests/test_a104_evolutionary_episode.py:80` (`execution_profile.implementation` is the native request
version), `tests/execution_input_version_probe.py:43,88` (diagnostic report without `helper_sha256` / `source_sha256`).
Not edited: `tests/fixtures/a104/real/mj0044/native-pbs-9040517.json` (captured real HPC result carrying
`worker_sha256`; data, read by `tests/test_a104_relationship_correspondence.py` only for its trees).

## Suspects carried over (task item)
| suspect | a104 evidence | result |
|---|---|---|
| `runtime.py:478-482` completed action whose decision has no `pending_work` | none: 63 directories save a decision (`saved = {'context': context, ...`), the same 63 add `pending_work` first (`context = {**context, 'pending_work': self.workflow.pending_work(self)}`; set comparison of the two directory lists: equal) | removed (clean merge): the `elif packet is not None` branch is gone, `decision_context['pending_work']` read unconditionally |
| `decision_history.py` query built from the tables present | none in product code: `runtime_estimation_contexts` is created by `Journal` (`episode_journal.py:67`), the other two by `CompletionLedger` (`episode_completion.py:137-142`), built by every `Workflow` (`runtime.py:762`) | removed (clean merge): `_tables` deleted, joins unconditional |
| `composition_information.restricted_root` None default | none in product code: `Workflow.__init__` refuses any other value (`runtime.py:697-699`) | removed (clean merge): strict read after the path conditions (`composition_information.py:57-60`); no a104-owned double needed a change |
| `homology_results.py` (fp3: snapshot defaults, worker row without grading outcome) | a104's `homology_results.py` and `phmmer_result_worker.py` are byte-identical to a103's before; the one snapshot writer (`homology_results.py:344-354`) always writes the three fields; the worker always writes `grading_file` or `grading_failure` | removed (clean merge), with `phmmer_shared_grading_unavailable` |
| `component_assessment_dependencies.py` | a104's copy never had `qualification_assessment_changes`; the merge removed only the then-unused `deepcopy` import | import removed |

## Kept, with reason
- `run_statistics.py:65,81-82` `ExecutionClass.implementation_sha256`, set at `execution_recording.py:141` and
  `ordinary_execution.py:60,99`, read at `execution_memory.py:219`: timing-class key from an external executable's
  digest; `ordinary_execution.py:55` `native_pairwise_aligner_sha256` (Biopython's compiled extension).
- `literature_experimental_prompt.py:95` `_TRACKING` lists the field name `implementation_sha256`: a filter that keeps
  tracking fields out of the model presentation; `ExecutionClass` records still carry that name.
- `hmmer_alignment_preparation_data.py:75` `ALIMASK_PROFILE_EXECUTABLE_SHA256` and `ALIMASK_PROFILE["source_sha256s"]`:
  owner decision (selects the grading profile).
- `literature_controlled_response_storage.py:66` / `literature_gel_storage.py:55` `implementation_descriptor`:
  `native_schema_sha256` is a digest of a cells schema (data contract) plus versions; `implementation_dependencies` of
  the controlled-response extraction are contract version strings; the "source closure" checks
  (`literature_controlled_response_storage.py:646`, `literature_gel_inputs.py:420`, `literature_gel_storage.py:386`)
  compare literature source records.
- `a104_hpc.py:362` comparison of the plan's staged worker file digest with the digest of the body's `worker_text`
  (transfer record of staged data; it was compared with the removed `worker_sha256` before).
- `native_blast_vdb_utility_execution.py` `runtime_files[].sha256` / `expected_sha256`: the configured external NCBI VDB
  utility and its runtime files (external executable observed at run time, as BLAST/HMMER software).
- `bvbrc_application_definitions.py:34-35,223`, `bvbrc_data_fields.py`: digests of the provider's application specs and
  data-field schemas (third-party data).
- `a104_hpc.py:224`, `a104_native_worker.py:102`, `method_loop/durable.py:572`, `native_hmmer_local.py:42`:
  `Path(__file__)` used to read the staged worker text or set `PYTHONPATH`, not hashed.
- `schema_information_text.schema_fingerprint` and its users, all remaining `manifest_sha256` (34), `source_sha256`
  (68), `fingerprint` (43), `read_bytes()).hexdigest()` (16): schemas, requests, worker/database manifests, receipts,
  sequence files, executables.
- `vendor/SOURCE.*.json`, `method_loop/SOURCE.json` and similar provenance JSON (decision: handled tree-wide later),
  except the two fields recipe section 5 removes.

## Left for decision
None. (The two items fp2/fp3 listed are decided in the task: alimask pin kept; staging accepts equal bytes.)

## Gate (measured, all after the last product edit)
1. Syntax and names: 4,021 `.py` files parsed, 0 syntax errors; bound-name check of the 171 changed `.py` files: 0 global
   names referenced but not bound (the only reports are the 13 pre-existing `import *` modules) (`runs/claude_fp5_002`,
   output `<scratchpad>/fp5/check_002.out`). Import check over all 3,897 product modules of a104 (every `.py` outside
   `tests/`) prints `{}` (`runs/claude_fp5_003`).
2. Tests: all 87 test files, one file per launcher run, isolated form (`runs/claude_fp5_101..187`, logs
   `runs/claude_fp5_homes/101..187.log`, junit in each run directory), 10:09:40-10:13:14. 0 collection errors.

   | | files | collected | passed | failed | errors | skipped | test seconds |
   |---|---|---|---|---|---|---|---|
   | before (`runs/claude_rec4_107..193`) | 87 | 2,107 | 2,041 | 66 | 0 | 0 | 415 |
   | expected, written down before the pass (`<scratchpad>/fp5/expected.txt`) | 87 | 2,107 | about 2,027 | about 80 | 0 | 0 | well under 415 |
   | measured | 87 | 2,107 | **2,041** | **66** | 0 | 0 | 152 (3.5 min wall) |

   Per-file passed/failed counts are identical to before for all 87 files; the 66 failures are the same 66 test ids
   (`diff` of the FAILED lines of `runs/claude_rec4_163/stdout.log` and `runs/claude_fp5_homes/157.log`: equal), all in
   `tests/proteome_partner/test_proteome_saved_host.py` with the same pre-existing cause
   (`AppServiceCustodyError: bvbrc_appservice_custody_parent_selection_invalid` -> `original_assignment_transport_
   mismatch`). **0 tests that passed before fail now.** The expectation of 14 failures awaiting shared test fixes was
   wrong because the shared-root agent had already changed the four shared check modules in the working tree.
   Awaiting shared test fixes: none. Speed: `scientific_process/tests/test_head_task.py` 226 s -> 6 s.
3. Site counts (lines/files, whole area incl. tests and fixtures, `49dee49e6` -> now):

   | grep | before | after | what remains |
   |---|---|---|---|
   | `implementation_sha256` | 146/67 | 8/5 | `ExecutionClass.implementation_sha256` (7) and the `_TRACKING` name |
   | `implementation_record`, `SOURCE_PATHS`, `CALLABLE_SHA256`, `resource_implementation_bytes`, `_context_source_key`, `module_sha256`, `callable_sha256`, `source_function_sha256`, `code_manifest`, `REQUIRED_MODULES` | 0/0 | 0/0 | |
   | `_binding_source_bytes` | 69/63 | 0/0 | |
   | `_AXIS_DIRECTORY` | 61/61 | 0/0 | |
   | `_context_source` | 55/23 | 10/8 | `caller_context_source_ref` / `supplied_context_source_refs` (record field names) |
   | `manifest_sha256` | 74/19 | 34/18 | saved worker/database manifests, receipts (data) |
   | `_verify_implementation` | 6/2 | 0/0 | |
   | `implementation_identity` | 20/5 | 0/0 | |
   | `adapter_sha256`, `script_sha256` | 4/1 each | 0/0 | |
   | `fingerprint` | 45/12 | 43/11 | schema and request digests, prose |
   | `SOURCE_.*SHA256` (regex) | 6 lines | 0 | |
   | `template_sha256` | 2/2 | 0/0 | |
   | `read_bytes()).hexdigest()` | 41/24 | 16/12 | requests, artifacts, executables, Biopython extension |
   | `rglob('*.py')` | 2/2 | 0/0 | |
   | `worker_fingerprint` | 2/1 | 0/0 | |
   | `worker_sha256` | 8/4 | 1/1 | captured real HPC result fixture (data) |
   | `python_sha256` | 8/4 | 0/0 | |
   | `producer_verification`, `package_files` | 20/4, 10/4 | 0/0 | |
   | `producer_manifest` | 91/13 | 28/8 | BV-BRC provider data role, `attempt_output_version` labels |
   | `source_pins` | 4/1 | 4/1 | field name of the fluorescence intent; rows are `{path}` |
   | `implementation_files` | 31/12 | 27/9 | path/module lists (13a/13b, execution selection, prompt key list) |
   | `driver_runtime` | 35/15 | 21/2 | record name (13a keeps the record); 13 files lost it with the rosters |
   | `verify_driver_runtime` | 3/2 | 3/2 | kept by 13a without digests |
   | `source_sha256` | 71/24 | 68/21 | alignment/sequence source files, native receipts (data) |

## Handoffs
- Applied: no row is addressed to `fp5`. The shared fixtures named in rows 437/438/453/454 are already changed in the
  working tree by the shared-root agent (`root/tests/hpc_prediction_behavior.py`, `hpc_launch_task_checks.py`,
  `hpc_planning_allocation_task_behavior.py`, `hpc_prediction_prompt_behavior.py`), so no a104 test awaits them.
- Written (`handoffs.tsv` rows 470-471): to `fp-top,fpr` — the shared `fluorescence_software_v1` record
  (`root/library/native_fluorescence_contracts.py` PIN_SCHEMA/_pin, `tests/test_native_fluorescence_contracts.py`, the
  operator configuration); the fluorescence intent producer is already row 467 (fp4). To `fp-top` — one NOTICE for
  tests that drive a104 (forms gone, strict `root_action_boundary`, unconditional `pending_work` and ledger joins).
  No new row for the protein-structure (rows 443-445, 452), driver-runtime (447-450) or BLAST-database producer (431-432)
  records.

Not verified by running: no a104 test exercises the native BLAST database drivers/result workers, the HMMER preparation
result publication, `native_driver_runtime.py` (including the new byte comparison in `_copy_source`),
`a104_native_worker.py`, the fluorescence and protein-structure library records or `terminal_scientific_evidence.py`;
those edits are covered by the syntax, bound-name and import checks only (the BLAST database edits are the ones a101's
tests exercise in a101). Tests outside a104 were not run.
