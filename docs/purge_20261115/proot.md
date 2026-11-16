# proot: backward-facing removal in the shared-root top level (15 November 2026)

Area: files directly in `gene_annotation_episode/episodic_workflow/root/` (428 `*.py`, `defaults.toml`, notes, one
JSON) plus `root/method_loop/` and `root/vendor/`.

## Coverage — read this first

First pass: one agent worked from a keyword scan (2,431 hit lines in 323 files). Second pass: the 121 files with no
keyword hit were each read in full by two sub-agents (14 + 31 edited, the rest clean), and a third sub-agent worked
the multi-version sites; it was cut off by a usage limit and later by the session restart, so the lead finished its
list and it left no report of its own. Narration comments (class 7) were removed only next to edited sites and in
about 30 docstrings in the second pass; roughly 170 keyword-scan narration lines remain.

Totals against the starting commit a0d9f1666: 153 `*.py` files changed in the area (+515 / -2,181 lines; the count
is from `git diff` and includes edits agent `h4` and others made to the same files), 4 files deleted (-2,477
lines), 0 tests deleted (the area holds no tests).

Correction to the first report: `task_action_contracts._recorded_assignment_transport` at first refused every saved
request without the transport proof. That was wrong for decision-exchange requests, which the current program saves
with a protocol marker and no proof (`task_decision.py:139-147`). It now refuses only a direct request without a
valid proof. A correcting row went to `roothomes`.

## Removed, by class

Class 1 — parameters, branches and helpers for the past (9 sites)
- `historical=` validation mode removed from 17 definitions and every call: `practical_execution_records.py`
  (`validate_assignment`, `terminal_job_matches`, `_job_matches`, `assess_validations`, `validate_validations`),
  `terminal_scientific_evidence.py` (5 functions), `practical_receipt_information.py` (3 methods),
  `flux_balance_execution_inputs.py` (4 methods). Error codes `fba_historical_validation_*` went with it.
- `atac_differential_result_receipts.py`, `chromatin_interaction_result_receipts.py`: `retained_policy` and
  `_historical` imports removed; only `POLICY` is used.
- `task_action_contracts.py`: old expanded-assignment transport removed (`_legacy_episode_assignments`, the second
  decoder, `unproven_replay`); `_recorded_assignment_transport` refuses a direct request without the proof. Callers
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

## Second pass (after the first report)

Removed
- Non-owned branch lifecycle: `workflow_setup.py:54` refuses every lifecycle but `owned_child_turn_taking_v2`, so the
  not-owned alternatives and `admit_unowned_return` went from 14 `from_child_*.py` files, `child_commission.py`,
  `action_execution.py` (including the unreachable tail of `report`), `child_delivery.py`, `episode_construction.py`,
  `report_redelivery.py`, `workflow_values.py`, `report_validation.py`, `predefined_child_message_owners.py`.
- Saved tool-action results without `pending_work_after_action` are refused (every writer adds it:
  `task_actions.py:142`): `rna_result_custody.py`, `rna_comparison_result_custody.py`,
  `protein_structure_return_operands.py`, `protein_structure_result_receipts.py`, `fluorescence_result_receipts.py`,
  `expression_nmf_result_receipts.py`, `genomic_overlap_result_receipts.py`, `local_file_capture_results.py`,
  `api_saved_records.py`.
- `episode_receipts.read_manifest`: a manifest with a NULL `received_report_prefix` is refused (`bind` always writes it).
- Names-only tool library (`scientific_tool_library_v1`, `tool_info=` switch, `supports_tool_info`, `resolve(names)`,
  retrieval request v1): `scientific_tool_library.py`, `scientific_tool_retrieval.py`, `action_execution.py`,
  `scientific_process_setup.py`.
- `legacy_result_ungraded` (`alignment_site_action_records.py`): a result without the grading envelope is refused.
- `episode_application_services.py`: `actual_tool_catalog_v1`; `execution_prompt.py`: `rfam_batch_result_selector_v1`;
  `rfam_batch_returns.py`: validation of `rfam_batch_tblout_parse_result_v1` (no writer).
- `literature_required_grading.py`: `allow_legacy_quote`. Unused `action_execution as _original` imports in six
  `to_child_*.py`. Wrong comment above `JOB_TOOLS`.

Traced to a current writer and kept (both forms are current)
- `flux_balance_returns._LEGACY_SOURCES`: `native_flux_balance_results.py:215`, `flux_balance_returns.py:522`.
- `JOB_TOOLS`: `practical.job.*` is written by `library/local_practical_operations.py:1020,1541,1853`, `exec_command`
  by `terminal_execution.py:298`.
