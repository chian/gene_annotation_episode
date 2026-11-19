# a110/biochemical_feasibility_evidence/hpc_work_planning/execution_job_submission — episode intent at 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a110/biochemical_feasibility_evidence/hpc_work_planning/execution_job_submission/<file>`
(only the 38 files directly in this folder, 2,043 lines; `tests/` (2 files) not read; no grading/ or scoring/; child folders
`hpc_job_execution/` and `local_job_execution/` belong to other agents).

## Purpose (own words)

The Launch episode commissioned by the A110 HPC work-planning parent. `binding_path = 'biochemical_feasibility_evidence/hpc_work_planning/execution_job_submission'`,
`commissioning_parent = 'biochemical_feasibility_evidence/hpc_work_planning'`, `roles = ('launch',)`, `entry_roles = ()` (never an entry),
`replaces_default_instructions = True`, authority flags for received execution information and initial information, class `ExecutionEpisode`,
decision source `LaunchTask`, renderer `task_presentation.present_launch_context`. `goal.LaunchGoal.instructions`:

> Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, recorded inventory and timing
> information inform the choice. Preserve the original job, immutable inputs, constraints and pinned instructions. A resource child owns
> iterative execution in the shared loop. Receive its requested typed handoff; no infrastructure chooses an approach. Actual received usable
> handoff completes this launch endpoint with exact zero future credit.

## Task and instructions

`task_instructions.instructions`: job-episode instructions for a job source, else `library.scientific_instruction_text.INSTRUCTIONS` (via the
`runtime_prompt` alias) — replaced by the goal text above — then REASONING_COMMIT_REQUIREMENT when `reason` is permitted (it is not under an
hpc path), tool knowledge, launch library, pending_child_delivery repair, wait and native-event paragraphs when wait is permitted (not under
an hpc path), and the decision_exchange_v1 history replacement. `task_presentation.present_launch_context` is the same frame-state presenter
as the results episode but imports its helpers directly. `task.py` wires `validate_hpc_launch_report_contract` as
`_validate_hpc_launch_report_contract`, validates reports with grain 'launch', and executes `reason` selections through the binding's
`execute_reasoning` or `store.commit_reasoning`.

## What it reads from its parent's assignment

`assignment_schema('launch')`: `execution_launch_assignment_v1` {`requests` {resource_id → practical assignment schema with `resource_id`/`resource_kind`
const and `requested_job` = generic job or, for FBA resources, the configured `native_flux_balance` operation/mode/software/model formats},
`immutable_input_versions` (INPUT_VERSION_SCHEMA), `constraints`, `launch_instructions` (SELECTION_SCHEMA)}, or the compact FBA launch schema.
`prepare_assignment`: validate (`checked`); when the parent role is `hpc` or `hpc_execution`, `hpc_work_planning.to_child_execution_job_submission.authenticate_launch`
(only the exact planned launch, one reservation); a compact FBA launch returns `flux_balance_requests.preview(parent, selected)[0]`; otherwise
`_launch` (each request `_validate_request`, `_constraints`), FBA input references must match the immutable versions, `_versions` validates input
versions. `context_receipts.required_return_sources`: `execution_handoff_refs` when the parent is `biochemical_feasibility_evidence` and an
annotation task is required (under the HPC parent this condition is false). `LaunchPreparation.initial_decision_context` of the HPC parent
supplies this episode's `hpc_execution_job` (plan id, objective, manifest, acceptance, supplied input file, coordinator workspace, instructions).

## Children it may commission

| Role | Child folder | Sends | Takes back |
|---|---|---|---|
| launch_local | local_job_execution | the selected request assignment unchanged; envelope `to_child_local_job_execution.assemble_request` (goal child of parent with contract schema, message {scope, initial_report, inprocess_completion_order, report_contract_declaration checked by `validate_saved_fact_form`, job_assignment, episode_assignment with materialized launch_instructions, biochemical_feasibility_evidence, knowledge_inheritance = `receipts.bind(child, parent)`}) | `receive_report`: recorded-admission refs, else specialist `receive_child_progress_for_role` / `receive_child_progress` / provider `receive_form`; form refs + `episode_bindings.received_form_references`; `receipts.receive` (child_form / report_redelivery); tool attributions |
| launch_hpc | hpc_job_execution | same envelope (`to_child_hpc_job_execution.assemble_request`) | same receiver |

