# a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/`
(40 Python files directly in the folder; no `grading/` or `scoring/` subfolder; `tests/` and the child folders
`api_job_execution`, `local_job_execution`, `hpc_job_execution` not read). Nothing from the old shared root was read.
Where behaviour lives in old shared modules (the received result readers, `api_service_execution`,
`execution_progress`, `a107_execution_bindings`, `a107_blast_execution`, `practical_yield`, `numerical`), this page says
only what this episode's own files ask of them.

Old binding: class `ExecutionEpisode` (launch), `binding_path = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'`,
`commissioning_parent = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution'`, role `launch`, no entry
roles, version `execution_episode_v1`, `replaces_default_instructions = True`. Decision source `LaunchTask`; prompt
renderer `present_launch_context`. Mixes in `A107BlastExecution` (old shared).

## What this episode is for

It chooses which permitted concrete execution request to commission on an explicit resource and receives that
resource child's typed handoff; the handoff is its endpoint. In its own words (`goal.py`):

> Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, recorded
> inventory and timing information inform the choice. Preserve the original job, immutable inputs, constraints and
> pinned instructions. A resource child owns iterative execution in the shared loop. Receive its requested typed
> handoff; no infrastructure chooses an approach. Actual received usable handoff completes this launch endpoint with
> exact zero future credit.

Under the HPC allocation parent, the parent also supplies `hpc_execution_job` (frozen plan, manifest, acceptance,
input file, workspace and instructions) to this episode's decision context through its `initial_decision_context`.

## Task and instructions

- One unit is one model-selected action. Under any `hpc` path element: `tool`, `child`, `redeliver_report`.
  Otherwise also `reason` and `wait` (`episode.py`). The task loop executes `reason` commits through the specialist or
  the Store but, unlike the results copy, does not run the empty-commit admission check.
- Instructions (`task_instructions.py`, identical to the results copy): binding goal replaces the defaults; then
  reasoning requirement when `reason` is permitted, tool knowledge, launch library, repair, wait and native-event
  guidance, and the exchange-history substitution.

## What it reads from its parent's assignment

`from_parent.py`: `execution_launch_assignment_v1` = `requests` (one or more, keyed by configured resource id; each a
concrete request schema per resource kind — the API execution's schema for API resources, the practical assignment
schema with `resource_kind` and `requested_job` alternatives for local/HPC, including NMF, RNA structure, Infernal,
Infernal preparation and preparation jobs), `immutable_input_versions`, `constraints` (`allowed_resource_ids`,
`allowed_kinds`, `resource_id`, `kind`), and `launch_instructions` (library selection). Preparation: when the parent
role is `hpc`/`hpc_execution`, `authenticate_launch` from the HPC parent's `to_child_execution_job_submission.py`
(only the exact planned launch, once); BLAST-graded requests must match an `ncbi_blast` resource; each request is
validated (API requests against the API execution in scope); masking/utility inputs, immutable versions and native
BLAST database, standard BLAST and RNA structure job inputs are validated. Required return source
`execution_handoff_refs` under the axis head when an annotation task is required (`context_receipts.py`).

## Children

`launch_api`, `launch_local`, `launch_hpc` (its child episodes `api_job_execution`, `local_job_execution`,
`hpc_job_execution`). A role is offered only if some configured resource of that kind is permitted by the assignment
(in `requests` and inside the constraints).
- Sends: the assignment unchanged (`prepare_child_request` returns it for all three) through each role's own copy of
  the old request assembler (`to_child_*_job_execution.py`: goal, scope, initial report, report contract declaration,
  job and episode assignment, receipts inheritance).
- Takes back: through each role's own copy of the old report intake (`from_child_*_job_execution.py`): recorded
  admission references, progress forms, received form references, native timing receipts, tool attributions. The
  three copies are identical apart from their docstrings.

## Decision state and what the model sees

