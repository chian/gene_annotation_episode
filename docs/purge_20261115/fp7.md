# fp7 — a106: code that fingerprints the codebase removed (16 November 2026)

Area: `gene_annotation_episode/episodic_workflow/root/a106/` (`R/` below). Brief: `FP_BRIEF.md`. Shapes: `fp_recipe.md`
(sections 1-20 followed; a106 additions appended as section 21). Deleted tests: `fp7_deleted_tests.tsv` (one
parametrized case). Per-file gate table: `fp7_gate_results.tsv`. Comparison base: commit `d2f371805` (Checkpoint 17,
HEAD when the task started). No git add/commit, no sub-agents, one launcher command at a time (slot `fp7`).

## Outcome
Every a106 row of `h5_self_hashing.tsv` (118) and of `pa106_self_hashing.txt` (131 sites) is handled: 85 h5 texts are
gone, 1 file was already gone (`literature_controlled_response_v2_inputs.py`, deleted by cr1), 23 lines remain only
with the digest part removed (binding records, `episode_composition`, `durable.py`, runtime/independent estimator
versions ...), 9 are kept on purpose (see "Kept"). Removed: binding digests (literature, scientific process, progress
assessment), hub helpers and the roster module `R/literature_implementation_sources.py`, the runtime-binding digest,
the vendored-estimator pin, the acquisition observer/transport digests, the BV-BRC adapter pin (TnSeq/RNASeq adapter
roster, analysis contract, saved facts, publication, schemas, relation check), tool-source pins (FBA source function,
protein disorder, fluorescence report profiles, RNA worker source) and the 13a/13b/19 pins of the
`library/retained_input_authority` readers. The three sibling suspects are carried over with a106 evidence.
The A106 literature grading code (graders, subscoring sheets, `investigation_finding`, credit, iterator) is not edited;
the only line touched in a grading module is an unused import (`library/literature_assay_grading_storage.py:6`).
Nothing is left for decision.

Change against `d2f371805`: 108 files (107 modified, 1 deleted), +150 −658 lines; product `.py` 101 files, 3 JSON files
(+4 −40), 4 test files (+5 −4).

How it was done:
- Three-way merges (`git merge-file`, arm name replaced) for the 83 a106 files with the same relative path as a file
  changed by a105 (`06214e132→d2f371805`), a104 (`49dee49e6→06214e132`), a107 (`9fc7d3e54→6737ddfe8`) or a102
  (`330ef3fe7→9fc7d3e54`), each from the sibling whose pre-task file is closest to a106's (table:
  `<scratchpad>/fp7/merge_status.tsv`).
  - 41 clean, taken after reading each diff: from a105 24 (`application_execution_binding`, `episode_composition`,
    `numerical`, `ordinary_execution`, `scientific_process/scientific_contracts` and 19 `library/retained_input_authority`
    files incl. both `bvbrc_appservice_schemas.json`), from a102 11 (`composition_information`, `decision_history`,
    `method_loop/durable`, `execution_progress`, `vendor/SOURCE.nano-graphrag.json`, 6 `execution_contracts.py` hubs),
    from a104 3 (`runtime`, `component_assessment_dependencies`, `bvbrc_appservice_schemas.json`), from a107 3
    (`api_bvbrc_appservice`, `bvbrc_appservice_adapters`, `bvbrc_appservice_publication`).
  - 42 with conflicts: `independent_execution.py` (took the removal side), `chromatin_interaction_contracts.py` (took
    a105's schema line, kept a106's import position), `acquisition.py`, `bvbrc_appservice_contracts.py` (a106 shapes,
    edited directly); the 28 literature binding records/hubs, 2 progress binding records and
    `scientific_process/binding_record.py` differ in shape from every sibling and were edited with asserted perl
    (`<scratchpad>/fp7/m1.pl`); 6 `execution_*/binding_record.py` and `scientific_process/episode.py` already had no
    digest in a106 (ours kept).
