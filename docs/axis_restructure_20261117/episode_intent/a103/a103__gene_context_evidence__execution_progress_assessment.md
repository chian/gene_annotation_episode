# a103/gene_context_evidence/execution_progress_assessment — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/execution_progress_assessment/<file>`
(only files directly in this folder; no `grading/` or `scoring/` subfolder exists; `tests/` not covered).
Old binding class: `MonitorEpisode` (`binding_path = 'gene_context_evidence/execution_progress_assessment'`,
`commissioning_parent = 'gene_context_evidence'`, `roles = entry_roles = ('monitor',)`), decision source
`ProgressMonitoringTask`, prompt renderer `library.monitor_prompt.render_monitor_prompt`. Contract version
`monitor_episode_binding_v1`; assignment version `monitor_assignment_v1`.

## What it is for (its goal, in its own words)

`goal.py` `instructions()`:

> Investigate which further exposed progress information is useful for the assigned target. Use actual status,
> measured quantities, committed references and source-bound logs. Liveness establishes process presence only;
> elapsed time alone establishes neither productive work nor a stall. Unknown information stays unknown. Earlier
> outcomes and your admitted child forms inform later decisions. You may explicitly commission an ordinary monitor
> for one exposed direct dependency; no descendant traversal, fanout, cadence or depth is prescribed. Return the
> original parent's typed form at your closure even while the target remains active. Do not report private
> reasoning, intentions or unrestricted findings. Recorded facts use saved delivered observations; closure does not
> poll or compose another report with a model.

followed by one of two credit sentences: with the private yield binding, "The monitor's information-credit projector
and bound yield rule govern continuation."; without it, "The caller's monitoring projector and configured controller
own credit and continuation." Always ends: "Repeated observation identities and read timestamps alone earn no new
information."

`planning_context()` (shown to the model as `monitor_goal`): objective = the request goal, target handle, requested
fields, unresolved question "Which exposed progress information would improve the original requested report?",
progress definition "Actual received information under the caller-bound monitoring projector; repeated identities
and timestamps alone earn no credit.", and the yield settings.

## Task and instructions

