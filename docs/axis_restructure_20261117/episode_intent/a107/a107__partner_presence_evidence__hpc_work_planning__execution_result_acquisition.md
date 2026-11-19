# a107/partner_presence_evidence/hpc_work_planning/execution_result_acquisition — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/execution_result_acquisition/`
(42 Python files directly in the folder; no `grading/`, `scoring/` or `tests/` subfolder). Nothing from the old shared
root was read. Where behaviour lives in old shared modules (the native result adapters, `api_service_execution`,
`execution_progress`, `local_file_capture_results`, `practical_yield`, `numerical`, the received result readers), this
page says only what this episode's own files ask of them.

Old binding: class `ExecutionEpisode` (results), `binding_path = 'partner_presence_evidence/hpc_work_planning/execution_result_acquisition'`,
`commissioning_parent = 'partner_presence_evidence/hpc_work_planning'`, role `results`, no entry roles, version
`execution_episode_v1`, `replaces_default_instructions = True`. Decision source `ResultsTask`; prompt renderer
`present_results_context`. Mixes in `A107BlastExecution` (old shared) for BLAST-graded checks.

## What this episode is for

It acquires the results of one already handed-off execution attempt through that original handoff, reading status and
the requested file windows or pages, and returns the acquired records for the scientific parent to interpret. In its
own words (`instructions.py`):

> Acquire the original selected execution results through the original handoff. Choose bounded status or requested
> file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. Native paths expose the
> current resource filesystem: the exact attempt observation does not establish that current file bytes were produced
> by that attempt. Separate read windows are not an atomic file snapshot. The scientific parent interprets the returned
> records. Original work, resource and selector stay fixed. Only actual complete acquisition establishes this endpoint.

## Task and instructions

- One unit is one model-selected `tool` action; also `wait` when the target is an API target with assignment version
  `api_service_assignment_v1` (`goal.py`). No children, no `reason`, no `redeliver_report` in the permitted list.
  (The task loop still contains reasoning-commit admission and execution branches inherited from the shared copy.)
- Instructions (`task_instructions.py`): the binding goal replaces the default instructions; then the reasoning-commit
  requirement if `reason` is permitted, tool knowledge, the launch library, repair guidance, wait and native-event
  guidance when `wait` is permitted, and the exchange-history substitution under the decision-exchange protocol.

## What it reads from its parent's assignment

`RESULTS_SCHEMA` (library `execution_result_contract`), with the selector extended (`from_parent.py`) by: local file
source selector `local_file_source_selector_v1`; the native result selector conditions; expression NMF result
selector (when NMF readers are configured); RNA structure result and RNA comparison selectors (when RNA readers are
configured). The assignment carries the `handoff_ref` of the attempt, the `selector` (paths/path/offset/limit or a
typed selector) and `constraints`. Preparation:
- restores a successfully returned original results commission on resume (`saved_commission.py`);
- resolves the target from the handoff (or from a retained masking/utility/NMF target), checks the selector against
  the target, and validates selected inputs for local file sources, BLAST masking/utility, RNA comparison/structure,
  standard and native BLAST database targets.
`result_state.py`: a BLAST-graded API target requires the parent's form to contain the typed graded return field.
Required return source `execution_result_refs` under the axis head when an annotation task is required.

## Children

None (`child_roles` and `allowed_children` return `()`).

## Decision state and what the model sees

Old generic snapshot (own copy `results_decision_snapshot` in `internal_summary.py`) plus `decision_context`:
`execution_assignment`; `execution_progress` (live facts); `execution_target` and `execution_target_description`
(status/collect operations and origin for local file sources; NMF description; otherwise the progress provider's
target description for the selector); `selected_execution_task` (version `selected_execution_task_v1`: the scientific
parent's `scientific_question` and `selected_tool_info`, the request's resource, endpoint, constraints and job — HMMER
and NMF jobs through their scientific views — plus the selector and result description). Rendering
(`presentation.py`) picks a text renderer by context kind or falls back to JSON.

## Tools

`work_operations.py` selects the catalog by target kind: expression NMF results, BLAST masking, BLAST utility, RNA
comparison, RNA structure, standard BLAST database, native BLAST database, API execution, HMMER preparation, HMMER,
native BLAST, Infernal, Infernal preparation; otherwise the native catalog (`result_records.py`):
- `execution.results.status` — observe the exact handed-off physical attempt once;
- `execution.results.collect` — observe the attempt and acquire first windows of all requested paths (window
  `min(log_window_bytes, 1 MiB, requested length)`);
- `execution.results.read` — one selected window `{path, offset, limit ≤ 1 MiB}` inside the requested interval.
Native acquisition (`native_file_acquisition.py`) writes immutable intent, observation and per-window files, refuses
after a completed endpoint (`execution_results_assignment_already_completed`), records per-window failures, and
publishes one `execution_result_information_v2` source with origin qualification (`current_resource_filesystem`,
`attempt_output_version: unverified`, `separate_reads_no_atomic_file_snapshot`). Local file sources go to
`local_file_sources.execute`. Errors return `invalid` outcomes, except retained-artifact capture errors, which raise.

## Credit

Credit kind `operational` (`credit.py`). If a closed credit view was frozen in the closing facts, that view is
returned unchanged (`closed_credit.py`). Otherwise the matching adapter's credit view, or the API's, or:
`credit = handoff_unit × 0 + acquired_record_unit × fraction`, where `fraction` is the mean over requested paths of the
newly covered byte positions (union of received windows minus those already in initial records) divided by the
requested interval; for local file sources a count-based variant `acquired_record_unit × acquired count`. Binding
version `execution_received_selector_coverage_credit_v2` (or `execution_received_records_credit_v1`). The fraction is
by construction at most one per path; no clamp is applied.

## Continuation

Only with `require_private_yield` (`yield_estimator.py`); else raises `execution_private_yield_binding_not_enabled`.
- Native selector with an open-ended requested path → profile `results_yield_profiles['native_unbounded_<kind>']`,
  plain controller with its `cutoff` and `parameters` (nearest: **accumulation**).
- Native finite selector → profile `task_yield_profiles['results:native_finite_<kind>']`; `remaining =
  acquired_record_unit × (1 − fraction already in initial records)`; estimate `estimate_bounded_credit_yield` with
  `maximum_credit=remaining` (nearest: **bounded quality**), switching to the completion estimator once a verified
  completion proof is in context, and exact zero when nothing remains.
