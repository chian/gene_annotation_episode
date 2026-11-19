# a110/biochemical_feasibility_evidence/execution_progress_assessment — episode intent at 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a110/biochemical_feasibility_evidence/execution_progress_assessment/<file>`
(only files directly in this folder; `tests/` (4 files) not read; no grading/ or scoring/ subfolder; no child folder). 26 Python files, 1,250 lines.

## Purpose (own words)

`binding_path = 'biochemical_feasibility_evidence/execution_progress_assessment'`, `commissioning_parent = 'biochemical_feasibility_evidence'`,
`roles = entry_roles = ('monitor',)`, class `MonitorEpisode`, decision source `ProgressMonitoringTask`, renderer `library.monitor_prompt.render_monitor_prompt`.
`goal.instructions`:

> Investigate which further exposed progress information is useful for the assigned target. Use actual status, measured quantities,
> committed references and source-bound logs. Liveness establishes process presence only; elapsed time alone establishes neither
> productive work nor a stall. Unknown information stays unknown. Earlier outcomes and your admitted child forms inform later decisions.
> You may explicitly commission an ordinary monitor for one exposed direct dependency; no descendant traversal, fanout, cadence or depth
> is prescribed. Return the original parent's typed form at your closure even while the target remains active. Do not report private
> reasoning, intentions or unrestricted findings. Recorded facts use saved delivered observations; closure does not poll or compose
> another report with a model. [credit sentence] Repeated observation identities and read timestamps alone earn no new information.

The credit sentence is "The monitor's information-credit projector and bound yield rule govern continuation." when a private yield binding is
configured, otherwise "The caller's monitoring projector and configured controller own credit and continuation."
`goal.planning_context` adds: objective, target_handle, requested_fields, unresolved_question "Which exposed progress information would improve
the original requested report?", progress_definition "Actual received information under the caller-bound monitoring projector; repeated
identities and timestamps alone earn no credit.", yield_settings.

## Task and instructions

`task_instructions.instructions` = binding goal text + `ACTION_BOUNDARY` ("Do not emit a stop action or invent a turn budget, approval review,
quality gate, experiment, term or observation") + `CREDIT_COMPONENT_GUIDANCE` (current_evidence_vector is the projector's component values;
a progress proxy, not biological truth) + `RESOURCE_ESTIMATE_GUIDANCE` (resource_tool_estimates describe expected time/resources; a timing
experiment earns monitoring credit for timing information learned; missing history = unknown duration; job elapsed time and own monitoring
action duration are distinct) + `REPORT_GUIDANCE` (typed-form-only return, report_update is the interpretation before the next action, no
separate report composer, redeliver_report for a report_delivery_failure, never recommission to fix representation) + history guidance
(`EXCHANGE_HISTORY_GUIDANCE` under `decision_exchange_v1`, otherwise `HISTORY_GUIDANCE`) + `HOST_EXECUTION_GUIDANCE`, then tool knowledge and
launch-library instructions when present, `REPAIR_GUIDANCE` (pending_child_delivery), and when wait is permitted `WAIT_GUIDANCE`
(pending_child_ handle, event returned, after_cursor 0; waiting earns no credit) plus `NATIVE_EVENT_GUIDANCE` when native events exist.
These guidance texts live in this episode's own file (the job episodes import theirs).

## What it reads from its parent's assignment

`contracts._ASSIGNMENT` (`monitor_assignment_v1`): `target_handle` (text), `requested_fields` (subset of execution_status, measurements,
log_windows, committed_record_refs, dependencies, result_available), `known_progress_refs`, `permitted_committed_record_types`
(enum of RECORD_SCHEMAS). `_assignment` requires the target handle in scope as an `execution_handle` and every known progress ref to read
back with the same target. `prepare_assignment` requires an operation key; when the commissioning parent is itself a monitor, the
dependency rule below applies. `required_return_sources` delegates to the parent's own
`..to_child_execution_progress_assessment.required_return_sources(services)` when the parent is `biochemical_feasibility_evidence`.

## Children it may commission

| Role | Child | Sends | Takes back |
|---|---|---|---|
| monitor (recursive, same binding) | execution_progress_assessment | `prepare_dependency_request`: the child's `target_handle` must be one of `services.dependencies(original target)` handles (exposed direct dependency only) and its permitted record types must not expand the parent's | `receive_progress`: validates the typed form; every `episode_progress` reference is read through the provider and collected; a content digest of form+schema+scope signs `provider._receive_progress(episode_id, refs, signature, operation_key)` |

