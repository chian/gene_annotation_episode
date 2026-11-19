# Episode intent: A107 `execution_progress_assessment`

Episode path: `root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment`
Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment/<file>` (27 files, no `grading/` or `scoring/` subfolder; child episode folders not read).
Binding class: `MonitorEpisode` (episode.py), built from 11 mixins. Role: `monitor`. `entry_roles = ('monitor',)`, so it can be a run entry. Commissioning parent: `hpc_allocation_execution`. Binding version `monitor_episode_binding_v1`.

## What this episode is for (its goal, in its own words)

episode.py docstring: "Connect the predefined A107 progress-monitoring task, reports, credit and continuation."

goal.py `MonitorGoal.instructions`:

> Investigate which further exposed progress information is useful for the assigned target. Use actual status, measured quantities, committed references and source-bound logs. Liveness establishes process presence only; elapsed time alone establishes neither productive work nor a stall. Unknown information stays unknown. Earlier outcomes and your admitted child forms inform later decisions. You may explicitly commission an ordinary monitor for one exposed direct dependency; no descendant traversal, fanout, cadence or depth is prescribed. Return the original parent's typed form at your closure even while the target remains active. Do not report private reasoning, intentions or unrestricted findings. Recorded facts use saved delivered observations; closure does not poll or compose another report with a model. {credit_instruction} Repeated observation identities and read timestamps alone earn no new information.

`credit_instruction` depends on the yield binding:
- with a private yield binding: "The monitor's information-credit projector and bound yield rule govern continuation."
- without: "The caller's monitoring projector and configured controller own credit and continuation."

`planning_context` (shown as `monitor_goal`) holds:
- `objective` = the request goal, plus `target_handle` and `requested_fields`;
- `unresolved_question`: "Which exposed progress information would improve the original requested report?";
- `progress_definition`: "Actual received information under the caller-bound monitoring projector; repeated identities and timestamps alone earn no credit.";
- `yield_settings`.

## Task and instructions

- task.py `ProgressMonitoringTask` is composed of `MonitorDecisionState`, `MonitorTaskState`, `MonitorTaskDecision`, `MonitorWaiting` and `MonitorReportDelivery`. It is the same old ordinary loop as the job episodes, except:
  - the decision context comes from `self.decision_state(view)`;
  - there is no reason-commit validation, job-child OSError feedback, ContractError repair feedback or reads.map feedback;
  - wait is performed inline;
  - there is no `automatic_score_updates` and no `retain_shared_grading_results`;
  - `validate_report` is called with `grain='monitor'`.
- task_instructions.py is the monitor's own instruction composer. The text is the goal, then ACTION_BOUNDARY, CREDIT_COMPONENT_GUIDANCE, RESOURCE_ESTIMATE_GUIDANCE, REPORT_GUIDANCE, the history guidance (EXCHANGE_HISTORY_GUIDANCE under `decision_exchange_v1`, otherwise HISTORY_GUIDANCE) and HOST_EXECUTION_GUIDANCE. Added after that: tool_knowledge and launch_instruction_library text when present, REPAIR_GUIDANCE, WAIT_GUIDANCE when wait is permitted, and NATIVE_EVENT_GUIDANCE when there is native event information. The blocks say:
  - ACTION_BOUNDARY: "Do not emit a stop action or invent a turn budget, approval review, quality gate, experiment, term or observation."
  - RESOURCE_ESTIMATE_GUIDANCE: "A timing experiment earns monitoring credit for timing information learned and updates execution expectations. Missing history means duration is unknown. Job elapsed time and the duration of an own monitoring action are distinct measurements."
  - CREDIT_COMPONENT_GUIDANCE: current_evidence_vector describes the progress proxy, not biological truth.
  - REPORT_GUIDANCE: a child returns only the parent's typed form, report_update is filled before the next action, and redeliver_report is a representation repair only.

  This composer is fully written out in the episode, unlike the job episodes, which patch `runtime_prompt.INSTRUCTIONS`.
- task_decision.py `MonitorTaskDecision` follows the same exchange protocol as the job copies. `complete_decision` calls `provider.complete_with_presentation(..., prompt_renderer=binding.decision_prompt_renderer)` when that exists, and `provider.complete` otherwise. It is simpler than the job copies' `decision_completion` identity checks.
- `decision_prompt_renderer` = library `render_monitor_prompt`.

## What it reads from its parent's assignment

contracts.py `_ASSIGNMENT` (`monitor_assignment_v1`):
- `target_handle` (text);
- `requested_fields`: a subset of execution_status, measurements, log_windows, committed_record_refs, dependencies and result_available;
- `known_progress_refs`;
- `permitted_committed_record_types`: a subset of RECORD_SCHEMAS.

from_parent.py `_assignment`:
- validates against that schema;
- requires `services.reference_in_scope(target_handle, scope, 'execution_handle')`, otherwise `progress_target_unavailable_or_outside_scope`;
- requires every known progress ref to read back with the same target, otherwise `monitor_known_progress_target_mismatch`.

`prepare_assignment` requires an operation_key. When the parent is itself a monitor, it applies `prepare_dependency_request`.

## Children it may commission

The child is recursive: the monitor role, i.e. this same binding, run on an exposed direct dependency.
- `child_roles` = `('monitor',)`. `allowed_children` = `('monitor',)` only when `services.dependencies(target_handle, scope)` is non-empty.
- **Sends** (to_child_execution_progress_assessment.py `prepare_dependency_request`): a monitor assignment whose `target_handle` must be one of the parent's exposed direct dependency handles (`monitor_child_target_not_exposed_direct_dependency`). Its `permitted_committed_record_types` must be a subset of the parent's (`monitor_child_expands_permitted_record_types`).
- **Takes back** (from_child_execution_progress_assessment.py `receive_progress`): the child's typed form, validated against the schema.
  - Every `episode_progress` reference is read through `provider.read_progress` and collected.
  - The references are admitted with `provider._receive_progress(episode_id, refs, signature, operation_key)`, where the signature is the content_digest of form, schema and scope.
  - It requires a non-empty episode_id and operation_key (`progress_delivery_identity_required`).
- When the parent is the partner_presence_evidence head and `services.annotation_task_required()`, `required_return_sources` = `('monitoring_progress_refs',)`.

## Decision state and what it shows the model

- decision_state.py `MonitorDecisionState.decision_state` is the same model input set as the job `native_decision_snapshot`, plus `investigation_progress` (retained_finding_count, inactive_dependencies, detail_pages) when `receipt_projection`.
- decision_inputs.py `MonitorDecisionInputs.decision_inputs` adds:
  - resource_context, launch_instruction_library, selected_launch_instructions and child_options;
  - the binding's initial decision context and completed_action_reports;
  - pending_work and `execution_expectations` (captured for `'monitor'`);
  - resource_tool_estimates, native_execution_expectations, waiting_support and contract_information_profile.

  Unlike the job copies there are no shared_information_context, job-source estimates or hpc requested_action_history.
- internal_summary.py `MonitorSummary.decision_context` supplies:
  - `monitor_assignment`;
  - `monitor_target_description` (`services.describe_progress_target`);
  - `monitor_direct_dependencies`;
  - `monitor_received_progress_refs`;
  - `monitor_information_meaning`: "Exposed direct relationships and already delivered observations. Empty measurements/log windows do not assert absence or a stall.";
  - `monitor_goal` (planning_context).
- received_progress.py `_received` returns the known_progress_refs, the own progress refs (paged `services.own_outcomes` by `outcome_page_size`) and `services.received_progress_refs(episode_id)`. When `services.progress_selection` exists, it is used instead.

## Tools it offers

`permitted_common_actions` = `('tool', 'child', 'wait', 'redeliver_report')`.

progress_operations.py catalog:
- `progress.observe(requested_fields[, native_operation])`: observes selected exposed fields of the assigned target and never traverses dependents. `native_operation` is added only when the target descriptor supplies a `selected_observation_schema` whose only property is `native_operation`. The requested fields must be a subset of the assignment's (`monitor_observation_expands_requested_fields`). The call is `services.observe_progress(..., permitted_committed_record_types, operation_key, **native_observation_options(...))`.
- `progress.read(progress_ref)`: reads an already delivered observation.
- `progress.log(progress_ref, log_index)`: reads one exact retained log window through `source.read`, with source/artifact representation matching (`progress_log_source_artifact_mismatch`). Empty windows return empty text.

Results carry `progress_refs`, with committed refs filtered to the permitted record types. A ContractError becomes `status: invalid`.

## Credit

credit.py `MonitorEpisodeCredit`:
- `credit_kind` is `'monitoring'`.
- `credit_view` = `services.bound_role_credit(context, receiver_selection)`: the caller-bound projector.
- `information_credit(progress_reader, information_unit)` returns the library `ProgressInformationCredit`, which counts newly informative received snapshots times `information_unit`.

Credit is never bounded.

## Continuation

yield_estimator.py:
- The settings are `yield_settings = {kind: 'information_accumulation', cutoff>=0, uncertainty_alpha in (0,1)}` and `information_unit > 0`. Configuring them sets `private_yield_binding`.
- `yield_controller` = `YieldController(epoch, initial_credit, cutoff, YieldParameters(uncertainty_alpha=alpha), estimate_with_context=_monitor_information_yield)`.
- `_monitor_information_yield` raises on any negative score (`monitor_information_credit_cannot_decrease`) and uses `estimate_nonnegative_yield`. Its binding is `monitor_information_accumulation_v1`:
  - credit = newly informative received snapshot count times information_unit;
  - forecast = next monitor action's information credit;
  - decision = predicted upper gain at or below the cutoff.
- New estimator: **accumulation**. Settings: cutoff and uncertainty_alpha, with the information_unit as the credit unit.

## What it reports to its parent

to_parent.py `MonitorReport.fact_sources` lists these sources:
- `monitoring_progress_refs` (episode_progress refs);
- `monitoring_target_handle`;
- `monitoring_execution_state`: pending, executing, returned, admitted or null;
- `monitoring_result_available`;
- `monitoring_observed_at_unix_seconds` (from the UTC observed_at; the read time is not refreshed);
- `monitoring_committed_record_refs` (permitted types only);
- `monitoring_dependency_handles` (direct only).

`facts` reads them from the latest delivered snapshot of the assigned target.

`resolve` accepts these references:
- progress refs that were received;
- the target handle, plus handles and dependencies seen in received snapshots;
- other references through `reference_in_context`.

`validate_report`:
- applies validate_form;
- requires x-source fields to equal the facts (`monitor_recorded_fact_mismatch`);
- requires every referenced record to be of a permitted type and to have been received (`monitor_record_not_permitted_or_received`).

report_delivery.py `finish` is the same form_with_facts and runtime_forms save as the job task_report.

## Configuration

`MonitorConfiguration(services, *, outcome_page_size=32, information_unit=None, yield_settings=None)`. `_role` accepts only `'monitor'`. `as_record` holds the outcome_page_size, plus the information_unit and yield_settings when bound.

## File-by-file

`w.` = `self.workflow.`.

| file | lines | own intent | old-runner names |
|---|---|---|---|
| `__init__.py` | 1 | none | none |
| binding_record.py | 9 | binding id/version/config | none |
| configuration.py | 31 | page size; information accumulation settings | communication(1) |
| contracts.py | 10 | assignment schema; fields; states | none (domain imports) |
| credit.py | 21 | monitoring credit; information credit | ProgressInformationCredit(2) (library.progress_information_credit) |
| decision_inputs.py | 49 | decision context assembly for the monitor | `_live_original_runtime`(3), runtime(1), episode_work_report(1), w.resource_estimator(4), w.launch_instructions(2), w.available_child_roles, w.binding_context, w.episode_bindings, w.execution_expectations, w.native_estimation_context, w.pending_work, w.permits_common_action, w.resource_context, w.waiting_support |
| decision_state.py | 44 | model inputs incl. investigation_progress | `_live_original_runtime`(11), runtime(1), runtime_actions(2), w.journal(3), w.store(3), w.binding_context, w.catalog, w.controller_binding, w.delivery_status, w.extra_report_sources, w.job_episode_options, w.knowledge, w.local_outcome_preview, w.pending_work, w.receipt_projection, w.run_id, w.source_credit_binding, w.source_credit_view, w.specialist, w.tools, w.working_state |
| episode.py | 59 | role monitor; recursive child; actions; required return source | communication(1); class attrs decision_source_type, decision_prompt_renderer |
| from_child_execution_progress_assessment.py | 20 | admit the child's progress refs | communication(1), method_loop.durable content_digest(1) |
| from_parent.py | 33 | assignment validation and scope | communication(1) |
| goal.py | 15 | goal text; planning context | communication(1) |
| initial_information.py | 9 | readers for own path | none |
| internal_summary.py | 13 | monitor decision context | communication(1) |
| progress_operations.py | 58 | progress.observe/read/log | communication(1), episode_bindings native_observation_options(1) |
| progress_records.py | 16 | UTC timestamp; unique | none |
| received_api_reports.py / received_execution_information.py | 4 / 4 | own path | none |
| received_progress.py | 30 | received and own progress refs | none |
| report_delivery.py | 23 | finish | `_live_original_runtime`(7), runtime(1), runtime_forms(2), w.journal(2), w.release(2), w.binding_context, w.episode_bindings, w.facts, w.pending_handles, w.source_credit_view |
| task.py | 180 | monitor loop | `_live_original_runtime`(41), runtime(1), providers(1), episode_source_failure(1), runtime_actions(8), runtime_episodes(1), runtime_model_calls(2), w.execution_binding(7), w.journal(7), w.store(7), w.inprocess_replay(4), w.completed_unit(3), w.completions(3), w.decision_exchanges(3), w.selected(3), w.controller_value(2), w.run_id(2), w.action_schema, w.delivery_resolution_inputs, w.execute, w.last_observed_credit, w.next_return, w.pending_work, w.perform_selected_wait, w.receive_native_outcome, w.receive_outcome, w.resolve_pending_deliveries, w.resolver, w.source_credit_view, w.validate_report |
| task_decision.py | 299 | exchange protocol; complete_decision with renderer | `_live_original_runtime`(83), runtime(1), runtime_model_calls(8), w.validate_contract_information(5), w.decision_exchanges(4), w.receipts(4), w.decision_protocol(3), w.journal(3), w.provider(3), w.store(2), w.uses_received_record_context(2), w.contract_information_profile, w.contract_information_reply, w.controller_binding, w.execute, w.freeze_contract_information, w.history_preview, w.numerical_contracts, w.run_id, w.services, w.specialist |
| task_instructions.py | 86 | the monitor's full instruction text | w.binding_context, w.decision_protocol, w.knowledge, w.launch_instructions, w.native_event_information, w.permits_common_action, w.specialist (1 each) |
| task_state.py | 108 | source state (same as the job task_state) | `_live_original_runtime`(14), runtime(1), episode_source_failure(1), runtime_actions(5), w.inprocess_replay(7), w.journal(5), w.completions(4), w.execution_binding(4), w.progress_provider(2), w.store(2), w.archive, w.controller_value, w.recover_commissions, w.run_id, w.source_credit_view |
| to_child_execution_progress_assessment.py | 11 | direct-dependency child request | none (domain) |
| to_parent.py | 91 | monitoring facts, resolve, report validation | communication(1), episode_bindings reference_in_context(1) |
| waiting.py | 9 | suspension to backend | w.execution_handle(2), w.execution_backend(1) |
| yield_estimator.py | 23 | information accumulation continuation | numerical(2) estimate_nonnegative_yield(2) YieldController(2) YieldParameters(2) |

Old `services` callbacks used: reference_in_scope, read_progress, dependencies, describe_progress_target, observe_progress, read_record, execute_tool, own_outcomes, received_progress_refs, progress_selection, bound_role_credit and annotation_task_required. The old `provider._receive_progress` and `provider.read_progress` are also used, in the child return.

## Differences from similar episodes

- The job-execution siblings under `execution_job_submission` differ in these ways:
  - credit kind: monitoring here, operational there;
  - estimator: accumulation here, completion with a target there;
  - children: this episode has a recursive child, the job episodes have none;
  - actions: this episode offers child, wait and redeliver_report;
  - instructions: written out in full here, where the job episodes patch the old runtime INSTRUCTIONS;
  - provider path: a simpler `complete_decision`.
- It is a run entry role (`entry_roles = ('monitor',)`). The job episodes are not.

## Carried over

Source: `runs/carry_over/functions/a107__partner_presence_evidence__hpc_work_planning__hpc_allocation_execution__execution_progress_assessment.tsv`; old files read with `git show 97308b94c:<path>` (git dir of the repository clone `gene_annotation_episode_disk`). Kind: machinery (old-runner, not carried) or episode function (placed, or reported as not placed). Library candidates are marked.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | MonitorBindingRecord | machinery | the binding's own as_record() (configuration identity `monitor_episode_binding_v1`); the system journals settings and declared services |
| binding_record.py | MonitorBindingRecord.as_record | machinery | the binding's own as_record() (configuration identity `monitor_episode_binding_v1`); the system journals settings and declared services |
| configuration.py | MonitorConfiguration | episode function | settings: `messages/read_from_parent.py` ASSIGNMENT_FORM `information_unit` (new field); `yield_estimator.py yield_controller` (`cost`, `parameters`, same value checks); `outcome_page_size` not needed (all outcomes are in the view) |
| configuration.py | MonitorConfiguration.__init__ | episode function | settings: `messages/read_from_parent.py` ASSIGNMENT_FORM `information_unit` (new field); `yield_estimator.py yield_controller` (`cost`, `parameters`, same value checks); `outcome_page_size` not needed (all outcomes are in the view) |
| configuration.py | MonitorConfiguration._role | machinery | old role name check (`monitor` only); each role is its own episode |
| credit.py | MonitorEpisodeCredit | episode function | `credit.py credit` |
| credit.py | MonitorEpisodeCredit.credit_kind | machinery | `credit_kind` is deleted (README 3d) |
| credit.py | MonitorEpisodeCredit.credit_view | episode function | `credit.py credit` (the credit number); the other view fields are in `messages/internal_summary.py` |
| credit.py | MonitorEpisodeCredit.information_credit | episode function | `credit.py information_projection` (calls library `grading/partner_presence_evidence/progress_information_credit.py::ProgressInformationCredit`; already in library) |
| decision_inputs.py | MonitorDecisionInputs | episode function | `task.py decide` (launch_instruction_library, selected_launch_instructions); `messages/internal_summary.py`. Not carried and listed in the blocked file: resource_context, execution_expectations, resource_tool_estimates, native_execution_expectations, contract_information_profile, waiting_support, pending_work (system machinery or services not provided) |
| decision_inputs.py | MonitorDecisionInputs.decision_inputs | episode function | `task.py decide` (launch_instruction_library, selected_launch_instructions); `messages/internal_summary.py`. Not carried and listed in the blocked file: resource_context, execution_expectations, resource_tool_estimates, native_execution_expectations, contract_information_profile, waiting_support, pending_work (system machinery or services not provided) |
| decision_state.py | MonitorDecisionState | episode function | `messages/internal_summary.py internal_summary` and `task.py decide` (context); old-runner fields (pending_work, report_deliveries, report_lifecycle, receipt_projection, journal views, run_id) are machinery |
| decision_state.py | MonitorDecisionState.decision_state | episode function | `messages/internal_summary.py internal_summary` and `task.py decide` (context); old-runner fields (pending_work, report_deliveries, report_lifecycle, receipt_projection, journal views, run_id) are machinery |
| episode.py | MonitorEpisode | episode function | `episode.py ExecutionProgressAssessment` |
| episode.py | MonitorEpisode.child_roles | episode function | `task.py CHILD_SLOTS` |
| episode.py | MonitorEpisode.required_return_sources | episode function | `messages/final_to_parent.py RETURN_FORM` (fields) and `messages/msg_to_child.py` (selection) |
| episode.py | MonitorEpisode.permitted_common_actions | episode function | `task.py action` (tool and child kept; `wait` and `redeliver_report` are machinery and not carried) |
| episode.py | MonitorEpisode.allowed_children | episode function | `task.py selection_schema` (the monitor_dependency option exists only while the target exposes direct dependencies) |
| episode.py | MonitorEpisode.prepare_child_request | episode function | `messages/msg_to_child.py msg_to_child` |
| episode.py | MonitorEpisode.receive_child_progress | episode function | `messages/read_from_child.py read_from_child` |
| from_child_execution_progress_assessment.py | receive_progress | episode function | `messages/read_from_child.py read_from_child` (the recording under the operation key with a signature is machinery) |
| from_parent.py | MonitorAssignment | episode function | `messages/read_from_parent.py` ASSIGNMENT_FORM / read_from_parent |
| from_parent.py | MonitorAssignment.assignment_schema | episode function | `messages/read_from_parent.py` ASSIGNMENT_FORM / read_from_parent |
| from_parent.py | MonitorAssignment._assignment | episode function | `messages/read_from_parent.py` ASSIGNMENT_FORM / read_from_parent |
| from_parent.py | MonitorAssignment.prepare_assignment | episode function | `messages/read_from_parent.py read_from_parent`; the provider-backed admission (target is an execution handle in scope; known refs are observations of the target) is not carried (see unplaced) |
| goal.py | MonitorGoal | episode function | `goal.py GOAL`; `task.py instructions` |
| goal.py | MonitorGoal.instructions | episode function | `goal.py GOAL`; `task.py instructions` |
| goal.py | MonitorGoal.planning_context | episode function | `messages/internal_summary.py` key `monitor_goal` |
| initial_information.py | initial_information | episode function | not placed: reads the old catalog readers and `library/execution_initial_information/presentation` (`resource_information`, `received_api_information`), neither in the library nor a service; see unplaced in the blocked file |
| internal_summary.py | MonitorSummary | episode function | `messages/internal_summary.py internal_summary` |
| internal_summary.py | MonitorSummary.decision_context | episode function | `messages/internal_summary.py internal_summary` |
| progress_operations.py | ProgressOperations | episode function | `task.py catalog`, `selection_schema` |
| progress_operations.py | ProgressOperations.catalog | episode function | `task.py catalog` (including the `native_operation` property when the target description declares a `selected_observation_schema`), `selection_schema` |
| progress_operations.py | ProgressOperations.execute | episode function | `task.py progress_observe`, `progress_read`, `progress_log` (tools; `native_operation` is passed to the service as written). observe is BLOCKED-ON-JOB-SERVICE |
| progress_records.py | _timestamp | episode function | `messages/final_to_parent.py _timestamp_seconds` (copied; library candidate) |
| progress_records.py | _unique | episode function | `messages/internal_summary.py _unique` (copied; library candidate) |
| received_api_reports.py | received_api_reports | episode function | not placed: old reader-catalog selection (`catalog.received` / `catalog.configured` for this path); no catalog exists now; see unplaced in the blocked file |
| received_execution_information.py | received_execution_information | episode function | not placed: old reader-catalog selection (`catalog.received` / `catalog.configured` for this path); no catalog exists now; see unplaced in the blocked file |
| received_progress.py | ReceivedProgress | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| received_progress.py | ReceivedProgress._received | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| received_progress.py | ReceivedProgress._snapshot | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| received_progress.py | OwnProgress | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| received_progress.py | OwnProgress._own_progress_refs | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| report_delivery.py | MonitorReportDelivery | episode function | `messages/final_to_parent.py final_to_parent` (saving the form, `runtime_forms`, release and pending_handles are machinery) |
| report_delivery.py | MonitorReportDelivery.finish | episode function | `messages/final_to_parent.py final_to_parent` (saving the form, `runtime_forms`, release and pending_handles are machinery) |
| task.py | ProgressMonitoringTask | episode function | `task.py decide` and `action` |
| task.py | ProgressMonitoringTask.next | episode function | `task.py decide` and `action` |
| task.py | ProgressMonitoringTask.apply_response | episode function | `task.py action` (rejection with feedback) |
| task.py | ProgressMonitoringTask.execute | episode function | `task.py` tools and ChildCall; the `wait` branch is machinery (not carried) |
| task_decision.py | MonitorTaskDecision | machinery | the decision machine; its episode content is in `task.py decide` |
| task_decision.py | MonitorTaskDecision.call | machinery | the model call and its saving: `decide` returns a ModelRequest, the system calls and records it |
| task_decision.py | MonitorTaskDecision.instructions | episode function | `task.py instructions` |
| task_decision.py | MonitorTaskDecision.complete_decision | machinery | model call recording and conversation state |
| task_decision.py | MonitorTaskDecision.conversation_key | machinery | model call recording and conversation state |
| task_decision.py | MonitorTaskDecision.interpretation_context | machinery | the decision-exchange loop and its saved-request checks |
| task_decision.py | MonitorTaskDecision.exchange_schema | machinery | the decision-exchange loop and its saved-request checks |
| task_decision.py | MonitorTaskDecision.exchange_response | machinery | the decision-exchange loop and its saved-request checks |
| task_decision.py | MonitorTaskDecision.validate_contract_exchange_request | machinery | the decision-exchange loop and its saved-request checks |
| task_decision.py | MonitorTaskDecision.validate_contract_exchange_history | machinery | the decision-exchange loop and its saved-request checks |
| task_decision.py | MonitorTaskDecision.exchange_decision | machinery | the decision-exchange loop and its saved-request checks |
| task_instructions.py | instructions | episode function | `task.py instructions` (goal, ACTION_BOUNDARY, CREDIT_COMPONENT_GUIDANCE, HOST_EXECUTION_GUIDANCE; the blocks about the exchange, report_update, redelivery, wait, native events and resource estimates describe actions or inputs that no longer exist) |
| task_state.py | MonitorTaskState | episode function | state is `messages/internal_summary.py` (a function of the view); the decision counter, feedback and report_values are the system's or deleted |
| task_state.py | MonitorTaskState.__init__ | episode function | state is `messages/internal_summary.py` (a function of the view); the decision counter, feedback and report_values are the system's or deleted |
| task_state.py | MonitorTaskState.bind_execution_context | machinery | checkpoint/restore, effect recording and the failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.record_execution_failure | machinery | checkpoint/restore, effect recording and the failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.restore_checkpoint | machinery | checkpoint/restore, effect recording and the failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.restore | machinery | checkpoint/restore, effect recording and the failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.record_effect | machinery | checkpoint/restore, effect recording and the failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.checkpoint | machinery | checkpoint/restore, effect recording and the failed-outcome recording (a tool returns its failure as its outcome) |
| to_child_execution_progress_assessment.py | prepare_dependency_request | episode function | `messages/msg_to_child.py msg_to_child` |
| to_parent.py | MonitorReport | episode function | `messages/final_to_parent.py` |
| to_parent.py | MonitorReport.fact_sources | episode function | `messages/final_to_parent.py RETURN_FORM` |
| to_parent.py | MonitorReport.facts | episode function | `messages/final_to_parent.py monitor_facts` and `final_to_parent` |
| to_parent.py | MonitorReport.resolve | episode function | `messages/final_to_parent.py validate_report` (references must be received progress refs) |
| to_parent.py | MonitorReport.validate_report | episode function | `messages/final_to_parent.py validate_report` (the fact and received-reference checks; the first step, `validate_form` of the parent-written report schema, has no schema now and is not called) |
| waiting.py | MonitorWaiting | machinery | wait/suspension machinery |
| waiting.py | MonitorWaiting.suspension_changed | machinery | wait/suspension machinery |
| yield_estimator.py | _monitor_information_yield | machinery | episode-local estimator, deleted (README 7b: accumulation controller) |
| yield_estimator.py | MonitorEpisodeYield | episode function | `yield_estimator.py yield_controller` (AccumulationYieldController) |
| yield_estimator.py | MonitorEpisodeYield.yield_controller | episode function | `yield_estimator.py yield_controller` (AccumulationYieldController) |
