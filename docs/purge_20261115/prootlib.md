# prootlib — shared root library purge (`gene_annotation_episode/episodic_workflow/root/library/`)

Area: flat directory, 1,131 Python modules + 11 JSON schema files + 1 licence, no test files.
Detail for two of the five file lists is in `prootliba.md` (bvbrc_* and literature_*) and `prootlibb.md`
(native_/blast_/hmmer_/infernal_/rfam_/homology_/homer_/macs2_/lumpy_).

## How it was done, and how deep
- Planned fan-out was four sub-agents. Two were refused by the session's concurrent-agent limit, so: sub-agent a
  did bvbrc_* (182 files) and afterwards literature_* (270); sub-agent b did the native/blast/hmmer list (289);
  the parent did atac/chromatin/flux/execution/resource/hpc (105) and "the rest" (297).
- Coverage everywhere is keyword sweeps over every file plus reading each hit in context. It is NOT a line-by-line
  read of the 358,000 lines. Files with no vocabulary hit were not opened.
- First pass left file/location/digest/version checks alone (owner update); the later instruction "remove the
  pin mechanism too" reversed that for old forms — see "Mechanical pass". Current-pin code is left to agent h4.

## Totals (git diff over the area)
104 files changed, +485 / -11,900 lines; 102 edited, 2 modules deleted; 1,129 modules remain.
Tests deleted: 0 (the area has none; `prootlib_deleted_tests.tsv` has only its header).

