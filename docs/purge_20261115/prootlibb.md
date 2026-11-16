# prootlibb — shared root library purge, list b (289 modules)

Scope: `native_*` (except atac/chromatin/flux), `blast_*`, `hmm*`, `hmmer_*`, `nhmmer*`, `infernal_*`, `rfam_*`,
`homology_*`, `homer_*`, `macs2_*`, `lumpy_*` in `gene_annotation_episode/episodic_workflow/root/library/`.

## How it was done (read this first)
- The planned fan-out to three sub-agents was refused (concurrent subagent limit), so one agent covered all 289 files.
- Coverage is by keyword sweeps over the whole list (historical/legacy/upgrade/migrat/previous/prior/compat/packet/
  V1-V2/anyOf/version-in/memory values/numbered work references) and reading every hit region that looked like
  acceptance of an older form. Files with no hits were NOT opened one by one.
- The parent's mid-task clarification was applied: module-path / source-location / implementation-version
  alternatives are left untouched; record-form alternatives and second memory values are removed.

## Totals (`git diff --numstat` over list b)
46 files touched: 45 edited, 1 deleted; +113 / -7,984 lines (7,695 of the deletions are the one deleted module).

## Removed, by class
Class 1 — parameters / branches / helpers for the past (7 mechanisms, about 25 sites)
- `native_fluorescence_contracts.validate_fluorescence_policy(fresh=)` and the three `fresh=True` call sites
  (`native_fluorescence_local._allocation`, `_preparation`, `_driver`).
- `native_expression_nmf_contracts.expression_nmf_environment(recorded_environment=)` with the OPENBLAS/OMP
  thread-ceiling variant; its two callers in list b; the 20 GiB + ceilings alternative in
  `native_expression_nmf_contracts` and `native_expression_nmf_preparation` (two `require` blocks collapsed, one
  duplicate deleted).
- `native_genomic_overlap_preparation`: `historical` environment (thread ceilings) alternative; the
  "legacy receipts" branch for records without `dependencies` (now a required field in intent, execution,
  `_environment`, `_pins`, `_execution_fields`).
- `native_hmmer_preparation_result_worker.effective_metadata(include_map_context=)` and the publication-side
  "historical absence" selection.
- `infernal_search_contracts._locator(legacy=)` (every caller passed True; behaviour kept, parameter gone).
- `native_blast_result_worker._hsp_values(archived_values=)` v1 read path.
- `native_hmmer_preparation_contracts.recorded_operation_matches_compiled`: tolerance for old hmmsim records
  lacking `--fast/--tlinear`; now exact digest equality.

Class 2 — more than the current record version (9 mechanisms, about 30 sites)
- `native_blast_standard_database_result_worker` / `_result_publication`: `result_worker_manifest_v1` with
  `calculations_v1` (`_ROLES_V1`, `_ROLES_V2`, `_MANIFEST_ROLES`); only manifest v2 is accepted.
- `native_blast_result_publication` / `native_blast_hsp_views`: `native_blast_prepared_grading_v1`,
  `native_blast_retained_grading_v1`, sheet/scores `collection_v1` (`_VERSIONS` table and v1 branches).
- `rfam_batch_infernal.upgrade_saved_rfam_search_sheet`, `infernal_search_cells.upgrade_saved_infernal_search_sheet`
  deleted; `validate_infernal_search_sheet` now requires `lineage is None`.
- `hmmer_preparation_result_views`: empty `calibration` accepted for "older saved extractions" removed.
- Memory policy (owner decision, 5 GiB): `HISTORICAL_POLICY` deleted (fluorescence); second value 21474836480
  removed from `native_genomic_overlap_job_schema` (check + schema enum), `native_protein_structure_job_schema`
  and `native_rna_structure_contracts` (`_RECORDED_MEMORY_BYTES`), `native_protein_structure_contracts`
  (`ProteinPolicy` literal), `native_blast_utility_contracts` (VDB allocation check).
