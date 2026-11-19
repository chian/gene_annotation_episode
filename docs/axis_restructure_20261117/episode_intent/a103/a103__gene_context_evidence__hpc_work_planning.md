# a103/gene_context_evidence/hpc_work_planning — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/hpc_work_planning/<file>`
(only files directly in this folder; no `grading/` or `scoring/` subfolder; child folders execution_job_submission,
execution_progress_assessment, execution_result_acquisition, hpc_allocation_execution, hpc_resource_prediction and
`tests/` are not covered). Old binding class: `HPCEpisode` (`binding_path = 'gene_context_evidence/hpc_work_planning'`,
`commissioning_parent = 'gene_context_evidence'`, `roles = entry_roles = ('hpc',)`), decision source `HPCWorkTask`,
prompt renderer `library.hpc_prompt.render_hpc_prompt`, `replaces_default_instructions = True`. Binding record
version `hpc_episode_v1`.

## What it is for (its goal, in its own words)

`goal.py` `instructions()` (one paragraph, abridged only at "..."):

> Iterate toward the original accomplishment while balancing expected credit against real elapsed time and resource
> demand. The hpc parent can commission hpc_prediction and hpc_execution as sisters: prediction fits/measures/
> compares; execution prepares, launches, monitors and parses the selected work. Both assignments copy
> hpc_child_commission exactly and carry the hpc parent owner_episode_id. Both sisters inherit exactly hpc_child_scope
> ... Use hpc_report_form as the return contract. ... No historical validation support means no invented
> model-improvement credit. Queue/setup costs belong to an allocation, which should carry enough useful work. When
> candidates are absent, discover the remote environment and documentation with hpc.discovery.run, then design
> candidate portfolios with hpc.candidate.propose. Discover is for lightweight inspection; leave installation and
> file staging to Launch, and scientific computation to the actual allocation. You choose the real inputs, database,
> executable commands, resources, worker code and preparation instructions. Never fabricate inputs or receipts. Every
> work unit writes result.json and progress.json under os.environ["HPC_UNIT_DIRECTORY"] ... Compute commands must run
> on allocated compute nodes using the facility launcher. Commission hpc_prediction only when model improvement
> warrants its own iteration. Compare portfolios using current queue features and measured history. A plan freezes
> its original forecast, scientific manifest and acceptance criteria. Commission launch -> launch_hpc with that actual
> job and resource. ... Use hpc_launch_report_form as the Launch return contract. If a completed Launch return omitted
> its receipt, use redeliver_report with the existing delivery_ref ...; report repair must not commission another
> Launch. Attach that received handoff. Use hpc.monitor once when another observation can affect your decision ...
> Use hpc.results directly for known parsing. Commission monitor/results children only for actual investigation.
> ... When hpc_monitor_controllers is present, select hpc.monitor.wait for a scheduled observation ... This preserves
> pending accomplishment value across waits without credit for sleeping. ... Do not poll for credit or duplicate a
> submitted attempt. Never replace an uncertain submission. Accepted accomplishment, model improvement, and fixed
> prospective forecast validation are the only parent credit components; launch-local credits are not added again.

## Task and instructions

`task_instructions.instructions()`: goal + tool knowledge + launch library instructions (when present) + the repair
paragraph + the wait paragraph (when wait permitted) + native event paragraph (when present and wait permitted). No
ACTION_BOUNDARY / credit / report / history blocks (differs from the monitor). The task files are the old iterator
copied with grain `'hpc'`; own additions: `HPCWorkTask._validate_hpc_launch_report_contract`
(`library.hpc_handoff_report_contract`), failed-execution recording only for `tool` actions (not `reason`), decision
state without the annotation-axis branch, decision inputs add `requested_action_history` for HPC contexts.

## What it reads from its parent's assignment

