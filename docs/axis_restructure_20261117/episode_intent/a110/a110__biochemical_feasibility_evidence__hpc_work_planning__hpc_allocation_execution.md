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