- BEHAVIOUR CHANGE to confirm: `native_homer_execution.POLICY['memory_bytes']` 21474836480 -> 5368709120. This was
  the live HOMER launch policy, not a recorded alternative; changed because the clarification says any product
  POLICY above 5 GiB becomes the bound.

Class 6 — module that exists only for the past (1)
- `blast_utility_historical_fact_schemas.py` deleted (7,695 lines). Its only importer is
  `root/communication.py:302-304`, outside the library.

Class 7 — narration (about 24 sites in 21 files)
- References to verification directories, packet425, work247, pure253, by327, to342/actual342/strict342,
  "initial port", "historically embedded", "extracted from <module>" docstrings (7 `*_job_schema` / `*_schema`
  modules), "historical v1 shapes", "legacy conversion" docstrings in rfam/infernal.

Classes 3, 4, 5: nothing removed in this list (no digest tables edited, no saved sources, no tests).

## Public names removed / signatures changed
Recorded in `<S>/prootlibb_external.tsv` (20 rows). The ones other areas certainly reference:
- `blast_utility_historical_fact_schemas` module — `root/communication.py:302-304`.
- `native_fluorescence_contracts.HISTORICAL_POLICY` — `root/tests/fluorescence_module_identity_checks.py:76`.
- `validate_recorded_genomic_overlap_policy` now refuses 20 GiB — used by `root/genomic_overlap_result_receipts.py`,
  `root/expression_nmf_result_receipts.py`, `root/molecular_result_actions.py`.
- `native_homer_execution.POLICY` value; `_RECORDED_MEMORY_BYTES` (rna, protein structure).

cross.tsv: wrote 1 row (`expression_nmf_result_worker.py:119` must drop `recorded_environment=`); a later grep shows
the argument is gone from that file, so its owner has applied it. No rows addressed to list b.

## Left because it is a file / digest / version registration (not edited)
- `native_blast_local.py:44`, `native_blast_utility_local.py:43`, `native_blast_masking_local.py:43`
  `_historical_command` (old `-m gene_annotation_episode.<driver>` command line and its base environment).
- `native_hmmer_preparation_result_publication.py:46-83,229-245,325,393,421` (`_HISTORICAL_WORKER_MODULE`,
  `_HISTORICAL_VERIFY_MODULE`, `_HISTORICAL_WORKER_PROGRAM`, `_LEGACY_ROOT_WORKER_PROGRAM`).
- `native_hmmer_preparation_local.py:98` `historical_command`.
- `native_fluorescence_preparation.py:29,113` `HISTORICAL_WORKER_MODULE`; `native_fluorescence_contracts.py:34-38,
  198-211` `LEGACY_IMPLEMENTATION_NAMES` and the two-layout `_software_implementation_root`.
- `native_macs2_peak_execution.py:34,111,182` `LEGACY_DRIVER_MODULE`.
- `native_lumpy_execution.py:39-40,101-103,181-185,488-502` `DRIVER_MODULE` vs `CURRENT_DRIVER_MODULE`, including
  the thread-ceiling environment tied to the original driver identity.
- `native_homer_execution.py:45-46,174,327,606` `homer_native_software_v1` vs `CURRENT_SOFTWARE_VERSION` /
  `CURRENT_WORKER_MODULE`; `homer_tf_worker_ports.py:15-33` `_LEGACY` module prefix.
- `native_genomic_overlap_preparation.py:363-369,386` `_recorded_source_paths` (two module/source layouts);
  `native_expression_nmf_preparation.py:~86` second accepted worker module in the frozen command.

## Live despite its name (kept)
- Mode-keyed version families, all written today: BLAST utility job v1/v2/v3 and operation v1/v2/v3
  (`native_blast_utility_contracts.py:433-435`), `LEGACY_MODES` (the five original program/mode pairs, `:35`),
  `_HISTORICAL_OPERATION_SCHEMA` (`:58`, the operation schema of v1/v2 jobs), result selector v1/v2 and
  `_LEGACY_FACT_SCHEMAS` (`blast_utility_result_views.py:103,162,541`), plan/manifest v1/v2 by VDB
  (`native_blast_utility_result_worker.py:604`).
