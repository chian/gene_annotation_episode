# a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/`
(43 Python files directly in the folder; no `grading/` or `scoring/` subfolder; `tests/` and the child folders
`execution_job_submission`, `execution_progress_assessment`, `execution_result_acquisition` not read here — the
first has its own page). Nothing from the old shared root was read. Where behaviour lives in old shared modules
(`hpc_ledger`, `hpc_campaign`, `hpc_queue`, `hpc_monitoring`, `hpc_history`, `execution_memory`,
`library.hpc_prediction`, `library.hpc_continuation`), this page says only what this episode's own files ask of them.

Old binding: class `HPCEpisode`, `binding_path = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution'`,
`commissioning_parent = 'partner_presence_evidence/hpc_work_planning'`, role `hpc_execution`, no entry roles,
version `hpc_episode_v1`, `replaces_default_instructions = True`. Decision source `HPCWorkTask`; prompt renderer
`render_hpc_prompt`. `episode.py` also holds `create_execution_bindings`, which constructs the job submission, API /
local / HPC job execution and result acquisition bindings of its subtree with the caller's operands.

## What this episode is for

It is the execution sister of the HPC work: given an HPC commission, it discovers the resource, proposes and compares
work portfolios, freezes a plan with its forecast, commissions the launch of that exact plan, attaches the returned
PBS handoff, monitors the original allocation, reorders pending units, and parses and accepts unit results — balancing
expected credit against elapsed time and resource demand. Its goal text (`goal.py`) is written for the HPC parent
and its two sisters together:

> Iterate toward the original accomplishment while balancing expected credit against real elapsed time and resource demand. The hpc parent can commission hpc_prediction and hpc_execution as sisters: prediction fits/measures/compares; execution prepares, launches, monitors and parses the selected work. Both assignments copy hpc_child_commission exactly and carry the hpc parent owner_episode_id. Both sisters inherit exactly hpc_child_scope, including an empty subject_refs list for an operational task with no biological inputs. Candidate IDs, model IDs, queue observations and resource IDs are not biological subject_refs. Use hpc_report_form as the return contract. Use the shared current model and comparisons; resource observations and candidate requests are different quantities. If suitable history is available, a prediction iteration can improve sizing before launching. No historical validation support means no invented model-improvement credit. Queue/setup costs belong to an allocation, which should carry enough useful work. When candidates are absent, discover the remote environment and documentation with hpc.discovery.run, then design candidate portfolios with hpc.candidate.propose. Discover is for lightweight inspection; leave installation and file staging to Launch, and scientific computation to the actual allocation. You choose the real inputs, database, executable commands, resources, worker code and preparation instructions. Never fabricate inputs or receipts. Every work unit writes result.json and progress.json under os.environ["HPC_UNIT_DIRECTORY"], its original per-unit working directory. The allocation workspace is for staged inputs, not these unit outputs; its fields must satisfy the caller acceptance predicates. The environment contains HPC_UNIT_DIRECTORY. Candidate files use relative paths; {allocation_workspace} expands in files, argv, environment and preparation. Compute commands must run on allocated compute nodes using the facility launcher. Compare portfolios using current queue features and measured history. A plan freezes its original forecast, scientific manifest and acceptance criteria. Commission launch -> launch_hpc with that actual job and resource. The execution agent chooses its scripts, environment and operational commands from the supplied resource instructions and observations. Supplied reference sources are available in the local input file; do not transcribe them into a child goal or prescribe a setup/submit sequence. Use hpc_launch_report_form as the Launch return contract. If a completed Launch return omitted its receipt, use redeliver_report with the existing delivery_ref and hpc_launch_report_form; report repair must not commission another Launch. Attach that received handoff. Use hpc.monitor once when another observation can affect your decision; it revises conditional predictions and attainable credit. Use hpc.results directly for known parsing. Commission monitor/results children only for actual investigation. Completed unit outputs can await parsing while PBS is still running or cleaning up. When pending_action is collect, use hpc.results for those original outputs; completion is not acceptance. When hpc_monitor_controllers is present, select hpc.monitor.wait for a scheduled observation: its attached controller evaluates the conditional forecast, persists a wake time, and executes the original monitor at that time. This preserves pending accomplishment value across waits without credit for sleeping. The timer cannot turn into another unobserved wait. Do not poll for credit or duplicate a submitted attempt. Never replace an uncertain submission. Accepted accomplishment, model improvement, and fixed prospective forecast validation are the only parent credit components; launch-local credits are not added again.

