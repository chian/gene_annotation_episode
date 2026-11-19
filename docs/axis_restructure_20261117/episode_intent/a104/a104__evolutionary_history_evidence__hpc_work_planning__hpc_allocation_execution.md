# a104 / evolutionary_history_evidence / hpc_work_planning / hpc_allocation_execution

Source: the episode's own files at commit `97308b94c`
(`git show HEAD:gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution/<file>`).
The `tests/` folder is not covered here, and the folder has no `grading/` or `scoring/` subfolder. The child folders (`execution_job_submission`,
`execution_progress_assessment`, `execution_result_acquisition`) are documented separately. Old binding class: `HPCEpisode`. Decision source:
`HPCWorkTask`, with `child_return_form_policy = HPC_HANDOFF_RETURN_POLICY`. Prompt renderer: `present_task_context`, which selects
`render_hpc_prompt` for HPC contexts. Commissioning parent: `evolutionary_history_evidence/hpc_work_planning` (role `hpc`).

## Purpose (goal, in its own words)

Role `hpc_execution`. It is not an entry role, and it replaces the default instructions. From `goal.py` (verbatim, long):

> Iterate toward the original accomplishment while balancing expected credit against real elapsed time and resource
> demand. The hpc parent can commission hpc_prediction and hpc_execution as sisters: prediction fits/measures/compares;
> execution prepares, launches, monitors and parses the selected work. Both assignments copy hpc_child_commission
> exactly and carry the hpc parent owner_episode_id. Both sisters inherit exactly hpc_child_scope, including an empty
> subject_refs list for an operational task with no biological inputs. Candidate IDs, model IDs, queue observations and
> resource IDs are not biological subject_refs. Use hpc_report_form as the return contract. Use the shared current model
> and comparisons; resource observations and candidate requests are different quantities. If suitable history is
> available, a prediction iteration can improve sizing before launching. No historical validation support means no
> invented model-improvement credit. Queue/setup costs belong to an allocation, which should carry enough useful work.
> When candidates are absent, discover the remote environment and documentation with hpc.discovery.run, then design
> candidate portfolios with hpc.candidate.propose. Discover is for lightweight inspection; leave installation and file
> staging to Launch, and scientific computation to the actual allocation. You choose the real inputs, database,
> executable commands, resources, worker code and preparation instructions. Never fabricate inputs or receipts. Every
> work unit writes result.json and progress.json under os.environ["HPC_UNIT_DIRECTORY"], its original per-unit working
> directory. The allocation workspace is for staged inputs, not these unit outputs; its fields must satisfy the caller
> acceptance predicates. The environment contains HPC_UNIT_DIRECTORY. Candidate files use relative paths;
> {allocation_workspace} expands in files, argv, environment and preparation. Compute commands must run on allocated
> compute nodes using the facility launcher. Compare portfolios using current queue features and measured history. A
> plan freezes its original forecast, scientific manifest and acceptance criteria. Commission launch -> launch_hpc with
> that actual job and resource. The execution agent chooses its scripts, environment and operational commands from the
> supplied resource instructions and observations. Supplied reference sources are available in the local input file; do
> not transcribe them into a child goal or prescribe a setup/submit sequence. Use hpc_launch_report_form as the Launch
> return contract. If a completed Launch return omitted its receipt, use redeliver_report with the existing delivery_ref
> and hpc_launch_report_form; report repair must not commission another Launch. Attach that received handoff. Use
> hpc.monitor once when another observation can affect your decision; it revises conditional predictions and attainable
> credit. Use hpc.results directly for known parsing. Commission monitor/results children only for actual
> investigation. Completed unit outputs can await parsing while PBS is still running or cleaning up. When pending_action
> is collect, use hpc.results for those original outputs; completion is not acceptance. When hpc_monitor_controllers is
> present, select hpc.monitor.wait for a scheduled observation: its attached controller evaluates the conditional
> forecast, persists a wake time, and executes the original monitor at that time. This preserves pending accomplishment
> value across waits without credit for sleeping. The timer cannot turn into another unobserved wait. Do not poll for
> credit or duplicate a submitted attempt. Never replace an uncertain submission. Accepted accomplishment, model
> improvement, and fixed prospective forecast validation are the only parent credit components; launch-local credits are
> not added again.

## Task and instructions

`task_instructions.instructions` composes the instructions. It contains:
- the goal;
- the tool knowledge, when present;
- the launch-instruction library, when present;
- the pending-child-delivery repair text;
- the in-process wait text, when wait is permitted;
- the native-event text, when native event information exists and wait is permitted.

It has none of the A-root instructions, none of the monitor's ACTION_BOUNDARY/CREDIT/RESOURCE/REPORT/HISTORY constants, and no
reasoning-commit requirement. The task loop is the monitor family's: `tool` and `wait` execution only.

## What it reads from its parent's assignment

`from_parent.assignment_schema` reads:
- `owner_episode_id` (required);
- either `commission_id`, an enum of the configured commissions (exactly one of the two, `oneOf`), or `commission_source_ref`, read through
  `hpc_commission_sources.read`.

`prepare_assignment` requires:
- the parent role is `hpc`;
- `owner_episode_id` equals the parent's episode id;
- the commission identity equals the parent assignment's;
- when private yield is on, the commission carries `yield_bindings`.

`portfolio_state.state` opens the existing HPC ledger at `directory/hpc/digest(run_id, owner)`. It requires the ledger owner's scope and
commission identity to equal this context's: "sister_scope_must_equal_original_parent_scope".

## Children

The children are `launch`, `monitor` and `results` (`allowed_children` returns all three).

- **`launch`**, the `execution_job_submission` episode.
  - Sent: the launch assignment from a frozen `hpc.plan` (`plan.launch_assignment`). At the child's `prepare_assignment`, `authenticate_launch`
    requires that it equals exactly one plan's launch assignment and that the scope matches. It records a `launch_commission` reservation per
    plan, and a closed plan refuses another launch.
  - For `launch`/`launch_hpc` children, `LaunchPreparation.initial_decision_context` supplies `hpc_execution_job` with these fields: plan_id,
    objective, scientific_manifest, scientific_acceptance (obligations), supplied_input_file (the frozen plan written immutably),
    coordinator_workspace, and instructions on using the terminal freely, not transcribing sources, preserving unit identities, and
    investigating rather than duplicating uncertain submissions.
  - Taken back: the typed form under `hpc_launch_report_form` (`execution_handoff_refs`). `original_launch_handoff` can recover a
    launch_hpc's actual handoff receipt from committed outcomes across report repair. The handoff is then attached with `hpc.handoff`.
- **`monitor`**, the `execution_progress_assessment` episode under this parent.
  - Sent: a `monitor_assignment_v1`, validated unchanged by `prepare_request` ("this parent requests information; it never polls here").
  - Taken back: `receive_progress` admits the form's `episode_progress` references into received progress.
- **`results`**, the `execution_result_acquisition` episode under this parent.
  - Sent: the selected results assignment (no preparation hook).
  - Taken back: the typed form through the common child-form receipt (`from_child_execution_result_acquisition.receive_report`, old machinery).
- `episode.create_execution_bindings` builds the five job-submission/result bindings (launch, api, local, hpc, results) with the same
  operands.