`allowed_children`: a role only when some configured resource of its kind (`local` / `pbs_ssh`→hpc) is permitted by the assignment's
`requests` and `constraints` (allowed_resource_ids, allowed_kinds, resource_id, kind). Common actions: `tool, child, redeliver_report` under an
hpc path (this episode's normal place), otherwise `tool, reason, child, wait, redeliver_report`.

## Decision state and what it shows the model

`internal_summary.LaunchDecisionState.decision_state`: the common snapshot (as the results episode). Binding `decision_context`: compact FBA
assignment → practical assignment/progress/completed; otherwise `execution_assignment`, `execution_progress` (= current facts) and, for native FBA
requests with a scientific parent task, `selected_execution_task`. Decision inputs (task_decision) as the results episode, without the
job-source resource estimate or waiting support.

## Tools offered

`work_operations.catalog` = `resource_information.launch_operation_catalog`: only `execution.capabilities` ("Read the actual caller-bound resource
configuration and already recorded inventory; no discovery or selection."), answered by `library.execution_resource_information.execution_capability_information`.
Errors return invalid outcomes. Launching itself is a child commission.

## Credit

`credit_kind` = `operational`. Closed view reused when saved (same closed-credit machinery as results, in credit.py). Live:
credit = `handoff_unit × |resource_ids with a usable received handoff − those already in the initial known records|` (+ acquired part fixed 0);
binding `execution_received_records_credit_v1`. Unbounded; not clamped.

## Continuation

`yield_controller` (requires `require_private_yield`) → `_launch_yield_controller`: eligible = permitted original requests; remaining =
(eligible − already received at start) × handoff_unit. Remaining > 0 → `BoundedYieldController(epoch, initial_credit, cutoff, remaining,
YieldParameters(**parameters))` from task profile `launch:<sorted request classes>` (class = practical_<kind>[_native_*]_handoff|outputs, or
compact_<version>) → yield_control **bounded quality** (maximum = remaining handoff credit). Nothing remaining → exact-zero estimator
(`launch_original_request_exhaustion_v1`). Settings: `task_yield_profiles` {cutoff > 0, parameters}; `results_yield_profiles` are accepted by
configuration but unused here. `completion._proof_for_action`: a completed action whose records include a usable handoff matching the
assignment → `practical_completion_v1` (`received_usable_handoff`); `verify_completion` reuses the single recorded historical verification on a
closed episode.

## Report to parent

`to_parent.facts`: FBA fact sources (empty), `execution_handoff_refs`, `execution_result_refs`, `execution_file_source_refs`,
`execution_file_capture_outcomes`, `execution_result_origin`, `execution_completed` (any received handoff returnable) + closed credit snapshot.
`validate_report`: FBA report validation, references resolve, x-source fields equal facts. The HPC parent asks for
`hpc_launch_report_form {execution_handoff_refs}`.

## Differences from similar episodes

- vs `a110/biochemical_feasibility_evidence/execution_job_submission` (the role-level Launch sibling): commissioning_parent is hpc_work_planning,
  `entry_roles = ()` instead of `('launch',)`, renderer `task_presentation.present_launch_context` (direct imports) instead of
  `presentation.present_context` (providers alias), `task.py` adds the hpc launch-report contract hook and drops the reason-commit emptiness
  check, `task_decision` drops the job-source resource estimate and waiting_support, instruction text is imported from the shared library
  instead of inlined; all other files are textually identical.
- vs `a107/partner_presence_evidence/execution_job_submission`: no `api_job_execution` child (a107 has api_job_execution and
  `received_api_reports`); A110 adds FBA request/input handling.
- vs the results episode: shares configuration, closed credit, FBA and yield-profile code, but credits distinct new usable handoffs and only
  offers `execution.capabilities` plus resource-child commissions.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| __init__.py | 1 | empty package marker | none |
| action_outcome.py | 5 | _outcome: completed with refs, or invalid with arguments_or_reference feedback | none |
| binding_record.py | 9 | as_record execution_episode_v1 with this binding id, resources, units, log selection, yield profiles | none |
| binding_roles.py | 6 | VERSION; ROLES; KINDS local/pbs_ssh->hpc; ROLE_KINDS launch_local/launch_hpc | none |
| completion.py | 76 | completion proof = completed action with a usable matching handoff; verification incl. historical verdict | import:root.a110.communication(2), import:root.a110.episode_return_records(4), import:root.a110.execution_contracts(5), import:root.a110.flux_balance_request_binding(2), import:root.a110.method_loop.identities(1), import:root.a110.numerical(1), import:root.a110.practical_execution_records(1), import:root.a110.practical_yield(1), table:runtime_actions(1), table:runtime_observations(1), yield:ESTIMATOR_VERSION(1), yield:NumericBand(1) |
| configuration.py | 74 | operands and validation; terminal behaviours, progress provider, local file sources, FBA inputs/requests/results/returns | import:root.a110.communication(2), import:root.a110.execution_contracts(2), import:root.a110.execution_progress(1), import:root.a110.flux_balance_execution_inputs(1), import:root.a110.flux_balance_request_binding(1), import:root.a110.flux_balance_returns(1), import:root.a110.library.received_execution_information.received_result_readers(1), import:root.a110.local_file_capture_results(1), import:root.a110.native_flux_balance_bindings(1), import:root.a110.native_flux_balance_results(1), import:root.a110.numerical(4), yield:YieldController(2), yield:YieldParameters(2) |
| context_receipts.py | 33 | required_return_sources execution_handoff_refs; initial_references (FBA input versions / handoff) | import:root.a110.communication(4), import:root.a110.flux_balance_request_binding(3) |
| credit.py | 150 | operational credit: closed view machinery; live handoff_unit × new usable handoffs per resource | import:root.a110.communication(1), import:root.a110.episode_receipts(1), import:root.a110.episode_return_records(4), import:root.a110.execution_contracts(14), table:runtime_episodes(2), table:runtime_forms(3), table:runtime_observations(1), table:runtime_receipt_inheritance(2), table:runtime_record_receipts(2), table:sqlite_master(2) |
| credit_records.py | 3 | _CLOSED_CREDIT version name | none |
| episode.py | 125 | ExecutionEpisode composition; binding path under hpc_work_planning; roles launch, no entry; children launch_local/launch_hpc; common actions; receivers and assemblers | import:root.a110.communication(1), import:root.a110.execution_contracts(0), import:root.a110.library.execution_resource_information(2), import:root.a110.library.received_execution_information.received_result_readers(17), import:root.a110.practical_execution_state(0) |
| from_child_hpc_job_execution.py | 32 | receive hpc_job_execution form (recorded admission / progress receivers / receipts / attributions) | _live_original_runtime._references_in(1), import:root.a110.delivery_counterpart(1), import:root.a110.episode_return_records(1), import:root.a110.runtime(module)(1), workflow.binding_context(4), workflow.episode_bindings(1), workflow.is_job_source(2), workflow.progress_provider(4), workflow.receipts(3), workflow.receive_tool_attributions(1), workflow.run_id(5), workflow.specialist(1), workflow.store(3) |
| from_child_local_job_execution.py | 32 | receive local_job_execution form (same path) | _live_original_runtime._references_in(1), import:root.a110.delivery_counterpart(1), import:root.a110.episode_return_records(1), import:root.a110.runtime(module)(1), workflow.binding_context(4), workflow.episode_bindings(1), workflow.is_job_source(2), workflow.progress_provider(4), workflow.receipts(3), workflow.receive_tool_attributions(1), workflow.run_id(5), workflow.specialist(1), workflow.store(3) |
| from_parent.py | 80 | launch assignment schema (requests, immutable inputs, constraints, launch_instructions; compact FBA); prepare_assignment with authenticate_launch; request schema; _launch | import:episode:biochemical_feasibility_evidence.hpc_work_planning.to_child_execution_job_submission(1), import:root.a110.communication(0), import:root.a110.execution_contracts(3), import:root.a110.flux_balance_contracts(1), import:root.a110.flux_balance_request_binding(4), import:root.a110.launch_instructions(1), import:root.a110.library.execution_result_contract(0), import:root.a110.local_file_capture_results(0), import:root.a110.practical_execution_records(3), import:root.a110.resource_records(1) |
| goal.py | 13 | own goal text | import:root.a110.communication(0), import:root.a110.execution_contracts(0), import:root.a110.practical_execution_records(0) |
| handoff_receipts.py | 52 | _context_target (assignment custody) and _received (result bodies and usable practical handoffs) | import:root.a110.communication(3), import:root.a110.execution_contracts(2), import:root.a110.flux_balance_request_binding(4) |
| initial_information.py | 8 | resource_information from catalog readers of this binding path | import:root.a110.library.execution_initial_information.presentation(1) |
| input_versions.py | 26 | validate input versions; FBA inputs match original versions | import:root.a110.communication(1), import:root.a110.episode_return_records(1), import:root.a110.execution_contracts(0), import:root.a110.execution_input_versions(1) |
| internal_summary.py | 80 | binding decision_context and LaunchDecisionState common snapshot | _live_original_runtime.FACT_MEANINGS(1), _live_original_runtime.FACT_SOURCES(1), _live_original_runtime.Mapping(3), _live_original_runtime._plain(2), _live_original_runtime._references_in(1), _live_original_runtime.json(2), import:root.a110.communication(4), import:root.a110.flux_balance_request_binding(5), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.binding_context(1), self.workflow.catalog(1), self.workflow.controller_binding(1), self.workflow.delivery_status(1), self.workflow.extra_report_sources(1), self.workflow.job_episode_options(1), self.workflow.journal(3), self.workflow.knowledge(1), self.workflow.local_outcome_preview(1), self.workflow.pending_work(1), self.workflow.run_id(1), self.workflow.source_credit_binding(1), self.workflow.source_credit_view(1), self.workflow.specialist(1), self.workflow.store(3), self.workflow.tools(1), self.workflow.working_state(1), table:runtime_actions(2) |
| launch_assignment_records.py | 3 | LAUNCH_VERSION name | none |
| launch_state.py | 24 | initialize per assignment kind; state() refuses (practical state belongs to resource roles) | import:root.a110.communication(3), import:root.a110.flux_balance_request_binding(2) |
| received_execution_information.py | 4 | select this path's configured/received result readers | none |
| received_result_records.py | 16 | result provider/origin names, native selector schema, native result operation catalog | import:root.a110.execution_contracts(5) |
| report_delivery.py | 23 | finish: save facts+form once, release, return form | _live_original_runtime.Record(2), _live_original_runtime._json(2), _live_original_runtime.form_with_facts(1), _live_original_runtime.json(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.binding_context(1), self.workflow.episode_bindings(1), self.workflow.facts(1), self.workflow.journal(2), self.workflow.pending_handles(1), self.workflow.release(2), self.workflow.source_credit_view(1), table:runtime_forms(2) |
| resource_information.py | 64 | launch_operation_catalog (execution.capabilities); resource_tool_contracts incl. FBA | import:root.a110.execution_contracts(3), import:root.a110.library.execution_operation_information(1), import:root.a110.native_flux_balance_tool_info(1) |
| schema_fields.py | 6 | TEXT/OFFSET/LIMIT/FILE_LIMIT schema fragments | none |
| scientific_reference_support.py | 11 | _matches_flux_balance_assignment | import:root.a110.communication(2), import:root.a110.execution_contracts(2), import:root.a110.flux_balance_request_binding(2) |
| task.py | 211 | decision loop; own: hpc launch report contract hook, grain launch, reason execution path | _live_original_runtime.AcquisitionError(2), _live_original_runtime.ActionFailure(1), _live_original_runtime.ContractError(2), _live_original_runtime.ContractInformationError(1), _live_original_runtime.Draft202012Validator(2), _live_original_runtime.EventTargetError(2), _live_original_runtime.Mapping(7), _live_original_runtime.ReportBoundaryError(1), _live_original_runtime.ReportRedelivery(2), _live_original_runtime.SourceEnd(2), _live_original_runtime.ValidationError(2), _live_original_runtime.WorkflowError(2), _live_original_runtime._decode_recorded_action_response(1), _live_original_runtime._json(5), _live_original_runtime._plain(1), _live_original_runtime._wait_target_feedback(2), _live_original_runtime.inspect(1), _live_original_runtime.json(8), _live_original_runtime.nullcontext(5), _live_original_runtime.observes_action_outcome(1), _live_original_runtime.schema_failure_diagnostic(1), _live_original_runtime.sqlite3(2), _live_original_runtime.subprocess(2), _live_original_runtime.validate_form(1), import:root.a110.episode_source_failure(1), import:root.a110.library.hpc_handoff_report_contract(1), import:root.a110.providers(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.action_schema(1), self.workflow.automatic_score_updates(1), self.workflow.binding_context(1), self.workflow.completed_unit(3), self.workflow.completions(3), self.workflow.controller_value(2), self.workflow.decision_exchanges(3), self.workflow.delivery_resolution_inputs(1), self.workflow.execute(1), self.workflow.execution_binding(7), self.workflow.inprocess_replay(4), self.workflow.journal(7), self.workflow.last_observed_credit(1), self.workflow.next_return(1), self.workflow.pending_work(1), self.workflow.perform_selected_wait(1), self.workflow.receive_native_outcome(1), self.workflow.receive_outcome(1), self.workflow.resolve_pending_deliveries(1), self.workflow.resolver(1), self.workflow.retain_shared_grading_results(1), self.workflow.run_id(3), self.workflow.selected(3), self.workflow.source_credit_view(1), self.workflow.specialist(1), self.workflow.store(8), self.workflow.validate_report(1), table:runtime_actions(8), table:runtime_episodes(1), table:runtime_model_calls(2) |
| task_decision.py | 358 | decision call/exchange; launch decision inputs; decision_completion guard | _live_original_runtime.CONTRACT_INFORMATION_OPERATIONS(1), _live_original_runtime.DECISION_CONTEXT_VERSION(2), _live_original_runtime.DECISION_EXCHANGE_PROTOCOL(5), _live_original_runtime.Draft202012Validator(1), _live_original_runtime.Mapping(4), _live_original_runtime.ValidationError(5), _live_original_runtime.WorkflowError(14), _live_original_runtime._ASSIGNMENT_TRANSPORT(1), _live_original_runtime._action_generation_schema(2), _live_original_runtime._category_yield_parameters(1), _live_original_runtime._digest(1), _live_original_runtime._json(14), _live_original_runtime._object(3), _live_original_runtime._plain(2), _live_original_runtime._recorded_action_generation_schema(1), _live_original_runtime._recorded_assignment_transport(1), _live_original_runtime._references_in(1), _live_original_runtime.apply_state_frame(1), _live_original_runtime.child_option_information(2), _live_original_runtime.composition_lookup_schema(2), _live_original_runtime.instructional_model_context(4), _live_original_runtime.is_contract_information(1), _live_original_runtime.json(3), _live_original_runtime.lookup_attempts(1), _live_original_runtime.model_snapshot(2), _live_original_runtime.requested_contract_information(2), _live_original_runtime.schema_failure_diagnostic(2), _live_original_runtime.sqlite3(1), _live_original_runtime.state_frame(1), _live_original_runtime.yield_table(1), import:root.a110.episode_work_report(2), import:root.a110.library.hpc_prompt(1), import:root.a110.providers(4), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow(passed)(6), self.workflow.available_child_roles(1), self.workflow.binding_context(1), self.workflow.contract_information_profile(1), self.workflow.contract_information_reply(1), self.workflow.controller_binding(1), self.workflow.decision_exchanges(4), self.workflow.decision_protocol(3), self.workflow.episode_bindings(1), self.workflow.execute(1), self.workflow.execution_expectations(1), self.workflow.freeze_contract_information(1), self.workflow.freeze_literature_numerical_contracts(1), self.workflow.history_preview(1), self.workflow.journal(3), self.workflow.launch_instructions(2), self.workflow.native_estimation_context(1), self.workflow.numerical_contracts(1), self.workflow.pending_work(1), self.workflow.provider(3), self.workflow.receipts(4), self.workflow.resource_context(1), self.workflow.resource_estimator(4), self.workflow.run_id(1), self.workflow.services(2), self.workflow.shared_information_context(1), self.workflow.specialist(1), self.workflow.store(2), self.workflow.uses_received_record_context(2), self.workflow.validate_contract_information(5), table:runtime_model_calls(8) |
| task_instructions.py | 28 | instruction composition with shared library text | _live_original_runtime_prompt.DECISION_EXCHANGE_PROTOCOL(1), _live_original_runtime_prompt.INSTRUCTIONS(4), _live_original_runtime_prompt.REASONING_COMMIT_REQUIREMENT(1), import:root.a110.library.scientific_instruction_text(0), import:root.a110.runtime_prompt(module)(1), workflow.binding_context(1), workflow.decision_protocol(1), workflow.is_job_source(1), workflow.job_episodes(1), workflow.knowledge(1), workflow.launch_instructions(1), workflow.native_event_information(1), workflow.permits_common_action(3), workflow.specialist(1) |
| task_presentation.py | 60 | prompt presenter (frame state, renderer choice incl. A110 scientific renderer) | import:episode:biochemical_feasibility_evidence.task_decision(1), import:root.a110.decision_context(4), import:root.a110.library.hpc_prompt(3), import:root.a110.library.monitor_prompt(3), import:root.a110.library.scientific_decision_presentation(7), import:root.a110.receiver_prompt(1) |
| task_state.py | 108 | episode source state, checkpoint/restore, record_effect | _live_original_runtime.ActionLeaf(1), _live_original_runtime.EFFECT_VERSION(1), _live_original_runtime.Episode(1), _live_original_runtime.Record(1), _live_original_runtime._json(2), _live_original_runtime._object(1), _live_original_runtime._plain(1), _live_original_runtime.interpretation_schema(1), _live_original_runtime.json(4), import:root.a110.episode_source_failure(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.archive(1), self.workflow.completions(4), self.workflow.controller_value(1), self.workflow.execution_binding(4), self.workflow.inprocess_replay(7), self.workflow.journal(5), self.workflow.progress_provider(2), self.workflow.recover_commissions(1), self.workflow.run_id(1), self.workflow.source_credit_view(1), self.workflow.store(2), table:runtime_actions(5), workflow.context(1), workflow.grains(1) |
| task_suspension.py | 9 | suspension_changed -> execution backend suspension | self.workflow.execution_backend(1), self.workflow.execution_handle(2) |
| terminal_execution.py | 131 | TerminalExecutionBehavior (instruction-led terminal execution per resource kind) | import:root.a110.acquisition(1), import:root.a110.communication(8), import:root.a110.domain(1), import:root.a110.library.execution_operation_information(1), import:root.a110.practical_execution_operations(0), import:root.a110.practical_execution_records(3), import:root.a110.practical_execution_state(1), import:root.a110.practical_receipt_information(3), import:root.a110.practical_yield(1), import:root.a110.terminal_execution(5), import:root.a110.terminal_scientific_evidence(2), yield:PracticalYieldEstimator(1) |
| to_child_hpc_job_execution.py | 29 | assemble hpc_job_execution request envelope | _live_original_runtime.ContractInformationError(1), _live_original_runtime.Episode(2), _live_original_runtime.EpisodeGoal(2), _live_original_runtime.EpisodeRequest(1), _live_original_runtime.Record(1), _live_original_runtime._plain(3), _live_original_runtime.validate_saved_fact_form(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), workflow.context(2), workflow.grains(2), workflow.inprocess_completion_order(2), workflow.launch_instructions(1), workflow.receipts(2) |
| to_child_local_job_execution.py | 29 | assemble local_job_execution request envelope | _live_original_runtime.ContractInformationError(1), _live_original_runtime.Episode(2), _live_original_runtime.EpisodeGoal(2), _live_original_runtime.EpisodeRequest(1), _live_original_runtime.Record(1), _live_original_runtime._plain(3), _live_original_runtime.validate_saved_fact_form(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), workflow.context(2), workflow.grains(2), workflow.inprocess_completion_order(2), workflow.launch_instructions(1), workflow.receipts(2) |
| to_parent.py | 36 | facts (handoff/result/file refs, origin, completed) + closed credit; validate_report | import:root.a110.communication(2), import:root.a110.flux_balance_return_views(1) |
| work_operations.py | 27 | catalog execution.capabilities and execute; invalid outcome on error | import:root.a110.communication(0), import:root.a110.execution_contracts(1), import:root.a110.library.execution_resource_information(1), import:root.a110.native_file_capture(1) |
| yield_estimator.py | 61 | request yield class, task profile, launch bounded yield / exact zero, practical_estimator | import:root.a110.communication(2), import:root.a110.numerical(6), import:root.a110.practical_yield(1), yield:BoundedYieldController(1), yield:NumericBand(1), yield:PracticalYieldEstimator(1), yield:YieldController(1), yield:YieldEstimate(1), yield:YieldParameters(2) |