- API target → `results:api_<service>[_<selector version>]`; typed native selector → `results:typed_<kind>_<version>`;
  both use the practical completion estimator verifying this episode's completion proof (nearest: **completion with a
  target**).
Missing profile keys raise `execution_original_task_yield_profile_required:<key>`.

## Report to parent

`to_parent.py` facts: for an applicable native adapter its facts merged over empty native sources; for API targets the
API facts with `execution_result_origin: null`, plus BLAST grader rows when the launch request was BLAST-graded (one
retained grader sheet per result, matching query length/sha256, subject and database); otherwise
`execution_handoff_refs`, `bvbrc_appservice_support_refs` (if the appservice is bound), `execution_blast_hsps: []`,
`execution_result_refs` (results with windows), `execution_file_source_refs`, `execution_file_capture_outcomes`,
`execution_result_origin`, `execution_completed`. The closed-credit snapshot fact is added once at closing. Validation:
each configured return adapter validates; UniProt and Rfam returns validate when bound; every `x-source` field must
equal its (live or frozen) fact.

## Differences from similar episodes

- Shares most files with `hpc_allocation_execution/execution_job_submission` (same `binding_roles`, `configuration`,
  `terminal_execution`, `task_instructions`, presentation, input versions, closed credit); they differ in role,
  tools, credit, completion and yield (see that page).
- Unlike the launch episode it has no children and its permitted actions are only `tool` (and `wait` for API service
  targets); its task loop keeps reasoning-commit, job-child failure, `reads.map` diagnostics, automatic score update and
  shared grading branches that the launch copy also partly carries.
