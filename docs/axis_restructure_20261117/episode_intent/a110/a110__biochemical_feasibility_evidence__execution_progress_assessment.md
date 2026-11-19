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
