# a101 / sequence_homology_evidence / execution_progress_assessment

Source: the episode's own files at commit `97308b94c`
(`git show HEAD:gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/execution_progress_assessment/<file>`).
`tests/` is not covered here. Old binding class `MonitorEpisode`; decision source `ProgressMonitoringTask`; prompt
renderer `render_monitor_prompt`.

## Purpose (goal, in its own words)

Role `monitor` (also an entry role). `goal.py`:

> Investigate which further exposed progress information is useful for the assigned target. Use actual status,
> measured quantities, committed references and source-bound logs. Liveness establishes process presence only;
> elapsed time alone establishes neither productive work nor a stall. Unknown information stays unknown. Earlier
> outcomes and your admitted child forms inform later decisions. You may explicitly commission an ordinary monitor for
> one exposed direct dependency; no descendant traversal, fanout, cadence or depth is prescribed. Return the original
> parent's typed form at your closure even while the target remains active. Do not report private reasoning,
> intentions or unrestricted findings. Recorded facts use saved delivered observations; closure does not poll or
> compose another report with a model. *[private: "The monitor's information-credit projector and bound yield rule
> govern continuation." / otherwise: "The caller's monitoring projector and configured controller own credit and
> continuation."]* Repeated observation identities and read timestamps alone earn no new information.

The planning context (`monitor_goal`) holds: objective, target_handle, requested_fields, unresolved_question "Which
exposed progress information would improve the original requested report?", progress_definition "Actual received
information under the caller-bound monitoring projector; repeated identities and timestamps alone earn no credit.",
and yield_settings.

## Task and instructions

`task_instructions.instructions` is this episode's own composition. It does not use the A-root INSTRUCTIONS. It
joins: monitor goal + ACTION_BOUNDARY (no stop action or invented budget/gate) + CREDIT_COMPONENT_GUIDANCE +
RESOURCE_ESTIMATE_GUIDANCE + REPORT_GUIDANCE + history guidance (exchange or plain) + HOST_EXECUTION_GUIDANCE. Then it
adds tool knowledge, launch instructions, REPAIR_GUIDANCE, and WAIT_GUIDANCE / NATIVE_EVENT_GUIDANCE when wait is
permitted. `task.py` follows the common loop with selected wait support. Compared with local_job_execution it has no
automatic score updates and none of the component/MinHash/reads.map feedback branches. `task_decision.decision_completion`
calls the provider through `complete_with_presentation(prompt_renderer=render_monitor_prompt)`.

## What it reads from its parent's assignment

Assignment `monitor_assignment_v1` (`contracts._ASSIGNMENT`):

- `target_handle`, which must be in scope as an `execution_handle`;
- `requested_fields`, a subset of execution_status, measurements, log_windows, committed_record_refs, dependencies,
  result_available;
- `known_progress_refs`, each of which must be a progress snapshot of the same target;
- `permitted_committed_record_types`.

`prepare_assignment` requires an operation_key. When the parent is itself a monitor, the assignment also goes
through `prepare_dependency_request`.

## Children

- `monitor` (itself, recursively), offered only when `services.dependencies(target_handle)` is non-empty.
- To the child (`to_child_execution_progress_assessment.prepare_dependency_request`): a `monitor_assignment_v1`
  whose target_handle must be one of the parent target's exposed direct dependencies, and whose
  permitted_committed_record_types may not widen the parent's.
- From the child (`from_child_execution_progress_assessment.receive_progress`): the child's typed form is validated
  and its `episode_progress` references are read and admitted into the provider's progress receipt index (under a
  signature digest of form, schema and scope). They then count as received progress for this monitor.

## Decision state shown to the model

