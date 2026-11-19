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
