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