- Byte windows in `local_file_capture_results.py` (current capture form; only the word "legacy" was removed).
- `bvbrc_proteome` adapters '1' and '2': `library/bvbrc_proteome_bundle_resolution.py:686` and
  `library/bvbrc_proteome_bundle_adapter_v2.py:76`.
- `rfam_batch_retained_grading_v1`/`_v2`: both written at `library/rfam_batch_publication.py:411,414`.
- `native_blast_database_results` `VERSION`/`FUNCTION_VERSION`: both written at line 212.
- `native_protein_structure_bundle_v1` and `SAVED_ACTION_SOURCE_VERSION`: two source kinds, not two versions.
- `api_execution_assignment_v1` beside `api_service_assignment_v1`: the HMMER API binding (`hmmer_api` resources).
- Molecular-sequence selectors v1/v3/v4: `library/molecular_sequence_result_contracts.py:1885`.
- `_validate_historical` / `_historical` in `*_returns.py`: they read `runtime_report_attempts` rows of the same run,
  written by `episode_admission.py:90`. `legacy_returns`: the live `NativeProteinStructureReturns` object built at
  `execution_result_selection.py:38-41`; `retained_protein_structure_reader` is called by
  `library/protein_structure_tools.py:935`.
- No file in the area handles `max_bytes`; `bvbrc_appservice_records.py:291` only calls the top-level
  `download_request`, and the uncapped `legacy_cached_download` path was removed in the first pass.

## Not established (still open)
- `literature_a105_worksheet.py:115,149`: `VERSION` and `VERSION_V2`. The only builder defaults to v1 and has no
  non-test caller; three library modules read both.
- `protein_structure_operands.py:346-356` `GRADING_SCHEMA` / `GRADING_SCHEMA_V2` and
  `execution_scientific_inputs.py:360` blast-utility selectors v1/v2: both forms are still defined and read in
  `root/library`; which is written was not traced.
- `local_execution_validation.py:116-117,153-160`: blast-utility job v2/v3 and fluorescence v2 branches (library
  still defines v1-v3).
- `execution_binding_catalogue.py:35-70`: path for an owner without `_private_execution_bindings`; both product
  constructors register, about 30 test files do not.
- `getattr(..., None)` defaults on workflow/service attributes that every product `Workflow` sets (partial hosts in
  tests rely on them); `type(job_episodes) is HomologyEpisodes ... else` branches in the `to_child_*` files.
- Seventeen `"received_report_prefix" in manifest` guards are now unreachable (the manifest reader refuses first).
- `saved_run_configuration.py:22-33` (provider config flat or under `models`), `method_loop/reconstruction.py:62-66`
  (vendored, no user), `default_scientific_binding.py:66`, `decision_context.py:34`, `evidence_axis_contracts.py:116,179`,
  `literature_amount_inputs.py:229`, `literature_optical_inputs.py:198`, `literature_rate_storage.py:825-874`.

## Verification
- Import check of all modules in the area: `{}` (0 failures), last run `runs/claude_proot_028`.
- Root test files (owned by `roothomes`, not edited here), last run after all edits:
  - `test_root_journal_support.py`: 2 passed (was 2 passed).
  - `test_root_native_factory.py`: 7 passed (was 8; one test removed by another area).
  - `test_signed_evidence_root.py`: 21 passed / 10 failed (unchanged).
  - `test_annotation_task_boundaries.py`: 5 passed (the 7 that failed in the first pass were deleted by `roothomes`;
    two of them may have failed only because of the transport-proof mistake corrected above).
  - `test_execution_local_file_sources.py`: 43 passed / 31 failed (first pass: 66 / 8). Eighteen new failures are
    `execution_file_capture_public_outcome_conflict`: the test fixture saves action results without
    `pending_work_after_action`. One failure is a fixture request without the transport proof. The other new
    failures were not examined.
- No other test files were run.

## Handoffs
Written from `proot`: 16 rows (6 to `rootlib`, 10 to `roothomes`), including the correction about the transport proof
and the fixtures that must save `pending_work_after_action`. One of the ten is an informational row a sub-agent
wrote (256 sub-home files still carry the not-owned lifecycle alternative).
Applied: every row addressed to `proot` that names a file directly in `root/` (see the first-pass list, plus
`literature_required_grading.py`, `scientific_tool_library.py`, `task_action_contracts.py`). Row 22 from `ptop`
(`bvbrc_appservice_records.py:291`) needed no change. Rows that name `root/tests` or sub-home files were redirected
to `roothomes`; its sub-home call sites for `_accept_legacy_quotes` and `control_version=` were already at zero.
