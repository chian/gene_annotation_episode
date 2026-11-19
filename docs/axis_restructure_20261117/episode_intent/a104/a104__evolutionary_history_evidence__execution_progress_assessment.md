# a104/evolutionary_history_evidence/execution_progress_assessment — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/execution_progress_assessment/<file>`
(only files directly in this folder; no child folders, no `grading/` or `scoring/`; `tests/` with five test files is
not covered). Old binding class: `MonitorEpisode` (`binding_path = 'evolutionary_history_evidence/execution_progress_assessment'`,
`commissioning_parent = 'evolutionary_history_evidence'`, `roles = entry_roles = ('monitor',)`), decision source
`ProgressMonitoringTask`, renderer `present_task_context`. Binding record version `monitor_episode_binding_v1`.
36 files, 1970 lines (without tests).

## What it is for (its goal, in its own words)

`goal.py`:

> Investigate which further exposed progress information is useful for the assigned target. Use actual status,
> measured quantities, committed references and source-bound logs. Liveness establishes process presence only;
> elapsed time alone establishes neither productive work nor a stall. Unknown information stays unknown. Earlier
> outcomes and your admitted child forms inform later decisions. You may explicitly commission an ordinary monitor
> for one exposed direct dependency; no descendant traversal, fanout, cadence or depth is prescribed. Return the
> original parent's typed form at your closure even while the target remains active. Do not report private
> reasoning, intentions or unrestricted findings. Recorded facts use saved delivered observations; closure does not
> poll or compose another report with a model. *{credit sentence}* Repeated observation identities and read
> timestamps alone earn no new information.

The credit sentence is "The monitor's information-credit projector and bound yield rule govern continuation." when
privately yield-bound, else "The caller's monitoring projector and configured controller own credit and
continuation." `planning_context` adds: objective, target handle, requested fields, unresolved question "Which exposed
progress information would improve the original requested report?", progress definition, yield settings.

## Task and instructions

`task_instructions.py` composes its own fixed text (it does not replace a default prompt): goal + `ACTION_BOUNDARY`
("Do not emit a stop action or invent a turn budget, approval review, quality gate, experiment, term or
observation.") + `CREDIT_COMPONENT_GUIDANCE` + `RESOURCE_ESTIMATE_GUIDANCE` (timing experiments earn monitoring credit;
missing history means duration unknown; job elapsed time and own action duration are distinct) + `REPORT_GUIDANCE`
(child returns only the typed form; `report_update` before the next action; redelivery reuses saved facts) + history
guidance (exchange variant under `decision_exchange_v1`) + `HOST_EXECUTION_GUIDANCE`; then knowledge, launch library,
repair paragraph, wait and native-event paragraphs.

## What it reads from its parent's assignment

`monitor_assignment_v1` `{target_handle, requested_fields ⊆ (execution_status, measurements, log_windows,
committed_record_refs, dependencies, result_available), known_progress_refs, permitted_committed_record_types}`.
The target handle must be in scope (`execution_handle`), every known progress ref must be for the same target, and a
`monitor` parent's child assignment goes through `prepare_dependency_request`.

## Children

Role `monitor` (itself, recursively), allowed only when the target exposes direct dependencies. Sent: a
`monitor_assignment_v1` whose `target_handle` is one exposed **direct** dependency of the parent's target and whose
permitted record types do not widen the parent's. Taken back: the child's typed form; every `episode_progress`
reference in it is read and recorded as received progress (`from_child_execution_progress_assessment.py`).

## Decision state shown to the model