The common decision_state (goal, credit, controller, tools, report form, ...), plus `internal_summary.decision_context`:
monitor_assignment, monitor_target_description, monitor_direct_dependencies, monitor_received_progress_refs,
monitor_information_meaning ("Exposed direct relationships and already delivered observations. Empty
measurements/log windows do not assert absence or a stall."), and monitor_goal. `decision_inputs` matches local's
except that it drops shared_information_context and HPC action history and adds waiting_support.

## Tools offered

- `progress.observe`: `{requested_fields, [native_operation]}`. It observes selected exposed fields of the assigned
  target (fields may not widen the assignment) and never traverses dependents.
- `progress.read`: `{progress_ref}`, an already delivered snapshot.
- `progress.log`: `{progress_ref, log_index}`, one retained log window read through `source.read` with byte custody.

Common actions: tool, child, wait and redeliver_report. Wait is not offered for a private-yield BLAST job.

## Credit

- `credit_kind` = `monitoring`.
- `credit_view` = `services.bound_role_credit` (the caller-bound projector).
- `information_credit` = `ProgressInformationCredit(progress_reader, information_unit)`: newly informative received
  snapshot count × information_unit. Repeated identities and timestamps add nothing.

## Continuation

Only when `yield_settings` is configured (`{kind: information_accumulation, cutoff, uncertainty_alpha}`, with an
`information_unit`):

- BLAST job (`target_identity.is_blast_job`: api + ncbi_blast): `blast_monitor_yield` forecasts exact zero once one
  original BLAST status observation of this target is in the contexts, and `STATUS_UNIDENTIFIABLE` until then. This
  corresponds to the **completion-with-a-target** estimator (target = one status observation).
- Otherwise: `_monitor_information_yield` = `estimate_nonnegative_yield` on the credit history, raising if credit
  ever decreases. This corresponds to the **accumulation** estimator.

Both used `YieldController(epoch, initial_credit, cutoff, YieldParameters(uncertainty_alpha))`.

## Report to parent

- Fact sources: monitoring_progress_refs, monitoring_target_handle, monitoring_execution_state,
  monitoring_result_available, monitoring_observed_at_unix_seconds, monitoring_committed_record_refs,
  monitoring_dependency_handles. The values come from the latest delivered snapshot of the assigned target.
- `validate_report`: recorded facts must match, and every referenced record must be of a permitted type and received.
- `required_return_sources`, when the parent is sequence_homology_evidence, comes from the **parent's** own
  `to_child_execution_progress_assessment.required_return_sources(services)` (outside this folder).

## Differences from similar episodes

- It is the only one of these four that may commission a child (itself, for a direct dependency).
- It has its own instruction composer (it does not use the A-root INSTRUCTIONS) and its own prompt renderer.
- Its BLAST-specific continuation (finish after one original status observation) is unique to this episode.
- Compared with execution_result_acquisition: progress information versus result bytes (see that file).

## Per-file table

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| __init__.py | 1 | Empty package marker. | none |
| binding_record.py | 9 | Binding record id `sequence_homology_evidence/execution_progress_assessment`, VERSION `monitor_episode_binding_v1`, configuration outcome_page_size and, when private, information_unit + yield_settings. | none |
| configuration.py | 31 | outcome_page_size (default 32, positive int); optional yield_settings exactly {kind: information_accumulation, cutoff >= 0 finite, uncertainty_alpha in (0,1)} requiring a positive information_unit; role must be `monitor`. | `import:a101.communication` (1) |
| contracts.py | 10 | Assignment contract `monitor_assignment_v1`: target_handle, requested_fields (subset of execution_status, measurements, log_windows, committed_record_refs, dependencies, result_available), known_progress_refs, permitted_committed_record_types; target states pending/executing/returned/admitted. | `import:a101.domain` (1) |
| credit.py | 21 | credit_kind 'monitoring'; credit_view = services.bound_role_credit (caller-bound projector); information_credit = ProgressInformationCredit(progress_reader, information_unit). | `import:a101.library.progress_information_credit` (1), `self.services.bound_role_credit` (1) |
| decision_inputs.py | 71 | As local_job_execution minus shared_information_context and HPC requested_action_history, plus waiting_support when wait is permitted. | `import:a101.episode_work_report` (1), `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.available_child_roles` (1), `self.workflow.binding_context` (2), `self.workflow.episode_bindings` (1), `self.workflow.execution_expectations` (1), `self.workflow.job_episodes` (2), `self.workflow.launch_instructions` (2), `self.workflow.native_estimation_context` (1), `self.workflow.native_event_information` (2), `self.workflow.pending_work` (1), `self.workflow.permits_common_action` (1), `self.workflow.resource_context` (1), `self.workflow.resource_estimator` (4), `self.workflow.store` (2), `self.workflow.waiting_support` (1) |
| decision_state.py | 55 | Identical in content to local_job_execution's decision_state (class name differs). | `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.binding_context` (1), `self.workflow.catalog` (1), `self.workflow.controller_binding` (1), `self.workflow.delivery_status` (1), `self.workflow.extra_report_sources` (1), `self.workflow.job_episode_options` (1), `self.workflow.journal` (3), `self.workflow.knowledge` (1), `self.workflow.local_outcome_preview` (1), `self.workflow.pending_work` (1), `self.workflow.receipt_projection` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_binding` (1), `self.workflow.source_credit_view` (1), `self.workflow.specialist` (1), `self.workflow.store` (3), `self.workflow.tools` (1), `self.workflow.working_state` (1), `table:runtime_actions` (2) |
| episode.py | 57 | Role `monitor` (entry role), commissioning parent `sequence_homology_evidence`, may commission child `monitor` only when the target exposes direct dependencies; permitted actions tool/child/wait/redeliver_report, or without wait for a private-yield BLAST job; required_return_sources from the scientific parent's to_child file when parent is sequence_homology_evidence; prompt renderer render_monitor_prompt. | `import:a101.communication` (1), `import:a101.library.monitor_prompt` (1), `self.services.dependencies` (1) |
| from_child_execution_progress_assessment.py | 20 | receive_progress: validate the child's form, collect its `episode_progress` references (each read through the provider), digest form/schema/scope and admit them into the provider's progress receipt index. | `import:a101.communication` (1), `import:a101.domain` (1), `import:a101.method_loop.durable` (1) |
| from_parent.py | 33 | assignment_schema = contracts._ASSIGNMENT; `_assignment` checks target_handle in scope (execution_handle) and every known_progress_ref belongs to that target; child assignments go through prepare_dependency_request. | `import:a101.communication` (1), `import:a101.domain` (1), `self.services.read_progress` (1), `self.services.reference_in_scope` (1) |
| goal.py | 15 | Own goal text: "Investigate which further exposed progress information is useful for the assigned target. ... Liveness establishes process presence only; elapsed time alone establishes neither productive work nor a stall. Unknown information stays unknown. ... You may explicitly commission an ordinary monitor for one exposed direct dependency ... Return the original parent's typed form at your closure even while the target remains active ..." + credit sentence (private or caller projector) + "Repeated observation identities and read timestamps alone earn no new information." planning_context: objective, target_handle, requested_fields, unresolved_question, progress_definition, yield_settings. | `import:a101.communication` (1) |
| internal_summary.py | 13 | decision_context: monitor_assignment, monitor_target_description, monitor_direct_dependencies, monitor_received_progress_refs, monitor_information_meaning, monitor_goal (planning_context). | `import:a101.communication` (1), `self.services.dependencies` (1) |
| progress_operations.py | 58 | Tools: progress.observe (requested_fields within assignment, optional selected native_operation), progress.read (delivered snapshot), progress.log (one retained log window via source.read with byte custody). Results carry progress_refs and permitted committed record refs. | `import:a101.communication` (1), `import:a101.domain` (1), `import:a101.episode_bindings` (1), `self.services.execute_tool` (1), `self.services.observe_progress` (1), `self.services.read_record` (2) |
| progress_records.py | 16 | UTC timestamp parser and de-duplicating list helper. | `import:a101.domain` (1) |
| received_progress.py | 30 | _received = known_progress_refs + own outcome progress_refs (paged by outcome_page_size) + progress received from children (or services.progress_selection); _snapshot only for received refs. | `import:a101.domain` (1), `self.services.own_outcomes` (1), `self.services.read_progress` (1), `self.services.received_progress_refs` (1) |
| report_delivery.py | 34 | Identical in content to local_job_execution's finish. | `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.binding_context` (1), `self.workflow.episode_bindings` (1), `self.workflow.facts` (1), `self.workflow.journal` (2), `self.workflow.pending_handles` (1), `self.workflow.release` (2), `self.workflow.source_credit_view` (1), `table:runtime_forms` (2) |
| target_identity.py | 10 | is_blast_job: target described as resource_kind api and service ncbi_blast. | none |
| task.py | 188 | As local minus the component/MinHash/reads.map feedback branches and automatic score updates; plus selected wait (carries last observed credit). | `import:a101.episode_source_failure` (1), `import:a101.library.live_runtime_functions` (1), `import:a101.providers` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.action_schema` (1), `self.workflow.completed_unit` (3), `self.workflow.completions` (3), `self.workflow.controller_value` (2), `self.workflow.decision_exchanges` (3), `self.workflow.delivery_resolution_inputs` (1), `self.workflow.execute` (1), `self.workflow.execution_binding` (7), `self.workflow.inprocess_replay` (4), `self.workflow.journal` (7), `self.workflow.last_observed_credit` (1), `self.workflow.next_return` (1), `self.workflow.pending_work` (1), `self.workflow.receive_native_outcome` (1), `self.workflow.receive_outcome` (1), `self.workflow.resolve_pending_deliveries` (1), `self.workflow.resolver` (1), `self.workflow.run_id` (2), `self.workflow.selected` (3), `self.workflow.source_credit_view` (1), `self.workflow.store` (7), `self.workflow.validate_report` (1), `table:runtime_actions` (8), `table:runtime_episodes` (1), `table:runtime_model_calls` (2) |
| task_decision.py | 348 | As local plus own instructions() and decision_completion() that routes the provider call through complete_with_presentation with this binding's decision_prompt_renderer (render_monitor_prompt) when the provider is the original model class; no literature numerical contract freezing. | `import:a101.library.live_runtime_functions` (1), `import:a101.providers` (2), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `import:providers` (1), `name:bind_functions` (2), `self.workflow.contract_information_profile` (1), `self.workflow.contract_information_reply` (1), `self.workflow.controller_binding` (1), `self.workflow.decision_exchanges` (4), `self.workflow.decision_protocol` (3), `self.workflow.execute` (1), `self.workflow.freeze_contract_information` (1), `self.workflow.history_preview` (1), `self.workflow.journal` (3), `self.workflow.numerical_contracts` (1), `self.workflow.provider` (3), `self.workflow.receipts` (4), `self.workflow.run_id` (1), `self.workflow.services` (2), `self.workflow.specialist` (2), `self.workflow.store` (2), `self.workflow.uses_received_record_context` (2), `self.workflow.validate_contract_information` (5), `table:runtime_model_calls` (8) |
| task_instructions.py | 86 | Own instruction composition: monitor goal + action boundary + credit-component + resource-estimate + report guidance + history (exchange or plain) + host execution guidance, tool knowledge, launch instructions, repair, wait and native event guidance. | `self.workflow.binding_context` (1), `self.workflow.decision_protocol` (1), `self.workflow.knowledge` (1), `self.workflow.launch_instructions` (1), `self.workflow.native_event_information` (1), `self.workflow.permits_common_action` (1), `self.workflow.specialist` (1) |
| task_state.py | 115 | Identical in content to local_job_execution's task state (class name differs). | `import:a101.episode_source_failure` (1), `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.archive` (1), `self.workflow.completions` (4), `self.workflow.context` (1), `self.workflow.controller_value` (1), `self.workflow.execution_binding` (4), `self.workflow.grains` (1), `self.workflow.inprocess_replay` (7), `self.workflow.journal` (5), `self.workflow.progress_provider` (2), `self.workflow.recover_commissions` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_view` (1), `self.workflow.store` (2), `table:runtime_actions` (5) |
| to_child_execution_progress_assessment.py | 11 | prepare_dependency_request: child target must be an exposed direct dependency of the parent's target and may not widen permitted_committed_record_types. | `import:a101.domain` (1) |
| to_parent.py | 91 | Fact sources: monitoring_progress_refs, monitoring_target_handle, monitoring_execution_state, monitoring_result_available, monitoring_observed_at_unix_seconds, monitoring_committed_record_refs, monitoring_dependency_handles; facts from latest delivered snapshot of the target; resolve progress/execution handles; validate_report: form equals recorded facts and every referenced record is permitted and received. | `import:a101.communication` (1), `import:a101.domain` (1), `import:a101.episode_bindings` (1), `self.services.read_progress` (3), `self.services.read_record` (2) |
| waiting.py | 31 | _execute_selected_wait (failed outcome on EventTargetError enters the iterator) and suspension_changed. | `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.execution_backend` (1), `self.workflow.execution_handle` (2), `self.workflow.perform_selected_wait` (1) |
| yield_estimator.py | 31 | Private continuation: blast_monitor_yield (exact zero forecast after one observation of the original BLAST status, else unidentifiable) for BLAST jobs; else _monitor_information_yield (estimate_nonnegative_yield on newly informative snapshot credit, raises on decrease); YieldController(cutoff, uncertainty_alpha). | `import:a101.numerical` (3), `name:estimate_nonnegative_yield` (2), `name:NumericBand` (3), `name:STATUS_UNIDENTIFIABLE` (2), `name:YieldController` (2), `name:YieldEstimate` (2), `name:YieldParameters` (2) |

Old-runner names are counted per file: `self.workflow.<member>` (also `source.workflow` and `workflow.` in module functions), `self.services.<member>`, journal/receipt table names, imports from old shared-root modules (`import:<module>`), and old yield/rebinding names (`name:`). No `BindingContext` literal occurs in these files; the old binding context arrives through `self.workflow.binding_context(...)`. The same rows are in `runs/carry_over/calls/a101_02.tsv`.

## Carried over

Written 19 November 2026 (job `u005`, this step). One row per row of `runs/carry_over/functions/a101__sequence_homology_evidence__execution_progress_assessment.tsv`.

| old file | kind | name | classification | new place or reason |
|---|---|---|---|---|
| binding_record.py | class | MonitorBindingRecord | machinery | binding record class: not carried |
| binding_record.py | method | MonitorBindingRecord.as_record | machinery | the binding's own `as_record()`: deleted (README 3d) |
| configuration.py | class | MonitorConfiguration | episode function | `yield_estimator.py` (settings checks), `messages/read_from_parent.py` (`information_unit`) |
| configuration.py | method | MonitorConfiguration.__init__ | episode function | `yield_estimator.py yield_controller` (cutoff and uncertainty_alpha checks over `settings`, `monitor_private_yield_binding_not_enabled`); `messages/read_from_parent.py ASSIGNMENT_FORM` field `information_unit`; `outcome_page_size` dropped (it paged the old `services.own_outcomes`; every outcome is in the view) |
| configuration.py | method | MonitorConfiguration._role | machinery | role dispatch: each role is its own episode now |
| credit.py | class | MonitorEpisodeCredit | episode function | `credit.py` |
| credit.py | method | MonitorEpisodeCredit.credit_kind | machinery | `credit_kind` is deleted (README 3d) |
| credit.py | method | MonitorEpisodeCredit.credit_view | machinery | `services.bound_role_credit`: replaced by `credit.py credit(summary, records)` |
| credit.py | method | MonitorEpisodeCredit.information_credit | episode function | `credit.py information_projection` (calls the library `ProgressInformationCredit`) |
| decision_inputs.py | class | MonitorDecisionInputs | episode function | `task.py decide` |
| decision_inputs.py | method | MonitorDecisionInputs.decision_inputs | episode function | `task.py decide` (launch instruction library and selected sections). Not carried: `resource_context`, `execution_expectations`, `resource_tool_estimates`, `native_execution_expectations` (BLOCKED-ON-JOB-SERVICE: estimate_table), `child_options`, `completed_action_reports`, `pending_work`, `native_event_targets`, `waiting_support`, `contract_information_profile` (old-runner state or gone actions) |
| decision_inputs.py | function | _bind_original_task_runtime_providers | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`): not carried |
| decision_state.py | class | MonitorDecisionState | episode function | `messages/internal_summary.py`, `task.py decide` |
| decision_state.py | method | MonitorDecisionState.decision_state | episode function | `task.py decide` context (goal, credit, controller, tools, last outcome, feedback, time accounting) and `messages/internal_summary.py`. Not carried: runtime_actions reads, report lifecycle and deliveries, pending work, receipt projection, journal views |
| decision_state.py | function | _bind_original_task_runtime_providers | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`): not carried |
| episode.py | class | MonitorEpisode | episode function | `episode.py ExecutionProgressAssessment` |
| episode.py | method | MonitorEpisode.prepare_child_request | episode function | `messages/msg_to_child.py msg_to_child` |
| episode.py | method | MonitorEpisode.receive_child_progress | episode function | `messages/read_from_child.py read_from_child` |
| episode.py | method | MonitorEpisode.child_roles | episode function | `task.py CHILD_SLOTS` (slot `monitor`: this episode's own binding path) |
| episode.py | method | MonitorEpisode.required_return_sources | episode function | the parent's selection: `ExecutionProgressAssessment` declares every fact selectable in `messages/final_to_parent.py RETURN_FORM`; the head selects `monitoring_progress_refs` in its own `msg_to_child` (not this episode's) |
| episode.py | method | MonitorEpisode.permitted_common_actions | machinery | common-action permission (wait, redeliver_report): gone; tool and child are offered by `task.py decide/action`; the old BLAST rule (no wait) has no wait to remove |
| episode.py | method | MonitorEpisode.allowed_children | episode function | `task.py selection_schema` (the `monitor_dependency` option only while the latest observation exposes job dependencies) and `messages/msg_to_child.py` |
| from_child_execution_progress_assessment.py | function | receive_progress | episode function | `messages/read_from_child.py read_from_child` (the provider receipt index, signature digest and operation-key recording are the system's) |
| from_parent.py | class | MonitorAssignment | episode function | `messages/read_from_parent.py` |
| from_parent.py | method | MonitorAssignment.assignment_schema | episode function | `messages/read_from_parent.py ASSIGNMENT_FORM` |
| from_parent.py | method | MonitorAssignment._assignment | episode function | `messages/read_from_parent.py ASSIGNMENT_FORM` and `read_from_parent`; the scope and provider admission part is unplaced (see blocked file) |
| from_parent.py | method | MonitorAssignment.prepare_assignment | episode function | `messages/msg_to_child.py` (the parent side builds the assignment, `prepare_dependency_request` check) and `messages/read_from_parent.py`; the `operation_key` requirement is the system's `ctx.operation_key` |
| goal.py | class | MonitorGoal | episode function | `goal.py` |
| goal.py | method | MonitorGoal.instructions | episode function | `goal.py GOAL` |
| goal.py | method | MonitorGoal.planning_context | episode function | `messages/internal_summary.py` key `monitor_goal`; `task.py decide` adds `yield_settings` |
| internal_summary.py | class | MonitorSummary | episode function | `messages/internal_summary.py` |
| internal_summary.py | method | MonitorSummary.decision_context | episode function | `messages/internal_summary.py` (assignment, direct dependencies, received progress refs, meaning, goal) and `task.py decide` (target description, a recorded `job_access` read) |
| progress_operations.py | class | ProgressOperations | episode function | `task.py` tools |
| progress_operations.py | method | ProgressOperations.catalog | episode function | `task.py catalog` |
| progress_operations.py | method | ProgressOperations.execute | episode function | `task.py progress_observe`, `progress_read`, `progress_log` (tools), `_tool_call` and `action`; `native_operation` raises (unplaced) |
| progress_records.py | function | _timestamp | episode function | `messages/final_to_parent.py _timestamp_seconds` (library candidate) |
| progress_records.py | function | _unique | episode function | `messages/internal_summary.py _unique` (library candidate) |
| received_progress.py | class | ReceivedProgress | episode function | `messages/internal_summary.py` |
| received_progress.py | method | ReceivedProgress._received | episode function | `messages/internal_summary.py` (`monitor_received_progress_refs`); `services.progress_selection` and `services.received_progress_refs` are provider reads: not carried |
| received_progress.py | method | ReceivedProgress._snapshot | episode function | `task.py _tool_call` (only a received ref has a snapshot) |
| received_progress.py | class | OwnProgress | episode function | `messages/internal_summary.py` |
| received_progress.py | method | OwnProgress._own_progress_refs | episode function | `messages/internal_summary.py` (the progress refs of `view.outcomes`; no paging) |
| report_delivery.py | class | MonitorReportDelivery | episode function | `messages/final_to_parent.py` |
| report_delivery.py | method | MonitorReportDelivery.finish | episode function | `messages/final_to_parent.py final_to_parent` (the recorded facts of the result); `runtime_forms`, `form_with_facts`, `pending_handles`, `release`: machinery, not carried |
| report_delivery.py | function | _bind_original_task_runtime_providers | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`): not carried |
| target_identity.py | function | is_blast_job | episode function | `messages/read_from_parent.py is_blast_job` (library candidate; reads the assignment's `target_description`) |
| task.py | class | ProgressMonitoringTask | episode function | `task.py` (`decide`, `action`, tools); the decision machine around it is machinery |
| task.py | method | ProgressMonitoringTask.next | machinery | decision loop, journal replay, source failure, completion slots, redelivery: the system's; the model request is `task.py decide` |
| task.py | method | ProgressMonitoringTask.apply_response | episode function | `task.py action` (decode, validate against the selection schema, `Rejected(feedback)`); the report_update, journal and receipt parts are machinery |
| task.py | method | ProgressMonitoringTask.execute | machinery | unit execution and recording (`runtime_actions`, `receive_outcome`, completions, wait): the system's; the tools are in `task.py` |
| task.py | function | _bind_original_task_runtime_providers | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`): not carried |
| task_decision.py | class | MonitorTaskDecision | episode function | `task.py` (`decide`, `instructions`) |
| task_decision.py | method | MonitorTaskDecision.call | machinery | model call recording (`runtime_model_calls`, `journal.measure`, receipts): the system's |
| task_decision.py | method | MonitorTaskDecision.instructions | episode function | `task.py instructions` |
| task_decision.py | method | MonitorTaskDecision.decision_completion | machinery | provider patching and presentation routing: not carried; the prompt renderer `render_monitor_prompt` has no home now (unplaced); `decide` renders its own context |
| task_decision.py | method | MonitorTaskDecision.conversation_key | machinery | conversation state: deleted (README 3a) |
| task_decision.py | method | MonitorTaskDecision.interpretation_context | machinery | decision-exchange loop: not carried |
| task_decision.py | method | MonitorTaskDecision.exchange_schema | machinery | decision-exchange loop: not carried |
| task_decision.py | method | MonitorTaskDecision.exchange_response | machinery | decision-exchange loop: not carried |
| task_decision.py | method | MonitorTaskDecision.validate_contract_exchange_request | machinery | saved-request check: deleted |
| task_decision.py | method | MonitorTaskDecision.validate_contract_exchange_history | machinery | saved-request check: deleted |
| task_decision.py | method | MonitorTaskDecision.exchange_decision | machinery | decision-exchange loop: not carried |
| task_decision.py | function | _bind_original_task_runtime_providers | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`): not carried |
| task_instructions.py | function | instructions | episode function | `task.py instructions` (goal, action boundary, credit-component guidance, host-execution guidance, tool-knowledge and launch texts). Not carried: report, history, repair, wait and native-event guidance (describe gone actions), the resource-estimate guidance (BLOCKED-ON-JOB-SERVICE: estimate_table) |
| task_state.py | class | MonitorTaskState | machinery | task state, checkpoint and restore: the system's |
| task_state.py | method | MonitorTaskState.__init__ | machinery | task state: not carried |
| task_state.py | method | MonitorTaskState.bind_execution_context | machinery | old runner context binding |
| task_state.py | method | MonitorTaskState.record_execution_failure | machinery | failure recording: a tool returns its failure (README 3a) |
| task_state.py | method | MonitorTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | method | MonitorTaskState.restore | machinery | checkpoint/restore |
| task_state.py | method | MonitorTaskState.record_effect | machinery | `record_effect`: recording |
| task_state.py | method | MonitorTaskState.checkpoint | machinery | checkpoint/restore |
| task_state.py | function | _bind_original_task_runtime_providers | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`): not carried |
| to_child_execution_progress_assessment.py | function | prepare_dependency_request | episode function | `messages/msg_to_child.py msg_to_child` (the two refusals are raised while the commission is built) |
| to_parent.py | class | MonitorReport | episode function | `messages/final_to_parent.py` |
| to_parent.py | method | MonitorReport.fact_sources | episode function | `messages/final_to_parent.py RETURN_FORM` fields and `REPORT_SCHEMAS` |
| to_parent.py | method | MonitorReport.facts | episode function | `messages/final_to_parent.py monitor_facts` and `final_to_parent` |
| to_parent.py | method | MonitorReport.resolve | episode function | `messages/final_to_parent.py _resolver` (the `reference_in_context` fallback has no home: unplaced) |
| to_parent.py | method | MonitorReport.validate_report | episode function | `messages/final_to_parent.py validate_report`, called by `final_to_parent` before it returns |
| waiting.py | class | MonitorWaiting | machinery | wait/suspension machinery: not carried |
| waiting.py | method | MonitorWaiting._execute_selected_wait | machinery | wait machinery (`perform_selected_wait`): the system has no wait |
| waiting.py | method | MonitorWaiting.suspension_changed | machinery | suspension machinery |
| waiting.py | function | _bind_original_task_runtime_providers | machinery | provider patching (`_bind_original_task_runtime_providers`, `bind_functions`): not carried |
| yield_estimator.py | function | _monitor_information_yield | episode function | `yield_estimator.py yield_controller` (accumulation controller, README 7b); the raise on decrease is in `credit.py credit` |
| yield_estimator.py | function | blast_monitor_yield | episode function | `yield_estimator.py yield_controller` (completion controller, target = information unit, README 7b) |
| yield_estimator.py | class | MonitorEpisodeYield | episode function | `yield_estimator.py` |
| yield_estimator.py | method | MonitorEpisodeYield.yield_controller | episode function | `yield_estimator.py yield_controller` |
