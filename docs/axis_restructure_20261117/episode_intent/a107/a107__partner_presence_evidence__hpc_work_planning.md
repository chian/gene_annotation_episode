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