## Decision state and what the model sees

The common decision state applies, without the annotation-axis branch and without monitoring information credit. Decision inputs are as
for the monitor, plus `requested_action_history` for HPC contexts, and expectations use role `hpc_execution`.

The episode's own `internal_summary.decision_context` adds:
- `hpc_commission`, `hpc_owner_episode_id`, `hpc_candidates` and `hpc_resource`;
- `hpc_child_scope`, `hpc_child_commission`, `hpc_launch_deliveries` (delivery_ref and delivered form of launch children) and
  `hpc_launch_report_form`;
- `hpc_tool_request`, `hpc_model_ref`, `hpc_credit`, `hpc_latest_comparison` and `hpc_model_support`;
- `hpc_report_form`, `hpc_plans`, `hpc_latest_monitor` and `hpc_monitor_controllers`;
- `hpc_activity_decision`: the wait/collect advice from the last controller diagnostic;
- `hpc_queue_refs`, `hpc_shared_memory`/`hpc_shared_history_refs` and `hpc_available_training_ids`.

## Tools

The tools come from `work_operations.catalog`. Each action is cached per operation key in the ledger.
- **Planning tools:**
  - `hpc.read`: retained evidence or a received result source;
  - `hpc.compare`: all portfolios, by net expected value;
  - `hpc.history.refresh`: only when shared memory is configured;
  - `hpc.discovery.run`: one lightweight SSH command, run from `/lus/flare/projects/BioReason-Aurora-Test`;
  - `hpc.candidate.propose`: an immutable candidate (JSON);
  - `hpc.queue.observe`: PBS queue and ALCF score;
  - `hpc.plan`: freeze a portfolio and its forecasts, returning a concrete launch assignment;
  - `hpc.handoff`: bind the received PBS handoff to the frozen plan, and attach the monitor controller when the commission has `monitoring`.
- **Tools on the attached original allocation:**
  - `hpc.monitor`: observe once and update the conditional forecast;
  - `hpc.monitor.wait`: MonitorCronController timer, then one observation, with no credit for waiting;
  - `hpc.results`: parse the unit result.json files, check completion hashes, apply acceptance predicates, publish `episode.hpc_result`
    sources, and close the plan and export the measurement on a terminal job;
  - `hpc.allocation.order`: reorder original pending units only.

The common actions are tool, child and redeliver_report, plus `wait` unless the commission has `monitoring`.

## Credit

The credit kind is `operational`. `credit_view` is the HPC ledger's `credit_view()`. Its components are accepted accomplishment (obligation
credit when a result passes acceptance), model improvement, and fixed prospective forecast validation (slots frozen per forecast). It is
"signed measured credit; repeated polling adds none", and launch-local credits are not added again. Credit is not bounded here. (Note: in
`continuation_for_action`, the expected continuation value per obligation uses `scale = min(1.0, schedule_value / compared_total)`. That is
a scaling of a forecast, not of credit.)

## Continuation

`yield_estimator.yield_controller` applies only when `require_commission_yield`. It takes `commission['yield_bindings'][role]` = `{cutoff,
parameters}`, uses estimator `HPCContinuationEstimator(verify).with_continuation_cost(cutoff)` with an old `YieldController`, and reads the
continuation evidence from `continuation_for_action`:
- remaining obligations;
- pending allocations: collect upper bound for terminal or ready outputs, otherwise a `choose_schedule` valuation;
- deduplicated pending values;
- `active_credit_ceiling = 0` when all remaining obligations are pending, there are no new training cases, and every candidate is single-unit;
- `active_history_indices`, which excludes passive monitor/wait/results actions.

Current-runner closest: **completion with a target**, where the target is the commission's remaining obligation credit, with a continuation
cost. Settings per role: `cutoff` and YieldParameters `parameters`.

## Report to parent

`to_parent.facts`:
- `hpc_credit` (the ledger credit);
- `hpc_model_ref` (the selected prediction model, namespace `hpc_model`);
- `hpc_accepted_obligations`;
- `hpc_result_refs` (received `episode.hpc_result` sources).

`validate_report` requires every x-source field to equal its fact. A closed `hpc_model` reference is validated read-only against the owner's
hpc.sqlite (`closed_models.frozen_reference`).

## Differences from similar episodes

- Compared with the sibling monitor (`hpc_work_planning/execution_progress_assessment`): the same task, presentation and decision family, but
  with a much longer HPC-specific goal and a reduced instruction composition. There is no annotation-axis branch, no monitoring information
  credit, and no ACTION_BOUNDARY or other guidance constants.
- Unlike Results and Launch, its configuration is commission-based (an HPC ledger, not execution resources/units), and its yield is the HPC
  continuation estimator.
- `resource_discovery` runs `subprocess.run(..., timeout=90)`: an elapsed-time cutoff on the discovery command. Byte truncation applies to
  stdout (64 KiB) and stderr (8 KiB). `allocation_observations` limits allocation-status reads to 512 KiB and progress reads to 16 KiB.

## Files

