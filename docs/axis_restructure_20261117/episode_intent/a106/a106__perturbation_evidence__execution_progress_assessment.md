# a106/perturbation_evidence/execution_progress_assessment — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a106/perturbation_evidence/execution_progress_assessment/<file>`
(only files directly in this folder; no `grading/`/`scoring/`; `tests/` not covered). Old binding class
`MonitorEpisode` (`binding_path = 'perturbation_evidence/execution_progress_assessment'`, `commissioning_parent =
'perturbation_evidence'`, `roles = entry_roles = ('monitor',)`), decision source `ProgressMonitoringTask`, prompt
renderer `render_monitor_prompt` (old shared `library/monitor_prompt`). Version `monitor_episode_binding_v1`.

## What it is for (its goal, in its own words)

`goal.py`: "Investigate which further exposed progress information is useful for the assigned target. Use actual
status, measured quantities, committed references and source-bound logs. Liveness establishes process presence only;
elapsed time alone establishes neither productive work nor a stall. Unknown information stays unknown. Earlier
outcomes and your admitted child forms inform later decisions. You may explicitly commission an ordinary monitor for
one exposed direct dependency; no descendant traversal, fanout, cadence or depth is prescribed. Return the original
parent's typed form at your closure even while the target remains active. Do not report private reasoning,
intentions or unrestricted findings. Recorded facts use saved delivered observations; closure does not poll or
compose another report with a model." + (private yield: "The monitor's information-credit projector and bound yield
rule govern continuation." / else "The caller's monitoring projector and configured controller own credit and
continuation.") + "Repeated observation identities and read timestamps alone earn no new information."
`planning_context` also gives the unresolved question "Which exposed progress information would improve the
original requested report?" and progress definition "Actual received information under the caller-bound monitoring
projector; repeated identities and timestamps alone earn no credit."

## Task and instructions

`task_instructions.py` (own text, not the scientific INSTRUCTIONS): goal + ACTION_BOUNDARY + CREDIT_COMPONENT_GUIDANCE
+ RESOURCE_ESTIMATE_GUIDANCE + REPORT_GUIDANCE + history (exchange or fresh-conversation) + HOST_EXECUTION_GUIDANCE +
tool knowledge + launch instructions + REPAIR + WAIT (+ NATIVE_EVENT). `task.py` has no reason branch and no
automatic score updates/shared grading retention; `task_decision.py` routes the model call through
`decision_completion()` so the monitor's own prompt renderer is used, and has no literature numerical contracts.

## What it reads from its parent's assignment

`monitor_assignment_v1`: `target_handle` (must be an execution_handle in scope), `requested_fields` subset of
execution_status/measurements/log_windows/committed_record_refs/dependencies/result_available,
`known_progress_refs` (must belong to the target), `permitted_committed_record_types`.

## Children it may commission

| role | child binding | sent | taken back |
|---|---|---|---|
| `monitor` (recursive) | itself | assignment for one exposed direct dependency of its target; permitted record types no wider than its own | typed form; its `episode_progress` references admitted into the progress provider (`receive_progress`) |

Allowed only when the target exposes direct dependencies.

## Decision state and what it shows the model

