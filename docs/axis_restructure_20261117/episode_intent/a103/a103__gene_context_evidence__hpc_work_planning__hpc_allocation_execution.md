# a103/gene_context_evidence/hpc_work_planning/hpc_allocation_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/hpc_work_planning/hpc_allocation_execution/<file>` (only files directly in this
folder; its child folders `execution_job_submission/`, `execution_progress_assessment/`,
`execution_result_acquisition/` and `tests/` are not covered here). Old binding class `HPCEpisode`
(`binding_path = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution'`,
`commissioning_parent = 'gene_context_evidence/hpc_work_planning'`, `roles = ('hpc_execution',)`, `entry_roles = ()`),
decision source `HPCWorkTask`, prompt renderer `library.hpc_prompt.render_hpc_prompt`, record version `hpc_episode_v1`.

## What it is for (its goal, in its own words)

`goal.py` (abridged only by the ellipses):

> Iterate toward the original accomplishment while balancing expected credit against real elapsed time and resource
> demand. The hpc parent can commission hpc_prediction and hpc_execution as sisters: prediction fits/measures/compares;
> execution prepares, launches, monitors and parses the selected work. Both assignments copy hpc_child_commission exactly
> and carry the hpc parent owner_episode_id. Both sisters inherit exactly hpc_child_scope ... Use hpc_report_form as the
> return contract. ... Queue/setup costs belong to an allocation, which should carry enough useful work. When candidates
> are absent, discover the remote environment and documentation with hpc.discovery.run, then design candidate
> portfolios with hpc.candidate.propose. ... You choose the real inputs, database, executable commands, resources,
> worker code and preparation instructions. Never fabricate inputs or receipts. Every work unit writes result.json and
> progress.json under os.environ["HPC_UNIT_DIRECTORY"] ... Compute commands must run on allocated compute nodes using the
> facility launcher. Compare portfolios using current queue features and measured history. A plan freezes its original
> forecast, scientific manifest and acceptance criteria. Commission launch -> launch_hpc with that actual job and
> resource. ... Use hpc_launch_report_form as the Launch return contract. If a completed Launch return omitted its
> receipt, use redeliver_report ...; report repair must not commission another Launch. Attach that received handoff. Use
> hpc.monitor once when another observation can affect your decision ... Use hpc.results directly for known parsing.
> Commission monitor/results children only for actual investigation. ... When hpc_monitor_controllers is present, select
> hpc.monitor.wait for a scheduled observation ... without credit for sleeping. ... Do not poll for credit or duplicate a
> submitted attempt. Never replace an uncertain submission. Accepted accomplishment, model improvement, and fixed
> prospective forecast validation are the only parent credit components; launch-local credits are not added again.

The full text is in `goal.py`; it is the planning parent's text minus "Commission hpc_prediction only when model
improvement warrants its own iteration." (this episode is the execution sister and has no prediction child).

## Task and instructions

Each unit is an HPC tool action, a child commission (`launch`, `monitor`, `results`), a wait (unless the commission
binds `monitoring`, in which case `hpc.monitor.wait` replaces it) or a report redelivery. Instructions
(`task_instructions.py`): goal + tool knowledge + launch library + pending-child repair + wait + native-event texts.

## What it reads from its parent's assignment

`from_parent.assignment_schema`: `owner_episode_id` (required; the planning parent's episode id), and exactly one of
`commission_id` (enum of configured commissions) or `commission_source_ref` (a Store commission source read with
`hpc_commission_sources.read`). Admission: the parent must be role `hpc`, `owner_episode_id` must be the parent's own
episode id and the commission identity must equal the parent's; with `require_commission_yield` the commission must carry
`yield_bindings`. The scope must equal the owner's recorded scope (`portfolio_state.state`).

## Children

- `launch` -> `hpc_allocation_execution/execution_job_submission`. Sends the frozen plan's `launch_assignment`
  (`hpc.plan` returns it); `authenticate_launch` lets only the exact planned launch consume the plan's slot and refuses
  a closed allocation; the Launch child's initial context gets `hpc_execution_job` (plan id, objective, manifest,
  acceptance, supplied input file, coordinator workspace, instructions). Takes back `execution_handoff_refs` under
  `hpc_launch_report_form`; `original_launch_handoff` recovers the actual handoff across report repair. The handoff is
  then attached with `hpc.handoff`.
- `monitor` -> `hpc_allocation_execution/execution_progress_assessment`. Sends a `monitor_assignment_v1` unchanged
  (validated). Takes back its `episode_progress` references into received progress.
