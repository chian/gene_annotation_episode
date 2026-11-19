# Episode intent: `execution_progress_assessment` (A102)

Episode folder: `gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment`

Source read: this folder's own 29 files at commit `97308b94c` (1,406 lines), including its `tests/` folder. Nothing outside the folder was read, so anything that lives in an imported module is described only as far as this folder's files show it.

Old identity: binding path `structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment`, old role name `monitor`, commissioned by `.../hpc_allocation_execution`. It could also be entered directly (`entry_roles = ('monitor',)`), and it may commission itself.

## What this episode is for

It finds out which further progress information about one assigned execution target is useful, from what the target actually exposes, and returns that to its parent while the target may still be running. Its goal, in its own words (`goal.py`):

> Investigate which further exposed progress information is useful for the assigned target. Use actual status, measured quantities, committed references and source-bound logs. Liveness establishes process presence only; elapsed time alone establishes neither productive work nor a stall. Unknown information stays unknown. Earlier outcomes and your admitted child forms inform later decisions. You may explicitly commission an ordinary monitor for one exposed direct dependency; no descendant traversal, fanout, cadence or depth is prescribed. Return the original parent's typed form at your closure even while the target remains active. Do not report private reasoning, intentions or unrestricted findings. Recorded facts use saved delivered observations; closure does not poll or compose another report with a model.

followed by one of two sentences:

- with its own yield settings: "The monitor's information-credit projector and bound yield rule govern continuation."
- without: "The caller's monitoring projector and configured controller own credit and continuation."

and then: "Repeated observation identities and read timestamps alone earn no new information."

