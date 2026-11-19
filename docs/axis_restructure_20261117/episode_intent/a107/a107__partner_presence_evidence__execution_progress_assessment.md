# A107 `partner_presence_evidence/execution_progress_assessment`

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/execution_progress_assessment/<file>`
(27 files directly in the folder, about 1,280 lines; plus `tests/`: test_credit_behavior.py, test_progress_task.py,
test_prompt_behavior.py, test_task_behavior.py. These were not read. They are not grading or scoring material).

## Purpose (its own words)

`binding_path = 'partner_presence_evidence/execution_progress_assessment'`, `commissioning_parent = 'partner_presence_evidence'`,
`roles = entry_roles = ('monitor',)`. Module docstring: "Connect the predefined A107 progress-monitoring task, reports, credit and
continuation." `goal.instructions`:

> Investigate which further exposed progress information is useful for the assigned target. Use actual status, measured
> quantities, committed references and source-bound logs. Liveness establishes process presence only; elapsed time alone
> establishes neither productive work nor a stall. Unknown information stays unknown. Earlier outcomes and your admitted child
> forms inform later decisions. You may explicitly commission an ordinary monitor for one exposed direct dependency; no
> descendant traversal, fanout, cadence or depth is prescribed. Return the original parent's typed form at your closure even
> while the target remains active. Do not report private reasoning, intentions or unrestricted findings. Recorded facts use
> saved delivered observations; closure does not poll or compose another report with a model. <credit sentence>
> Repeated observation identities and read timestamps alone earn no new information.

The credit sentence is either "The monitor's information-credit projector and bound yield rule govern continuation." (private
yield) or "The caller's monitoring projector and configured controller own credit and continuation."

`planning_context` (shown as `monitor_goal`): the objective, target_handle, requested_fields, the
unresolved_question "Which exposed progress information would improve the original requested report?", the progress_definition and the yield_settings.

## Task and instructions

`task_instructions.instructions` is its own composition. It contains no scientific annotation text. It is
goal + ACTION_BOUNDARY ("Do not emit a stop action or invent a turn budget, approval review, quality gate...") +
CREDIT_COMPONENT_GUIDANCE + RESOURCE_ESTIMATE_GUIDANCE + REPORT_GUIDANCE + (EXCHANGE_HISTORY_GUIDANCE under decision_exchange_v1, otherwise
HISTORY_GUIDANCE) + HOST_EXECUTION_GUIDANCE. Then tool knowledge, the launch library and REPAIR_GUIDANCE follow, and WAIT_GUIDANCE (+ NATIVE_EVENT_GUIDANCE) when
wait is permitted. Renderer: `library.monitor_prompt.render_monitor_prompt`.

## What it reads from the parent's assignment

`_ASSIGNMENT` (contracts.py): `{version: monitor_assignment_v1, target_handle, requested_fields ⊆ FIELDS (execution_status,
measurements, log_windows, committed_record_refs, dependencies, result_available), known_progress_refs, permitted_committed_record_types}`.
`_assignment` validates it. The target handle must be in scope (`services.reference_in_scope(..., 'execution_handle')`), and each
known progress ref must belong to the same target. For a parent with role `monitor`, `prepare_assignment` applies
`prepare_dependency_request`: the child target must be an exposed direct dependency of the parent's target, and the permitted
record types may not expand.

## Children

`child_roles` → `('monitor',)` (itself, recursively). `allowed_children` gives `('monitor',)` only when
`services.dependencies(target)` is non-empty.
- Sends (to_child_execution_progress_assessment.py): the same `_ASSIGNMENT` shape for one exposed direct dependency.
- Takes back (from_child_execution_progress_assessment.py): the child's typed form is validated. Every `episode_progress`
  reference in it is read through `provider.read_progress` and recorded with `provider._receive_progress(episode_id, refs,
  content_digest(form, schema, scope), operation_key)` (`receive_child_progress`).

## Decision state shown to the model

The generic snapshot (`decision_state.py`) adds `investigation_progress` when `receipt_projection` is set and
`monitoring_information_credit/binding` when present. Own `decision_context`: `monitor_assignment`,
`monitor_target_description` (`services.describe_progress_target`), `monitor_direct_dependencies`,
`monitor_received_progress_refs` and `monitor_information_meaning` ("Exposed direct relationships and already delivered
observations. Empty measurements/log windows do not assert absence or a stall."), plus `monitor_goal`.
`decision_inputs` gives the launch library, child options, initial binding context, completed action reports, pending work,
execution expectations ('monitor'), resource estimates, native expectations and waiting_support.

## Tools offered

`permitted_common_actions` → `('tool','child','wait','redeliver_report')`. Catalog:
- `progress.observe{requested_fields [+ native_operation from the target's selected_observation_schema]}`: observe selected
  exposed fields of the assigned target. The fields may not expand the assignment. It passes the permitted record types and the operation key.
- `progress.read{progress_ref}`: an already delivered observation.
- `progress.log{progress_ref, log_index}`: one retained log window, read through `source.read` with byte custody. The representation is
  matched to the window's artifact ref.
Contract errors return `status:'invalid'` with feedback. That outcome still enters the iterator.

## Credit

`credit_kind` → 'monitoring'. `credit_view` → `services.bound_role_credit(context, receiver_selection)` (the caller-bound
projector). `information_credit(progress_reader, information_unit)` selects
`library.progress_information_credit.ProgressInformationCredit`: newly informative received snapshots × information_unit.
Repeated identities and timestamps earn nothing.

## Continuation

Private yield, when `yield_settings = {kind: 'information_accumulation', cutoff ≥ 0, uncertainty_alpha ∈ (0,1)}` with
`information_unit > 0`: `YieldController(epoch, initial_credit, cutoff, YieldParameters(uncertainty_alpha))` with
`_monitor_information_yield` = `estimate_nonnegative_yield` (it raises on a negative step). Its estimator binding is
`monitor_information_accumulation_v1`. This maps to the accumulation estimator; the settings are cutoff, uncertainty_alpha and information_unit.
Without yield_settings, the caller's controller owns continuation.

## Report to parent

`required_return_sources` for a `partner_presence_evidence` parent → `..to_child_execution_progress_assessment.required_return_sources(services)`
(the parent A107 file, not this folder). Fact sources: `monitoring_progress_refs`, `monitoring_target_handle`,
`monitoring_execution_state` (pending/executing/returned/admitted/None), `monitoring_result_available`,
`monitoring_observed_at_unix_seconds` (UTC original time, not refreshed), `monitoring_committed_record_refs` (permitted types
only) and `monitoring_dependency_handles` (direct only). `resolve` admits progress refs it received and handles of the target and its dependencies.
`validate_report` enforces fact equality and that every record reference in the form is of a permitted type and was actually delivered.

## Differences

- The only one of the four whose credit is caller-projected ('monitoring'), whose estimator is information accumulation, and
  which recursively commissions itself.
- Its task loop has no reason branch, no job_child failure handler, no automatic score updates and no shared grading retention.
  It uses `complete_decision` (provider `complete_with_presentation` with the binding's renderer) instead of the old
  `_ORIGINAL_MODEL_*` identity check.
- hpc_work_planning has its own copy of this episode under `hpc_work_planning/execution_progress_assessment`. That copy is assigned to other agents.

## File by file

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 1 | none | none |
| binding_record.py | 9 | binding id; page size; info unit and yield settings | none |
| configuration.py | 31 | outcome_page_size; information yield settings validation; role check | `communication.plain` |
| contracts.py | 10 | VERSION, FIELDS, _STATES, _ASSIGNMENT | none (`domain.REF/RECORD_SCHEMAS/obj`) |
| credit.py | 21 | monitoring credit through the caller projector; information credit selector | `services.bound_role_credit` |
| decision_inputs.py | 49 | monitor decision inputs (incl. waiting_support) | self.workflow.{resource_context, launch_instructions(2), available_child_roles, episode_bindings, binding_context, pending_work, execution_expectations, resource_estimator(4), native_estimation_context, permits_common_action, waiting_support}; `runtime.child_option_information/Mapping`; `episode_work_report.completed_action_reports` |
| decision_state.py | 44 | none (generic snapshot + investigation_progress) | self.workflow.{store(3), journal(3), working_state, run_id, local_outcome_preview, source_credit_view, receipt_projection, source_credit_binding, pending_work, delivery_status, controller_binding, catalog, knowledge, job_episode_options, extra_report_sources, specialist, binding_context, tools}; table `runtime_actions`; `runtime.*` |
| episode.py | 60 | composition; recursive monitor child; actions; child request/progress hooks | `communication.plain`; `services.dependencies` |
| from_child_execution_progress_assessment.py | 20 | admit the child's progress refs | `communication.plain/validate_form`, `method_loop.durable.content_digest`; `provider._receive_progress` |
| from_parent.py | 33 | assignment schema and validation | `services.reference_in_scope`, `services.read_progress` |
| goal.py | 15 | goal text and planning_context | `communication.plain` |
| initial_information.py | 9 | own initial information | `catalog.readers` |
| internal_summary.py | 13 | monitor decision context | `services.describe_progress_target`, `services.dependencies` |
| progress_operations.py | 58 | progress.observe/read/log | `episode_bindings.native_observation_options`; `services.observe_progress/describe_progress_target/read_record/execute_tool` |
| progress_records.py | 16 | UTC timestamp, unique | none |
| received_api_reports.py | 4 | own API readers | `catalog` |
| received_execution_information.py | 4 | own result readers | `catalog` |
| received_progress.py | 30 | received progress = known + own outcomes + received | `services.progress_selection/received_progress_refs/read_progress/own_outcomes` |
| report_delivery.py | 23 | none (generic finish) | self.workflow.{source_credit_view, pending_handles, episode_bindings, binding_context, release(2), journal(2), facts}; table `runtime_forms`; `runtime.*` |
| task.py | 180 | none (generic loop, trimmed) | self.workflow.{journal(7), inprocess_replay(4), execution_binding(7), completions(3), completed_unit(3), selected(3), next_return, resolve_pending_deliveries, action_schema, delivery_resolution_inputs, decision_exchanges(3), store(7), resolver, validate_report, execute, perform_selected_wait, pending_work, receive_native_outcome, receive_outcome, last_observed_credit, source_credit_view, controller_value(2), run_id(2)}; tables `runtime_actions`, `runtime_episodes`, `runtime_model_calls`; `runtime.*`; `providers.ModelCallError`; `episode_source_failure` |
| task_decision.py | 299 | none (generic; own complete_decision) | self.workflow.{journal, contract_information_profile, validate_contract_information(5), numerical_contracts, decision_protocol(3), decision_exchanges(4), receipts(4), uses_received_record_context(2), provider(3), history_preview, services, contract_information_reply, execute, specialist, store(2), run_id, controller_binding}; table `runtime_model_calls`; `runtime.*` (34) |
| task_instructions.py | 86 | the monitor's own instruction texts | self.workflow.{specialist, binding_context, decision_protocol, knowledge, launch_instructions, permits_common_action, native_event_information} |
| task_state.py | 108 | none | the same as local task_state |
| to_child_execution_progress_assessment.py | 11 | direct-dependency child admission | `services.dependencies` |
| to_parent.py | 91 | fact sources, facts, resolve, validate_report | `communication.*`, `episode_bindings.reference_in_context`; `services.read_progress/read_record` |
| waiting.py | 9 | none (suspension) | self.workflow.execution_handle(2), execution_backend |
| yield_estimator.py | 23 | information accumulation estimator | `numerical.{YieldController, YieldParameters, estimate_nonnegative_yield}` |

## Carried over

Rows copied from `runs/carry_over/functions/a107__partner_presence_evidence__execution_progress_assessment.tsv`; machinery is not carried. Checked against the code on 19 November 2026.

| old file | name | kind | new place or reason |
|---|---|---|---|
| binding_record.py | MonitorBindingRecord | machinery | binding's own as_record() and binding record: deleted (README 3d/3e) |
| binding_record.py | MonitorBindingRecord.as_record | machinery | binding's own as_record(): deleted |
| configuration.py | MonitorConfiguration | episode function | settings `cost`, `parameters` (yield_estimator.py); `information_unit` is the assignment field of messages/read_from_parent.py; the information-yield settings validation is the controller's |
| configuration.py | MonitorConfiguration.__init__ | episode function | `yield_estimator.py` settings['cost'], settings['parameters']; `messages/read_from_parent.py` information_unit (positive, else ContractError); outcome_page_size dropped (the summary holds all outcomes) |
| configuration.py | MonitorConfiguration._role | machinery | role check: the binding has one role; every role is its own episode |
| credit.py | MonitorEpisodeCredit | episode function | credit.py `credit` |
| credit.py | MonitorEpisodeCredit.credit_kind | machinery | credit_kind deleted (README 3d) |
| credit.py | MonitorEpisodeCredit.credit_view | episode function | credit.py `credit` (the caller-bound projector services.bound_role_credit is a service-less credit over the summary) |
| credit.py | MonitorEpisodeCredit.information_credit | episode function | credit.py `credit`: library episode_support/grading/partner_presence_evidence/progress_information_credit.py `ProgressInformationCredit(SummaryProgress(...), information_unit=...)` |
| decision_inputs.py | MonitorDecisionInputs | episode function | task.py `decide` (context) and messages/internal_summary.py |
| decision_inputs.py | MonitorDecisionInputs.decision_inputs | episode function | task.py `decide`: launch library, tool knowledge, tools, time_accounting, yield table; resource context, completed action reports, pending work, resource estimates and native expectations not carried (no object in the new runner; estimates need the estimate table) |
| decision_state.py | MonitorDecisionState | episode function | messages/internal_summary.py `internal_summary` and task.py `decide` |
| decision_state.py | MonitorDecisionState.decision_state | episode function | messages/internal_summary.py `internal_summary`; the old-runner parts (journal, working_state, receipt_projection, delivery status, pending work) are machinery |
| episode.py | MonitorEpisode | episode function | episode.py `ExecutionProgressAssessment` |
| episode.py | MonitorEpisode.child_roles | episode function | task.py `CHILD_SLOTS = {'monitor': BINDING_PATH}` |
| episode.py | MonitorEpisode.required_return_sources | episode function | messages/final_to_parent.py `RETURN_FORM` (selectable monitoring_* fields; the parent selects) |
| episode.py | MonitorEpisode.permitted_common_actions | machinery | action kinds are the system's; `redeliver_report` not carried; the wait is the tool `wait_for_events` in task.py |
| episode.py | MonitorEpisode.allowed_children | episode function | task.py `action` (a monitor child only for an exposed direct dependency) and `selection_schema` |
| episode.py | MonitorEpisode.prepare_child_request | episode function | task.py `action` (child target and record-type checks of the model's pick) and messages/msg_to_child.py |
| episode.py | MonitorEpisode.receive_child_progress | episode function | messages/read_from_child.py `read_from_child` |
| from_child_execution_progress_assessment.py | receive_progress | episode function | messages/read_from_child.py `read_from_child` (admitting the child's progress refs); provider._receive_progress ledger and content_digest signature are old receipts, machinery |
| from_parent.py | MonitorAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | MonitorAssignment.assignment_schema | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` and `ASSIGNMENT_SCHEMA` |
| from_parent.py | MonitorAssignment._assignment | episode function | messages/read_from_parent.py `read_from_parent` (schema, target of known snapshots); target in scope: task.py `target_in_scope` (BLOCKED-ON-JOB-SERVICE) |
| from_parent.py | MonitorAssignment.prepare_assignment | episode function | messages/msg_to_child.py `msg_to_child` and task.py `action` (dependency admission) |
| goal.py | MonitorGoal | episode function | goal.py and task.py `GOAL_INSTRUCTIONS` |
| goal.py | MonitorGoal.instructions | episode function | task.py `GOAL_INSTRUCTIONS`, `instructions` |
| goal.py | MonitorGoal.planning_context | episode function | messages/internal_summary.py summary['goal']; task.py `decide` monitor_goal |
| initial_information.py | initial_information | episode function | NOT PLACED: library.execution_initial_information.presentation (resource_information, received_api_information) has no module and catalog.readers is the old runner's reader catalog; the model is not shown this information |
| internal_summary.py | MonitorSummary | episode function | messages/internal_summary.py `internal_summary` and task.py `decide` |
| internal_summary.py | MonitorSummary.decision_context | episode function | messages/internal_summary.py `internal_summary`; task.py `decide` (target description and direct dependencies come from the job_access service, BLOCKED-ON-JOB-SERVICE) |
| progress_operations.py | ProgressOperations | episode function | task.py tools |
| progress_operations.py | ProgressOperations.catalog | episode function | task.py `tool_catalog` |
| progress_operations.py | ProgressOperations.execute | episode function | task.py tools `progress_observe`, `progress_read`, `progress_log` (`progress.log` reads the window through ctx.store.open_artifact instead of source.read) |
| progress_records.py | _timestamp | episode function | messages/final_to_parent.py `_timestamp_seconds` (library candidate) |
| progress_records.py | _unique | episode function | messages/internal_summary.py `_unique` (library candidate) |
| received_api_reports.py | received_api_reports | machinery | selects the old catalog reader authority (catalog.received): received records are custody now |
| received_execution_information.py | received_execution_information | machinery | selects the old catalog reader authority (catalog.received): received records are custody now |
| received_progress.py | ReceivedProgress | episode function | messages/internal_summary.py (received_progress_refs, progress_snapshots) |
| received_progress.py | ReceivedProgress._received | episode function | messages/internal_summary.py `internal_summary` received_progress_refs (known + own outcomes + child reports; the services.progress_selection/received_progress_refs providers are old-runner) |
| received_progress.py | ReceivedProgress._snapshot | episode function | task.py `_received_snapshot` |
| received_progress.py | OwnProgress | episode function | messages/internal_summary.py own_progress_refs |
| received_progress.py | OwnProgress._own_progress_refs | episode function | messages/internal_summary.py (own outcomes read from view.outcomes; services.own_outcomes paging dropped) |
| report_delivery.py | MonitorReportDelivery | machinery | report delivery/finish bookkeeping (runtime_forms, release, pending handles); the facts are messages/final_to_parent.py |
| report_delivery.py | MonitorReportDelivery.finish | machinery | generic finish: the system's final_to_parent call; nothing episode-specific |
| task.py | ProgressMonitoringTask | machinery | the old decision loop: the system's loop with task.py decide/action |
| task.py | ProgressMonitoringTask.next | episode function | task.py `decide` |
| task.py | ProgressMonitoringTask.apply_response | episode function | task.py `action` (rejection of an invalid answer by Rejected) |
| task.py | ProgressMonitoringTask.execute | machinery | execution of the selected unit, journaling, recorded replay, wait/suspension and redelivery: the system's |
| task_decision.py | MonitorTaskDecision | machinery | old decision machine |
| task_decision.py | MonitorTaskDecision.call | machinery | model call and its journaling: decide returns a ModelRequest |
| task_decision.py | MonitorTaskDecision.instructions | episode function | task.py `instructions` |
| task_decision.py | MonitorTaskDecision.complete_decision | machinery | provider complete_with_presentation with the old renderer: decide returns a ModelRequest |
| task_decision.py | MonitorTaskDecision.conversation_key | machinery | provider conversation state: deleted |
| task_decision.py | MonitorTaskDecision.interpretation_context | machinery | decision-exchange context |
| task_decision.py | MonitorTaskDecision.exchange_schema | machinery | decision-exchange loop |
| task_decision.py | MonitorTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | MonitorTaskDecision.validate_contract_exchange_request | machinery | saved-exchange check |
| task_decision.py | MonitorTaskDecision.validate_contract_exchange_history | machinery | saved-exchange check |
| task_decision.py | MonitorTaskDecision.exchange_decision | machinery | decision-exchange loop (exchange_decision) |
| task_instructions.py | instructions | episode function | task.py `instructions` (resource-estimate, report, history, repair and pending-child paragraphs describe inputs and actions that no longer exist and are not carried) |
| task_state.py | MonitorTaskState | machinery | task state, checkpoint and restore |
| task_state.py | MonitorTaskState.__init__ | machinery | task state |
| task_state.py | MonitorTaskState.bind_execution_context | machinery | task state |
| task_state.py | MonitorTaskState.record_execution_failure | machinery | a failed tool returns its outcome (task.py tools return status invalid) |
| task_state.py | MonitorTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | MonitorTaskState.restore | machinery | checkpoint/restore |
| task_state.py | MonitorTaskState.record_effect | machinery | record_effect: the system's attempts journal |
| task_state.py | MonitorTaskState.checkpoint | machinery | checkpoint/restore |
| to_child_execution_progress_assessment.py | prepare_dependency_request | episode function | task.py `action` (direct dependency and record-type checks of the model's pick) and messages/msg_to_child.py |
| to_parent.py | MonitorReport | episode function | messages/final_to_parent.py |
| to_parent.py | MonitorReport.fact_sources | episode function | messages/final_to_parent.py `RETURN_FORM` |
| to_parent.py | MonitorReport.facts | episode function | messages/final_to_parent.py `monitor_facts` (over the summary) |
| to_parent.py | MonitorReport.resolve | machinery | reference resolver of the old report validation (receipts); the check is `validate_report` over the summary's received refs |
| to_parent.py | MonitorReport.validate_report | episode function | messages/final_to_parent.py `validate_report` (the axis validate_form step is not called: no parent-written form) |
| waiting.py | MonitorWaiting | machinery | suspension machinery |
| waiting.py | MonitorWaiting.suspension_changed | machinery | suspension machinery (the wait is the tool `wait_for_events`) |
| yield_estimator.py | _monitor_information_yield | episode function | estimator deleted; accumulation controller (yield_estimator.py); its non-decrease rule is credit.py `checked_increment` |
| yield_estimator.py | MonitorEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | MonitorEpisodeYield.yield_controller | episode function | yield_estimator.py `yield_controller` (AccumulationYieldController) |
