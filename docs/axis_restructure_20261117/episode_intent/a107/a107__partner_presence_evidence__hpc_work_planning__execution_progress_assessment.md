# a107/partner_presence_evidence/hpc_work_planning/execution_progress_assessment — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/execution_progress_assessment/`
(27 Python files directly in the folder; no `grading/` or `scoring/` subfolder; `tests/` not read). Nothing from the
old shared root was read. Where behaviour lives in old shared modules (`root.a107.library.progress_information_credit`,
`root.a107.library.monitor_prompt`, `root.a107.numerical`, `root.a107.episode_bindings`), this page says only what this
episode's own files ask of them.

Old binding: class `MonitorEpisode`, `binding_path = 'partner_presence_evidence/hpc_work_planning/execution_progress_assessment'`,
`commissioning_parent = 'partner_presence_evidence/hpc_work_planning'`, role and entry role `monitor`, version
`monitor_episode_binding_v1`. Decision source `ProgressMonitoringTask`; prompt renderer `render_monitor_prompt`.

## What this episode is for

It watches one assigned execution target (a job handle) and gathers the exposed progress information that is useful to
the parent's requested report: status, measured quantities, committed records and source-bound log windows. It never
traverses descendants on its own; it may commission one ordinary monitor per exposed direct dependency. In its own
words (`goal.py`):

> Investigate which further exposed progress information is useful for the assigned target. Use actual status,
> measured quantities, committed references and source-bound logs. Liveness establishes process presence only; elapsed
> time alone establishes neither productive work nor a stall. Unknown information stays unknown. Earlier outcomes and
> your admitted child forms inform later decisions. You may explicitly commission an ordinary monitor for one exposed
> direct dependency; no descendant traversal, fanout, cadence or depth is prescribed. Return the original parent's typed
> form at your closure even while the target remains active. Do not report private reasoning, intentions or
> unrestricted findings. Recorded facts use saved delivered observations; closure does not poll or compose another
> report with a model. [credit sentence] Repeated observation identities and read timestamps alone earn no new
> information.

The credit sentence depends on configuration: with a private yield binding, "The monitor's information-credit projector
and bound yield rule govern continuation."; without, "The caller's monitoring projector and configured controller own
credit and continuation."

Planning context (`goal.py`): objective = the request goal; `target_handle`; `requested_fields`; unresolved question
"Which exposed progress information would improve the original requested report?"; progress definition "Actual received
information under the caller-bound monitoring projector; repeated identities and timestamps alone earn no credit.";
the yield settings.

## Task and instructions