Old-runner names are listed as `name×uses`. `workflow.*` means `self.workflow.*` / `source.workflow.*` / `workflow.*`. `BindingContext .x` means the old binding-context attribute `context.x` / `parent.x`. `table x` is a journal or receipt table named in SQL or in `journal.row/save`. The full per-use list is in `runs/carry_over/calls/a104_04.tsv`.

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | Empty package marker. | none |
| `action_admission.py` | 67 | Admit a model response (grain `hpc_execution`). Old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; ActionFailure×1; bind_functions×2; _bind_preserved_runtime_providers×2; ReportRedelivery×3; SourceEnd×1; WorkflowError×1; table runtime_actions×1; table runtime_model_calls×1; workflow.decision_exchanges×3; workflow.execution_binding×1; workflow.journal×2; workflow.resolver×1; workflow.selected×1; workflow.store×1; workflow.validate_report×1 |
| `action_execution.py` | 75 | Execute tool/wait selection. Old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; ActionFailure×2; bind_functions×2; _bind_preserved_runtime_providers×2; ReportRedelivery×1; SourceEnd×1; WorkflowError×2; table runtime_actions×5; workflow.completions×1; workflow.controller_value×2; workflow.execute×1; workflow.execution_binding×4; workflow.journal×1; workflow.last_observed_credit×1; workflow.pending_work×1; workflow.perform_selected_wait×1; workflow.receive_native_outcome×1; workflow.receive_outcome×1; workflow.run_id×1; workflow.source_credit_view×1; workflow.store×3 |
| `allocation_handoff.py` | 35 | `hpc.handoff`: bind a received PBS handoff to the exact frozen plan (must be received and match practical_assignment); attach the monitor controller when the commission has `monitoring`. Routes monitor.wait / allocation.order / monitor / results on the original allocation; without a handoff, returns recovery feedback (redeliver Launch report, do not relaunch). | BindingContext .scope×1; root.a104.episode_bindings×1; root.a104.hpc_monitoring×1 |
| `allocation_observations.py` | 83 | Read the original allocation: native status once, allocation-status.json, unit progress.json; telemetry, phase change, recent completion rate; measure; then monitor or collect. | BindingContext .scope×1; root.a104.episode_bindings×1; root.a104.execution_progress×1; root.a104.hpc_campaign×3 |
| `allocation_order.py` | 16 | `hpc.allocation.order`: reorder only original unit ids via the allocation control file. | none |
| `allocation_results.py` | 74 | `hpc.results`: read each finished unit's result.json from its original unit directory, check the completion hash, publish an `episode.hpc_result` source, accept the obligation when returncode 0 and the acceptance predicate holds; close the plan when the job is terminal and export the measurement. | BindingContext .episode_id×2; BindingContext .scope×1; import root.a104×1; root.a104.communication×1; root.a104.hpc_campaign×1 |
| `binding_record.py` | 10 | Binding record `hpc_episode_v1`: resources, commissions, shared execution memory, require_commission_yield. | none |
| `closed_models.py` | 27 | Validate a closed `hpc_model` reference read-only against the owner's hpc.sqlite. | BindingContext .assignment×1; BindingContext .episode_id×1; BindingContext .role×1; BindingContext .run_id×2; BindingContext .scope×1; import root.a104×1; root.a104.communication×1; root.a104.episode_return_records×1; EpisodeReturnRecords×2; table runtime_forms×1 |
| `configuration.py` | 32 | Construction operands: services, store, run_id, directory, resources (at least one pbs_ssh), commissions (validated), optional shared_execution_memory, require_commission_yield (every commission must then carry yield_bindings). | root.a104.communication×1; root.a104.execution_memory×1; root.a104.hpc_campaign×1 |
| `credit.py` | 16 | Credit kind `operational`; credit_view = the HPC ledger's credit view. | none |
| `decision_contracts.py` | 128 | Decision-exchange envelope and replay validation. Old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; WorkflowError×10; table runtime_model_calls×1; workflow.contract_information_reply×1; workflow.decision_exchanges×2; workflow.journal×1; workflow.store×2; workflow.validate_contract_information×2; _category_yield_parameters×1; yield_table×1 |
| `decision_exchange.py` | 110 | request_context lookup loop (no annotation-axis branch). Old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; WorkflowError×1; table runtime_model_calls×2; workflow.controller_binding×1; workflow.decision_exchanges×1; workflow.execute×1; workflow.journal×1; workflow.run_id×1; workflow.services×1; workflow.validate_contract_information×1; _category_yield_parameters×2; yield_table×2 |
| `decision_inputs.py` | 73 | Like the monitor's, plus requested_action_history for HPC contexts; execution_expectations role `hpc_execution`. | import root.a104×1; root.a104.episode_work_report×2; root.a104.library.hpc_prompt×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; workflow.available_child_roles×1; workflow.binding_context×2; workflow.episode_bindings×1; workflow.execution_expectations×1; workflow.job_episodes×2; workflow.launch_instructions×2; workflow.native_estimation_context×1; workflow.native_event_information×2; workflow.pending_work×1; workflow.permits_common_action×1; workflow.resource_context×1; workflow.resource_estimator×4; workflow.store×2; workflow.waiting_support×1 |
| `decision_provider.py` | 60 | Presentation-provider selection. Old-runner/provider machinery. | root.a104.providers×2; root.a104.runtime×1; import root.providers×1; WorkflowError×1; workflow.provider×1; workflow.specialist×2; _category_yield_parameters×1; yield_table×1 |
| `decision_state.py` | 40 | Decision state (no annotation-axis branch, no monitoring information credit). Old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; view.child_reports×2; view.controller_state×1; view.model_inputs×1; table runtime_actions×1; workflow.binding_context×1; workflow.catalog×1; workflow.controller_binding×1; workflow.delivery_status×1; workflow.extra_report_sources×1; workflow.job_episode_options×1; workflow.journal×2; workflow.knowledge×1; workflow.local_outcome_preview×1; workflow.pending_work×1; workflow.receipt_projection×1; workflow.run_id×1; workflow.source_credit_binding×1; workflow.source_credit_view×1; workflow.specialist×1; workflow.store×3; workflow.tools×1; workflow.working_state×1 |
| `episode.py` | 94 | HPCEpisode composition: role `hpc_execution`, not an entry role, children launch/monitor/results, common actions tool/child/redeliver_report (+wait unless the commission has monitoring), child request/report hooks; create_execution_bindings builds the five job-submission/result bindings. | BindingContext .assignment×1; BindingContext .role×1; BindingContext .scope×1; root.a104.evolutionary_history_evidence.* (absolute own-tree path)×5 |
| `forecast_observations.py` | 80 | Freeze forecasts with validation slots, last forecast, measure queue/work/setup metrics, `hpc.monitor` conditional forecast update and remaining work. | import root.a104×1; root.a104.hpc_campaign×1; root.a104.library×1; root.a104.library.hpc_resource_prediction×2 |
| `from_child_execution_job_submission.py` | 90 | original_launch_handoff: recover a launch_hpc's actual handoff receipt across report repair; receive_report: old child-form receipt/progress admission. | BindingContext .assignment×1; BindingContext .path×2; BindingContext .role×1; BindingContext .run_id×3; BindingContext .scope×2; import root.a104×1; root.a104.communication×1; root.a104.delivery_counterpart×1; root.a104.episode_return_records×1; root.a104.hpc_ledger×1; root.a104.method_loop.identities×1; root.a104.runtime×1; EpisodeRef×2; EpisodeReturnRecords×2; WorkflowError×2; table runtime_actions×1; table runtime_episodes×1; table runtime_report_attempts×2; workflow.binding_context×4; workflow.episode_bindings×1; workflow.is_job_source×2; workflow.job_episodes×2; workflow.native_timing_information×1; workflow.progress_provider×4; workflow.receipts×3; workflow.receive_tool_attributions×1; workflow.run_id×6; workflow.specialist×1; workflow.store×7 |
| `from_child_execution_progress_assessment.py` | 23 | Receive monitor child's typed form into received progress (same as the monitor's own). | BindingContext .episode_id×3; BindingContext .scope×2; root.a104.communication×1; root.a104.domain×1; root.a104.method_loop.durable×1; content_digest×2 |
| `from_child_execution_result_acquisition.py` | 44 | Old child-form receipt/progress admission for results children. | root.a104.delivery_counterpart×1; root.a104.episode_return_records×1; root.a104.runtime×1; EpisodeReturnRecords×2; WorkflowError×2; table runtime_report_attempts×2; workflow.binding_context×4; workflow.episode_bindings×1; workflow.is_job_source×2; workflow.job_episodes×2; workflow.native_timing_information×1; workflow.progress_provider×4; workflow.receipts×3; workflow.receive_tool_attributions×1; workflow.run_id×6; workflow.specialist×1; workflow.store×7 |
| `from_parent.py` | 43 | Assignment: commission_id (enum of configured) or commission_source_ref, plus owner_episode_id; must belong to its original `hpc` parent and carry the same commission identity; yield binding required when private yield is on. | BindingContext .assignment×1; BindingContext .episode_id×1; BindingContext .role×1; root.a104.communication×1; root.a104.domain×1; root.a104.execution_contracts×1; root.a104.hpc_commission_sources×1 |
| `goal.py` | 10 | Goal text (see Purpose). | none |
| `internal_summary.py` | 56 | decision_context: commission, owner, candidates, resource, child scope/commission, launch deliveries, launch report form, tool requests, current model, credit, latest comparison, model support, hpc_report_form, plans, latest monitor, monitor controllers, activity decision, queue refs, shared memory/history, available training ids. | BindingContext .assignment×1; BindingContext .episode_id×1; BindingContext .run_id×1; BindingContext .scope×1; root.a104.communication×1; root.a104.library×1; table runtime_episodes×1; table runtime_report_attempts×1 |
| `measured_history.py` | 82 | History rows (commission history + latest shared snapshot + one latest measurement per closed allocation), shared history query and queue pooling rules, export_closed to shared memory, `hpc.history.refresh`. | root.a104.execution_guidance×1; root.a104.hpc_history×1; root.a104.library.hpc_resource_prediction×1 |
| `portfolio_candidates.py` | 23 | `hpc.candidate.propose`: immutable candidate identity, validated against the commission. | root.a104.hpc_campaign×1 |
| `portfolio_comparison.py` | 44 | Candidates, features, `hpc.compare` (sorted by net expected value). | BindingContext .episode_id×1; import root.a104×1; root.a104.library×1 |
| `portfolio_planning.py` | 38 | `hpc.plan`: fresh enabled execution queue, queue limits, build plan, freeze original and reference forecasts. | import root.a104×1; root.a104.hpc_campaign×1; root.a104.library×1 |
| `portfolio_state.py` | 38 | HPC ledger state (owner scope and commission identity must match), initialize prior/shared-history model, current model. | BindingContext .assignment×4; BindingContext .role×1; BindingContext .scope×2; import root.a104×1; root.a104.communication×1; root.a104.domain×1; root.a104.hpc_ledger×1; root.a104.library×1 |
| `presentation.py` | 42 | Text-task prompt rendering (identical to the monitor's). Provider machinery. | root.a104.providers×1 |
| `presentation_selection.py` | 30 | Renderer selection (identical to the monitor's). | root.a104.evolutionary_history_evidence_prompt×2; root.a104.library.hpc_prompt×1; root.a104.library.monitor_prompt×1; root.a104.native_profile_presentation×1; root.a104.providers×1; root.a104.receiver_prompt×1 |
| `queue_observations.py` | 35 | Queue observation with shared-memory freshness, `hpc.queue.observe`. | import root.a104×1; root.a104.execution_guidance×1 |
| `received_evidence.py` | 60 | Known refs, resolve received `episode.hpc_result` sources, `hpc.read`. | BindingContext .received_record_refs×1; BindingContext .scope×1; root.a104.communication×1; self.services.record_selection (getattr)×1 |
| `report_delivery.py` | 32 | finish(). Old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; form_with_facts×2; Record×3; table runtime_forms×2; workflow.binding_context×1; workflow.episode_bindings×1; workflow.facts×1; workflow.journal×2; workflow.pending_handles×1; workflow.release×2; workflow.source_credit_view×1 |
| `resource_discovery.py` | 30 | `hpc.discovery.run`: one SSH command in the project directory, cached in shared memory; stdout/stderr byte-truncated. | import root.a104×1; root.a104.execution_guidance×1 |
| `task.py` | 107 | HPCWorkTask.next() with HPC handoff return-form policy. Old-runner machinery. | import root.a104×1; root.a104.episode_source_failure×1; root.a104.library.hpc_handoff_return_form×1; root.a104.library.live_runtime_functions×1; root.a104.providers×1; root.a104.runtime×1; ActionFailure×1; bind_functions×2; _bind_preserved_runtime_providers×2; ReportRedelivery×1; SourceEnd×3; view.units_consumed×4; WorkflowError×2; table runtime_actions×2; table runtime_episodes×1; table runtime_model_calls×1; workflow.action_schema×1; workflow.completed_unit×3; workflow.completions×2; workflow.delivery_resolution_inputs×1; workflow.execution_binding×2; workflow.inprocess_replay×4; workflow.journal×4; workflow.next_return×1; workflow.resolve_pending_deliveries×1; workflow.run_id×1; workflow.selected×2; workflow.store×3 |
| `task_decision.py` | 92 | Decision call. Old-runner machinery. | import root.a104×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; bind_functions×2; _bind_preserved_runtime_providers×2; WorkflowError×6; table runtime_model_calls×5; workflow.contract_information_profile×1; workflow.decision_exchanges×1; workflow.decision_protocol×3; workflow.freeze_contract_information×1; workflow.history_preview×1; workflow.journal×1; workflow.numerical_contracts×1; workflow.provider×2; workflow.receipts×4; workflow.services×1; workflow.uses_received_record_context×2; workflow.validate_contract_information×2; _category_yield_parameters×1; yield_table×1 |
| `task_instructions.py` | 14 | Instruction composition (see Task and instructions). | workflow.binding_context×1; workflow.knowledge×1; workflow.launch_instructions×1; workflow.native_event_information×1; workflow.permits_common_action×2; workflow.specialist×1 |
| `task_state.py` | 117 | Task state and checkpoint/restore. Old-runner machinery. | import root.a104×1; root.a104.episode_source_failure×1; root.a104.library.live_runtime_functions×1; root.a104.runtime×1; ActionLeaf×2; bind_functions×2; _bind_preserved_runtime_providers×2; Episode.identity×1; Record×2; table runtime_actions×5; workflow.archive×1; workflow.completions×4; workflow.context×1; workflow.controller_value×1; workflow.execution_binding×4; workflow.grains×1; workflow.inprocess_replay×7; workflow.journal×5; workflow.progress_provider×2; workflow.recover_commissions×1; workflow.run_id×1; workflow.source_credit_view×1; workflow.store×2 |
| `task_waiting.py` | 9 | suspension_changed. Old-runner machinery. | workflow.execution_backend×1; workflow.execution_handle×2 |
| `to_child_execution_job_submission.py` | 97 | authenticate_launch: only the exact planned launch may consume the allocation slot (reservation per plan; closed plan refuses); initial_decision_context for launch/launch_hpc children: hpc_execution_job (plan, objective, manifest, acceptance, input file, workspace, instructions). assemble_request: old. | BindingContext .assignment×2; BindingContext .episode_id×1; BindingContext .path×2; BindingContext .role×3; BindingContext .run_id×3; BindingContext .scope×2; import root.a104×1; root.a104.communication×1; root.a104.episode_contract_information×1; root.a104.hpc_ledger×1; root.a104.method_loop.identities×1; root.a104.practical_execution_state×1; root.a104.runtime×1; EpisodeGoal×3; Episode.identity×2; EpisodeRef×2; EpisodeRequest×2; Record×2; workflow.context×2; workflow.evolutionary_history_evidence_binding×1; workflow.grains×2; workflow.inprocess_completion_order×2; workflow.launch_instructions×1; workflow.receipts×2 |
| `to_child_execution_progress_assessment.py` | 42 | prepare_request: validate monitor_assignment_v1 unchanged (no polling here). assemble_request: old. | root.a104.communication×1; root.a104.domain×1; root.a104.episode_contract_information×1; root.a104.runtime×1; EpisodeGoal×3; Episode.identity×2; EpisodeRequest×2; Record×2; workflow.context×2; workflow.evolutionary_history_evidence_binding×1; workflow.grains×2; workflow.inprocess_completion_order×2; workflow.launch_instructions×1; workflow.receipts×2 |
| `to_child_execution_result_acquisition.py` | 30 | assemble_request only (old). | root.a104.episode_contract_information×1; root.a104.runtime×1; EpisodeGoal×3; Episode.identity×2; EpisodeRequest×2; Record×2; workflow.context×2; workflow.evolutionary_history_evidence_binding×1; workflow.grains×2; workflow.inprocess_completion_order×2; workflow.launch_instructions×1; workflow.receipts×2 |
| `to_parent.py` | 41 | Report facts hpc_credit, hpc_model_ref, hpc_accepted_obligations, hpc_result_refs; resolve `hpc_model`; facts must match. | root.a104.communication×1; root.a104.episode_bindings×1 |
| `waiting.py` | 50 | activity_advice from the last controller diagnostic (wait/collect -> suggested tool); `hpc.monitor.wait` via MonitorCronController (terminal or ready outputs -> collect now). | BindingContext .episode_id×1; BindingContext .run_id×1; root.a104.hpc_monitoring×1; table runtime_observations×1 |
| `work_operations.py` | 54 | Tool catalog (hpc.read, hpc.compare, hpc.history.refresh, hpc.discovery.run, hpc.candidate.propose, hpc.queue.observe, hpc.plan, hpc.handoff, hpc.monitor, hpc.monitor.wait, hpc.results, hpc.allocation.order) and dispatch with cached per-operation-key actions. | BindingContext .episode_id×1; root.a104.communication×1; root.a104.domain×1; root.a104.execution_contracts×1 |
| `yield_estimator.py` | 101 | Private yield from the commission's yield_bindings[role] with HPCContinuationEstimator and continuation cost = cutoff; continuation_for_action values pending obligations (collect upper bound, schedule valuation, deduplicated pending) and active history indices. | BindingContext .assignment×1; BindingContext .episode_id×3; BindingContext .role×5; BindingContext .run_id×3; BindingContext .scope×1; root.a104.hpc_monitoring×1; root.a104.library×1; root.a104.library.hpc_continuation×1; root.a104.numerical×1; table runtime_actions×2; table runtime_observations×1; HPCContinuationEstimator×2; YieldController×2; YieldParameters×2 |

## Carried over

One row per old function, class and method (`runs/carry_over/functions/a104__evolutionary_history_evidence__hpc_work_planning__hpc_allocation_execution.tsv`, 154 rows). Kind: `machinery` (old runner, not carried) or `episode function` (new place). Carried 19 November 2026 into the ten-file form; the job services and the HPC ledger are BLOCKED-ON-JOB-SERVICE (see `carry_over_blocked/a104__evolutionary_history_evidence__hpc_work_planning__hpc_allocation_execution.md`). "library candidate" marks a function of this episode's task.py that is not episode-specific. Old source: `git show 97308b94c:<path>` (git dir `/home/chia/repos/gene_annotation_episode_disk/.git`).

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| action_admission.py | HPCWorkTaskAdmission | episode function | task.py: action (the validation of the model's answer and Rejected); the journal rows, decision-exchange decoding, report_update handling and ReportRedelivery of the old body are machinery |
| action_admission.py | HPCWorkTaskAdmission.apply_response | episode function | task.py: action (decode_response, schema validation, Rejected(rejection_feedback)); the runtime_actions/runtime_model_calls rows, record_effect, report_update/validate_report on report values and ReportRedelivery are machinery |
| action_admission.py | _bind_preserved_runtime_providers | machinery | provider patching (_bind_preserved_runtime_providers): deleted (README 3a) |
| action_execution.py | HPCWorkTaskExecution | machinery | recorded unit execution (runtime_actions rows, completions.stage, receive_outcome, ActionFailure, controller_value): the system runs a ToolCall as one unit; the dispatch is task.py: _run and _execute |
| action_execution.py | HPCWorkTaskExecution.execute | machinery | recorded unit execution (runtime_actions rows, completions.stage, receive_outcome, ActionFailure, controller_value): the system runs a ToolCall as one unit; the dispatch is task.py: _run and _execute; the wait branch (perform_selected_wait) is not carried |
| action_execution.py | _bind_preserved_runtime_providers | machinery | provider patching (_bind_preserved_runtime_providers): deleted (README 3a) |
| allocation_handoff.py | AllocationHandoff | episode function | task.py: _attach_original_handoff and _execute (the two methods) |
| allocation_handoff.py | AllocationHandoff._attach_original_handoff | episode function | task.py: _attach_original_handoff (tool hpc_handoff); the received-reference test is ctx.store.holds |
| allocation_handoff.py | AllocationHandoff._work_on_original_allocation | episode function | task.py: _execute (the branch of hpc_monitor, hpc_monitor_wait, hpc_results and hpc_allocation_order) |
| allocation_observations.py | AllocationObservations | episode function | task.py: _read_target, _target, _window, _allocation, _observe_original_allocation |
| allocation_observations.py | AllocationObservations.targets | episode function | task.py: _read_target (ExecutionTargetReader is not in the library; the call is job_access.read_target, BLOCKED-ON-JOB-SERVICE) |
| allocation_observations.py | AllocationObservations._target | episode function | task.py: _target |
| allocation_observations.py | AllocationObservations._window | episode function | task.py: _window |
| allocation_observations.py | AllocationObservations._allocation | episode function | task.py: _allocation |
| allocation_observations.py | AllocationObservations._observe_original_allocation | episode function | task.py: _observe_original_allocation |
| allocation_order.py | AllocationOrder | episode function | task.py: _order_original_units |
| allocation_order.py | AllocationOrder._order_original_units | episode function | task.py: _order_original_units (tool hpc_allocation_order; job_access.write_allocation_control, BLOCKED-ON-JOB-SERVICE) |
| allocation_results.py | AllocationResults | episode function | task.py: _collected_unit_ids, _uncollected_completed_unit_ids, _publish, _collect_original_results |
| allocation_results.py | AllocationResults._collected_unit_ids | episode function | task.py: _collected_unit_ids (library candidate) |
| allocation_results.py | AllocationResults._uncollected_completed_unit_ids | episode function | task.py: _uncollected_completed_unit_ids (library candidate) |
| allocation_results.py | AllocationResults._publish | episode function | task.py: _publish (writes the Source through ctx.store.artifact and ctx.store.put) |
| allocation_results.py | AllocationResults._collect_original_results | episode function | task.py: _collect_original_results (tool hpc_results) |
| binding_record.py | HPCBindingRecord | machinery | the binding's own as_record() (README 3) |
| binding_record.py | HPCBindingRecord.as_record | machinery | the binding's own as_record() (README 3) |
| closed_models.py | ClosedModels | machinery | authentication of a closed hpc_model reference through runtime_forms, EpisodeReturnRecords and the owner ledger file (journal re-validation); custody and final_to_parent replace it |
| closed_models.py | ClosedModels.frozen_reference | machinery | authentication of a closed hpc_model reference through runtime_forms, EpisodeReturnRecords and the owner ledger file (journal re-validation); custody and final_to_parent replace it |
| configuration.py | HPCConfiguration | episode function | ctx.settings: resources and shared_execution_memory (task.py docstring); commission identity: messages/read_from_parent.py; yield binding: yield_estimator.py settings |
| configuration.py | HPCConfiguration.__init__ | episode function | ctx.settings: resources and shared_execution_memory (task.py docstring); the configured commissions are read by the ledger service (hpc_ledger.open); the commission yield binding is settings cost and parameters (yield_estimator.py); services/store/run_id/directory are the system and the services |
| credit.py | HPCEpisodeCredit | episode function | credit.py: credit |
| credit.py | HPCEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d); the credit is the ledger's operational credit |
| credit.py | HPCEpisodeCredit.credit_view | episode function | credit.py: credit (reads the ledger credit view that every tool returns in its outcome state, task.py: _state) |
| decision_contracts.py | HPCWorkTaskDecisionContracts | machinery | decision-exchange envelope, saved-request checks and replay validation (validate_contract_exchange_request/history, exchange_schema, exchange_response, interpretation_context): deleted; the system compares a rebuilt model request with its record (README 3a) |
| decision_contracts.py | HPCWorkTaskDecisionContracts.interpretation_context | machinery | decision-exchange envelope, saved-request checks and replay validation (validate_contract_exchange_request/history, exchange_schema, exchange_response, interpretation_context): deleted; the system compares a rebuilt model request with its record (README 3a) |
| decision_contracts.py | HPCWorkTaskDecisionContracts.exchange_schema | machinery | decision-exchange envelope, saved-request checks and replay validation (validate_contract_exchange_request/history, exchange_schema, exchange_response, interpretation_context): deleted; the system compares a rebuilt model request with its record (README 3a) |
| decision_contracts.py | HPCWorkTaskDecisionContracts.exchange_response | machinery | decision-exchange envelope, saved-request checks and replay validation (validate_contract_exchange_request/history, exchange_schema, exchange_response, interpretation_context): deleted; the system compares a rebuilt model request with its record (README 3a) |
| decision_contracts.py | HPCWorkTaskDecisionContracts.validate_contract_exchange_request | machinery | decision-exchange envelope, saved-request checks and replay validation (validate_contract_exchange_request/history, exchange_schema, exchange_response, interpretation_context): deleted; the system compares a rebuilt model request with its record (README 3a) |
| decision_contracts.py | HPCWorkTaskDecisionContracts.validate_contract_exchange_history | machinery | decision-exchange envelope, saved-request checks and replay validation (validate_contract_exchange_request/history, exchange_schema, exchange_response, interpretation_context): deleted; the system compares a rebuilt model request with its record (README 3a) |
| decision_contracts.py | _bind_preserved_runtime_providers | machinery | provider patching (_bind_preserved_runtime_providers): deleted (README 3a) |
| decision_exchange.py | HPCWorkTaskDecisionExchange | machinery | the request_context decision-exchange loop (exchange_decision): not carried; a lookup is a tool (README 3a) |
| decision_exchange.py | HPCWorkTaskDecisionExchange.exchange_decision | machinery | the request_context decision-exchange loop (exchange_decision): not carried; a lookup is a tool (README 3a) |
| decision_exchange.py | _bind_preserved_runtime_providers | machinery | provider patching (_bind_preserved_runtime_providers): deleted (README 3a) |
| decision_inputs.py | HPCWorkDecisionInputs | episode function | task.py: decide |
| decision_inputs.py | HPCWorkDecisionInputs.decision_inputs | episode function | task.py: decide (launch_instruction_library, tool_knowledge, child_options); requested_action_history and completed_action_reports: messages/internal_summary.py (launches, monitors, acquisitions from view.outcomes); resource_context, execution_expectations, resource_estimator, native event information and waiting_support came from the old shared root and the generic wait action: not carried |
| decision_inputs.py | _bind_preserved_runtime_providers | machinery | provider patching (_bind_preserved_runtime_providers): deleted (README 3a) |
| decision_provider.py | HPCWorkTaskDecisionProvider | machinery | presentation-provider patching and provider identity checks (decision_completion): the system calls the model provider |
| decision_provider.py | HPCWorkTaskDecisionProvider.decision_completion | machinery | presentation-provider patching and provider identity checks (decision_completion): the system calls the model provider |
| decision_state.py | HPCWorkDecisionState | episode function | messages/internal_summary.py: internal_summary and task.py: decide (the context) |
| decision_state.py | HPCWorkDecisionState.decision_state | episode function | messages/internal_summary.py: internal_summary (what the view holds) and task.py: decide (context from the summary, ctx.clock, ctx.settings); the runtime_actions SQL (visual_evidence), receipts, report_update/report_basis, delivery_status and the journal elapsed_view are machinery |
| decision_state.py | _bind_preserved_runtime_providers | machinery | provider patching (_bind_preserved_runtime_providers): deleted (README 3a) |
| episode.py | HPCEpisode | episode function | episode.py: HpcAllocationExecution |
| episode.py | HPCEpisode.child_roles | episode function | task.py: CHILD_SLOTS = {launch, monitor, results} |
| episode.py | HPCEpisode.allowed_children | machinery | child admission by role (allowed_children, caller capabilities): the slots are CHILD_SLOTS |
| episode.py | HPCEpisode.permitted_common_actions | machinery | the generic wait and redeliver_report actions are not carried (README 3a, 3b); tool and child are the two units |
| episode.py | HPCEpisode.prepare_child_request | episode function | messages/msg_to_child.py: msg_to_child (monitor branch; the monitor_assignment_v1 validation is the child's own form) |
| episode.py | HPCEpisode.child_request_assembler | episode function | messages/msg_to_child.py: msg_to_child (one branch per slot) |
| episode.py | HPCEpisode.receive_child_progress_for_role | episode function | messages/read_from_child.py: read_from_child (monitor branch); the delivery to the progress provider is machinery |
| episode.py | HPCEpisode.child_report_receiver | episode function | messages/read_from_child.py: read_from_child (launch and results branches) |
| episode.py | create_execution_bindings | machinery | home factory / binding construction with the caller operands (README 3, C1): the registry is built by the caller of link |
| forecast_observations.py | ForecastObservations | episode function | task.py: _freeze, _last_forecast, _measure, _update_conditional_forecast |
| forecast_observations.py | ForecastObservations._freeze | episode function | task.py: _freeze (library candidate) |
| forecast_observations.py | ForecastObservations._last_forecast | episode function | task.py: _last_forecast (library candidate) |
| forecast_observations.py | ForecastObservations._measure | episode function | task.py: _measure (library candidate) |
| forecast_observations.py | ForecastObservations._update_conditional_forecast | episode function | task.py: _update_conditional_forecast (tool hpc_monitor) |
| from_child_execution_job_submission.py | LaunchReceiptCustody | machinery | recovery of the launch receipt across report repair through runtime_actions and the ledger file (redelivery / journal re-validation); custody returns the handoff in the child result |
| from_child_execution_job_submission.py | LaunchReceiptCustody.original_launch_handoff | machinery | recovery of the launch receipt across report repair through runtime_actions and the ledger file (redelivery / journal re-validation); custody returns the handoff in the child result |
| from_child_execution_job_submission.py | receive_report | episode function | messages/read_from_child.py: read_from_child (launch branch: handoff_refs, completed); the receipts ledger, progress-provider delivery and runtime_report_attempts timing rows are machinery |
| from_child_execution_progress_assessment.py | receive_progress | episode function | messages/read_from_child.py: read_from_child (monitor branch: the delivered progress observations); the provider delivery (_receive_progress) is machinery |
| from_child_execution_result_acquisition.py | receive_report | episode function | messages/read_from_child.py: read_from_child (results branch: result_refs, completed); the receipts ledger and progress-provider delivery are machinery |
| from_parent.py | HPCAssignment | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | HPCAssignment.assignment_schema | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM (owner_episode_id, commission_id, commission_source_ref under the old names; the oneOf is read_from_parent) |
| from_parent.py | HPCAssignment.commission_identity | episode function | messages/read_from_parent.py: read_from_parent (the parent input's commission) |
| from_parent.py | HPCAssignment._commission | machinery | reading the commission from the configured dict or from the Store through hpc_commission_sources: the ledger service holds the commission (task.py: _ledger, hpc_ledger.open) |
| from_parent.py | HPCAssignment.prepare_assignment | machinery | checks of the commission against the commissioning HPC parent (role, owner, identity, yield binding): checks of a commission are not carried (rule 1) |
| goal.py | HPCGoal | episode function | goal.py: GOAL, UNIT, RESULT; task.py: INSTRUCTIONS |
| goal.py | HPCGoal.instructions | episode function | task.py: INSTRUCTIONS (the old text; the spans on redeliver_report, hpc_report_form, hpc_launch_report_form, pending_action and the generic wait are replaced by the handoff and tool names); goal.py: GOAL |
| internal_summary.py | HPCSummary | episode function | messages/internal_summary.py: internal_summary; task.py: _state |
| internal_summary.py | HPCSummary.decision_context | episode function | task.py: _state (the ledger part, read by the tools: the summary has no services) and messages/internal_summary.py: internal_summary; hpc_launch_deliveries, hpc_activity_decision and the two report forms are machinery |
| measured_history.py | MeasuredHistory | episode function | task.py: _history, _shared_history, _export_closed, _refresh_measured_history |
| measured_history.py | MeasuredHistory._history | episode function | task.py: _history (library candidate) |
| measured_history.py | MeasuredHistory._shared_history | episode function | task.py: _shared_history (estimate_table service: BLOCKED-ON-JOB-SERVICE) |
| measured_history.py | MeasuredHistory.export_closed | episode function | task.py: _export_closed (estimate_table.record: BLOCKED-ON-JOB-SERVICE) |
| measured_history.py | MeasuredHistory._refresh_measured_history | episode function | task.py: _refresh_measured_history (tool hpc_history_refresh) |
| portfolio_candidates.py | PortfolioCandidates | episode function | task.py: _propose_portfolio |
| portfolio_candidates.py | PortfolioCandidates._propose_portfolio | episode function | task.py: _propose_portfolio (tool hpc_candidate_propose) |
| portfolio_comparison.py | PortfolioComparison | episode function | task.py: _candidates, _features, _comparisons, _candidate, _compare_portfolios |
| portfolio_comparison.py | PortfolioComparison._candidates | episode function | task.py: _candidates (library candidate) |
| portfolio_comparison.py | PortfolioComparison._features | episode function | task.py: _features (library candidate) |
| portfolio_comparison.py | PortfolioComparison._comparisons | episode function | task.py: _comparisons (library candidate) |
| portfolio_comparison.py | PortfolioComparison._candidate | episode function | task.py: _candidate (library candidate) |
| portfolio_comparison.py | PortfolioComparison._compare_portfolios | episode function | task.py: _compare_portfolios (tool hpc_compare) |
| portfolio_planning.py | PortfolioPlanning | episode function | task.py: _freeze_portfolio_plan |
| portfolio_planning.py | PortfolioPlanning._freeze_portfolio_plan | episode function | task.py: _freeze_portfolio_plan (tool hpc_plan; stage_launch_input: BLOCKED-ON-JOB-SERVICE) |
| portfolio_state.py | PortfolioState | episode function | task.py: _ledger, _initialize, _current_model |
| portfolio_state.py | PortfolioState.state | episode function | task.py: _ledger (hpc_ledger.open(owner_episode_id, scope, commission): the scope and commission identity checks are the ledger service's: BLOCKED-ON-JOB-SERVICE) |
| portfolio_state.py | PortfolioState.initialize | episode function | task.py: _initialize (tool hpc_state and the first step of every operation) |
| portfolio_state.py | PortfolioState._current_model | episode function | task.py: _current_model (library candidate) |
| presentation.py | present_task_context | machinery | provider presentation protocol with conversation state frames (apply_state_frame, scientific_prompt_states): every ModelRequest carries the full context; the HPC text renderer it selected is unplaced (render_hpc_prompt) |
| presentation_selection.py | task_presentation_selection | machinery | renderer selection by context kind for the provider presentation protocol; its renderers (render_hpc_prompt, render_monitor_prompt, render_receiver_prompt, ...) came from the old shared root: not carried; the context travels as the ModelRequest mapping |
| queue_observations.py | QueueObservations | episode function | task.py: _observe_queue, _queue, _observe_resource_queue |
| queue_observations.py | QueueObservations._observe_queue | episode function | task.py: _observe_queue (job_access.observe_queue, estimate_table: BLOCKED-ON-JOB-SERVICE) |
| queue_observations.py | QueueObservations._queue | episode function | task.py: _queue (library candidate) |
| queue_observations.py | QueueObservations._observe_resource_queue | episode function | task.py: _observe_resource_queue (tool hpc_queue_observe) |
| received_evidence.py | ReceivedEvidence | episode function | task.py: _read_evidence, _read_retained |
| received_evidence.py | ReceivedEvidence._known | machinery | the set of received references (context.received_record_refs, services.record_selection): custody; the test is ctx.store.holds / records.holds |
| received_evidence.py | ReceivedEvidence.resolve_received_reference | machinery | resolution of a received hpc_result Source against the store and the scope (validate_scope): custody; task.py: _read_evidence checks holds and the Source's own receipt |
| received_evidence.py | ReceivedEvidence.read_evidence | episode function | task.py: _read_evidence |
| received_evidence.py | ReceivedEvidence._read_retained_evidence | episode function | task.py: _read_retained (tool hpc_read) |
| report_delivery.py | HPCWorkReportDelivery | machinery | report delivery (runtime_forms rows, form_with_facts, release, pending_handles): messages/final_to_parent.py: final_to_parent replaces it |
| report_delivery.py | HPCWorkReportDelivery.finish | machinery | report delivery (runtime_forms rows, form_with_facts, release, pending_handles): messages/final_to_parent.py: final_to_parent replaces it |
| report_delivery.py | _bind_preserved_runtime_providers | machinery | provider patching (_bind_preserved_runtime_providers): deleted (README 3a) |
| resource_discovery.py | ResourceDiscovery | episode function | task.py: _discover_resource |
| resource_discovery.py | ResourceDiscovery._discover_resource | episode function | task.py: _discover_resource (tool hpc_discovery_run; the ssh subprocess is job_access.run_command: BLOCKED-ON-JOB-SERVICE) |
| task.py | HPCWorkTask | machinery | the old decision machine class (mix-ins, child_return_form_policy, instruction_composer): decide and action in task.py; HPC_HANDOFF_RETURN_POLICY is the child return form selection in msg_to_child |
| task.py | HPCWorkTask.next | machinery | the old decision loop (inprocess replay, completions, resolve_pending_deliveries, source_failed SourceEnd, model call, apply_response): the system loop |
| task.py | _bind_preserved_runtime_providers | machinery | provider patching (_bind_preserved_runtime_providers): deleted (README 3a) |
| task_decision.py | HPCWorkTaskDecision | machinery | the old model-call and decision-exchange class: decide returns a ModelRequest |
| task_decision.py | HPCWorkTaskDecision.call | machinery | model call with saved request checks, contract information freezing, state frames and journal rows: decide returns a ModelRequest; the system records and replays |
| task_decision.py | HPCWorkTaskDecision.instructions | episode function | task.py: decide (INSTRUCTIONS + knowledge and launch instruction text) |
| task_decision.py | HPCWorkTaskDecision.conversation_key | machinery | conversation session key of the provider: every ModelRequest carries the full context |
| task_decision.py | _bind_preserved_runtime_providers | machinery | provider patching (_bind_preserved_runtime_providers): deleted (README 3a) |
| task_instructions.py | instructions | episode function | task.py: INSTRUCTIONS, ACTION_BOUNDARY, HOST_EXECUTION_GUIDANCE, ANSWER_INSTRUCTION and decide (knowledge and launch text appended); the redelivery, generic wait and native-event paragraphs describe actions that no longer exist and are not carried |
| task_state.py | HPCWorkTaskState | machinery | checkpoint/restore, record_effect and recorded failures of the old task |
| task_state.py | HPCWorkTaskState.__init__ | machinery | state of the old task (feedback, report_values, calls, restored flags) |
| task_state.py | HPCWorkTaskState.bind_execution_context | machinery | old execution-context binding |
| task_state.py | HPCWorkTaskState.record_execution_failure | machinery | record_source_failure / record_execution_failure (README 3a, 3c): a tool returns its failure as its outcome |
| task_state.py | HPCWorkTaskState.restore_checkpoint | machinery | checkpoint/restore (README 3e) |
| task_state.py | HPCWorkTaskState.restore | machinery | checkpoint/restore (README 3e) |
| task_state.py | HPCWorkTaskState.record_effect | machinery | record_effect (README 3e) |
| task_state.py | HPCWorkTaskState.checkpoint | machinery | checkpoint/restore (README 3e) |
| task_state.py | _bind_preserved_runtime_providers | machinery | provider patching (_bind_preserved_runtime_providers): deleted (README 3a) |
| task_waiting.py | HPCWorkSuspension | machinery | wait/suspension machinery of the old task (suspension_changed) |
| task_waiting.py | HPCWorkSuspension.suspension_changed | machinery | wait/suspension machinery of the old task (suspension_changed) |
| to_child_execution_job_submission.py | authenticate_launch | episode function | task.py: _check_child (a plan is launched once; the equality of the selected launch assignment with plan['launch_assignment'] is by construction: msg_to_child sends the plan's frozen assignment); the ledger reservation row is not written: nothing checks a commission |
| to_child_execution_job_submission.py | LaunchPreparation | episode function | messages/msg_to_child.py: msg_to_child (launch branch: message hpc_execution_job); task.py: _freeze_portfolio_plan (the supplied input file) |
| to_child_execution_job_submission.py | LaunchPreparation.initial_decision_context | episode function | messages/msg_to_child.py: msg_to_child (launch branch: message hpc_execution_job: plan id, objective, scientific manifest, scientific acceptance, supplied input file, instructions); task.py: _freeze_portfolio_plan (hpc_ledger.stage_launch_input writes the file: BLOCKED-ON-JOB-SERVICE) |
| to_child_execution_job_submission.py | assemble_request | machinery | the old request envelope (EpisodeGoal, EpisodeRequest, knowledge_inheritance, report contract declaration): ChildMessage |
| to_child_execution_progress_assessment.py | prepare_request | episode function | messages/msg_to_child.py: msg_to_child (monitor branch: the assignment fields of monitor_assignment_v1; the schema validation is the child's own form) |
| to_child_execution_progress_assessment.py | assemble_request | machinery | the old request envelope (EpisodeGoal, EpisodeRequest, knowledge_inheritance, report contract declaration): ChildMessage |
| to_child_execution_result_acquisition.py | assemble_request | machinery | the old request envelope (EpisodeGoal, EpisodeRequest, knowledge_inheritance, report contract declaration): ChildMessage; the results commission is msg_to_child (results branch) |
| to_parent.py | HPCReport | episode function | messages/final_to_parent.py: RETURN_FORM, final_to_parent, validate_report |
| to_parent.py | HPCReport.fact_sources | episode function | messages/final_to_parent.py: RETURN_FORM (hpc_credit, hpc_model_ref, hpc_accepted_obligations, hpc_result_refs under the old names, selectable; credit and finding required) |
| to_parent.py | HPCReport.facts | episode function | messages/final_to_parent.py: _facts and final_to_parent (from the ledger state of the summary); hpc_credit is completion[credit] |
| to_parent.py | HPCReport.resolve | machinery | the report-form reference resolver (namespaces hpc_model and source): the parent no longer writes a JSON-schema form; held records are custody |
| to_parent.py | HPCReport.validate_report | episode function | messages/final_to_parent.py: validate_report (every returned fact equals the recorded fact); the axis validate_form step of the parent's JSON-schema form is not carried |
| waiting.py | HPCActivityAdvice | episode function | task.py: _wait_for_original_observation (tool hpc_monitor_wait); activity_advice is machinery |
| waiting.py | HPCActivityAdvice.activity_advice | machinery | reads the last controller step of runtime_observations (activity_mode wait/collect): deleted with the reading of earlier controller records (README 3d) |
| waiting.py | HPCActivityAdvice._wait_for_original_observation | episode function | task.py: _wait_for_original_observation (tool hpc_monitor_wait: a wait tool is episode code) |
| work_operations.py | HPCWorkOperations | episode function | task.py: catalog, _execute, _run, TOOLS |
| work_operations.py | HPCWorkOperations.catalog | episode function | task.py: catalog (and TOOLS: hpc_read ... hpc_allocation_order) |
| work_operations.py | HPCWorkOperations.execute | episode function | task.py: _execute and _run (the twelve tools); the operation-key cache is ledger.cached/save_action keyed on ctx.operation_key |
| yield_estimator.py | HPCEpisodeYield | episode function | yield_estimator.py: yield_controller |
| yield_estimator.py | HPCEpisodeYield.yield_controller | episode function | yield_estimator.py: yield_controller (AccumulationYieldController; cost and parameters from settings, the old commission yield_bindings['hpc_execution']) |
| yield_estimator.py | HPCEpisodeYield.continuation_for_action | machinery | estimator packet of the old HPCContinuationEstimator (continuation evidence, runtime_observations/runtime_actions SQL): no estimator of its own (README 3d, 7b); the controller input is built by the system |
| yield_estimator.py | HPCEpisodeYield.practical_estimator | machinery | HPCContinuationEstimator with its verify callback (README 7b): no estimator of its own |