- `results` -> `hpc_allocation_execution/execution_result_acquisition`. Sent and received through the generic child
  path (no private to/from file); used only for actual investigation (`hpc.results` parses known outputs directly).
Child credits are not added ("launch-local credits are not added again").

## Decision state shown to the model

The old generic view (as the monitor's, without the annotation-axis branch) plus `internal_summary.decision_context`:
`hpc_commission`, `hpc_owner_episode_id`, `hpc_candidates`, `hpc_resource`, `hpc_child_scope`, `hpc_child_commission`,
`hpc_launch_deliveries` (delivery refs and delivered forms of Launch children), `hpc_launch_report_form`
(`execution_handoff_refs`), `hpc_tool_request`, `hpc_model_ref`, `hpc_credit`, `hpc_latest_comparison`,
`hpc_model_support`, `hpc_report_form` (`hpc_credit`, `hpc_model_ref`, `hpc_result_refs`), `hpc_plans`,
`hpc_latest_monitor`, `hpc_monitor_controllers`, `hpc_activity_decision` (wait/collect advice), `hpc_queue_refs`,
`hpc_shared_memory`/`hpc_shared_history_refs`, `hpc_available_training_ids`. Per-call inputs add expectations keyed
`hpc_execution` and `requested_action_history`.

## Tools (`work_operations.catalog`)

`hpc.read`, `hpc.compare` (model_ref, queue_ref), `hpc.history.refresh` (with shared memory), `hpc.discovery.run`
(command), `hpc.candidate.propose` (candidate_json; schema described in the tool text), `hpc.queue.observe`, `hpc.plan`
(candidate_id, model_ref, queue_ref), `hpc.handoff` (plan_ref, handoff_ref), `hpc.monitor` (plan_ref, refresh_queue),
`hpc.monitor.wait` (plan_ref), `hpc.results` (plan_ref), `hpc.allocation.order` (plan_ref, unit_ids). Every action is
recorded once per operation key in the HPC ledger; invalid ones return `invalid` with recovery feedback.

## Credit

Kind `operational`; `HPCLedger.credit_view()`: signed measured credit from accepted obligations (each obligation's
`credit`), model improvement and fixed prospective forecast validation slots; "repeated polling adds none". Unbounded.

## Continuation

`yield_estimator.yield_controller`: requires `require_commission_yield`; uses
`commission['yield_bindings']['hpc_execution']` `{cutoff, parameters}` with `HPCContinuationEstimator(verify)
.with_continuation_cost(cutoff)`. `continuation_for_action` records evidence per action: zero when all obligations are
accepted; otherwise, for each open plan with a monitor controller, the expected continuation credit (unresolved
acceptance upper bound when outputs await collection, else `choose_schedule` valuation scaled to the attainable
expected credit), `pending_action = collect`, active credit ceiling 0 when all remaining obligations are pending, no new
training cases and single-unit candidates, and the indices of active (non-wait, non-passive) actions. In the new layout
the nearest of the three is **completion with a target** (target = the commission's obligation credits); the pending
expectation and continuation cost are this episode's own operands.

## Report to its parent

`hpc_credit` (number), `hpc_model_ref` (namespace `hpc_model`), `hpc_accepted_obligations`, `hpc_result_refs` (received
`episode.hpc_result` sources); the parent asks with `hpc_report_form`. Fact fields must equal recorded evidence.

## Differences from similar episodes

Shares `decision_state.py`, `task_decision.py`, `task_state.py`, `report_delivery.py`, `task_instructions.py`,
`task_waiting.py`, `from_child_execution_progress_assessment.py` and `to_child_execution_progress_assessment.py` with its
parent `hpc_work_planning`; every other file is its own. Against the planning parent: no `hpc_prediction`/
`hpc_execution` children (only `launch, monitor, results`), no entry role, assignment requires `owner_episode_id` and a
parent-owned commission (the parent's assignment instead admits `tool_request`), goal minus the prediction sentence.

Notes for the port: `resource_discovery.py` hard-codes the Aurora project path and uses `subprocess.run(timeout=90)` (a
time limit); `configuration.py`/`yield_estimator.py` require the yield binding flag.

## Files

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | Empty package marker. | none |
| `allocation_handoff.py` | 35 | `hpc.handoff`: bind a received PBS handoff to the frozen plan (must match `practical_assignment`), optionally attach a `MonitorCronController`; route `hpc.monitor`, `hpc.monitor.wait`, `hpc.results`, `hpc.allocation.order` to the original allocation; refuses before a handoff with recovery text "redeliver_report ... Do not launch replacement work." | `BindingContext`: scope; `import`: episode_bindings, hpc_monitoring |
| `allocation_observations.py` | 83 | Observe the original job once per action (`native_status`, `allocation-status.json` <= 512 KiB, per-unit `progress.json`), check identity (plan, job, manifest digest, unit ids), compute telemetry, phase change and recent fraction rate, record measurements; dispatch to forecast update or result collection. | `BindingContext`: scope; `import`: episode_bindings, execution_progress, hpc_campaign×3 |
| `allocation_order.py` | 16 | `hpc.allocation.order`: reorder original pending units at the next unit boundary through the native allocation control; only original unit ids. | none |
| `allocation_results.py` | 74 | `hpc.results`: read each completed/failed unit's `result.json` at its original unit directory, verify its completion hash, publish a `episode.hpc_result` Store source, accept an obligation only when returncode 0 and the commission's acceptance predicate holds; close and export the allocation when the job is terminal. | `BindingContext`: episode_id×2, scope; `import`: communication, hpc_campaign, hpc_queue (module) |
| `binding_record.py` | 10 | Binding identity record `hpc_episode_v1`: path, resources, commissions, shared execution memory, `require_commission_yield`. | none |
| `closed_models.py` | 27 | Validate a closed `hpc_model` identifier read-only from the owner's ledger after closure. | `BindingContext`: assignment, episode_id, role, run_id×2, scope; `import`: communication, episode_return_records, hpc_queue (module); `table`: runtime_forms |
| `configuration.py` | 32 | Construction settings: resources (at least one `pbs_ssh`), `commissions` (validated campaigns), optional `shared_execution_memory` (`ExecutionMemory`), `require_commission_yield` (then every commission needs `yield_bindings`). | `import`: communication, execution_memory, hpc_campaign |
| `credit.py` | 16 | Credit kind `operational`; credit view = the HPC ledger's `credit_view()`. | none |
| `decision_inputs.py` | 64 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Expectations keyed by role `hpc_execution`; `requested_action_history` for HPC contexts. | `import`: episode_work_report×2, library.hpc_prompt, runtime, runtime (module); `runtime`: child_option_information; `self.workflow`: available_child_roles, binding_context×2, episode_bindings, execution_expectations, job_episodes×2, launch_instructions×2, native_estimation_context, native_event_information×2, pending_work, permits_common_action, resource_context, resource_estimator×4, store×2, waiting_support |
| `decision_state.py` | 31 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Same view as its parent planning episode (identical file). | `import`: runtime (module), runtime×6; `runtime`: FACT_MEANINGS, FACT_SOURCES, Mapping×2, _plain×2, _references_in, json; `self.workflow`: binding_context, catalog, controller_binding, delivery_status, extra_report_sources, job_episode_options, journal×2, knowledge, local_outcome_preview, pending_work, receipt_projection, run_id, source_credit_binding, source_credit_view, specialist, store×3, tools, working_state; `table`: runtime_actions; `view`: child_reports×2, controller_state, model_inputs |
| `episode.py` | 75 | The binding: path, parent `gene_context_evidence/hpc_work_planning`, role `hpc_execution`, no entry roles, decision source `HPCWorkTask`, prompt renderer `render_hpc_prompt`, `replaces_default_instructions`. Child roles `launch, monitor, results`; permitted actions `tool, child, redeliver_report` (+ `wait` unless the commission has `monitoring`). Monitor requests pass through `prepare_request`; monitor child progress is received by `receive_progress`. Also `create_execution_bindings` constructing its five descendant execution bindings with the caller's operands. | `BindingContext`: assignment, role, scope; `import`: gene_context_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.api_job_execution.episode, gene_context_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.episode, gene_context_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.hpc_job_execution.episode, gene_context_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.local_job_execution.episode, gene_context_evidence.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.episode, library.hpc_prompt |
| `forecast_observations.py` | 80 | Freeze forecasts with their validation slots; last forecast; measured queue/setup/work durations (censored when unfinished); `hpc.monitor` updates the conditional prediction (optional queue refresh), remaining work and "Choose an event/elapsed threshold where changed evidence could alter a decision." | `import`: hpc_campaign, hpc_queue (module), library, library.hpc_resource_prediction×2 |
| `from_child_execution_job_submission.py` | 46 | Recover the frozen plan's actual Launch handoff across a Launch report repair, from committed native outcomes under this HPC owner path only (never a sibling's conversation). | `BindingContext`: assignment, path×2, role, run_id×3, scope×2; `import`: communication, hpc_ledger, hpc_queue (module), method_loop.identities; `table`: runtime_actions, runtime_episodes |
| `from_child_execution_progress_assessment.py` | 23 | Admit the monitor child's `episode_progress` references into the HPC parent's received progress (same rule as the monitor's own receiver). | `BindingContext`: episode_id×3, scope×2; `import`: communication×2, domain, method_loop.durable |
| `from_parent.py` | 43 | Assignment form and admission (see "What it reads"). | `BindingContext`: assignment, episode_id, role; `import`: communication, domain, execution_contracts, hpc_commission_sources |
| `goal.py` | 10 | Goal text (quoted); identical to the planning parent's except it omits the parent's last sentence "Commission hpc_prediction only when model improvement warrants its own iteration." | none |
| `internal_summary.py` | 56 | Decision context (see "Decision state"). | `BindingContext`: assignment, episode_id, run_id, scope; `import`: communication, library; `table`: runtime_episodes, runtime_report_attempts |
| `measured_history.py` | 82 | Training history: commission history + latest shared history + one latest observation per closed allocation; shared history query (queue timing resource-wide, work timing only with matching profile; PBS queues not pooled unless modelled; at most 2000 rows); export closed allocations to shared memory; `hpc.history.refresh`. | `import`: execution_guidance, hpc_history, library.hpc_resource_prediction |
| `portfolio_candidates.py` | 23 | `hpc.candidate.propose`: retain a model-authored candidate portfolio (immutable identity), validated with the commission. | `import`: hpc_campaign |
| `portfolio_comparison.py` | 44 | `hpc.compare`: predict and compare every candidate with a model and queue observation, excluding already credited obligations; sorted by net expected value. | `BindingContext`: episode_id; `import`: hpc_queue (module), library |
| `portfolio_planning.py` | 38 | `hpc.plan`: freeze one candidate into a plan with original prediction/reference forecasts on a fresh, enabled, started Execution queue whose node/wall limits the candidate satisfies. | `import`: hpc_campaign, hpc_queue (module), library |
| `portfolio_state.py` | 38 | The HPC ledger opened at `hpc/<digest(run, owner)>`; sister scope and commission must equal the original owner's; initialise reference model and optional shared-history model. | `BindingContext`: assignment×4, role, scope×2; `import`: communication, domain, hpc_ledger, hpc_queue (module), library |
| `queue_observations.py` | 35 | `hpc.queue.observe`: PBS queue snapshot (shared-memory cache if fresh within `queue_max_age_seconds`); freshness required before planning. | `import`: execution_guidance, hpc_queue (module) |
| `received_evidence.py` | 60 | Which `episode.hpc_result` sources this episode received; `hpc.read` of retained evidence (history rows, ledger records, owned received result sources). | `BindingContext`: received_record_refs, scope; `import`: communication; `services`: record_selection |
| `report_delivery.py` | 25 | Old-runner closure (identical to the planning parent's). | `import`: library.private_policy_call, library.report_fact_assembly, runtime (module), runtime×4; `runtime`: Record×2, _json×2, form_with_facts, json; `self.workflow`: binding_context, episode_bindings, facts, journal×2, pending_handles, release×2, source_credit_view; `table`: runtime_forms×2 |
| `resource_discovery.py` | 30 | `hpc.discovery.run`: one lightweight remote command through the configured SSH argv, run inside `/lus/flare/projects/BioReason-Aurora-Test`; stdout 64 KiB / stderr 8 KiB; shared-memory cache; uses `subprocess.run(..., timeout=90)`. | `import`: execution_guidance, hpc_queue (module) |
| `task.py` | 182 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Report grain `hpc_execution`; carries `validate_hpc_launch_report_contract`. | `import`: episode_source_failure, library.action_contracts, library.hpc_handoff_report_contract, library.private_policy_call, providers, runtime (module), runtime×18; `runtime`: ActionFailure, ContractInformationError, Draft202012Validator×2, EventTargetError×2, ReportBoundaryError, ReportRedelivery×2, SourceEnd×2, ValidationError×2, WorkflowError×2, _decode_recorded_action_response, _json×5, _wait_target_feedback×2, inspect, json×8, nullcontext×5, observes_action_outcome, schema_failure_diagnostic, validate_form; `self.workflow`: action_schema, completed_unit×3, completions×3, controller_value×2, decision_exchanges×3, delivery_resolution_inputs, execute, execution_binding×7, inprocess_replay×4, journal×7, last_observed_credit, next_return, pending_work, perform_selected_wait, receive_native_outcome, receive_outcome, resolve_pending_deliveries, resolver, run_id×2, selected×3, source_credit_view, store×7, validate_report; `table`: runtime_actions×8, runtime_episodes, runtime_model_calls×2; `view`: units_consumed×4 |
| `task_decision.py` | 289 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Identical to the planning parent's. | `import`: runtime (module), runtime×30; `name`: composition_information×2; `runtime`: CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION×2, DECISION_EXCHANGE_PROTOCOL×5, Draft202012Validator, Mapping×2, ValidationError×5, WorkflowError×14, _ASSIGNMENT_TRANSPORT, _action_generation_schema×2, _category_yield_parameters, _digest, _json×14, _object×3, _plain×2, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema×2, instructional_model_context×4, is_contract_information, json×3, lookup_attempts, model_snapshot×2, requested_contract_information×2, schema_failure_diagnostic×2, sqlite3, state_frame, yield_table; `self.workflow`: contract_information_profile, contract_information_reply, controller_binding, decision_exchanges×4, decision_protocol×3, execute, freeze_contract_information, history_preview, journal×3, numerical_contracts, provider×3, receipts×4, run_id, services×2, specialist, store×2, uses_received_record_context×2, validate_contract_information×5; `table`: runtime_model_calls×8 |
| `task_instructions.py` | 14 | Instruction composition: goal + tool knowledge + launch library + pending-child repair + wait + native-event texts. | `self.workflow`: binding_context, knowledge, launch_instructions, native_event_information, permits_common_action×2, specialist |
| `task_state.py` | 108 | Old-runner decision-loop machinery shared (as copies) by every A103 episode: replay through `completions`/`inprocess_replay`, journal rows, model call, admission of the selection and of `report_update`, execution, credit after the action. Own intent: only the details noted. Failed own action recorded for kind `tool` only. | `import`: episode_source_failure, runtime (module), runtime×9; `runtime`: ActionLeaf, EFFECT_VERSION, Episode, Record, _json×2, _object, _plain, interpretation_schema, json×4; `self.workflow`: archive, completions×4, controller_value, execution_binding×4, inprocess_replay×7, journal×5, progress_provider×2, recover_commissions, run_id, source_credit_view, store×2; `table`: runtime_actions×5 |
| `task_waiting.py` | 9 | Wait suspension to the execution backend. | `self.workflow`: execution_backend, execution_handle×2 |
| `to_child_execution_job_submission.py` | 67 | `authenticate_launch` (only the exact planned launch may consume the plan's allocation slot; closed allocations refuse) and `initial_decision_context` for the Launch child: `hpc_execution_job` with plan id, objective, scientific manifest, acceptance, supplied input file (immutable `launch-inputs/<plan>.json`), coordinator workspace and its instruction text. | `BindingContext`: assignment×2, episode_id, path×2, role×3, run_id×3, scope×2; `import`: communication, hpc_ledger, hpc_queue (module), method_loop.identities, practical_execution_state |
| `to_child_execution_progress_assessment.py` | 12 | Monitor request: the HPC parent passes a `monitor_assignment_v1` unchanged after schema validation ("This parent requests information; it never polls here"). | `import`: communication, domain |
| `to_parent.py` | 41 | Report facts `hpc_credit`, `hpc_model_ref`, `hpc_accepted_obligations`, `hpc_result_refs`; references resolve to own models or the receiving context; fact fields must equal recorded evidence. | `import`: communication, episode_bindings |
| `waiting.py` | 50 | `activity_advice` from the last controller diagnostic (wait/collect) and `hpc.monitor.wait`: schedule the next observation through the monitor controller, wait, observe once; terminal or ready outputs mean collect now. | `BindingContext`: episode_id, run_id; `import`: hpc_monitoring; `table`: runtime_observations |
| `work_operations.py` | 54 | Tool catalog and dispatch (see "Tools"); every action recorded in the ledger once per operation key. | `BindingContext`: episode_id; `import`: communication, domain, execution_contracts |
| `yield_estimator.py` | 101 | Continuation (see "Continuation") and `continuation_for_action` evidence. | `BindingContext`: assignment, episode_id×3, role×5, run_id×3, scope; `import`: hpc_monitoring, library, library.hpc_continuation, numerical×2; `table`: runtime_actions×2, runtime_observations; `yield`: HPCContinuationEstimator, YieldController, YieldParameters, estimate_with_context, with_continuation_cost |
