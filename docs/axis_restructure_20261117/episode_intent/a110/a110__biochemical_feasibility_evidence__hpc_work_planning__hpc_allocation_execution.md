# Intent: a110/biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution

Read from its own files at commit `97308b94c` (`git show HEAD:gene_annotation_episode/episodic_workflow/root/a110/biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/<file>`). Its child folders (`execution_job_submission/`, `execution_progress_assessment/`, `execution_result_acquisition/`) and `tests/` were not read for this note. Old role name: `hpc_execution`. The old parent role was `hpc` (`hpc_work_planning`), and its old sister was `hpc_prediction` (`hpc_resource_prediction`).

## Purpose (its own words, `goal.py`)

"Iterate toward the original accomplishment while balancing expected credit against real elapsed time and resource demand." Execution "prepares, launches, monitors and parses the selected work". The prediction sister "fits/measures/compares".

The episode owns one HPC allocation portfolio from start to finish, for a commission that its HPC parent froze:
- It discovers the remote environment.
- It proposes candidate portfolios (queue, nodes, wall_seconds, features, units with argv/env/effort, files, preparation).
- It observes the PBS queue, compares portfolios with the current shared model, and freezes one plan with its original forecast, scientific manifest and acceptance criteria.
- It commissions Launch, attaches the PBS handoff that comes back, and monitors it (including a scheduled timer wait).
- It collects unit results, checks them against the original acceptance predicates, and closes the allocation into measured history.

## Task and instructions

`goal.py` (`HPCGoal.instructions`) holds the whole instruction text. The main points:
- **Commission and scope:** prediction and execution are sisters. Both copy `hpc_child_commission` and carry the HPC parent's `owner_episode_id`. Both inherit `hpc_child_scope` exactly; `subject_refs` may be empty, and candidate/model/queue/resource IDs are not biological subject_refs. Return through `hpc_report_form`.
- **Discovery and candidates:** when candidates are absent, use `hpc.discovery.run`, then `hpc.candidate.propose`. Discovery is lightweight only: installation and staging belong to Launch, and computation belongs to the allocation.
- **Work-unit rules:** every work unit writes `result.json` and `progress.json` under `$HPC_UNIT_DIRECTORY`. `{allocation_workspace}` expands in files, argv, env and preparation. Compute runs on the allocated compute nodes through the facility launcher.
- **Plan and Launch:** compare portfolios with current queue features and measured history; a plan freezes its forecast, manifest and acceptance. Commission `launch -> launch_hpc` with that job and resource. Do not transcribe reference sources into a child goal or prescribe a setup/submit sequence. Use `hpc_launch_report_form`. If a completed Launch omitted its receipt, use `redeliver_report`; never commission another Launch.
- **Monitoring and collection:** use `hpc.monitor` only when another observation can change a decision. When `pending_action` is collect, use `hpc.results`. When `hpc_monitor_controllers` exists, use `hpc.monitor.wait`. Never poll for credit, duplicate a submitted attempt, or replace an uncertain submission.
- **Credit:** parent credit = accepted accomplishment + model improvement + fixed prospective forecast validation; "launch-local credits are not added again".

`task_instructions.py` appends text that belongs to the old runner, not to this episode:
- the `tool_knowledge` and `launch_instruction_library` instruction blocks;
- `pending_child_delivery` / `redeliver_report` repair text;
- the in-process `wait` on a `pending_child_` handle;
- the `native_event_targets` text.

## What it reads from its parent's assignment (`from_parent.py`)

The assignment schema is `{owner_episode_id (required), commission_id (enum of configured commissions) | commission_source_ref (reference)}`, with exactly one of the two commission fields.

`prepare_assignment` refuses a commission unless all of these hold:
- the parent role is `hpc`;
- `owner_episode_id` equals the parent's episode_id;
- the commission identity equals the parent's own.

When `require_commission_yield` is set, it also requires `yield_bindings` in the commission.

`_commission()` resolves the commission. For `commission_source_ref`, it reads through `hpc_commission_sources.read(store, ref, scope, resources)`. The commission carries `resource_id`, `objective`, `obligations` (id -> credit plus acceptance predicate), `preferences`, `candidates`, `history`, `validation_ids`, `model`, `credit.validation_slots`, `limits` (`queue_max_age_seconds`, `result_limit_bytes`), optional `monitoring`, `execution_profile` and `yield_bindings`.

`PortfolioState.state()` opens the existing owner's HPCLedger at `directory/hpc/digest(run_id, owner)`. The HPC parent creates this ledger, and the prediction sister shares it. `state()` requires the same scope and commission identity as the ledger owner.

## Children it may commission

`child_roles` = (`launch`, `monitor`, `results`).

| Child (new folder) | What it sends | What it takes back |
|---|---|---|
| `launch` -> `execution_job_submission` | The plan's frozen `launch_assignment`. `to_child_execution_job_submission.authenticate_launch` lets only that exact planned assignment consume a `launch_commission` reservation (one per plan; refused once the plan is `closed`). `LaunchPreparation.initial_decision_context` supplies `hpc_execution_job` to the launch and launch_hpc grandchild: `{plan_id, objective, scientific_manifest, scientific_acceptance (obligations), supplied_input_file (immutable launch-inputs/<plan_id>.json), coordinator_workspace, instructions}`. Those instructions say: use general terminal commands, keep identities and acceptance, run in the actual allocation, and investigate rather than duplicate. | `hpc_launch_report_form = {execution_handoff_refs: [ref ns execution_handoff]}`. The model then calls `hpc.handoff(plan_ref, handoff_ref)`. `from_child_execution_job_submission.original_launch_handoff` recovers the handoff of the frozen plan's `launch_hpc` from committed action results when Launch report repair is needed. `internal_summary` lists `hpc_launch_deliveries` from report attempts. |
| `monitor` -> `execution_progress_assessment` | `prepare_request` validates the assignment against the child's `_ASSIGNMENT`: selected target, known observations, requested fields, permitted records. "This parent requests information; it never polls here." | `receive_progress`: validates the typed form; every `episode_progress` reference is read through the progress provider; then `_receive_progress(episode_id, refs, digest(form, schema, scope), operation_key)`. |
| `results` -> `execution_result_acquisition` | `assemble_request` builds the request envelope: goal, scope, initial_report, optional job/episode assignment, `biochemical_feasibility_evidence`, report-contract declaration. | `receive_report`: collects the references in the received form for the parent's receipts. |

