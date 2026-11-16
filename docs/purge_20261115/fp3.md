# fp3 — a103: code that fingerprints the codebase removed; the untraced suspects settled (16 November 2026)

Area: `gene_annotation_episode/episodic_workflow/root/a103/` (`R/` below). Brief: `FP_BRIEF.md`. Shapes: `fp_recipe.md`
(sections 1-15 followed; a103 additions appended as "13a/13b (fp3)", "17", "18"). Deleted tests:
`fp3_deleted_tests.tsv` (none). Per-file gate table: `fp3_gate_results.tsv`. Comparison base: commit `4a3aba851`
(checkpoints 7-9 were committed underneath this task and contain part of it, so `git diff HEAD` does not show the change).

## Outcome
Every mechanism of recipe sections 1-12 that exists in a103 is removed, sections 13a and 13b are applied (decision
given in the task), and three mechanisms that only a103 has are removed: the root and improvement parent records that
hashed a roster of their own files, the code manifest of the staged gene-context HPC worker, and the genomic-overlap
family (result-worker source/interpreter/dependency pins and the driver's interpreter/module digests), for which a103
is both producer and reader. Of the ten listed suspects five are removed and five are kept with their current
producer; one more branch (the a103 twin of a suspect fp2 removed in a102) is removed for the same reason. Nothing in
a103 product code or tests now hashes, records or compares Python source of this repository. What still carries a
digest of program text: one constant kept by analogy with the owner's alimask decision (`_P3_SOURCE_SHA256`, "Left for
decision" 1) and three provenance JSON documents no code reads ("Left for decision" 2).

Change against `4a3aba851`: 184 files (182 modified, 2 deleted), 387 lines added, 2,106 removed; 183 are product
files, 1 is an a103-owned test double (+1 line). No test and no fixture was deleted or changed in content.

How it was done: three-way merges from a101 (base `2ad8be3de`) gave 20 clean files; a103's layout is a102's, so the
rest came from merges from a102 (base `330ef3fe7`; 43 clean, 7 conflicts resolved to the removal side, 6 more clean
for sections 13 and the suspects), two adapter files taken in a101's form, and asserted perl scripts for the shapes
that differ (`<scratchpad>/fp3/*.pl`).

## Removed, by class
Counts are `lines/files` matching the token in the whole area at `4a3aba851` -> now.

### Class 1 — runtime-computed binding identity
- `implementation_sha256`: 133/75 -> 7/4 (the 7 are the kept `ExecutionClass.implementation_sha256`, see "Kept").
- 42 `binding_record.py` no longer compute or carry the digest: 14 literature (`published_evidence_assessment/**`
  and its `scientific_process/` mirror), 10 resource, 6 progress, 6 hpc, 6 homology. `scientific_process/episode.py`
  the same. All records are `{version, binding_id, configuration}` (the homology records keep their other fields).
- a103 only: `R/episode.py` and `R/legacy_improvement/episode.py` `as_record()` (before `:50-56` in both) hashed a
  roster of their own files; the roster module `R/implementation.py` and `R/a103_resource_implementation.py` are deleted.
- `_binding_source_bytes` 156/120 -> 0, `_AXIS_DIRECTORY` 138/94 -> 0: 66 helper definitions (30 `contracts.py`,
  14 `source_contracts.py`, 10 `resource_contracts.py`, 6 `execution_contracts.py`, 6 `binding_record.py`) and 54
  import lists; `resource_implementation_bytes` 21/11 -> 0.
- Consumers: `episode_composition.py` (scientific descriptor field set; the 43 rows of `_PRIVATE_RECONSTRUCTION` and
  the rows of `resource_reconstruction.RESOURCE_RECONSTRUCTION` lose the `fingerprinted` member and its two checks),
  `execution_progress.py` and `homology_progress.py` `as_record()`, `independent_execution.implementation_sha256()`
  with the runtime-binding field (`make_runtime_binding`, `open_commission`, `method_loop/durable.py`,
  `application_execution_binding.py`), `homology_results.py` `parser_implementation_sha256` / `worker_fingerprint`,
  repository sources out of the two timing-class descriptors of `ordinary_execution.py`.

### Class 2 — worker/job implementation manifests
- Native BLAST database result workers (`request.implementation`, `input_implementation_sha256`,
  `implementation_manifest_sha256`, `_implementation`, `_implementation_modules`, `_verify_implementation`,
  `*_implementation_identity`): `implementation_identity` 19/4 -> 0, `_verify_implementation` 6/2 -> 0.
- BV-BRC adapter pin: `implementation_sha256()` and `_DEPENDENCIES` of four adapters (proteome, proteome v2,
  comparative systems, genome alignment; homology via the a102 merge), `bind_adapters`, publication inputs, two
  `*_returns.py` checks, `bvbrc_appservice_schemas.json`; `bvbrc_comparative_systems_host_inputs.py:121` now
  requires only that the selected adapter is bound.
- Acquisition `adapter_sha256` 4/1 -> 0, `script_sha256` 4/1 -> 0.
- Producer manifest of the native BLAST database drivers: `producer_verification` 20/4 -> 0, `package_files`
  10/4 -> 0, `producer_manifest` 96/15 -> 33/10 (BV-BRC's provider data role and three `attempt_output_version`
  labels remain, see "Kept").
- a103 only, recipe section 14 shape: `a103_hpc.py`, `a103_hpc_worker.py`, `hpc_scientific_commission.py`
  (`code_manifest` 10/3 -> 0, `worker_sha256` 6/3 -> 0, `source_snapshot_sha256` 2/2 -> 0). The staged files are
  unchanged; the request is `{version, scientific_profile, biopython_version, plan, assets}`.
- 13a: `native_driver_runtime.py` and `native_hmmer_preparation_result_publication.py` (clean merge from a102):
  the record is `{python_executable, python_version, module_root, implementation_files: [{module}], dependencies:
  [{distribution, version, package_root, files: [{path}]}]}`; `stream_identity`, `file_identity`, `_copy_exact` and
  the re-observation check are gone. `python_sha256` 10/5 -> 0.
- 13a, a103 only — genomic-overlap result worker (`native_genomic_overlap_preparation.py`,
  `genomic_overlap_worker_runtime.py`, reader `genomic_overlap_result_receipts.py:675-702`): `source_pins` rows and
  `interpreter` are `{path}`, dependency file rows `{path}`; sources and interpreter are copied straight into the
  snapshot (before: captured into the Store and compared by sha256/size); `_verify_snapshot` keeps the path and
  read-only-mode checks; `file_pin` and its four helpers are deleted. In the same lines the "legacy" record without
  `dependencies` (no producer: `_snapshot` always writes it) is removed, as the shared-root copy already had.
- 13b: `terminal_scientific_evidence.py` (clean merge from a102) no longer turns `python_sha256` /
  `implementation_files[].sha256` into file pins. a103 only — genomic-overlap driver software binding
  (`native_genomic_overlap_contracts.py:42-64,262-270,825`, `native_genomic_overlap_driver.py:267-292`):
  no `python_sha256`, `ImplementationFile` is `{module}`, `python_observed` is `{version}`.

Codes that can no longer be raised and are gone: `appservice_adapter_implementation_conflict`,
`appservice_publication_adapter_configuration_conflict`, `publication_adapter_binding_conflict`,
`original_adapter_pin_required`, `response_capture_adapter_changed`, the three
`native_blast_database_implementation_*` codes and their three standard-database equivalents, the six `producer_*`
bundle failure codes, `result_worker_original_software_changed`, `result_worker_original_source_size_conflict`,
`terminal_native_implementation_path_unavailable`, `genomic_overlap_preparation_dependency_conflict`, five
`a103_hpc_*` snapshot/manifest codes, `parent_private_homology_source_unavailable`.

### Class 3 — pinned source constants
`SOURCE_SHA256` / `template_sha256` of the vendored estimator (`numerical.py`, `runtime.py`,
`independent_execution.py`, two digests in `vendor/SOURCE.nano-graphrag.json`): `template_sha256` 2/2 -> 0,
`SOURCE_.*SHA256` 8/4 -> 2/1 (the 2 are `_P3_SOURCE_SHA256`). The docstring of
`native_genomic_overlap_contracts.py` no longer claims the definitions equal a contract document by digest. a103 has
none of a101's `retained_input_authority` constants (flux balance, protein disorder, fluorescence, RNA structure).

### Class 4 — tests and fixtures
No a103 test or fixture mentioned any removed field (grep before the first edit: 0 hits), so nothing was deleted.
One a103-owned double edited: `R/tests/resource_task_checks.py:164` sets `root_action_boundary` (suspect below).

## The suspects (task item 4)
| suspect | current producer of the older/absent form | result |
|---|---|---|
| `library/hpc_prediction.py:150-151` (model without a resource metric skips that measurement) | yes: `prior_model` takes `resource_priors` as optional (`:102`) and `hpc_campaign.validate_commission` (`:53`) accepts such a caller-configured commission (`execution_service_setup.py:74-81`); every measured observation carries resource metrics (`hpc_work_planning/forecast_observations.py:37` -> `hpc_history.py:21` -> `hpc_work_planning/measured_history.py:42-62`) | kept; the file is byte-identical to a102's |
| `component_assessment_dependencies.py` `qualification_assessment_changes` (before `:61-72`) | none: no caller in a103 and nothing in a103 writes `source_function_finding` / `partner.requirement_evidence`; a101's copy has neither function | removed with its helper `correction_refs` |
| `homology_results.py:184` (snapshot without captured inventory) | none: the one writer (`extract()`, `INSERT OR IGNORE INTO homology_result_snapshots`) always writes `parse_inventory`, `publication_witness_version`, `native_termination_seen`; the other readers (`homology_recovery.py:28`, `homology_search_receipt.py:29-30`) already read them directly | removed: `recorded_coverage` / `_native_complete` read the fields without defaults |
| `homology_results.py:384` (worker row with no grading outcome) | none: `phmmer_result_worker.py:153-163` always writes `grading_file` or `grading_failure` | removed: `_grading` never returns `None`; the dependent `phmmer_shared_grading_unavailable` code and its reader are gone |
| `api_bvbrc_minhash.py:145-155` (empty result selector) | yes: `{}` is one of the two forms of the published selector schema (`bvbrc_minhash_contracts.py:65-79,166-170`; offered at `api_bvbrc_minhash.py:78`, `execution_progress.py:782`) | kept |
| `provider_jobs.py:21-34` | yes for the `"hmmer"` default: `api_execution.py:228-236,380` writes HMMER requests without a `provider` key. The identity-version comparison admits nothing older, it refuses (`hmmer_request_identity_version_unsupported`) | kept |
| `bvbrc_genome_alignment_inputs.py:405-411` | yes: "older" is an earlier stdout snapshot of the same task among the retained `TaskInfoReceipt` records, not an older format | kept |
| `api_service_execution.py:585,810` `historical_uniprot` | yes: `uniprot_returns.py:471` and `:685` call with `verify_artifacts=False` | kept |
| `practical_execution_records.py:26` `practical.job.*` | yes: current local-job operations (`practical_execution_operations.py:442-443,741-742,839`) | kept |
| `decision_history.py` query built from the tables present | none in product code (`episode_journal.py:67`, `episode_completion.py:137-147`, built by every `Workflow`, `runtime.py:1478`); only shared test fixtures | removed, a102 shape (clean merge); fixtures handed off |
| `composition_information.restricted_root` None default | none in product code (`runtime.py:1413-1415` refuses any other value) | removed, a102 shape: strict read after the path conditions (`composition_information.py:57-60`) |
| not in the list — `runtime.py:516-518`, the a103 twin of fp2's `pending_work` suspect | none: 75 directories save a decision, the same 75 add `pending_work` first (set comparison of the two directory lists: equal) | removed like a102: the `elif packet is not None` branch is gone |

## Kept, with reason
- Decision 2: `hmmer_alignment_preparation_data.py:75-76,146`, `hmmer_alignment_preparation_calculations.py:124`
  (`ALIMASK_PROFILE_EXECUTABLE_SHA256`, `ALIMASK_PROFILE["source_sha256s"]`). Decision 3 has no object in a103 (no
  weight-oracle test, no `SOURCE_PINS.json`).
- `run_statistics.py:65,81-82` `ExecutionClass.implementation_sha256`, set at `execution_recording.py:141` and
  `ordinary_execution.py:60,99`, read at `execution_memory.py:219`: timing-class key from an external executable's
  digest; `ordinary_execution.py:55` `native_pairwise_aligner_sha256` (Biopython's compiled extension).
- `numerical.py:39,69` `SOURCE_REVISION`: upstream commit label, compared with nothing.
- `native_genomic_overlap_contracts.py:32,447-448` `_REQUIRED_MODULES` (module names, no digests) and
  `bedtools_sha256` (`native_genomic_overlap_driver.py:334-347`): configured external executable observed at run time.
- `native_genomic_overlap_preparation.py:294` `GENOMIC_OVERLAP_DEPENDENCIES_SHA256`: digest of the dependency record.
- `a103_hpc.py:148` and `hpc_campaign.py:161-167`: digests of the staged files of a plan compared with the request
  body (transfer record of staged data, kept in a101 and a102 too).
- `native_blast_acquisition.py:27`, `native_hmmer_acquisition.py:23`, `native_genomic_overlap_results.py:39`: the
  vocabulary value `original_producer_manifest_and_verified_file_digests` (credit key, as in a101/a102).
- `execution_job_submission/**/closed_credit.py:74,88` `binding_sha256`: digest of the binding record, which no longer
  contains a source digest.
- All remaining `manifest_sha256` (34), `source_sha256` (109), `fingerprint` (74), `read_bytes()).hexdigest()` (20)
  sites: requests, schemas, database and worker manifests, receipts, sequence files, external executables.
- `R/tests/fixtures/genomic_overlap/returns/FIXTURE_PINS.json`: digests of three data fixtures.

## Left for decision
1. `bvbrc_genome_alignment_inputs.py:36,659` `_P3_SOURCE_SHA256`: a hard-coded digest of one inspected version of
   the BV-BRC application source, compared with a supplied `producer_source` content binding. It is a pinned constant
   for third-party source, which the brief puts in scope; a match is what admits the retained-source default recipe
   (`progressiveMauve`) when no command was observed (`:712-721`), so removing or loosening it changes which
   invocation is inferred for grading. Kept on the reasoning of the owner's alimask decision. The same constant is in
   `root/library/bvbrc_genome_alignment_inputs.py:36`.
2. `R/vendor/SOURCE.infrastructure.json`, `R/method_loop/SOURCE.json`, `R/method_loop/LOCAL_PATCHES.json`: provenance
   documents listing sha256 of vendored and repository source files (for example `target_sha256` of
   `gene_annotation_episode/providers.py`). No code reads them; a101 and a102 left theirs. Say if they should go.
3. Consequence of removing the staging digest, to confirm: `native_genomic_overlap_preparation._stage` (`:265-285`)
   used to accept an already staged file when its digest matched; without a digest an existing target is refused
   (`genomic_overlap_preparation_snapshot_conflict`), so a preparation interrupted while staging its snapshot is not
   resumed in the same directory. The alternative is a byte comparison with the current source file.

Seen while editing, not changed:
- `native_genomic_overlap_preparation.py:353-354`: `_pins` requires `source_snapshot/gene_annotation_episode/<name>.py`
  for the names in `_REQUIRED_SOURCES`, but the a103 modules are staged under
  `source_snapshot/gene_annotation_episode/episodic_workflow/root/a103/`. The requirement cannot hold for a real
  snapshot, so the a103 genomic-overlap result-worker preparation cannot complete as written (same before this task;
  the shared-root copy has a corrected `_recorded_source_paths`). No a103 test covers this module.
- `native_genomic_overlap_preparation.py:293` and `a103_hpc_worker.py:54-55` set `OMP_NUM_THREADS` /
  `OPENBLAS_NUM_THREADS` / `MKL_NUM_THREADS` to 1 for the worker; the shared-root copy refuses these variables.
- `waiting.completed_action_context` still accepts `pending_at_selection=None` (`waiting.py:630`); no a103 caller
  passes it any more (same note as fp2).

## Gate (measured)
1. Syntax and imports, after the last product edit: 3,412 `.py` files parsed, 0 syntax errors; symtable check of the
   180 changed `.py` files: 0 global names referenced but not bound that were bound before (the one report,
   `independent_execution.py` `options`, is identical at `4a3aba851`) (`runs/claude_fp3_006`). Import check over all
   3,262 product modules prints `{}` (`runs/claude_fp3_007`).
2. Tests: all 98 test files, one file per launcher run, isolated form, after the last edit (`runs/claude_fp3_201..298`,
   logs `runs/claude_fp3_homes/201..298.log`). 0 collection errors.

   | | files | collected | passed | failed | errors | skipped | test seconds |
   |---|---|---|---|---|---|---|---|
   | before (`runs/claude_rec3_a103f_001..098`) | 98 | 4,331 | 4,329 | 2 | 0 | 0 | 890 |
   | expected, written down before the first pass | 98 | 4,331 | 4,329 | 2 | 0 | 0 | about 890, 16 min wall |
   | expected, written down before the final pass | 98 | 4,331 | 4,308 | 23 | 0 | 0 | about 220, 5 min wall |
   | measured, final pass | 98 | 4,331 | **4,308** | **23** | 0 | 0 | 214 (280 s wall) |

   The first expectation was wrong in two ways that the first pass (`claude_fp3_101..198`) showed: the removal makes
   the tests four times faster (`tests/test_private_resource_tasks.py` 510 s -> 30 s: every `as_record()` used to read
   the source tree), and shared fixtures fail (below).
   Per-test comparison with the previous junit files:
   - Failed before, fails now (1): `tests/test_a103_context.py::
     test_runtime_parent_receives_exact_component_operands_from_automatic_grading` (stand-in workflow has no
     `shared_information_repository`).
   - Failed before, passes now (1): `tests/test_a103_real_detection.py::
     test_real_complete_search_scoped_absence_unknown_and_cooccurrence` — 2 passed in both passes of this task (the
     systemd unit started), so it was not rerun.
   - Passed before, fail now (22), all in checks that the a103 test files import from `root/tests/`:
     - 20 x `sqlite3.OperationalError: no such table: runtime_decision_effects` (suspect `decision_history`): the
       shared fixtures `root/tests/hpc_launch_task_checks.py:39`, `hpc_planning_allocation_task_behavior.py:179`,
       `hpc_prediction_prompt_behavior.py:136` open a journal without the completion ledger. 10 a103 files, 2 tests
       each: 4 x `execution_job_submission/tests/test_private_launch.py`, 4 x `tests/test_planning_allocation_task.py`,
       2 x `hpc_resource_prediction/tests/test_prediction_prompt.py` under `hpc_work_planning/` and
       `scientific_process/hpc_work_planning/`. Verified: with a ledger built for every a103 journal by a pytest
       plugin kept in the scratchpad (not in the repository) the 10 files pass completely, 204 passed
       (`runs/claude_fp3_501..510`).
     - 2 x `KeyError: 'implementation_sha256'`: `root/tests/hpc_prediction_behavior.py:177` asserts the digest
       length; `test_saved_description_config_and_prediction_goal` in the two a103
       `hpc_resource_prediction/tests/test_prediction_behavior.py`.
     Both need an edit in `root/tests/`, outside this area; handoff rows written (fp2 wrote the same two for a102).
     The 20 can be made to pass without `fp-top` by reversing the `decision_history.py` change
     (`git diff 4a3aba851 -- R/decision_history.py`); I left it as fp2 did.
   - One regression of my own appeared in the first pass and is fixed: 40 tests of
     `tests/test_private_resource_tasks.py` failed with `too many values to unpack` because
     `resource_reconstruction.RESOURCE_RECONSTRUCTION` still had the `fingerprinted` member; the final pass has
     1,400 passed there.
3. Site counts: next section.

Not verified by running: no a103 test covers the native BLAST database drivers and result workers, `a103_hpc*`,
`native_driver_runtime.py`, the HMMER preparation result publication, `terminal_scientific_evidence.py` or any
genomic-overlap module. Those edits are covered by the syntax, bound-name and import checks only (the BLAST database
edits are the ones a101's tests exercise in a101). Tests outside a103 were not run.

## Site counts for the greps of the brief (lines/files, whole area incl. tests and fixtures)
| grep | before | after | what remains |
|---|---|---|---|
| `implementation_sha256` | 133/75 | 7/4 | `ExecutionClass.implementation_sha256` |
| `implementation_record` | 0/0 | 0/0 | |
| `_binding_source_bytes` | 156/120 | 0/0 | |
| `SOURCE_PATHS` | 0/0 | 0/0 | |
| `manifest_sha256` | 81/22 | 34/18 | saved worker/database manifests, receipts, allocation manifests (data) |
| `_verify_implementation` | 6/2 | 0/0 | |
| `adapter_sha256` | 4/1 | 0/0 | |
| `script_sha256` | 4/1 | 0/0 | |
| `fingerprint` | 82/41 | 74/39 | input-byte and schema digests; prose in docstrings and two instruction files |
| `SOURCE_.*SHA256` | 8/4 | 2/1 | `_P3_SOURCE_SHA256` (Left for decision 1) |
| `CALLABLE_SHA256` | 0/0 | 0/0 | |
| `template_sha256` | 2/2 | 0/0 | |
| `read_bytes()).hexdigest()` | 41/27 | 20/15 | requests, artifacts, receipts, executables; one Biopython extension |
| `resource_implementation_bytes` | 21/11 | 0/0 | |
| `_context_source_key` | 0/0 | 0/0 | |
| `source_pins` | 11/2 | 11/2 | the field name of the genomic-overlap intent; its rows are `{path}` now |
| `module_sha256`, `callable_sha256`, `source_function_sha256` | 0/0 | 0/0 | |
| `implementation_identity` | 19/4 | 0/0 | |
| `worker_fingerprint` | 2/1 | 0/0 | |
| `source_sha256` | 111/31 | 109/29 | alignment/sequence source files and native receipts (data) |
| `rglob('\*.py')` | 2/2 | 0/0 | |
| `driver_runtime` | 26/4 | 25/4 | the record name (13a keeps the record) |
| `implementation_files` | 20/11 | 10/5 | module-name lists (13a/13b) and one prompt key list |
| `verify_driver_runtime` | 3/2 | 3/2 | kept by 13a without digests |
| `result_worker_original_software_changed` | 1/1 | 0/0 | |
| `REQUIRED_MODULES` | 2/1 | 2/1 | module-name roster (13b keeps name checks) |
| `producer_manifest` | 96/15 | 33/10 | BV-BRC provider data role; three `attempt_output_version` labels |
| `producer_verification` | 20/4 | 0/0 | |
| `package_files` | 10/4 | 0/0 | |
| `python_sha256` | 10/5 | 0/0 | |
| `code_manifest` | 10/3 | 0/0 | |

## Handoffs
- Applied: none were addressed to `fp3`. The older rows to `pa103` (355, 361, 415-417, 421, 422, 425, 274) are
  already in effect (checked by grep).
- Written (`handoffs.tsv` rows 453-462): to `fp-top` — the digest assert at
  `root/tests/hpc_prediction_behavior.py:177` and the three shared fixtures without a completion ledger (both now
  also needed for a103); three notices (annotation-root doubles need `root_action_boundary`; hand-saved decisions
  need `pending_work`; the list of forms gone from a103 for parametrized tests); the shared-root copies of the
  genomic-overlap result-worker pins and of the genomic-overlap software binding (not yet listed by fp1/fp2); the
  operator resource configuration of a genomic-overlap resource; a notice about `_P3_SOURCE_SHA256` in the shared
  root. To `fp1` — the two `homology_results.py` branches that a101's copy still has.
- No row for `hpc_scientific_commission` / `component_native_*` (fp2 row 451 covers the shared producer) or for the
  13a/13b producers already listed in rows 443-450.
