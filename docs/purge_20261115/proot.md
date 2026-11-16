# proot: backward-facing removal in the shared-root top level (15 November 2026)

Area: files directly in `gene_annotation_episode/episodic_workflow/root/` (428 `*.py`, `defaults.toml`, notes, one
JSON) plus `root/method_loop/` and `root/vendor/`.

## Coverage — read this first

This area was NOT reviewed line by line. No sub-agents could be started (the concurrent sub-agent limit was already
reached), so one agent worked from a keyword scan (2,431 hit lines in 323 files) and followed the code-level hits.
Every item under "Removed" was read and edited; everything under "Not reviewed / not established" still needs a
decision. Comment and docstring narration (class 7) was only removed where it sat next to an edited site: most of it
remains.

Totals: 78 `*.py` files changed in the area (+287 / -1,234 lines; this count is from `git diff` and includes any
edits agent `h4` made to the same files), 4 files deleted (-2,477 lines), 0 tests deleted (the area holds no tests).

## Removed, by class

Class 1 — parameters, branches and helpers for the past (9 sites)
- `historical=` validation mode removed from 17 definitions and every call: `practical_execution_records.py`
  (`validate_assignment`, `terminal_job_matches`, `_job_matches`, `assess_validations`, `validate_validations`),
  `terminal_scientific_evidence.py` (5 functions), `practical_receipt_information.py` (3 methods),
  `flux_balance_execution_inputs.py` (4 methods). Error codes `fba_historical_validation_*` went with it.
- `atac_differential_result_receipts.py`, `chromatin_interaction_result_receipts.py`: `retained_policy` and
  `_historical` imports removed; only `POLICY` is used.
- `task_action_contracts.py`: old expanded-assignment transport removed (`_legacy_episode_assignments`, the second
  decoder, `unproven_replay`); `_recorded_assignment_transport` now refuses a request without the proof. Callers
  updated in `task_actions.py`, `task_decision.py`, `bvbrc_appservice_custody.py`.
- `bvbrc_appservice_host.py`: `legacy_cached_download` (142 lines, uncapped downloads from before `max_bytes`) and
  the `_completed_download` / `_completed_appservice_download` flag chain through `bvbrc_appservice_records.py`,
  `api_service_assignments.py`, `api_saved_records.py`, `api_service_operations.py`.
- `numerical.py` `YieldParameters`: ignored compatibility operands `window_size` / `subsample_size` and the
  `*_semantics: legacy_ignored_*` record keys removed; `saved_run_configuration.py`, `yield_parameters.py` follow.
- `episode_work_report.py`: `_grading_report_values` / `_axis_report_fields` (projection of old report forms through
  `legacy_report_schema`; the modules it imported no longer exist in the shared root).
- `terminal_binding_catalogue.py`: `LEGACY_VERSION`, `legacy_descriptor`, `expand_original_descriptor` (no caller).
- `scientific_tool_library.py` `retrieve` compatibility alias; `tool_reference_records.py` `tool_names` (only the
  removed v2 selection used it).
- `hpc_result_receipts.py`: old plan field `files_to_stage` no longer read; only `supplied_files`.

Class 2 — more than the current record/schema version (11 sites)
- Scientific process: `LEGACY_SELECTION_VERSION` (`scientific_process_selection_v2`) and `LEGACY_RETURN_VERSION`
  (`scientific_process_result_v2`) removed from `scientific_process_records.py`, `_provenance.py`, `_reports.py`.
- Assay grading: `LEGACY_VERSION`, `legacy_assay_grading_cells_schema`, `population_schema(legacy=...)`,
  `legacy_version` aliases (`literature_assay_grading_storage.py`, `literature_assay_grading_inputs.py`,
  `literature_a108_grading_inputs.py`, `literature_intervention_storage.py`, `literature_a106_subscore_storage.py`,
  `communication.py`).
- `readable_record_versions` (v1 beside v2) removed from `literature_assay_storage.py`, `literature_quantity_storage.py`,
  `literature_transport_storage.py`, `literature_binding_model_storage.py`, reader in `literature_rate_storage.py`;
  three v1-only reasons dropped from `literature_assay_storage.REASONS`.
- `literature_partner_storage.py`: `legacy_reference_types` and the unmarked (pre-`literal_reference_roles_version`) form.
- Wait inputs: `wait_inputs_binding_v1`, absent `completed_action_inputs`, `pending_work_v1`, `wait_inputs_v1`
  (`include_identities=False`) removed from `workflow_setup.py`, `saved_run_assembly.py`, `wait_events.py`,
  `wait_estimation_inputs.py`, `wait_coordination.py`, `task_actions.py`, `action_execution.py`,
  `episode_report_acquisition.py`, `continuation_observation.py`.
- `legacy_grouped_v1` progress-receipt order removed (`workflow_setup.py`, `saved_run_assembly.py`, `outcome_receipts.py`).
- Database schema migrations removed: `episode_journal.py` (REAL→ANY credit rebuild, two `ADD COLUMN`),
  `episode_receipts.py` (`ADD COLUMN received_report_prefix`), `shared_information.py` (missing `state` column).