`prepare_child_request` passes assignments through unchanged, except for monitor's validation.

## Decision state and what the model sees

The old generic context (`decision_state.py`) is mostly old-runner presentation:
- goal, scope, working_state, visible_record_refs;
- current_credit, credit_binding, time_accounting, pending_work;
- last_local_outcome, feedback, controller, tools;
- report facts and forms.

`decision_inputs.py` adds old-runner items: resource_context, the launch instruction library, child_options, initial binding context, completed_action_reports and requested_action_history, execution_expectations and resource estimates, and waiting_support.

The part that belongs to this episode is `internal_summary.HPCSummary.decision_context`:
- Commission and owner: `hpc_commission`, `hpc_owner_episode_id`, `hpc_candidates`, `hpc_resource`, `hpc_child_scope`, `hpc_child_commission`.
- Launch handoff: `hpc_launch_deliveries`, `hpc_launch_report_form`, `hpc_tool_request`.
- Model and credit: `hpc_model_ref`, `hpc_credit`, `hpc_latest_comparison`, `hpc_model_support`, `hpc_report_form`.
- Plans and monitoring: `hpc_plans`, `hpc_latest_monitor`, `hpc_monitor_controllers`, `hpc_activity_decision` (`waiting.activity_advice`: wait/collect mode with suggested tool, active_next_gain, pending expected credit and upper bound, read from the last controller observation's diagnostics).
- Queue and history: `hpc_queue_refs`, optional `hpc_shared_memory`/`hpc_shared_history_refs`, `hpc_available_training_ids`.

The prompt is rendered by `library.hpc_prompt.render_hpc_prompt`.

## Tools it offers (`work_operations.py`)

| Tool | Arguments | Purpose |
|---|---|---|
| `hpc.read` | reference | Retained evidence by exact identity; a result Source is read only when it was received and its body matches the ledger (`received_evidence.py`). |
| `hpc.compare` | model_ref, queue_ref | Compare all portfolios, ranked by `net_expected_value`. |
| `hpc.history.refresh` | none | Only when shared memory is configured: age-weighted shared timing history; queue-only rows pooled per queue rule. |
| `hpc.discovery.run` | command | One SSH inspection, run as `cd /lus/flare/projects/BioReason-Aurora-Test && <command>`, cached in memory. |
| `hpc.candidate.propose` | candidate_json | Immutable candidate identity, validated through `validate_commission`. |
| `hpc.queue.observe` | none | PBS queue + ALCF score, cached when fresh. |
| `hpc.plan` | candidate_id, model_ref, queue_ref | Needs a fresh queue observation and an enabled, started Execution queue within min/max nodes/wall. Builds the plan and original/reference predictions and freezes the forecast slots. |
| `hpc.handoff` | plan_ref, handoff_ref | Handoff must be received and match `practical_assignment`. Attaches a MonitorCronController when the commission has `monitoring`. |
| `hpc.monitor` | plan_ref, refresh_queue | Native status, allocation-status.json, unit progress.json, measured metrics, refreshed queue forecast; freezes the conditional forecast. |
| `hpc.monitor.wait` | plan_ref | Reserves a schedule, waits on the persisted timer, then monitors exactly once. Collects immediately if terminal or outputs are ready. |
| `hpc.results` | plan_ref | Reads each finished unit's result.json (sha256 must match the completion receipt), publishes a Source (`episode.hpc_result`), and accepts the obligation when returncode is 0 and the `accepts` predicate holds. On a terminal state it records measured success and `closed`, and exports to shared history. |
| `hpc.allocation.order` | plan_ref, unit_ids | Reorder unstarted original units through `write_allocation_control`. |

Common actions are `tool`, `child`, `wait` and `redeliver_report`. `wait` is withheld when the commission has `monitoring`.

## Credit

- `credit.py`: `credit_kind` = 'operational'; `credit_view` = `HPCLedger.credit_view()`.
- Contributions, per the goal text: `actual:<obligation>` for accepted obligations, model improvement, and fixed prospective forecast validation slots (`ledger.freeze` / `ledger.score`). The validation slots are signed.
- Repeated polling adds no credit (`fact_sources.hpc_credit` meaning).
- Launch credits are not added again.

## Continuation (`yield_estimator.py`)

Old behaviour:
- `YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters), estimate_with_context=HPCContinuationEstimator(verify).with_continuation_cost(cutoff))`. Settings come from `commission['yield_bindings'][role]` = `{cutoff, parameters}` and are required when `require_commission_yield`.
- `continuation_for_action` builds an evidence packet: the remaining unaccepted obligations; per open plan, a valuation (`collect` = sum of the remaining obligations' credit as an upper bound, otherwise `choose_schedule` scaled by `prediction.compare`); `pending_by_obligation`; `active_credit_ceiling` = 0 when every remaining obligation is pending and there are no new training cases; `active_history_indices` (non-passive actions) from `runtime_observations` and `runtime_actions`.

Mapping to the three new yield estimators:
- The credit is signed and has no declared maximum, so the fit is **AccumulationYieldEstimator**, with settings from the commission's `yield_bindings` (cutoff = continuation cost, parameters).
- The pending-allocation valuation (expected credit while waiting/collecting) has no counterpart in the new estimator and must be carried as observation context or decided by the owner. This is a gap; it needs a decision.
- Flags under the house rules:
  - `scale = min(1.0, ...)` in `continuation_for_action` rescales the expected valuation. This is not a credit clamp, but it should be checked.
  - `resource_discovery` runs `subprocess.run(..., timeout=90)`. That is an elapsed-time cutoff, which is forbidden.
  - `_shared_history` keeps only `[:2000]` observations. That is a count limit.
  - stdout/stderr are truncated to 65536/8192 bytes. These are output windows, not stopping limits.

## What it reports to its parent (`to_parent.py`)

The facts:
- `hpc_credit` (number);
- `hpc_model_ref` (namespace `hpc_model`);
- `hpc_accepted_obligations`;
- `hpc_result_refs` (Sources that this episode received).

`validate_report` requires each `x-source` field to equal the recorded facts. `closed_models.frozen_reference` checks a closed `hpc_model` ref read-only against the owner ledger and the saved `runtime_forms` facts.

## Differences from sibling / similar episodes

- Its sister `hpc_resource_prediction` shares the same owner HPCLedger. Execution is the only one that launches, monitors and collects.
- It is the only A110 episode here with its own tool library (12 `hpc.*` tools).
- Its continuation is valuation-driven (pending obligations), not completion-proof-driven like its job children.

## File-by-file

Counts and uses for every name are in `runs/carry_over/calls/a110_04.tsv`. "BindingContext.x" means `context.x` on the old binding context.

| Old file | Lines | Own intent | Old-runner names |
|---|---|---|---|
| goal.py | 10 | Full instruction text (above) | none |
| task_instructions.py | 14 | Appended repair/wait/native-event text | `self.workflow.specialist`, `.binding_context`, `.knowledge`, `.launch_instructions`, `.permits_common_action`×2, `.native_event_information` |
| task.py | 183 | Own-action loop: decide -> apply_response -> execute -> credit. Wait failures become feedback. A model failure ends the source as `source_failed`. | `self.workflow.journal`, `.inprocess_replay`, `.execution_binding`, `.completions`, `.selected`, `.next_return`, `.resolve_pending_deliveries`, `.store`, `.resolver`, `.validate_report`, `.perform_selected_wait`, `.execute`, `.pending_work`, `.receive_native_outcome`, `.receive_outcome`, `.last_observed_credit`, `.source_credit_view`, `.controller_value`, `.decision_exchanges`, `.action_schema`, `.delivery_resolution_inputs`; `runtime.*` (SourceEnd, ReportRedelivery, ActionFailure, validate_form, observes_action_outcome, nullcontext, _json, ...); `providers.ModelCallError`; `episode_source_failure.record_source_failure`; tables `runtime_episodes`, `runtime_actions`, `runtime_model_calls` |
| task_decision.py | 289 | Decision call plus the request_context exchange protocol (lookups: child_options, composition_information, own attempts) | `self.workflow.journal`, `.decision_exchanges`, `.contract_information_profile`, `.validate_contract_information`, `.freeze_contract_information`, `.numerical_contracts`, `.decision_protocol`, `.receipts`, `.uses_received_record_context`, `.provider`, `.history_preview`, `.controller_binding`, `.services`, `.execute`, `.specialist`, `.store`, `.contract_information_reply`; about 30 `runtime.*` names (yield_table, model_snapshot, state_frame, apply_state_frame, ...); table `runtime_model_calls` |
| task_state.py | 108 | Source state, checkpoint/restore, recorded failure becomes a failed own action | `runtime.Episode`, `ActionLeaf`, `EFFECT_VERSION`, `interpretation_schema`, `Record`; `self.workflow.completions`×4, `.inprocess_replay`×7, `.execution_binding`×4, `.journal`×5, `.archive`, `.recover_commissions`, `.progress_provider`; table `runtime_actions`×5 |
| task_waiting.py | 9 | Suspension condition | `self.workflow.execution_handle`, `.execution_backend` |
| decision_inputs.py | 53 | Old decision inputs (above) | `self.workflow.resource_context`, `.launch_instructions`×2, `.available_child_roles`, `.episode_bindings`, `.binding_context`, `.pending_work`, `.execution_expectations`, `.resource_estimator`×4, `.native_estimation_context`, `.permits_common_action`, `.waiting_support`; `runtime.child_option_information`; `episode_work_report.*` |
| decision_state.py | 31 | Old generic context | about 20 `self.workflow.*` names; `runtime.FACT_*`, `_references_in`; table `runtime_actions` |
| report_delivery.py | 23 | Finish: form_with_facts, saved once | `self.workflow.journal`, `.facts`, `.release`, `.source_credit_view`, `.pending_handles`, `.episode_bindings`, `.binding_context`; `runtime.form_with_facts`, `Record`; table `runtime_forms` |
| internal_summary.py | 56 | The `hpc_*` decision context (above) | BindingContext.assignment/episode_id/run_id/scope; `communication.plain`; tables `runtime_report_attempts`, `runtime_episodes` |
| episode.py | 88 | Binding: roles, children, common actions, child request/receive routing, `create_execution_bindings` for 4 bindings | BindingContext.assignment/scope; old hook names (`decision_source_type`, `child_request_assembler`, `execution_child_report_receiver`, `receive_child_progress_for_role`) |
| configuration.py | 32 | Needs a pbs_ssh resource; validates commissions; optional ExecutionMemory; require_commission_yield | `communication.plain`×4 |
| credit.py | 16 | operational; ledger credit view | none |
| yield_estimator.py | 101 | Continuation (above) | `numerical.YieldController`, `YieldParameters`; BindingContext.role/run_id/episode_id; tables `runtime_observations`, `runtime_actions` |
| from_parent.py | 43 | Assignment schema / commission resolution | `communication.plain`×2 |
| to_parent.py | 41 | Facts / report validation | `episode_bindings.reference_in_context`; `communication.validate_form` |
| to_child_execution_job_submission.py | 70 | authenticate_launch, hpc_execution_job context | BindingContext.path×4/role×3/run_id/scope/assignment; `method_loop.identities.EpisodeRef`; `communication.plain` |
| from_child_execution_job_submission.py | 46 | Recovers the original launch handoff | BindingContext.path/role/run_id/scope/assignment; `EpisodeRef`; tables `runtime_actions`, `runtime_episodes` |
| to_child_execution_progress_assessment.py | 12 | Validate the monitor assignment | `communication.plain` |
| from_child_execution_progress_assessment.py | 23 | Receive progress refs | BindingContext.episode_id/scope; `communication.validate_form`; `method_loop.durable.content_digest` |
| to_child_execution_result_acquisition.py | 29 | Results request envelope | `runtime.EpisodeGoal`, `EpisodeRequest`, `Episode`, `validate_saved_fact_form`; `self.workflow.context`, `.grains`, `.receipts`, `.inprocess_completion_order`, `.launch_instructions`; `knowledge_inheritance` |
| from_child_execution_result_acquisition.py | 32 | Receive the results report | `self.workflow.receipts`, `.progress_provider`, `.specialist`, `.binding_context`×4, `.episode_bindings`, `.is_job_source`, `.receive_tool_attributions`; `EpisodeReturnRecords`; `delivery_counterpart` |
| work_operations.py | 54 | Tool catalog and dispatch | BindingContext.episode_id; `communication.plain` |
| waiting.py | 50 | activity_advice; hpc.monitor.wait | BindingContext.run_id/episode_id; table `runtime_observations` |
| allocation_handoff.py | 35 | hpc.handoff; route to monitor/order/results | `episode_bindings.reference_in_context` |
| allocation_observations.py | 82 | Targets, windows, allocation receipt, observe | `episode_bindings.reference_in_context` |
| allocation_order.py | 16 | hpc.allocation.order | none |
| allocation_results.py | 74 | hpc.results acceptance/publication/close | BindingContext.episode_id/scope; `communication.plain` |
| closed_models.py | 27 | Closed hpc_model ref check | `EpisodeReturnRecords`; table `runtime_forms` |
| forecast_observations.py | 80 | Freeze/measure/conditional forecast | none |
| measured_history.py | 82 | History, shared history, export_closed | none (`[:2000]` cap) |
| portfolio_candidates.py | 23 | hpc.candidate.propose | none |
| portfolio_comparison.py | 44 | hpc.compare | BindingContext.episode_id |
| portfolio_planning.py | 38 | hpc.plan | none |
| portfolio_state.py | 38 | Owner ledger, prior model, shared-history initial fit | BindingContext.assignment×4/role/scope |
| queue_observations.py | 35 | hpc.queue.observe with memory cache | none |
| received_evidence.py | 60 | hpc.read with received-source check | BindingContext.received_record_refs; `self.services.record_selection` |
| resource_discovery.py | 30 | hpc.discovery.run | none (timeout=90) |
| binding_record.py | 8 | as_record (hpc_episode_v1) | none |
| initial_information.py | 8 | catalog readers for this path | old catalog reader protocol |
| received_execution_information.py | 4 | catalog configured/received for this path | old catalog protocol |
| __init__.py | 0 | none | none |

## Carried over

One row per row of `runs/carry_over/functions/a110__biochemical_feasibility_evidence__hpc_work_planning__hpc_allocation_execution.tsv`; the first three columns are copied from it. "class" says whether the old function is old-runner machinery (not carried, with its reason) or an episode function (its new place). Task, tools and messages are in the episode folder; every library function used is an existing `episode_support/` module (no file was added there).

| old file | kind | name | class | new place or machinery reason |
|---|---|---|---|---|
| allocation_handoff.py | class | AllocationHandoff | episode function | task.py (the class held the two methods below; its tools are `hpc_handoff` and the shared opening of the allocation tools) |
| allocation_handoff.py | method | AllocationHandoff._attach_original_handoff | episode function | task.py `hpc_handoff` (the received-handoff test is `ctx.store.holds`; the target is read by `handoff_target`, BLOCKED-ON-JOB-SERVICE; the monitor controller attach is `monitor_attach`, not placed for this axis, reached only when the commission declares `monitoring`) |
| allocation_handoff.py | method | AllocationHandoff._work_on_original_allocation | episode function | task.py `original_plan` (the handoff-attached check) and `original_target`, called by `hpc_monitor`, `hpc_monitor_wait`, `hpc_results`, `hpc_allocation_order` |
| allocation_observations.py | class | AllocationObservations | episode function | task.py (the class held the methods below) |
| allocation_observations.py | method | AllocationObservations.targets | machinery | per-axis provider construction (`ExecutionTargetReader`); replaced by the `job_access` service and the held job ledger handoff record, both BLOCKED-ON-JOB-SERVICE (`handoff_target`, `observe_target`, `read_window`) |
| allocation_observations.py | method | AllocationObservations._target | episode function | task.py `original_target` |
| allocation_observations.py | method | AllocationObservations._window | episode function | task.py `window` (the read itself is `read_window`, BLOCKED-ON-JOB-SERVICE); library candidate |
| allocation_observations.py | method | AllocationObservations._allocation | episode function | task.py `allocation_receipt`; library candidate |
| allocation_observations.py | method | AllocationObservations._observe_original_allocation | episode function | task.py `observe_allocation` (the branch on the tool is `hpc_monitor` / `hpc_results`); library candidate |
| allocation_order.py | class | AllocationOrder | episode function | task.py (the class held the method below) |
| allocation_order.py | method | AllocationOrder._order_original_units | episode function | task.py `hpc_allocation_order` (the write is `write_allocation_control`, BLOCKED-ON-JOB-SERVICE) |
| allocation_results.py | class | AllocationResults | episode function | task.py (the class held the methods below) |
| allocation_results.py | method | AllocationResults._collected_unit_ids | episode function | task.py `collected_unit_ids`; library candidate |
| allocation_results.py | method | AllocationResults._uncollected_completed_unit_ids | episode function | task.py `uncollected_completed_unit_ids`; library candidate |
| allocation_results.py | method | AllocationResults._publish | episode function | task.py `publish_result` (through `ctx.store.artifact` and `ctx.store.put`) |
| allocation_results.py | method | AllocationResults._collect_original_results | episode function | task.py `collect_original_results`, called by `hpc_results`; library candidate |
| binding_record.py | class | HPCBindingRecord | machinery | binding_record.py: the binding's own record (the system records the declaration) |
| binding_record.py | method | HPCBindingRecord.as_record | machinery | the binding's own `as_record()` (README 3e); the settings are journaled by the system |
| closed_models.py | class | ClosedModels | machinery | validation of a closed episode's `hpc_model` reference from the old runner's saved forms (`runtime_forms`, `EpisodeReturnRecords`) |
| closed_models.py | method | ClosedModels.frozen_reference | machinery | reads `runtime_forms` and opens the ledger read-only by path: old-runner re-validation; the check that a reported model is in the ledger is `resolve` in messages/final_to_parent.py |
| configuration.py | class | HPCConfiguration | episode function | ctx.settings (documented in task.py): `directory`, `resources`, `shared_execution_memory` and the credit units; the constructor's checks of static commissions and of a configured `pbs_ssh` resource are not carried: the commission is read from the owner ledger, which validated it, and `resource_of` raises on a resource that is not configured |
| configuration.py | method | HPCConfiguration.__init__ | episode function | ctx.settings (task.py, `memory_enabled`, `resource_of`); the yield bindings are settings `cutoff` and `parameters` (yield_estimator.py); `require_commission_yield` is not carried (the settings are required) |
| credit.py | class | HPCEpisodeCredit | episode function | credit.py |
| credit.py | method | HPCEpisodeCredit.credit_kind | machinery | `credit_kind` is deleted (README 3d); the kind `operational` is the docstring of credit.py |
| credit.py | method | HPCEpisodeCredit.credit_view | episode function | credit.py `credit` (reads the credit view each tool returned in its outcome as `ledger_view`; the ledger is read in task.py `ledger_view`) |
| decision_inputs.py | class | HPCWorkDecisionInputs | episode function | task.py `decide` (the context) and messages/internal_summary.py |
| decision_inputs.py | method | HPCWorkDecisionInputs.decision_inputs | episode function | task.py `decide`: the launch-instruction library, the tool knowledge, `requested_action_history` and `resource_tool_estimates` (BLOCKED-ON-JOB-SERVICE: estimate_table); not carried: `resource_context`, `child_option_information` (the model's child options are `CHILD_CATALOG` in task.py), `completed_action_reports`, `pending_work`, `waiting_support`, `native_estimation_context` (old runner, pending work and wait machinery) |
| decision_state.py | class | HPCWorkDecisionState | episode function | messages/internal_summary.py and task.py `decide` |
| decision_state.py | method | HPCWorkDecisionState.decision_state | episode function | messages/internal_summary.py `internal_summary` (outcome history, ledger view, launches) and `decide` (the context); the reads of `runtime_actions`, `receipt_projection`, `delivery_status` and `pending_work` are machinery and not carried |
| episode.py | class | HPCEpisode | episode function | episode.py `HPCAllocationExecution(EpisodeBinding)` |
| episode.py | method | HPCEpisode.child_roles | episode function | task.py `CHILD_SLOTS` (launch, monitor, results) |
| episode.py | method | HPCEpisode.allowed_children | episode function | task.py `CHILD_SLOTS` |
| episode.py | method | HPCEpisode.permitted_common_actions | machinery | the permitted action kinds: the task offers tools and child commissions only; the `wait` action (offered only without `monitoring`) and `redeliver_report` are deleted (wait/redelivery machinery); a scheduled wait is the tool `hpc_monitor_wait` |
| episode.py | method | HPCEpisode.prepare_child_request | episode function | messages/msg_to_child.py `msg_to_child` (monitor branch: the assignment passed unchanged) |
| episode.py | method | HPCEpisode.receive_child_progress_for_role | machinery | received-progress admission into the old progress provider; the monitor's typed result is read in messages/read_from_child.py |
| episode.py | method | HPCEpisode.execution_child_report_receiver | machinery | returned `receive_report` (the old receipt-ledger admission of the results child's report) for the role `results`: receipts and report admission are the system's |
| episode.py | method | HPCEpisode.child_request_assembler | machinery | returned `assemble_request` for the role `results` (the old request, receipt-inheritance and report-contract assembly): the commission is messages/msg_to_child.py `msg_to_child` (slot `results`) |
| episode.py | function | create_execution_bindings | machinery | home factory: constructed the launch, resource and results bindings with the caller's operands; there is no table of bindings |
| forecast_observations.py | class | ForecastObservations | episode function | task.py (the class held the methods below) |
| forecast_observations.py | method | ForecastObservations._freeze | episode function | task.py `freeze_forecast`; library candidate |
| forecast_observations.py | method | ForecastObservations._last_forecast | episode function | task.py `last_forecast`; library candidate |
| forecast_observations.py | method | ForecastObservations._measure | episode function | task.py `measure`; library candidate |
| forecast_observations.py | method | ForecastObservations._update_conditional_forecast | episode function | task.py `update_conditional_forecast`, called by `hpc_monitor` and `hpc_monitor_wait`; library candidate |
| from_child_execution_job_submission.py | class | LaunchReceiptCustody | machinery | receipt custody of a launch report across report repair |
| from_child_execution_job_submission.py | method | LaunchReceiptCustody.original_launch_handoff | machinery | recovered the handoff from `runtime_actions` / `runtime_episodes` by SQL across a report repair; the launch child's admitted result names its handoff records, the system receipts them, and the unit outcome is in `view.outcomes` |
| from_child_execution_progress_assessment.py | function | receive_progress | machinery | admitted `episode_progress` references into the old progress provider (received-progress ledger); the monitor returns its progress observations in typed fields |
| from_child_execution_result_acquisition.py | function | receive_report | machinery | admitted the results child's report into the old receipt ledger (`EpisodeReturnRecords`, `receipts.receive`, `receive_tool_attributions`) and the progress provider (`receive_form`, `receive_child_progress`): custody (`record_refs` fields of the child's result) and the system's admission replace it; what the parent keeps is messages/read_from_child.py `read_from_child` (slot `results`) |
| from_parent.py | class | HPCAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | method | HPCAssignment.assignment_schema | episode function | messages/read_from_parent.py `ASSIGNMENT_FORM` (`owner_episode_id`, `commission_id`, `commission_source_ref`; new fields `scope`, `input_refs`) |
| from_parent.py | method | HPCAssignment.commission_identity | episode function | messages/read_from_parent.py `read_from_parent` (the key `commission_identity`); compared with the owner record in task.py `open_ledger` |
| from_parent.py | method | HPCAssignment._commission | episode function | task.py `open_ledger` (`ledger.commission`: the commission is read from the owner ledger, not again from a configuration or a Store source) |
| from_parent.py | method | HPCAssignment.prepare_assignment | episode function | messages/read_from_parent.py `read_from_parent` (exactly one commission identity); the check that the commissioning parent is the `hpc` episode named by `owner_episode_id` (it read the parent's role and assignment) is not carried: the ledger of that owner must carry this scope and commission identity (`open_ledger`); the `yield_bindings` presence check is the required settings |
| goal.py | class | HPCGoal | episode function | goal.py `GOAL`, `UNIT`, `RESULT`; the instruction text is task.py `INSTRUCTIONS` |
| goal.py | method | HPCGoal.instructions | episode function | task.py `INSTRUCTIONS` (the whole text; the redeliver_report sentence and the dotted tool names are changed) |
| initial_information.py | function | initial_information | episode function | UNPLACED: `resource_information(catalog.readers(binding_path, context))` of the old `execution_initial_information.presentation` (not in `episode_support/`); the model is shown the configured resource (`hpc_resource`) and the tool estimates in task.py `decide`. Listed in unplaced_old_functions |
| internal_summary.py | class | HPCSummary | episode function | messages/internal_summary.py |
| internal_summary.py | method | HPCSummary.decision_context | episode function | messages/internal_summary.py `internal_summary` and task.py `ledger_view` (the ledger fields) and `decide` (the context keys `hpc_*`); the `runtime_report_attempts` read of launch deliveries is the launches kept from the launch child's reports |
| measured_history.py | class | MeasuredHistory | episode function | task.py (the class held the methods below) |
| measured_history.py | method | MeasuredHistory._history | episode function | task.py `measured_history`; library candidate |
| measured_history.py | method | MeasuredHistory._shared_history | episode function | task.py `shared_history` (the first-2000 cut is not carried; the history read is `estimate_history`, BLOCKED-ON-JOB-SERVICE: estimate_table); library candidate |
| measured_history.py | method | MeasuredHistory.export_closed | episode function | task.py `export_closed` (the write is `estimate_record`, BLOCKED-ON-JOB-SERVICE: estimate_table); library candidate |
| measured_history.py | method | MeasuredHistory._refresh_measured_history | episode function | task.py `hpc_history_refresh` |
| portfolio_candidates.py | class | PortfolioCandidates | episode function | task.py (the class held the method below) |
| portfolio_candidates.py | method | PortfolioCandidates._propose_portfolio | episode function | task.py `hpc_candidate_propose` |
| portfolio_comparison.py | class | PortfolioComparison | episode function | task.py (the class held the methods below) |
| portfolio_comparison.py | method | PortfolioComparison._candidates | episode function | task.py `candidates_of`; library candidate |
| portfolio_comparison.py | method | PortfolioComparison._features | episode function | task.py `candidate_features`; library candidate |
| portfolio_comparison.py | method | PortfolioComparison._comparisons | episode function | task.py `comparisons`; library candidate |
| portfolio_comparison.py | method | PortfolioComparison._candidate | episode function | task.py `candidate_of`; library candidate |
| portfolio_comparison.py | method | PortfolioComparison._compare_portfolios | episode function | task.py `hpc_compare` |
| portfolio_planning.py | class | PortfolioPlanning | episode function | task.py (the class held the method below) |
| portfolio_planning.py | method | PortfolioPlanning._freeze_portfolio_plan | episode function | task.py `hpc_plan` (it also writes the launch input file the old launch preparation wrote at the launch child's first decision) |
| portfolio_state.py | class | PortfolioState | episode function | task.py (the class held the methods below) |
| portfolio_state.py | method | PortfolioState.state | episode function | task.py `open_ledger` (the ledger directory is `settings['directory']` / `hpc` / digest of run id and owner; the owner's scope and commission identity must equal this commission's; the ledger library is not carried: BLOCKED-ON-STORE-ACCESS) |
| portfolio_state.py | method | PortfolioState.initialize | episode function | task.py `open_ledger` (reference model, and the fit from shared history when `shared_execution_memory` is set) |
| portfolio_state.py | method | PortfolioState._current_model | episode function | task.py `current_model`; library candidate |
| queue_observations.py | class | QueueObservations | episode function | task.py (the class held the methods below) |
| queue_observations.py | method | QueueObservations._observe_queue | episode function | task.py `observe_queue` (the acquisition is `observe_queue_value`, BLOCKED-ON-JOB-SERVICE: job_access; the cache is `estimate_latest` / `estimate_observe`, BLOCKED-ON-JOB-SERVICE: estimate_table); library candidate |
| queue_observations.py | method | QueueObservations._queue | episode function | task.py `queue_snapshot`; library candidate |
| queue_observations.py | method | QueueObservations._observe_resource_queue | episode function | task.py `hpc_queue_observe` |
| received_evidence.py | class | ReceivedEvidence | episode function | task.py (the class held the methods below) |
| received_evidence.py | method | ReceivedEvidence._known | machinery | the hand-kept set of received references and `services.record_selection`: replaced by `ctx.store.holds` |
| received_evidence.py | method | ReceivedEvidence.resolve_received_reference | episode function | task.py `resolve_result_source` (held source of provider `episode.hpc_result`, this run, within the scope) |
| received_evidence.py | method | ReceivedEvidence.read_evidence | episode function | task.py `read_evidence`; library candidate |
| received_evidence.py | method | ReceivedEvidence._read_retained_evidence | episode function | task.py `hpc_read` |
| received_execution_information.py | function | received_execution_information | episode function | UNPLACED: `catalog.configured` / `catalog.received` of the old result-reader catalog (not in `episode_support/`; no reader of this axis is selected by this episode). Listed in unplaced_old_functions |
| report_delivery.py | class | HPCWorkReportDelivery | machinery | report delivery: typed form built once from saved facts (`form_with_facts`, `Record`, `runtime_forms`, `release`); the typed report is the system's result of messages/final_to_parent.py |
| report_delivery.py | method | HPCWorkReportDelivery.finish | machinery | saved the report form and released the episode (report_form and workflow.release machinery) |
| resource_discovery.py | class | ResourceDiscovery | episode function | task.py (the class held the method below) |
| resource_discovery.py | method | ResourceDiscovery._discover_resource | episode function | task.py `hpc_discovery_run` (the remote command is `run_command`, BLOCKED-ON-JOB-SERVICE: job_access; the old 90-second timeout and the output truncation are not carried) |
| task.py | class | HPCWorkTask | episode function | task.py `decide`, `action`, `TOOLS` (the task class was the decision loop) |
| task.py | method | HPCWorkTask.next | episode function | task.py `decide` (the model request) and `action`; the replay, checkpoint, source-failure and delivery-resolution branches are machinery |
| task.py | method | HPCWorkTask.apply_response | episode function | task.py `action` (validation of the answer against the schema, `Rejected(feedback)`); the report-update admission (`interpret_schema`, `validate_report`, `report_values`), `record_effect` and the redelivery branch are machinery |
| task.py | method | HPCWorkTask.execute | episode function | task.py `TOOLS` (each tool is one unit; its outcome, a failure included, is the unit's outcome); the journal rows, `receive_outcome`, `controller_value`, the wait branch and `ActionFailure` are machinery |
| task_decision.py | class | HPCWorkTaskDecision | machinery | the model call and the decision exchange |
| task_decision.py | method | HPCWorkTaskDecision.call | machinery | provider call and its recording: `decide` returns a `ModelRequest` |
| task_decision.py | method | HPCWorkTaskDecision.instructions | episode function | task.py `decide` (`INSTRUCTIONS`, then the launch-instruction and tool-knowledge texts when their directories are set) |
| task_decision.py | method | HPCWorkTaskDecision.conversation_key | machinery | conversation sessions (every `ModelRequest` carries the full context) |
| task_decision.py | method | HPCWorkTaskDecision.interpretation_context | machinery | the running report interpretation (`report_update`) |
| task_decision.py | method | HPCWorkTaskDecision.exchange_schema | machinery | decision-exchange schema |
| task_decision.py | method | HPCWorkTaskDecision.exchange_response | machinery | decision-exchange response |
| task_decision.py | method | HPCWorkTaskDecision.validate_contract_exchange_request | machinery | saved-request check of the decision exchange |
| task_decision.py | method | HPCWorkTaskDecision.validate_contract_exchange_history | machinery | saved-exchange history check |
| task_decision.py | method | HPCWorkTaskDecision.exchange_decision | machinery | the decision-exchange loop (a lookup is a tool: `hpc_read`) |
| task_decision.py | method | HPCWorkTaskDecision.complete_decision | machinery | provider call and its recording |
| task_instructions.py | function | instructions | episode function | task.py `decide` / `INSTRUCTIONS`; the paragraphs about `pending_child_delivery`, `redeliver_report`, the pending-child wait and the native-event targets describe actions that no longer exist and are not carried |
| task_state.py | class | HPCWorkTaskState | machinery | per-episode decision state, restore and checkpoint |
| task_state.py | method | HPCWorkTaskState.__init__ | machinery | decision-state constructor (feedback, report values, restored flags) |
| task_state.py | method | HPCWorkTaskState.bind_execution_context | machinery | binding of the old execution context |
| task_state.py | method | HPCWorkTaskState.record_execution_failure | machinery | recorded a failed tool action as a failed outcome: the tool returns its failure as its outcome |
| task_state.py | method | HPCWorkTaskState.restore_checkpoint | machinery | checkpoint restore |
| task_state.py | method | HPCWorkTaskState.restore | machinery | restore of the decision state from the journal |
| task_state.py | method | HPCWorkTaskState.record_effect | machinery | effect recording |
| task_state.py | method | HPCWorkTaskState.checkpoint | machinery | checkpoint |
| task_waiting.py | class | HPCWorkSuspension | machinery | suspension of the episode for the external executor |
| task_waiting.py | method | HPCWorkSuspension.suspension_changed | machinery | wait/suspension machinery |
| to_child_execution_job_submission.py | function | authenticate_launch | episode function | messages/msg_to_child.py (the launch commission is built from the frozen plan) and task.py `action` (a plan is launched once; a closed plan is not launched); the reservation row `launch_commission` is not written (the system's unit journal is the one record of a launch) |
| to_child_execution_job_submission.py | class | LaunchPreparation | episode function | messages/msg_to_child.py and task.py `hpc_plan` |
| to_child_execution_job_submission.py | method | LaunchPreparation.initial_decision_context | episode function | messages/msg_to_child.py: `hpc_execution_job` rides in `ChildMessage.message` of the launch commission (the launch child's form has no field for it; its parent input keeps the message); the input file is written by task.py `hpc_plan` (the old code wrote it at the launch child's first decision) |
| to_child_execution_progress_assessment.py | function | prepare_request | episode function | messages/msg_to_child.py (monitor branch: the assignment is passed on; the child's form admits it) |
| to_child_execution_result_acquisition.py | function | assemble_request | episode function | messages/msg_to_child.py `msg_to_child` (slot `results`: the assignment with the one handoff record, the selector, `resource_kind` and `acquired_record_unit`); the old goal, report-contract declaration (`validate_saved_fact_form`), `job_assignment`, `episode_assignment`, `knowledge_inheritance` receipts and `Episode.identity` are old-runner machinery |
| to_parent.py | class | HPCReport | episode function | messages/final_to_parent.py |
| to_parent.py | method | HPCReport.fact_sources | episode function | messages/final_to_parent.py `RETURN_FORM` (`hpc_credit`, `hpc_model_ref`, `hpc_accepted_obligations`, `hpc_result_refs`, selectable; plus `credit` and `finding`) |
| to_parent.py | method | HPCReport.facts | episode function | messages/final_to_parent.py `facts` and `final_to_parent` |
| to_parent.py | method | HPCReport.resolve | episode function | messages/final_to_parent.py `resolve` (the namespace `hpc_model`; the namespace `source` is the system's held-record check) |
| to_parent.py | method | HPCReport.validate_report | episode function | messages/final_to_parent.py `validate_report` (the `validate_form` step raises `NotImplementedError('validate_form_not_built:A110')`) |
| waiting.py | class | HPCActivityAdvice | episode function | task.py `hpc_monitor_wait` (the class held the advice and the wait) |
| waiting.py | method | HPCActivityAdvice.activity_advice | machinery | read the old estimator's journaled diagnostics (`runtime_observations`, `activity_mode`) to suggest a tool; that estimator is deleted and the yield table (`action_yields`) is shown instead |
| waiting.py | method | HPCActivityAdvice._wait_for_original_observation | episode function | task.py `hpc_monitor_wait`; its `MonitorCronController` (`reserve`, `wait`) is not in this axis's library (`jobs/hpc/biochemical_feasibility_evidence/hpc_monitoring.py` holds `validate_policy` only): `monitor_reserve` and `monitor_wait` raise `NotImplementedError('hpc_monitor_controller_not_placed:A110...')` with the intended call kept |
| work_operations.py | class | HPCWorkOperations | episode function | task.py `TOOL_CATALOG`, `CHILD_CATALOG`, `TOOLS` |
| work_operations.py | method | HPCWorkOperations.catalog | episode function | task.py `TOOL_CATALOG` (tool names with underscores; `hpc_history_refresh` only with the shared memory: `offered`) and `CHILD_CATALOG` |
| work_operations.py | method | HPCWorkOperations.execute | machinery | the dispatcher with the operation ledger (`ledger.cached`, `ledger.put('action_intent')`, `ledger.save_action`): the system's attempts journal and `ctx.operation_key` replace it; the dispatch is `TOOLS` |
| yield_estimator.py | class | HPCEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | method | HPCEpisodeYield.yield_controller | episode function | yield_estimator.py `yield_controller` (`AccumulationYieldController`, cost and parameters from the settings `cutoff` and `parameters`) |
| yield_estimator.py | method | HPCEpisodeYield.continuation_for_action | machinery | the per-action continuation packet (README 3d: estimator packets have no way into the controller; the three old comparisons are deleted) |
| yield_estimator.py | method | HPCEpisodeYield.practical_estimator | machinery | `HPCContinuationEstimator` with its verifier (README 7b: deleted, no episode supplies a forecast) |