Old generic decision state (own class copy `LaunchDecisionState` in `internal_summary.py`) plus `decision_context`:
`execution_assignment`, `execution_progress` (live facts), and `selected_execution_task` (scientific question and
selected tool info from the scientific parent; each request's resource, endpoint, constraints and job, with HMMER and
NMF scientific views). Decision inputs (`task_decision.py`) add resource context, shared information context, launch
library and selected launch instructions, child options, completed action reports, requested action history in HPC
contexts, pending work and execution expectations for role `launch`; unlike the results copy, no `waiting_support`.

## Tools

One tool (`resource_information.py`, `work_operations.py`): `execution.capabilities` — "Read the actual caller-bound
resource configuration and already recorded inventory; no discovery or selection." Returns
`execution_capability_information`. `resource_tool_contracts` declares the bound launch, result and homology
operation contracts per resource (for presentation to callers), as in the results copy.

## Credit

Credit kind `operational` (`credit.py`). A frozen closed credit view is returned unchanged when present. Otherwise
`credit = handoff_unit × (number of distinct resource ids with a usable received handoff, minus those already in the
initial records)`; the acquired-record term is zero for launch. Binding version `execution_received_records_credit_v1`.
Not bounded or rescaled.

## Continuation

Only with `require_private_yield` (`yield_estimator.py`). `remaining = handoff_unit × |eligible requests − resources
with a usable handoff already in the initial records|`. If `remaining > 0`: profile
`task_yield_profiles['launch:' + '+'.join(sorted request classes)]` (classes such as `api_<service>[_algorithm][_database]_handoff`,
`practical_<kind>_<native jobs>_<handoff|outputs>`, `compact_<version>`) with a bounded controller whose maximum is
`remaining` (nearest: **bounded quality**, settings `cutoff`, `parameters`, maximum = remaining handoff credit). If
nothing remains: exact zero forecast, cutoff 0, and any nonzero credit raises. Completion proof (`completion.py`): a
completed action whose record refs contain a usable handoff consistent with the context (`received_usable_handoff`).

## Report to parent

`to_parent.py` facts: empty native sources for configured adapters, `execution_handoff_refs`,
`bvbrc_appservice_support_refs` (when bound), `execution_blast_hsps: []`, `execution_result_refs`,
`execution_file_source_refs`, `execution_file_capture_outcomes`, `execution_result_origin`, `execution_completed`
(any received handoff returnable), plus the frozen closed-credit fact at closing. The HPC parent reads it through
`hpc_launch_report_form` (`execution_handoff_refs`). Validation as in the results copy.

## Differences from similar episodes

- With `execution_result_acquisition` it shares identical copies of `action_outcome`, `binding_roles`,
  `configuration` (apart from its own terminal behaviour import), `credit_records`, `schema_fields`,
  `task_instructions`, `task_state`, `task_suspension`, `terminal_execution`, `report_delivery`, the presentation
  function and the closed-credit methods. It differs in role (`launch` vs `results`), children (three resource roles
  vs none), tools (`execution.capabilities` vs result reads), credit (handoffs vs byte coverage), completion (usable
  handoff vs complete windows) and yield (request-slot bound vs selector-coverage bound / completion).