## Task and instructions

- One unit is one model-selected action: `tool`, `child` (`launch`, `monitor`, `results`), `redeliver_report`, and
  `wait` unless the commission has `monitoring` (then waiting goes through `hpc.monitor.wait`). No `reason`.
- Instructions (`task_instructions.py`): the binding goal; tool knowledge and launch-library instructions when present;
  repair guidance; wait and native-event guidance when `wait` is permitted. It does not add the monitor's action
  boundary, credit-component, resource-estimate, report or history blocks.

## What it reads from its parent's assignment

`from_parent.py`: `owner_episode_id` (required) plus exactly one of `commission_id` (one of the configured
commissions) or `commission_source_ref` (a Store source read by `hpc_commission_sources.read`). The parent must be
the original `hpc` episode: `owner_episode_id` equals the parent's episode id and the commission identity equals the
parent's. With `require_commission_yield`, the commission must carry `yield_bindings`. The ledger
(`portfolio_state.py`) is the owner's `hpc/<digest(run_id, owner)>` ledger; its recorded owner scope and commission
must equal this episode's (`sister_scope_must_equal_original_parent_scope`).

## Children

- `launch` (its own child `execution_job_submission`). Sends: the plan's `launch_assignment` returned by `hpc.plan`;
  `authenticate_launch` (`to_child_execution_job_submission.py`, called from the child's assignment preparation)
  admits only an assignment equal to exactly one frozen plan's `launch_assignment`, in the owner's scope, reserves
  `launch:<plan_id>` once, and refuses a closed allocation. `initial_decision_context` gives a `launch` or
  `launch_hpc` descendant `hpc_execution_job`: plan id, objective, scientific manifest, scientific acceptance, the
  frozen plan written to `launch-inputs/<plan_id>.json`, the coordinator workspace, and instructions (choose your own
  scripts, environment and transfer; keep unit identities, inputs, output/progress formats and acceptance; run in the
  actual allocation; investigate rather than duplicate an uncertain submission). Takes back: the
  `hpc_launch_report_form` (`execution_handoff_refs`); `original_launch_handoff`
  (`from_child_execution_job_submission.py`) recovers the plan's handoff from committed outcomes under the owning
  path when the return omitted it.
- `monitor` (its own child `execution_progress_assessment`). Sends: an assignment validated against the monitor's
  `_ASSIGNMENT` schema, unchanged. Takes back: the typed form's `episode_progress` references into this parent's
  received progress (`receive_child_progress_for_role`).
- `results` (its own child `execution_result_acquisition`). Sends: the assignment unchanged through the old request
  assembler (`to_child_execution_result_acquisition.py`). Takes back: references through the old report intake
  (`from_child_execution_result_acquisition.py`). The goal says to use `hpc.results` directly for known parsing and
  commission monitor/results children only for actual investigation.

## Decision state and what the model sees

Generic old decision state (no annotation-axis branch) plus `decision_context` (`internal_summary.py`):
`hpc_commission`, `hpc_candidates`, `hpc_resource`, `hpc_child_scope`, `hpc_child_commission`,
`hpc_launch_deliveries` (delivery refs and delivered forms of launch children), `hpc_launch_report_form`,
`hpc_tool_request`, `hpc_model_ref`, `hpc_credit`, `hpc_latest_comparison`, `hpc_model_support`, `hpc_report_form`
(`hpc_credit`, `hpc_model_ref`, `hpc_result_refs`), `hpc_plans`, `hpc_latest_monitor`, `hpc_monitor_controllers`,
`hpc_activity_decision` (from the last observation's `activity_mode` wait/collect: suggested tool, active next gain,
pending expected credit and upper bound), `hpc_queue_refs`, shared memory and shared history refs when bound, and
`hpc_available_training_ids`.

## Tools

`work_operations.py` (every action is cached by operation key in the ledger and saved through `ledger.save_action`):
- `hpc.read` — read retained evidence (history row, ledger record, or a received owned `episode.hpc_result` source);
- `hpc.compare` — compare all approved portfolios by net expected value for a `model_ref` and `queue_ref`;
- `hpc.history.refresh` (only with shared memory) — read age-weighted shared timing history once;
- `hpc.discovery.run` — one lightweight SSH command run in `/lus/flare/projects/BioReason-Aurora-Test`, cached when
  fresh;
- `hpc.candidate.propose` — retain an executable portfolio (`candidate_json`; immutable identity);
- `hpc.queue.observe` — acquire PBS queue and ALCF status once;
- `hpc.plan` — freeze one portfolio and forecasts (fresh enabled execution queue, within its limits);
- `hpc.handoff` — bind the received PBS handoff to the frozen plan; attach a monitor cron controller when the
  commission has monitoring;
- `hpc.monitor` — observe the original job and unit progress once; update and freeze conditional forecasts;
- `hpc.monitor.wait` — reserve a forecast-valued schedule, wait, observe exactly once; collect-now when the job is
  terminal or unit outputs are ready;
- `hpc.results` — parse unit results by recorded sha256 and accept by the obligation predicate;
- `hpc.allocation.order` — reorder original pending units at the next unit boundary.

## Credit

Credit kind `operational`; credit view is the HPC ledger's own `credit_view()` (contributions per slot). Per the goal
and fact meanings: accepted accomplishment, model improvement and fixed prospective forecast validation are the only
components; "repeated polling adds none"; launch-local credits are not added again. Measurements are scored as they
are recorded (`ledger.score`), forecasts are frozen with validation slots.

## Continuation

Only with `require_commission_yield` (`yield_estimator.py`), else raises `hpc_episode_yield_binding_required`. The
commission's `yield_bindings['hpc_execution']` supplies `cutoff` and `parameters`; the estimator is
`HPCContinuationEstimator` with continuation cost = cutoff, verifying evidence packets written by
`continuation_for_action`: expected continuation credit 0 when all obligations are accepted; otherwise, per open
monitored plan, an unresolved-acceptance upper bound when outputs await collection (pending action `collect`) or the
forecast schedule valuation scaled to attainable obligations; deduplicated per obligation; an active ceiling of 0 when
every remaining obligation is pending, there are no untrained history cases and all candidates are single-unit; plus
the indices of active (non-wait, non-passive) actions. Nearest current estimator: **completion with a target**
(obligation acceptance), but the pending-allocation valuation and active/passive split have no direct counterpart.

## Report to parent

Facts (`to_parent.py`): `hpc_credit` (signed measured credit), `hpc_model_ref` (namespace `hpc_model`),
`hpc_accepted_obligations`, `hpc_result_refs` (received owned result sources). Form fields with `x-source` must equal
the facts. `frozen_reference` (`closed_models.py`) validates a closed `hpc_model` id read-only from the owner ledger.

## Differences from similar episodes and things to note

- Unlike the monitor it drops the annotation-axis branches and the long guidance set, and `task_state` records
  execution failures only for `tool` actions.
- Its credit and continuation are obligation/forecast based through the shared HPC ledger, unlike the operational
  handoff/byte credit of launch and results.
- Cross-episode coupling: the child `execution_job_submission` imports `authenticate_launch` from this episode's
  `to_child_execution_job_submission.py`; this episode imports `_ASSIGNMENT` from its child
  `execution_progress_assessment/contracts.py`; `create_execution_bindings` imports five descendant episode classes.
- Limits that conflict with the no-limits rule: `resource_discovery.py` runs SSH with `timeout=90` and truncates
  stdout to 65536 and stderr to 8192 bytes; `measured_history.py` caps shared history observations at `[:2000]`.
  The commission's `limits` (`queue_max_age_seconds`, `result_limit_bytes`) are caller data.
- `yield_estimator.py` scales a valuation with `min(1.0, ...)` (a forecast share, not credit).

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | Empty package marker. | none |
| `allocation_handoff.py` | 35 | `hpc.handoff`: binds a received PBS handoff to its frozen plan (assignment must equal the plan's practical assignment), optionally attaches a monitor cron controller; routes allocation work (`hpc.monitor.wait`, `hpc.allocation.order`, observe) and refuses before a handoff is attached, with recovery text. | `BindingContext`: scope; `imports root.a107`: episode_bindings, hpc_monitoring |
| `allocation_observations.py` | 83 | Reads the original allocation receipt (`allocation-status.json`) and unit progress, builds telemetry, phase change and recent progress rate, records a measurement and routes to monitor or results. | `BindingContext`: scope; `imports root.a107`: episode_bindings, execution_progress, hpc_campaign×3 |
| `allocation_order.py` | 16 | `hpc.allocation.order`: reorder only original pending units at the next unit boundary. | none |
| `allocation_results.py` | 74 | `hpc.results`: for completed/failed units, read `result.json` from the unit directory, check its recorded sha256, publish an `episode.hpc_result` source, accept against the commission's obligation predicate; close and export the allocation when the job ends. | `BindingContext`: episode_id×2, scope; `imports root.a107`: communication, hpc_campaign, hpc_queue |
| `binding_record.py` | 8 | Binding identity record `hpc_episode_v1`: resources, commissions, shared execution memory, commission-yield flag. | none |
| `closed_models.py` | 27 | Validates a closed `hpc_model` reference read-only from the owner's ledger. | `BindingContext`: assignment, episode_id, role, run_id×2, scope; `imports root.a107`: communication, episode_return_records, hpc_queue; `names`: EpisodeReturnRecords×2; `tables`: runtime_forms |
| `configuration.py` | 32 | Constructor operands: resources (must include pbs_ssh), commissions validated by `validate_commission`, optional shared execution memory, `require_commission_yield` (then every commission needs `yield_bindings`). | `imports root.a107`: communication, execution_memory, hpc_campaign |
| `credit.py` | 16 | Credit kind `operational`; credit view is the HPC ledger's own `credit_view()`. | none |
| `decision_inputs.py` | 53 | Generic old decision inputs, with HPC additions: requested action history for HPC contexts; role `hpc_execution` for execution expectations; no annotation-axis branch. | `imports root.a107`: episode_work_report×2, library.hpc_prompt, runtime×2; `runtime`: child_option_information; `self.workflow`: available_child_roles, binding_context, episode_bindings, execution_expectations, launch_instructions×2, native_estimation_context, pending_work, permits_common_action, resource_context, resource_estimator×4, waiting_support |
| `decision_state.py` | 31 | Generic old decision state without the annotation-axis branch. | `imports root.a107`: runtime×2; `journal`: elapsed_view; `runtime`: FACT_MEANINGS, FACT_SOURCES, json, Mapping×2, _plain×2, _references_in; `self.workflow`: binding_context, catalog, controller_binding, delivery_status, extra_report_sources, job_episode_options, journal×2, knowledge, local_outcome_preview, pending_work, receipt_projection, run_id, source_credit_binding, source_credit_view, specialist, store×3, tools, working_state; `tables`: runtime_actions; `view`: child_reports×2, controller_state, model_inputs |
| `episode.py` | 91 | Composes the binding: path, parent `partner_presence_evidence/hpc_work_planning`, role `hpc_execution`, no entry roles, `replaces_default_instructions`, decision source `HPCWorkTask`, renderer `render_hpc_prompt`; children `launch`, `monitor`, `results`; common actions tool, child, redeliver_report, plus wait unless the commission has monitoring. Also `create_execution_bindings`, constructing the execution subtree bindings with the caller's operands. | `BindingContext`: assignment, role, scope; `imports root.a107`: library.hpc_prompt |
| `forecast_observations.py` | 80 | Freezes forecasts with validation slots, finds the last forecast, measures queue/work/setup metrics, and `hpc.monitor` updates the conditional prediction (optional queue refresh) and remaining work comparison. | `imports root.a107`: hpc_campaign, hpc_queue, library, library.hpc_resource_prediction×2 |
| `from_child_execution_job_submission.py` | 46 | Recovers the original launch handoff for a frozen plan from committed outcomes under the owning HPC path (report repair). | `BindingContext`: assignment, path×2, role, run_id×3, scope×2; `imports root.a107`: communication, hpc_ledger, hpc_queue, method_loop.identities; `names`: EpisodeRef×2; `tables`: runtime_actions, runtime_episodes |
| `from_child_execution_progress_assessment.py` | 23 | Admits a monitor child's typed form into this parent's received progress. | `BindingContext`: episode_id×3, scope×2; `imports root.a107`: communication, domain, method_loop.durable; `names`: content_digest×2; `provider`: read_progress, _receive_progress |
| `from_child_execution_result_acquisition.py` | 44 | Generic old child-report intake for the results child (recorded admission, progress forms, receipts, timing receipts, tool attributions). | `imports root.a107`: delivery_counterpart, episode_return_records, runtime; `names`: EpisodeReturnRecords×2; `runtime`: _json, json, _references_in, WorkflowError; `self.workflow`: binding_context×4, episode_bindings, is_job_source×2, job_episodes×2, native_timing_information, progress_provider×4, receipts×3, receive_tool_attributions, run_id×6, specialist, store×7; `tables`: runtime_report_attempts×2 |
| `from_parent.py` | 43 | Assignment schema: `owner_episode_id` plus `commission_id` or `commission_source_ref`; the parent must be the original `hpc` parent with the same commission identity; commission yield binding required when configured. | `BindingContext`: assignment, episode_id, role; `imports root.a107`: communication, domain, execution_contracts, hpc_commission_sources |
| `goal.py` | 10 | The episode's goal text (see "What this episode is for"). | none |
| `initial_information.py` | 9 | Resource and received API information from this binding path's readers. | `catalog`: readers; `imports root.a107`: library.execution_initial_information.presentation |
| `internal_summary.py` | 56 | Decision context: commission, candidates, resource, child scope and commission, launch deliveries, launch and HPC report forms, tool requests, model ref/support, credit, latest comparison, plans, latest monitor, monitor controllers, activity advice, queue refs, shared memory, training ids. | `BindingContext`: assignment, episode_id, run_id, scope; `imports root.a107`: communication, library; `tables`: runtime_episodes, runtime_report_attempts |
| `measured_history.py` | 82 | History = commission history + latest shared history snapshot + one latest measurement per closed allocation; shared history filtered by profile and queue; export of closed measurements to shared memory; `hpc.history.refresh`. | `imports root.a107`: execution_guidance, hpc_history, library.hpc_resource_prediction |
| `portfolio_candidates.py` | 23 | `hpc.candidate.propose`: immutable candidate identities, validated within the commission. | `imports root.a107`: hpc_campaign |
| `portfolio_comparison.py` | 44 | `hpc.compare`: predict and compare all candidates by net expected value. | `BindingContext`: episode_id; `imports root.a107`: hpc_queue, library |
| `portfolio_planning.py` | 38 | `hpc.plan`: requires a fresh queue observation of an enabled execution queue and candidate within queue limits; freezes plan, prediction and reference forecast. | `imports root.a107`: hpc_campaign, hpc_queue, library |
| `portfolio_state.py` | 38 | The per-owner HPC ledger (opened, scope and commission must equal the owner's), prior reference model and initial shared-history model. | `BindingContext`: assignment×4, role, scope×2; `imports root.a107`: communication, domain, hpc_ledger, hpc_queue, library |
| `queue_observations.py` | 35 | PBS queue observation with shared memory cache by `queue_max_age_seconds`; `hpc.queue.observe`. | `imports root.a107`: execution_guidance, hpc_queue |
| `received_api_reports.py` | 4 | Selects this binding path's declared API reader authority. | `catalog`: configured, received |
| `received_evidence.py` | 60 | Known records; resolves received `episode.hpc_result` sources in scope; `hpc.read` of ledger, history or owned result sources. | `BindingContext`: received_record_refs, scope; `imports root.a107`: communication; `services`: record_selection |
| `received_execution_information.py` | 4 | Selects this binding path's declared result readers. | `catalog`: configured, received |
| `report_delivery.py` | 23 | Generic old finish (identical to the monitor copy apart from names). | `imports root.a107`: runtime×2; `journal`: row, save; `runtime`: form_with_facts, _json×2, json, Record×2; `self.workflow`: binding_context, episode_bindings, facts, journal×2, pending_handles, release×2, source_credit_view; `tables`: runtime_forms×2 |
| `resource_discovery.py` | 30 | `hpc.discovery.run`: one SSH command in the project directory, cached in shared memory when fresh. | `imports root.a107`: execution_guidance, hpc_queue |
| `task.py` | 183 | Generic old task loop; grain `hpc_execution`; binds `validate_hpc_launch_report_contract`. | `imports root.a107`: episode_source_failure, library.hpc_handoff_report_contract, providers, runtime×2; `journal`: measure, row×7, save×3; `names`: ModelCallError×2; `runtime`: ActionFailure, ContractInformationError, _decode_recorded_action_response, Draft202012Validator×2, EventTargetError×2, inspect, _json×5, json×8, nullcontext×5, observes_action_outcome, ReportBoundaryError, ReportRedelivery×2, schema_failure_diagnostic, SourceEnd×2, validate_form, ValidationError×2, _wait_target_feedback×2, WorkflowError×2; `self.workflow`: action_schema, completed_unit×3, completions×3, controller_value×2, decision_exchanges×3, delivery_resolution_inputs, execute, execution_binding×7, inprocess_replay×4, journal×7, last_observed_credit, next_return, pending_work, perform_selected_wait, receive_native_outcome, receive_outcome, resolve_pending_deliveries, resolver, run_id×2, selected×3, source_credit_view, store×7, validate_report; `tables`: runtime_actions×8, runtime_episodes, runtime_model_calls×2; `view`: units_consumed×4 |
| `task_decision.py` | 289 | Generic old model-call machinery without the annotation-axis yield-table branch. | `exchanges`: measure, prepare, resolve_lookup, respond, rows; `imports root.a107`: runtime×2; `journal`: measure×2, row×2, save×4; `provider`: complete; `runtime`: _action_generation_schema×2, apply_state_frame, _ASSIGNMENT_TRANSPORT, _category_yield_parameters, child_option_information, composition_lookup_schema×2, CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION×2, DECISION_EXCHANGE_PROTOCOL×5, _digest, Draft202012Validator, infernal_receiver_context×2, instructional_model_context×4, is_contract_information, _json×14, json×3, lookup_attempts, Mapping×2, model_snapshot×2, _object×3, _plain×2, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, requested_contract_information×2, schema_failure_diagnostic×2, sqlite3, state_frame, ValidationError×5, WorkflowError×14, yield_table; `self.workflow`: contract_information_profile, contract_information_reply, controller_binding, decision_exchanges×4, decision_protocol×3, execute, freeze_contract_information, history_preview, journal×3, numerical_contracts, provider×3, receipts×4, run_id, services, specialist, store×2, uses_received_record_context×2, validate_contract_information×5; `tables`: runtime_model_calls×8 |
| `task_instructions.py` | 14 | Instruction composition: binding goal, knowledge, launch library, repair, wait and native-event text (no action-boundary, credit-component, report or history text, unlike the monitor). | `self.workflow`: binding_context, knowledge, launch_instructions, native_event_information, permits_common_action×2, specialist |
| `task_state.py` | 108 | Generic old state; failure recording only for `tool` actions. | `imports root.a107`: episode_source_failure, runtime×2; `journal`: row×3, save×2; `runtime`: ActionLeaf, EFFECT_VERSION, Episode, interpretation_schema, _json×2, json×4, _object, _plain, Record; `self.workflow`: archive, completions×4, context, controller_value, execution_binding×4, grains, inprocess_replay×7, journal×5, progress_provider×2, recover_commissions, run_id, source_credit_view, store×2; `tables`: runtime_actions×5 |
| `task_waiting.py` | 9 | Generic old suspension hook. | `self.workflow`: execution_backend, execution_handle×2 |
| `to_child_execution_job_submission.py` | 70 | `authenticate_launch`: only the exact planned launch assignment may reserve the allocation slot once; `initial_decision_context` gives a launch child the frozen job (objective, manifest, acceptance, input file, workspace, instructions). | `BindingContext`: assignment×2, episode_id, path×4, role×4, run_id×3, scope×2; `imports root.a107`: communication, hpc_ledger, hpc_queue, method_loop.identities, practical_execution_state; `names`: EpisodeRef×2 |
| `to_child_execution_progress_assessment.py` | 12 | Monitor child request: validated against the monitor assignment schema, passed through unchanged. | `imports root.a107`: communication, domain |
| `to_child_execution_result_acquisition.py` | 29 | Generic old child request assembler (goal, message, receipts inheritance). | `imports root.a107`: runtime×2; `runtime`: ContractInformationError, Episode×2, EpisodeGoal×2, EpisodeRequest, _plain×3, Record, validate_saved_fact_form; `self.workflow`: context×2, grains×2, inprocess_completion_order×2, launch_instructions, receipts×2 |
| `to_parent.py` | 41 | Facts `hpc_credit`, `hpc_model_ref`, `hpc_accepted_obligations`, `hpc_result_refs`; `hpc_model` reference resolution; report must equal facts. | `imports root.a107`: communication, episode_bindings |
| `waiting.py` | 50 | Activity advice from the last observation diagnostics; `hpc.monitor.wait` (initial monitor, collect-now cases, reserve schedule, wait, observe once). | `BindingContext`: episode_id, run_id; `imports root.a107`: hpc_monitoring; `tables`: runtime_observations |
| `work_operations.py` | 54 | Tool catalog and dispatch (see "Tools"). | `BindingContext`: episode_id; `imports root.a107`: communication, domain, execution_contracts |
| `yield_estimator.py` | 101 | Private continuation (see "Continuation") and `continuation_for_action` pending-value evidence. | `BindingContext`: assignment, episode_id×3, role×5, run_id×3, scope; `imports root.a107`: hpc_monitoring, library, library.hpc_continuation, numerical; `names`: HPCContinuationEstimator×2, YieldController×2, YieldParameters×2; `tables`: runtime_actions×2, runtime_observations |
