# a102 / structural_homology_evidence / execution_progress_assessment

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/execution_progress_assessment/<file>`. I read only the files directly in this folder. It has no `grading/` or `scoring/` subfolder.

## Purpose (its own words)
"Investigate which further exposed progress information is useful for the assigned target. Use actual status, measured quantities, committed references and source-bound logs. Liveness establishes process presence only; elapsed time alone establishes neither productive work nor a stall. Unknown information stays unknown. ... You may explicitly commission an ordinary monitor for one exposed direct dependency; no descendant traversal, fanout, cadence or depth is prescribed. Return the original parent's typed form at your closure even while the target remains active. ... Repeated observation identities and read timestamps alone earn no new information." (`goal.py`)

## Task and instructions
- Role `monitor`, which is also an entry role. Its commissioning parent is `structural_homology_evidence`.
- Instructions (`task_instructions.py`) are the goal plus this episode's own blocks:
  - ACTION_BOUNDARY: no stop action, budget, approval review, quality gate or invented observation;
  - credit-component guidance;
  - resource-estimate guidance: a timing experiment earns monitoring credit for timing learned;
  - report guidance: return only the parent's typed form, plus redelivery rules;
  - history guidance, or exchange-history guidance under decision exchange;
  - host-execution, repair, wait and native-event guidance.
- `planning_context`: objective, target handle, requested fields, the unresolved question "Which exposed progress information would improve the original requested report?", progress definition, yield settings.

## What it reads from its parent's assignment
- `monitor_assignment_v1` (`contracts.py`): `target_handle`, `requested_fields` (subset of execution_status, measurements, log_windows, committed_record_refs, dependencies, result_available), `known_progress_refs`, `permitted_committed_record_types`.
- The target must be in scope as an `execution_handle`. Every known progress ref must belong to that target (`from_parent.py`).
- When commissioned by `structural_homology_evidence`, the required return sources come from the parent's own `to_child_execution_progress_assessment.required_return_sources(services)`.

## Children
- Self-nesting `monitor`. It is allowed only when `services.dependencies(target)` exposes direct dependencies (`episode.py`).
- Sends (`to_child_execution_progress_assessment.py`): a monitor assignment. Its `target_handle` must be one of this target's exposed direct dependencies, and its `permitted_committed_record_types` must be a subset of its own.
- Takes back (`from_child_execution_progress_assessment.py`): the child's typed form. Each `episode_progress` reference is read through the provider and admitted into this episode's received progress, signed by form/schema/scope.

## Decision state shown to the model
- The generic decision state (`decision_state.py`) plus `internal_summary.decision_context`:
  - `monitor_assignment`;
  - `monitor_target_description` from `services.describe_progress_target`;
  - `monitor_direct_dependencies`;
  - `monitor_received_progress_refs`;
  - `monitor_information_meaning`: empty measurements or logs do not assert absence or a stall;
  - `monitor_goal` (the planning context).
- `decision_inputs` adds resource context, the launch-instruction library, child options, completed action reports, pending work, `monitor` execution expectations, estimates and waiting support.
- Renderer: `render_monitor_prompt`. It is always used when the provider supports presentation, with no context gating.

## Tools
- `progress.observe`: selected fields, which cannot expand the assigned fields, plus an optional `native_operation` from the target's `selected_observation_schema`. It calls `services.observe_progress`.
- `progress.read`: a received observation.
- `progress.log`: one retained log window, read through `source.read` with source/artifact byte custody.
- Common actions: `tool`, `child`, `wait`, `redeliver_report`. There is no `reason` action in the execute path.

## Credit
- Kind `monitoring`. `credit_view` is the caller-bound `services.bound_role_credit(context, selection)`.
- `information_credit` selects `ProgressInformationCredit(progress_reader, information_unit)`: newly informative received snapshot count × `information_unit`. Repeated identities and timestamps earn nothing.
- Credit history must not decrease (`monitor_information_credit_cannot_decrease`).

## Continuation
- Optional private yield binding: `yield_settings = {kind: 'information_accumulation', cutoff >= 0, uncertainty_alpha in (0,1)}` plus `information_unit > 0`.
- Old estimator: `estimate_nonnegative_yield` with binding `monitor_information_accumulation_v1`. It forecasts the next action's information credit and stops when the predicted upper gain is at or below the cutoff. This maps to the new **accumulation** yield estimator.

## Report to parent
- Fact sources:
  - `monitoring_progress_refs` (episode_progress refs);
  - `monitoring_target_handle`;
  - `monitoring_execution_state`, the lifecycle state of the latest target observation, or null;
  - `monitoring_result_available`;
  - `monitoring_observed_at_unix_seconds`;
  - `monitoring_committed_record_refs`, permitted types only;
  - `monitoring_dependency_handles`.
- `validate_report`: fact fields must match. Every record reference in the form must be a permitted, received committed record (`monitor_record_not_permitted_or_received`).

## Differences visible
- Compared with the results and local siblings:
  - credit is projected by the caller (`bound_role_credit`), not computed from own receipts;
  - it self-nests;
  - it permits `child` and `wait`;
  - its decision call never freezes literature numerical contracts and has no `is_job_source` receipt guard;
  - its task `execute` has no `reason` branch;
  - presentation is unconditional.
- `hpc_work_planning` receives this episode's progress forms with an identical receiver function.

## File by file

Old-runner names column: `imp:` = `import gene_annotation_episode.episodic_workflow.root.a102.<module>` (old runner or old shared non-episode module; see runs/placement_plan/placement.tsv and runs/placement_merge/plan.tsv for where non-episode modules went). `runtime.X` = name used through `_live_original_runtime` (root.a102.runtime). `table:` = old journal/receipt SQLite table. ×N = number of uses. Per-use detail: runs/carry_over/calls/a102_02.tsv.

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| __init__.py | 1 | Empty package marker. | none |
| binding_record.py | 9 | Binding identity `structural_homology_evidence/execution_progress_assessment`, version `monitor_episode_binding_v1`, configuration: `outcome_page_size`, and when a private yield is bound `information_unit` + `yield_settings`. | none |
| configuration.py | 31 | Constructor: `outcome_page_size` (positive int, default 32); optional `yield_settings` must be exactly `{kind: information_accumulation, cutoff >= 0, uncertainty_alpha in (0,1)}` and then requires a positive `information_unit`. `_role` accepts only `monitor`. | imp:communication×1 |
| contracts.py | 10 | `VERSION`, FIELDS (`execution_status`, `measurements`, `log_windows`, `committed_record_refs`, `dependencies`, `result_available`), states (pending/executing/returned/admitted), assignment schema `monitor_assignment_v1`: `target_handle`, `requested_fields`, `known_progress_refs`, `permitted_committed_record_types`. | imp:domain×1 |
| credit.py | 21 | Credit kind `monitoring`; `credit_view` delegated to the caller-bound `services.bound_role_credit`; `information_credit` selects `ProgressInformationCredit(progress_reader, information_unit)` (newly informative received snapshots × unit). | imp:library.progress_information_credit×1, ProgressInformationCredit×2, self.services.bound_role_credit×1 |
| decision_inputs.py | 49 | Adds to the saved decision: resource context, launch-instruction library, child options, initial binding context, completed action reports, pending work, `monitor` execution expectations, resource/native estimates, waiting support, contract profile. No shared_information_context, no HPC requested-action history (differs from the results/local copies). | imp:episode_work_report×1, imp:runtime×2, runtime.child_option_information×1, runtime.Mapping×1, self.workflow.available_child_roles×1, self.workflow.binding_context×1, self.workflow.episode_bindings×1, self.workflow.execution_expectations×1, self.workflow.launch_instructions×2, self.workflow.native_estimation_context×1, self.workflow.pending_work×1, self.workflow.permits_common_action×1, self.workflow.resource_context×1, self.workflow.resource_estimator×4, self.workflow.waiting_support×1 |
| decision_state.py | 44 | Generic decision-state assembly (same fields as the other episodes, annotation-axis branches inert) then specialist `decision_context`. | imp:runtime×2, runtime.FACT_MEANINGS×1, runtime.FACT_SOURCES×1, runtime.json×2, runtime.Mapping×3, runtime._plain×2, runtime._references_in×1, self.workflow.binding_context×1, self.workflow.catalog×1, self.workflow.controller_binding×1, self.workflow.delivery_status×1, self.workflow.extra_report_sources×1, self.workflow.job_episode_options×1, self.workflow.journal×3, self.workflow.knowledge×1, self.workflow.local_outcome_preview×1, self.workflow.pending_work×1, self.workflow.receipt_projection×1, self.workflow.run_id×1, self.workflow.source_credit_binding×1, self.workflow.source_credit_view×1, self.workflow.specialist×1, self.workflow.store×3, self.workflow.tools×1, self.workflow.working_state×1, table:runtime_actions×2 |
| episode.py | 54 | `MonitorEpisode`: `binding_path structural_homology_evidence/execution_progress_assessment`, `commissioning_parent structural_homology_evidence`, roles/entry_roles `('monitor',)`, decision source `ProgressMonitoringTask`, renderer `render_monitor_prompt`. Self-nesting child role `monitor`, only when the target exposes direct dependencies. Common actions `tool, child, wait, redeliver_report`. `required_return_sources` from the parent's own to_child file when commissioned by `structural_homology_evidence`. `receive_child_progress` admits the child's progress refs. | imp:communication×1, imp:library.monitor_prompt×1, self.services.dependencies×1 |
| from_child_execution_progress_assessment.py | 20 | Receiving a recursive monitor child's form: validate it, collect `episode_progress` references (each read through the provider), sign form/schema/scope and `_receive_progress` into the received progress index. | imp:communication×1, imp:domain×1, imp:method_loop.durable×1 |
| from_parent.py | 33 | Assignment schema = `_ASSIGNMENT`; `_assignment` requires the target handle in scope (`execution_handle`) and every known progress ref to belong to that target; `prepare_assignment` needs an operation key and, when the parent is itself a monitor, applies the dependency rule. | imp:communication×1, imp:domain×1, self.services.read_progress×1, self.services.reference_in_scope×1 |
| goal.py | 15 | Goal text: investigate which further exposed progress information is useful for the assigned target; liveness is presence only; elapsed time alone is neither progress nor stall; unknown stays unknown; may commission a monitor for one exposed direct dependency, no traversal/fan-out/cadence/depth prescribed; return the parent's typed form at closure even while the target is active; repeated observation identities and timestamps earn nothing. `planning_context`: objective, target, requested fields, unresolved question, progress definition, yield settings. | imp:communication×1 |
| internal_summary.py | 13 | Decision context: monitor assignment, target description, direct dependencies, received progress refs, meaning note (empty measurements/logs do not assert absence or stall), monitor goal. | imp:communication×1, self.services.dependencies×1, self.services.describe_progress_target×1 |
| progress_operations.py | 58 | Tools: `progress.observe` (subset of requested fields, optional selected `native_operation` schema from the target descriptor), `progress.read` (a received observation), `progress.log` (one retained log window with source/artifact custody, via `source.read`). Committed refs filtered by permitted record types; invalid arguments return status `invalid` with feedback. | imp:communication×1, imp:domain×1, imp:episode_bindings×1, self.services.describe_progress_target×1, self.services.execute_tool×1, self.services.observe_progress×1, self.services.read_record×2 |
| progress_records.py | 16 | `_timestamp` (UTC ISO required) and `_unique`. | imp:domain×1 |
| received_progress.py | 30 | `_received`: progress refs = services selection, or assignment known refs + own outcomes' progress refs + services received refs; `_snapshot` only for received refs; `_own_progress_refs` pages own outcomes by `outcome_page_size`. | imp:domain×1, self.services.own_outcomes×1, self.services.progress_selection×1, self.services.read_progress×1, self.services.received_progress_refs×1 |
| report_delivery.py | 25 | Generic `finish` (form saved once in `runtime_forms`). | imp:library.private_policy_call×1, imp:library.report_fact_assembly×1, imp:runtime×2, runtime.form_with_facts×1, runtime._json×2, runtime.json×1, runtime.Record×2, self.workflow.binding_context×1, self.workflow.episode_bindings×1, self.workflow.facts×1, self.workflow.journal×2, self.workflow.pending_handles×1, self.workflow.release×2, self.workflow.source_credit_view×1, table:runtime_forms×2 |
| task.py | 182 | `ProgressMonitoringTask.next/apply_response/execute`: generic loop with grain `monitor`; no `reason` action branch in execute (only wait and tool); no job_child failure branch. | imp:episode_source_failure×1, imp:library.action_contracts×1, imp:library.private_policy_call×1, imp:providers×1, imp:runtime×2, runtime.ActionFailure×1, runtime.ContractInformationError×1, runtime._decode_recorded_action_response×1, runtime.Draft202012Validator×2, runtime.EventTargetError×2, runtime.inspect×1, runtime._json×5, runtime.json×8, runtime.nullcontext×5, runtime.observes_action_outcome×1, runtime.ReportBoundaryError×1, runtime.ReportRedelivery×2, runtime.schema_failure_diagnostic×1, runtime.SourceEnd×2, runtime.validate_form×1, runtime.ValidationError×2, runtime._wait_target_feedback×2, runtime.WorkflowError×2, self.workflow.action_schema×1, self.workflow.completed_unit×3, self.workflow.completions×3, self.workflow.controller_value×2, self.workflow.decision_exchanges×3, self.workflow.delivery_resolution_inputs×1, self.workflow.execute×1, self.workflow.execution_binding×7, self.workflow.inprocess_replay×4, self.workflow.journal×7, self.workflow.last_observed_credit×1, self.workflow.next_return×1, self.workflow.pending_work×1, self.workflow.perform_selected_wait×1, self.workflow.receive_native_outcome×1, self.workflow.receive_outcome×1, self.workflow.resolve_pending_deliveries×1, self.workflow.resolver×1, self.workflow.run_id×2, self.workflow.selected×3, self.workflow.source_credit_view×1, self.workflow.store×7, self.workflow.validate_report×1, table:runtime_actions×8, table:runtime_episodes×1, table:runtime_model_calls×2 |
| task_decision.py | 299 | `call`, `complete_decision` (always uses `complete_with_presentation` with this renderer when available - no context gating, unlike local/results), exchange protocol helpers; no literature numerical freezing; receipts skip only `uses_received_record_context` (no `is_job_source` check). | imp:runtime×2, runtime._action_generation_schema×2, runtime.apply_state_frame×1, runtime._ASSIGNMENT_TRANSPORT×1, runtime._category_yield_parameters×1, runtime.child_option_information×1, runtime.composition_lookup_schema×2, runtime.CONTRACT_INFORMATION_OPERATIONS×1, runtime.DECISION_CONTEXT_VERSION×2, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest×1, runtime.Draft202012Validator×1, runtime.instructional_model_context×4, runtime.is_contract_information×1, runtime._json×14, runtime.json×3, runtime.lookup_attempts×1, runtime.Mapping×3, runtime.model_snapshot×2, runtime._object×3, runtime._plain×2, runtime._recorded_action_generation_schema×1, runtime._recorded_assignment_transport×1, runtime._references_in×1, runtime.requested_contract_information×2, runtime.schema_failure_diagnostic×2, runtime.sqlite3×1, runtime.state_frame×1, runtime.ValidationError×5, runtime.WorkflowError×14, runtime.yield_table×1, self.workflow.contract_information_profile×1, self.workflow.contract_information_reply×1, self.workflow.controller_binding×1, self.workflow.decision_exchanges×4, self.workflow.decision_protocol×3, self.workflow.execute×1, self.workflow.freeze_contract_information×1, self.workflow.history_preview×1, self.workflow.journal×3, self.workflow.numerical_contracts×1, self.workflow.provider×3, self.workflow.receipts×4, self.workflow.run_id×1, self.workflow.services×2, self.workflow.specialist×1, self.workflow.store×2, self.workflow.uses_received_record_context×2, self.workflow.validate_contract_information×5, table:runtime_model_calls×8 |
| task_instructions.py | 86 | This episode's own instruction blocks: ACTION_BOUNDARY (no stop action, no invented budgets/gates), CREDIT_COMPONENT_GUIDANCE, RESOURCE_ESTIMATE_GUIDANCE (timing experiment earns monitoring credit for timing learned), REPORT_GUIDANCE, HISTORY/EXCHANGE_HISTORY guidance, HOST_EXECUTION_GUIDANCE, REPAIR, WAIT, NATIVE_EVENT. Composed after the specialist goal. | self.workflow.binding_context×1, self.workflow.decision_protocol×1, self.workflow.knowledge×1, self.workflow.launch_instructions×1, self.workflow.native_event_information×1, self.workflow.permits_common_action×1, self.workflow.specialist×1 |
| task_state.py | 108 | Generic decision-source state; `record_execution_failure` covers `tool` and `reason` actions. | imp:episode_source_failure×1, imp:runtime×2, runtime.ActionLeaf×1, runtime.EFFECT_VERSION×1, runtime.Episode×1, runtime.interpretation_schema×1, runtime._json×2, runtime.json×4, runtime._object×1, runtime._plain×1, runtime.Record×1, self.workflow.archive×1, self.workflow.completions×4, self.workflow.context×1, self.workflow.controller_value×1, self.workflow.execution_binding×4, self.workflow.grains×1, self.workflow.inprocess_replay×7, self.workflow.journal×5, self.workflow.progress_provider×2, self.workflow.recover_commissions×1, self.workflow.run_id×1, self.workflow.source_credit_view×1, self.workflow.store×2, table:runtime_actions×5 |
| to_child_execution_progress_assessment.py | 11 | Commissioning the recursive monitor child: the child's target must be one of the parent's exposed direct dependencies and its permitted record types must not exceed the parent's. | imp:domain×1, self.services.dependencies×1 |
| to_parent.py | 91 | Fact sources: `monitoring_progress_refs`, `monitoring_target_handle`, `monitoring_execution_state`, `monitoring_result_available`, `monitoring_observed_at_unix_seconds`, `monitoring_committed_record_refs`, `monitoring_dependency_handles`; `facts` from the latest received target observation; `resolve` for progress/handles; `validate_report` requires fact fields to match and every record ref to be a permitted, received committed record. | imp:communication×1, imp:domain×1, imp:episode_bindings×1, self.services.read_progress×3, self.services.read_record×2 |
| waiting.py | 9 | `suspension_changed` on the old execution backend. | self.workflow.execution_backend×1, self.workflow.execution_handle×2 |
| yield_estimator.py | 23 | `_monitor_information_yield`: credit history must be non-decreasing; `estimate_nonnegative_yield` with binding `monitor_information_accumulation_v1` (forecast next action's information credit; stop when predicted upper gain at or below cutoff). `yield_controller` needs the private binding: `YieldController(epoch, initial_credit, cutoff, YieldParameters(uncertainty_alpha))`. | estimate_nonnegative_yield×2, imp:numerical×2, YieldController×2, YieldParameters×2 |

## Carried over

Source read with `git show 97308b94c:<path>` (git dir `/home/chia/repos/gene_annotation_episode_disk/.git`). One row per old function, class and method (`runs/carry_over/functions/a102__structural_homology_evidence__execution_progress_assessment.tsv`). "machinery" rows are not carried; "episode function" rows name the new place (file and name, or library path). The new files: `goal.py`, `task.py`, `credit.py`, `yield_estimator.py`, `episode.py`, `messages/{read_from_parent,msg_to_child,read_from_child,internal_summary,final_to_parent}.py` under `gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/execution_progress_assessment/`. Progress snapshots are carried in tool outcomes and the summary (credit reads them from the summary); the job service is `job_access` (BLOCKED-ON-JOB-SERVICE, see `carry_over_blocked/a102__structural_homology_evidence__execution_progress_assessment.md`).

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | MonitorBindingRecord (class) | machinery | the binding's own as_record() (README 3e) |
| binding_record.py | MonitorBindingRecord.as_record (method) | machinery | the binding's own as_record(); the credit projector's as_record() is episode content and is called in the library |
| configuration.py | MonitorConfiguration (class) | episode function | values the run sets: settings cost and parameters (yield_estimator.py), information_unit (messages/read_from_parent.py ASSIGNMENT_FORM and credit.py) |
| configuration.py | MonitorConfiguration.__init__ (method) | episode function | yield settings kind/cutoff/uncertainty_alpha -> settings cost and parameters read in yield_estimator.py (the controller validates them); information_unit -> read_from_parent.py (new assignment field); services/outcome_page_size/tool registry: machinery |
| configuration.py | MonitorConfiguration._role (method) | machinery | role check; each role is its own episode |
| credit.py | MonitorEpisodeCredit (class) | episode function | credit.py |
| credit.py | MonitorEpisodeCredit.credit_kind (method) | machinery | credit kind label of the old services.bound_role_credit |
| credit.py | MonitorEpisodeCredit.credit_view (method) | episode function | credit.py: credit(summary, records); the caller-bound projector is the library ProgressInformationCredit over the summary's snapshots |
| credit.py | MonitorEpisodeCredit.information_credit (method) | episode function | credit.py: ProgressInformationCredit(SummaryProgress(summary snapshots), information_unit=summary[information_unit]); already in library: episode_support/grading/structural_homology_evidence/progress_information_credit.py |
| decision_inputs.py | MonitorDecisionInputs (class) | episode function | task.py decide |
| decision_inputs.py | MonitorDecisionInputs.decision_inputs (method) | episode function | task.py decide (launch instruction library and selected instructions, child_options, execution expectations: optional settings); resource_context, completed_action_reports, pending_work, resource_estimator/native estimates, waiting_support: old-runner workflow state, not carried |
| decision_state.py | MonitorDecisionState (class) | episode function | messages/internal_summary.py and task.py decide |
| decision_state.py | MonitorDecisionState.decision_state (method) | episode function | messages/internal_summary.py (view-derived fields: goal, received progress, outcome history, controller yield table) and task.py decide (tools, credit-free context, time_accounting); journal reads (working_state, visual_evidence, delivery_status, report lifecycle, elapsed_view): machinery |
| episode.py | MonitorEpisode (class) | episode function | episode.py: class ExecutionProgressAssessment(EpisodeBinding) |
| episode.py | MonitorEpisode.child_roles (method) | episode function | task.py CHILD_SLOTS = {monitor: own binding path} |
| episode.py | MonitorEpisode.required_return_sources (method) | episode function | messages/final_to_parent.py RETURN_FORM (monitoring_progress_refs selectable) and messages/msg_to_child.py selection; the conditional on the parent annotation task cannot be expressed in a form |
| episode.py | MonitorEpisode.permitted_common_actions (method) | machinery | tool and child are the system's two action kinds; wait is the tool wait_for_events in task.py; redeliver_report is report-delivery machinery |
| episode.py | MonitorEpisode.allowed_children (method) | episode function | task.py action (child offered only when direct dependencies are exposed: selection_schema) and decide |
| episode.py | MonitorEpisode.prepare_child_request (method) | episode function | task.py action (dependency and record-type checks) and messages/msg_to_child.py |
| episode.py | MonitorEpisode.receive_child_progress (method) | episode function | messages/read_from_child.py read_from_child |
| from_child_execution_progress_assessment.py | receive_progress (function) | episode function | messages/read_from_child.py read_from_child (provider read of each reference replaced by the snapshots the child returns); _receive_progress ledger/recorded receipts: machinery |
| from_parent.py | MonitorAssignment (class) | episode function | messages/read_from_parent.py |
| from_parent.py | MonitorAssignment.assignment_schema (method) | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and ASSIGNMENT_SCHEMA |
| from_parent.py | MonitorAssignment._assignment (method) | episode function | messages/read_from_parent.py read_from_parent (schema, known-snapshot target match); target in scope: task.py decide via job_access (BLOCKED-ON-JOB-SERVICE) |
| from_parent.py | MonitorAssignment.prepare_assignment (method) | episode function | messages/msg_to_child.py msg_to_child (dependency branch); operation_key requirement: machinery |
| goal.py | MonitorGoal (class) | episode function | goal.py constants; instruction text in task.py |
| goal.py | MonitorGoal.instructions (method) | episode function | task.py GOAL_INSTRUCTIONS (private yield binding variant) |
| goal.py | MonitorGoal.planning_context (method) | episode function | messages/internal_summary.py summary[goal] and task.py decide monitor_goal (yield_settings from ctx.settings) |
| internal_summary.py | MonitorSummary (class) | episode function | messages/internal_summary.py |
| internal_summary.py | MonitorSummary.decision_context (method) | episode function | messages/internal_summary.py internal_summary and task.py decide (target description and direct dependencies are recorded service reads: BLOCKED-ON-JOB-SERVICE) |
| progress_operations.py | ProgressOperations (class) | episode function | task.py TOOLS |
| progress_operations.py | ProgressOperations.catalog (method) | episode function | task.py tool_catalog and selection_schema |
| progress_operations.py | ProgressOperations.execute (method) | episode function | task.py progress_observe, progress_read, progress_log (invalid outcomes returned as units); native_observation_options: not placed (raises) |
| progress_records.py | _timestamp (function) | episode function | messages/final_to_parent.py _timestamp_seconds (private copy) - library candidate |
| progress_records.py | _unique (function) | episode function | messages/internal_summary.py _unique (private copy) - library candidate |
| received_progress.py | ReceivedProgress (class) | episode function | messages/internal_summary.py |
| received_progress.py | ReceivedProgress._received (method) | episode function | messages/internal_summary.py: received = baseline + own + child-delivered refs; services.progress_selection/received_progress_refs ledger: machinery |
| received_progress.py | ReceivedProgress._snapshot (method) | episode function | task.py _received_snapshot (the check that a reference was received) |
| received_progress.py | OwnProgress (class) | episode function | messages/internal_summary.py |
| received_progress.py | OwnProgress._own_progress_refs (method) | episode function | messages/internal_summary.py: own refs from view.outcomes (services.own_outcomes paging: machinery) |
| report_delivery.py | MonitorReportDelivery (class) | episode function | messages/final_to_parent.py |
| report_delivery.py | MonitorReportDelivery.finish (method) | episode function | messages/final_to_parent.py final_to_parent (credit and recorded facts, validate_report before the result); runtime_forms save, form_with_facts, release, pending_handles: machinery |
| task.py | ProgressMonitoringTask (class) | episode function | task.py decide and action |
| task.py | ProgressMonitoringTask.next (method) | episode function | task.py decide (model request over the summary); source_failed/SourceEnd, in-process replay, completions slot, resolve_pending_deliveries, delivery_resolution, apply_response transaction wrapping: machinery |
| task.py | ProgressMonitoringTask.apply_response (method) | episode function | task.py action (decode, validate, Rejected); report_update admission, ReportRedelivery, record_effect: machinery |
| task.py | ProgressMonitoringTask.execute (method) | episode function | task.py TOOLS (tool selection) and wait_for_events (wait selection); journal save/measure, receive_native_outcome, receive_outcome, last_observed_credit, completions.stage, checkpoint, ActionFailure: machinery |
| task_decision.py | MonitorTaskDecision (class) | episode function | task.py decide |
| task_decision.py | MonitorTaskDecision.call (method) | machinery | model call and its journal rows; decide returns ModelRequest |
| task_decision.py | MonitorTaskDecision.instructions (method) | episode function | task.py instructions |
| task_decision.py | MonitorTaskDecision.complete_decision (method) | machinery | model call with presentation; decide returns ModelRequest |
| task_decision.py | MonitorTaskDecision.conversation_key (method) | machinery | provider conversation key |
| task_decision.py | MonitorTaskDecision.interpretation_context (method) | machinery | report_update interpretation schema (report_form machinery) |
| task_decision.py | MonitorTaskDecision.exchange_schema (method) | machinery | decision-exchange loop |
| task_decision.py | MonitorTaskDecision.exchange_response (method) | machinery | decision-exchange loop |
| task_decision.py | MonitorTaskDecision.validate_contract_exchange_request (method) | machinery | decision-exchange loop |
| task_decision.py | MonitorTaskDecision.validate_contract_exchange_history (method) | machinery | decision-exchange loop |
| task_decision.py | MonitorTaskDecision.exchange_decision (method) | machinery | decision-exchange loop |
| task_instructions.py | instructions (function) | episode function | task.py instructions (goal, action boundary, credit components, host execution, tool-knowledge, launch library, native events); resource-estimate, report, history, repair, wait-on-pending-child paragraphs describe machinery not carried |
| task_state.py | MonitorTaskState (class) | machinery | checkpoint/restore state |
| task_state.py | MonitorTaskState.__init__ (method) | machinery | checkpoint/restore state |
| task_state.py | MonitorTaskState.bind_execution_context (method) | machinery | execution context binding |
| task_state.py | MonitorTaskState.record_execution_failure (method) | machinery | journal runtime_actions failure rows |
| task_state.py | MonitorTaskState.restore_checkpoint (method) | machinery | checkpoint/restore |
| task_state.py | MonitorTaskState.restore (method) | machinery | checkpoint/restore |
| task_state.py | MonitorTaskState.record_effect (method) | machinery | journal rows |
| task_state.py | MonitorTaskState.checkpoint (method) | machinery | checkpoint/restore |
| to_child_execution_progress_assessment.py | prepare_dependency_request (function) | episode function | task.py action (target must be an exposed direct dependency; permitted record types must not exceed the parent's) and messages/msg_to_child.py |
| to_parent.py | MonitorReport (class) | episode function | messages/final_to_parent.py |
| to_parent.py | MonitorReport.fact_sources (method) | episode function | messages/final_to_parent.py RETURN_FORM (seven monitoring_* fields under the old names, selectable) plus monitoring_progress_snapshots |
| to_parent.py | MonitorReport.facts (method) | episode function | messages/final_to_parent.py monitor_facts |
| to_parent.py | MonitorReport.resolve (method) | machinery | reference resolution for the old report-form validation (validate_form); the received-reference and committed-record checks it served are in validate_report |
| to_parent.py | MonitorReport.validate_report (method) | episode function | messages/final_to_parent.py validate_report (called before the result is returned); the axis validate_form step is not built (BLOCKED, see misfits) |
| waiting.py | MonitorWaiting (class) | machinery | suspension machinery |
| waiting.py | MonitorWaiting.suspension_changed (method) | machinery | suspension of the old execution backend; the wait itself is the tool wait_for_events |
| yield_estimator.py | _monitor_information_yield (function) | episode function | credit.py checked_increment (credit cannot decrease) and yield_estimator.py: accumulation controller |
| yield_estimator.py | MonitorEpisodeYield (class) | episode function | yield_estimator.py |
| yield_estimator.py | MonitorEpisodeYield.yield_controller (method) | episode function | yield_estimator.py yield_controller: AccumulationYieldController(epoch, initial_credit, settings[cost], settings[parameters]) |