`from_parent.assignment_schema`: either `commission_id` (enum of configured commissions) or `commission_source_ref`
(a reference the parent actually received; read through `hpc_commission_sources.read` with scope and resources);
optional `tool_request` {name, resources api|local|hpc, arguments_json, result_reader, objective} resolved against
the parent's real frozen scientific tool library (`gene_context_evidence_binding.tool_library`), validated arguments
and an actual result reader, plus an `execution_rule` ("Implement this exact requested computation through the HPC
template ... do not replace scientific grading with the allocation acceptance score."). When commission yield is
required, the commission must carry `yield_bindings`.

## Children it may commission

`child_roles = ('hpc_prediction', 'hpc_execution', 'launch', 'monitor', 'results')`, all allowed.
- `hpc_prediction` — sends `to_child_hpc_resource_prediction.prepare_request`: commission identity +
  `owner_episode_id` equal to this hpc episode; takes back via `from_child_hpc_resource_prediction.receive_prediction_report`
  (old receipts/progress/timing admission of the typed form).
- `hpc_execution` (hpc_allocation_execution) — same send rule (`to_child_hpc_allocation_execution`); same receiver
  body (`from_child_hpc_allocation_execution.receive_allocation_report`).
- `launch` (execution_job_submission → launch_hpc) — `to_child_execution_job_submission.authenticate_launch`: only
  the exact planned launch assignment may consume the allocation slot (reservation `launch:<plan_id>`, refused after
  closure); `LaunchPreparation.initial_decision_context` gives launch/launch_hpc children `hpc_execution_job`
  {plan_id, objective, scientific_manifest, scientific_acceptance, supplied_input_file (immutable plan JSON),
  coordinator_workspace, instructions}. Takes back: `execution_handoff_refs` per `hpc_launch_report_form`;
  `from_child_execution_job_submission.original_launch_handoff` recovers the actual receipt across report repair.
- `monitor` (execution_progress_assessment) — sends the monitor's own `monitor_assignment_v1` unchanged after schema
  validation ("This parent requests information; it never polls here."); takes back `episode_progress` refs into
  received progress (`receive_child_progress_for_role`).
- `results` (execution_result_acquisition) — assignment passed through unchanged.

## Decision state and what it shows the model

Common decision state plus `HPCSummary.decision_context`: `hpc_commission`, `hpc_owner_episode_id`, `hpc_candidates`,
`hpc_resource`, `hpc_child_scope`, `hpc_child_commission`, `hpc_launch_deliveries` (delivery_ref + delivered form of
launch children), `hpc_launch_report_form`, `hpc_tool_request`, `hpc_model_ref`, `hpc_credit`,
`hpc_latest_comparison`, `hpc_model_support`, `hpc_report_form`, `hpc_plans`, `hpc_latest_monitor`,
`hpc_monitor_controllers`, `hpc_activity_decision` (wait/collect advice from the latest iterator estimate),
`hpc_queue_refs`, shared memory/history refs, `hpc_available_training_ids`.

## Tools it offers

`work_operations.catalog()`: `hpc.read`, `hpc.compare`, `hpc.history.refresh` (only with shared memory),
`hpc.discovery.run` (one SSH command in `/lus/flare/projects/BioReason-Aurora-Test`), `hpc.candidate.propose`,
`hpc.queue.observe`, `hpc.plan`, `hpc.handoff`, `hpc.monitor`, `hpc.monitor.wait`, `hpc.results`,
`hpc.allocation.order`. Every action is cached in the HPC ledger by operation key with an action intent. Common
actions: tool, child, redeliver_report, plus wait when the commission has no `monitoring` section.

## How its credit is counted

`credit_kind = 'operational'`; `credit_view` = the HPC ledger's credit view: accepted actual obligations (per
obligation credit), model improvement, fixed prospective forecast validation slots; signed; repeated polling adds
none; launch-local credits are not added again.

## Continuation

`HPCEpisodeYield.yield_controller` (only with `require_commission_yield`): `commission['yield_bindings'][role]` →
`YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters), estimate_with_context=
HPCContinuationEstimator(verify).with_continuation_cost(cutoff))`. `continuation_for_action` writes per-action
evidence: remaining obligations, pending value per obligation (collect upper bound when outputs await acceptance;
`choose_schedule` valuation when running), active credit ceiling 0 when everything remaining is pending and no new
training cases, active history indices. New-layout estimator: **completion with a target** (remaining obligations);
settings per commission: `cutoff`, `parameters`.

