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