- a106-specific: `m2.pl` (acquisition), `m3.pl` (adapter pin, analysis contract, six literature execution hubs, roster
  import), module deletion, two test edits; then two test-fixture fixes for the `decision_history` merge (below).

## Removed, by class
Counts `lines/files` over tracked files of the area, `d2f371805` → now.

### Class 1 — runtime-computed binding identity
- `implementation_sha256` 83/54 → 8/5 (kept: `ExecutionClass.implementation_sha256` 5 lines, two `_TRACKING` name
  filters in `library/literature_experimental_prompt.py:30,35`, the tracking-filter test
  `tests/test_private_literature_tracking_projection.py:36`).
- 17 binding records no longer compute or carry the digest: 14 literature (rglob of the arm + four context files),
  `scientific_process/binding_record.py` (`rglob('*.py')`), `execution_progress_assessment/binding_record.py` and its
  `scientific_process/` mirror (own `_binding_source_bytes` with `monitor_prompt`/`progress_information_credit`).
  Records are `{version, binding_id, configuration}`; `execution_progress.as_record` loses the hash of its own file.
- `_binding_source_bytes` 30/28 → 0, `_AXIS_DIRECTORY` 54/40 → 0: 14 literature hubs (`source_contracts.py`, also
  `import hashlib`, `from pathlib import Path`), 12 `execution_contracts.py` hubs (first `Path` import kept: imported by
  `configuration.py`), 2 progress records. Deleted module: `R/literature_implementation_sources.py` (roster; only importer
  was an unused import).
- Consumers: `scientific_process/process_state.restore_closed_process` (a104 shape; code
  `scientific_closed_implementation_identity_invalid` gone), `episode_composition.scientific_binding_compatible`,
  `independent_execution` (`implementation_sha256()`, runtime-binding field, `identity_conflict` check, `__all__`),
  `method_loop/durable.validate_commission`, `application_execution_binding.py`, `ordinary_execution.py` (spreadsheet
  timing class no longer hashes adapter/worker sources).

### Class 2 — worker/job implementation manifests and software-record pins
- Acquisition (recipe 8): observer `adapter_sha256` + `response_capture_adapter_changed`, `script_sha256` in three
  transport/diagnostic dicts.
- BV-BRC adapter pin (recipe 6, a106 layout = recipe 21): `bvbrc_intervention_bundle_adapter._DEPENDENCIES` +
  `implementation_sha256()` and the tnseq/rnaseq re-exports; `bind_adapters` binds the module; `publication_inputs`,
  `_validate_inputs` configured-row check, `_grade`, `read`, `result_identity`, `_bundle_content_kind`; analysis
  contract (`prepare_analysis_contract`, 15 copies) without the digest; `bvbrc_application_facts`
  `original_adapter_pin_required`; relation check `publication_adapter_binding_conflict`; schema entries in both
  `bvbrc_appservice_schemas.json`.
- 13a/13b/19 readers in `library/retained_input_authority` (clean a105 merges): ATAC `_DRIVER`, RNA software record and
  `COMPATIBILITY_FIELDS`, protein-structure `Software`/`ImplementationFile`, genomic-overlap software binding, FBA
  `FBASoftware`, NMF `FILE_SCHEMA`, fluorescence `PIN_SCHEMA`; worker-intent pins `{path}` in
  `native_expression_nmf_preparation`, `native_flux_balance_preparation`, `native_fluorescence_preparation`,
  `atac_differential_result_receipts`, `chromatin_interaction_result_receipts`.
- Codes gone: `appservice_adapter_implementation_conflict`, `appservice_publication_adapter_configuration_conflict`,
  `publication_adapter_binding_conflict`, `original_adapter_pin_required`, `response_capture_adapter_changed`,
  `scientific_closed_implementation_identity_invalid`, `fba_source_function_mismatch`, `invalid_fluorescence_pin`.