`allowed_children` returns `('monitor',)` only when the target currently exposes dependencies, else none.

## Decision state and what it shows the model

`decision_state.decision_state` builds the common snapshot (goal, scope, working_state, visible_record_refs, current_credit,
current_evidence_vector, investigation_progress when receipt projection applies, credit_binding, time_accounting, pending_work,
last_local_outcome, feedback, visual_evidence, report_deliveries, controller, controller_binding, tools, tool_knowledge,
job_episode_options, available_report_facts, requested_report_purpose, requested_form, current_report_update, current_report_basis_refs,
report_lifecycle) and adds `monitoring_information_credit` / `monitoring_information_binding` when the credit view carries them.
`decision_inputs` adds resource_context, launch_instruction_library, selected_launch_instructions, child_options, the binding's initial
decision context, completed_action_reports, pending_work, execution_expectations for 'monitor', resource_tool_estimates,
native_execution_expectations, waiting_support and contract_information_profile.
The binding's own `internal_summary.decision_context` contributes `monitor_assignment`, `monitor_target_description`
(services.describe_progress_target), `monitor_direct_dependencies`, `monitor_received_progress_refs`, `monitor_information_meaning`
("Exposed direct relationships and already delivered observations. Empty measurements/log windows do not assert absence or a stall.")
and `monitor_goal` (planning_context).

## Tools offered

`progress_operations.catalog`: `progress.observe` (requested_fields, plus `native_operation` when the target descriptor supplies a closed
`selected_observation_schema`; "Retain the original observation identity when facts are unchanged. This operation never traverses dependent
work."), `progress.read` (progress_ref; only already delivered), `progress.log` (progress_ref, log_index; reads the exact retained window via
`source.read` with representation matched to the source artifact; empty window returns empty text). Observe may not expand the assignment's
requested fields. Committed records are filtered to permitted types. A ContractError returns an `invalid` outcome with feedback (it still
enters the iterator). Common actions: tool, child, wait, redeliver_report.

## Credit