- `communication.py`: historical BLAST-utility fact schemas, chromatin schema alternatives and the two older
  perturbation-summary field sets no longer accepted (one current tree each).
- `episode.py`: special refusal of `signed_root_episode_binding_v1` (the generic error now refuses it).
- `episode_composition.py`, `saved_binding_reconstruction.py`: refusals naming old aggregate identities / old factory
  path (the generic `unavailable_binding` error now applies).
- `literature_product_coupling_storage.py`: payload without `projection_version` no longer accepted.

Class 6 — files that exist only for the past (4 deleted)
- `RELOCATION_REVIEW.md`, `ownership.md`, `schema-notes.md` (nothing reads them),
  `literature_assay_grading_legacy_cells_v1.json` (its only reader was removed).

Class 7 — narration: 14 comments/docstrings beside the edited sites. Classes 4, 5: nothing to remove (the area has no
saved source copies or tests). Class 3 is listed in its own section below.

Native-job memory decision: `local_execution_validation.py:124,141` ceiling and `molecular_result_values.POLICY`
set to 5 GiB (`5368709120`, the literal the root library uses); the two RNA prompts now say 5 GiB.

## Live despite its name (kept, not renamed)
- `legacy_annotation` home references (catalogues, `task_selection.py:12`, `credit_projection.py:13`,
  `continuation_observation.py:17`): it is the binding of the default `improvement` role
  (`action_execution.py:172,226`, `runtime.py:22`).
- `self.legacy` / `_legacy_binding()` / `_legacy_context()` / `LEGACY_PROVIDER` in `api_*`: the HMMER API binding
  built for the current resource kind `hmmer_api` (`api_service_configuration.py:39-46`).
- `legacy_returns` in `protein_structure_action_records.py`: set from the current results binding
  (`workflow_protein_structure.py:34`).
- `_legacy_scientific_process_binding`: set by `workflow_setup.py:214` for registries without private owners.
- `LEGACY_EVIDENCE_SLOT = "annotation_distinction"`: the published library index still uses this slot
  (`research/slotted_process_library/index.json`).
- `_validate_historical` / `_historical` / `_historical_ordinary` methods of the `*_returns.py` classes and
  `historical_uniprot` / `historical_enrichr` in `api_saved_records.py`: re-validation of forms saved earlier in the
  same run.
- `legacy_uniprot_records` use in `tool_reference_imports.py:141-240`: the current UniProt publication path.
- `_prepare_orf_sequence_operand`: called by `library/molecular_sequence_tools.py:428`.

## Class 3 — historical digest / release alternatives (removed after the coordinator's clarification; 10 sites)
- `literature_kinetic_storage.py`: `LEGACY_VERSION` (record v2), `_LEGACY_FROZEN`, `_FROZEN`, `_SOURCE_LOCATION_FROZEN`,
  `_LEGACY_SAVED_IMPLEMENTATION` and the `{sha256, validation_version}` receipt form; only
  `root_kinetic_implementation_v1` is produced and accepted. `literature_population_task_metadata.py` follows.
- `literature_concentration_window_release.py` / `_storage.py`: `HISTORICAL_VERSION`, `_HISTORICAL_*` tables,
  `retained_v2`, `retained_v3`, the `original_implementation_v1` branch, `PURE_HASHES`, `_implementation_files`; only v4.
- `literature_binding_interaction_storage.py`: `_FROZEN`, `_COMPATIBLE_RATE_STORAGE`, `_ORIGINAL_DEPENDENCIES`,
  `_PREVIOUS_DEPENDENCIES`, `_PRE_CONNECTION_DEPENDENCIES`; only `root_binding_interaction_implementation_v3`.
- `literature_kinetic_summary_precision_storage.py`: historical v3/v4 and original v1/v2 receipts, `_PURE_HASHES*`.
- `literature_measurement_comparison_storage.py`: `_validate_original_implementation`, `_PURE_HASHES`/`_V2`/`_V3`.
- `literature_endpoint_signal_storage.py`: v3, v2 and original-v1 receipts, `_PURE_HASHES`; only v4.
- `literature_compiled_assay_storage.py`, `literature_ion_discrimination_storage.py`,
  `literature_measurement_validation_storage.py`, `literature_product_coupling_storage.py`: the
  `*_original_implementation_v1` receipt alternative with its `_FROZEN` table / file list.
- `episode_composition.py`: `_SCIENTIFIC_IMPLEMENTATION_COMPATIBILITY` (accepted older implementation digests);
  `scientific_binding_compatible` is exact equality. Descriptor versions `scientific_process_episodes_v5..v9` are no
  longer accepted there or in `saved_private_binding_catalogue.py`.
- `literature_amount_inputs.py`: `_RELEASED027_LEXICAL_DEPENDENCY`.
- `literature_sheet_updates.py`: historical adapter coordinates (`defining_adapter_coordinates`).