The goal summary it also shows the model (`goal.py`, `planning_context`): `objective` (the request's goal), `target_handle`, `requested_fields`, `unresolved_question` = "Which exposed progress information would improve the original requested report?", `progress_definition` = "Actual received information under the caller-bound monitoring projector; repeated identities and timestamps alone earn no credit.", and `yield_settings`.

## Task and instructions

One unit of its cycle is one selected action: a progress tool, a child monitor for one direct dependency, a wait, or a report redelivery. Each decision the model returns a `selection` and a `report_update`. A selection that fails admission creates no unit: the model gets feedback and decides again. A failed model call ends the episode's source as `source_failed`. A tool call that breaks the assignment's limits returns an `invalid` outcome, which is kept and enters the iterator; on replay it is not observed again.

Permitted actions (`episode.py`): `tool`, `child`, `wait`, `redeliver_report`.

Instructions are this episode's own text, composed in `task_instructions.py` (it imports nothing from the old shared prompt): the goal text, then

1. `ACTION_BOUNDARY`: "Do not emit a stop action or invent a turn budget, approval review, quality gate, experiment, term or observation."
2. `CREDIT_COMPONENT_GUIDANCE`: `current_evidence_vector` holds the projector's component values from the same projection as `current_credit`; "they describe the progress proxy, not biological truth."
3. `RESOURCE_ESTIMATE_GUIDANCE`: how to read `resource_tool_estimates`; "A timing experiment earns monitoring credit for timing information learned and updates execution expectations. Missing history means duration is unknown. Job elapsed time and the duration of an own monitoring action are distinct measurements."
4. `REPORT_GUIDANCE`: a commissioned child returns only the parent's typed form; `report_update` is the interpretation before the selected action; `report_delivery_failure` is repaired with `redeliver_report`, not by recommissioning.
5. history guidance: under the exchange protocol, use `request_context` and `episode.history`; otherwise the fresh-conversation text about `restored_episode_history`.
6. `HOST_EXECUTION_GUIDANCE`: "Do not execute native provider tools. The host executes your selected action."
7. tool-knowledge and launch-instruction-library instructions when present;
8. `REPAIR_GUIDANCE` (the `pending_child_delivery` paragraph), `WAIT_GUIDANCE` (waiting for a `pending_child_` handle), and `NATIVE_EVENT_GUIDANCE` when native event targets exist.

The prompt is rendered by this episode's own renderer, `render_monitor_prompt`, whenever the provider supports presentation (`task_decision.py`). The renderer is imported from outside the folder.

## What it reads from its parent's assignment

The assignment form `monitor_assignment_v1` (`contracts.py`):

- `target_handle`: the execution handle to assess; it must be an execution handle in scope;
- `requested_fields`: a subset of `execution_status`, `measurements`, `log_windows`, `committed_record_refs`, `dependencies`, `result_available`; the monitor may never observe more than these;
- `known_progress_refs`: progress observations the parent already has; each must be an observation of the same target;
- `permitted_committed_record_types`: the record types whose committed records it may return.

From the request message: `initial_report`, `episode_assignment.launch_instructions`, `job_assignment`, the goal (shown as `objective`) and the report contract. When the parent is the axis head and an annotation task is required, the parent must request the fact `monitoring_progress_refs`.

## Children

One child: itself (`to_child_execution_progress_assessment.py`, `from_child_execution_progress_assessment.py`). It is allowed only while the assigned target exposes direct dependencies.

- What it sends: a `monitor_assignment_v1` whose `target_handle` is one exposed direct dependency of its own target (otherwise `monitor_child_target_not_exposed_direct_dependency`) and whose `permitted_committed_record_types` do not exceed its own (otherwise `monitor_child_expands_permitted_record_types`). The instructions add: "no descendant traversal, fanout, cadence or depth is prescribed."
- What it takes back: the child's typed form. Every reference of namespace `episode_progress` in it must be a readable progress observation in scope; those references are recorded as received by this monitor under the delivery's operation key, with a signature of form, schema and scope (the same key with a different form is a conflict). They then count as this monitor's received progress.

## Decision state and what it shows the model

State kept between decisions (`task_state.py`): the decision counter, `feedback`, the last outcome and its index, the current `report_values` (starting from the parent's `initial_report`) and their basis refs. Received progress (`received_progress.py`) is the assignment's `known_progress_refs`, the progress refs in this monitor's own action outcomes, and the progress received from child monitors.

Shown to the model at each decision:

- base state (`decision_state.py`): `goal`, `scope`, `working_state`, `visible_record_refs`, `current_credit`, `current_evidence_vector`, `credit_binding`, `time_accounting`, `pending_work`, `last_local_outcome`, `feedback`, `visual_evidence`, `report_deliveries`, `controller`, `controller_binding`, `tools`, `tool_knowledge`, `job_episode_options`, `available_report_facts`, `requested_report_purpose`, `requested_form`, `current_report_update`, `current_report_basis_refs`, `report_lifecycle`, and admitted child reports;
- `monitoring_information_credit` and `monitoring_information_binding` when the credit view carries them;
- this episode's own fields (`internal_summary.py`): `monitor_assignment`, `monitor_target_description`, `monitor_direct_dependencies`, `monitor_received_progress_refs`, `monitor_information_meaning` = "Exposed direct relationships and already delivered observations. Empty measurements/log windows do not assert absence or a stall.", and `monitor_goal` (the goal summary above);
- extra inputs (`decision_inputs.py`): `resource_context`, `launch_instruction_library`, `selected_launch_instructions`, `child_options`, `completed_action_reports`, `pending_work`, `execution_expectations` captured for `monitor`, `resource_tool_estimates`, `native_execution_expectations`, `waiting_support`, `contract_information_profile`;
- under the exchange protocol, the per-action yield table and the answers to its own lookups.

## Tools it offers

Three tools (`progress_operations.py`):

- `progress.observe`: "Observe selected exposed fields of your assigned target. Retain the original observation identity when facts are unchanged. This operation never traverses dependent work." Argument `requested_fields` (must be within the assignment's `requested_fields`), plus `native_operation` when the target's description declares a selected-observation schema.
- `progress.read`: "Read an already delivered exact progress observation." Argument `progress_ref` (must be received progress).
- `progress.log`: "Read one exact retained log window from an already delivered progress observation, preserving source/artifact byte custody." Arguments `progress_ref`, `log_index`; the window is read by exact byte range through `source.read`; an empty window returns empty text without a read.

An outcome carries `progress_refs`; committed records are listed only for permitted record types.

## How its credit is counted

Credit kind is `monitoring` (`credit.py`). The credit view is the caller-bound role credit for this monitor. The information credit calculation it selects is `ProgressInformationCredit(progress_reader, information_unit=...)`: the yield binding text describes the credit as "newly informative received snapshot count times information unit". The calculation is outside this folder. The information unit is always passed explicitly. Repeated observation identities and read timestamps earn nothing. After each tool action the task records the current credit view's `credit`; a wait keeps the last observed credit. A child's return adds to this monitor's received progress. Nothing in this folder bounds, clamps or rescales the credit.

## Continuation

`yield_estimator.py`, `configuration.py`. Two modes:

- With its own yield settings, exactly `{kind: 'information_accumulation', cutoff >= 0, uncertainty_alpha in (0, 1)}` plus `information_unit > 0`: the old controller was `YieldController(epoch, initial_credit, cutoff, YieldParameters(uncertainty_alpha=...))` with an accumulation estimate (`estimate_nonnegative_yield`) over this monitor's own action credits. A decreasing credit raises `monitor_information_credit_cannot_decrease`. Binding text: forecast = "next_monitor_action_information_credit"; decision = "predicted_upper_gain_at_or_below_monitor_cutoff". Of the three current estimators this is accumulation.
- Without them, asking for the controller raises `monitor_private_yield_binding_not_enabled`; the caller's projector and controller own credit and continuation.

## What it reports to its parent

The parent's typed form, filled with recorded facts and the latest admitted interpretations, returned at closure even while the target is still active (`report_delivery.py`). Facts a parent may request (`to_parent.py`):

- `monitoring_progress_refs`: delivered progress observation identities, including admitted child updates;
- `monitoring_target_handle`;
- `monitoring_execution_state` (`pending`, `executing`, `returned`, `admitted`, or null without an observation);
- `monitoring_result_available`;
- `monitoring_observed_at_unix_seconds` (the original observation time, not refreshed);
- `monitoring_committed_record_refs` (permitted types only, actually delivered);
- `monitoring_dependency_handles` (direct dependencies in the latest observation of the assigned target).

Facts come from delivered observations only; nothing is observed at closure. A report whose fact fields disagree with recorded facts, or that names a record not permitted or not received, is refused. With no report contract it returns `credit`, `pending_handles` and the binding's current report facts.

## How it differs from similar episodes

Compared with the three job episodes under `execution_job_submission`:

- It observes; it runs nothing. Its tools are `progress.observe`, `progress.read`, `progress.log`.
- It may commission a child (itself, one direct dependency at a time), may wait, and may redeliver a report. The job episodes are leaves.
- Its credit kind is `monitoring` (information received), not `operational`; its continuation is accumulation, not completion.
- It can leave credit and continuation to its caller; the job episodes always require their own yield profile.
- It can be an entry point; the job episodes cannot.
- Its instructions are fully its own text in `task_instructions.py`; the job episodes take the reasoning-commit text and the history paragraph from the old shared prompt module.
- Its prompt renderer is used unconditionally; the job episodes test the context first.
- Its task has no `reason` branch, no automatic score updates and no shared-read retention; its decision inputs have no `shared_information_context`, no `requested_action_history` and no job-source estimate.
- It has no closed-credit freezing files and no protein-structure or result-custody files.
- Its folder uses the `to_child_*` / `from_child_*` / `task_instructions.py` / `task_decision.py` file names; the HPC and local job episodes use `decision_delivery.py` / `decision_context.py`.

Same-named episodes exist in A102 under two other parents: `structural_homology_evidence/execution_progress_assessment` and `structural_homology_evidence/hpc_work_planning/execution_progress_assessment`. Their contents were not read. By file hash at `97308b94c`, each differs from this folder in `binding_record.py`, `episode.py` and the four test files; every other file is byte-identical.

## Tests in the folder

`tests/test_progress_task.py` (153 lines) states this episode's expected behaviour: observe returns the actual snapshot and credit follows received refs; invalid operations return `invalid` outcomes with their code; a child assignment must name an exposed direct dependency; the report uses delivered information and never observes; yield settings and the wait permission are preserved; an invalid action is kept and replayed without observing again; a child's delivery is recorded once. It is built on scripted stand-ins (`SimpleNamespace` services and workflow, `object.__new__` on the task) and on the old `Workflow`, `ProgressProvider` and `BindingContext`. The other three test files only run shared check classes from the old shared root.

## File by file

Counts in the last column are occurrences in the file (import lines included). `self.workflow.x` also counts `source.workflow.x`. `runtime.x` means an attribute read from the old per-axis `runtime` module. `BindingContext.x` counts reads of `context.x` / `parent.x` on the old context object. `self.services.x` is the old per-axis services provider. "old-runner callback" marks a method the old runner or old binding table called by name. The same rows are in `runs/carry_over/calls/a102_05.tsv`.

| Old file | Lines | This episode's own intent in it | Old-runner names used (name xN) |
|---|---|---|---|
| `binding_record.py` | 9 | Configuration identity: `version` `monitor_episode_binding_v1`, binding id (its own path), `outcome_page_size`, and, when its own yield is configured, `information_unit` and `yield_settings`. | `old-runner callback as_record()` x1 |
| `configuration.py` | 31 | Settings: `outcome_page_size` (int >= 1, default 32); optional `yield_settings` = exactly `{kind: 'information_accumulation', cutoff >= 0, uncertainty_alpha in (0,1)}`, which then requires `information_unit` > 0. Without `yield_settings` the caller's projector and controller own credit and continuation. Only role `monitor` is accepted. | `import root.a102.communication` x1 |
| `contracts.py` | 10 | The assignment form `monitor_assignment_v1`: `target_handle`, `requested_fields` (subset of `execution_status`, `measurements`, `log_windows`, `committed_record_refs`, `dependencies`, `result_available`), `known_progress_refs`, `permitted_committed_record_types`. Lifecycle states `pending`, `executing`, `returned`, `admitted`. | `import root.a102.domain` x1 |
| `credit.py` | 21 | Credit kind is `monitoring`. The credit view is the caller-bound role credit; the information credit calculation is `ProgressInformationCredit(progress_reader, information_unit=...)` with the unit always explicit. | `BindingContext.role` x1; `import root.a102.library.progress_information_credit` x1; `old-runner callback credit_kind()` x1; `old-runner callback credit_view()` x1; `old-runner callback information_credit()` x1; `ProgressInformationCredit` x2; `self.services.bound_role_credit` x1 |
| `decision_inputs.py` | 49 | Extra inputs added to every new decision: `resource_context`, `launch_instruction_library`, `selected_launch_instructions`, `child_options`, the binding's initial context, `completed_action_reports`, `pending_work`, `execution_expectations` captured for `monitor`, `resource_tool_estimates`, `native_execution_expectations`, `waiting_support`, `contract_information_profile`. (No `shared_information_context`, no `requested_action_history`, no job-source estimate branch, unlike the job episodes.) | `import root.a102` x1; `import root.a102.episode_work_report` x1; `import root.a102.runtime` x1; `runtime.child_option_information` x1; `runtime.Mapping` x1; `self.workflow.available_child_roles` x1; `self.workflow.binding_context` x1; `self.workflow.episode_bindings` x1; `self.workflow.execution_expectations` x1; `self.workflow.launch_instructions` x2; `self.workflow.native_estimation_context` x1; `self.workflow.pending_work` x1; `self.workflow.permits_common_action` x1; `self.workflow.resource_context` x1; `self.workflow.resource_estimator` x4; `self.workflow.waiting_support` x1 |
| `decision_state.py` | 44 | Base decision state shown to the model (same field list as the job episodes) plus `monitoring_information_credit` and `monitoring_information_binding` when the credit view carries them, plus this episode's own fields from `internal_summary.py`. | `import root.a102` x1; `import root.a102.runtime` x1; `runtime.FACT_MEANINGS` x1; `runtime.FACT_SOURCES` x1; `runtime.json` x2; `runtime.Mapping` x3; `runtime._plain` x2; `runtime._references_in` x1; `self.workflow.binding_context` x1; `self.workflow.catalog` x1; `self.workflow.controller_binding` x1; `self.workflow.delivery_status` x1; `self.workflow.extra_report_sources` x1; `self.workflow.job_episode_options` x1; `self.workflow.journal` x3; `self.workflow.knowledge` x1; `self.workflow.local_outcome_preview` x1; `self.workflow.pending_work` x1; `self.workflow.receipt_projection` x1; `self.workflow.run_id` x1; `self.workflow.source_credit_binding` x1; `self.workflow.source_credit_view` x1; `self.workflow.specialist` x1; `self.workflow.store` x3; `self.workflow.tools` x1; `self.workflow.working_state` x1; `table runtime_actions` x2; `view.child_reports` x2; `view.controller_state` x1; `view.model_inputs` x1 |
| `episode.py` | 53 | Assembles the episode: path `.../hpc_allocation_execution/execution_progress_assessment`, commissioned by `.../hpc_allocation_execution`, old role `monitor`, may be entered at `monitor`, task `ProgressMonitoringTask`, own prompt renderer `render_monitor_prompt`. Children: itself (`monitor`), allowed only while the target exposes direct dependencies. Permitted actions: `tool`, `child`, `wait`, `redeliver_report`. When the parent is the axis head and an annotation task is required, the parent must request `monitoring_progress_refs`. | `BindingContext.assignment` x1; `BindingContext.path` x1; `BindingContext.role` x2; `BindingContext.scope` x2; `commissioning_parent` x1; `decision_prompt_renderer` x1; `decision_source_type` x1; `entry_roles` x1; `import root.a102.communication` x1; `import root.a102.library.monitor_prompt` x1; `old-runner callback allowed_children()` x1; `old-runner callback child_roles()` x1; `old-runner callback permitted_common_actions()` x1; `old-runner callback prepare_child_request()` x1; `old-runner callback receive_child_progress()` x1; `old-runner callback required_return_sources()` x1; `self.services.annotation_task_required` x1; `self.services.dependencies` x1 |
| `from_child_execution_progress_assessment.py` | 20 | Taking back a child monitor's return: every `episode_progress` reference in the form must be a readable progress observation in scope; the delivery is recorded once under its operation key with a signature of form, schema and scope (a different form under the same key conflicts). | `BindingContext.episode_id` x3; `BindingContext.scope` x2; `content_digest` x2; `import root.a102.communication` x1; `import root.a102.domain` x1; `import root.a102.method_loop.durable` x1 |
| `from_parent.py` | 33 | Assignment admission: the form must match; the `target_handle` must be an execution handle in scope; every `known_progress_refs` entry must be an observation of that same target. When the parent is itself a monitor, the dependency rule of `to_child_...` applies. | `BindingContext.role` x1; `import root.a102.communication` x1; `import root.a102.domain` x1; `old-runner callback assignment_schema()` x1; `old-runner callback prepare_assignment()` x1; `self.services.read_progress` x1; `self.services.reference_in_scope` x1 |
| `goal.py` | 15 | The instruction text (quoted in full above) and the goal summary shown to the model: `objective`, `target_handle`, `requested_fields`, `unresolved_question` ("Which exposed progress information would improve the original requested report?"), `progress_definition`, `yield_settings`. | `BindingContext.assignment` x1; `BindingContext.request` x1; `BindingContext.role` x1; `BindingContext.scope` x1; `import root.a102.communication` x1; `old-runner callback instructions()` x1; `old-runner callback planning_context()` x1 |
| `__init__.py` | 1 | Empty (one blank line). | none |
| `internal_summary.py` | 13 | Own decision fields: `monitor_assignment`, `monitor_target_description`, `monitor_direct_dependencies`, `monitor_received_progress_refs`, `monitor_information_meaning` ("... Empty measurements/log windows do not assert absence or a stall."), `monitor_goal`. | `BindingContext.assignment` x1; `BindingContext.role` x1; `BindingContext.scope` x3; `import root.a102.communication` x1; `old-runner callback decision_context()` x1; `self.services.dependencies` x1; `self.services.describe_progress_target` x1 |
| `progress_operations.py` | 58 | The three tools: `progress.observe` (selected fields of the assigned target, never more than the assignment's `requested_fields`, optional `native_operation` when the target declares one; never traverses dependents), `progress.read` (an already delivered observation), `progress.log` (one retained log window of a delivered observation, read by exact byte range through `source.read`). Committed records are returned only for permitted record types. A contract error is returned as an `invalid` outcome, not raised. | `BindingContext.assignment` x2; `BindingContext.role` x1; `BindingContext.scope` x4; `import root.a102.communication` x1; `import root.a102.domain` x1; `import root.a102.episode_bindings` x1; `native_observation_options` x2; `old-runner callback catalog()` x1; `old-runner callback execute()` x1; `self.services.describe_progress_target` x1; `self.services.execute_tool` x1; `self.services.observe_progress` x1; `self.services.read_record` x2 |
| `progress_records.py` | 16 | UTC timestamp parsing (non-UTC refused) and order-preserving de-duplication. | `import root.a102.domain` x1 |
| `received_progress.py` | 30 | What counts as received progress: the assignment's `known_progress_refs`, this monitor's own action outcomes (paged by `outcome_page_size`) and progress received from child monitors; or the caller's selection when one is supplied. A progress ref not received cannot be read. | `BindingContext.assignment` x1; `BindingContext.episode_id` x2; `BindingContext.scope` x2; `import root.a102.domain` x1; `self.services.own_outcomes` x1; `self.services.progress_selection` x1; `self.services.read_progress` x1; `self.services.received_progress_refs` x1 |
| `report_delivery.py` | 25 | Closing report: the parent's form filled with recorded facts and the latest admitted interpretations, saved once. Without a report contract: `credit`, `pending_handles` and the binding's current report facts. | `import root.a102` x1; `import root.a102.library.private_policy_call` x1; `import root.a102.library.report_fact_assembly` x1; `import root.a102.runtime` x1; `_invoke_private_policy` x2; `old-runner callback finish()` x1; `runtime.form_with_facts` x1; `runtime._json` x2; `runtime.json` x1; `runtime.Record` x2; `self.workflow.binding_context` x1; `self.workflow.episode_bindings` x1; `self.workflow.facts` x1; `self.workflow.journal` x2; `self.workflow.pending_handles` x1; `self.workflow.release` x2; `self.workflow.source_credit_view` x1; `table runtime_forms` x2 |
| `task_decision.py` | 299 | One decision (inputs, save, model call or exchange, replay) with the exchange protocol inlined in this one file. The own prompt renderer is used whenever the provider supports presentation (no context test, unlike the job episodes). No job-source or literature-contract branches. | `complete_with_presentation` x1; `conversation_key` x5; `decision_prompt_renderer` x1; `has_session` x3; `import root.a102` x1; `import root.a102.runtime` x1; `instruction_composer` x1; `old-runner callback instructions()` x1; `runtime._action_generation_schema` x2; `runtime.apply_state_frame` x1; `runtime._ASSIGNMENT_TRANSPORT` x1; `runtime._category_yield_parameters` x1; `runtime.child_option_information` x1; `runtime.composition_lookup_schema` x2; `runtime.CONTRACT_INFORMATION_OPERATIONS` x1; `runtime.DECISION_CONTEXT_VERSION` x2; `runtime.DECISION_EXCHANGE_PROTOCOL` x5; `runtime._digest` x1; `runtime.Draft202012Validator` x1; `runtime.instructional_model_context` x4; `runtime.is_contract_information` x1; `runtime._json` x14; `runtime.json` x3; `runtime.lookup_attempts` x1; `runtime.Mapping` x3; `runtime.model_snapshot` x2; `runtime._object` x3; `runtime._plain` x2; `runtime._recorded_action_generation_schema` x1; `runtime._recorded_assignment_transport` x1; `runtime._references_in` x1; `runtime.requested_contract_information` x2; `runtime.schema_failure_diagnostic` x2; `runtime.sqlite3` x1; `runtime.state_frame` x1; `runtime.ValidationError` x5; `runtime.WorkflowError` x14; `runtime.yield_table` x1; `self.workflow.contract_information_profile` x1; `self.workflow.contract_information_reply` x1; `self.workflow.controller_binding` x1; `self.workflow.decision_exchanges` x4; `self.workflow.decision_protocol` x3; `self.workflow.execute` x1; `self.workflow.freeze_contract_information` x1; `self.workflow.history_preview` x1; `self.workflow.journal` x3; `self.workflow.numerical_contracts` x1; `self.workflow.provider` x3; `self.workflow.receipts` x4; `self.workflow.run_id` x1; `self.workflow.services` x2; `self.workflow.specialist` x1; `self.workflow.store` x2; `self.workflow.uses_received_record_context` x2; `self.workflow.validate_contract_information` x5; `table runtime_model_calls` x8 |
| `task_instructions.py` | 86 | This episode's full instruction composition, with its own text blocks: goal, `ACTION_BOUNDARY`, `CREDIT_COMPONENT_GUIDANCE`, `RESOURCE_ESTIMATE_GUIDANCE`, `REPORT_GUIDANCE`, history guidance (exchange or fresh-conversation variant), `HOST_EXECUTION_GUIDANCE`, tool knowledge, launch-instruction library, `REPAIR_GUIDANCE`, `WAIT_GUIDANCE`, `NATIVE_EVENT_GUIDANCE`. Imports nothing from the old runtime prompt. | `old-runner callback instructions()` x1; `self.workflow.binding_context` x1; `self.workflow.decision_protocol` x1; `self.workflow.knowledge` x1; `self.workflow.launch_instructions` x1; `self.workflow.native_event_information` x1; `self.workflow.permits_common_action` x1; `self.workflow.specialist` x1 |
| `task.py` | 182 | The episode's unit cycle. Each admitted selection is one unit; a rejected selection gives feedback and no unit; a failed model call ends the source as `source_failed`. Action kinds executed here: `wait` and tool (no `reason` branch, no automatic score updates, no shared-read retention). Credit after an action is the current credit view (a wait keeps the last observed credit). Report updates validated for grain `monitor`. Docstring: "original selected outcomes return to the ordinary iterator". | `import root.a102` x1; `import root.a102.episode_source_failure` x1; `import root.a102.library.action_contracts` x1; `import root.a102.library.private_policy_call` x1; `import root.a102.providers` x1; `import root.a102.runtime` x1; `_invoke_private_policy` x2; `ModelCallError` x2; `old-runner callback execute()` x1; `record_source_failure` x2; `runtime.ActionFailure` x1; `runtime.ContractInformationError` x1; `runtime._decode_recorded_action_response` x1; `runtime.Draft202012Validator` x2; `runtime.EventTargetError` x2; `runtime.inspect` x1; `runtime._json` x5; `runtime.json` x8; `runtime.nullcontext` x5; `runtime.observes_action_outcome` x1; `runtime.ReportBoundaryError` x1; `runtime.ReportRedelivery` x2; `runtime.schema_failure_diagnostic` x1; `runtime.SourceEnd` x2; `runtime.validate_form` x1; `runtime.ValidationError` x2; `runtime._wait_target_feedback` x2; `runtime.WorkflowError` x2; `self._execution_context` x2; `self.workflow.action_schema` x1; `self.workflow.completed_unit` x3; `self.workflow.completions` x3; `self.workflow.controller_value` x2; `self.workflow.decision_exchanges` x3; `self.workflow.delivery_resolution_inputs` x1; `self.workflow.execute` x1; `self.workflow.execution_binding` x7; `self.workflow.inprocess_replay` x4; `self.workflow.journal` x7; `self.workflow.last_observed_credit` x1; `self.workflow.next_return` x1; `self.workflow.pending_work` x1; `self.workflow.perform_selected_wait` x1; `self.workflow.receive_native_outcome` x1; `self.workflow.receive_outcome` x1; `self.workflow.resolve_pending_deliveries` x1; `self.workflow.resolver` x1; `self.workflow.run_id` x2; `self.workflow.selected` x3; `self.workflow.source_credit_view` x1; `self.workflow.store` x7; `self.workflow.validate_report` x1; `table runtime_actions` x8; `table runtime_episodes` x1; `table runtime_model_calls` x2 |
| `task_state.py` | 108 | Task state: decision counter, `feedback`, `last_outcome`, `report_values` (start from the parent's `initial_report`), `report_basis`. A selected operation that raises is recorded as a failed outcome with its credit and still enters the iterator. | `import root.a102` x1; `import root.a102.episode_source_failure` x1; `import root.a102.runtime` x1; `old-runner callback bind_execution_context()` x1; `old-runner callback record_execution_failure()` x1; `record_source_failure` x2; `runtime.ActionLeaf` x1; `runtime.EFFECT_VERSION` x1; `runtime.Episode` x1; `runtime.interpretation_schema` x1; `runtime._json` x2; `runtime.json` x4; `runtime._object` x1; `runtime._plain` x1; `runtime.Record` x1; `self._execution_context` x2; `self.workflow.archive` x1; `self.workflow.completions` x4; `self.workflow.context` x1; `self.workflow.controller_value` x1; `self.workflow.execution_binding` x4; `self.workflow.grains` x1; `self.workflow.inprocess_replay` x7; `self.workflow.journal` x5; `self.workflow.progress_provider` x2; `self.workflow.recover_commissions` x1; `self.workflow.run_id` x1; `self.workflow.source_credit_view` x1; `self.workflow.store` x2; `table runtime_actions` x5 |
| `tests/__init__.py` | 1 | Docstring only. | none |
| `tests/test_credit_behavior.py` | 5 | Runs a shared check class from the old shared root with `home` set to this episode. No body of its own. | `import root.tests.monitor_credit_behavior` x1 |
| `tests/test_progress_task.py` | 153 | Own behaviour checks: observe returns the actual snapshot and credit follows received refs; invalid operations return `invalid` outcomes; a child assignment must name an exposed direct dependency; the report uses delivered information without polling; yield settings preserved; an invalid action is kept and replayed without observing again; child receipt identity. Built on scripted stand-ins (`SimpleNamespace` services and workflow, `object.__new__` on the task) and on the old `Workflow` and `ProgressProvider`. | `BindingContext` x2; `BindingContext.assignment` x1; `BindingContext.episode_id` x3; `BindingContext.path` x1; `BindingContext.scope` x1; `import root.a102.domain` x2; `import root.a102.episode_bindings` x1; `import root.a102.episode_monitoring` x1; `import root.a102.runtime` x1; `import root.a102.state` x1; `import root.a102.structural_homology_evidence.hpc_work_planning.hpc_allocation_execution.execution_progress_assessment.episode` x1; `import root.a102.structural_homology_evidence.hpc_work_planning.hpc_allocation_execution.execution_progress_assessment.task` x1; `old-runner callback execute()` x1; `ProgressProvider` x2; `self.services.observe_progress` x1; `SimpleNamespace` x5 |
| `tests/test_prompt_behavior.py` | 5 | Runs a shared check class from the old shared root with `home` set to this episode. | `import root.tests.monitor_prompt_behavior` x1 |
| `tests/test_task_behavior.py` | 5 | Runs a shared check class from the old shared root with `home` set to this episode. | `import root.tests.monitor_task_behavior` x1 |
| `to_child_execution_progress_assessment.py` | 11 | What it sends a child monitor: a monitor assignment whose `target_handle` is one exposed direct dependency of this monitor's own target and whose `permitted_committed_record_types` do not exceed its own. | `BindingContext.assignment` x1; `BindingContext.scope` x2; `import root.a102.domain` x1; `self.services.dependencies` x1 |
| `to_parent.py` | 91 | Report facts a parent may request: `monitoring_progress_refs`, `monitoring_target_handle`, `monitoring_execution_state`, `monitoring_result_available`, `monitoring_observed_at_unix_seconds`, `monitoring_committed_record_refs`, `monitoring_dependency_handles`. Facts come from delivered observations only (latest observation of the assigned target); nothing is polled at closure. References allowed in the report: received progress refs, the target handle and handles seen in received observations, and committed records of permitted types that were actually delivered. | `BindingContext.assignment` x3; `BindingContext.role` x2; `BindingContext.scope` x6; `import root.a102.communication` x1; `import root.a102.domain` x1; `import root.a102.episode_bindings` x1; `old-runner callback facts()` x1; `old-runner callback fact_sources()` x1; `old-runner callback resolve()` x1; `old-runner callback validate_report()` x1; `reference_in_context` x2; `self.services.read_progress` x3; `self.services.read_record` x2 |
| `waiting.py` | 9 | Records the current wait condition and tells the old execution backend. | `old-runner callback suspension_changed()` x1; `self.workflow.execution_backend` x1; `self.workflow.execution_handle` x2 |
| `yield_estimator.py` | 23 | Continuation: requires its own yield settings; controller = `cutoff` + `uncertainty_alpha` with an accumulation estimate over this monitor's own action credits (credit may not decrease). Estimator binding text: credit = newly informative received snapshot count x information unit; forecast = next monitor action's information credit; stop when the predicted upper gain is at or below the cutoff. | `BindingContext.role` x1; `estimate_nonnegative_yield` x2; `import root.a102.numerical` x2; `old-runner callback yield_controller()` x1; `YieldController` x2; `YieldParameters` x2 |

## Old-runner names in this folder, by kind

| Kind | Distinct names | Uses |
|---|---|---|
| `BindingContext` and its attributes | 7 | 57 |
| `self.services.<member>` (old per-axis services) | 12 | 23 |
| `self.workflow.<member>` | 67 | 178 |
| callbacks the old runner called by name | 26 | 30 |
| imports from the old `root.a102` / `root.tests` trees | 22 | 54 |
| old `runtime` module attributes | 50 | 151 |
| old journal / receipt tables | 4 | 28 |
| old yield names | 3 | 6 |
| other old-runner names | 21 | 48 |

`self.workflow` members used: `action_schema` x1, `archive` x1, `available_child_roles` x1, `binding_context` x4, `catalog` x1, `completed_unit` x3, `completions` x7, `context` x1, `contract_information_profile` x1, `contract_information_reply` x1, `controller_binding` x2, `controller_value` x3, `decision_exchanges` x7, `decision_protocol` x4, `delivery_resolution_inputs` x1, `delivery_status` x1, `episode_bindings` x2, `execute` x2, `execution_backend` x1, `execution_binding` x11, `execution_expectations` x1, `execution_handle` x2, `extra_report_sources` x1, `facts` x1, `freeze_contract_information` x1, `grains` x1, `history_preview` x1, `inprocess_replay` x11, `job_episode_options` x1, `journal` x20, `knowledge` x2, `last_observed_credit` x1, `launch_instructions` x3, `local_outcome_preview` x1, `native_estimation_context` x1, `native_event_information` x1, `next_return` x1, `numerical_contracts` x1, `pending_handles` x1, `pending_work` x3, `perform_selected_wait` x1, `permits_common_action` x2, `progress_provider` x2, `provider` x3, `receipt_projection` x1, `receipts` x4, `receive_native_outcome` x1, `receive_outcome` x1, `recover_commissions` x1, `release` x2, `resolve_pending_deliveries` x1, `resolver` x1, `resource_context` x1, `resource_estimator` x4, `run_id` x5, `selected` x3, `services` x2, `source_credit_binding` x1, `source_credit_view` x4, `specialist` x3, `store` x14, `tools` x1, `uses_received_record_context` x2, `validate_contract_information` x5, `validate_report` x1, `waiting_support` x1, `working_state` x1.

Old tables named: `runtime_actions` x15, `runtime_episodes` x1, `runtime_forms` x2, `runtime_model_calls` x10.

Old yield names: `estimate_nonnegative_yield` x2, `YieldController` x2, `YieldParameters` x2; also `runtime.yield_table` and `runtime._category_yield_parameters` for the yield table shown to the model.

## Carried over

Source: `runs/carry_over/functions/a102__structural_homology_evidence__hpc_work_planning__hpc_allocation_execution__execution_progress_assessment.tsv`. The old files could not be read at this carry-over (no commit `97308b94c` in the available repository); the table follows the rows of that file, the intent above, and the A102 monitor library mirror `episode_support/jobs/service_calls/structural_homology_evidence/monitor_runtime.py` (read-only, not imported).

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | MonitorBindingRecord | machinery | the binding's own as_record() (configuration identity `monitor_episode_binding_v1`); the system journals settings and declared services |
| binding_record.py | MonitorBindingRecord.as_record | machinery | the binding's own as_record() (configuration identity `monitor_episode_binding_v1`); the system journals settings and declared services |
| configuration.py | MonitorConfiguration | episode function | settings: `messages/read_from_parent.py` ASSIGNMENT_FORM `information_unit` (new field); `yield_estimator.py yield_controller` (`cost`, `parameters`, same value checks); `outcome_page_size` not needed (all outcomes are in the view) |
| configuration.py | MonitorConfiguration.__init__ | episode function | settings: `messages/read_from_parent.py` ASSIGNMENT_FORM `information_unit` (new field); `yield_estimator.py yield_controller` (`cost`, `parameters`, same value checks); `outcome_page_size` not needed (all outcomes are in the view) |
| configuration.py | MonitorConfiguration._role | machinery | old role name check (`monitor` only); each role is its own episode |
| credit.py | MonitorEpisodeCredit | episode function | `credit.py credit` |
| credit.py | MonitorEpisodeCredit.credit_kind | machinery | `credit_kind` is deleted (README 3d) |
| credit.py | MonitorEpisodeCredit.credit_view | episode function | `credit.py credit` (the credit number); the other view fields are in `messages/internal_summary.py` |
| credit.py | MonitorEpisodeCredit.information_credit | episode function | `credit.py information_projection` (calls library `grading/structural_homology_evidence/progress_information_credit.py::ProgressInformationCredit`; already in library) |
| decision_inputs.py | MonitorDecisionInputs | episode function | `task.py decide` (launch_instruction_library, selected_launch_instructions); `messages/internal_summary.py`. Not carried and listed in the blocked file: resource_context, execution_expectations, resource_tool_estimates, native_execution_expectations, contract_information_profile, waiting_support, pending_work (system machinery or services not provided) |
| decision_inputs.py | MonitorDecisionInputs.decision_inputs | episode function | `task.py decide` (launch_instruction_library, selected_launch_instructions); `messages/internal_summary.py`. Not carried and listed in the blocked file: resource_context, execution_expectations, resource_tool_estimates, native_execution_expectations, contract_information_profile, waiting_support, pending_work (system machinery or services not provided) |
| decision_state.py | MonitorDecisionState | episode function | `messages/internal_summary.py internal_summary` and `task.py decide` (context); old-runner fields (pending_work, report_deliveries, report_lifecycle, receipt_projection, journal views, run_id) are machinery |
| decision_state.py | MonitorDecisionState.decision_state | episode function | `messages/internal_summary.py internal_summary` and `task.py decide` (context); old-runner fields (pending_work, report_deliveries, report_lifecycle, receipt_projection, journal views, run_id) are machinery |
| episode.py | MonitorEpisode | episode function | `episode.py ExecutionProgressAssessment` |
| episode.py | MonitorEpisode.child_roles | episode function | `task.py CHILD_SLOTS` |
| episode.py | MonitorEpisode.required_return_sources | episode function | `messages/final_to_parent.py RETURN_FORM` (fields) and `messages/msg_to_child.py` (selection) |
| episode.py | MonitorEpisode.permitted_common_actions | episode function | `task.py action` (tool and child kept; `wait` and `redeliver_report` are machinery and not carried) |
| episode.py | MonitorEpisode.allowed_children | episode function | `task.py selection_schema` (the monitor_dependency option exists only while the target exposes direct dependencies) |
| episode.py | MonitorEpisode.prepare_child_request | episode function | `messages/msg_to_child.py msg_to_child` |
| episode.py | MonitorEpisode.receive_child_progress | episode function | `messages/read_from_child.py read_from_child` |
| from_child_execution_progress_assessment.py | receive_progress | episode function | `messages/read_from_child.py read_from_child` (the recording under the operation key with a signature is machinery) |
| from_parent.py | MonitorAssignment | episode function | `messages/read_from_parent.py` ASSIGNMENT_FORM / read_from_parent |
| from_parent.py | MonitorAssignment.assignment_schema | episode function | `messages/read_from_parent.py` ASSIGNMENT_FORM / read_from_parent |
| from_parent.py | MonitorAssignment._assignment | episode function | `messages/read_from_parent.py` ASSIGNMENT_FORM / read_from_parent |
| from_parent.py | MonitorAssignment.prepare_assignment | episode function | `messages/read_from_parent.py read_from_parent`; the provider-backed admission (target is an execution handle in scope; known refs are observations of the target) is not carried (see unplaced) |
| goal.py | MonitorGoal | episode function | `goal.py GOAL`; `task.py instructions` |
| goal.py | MonitorGoal.instructions | episode function | `goal.py GOAL`; `task.py instructions` |
| goal.py | MonitorGoal.planning_context | episode function | `messages/internal_summary.py` key `monitor_goal` |
| internal_summary.py | MonitorSummary | episode function | `messages/internal_summary.py internal_summary` |
| internal_summary.py | MonitorSummary.decision_context | episode function | `messages/internal_summary.py internal_summary` |
| progress_operations.py | ProgressOperations | episode function | `task.py CATALOG`, `selection_schema` |
| progress_operations.py | ProgressOperations.catalog | episode function | `task.py CATALOG`, `selection_schema` |
| progress_operations.py | ProgressOperations.execute | episode function | `task.py progress_observe`, `progress_read`, `progress_log` (tools). observe is BLOCKED-ON-JOB-SERVICE |
| progress_records.py | _timestamp | episode function | `messages/final_to_parent.py _timestamp_seconds` (copied; library candidate) |
| progress_records.py | _unique | episode function | `messages/internal_summary.py _unique` (copied; library candidate) |
| received_progress.py | ReceivedProgress | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| received_progress.py | ReceivedProgress._received | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| received_progress.py | ReceivedProgress._snapshot | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| received_progress.py | OwnProgress | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| received_progress.py | OwnProgress._own_progress_refs | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| report_delivery.py | MonitorReportDelivery | episode function | `messages/final_to_parent.py final_to_parent` (saving the form, `runtime_forms`, release and pending_handles are machinery) |
| report_delivery.py | MonitorReportDelivery.finish | episode function | `messages/final_to_parent.py final_to_parent` (saving the form, `runtime_forms`, release and pending_handles are machinery) |
| task.py | ProgressMonitoringTask | episode function | `task.py decide` and `action` |
| task.py | ProgressMonitoringTask.next | episode function | `task.py decide` and `action` |
| task.py | ProgressMonitoringTask.apply_response | episode function | `task.py action` (rejection with feedback) |
| task.py | ProgressMonitoringTask.execute | episode function | `task.py` tools and ChildCall; the `wait` branch is machinery (not carried) |
| task_decision.py | MonitorTaskDecision | machinery | the decision machine; its episode content is in `task.py decide` |
| task_decision.py | MonitorTaskDecision.call | machinery | the model call and its saving: `decide` returns a ModelRequest, the system calls and records it |
| task_decision.py | MonitorTaskDecision.instructions | episode function | `task.py instructions` |
| task_decision.py | MonitorTaskDecision.complete_decision | machinery | model call recording and conversation state |
| task_decision.py | MonitorTaskDecision.conversation_key | machinery | model call recording and conversation state |
| task_decision.py | MonitorTaskDecision.interpretation_context | machinery | the decision-exchange loop and its saved-request checks |
| task_decision.py | MonitorTaskDecision.exchange_schema | machinery | the decision-exchange loop and its saved-request checks |
| task_decision.py | MonitorTaskDecision.exchange_response | machinery | the decision-exchange loop and its saved-request checks |
| task_decision.py | MonitorTaskDecision.validate_contract_exchange_request | machinery | the decision-exchange loop and its saved-request checks |
| task_decision.py | MonitorTaskDecision.validate_contract_exchange_history | machinery | the decision-exchange loop and its saved-request checks |
| task_decision.py | MonitorTaskDecision.exchange_decision | machinery | the decision-exchange loop and its saved-request checks |
| task_instructions.py | instructions | episode function | `task.py instructions` (goal, ACTION_BOUNDARY, CREDIT_COMPONENT_GUIDANCE, HOST_EXECUTION_GUIDANCE; the blocks about the exchange, report_update, redelivery, wait, native events and resource estimates describe actions or inputs that no longer exist) |
| task_state.py | MonitorTaskState | episode function | state is `messages/internal_summary.py` (a function of the view); the decision counter, feedback and report_values are the system's or deleted |
| task_state.py | MonitorTaskState.__init__ | episode function | state is `messages/internal_summary.py` (a function of the view); the decision counter, feedback and report_values are the system's or deleted |
| task_state.py | MonitorTaskState.bind_execution_context | machinery | checkpoint/restore, effect recording and the failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.record_execution_failure | machinery | checkpoint/restore, effect recording and the failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.restore_checkpoint | machinery | checkpoint/restore, effect recording and the failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.restore | machinery | checkpoint/restore, effect recording and the failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.record_effect | machinery | checkpoint/restore, effect recording and the failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.checkpoint | machinery | checkpoint/restore, effect recording and the failed-outcome recording (a tool returns its failure as its outcome) |
| to_child_execution_progress_assessment.py | prepare_dependency_request | episode function | `messages/msg_to_child.py msg_to_child` |
| to_parent.py | MonitorReport | episode function | `messages/final_to_parent.py` |
| to_parent.py | MonitorReport.fact_sources | episode function | `messages/final_to_parent.py RETURN_FORM` |
| to_parent.py | MonitorReport.facts | episode function | `messages/final_to_parent.py monitor_facts` and `final_to_parent` |
| to_parent.py | MonitorReport.resolve | episode function | `messages/final_to_parent.py validate_report` (references must be received progress refs) |
| to_parent.py | MonitorReport.validate_report | episode function | `messages/final_to_parent.py validate_report` (raises NotImplementedError('validate_form_not_built:A102') after the fact check) |
| waiting.py | MonitorWaiting | machinery | wait/suspension machinery |
| waiting.py | MonitorWaiting.suspension_changed | machinery | wait/suspension machinery |
| yield_estimator.py | _monitor_information_yield | machinery | episode-local estimator, deleted (README 7b: accumulation controller) |
| yield_estimator.py | MonitorEpisodeYield | episode function | `yield_estimator.py yield_controller` (AccumulationYieldController) |
| yield_estimator.py | MonitorEpisodeYield.yield_controller | episode function | `yield_estimator.py yield_controller` (AccumulationYieldController) |