## Removed, by class
Class 1 — parameters, branches, helpers for the past (about 110 sites)
- The specific item: `atac_result_*.py` and `chromatin_result_*.py` (10 files): `_historical` deleted from both
  `*_receipt_values.py`, every `historical=` argument removed, every `retained_policy(...)` replaced by the single
  `POLICY` (the equality checks that follow refuse any other policy with the module's existing `require`), the
  historical-only OPENBLAS/OMP environment branch removed. The two contracts modules never defined
  `retained_policy`; that import is what stopped the 10 modules importing. All 12 import now.
- Flux balance: `HISTORICAL_POLICY`, every `historical` / `historical_worker` / `historical_source` parameter,
  `_validation_policy`, `_saved_validation_mode` (tried current then historical envelope) across
  `native_flux_balance_{contracts,preparation,capture,local}`, `flux_balance_{result_receipts,request_binding,
  operands,result_selection,worker_contracts,native_capture_contracts}`, `execution_progress`,
  `local_practical_operations`.
- `action_contracts.reasoning_action_schema(_accept_legacy_quotes=)`; `literature_intervention_inputs`
  unused `legacy=`; sub-agent b: `validate_fluorescence_policy(fresh=)`, `expression_nmf_environment(
  recorded_environment=)`, `effective_metadata(include_map_context=)`, `_hsp_values(archived_values=)`,
  `_locator(legacy=)`, genomic-overlap historical environment.
Class 2 — more than the current record form (about 45 sites)
- `flux_balance_request_binding`: `LEGACY_CONTROL_VERSION` (v1) and the `control_version` parameter; only
  `flux_balance_request_binding_v2` / `flux_balance_practical_outcome_v2`.
- `component_received_reports`: `legacy_report_schema`, `VERSION` (`component_axis_report_v1`), `PATH_STATES`;
  `report_axis` accepts only `component_axis_saved_grading_report_v2`.
- `chromatin_interaction_return_views.chromatin_fact_schema_alternatives` (current + legacy field tree).
- `literature_perturbation_summary_return_contracts.perturbation_summary_cells_schema` two older field sets;
  sub-agent a: product-coupling `_meaning_v1`, controlled-response "Legacy saved shape", fastqutils legacy
  requested-form grammars, BV-BRC Data array-with-headers reader, MetaCATS older adequacy object; sub-agent b:
  BLAST standard-database manifest v1, native BLAST grading v1, `upgrade_saved_rfam_search_sheet`,
  `upgrade_saved_infernal_search_sheet`, empty HMMER2 calibration form, hmmsim old-record tolerance.
- Memory decision (5 GiB): 20 GiB `POLICY` -> 5368709120 in `native_atac_differential_contracts`,
  `native_chromatin_interaction_contracts`, `chromatin_interaction_contracts` (schema const),
  `original_fluorescence_observation`, `somatic_variant_contracts` (and `java_heap_mb < 5*1024`),
  `molecular_sequence_result_contracts` (3 sites), `native_homer_execution`; second accepted value 21474836480
  removed in genomic overlap, expression NMF, protein structure, RNA structure, BLAST utility VDB check.
  No 21474836480 remains in the area.
Class 3, 4, 5 — none in this area (no digest table edited, no saved sources, no tests).
Class 6 — modules that exist only for the past (2): `chromatin_interaction_legacy_return_schemas.py`,
  `blast_utility_historical_fact_schemas.py` (7,695 lines).
Class 7 — narration (about 45 sites): receipt-module docstrings, ownership-account docstrings (4 files),
  `record_serialization`, flux operands, packet/work-number references in list b, 12 sites in list a.

## Behaviour changes to confirm
- `native_homer_execution.POLICY`, `somatic_variant_contracts.POLICY` (+ Java heap bound),
  `molecular_sequence_result_contracts.ORDINARY_ORF_POLICY` and the ATAC/chromatin `POLICY` were LIVE launch
  policies at 20 GiB, not recorded alternatives; they are now 5 GiB under the owner's memory decision.

## Mechanical pass (second instruction: "remove the pin mechanism too") — supersedes the earlier "left in place"
Everything previously listed as left under the owner update is now removed; only the current root/library module
path, layout, software version and release is accepted, refused otherwise by each module's existing error.
Current implementation-digest pin code was left for agent h4.
- Parent lists: `LEGACY_WORKER_MODULE` and the conditional source check (`native_atac_differential_preparation`);
  old driver enum entry (`chromatin_interaction_contracts.py:240`); old driver alternative in
  `native_flux_balance_contracts` (3 sites); `_LEGACY` prefix, `module(current=)` and the fallback in
  `native_selection` (`molecular_worker_ports`, `ordinary_scientific_worker_ports`,
  `physical_measurement_worker_ports`; `recorded_module` now returns the one current module);
  `esm_gene_embedding_contracts.esm_worker_module` old pair; old worker alternatives in
  `protein_conservation_tools`, `rna_structure_comparison_contracts`, `rna_structure_comparison_publication`,
  `restriction_mapping_jobs._software_location` (now `restriction_software_conflict`), the old default in
  `protease_kinetics_tools._command`, `tf_binding_tools._WORKERS` values. `LEGACY_DRIVER_MODULE` /
  `LEGACY_REQUIRED_MODULES` / `legacy_sources` in the ATAC and chromatin modules had already been removed by h1.
- ptop's 7 rows applied (`atac_differential_execution_information.py`, `chromatin_interaction_execution_
  information.py`); the same change made for 16 module names in `execution_progress.py` information strings.
- List b (22 files): see `prootlibb.md` "Mechanical pass". Lists a/c: literature historical release tables and
  predicates, `literature_saved_adapter_definitions.py`, the two fastqutils legacy JSON files and their list
  entries; see `prootliba.md` "Mechanical pass".
- Deleted files in the area now: `blast_utility_historical_fact_schemas.py`,
  `chromatin_interaction_legacy_return_schemas.py`, `literature_saved_adapter_definitions.py`,
  `bvbrc_fastqutils_legacy_v2_schemas.json`, `bvbrc_fastqutils_legacy_cutadapt_schemas.json`.
- `execution_progress` / `resource_id`: restored the single-bound-resource handling (without the "legacy"
  narration). The root assignment schema (`root/practical_execution_records.py:120,267-270`) is the commission
  schema and lets a commission omit `resource_id` for plain jobs, so a current author can legitimately omit it;
  schema and code agree again.
- Area totals after this pass (includes edits h1/h4 made inside the area): 143 files changed, +656 / -39,132;
  1,128 modules + 9 JSON files remain.
- Import check `runs/claude_prootlib_031`: all 1,128 modules import (`{}`).

Single stale old paths with NO current counterpart (not alternatives; need a decision, nothing mechanical to do)
- `native_flux_balance_preparation.py:38` `WORKER_MODULE = "gene_annotation_episode.flux_balance_result_worker"`:
  that module exists only in `root/a107/library` and `root/a110` (never at top level in HEAD).
- `rna_result_preparation.py:160` launches `gene_annotation_episode.native_rna_structure_result_worker`: exists
  nowhere. `execution_progress.py` names `gene_annotation_episode.rna_structure_native`: exists nowhere.
- `native_expression_nmf_contracts.py:18` `DRIVER_MODULE` and `native_blast_standard_database_contracts.py:99,621`
  `entry_module`: drivers exist only as per-axis copies.
- Information strings and worker names that point at top-level modules still on disk were left as they are.

## Live despite its name (kept, with evidence)
- Home name `legacy_annotation` in path strings (`resource_binding_records.py:10-94`, `nominal_child_messages.py:
  80-171`, homology adapter): `root/legacy_annotation/episode.py` exists and is a current home.
- `_LEGACY_PROFILE = "legacy_v1"` (`molecular_sequence_result_contracts.py:39`): default profile of current
  operations. `legacy_pointer`, `legacy_quantities`, `include_legacy_clipping`, `legacy_result_ungraded`,
  `legacy_unlinked`: field names / codes in current records.
- `legacy_returns` (`protein_structure_tools.py:903-941`): `root/protein_structure_result_publication.py:61`
  writes `protein_structure_saved_sheet_v1` today. `tool_grading_artifact_v1/v2`, flux run plan v1/v2
  (`native_flux_balance_local.py:111`), execution_status_v1/v2: both forms written by current code.
- `original_fluorescence_*`: the current fluorescence receipt owner (`root/native_fluorescence_results.py`).
- `_historical_store_root`, `_validate_historical`, `OriginalFluorescenceReturns._historical`, `_READING`:
  records saved earlier in the same run. `legacy_task_relevant`: the current `literature.figure.populate` tool.
- Upstream vocabulary: HMMER2 / Infernal legacy formats, samstat legacy report, Mauve v4, COBRA `native_legacy`,
  UniProt `legacy_*` codes; statistical priors; HPC `wall_seconds` (scheduler walltime, not a policy budget).

## Kept, uncertain
- `monitoring_credit.py:84` `include_handoff_checks` ("historical runs retain sample-only"); which value current
  callers select was not traced.
- `molecular_sequence_native` / `_driver` request versions v1-v3 and `protein_structure_contracts` V1/V2
  descriptor cohorts: look operation-keyed and current, not verified per writer.
- List a: ~165 `reviewed_source` / `source_contract` values citing old packets in fastqutils `*_specs.py`;
  optional `interpretation_basis` (`literature_perturbation_summary.py:160`); `literature_task_schema.py:17`.
- List b: `_retain_correspondence=False` output form; `rfam_batch_tblout_parse_result_v1` (no library builder,
  validated by `root/rfam_batch_returns.py:341`); `RFAM_LEGACY_RESULT_SELECTOR_SCHEMA`; HMMER alignment facts
  accepted absent; homology rows tolerating missing grading.

## Import check
Final: `runs/claude_prootlib_031`, all 1,128 modules import (`{}`), run after the mechanical pass. Earlier
checks: `_001`, `_002`, `_020`, `_021` (first pass, 1,129 modules), `_030`.

## Test files run (tests belong to other areas; none edited)
| file | before | after |
| --- | --- | --- |
| `tests/test_native_atac_differential_contracts.py` | 10 passed | 10 passed |
| `root/tests/test_atac_differential_result_receipts.py` | 35 passed, 20 errors | collection error: `gene_annotation_episode.atac_differential_result_receipts` deleted by ptop |
| `root/tests/test_chromatin_interaction_execution_information.py` | 19 passed, 4 failed | collection error: top-level module deleted by ptop |
| `tests/test_bvbrc_data_readers.py` (sub-agent a) | 78 passed | 71 passed, 7 failed (removed array reader) |
| `tests/test_bvbrc_comparative_systems_data_inputs.py` (sub-agent a) | 54 passed | 52 passed, 2 failed |
No other test file was run; the receipt, flux-balance, component-report and literature changes are verified by
import only.

## Handoffs
Written (22 rows from `prootlib`, incl. ptop for `molecular_measurement_tools.py:257,312`): to `proot` (communication.py chromatin and perturbation schemas — already
applied there; flux `control_version=`; `_accept_legacy_quotes=`; `legacy_report_schema`; `historical`
parameters in terminal_scientific_evidence / practical_receipt_information; 20 GiB receipts;
`literature_product_coupling_storage.py:308`), to `roothomes` (103 `task_actions.py` and 36 `operations.py`
call sites, component report users), to `ptests` (tests using removed names or asserting 20 GiB).
Applied: proot's 4 rows to `rootlib` (retained_policy/_historical/historical parameters — all done);
cross-list row from sub-agent b (`expression_nmf_result_worker.py` drops `recorded_environment=`).
ptop's 7 rows and h1's 2 rows: applied in the mechanical pass. `pa102 -> root-shared` concerns `root/scientific_process`, not this area.
