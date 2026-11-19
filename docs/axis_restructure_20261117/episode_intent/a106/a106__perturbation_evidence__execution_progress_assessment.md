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
