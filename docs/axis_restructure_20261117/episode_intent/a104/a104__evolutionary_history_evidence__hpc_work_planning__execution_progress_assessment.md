# a104 / evolutionary_history_evidence / hpc_work_planning / execution_progress_assessment

Source: the episode's own files at commit `97308b94c`
(`git show HEAD:gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/hpc_work_planning/execution_progress_assessment/<file>`).
The `tests/` folder is not covered here, and the folder has no `grading/` or `scoring/` subfolder. Old binding class: `MonitorEpisode`. Decision
source: `ProgressMonitoringTask`. Prompt renderer: `present_task_context`, which selects `render_monitor_prompt` for monitor contexts.
Commissioning parent: `evolutionary_history_evidence/hpc_work_planning`.

## Purpose (goal, in its own words)

Role `monitor`, which is also an entry role. From `goal.py`:

> Investigate which further exposed progress information is useful for the assigned target. Use actual status,
> measured quantities, committed references and source-bound logs. Liveness establishes process presence only;
> elapsed time alone establishes neither productive work nor a stall. Unknown information stays unknown. Earlier
> outcomes and your admitted child forms inform later decisions. You may explicitly commission an ordinary monitor for
> one exposed direct dependency; no descendant traversal, fanout, cadence or depth is prescribed. Return the original
> parent's typed form at your closure even while the target remains active. Do not report private reasoning,
> intentions or unrestricted findings. Recorded facts use saved delivered observations; closure does not poll or
> compose another report with a model. *[private yield: "The monitor's information-credit projector and bound yield
> rule govern continuation." / otherwise: "The caller's monitoring projector and configured controller own credit and
> continuation."]* Repeated observation identities and read timestamps alone earn no new information.

`planning_context` (shown as `monitor_goal`) contains:
- `objective` (the request goal);
- `target_handle` and `requested_fields`;
- `unresolved_question`: "Which exposed progress information would improve the original requested report?";
- `progress_definition`: "Actual received information under the caller-bound monitoring projector; repeated identities and
  timestamps alone earn no credit.";
- `yield_settings`.

## Task and instructions

`task_instructions.instructions` composes the episode's own instructions. It does not use the A-root `INSTRUCTIONS`. In order, it joins:
- the goal;
- `ACTION_BOUNDARY`: no stop action, and no invented turn budget, approval review, quality gate, experiment, term or observation;
- `CREDIT_COMPONENT_GUIDANCE`;
- `RESOURCE_ESTIMATE_GUIDANCE`: a timing experiment earns monitoring credit for the timing information learned;
- `REPORT_GUIDANCE`;
- the history guidance: `EXCHANGE_HISTORY_GUIDANCE` under `decision_exchange_v1`, otherwise `HISTORY_GUIDANCE`;
- `HOST_EXECUTION_GUIDANCE`.

It then appends the tool knowledge and the launch-instruction library when they are present, and `REPAIR_GUIDANCE` for `pending_child_delivery`. When
wait is permitted, it also appends `WAIT_GUIDANCE`, plus `NATIVE_EVENT_GUIDANCE` when native event information exists.

`task.py` follows the common loop and has no reason action. `action_execution.execute` handles `tool` and `wait` only. It has no automatic
score updates and no shared-grading retention, unlike Results.

## What it reads from its parent's assignment

The assignment is `monitor_assignment_v1` (`contracts._ASSIGNMENT`, checked by `from_parent._assignment`). It has these fields:
- `target_handle`. It must be in scope as an `execution_handle` (`services.reference_in_scope`).
- `requested_fields`. This is a subset of `execution_status`, `measurements`, `log_windows`, `committed_record_refs`, `dependencies` and
  `result_available`.
- `known_progress_refs`. Each must be a progress snapshot of the same target.
- `permitted_committed_record_types`, drawn from `RECORD_SCHEMAS`.

`prepare_assignment` requires a non-empty operation_key. When the parent is itself a monitor, the assignment also passes
`prepare_dependency_request`.

## Children

- **`monitor` (itself, recursively).** It is allowed only when `services.dependencies(target_handle)` is non-empty.
  - Sent: `to_child_execution_progress_assessment.prepare_dependency_request` produces a `monitor_assignment_v1`. Its `target_handle` must be
    an exposed direct dependency of the parent's target, and its `permitted_committed_record_types` may not widen the parent's.
  - Taken back: `from_child_execution_progress_assessment.receive_progress` validates the child's typed form and reads each
    `episode_progress` reference in scope. It admits them into the provider's received-progress index under a `content_digest` of form,
    schema and scope. They then count as received progress for this monitor (`received_progress._received`).
- The module's `assemble_request` is the old child-request builder (EpisodeGoal/EpisodeRequest, `knowledge_inheritance` receipts). It is
  not intent.

## Decision state and what the model sees

The common decision state (`decision_state.py`) holds:
- goal, scope, working_state and visible_record_refs;
- current_credit and current_evidence_vector, credit_binding and time_accounting;
- pending_work, last_local_outcome, feedback and visual_evidence;
- report_deliveries, controller and controller_binding;
- tools, tool_knowledge and job_episode_options;
- available_report_facts, requested_report_purpose/requested_form, and current_report_update with its basis refs.

When the credit view carries them, `monitoring_information_credit` and `monitoring_information_binding` are added.

`decision_inputs.py` adds:
- resource_context and launch_instruction_library;
- selected_launch_instructions and child_options;
- completed_action_reports and pending_work;
- execution_expectations under role `monitor`, with job_execution_options when search_modes are configured;
- resource_tool_estimates and native_execution_expectations;
- native_event_targets and waiting_support;
- contract_information_profile.

The episode's own `internal_summary.decision_context` contributes:
- `monitor_assignment` and `monitor_target_description`;
- `monitor_direct_dependencies` and `monitor_received_progress_refs`;
- `monitor_information_meaning`: "Exposed direct relationships and already delivered observations. Empty measurements/log windows do not
  assert absence or a stall.";
- `monitor_goal`.

## Tools

The tools come from `progress_operations.catalog`:
- **`progress.observe`.** It takes `requested_fields`, which must stay within the assignment's fields. When the target descriptor supplies a
  `selected_observation_schema`, it also takes `native_operation`. It observes the assigned target once and never traverses dependent work.
  Committed refs are filtered to the permitted record types.
- **`progress.read`.** It reads an already delivered snapshot (`progress_ref`).
- **`progress.log`.** It takes `progress_ref` and `log_index`. It reads one retained log window through `source.read` and checks that the
  window's artifact is one of the source's representations.

Any ContractError becomes an `invalid` outcome with `arguments_or_reference` feedback. The common actions are tool, child, wait and
redeliver_report.

The observers under this folder do the native observation behind `progress.observe`. They are domain support used by other episodes too:
Results and Launch import `APIObserver`.
- `api_observer` handles generic API services.
- `hmmer_observer` handles EBI HMMER and uses the `api_execution_observations` table.
- `appservice_observer` handles BV-BRC AppService (query_tasks, stdout and stderr). It checks the selected action and makes no remote
  mutation.

## Credit

The credit kind is `monitoring`. `credit_view` passes through to the caller-bound projector (`services.bound_role_credit`). With a private
yield binding, `information_credit` builds `ProgressInformationCredit(progress_reader, information_unit=...)`: credit is the count of newly
informative received snapshots × `information_unit`. Repeated identities and timestamps earn nothing, and decreasing credit is rejected.
Credit is not bounded.

## Continuation

When `yield_settings` is configured (`{kind: information_accumulation, cutoff >= 0, uncertainty_alpha in (0,1)}` plus a positive
`information_unit`), `yield_estimator.MonitorEpisodeYield.yield_controller` builds an old `YieldController(epoch, initial_credit, cutoff,
YieldParameters(uncertainty_alpha))`. Its estimator is `_monitor_information_yield`, which uses `estimate_nonnegative_yield` and binding
`monitor_information_accumulation_v1`. It stops when the predicted upper gain is at or below the cutoff. Without private settings, the
caller's controller governs.

Current-runner equivalent: **accumulation** (`yield_control.AccumulationYieldController` / `AccumulationYieldEstimator`), with settings
`cutoff` and `uncertainty_alpha`. The operand `information_unit` belongs to the credit, not to the estimator.

## Report to parent

`to_parent.fact_sources` and `facts` supply:
- `monitoring_progress_refs`: delivered observation identities, including admitted child updates;
- `monitoring_target_handle`;
- `monitoring_execution_state`: the latest lifecycle state, or null without an observation;
- `monitoring_result_available`;
- `monitoring_observed_at_unix_seconds`;
- `monitoring_committed_record_refs`: permitted types only;
- `monitoring_dependency_handles`.

`validate_report` checks that every x-source field equals the recorded fact. Every committed-record reference in the form must have a
permitted type and must have been received. Progress and execution namespaces resolve only to received snapshots and their target or
dependency handles.

## Differences from similar episodes

- Compared with its HPC sibling `hpc_allocation_execution` (the same task family): this monitor carries the full private instruction
  constants (ACTION_BOUNDARY, CREDIT_COMPONENT, RESOURCE_ESTIMATE, REPORT and HISTORY guidance), and its decision state has the
  annotation-axis-credit and monitoring-information-credit branches. The HPC parent's composition is goal + library + repair + wait only.
- Its `presentation` and `presentation_selection` are identical to the `hpc_allocation_execution` parent's copies. The parent's
  `decision_state`, `decision_inputs` and `decision_exchange` belong to the same task family but drop the annotation-axis and
  monitoring-information-credit branches, use role `hpc_execution` for expectations, and add `requested_action_history`.
- Unlike Results and Launch, it has no `reason` action, no `automatic_score_updates` and no shared grading retention.

## Files

Old-runner names are listed as `name×uses`. `workflow.*` means `self.workflow.*` / `source.workflow.*` / `workflow.*`. `BindingContext .x` means the old binding-context attribute `context.x` / `parent.x`. `table x` is a journal or receipt table named in SQL or in `journal.row/save`. The full per-use list is in `runs/carry_over/calls/a104_04.tsv`.

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 1 | Empty package marker. | none |
| `action_admission.py` | 67 | Admit a model response: decode, validate selection, admit report_update against the interpretation schema with grain `monitor`; invalid selections become `action_contract` feedback (with the closed-top-level-form repair hint). Own intent: the admission/feedback rules; the rest is old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; ActionFailure×1; bind_functions×2; _bind_preserved_runtime_providers×2; ReportRedelivery×3; SourceEnd×1; WorkflowError×1; table runtime_actions×1; table runtime_model_calls×1; workflow.decision_exchanges×3; workflow.execution_binding×1; workflow.journal×2; workflow.resolver×1; workflow.selected×1; workflow.store×1; workflow.validate_report×1 |
| `action_execution.py` | 75 | Execute a selected tool or wait; a wait's credit is the last observed credit, a tool's is the current credit view; failed outcomes raise ActionFailure into the iterator. Own intent: tool/wait only (no reason, no automatic score updates). | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; ActionFailure×2; bind_functions×2; _bind_preserved_runtime_providers×2; ReportRedelivery×1; SourceEnd×1; WorkflowError×2; table runtime_actions×5; workflow.completions×1; workflow.controller_value×2; workflow.execute×1; workflow.execution_binding×4; workflow.journal×1; workflow.last_observed_credit×1; workflow.pending_work×1; workflow.perform_selected_wait×1; workflow.receive_native_outcome×1; workflow.receive_outcome×1; workflow.run_id×1; workflow.source_credit_view×1; workflow.store×3 |
| `api_observer.py` | 58 | Observe an API execution target (generic API service, HMMER API via HMMERObserver, BV-BRC AppService via AppServiceObserver), with immutable per-operation-key intent/snapshot/observation files. Domain support, not binding. | root.a104.evolutionary_history_evidence.* (absolute own-tree path)×2; root.a104.library.api_record_values×1 |
| `appservice_observer.py` | 136 | BV-BRC AppService progress observation: authenticates the selected progress.observe action and native_operation (query_tasks/stdout/stderr/...), prepares a non-mutating observation, retains response once, projects native status/timing/log bytes; unobserved state stays `unknown`. Domain support. | BindingContext .episode_id×2; BindingContext .scope×2; root.a104.library.appservice_monitor_custody×1; root.a104.library.appservice_monitor_values×1; table runtime_actions×1 |
| `binding_record.py` | 9 | Binding record: version `monitor_episode_binding_v1`, outcome_page_size, and (when private yield) information_unit + yield_settings. | none |
| `configuration.py` | 31 | Construction operands: outcome_page_size (positive int, default 32), optional private yield settings `{kind: information_accumulation, cutoff >= 0, uncertainty_alpha in (0,1)}` requiring a positive information_unit; `_role` accepts only `monitor`. | root.a104.communication×1 |
| `contracts.py` | 10 | Assignment contract `monitor_assignment_v1` (target_handle, requested_fields subset of FIELDS, known_progress_refs, permitted_committed_record_types); FIELDS; lifecycle states pending/executing/returned/admitted. | root.a104.domain×1 |
| `credit.py` | 21 | Credit kind `monitoring`; credit_view delegates to the caller-bound projector (`services.bound_role_credit`); information_credit builds ProgressInformationCredit with an explicit information_unit. | BindingContext .role×1; root.a104.library.progress_information_credit×1; self.services.bound_role_credit×1 |
| `decision_contracts.py` | 133 | Decision-exchange envelope (request_context vs select_action) and replay validation of contract-information exchanges. Old-runner machinery; no episode-specific intent beyond the docstring rule "do not add a whole-action schema gate". | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; WorkflowError×10; table runtime_model_calls×1; workflow.contract_information_reply×1; workflow.decision_exchanges×2; workflow.journal×1; workflow.store×2; workflow.validate_contract_information×2; _category_yield_parameters×1; yield_table×1 |
| `decision_exchange.py` | 112 | request_context lookup loop for one pending decision (child_options, composition_information, own-attempt lookups). Old-runner machinery; annotation-axis yield table branch present but not this episode's. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; WorkflowError×1; table runtime_model_calls×2; workflow.controller_binding×1; workflow.decision_exchanges×1; workflow.execute×1; workflow.journal×1; workflow.run_id×1; workflow.services×1; workflow.validate_contract_information×1; _category_yield_parameters×2; yield_table×2 |
| `decision_inputs.py` | 69 | Adds to the decision context: resource context, launch-instruction library, selected launch instructions, child_options, completed_action_reports, pending_work, execution_expectations (role `monitor`), resource_tool_estimates, native execution expectations, native_event_targets, waiting_support, contract_information_profile. | import root.a104×1; root.a104.episode_work_report×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; workflow.available_child_roles×1; workflow.binding_context×2; workflow.episode_bindings×1; workflow.execution_expectations×1; workflow.job_episodes×2; workflow.launch_instructions×2; workflow.native_estimation_context×1; workflow.native_event_information×2; workflow.pending_work×1; workflow.permits_common_action×1; workflow.resource_context×1; workflow.resource_estimator×4; workflow.store×2; workflow.waiting_support×1 |
| `decision_provider.py` | 61 | Chooses complete_with_presentation with this binding's prompt renderer when the provider is unmodified. Old-runner/provider machinery. | root.a104.providers×2; root.a104.runtime×1; import root.providers×1; WorkflowError×1; workflow.provider×1; workflow.specialist×2; _category_yield_parameters×1; yield_table×1 |
| `decision_state.py` | 53 | Decision context shown to the model: goal, scope, working state, visible refs, current credit/evidence vector, credit_binding, time_accounting, pending_work, last outcome, feedback, report_deliveries, controller state, tools, tool knowledge, job options, available report facts, requested form/purpose, current report; plus monitoring_information_credit and the binding's own decision_context. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; view.child_reports×2; view.controller_state×1; view.model_inputs×1; table runtime_actions×2; workflow.binding_context×1; workflow.catalog×1; workflow.controller_binding×1; workflow.delivery_status×1; workflow.extra_report_sources×1; workflow.job_episode_options×1; workflow.journal×3; workflow.knowledge×1; workflow.local_outcome_preview×1; workflow.pending_work×1; workflow.receipt_projection×1; workflow.run_id×1; workflow.source_credit_binding×1; workflow.source_credit_view×1; workflow.specialist×1; workflow.store×3; workflow.tools×1; workflow.working_state×1 |
| `episode.py` | 59 | MonitorEpisode composition: binding_path, commissioning parent `evolutionary_history_evidence/hpc_work_planning`, role/entry role `monitor`, child role `monitor` only when the target has exposed direct dependencies, common actions tool/child/wait/redeliver_report, required return source `monitoring_progress_refs` under an annotation-task parent, child request/progress hooks. | BindingContext .assignment×1; BindingContext .path×1; BindingContext .role×2; BindingContext .scope×2; root.a104.communication×1; self.services.annotation_task_required (getattr)×1; self.services.dependencies×1 |
| `from_child_execution_progress_assessment.py` | 20 | Receive a recursive monitor child's typed form: collect `episode_progress` references (each read in scope), sign form/schema/scope with content_digest, admit into the provider's received-progress index. | BindingContext .episode_id×3; BindingContext .scope×2; root.a104.communication×1; root.a104.domain×1; root.a104.method_loop.durable×1; content_digest×2 |
| `from_parent.py` | 33 | Read the parent's assignment: validate schema, target_handle must be an in-scope `execution_handle`, every known_progress_ref must be a snapshot of the same target; prepare_assignment requires an operation_key and, when the parent is a monitor, applies the dependency rule. | BindingContext .role×1; root.a104.communication×1; root.a104.domain×1; self.services.read_progress×1; self.services.reference_in_scope×1 |
| `goal.py` | 15 | Goal text (see Purpose) and planning_context (objective, target_handle, requested_fields, unresolved question, progress definition, yield_settings). | BindingContext .assignment×1; BindingContext .request×1; BindingContext .role×1; BindingContext .scope×1; root.a104.communication×1 |
| `hmmer_observer.py` | 46 | EBI HMMER API status observation with an `api_execution_observations` row per operation key; unknown outcome recorded when the response is lost. Domain support. | root.a104.api_error_feedback×1; root.a104.library.hmmer_record_values×1; table api_execution_observations×4 |
| `internal_summary.py` | 13 | decision_context: monitor_assignment, target description, direct dependencies, received progress refs, information meaning ("empty measurements/log windows do not assert absence or a stall"), monitor_goal. | BindingContext .assignment×1; BindingContext .role×1; BindingContext .scope×3; root.a104.communication×1; self.services.dependencies×1; self.services.describe_progress_target (getattr)×1 |
| `own_progress.py` | 16 | Page through own action outcomes (outcome_page_size) collecting progress_refs. | BindingContext .episode_id×1; root.a104.domain×1; self.services.own_outcomes×1 |
| `presentation.py` | 42 | Text-task prompt rendering over decision frames (bootstrap/update/lookup) via the selected renderer; otherwise raw JSON. Provider presentation machinery. | root.a104.providers×1 |
| `presentation_selection.py` | 30 | Renderer selection: hpc / published scientific / api launch / selected execution / monitor / receiver prompt. | root.a104.evolutionary_history_evidence_prompt×2; root.a104.library.hpc_prompt×1; root.a104.library.monitor_prompt×1; root.a104.native_profile_presentation×1; root.a104.providers×1; root.a104.receiver_prompt×1 |
| `progress_operations.py` | 58 | Tools: `progress.observe` (selected requested_fields within the assignment, optional native_operation from the target descriptor), `progress.read` (delivered snapshot), `progress.log` (exact retained log window via source.read, byte custody checked). Committed refs filtered to permitted record types; errors become `invalid` outcomes. | BindingContext .assignment×2; BindingContext .role×1; BindingContext .scope×4; root.a104.communication×1; root.a104.domain×1; root.a104.episode_bindings×1; self.services.describe_progress_target (getattr)×1; self.services.execute_tool×1; self.services.observe_progress×1; self.services.read_record×2 |
| `progress_records.py` | 16 | UTC timestamp parsing (Z or +00:00 only) and order-preserving unique. | root.a104.domain×1 |
| `received_progress.py` | 20 | Received progress = known_progress_refs + own outcome progress refs + child-received refs (or a caller progress_selection); a snapshot may be read only if received. | BindingContext .assignment×1; BindingContext .episode_id×1; BindingContext .scope×2; root.a104.domain×1; self.services.progress_selection (getattr)×1; self.services.read_progress×1; self.services.received_progress_refs×1 |
| `report_delivery.py` | 32 | finish(): without a report contract returns credit + pending handles + current facts; with one, reuses a saved form or fills the form from facts and saves it. Old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; form_with_facts×2; Record×3; table runtime_forms×2; workflow.binding_context×1; workflow.episode_bindings×1; workflow.facts×1; workflow.journal×2; workflow.pending_handles×1; workflow.release×2; workflow.source_credit_view×1 |
| `task.py` | 102 | ProgressMonitoringTask.next(): replay/restore paths, then call the model and apply the response; a model-call error records a source failure and ends the source. Old-runner machinery. | import root.a104×1; root.a104.episode_source_failure×1; root.a104.library.live_runtime_functions×1; root.a104.providers×1; root.a104.runtime×1; ActionFailure×1; bind_functions×2; _bind_preserved_runtime_providers×2; ReportRedelivery×1; SourceEnd×3; view.units_consumed×4; WorkflowError×2; table runtime_actions×2; table runtime_episodes×1; table runtime_model_calls×1; workflow.action_schema×1; workflow.completed_unit×3; workflow.completions×2; workflow.delivery_resolution_inputs×1; workflow.execution_binding×2; workflow.inprocess_replay×4; workflow.journal×4; workflow.next_return×1; workflow.resolve_pending_deliveries×1; workflow.run_id×1; workflow.selected×2; workflow.store×3 |
| `task_decision.py` | 93 | One decision call: saved-request replay checks, exchange protocol, restored history on a fresh session, journaled request/response. Old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; WorkflowError×6; table runtime_model_calls×5; workflow.contract_information_profile×1; workflow.decision_exchanges×1; workflow.decision_protocol×3; workflow.freeze_contract_information×1; workflow.history_preview×1; workflow.journal×1; workflow.numerical_contracts×1; workflow.provider×2; workflow.receipts×4; workflow.services×1; workflow.uses_received_record_context×2; workflow.validate_contract_information×2; _category_yield_parameters×1; yield_table×1 |
| `task_instructions.py` | 86 | The episode's own instruction composition (see Task and instructions). | workflow.binding_context×1; workflow.decision_protocol×1; workflow.knowledge×1; workflow.launch_instructions×1; workflow.native_event_information×1; workflow.permits_common_action×1; workflow.specialist×1 |
| `task_state.py` | 117 | Task state fields (report values/basis, feedback, last outcome) and restore/checkpoint/record_effect; failed execution recorded as a failed own action with credit. Old-runner machinery. | import root.a104×1; root.a104.episode_source_failure×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; ActionLeaf×2; bind_functions×2; _bind_preserved_runtime_providers×2; Episode.identity×1; Record×2; table runtime_actions×5; workflow.archive×1; workflow.completions×4; workflow.context×1; workflow.controller_value×1; workflow.execution_binding×4; workflow.grains×1; workflow.inprocess_replay×7; workflow.journal×5; workflow.progress_provider×2; workflow.recover_commissions×1; workflow.run_id×1; workflow.source_credit_view×1; workflow.store×2 |
| `to_child_execution_progress_assessment.py` | 41 | prepare_dependency_request: child target must be an exposed direct dependency of the parent target; permitted record types may not widen. assemble_request: old child-request construction. | BindingContext .assignment×1; BindingContext .scope×2; root.a104.domain×1; root.a104.episode_contract_information×1; root.a104.runtime×1; EpisodeGoal×3; Episode.identity×2; EpisodeRequest×2; Record×2; self.services.dependencies×1; workflow.context×2; workflow.evolutionary_history_evidence_binding×1; workflow.grains×2; workflow.inprocess_completion_order×2; workflow.launch_instructions×1; workflow.receipts×2 |
| `to_parent.py` | 91 | Report facts (monitoring_progress_refs, target_handle, execution_state, result_available, observed_at_unix_seconds, committed_record_refs, dependency_handles), reference resolution and report validation (recorded facts must match; committed records must be permitted and received). | BindingContext .assignment×3; BindingContext .role×2; BindingContext .scope×6; root.a104.communication×1; root.a104.domain×1; root.a104.episode_bindings×1; self.services.read_progress×3; self.services.read_record×2 |
| `waiting.py` | 9 | suspension_changed: forwards the wait condition to the execution backend. | workflow.execution_backend×1; workflow.execution_handle×2 |
| `yield_estimator.py` | 23 | Private information-accumulation yield: credit = newly informative received snapshot count x information_unit, decreasing credit rejected, estimate_nonnegative_yield, stop when predicted upper gain <= cutoff; only when private yield is enabled. | BindingContext .role×1; root.a104.numerical×2; estimate_nonnegative_yield×2; YieldController×2; YieldParameters×2 |

## Carried over

Source: `runs/carry_over/functions/a104__evolutionary_history_evidence__hpc_work_planning__execution_progress_assessment.tsv` (one row per row of that file). The old files were read with `git show 97308b94c:<path>` from the repository clone `/home/chia/repos/gene_annotation_episode_disk` (this checkout has no `.git`). The folder follows the finished A102 monitor carry-over in shape only (copied, not imported), with A104's own library pieces and transport.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| action_admission.py | ProgressMonitoringTaskAdmission | episode function | `task.py action` (decode, validate against the closed selection schema, `Rejected(feedback)`); the journal rows for rejected answers, `validate_report` of the delivery and `execution_binding` calls are machinery |
| action_admission.py | ProgressMonitoringTaskAdmission.apply_response | episode function | `task.py action` (decode, validate against the closed selection schema, `Rejected(feedback)`); the journal rows for rejected answers, `validate_report` of the delivery and `execution_binding` calls are machinery |
| action_admission.py | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| action_execution.py | ProgressMonitoringTaskExecution | episode function | `task.py` tools `progress_observe`, `progress_read`, `progress_log` and `ChildCall`; the journal action rows, the wait branch, `controller_value`, `last_observed_credit` and `receive_outcome` are machinery (the system journals the unit and prices it with `credit.py`) |
| action_execution.py | ProgressMonitoringTaskExecution.execute | episode function | `task.py` tools `progress_observe`, `progress_read`, `progress_log` and `ChildCall`; the journal action rows, the wait branch, `controller_value`, `last_observed_credit` and `receive_outcome` are machinery (the system journals the unit and prices it with `credit.py`) |
| action_execution.py | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| api_observer.py | APIObserver | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| api_observer.py | APIObserver.__init__ | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| api_observer.py | APIObserver._observation | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| api_observer.py | APIObserver.observe_target | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| appservice_observer.py | AppServiceObserver | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| appservice_observer.py | AppServiceObserver._selection | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| appservice_observer.py | AppServiceObserver._prepare | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| appservice_observer.py | AppServiceObserver._response | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| appservice_observer.py | AppServiceObserver._source | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| appservice_observer.py | AppServiceObserver._project | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| appservice_observer.py | AppServiceObserver.observe | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| binding_record.py | MonitorBindingRecord | machinery | the binding's own as_record() (configuration identity `monitor_episode_binding_v1`); the system journals settings and declared services |
| binding_record.py | MonitorBindingRecord.as_record | machinery | the binding's own as_record() (configuration identity `monitor_episode_binding_v1`); the system journals settings and declared services |
| configuration.py | MonitorConfiguration | episode function | settings: `messages/read_from_parent.py` ASSIGNMENT_FORM `information_unit` (new field); `yield_estimator.py yield_controller` (`cost`, `parameters`, same value checks); `outcome_page_size` not needed (all outcomes are in the view) |
| configuration.py | MonitorConfiguration.__init__ | episode function | settings: `messages/read_from_parent.py` ASSIGNMENT_FORM `information_unit` (new field); `yield_estimator.py yield_controller` (`cost`, `parameters`, same value checks); `outcome_page_size` not needed (all outcomes are in the view) |
| configuration.py | MonitorConfiguration._role | machinery | old role name check (`monitor` only); each role is its own episode |
| credit.py | MonitorEpisodeCredit | episode function | `credit.py credit` |
| credit.py | MonitorEpisodeCredit.credit_kind | machinery | `credit_kind` is deleted (README 3d) |
| credit.py | MonitorEpisodeCredit.credit_view | episode function | `credit.py credit` (the number); the other view fields are in `messages/internal_summary.py` |
| credit.py | MonitorEpisodeCredit.information_credit | episode function | `credit.py information_projection` (calls library `grading/evolutionary_history_evidence/progress_information_credit.py::ProgressInformationCredit`; already in library) |
| decision_contracts.py | MonitorTaskDecisionContracts | machinery | the decision-exchange contract validation and saved-request checks (README 3a) |
| decision_contracts.py | MonitorTaskDecisionContracts.interpretation_context | machinery | the decision-exchange contract validation and saved-request checks (README 3a) |
| decision_contracts.py | MonitorTaskDecisionContracts.exchange_schema | machinery | the decision-exchange contract validation and saved-request checks (README 3a) |
| decision_contracts.py | MonitorTaskDecisionContracts.exchange_response | machinery | the decision-exchange contract validation and saved-request checks (README 3a) |
| decision_contracts.py | MonitorTaskDecisionContracts.validate_contract_exchange_request | machinery | the decision-exchange contract validation and saved-request checks (README 3a) |
| decision_contracts.py | MonitorTaskDecisionContracts.validate_contract_exchange_history | machinery | the decision-exchange contract validation and saved-request checks (README 3a) |
| decision_contracts.py | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| decision_exchange.py | MonitorTaskDecisionExchange | machinery | the decision-exchange loop and its saved-request checks (README 3a) |
| decision_exchange.py | MonitorTaskDecisionExchange.exchange_decision | machinery | the decision-exchange loop and its saved-request checks (README 3a) |
| decision_exchange.py | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| decision_inputs.py | MonitorDecisionInputs | episode function | `task.py decide` (launch_instruction_library, selected_launch_instructions, tool_knowledge) and `messages/internal_summary.py`. Not carried, listed in the blocked file: resource_context, execution_expectations, resource_tool_estimates, native expectations, waiting support, contract profile, completed_action_reports, child options (services not provided or old-runner state) |
| decision_inputs.py | MonitorDecisionInputs.decision_inputs | episode function | `task.py decide` (launch_instruction_library, selected_launch_instructions, tool_knowledge) and `messages/internal_summary.py`. Not carried, listed in the blocked file: resource_context, execution_expectations, resource_tool_estimates, native expectations, waiting support, contract profile, completed_action_reports, child options (services not provided or old-runner state) |
| decision_inputs.py | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| decision_provider.py | MonitorTaskDecisionProvider | machinery | provider patching and presentation routing of the old model class (`decision_completion`); the system calls the model for the `ModelRequest` `decide` returns |
| decision_provider.py | MonitorTaskDecisionProvider.decision_completion | machinery | provider patching and presentation routing of the old model class (`decision_completion`); the system calls the model for the `ModelRequest` `decide` returns |
| decision_state.py | MonitorDecisionState | episode function | `messages/internal_summary.py internal_summary` and `task.py decide` (context); old-runner fields (pending_work, report_deliveries, receipt_projection, journal views, run_id) are machinery |
| decision_state.py | MonitorDecisionState.decision_state | episode function | `messages/internal_summary.py internal_summary` and `task.py decide` (context); old-runner fields (pending_work, report_deliveries, receipt_projection, journal views, run_id) are machinery |
| decision_state.py | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| episode.py | MonitorEpisode | episode function | `episode.py ExecutionProgressAssessment` |
| episode.py | MonitorEpisode.child_roles | episode function | `task.py CHILD_SLOTS` |
| episode.py | MonitorEpisode.required_return_sources | episode function | `messages/final_to_parent.py RETURN_FORM` (selectable fields) and the selection of the parent's `msg_to_child.py` |
| episode.py | MonitorEpisode.permitted_common_actions | episode function | `task.py action` (tool and child kept; `wait` and `redeliver_report` are machinery and not carried) |
| episode.py | MonitorEpisode.allowed_children | episode function | `task.py selection_schema` (the monitor_dependency option exists only while the target exposes direct dependencies) |
| episode.py | MonitorEpisode.prepare_child_request | episode function | `messages/msg_to_child.py msg_to_child` |
| episode.py | MonitorEpisode.child_request_assembler | machinery | old child request assembly (`assemble_request`: goal, scope, initial report, report contract declaration, knowledge inheritance); the system derives the child goal and reporting contract from `ChildMessage` |
| episode.py | MonitorEpisode.receive_child_progress | episode function | `messages/read_from_child.py read_from_child` |
| from_child_execution_progress_assessment.py | receive_progress | episode function | `messages/read_from_child.py read_from_child` (the recording under the operation key with a content signature is machinery) |
| from_parent.py | MonitorAssignment | episode function | `messages/read_from_parent.py` ASSIGNMENT_FORM / read_from_parent |
| from_parent.py | MonitorAssignment.assignment_schema | episode function | `messages/read_from_parent.py` ASSIGNMENT_FORM / read_from_parent |
| from_parent.py | MonitorAssignment._assignment | episode function | `messages/read_from_parent.py` ASSIGNMENT_FORM / read_from_parent |
| from_parent.py | MonitorAssignment.prepare_assignment | episode function | `messages/read_from_parent.py read_from_parent`; the provider-backed admission (target is an execution handle in scope; known refs are observations of the target) and the operation key requirement are not carried (see blocked file) |
| goal.py | MonitorGoal | episode function | `goal.py GOAL`; `task.py instructions` |
| goal.py | MonitorGoal.instructions | episode function | `goal.py GOAL`; `task.py instructions` |
| goal.py | MonitorGoal.planning_context | episode function | `messages/internal_summary.py` key `monitor_goal` |
| hmmer_observer.py | HMMERObserver | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| hmmer_observer.py | HMMERObserver.__init__ | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| hmmer_observer.py | HMMERObserver.observe_target | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| hmmer_observer.py | HMMERObserver._unknown_observation | episode function | NOT PLACED, BLOCKED-ON-JOB-SERVICE: the old provider-backed observer of one job kind (target files, intents and snapshots under the reader directory, raw Store SQL); this is what `job_access.observe_progress` does for the commissioned target (see the blocked file). `task.py progress_observe` names `ctx.services['job_access'].observe_progress(...)` and raises where it is reached. Library candidate (old form: `store.db`, files under the reader directory) |
| internal_summary.py | MonitorSummary | episode function | `messages/internal_summary.py internal_summary` |
| internal_summary.py | MonitorSummary.decision_context | episode function | `messages/internal_summary.py internal_summary` |
| own_progress.py | OwnProgress | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| own_progress.py | OwnProgress._own_progress_refs | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| presentation.py | present_task_context | machinery | `decision_prompt_renderer` / `present_task_context`: the renderer selection and per-episode prompt state across bootstrap/update/lookup frames (conversation state, README 3a); the episode's own rendering is the `ModelRequest.context` built in `task.py decide` |
| presentation_selection.py | task_presentation_selection | machinery | renderer selection table of the old presenter (README 3a prompt renderers; the old monitor renderer lives in the old shared prompt modules); `task.py decide` puts the context in the request |
| progress_operations.py | ProgressOperations | episode function | `task.py CATALOG`, `selection_schema` |
| progress_operations.py | ProgressOperations.catalog | episode function | `task.py CATALOG`, `selection_schema` |
| progress_operations.py | ProgressOperations.execute | episode function | `task.py progress_observe`, `progress_read`, `progress_log` (tools). observe is BLOCKED-ON-JOB-SERVICE; the `native_operation` argument is not carried (blocked file) |
| progress_records.py | _timestamp | episode function | `messages/final_to_parent.py _timestamp_seconds` (copied; library candidate) |
| progress_records.py | _unique | episode function | `messages/internal_summary.py _unique` (copied; library candidate) |
| received_progress.py | ReceivedProgress | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| received_progress.py | ReceivedProgress._received | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| received_progress.py | ReceivedProgress._snapshot | episode function | `messages/internal_summary.py` (received_progress_refs, progress_snapshots, monitor_received_progress_refs) |
| report_delivery.py | MonitorReportDelivery | episode function | `messages/final_to_parent.py final_to_parent` (saving the form in `runtime_forms`, release and pending_handles are machinery) |
| report_delivery.py | MonitorReportDelivery.finish | episode function | `messages/final_to_parent.py final_to_parent` (saving the form in `runtime_forms`, release and pending_handles are machinery) |
| report_delivery.py | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| task.py | ProgressMonitoringTask | episode function | `task.py decide` and `action`; the loop, `completed_unit`, `inprocess_replay`, journal rows and pending deliveries are machinery |
| task.py | ProgressMonitoringTask.next | episode function | `task.py decide` and `action`; the loop, `completed_unit`, `inprocess_replay`, journal rows and pending deliveries are machinery |
| task.py | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| task_decision.py | MonitorTaskDecision | machinery | conversation state (`conversation_key`) |
| task_decision.py | MonitorTaskDecision.call | machinery | the model call and its saving: `decide` returns a ModelRequest, the system calls and records it; its decision assembly content is in `task.py decide` |
| task_decision.py | MonitorTaskDecision.instructions | episode function | `task.py instructions` |
| task_decision.py | MonitorTaskDecision.conversation_key | machinery | conversation state (`conversation_key`) |
| task_decision.py | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| task_instructions.py | instructions | episode function | `task.py instructions` (goal, ACTION_BOUNDARY, CREDIT_COMPONENT_GUIDANCE, HOST_EXECUTION_GUIDANCE; the blocks about the exchange, report_update, redelivery, wait, native events and resource estimates describe machinery or services that are gone and are not carried) |
| task_state.py | MonitorTaskState | episode function | state is `messages/internal_summary.py` (a function of the view); the decision counter, feedback and report_values are the system's or deleted |
| task_state.py | MonitorTaskState.__init__ | episode function | state is `messages/internal_summary.py` (a function of the view); the decision counter, feedback and report_values are the system's or deleted |
| task_state.py | MonitorTaskState.bind_execution_context | machinery | checkpoint/restore, effect recording and failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.record_execution_failure | machinery | checkpoint/restore, effect recording and failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.restore_checkpoint | machinery | checkpoint/restore, effect recording and failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.restore | machinery | checkpoint/restore, effect recording and failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.record_effect | machinery | checkpoint/restore, effect recording and failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | MonitorTaskState.checkpoint | machinery | checkpoint/restore, effect recording and failed-outcome recording (a tool returns its failure as its outcome) |
| task_state.py | _bind_preserved_runtime_providers | machinery | provider patching (`_bind_preserved_runtime_providers`) |
| to_child_execution_progress_assessment.py | prepare_dependency_request | episode function | `messages/msg_to_child.py msg_to_child` |
| to_child_execution_progress_assessment.py | assemble_request | machinery | old child request assembly (`assemble_request`: EpisodeGoal, EpisodeRequest, knowledge inheritance); the system derives the child request from `ChildMessage` |
| to_parent.py | MonitorReport | episode function | `messages/final_to_parent.py` |
| to_parent.py | MonitorReport.fact_sources | episode function | `messages/final_to_parent.py RETURN_FORM` |
| to_parent.py | MonitorReport.facts | episode function | `messages/final_to_parent.py monitor_facts` and `final_to_parent` |
| to_parent.py | MonitorReport.resolve | episode function | `messages/final_to_parent.py validate_report` (received progress refs) and `messages/internal_summary.py` (held-record reads); the resolver over the old provider is machinery |
| to_parent.py | MonitorReport.validate_report | episode function | `messages/final_to_parent.py validate_report` (called by `final_to_parent` before it returns); its `validate_form` step is not carried |
| waiting.py | MonitorWaiting | machinery | wait/suspension machinery (`suspension_changed` reports a wait condition to the execution backend) |
| waiting.py | MonitorWaiting.suspension_changed | machinery | wait/suspension machinery (`suspension_changed` reports a wait condition to the execution backend) |
| yield_estimator.py | _monitor_information_yield | machinery | episode-local estimator (README 7b): the information accumulation is `AccumulationYieldController`; its raise on a decreasing information credit is in `credit.py` |
| yield_estimator.py | MonitorEpisodeYield | episode function | `yield_estimator.py yield_controller` (`AccumulationYieldController`, README 7b) |
| yield_estimator.py | MonitorEpisodeYield.yield_controller | episode function | `yield_estimator.py yield_controller` (`AccumulationYieldController`, README 7b) |