### Class 3 — pinned source constants
`SOURCE_.*SHA256` 12/7 → 0: vendored estimator (`numerical.py`, `runtime.py`, `independent_execution.py`, two fields of
`vendor/SOURCE.nano-graphrag.json`), `SOURCE_FUNCTION_SHA256` (+ producer and two schema fields), protein disorder
`SOURCE_SHA256`/`CALLABLE_SHA256` (+ `module_sha256`/`callable_sha256` profile fields), fluorescence `PROFILE_SOURCES`
(operation only), RNA `worker_source_sha256`. `template_sha256` 2/2 → 0.

### Class 4 — tests and fixtures
- Deleted: `tests/test_private_descriptor_reopening.py` case `[hash]` (identity mechanism).
- Edited: `tests/intervention_analysis_fixtures.py:55` (publication inputs without the adapter digest).
- Fixed (caused by the carried-over `decision_history` suspect): `tests/test_private_literature_presentation_boundaries.py:26`
  and `tests/test_private_operational_presentation.py:33` build `CompletionLedger(store, journal)` after the `Journal`, as
  `Workflow.__init__` does (recipe 16, arm-owned doubles). Without it 15+15 tests failed with `no such table:
  runtime_decision_effects`.
- No fixture file carries a removed field.

## Suspects carried over
| suspect | a106 evidence | result |
|---|---|---|
| `runtime.py` completed action whose decision has no `pending_work` | 32 directories save a decision (`saved = {'context': context`); the same 32 add `pending_work` (set comparison equal) | removed (clean merge from a104) |
| `decision_history._tables` | `runtime_estimation_contexts` created by `episode_journal.py:67`, the other two by `episode_completion.py:137,142`; `CompletionLedger` built by every `Workflow` (`runtime.py:759`) | removed (clean merge from a102); two arm-owned test doubles given the ledger |
| `composition_information.restricted_root` default | `Workflow.__init__` always sets the attribute (`runtime.py:711-713`, value `None` or the current version) | strict read after the path conditions (clean merge) |

## Kept, with reason
- `run_statistics.py:65,81-82`, `ordinary_execution.py:69`, `execution_memory.py:219` `ExecutionClass.implementation_sha256`:
  timing-class key (versions only now).
- `library/literature_experimental_prompt.py:30,35` `_TRACKING`: presentation filter of a field name.
- `literature_controlled_response_storage.implementation_descriptor`, `literature_gel_storage.implementation_descriptor`
  (cells-schema digest, versions), `implementation_dependencies` (`literature_controlled_response_inputs.py:1718`, v3
  inputs: contract version strings), source-closure checks (`literature_controlled_response_storage.py`,
  `literature_gel_inputs.py`, `literature_gel_storage.py`: literature source records). A106 grading records; unchanged.
- `native_atac_differential_contracts._MACS` (`python_sha256`, `macs2_sha256` of the external MACS2 install),
  `rna_module_sha256`/`rna_extension_sha256`: external tools observed at run time.
- `scientific_tool_library._file_sha256` (tool index JSON), `schema_fingerprint` users, `manifest_sha256` (6),
  `source_sha256` (23), `read_bytes()).hexdigest()` (7: executables, requests, receipts): data.
- `method_loop/durable.py:572`, `execution_memory.py:65`: `Path(__file__)` for `PYTHONPATH`/locations.
- `R/docs/**` provenance JSON with digests (handled tree-wide later).

## Gate (measured, after the last product edit)
1. Syntax: 1,661 `.py` files, 0 errors; undefined-name check of the 102 changed `.py` files: 0 undefined; the unused
   imports reported are re-export hubs and pre-existing (`acquisition.os`, `episode_composition.import_module`,
   `literature_assay_grading_storage.Path`, `ordinary_execution.version`) (`runs/claude_fp7_001`). Import check over all
   1,535 product modules prints `{}` (`runs/claude_fp7_002`).