## Left for `h4` (current pin mechanism, untouched by this agent)
- Current digest tables and the functions that hash and compare them: `literature_concentration_window_release.py`
  (`_FILES`, `prospective`, `retained`), `literature_binding_interaction_release.py`,
  `literature_product_kinetic_relocation.py`, `_common_root_receipt_files` / `_common_implementation_receipt`,
  `_CURRENT_IMPLEMENTATION_VERSION` validators, `LEXICAL_DEPENDENCY` release digests,
  `implementation_sha256` in `saved_private_binding_catalogue.py`.
- `method_loop/SOURCE.json`, `method_loop/LOCAL_PATCHES.json`, `vendor/SOURCE.*.json` (vendoring provenance with
  hashes) were not changed.
- No pin was re-pinned. Every edited file changed digest, so current pin tables naming them now mismatch.

## Not reviewed / not established (still open)
- `flux_balance_returns.py` `_LEGACY_SOURCES` and the non-ordinary-prefix branch (`legacy_source` identity).
- `alignment_site_action_records.py:122` `legacy_result_ungraded`.
- `local_file_capture_results.py:135,809-819` "legacy complete byte windows".
- `practical_execution_records.py:24` `JOB_TOOLS` comment says `practical.job.*` receipts are legacy, yet four
  receipt modules require those tool names.
- Multi-version acceptance not examined: `bvbrc_proteome_returns._ADAPTER_VERSIONS ('1','2')`,
  `rfam_batch_returns.py:219,341`, `execution_prompt.py:46`, `execution_scientific_inputs.py:360`,
  `literature_a105_worksheet.py:115`, `protein_structure_operands.py:204,354`, `native_blast_database_results.py:109`,
  `episode_application_services.py:28`, `execution_request_custody.py:24`.
- `literature_required_grading.py:170` still passes `allow_legacy_quote=True`; `domain.source_location_inputs`
  (area `ptop`) still takes it.
- `action_history.py:13` (journals without the effects table), `decision_context.py:34`, `evidence_axis_contracts.py:116,179`,
  `literature_amount_inputs.py:229,461`, `literature_optical_inputs.py:198`, `literature_rate_storage.py:825-874`,
  `default_scientific_binding.py:66`, unowned-registry paths in `root_binding_selection.py` / `private_episode_selection.py`.
- About 200 narration comments in the scan (`narr.txt` in the scratchpad) were not edited.
- The ~105 files with no keyword hit were not opened.

## Verification
- Import check of all 440 modules (428 top-level, `method_loop`, `vendor`): `{}` (0 failures), last run
  `runs/claude_proot_016` (after the class 3 removals).
- Test files run (before → after; root/tests belongs to `roothomes` and was changing during the run):
  - `test_root_journal_support.py`: 2 passed → 2 passed.
  - `test_root_native_factory.py`: 8 passed → 7 passed, 0 failed (one test removed by another area).
  - `test_signed_evidence_root.py`: 21 passed / 10 failed → 21 passed / 10 failed.
  - `test_execution_local_file_sources.py`: 69 passed / 7 failed (76) → 66 passed / 8 failed (74); the new failure was
    not identified.
  - `test_annotation_task_boundaries.py`: 12 passed → 5 passed / 7 failed. Cause: its stub workflows model the removed
    older wait-input mode (no `pending_work`) and saved requests without `assignment_transport`. Handed to `roothomes`.
- No other test files were run, and none were rerun after the class 3 removals (import check only).

## Handoffs
Written (12 rows from `proot`): 5 to `rootlib` (keep/removal of names the ATAC/chromatin receipt files import;
`historical=` call sites in library; library functions no longer passed `historical=`; delete
`blast_utility_historical_fact_schemas.py`), 7 to `roothomes` (`LEGACY_SELECTION_VERSION` / `LEGACY_RETURN_VERSION`
users in `scientific_process/`; `unproven_replay` / `recorded_transport` in ~100 sub-home `task_actions.py` and
siblings; `YieldParameters(100, 50)` in 7 test files; two tests passing `historical=`; the task-boundary tests;
a redirect of rows misaddressed to `proot`).
Applied (rows to `proot` that name root top-level files): `communication.py` chromatin and perturbation-summary
schemas, `control_version=` in `terminal_scientific_evidence.py` / `practical_receipt_information.py`,
`_accept_legacy_quotes` in `task_actions.py`, `legacy_report_schema` in `episode_work_report.py`, 20 GiB sites (h2),
`literature_product_coupling_storage.py` (`_meaning_v1`, `projection_version`), a105 test comment in
`literature_binding_interaction_storage.py`, `literature_sheet_updates.py` (deleted adapter-definitions module), old
release branches in summary-precision / endpoint-signal / kinetic storage.
Not applied: 51 `ptop` rows and 4 `prootlib` rows addressed to `proot` name files under `root/tests` or sub-home
directories, which are `roothomes` files; a redirect row was written.