- Program-keyed: `native_blast_database_result_worker.py:1583` manifest v1/v2/function, sheet_set v1/v2.
- Option-keyed sheets: `blast_iteration_inputs.py:361-390` (v1/v2/v3), `blast_database_grader.py:1070-1108`,
  `blast_sequence_database.py:250-252`; `tool_grading_artifact_v1/v2` (`native_protein_structure_worker.py:146`);
  fluorescence job/manifest v1/v2 by binding (`native_fluorescence_tool_info.py:44`).
- `_validate_historical` (`native_blast_utility_returns.py:157`, `native_blast_masking_returns.py:154`): validates
  a form saved earlier in the same run.
- `_historical_store_root` / `_historical_path` (`macs2_peak_tools.py:339`, `homer_motif_tools.py:228`): the
  store root recorded by the same run's worker.
- `legacy` local-attempt layout beside `terminal_plan_identity` (`native_fluorescence_contracts.py:527`,
  `native_expression_nmf_contracts.py:~150`): the current local-job directory layout.
- Homology adapter: `_legacy(context)` (`homology_resource_assignment.py:109`), `LEGACY_HANDOFF_SCHEMA` /
  `_legacy_assignment` (`native_event_information.py:21,167`), `Legacy*Episodes` from the `legacy_annotation` home
  (`homology_episode_family.py:14-16,54`).
- Field names in current records: `legacy_pointer`, `old_style_index`, `legacy`/`-legacy` BLAST+ flags,
  `earlier_search_key`, `include_legacy_clipping`, `representation.legacy` and `legacy_hmmer2` (HMMER2 format,
  `hmmer_model_legacy.py`, `hmmer_model_binary2.py`), `infernal_cm_legacy_ascii`, `PACKET_VERSION`.

## Uncertain — kept, needs a decision
- `_retain_correspondence=False` output form (calculations_v1) in `native_blast_standard_database_calculators.py:251,
  329,628`; the worker always passes True, but the same private flag exists in `blast_database_grader`,
  `blast_sequence_database` and another list's `biopython_pairwise_grader`, and a101 tests call the default form.
- `rfam_batch_tblout_parse_result_v1` / `infernal_search_sheet_v1` in `rfam_batch_table_grader.py:21-25` and
  `rfam_batch_table_views.py`: no library code builds this form any more (the builder writes
  `rfam_batch_parse_result_v2`), but `root/rfam_batch_returns.py:341` validates it. Looks old-only; not removed.
- `RFAM_LEGACY_RESULT_SELECTOR_SCHEMA` (`rfam_batch_contracts.py:489`, selector v1 and v2):
  `root/tests/test_api_rfam_service.py:30` uses v1 as the normal selector.
- HMMER alignment "optional new facts" (`input_decoding`, `source_alphabet`, ...) accepted absent:
  `hmmer_alignment_preparation_data.py:446`, `hmmer_alignment_input_validation.py:808`,
  `hmmer_alignment_preparation_calculations.py:401,473`. Not established whether absence is still produced.
- `homology_result_publication.py:66` (row with neither `grading_file` nor `grading_failure`) and
  `homology_result_coverage.py:105-123` (`snapshot.get` for snapshots without inventory).

## Import check
`runs/claude_prootlibb_001`: all 288 remaining modules of list b import (`{}`).
No test files were run (the library has none; tests in other areas that use the removed names were not touched).

## Mechanical pass (third instruction: remove old module-path / layout / software-version alternatives)
This supersedes the section "Left because it is a file / digest / version registration": everything listed there is
now removed. Only the current library path, layout or version is accepted; anything else hits the existing refusal.
Current implementation-digest pin code (`verify_driver_runtime`, `validate_driver_runtime`, `implementation_files`
digest checks) was not touched.