Copy of the launch decision state; binding decision_context: monitor_assignment, monitor_target_description,
monitor_direct_dependencies, monitor_received_progress_refs, monitor_information_meaning ("Empty measurements/log
windows do not assert absence or a stall."), monitor_goal (planning_context). Decision inputs as the launch child
without shared_information_context.

## Tools it offers

`progress.observe` (requested fields within the assignment, optional native_operation from the target descriptor),
`progress.read` (a delivered observation), `progress.log` (one exact retained log window via source.read, byte
custody checked). Common actions: tool, child, wait, redeliver_report (no reason).

## How its credit is counted

Credit kind `monitoring`; credit_view = `services.bound_role_credit` (caller-bound monitoring projector);
`information_credit` = `ProgressInformationCredit(progress_reader, information_unit)` (newly informative received
snapshot count x information_unit).

## Continuation

`YieldController(cutoff, YieldParameters(uncertainty_alpha), estimate_with_context=_monitor_information_yield)`
(accumulation; `estimate_nonnegative_yield`; credit may not decrease; estimator binding
`monitor_information_accumulation_v1`). Settings `yield_settings {kind information_accumulation, cutoff,
uncertainty_alpha}`; requires private yield.

## What it reports to its parent

Fact sources: monitoring_progress_refs, monitoring_target_handle, monitoring_execution_state,
monitoring_result_available, monitoring_observed_at_unix_seconds, monitoring_committed_record_refs,
monitoring_dependency_handles (from the latest delivered target observation). Required return to a
perturbation_evidence parent: `monitoring_progress_refs` when the annotation task is required (rule owned by the
head's `to_child_execution_progress_assessment.required_return_sources`). `validate_report` checks fact fields and
that every referenced record is permitted and received.

## Differences from siblings

Unlike launch/api children: no resource configuration, information credit instead of operational credit, own
prompt renderer and instruction text, recursive dependency monitors. The head owns its request preparation
(`prepare_request`) and progress receipt.

## File by file
| old file | lines | own intent | old-runner names (uses) |
|---|---|---|---|
| __init__.py | 1 | package marker | none |
| binding_record.py | 9 | as_record: version monitor_episode_binding_v1, binding_id, outcome_page_size, information_unit + yield_settings when private yield | none |
| configuration.py | 31 | construction: outcome_page_size, information_unit, yield_settings {kind information_accumulation, cutoff, uncertainty_alpha} | `import:communication` x1 |
| contracts.py | 10 | VERSION, FIELDS (execution_status, measurements, log_windows, committed_record_refs, dependencies, result_available), states, monitor_assignment_v1 schema (target_handle, requested_fields, known_progress_refs, permitted_committed_record_types) | `import:domain` x1 |
| credit.py | 21 | credit kind 'monitoring'; credit_view = services.bound_role_credit; information_credit = ProgressInformationCredit(progress_reader, information_unit) | `import:library.progress_information_credit` x1, `services.bound_role_credit` x1 |
| decision_inputs.py | 68 | decision inputs as launch minus shared_information_context | `bind_functions` x2, `binding_context` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.available_child_roles` x1, `self.workflow.binding_context` x1, `self.workflow.episode_bindings` x1, `self.workflow.execution_expectations` x1, `self.workflow.launch_instructions` x2, `self.workflow.native_estimation_context` x1, `self.workflow.pending_work` x1, `self.workflow.permits_common_action` x1, `self.workflow.resource_context` x1, `self.workflow.resource_estimator` x4, `self.workflow.waiting_support` x1 |
| decision_presentation.py | 51 | present_credit_state, completed work, yield table (copy) | `bind_functions` x2, `import:episode_work_report` x1, `import:library.live_runtime_functions` x1, `import:runtime` x4, `self.workflow.controller_binding` x1, `self.workflow.journal` x1, `table:runtime_actions` x1 |
| decision_state.py | 78 | decision state shown to model (copy of launch shape) | `bind_functions` x2, `binding_context` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.binding_context` x1, `self.workflow.catalog` x1, `self.workflow.controller_binding` x1, `self.workflow.delivery_status` x1, `self.workflow.extra_report_sources` x1, `self.workflow.job_episode_options` x1, `self.workflow.journal` x2, `self.workflow.knowledge` x1, `self.workflow.local_outcome_preview` x1, `self.workflow.pending_work` x1, `self.workflow.receipt_projection` x1, `self.workflow.run_id` x1, `self.workflow.source_credit_binding` x1, `self.workflow.source_credit_view` x1, `self.workflow.specialist` x1, `self.workflow.store` x3, `self.workflow.tools` x1, `self.workflow.working_state` x1, `table:runtime_actions` x1 |
| episode.py | 54 | binds role monitor; recursive child monitor only when the target exposes direct dependencies; common actions tool/child/wait/redeliver_report (no reason); prompt renderer render_monitor_prompt; required return sources from the head's to_child_execution_progress_assessment | `import:communication` x1, `import:library.monitor_prompt` x1, `import:to_child_execution_progress_assessment` x1, `services.dependencies` x1 |
| from_child_execution_progress_assessment.py | 20 | receive_progress: admit episode_progress references from a child monitor's form | `import:communication` x1, `import:domain` x1, `import:method_loop.durable` x1 |
| from_parent.py | 33 | assignment validation: target_handle in scope, known_progress_refs belong to the target; dependency child check | `import:communication` x1, `import:domain` x1, `services.read_progress` x1, `services.reference_in_scope` x1 |
| goal.py | 15 | the episode goal text; planning_context (objective, target, requested fields, progress definition, yield settings) | `import:communication` x1 |
| internal_summary.py | 13 | decision_context: monitor_assignment, target description, direct dependencies, received progress refs, information meaning, monitor_goal | `import:communication` x1, `services.dependencies` x1, `services.describe_progress_target` x1 |
| progress_operations.py | 58 | tools progress.observe (requested fields subset, optional native_operation), progress.read, progress.log (exact retained log window via source.read) | `import:communication` x1, `import:domain` x1, `import:episode_bindings` x1, `services.describe_progress_target` x1, `services.execute_tool` x1, `services.observe_progress` x1, `services.read_record` x2 |
| progress_records.py | 16 | UTC timestamp parse, unique | `import:domain` x1 |
| received_progress.py | 30 | received progress refs (assignment known + own outcomes + delivered), snapshot read guarded by receipt | `import:domain` x1, `services.own_outcomes` x1, `services.progress_selection` x1, `services.read_progress` x1, `services.received_progress_refs` x1 |
| report_delivery.py | 33 | finish (copy) | `bind_functions` x2, `binding_context` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.binding_context` x1, `self.workflow.episode_bindings` x1, `self.workflow.facts` x1, `self.workflow.journal` x2, `self.workflow.pending_handles` x1, `self.workflow.release` x2, `self.workflow.source_credit_view` x1, `table:runtime_forms` x2 |
| task.py | 187 | decision loop without reason actions or automatic score updates | `bind_functions` x2, `import:episode_source_failure` x1, `import:library.live_runtime_functions` x1, `import:providers` x1, `import:runtime` x2, `self.workflow.action_schema` x1, `self.workflow.completed_unit` x3, `self.workflow.completions` x3, `self.workflow.controller_value` x2, `self.workflow.decision_exchanges` x3, `self.workflow.delivery_resolution_inputs` x1, `self.workflow.execute` x1, `self.workflow.execution_binding` x7, `self.workflow.inprocess_replay` x4, `self.workflow.journal` x7, `self.workflow.last_observed_credit` x1, `self.workflow.next_return` x1, `self.workflow.pending_work` x1, `self.workflow.receive_native_outcome` x1, `self.workflow.receive_outcome` x1, `self.workflow.resolve_pending_deliveries` x1, `self.workflow.resolver` x1, `self.workflow.run_id` x2, `self.workflow.selected` x3, `self.workflow.source_credit_view` x1, `self.workflow.store` x7, `self.workflow.validate_report` x1, `table:runtime_actions` x8, `table:runtime_episodes` x1, `table:runtime_model_calls` x2 |
| task_decision.py | 428 | model call through decision_completion (presentation renderer) + decision exchange; no literature numerical contracts | `bind_functions` x3, `import:library.live_runtime_functions` x1, `import:providers` x3, `import:runtime` x2, `self.workflow.contract_information_profile` x1, `self.workflow.contract_information_reply` x1, `self.workflow.decision_exchanges` x4, `self.workflow.decision_protocol` x3, `self.workflow.execute` x1, `self.workflow.freeze_contract_information` x1, `self.workflow.history_preview` x1, `self.workflow.journal` x3, `self.workflow.numerical_contracts` x1, `self.workflow.provider` x3, `self.workflow.receipts` x4, `self.workflow.run_id` x1, `self.workflow.services` x2, `self.workflow.specialist` x2, `self.workflow.store` x2, `self.workflow.uses_received_record_context` x2, `self.workflow.validate_contract_information` x5, `services.decision_exchange_instructions` x1, `services.instructions` x1, `table:runtime_model_calls` x8 |
| task_instructions.py | 86 | own instruction composition: goal + action boundary + credit component + resource estimate + report + history + host guidance, repair, wait, native events | `binding_context` x1, `source.workflow.binding_context` x1, `source.workflow.decision_protocol` x1, `source.workflow.knowledge` x1, `source.workflow.launch_instructions` x1, `source.workflow.native_event_information` x1, `source.workflow.permits_common_action` x1, `source.workflow.specialist` x1 |
| task_state.py | 114 | decision state (copy) | `bind_functions` x2, `import:episode_source_failure` x1, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.archive` x1, `self.workflow.completions` x4, `self.workflow.controller_value` x1, `self.workflow.execution_binding` x4, `self.workflow.inprocess_replay` x7, `self.workflow.journal` x5, `self.workflow.progress_provider` x2, `self.workflow.recover_commissions` x1, `self.workflow.run_id` x1, `self.workflow.source_credit_view` x1, `self.workflow.store` x2, `table:runtime_actions` x5, `workflow.context` x1, `workflow.grains` x1 |
| to_child_execution_progress_assessment.py | 11 | prepare_dependency_request: child target must be an exposed direct dependency, record types no wider than parent | `import:domain` x1, `services.dependencies` x1 |
| to_parent.py | 91 | fact sources monitoring_progress_refs, target_handle, execution_state, result_available, observed_at_unix_seconds, committed_record_refs, dependency_handles; facts from latest delivered target observation; resolve; validate_report checks recorded facts and permitted committed records | `import:communication` x1, `import:domain` x1, `import:episode_bindings` x1, `services.read_progress` x3, `services.read_record` x2 |
| waiting.py | 30 | selected wait + suspension (copy) | `bind_functions` x2, `import:library.live_runtime_functions` x1, `import:runtime` x2, `self.workflow.execution_backend` x1, `self.workflow.execution_handle` x2, `self.workflow.perform_selected_wait` x1 |
| yield_estimator.py | 23 | accumulation YieldController(cutoff, uncertainty_alpha) with _monitor_information_yield (estimate_nonnegative_yield; credit cannot decrease) | `import:numerical` x2 |

## Carried over

Source read with `git show 97308b94c:<path>` (git dir `/home/chia/repos/gene_annotation_episode_disk/.git`). One row per old function, class and method (`runs/carry_over/functions/a106__perturbation_evidence__execution_progress_assessment.tsv`). Files written: `goal.py`, `task.py`, `credit.py`, `yield_estimator.py`, `episode.py`, `messages/*` (with `msg_to_child.py` and `read_from_child.py`: the episode commissions a monitor of its own kind). Nothing was added to `episode_support/`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | MonitorBindingRecord (class) | machinery | the binding's own as_record() (README 3e) |
| binding_record.py | MonitorBindingRecord.as_record (method) | machinery | the binding's own as_record() (README 3e) |
| configuration.py | MonitorConfiguration (class) | episode function | settings: information_unit is the assignment field in messages/read_from_parent.py; cost and parameters are ctx.settings read in yield_estimator.py; outcome_page_size (old own_outcomes paging) is not carried |
| configuration.py | MonitorConfiguration.__init__ (method) | episode function | values: information_unit -> messages/read_from_parent.py ASSIGNMENT_FORM and its positive check; yield_settings cutoff/uncertainty_alpha -> ctx.settings cost/parameters in yield_estimator.py; outcome_page_size -> not carried (old own_outcomes paging) |
| configuration.py | MonitorConfiguration._role (method) | machinery | role dispatch of the old multi-role binding; the episode has one role |
| credit.py | MonitorEpisodeCredit (class) | episode function | credit.py credit |
| credit.py | MonitorEpisodeCredit.credit_kind (method) | machinery | credit kind label of the old credit view ('monitoring'); the credit is credit.py credit |
| credit.py | MonitorEpisodeCredit.credit_view (method) | machinery | old services.bound_role_credit credit view; the number is credit.py credit(summary, records) |
| credit.py | MonitorEpisodeCredit.information_credit (method) | episode function | credit.py credit: ProgressInformationCredit (library grading/perturbation_evidence/progress_information_credit.py) over a SummaryProgress reader of the summary snapshots |
| decision_inputs.py | MonitorDecisionInputs (class) | episode function | task.py decide (context) and messages/internal_summary.py |
| decision_inputs.py | MonitorDecisionInputs.decision_inputs (method) | episode function | task.py decide: launch instruction library listing, selected launch instructions, child_options, execution expectations (estimate_table read; BLOCKED-ON-JOB-SERVICE); resource_context, native estimation, pending_work, waiting_support and resource estimates are old-runner inputs not carried |
| decision_inputs.py | _a106_original_global_ValueError (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_inputs.py | _a106_original_global_child_option_information (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_inputs.py | _a106_original_global_set (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_inputs.py | _bind_original_task_runtime_providers (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_presentation.py | present_credit_state (function) | machinery | old presentation of root annotation-axis credit forms and journal reads; the monitor shows controller table via internal_summary |
| decision_presentation.py | prepare_completed_work (function) | machinery | old completed_action_reports over the old journal (runtime_actions); not carried |
| decision_presentation.py | decision_yield_table (function) | episode function | messages/internal_summary.py 'controller' (library records/progress_views.py yield_table over view.controller_state) |
| decision_presentation.py | _bind_original_task_runtime_providers (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_state.py | MonitorDecisionState (class) | episode function | messages/internal_summary.py and task.py decide |
| decision_state.py | MonitorDecisionState.decision_state (method) | episode function | messages/internal_summary.py internal_summary (goal, last outcome, received progress, controller) and task.py decide (context for the model); journal/working_state/report lifecycle/delivery parts are old-runner and not carried |
| decision_state.py | _a106_original_global_FACT_MEANINGS (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_state.py | _a106_original_global_FACT_SOURCES (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_state.py | _a106_original_global_Mapping (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_state.py | _a106_original_global__references_in (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_state.py | _a106_original_global_callable (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_state.py | _a106_original_global_getattr (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_state.py | _a106_original_global_isinstance (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_state.py | _a106_original_global_json (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_state.py | _a106_original_global_sorted (function) | machinery | provider patching of the old shared runtime (README 3e) |
| decision_state.py | _bind_original_task_runtime_providers (function) | machinery | provider patching of the old shared runtime (README 3e) |
| episode.py | MonitorEpisode (class) | episode function | episode.py ExecutionProgressAssessment (one class, EpisodeBinding) |
| episode.py | MonitorEpisode.child_roles (method) | episode function | task.py CHILD_SLOTS = {'monitor': BINDING_PATH} |
| episode.py | MonitorEpisode.required_return_sources (method) | episode function | the parent selects: monitoring_progress_refs and monitoring_progress_snapshots are named in messages/msg_to_child.py selection; fields declared in messages/final_to_parent.py RETURN_FORM |
| episode.py | MonitorEpisode.permitted_common_actions (method) | episode function | task.py decide/selection_schema: tool and child (wait is the tool wait_for_events; redeliver_report not carried) |
| episode.py | MonitorEpisode.allowed_children (method) | episode function | task.py selection_schema offers the monitor child only when the target exposes direct dependencies; task.py action checks it |
| episode.py | MonitorEpisode.prepare_child_request (method) | episode function | task.py action (dependency, permitted types, known progress checks) and messages/msg_to_child.py |
| episode.py | MonitorEpisode.receive_child_progress (method) | episode function | messages/read_from_child.py read_from_child |
| from_child_execution_progress_assessment.py | receive_progress (function) | episode function | messages/read_from_child.py read_from_child (every delivered progress ref must come with its snapshot); the provider _receive_progress ledger and signature are old-runner receipts, not carried |
| from_parent.py | MonitorAssignment (class) | episode function | messages/read_from_parent.py |
| from_parent.py | MonitorAssignment.assignment_schema (method) | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and ASSIGNMENT_SCHEMA |
| from_parent.py | MonitorAssignment._assignment (method) | episode function | messages/read_from_parent.py read_from_parent (schema, positive unit, known-progress target match); the in-scope execution_handle check is task.py target_in_scope (BLOCKED-ON-JOB-SERVICE) |
| from_parent.py | MonitorAssignment.prepare_assignment (method) | episode function | messages/msg_to_child.py msg_to_child and task.py action (dependency request checks) |
| goal.py | MonitorGoal (class) | episode function | goal.py and task.py GOAL_INSTRUCTIONS |
| goal.py | MonitorGoal.instructions (method) | episode function | task.py GOAL_INSTRUCTIONS (the private-yield wording) |
| goal.py | MonitorGoal.planning_context (method) | episode function | messages/internal_summary.py 'goal' (objective, target, requested fields, unresolved question, progress definition) and task.py decide 'monitor_goal' |
| internal_summary.py | MonitorSummary (class) | episode function | messages/internal_summary.py |
| internal_summary.py | MonitorSummary.decision_context (method) | episode function | messages/internal_summary.py internal_summary and task.py decide (monitor_assignment, target description, direct dependencies, received progress refs, information meaning, monitor_goal) |
| progress_operations.py | ProgressOperations (class) | episode function | task.py TOOLS |
| progress_operations.py | ProgressOperations.catalog (method) | episode function | task.py tool_catalog |
| progress_operations.py | ProgressOperations.execute (method) | episode function | task.py tools progress_observe, progress_read, progress_log (observe via job_access: BLOCKED-ON-JOB-SERVICE; native_observation_options not placed: raises) |
| progress_records.py | _timestamp (function) | episode function | messages/final_to_parent.py _timestamp_seconds |
| progress_records.py | _unique (function) | episode function | messages/internal_summary.py _unique |
| received_progress.py | ReceivedProgress (class) | episode function | messages/internal_summary.py |
| received_progress.py | ReceivedProgress._received (method) | episode function | messages/internal_summary.py received_progress_refs (known + own outcomes + child reports); the old provider selection/received ledgers are not carried |
| received_progress.py | ReceivedProgress._snapshot (method) | episode function | task.py action (received flag and snapshot carried into the call) and _received_snapshot; unreceived raises monitor_progress_not_received |
| received_progress.py | OwnProgress (class) | episode function | messages/internal_summary.py |
| received_progress.py | OwnProgress._own_progress_refs (method) | episode function | messages/internal_summary.py own_progress_refs from view.outcomes (no outcome paging) |
| report_delivery.py | MonitorReportDelivery (class) | episode function | messages/final_to_parent.py |
| report_delivery.py | MonitorReportDelivery.finish (method) | episode function | messages/final_to_parent.py final_to_parent (facts from delivered observations, validate_report before return); runtime_forms save, form_with_facts of a model-written report and release are old-runner, not carried |
| report_delivery.py | _bind_original_task_runtime_providers (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task.py | ProgressMonitoringTask (class) | machinery | the old decision loop class (README 3a); decide/action/tools in task.py |
| task.py | ProgressMonitoringTask.next (method) | machinery | old decision loop step with replay/checkpoint/source-failure handling; decide in task.py |
| task.py | ProgressMonitoringTask.apply_response (method) | episode function | task.py action (decode and validate the answer, Rejected on error); report_update validation and delivery resolution are machinery, not carried |
| task.py | ProgressMonitoringTask.execute (method) | machinery | old action execution with journal rows, native outcome receipt and completion staging; the system runs the unit; a returned invalid tool outcome is still a unit |
| task.py | _bind_original_task_runtime_providers (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | MonitorTaskDecision (class) | episode function | task.py decide/action |
| task_decision.py | MonitorTaskDecision.call (method) | machinery | old model call with exchange, journal save and session; decide returns a ModelRequest |
| task_decision.py | MonitorTaskDecision.instructions (method) | episode function | task.py instructions |
| task_decision.py | MonitorTaskDecision.decision_completion (method) | episode function | task.py decide (the monitor own prompt/context rendering; model request) |
| task_decision.py | MonitorTaskDecision.conversation_key (method) | machinery | old provider conversation key (README 5 item 7) |
| task_decision.py | MonitorTaskDecision.interpretation_context (method) | machinery | old report interpretation context for the model-written report update; not carried |
| task_decision.py | MonitorTaskDecision.exchange_schema (method) | machinery | decision-exchange loop |
| task_decision.py | MonitorTaskDecision.exchange_response (method) | machinery | decision-exchange loop |
| task_decision.py | MonitorTaskDecision.validate_contract_exchange_request (method) | machinery | decision-exchange loop |
| task_decision.py | MonitorTaskDecision.validate_contract_exchange_history (method) | machinery | decision-exchange loop |
| task_decision.py | MonitorTaskDecision.exchange_decision (method) | machinery | decision-exchange loop |
| task_decision.py | _a106_original_global_DECISION_CONTEXT_VERSION (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_OSError (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_TypeError (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_ValidationError (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_ValueError (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global__action_generation_schema (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global__json (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global__plain (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_child_option_information (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_instructional_model_context (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_isinstance (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_len (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_lookup_attempts (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_model_snapshot (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_requested_contract_information (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_schema_failure_diagnostic (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_sqlite3 (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_state_frame (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_str (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _a106_original_global_type (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_decision.py | _bind_original_task_runtime_providers (function) | machinery | provider patching of the old shared runtime (README 3e) |
| task_instructions.py | instructions (function) | episode function | task.py instructions (goal, action boundary, credit, host execution, tool knowledge, launch library, native events; resource/report/history/repair/pending-child paragraphs not carried) |
| task_state.py | MonitorTaskState (class) | machinery | checkpoint/restore state of the old task |
| task_state.py | MonitorTaskState.__init__ (method) | machinery | checkpoint/restore state of the old task |
| task_state.py | MonitorTaskState.bind_execution_context (method) | machinery | old execution context binding |
| task_state.py | MonitorTaskState.record_execution_failure (method) | machinery | old journal failure record; a tool exception ends the run |
| task_state.py | MonitorTaskState.restore_checkpoint (method) | machinery | checkpoint/restore |
| task_state.py | MonitorTaskState.restore (method) | machinery | checkpoint/restore |
| task_state.py | MonitorTaskState.record_effect (method) | machinery | old journal effect record |
| task_state.py | MonitorTaskState.checkpoint (method) | machinery | checkpoint/restore |
| task_state.py | _bind_original_task_runtime_providers (function) | machinery | provider patching of the old shared runtime (README 3e) |
| to_child_execution_progress_assessment.py | prepare_dependency_request (function) | episode function | task.py action (target must be an exposed direct dependency; permitted types no wider; known progress held) and messages/msg_to_child.py |
| to_parent.py | MonitorReport (class) | episode function | messages/final_to_parent.py |
| to_parent.py | MonitorReport.fact_sources (method) | episode function | messages/final_to_parent.py RETURN_FORM (seven monitoring facts, selectable) |
| to_parent.py | MonitorReport.facts (method) | episode function | messages/final_to_parent.py monitor_facts |
| to_parent.py | MonitorReport.resolve (method) | episode function | messages/final_to_parent.py validate_report (references must be received progress or delivered permitted records); the old resolver for a parent-written form is not carried |
| to_parent.py | MonitorReport.validate_report (method) | episode function | messages/final_to_parent.py validate_report, called by final_to_parent before returning; its first step (validate_form of the parent-written form) has no object: the system admits RETURN_FORM |
| waiting.py | MonitorWaiting (class) | episode function | task.py wait_for_events |
| waiting.py | MonitorWaiting._execute_selected_wait (method) | episode function | task.py tool wait_for_events (library jobs/waiting.py selected_wait; event ledger service native_events: BLOCKED-ON-JOB-SERVICE) |
| waiting.py | MonitorWaiting.suspension_changed (method) | machinery | suspension of the old execution backend |
| waiting.py | _bind_original_task_runtime_providers (function) | machinery | provider patching of the old shared runtime (README 3e) |
| yield_estimator.py | _monitor_information_yield (function) | episode function | credit.py checked_increment (information credit cannot decrease) and yield_estimator.py: AccumulationYieldController |
| yield_estimator.py | MonitorEpisodeYield (class) | episode function | yield_estimator.py |
| yield_estimator.py | MonitorEpisodeYield.yield_controller (method) | episode function | yield_estimator.py yield_controller: AccumulationYieldController(epoch, initial_credit, settings[cost], settings[parameters]) |