- Its decision snapshot is a free function in `internal_summary.py`; the launch episode has it as a class.
- `configuration.py` imports `TerminalExecutionBehavior` from this episode's own `terminal_execution.py`.
- The copy under `hpc_allocation_execution/execution_result_acquisition` (the HPC episode's `results` child) was not
  read.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | Empty package marker. | none |
| `action_outcome.py` | 5 | Shape of one tool outcome: completed with references, or invalid with an `arguments_or_reference` feedback code. | none |
| `binding_record.py` | 9 | Binding identity record: id, version `execution_episode_v1`, configuration (resources, initial information, handoff and acquired-record units, log window bytes and roles, private-yield flag, results and task yield profiles). | none |
| `binding_roles.py` | 6 | Role vocabulary shared with the launch family (`launch`, `launch_api`, `launch_local`, `launch_hpc`, `results`) and resource-kind mapping (local, pbs_ssh to hpc, hmmer_api/api to api). | none |
| `closed_credit.py` | 122 | Freezes the operational credit view into the closing facts once (`execution_closed_operational_credit_v1`) with digests of context, binding, completion, archive, observation history and receipt prefix; on later reads returns only that frozen view, never a re-projection. | `BindingContext`: as_record×2, episode_id×8, role; `imports root.a107`: communication, episode_receipts, episode_return_records×3, execution_contracts×2; `names`: EpisodeReceipts×2, EpisodeReturnRecords×2; `tables`: runtime_episodes×2, runtime_forms×3, runtime_observations, runtime_receipt_inheritance×2, runtime_record_receipts×2 |
| `completion.py` | 184 | Practical completion proofs: native windows must cover every requested byte range of a completed returncode-0 attempt; delegates to each native adapter (BLAST masking/utility/database/standard database, HMMER, Infernal, RNA structure, expression NMF) or the API execution; verification reuses a recorded endpoint verdict for a closed episode. | `BindingContext`: assignment×4, episode_id×8, run_id×4, scope; `imports root.a107`: communication, episode_return_records, execution_contracts×2, method_loop.identities, native_blast_database_acquisition, native_blast_standard_database_acquisition, native_rna_structure_acquisition, numerical, practical_execution_records, practical_yield; `names`: ESTIMATOR_VERSION×2, NumericBand×2, UnitRef×2; `tables`: runtime_actions×2, runtime_observations |
| `configuration.py` | 120 | Constructor operands and validation: explicit resources (kinds local/pbs_ssh/api), initial inventory per resource, positive handoff and acquired-record credit units, log window, private yield flag, `results_yield_profiles` (only native_unbounded_local / native_unbounded_hpc) and `task_yield_profiles`; builds terminal behaviours, API execution, progress provider, local file sources and the native result readers that are configured. | `imports root.a107`: a107_execution_bindings×4, api_service_execution, communication, execution_contracts, execution_progress, expression_nmf_returns, local_file_capture_results, native_expression_nmf_contracts, native_expression_nmf_results, native_infernal_preparation_results, native_infernal_preparation_returns, native_infernal_preparation_tool_info, native_infernal_results, native_infernal_returns, native_infernal_tool_info, native_rna_structure_contracts, native_rna_structure_results, native_rna_structure_returns, numerical, rna_structure_comparison_results, rna_structure_comparison_returns; `names`: YieldController×3, YieldParameters×3 |
| `credit.py` | 81 | Operational credit: delegates to the native adapter or API; otherwise `handoff_unit * 0 + acquired_record_unit * new selector byte coverage fraction` (coverage of requested byte positions not already in the initial records), or a count-based variant for local file sources. | `BindingContext`: assignment; `imports root.a107`: communication |
| `credit_records.py` | 3 | Name of the frozen closed-credit fact. | none |
| `episode.py` | 109 | Composes the binding: path, parent `partner_presence_evidence/hpc_work_planning`, role `results`, no entry roles, `replaces_default_instructions`, decision source `ResultsTask`, prompt renderer `present_results_context`; binds the received-result reader functions and target predicates as methods. | `imports root.a107`: a107_blast_execution, communication, execution_contracts, library.execution_resource_information×2, library.received_execution_information.received_result_readers×20, library.received_execution_targets×8 |
| `from_parent.py` | 122 | Assignment schema `RESULTS_SCHEMA` extended with selector variants (local file source, native result selectors, expression NMF, RNA structure and comparison); assignment preparation restores a recorded commission, resolves the handoff target and validates selected inputs per selector kind; initial references per role. Requires return source `execution_result_refs` under the axis head when an annotation task is required. | `BindingContext`: assignment×2, path, role×5; `imports root.a107`: a107_execution_bindings×2, communication, execution_contracts×2, expression_nmf_result_contracts, launch_instructions, library.execution_result_contract, local_file_capture_results×2, native_blast_database_acquisition, native_blast_database_result_publication×2, native_blast_standard_database_acquisition, native_blast_standard_database_result_publication×2, native_rna_structure_acquisition, native_rna_structure_result_publication×3, resource_records, rna_structure_comparison_contracts, rna_structure_comparison_operands×2, rna_structure_result_views; `services`: annotation_task_required |
| `goal.py` | 19 | No children; common actions `tool` only, plus `wait` for an `api_service_assignment_v1` API target. | `imports root.a107`: communication |
| `initial_information.py` | 12 | Initial information: for local file sources only the local resource capability; otherwise resource and received API information from this binding path's readers. | `catalog`: readers; `imports root.a107`: library.execution_initial_information.presentation |
| `input_versions.py` | 21 | Validation of masking, utility and expression NMF job inputs and immutable input versions through library functions. | `imports root.a107`: execution_input_versions, expression_nmf_operands, library.received_execution_information.received_result_readers |
| `instructions.py` | 7 | The episode's goal text (see "What this episode is for"). | none |
| `internal_summary.py` | 97 | Decision context: assignment, live facts as `execution_progress`, the target and its description, and `selected_execution_task` (scientific question and selected tool info from the scientific parent). Also holds the episode's own copy of the old decision snapshot builder. | `BindingContext`: assignment×3, scope; `imports root.a107`: communication, expression_nmf_execution_information, expression_nmf_presentation, local_file_capture_results, native_profile_presentation, runtime×2; `journal`: elapsed_view, row; `runtime`: FACT_MEANINGS, FACT_SOURCES, json×2, Mapping×3, _plain×2, _references_in; `self.workflow`: binding_context, catalog, controller_binding, delivery_status, extra_report_sources, job_episode_options, journal×3, knowledge, local_outcome_preview, pending_work, run_id, source_credit_binding, source_credit_view, specialist, store×3, tools, working_state; `services`: scientific_parent_task; `tables`: runtime_actions×2; `view`: child_reports×2, controller_state, model_inputs |
| `native_file_acquisition.py` | 63 | Native result acquisition for `execution.results.status/collect/read`: immutable intent, one observation and per-window files under the result directory; refuses after a completed proof; publishes one `execution_result_information_v2` source. | `BindingContext`: assignment×3, episode_id×4, run_id, scope; `imports root.a107`: communication, execution_contracts, practical_execution_state×2; `tables`: runtime_actions |
| `native_target_state.py` | 8 | `state` is not available for the results role. | none |
| `presentation.py` | 73 | Prompt presentation: chooses the text renderer by context kind (HPC, published scientific, API launch, RNA comparison/structure, selected execution, monitor, RNA comparison receiver) or plain JSON. | `imports root.a107`: decision_context, execution_prompt, infernal_result_presentation, library.hpc_prompt, library.monitor_prompt, library.scientific_decision_presentation×2, partner_presence_evidence.task_decision, rna_structure_comparison_presentation, rna_structure_comparison_prompt, rna_structure_comparison_receiver_prompt, rna_structure_presentation, rna_structure_prompt; `provider`: scientific_prompt_states×4 |
| `receipt_selection.py` | 35 | Classifies known records into received handoffs and result bodies for this assignment. | `BindingContext`: assignment, role, scope×2; `imports root.a107`: communication |
| `received_api_reports.py` | 4 | Selects this binding path's declared API reader authority. | `catalog`: configured, received |
| `received_execution_information.py` | 4 | Selects this binding path's declared result readers. | `catalog`: configured, received |
| `received_launch_records.py` | 3 | Launch assignment version name. | none |
| `received_launch_requests.py` | 69 | Launch request schema and validation (kept in the results binding for launch-family role checks). | `imports root.a107`: a107_blast_execution×2, a107_execution_bindings×2, execution_contracts, native_expression_nmf_tool_info, native_infernal_preparation_tool_info, native_infernal_tool_info, native_rna_structure_tool_info, practical_execution_records×2 |
| `report_delivery.py` | 23 | Generic old finish (identical to the monitor copy apart from names). | `imports root.a107`: runtime×2; `journal`: row, save; `runtime`: form_with_facts, _json×2, json, Record×2; `self.workflow`: binding_context, episode_bindings, facts, journal×2, pending_handles, release×2, source_credit_view; `tables`: runtime_forms×2 |
| `resource_information.py` | 68 | Declares bound launch, result and homology operation contracts per resource. | `imports root.a107`: a107_execution_bindings×3, execution_contracts×2, library.execution_operation_information, native_expression_nmf_tool_info, native_infernal_preparation_tool_info, native_infernal_tool_info, native_rna_structure_tool_info |
| `result_publication.py` | 13 | Publishes a result body as a Store source `episode.execution_result`. | `BindingContext`: episode_id, run_id, scope; `imports root.a107`: execution_contracts×2 |
| `result_records.py` | 14 | Result record names, native result origin qualification and the native result operation catalog. | `imports root.a107`: execution_contracts |
| `result_state.py` | 26 | Initialization per target kind; a BLAST-graded target requires its typed graded return in the parent's form. | `BindingContext`: assignment×5, request, scope; `imports root.a107`: a107_blast_execution×2, communication |
| `saved_commission.py` | 46 | Restores a successfully returned original results commission on resume. | `BindingContext`: episode_id×3, path, request; `imports root.a107`: communication, episode_receipts, episode_return_records; `names`: EpisodeReceipts×2, EpisodeReturnRecords×2; `tables`: runtime_actions, runtime_episodes, runtime_report_attempts |
| `schema_fields.py` | 6 | Shared schema fragments (text, offset, limit, 1 MiB file limit). | none |
| `selector_records.py` | 7 | Native selector schema (paths/path/offset/limit). | `imports root.a107`: execution_contracts |
| `target_custody.py` | 68 | Target/context consistency checks and the BLAST grader requirement rebuilt from the original launch request. | `BindingContext`: assignment×2, role×3, scope×3; `imports root.a107`: a107_blast_execution×2, communication, execution_contracts; `tables`: runtime_episodes×2 |
| `task.py` | 228 | Generic old task loop, with results-specific additions: reasoning-commit admission (empty commits rejected), job-child storage failure feedback, `reads.map` parameter diagnostics, reasoning execution, automatic score updates and shared grading retention. | `imports root.a107`: episode_source_failure, providers, read_mapping, runtime×2; `journal`: measure, row×7, save×3; `names`: ModelCallError×2; `runtime`: AcquisitionError×2, ActionFailure, ContractError, ContractInformationError, _decode_recorded_action_response, Draft202012Validator×3, EventTargetError×2, inspect, _json×5, json×8, Mapping×3, nullcontext×5, observes_action_outcome, ReportBoundaryError, ReportRedelivery×2, schema_failure_diagnostic, SourceEnd×2, sqlite3×2, subprocess×2, validate_form, ValidationError×3, _wait_target_feedback×2, WorkflowError×2; `self.workflow`: action_schema, automatic_score_updates, binding_context×2, completed_unit×3, completions×3, controller_value×2, decision_exchanges×3, delivery_resolution_inputs, execute, execution_binding×7, inprocess_replay×4, journal×7, last_observed_credit, next_return, pending_work, perform_selected_wait, permits_common_action, reasoning_action_schema, receive_native_outcome, receive_outcome, resolve_pending_deliveries, resolver, retain_shared_grading_results, run_id×3, selected×3, source_credit_view, specialist×2, store×9, validate_report; `tables`: runtime_actions×8, runtime_episodes, runtime_model_calls×2; `view`: units_consumed×4 |
| `task_decision.py` | 360 | Generic old model-call machinery with the results decision inputs inlined (shared information context, requested action history for HPC contexts, literature numerical contracts) and a private provider completion that uses the binding's prompt renderer only for the original model class. | `exchanges`: measure, prepare, resolve_lookup, respond, rows; `imports root.a107`: episode_work_report×2, library.hpc_prompt, providers, runtime×2; `journal`: measure×2, row×2, save×4; `provider`: complete; `runtime`: _action_generation_schema×2, apply_state_frame, _ASSIGNMENT_TRANSPORT, _category_yield_parameters, child_option_information×2, composition_lookup_schema×2, CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION×2, DECISION_EXCHANGE_PROTOCOL×5, _digest, Draft202012Validator, infernal_receiver_context×2, instructional_model_context×4, is_contract_information, _json×14, json×3, lookup_attempts, Mapping×4, model_snapshot×2, _object×3, _plain×2, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, requested_contract_information×2, schema_failure_diagnostic×2, sqlite3, state_frame, ValidationError×5, WorkflowError×14, yield_table; `self.workflow`: available_child_roles, binding_context, contract_information_profile, contract_information_reply, controller_binding, decision_exchanges×4, decision_protocol×3, episode_bindings, execute, execution_expectations, freeze_contract_information, freeze_literature_numerical_contracts, history_preview, journal×3, launch_instructions×2, native_estimation_context, numerical_contracts, pending_work, permits_common_action, provider×3, receipts×4, resource_context, resource_estimator×4, run_id, services×2, shared_information_context, specialist, store×2, uses_received_record_context×2, validate_contract_information×5, waiting_support; `tables`: runtime_model_calls×8 |
| `task_instructions.py` | 28 | Instruction composition: job-episode instructions or default runtime instructions, replaced by the binding goal (`replaces_default_instructions`), plus reasoning, knowledge, launch library, repair, wait, native-event and exchange history text. | `imports root.a107`: library.scientific_instruction_text×3, runtime_prompt; `runtime_prompt`: DECISION_EXCHANGE_PROTOCOL, INSTRUCTIONS×4, REASONING_COMMIT_REQUIREMENT; `self.workflow`: binding_context, decision_protocol, is_job_source, job_episodes, knowledge, launch_instructions, native_event_information, permits_common_action×3, specialist |
| `task_state.py` | 108 | Generic old per-episode state (identical to the monitor copy apart from names). | `imports root.a107`: episode_source_failure, runtime×2; `journal`: row×3, save×2; `runtime`: ActionLeaf, EFFECT_VERSION, Episode, interpretation_schema, _json×2, json×4, _object, _plain, Record; `self.workflow`: archive, completions×4, context, controller_value, execution_binding×4, grains, inprocess_replay×7, journal×5, progress_provider×2, recover_commissions, run_id, source_credit_view, store×2; `tables`: runtime_actions×5 |
| `task_suspension.py` | 9 | Generic old suspension hook. | `self.workflow`: execution_backend, execution_handle×2 |
| `terminal_execution.py` | 131 | Instruction-led terminal execution behaviour for local/HPC launch roles: the model chooses commands; immutable receipts, validations, completion proof and practical estimator. | `BindingContext`: assignment×6, episode_id×4, role, run_id×5; `imports root.a107`: acquisition, communication, domain, library.execution_operation_information, practical_execution_operations, practical_execution_records, practical_execution_state, practical_receipt_information×3, practical_yield, terminal_execution, terminal_scientific_evidence×2; `names`: PracticalYieldEstimator×2 |
| `to_parent.py` | 145 | Live facts per adapter (native empty sources merged), API facts with BLAST grader rows, native handoff/result refs, file sources, origin and `execution_completed`; frozen closed-credit facts; report validation against recorded facts. | `BindingContext`: assignment, scope×2; `imports root.a107`: a107_blast_execution×2, blast_pairwise_result_views, blast_utility_result_views, communication×2, expression_nmf_return_views, hmmer_native_result_views, hmmer_preparation_result_views, infernal_native_result_views, infernal_preparation_result_views, native_blast_database_results, native_blast_standard_database_results, rna_structure_comparison_views, rna_structure_result_views×2, sequence_masking_result_views, tool_grading_artifacts, uniprot_return_contracts |
| `work_operations.py` | 121 | Tool catalog and dispatch per target kind (see "Tools"). | `BindingContext`: assignment×12; `imports root.a107`: communication, execution_contracts, library.execution_resource_information, native_blast_acquisition, native_blast_database_acquisition, native_blast_database_results, native_blast_masking_results, native_blast_results, native_blast_standard_database_acquisition, native_blast_standard_database_results, native_blast_utility_results, native_expression_nmf_results, native_file_capture, native_hmmer_acquisition, native_hmmer_preparation_acquisition, native_hmmer_preparation_results, native_hmmer_results, native_infernal_acquisition, native_infernal_preparation_acquisition, native_infernal_preparation_results, native_infernal_results, native_rna_structure_acquisition, native_rna_structure_results, rna_structure_comparison_results |
| `yield_estimator.py` | 99 | Private continuation selection per assignment kind (see "Continuation"). | `BindingContext`: assignment; `imports root.a107`: communication, execution_contracts×3, library.execution_result_contract, native_blast_database_acquisition, native_blast_standard_database_acquisition, native_rna_structure_acquisition, numerical, practical_execution_records, practical_yield×2; `names`: estimate_bounded_credit_yield×2, NumericBand×2, PracticalYieldEstimator×5, YieldController×4, YieldEstimate×2, YieldParameters×4 |

## Carried over

Carried on 19 November 2026 into `gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/execution_result_acquisition/` (ten files, no children). One row per row of `runs/carry_over/functions/a107__partner_presence_evidence__hpc_work_planning__execution_result_acquisition.tsv`. Nothing was copied from another episode folder. "unplaced" rows are listed with their reason in `docs/axis_restructure_20261117/carry_over_blocked/a107__partner_presence_evidence__hpc_work_planning__execution_result_acquisition.md`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| action_outcome.py | _outcome | episode function | task.py _outcome |
| binding_record.py | ResultsBindingRecord | machinery | the binding's own as_record() and its configuration record (binding_record.py); settings are journaled by the system |
| binding_record.py | ResultsBindingRecord.as_record | machinery | the binding's own as_record() and its configuration record (binding_record.py); settings are journaled by the system |
| closed_credit.py | ResultsClosedCredit | machinery | the pinned closed credit view: receipts and runtime_* digests of the old runner; the system hands the credit its controller last saw to final_to_parent |
| closed_credit.py | ResultsClosedCredit._closed_credit_carrier | machinery | the pinned closed credit view: receipts and runtime_* digests of the old runner; the system hands the credit its controller last saw to final_to_parent |
| closed_credit.py | ResultsClosedCredit._closed_credit_receipts | machinery | the pinned closed credit view: receipts and runtime_* digests of the old runner; the system hands the credit its controller last saw to final_to_parent |
| closed_credit.py | ResultsClosedCredit._closed_credit_value | machinery | the pinned closed credit view: receipts and runtime_* digests of the old runner; the system hands the credit its controller last saw to final_to_parent |
| closed_credit.py | ResultsClosedCredit._closed_credit_facts | machinery | the pinned closed credit view: receipts and runtime_* digests of the old runner; the system hands the credit its controller last saw to final_to_parent |
| closed_credit.py | ResultsClosedCredit._closed_operational_credit_view | machinery | the pinned closed credit view: receipts and runtime_* digests of the old runner; the system hands the credit its controller last saw to final_to_parent |
| completion.py | ResultsCompletion | machinery | container of the practical completion proof for the old PracticalYieldEstimator (README 3d: completion proof is not a controller input); its native function is placed as messages/internal_summary.py native_results_complete |
| completion.py | ResultsCompletion._native_results_complete | episode function | messages/internal_summary.py native_results_complete (library candidate); the typed-host branches (local file sources, masking, utility, NMF, RNA structure, standard and native BLAST database) return False in the old code and are not carried (BLOCKED-ON-JOB-SERVICE) |
| completion.py | ResultsCompletion._proof_for_action | machinery | completion proof lookup per action for the estimator and the refusal after completion; the refusal is carried by the completed flag of messages/internal_summary.py (read in task.py acquire); typed-host proofs BLOCKED-ON-JOB-SERVICE |
| completion.py | ResultsCompletion.completion_for_action | machinery | estimator packet (completion proof in the controller input); README 3d: deleted |
| completion.py | ResultsCompletion._closed_completion_verdict | machinery | reading earlier runtime_observations and the recorded endpoint verdict; deleted (README 3d) |
| completion.py | ResultsCompletion.verify_completion | machinery | completion verification for the old PracticalYieldEstimator; deleted (README 3d, 7b) |
| configuration.py | ResultsConfiguration | episode function | values split: messages/read_from_parent.py (positive acquired_record_unit check), task.py (ctx.settings log_window_bytes, knowledge and launch directories), yield_estimator.py (yield profiles); resource and provider construction is machinery (per-axis providers) and the host construction BLOCKED-ON-JOB-SERVICE |
| configuration.py | ResultsConfiguration.__init__ | episode function | same split as the class: messages/read_from_parent.py, task.py, yield_estimator.py; handoff_unit is not carried (always multiplied by a count fixed at zero); require_private_yield, the typed host construction and the practical behaviours are machinery or BLOCKED-ON-JOB-SERVICE |
| credit.py | ResultsCredit | episode function | credit.py credit |
| credit.py | ResultsCredit._generic_result_selector_progress | episode function | credit.py selector_progress (library candidate) |
| credit.py | ResultsCredit.credit_kind | machinery | role lookup of the credit kind (README 3d: credit_kind deleted) |
| credit.py | ResultsCredit.project_credit | episode function | credit.py credit; the closed-view branch is machinery, the typed-host and API credit views BLOCKED-ON-JOB-SERVICE |
| credit.py | ResultsCredit._live_project_credit | episode function | credit.py credit (native branch); the typed-host, API and local file source credit views BLOCKED-ON-JOB-SERVICE |
| credit.py | ResultsCredit.credit_view | machinery | the old credit view record; credit returns the number |
| episode.py | ExecutionEpisode | episode function | episode.py ExecutionResultAcquisition |
| from_parent.py | ResultsFromParent | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM, read_from_parent) |
| from_parent.py | ResultsFromParent.required_return_sources | machinery | the parent states which return sources it wants; the parent selects fields of RETURN_FORM in msg_to_child (README 3b C4) |
| from_parent.py | ResultsFromParent.child_assignment_schema | machinery | the parent states what the child takes; the child's form is ASSIGNMENT_FORM (README 3b C3); the body had a dead branch |
| from_parent.py | ResultsFromParent.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and NATIVE_SELECTOR_SCHEMA; the typed selector variants are BLOCKED-ON-JOB-SERVICE |
| from_parent.py | ResultsFromParent.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent and native_windows (native selector admission and workspace confinement); the typed target admissions (local file source, masking, utility, RNA, BLAST database) BLOCKED-ON-JOB-SERVICE; restoring a saved commission is machinery |
| from_parent.py | ResultsFromParent.initial_references | episode function | messages/read_from_parent.py ASSIGNMENT_FORM handoff_ref, initial_result_refs, initial_result_artifact_refs (custody passes them); the typed validate_selected_inputs BLOCKED-ON-JOB-SERVICE |
| goal.py | ResultsGoal | episode function | goal.py and task.py |
| goal.py | ResultsGoal.child_roles | machinery | no children: CHILD_SLOTS = {} in task.py |
| goal.py | ResultsGoal.allowed_children | machinery | no children: CHILD_SLOTS = {} in task.py |
| goal.py | ResultsGoal.permitted_common_actions | episode function | task.py (the model selects a tool only); the wait action of an API target is wait machinery and API targets are not carried (BLOCKED-ON-JOB-SERVICE) |
| initial_information.py | initial_information | episode function | task.py decide (the target, its description and the selected task are read from job_access); resource capabilities and received API information BLOCKED-ON-JOB-SERVICE |
| input_versions.py | ResultsInputVersions | episode function | unplaced: BLOCKED-ON-JOB-SERVICE: the typed result host's validate_selected_inputs (the old from_parent.py called it for a typed selector, which messages/read_from_parent.py raises for); wanted call: ctx.services['job_access'].result_host(target).validate_selected_inputs(...); not a launch-role function of this episode |
| input_versions.py | ResultsInputVersions._masking_inputs | episode function | unplaced: BLOCKED-ON-JOB-SERVICE: the typed result host's validate_selected_inputs (the old from_parent.py called it for a typed selector, which messages/read_from_parent.py raises for); wanted call: ctx.services['job_access'].result_host(target).validate_selected_inputs(...); not a launch-role function of this episode |
| input_versions.py | ResultsInputVersions._utility_inputs | episode function | unplaced: BLOCKED-ON-JOB-SERVICE: the typed result host's validate_selected_inputs (the old from_parent.py called it for a typed selector, which messages/read_from_parent.py raises for); wanted call: ctx.services['job_access'].result_host(target).validate_selected_inputs(...); not a launch-role function of this episode |
| input_versions.py | ResultsInputVersions._expression_nmf_inputs | episode function | unplaced: BLOCKED-ON-JOB-SERVICE: the typed result host's validate_selected_inputs (the old from_parent.py called it for a typed selector, which messages/read_from_parent.py raises for); wanted call: ctx.services['job_access'].result_host(target).validate_selected_inputs(...); not a launch-role function of this episode |
| input_versions.py | ResultsInputVersions._versions | episode function | unplaced: BLOCKED-ON-JOB-SERVICE: the typed result host's validate_selected_inputs (the old from_parent.py called it for a typed selector, which messages/read_from_parent.py raises for); wanted call: ctx.services['job_access'].result_host(target).validate_selected_inputs(...); not a launch-role function of this episode |
| instructions.py | ResultsInstructions | episode function | goal.py GOAL and task.py instructions |
| instructions.py | ResultsInstructions.instructions | episode function | goal.py GOAL (text unchanged); composed in task.py instructions |
| internal_summary.py | ResultsInternalSummary | episode function | messages/internal_summary.py internal_summary and task.py decide |
| internal_summary.py | ResultsInternalSummary._with_selected_execution_task | episode function | task.py decide (selected_execution_task from the commissioner's message, constraints and selector); the typed job views (NMF, HMMER scientific job views) and the resource information BLOCKED-ON-JOB-SERVICE |
| internal_summary.py | ResultsInternalSummary.decision_context | episode function | messages/internal_summary.py internal_summary (execution_progress) and task.py decide (execution_assignment, execution_target, execution_target_description); the local file source and NMF descriptions BLOCKED-ON-JOB-SERVICE |
| internal_summary.py | results_decision_snapshot | episode function | messages/internal_summary.py internal_summary (credit-facing state, last outcomes, yield table) and task.py decide (tools, time, library listings); its journal rows, working state, report update, report deliveries, pending work and visible-reference basis are old-runner machinery |
| native_file_acquisition.py | ResultsNativeFileAcquisition | episode function | task.py acquire |
| native_file_acquisition.py | ResultsNativeFileAcquisition._execute_native_results | episode function | task.py acquire and requested_windows (the immutable intent, observation and window files and the runtime_actions read are machinery; the refusal after a completed endpoint is an invalid outcome) |
| native_target_state.py | ResultsNativeTargetState | episode function | unplaced, not repaired: member of the old shared ExecutionEpisode mixin that no call of the results role reaches (state raised practical_resource_role_required); the launch episodes carry their own; library candidate if a launch episode needs it |
| native_target_state.py | ResultsNativeTargetState.state | episode function | unplaced, not repaired: member of the old shared ExecutionEpisode mixin that no call of the results role reaches (state raised practical_resource_role_required); the launch episodes carry their own; library candidate if a launch episode needs it |
| presentation.py | present_results_context | episode function | task.py decide (the context mapping); the text renderers (render_selected_execution_prompt, render_hpc_prompt, RNA, API) are in the old shared root and are not carried (README 5 item 16); the state-frame reconstruction is machinery |
| receipt_selection.py | ResultsReceiptSelection | episode function | messages/internal_summary.py _initial_bodies and internal_summary |
| receipt_selection.py | ResultsReceiptSelection._received | episode function | messages/internal_summary.py _initial_bodies (known retained results of this assignment, read through held records) and internal_summary; the practical-receipt and API handoff classification is replaced by handoff_ref in custody (BLOCKED-ON-JOB-SERVICE for its target) |
| received_api_reports.py | received_api_reports | machinery | catalog selection of this path's declared API reader authority (per-axis provider catalog); the API host itself is BLOCKED-ON-JOB-SERVICE |
| received_execution_information.py | received_execution_information | machinery | catalog selection of this path's declared result readers (per-axis provider catalog); the typed hosts themselves are BLOCKED-ON-JOB-SERVICE |
| received_launch_requests.py | ResultsReceivedLaunchRequests | episode function | unplaced: BLOCKED-ON-JOB-SERVICE: the typed result host's validate_selected_inputs (the old from_parent.py called it for a typed selector, which messages/read_from_parent.py raises for); wanted call: ctx.services['job_access'].result_host(target).validate_selected_inputs(...); not a launch-role function of this episode |
| received_launch_requests.py | ResultsReceivedLaunchRequests._permitted | episode function | unplaced: BLOCKED-ON-JOB-SERVICE: the typed result host's validate_selected_inputs (the old from_parent.py called it for a typed selector, which messages/read_from_parent.py raises for); wanted call: ctx.services['job_access'].result_host(target).validate_selected_inputs(...); not a launch-role function of this episode |
| received_launch_requests.py | ResultsReceivedLaunchRequests._request_schema | episode function | unplaced: BLOCKED-ON-JOB-SERVICE: the typed result host's validate_selected_inputs (the old from_parent.py called it for a typed selector, which messages/read_from_parent.py raises for); wanted call: ctx.services['job_access'].result_host(target).validate_selected_inputs(...); not a launch-role function of this episode |
| received_launch_requests.py | ResultsReceivedLaunchRequests._launch | episode function | unplaced: BLOCKED-ON-JOB-SERVICE: the typed result host's validate_selected_inputs (the old from_parent.py called it for a typed selector, which messages/read_from_parent.py raises for); wanted call: ctx.services['job_access'].result_host(target).validate_selected_inputs(...); not a launch-role function of this episode |
| received_launch_requests.py | ResultsReceivedLaunchRequests._constraints | episode function | unplaced: BLOCKED-ON-JOB-SERVICE: the typed result host's validate_selected_inputs (the old from_parent.py called it for a typed selector, which messages/read_from_parent.py raises for); wanted call: ctx.services['job_access'].result_host(target).validate_selected_inputs(...); not a launch-role function of this episode |
| report_delivery.py | ResultsReportDelivery | machinery | the generic old finish (report_form machinery, runtime_forms, release); the result is final_to_parent |
| report_delivery.py | ResultsReportDelivery.finish | machinery | the generic old finish (report_form machinery, runtime_forms, release); the result is final_to_parent |
| resource_information.py | ResultsResourceInformation | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (resource and operation contracts per resource need job_access reads) |
| resource_information.py | ResultsResourceInformation.resource_tool_contracts | episode function | unplaced: BLOCKED-ON-JOB-SERVICE; wanted call ctx.services['job_access'].read('resource_tool_contracts', resource_id) |
| result_publication.py | ResultsResultPublication | episode function | task.py _publish |
| result_publication.py | ResultsResultPublication._publish_result | episode function | task.py _publish (source episode.execution_result and its artifact, written through ctx.store) and validate_result_body |
| result_records.py | native_result_operation_catalog | episode function | task.py CATALOG and operation_catalog |
| result_state.py | ResultsResultState | episode function | messages/read_from_parent.py (selector check) and task.py |
| result_state.py | ResultsResultState.initialize | episode function | messages/read_from_parent.py native_windows (the selector check against the target); the BLAST grader typed return requirement, the NMF/masking/utility initial references and the API initialization BLOCKED-ON-JOB-SERVICE; creating the result directory is machinery (immutable files) |
| saved_commission.py | ResultsSavedCommission | machinery | restoring a returned original commission from runtime_* tables and the receipt ledger (resume is the runner) |
| saved_commission.py | ResultsSavedCommission._recorded_results_assignment | machinery | restoring a returned original commission from runtime_* tables and the receipt ledger (resume is the runner) |
| target_custody.py | ResultsTargetCustody | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (target consistency and the BLAST grader requirement need the handoff target and the original launch request) |
| target_custody.py | ResultsTargetCustody._context_target | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (results branch compares the target of the context with the handoff target) |
| target_custody.py | ResultsTargetCustody._blast_target_requirement | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (rebuilds the original BLAST return check from runtime_episodes and the launch request; wanted: the original launch request in custody) |
| task.py | ResultsTask | episode function | task.py decide, action, TOOLS (the loop is the system's) |
| task.py | ResultsTask.next | machinery | the old decision loop (calls, exchange, journal rows); decide and action in task.py |
| task.py | ResultsTask.apply_response | episode function | task.py action (schema validation and rejection with a diagnostic); the reasoning-commit, job-child, reads.map and report-update branches, record_effect and the runtime_actions reads are machinery or not permitted here |
| task.py | ResultsTask.execute | episode function | task.py tools (the selected tool runs); the runtime_actions rows, automatic_score_updates, receive_outcome, completions staging, controller_value and checkpoint are machinery |
| task_decision.py | ResultsTaskDecision | episode function | task.py decide |
| task_decision.py | ResultsTaskDecision.call | episode function | task.py decide (the results decision inputs: execution context, instructions, tools); the saved-request checks, runtime_model_calls rows, receipts.receive, shared information, literature numerical contract freezing, contract information and requested_action_history are machinery |
| task_decision.py | ResultsTaskDecision.instructions | episode function | task.py instructions |
| task_decision.py | ResultsTaskDecision.conversation_key | machinery | conversation state of the old provider session (README 3a) |
| task_decision.py | ResultsTaskDecision.interpretation_context | machinery | decision-exchange loop |
| task_decision.py | ResultsTaskDecision.exchange_schema | machinery | decision-exchange loop |
| task_decision.py | ResultsTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | ResultsTaskDecision.validate_contract_exchange_request | machinery | saved-request checks of the decision exchange |
| task_decision.py | ResultsTaskDecision.validate_contract_exchange_history | machinery | saved-request checks of the decision exchange |
| task_decision.py | ResultsTaskDecision.exchange_decision | machinery | decision-exchange loop (exchange_decision) |
| task_decision.py | ResultsTaskDecision.decision_completion | machinery | provider patching (private provider completion with the binding prompt renderer) |
| task_instructions.py | instructions | episode function | task.py instructions (goal text, knowledge and launch-library texts); the reasoning-commit, repair, pending-delivery, wait, native-event and exchange-history paragraphs describe actions this episode does not have |
| task_state.py | ResultsTaskState | machinery | old per-episode state, checkpoint and restore (inprocess_replay, runtime_actions); state is the view |
| task_state.py | ResultsTaskState.__init__ | machinery | old per-episode state, checkpoint and restore (inprocess_replay, runtime_actions); state is the view |
| task_state.py | ResultsTaskState.bind_execution_context | machinery | old per-episode state, checkpoint and restore (inprocess_replay, runtime_actions); state is the view |
| task_state.py | ResultsTaskState.record_execution_failure | machinery | old per-episode state, checkpoint and restore (inprocess_replay, runtime_actions); state is the view |
| task_state.py | ResultsTaskState.restore_checkpoint | machinery | old per-episode state, checkpoint and restore (inprocess_replay, runtime_actions); state is the view |
| task_state.py | ResultsTaskState.restore | machinery | old per-episode state, checkpoint and restore (inprocess_replay, runtime_actions); state is the view |
| task_state.py | ResultsTaskState.record_effect | machinery | old per-episode state, checkpoint and restore (inprocess_replay, runtime_actions); state is the view |
| task_state.py | ResultsTaskState.checkpoint | machinery | old per-episode state, checkpoint and restore (inprocess_replay, runtime_actions); state is the view |
| task_suspension.py | ResultsTaskSuspension | machinery | wait/suspension machinery (execution_backend set_suspension) |
| task_suspension.py | ResultsTaskSuspension.suspension_changed | machinery | wait/suspension machinery (execution_backend set_suspension) |
| terminal_execution.py | TerminalExecutionBehavior | episode function | unplaced, not repaired: member of the old shared ExecutionEpisode mixin that no call of the results role reaches (state raised practical_resource_role_required); the launch episodes carry their own; library candidate if a launch episode needs it |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | machinery | per-axis provider and old-runner construction (directory, store, resources) |
| terminal_execution.py | TerminalExecutionBehavior._operations | episode function | unplaced, not repaired: member of the old shared ExecutionEpisode mixin that no call of the results role reaches (state raised practical_resource_role_required); the launch episodes carry their own; library candidate if a launch episode needs it |
| terminal_execution.py | TerminalExecutionBehavior._assignment | episode function | unplaced, not repaired: member of the old shared ExecutionEpisode mixin that no call of the results role reaches (state raised practical_resource_role_required); the launch episodes carry their own; library candidate if a launch episode needs it |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | machinery | immutable state directory of the old runner |
| terminal_execution.py | TerminalExecutionBehavior.initialize | episode function | unplaced, not repaired: member of the old shared ExecutionEpisode mixin that no call of the results role reaches (state raised practical_resource_role_required); the launch episodes carry their own; library candidate if a launch episode needs it |
| terminal_execution.py | TerminalExecutionBehavior.state | episode function | unplaced, not repaired: member of the old shared ExecutionEpisode mixin that no call of the results role reaches (state raised practical_resource_role_required); the launch episodes carry their own; library candidate if a launch episode needs it |
| terminal_execution.py | TerminalExecutionBehavior.catalog | episode function | unplaced, not repaired: member of the old shared ExecutionEpisode mixin that no call of the results role reaches (state raised practical_resource_role_required); the launch episodes carry their own; library candidate if a launch episode needs it |
| terminal_execution.py | TerminalExecutionBehavior.execute | episode function | unplaced, not repaired: member of the old shared ExecutionEpisode mixin that no call of the results role reaches (state raised practical_resource_role_required); the launch episodes carry their own; library candidate if a launch episode needs it |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | machinery | completion proof for the estimator (README 3d: deleted) |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator (README 7b: deleted) |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | episode function | unplaced, not repaired: member of the old shared ExecutionEpisode mixin that no call of the results role reaches (state raised practical_resource_role_required); the launch episodes carry their own; library candidate if a launch episode needs it |
| terminal_execution.py | TerminalExecutionBehavior.facts | episode function | unplaced, not repaired: member of the old shared ExecutionEpisode mixin that no call of the results role reaches (state raised practical_resource_role_required); the launch episodes carry their own; library candidate if a launch episode needs it |
| terminal_execution.py | TerminalExecutionBehavior.resolve | machinery | reference resolution for the old report form (workflow.resolver) |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | episode function | unplaced, not repaired: member of the old shared ExecutionEpisode mixin that no call of the results role reaches (state raised practical_resource_role_required); the launch episodes carry their own; library candidate if a launch episode needs it |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | machinery | the old credit view record |
| to_parent.py | ResultsToParent | episode function | messages/final_to_parent.py (RETURN_FORM, final_to_parent) |
| to_parent.py | ResultsToParent.facts | episode function | messages/final_to_parent.py facts; the closed credit facts are machinery |
| to_parent.py | ResultsToParent._live_facts | episode function | messages/final_to_parent.py facts and RETURN_FORM selectable fields (generic native target); the typed-family facts are empty lists, and the facts of the API and of the hosts without an A107 library module (RNA structure and comparison, expression NMF, Infernal) BLOCKED-ON-JOB-SERVICE |
| to_parent.py | ResultsToParent.validate_report | episode function | messages/final_to_parent.py validate_report (facts agreement body); the adapters' validate_received_report and validate_form over the parent-written JSON-Schema form are not carried (no parent form; the system admits RETURN_FORM) |
| to_parent.py | ResultsToParent._blast_grader_rows | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (BLAST grader rows of an API result; wanted: the API result host and the grader sheet in custody) |
| work_operations.py | ResultsWorkOperations | episode function | task.py TOOLS and CATALOG |
| work_operations.py | ResultsWorkOperations.catalog | episode function | task.py CATALOG (the native catalog); the catalogs of the typed targets, API execution, HMMER, BLAST and Infernal BLOCKED-ON-JOB-SERVICE |
| work_operations.py | ResultsWorkOperations.execute | episode function | task.py execution_results_status, execution_results_collect, execution_results_read (acquire); typed and API dispatch BLOCKED-ON-JOB-SERVICE |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | unplaced, not repaired: classifies a launch request for a yield profile key; this episode keys profiles by resource_kind from parent_input (yield_estimator.py) and never receives a launch request |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py _profile |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (the require_private_yield switch is not carried) |
| yield_estimator.py | ExecutionEpisodeYield._results_yield_controller | episode function | yield_estimator.py yield_controller (accumulation for an unbounded selector, bounded quality for a finite one); the typed and API completion estimator BLOCKED-ON-JOB-SERVICE; the exact-zero forecast and the completion switch are not carried |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator (README 7b: deleted) |