- `launch_state.state` and the results `native_target_state.state` both raise `practical_resource_role_required`.
- The permitted actions include `reason` and `wait` outside an `hpc` path, which the results episode does not offer.
- Its `prepare_assignment` depends on the HPC parent's `authenticate_launch` (cross-episode import).

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 1 | Empty package marker. | none |
| `action_outcome.py` | 5 | Shape of one tool outcome (same as the results copy). | none |
| `binding_record.py` | 9 | Binding identity record (same fields as the results copy, own binding id). | none |
| `binding_roles.py` | 6 | Role vocabulary and resource-kind mapping (same as the results copy). | none |
| `completion.py` | 75 | Launch completion proof: a completed action whose record refs include a usable handoff consistent with this context (`received_usable_handoff`, endpoint `usable_handoff`); verification reuses a recorded endpoint verdict for a closed episode. | `BindingContext`: assignment×2, episode_id×7, run_id×3, scope; `imports root.a107`: communication, episode_return_records, execution_contracts×2, method_loop.identities, numerical, practical_execution_records, practical_yield; `names`: ESTIMATOR_VERSION×2, NumericBand×2, UnitRef×2; `tables`: runtime_actions, runtime_observations |
| `configuration.py` | 120 | Constructor operands and validation (identical to the results copy except the terminal behaviour import). | `imports root.a107`: a107_execution_bindings×4, api_service_execution, communication, execution_contracts, execution_progress, expression_nmf_returns, local_file_capture_results, native_expression_nmf_contracts, native_expression_nmf_results, native_infernal_preparation_results, native_infernal_preparation_returns, native_infernal_preparation_tool_info, native_infernal_results, native_infernal_returns, native_infernal_tool_info, native_rna_structure_contracts, native_rna_structure_results, native_rna_structure_returns, numerical, rna_structure_comparison_results, rna_structure_comparison_returns; `names`: YieldController×3, YieldParameters×3 |
| `context_receipts.py` | 55 | Requires return source `execution_handoff_refs` under the axis head when an annotation task is required; initial references of launch requests (RNA structure, masking, utility, expression NMF inputs). | `BindingContext`: assignment×2, path, role×3; `imports root.a107`: communication, native_blast_database_acquisition, native_blast_database_result_publication, native_blast_standard_database_acquisition, native_blast_standard_database_result_publication, native_rna_structure_acquisition, native_rna_structure_result_publication×2, rna_structure_comparison_operands; `services`: annotation_task_required |
| `credit.py` | 150 | Operational credit: `handoff_unit` × number of new resource ids with a usable received handoff not already in the initial records (no acquired-record term); closed-credit freezing as in the results copy. | `BindingContext`: as_record×2, episode_id×8, role; `imports root.a107`: communication, episode_receipts, episode_return_records×3, execution_contracts×2; `names`: EpisodeReceipts×2, EpisodeReturnRecords×2; `tables`: runtime_episodes×2, runtime_forms×3, runtime_observations, runtime_receipt_inheritance×2, runtime_record_receipts×2 |
| `credit_records.py` | 3 | Name of the frozen closed-credit fact. | none |
| `episode.py` | 161 | Composes the binding: path, parent `.../hpc_allocation_execution`, role `launch`, no entry roles, `replaces_default_instructions`, decision source `LaunchTask`, renderer `present_launch_context`. Children `launch_api`, `launch_local`, `launch_hpc`, offered only where a permitted request names a resource of that kind. Common actions tool, child, redeliver_report under an `hpc` path; else also reason and wait. | `BindingContext`: assignment, path; `imports root.a107`: a107_blast_execution, communication×2, execution_contracts×2, library.execution_resource_information×2, library.received_execution_information.received_result_readers×20, library.received_execution_targets×8, native_blast_database_acquisition, native_blast_standard_database_acquisition, native_rna_structure_acquisition, practical_execution_state×2 |
| `from_child_api_job_execution.py` | 44 | Generic old child-report intake for the API job child. | `imports root.a107`: delivery_counterpart, episode_return_records, runtime; `names`: EpisodeReturnRecords×2; `runtime`: _json, json, _references_in, WorkflowError; `self.workflow`: binding_context×4, episode_bindings, is_job_source×2, job_episodes×2, native_timing_information, progress_provider×4, receipts×3, receive_tool_attributions, run_id×6, specialist, store×7; `tables`: runtime_report_attempts×2 |
| `from_child_hpc_job_execution.py` | 44 | Generic old child-report intake for the HPC job child. | `imports root.a107`: delivery_counterpart, episode_return_records, runtime; `names`: EpisodeReturnRecords×2; `runtime`: _json, json, _references_in, WorkflowError; `self.workflow`: binding_context×4, episode_bindings, is_job_source×2, job_episodes×2, native_timing_information, progress_provider×4, receipts×3, receive_tool_attributions, run_id×6, specialist, store×7; `tables`: runtime_report_attempts×2 |
| `from_child_local_job_execution.py` | 44 | Generic old child-report intake for the local job child. | `imports root.a107`: delivery_counterpart, episode_return_records, runtime; `names`: EpisodeReturnRecords×2; `runtime`: _json, json, _references_in, WorkflowError; `self.workflow`: binding_context×4, episode_bindings, is_job_source×2, job_episodes×2, native_timing_information, progress_provider×4, receipts×3, receive_tool_attributions, run_id×6, specialist, store×7; `tables`: runtime_report_attempts×2 |
| `from_parent.py` | 114 | Assignment schema `execution_launch_assignment_v1`: per-resource request schemas, immutable input versions, constraints, launch instructions; preparation authenticates against the HPC plan when the parent is `hpc`/`hpc_execution`, validates requests, inputs and versions; resource constraints. | `BindingContext`: role×2; `imports root.a107`: a107_blast_execution×2, a107_execution_bindings×4, communication, execution_contracts×2, launch_instructions, library.execution_result_contract, local_file_capture_results×2, native_blast_database_acquisition, native_blast_database_result_publication, native_blast_standard_database_acquisition, native_blast_standard_database_result_publication, native_expression_nmf_tool_info, native_infernal_preparation_tool_info, native_infernal_tool_info, native_rna_structure_acquisition, native_rna_structure_result_publication, native_rna_structure_tool_info, practical_execution_records×2, resource_records |
| `goal.py` | 13 | The episode's goal text (see "What this episode is for"). | `imports root.a107`: communication, execution_contracts×2, practical_execution_records |
| `handoff_receipts.py` | 60 | Target/context checks and classification of known records into handoffs and results. | `BindingContext`: assignment×3, role×4, scope×5; `imports root.a107`: a107_blast_execution, communication, execution_contracts |
| `initial_information.py` | 9 | Resource and received API information from this binding path's readers. | `catalog`: readers; `imports root.a107`: library.execution_initial_information.presentation |
| `input_versions.py` | 24 | Masking/utility/NMF input and immutable version validation (same as results copy). | `imports root.a107`: communication, execution_contracts, execution_input_versions, expression_nmf_operands, library.received_execution_information.received_result_readers |
| `internal_summary.py` | 89 | Decision context: the launch assignment, live facts as `execution_progress`, `selected_execution_task` from the scientific parent; also this episode's own copy of the old decision-state builder. | `BindingContext`: assignment×2; `imports root.a107`: communication, expression_nmf_presentation, native_profile_presentation, runtime×2; `journal`: elapsed_view, row; `runtime`: FACT_MEANINGS, FACT_SOURCES, json×2, Mapping×3, _plain×2, _references_in; `self.workflow`: binding_context, catalog, controller_binding, delivery_status, extra_report_sources, job_episode_options, journal×3, knowledge, local_outcome_preview, pending_work, run_id, source_credit_binding, source_credit_view, specialist, store×3, tools, working_state; `services`: scientific_parent_task; `tables`: runtime_actions×2; `view`: child_reports×2, controller_state, model_inputs |
| `launch_assignment_records.py` | 3 | Launch assignment version name. | none |
| `launch_state.py` | 21 | Initialization: validate the launch, BLAST-graded requirements, masking/utility inputs and immutable versions. | `BindingContext`: assignment, scope×3; `imports root.a107`: a107_blast_execution, communication |
| `received_api_reports.py` | 4 | Selects this binding path's declared API reader authority. | `catalog`: configured, received |
| `received_execution_information.py` | 4 | Selects this binding path's declared result readers. | `catalog`: configured, received |
| `received_result_records.py` | 16 | Result record names, native origin, selector schema and native result operation catalog. | `imports root.a107`: execution_contracts |
| `report_delivery.py` | 23 | Generic old finish (identical to the other copies). | `imports root.a107`: runtime×2; `journal`: row, save; `runtime`: form_with_facts, _json×2, json, Record×2; `self.workflow`: binding_context, episode_bindings, facts, journal×2, pending_handles, release×2, source_credit_view; `tables`: runtime_forms×2 |
| `resource_information.py` | 72 | Launch operation catalog (`execution.capabilities`) and declared resource tool contracts. | `imports root.a107`: a107_execution_bindings×3, execution_contracts×2, library.execution_operation_information, native_expression_nmf_tool_info, native_infernal_preparation_tool_info, native_infernal_tool_info, native_rna_structure_tool_info |
| `schema_fields.py` | 6 | Shared schema fragments. | none |
| `task.py` | 219 | Generic old task loop; grain `launch`; reasoning execution present; binds `validate_hpc_launch_report_contract`. | `imports root.a107`: episode_source_failure, library.hpc_handoff_report_contract, providers, read_mapping, runtime×2; `journal`: measure, row×7, save×3; `names`: ModelCallError×2; `runtime`: AcquisitionError×2, ActionFailure, ContractError, ContractInformationError, _decode_recorded_action_response, Draft202012Validator×2, EventTargetError×2, inspect, _json×5, json×8, Mapping×2, nullcontext×5, observes_action_outcome, ReportBoundaryError, ReportRedelivery×2, schema_failure_diagnostic, SourceEnd×2, sqlite3×2, subprocess×2, validate_form, ValidationError×3, _wait_target_feedback×2, WorkflowError×2; `self.workflow`: action_schema, automatic_score_updates, binding_context, completed_unit×3, completions×3, controller_value×2, decision_exchanges×3, delivery_resolution_inputs, execute, execution_binding×7, inprocess_replay×4, journal×7, last_observed_credit, next_return, pending_work, perform_selected_wait, receive_native_outcome, receive_outcome, resolve_pending_deliveries, resolver, retain_shared_grading_results, run_id×3, selected×3, source_credit_view, specialist, store×8, validate_report; `tables`: runtime_actions×8, runtime_episodes, runtime_model_calls×2; `view`: units_consumed×4 |
| `task_decision.py` | 358 | Generic old model-call machinery with launch decision inputs inlined (role `launch` for execution expectations; no waiting support entry) and the private provider completion. | `exchanges`: measure, prepare, resolve_lookup, respond, rows; `imports root.a107`: episode_work_report×2, library.hpc_prompt, providers, runtime×2; `journal`: measure×2, row×2, save×4; `provider`: complete; `runtime`: _action_generation_schema×2, apply_state_frame, _ASSIGNMENT_TRANSPORT, _category_yield_parameters, child_option_information×2, composition_lookup_schema×2, CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION×2, DECISION_EXCHANGE_PROTOCOL×5, _digest, Draft202012Validator, infernal_receiver_context×2, instructional_model_context×4, is_contract_information, _json×14, json×3, lookup_attempts, Mapping×4, model_snapshot×2, _object×3, _plain×2, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, requested_contract_information×2, schema_failure_diagnostic×2, sqlite3, state_frame, ValidationError×5, WorkflowError×14, yield_table; `self.workflow`: available_child_roles, binding_context, contract_information_profile, contract_information_reply, controller_binding, decision_exchanges×4, decision_protocol×3, episode_bindings, execute, execution_expectations, freeze_contract_information, freeze_literature_numerical_contracts, history_preview, journal×3, launch_instructions×2, native_estimation_context, numerical_contracts, pending_work, provider×3, receipts×4, resource_context, resource_estimator×4, run_id, services×2, shared_information_context, specialist, store×2, uses_received_record_context×2, validate_contract_information×5; `tables`: runtime_model_calls×8 |
| `task_instructions.py` | 28 | Instruction composition (identical to the results copy). | `imports root.a107`: library.scientific_instruction_text×3, runtime_prompt; `runtime_prompt`: DECISION_EXCHANGE_PROTOCOL, INSTRUCTIONS×4, REASONING_COMMIT_REQUIREMENT; `self.workflow`: binding_context, decision_protocol, is_job_source, job_episodes, knowledge, launch_instructions, native_event_information, permits_common_action×3, specialist |
| `task_presentation.py` | 73 | Prompt presentation (identical to the results copy apart from name). | `imports root.a107`: decision_context, execution_prompt, infernal_result_presentation, library.hpc_prompt, library.monitor_prompt, library.scientific_decision_presentation×2, partner_presence_evidence.task_decision, rna_structure_comparison_presentation, rna_structure_comparison_prompt, rna_structure_comparison_receiver_prompt, rna_structure_presentation, rna_structure_prompt; `provider`: scientific_prompt_states×4 |
| `task_state.py` | 108 | Generic old state. | `imports root.a107`: episode_source_failure, runtime×2; `journal`: row×3, save×2; `runtime`: ActionLeaf, EFFECT_VERSION, Episode, interpretation_schema, _json×2, json×4, _object, _plain, Record; `self.workflow`: archive, completions×4, context, controller_value, execution_binding×4, grains, inprocess_replay×7, journal×5, progress_provider×2, recover_commissions, run_id, source_credit_view, store×2; `tables`: runtime_actions×5 |
| `task_suspension.py` | 9 | Generic old suspension hook. | `self.workflow`: execution_backend, execution_handle×2 |
| `terminal_execution.py` | 131 | Terminal execution behaviour (identical to the results copy). | `BindingContext`: assignment×6, episode_id×4, role, run_id×5; `imports root.a107`: acquisition, communication, domain, library.execution_operation_information, practical_execution_operations, practical_execution_records, practical_execution_state, practical_receipt_information×3, practical_yield, terminal_execution, terminal_scientific_evidence×2; `names`: PracticalYieldEstimator×2 |
| `to_child_api_job_execution.py` | 29 | Generic old child request assembler for the API job child. | `imports root.a107`: runtime×2; `runtime`: ContractInformationError, Episode×2, EpisodeGoal×2, EpisodeRequest, _plain×3, Record, validate_saved_fact_form; `self.workflow`: context×2, grains×2, inprocess_completion_order×2, launch_instructions, receipts×2 |
| `to_child_hpc_job_execution.py` | 29 | Generic old child request assembler for the HPC job child. | `imports root.a107`: runtime×2; `runtime`: ContractInformationError, Episode×2, EpisodeGoal×2, EpisodeRequest, _plain×3, Record, validate_saved_fact_form; `self.workflow`: context×2, grains×2, inprocess_completion_order×2, launch_instructions, receipts×2 |
| `to_child_local_job_execution.py` | 29 | Generic old child request assembler for the local job child. | `imports root.a107`: runtime×2; `runtime`: ContractInformationError, Episode×2, EpisodeGoal×2, EpisodeRequest, _plain×3, Record, validate_saved_fact_form; `self.workflow`: context×2, grains×2, inprocess_completion_order×2, launch_instructions, receipts×2 |
| `to_parent.py` | 81 | Facts: empty native sources, `execution_handoff_refs`, result refs, file sources, origin and `execution_completed` (any received handoff returnable); report validation. | `BindingContext`: scope; `imports root.a107`: a107_blast_execution, blast_pairwise_result_views, blast_utility_result_views, communication×2, expression_nmf_return_views, hmmer_native_result_views, hmmer_preparation_result_views, infernal_native_result_views, infernal_preparation_result_views, native_blast_database_results, native_blast_standard_database_results, rna_structure_comparison_views, rna_structure_result_views, sequence_masking_result_views, uniprot_return_contracts |
| `work_operations.py` | 35 | One tool `execution.capabilities` (see "Tools"). | `imports root.a107`: communication, execution_contracts, library.execution_resource_information, native_blast_acquisition, native_blast_database_acquisition, native_blast_standard_database_acquisition, native_file_capture, native_hmmer_acquisition, native_hmmer_preparation_acquisition, native_infernal_acquisition, native_infernal_preparation_acquisition, native_rna_structure_acquisition |
| `yield_estimator.py` | 67 | Private continuation for launch (see "Continuation"). | `BindingContext`: assignment, scope; `imports root.a107`: communication, numerical, practical_yield; `names`: BoundedYieldController×2, NumericBand×2, PracticalYieldEstimator×2, YieldController×2, YieldEstimate×2, YieldParameters×3 |