Removed (22 files)
- Old `-m gene_annotation_episode.<driver>` reservation commands: `_historical_command` and its base-environment
  branch in `native_blast_local.py`, `native_blast_utility_local.py`, `native_blast_masking_local.py`;
  `historical_command` in `native_hmmer_preparation_local.py`; `original_command` in `native_infernal_local.py` and
  `native_infernal_preparation_local.py`; the two-command tuple in `native_hmmer_local.py`.
- `native_hmmer_preparation_result_publication.py`: `_HISTORICAL_WORKER_MODULE`, `_HISTORICAL_VERIFY_MODULE`,
  `_HISTORICAL_WORKER_PROGRAM`, `_LEGACY_ROOT_WORKER_PROGRAM`; one `_WORKER_PROGRAM` literal with library imports;
  the historical thread-ceiling worker environment and the two historical-program refusals.
- Fluorescence: `HISTORICAL_WORKER_MODULE`; `LEGACY_IMPLEMENTATION_NAMES`; `_software_implementation_root` checks
  only the library layout (no `driver_module=`); recorded-argv module substitution; the old-layout fallback root in
  `native_fluorescence_prepared_contracts.py`.
- `native_macs2_peak_execution.LEGACY_DRIVER_MODULE`; unused old-path `DRIVER_MODULE` constants in
  `native_macs2_peak_job_schema.py` and `native_lumpy_job_schema.py`.
- Lumpy: `DRIVER_MODULE` now holds the library path (`CURRENT_DRIVER_MODULE` and `_CURRENT_REQUIRED_MODULES` folded
  into `DRIVER_MODULE` / `_REQUIRED_MODULES`); old-driver environment validation, argv choice and thread-ceiling
  native environment removed. `_current_driver` is kept as the single "library driver present" check used by the
  two existing `selected_worker_identity_conflict` refusals and by the pin verifier.
- Homer: old `WORKER_MODULE`, `homer_native_software_v1`, and the old two-file inventory branch;
  `homer_tf_worker_ports._LEGACY`, `module(current=)`; `recorded_module` returns the library module.
- Genomic overlap: second worker module and layout (`_recorded_source_paths(root)`), second command in intent and
  handle checks, second `driver_module` in the schema. Expression NMF: second worker module in the intent command.
- Schema alternatives: `native_blast_database_contracts` `entry_module` and package prefix;
  `_RECORDED_MODULE_PAIRS` and `Software` literals (protein structure); `worker_module` enum and driver map (RNA
  structure).
- Label change, writer and validator together: extractor `module` in `blast_native_iteration_records.py:450` and
  `native_blast_database_convergence.py:88` now names the library dotted path.

Not changed — old path with no library counterpart (needs a decision)
- `native_expression_nmf_contracts.py:18` `DRIVER_MODULE = 'gene_annotation_episode.native_expression_nmf_driver'`
  (used for argv at `:111`): no `native_expression_nmf_driver.py` exists at top level or in the library, only in
  `root/a107/`.
- `native_blast_standard_database_contracts.py:99,621` `entry_module` const
  `gene_annotation_episode.native_blast_standard_database_driver` and its top-level package-file set: the driver
  exists only as per-axis copies (a101-a104, a107).
These are single stale forms, not a second accepted alternative; picking a replacement path is not mechanical.

Top-level modules that still exist on disk and were named by removed alternatives: `native_macs2_peak_execution.py`,
`native_homer_worker.py`, `native_atac_differential_driver.py`, `native_atac_differential_reference.py`. They were
removed as alternatives anyway because the instruction named them explicitly; the root library now accepts only its
own copies.

External effect seen: `root/tests/test_native_lumpy_execution.py:32` uses `native._CURRENT_REQUIRED_MODULES`.
`<S>/prootlibb_external.tsv` now has 38 rows.

Import check after this pass: `runs/claude_prootlibb_002` printed `{}` for all 288 modules of list b.
`git diff --numstat` over list b now shows 63 files, +198 / -8,216; that total includes edits other agents made to
files on this list during the same period.
