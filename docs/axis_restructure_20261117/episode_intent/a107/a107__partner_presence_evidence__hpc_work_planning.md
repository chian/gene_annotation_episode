# A107 `partner_presence_evidence/hpc_work_planning`

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/<file>`
(49 files directly in the folder, about 2,300 lines; `tests/` has 6 files, which were not read; the child folders
`execution_job_submission/`, `execution_progress_assessment/`, `execution_result_acquisition/`, `hpc_allocation_execution/` and
`hpc_resource_prediction/` belong to other agents).

## Purpose (its own words)

`binding_path = 'partner_presence_evidence/hpc_work_planning'`, `commissioning_parent = 'partner_presence_evidence'`,
`roles = entry_roles = ('hpc',)`, `replaces_default_instructions = True`. `goal.instructions` (abridged; the full text is in goal.py):

> Iterate toward the original accomplishment while balancing expected credit against real elapsed time and resource demand.
> The hpc parent can commission hpc_prediction and hpc_execution as sisters: prediction fits/measures/compares; execution
> prepares, launches, monitors and parses the selected work. Both assignments copy hpc_child_commission exactly and carry the
> hpc parent owner_episode_id. Both sisters inherit exactly hpc_child_scope ... Use hpc_report_form as the return contract. ...
> When candidates are absent, discover the remote environment and documentation with hpc.discovery.run, then design candidate
> portfolios with hpc.candidate.propose. ... You choose the real inputs, database, executable commands, resources, worker code
> and preparation instructions. Never fabricate inputs or receipts. Every work unit writes result.json and progress.json under
> os.environ["HPC_UNIT_DIRECTORY"] ... Compute commands must run on allocated compute nodes using the facility launcher. ...
> A plan freezes its original forecast, scientific manifest and acceptance criteria. Commission launch -> launch_hpc with that
> actual job and resource. ... Use hpc_launch_report_form as the Launch return contract. If a completed Launch return omitted
> its receipt, use redeliver_report ... report repair must not commission another Launch. Attach that received handoff. Use
> hpc.monitor once when another observation can affect your decision ... Use hpc.results directly for known parsing. ... When
> hpc_monitor_controllers is present, select hpc.monitor.wait for a scheduled observation ... Do not poll for credit or
> duplicate a submitted attempt. Never replace an uncertain submission. Accepted accomplishment, model improvement, and fixed
> prospective forecast validation are the only parent credit components; launch-local credits are not added again.

## Task and instructions

`task_instructions.instructions` = the binding goal text + tool knowledge + launch library + the pending_child_delivery repair paragraph
+ (when wait is permitted) the in-process wait guidance + native_event_targets guidance. Renderer: `library.hpc_prompt.render_hpc_prompt`.

## What it reads from the parent's assignment

`assignment_schema('hpc')`: `{commission_id (enum of configured commissions) | commission_source_ref, tool_request?
{name, resources: api|local|hpc, arguments_json, result_reader, objective}}` with `oneOf` commission_id or commission_source_ref.
`prepare_assignment`: a commission_source_ref must be among `parent.received_record_refs` and readable through
`hpc_commission_sources.read`. A `tool_request` is resolved against the parent `partner_presence_evidence_binding.tool_library`.
It must have an actual result reader, and its arguments must validate against the tool's input schema. The result carries an
execution_rule: "Implement this exact requested computation through the HPC template ... do not replace scientific grading with
the allocation acceptance score". When `require_commission_yield` is set, the commission must carry `yield_bindings`.
Configuration: `resources` (at least one `pbs_ssh`), `commissions` (validated by `hpc_campaign.validate_commission`),
optional `shared_execution_memory` (ExecutionMemory) and `require_commission_yield`.

## Children (child_roles = hpc_prediction, hpc_execution, launch, monitor, results)

| child role | sends | takes back |
|---|---|---|
| `hpc_prediction` (hpc_resource_prediction) | `{commission_id \| commission_source_ref, owner_episode_id}`. The owner must be this hpc episode and the commission identity must equal the parent's (to_child_hpc_resource_prediction.py) | the typed `hpc_report_form` through `receive_prediction_report`: the recorded-admission refs, or the progress provider form, receipts, native timing receipts and tool attributions |
| `hpc_execution` (hpc_allocation_execution) | the same shape and checks (to_child_hpc_allocation_execution.py) | `receive_allocation_report` (the same receipt path) |
| `launch` (execution_job_submission, then launch_hpc) | the frozen plan's `launch_assignment`. `authenticate_launch` allows only the exact planned launch and reserves `launch:<plan_id>` once, never after the allocation closed. `LaunchPreparation.initial_decision_context` gives the child `hpc_execution_job {plan_id, objective, scientific_manifest, scientific_acceptance, supplied_input_file (immutable plan JSON), coordinator_workspace, instructions}` | `hpc_launch_report_form {execution_handoff_refs}`. `LaunchReceiptCustody.original_launch_handoff` recovers the actual PBS handoff receipt from committed native outcomes under this hpc path, which supports report repair |
| `monitor` (execution_progress_assessment) | `_ASSIGNMENT` validated as is (to_child_execution_progress_assessment.py: "This parent requests information; it never polls here") | `receive_progress`: episode_progress refs from the typed form go to `provider._receive_progress` |
| `results` (execution_result_acquisition) | assignment passed through; request assembled by `to_child_execution_result_acquisition.assemble_request` (goal, message with scope, initial_report, inprocess order, report_contract_declaration, job/episode assignment, knowledge_inheritance) | `receive_report` (from_child_execution_result_acquisition.py): recorded admission refs or the progress form, receipts and tool attributions |

`create_execution_bindings(*args, **configuration)` builds this hpc parent's private copies of the Launch (+api/local/hpc) and Results
bindings.

## Decision state shown to the model

The generic snapshot (decision_state.py, without the annotation-axes branch) + `HPCSummary.decision_context`: `hpc_commission`,
`hpc_candidates`, `hpc_resource`, `hpc_child_scope`, `hpc_child_commission`, `hpc_launch_deliveries` (launch child report
attempts from `runtime_report_attempts`), `hpc_launch_report_form`, `hpc_tool_request`, `hpc_model_ref`, `hpc_credit`,
`hpc_latest_comparison`, `hpc_model_support`, `hpc_report_form {hpc_credit, hpc_model_ref, hpc_result_refs}`, `hpc_plans`,
`hpc_latest_monitor`, `hpc_monitor_controllers`, `hpc_activity_decision` (from the last observation's estimator diagnostics:
wait or collect mode, suggested tool, active_next_gain, pending_expected_credit and bound), `hpc_queue_refs`, the shared memory and history refs, and
`hpc_available_training_ids`. decision_inputs adds `requested_action_history` for HPC contexts and `waiting_support`.

## Tools offered

`permitted_common_actions` → `('tool','child','redeliver_report')` when the commission has `monitoring`, otherwise also `wait`.
The tools are ledger-backed (`HPCLedger` under `<run>/hpc/<digest(run_id, episode_id)>`), idempotent per operation key and saved through
`ledger.save_action`:
`hpc.read`, `hpc.compare{model_ref, queue_ref}`, `hpc.history.refresh` (only with shared memory), `hpc.discovery.run{command}`
(SSH inspection rooted at `/lus/flare/projects/BioReason-Aurora-Test`), `hpc.candidate.propose{candidate_json}` (candidate
identities are immutable), `hpc.queue.observe`, `hpc.plan{candidate_id, model_ref, queue_ref}` (fresh queue, enabled Execution queue,
limits respected; freezes forecasts and validation slots), `hpc.handoff{plan_ref, handoff_ref}` (received handoff must match
the frozen practical assignment; attaches MonitorCronController), `hpc.monitor{plan_ref, refresh_queue}` (observe the job and allocation
status and unit progress, measure, update conditional forecasts), `hpc.monitor.wait{plan_ref}` (reserve a forecast-valued schedule,
wait, observe once), `hpc.results{plan_ref}` (verify the result sha against the unit receipt, apply the obligations' acceptance predicates,
close and export to shared history) and `hpc.allocation.order{plan_ref, unit_ids}`.

## Credit

`credit_kind` → 'operational'. `credit_view` → `HPCLedger.credit_view()`, whose contributions are accepted obligations ('actual'), model
improvement and frozen prospective forecast validation slots. `hpc_credit` is "Signed measured credit; repeated polling
adds none". Waiting earns 0 (`earned_wait_credit: 0.0`).

## Continuation

`yield_controller` requires `require_commission_yield`. It uses `commission['yield_bindings'][role] = {cutoff, parameters}` with
`HPCContinuationEstimator(verify).with_continuation_cost(cutoff)` (library.hpc_continuation). `continuation_for_action` writes a
ledger `continuation` record: the expected continuation credit from pending allocations (`hpc_monitoring.choose_schedule`, the
attainable units from `prediction.compare`, or the unresolved-acceptance upper bound for outputs awaiting collection), the pending action
(collect), the active credit ceiling 0 when all remaining obligations are pending with no new training cases, and the active history indices.
The closest of the three new estimators is completion with a target (the obligations); the pending-allocation valuation is its own operand.

## Report to parent

Facts: `hpc_credit`, `hpc_model_ref`, `hpc_accepted_obligations` and `hpc_result_refs` (only those known to this context).
`resolve` admits `hpc_model` refs in the ledger; `frozen_reference` validates a closed model through a read-only open of the
ledger sqlite and `runtime_forms` facts. `validate_report` enforces fact equality (`hpc_report_disagrees_with_recorded_evidence`).
`resolve_received_reference` / `read_evidence` admit only received `episode.hpc_result` sources that this ledger owns.

## Policy notes found in this old code (flag before carrying over)

- `resource_discovery.py`: `subprocess.run([...ssh_argv, command], ..., timeout=90)`. This is an elapsed-time limit, which the
  "no elapsed-time limits" rule forbids. stdout and stderr are truncated to 64 KiB and 8 KiB.
- `measured_history._shared_history`: `observations[...][:2000]`. This is a count cap on imported history.
- `yield_estimator.continuation_for_action`: `scale = min(1.0, expected_continuation_credit / total)`. It clamps a
  continuation valuation scale (not the earned credit itself).
- `resource_discovery.py` hard-codes the project path `/lus/flare/projects/BioReason-Aurora-Test`.

## Differences

- The only one of these four with five child roles and a persistent ledger. It is the only one with an exact-plan launch authentication.
- Its task loop removes the reason branch and job_child handling, like the monitor. `task_state` restricts failure recovery to
  `tool` actions. `task_decision` drops the annotation-axis yield table branch.

## File by file

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | none | none |
| allocation_handoff.py | 35 | attach the original handoff; route allocation tools | `episode_bindings.reference_in_context` |
| allocation_observations.py | 83 | target reader, compact windows, allocation receipt identity, observe and measure | `episode_bindings.reference_in_context` |
| allocation_order.py | 16 | reorder original units | none |
| allocation_results.py | 74 | collect, verify sha, accept, close, export | `communication.plain` |
| binding_record.py | 8 | binding id/config | none |
| closed_models.py | 27 | closed model ref validation | table `runtime_forms`; `episode_return_records.EpisodeReturnRecords` |
| configuration.py | 32 | resources, commissions, memory, yield flag | `communication.plain` |
| credit.py | 16 | ledger credit | none |
| decision_inputs.py | 53 | HPC decision inputs | self.workflow.{resource_context, launch_instructions(2), available_child_roles, episode_bindings, binding_context, pending_work, execution_expectations, resource_estimator(4), native_estimation_context, permits_common_action, waiting_support}; `runtime.child_option_information`; `episode_work_report.*` |
| decision_state.py | 31 | none (generic snapshot) | self.workflow.{store(3), journal(2), working_state, run_id, local_outcome_preview, source_credit_view, receipt_projection, source_credit_binding, pending_work, delivery_status, controller_binding, catalog, knowledge, job_episode_options, extra_report_sources, specialist, binding_context, tools}; table `runtime_actions`; `runtime.*` |
| episode.py | 104 | composition, roles, children, receivers, private child bindings | none directly (receivers named) |
| forecast_observations.py | 80 | freeze forecasts, measure, conditional forecast update | none |
| from_child_execution_job_submission.py | 46 | recover the original Launch handoff receipt | tables `runtime_actions`, `runtime_episodes`; `method_loop.identities.EpisodeRef` |
| from_child_execution_progress_assessment.py | 23 | receive monitor progress | `communication.*`, `method_loop.durable.content_digest`; `provider._receive_progress` |
| from_child_execution_result_acquisition.py | 44 | receive the Results form | workflow(param).{receipts(3), is_job_source(2), store(7), run_id(6), binding_context(4), progress_provider(4), specialist, episode_bindings, native_timing_information, job_episodes(2), receive_tool_attributions}; table `runtime_report_attempts`; `runtime._references_in/_json/json/WorkflowError`; `delivery_counterpart.child_role_for_delivery`; `episode_return_records` |
| from_child_hpc_allocation_execution.py | 32 | receive the allocation form | the same workflow(param) set minus specialist; table `runtime_report_attempts`; `runtime.*` |
| from_child_hpc_resource_prediction.py | 31 | receive the prediction form | the same as above |
| from_parent.py | 69 | assignment schema; commission; tool_request resolution | `communication.plain`; `services.workflow.partner_presence_evidence_binding` (getattr) |
| goal.py | 10 | the goal text | none |
| initial_information.py | 9 | own initial information | `catalog.readers` |
| internal_summary.py | 56 | HPC decision context | tables `runtime_report_attempts`, `runtime_episodes`; `communication.plain` |
| measured_history.py | 82 | measured history, shared history import/export | none (`[:2000]` cap) |
| portfolio_candidates.py | 23 | propose candidate | none |
| portfolio_comparison.py | 44 | compare portfolios | none |
| portfolio_planning.py | 38 | freeze plan | none |
| portfolio_state.py | 38 | ledger state; initialize prior/shared model | `communication.plain` |
| queue_observations.py | 35 | queue observation with memory cache | none |
| received_api_reports.py | 4 | own API readers | `catalog` |
| received_evidence.py | 60 | known refs; owned result sources | `services.record_selection` |
| received_execution_information.py | 4 | own result readers | `catalog` |
| report_delivery.py | 23 | none (generic finish) | self.workflow.{source_credit_view, pending_handles, episode_bindings, binding_context, release(2), journal(2), facts}; table `runtime_forms`; `runtime.*` |
| resource_discovery.py | 30 | SSH discovery with memory cache | none (`timeout=90`) |
| task.py | 183 | none (generic loop, trimmed; HPC launch report contract check) | the same self.workflow set as the monitor's task.py; tables `runtime_actions`, `runtime_episodes`, `runtime_model_calls`; `runtime.*`; `providers.ModelCallError`; `episode_source_failure` |
| task_decision.py | 289 | none (generic; own complete_decision) | the same as the monitor's task_decision |
| task_instructions.py | 14 | composition | self.workflow.{specialist, binding_context, knowledge, launch_instructions, permits_common_action(2), native_event_information} |
| task_state.py | 108 | none (failure recovery for tool only) | the same as local task_state |
| task_waiting.py | 9 | none (suspension) | self.workflow.execution_handle(2), execution_backend |
| to_child_execution_job_submission.py | 70 | exact-plan launch authentication; Launch child job information | `communication.plain`, `method_loop.identities.EpisodeRef` |
| to_child_execution_progress_assessment.py | 12 | monitor request | `communication.plain` |
| to_child_execution_result_acquisition.py | 29 | assemble the Results request | workflow(param).{context(2), grains(2), inprocess_completion_order(2), launch_instructions, receipts(2)}; `runtime.{EpisodeGoal, EpisodeRequest, Episode, Record, _plain, ContractInformationError, validate_saved_fact_form}` |
| to_child_hpc_allocation_execution.py | 33 | allocation child schema and owner check | `communication.plain` |
| to_child_hpc_resource_prediction.py | 29 | prediction child schema and owner check | `communication.plain` |
| to_parent.py | 41 | facts/resolve/validate | `communication.validate_form`, `episode_bindings.reference_in_context` |
| waiting.py | 50 | activity advice; scheduled monitor wait | table `runtime_observations` |
| work_operations.py | 54 | HPC tool catalog and dispatch | `communication.plain` |
| yield_estimator.py | 101 | HPC continuation estimator and evidence | tables `runtime_observations`, `runtime_actions`; `numerical.YieldController/YieldParameters`; `library.hpc_continuation.HPCContinuationEstimator` |

## Carried over

One row per row of `runs/carry_over/functions/a107__partner_presence_evidence__hpc_work_planning.tsv` (old file, kind, name copied). Classification: machinery (not carried, with the reason) or episode function (with its new place: a file of this episode, or the library function it calls; "library candidate" rows would be library functions that are not in the library yet: none of the rows here needs one that is not already in the episode file that uses it, so no row is marked so, and nothing is added to or moved into `episode_support/`). Every `task.py` helper that is a private copy of the sibling allocation episode's code is this episode's own copy (an episode imports nothing from another episode).

| old file | kind | name | classification | new place or machinery reason |
|---|---|---|---|---|
| allocation_handoff.py | class | AllocationHandoff | episode function | task.py: the class is dissolved into the module-level functions of its two methods |
| allocation_handoff.py | method | AllocationHandoff._attach_original_handoff | episode function | task.py hpc_handoff (the custody test is ctx.store.holds; the target read is handoff_target, BLOCKED-ON-JOB-SERVICE) |
| allocation_handoff.py | method | AllocationHandoff._work_on_original_allocation | episode function | task.py original_plan, original_target and the branches hpc_monitor, hpc_monitor_wait, hpc_allocation_order, hpc_results |
| allocation_observations.py | class | AllocationObservations | episode function | task.py: the class is dissolved into the module-level functions of its methods |
| allocation_observations.py | method | AllocationObservations.targets | episode function | task.py handoff_target / observe_target / read_window / write_allocation_control (ExecutionTargetReader is the job-access service: BLOCKED-ON-JOB-SERVICE) |
| allocation_observations.py | method | AllocationObservations._target | episode function | task.py original_target |
| allocation_observations.py | method | AllocationObservations._window | episode function | task.py window and window_value |
| allocation_observations.py | method | AllocationObservations._allocation | episode function | task.py allocation_receipt |
| allocation_observations.py | method | AllocationObservations._observe_original_allocation | episode function | task.py observe_allocation (the branches by tool are hpc_monitor and hpc_results) |
| allocation_order.py | class | AllocationOrder | episode function | task.py: dissolved into hpc_allocation_order |
| allocation_order.py | method | AllocationOrder._order_original_units | episode function | task.py hpc_allocation_order (write_allocation_control: BLOCKED-ON-JOB-SERVICE) |
| allocation_results.py | class | AllocationResults | episode function | task.py: the class is dissolved into the module-level functions of its methods |
| allocation_results.py | method | AllocationResults._collected_unit_ids | episode function | task.py collected_unit_ids |
| allocation_results.py | method | AllocationResults._uncollected_completed_unit_ids | episode function | task.py uncollected_completed_unit_ids |
| allocation_results.py | method | AllocationResults._publish | episode function | task.py publish_result (ctx.store.artifact and ctx.store.put) |
| allocation_results.py | method | AllocationResults._collect_original_results | episode function | task.py collect_original_results (the tool is hpc_results) |
| binding_record.py | class | HPCBindingRecord | machinery | binding_record.py: the binding's own as_record() (README 3d: deleted) |
| binding_record.py | method | HPCBindingRecord.as_record | machinery | the binding's own as_record() (the system derives the declaration) |
| closed_models.py | class | ClosedModels | machinery | re-validation of a closed episode's saved form (runtime_forms, EpisodeReturnRecords, a second read-only connection to the ledger); the episode's own check of its model identity is messages/final_to_parent.py resolve and validate_report |
| closed_models.py | method | ClosedModels.frozen_reference | machinery | as ClosedModels: runtime_forms and EpisodeReturnRecords re-validation of a closed episode |
| configuration.py | class | HPCConfiguration | episode function | the values are ctx.settings (task.py settings list, yield_estimator.py); the validations are task.py create_ledger and commission_of |
| configuration.py | method | HPCConfiguration.__init__ | episode function | ctx.settings: directory, resources, commissions, shared_execution_memory (the ExecutionMemory is the estimate_table service: BLOCKED-ON-JOB-SERVICE), units; the resource and commission checks are task.py create_ledger and commission_of; the yield flag and yield_bindings are yield_estimator.py settings cost and parameters; the old services, store, run_id are ctx |
| credit.py | class | HPCEpisodeCredit | episode function | credit.py (the class is dissolved) |
| credit.py | method | HPCEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d); the role check is gone with the role argument |
| credit.py | method | HPCEpisodeCredit.credit_view | episode function | credit.py credit (the ledger's credit view read from the summary's ledger_view; task.py ledger_view builds it) |
| decision_inputs.py | class | HPCWorkDecisionInputs | episode function | messages/internal_summary.py and task.py decide (the class is dissolved) |
| decision_inputs.py | method | HPCWorkDecisionInputs.decision_inputs | episode function | task.py decide (launch instruction library and selection, tool knowledge, resource tool estimates read from the estimate_table service, child options as the actions list) and messages/internal_summary.py (requested_action_history is actions); the old-runner parts (resource_context, supplied_initial binding context, completed_action_reports, pending_work, contract_information_profile, waiting_support, native_estimation_context) are machinery or not carried |
| decision_state.py | class | HPCWorkDecisionState | episode function | messages/internal_summary.py and task.py decide |
| decision_state.py | method | HPCWorkDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary and task.py decide context; the store snapshot, the runtime_actions read, the receipt projection, the report values and the credit binding are machinery |
| episode.py | class | HPCEpisode | episode function | episode.py HPCEpisode (one class on EpisodeBinding; the mix-in bases are deleted) |
| episode.py | method | HPCEpisode.child_roles | episode function | task.py CHILD_SLOTS |
| episode.py | method | HPCEpisode.allowed_children | episode function | task.py CHILD_SLOTS (which slots are offered is task.py offered) |
| episode.py | method | HPCEpisode.permitted_common_actions | machinery | the common actions tool, child, wait and redeliver_report: wait and redeliver_report are not carried (a wait action and redelivery do not exist), so the restriction by a commission's monitoring key has nothing to restrict |
| episode.py | method | HPCEpisode.prepare_child_request | episode function | messages/msg_to_child.py msg_to_child (one branch per slot) |
| episode.py | method | HPCEpisode.receive_child_progress_for_role | machinery | progress provider channel of the old runner; the monitor's values are read in messages/read_from_child.py |
| episode.py | method | HPCEpisode.child_report_receiver | episode function | messages/read_from_child.py read_from_child (hpc_prediction and hpc_execution); the recorded-admission receivers are machinery |
| episode.py | method | HPCEpisode.execution_child_report_receiver | episode function | messages/read_from_child.py read_from_child (results) |
| episode.py | method | HPCEpisode.child_request_assembler | episode function | messages/msg_to_child.py msg_to_child (results); the goal, receipts and inheritance assembly is machinery |
| episode.py | function | create_execution_bindings | machinery | home factory building the private child bindings (no table or list of bindings exists) |
| forecast_observations.py | class | ForecastObservations | episode function | task.py: the class is dissolved into the module-level functions of its methods |
| forecast_observations.py | method | ForecastObservations._freeze | episode function | task.py freeze_forecast |
| forecast_observations.py | method | ForecastObservations._last_forecast | episode function | task.py last_forecast |
| forecast_observations.py | method | ForecastObservations._measure | episode function | task.py measure |
| forecast_observations.py | method | ForecastObservations._update_conditional_forecast | episode function | task.py update_conditional_forecast (the tool is hpc_monitor) |
| from_child_execution_job_submission.py | class | LaunchReceiptCustody | machinery | recovered the plan's handoff from the old runner's committed outcome tables (runtime_actions, runtime_episodes) across a report repair; custody and the launch child's returned handoff records replace it |
| from_child_execution_job_submission.py | method | LaunchReceiptCustody.original_launch_handoff | machinery | as LaunchReceiptCustody (runtime_actions and runtime_episodes reads, EpisodeRef paths) |
| from_child_execution_progress_assessment.py | function | receive_progress | machinery | admission of the monitor's episode_progress references into the old progress provider; messages/read_from_child.py reads the monitor's typed result |
| from_child_execution_result_acquisition.py | function | receive_report | machinery | recorded admission, progress forms, receipts and tool attributions of the old runner; messages/read_from_child.py reads the results child's typed result |
| from_child_hpc_allocation_execution.py | function | receive_allocation_report | machinery | the same old receipt path; messages/read_from_child.py reads the typed result |
| from_child_hpc_resource_prediction.py | function | receive_prediction_report | machinery | the same old receipt path; messages/read_from_child.py reads the typed result |
| from_parent.py | class | HPCAssignment | episode function | messages/read_from_parent.py (the class is dissolved) |
| from_parent.py | method | HPCAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | method | HPCAssignment.commission_identity | episode function | task.py commission_identity |
| from_parent.py | method | HPCAssignment._commission | episode function | task.py commission_of (hpc_commission_sources.read: BLOCKED-ON-STORE-ACCESS, library not carried) |
| from_parent.py | method | HPCAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (the exactly-one identity check); the received-source and yield_bindings checks are not carried (custody; settings) |
| from_parent.py | method | HPCAssignment._tool_request | episode function | task.py resolve_tool_request (raises: the parent's tool library has no home; unplaced) |
| goal.py | class | HPCGoal | episode function | goal.py and task.py INSTRUCTIONS |
| goal.py | method | HPCGoal.instructions | episode function | goal.py GOAL, UNIT, RESULT and task.py INSTRUCTIONS (the goal text, with the report form and report-repair sentences left out and the tool names written with underscores) |
| initial_information.py | function | initial_information | episode function | not placed (see unplaced_old_functions): selects readers of the old catalog and calls library.execution_initial_information.presentation of the old shared root |
| internal_summary.py | class | HPCSummary | episode function | messages/internal_summary.py and task.py decide (the class is dissolved) |
| internal_summary.py | method | HPCSummary.decision_context | episode function | messages/internal_summary.py internal_summary (the ledger fields come from the ledger_view of the last tool outcome, task.py ledger_view) and task.py decide; hpc_launch_deliveries from runtime_report_attempts is the launches of the summary; hpc_launch_report_form and hpc_report_form are not carried |
| measured_history.py | class | MeasuredHistory | episode function | task.py: the class is dissolved into the module-level functions of its methods |
| measured_history.py | method | MeasuredHistory._history | episode function | task.py measured_history |
| measured_history.py | method | MeasuredHistory._shared_history | episode function | task.py shared_history (the [:2000] count cap is not carried; the estimate_table calls are BLOCKED-ON-JOB-SERVICE) |
| measured_history.py | method | MeasuredHistory.export_closed | episode function | task.py export_closed (estimate_record: BLOCKED-ON-JOB-SERVICE) |
| measured_history.py | method | MeasuredHistory._refresh_measured_history | episode function | task.py hpc_history_refresh |
| portfolio_candidates.py | class | PortfolioCandidates | episode function | task.py: dissolved into hpc_candidate_propose |
| portfolio_candidates.py | method | PortfolioCandidates._propose_portfolio | episode function | task.py hpc_candidate_propose |
| portfolio_comparison.py | class | PortfolioComparison | episode function | task.py: the class is dissolved into the module-level functions of its methods |
| portfolio_comparison.py | method | PortfolioComparison._candidates | episode function | task.py candidates_of |
| portfolio_comparison.py | method | PortfolioComparison._features | episode function | task.py candidate_features |
| portfolio_comparison.py | method | PortfolioComparison._comparisons | episode function | task.py comparisons |
| portfolio_comparison.py | method | PortfolioComparison._candidate | episode function | task.py candidate_of |
| portfolio_comparison.py | method | PortfolioComparison._compare_portfolios | episode function | task.py hpc_compare |
| portfolio_planning.py | class | PortfolioPlanning | episode function | task.py: dissolved into hpc_plan |
| portfolio_planning.py | method | PortfolioPlanning._freeze_portfolio_plan | episode function | task.py hpc_plan |
| portfolio_state.py | class | PortfolioState | episode function | task.py: the class is dissolved into create_ledger, open_ledger and current_model |
| portfolio_state.py | method | PortfolioState.state | episode function | task.py create_ledger (the first open: the ledger, the owner identity, the tool request) and open_ledger (every later tool); the tool is hpc_open |
| portfolio_state.py | method | PortfolioState.initialize | episode function | task.py create_ledger (the reference model and the shared-history entry model) |
| portfolio_state.py | method | PortfolioState._current_model | episode function | task.py current_model |
| queue_observations.py | class | QueueObservations | episode function | task.py: the class is dissolved into the module-level functions of its methods |
| queue_observations.py | method | QueueObservations._observe_queue | episode function | task.py observe_queue (observe_queue_value and the estimate_table calls: BLOCKED-ON-JOB-SERVICE) |
| queue_observations.py | method | QueueObservations._queue | episode function | task.py queue_snapshot |
| queue_observations.py | method | QueueObservations._observe_resource_queue | episode function | task.py hpc_queue_observe |
| received_api_reports.py | function | received_api_reports | episode function | not placed (see unplaced_old_functions): selects declared readers of the old catalog |
| received_evidence.py | class | ReceivedEvidence | episode function | task.py: the class is dissolved into resolve_result_source, read_evidence and hpc_read |
| received_evidence.py | method | ReceivedEvidence._known | machinery | hand-kept held set (received_record_refs and record_selection); records.holds / ctx.store.holds replace it |
| received_evidence.py | method | ReceivedEvidence.resolve_received_reference | episode function | task.py resolve_result_source |
| received_evidence.py | method | ReceivedEvidence.read_evidence | episode function | task.py read_evidence |
| received_evidence.py | method | ReceivedEvidence._read_retained_evidence | episode function | task.py hpc_read |
| received_execution_information.py | function | received_execution_information | episode function | not placed (see unplaced_old_functions): selects declared readers of the old catalog |
| report_delivery.py | class | HPCWorkReportDelivery | machinery | the generic finish of the old runner (source_credit_view, pending_handles, release, journal, runtime_forms); messages/final_to_parent.py final_to_parent returns the result |
| report_delivery.py | method | HPCWorkReportDelivery.finish | machinery | as HPCWorkReportDelivery (the report facts are messages/final_to_parent.py facts) |
| resource_discovery.py | class | ResourceDiscovery | episode function | task.py: dissolved into hpc_discovery_run |
| resource_discovery.py | method | ResourceDiscovery._discover_resource | episode function | task.py hpc_discovery_run (run_command: BLOCKED-ON-JOB-SERVICE; the 90 second timeout and the output truncation are not carried) |
| task.py | class | HPCWorkTask | machinery | the decision machine of the old runner (task.py decide and action replace it) |
| task.py | method | HPCWorkTask.next | machinery | the old unit source loop (restore, in-process replay, completions, redelivery, model call, source failure) |
| task.py | method | HPCWorkTask.apply_response | episode function | task.py action (validation of the model's selection against the offered actions and the plans); the saved-exchange decoding, the report_update interpretation and record_effect are machinery |
| task.py | method | HPCWorkTask.execute | machinery | unit execution, journaling, credit saving and controller input of the old runner (the system runs a tool and prices the unit) |
| task_decision.py | class | HPCWorkTaskDecision | machinery | the old decision exchange (task.py decide replaces it) |
| task_decision.py | method | HPCWorkTaskDecision.call | machinery | the old model call with saved exchanges and contract information; the system records the call |
| task_decision.py | method | HPCWorkTaskDecision.instructions | episode function | task.py decide (instructions composition, see task_instructions.py) |
| task_decision.py | method | HPCWorkTaskDecision.conversation_key | machinery | conversation state |
| task_decision.py | method | HPCWorkTaskDecision.interpretation_context | machinery | the decision exchange |
| task_decision.py | method | HPCWorkTaskDecision.exchange_schema | machinery | the decision exchange |
| task_decision.py | method | HPCWorkTaskDecision.exchange_response | machinery | the decision exchange |
| task_decision.py | method | HPCWorkTaskDecision.validate_contract_exchange_request | machinery | saved-request check |
| task_decision.py | method | HPCWorkTaskDecision.validate_contract_exchange_history | machinery | saved-request check |
| task_decision.py | method | HPCWorkTaskDecision.exchange_decision | machinery | the decision exchange |
| task_decision.py | method | HPCWorkTaskDecision.complete_decision | machinery | the old model call wrapper; decide returns a ModelRequest |
| task_instructions.py | function | instructions | episode function | task.py decide (INSTRUCTIONS, then the tool-knowledge text and the launch-library text when those libraries are configured); the pending_child_delivery, wait and native_event_targets paragraphs are not carried |
| task_state.py | class | HPCWorkTaskState | machinery | checkpoint and restore state of the old runner |
| task_state.py | method | HPCWorkTaskState.__init__ | machinery | old task state (feedback, report values, restored flags) |
| task_state.py | method | HPCWorkTaskState.bind_execution_context | machinery | old execution context binding |
| task_state.py | method | HPCWorkTaskState.record_execution_failure | machinery | failure recovery of the old runner (a tool returns its failure as its outcome) |
| task_state.py | method | HPCWorkTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | method | HPCWorkTaskState.restore | machinery | checkpoint/restore |
| task_state.py | method | HPCWorkTaskState.record_effect | machinery | recorder (record_effect) |
| task_state.py | method | HPCWorkTaskState.checkpoint | machinery | checkpoint/restore |
| task_waiting.py | class | HPCWorkSuspension | machinery | wait/suspension machinery |
| task_waiting.py | method | HPCWorkSuspension.suspension_changed | machinery | wait/suspension machinery |
| to_child_execution_job_submission.py | function | authenticate_launch | episode function | task.py action (rejects a second launch of a plan and a launch of a closed plan) and messages/msg_to_child.py (the launch is built from the frozen plan's launch_assignment); the write of the launch:<plan_id> reservation into the ledger is not carried (a commission has no write; the system's unit journal is the one record of a launch) |
| to_child_execution_job_submission.py | class | LaunchPreparation | episode function | messages/msg_to_child.py (launch branch) and task.py hpc_plan (the input file) |
| to_child_execution_job_submission.py | method | LaunchPreparation.initial_decision_context | episode function | messages/msg_to_child.py launch: the hpc_execution_job message; task.py hpc_plan writes the immutable input file; the old EpisodeRef path lookup of the owner is the owner episode id of the ledger view |
| to_child_execution_progress_assessment.py | function | prepare_request | episode function | messages/msg_to_child.py (monitor branch: the assignment passes unchanged with the information unit) |
| to_child_execution_result_acquisition.py | function | assemble_request | episode function | messages/msg_to_child.py (results branch: the assignment and the initial result records); the goal, the receipt inheritance, the report contract declaration and the in-process order are machinery |
| to_child_hpc_allocation_execution.py | function | assignment_schema | episode function | messages/msg_to_child.py (hpc_execution branch names the children's form fields) |
| to_child_hpc_allocation_execution.py | function | commission_identity | episode function | task.py commission_identity (the identity copied into the assignment) |
| to_child_hpc_allocation_execution.py | function | prepare_request | episode function | messages/msg_to_child.py (hpc_execution branch); the check that the owner is the commissioning parent is by construction |
| to_child_hpc_resource_prediction.py | function | assignment_schema | episode function | messages/msg_to_child.py (hpc_prediction branch names the children's form fields) |
| to_child_hpc_resource_prediction.py | function | commission_identity | episode function | task.py commission_identity (the identity copied into the assignment) |
| to_child_hpc_resource_prediction.py | function | prepare_request | episode function | messages/msg_to_child.py (hpc_prediction branch); the check that the owner is the commissioning parent is by construction |
| to_parent.py | class | HPCReport | episode function | messages/final_to_parent.py (the class is dissolved) |
| to_parent.py | method | HPCReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (the four facts as selectable fields) |
| to_parent.py | method | HPCReport.facts | episode function | messages/final_to_parent.py facts |
| to_parent.py | method | HPCReport.resolve | episode function | messages/final_to_parent.py resolve |
| to_parent.py | method | HPCReport.validate_report | episode function | messages/final_to_parent.py validate_report (called by final_to_parent before the result is returned) |
| waiting.py | class | HPCActivityAdvice | episode function | task.py hpc_monitor_wait (the class is dissolved) |
| waiting.py | method | HPCActivityAdvice.activity_advice | machinery | read the old continuation estimator's journaled diagnostics (runtime_observations: activity mode, active next gain, pending expected credit) to suggest wait or collect; the three controllers offer none |
| waiting.py | method | HPCActivityAdvice._wait_for_original_observation | episode function | task.py hpc_monitor_wait (a wait TOOL: the async tool that awaits the monitor controller) |
| work_operations.py | class | HPCWorkOperations | episode function | task.py (the class is dissolved: TOOL_CATALOG, CHILD_CATALOG, TOOLS) |
| work_operations.py | method | HPCWorkOperations.catalog | episode function | task.py TOOL_CATALOG, CHILD_CATALOG and offered |
| work_operations.py | method | HPCWorkOperations.execute | episode function | task.py TOOLS (each tool is one branch; the action_intent, cached and save_action ledger bookkeeping is machinery: the system journals the unit and gives ctx.operation_key) |
| yield_estimator.py | class | HPCEpisodeYield | episode function | yield_estimator.py (the class is dissolved) |
| yield_estimator.py | method | HPCEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (AccumulationYieldController; cost and parameters from settings) |
| yield_estimator.py | method | HPCEpisodeYield.continuation_for_action | machinery | the continuation packet of the old HPCContinuationEstimator (README 3d, 7b: deleted; nothing but the controller stops the Episode); includes its min(1.0, ...) scale |
| yield_estimator.py | method | HPCEpisodeYield.practical_estimator | machinery | the old HPCContinuationEstimator (README 7b) |