2. Tests: all 86 test files, one per launcher run, isolated form (`runs/claude_fp7_101..186`, logs
   `runs/claude_fp7_homes/NNN.log`), 11:01:17–11:05:15; two files rerun after the fixture fix (`runs/claude_fp7_201,202`).
   0 collection errors.

   | | files | tests | passed | failed | errors | skipped | test seconds |
   |---|---|---|---|---|---|---|---|
   | before (rec4 a106 rows; cr1 ran no a106 test file) | 86 | 1,912 | 1,869 | 9 | 0 | 34 | 211 |
   | expected, written before launching (`<scratchpad>/fp7/expected.txt`) | 86 | 1,911 | 1,868 | 9 | 0 | 34 | below 211 |
   | first pass | 86 | 1,911 | 1,838 | 39 | 0 | 34 | 174 (4 min wall) |
   | final (two files rerun after the fix) | 86 | 1,911 | **1,868** | **9** | 0 | 34 | 173 |

   - Passed before, failed in the first pass: 30 tests in `tests/test_private_literature_presentation_boundaries.py` (15)
     and `tests/test_private_operational_presentation.py` (15), cause: my `decision_history` merge (joins
     `runtime_decision_effects` unconditionally) against test fixtures that opened a journal without the completion
     ledger. Fixed in the fixtures; both files pass (64, 120).
   - The 9 failing test IDs are identical before and after (`diff` of FAILED lines; files
     `published_evidence_assessment/tests/test_a106_final_selection_feedback.py` 5,
     `tests/test_literature_perturbation_assessments.py` 2, `..._covariance_meanings.py` 1,
     `..._summary_integration.py` 1): pre-existing.
   - **0 tests that passed before fail now.** None awaits a top-level fixture.
   - Edited code that no a106 test names (covered only by syntax, name and import checks; `decision_history` and
     `composition_information` do run indirectly through `runtime`): `independent_execution`,
     `application_execution_binding`, `scientific_process/process_state`, `ordinary_execution`,
     `bvbrc_intervention_bundle_adapter`, `bvbrc_appservice_adapters`, `api_bvbrc_appservice`,
     `bvbrc_appservice_contracts`, `component_assessment_dependencies`, and the 17 edited
     `library/retained_input_authority` readers.
3. Site counts (lines/files, whole area, `d2f371805` → now):

| grep | before | after |
|---|---|---|
| `implementation_sha256` | 83/54 | 8/5 |
| `_binding_source_bytes` | 30/28 | 0/0 |
| `_AXIS_DIRECTORY` | 54/40 | 0/0 |
| `implementation_record`, `SOURCE_PATHS`, `_verify_implementation` | 0/0 | 0/0 |
| `adapter_sha256` / `script_sha256` | 4/1, 3/1 | 0/0 |
| `SOURCE_.*SHA256` | 12/7 | 0/0 |
| `CALLABLE_SHA256` / `callable_sha256` | 2/2, 1/1 | 0/0 |
| `template_sha256` | 2/2 | 0/0 |
| `source_function_sha256` | 4/3 | 0/0 |
| `worker_source_sha256` | 2/2 | 0/0 |
| `implementation_identity` | 1/1 | 0/0 |
| `python_sha256` | 7/5 | 1/1 (`_MACS`, external) |
| `module_sha256` | 3/3 | 2/2 (`rna_module_sha256`, external) |
| `rglob('*.py')` | 2/2 | 0/0 |
| `fingerprint` | 40/10 | 40/10 (schema digests, prose) |
| `manifest_sha256` | 6/5 | 6/5 (data) |
| `source_pins` | 24/5 | 24/5 (field name; rows are `{path}`) |
| `implementation_files` / `driver_runtime` | 26/12, 15/6 | 26/12, 15/6 (names/paths) |
| `source_sha256` | 27/14 | 23/10 (data) |
| `read_bytes()).hexdigest()` | 15/8 | 7/4 (data, executables) |

## Handoffs
- Applied: row 482 (`fpr → fp-a106`, shared helpers fixed; no a106 file failed for that reason).
- Written: none. Nothing outside a106 uses a removed a106 name (`git grep` of the removed names with `a106` outside the
  area: none); producers of the FBA/RNA/ATAC/fluorescence/NMF records are covered by earlier rows.