- One unit is one model-selected action: `tool`, `child` (a monitor), `wait`, or `redeliver_report`. No `reason` action.
- Instructions (`task_instructions.py`) are composed in this order: the goal above; ACTION_BOUNDARY ("Do not emit a stop
  action or invent a turn budget, approval review, quality gate, experiment, term or observation."); CREDIT_COMPONENT
  guidance (current_evidence_vector is a progress proxy, not biological truth); RESOURCE_ESTIMATE guidance (a timing
  experiment earns monitoring credit for timing information learned; missing history means duration unknown; job
  elapsed time and the monitoring action's own duration are distinct); REPORT guidance (report_update describes the
  interpretation before the selected action; redeliver_report repairs representation only); HISTORY guidance (or the
  exchange-history variant under the decision-exchange protocol); HOST_EXECUTION ("Do not execute native provider
  tools."). Then, if present in context, the tool-knowledge and launch-library instructions; REPAIR guidance
  (pending_child_delivery → redeliver_report); WAIT guidance (wait on a pending_child_ handle, event returned,
  after_cursor 0, reconsider_at null; waiting earns no credit); NATIVE_EVENT guidance when native event information is
  bound. These text blocks are this episode's own copies (the HPC allocation episode composes a shorter set).

## What it reads from its parent's assignment

Assignment `monitor_assignment_v1` (`contracts.py`, validated in `from_parent.py`):
- `target_handle` — must be in the episode's scope in the `execution_handle` namespace;
- `requested_fields` — subset of `execution_status`, `measurements`, `log_windows`, `committed_record_refs`,
  `dependencies`, `result_available`; an observation may not request more than these;
- `known_progress_refs` — earlier observations the parent already has; each must be of the same target;
- `permitted_committed_record_types` — the record types this monitor may return.

When the parent is itself a monitor, the assignment must also satisfy the dependency rule below.

## Children

One child kind: `monitor` — this same episode, recursively (`child_roles` = `('monitor',)`), offered only when the
services expose at least one direct dependency of the assigned target (`allowed_children`).
- Sends (`to_child_execution_progress_assessment.py`): an ordinary monitor assignment whose `target_handle` is one of
  the exposed direct dependencies of this target, with `permitted_committed_record_types` a subset of this
  assignment's. Otherwise `monitor_child_target_not_exposed_direct_dependency` /
  `monitor_child_expands_permitted_record_types`.
- Takes back (`from_child_execution_progress_assessment.py`): the parent's typed form; every reference declared in the
  `episode_progress` namespace is read (must exist in scope) and the set is received into this episode's received
  progress, keyed by a content digest of form, schema and scope and the operation key. Nothing else is taken from the
  child form.

## Decision state and what the model sees

Generic old decision state (`decision_state.py`) plus this episode's `decision_context` (`internal_summary.py`):
- `monitor_assignment` (validated assignment), `monitor_target_description` (services `describe_progress_target`),
  `monitor_direct_dependencies`, `monitor_received_progress_refs`, `monitor_information_meaning` ("Exposed direct
  relationships and already delivered observations. Empty measurements/log windows do not assert absence or a stall."),
  `monitor_goal` (planning context above);
- `monitoring_information_credit` and `monitoring_information_binding` from the credit view when the projector
  supplies them.

Received progress (`received_progress.py`): the parent's `known_progress_refs`, plus every `progress_refs` in this
episode's own outcomes (read in pages of `outcome_page_size`), plus refs received from child forms — or, when the
services provide `progress_selection`, exactly that selection's `known_progress_refs`.

## Tools

`progress_operations.py`:
- `progress.observe` — observe selected exposed fields of the assigned target; keep the original observation identity
  when facts are unchanged; never traverses dependent work. Arguments: `requested_fields` (subset of the assignment's),
  plus `native_operation` when the target descriptor supplies a `selected_observation_schema` (exactly one property
  `native_operation`). Returns the snapshot, its `progress_ref`, and the committed records whose type is permitted.
- `progress.read` — read an already delivered exact observation (`progress_ref` must be received).
- `progress.log` — read one retained log window (`progress_ref`, `log_index`) by byte offsets through `source.read`,
  using the representation (original/text/stdout/stderr) whose artifact matches the window; empty window returns empty
  text.
Contract errors return an `invalid` outcome with `arguments_or_reference` feedback.

## Credit

Credit kind `monitoring`. `credit_view` is the caller's bound role credit (`services.bound_role_credit`). With a private
yield binding, `information_credit` selects `ProgressInformationCredit(progress_reader, information_unit=...)`: per the
yield binding text, credit = newly informative received snapshot count × `information_unit`; repeated identities and
timestamps earn nothing. The credit is not bounded or rescaled.

## Continuation

Private yield only when configured (`yield_settings` `{kind: information_accumulation, cutoff, uncertainty_alpha}`):
`estimate_nonnegative_yield` over the episode's credit history (raises if any score is negative), labelled
`monitor_information_accumulation_v1`, forecast "next monitor action information credit", decision "predicted upper
gain at or below monitor cutoff". Nearest current estimator: **accumulation**, settings `cutoff` and
`uncertainty_alpha`. Without a private binding, `yield_controller` raises `monitor_private_yield_binding_not_enabled`
(the caller's controller owns continuation).

## Report to parent

Fact sources (`to_parent.py`), each with a report schema carrying `x-source`:
- `monitoring_progress_refs` — delivered observation identities (namespace `episode_progress`), including admitted
  child updates;
- `monitoring_target_handle` — the assigned handle;
- `monitoring_execution_state` — lifecycle state of the latest target observation, or null;
- `monitoring_result_available` — from the latest target observation, or null;
- `monitoring_observed_at_unix_seconds` — the original UTC observation time converted, never refreshed;
- `monitoring_committed_record_refs` — permitted committed records actually delivered;
- `monitoring_dependency_handles` — direct dependencies in the latest target observation.
Validation: the form is validated against the original schema; every fact field must equal its fact; any referenced
record outside the progress/execution namespaces must be of a permitted type and among the delivered committed
records. Required return source `monitoring_progress_refs` when the parent is the axis head and an annotation task is
required.

## Differences from similar episodes

- Compared with `hpc_allocation_execution`, this episode composes the full guidance block set (action boundary,
  credit components, resource estimates, report, history, host execution), keeps the annotation-axis branches in its
  decision state and yield table, and offers `wait` always; the HPC episode drops these.
- Its credit is information accumulation, unlike the operational credit of the launch and results episodes and the
  obligation-based credit of the HPC allocation episode.
- It is the only one of the four that recursively commissions itself.
- The HPC allocation episode admits its own monitor child's progress with a copy of the same receiving rule
  (`from_child_execution_progress_assessment.py` in that folder), and validates the request against this episode's
  `_ASSIGNMENT` schema by importing `.execution_progress_assessment.contracts` from its own child folder.
- The copy of this episode under `hpc_allocation_execution/execution_progress_assessment` was not read (another
  agent's folder).

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 1 | Empty package marker. | none |
| `binding_record.py` | 9 | Binding identity record: version `monitor_episode_binding_v1`, binding id, configuration `outcome_page_size` and, when a private yield is bound, `information_unit` and `yield_settings`. | none |
| `configuration.py` | 31 | Constructor operands: `outcome_page_size` (default 32, positive int); optional private yield settings `{kind: information_accumulation, cutoff >= 0, uncertainty_alpha in (0,1)}` which then require a positive finite `information_unit`. `_role` admits only role `monitor`. | `imports root.a107`: communication |
| `contracts.py` | 10 | The parent assignment schema `monitor_assignment_v1` (target_handle, requested_fields, known_progress_refs, permitted_committed_record_types); the six observable fields; lifecycle states pending/executing/returned/admitted. | `imports root.a107`: domain |
| `credit.py` | 21 | Credit kind `monitoring`; credit view delegated to the caller's bound role credit; `information_credit` selects the library `ProgressInformationCredit` with an explicit information unit. | `BindingContext`: role; `imports root.a107`: library.progress_information_credit; `services`: bound_role_credit |
| `decision_inputs.py` | 49 | Generic old decision-input assembly (resource context, launch instruction library, child options, completed action reports, pending work, execution expectations, resource estimates, waiting support). Nothing monitor-specific except the role name `monitor` passed to execution expectations. | `imports root.a107`: episode_work_report, runtime×2; `runtime`: child_option_information, Mapping; `self.workflow`: available_child_roles, binding_context, episode_bindings, execution_expectations, launch_instructions×2, native_estimation_context, pending_work, permits_common_action, resource_context, resource_estimator×4, waiting_support |
| `decision_state.py` | 44 | Generic old decision-state assembly (working state, visible refs, credit, controller, tools, report form). Adds `monitoring_information_credit` / `monitoring_information_binding` from the credit view when present; then the binding's own `decision_context`. | `imports root.a107`: runtime×2; `journal`: elapsed_view, row; `runtime`: FACT_MEANINGS, FACT_SOURCES, json×2, Mapping×3, _plain×2, _references_in; `self.workflow`: binding_context, catalog, controller_binding, delivery_status, extra_report_sources, job_episode_options, journal×3, knowledge, local_outcome_preview, pending_work, receipt_projection, run_id, source_credit_binding, source_credit_view, specialist, store×3, tools, working_state; `tables`: runtime_actions×2; `view`: child_reports×2, controller_state, model_inputs |
| `episode.py` | 59 | Composes the binding: path, commissioning parent `partner_presence_evidence/hpc_work_planning`, roles/entry roles `monitor`, decision source `ProgressMonitoringTask`, prompt renderer `render_monitor_prompt`. Self-recursive child role `monitor`, offered only when the target exposes direct dependencies. Common actions tool, child, wait, redeliver_report. Requires return source `monitoring_progress_refs` when the parent is the axis head and an annotation task is required. | `BindingContext`: assignment, path, role×2, scope×2; `imports root.a107`: communication, library.monitor_prompt; `services`: annotation_task_required, dependencies |
| `from_child_execution_progress_assessment.py` | 20 | Admits a recursive child monitor's typed form: every `episode_progress` reference in the form is read and collected, and the set is received into this episode's progress index under a content digest of form/schema/scope. | `BindingContext`: episode_id×3, scope×2; `imports root.a107`: communication, domain, method_loop.durable; `names`: content_digest×2; `provider`: read_progress, _receive_progress |
| `from_parent.py` | 33 | Validates the parent's assignment against the schema; target handle must be in scope (`execution_handle`); every known progress ref must belong to the same target. When the parent is itself a monitor, applies the dependency-request rule. | `BindingContext`: role; `imports root.a107`: communication, domain; `services`: read_progress, reference_in_scope |
| `goal.py` | 15 | The episode's goal text and planning context (see "What this episode is for"). | `BindingContext`: assignment, request, role, scope; `imports root.a107`: communication |
| `initial_information.py` | 9 | Initial information for this recipient: resource information plus received API information from the readers declared for this binding path. | `catalog`: readers; `imports root.a107`: library.execution_initial_information.presentation |
| `internal_summary.py` | 13 | What the model sees about its own task: the assignment, target description, direct dependencies, received progress refs, the meaning note (empty measurements/logs do not assert absence or stall) and the planning context. | `BindingContext`: assignment, role, scope×3; `imports root.a107`: communication; `services`: dependencies, describe_progress_target |
| `progress_operations.py` | 58 | The three tools `progress.observe`, `progress.read`, `progress.log` and their execution (see "Tools"). | `BindingContext`: assignment×2, role, scope×4; `imports root.a107`: communication, domain, episode_bindings; `services`: describe_progress_target, execute_tool, observe_progress, read_record×2 |
| `progress_records.py` | 16 | UTC timestamp parsing (must be UTC) and order-preserving uniqueness. | `imports root.a107`: domain |
| `received_api_reports.py` | 4 | Selects this binding path's declared API reader authority from the catalog. | `catalog`: configured, received |
| `received_execution_information.py` | 4 | Selects this binding path's declared result readers from the catalog. | `catalog`: configured, received |
| `received_progress.py` | 30 | Received progress = parent-known refs + own outcome progress refs (paged by `outcome_page_size`) + refs received from children, or the services' explicit progress selection; snapshots may be read only from received refs. | `BindingContext`: assignment, episode_id×2, scope×2; `imports root.a107`: domain; `services`: own_outcomes, progress_selection, read_progress, received_progress_refs |
| `report_delivery.py` | 23 | Generic old finish: without a report contract returns credit, pending handles and current report facts; with one, composes the form from saved facts once and saves it to `runtime_forms`. | `imports root.a107`: runtime×2; `journal`: row, save; `runtime`: form_with_facts, _json×2, json, Record×2; `self.workflow`: binding_context, episode_bindings, facts, journal×2, pending_handles, release×2, source_credit_view; `tables`: runtime_forms×2 |
| `task.py` | 180 | Generic old task loop (`next`, `apply_response`, `execute`): replay, model call, action admission, tool/wait execution, credit recording and controller value. Grain name `monitor` in report validation. | `imports root.a107`: episode_source_failure, providers, runtime×2; `journal`: measure, row×7, save×3; `names`: ModelCallError×2; `runtime`: ActionFailure, ContractInformationError, _decode_recorded_action_response, Draft202012Validator×2, EventTargetError×2, inspect, _json×5, json×8, nullcontext×5, observes_action_outcome, ReportBoundaryError, ReportRedelivery×2, schema_failure_diagnostic, SourceEnd×2, validate_form, ValidationError×2, _wait_target_feedback×2, WorkflowError×2; `self.workflow`: action_schema, completed_unit×3, completions×3, controller_value×2, decision_exchanges×3, delivery_resolution_inputs, execute, execution_binding×7, inprocess_replay×4, journal×7, last_observed_credit, next_return, pending_work, perform_selected_wait, receive_native_outcome, receive_outcome, resolve_pending_deliveries, resolver, run_id×2, selected×3, source_credit_view, store×7, validate_report; `tables`: runtime_actions×8, runtime_episodes, runtime_model_calls×2; `view`: units_consumed×4 |
| `task_decision.py` | 299 | Generic old model-call machinery: journaled decision calls, decision-exchange protocol (request_context lookups vs select_action), contract-information validation, provider completion with the binding's prompt renderer. Monitor variant still carries the annotation-axis yield table branch. | `exchanges`: measure, prepare, resolve_lookup, respond, rows; `imports root.a107`: runtime×2; `journal`: measure×2, row×2, save×4; `provider`: complete; `runtime`: _action_generation_schema×2, apply_state_frame, _ASSIGNMENT_TRANSPORT, _category_yield_parameters, child_option_information, composition_lookup_schema×2, CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION×2, DECISION_EXCHANGE_PROTOCOL×5, _digest, Draft202012Validator, infernal_receiver_context×2, instructional_model_context×4, is_contract_information, _json×14, json×3, lookup_attempts, Mapping×3, model_snapshot×2, _object×3, _plain×2, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, requested_contract_information×2, schema_failure_diagnostic×2, sqlite3, state_frame, ValidationError×5, WorkflowError×14, yield_table; `self.workflow`: contract_information_profile, contract_information_reply, controller_binding, decision_exchanges×4, decision_protocol×3, execute, freeze_contract_information, history_preview, journal×3, numerical_contracts, provider×3, receipts×4, run_id, services, specialist, store×2, uses_received_record_context×2, validate_contract_information×5; `tables`: runtime_model_calls×8 |
| `task_instructions.py` | 86 | Instruction composition: binding goal + action boundary + credit-component + resource-estimate + report + history + host-execution guidance, then tool knowledge, launch library, repair, wait and native-event guidance. The guidance text blocks are this episode's own copies. | `self.workflow`: binding_context, decision_protocol, knowledge, launch_instructions, native_event_information, permits_common_action, specialist |
| `task_state.py` | 108 | Generic old per-episode mutable state, restore/checkpoint, failure recording. | `imports root.a107`: episode_source_failure, runtime×2; `journal`: row×3, save×2; `runtime`: ActionLeaf, EFFECT_VERSION, Episode, interpretation_schema, _json×2, json×4, _object, _plain, Record; `self.workflow`: archive, completions×4, context, controller_value, execution_binding×4, grains, inprocess_replay×7, journal×5, progress_provider×2, recover_commissions, run_id, source_credit_view, store×2; `tables`: runtime_actions×5 |
| `to_child_execution_progress_assessment.py` | 11 | Rule for commissioning a child monitor: the child target must be an exposed direct dependency of this target, and its permitted record types must not exceed this assignment's. | `BindingContext`: assignment, scope×2; `imports root.a107`: domain |
| `to_parent.py` | 91 | The facts this episode reports (seven `monitoring_*` sources), how references in the report are resolved, and report validation (fact fields must equal facts; referenced committed records must be permitted and received). | `BindingContext`: assignment×3, role×2, scope×6; `imports root.a107`: communication, domain, episode_bindings; `services`: read_progress×3, read_record×2 |
| `waiting.py` | 9 | Generic old suspension hook to the execution backend. | `self.workflow`: execution_backend, execution_handle×2 |
| `yield_estimator.py` | 23 | Private continuation: `estimate_nonnegative_yield` over the monitor's own credit history (credit must never decrease), labelled `monitor_information_accumulation_v1`; controller with `cutoff` and `uncertainty_alpha` from the private yield settings; raises when no private yield binding is configured. | `BindingContext`: role; `imports root.a107`: numerical×2; `names`: estimate_nonnegative_yield×2, YieldController×2, YieldParameters×2 |