Old runner context (kept with its annotation-axis branch and `monitoring_information_credit` /
`monitoring_information_binding` passthrough) plus `monitor_assignment`, `monitor_target_description`,
`monitor_direct_dependencies`, `monitor_received_progress_refs`, `monitor_information_meaning` ("Exposed direct
relationships and already delivered observations. Empty measurements/log windows do not assert absence or a stall."),
`monitor_goal` (planning context). Rendered by `present_task_context` (monitor prompt).

## Tools

`progress.observe` (selected exposed fields of the assigned target; may not expand the assignment's fields; optional
`native_operation` when the target descriptor offers one; never traverses dependants), `progress.read` (an already
delivered observation), `progress.log` (one retained log window, via `source.read`, with source / artifact
custody). Plus `child`, `wait`, `redeliver_report` common actions. Its folder also holds `api_observer.py`,
`hmmer_observer.py`, `appservice_observer.py`, which the execution owners' progress provider uses to observe API jobs.

## Credit

`monitoring`. `credit_view` = the caller-bound projector (`services.bound_role_credit`). The episode offers
`information_credit(progress_reader, information_unit)` = `ProgressInformationCredit`: newly informative received
snapshots × `information_unit`; repeated identities and timestamps earn nothing.

## Continuation

Private binding when `yield_settings = {kind: 'information_accumulation', cutoff ≥ 0, uncertainty_alpha ∈ (0,1)}`
and `information_unit > 0`. Estimator `_monitor_information_yield`: scores must be non-negative,
`estimate_nonnegative_yield`, binding `monitor_information_accumulation_v1` (forecast = next action's information
credit; stop when predicted upper gain ≤ cutoff). New runner: **accumulation**, settings cutoff and uncertainty_alpha.

## What it reports to its parent

`monitoring_progress_refs`, `monitoring_target_handle`, `monitoring_execution_state` (latest delivered target
observation; null without one), `monitoring_result_available`, `monitoring_observed_at_unix_seconds` (original time,
not refreshed), `monitoring_committed_record_refs` (permitted types only), `monitoring_dependency_handles` (direct
only). Recorded fields must equal facts; any record reference in the form must be a permitted committed record that
was actually received.

## Differences from similar episodes

- Shares the task-file family with `hpc_work_planning` but has its own instruction composer with fixed guidance
  blocks, keeps the annotation-axis branch in `decision_state.py`, and has no `requested_action_history`.
- `required_return_sources` imports `required_return_sources` from the parent's
  `evolutionary_history_evidence/to_child_execution_progress_assessment.py` (`..` import), i.e. the parent decides
  what it requires back.
- `hpc_work_planning` has its own `execution_progress_assessment` child folder (not covered here).

## Old-runner and old-shared names to replace

Counts are uses (imported names counted per use) summed over this episode's files; files = how many files use it. Per-file rows are in `runs/carry_over/calls/a104_02.tsv`.

**imports from the old shared tree / old runner modules**: `a104.communication` 15 uses / 8 files, `a104.episode_bindings` 2 uses / 2 files, `a104.episode_contract_information` 2 uses / 1 files, `a104.episode_source_failure` 2 uses / 2 files, `a104.episode_work_report` 1 uses / 1 files, `a104.library.live_runtime_functions` 10 uses / 10 files, `a104.method_loop.durable` 1 uses / 1 files, `a104.numerical` 3 uses / 1 files, `a104.providers` 30 uses / 4 files, `a104.runtime` 267 uses / 12 files, `providers` 11 uses / 1 files.

**old runner object members (`self.workflow.*`, `source.workflow.*`, `workflow.*`)**: `self.workflow.action_schema` 1 uses / 1 files, `self.workflow.archive` 1 uses / 1 files, `self.workflow.available_child_roles` 1 uses / 1 files, `self.workflow.binding_context` 4 uses / 3 files, `self.workflow.catalog` 1 uses / 1 files, `self.workflow.completed_unit` 3 uses / 1 files, `self.workflow.completions` 7 uses / 3 files, `self.workflow.contract_information_profile` 1 uses / 1 files, `self.workflow.contract_information_reply` 1 uses / 1 files, `self.workflow.controller_binding` 2 uses / 2 files, `self.workflow.controller_value` 3 uses / 2 files, `self.workflow.decision_exchanges` 7 uses / 4 files, `self.workflow.decision_protocol` 3 uses / 1 files, `self.workflow.delivery_resolution_inputs` 1 uses / 1 files, `self.workflow.delivery_status` 1 uses / 1 files, `self.workflow.episode_bindings` 2 uses / 2 files, `self.workflow.execute` 2 uses / 2 files, `self.workflow.execution_backend` 1 uses / 1 files, `self.workflow.execution_binding` 11 uses / 4 files, `self.workflow.execution_expectations` 1 uses / 1 files, `self.workflow.execution_handle` 2 uses / 1 files, `self.workflow.extra_report_sources` 1 uses / 1 files, `self.workflow.facts` 1 uses / 1 files, `self.workflow.freeze_contract_information` 1 uses / 1 files, `self.workflow.history_preview` 1 uses / 1 files, `self.workflow.inprocess_replay` 11 uses / 2 files, `self.workflow.job_episode_options` 1 uses / 1 files, `self.workflow.job_episodes` 2 uses / 1 files, `self.workflow.journal` 20 uses / 9 files, `self.workflow.knowledge` 1 uses / 1 files, `self.workflow.last_observed_credit` 1 uses / 1 files, `self.workflow.launch_instructions` 2 uses / 1 files, `self.workflow.local_outcome_preview` 1 uses / 1 files, `self.workflow.native_estimation_context` 1 uses / 1 files, `self.workflow.native_event_information` 2 uses / 1 files, `self.workflow.next_return` 1 uses / 1 files, `self.workflow.numerical_contracts` 1 uses / 1 files, `self.workflow.pending_handles` 1 uses / 1 files, `self.workflow.pending_work` 3 uses / 3 files, `self.workflow.perform_selected_wait` 1 uses / 1 files, `self.workflow.permits_common_action` 1 uses / 1 files, `self.workflow.progress_provider` 2 uses / 1 files, `self.workflow.provider` 3 uses / 2 files, `self.workflow.receipt_projection` 1 uses / 1 files, `self.workflow.receipts` 4 uses / 1 files, `self.workflow.receive_native_outcome` 1 uses / 1 files, `self.workflow.receive_outcome` 1 uses / 1 files, `self.workflow.recover_commissions` 1 uses / 1 files, `self.workflow.release` 2 uses / 1 files, `self.workflow.resolve_pending_deliveries` 1 uses / 1 files, `self.workflow.resolver` 1 uses / 1 files, `self.workflow.resource_context` 1 uses / 1 files, `self.workflow.resource_estimator` 4 uses / 1 files, `self.workflow.run_id` 5 uses / 5 files, `self.workflow.selected` 3 uses / 2 files, `self.workflow.services` 2 uses / 2 files, `self.workflow.source_credit_binding` 1 uses / 1 files, `self.workflow.source_credit_view` 4 uses / 4 files, `self.workflow.specialist` 3 uses / 2 files, `self.workflow.store` 16 uses / 7 files, `self.workflow.tools` 1 uses / 1 files, `self.workflow.uses_received_record_context` 2 uses / 1 files, `self.workflow.validate_contract_information` 5 uses / 3 files, `self.workflow.validate_report` 1 uses / 1 files, `self.workflow.waiting_support` 1 uses / 1 files, `self.workflow.working_state` 1 uses / 1 files, `source.workflow.binding_context` 1 uses / 1 files, `source.workflow.decision_protocol` 1 uses / 1 files, `source.workflow.knowledge` 1 uses / 1 files, `source.workflow.launch_instructions` 1 uses / 1 files, `source.workflow.native_event_information` 1 uses / 1 files, `source.workflow.permits_common_action` 1 uses / 1 files, `source.workflow.specialist` 1 uses / 1 files, `workflow.context` 3 uses / 2 files, `workflow.evolutionary_history_evidence_binding` 1 uses / 1 files, `workflow.grains` 3 uses / 2 files, `workflow.inprocess_completion_order` 2 uses / 1 files, `workflow.launch_instructions` 1 uses / 1 files, `workflow.receipts` 2 uses / 1 files.

**old journal / receipt tables named in SQL or journal calls**: `runtime_actions` 16 uses / 6 files, `runtime_episodes` 1 uses / 1 files, `runtime_forms` 2 uses / 1 files, `runtime_model_calls` 10 uses / 5 files.

**receipt / binding-context tokens**: `binding_context` 5 uses / 4 files, `knowledge_inheritance` 1 uses / 1 files, `receipts.bind` 1 uses / 1 files, `receipts.receive` 2 uses / 1 files.

## File by file

| old file | lines | this episode's own intent | old-runner / old-shared names used |
|---|---|---|---|
| `__init__.py` | 1 | Empty. | — |
| `action_admission.py` | 67 | No episode intent beyond its class name: a per-episode copy of the old runner's `apply_response` (grain `monitor`; no reasoning action, no job-child failure branch), rebound into the old runtime namespace by `bind_functions`. | `a104.library.live_runtime_functions` {bind_functions}; `a104.runtime` {ActionFailure, ContractInformationError, Draft202012Validator, EventTargetError, ReportBoundaryError, ReportRedelivery, SourceEnd, ValidationError, WorkflowError, _decode_recorded_action_response, _json, _wait_target_feedback, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, validate_form}; `self.workflow.decision_exchanges`×3; `self.workflow.execution_binding`×1; `self.workflow.journal`×2; `self.workflow.resolver`×1; `self.workflow.selected`×1; `self.workflow.store`×1; `self.workflow.validate_report`×1; `table runtime_actions`×1; `table runtime_model_calls`×1 |
| `action_execution.py` | 75 | No episode intent beyond its class name: a per-episode copy of the old runner's `execute` (tool or wait only; no reason action, no automatic score updates), rebound into the old runtime namespace by `bind_functions`. | `a104.library.live_runtime_functions` {bind_functions}; `a104.runtime` {ActionFailure, ContractInformationError, Draft202012Validator, EventTargetError, ReportBoundaryError, ReportRedelivery, SourceEnd, ValidationError, WorkflowError, _decode_recorded_action_response, _json, _wait_target_feedback, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, validate_form}; `self.workflow.completions`×1; `self.workflow.controller_value`×2; `self.workflow.execute`×1; `self.workflow.execution_binding`×4; `self.workflow.journal`×1; `self.workflow.last_observed_credit`×1; `self.workflow.pending_work`×1; `self.workflow.perform_selected_wait`×1; `self.workflow.receive_native_outcome`×1; `self.workflow.receive_outcome`×1; `self.workflow.run_id`×1; `self.workflow.source_credit_view`×1; `self.workflow.store`×3; `table runtime_actions`×5 |
| `api_observer.py` | 58 | `APIObserver`: turns an API job event / snapshot into a progress observation for a target (HMMER via `HMMERObserver`, AppService native operations). Used by the execution owners' progress provider. | — |
| `appservice_observer.py` | 136 | `AppServiceObserver`: BV-BRC AppService monitor operations — selection of a native operation tied to the selected action, request preparation, fresh / saved response retention, source and projection of the observation. | `table runtime_actions`×1 |
| `binding_record.py` | 9 | `as_record()`: `monitor_episode_binding_v1`, `binding_id='evolutionary_history_evidence/execution_progress_assessment'`, `outcome_page_size`, and `information_unit` + `yield_settings` when privately bound. | — |
| `configuration.py` | 31 | `outcome_page_size` (default 32, ≥1); optional private yield: `yield_settings` must be exactly `{kind:'information_accumulation', cutoff≥0, uncertainty_alpha in (0,1)}` and then `information_unit>0` is required. Only role `monitor`. | `a104.communication` {plain} |
| `contracts.py` | 10 | Assignment `monitor_assignment_v1` {target_handle, requested_fields ⊆ (execution_status, measurements, log_windows, committed_record_refs, dependencies, result_available), known_progress_refs, permitted_committed_record_types}; states pending / executing / returned / admitted. | — |
| `credit.py` | 21 | `credit_kind`=`monitoring`; `credit_view` = the caller's bound projector (`services.bound_role_credit`); `information_credit(progress_reader, information_unit)` = `ProgressInformationCredit` (newly informative received snapshots × unit). | — |
| `decision_contracts.py` | 133 | No episode intent beyond its class name: a per-episode copy of the old runner's decision-exchange contract, rebound into the old runtime namespace by `bind_functions`. | `a104.library.live_runtime_functions` {bind_functions}; `a104.runtime` {CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, Draft202012Validator, Mapping, ValidationError, WorkflowError, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _category_yield_parameters, _digest, _json, _object, _plain, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema, instructional_model_context, is_contract_information, json, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic, sqlite3, state_frame, yield_table}; `self.workflow.contract_information_reply`×1; `self.workflow.decision_exchanges`×2; `self.workflow.journal`×1; `self.workflow.store`×2; `self.workflow.validate_contract_information`×2; `table runtime_model_calls`×1 |
| `decision_exchange.py` | 112 | No episode intent beyond its class name: a per-episode copy of the old runner's `decision_exchange_v1` loop, rebound into the old runtime namespace by `bind_functions`. | `a104.library.live_runtime_functions` {bind_functions}; `a104.runtime` {CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, Draft202012Validator, Mapping, ValidationError, WorkflowError, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _category_yield_parameters, _digest, _json, _object, _plain, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema, instructional_model_context, is_contract_information, json, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic, sqlite3, state_frame, yield_table}; `self.workflow.controller_binding`×1; `self.workflow.decision_exchanges`×1; `self.workflow.execute`×1; `self.workflow.journal`×1; `self.workflow.run_id`×1; `self.workflow.services`×1; `self.workflow.validate_contract_information`×1; `table runtime_model_calls`×2 |
| `decision_inputs.py` | 69 | No episode intent beyond its class name: a per-episode copy of the old runner's decision inputs (resource context, launch library, child options, initial binding context, completed action reports, pending work, execution expectations for planning role `monitor`, resource / native estimates, native event targets, waiting support), rebound into the old runtime namespace by `bind_functions`. | `a104.episode_work_report` {completed_action_reports}; `a104.library.live_runtime_functions` {bind_functions}; `a104.runtime` {Mapping, child_option_information}; `self.workflow.available_child_roles`×1; `self.workflow.binding_context`×2; `self.workflow.episode_bindings`×1; `self.workflow.execution_expectations`×1; `self.workflow.job_episodes`×2; `self.workflow.launch_instructions`×2; `self.workflow.native_estimation_context`×1; `self.workflow.native_event_information`×2; `self.workflow.pending_work`×1; `self.workflow.permits_common_action`×1; `self.workflow.resource_context`×1; `self.workflow.resource_estimator`×4; `self.workflow.store`×2; `self.workflow.waiting_support`×1; `token binding_context`×2 |
| `decision_provider.py` | 61 | Model-call hook with this episode's `present_task_context` renderer. | `a104.providers` {_ORIGINAL_DECLARED_PRESENTATION, _ORIGINAL_MODEL_COMPLETE, _ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION, _ORIGINAL_MODEL_INSTANCE_DICT}; `a104.runtime` {CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, Draft202012Validator, Mapping, ValidationError, WorkflowError, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _category_yield_parameters, _digest, _json, _object, _plain, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema, instructional_model_context, is_contract_information, json, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic, sqlite3, state_frame, yield_table}; `providers` {_ORIGINAL_MODEL_COMPLETE, _ORIGINAL_MODEL_COMPLETE_SERIAL, _ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION, _ORIGINAL_MODEL_INSTANCE_DICT, _ORIGINAL_MODEL_SESSION_TYPE, _ORIGINAL_SESSION_COMPLETE, _ORIGINAL_SESSION_PRESENTATION}; `self.workflow.provider`×1; `self.workflow.specialist`×2 |
| `decision_state.py` | 53 | No episode intent beyond its class name: a per-episode copy of the old runner's decision context (keeps the annotation-axis branch and `monitoring_information_credit` passthrough), rebound into the old runtime namespace by `bind_functions`. | `a104.library.live_runtime_functions` {bind_functions}; `a104.runtime` {FACT_MEANINGS, FACT_SOURCES, Mapping, _plain, _references_in, json}; `self.workflow.binding_context`×1; `self.workflow.catalog`×1; `self.workflow.controller_binding`×1; `self.workflow.delivery_status`×1; `self.workflow.extra_report_sources`×1; `self.workflow.job_episode_options`×1; `self.workflow.journal`×3; `self.workflow.knowledge`×1; `self.workflow.local_outcome_preview`×1; `self.workflow.pending_work`×1; `self.workflow.receipt_projection`×1; `self.workflow.run_id`×1; `self.workflow.source_credit_binding`×1; `self.workflow.source_credit_view`×1; `self.workflow.specialist`×1; `self.workflow.store`×3; `self.workflow.tools`×1; `self.workflow.working_state`×1; `table runtime_actions`×2; `token binding_context`×1 |
| `episode.py` | 60 | `binding_path='evolutionary_history_evidence/execution_progress_assessment'`, `commissioning_parent='evolutionary_history_evidence'`, `roles=entry_roles=('monitor',)`; child role `monitor` allowed only when the target exposes direct dependencies; permitted `('tool','child','wait','redeliver_report')`; `required_return_sources` from the parent's own `to_child_execution_progress_assessment` when the parent is `evolutionary_history_evidence`; child request preparation / assembly; child progress receipt. | `a104.communication` {plain} |
| `from_child_execution_progress_assessment.py` | 20 | `receive_progress`: admit the recursive monitor child's typed form; every `episode_progress` reference is read and recorded through `provider._receive_progress` with a content digest of form / schema / scope. | `a104.communication` {plain, validate_form}; `a104.method_loop.durable` {content_digest} |
| `from_parent.py` | 33 | Assignment schema `_ASSIGNMENT`; `_assignment` checks the target handle is in scope and every known progress ref belongs to the same target; a `monitor` parent's assignment goes through `prepare_dependency_request`. | `a104.communication` {plain} |
| `goal.py` | 15 | **Own goal text** ("Investigate which further exposed progress information is useful for the assigned target ... Liveness establishes process presence only; elapsed time alone establishes neither productive work nor a stall. Unknown information stays unknown ... You may explicitly commission an ordinary monitor for one exposed direct dependency; no descendant traversal, fanout, cadence or depth is prescribed. Return the original parent's typed form at your closure even while the target remains active ... Repeated observation identities and read timestamps alone earn no new information.") with a credit sentence that depends on private yield binding; `planning_context` (objective, target handle, requested fields, unresolved question, progress definition, yield settings). | `a104.communication` {plain} |
| `hmmer_observer.py` | 46 | `HMMERObserver`: qualified HMMER target observation; unknown observation when it cannot be read. | — |
| `internal_summary.py` | 13 | Model sees `monitor_assignment`, `monitor_target_description`, `monitor_direct_dependencies`, `monitor_received_progress_refs`, `monitor_information_meaning` ("Empty measurements/log windows do not assert absence or a stall"), `monitor_goal`. | `a104.communication` {plain} |
| `own_progress.py` | 16 | Page through this episode's own outcomes (`outcome_page_size`) collecting progress refs. | — |
| `presentation.py` | 42 | `present_task_context`: text renderer with prompt state, using `presentation_selection`. | `a104.providers` {DECISION_CONTEXT_VERSION, _ordinary_runtime_receiver_context, apply_state_frame, deepcopy, is_api_launch_context, is_published_scientific_context, json, render_api_launch_prompt, render_evolutionary_history_evidence_prompt, text_instructions} |
| `presentation_selection.py` | 30 | Renderer policy: HPC, published scientific, API launch, selected execution, monitor, receiver prompt. | `a104.providers` {DECISION_CONTEXT_VERSION, _ordinary_runtime_receiver_context, apply_state_frame, deepcopy, is_api_launch_context, is_published_scientific_context, json, render_api_launch_prompt, render_evolutionary_history_evidence_prompt, text_instructions} |
| `progress_operations.py` | 58 | Tools: `progress.observe` (selected exposed fields of the assigned target, never traverses dependants, may not expand requested fields; optional `native_operation` from the target descriptor), `progress.read` (an already delivered observation), `progress.log` (one retained log window with source / artifact byte custody, via `source.read`). Committed records filtered to permitted types. | `a104.communication` {plain}; `a104.episode_bindings` {native_observation_options} |
| `progress_records.py` | 16 | UTC timestamp parsing; `_unique`. | — |
| `received_progress.py` | 20 | `_received`: progress refs = caller's `progress_selection`, else known + own + received; `_snapshot` only for received refs. | — |
| `report_delivery.py` | 32 | No episode intent beyond its class name: a per-episode copy of the old runner's `finish()`, rebound into the old runtime namespace by `bind_functions`. | `a104.library.live_runtime_functions` {bind_functions}; `a104.runtime` {Record, _json, form_with_facts, json}; `self.workflow.binding_context`×1; `self.workflow.episode_bindings`×1; `self.workflow.facts`×1; `self.workflow.journal`×2; `self.workflow.pending_handles`×1; `self.workflow.release`×2; `self.workflow.source_credit_view`×1; `table runtime_forms`×2; `token binding_context`×1 |
| `task.py` | 102 | No episode intent beyond its class name: a per-episode copy of the old runner's `next()`, rebound into the old runtime namespace by `bind_functions`. | `a104.episode_source_failure` {record_source_failure}; `a104.library.live_runtime_functions` {bind_functions}; `a104.providers` {ModelCallError}; `a104.runtime` {ActionFailure, ContractInformationError, Draft202012Validator, EventTargetError, ReportBoundaryError, ReportRedelivery, SourceEnd, ValidationError, WorkflowError, _decode_recorded_action_response, _json, _wait_target_feedback, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, validate_form}; `self.workflow.action_schema`×1; `self.workflow.completed_unit`×3; `self.workflow.completions`×2; `self.workflow.delivery_resolution_inputs`×1; `self.workflow.execution_binding`×2; `self.workflow.inprocess_replay`×4; `self.workflow.journal`×4; `self.workflow.next_return`×1; `self.workflow.resolve_pending_deliveries`×1; `self.workflow.run_id`×1; `self.workflow.selected`×2; `self.workflow.store`×3; `table runtime_actions`×2; `table runtime_episodes`×1; `table runtime_model_calls`×1 |
| `task_decision.py` | 93 | No episode intent beyond its class name: a per-episode copy of the old runner's `call()`, rebound into the old runtime namespace by `bind_functions`. | `a104.library.live_runtime_functions` {bind_functions}; `a104.runtime` {CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, Draft202012Validator, Mapping, ValidationError, WorkflowError, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _category_yield_parameters, _digest, _json, _object, _plain, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema, instructional_model_context, is_contract_information, json, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic, sqlite3, state_frame, yield_table}; `self.workflow.contract_information_profile`×1; `self.workflow.decision_exchanges`×1; `self.workflow.decision_protocol`×3; `self.workflow.freeze_contract_information`×1; `self.workflow.history_preview`×1; `self.workflow.journal`×1; `self.workflow.numerical_contracts`×1; `self.workflow.provider`×2; `self.workflow.receipts`×4; `self.workflow.services`×1; `self.workflow.uses_received_record_context`×2; `self.workflow.validate_contract_information`×2; `table runtime_model_calls`×5; `token receipts.receive`×2 |
| `task_instructions.py` | 86 | **Own instruction composition** (unlike its sibling HPC episode): goal + `ACTION_BOUNDARY` (no stop action, no invented turn budget / approval / quality gate) + `CREDIT_COMPONENT_GUIDANCE` + `RESOURCE_ESTIMATE_GUIDANCE` (timing experiments earn monitoring credit; job elapsed time ≠ own action duration) + `REPORT_GUIDANCE` (child returns only the typed form; redelivery) + history guidance (exchange or fresh-conversation variant) + `HOST_EXECUTION_GUIDANCE`; then knowledge, launch library, repair, wait and native-event paragraphs. | `source.workflow.binding_context`×1; `source.workflow.decision_protocol`×1; `source.workflow.knowledge`×1; `source.workflow.launch_instructions`×1; `source.workflow.native_event_information`×1; `source.workflow.permits_common_action`×1; `source.workflow.specialist`×1; `token binding_context`×1 |
| `task_state.py` | 117 | No episode intent beyond its class name: a per-episode copy of the old runner's task state / checkpoint, rebound into the old runtime namespace by `bind_functions`. | `a104.episode_source_failure` {record_source_failure}; `a104.library.live_runtime_functions` {bind_functions}; `a104.runtime` {ActionLeaf, EFFECT_VERSION, Episode, Record, _json, _object, _plain, interpretation_schema, json}; `self.workflow.archive`×1; `self.workflow.completions`×4; `self.workflow.controller_value`×1; `self.workflow.execution_binding`×4; `self.workflow.inprocess_replay`×7; `self.workflow.journal`×5; `self.workflow.progress_provider`×2; `self.workflow.recover_commissions`×1; `self.workflow.run_id`×1; `self.workflow.source_credit_view`×1; `self.workflow.store`×2; `table runtime_actions`×5; `workflow.context`×1; `workflow.grains`×1 |
| `to_child_execution_progress_assessment.py` | 41 | `prepare_dependency_request`: a child monitor may only target an exposed **direct** dependency of the parent's target and may not widen permitted record types. `assemble_request` is a per-file copy of the old runner's child-request assembly (goal, message with scope / initial report / job and episode assignment, identity from `workflow.grains`, `knowledge_inheritance` from `workflow.receipts.bind`). | `a104.episode_contract_information` {ContractInformationError, validate_saved_fact_form}; `a104.runtime` {Episode, EpisodeGoal, EpisodeRequest, Record, _plain}; `token knowledge_inheritance`×1; `token receipts.bind`×1; `workflow.context`×2; `workflow.evolutionary_history_evidence_binding`×1; `workflow.grains`×2; `workflow.inprocess_completion_order`×2; `workflow.launch_instructions`×1; `workflow.receipts`×2 |
| `to_parent.py` | 91 | Facts `monitoring_progress_refs`, `monitoring_target_handle`, `monitoring_execution_state` (latest delivered target observation; null without one), `monitoring_result_available`, `monitoring_observed_at_unix_seconds` (not refreshed), `monitoring_committed_record_refs` (permitted types only), `monitoring_dependency_handles` (direct only). `resolve` for progress / handle namespaces; `validate_report`: recorded fields equal facts, and any record reference must be a permitted, received committed record. | `a104.communication` {plain, validate_form}; `a104.episode_bindings` {reference_in_context} |
| `waiting.py` | 9 | `suspension_changed` → `execution_backend` (old runner). | `self.workflow.execution_backend`×1; `self.workflow.execution_handle`×2 |
| `yield_estimator.py` | 23 | `_monitor_information_yield`: credit may never decrease; `estimate_nonnegative_yield` with binding `monitor_information_accumulation_v1` (forecast = next action's information credit; stop when predicted upper gain ≤ cutoff). `yield_controller` requires the private binding, uses `yield_settings.cutoff` and `uncertainty_alpha`. | `a104.numerical` {YieldController, YieldParameters, estimate_nonnegative_yield} |

## Carried over

Written 19 November 2026 by the carry-over of this episode (job episode; monitor). Old files read with `git show 97308b94c:<path>` from `/home/chia/repos/gene_annotation_episode_disk` (the working checkout has no `.git`). Items blocked or unplaced are in `docs/axis_restructure_20261117/carry_over_blocked/a104__evolutionary_history_evidence__execution_progress_assessment.md`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| action_admission.py | ProgressMonitoringTaskAdmission | machinery | hook-era class that held the bound copy of the old runner apply_response |
| action_admission.py | ProgressMonitoringTaskAdmission.apply_response | episode function | task.py::action (validation of the answer and Rejected feedback; the decision-exchange, journal, receipt, report-redelivery and runtime_* parts of the old body are machinery) |
| action_admission.py | _bind_preserved_runtime_providers | machinery | provider patching / bind_functions (README 3a) |
| action_execution.py | ProgressMonitoringTaskExecution | machinery | hook-era class that held the bound copy of the old runner execute |
| action_execution.py | ProgressMonitoringTaskExecution.execute | episode function | task.py::progress_observe, progress_read, progress_log, called as ToolCall (the journal, completions, controller_value, pending_work, wait and runtime_actions parts are machinery) |
| action_execution.py | _bind_preserved_runtime_providers | machinery | provider patching / bind_functions (README 3a) |
| api_observer.py | APIObserver | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also uses api_execution_* files, store.artifact on a raw reader |
| api_observer.py | APIObserver.__init__ | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also uses api_execution_* files, store.artifact on a raw reader |
| api_observer.py | APIObserver._observation | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also uses api_execution_* files, store.artifact on a raw reader |
| api_observer.py | APIObserver.observe_target | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also uses api_execution_* files, store.artifact on a raw reader |
| appservice_observer.py | AppServiceObserver | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also reads runtime_actions (machinery) and keeps intent/response files by operation key |
| appservice_observer.py | AppServiceObserver._selection | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also reads runtime_actions (machinery) and keeps intent/response files by operation key |
| appservice_observer.py | AppServiceObserver._prepare | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also reads runtime_actions (machinery) and keeps intent/response files by operation key |
| appservice_observer.py | AppServiceObserver._response | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also reads runtime_actions (machinery) and keeps intent/response files by operation key |
| appservice_observer.py | AppServiceObserver._source | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also reads runtime_actions (machinery) and keeps intent/response files by operation key |
| appservice_observer.py | AppServiceObserver._project | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also reads runtime_actions (machinery) and keeps intent/response files by operation key |
| appservice_observer.py | AppServiceObserver.observe | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also reads runtime_actions (machinery) and keeps intent/response files by operation key |
| binding_record.py | MonitorBindingRecord | machinery | binding_record.py (README 3 table) |
| binding_record.py | MonitorBindingRecord.as_record | machinery | the binding's own as_record() |
| configuration.py | MonitorConfiguration | episode function | yield_estimator.py::yield_controller (yield settings), messages/read_from_parent.py ASSIGNMENT_FORM (information_unit); outcome_page_size not carried (view.outcomes is read whole) |
| configuration.py | MonitorConfiguration.__init__ | episode function | yield_estimator.py::yield_controller (cutoff >= 0 and uncertainty_alpha in (0,1) checks, monitor_private_yield_binding_not_enabled); messages/read_from_parent.py (information_unit) |
| configuration.py | MonitorConfiguration._role | machinery | single role monitor; each role is its own episode |
| credit.py | MonitorEpisodeCredit | episode function | credit.py |
| credit.py | MonitorEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | MonitorEpisodeCredit.credit_view | episode function | credit.py::credit (the episode owns its projector call; services.bound_role_credit is old runner) |
| credit.py | MonitorEpisodeCredit.information_credit | episode function | credit.py::information_projection (calls the library ProgressInformationCredit, already in library: grading/evolutionary_history_evidence/progress_information_credit.py) |
| decision_contracts.py | MonitorTaskDecisionContracts | machinery | decision-exchange contract / saved-request checks (README 3a) |
| decision_contracts.py | MonitorTaskDecisionContracts.interpretation_context | machinery | decision-exchange contract / saved-request checks (README 3a) |
| decision_contracts.py | MonitorTaskDecisionContracts.exchange_schema | machinery | decision-exchange contract / saved-request checks (README 3a) |
| decision_contracts.py | MonitorTaskDecisionContracts.exchange_response | machinery | decision-exchange contract / saved-request checks (README 3a) |
| decision_contracts.py | MonitorTaskDecisionContracts.validate_contract_exchange_request | machinery | decision-exchange contract / saved-request checks (README 3a) |
| decision_contracts.py | MonitorTaskDecisionContracts.validate_contract_exchange_history | machinery | decision-exchange contract / saved-request checks (README 3a) |
| decision_contracts.py | _bind_preserved_runtime_providers | machinery | provider patching / bind_functions (README 3a) |
| decision_exchange.py | MonitorTaskDecisionExchange | machinery | decision-exchange loop |
| decision_exchange.py | MonitorTaskDecisionExchange.exchange_decision | machinery | exchange_decision (a lookup is a tool) |
| decision_exchange.py | _bind_preserved_runtime_providers | machinery | provider patching / bind_functions (README 3a) |
| decision_inputs.py | MonitorDecisionInputs | episode function | task.py::decide (context) |
| decision_inputs.py | MonitorDecisionInputs.decision_inputs | episode function | task.py::decide: launch_instruction_library and selected_launch_instructions; resource_context, execution_expectations, resource/native estimates, native_event_targets, waiting_support, completed_action_reports and pending_work are not carried (estimate_table service not provided; wait and pending work do not exist) - listed in the blocked file |
| decision_inputs.py | _bind_preserved_runtime_providers | machinery | provider patching / bind_functions (README 3a) |
| decision_provider.py | MonitorTaskDecisionProvider | machinery | model-call hook / provider patching |
| decision_provider.py | MonitorTaskDecisionProvider.decision_completion | machinery | model-call hook (the system calls the provider and records the call) |
| decision_state.py | MonitorDecisionState | episode function | messages/internal_summary.py and task.py::decide |
| decision_state.py | MonitorDecisionState.decision_state | episode function | messages/internal_summary.py::internal_summary and task.py::decide context (the annotation-axis branch, runtime_actions reads, pending_work, report_deliveries and elapsed_view are old runner and not carried; time is ctx.clock via time_accounting) |
| decision_state.py | _bind_preserved_runtime_providers | machinery | provider patching / bind_functions (README 3a) |
| episode.py | MonitorEpisode | episode function | episode.py::ExecutionProgressAssessment |
| episode.py | MonitorEpisode.child_roles | episode function | task.py CHILD_SLOTS = {'monitor': BINDING_PATH} |
| episode.py | MonitorEpisode.required_return_sources | machinery | replaced by RETURN_FORM selectable fields and ChildMessage.selection (README 3b C4) |
| episode.py | MonitorEpisode.permitted_common_actions | machinery | common actions tool/child are ToolCall/ChildCall; wait and redeliver_report are not carried |
| episode.py | MonitorEpisode.allowed_children | episode function | task.py::selection_schema (monitor_dependency offered only while the observed target exposes direct dependencies) |
| episode.py | MonitorEpisode.prepare_child_request | episode function | messages/msg_to_child.py::msg_to_child |
| episode.py | MonitorEpisode.child_request_assembler | machinery | child_request_assembler / assemble_request (README 3b C1) |
| episode.py | MonitorEpisode.receive_child_progress | episode function | messages/read_from_child.py::read_from_child |
| from_child_execution_progress_assessment.py | receive_progress | episode function | messages/read_from_child.py::read_from_child (provider._receive_progress and the content_digest signature are old runner) |
| from_parent.py | MonitorAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | MonitorAssignment.assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| from_parent.py | MonitorAssignment._assignment | episode function | messages/read_from_parent.py::read_from_parent and ASSIGNMENT_FORM (the in-scope and same-target admission through the old provider is not carried: no records or services there) |
| from_parent.py | MonitorAssignment.prepare_assignment | episode function | messages/msg_to_child.py::msg_to_child |
| goal.py | MonitorGoal | episode function | goal.py, task.py::instructions, messages/internal_summary.py |
| goal.py | MonitorGoal.instructions | episode function | goal.py::GOAL and task.py::instructions |
| goal.py | MonitorGoal.planning_context | episode function | messages/internal_summary.py (monitor_goal) |
| hmmer_observer.py | HMMERObserver | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also store.db on api_execution_observations |
| hmmer_observer.py | HMMERObserver.__init__ | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also store.db on api_execution_observations |
| hmmer_observer.py | HMMERObserver.observe_target | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also store.db on api_execution_observations |
| hmmer_observer.py | HMMERObserver._unknown_observation | episode function | unplaced: BLOCKED-ON-JOB-SERVICE (job-access service internals; no service is written here); also store.db on api_execution_observations |
| internal_summary.py | MonitorSummary | episode function | messages/internal_summary.py |
| internal_summary.py | MonitorSummary.decision_context | episode function | messages/internal_summary.py::internal_summary (monitor_* fields); the target description is a recorded job_access read in task.py::decide |
| own_progress.py | OwnProgress | episode function | messages/internal_summary.py |
| own_progress.py | OwnProgress._own_progress_refs | episode function | messages/internal_summary.py::internal_summary (own progress refs from view.outcomes; the outcome paging is not needed) |
| presentation.py | present_task_context | episode function | unplaced: library candidate (the monitor prompt renderer render_monitor_prompt is in no library module; the context travels as ModelRequest.context) |
| presentation_selection.py | task_presentation_selection | episode function | unplaced: library candidate (renderer selection over hpc/monitor/api-launch prompt renderers that are in no library module) |
| progress_operations.py | ProgressOperations | episode function | task.py (TOOLS, catalog) |
| progress_operations.py | ProgressOperations.catalog | episode function | task.py::catalog |
| progress_operations.py | ProgressOperations.execute | episode function | task.py::progress_observe, progress_read, progress_log (observe is BLOCKED-ON-JOB-SERVICE) |
| progress_records.py | _timestamp | episode function | messages/final_to_parent.py::_timestamp_seconds |
| progress_records.py | _unique | episode function | messages/internal_summary.py::_unique |
| received_progress.py | ReceivedProgress | episode function | messages/internal_summary.py, task.py |
| received_progress.py | ReceivedProgress._received | episode function | messages/internal_summary.py::internal_summary (monitor_received_progress_refs = known + own + child; services.progress_selection and received_progress_refs are old runner) |
| received_progress.py | ReceivedProgress._snapshot | episode function | task.py::_tool_call (a snapshot is handed to progress_read / progress_log only for a received ref) |
| report_delivery.py | MonitorReportDelivery | episode function | messages/final_to_parent.py |
| report_delivery.py | MonitorReportDelivery.finish | episode function | messages/final_to_parent.py::final_to_parent (form_with_facts, journal, release, pending_handles, runtime_forms are old runner) |
| report_delivery.py | _bind_preserved_runtime_providers | machinery | provider patching / bind_functions (README 3a) |
| task.py | ProgressMonitoringTask | episode function | task.py (decide, action, tools) |
| task.py | ProgressMonitoringTask.next | episode function | task.py::decide and task.py::action (the replay, completions, pending delivery, SourceEnd and checkpoint parts of the old body are machinery) |
| task.py | _bind_preserved_runtime_providers | machinery | provider patching / bind_functions (README 3a) |
| task_decision.py | MonitorTaskDecision | episode function | task.py::decide |
| task_decision.py | MonitorTaskDecision.call | machinery | old runner model-call wrapper (decision exchange, receipts, runtime_model_calls) |
| task_decision.py | MonitorTaskDecision.instructions | episode function | task.py::instructions |
| task_decision.py | MonitorTaskDecision.conversation_key | machinery | conversation state (README 3a) |
| task_decision.py | _bind_preserved_runtime_providers | machinery | provider patching / bind_functions (README 3a) |
| task_instructions.py | instructions | episode function | task.py::instructions (goal + ACTION_BOUNDARY + CREDIT_COMPONENT_GUIDANCE + RESOURCE_ESTIMATE_GUIDANCE + HOST_EXECUTION_GUIDANCE; REPORT, HISTORY, REPAIR, WAIT and NATIVE_EVENT guidance describe actions that no longer exist and are not carried) |
| task_state.py | MonitorTaskState | machinery | task state / checkpoint (README 3 table) |
| task_state.py | MonitorTaskState.__init__ | machinery | task_state.py: restore / checkpoint / record_effect / failure recording (the tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.bind_execution_context | machinery | task_state.py: restore / checkpoint / record_effect / failure recording (the tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.record_execution_failure | machinery | task_state.py: restore / checkpoint / record_effect / failure recording (the tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.restore_checkpoint | machinery | task_state.py: restore / checkpoint / record_effect / failure recording (the tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.restore | machinery | task_state.py: restore / checkpoint / record_effect / failure recording (the tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.record_effect | machinery | task_state.py: restore / checkpoint / record_effect / failure recording (the tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.checkpoint | machinery | task_state.py: restore / checkpoint / record_effect / failure recording (the tool returns its failure as its outcome) |
| task_state.py | _bind_preserved_runtime_providers | machinery | provider patching / bind_functions (README 3a) |
| to_child_execution_progress_assessment.py | prepare_dependency_request | episode function | messages/msg_to_child.py::msg_to_child (both refusals kept as the errors it raises) |
| to_child_execution_progress_assessment.py | assemble_request | machinery | child_request_assembler / assemble_request (README 3b C1, C3) |
| to_parent.py | MonitorReport | episode function | messages/final_to_parent.py |
| to_parent.py | MonitorReport.fact_sources | episode function | messages/final_to_parent.py::RETURN_FORM |
| to_parent.py | MonitorReport.facts | episode function | messages/final_to_parent.py::monitor_facts |
| to_parent.py | MonitorReport.resolve | episode function | messages/final_to_parent.py::resolve_reference |
| to_parent.py | MonitorReport.validate_report | episode function | messages/final_to_parent.py::validate_report (called by final_to_parent; its validate_form step has no counterpart, see the blocked file) |
| waiting.py | MonitorWaiting | machinery | wait / suspension machinery (README 3b) |
| waiting.py | MonitorWaiting.suspension_changed | machinery | suspension_changed -> execution_backend (old runner) |
| yield_estimator.py | _monitor_information_yield | machinery | episode-local estimator deleted (README 3d, 7b): accumulation controller; its refusal of a decreasing credit is in credit.py::credit |
| yield_estimator.py | MonitorEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | MonitorEpisodeYield.yield_controller | episode function | yield_estimator.py::yield_controller (AccumulationYieldController, README 7b) |