`credit_kind` = `monitoring`. `credit_view` = `services.bound_role_credit(context, receiver_selection)` (the caller's projector, unchanged).
`information_credit(progress_reader, information_unit)` = `ProgressInformationCredit` — newly informative received snapshots × information_unit.
No clamping in these files.

## Continuation

Only with a private yield binding (`yield_settings = {kind: information_accumulation, cutoff (finite, >= 0), uncertainty_alpha in (0,1)}` plus a
positive `information_unit`): `YieldController(epoch, initial_credit, cutoff, YieldParameters(uncertainty_alpha))` with
`_monitor_information_yield` = `estimate_nonnegative_yield` (raises on negative scores), estimator binding
`monitor_information_accumulation_v1` (credit = newly informative snapshot count × unit; forecast = next action information credit; decision
= predicted upper gain at or below cutoff). Maps to yield_control **accumulation** with settings cutoff, uncertainty_alpha, information_unit.
Without the private binding `yield_controller` raises `monitor_private_yield_binding_not_enabled` (caller's controller governs).

## Report to parent

`to_parent.fact_sources`: `monitoring_progress_refs` (episode_progress refs incl. admitted child updates), `monitoring_target_handle`,
`monitoring_execution_state` (pending/executing/returned/admitted/null from the latest delivered target observation),
`monitoring_result_available`, `monitoring_observed_at_unix_seconds` (UTC converted, not refreshed), `monitoring_committed_record_refs`
(permitted types only), `monitoring_dependency_handles` (direct only). `validate_report`: references resolve; every x-source field equals the
recorded fact (`monitor_recorded_fact_mismatch`); any record reference in the form must be a permitted, received committed record.
`report_delivery.finish` saves facts+interpretations and the form once (runtime_forms) and returns it.

## Differences from similar episodes

- Same text as `a107/partner_presence_evidence/execution_progress_assessment` except: a107 also has `received_api_reports.py` (A110 has no API
  execution), a107 adds an `a107_sheet` key to `_completed_work_axis_results`, and a107's task_decision wraps snapshots in
  `infernal_receiver_context`.
- Unlike the job episodes (execution_result_acquisition, execution_job_submission), credit is `monitoring` (caller projector) and continuation is
  accumulation; it can recurse only on exposed direct dependencies; its guidance texts are inlined in its own task_instructions.py.
- The HPC parent's monitor child (hpc_work_planning/execution_progress_assessment, another agent) is commissioned with the same `_ASSIGNMENT`
  (hpc_work_planning imports `.execution_progress_assessment.contracts._ASSIGNMENT`).

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| __init__.py | 1 | empty package marker | none |
| binding_record.py | 9 | as_record: version monitor_episode_binding_v1, binding_id, configuration outcome_page_size (+ information_unit, yield_settings when private yield binding) | none |
| configuration.py | 31 | operands services, outcome_page_size (positive int, default 32), information_unit, yield_settings {kind information_accumulation, cutoff, uncertainty_alpha}; validation; _role admits only monitor | import:root.a110.communication(1) |
| contracts.py | 10 | VERSION; observable FIELDS; lifecycle states; _ASSIGNMENT monitor_assignment_v1 schema | import:root.a110.domain(3) |
| credit.py | 21 | credit_kind monitoring; credit_view = caller-bound role credit; information_credit = ProgressInformationCredit(unit) | import:root.a110.library.progress_information_credit(1), services.bound_role_credit(1), yield:ProgressInformationCredit(1) |
| decision_inputs.py | 49 | which extra inputs a monitor decision sees (resource/launch/child options/initial binding context/completed reports/pending work/expectations/estimates/waiting support/profile) | _live_original_runtime.Mapping(1), _live_original_runtime.child_option_information(1), import:root.a110.episode_work_report(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow(passed)(2), self.workflow.available_child_roles(1), self.workflow.binding_context(1), self.workflow.episode_bindings(1), self.workflow.execution_expectations(1), self.workflow.launch_instructions(2), self.workflow.native_estimation_context(1), self.workflow.pending_work(1), self.workflow.permits_common_action(1), self.workflow.resource_context(1), self.workflow.resource_estimator(4), self.workflow.waiting_support(1) |
| decision_state.py | 44 | common decision snapshot plus monitoring_information_credit/binding and the binding decision_context | _live_original_runtime.FACT_MEANINGS(1), _live_original_runtime.FACT_SOURCES(1), _live_original_runtime.Mapping(3), _live_original_runtime._plain(2), _live_original_runtime._references_in(1), _live_original_runtime.json(2), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.binding_context(1), self.workflow.catalog(1), self.workflow.controller_binding(1), self.workflow.delivery_status(1), self.workflow.extra_report_sources(1), self.workflow.job_episode_options(1), self.workflow.journal(3), self.workflow.knowledge(1), self.workflow.local_outcome_preview(1), self.workflow.pending_work(1), self.workflow.receipt_projection(1), self.workflow.run_id(1), self.workflow.source_credit_binding(1), self.workflow.source_credit_view(1), self.workflow.specialist(1), self.workflow.store(3), self.workflow.tools(1), self.workflow.working_state(1), table:runtime_actions(2) |
| episode.py | 58 | MonitorEpisode composition; binding_path, commissioning_parent, roles; renderer; child_roles monitor; parent return sources; common actions tool/child/wait/redeliver_report; child only when dependencies exposed | import:parent_episode:..to_child_execution_progress_assessment(1), import:root.a110.communication(1), import:root.a110.library.monitor_prompt(1), services.dependencies(1) |
| from_child_execution_progress_assessment.py | 20 | receive recursive monitor form: collect episode_progress refs, sign with content digest, deliver to provider | import:root.a110.communication(4), import:root.a110.domain(1), import:root.a110.method_loop.durable(1) |
| from_parent.py | 33 | assignment schema; target in scope as execution_handle; known progress refs must match target; dependency rule when parent is a monitor | import:root.a110.communication(1), import:root.a110.domain(4), services.read_progress(1), services.reference_in_scope(1) |
| goal.py | 15 | goal instructions text (own words) and planning_context | import:root.a110.communication(1) |
| initial_information.py | 8 | resource_information from catalog readers of this binding path | import:root.a110.library.execution_initial_information.presentation(1) |
| internal_summary.py | 13 | decision_context: assignment, target description, direct dependencies, received progress refs, information meaning, monitor_goal | import:root.a110.communication(1), services.dependencies(1) |
| progress_operations.py | 58 | tools progress.observe/read/log; field and record-type confinement; invalid outcomes returned with feedback | import:root.a110.communication(2), import:root.a110.domain(13), import:root.a110.episode_bindings(1), services.execute_tool(1), services.observe_progress(1), services.read_record(2) |
| progress_records.py | 16 | UTC timestamp parsing and _unique | import:root.a110.domain(1) |
| received_execution_information.py | 4 | select this path's configured/received result readers | none |
| received_progress.py | 30 | received progress = known refs + own outcomes (paged) + services received refs; snapshot only for received refs | import:root.a110.domain(1), services.own_outcomes(1), services.read_progress(1), services.received_progress_refs(1) |
| report_delivery.py | 23 | finish: save facts+form once, release, return form (or credit/pending handles/report facts without a contract) | _live_original_runtime.Record(2), _live_original_runtime._json(2), _live_original_runtime.form_with_facts(1), _live_original_runtime.json(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.binding_context(1), self.workflow.episode_bindings(1), self.workflow.facts(1), self.workflow.journal(2), self.workflow.pending_handles(1), self.workflow.release(2), self.workflow.source_credit_view(1), table:runtime_forms(2) |
| task.py | 180 | decision loop (replay/restore/model call/apply_response/execute); own: validate_report grain monitor | _live_original_runtime.ActionFailure(1), _live_original_runtime.ContractInformationError(1), _live_original_runtime.Draft202012Validator(2), _live_original_runtime.EventTargetError(2), _live_original_runtime.ReportBoundaryError(1), _live_original_runtime.ReportRedelivery(2), _live_original_runtime.SourceEnd(2), _live_original_runtime.ValidationError(2), _live_original_runtime.WorkflowError(2), _live_original_runtime._decode_recorded_action_response(1), _live_original_runtime._json(5), _live_original_runtime._wait_target_feedback(2), _live_original_runtime.inspect(1), _live_original_runtime.json(8), _live_original_runtime.nullcontext(5), _live_original_runtime.observes_action_outcome(1), _live_original_runtime.schema_failure_diagnostic(1), _live_original_runtime.validate_form(1), import:root.a110.episode_source_failure(1), import:root.a110.providers(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.action_schema(1), self.workflow.completed_unit(3), self.workflow.completions(3), self.workflow.controller_value(2), self.workflow.decision_exchanges(3), self.workflow.delivery_resolution_inputs(1), self.workflow.execute(1), self.workflow.execution_binding(7), self.workflow.inprocess_replay(4), self.workflow.journal(7), self.workflow.last_observed_credit(1), self.workflow.next_return(1), self.workflow.pending_work(1), self.workflow.perform_selected_wait(1), self.workflow.receive_native_outcome(1), self.workflow.receive_outcome(1), self.workflow.resolve_pending_deliveries(1), self.workflow.resolver(1), self.workflow.run_id(2), self.workflow.selected(3), self.workflow.source_credit_view(1), self.workflow.store(7), self.workflow.validate_report(1), table:runtime_actions(8), table:runtime_episodes(1), table:runtime_model_calls(2) |
| task_decision.py | 299 | decision call/exchange protocol, contract information checks, provider completion with this binding renderer | _live_original_runtime.CONTRACT_INFORMATION_OPERATIONS(1), _live_original_runtime.DECISION_CONTEXT_VERSION(2), _live_original_runtime.DECISION_EXCHANGE_PROTOCOL(5), _live_original_runtime.Draft202012Validator(1), _live_original_runtime.Mapping(3), _live_original_runtime.ValidationError(5), _live_original_runtime.WorkflowError(14), _live_original_runtime._ASSIGNMENT_TRANSPORT(1), _live_original_runtime._action_generation_schema(2), _live_original_runtime._category_yield_parameters(1), _live_original_runtime._digest(1), _live_original_runtime._json(14), _live_original_runtime._object(3), _live_original_runtime._plain(2), _live_original_runtime._recorded_action_generation_schema(1), _live_original_runtime._recorded_assignment_transport(1), _live_original_runtime._references_in(1), _live_original_runtime.apply_state_frame(1), _live_original_runtime.child_option_information(1), _live_original_runtime.composition_lookup_schema(2), _live_original_runtime.instructional_model_context(4), _live_original_runtime.is_contract_information(1), _live_original_runtime.json(3), _live_original_runtime.lookup_attempts(1), _live_original_runtime.model_snapshot(2), _live_original_runtime.requested_contract_information(2), _live_original_runtime.schema_failure_diagnostic(2), _live_original_runtime.sqlite3(1), _live_original_runtime.state_frame(1), _live_original_runtime.yield_table(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow(passed)(3), self.workflow.contract_information_profile(1), self.workflow.contract_information_reply(1), self.workflow.controller_binding(1), self.workflow.decision_exchanges(4), self.workflow.decision_protocol(3), self.workflow.execute(1), self.workflow.freeze_contract_information(1), self.workflow.history_preview(1), self.workflow.journal(3), self.workflow.numerical_contracts(1), self.workflow.provider(3), self.workflow.receipts(4), self.workflow.run_id(1), self.workflow.services(1), self.workflow.specialist(1), self.workflow.store(2), self.workflow.uses_received_record_context(2), self.workflow.validate_contract_information(5), table:runtime_model_calls(8) |
| task_instructions.py | 86 | own guidance texts (action boundary, credit components, resource estimates, report, history, host execution, repair, wait, native events) and order | workflow.binding_context(1), workflow.decision_protocol(1), workflow.knowledge(1), workflow.launch_instructions(1), workflow.native_event_information(1), workflow.permits_common_action(1), workflow.specialist(1) |
| task_state.py | 108 | episode source state, checkpoint/restore, record_effect | _live_original_runtime.ActionLeaf(1), _live_original_runtime.EFFECT_VERSION(1), _live_original_runtime.Episode(1), _live_original_runtime.Record(1), _live_original_runtime._json(2), _live_original_runtime._object(1), _live_original_runtime._plain(1), _live_original_runtime.interpretation_schema(1), _live_original_runtime.json(4), import:root.a110.episode_source_failure(1), import:root.a110.runtime(0), import:root.a110.runtime(module)(1), self.workflow.archive(1), self.workflow.completions(4), self.workflow.controller_value(1), self.workflow.execution_binding(4), self.workflow.inprocess_replay(7), self.workflow.journal(5), self.workflow.progress_provider(2), self.workflow.recover_commissions(1), self.workflow.run_id(1), self.workflow.source_credit_view(1), self.workflow.store(2), table:runtime_actions(5), workflow.context(1), workflow.grains(1) |
| to_child_execution_progress_assessment.py | 11 | child target must be an exposed direct dependency; record types cannot expand | import:root.a110.domain(2), services.dependencies(1) |
| to_parent.py | 91 | fact sources (7 monitoring_* facts), facts from latest delivered target observation, resolve namespaces, validate_report fact equality and record permission | import:root.a110.communication(4), import:root.a110.domain(4), import:root.a110.episode_bindings(1), services.read_progress(3), services.read_record(2) |
| waiting.py | 9 | suspension_changed -> execution backend suspension | self.workflow.execution_backend(1), self.workflow.execution_handle(2) |
| yield_estimator.py | 23 | monitor information accumulation estimator (non-negative scores) and YieldController from private yield settings | import:root.a110.numerical(3), yield:YieldController(1), yield:YieldParameters(1), yield:estimate_nonnegative_yield(1) |

## Carried over

Rows copied from `runs/carry_over/functions/a110__biochemical_feasibility_evidence__execution_progress_assessment.tsv`; machinery is not carried. Carried over on 19 November 2026 from `97308b94c` as a private binding in the ten-file form (goal.py, task.py, credit.py, yield_estimator.py, episode.py, messages/read_from_parent.py, msg_to_child.py, read_from_child.py, internal_summary.py, final_to_parent.py; the one child slot is this episode's own kind). Nothing is imported from another episode. Blocked items: `carry_over_blocked/a110__biochemical_feasibility_evidence__execution_progress_assessment.md`.

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
| credit.py | MonitorEpisodeCredit.information_credit | episode function | credit.py `credit`: library episode_support/grading/biochemical_feasibility_evidence/progress_information_credit.py `ProgressInformationCredit(SummaryProgress(...), information_unit=...)` |
| decision_inputs.py | MonitorDecisionInputs | episode function | task.py `decide` (context) and messages/internal_summary.py |
| decision_inputs.py | MonitorDecisionInputs.decision_inputs | episode function | task.py `decide`: launch library, tool knowledge, tools, time_accounting, yield table; resource context, completed action reports, pending work, resource estimates and native expectations not carried (no object in the new runner; estimates need the estimate table) |
| decision_state.py | MonitorDecisionState | episode function | messages/internal_summary.py `internal_summary` and task.py `decide` |
| decision_state.py | MonitorDecisionState.decision_state | episode function | messages/internal_summary.py `internal_summary`; the old-runner parts (journal, working_state, receipt_projection, delivery status, pending work) are machinery |
| episode.py | MonitorEpisode | episode function | episode.py `ExecutionProgressAssessment` |
| episode.py | MonitorEpisode.child_roles | episode function | task.py `CHILD_SLOTS = {'monitor': BINDING_PATH}` |
| episode.py | MonitorEpisode.required_return_sources | episode function | messages/final_to_parent.py `RETURN_FORM` (selectable monitoring_* fields; the parent selects) |
| episode.py | MonitorEpisode.permitted_common_actions | machinery | action kinds are the system's; `redeliver_report` not carried; the wait is the tool `wait_for_events` in task.py |
| episode.py | MonitorEpisode.allowed_children | episode function | task.py `selection_schema` (a monitor child offered only for the exposed direct dependencies of the latest delivered observation, from messages/internal_summary.py `monitor_direct_dependencies`) |
| episode.py | MonitorEpisode.prepare_child_request | episode function | messages/msg_to_child.py `msg_to_child` (child target and record-type checks raise while the commission is built; a wrong commission fails) and task.py `action` (child call) |
| episode.py | MonitorEpisode.receive_child_progress | episode function | messages/read_from_child.py `read_from_child` |
| from_child_execution_progress_assessment.py | receive_progress | episode function | messages/read_from_child.py `read_from_child` (admitting the child's progress refs); provider._receive_progress ledger and content_digest signature are old receipts, machinery |
| from_parent.py | MonitorAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | MonitorAssignment.assignment_schema | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` (one field per old property, same names) |
| from_parent.py | MonitorAssignment._assignment | episode function | messages/read_from_parent.py `read_from_parent` (schema, target of known snapshots); target in scope: task.py `target_in_scope` (BLOCKED-ON-JOB-SERVICE) |
| from_parent.py | MonitorAssignment.prepare_assignment | episode function | messages/msg_to_child.py `msg_to_child` (the dependency rule of the child assignment) |
| goal.py | MonitorGoal | episode function | goal.py `GOAL` |
| goal.py | MonitorGoal.instructions | episode function | task.py `instructions` |
| goal.py | MonitorGoal.planning_context | episode function | messages/internal_summary.py summary['goal']; task.py `decide` monitor_goal |
| initial_information.py | initial_information | episode function | NOT PLACED: library.execution_initial_information.presentation (resource_information, received_api_information) has no module and catalog.readers is the old runner's reader catalog; the model is not shown this information |
| internal_summary.py | MonitorSummary | episode function | messages/internal_summary.py `internal_summary` and task.py `decide` |
| internal_summary.py | MonitorSummary.decision_context | episode function | messages/internal_summary.py `internal_summary` (assignment, received progress refs, direct dependencies of the latest delivered observation, meaning, goal); task.py `decide` (target description: job_access recorded read, BLOCKED-ON-JOB-SERVICE) |
| progress_operations.py | ProgressOperations | episode function | task.py tools |
| progress_operations.py | ProgressOperations.catalog | episode function | task.py `tool_catalog` |
| progress_operations.py | ProgressOperations.execute | episode function | task.py tools `progress_observe`, `progress_read`, `progress_log` (`progress.log` reads the window through ctx.store.open_artifact instead of source.read) |
| progress_records.py | _timestamp | episode function | messages/final_to_parent.py `_timestamp_seconds` (library candidate) |
| progress_records.py | _unique | episode function | messages/internal_summary.py `_unique` (library candidate) |
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
| to_child_execution_progress_assessment.py | prepare_dependency_request | episode function | messages/msg_to_child.py `msg_to_child` (raises monitor_child_target_not_exposed_direct_dependency and monitor_child_expands_permitted_record_types) |
| to_parent.py | MonitorReport | episode function | messages/final_to_parent.py |
| to_parent.py | MonitorReport.fact_sources | episode function | messages/final_to_parent.py `RETURN_FORM` |
| to_parent.py | MonitorReport.facts | episode function | messages/final_to_parent.py `monitor_facts` (over the summary) |
| to_parent.py | MonitorReport.resolve | machinery | reference resolver of the old report validation (receipts); the check is `validate_report` over the summary's received refs |
| to_parent.py | MonitorReport.validate_report | episode function | messages/final_to_parent.py `validate_report` (recorded-fact, progress-ref, committed-record and state checks; the axis validate_form step raises NotImplementedError(validate_form_not_built:a110)) |
| waiting.py | MonitorWaiting | machinery | suspension machinery |
| waiting.py | MonitorWaiting.suspension_changed | machinery | suspension machinery (the wait is the tool `wait_for_events`) |
| yield_estimator.py | _monitor_information_yield | episode function | estimator deleted; accumulation controller (yield_estimator.py); its non-decrease rule is credit.py `checked_increment` |
| yield_estimator.py | MonitorEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | MonitorEpisodeYield.yield_controller | episode function | yield_estimator.py `yield_controller` (AccumulationYieldController) |