`task_instructions.instructions()` composes: the goal above + `ACTION_BOUNDARY` ("Do not emit a stop action or invent
a turn budget, approval review, quality gate, experiment, term or observation.") + `CREDIT_COMPONENT_GUIDANCE`
(evidence vector describes the progress proxy, not biological truth) + `RESOURCE_ESTIMATE_GUIDANCE` (timing
experiment earns monitoring credit for timing information learned; missing history means duration unknown; job
elapsed time and own monitoring action duration are distinct) + `REPORT_GUIDANCE` (child returns only the parent's
typed form; report_update describes the interpretation before the selected next action; redeliver_report repairs
representation only) + history guidance (`EXCHANGE_HISTORY_GUIDANCE` under decision_exchange_v1, else
`HISTORY_GUIDANCE`) + `HOST_EXECUTION_GUIDANCE`, then tool knowledge and launch library instructions when present,
`REPAIR_GUIDANCE`, `WAIT_GUIDANCE` (when wait permitted) and `NATIVE_EVENT_GUIDANCE` (when native event targets exist).
Of the four episodes here this is the only one carrying ACTION_BOUNDARY, credit/resource/report/history blocks.

The task (`task.py`, `task_state.py`, `task_decision.py`, `decision_state.py`, `decision_inputs.py`,
`report_delivery.py`, `waiting.py`) is the old generic iterator step copied in with grain `'monitor'`; its own
intent is limited to: report values start from the parent's `initial_report`; interpretations are admitted against
the parent's report contract; a failed/invalid selected action still enters the iterator with its outcome.

## What it reads from its parent's assignment

`contracts._ASSIGNMENT` (`monitor_assignment_v1`): `target_handle` (must be an `execution_handle` in scope),
`requested_fields` ⊆ {execution_status, measurements, log_windows, committed_record_refs, dependencies,
result_available}, `known_progress_refs` (each must read back to the same target), `permitted_committed_record_types`
(subset of the Store record schemas). `from_parent._assignment` validates; `prepare_assignment` requires an
operation key and, when the parent is itself a monitor, applies the child-dependency rule.
`required_return_sources`: when the parent is `gene_context_evidence`, the parent's own
`../to_child_execution_progress_assessment.required_return_sources(services)` (parent-owned file).

## Children it may commission

One kind only: another `monitor` (this same episode type, recursively) — `child_roles = ('monitor',)`, and
`allowed_children` offers it only when `services.dependencies(target_handle)` is non-empty.
- Sends (`to_child_execution_progress_assessment.prepare_dependency_request`): a `monitor_assignment_v1` whose
  `target_handle` is one of this target's exposed direct dependencies and whose `permitted_committed_record_types`
  do not exceed this monitor's.
- Takes back (`from_child_execution_progress_assessment.receive_progress`): every `episode_progress` reference in
  the child's typed form, each read for validity, deduplicated, admitted into this monitor's received progress
  (signature = digest of form, schema, scope).

## Decision state and what it shows the model

Old common decision state (goal, scope, working state, visible refs, current credit, evidence vector, pending work,
last outcome/feedback, report deliveries, controller, tools, tool knowledge, job options, available report facts,
requested report purpose/form, current report update/basis) plus `monitoring_information_credit` /
`monitoring_information_binding` from the credit view, plus this episode's `decision_context()`:
`monitor_assignment`, `monitor_target_description` (when the services describe it), `monitor_direct_dependencies`,
`monitor_received_progress_refs`, `monitor_information_meaning` ("Exposed direct relationships and already
delivered observations. Empty measurements/log windows do not assert absence or a stall."), `monitor_goal`.
Decision inputs add resource context, launch library, child options, completed action reports, pending work,
execution expectations (role 'monitor'), resource estimates, native event targets, waiting support.

## Tools it offers

`progress_operations.catalog()`:
- `progress.observe` — observe selected exposed fields of the assigned target (fields must stay within the
  assignment; optional `native_operation` property only when the target descriptor supplies a
  `selected_observation_schema` of exactly that shape). Retains the original observation identity when facts are
  unchanged; never traverses dependent work. Returns committed refs filtered to permitted record types.
- `progress.read` — read an already delivered progress observation (must be received).
- `progress.log` — read one retained log window of a delivered observation with source/artifact byte custody
  (via `source.read`; empty window returns empty text).
Contract errors return `status: invalid` with feedback (entering the iterator), never an exception.
Common actions: tool, child, wait, redeliver_report.

## How its credit is counted

`credit_kind = 'monitoring'`. `credit_view` delegates to the caller-bound role credit
(`services.bound_role_credit`). The episode's own calculation is `information_credit` =
`ProgressInformationCredit(progress_reader, information_unit)`: newly informative received snapshots × information
unit; repeated identities and timestamps earn nothing. Credit is unbounded.

## Continuation

Only with the private yield binding (`yield_settings` given): `MonitorEpisodeYield.yield_controller` →
`YieldController(epoch, initial_credit, cutoff, YieldParameters(uncertainty_alpha))` with
`_monitor_information_yield` = `estimate_nonnegative_yield` (scores must not decrease; binding
`monitor_information_accumulation_v1`, forecast "next monitor action information credit", decision "predicted upper
gain at or below monitor cutoff"). New-layout estimator: **accumulation**. Settings: `cutoff` (≥ 0, finite),
`uncertainty_alpha` (0 < α < 1), `information_unit` (> 0). Without the binding the caller's controller owned it.

## What it reports to its parent

`to_parent.fact_sources/facts`: `monitoring_progress_refs` (received progress identities), `monitoring_target_handle`,
`monitoring_execution_state` (latest target observation lifecycle state or null), `monitoring_result_available`,
`monitoring_observed_at_unix_seconds` (original UTC observation time), `monitoring_committed_record_refs` (permitted
committed records actually delivered), `monitoring_dependency_handles` (latest observation's direct dependencies).
`validate_report` requires fact-sourced fields to equal recorded facts and every non-progress record reference to be
of a permitted type and actually received. `resolve` admits received progress refs and handles of the target and its
observed dependencies.

## Differences from siblings / similar episodes

- Only episode of the four that recurses into itself (monitor → monitor on a direct dependency).
- Its `from_child_execution_progress_assessment.py` is the same logic as hpc_work_planning's monitor receiver
  (hpc's adds comments, no `_unique` import).
- hpc_work_planning commissions it with only a schema check (`prepare_request`), while this episode's own child rule
  enforces the direct-dependency and record-type narrowing.
- Accumulation continuation; the execution episodes use completion-with-target or bounded estimates.
- Decision state keeps the annotation-axis branch (shared with launch_local/results copies; hpc removed it).

## File by file
| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `binding_record.py` | 9 | Binding descriptor: outcome_page_size, information_unit and yield_settings when the private yield binding is on. | none |
| `configuration.py` | 31 | Settings: outcome_page_size (positive int, default 32); optional yield_settings {kind: information_accumulation, cutoff >= 0, uncertainty_alpha in (0,1)} which then requires a positive information_unit. Single role 'monitor'. | import:communication |
| `contracts.py` | 10 | Assignment contract monitor_assignment_v1: target_handle, requested_fields (subset of execution_status, measurements, log_windows, committed_record_refs, dependencies, result_available), known_progress_refs, permitted_committed_record_types. Lifecycle states pending/executing/returned/admitted. | import:domain |
| `credit.py` | 21 | Credit kind 'monitoring'; credit_view delegates to the caller-bound role credit; information_credit = ProgressInformationCredit(progress_reader, information_unit) i.e. newly informative received snapshots times the unit. | import:library.progress_information_credit, self.services.bound_role_credit |
| `decision_inputs.py` | 60 | Copy of old decision inputs (resource context, launch library, child options, completed action reports, pending work, execution expectations for role 'monitor', resource estimates, native event targets, waiting support). | import:episode_work_report, import:root.a103, import:runtime, runtime.child_option_information, runtime.Mapping, workflow.available_child_roles, workflow.binding_context×2, workflow.episode_bindings, workflow.execution_expectations, workflow.job_episodes×2, workflow.launch_instructions×2, workflow.native_estimation_context, workflow.native_event_information×2, workflow.pending_work, workflow.permits_common_action, workflow.resource_context, workflow.resource_estimator×4, workflow.store×2, workflow.waiting_support |
| `decision_state.py` | 44 | Copy (see common) plus monitoring_information_credit/binding from the credit view. | import:root.a103, import:runtime, runtime_actions×2, runtime.FACT_MEANINGS, runtime.FACT_SOURCES, runtime.json×2, runtime.Mapping×3, runtime._plain×2, runtime._references_in, workflow.binding_context, workflow.catalog, workflow.controller_binding, workflow.delivery_status, workflow.extra_report_sources, workflow.job_episode_options, workflow.journal×3, workflow.knowledge, workflow.local_outcome_preview, workflow.pending_work, workflow.receipt_projection, workflow.run_id, workflow.source_credit_binding, workflow.source_credit_view, workflow.specialist, workflow.store×3, workflow.tools, workflow.working_state |
| `episode.py` | 54 | Wires the monitor: path gene_context_evidence/execution_progress_assessment, roles/entry ('monitor',), task ProgressMonitoringTask, prompt render_monitor_prompt. Child roles ('monitor') allowed only when the target exposes direct dependencies. Common actions tool, child, wait, redeliver_report. Required return sources come from the parent gene_context_evidence's to_child file. | import:communication, import:library.monitor_prompt, self.services.dependencies |
| `from_child_execution_progress_assessment.py` | 20 | Receive a recursive monitor child's typed form: every episode_progress reference in the form is read and admitted into this monitor's received progress (dedup, content-digest signature). | import:communication, import:domain, import:method_loop.durable |
| `from_parent.py` | 33 | Validate the parent's monitor_assignment_v1: target handle in scope, every known progress ref belongs to the target; a monitor parent's child assignment goes through prepare_dependency_request. | import:communication, import:domain, self.services.read_progress, self.services.reference_in_scope |
| `goal.py` | 15 | Goal text (quoted in the doc) and planning_context: objective, target, requested fields, unresolved question, progress definition, yield settings. | import:communication |
| `__init__.py` | 1 | Package marker; no intent. | none |
| `internal_summary.py` | 13 | Decision context: assignment, target description, direct dependencies, received progress refs, meaning ("empty measurements do not assert absence or a stall"), monitor_goal. | import:communication, self.services.dependencies |
| `progress_operations.py` | 58 | Tools progress.observe (only fields within the assignment; optional native_operation from the target descriptor), progress.read, progress.log (byte window with source/artifact custody). Invalid arguments return an invalid outcome, not an exception. | import:communication, import:domain, import:episode_bindings, self.services.execute_tool, self.services.observe_progress, self.services.read_record×2 |
| `progress_records.py` | 16 | UTC timestamp parsing and order-preserving dedup. | import:domain |
| `received_progress.py` | 30 | Received progress = assignment known refs + own outcome progress refs (paged) + child-delivered refs; reads only received snapshots. | import:domain, self.services.own_outcomes, self.services.read_progress, self.services.received_progress_refs |
| `report_delivery.py` | 25 | Copy of old finish(): with no report contract return credit + pending handles + binding facts; otherwise compose the parent's typed form once from recorded facts + interpretations and save it. Own intent: recorded facts fill fact fields, interpretations are the last admitted report_update; no model call at closure. | import:library.private_policy_call, import:library.report_fact_assembly, import:root.a103, import:runtime, runtime_forms×2, runtime.form_with_facts, runtime._json×2, runtime.json, runtime.Record×2, workflow.binding_context, workflow.episode_bindings, workflow.facts, workflow.journal×2, workflow.pending_handles, workflow.release×2, workflow.source_credit_view |
| `task_decision.py` | 299 | Copy of the old decision call + full exchange loop in one file. | import:root.a103, import:runtime, runtime._action_generation_schema×2, runtime.apply_state_frame, runtime._ASSIGNMENT_TRANSPORT, runtime._category_yield_parameters, runtime.child_option_information, runtime.composition_lookup_schema×2, runtime.CONTRACT_INFORMATION_OPERATIONS, runtime.DECISION_CONTEXT_VERSION×2, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest, runtime.Draft202012Validator, runtime.instructional_model_context×4, runtime.is_contract_information, runtime._json×14, runtime.json×3, runtime.lookup_attempts, runtime.Mapping×3, runtime_model_calls×8, runtime.model_snapshot×2, runtime._object×3, runtime._plain×2, runtime._recorded_action_generation_schema, runtime._recorded_assignment_transport, runtime._references_in, runtime.requested_contract_information×2, runtime.schema_failure_diagnostic×2, runtime.sqlite3, runtime.state_frame, runtime.ValidationError×5, runtime.WorkflowError×14, runtime.yield_table, workflow.contract_information_profile, workflow.contract_information_reply, workflow.controller_binding, workflow.decision_exchanges×4, workflow.decision_protocol×3, workflow.execute, workflow.freeze_contract_information, workflow.history_preview, workflow.journal×3, workflow.numerical_contracts, workflow.provider×3, workflow.receipts×4, workflow.run_id, workflow.services×2, workflow.specialist, workflow.store×2, workflow.uses_received_record_context×2, workflow.validate_contract_information×5 |
| `task_instructions.py` | 86 | Instruction composition: goal + ACTION_BOUNDARY (no stop action, no invented budget/gate) + credit component, resource estimate, report, history, host execution, repair, wait and native event guidance. | workflow.binding_context, workflow.decision_protocol, workflow.knowledge, workflow.launch_instructions, workflow.native_event_information, workflow.permits_common_action, workflow.specialist |
| `task.py` | 182 | Copy of the old task iterator step (next/apply_response/execute) with grain 'monitor'. | import:episode_source_failure, import:library.action_contracts, import:library.private_policy_call, import:providers, import:root.a103, import:runtime, runtime.ActionFailure, runtime_actions×8, runtime.ContractInformationError, runtime._decode_recorded_action_response, runtime.Draft202012Validator×2, runtime_episodes, runtime.EventTargetError×2, runtime.inspect, runtime._json×5, runtime.json×8, runtime_model_calls×2, runtime.nullcontext×5, runtime.observes_action_outcome, runtime.ReportBoundaryError, runtime.ReportRedelivery×2, runtime.schema_failure_diagnostic, runtime.SourceEnd×2, runtime.validate_form, runtime.ValidationError×2, runtime._wait_target_feedback×2, runtime.WorkflowError×2, workflow.action_schema, workflow.completed_unit×3, workflow.completions×3, workflow.controller_value×2, workflow.decision_exchanges×3, workflow.delivery_resolution_inputs, workflow.execute, workflow.execution_binding×7, workflow.inprocess_replay×4, workflow.journal×7, workflow.last_observed_credit, workflow.next_return, workflow.pending_work, workflow.perform_selected_wait, workflow.receive_native_outcome, workflow.receive_outcome, workflow.resolve_pending_deliveries, workflow.resolver, workflow.run_id×2, workflow.selected×3, workflow.source_credit_view, workflow.store×7, workflow.validate_report |
| `task_state.py` | 108 | Copy of the old per-source task state (episode identity, report_values from parent initial_report, feedback, restore/checkpoint/record_effect against old completions). Own intent: report_values start from the parent's initial_report; interpretation schema from the parent report contract; failed selected tool/reason actions still enter the iterator with a failed outcome and credit. | import:episode_source_failure, import:root.a103, import:runtime, runtime.ActionLeaf, runtime_actions×5, runtime.EFFECT_VERSION, runtime.Episode, runtime.interpretation_schema, runtime._json×2, runtime.json×4, runtime._object, runtime._plain, runtime.Record, workflow.archive, workflow.completions×4, workflow.context, workflow.controller_value, workflow.execution_binding×4, workflow.grains, workflow.inprocess_replay×7, workflow.journal×5, workflow.progress_provider×2, workflow.recover_commissions, workflow.run_id, workflow.source_credit_view, workflow.store×2 |
| `to_child_execution_progress_assessment.py` | 11 | Child monitor request: target must be an exposed direct dependency of this target; child permitted record types must not exceed the parent's. | import:domain |
| `to_parent.py` | 91 | Facts monitoring_progress_refs, _target_handle, _execution_state, _result_available, _observed_at_unix_seconds, _committed_record_refs, _dependency_handles from the latest received target observation; reference resolution; report validation (fact fields must equal recorded facts; record refs must be permitted and received). | import:communication, import:domain, import:episode_bindings, self.services.read_progress×3, self.services.read_record×2 |
| `waiting.py` | 9 | Suspension hook (common). | workflow.execution_backend, workflow.execution_handle×2 |
| `yield_estimator.py` | 23 | Accumulation yield: scores must not decrease; estimate_nonnegative_yield with binding monitor_information_accumulation_v1; YieldController(cutoff, uncertainty_alpha). Only when private yield binding is on. | import:numerical×2 |

Usage counts per name and file: `runs/carry_over/calls/a103_02.tsv`.