Flag for the port: `yield_estimator.py` scales attainable expected credit by `min(1.0, expected_continuation_credit /
total)` — a clamp/rescale on expected credit, contrary to "credit never bounded, clamped or rescaled".
Also: `resource_discovery.py` uses `subprocess.run(..., timeout=90)` and truncates stdout to 65536 / stderr to 8192
bytes; `measured_history._shared_history` keeps at most 2000 observations — time/count limits to remove.

## What it reports to its parent

`to_parent.fact_sources/facts`: `hpc_credit` (signed measured credit), `hpc_model_ref` (current model),
`hpc_accepted_obligations`, `hpc_result_refs` (received episode.hpc_result Sources). `validate_report` requires
fact-sourced fields to equal recorded facts; `hpc_model` refs resolve to ledger models.

## Differences from siblings / similar episodes

- Only one of the four with a ledger-backed tool set and five child kinds; children are siblings under its own
  folder (`create_execution_bindings` constructs the five execution bindings under `hpc_work_planning/`).
- The two `from_child_hpc_*` receivers are textually identical apart from names; both use the old receipts path.
- Wait is withheld when the commission carries `monitoring` (then hpc.monitor.wait is used instead).
- Its monitor child request skips the monitor's own direct-dependency rule (schema check only).

## File by file
| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `allocation_handoff.py` | 35 | hpc.handoff: bind a received Launch handoff to the frozen plan (assignment must match), optionally attach the forecast-valued monitor cron controller; route hpc.monitor/.wait/.results/.allocation.order on the original allocation, refusing work before a handoff is attached (with redelivery recovery advice). | import:episode_bindings, import:hpc_monitoring |
| `allocation_observations.py` | 83 | Observe the original PBS job and allocation-status.json (identity checked), unit progress.json, phase change and recent fraction rate; record a measurement; then update forecast or collect results. | import:episode_bindings, import:execution_progress, import:hpc_campaign×3 |
| `allocation_order.py` | 16 | hpc.allocation.order: reorder only original pending units via allocation control. | none |
| `allocation_results.py` | 74 | hpc.results: read each finished unit's result.json (hash must match completion receipt), publish an episode.hpc_result Source, accept against the original obligation predicate; close allocation and export measured history. | import:communication, import:hpc_campaign, import:root.a103 |
| `binding_record.py` | 10 | Binding descriptor: resources, commissions, shared execution memory, require_commission_yield. | none |
| `closed_models.py` | 27 | Authenticate an hpc_model reference from a closed episode's saved facts and read-only ledger. | EpisodeReturnRecords, import:communication, import:episode_return_records, import:root.a103, runtime_forms |
| `configuration.py` | 32 | Settings: store, run_id, directory, resources (must include a pbs_ssh), commissions (validated), optional shared_execution_memory, require_commission_yield (then every commission needs yield_bindings). | import:communication, import:execution_memory, import:hpc_campaign |
| `credit.py` | 16 | Credit kind 'operational'; credit_view is the HPC ledger's credit view. | none |
| `decision_inputs.py` | 64 | Copy of decision inputs for role 'hpc' plus requested_action_history for HPC contexts. | import:episode_work_report×2, import:library.hpc_prompt, import:root.a103, import:runtime, runtime.child_option_information, workflow.available_child_roles, workflow.binding_context×2, workflow.episode_bindings, workflow.execution_expectations, workflow.job_episodes×2, workflow.launch_instructions×2, workflow.native_estimation_context, workflow.native_event_information×2, workflow.pending_work, workflow.permits_common_action, workflow.resource_context, workflow.resource_estimator×4, workflow.store×2, workflow.waiting_support |
| `decision_state.py` | 31 | Copy of decision state without the annotation-axis branch. | import:root.a103, import:runtime, runtime_actions, runtime.FACT_MEANINGS, runtime.FACT_SOURCES, runtime.json, runtime.Mapping×2, runtime._plain×2, runtime._references_in, workflow.binding_context, workflow.catalog, workflow.controller_binding, workflow.delivery_status, workflow.extra_report_sources, workflow.job_episode_options, workflow.journal×2, workflow.knowledge, workflow.local_outcome_preview, workflow.pending_work, workflow.receipt_projection, workflow.run_id, workflow.source_credit_binding, workflow.source_credit_view, workflow.specialist, workflow.store×3, workflow.tools, workflow.working_state |
| `episode.py` | 87 | Wires HPC planning: path gene_context_evidence/hpc_work_planning, role 'hpc', task HPCWorkTask, render_hpc_prompt, replaces default instructions. Children hpc_prediction, hpc_execution, launch, monitor, results. Without monitoring in the commission it may wait. Also builds the five child execution bindings under hpc_work_planning/. | import:gene_context_evidence.hpc_work_planning.execution_job_submission.api_job_execution.episode, import:gene_context_evidence.hpc_work_planning.execution_job_submission.episode, import:gene_context_evidence.hpc_work_planning.execution_job_submission.hpc_job_execution.episode, import:gene_context_evidence.hpc_work_planning.execution_job_submission.local_job_execution.episode, import:gene_context_evidence.hpc_work_planning.execution_result_acquisition.episode, import:library.hpc_prompt |
| `forecast_observations.py` | 80 | Freeze forecasts with validation slots, last forecast, measured metrics (queue/setup/work), conditional forecast update after hpc.monitor (optional queue refresh, reorder-aware remaining work). | import:hpc_campaign, import:library, import:library.hpc_resource_prediction×2, import:root.a103 |
| `from_child_execution_job_submission.py` | 46 | Recover this frozen plan's actual Launch receipt (handoff) from committed native outcomes under the owning HPC path. | import:communication, import:hpc_ledger, import:method_loop.identities, import:root.a103, runtime_actions, runtime_episodes |
| `from_child_execution_progress_assessment.py` | 23 | Admit the monitor child's episode_progress references into this parent's received progress. | import:communication, import:domain, import:method_loop.durable |
| `from_child_hpc_allocation_execution.py` | 31 | Receive the allocation child's admitted form through the old receipts/progress/timing path. | EpisodeReturnRecords, import:episode_return_records, import:root.a103, runtime._json, runtime.json, runtime._references_in, runtime_report_attempts×2, runtime.WorkflowError, workflow.binding_context×2, workflow.episode_bindings, workflow.is_job_source×2, workflow.job_episodes×2, workflow.native_timing_information, workflow.progress_provider×2, workflow.receipts×3, workflow.receive_tool_attributions, workflow.run_id×4, workflow.store×7 |
| `from_child_hpc_resource_prediction.py` | 31 | Receive the prediction child's admitted form (identical body to the allocation receiver). | EpisodeReturnRecords, import:episode_return_records, import:root.a103, runtime._json, runtime.json, runtime._references_in, runtime_report_attempts×2, runtime.WorkflowError, workflow.binding_context×2, workflow.episode_bindings, workflow.is_job_source×2, workflow.job_episodes×2, workflow.native_timing_information, workflow.progress_provider×2, workflow.receipts×3, workflow.receive_tool_attributions, workflow.run_id×4, workflow.store×7 |
| `from_parent.py` | 69 | Assignment: commission_id or commission_source_ref (received by parent), optional tool_request resolved against the scientific tool library with the exact reader and execution_rule; commission yield binding required when enabled. | import:communication, import:domain, import:execution_contracts, import:hpc_commission_sources |
| `goal.py` | 10 | Goal text (quoted in the doc). | none |
| `__init__.py` | 0 | Package marker; no intent. | none |
| `internal_summary.py` | 56 | Decision context: commission, owner, candidates, resource, child scope/commission, launch deliveries + launch report form, tool request, model ref/support, credit, latest comparison, report form, plans, latest monitor, monitor controllers, activity advice, queue refs, shared memory/history, available training ids. | import:communication, import:library, runtime_episodes, runtime_report_attempts |
| `measured_history.py` | 82 | Training history: commission history + shared history + one latest measurement per closed allocation; shared history query by execution profile with per-queue pooling rules; export of closed allocations; hpc.history.refresh. | import:execution_guidance, import:hpc_history, import:library.hpc_resource_prediction |
| `portfolio_candidates.py` | 23 | hpc.candidate.propose: immutable candidate identity, validated against the commission. | import:hpc_campaign |
| `portfolio_comparison.py` | 44 | hpc.compare: predict each candidate with the model and queue features, compare net expected value excluding already-credited obligations. | import:library, import:root.a103 |
| `portfolio_planning.py` | 38 | hpc.plan: require a fresh queue observation and an enabled started Execution queue within limits; build plan, freeze original prediction and reference forecast. | import:hpc_campaign, import:library, import:root.a103 |
| `portfolio_state.py` | 38 | The HPC ledger per (run, episode) with owner and tool request; initial reference model and optional shared-history fitted model. | import:communication, import:domain, import:hpc_ledger, import:library, import:root.a103 |
| `queue_observations.py` | 35 | Queue observation through memory cache within queue_max_age_seconds or live PBS; hpc.queue.observe. | import:execution_guidance, import:root.a103 |
| `received_evidence.py` | 60 | Known refs; resolve episode.hpc_result Sources owned by this ledger; hpc.read. | import:communication |
| `report_delivery.py` | 25 | Copy of old finish(): with no report contract return credit + pending handles + binding facts; otherwise compose the parent's typed form once from recorded facts + interpretations and save it. Own intent: recorded facts fill fact fields, interpretations are the last admitted report_update; no model call at closure. | import:library.private_policy_call, import:library.report_fact_assembly, import:root.a103, import:runtime, runtime_forms×2, runtime.form_with_facts, runtime._json×2, runtime.json, runtime.Record×2, workflow.binding_context, workflow.episode_bindings, workflow.facts, workflow.journal×2, workflow.pending_handles, workflow.release×2, workflow.source_credit_view |
| `resource_discovery.py` | 30 | hpc.discovery.run: one SSH command in the project directory, memory-cached inventory. | import:execution_guidance, import:root.a103 |
| `task_decision.py` | 289 | Copy of decision call + exchange loop (no annotation-axis branch). | import:root.a103, import:runtime, runtime._action_generation_schema×2, runtime.apply_state_frame, runtime._ASSIGNMENT_TRANSPORT, runtime._category_yield_parameters, runtime.child_option_information, runtime.composition_lookup_schema×2, runtime.CONTRACT_INFORMATION_OPERATIONS, runtime.DECISION_CONTEXT_VERSION×2, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest, runtime.Draft202012Validator, runtime.instructional_model_context×4, runtime.is_contract_information, runtime._json×14, runtime.json×3, runtime.lookup_attempts, runtime.Mapping×2, runtime_model_calls×8, runtime.model_snapshot×2, runtime._object×3, runtime._plain×2, runtime._recorded_action_generation_schema, runtime._recorded_assignment_transport, runtime._references_in, runtime.requested_contract_information×2, runtime.schema_failure_diagnostic×2, runtime.sqlite3, runtime.state_frame, runtime.ValidationError×5, runtime.WorkflowError×14, runtime.yield_table, workflow.contract_information_profile, workflow.contract_information_reply, workflow.controller_binding, workflow.decision_exchanges×4, workflow.decision_protocol×3, workflow.execute, workflow.freeze_contract_information, workflow.history_preview, workflow.journal×3, workflow.numerical_contracts, workflow.provider×3, workflow.receipts×4, workflow.run_id, workflow.services×2, workflow.specialist, workflow.store×2, workflow.uses_received_record_context×2, workflow.validate_contract_information×5 |
| `task_instructions.py` | 14 | Instruction composition: goal + tool knowledge + launch library + repair, wait and native event guidance (no ACTION_BOUNDARY/credit/report guidance blocks). | workflow.binding_context, workflow.knowledge, workflow.launch_instructions, workflow.native_event_information, workflow.permits_common_action×2, workflow.specialist |
| `task.py` | 182 | Copy of the task iterator step with grain 'hpc' and HPC launch report contract validation. | import:episode_source_failure, import:library.action_contracts, import:library.hpc_handoff_report_contract, import:library.private_policy_call, import:providers, import:root.a103, import:runtime, runtime.ActionFailure, runtime_actions×8, runtime.ContractInformationError, runtime._decode_recorded_action_response, runtime.Draft202012Validator×2, runtime_episodes, runtime.EventTargetError×2, runtime.inspect, runtime._json×5, runtime.json×8, runtime_model_calls×2, runtime.nullcontext×5, runtime.observes_action_outcome, runtime.ReportBoundaryError, runtime.ReportRedelivery×2, runtime.schema_failure_diagnostic, runtime.SourceEnd×2, runtime.validate_form, runtime.ValidationError×2, runtime._wait_target_feedback×2, runtime.WorkflowError×2, workflow.action_schema, workflow.completed_unit×3, workflow.completions×3, workflow.controller_value×2, workflow.decision_exchanges×3, workflow.delivery_resolution_inputs, workflow.execute, workflow.execution_binding×7, workflow.inprocess_replay×4, workflow.journal×7, workflow.last_observed_credit, workflow.next_return, workflow.pending_work, workflow.perform_selected_wait, workflow.receive_native_outcome, workflow.receive_outcome, workflow.resolve_pending_deliveries, workflow.resolver, workflow.run_id×2, workflow.selected×3, workflow.source_credit_view, workflow.store×7, workflow.validate_report |
| `task_state.py` | 108 | Copy of the old per-source task state (episode identity, report_values from parent initial_report, feedback, restore/checkpoint/record_effect against old completions). Own intent: report_values start from the parent's initial_report; interpretation schema from the parent report contract; failed selected tool/reason actions still enter the iterator with a failed outcome and credit. | import:episode_source_failure, import:root.a103, import:runtime, runtime.ActionLeaf, runtime_actions×5, runtime.EFFECT_VERSION, runtime.Episode, runtime.interpretation_schema, runtime._json×2, runtime.json×4, runtime._object, runtime._plain, runtime.Record, workflow.archive, workflow.completions×4, workflow.context, workflow.controller_value, workflow.execution_binding×4, workflow.grains, workflow.inprocess_replay×7, workflow.journal×5, workflow.progress_provider×2, workflow.recover_commissions, workflow.run_id, workflow.source_credit_view, workflow.store×2 |
| `task_waiting.py` | 9 | Suspension hook. | workflow.execution_backend, workflow.execution_handle×2 |
| `to_child_execution_job_submission.py` | 67 | Launch child: only the exact planned launch may consume the allocation slot (reservation); initial decision context for launch/launch_hpc children with the frozen manifest, acceptance, supplied input file and instructions. | import:communication, import:hpc_ledger, import:method_loop.identities, import:practical_execution_state, import:root.a103 |
| `to_child_execution_progress_assessment.py` | 12 | Monitor child request: validate against the monitor's monitor_assignment_v1; the parent requests information, never polls here. | import:communication, import:domain |
| `to_child_hpc_allocation_execution.py` | 29 | Allocation child assignment: commission identity + owner_episode_id must equal this hpc parent. | import:communication, import:domain, import:execution_contracts |
| `to_child_hpc_resource_prediction.py` | 29 | Prediction child assignment: same rule as the allocation child. | import:communication, import:domain, import:execution_contracts |
| `to_parent.py` | 41 | Facts hpc_credit, hpc_model_ref, hpc_accepted_obligations, hpc_result_refs; hpc_model resolution; fact fields must equal recorded facts. | import:communication, import:episode_bindings |
| `waiting.py` | 50 | activity_advice from the latest iterator estimate (wait/collect suggestion); hpc.monitor.wait via the cron controller (collect now when terminal or outputs ready; otherwise reserve, wait, observe once). | import:hpc_monitoring, runtime_observations |
| `work_operations.py` | 54 | Tool catalog hpc.read, hpc.compare, hpc.history.refresh (with memory), hpc.discovery.run, hpc.candidate.propose, hpc.queue.observe, hpc.plan, hpc.handoff, hpc.monitor, hpc.monitor.wait, hpc.results, hpc.allocation.order; dispatch with ledger action intent/cache. | import:communication, import:domain, import:execution_contracts |
| `yield_estimator.py` | 101 | Completion-with-target continuation: commission yield_bindings[role] (cutoff, parameters) with HPCContinuationEstimator; continuation_for_action builds the pending-value evidence (collect/wait, pending by obligation, active ceiling, active history indices). | import:hpc_monitoring, import:library, import:library.hpc_continuation, import:numerical, runtime_actions×2, runtime_observations |

Usage counts per name and file: `runs/carry_over/calls/a103_02.tsv`.
