# a103/gene_context_evidence/hpc_work_planning/execution_progress_assessment — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/hpc_work_planning/execution_progress_assessment/<file>` (only files directly in this
folder; `tests/` is not covered; this episode has no `grading/` or `scoring/` folder). Old binding class `MonitorEpisode`
(`binding_path = 'gene_context_evidence/hpc_work_planning/execution_progress_assessment'`,
`commissioning_parent = 'gene_context_evidence/hpc_work_planning'`, `roles = entry_roles = ('monitor',)`), decision source
`ProgressMonitoringTask`, prompt renderer `library.monitor_prompt.render_monitor_prompt`, record version
`monitor_episode_binding_v1`.

## What it is for (its goal, in its own words)

`goal.py`:

> Investigate which further exposed progress information is useful for the assigned target. Use actual status,
> measured quantities, committed references and source-bound logs. Liveness establishes process presence only; elapsed
> time alone establishes neither productive work nor a stall. Unknown information stays unknown. Earlier outcomes and
> your admitted child forms inform later decisions. You may explicitly commission an ordinary monitor for one exposed
> direct dependency; no descendant traversal, fanout, cadence or depth is prescribed. Return the original parent's typed
> form at your closure even while the target remains active. Do not report private reasoning, intentions or
> unrestricted findings. Recorded facts use saved delivered observations; closure does not poll or compose another
> report with a model.

followed by one of two credit sentences: with a private yield binding "The monitor's information-credit projector and
bound yield rule govern continuation."; otherwise "The caller's monitoring projector and configured controller own credit
and continuation." and always "Repeated observation identities and read timestamps alone earn no new information."

`planning_context`: unresolved question "Which exposed progress information would improve the original requested
report?"; progress definition "Actual received information under the caller-bound monitoring projector; repeated
identities and timestamps alone earn no credit."

## Task and instructions

The model decides each unit: a tool action, a recursive monitor child, a wait, or a report redelivery. Instructions
(`task_instructions.py`) are the goal text followed by fixed guidance blocks: ACTION_BOUNDARY ("Do not emit a stop action
or invent a turn budget, approval review, quality gate, experiment, term or observation"), CREDIT_COMPONENT_GUIDANCE,
RESOURCE_ESTIMATE_GUIDANCE ("A timing experiment earns monitoring credit for timing information learned ... Missing
history means duration is unknown"), REPORT_GUIDANCE (child returns only the parent's typed form; `report_update` is the
interpretation before the selected action; redeliver_report repairs representation only), HISTORY_GUIDANCE or
EXCHANGE_HISTORY_GUIDANCE, HOST_EXECUTION_GUIDANCE, then the tool-knowledge and launch-library instructions when present,
REPAIR_GUIDANCE (pending_child_delivery), WAIT_GUIDANCE and NATIVE_EVENT_GUIDANCE when wait is permitted.

## What it reads from its parent's assignment

`monitor_assignment_v1` (`contracts.py`): `target_handle` (an `execution_handle` in scope), `requested_fields` (subset of
`execution_status, measurements, log_windows, committed_record_refs, dependencies, result_available`),
`known_progress_refs` (each must read and name the same target), `permitted_committed_record_types`. Also the request's
`initial_report` (starting `report_values`) and report contract (interpretation schema and requested form).

## Children

One slot: `monitor` = this same binding (self-nesting). Offered only while the target exposes direct dependencies.
- Sends: a `monitor_assignment_v1` whose `target_handle` is one exposed direct dependency of the parent's target and
  whose `permitted_committed_record_types` are a subset of the parent's (`to_child_execution_progress_assessment.py`).
- Takes back: only the `episode_progress` references declared in the child's typed form; they are read, deduplicated
  and received into this episode's progress (`from_child_execution_progress_assessment.py`). The child's credit is not
  added.

## Decision state shown to the model

Old generic view (`decision_state.py`): goal, scope, working state, visible record refs, `current_credit`,
`current_evidence_vector`, `credit_binding`, `time_accounting`, `pending_work`, `last_local_outcome`, `feedback`,
`visual_evidence`, `report_deliveries`, controller state and binding, `tools`, `tool_knowledge`, `job_episode_options`,
`available_report_facts`, requested purpose/form, `current_report_update`, `current_report_basis_refs`,
`report_lifecycle`; plus `monitoring_information_credit`/`monitoring_information_binding` when present. Monitor's own
additions (`internal_summary.py`): `monitor_assignment`, `monitor_target_description`, `monitor_direct_dependencies`,
`monitor_received_progress_refs`, `monitor_information_meaning`, `monitor_goal` (planning context). Inputs added per call
(`decision_inputs.py`): resource context, launch instruction library and selected launch instructions, child options,
completed action reports, pending work, execution expectations (role `monitor`), resource-tool estimates, native
execution expectations, native event targets, waiting support.

## Tools

- `progress.observe` — observe selected exposed fields of the assigned target (never wider than `requested_fields`);
  keep the original observation identity when facts are unchanged; never traverses dependent work; optional
  `native_operation` argument when the target descriptor declares it.
- `progress.read` — read an already delivered exact progress observation (`progress_ref`).
- `progress.log` — read one retained log window (`progress_ref`, `log_index`) preserving source/artifact byte custody
  (through `source.read`).
Invalid arguments/references return an `invalid` outcome with feedback, which still enters the iterator.

## Credit

Kind `monitoring`. The credit view is the caller-bound monitoring projector (`services.bound_role_credit`). The
episode's own information credit (`credit.information_credit`) is `ProgressInformationCredit`: count of newly
informative received snapshots x `information_unit`. Unbounded; never decreases.

## Continuation

With the private yield binding (`configuration.yield_settings`): `monitor_information_accumulation_v1` — scores must not
decrease, `estimate_nonnegative_yield`, forecast = next monitor action's information credit, stop when predicted upper
gain <= cutoff. Settings: `cutoff` (finite, >= 0), `uncertainty_alpha` (0 < a < 1), plus `information_unit`. In the new
layout this is the **accumulation** yield estimator. Without the private binding the old caller's controller decided.

## Report to its parent

Fact sources (`to_parent.py`): `monitoring_progress_refs` (delivered progress identities incl. admitted child
updates), `monitoring_target_handle`, `monitoring_execution_state` (latest delivered lifecycle state or null),
`monitoring_result_available`, `monitoring_observed_at_unix_seconds` (original UTC observation time, not refreshed),
`monitoring_committed_record_refs` (permitted, delivered), `monitoring_dependency_handles` (exposed direct dependencies
in the latest observation). Every `x-source` field must equal the recorded fact; interpretive fields are the latest
admitted `report_update`. Required source `monitoring_progress_refs` when the parent is `gene_context_evidence` with an
annotation task.

## Differences from similar episodes

Byte-identical (all files except `episode.py` and `binding_record.py`, which differ only in path/parent) to
`a103/gene_context_evidence/execution_progress_assessment` and
`a103/gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment`.
`task_instructions.py` and `waiting.py` are shared with many other A103 episodes. Compared with the Results and Launch
episodes it has no `reason` action, its credit is information (snapshot count), not operational handoffs/bytes, and it
is the only one of the four that may commission itself.

## Files

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 1 | Empty package marker. | none |
| `binding_record.py` | 9 | Binding identity record: version `monitor_episode_binding_v1`, `binding_id` = this path, configuration `outcome_page_size` and, when a private yield is bound, `information_unit` and `yield_settings`. | none |
| `configuration.py` | 31 | Construction settings: `outcome_page_size` (positive int, default 32, pages own outcomes); optional private yield `{kind: information_accumulation, cutoff >= 0 finite, uncertainty_alpha in (0,1)}` which then requires a positive finite `information_unit`. Only role `monitor` is accepted. | `import`: communication |
| `contracts.py` | 10 | Assignment form `monitor_assignment_v1`: `target_handle` (text), `requested_fields` (unique subset of `execution_status, measurements, log_windows, committed_record_refs, dependencies, result_available`), `known_progress_refs` (unique refs), `permitted_committed_record_types` (unique subset of Store record schemas). Lifecycle states `pending, executing, returned, admitted`. | `import`: domain×3 |
| `credit.py` | 21 | Credit kind `monitoring`. Credit view is the caller-bound monitoring projector (`services.bound_role_credit`). Its own information credit is `ProgressInformationCredit(progress_reader, information_unit)`: newly informative received snapshots x information unit; repeated identities/timestamps earn nothing. | `BindingContext`: role; `import`: library.progress_information_credit; `services`: bound_role_credit; `yield`: ProgressInformationCredit |
| `decision_inputs.py` | 60 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Here: the execution-expectation capture and planning scopes are keyed by role `monitor`. | `import`: episode_work_report, runtime (module), runtime×2; `runtime`: Mapping, child_option_information; `self.workflow`: available_child_roles, binding_context×2, episode_bindings, execution_expectations, job_episodes×2, launch_instructions×2, native_estimation_context, native_event_information×2, pending_work, permits_common_action, resource_context, resource_estimator×4, store×2, waiting_support |
| `decision_state.py` | 44 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Builds the model view (see "decision state"); adds `monitoring_information_credit`/`monitoring_information_binding` when the credit view supplies them. | `import`: runtime (module), runtime×6; `runtime`: FACT_MEANINGS, FACT_SOURCES, Mapping×3, _plain×2, _references_in, json×2; `self.workflow`: binding_context, catalog, controller_binding, delivery_status, extra_report_sources, job_episode_options, journal×3, knowledge, local_outcome_preview, pending_work, receipt_projection, run_id, source_credit_binding, source_credit_view, specialist, store×3, tools, working_state; `table`: runtime_actions×2; `view`: child_reports×2, controller_state, model_inputs |
| `episode.py` | 53 | The binding: path, commissioning parent `gene_context_evidence/hpc_work_planning`, role and entry role `monitor`, decision source `ProgressMonitoringTask`, prompt renderer `render_monitor_prompt`. Child role `monitor` (itself, recursive) offered only while `services.dependencies(target_handle)` is non-empty. Permitted common actions `tool, child, wait, redeliver_report`. Required return source `monitoring_progress_refs` when the parent is `gene_context_evidence` and an annotation task is required. | `BindingContext`: assignment, path, role×2, scope×2; `import`: communication, library.monitor_prompt; `services`: annotation_task_required, dependencies |
| `from_child_execution_progress_assessment.py` | 20 | Admit the recursive monitor child's typed form: every field declared in namespace `episode_progress` must be a readable progress observation; those references (deduplicated) are received into this episode with a content digest of form+schema+scope and the operation key. Nothing else in the child form grants information. | `BindingContext`: episode_id×3, scope×2; `import`: communication×2, domain, method_loop.durable |
| `from_parent.py` | 33 | Assignment admission: schema check; `target_handle` must be in scope as an `execution_handle`; every `known_progress_ref` must read and name the same target. Commissioning needs an operation key; when the parent is itself a monitor the dependency rules of `to_child_*` apply. | `BindingContext`: role; `import`: communication, domain×2; `services`: read_progress, reference_in_scope |
| `goal.py` | 15 | Goal/instructions text (quoted in "What it is for") and `planning_context`: objective, target, requested fields, unresolved question "Which exposed progress information would improve the original requested report?", progress definition, yield settings. | `BindingContext`: assignment, request, role, scope; `import`: communication |
| `internal_summary.py` | 13 | Monitor-specific decision context: `monitor_assignment`, `monitor_target_description` (when the service describes it), `monitor_direct_dependencies`, `monitor_received_progress_refs`, `monitor_information_meaning` ("Empty measurements/log windows do not assert absence or a stall."), `monitor_goal`. | `BindingContext`: assignment, role, scope×3; `import`: communication; `services`: dependencies, describe_progress_target |
| `progress_operations.py` | 58 | The three tools (see "Tools") and their execution: observe may not widen `requested_fields`; optional native-operation schema from the target descriptor must be exactly `{native_operation}`; log reads go through `source.read` on the exact source/artifact byte window; committed records are filtered to permitted types; contract errors return an `invalid` outcome with feedback (they still enter the iterator). | `BindingContext`: assignment×2, role, scope×4; `import`: communication, domain×5, episode_bindings; `services`: describe_progress_target, execute_tool, observe_progress, read_record×2 |
| `progress_records.py` | 16 | Helpers: strict UTC timestamp parsing (`progress_utc_timestamp_required`) and order-preserving de-duplication. | `import`: domain |
| `received_progress.py` | 30 | What this episode has received: the assignment's known refs + refs in its own paged outcomes + refs the service says were delivered to it (or the service's `progress_selection` when present). A snapshot can be read only if received. | `BindingContext`: assignment, episode_id×2, scope×2; `import`: domain; `services`: own_outcomes, progress_selection, read_progress, received_progress_refs |
| `report_delivery.py` | 25 | Old-runner closure: without a report contract return `credit`, `pending_handles` and current report facts; with one, the saved form or `form_with_facts(report_values, schema, facts)` saved to `runtime_forms`. | `import`: library.private_policy_call, library.report_fact_assembly, runtime (module), runtime×4; `runtime`: Record×2, _json×2, form_with_facts, json; `self.workflow`: binding_context, episode_bindings, facts, journal×2, pending_handles, release×2, source_credit_view; `table`: runtime_forms×2 |
| `task.py` | 182 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Here: action kinds are `tool` and `wait` (no `reason`); report admission uses grain `monitor`; a `wait` takes the last observed credit, any other action the current credit view. | `import`: episode_source_failure, library.action_contracts, library.private_policy_call, providers, runtime (module), runtime×18; `runtime`: ActionFailure, ContractInformationError, Draft202012Validator×2, EventTargetError×2, ReportBoundaryError, ReportRedelivery×2, SourceEnd×2, ValidationError×2, WorkflowError×2, _decode_recorded_action_response, _json×5, _wait_target_feedback×2, inspect, json×8, nullcontext×5, observes_action_outcome, schema_failure_diagnostic, validate_form; `self.workflow`: action_schema, completed_unit×3, completions×3, controller_value×2, decision_exchanges×3, delivery_resolution_inputs, execute, execution_binding×7, inprocess_replay×4, journal×7, last_observed_credit, next_return, pending_work, perform_selected_wait, receive_native_outcome, receive_outcome, resolve_pending_deliveries, resolver, run_id×2, selected×3, source_credit_view, store×7, validate_report; `table`: runtime_actions×8, runtime_episodes, runtime_model_calls×2; `view`: units_consumed×4 |
| `task_decision.py` | 299 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Model call with journaling, the decision-exchange protocol (request_context lookups of child options, composition information, own attempts) and frozen contract information; dispatch through `complete_with_presentation` with this binding's prompt renderer. | `import`: runtime (module), runtime×30; `name`: composition_information×2; `runtime`: CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION×2, DECISION_EXCHANGE_PROTOCOL×5, Draft202012Validator, Mapping×3, ValidationError×5, WorkflowError×14, _ASSIGNMENT_TRANSPORT, _action_generation_schema×2, _category_yield_parameters, _digest, _json×14, _object×3, _plain×2, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema×2, instructional_model_context×4, is_contract_information, json×3, lookup_attempts, model_snapshot×2, requested_contract_information×2, schema_failure_diagnostic×2, sqlite3, state_frame, yield_table; `self.workflow`: contract_information_profile, contract_information_reply, controller_binding, decision_exchanges×4, decision_protocol×3, execute, freeze_contract_information, history_preview, journal×3, numerical_contracts, provider×3, receipts×4, run_id, services×2, specialist, store×2, uses_received_record_context×2, validate_contract_information×5; `table`: runtime_model_calls×8 |
| `task_instructions.py` | 86 | Instruction composition specific to this episode family: goal text + ACTION_BOUNDARY (no stop action, no invented budget/gate) + CREDIT_COMPONENT_GUIDANCE + RESOURCE_ESTIMATE_GUIDANCE + REPORT_GUIDANCE + HISTORY_GUIDANCE (or EXCHANGE_HISTORY_GUIDANCE) + HOST_EXECUTION_GUIDANCE, then tool knowledge, launch library, REPAIR_GUIDANCE, WAIT_GUIDANCE and NATIVE_EVENT_GUIDANCE when wait is permitted. | `self.workflow`: binding_context, decision_protocol, knowledge, launch_instructions, native_event_information, permits_common_action, specialist |
| `task_state.py` | 108 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Per-episode state: `report_values` start from the request's `initial_report`; interpretation schema from the report contract; a failed own action is recorded as a failed outcome and still enters the iterator (kinds `tool`, `reason`). | `import`: episode_source_failure, runtime (module), runtime×9; `runtime`: ActionLeaf, EFFECT_VERSION, Episode, Record, _json×2, _object, _plain, interpretation_schema, json×4; `self.workflow`: archive, completions×4, controller_value, execution_binding×4, inprocess_replay×7, journal×5, progress_provider×2, recover_commissions, run_id, source_credit_view, store×2; `table`: runtime_actions×5 |
| `to_child_execution_progress_assessment.py` | 11 | What a monitor may commission: the child's `target_handle` must be one of the parent target's exposed direct dependencies, and its permitted committed record types must be a subset of the parent's. | `BindingContext`: assignment, scope×2; `import`: domain |
| `to_parent.py` | 91 | Report facts (see "Report to parent") and their admission: reference resolution limited to received progress, the target and exposed dependency handles; every `x-source` field must equal the recorded fact; record references must be of permitted types and actually delivered. | `BindingContext`: assignment×3, role×2, scope×6; `import`: communication×2, domain, episode_bindings; `services`: read_progress×3, read_record×2 |
| `waiting.py` | 9 | Wait suspension: tells the execution backend which dependency this episode is suspended on. | `self.workflow`: execution_backend, execution_handle×2 |
| `yield_estimator.py` | 23 | Private continuation: `monitor_information_accumulation_v1`; scores must never decrease; `estimate_nonnegative_yield`; stops when the predicted upper gain is at or below the monitor cutoff; `YieldController(cutoff, YieldParameters(uncertainty_alpha))`. Raises unless the private yield binding was configured. | `BindingContext`: role; `import`: numerical×3; `yield`: YieldController, YieldParameters, estimate_nonnegative_yield, estimate_with_context |
