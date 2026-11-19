# a102 / structural_homology_evidence / hpc_work_planning

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence/hpc_work_planning/<file>`. I read only the files directly in this folder. It has no `grading/` or `scoring/` subfolder. Its child folders (`execution_job_submission`, `execution_progress_assessment`, `execution_result_acquisition`, `hpc_allocation_execution`, `hpc_resource_prediction`) and `tests/` were not read.

## Purpose (its own words)
"Iterate toward the original accomplishment while balancing expected credit against real elapsed time and resource demand." It plans, launches, monitors and collects HPC (PBS on Aurora) work for a commission. The commission carries obligations, acceptance predicates, credit, candidate portfolios, a prediction model and history. Its words on credit: "Accepted accomplishment, model improvement, and fixed prospective forecast validation are the only parent credit components; launch-local credits are not added again." (`goal.py`)

## Task and instructions
- Role `hpc`, which is also an entry role. Its commissioning parent is `structural_homology_evidence`.
- The goal text (`goal.py`) covers:
  - prediction and execution sisters;
  - copying `hpc_child_commission` and `hpc_child_scope` exactly;
  - discovery (`hpc.discovery.run`) and candidate design (`hpc.candidate.propose`);
  - per-unit `HPC_UNIT_DIRECTORY` result.json and progress.json;
  - compute only on allocated nodes;
  - comparing portfolios on current queue features and measured history;
  - freezing a plan;
  - Launch → launch_hpc with `hpc_launch_report_form`;
  - redeliver instead of relaunching;
  - attaching the handoff;
  - `hpc.monitor` only when it can change a decision;
  - `hpc.results`;
  - `hpc.monitor.wait` with the attached controller;
  - never polling for credit or duplicating a submission.
- `task_instructions.py`: goal + tool knowledge + launch library + repair + wait + native event. There is no reasoning-commit or history swap.

## What it reads from its parent's assignment
- `commission_id` (enum of configured commissions) or `commission_source_ref`. A source ref must already be received by the parent.
- Optional `tool_request` {name, resources, arguments_json, result_reader, objective}. It is resolved against the real scientific tool library and an actual result reader, and must not be replaced by the allocation acceptance score.
- With a private yield, the commission must carry `yield_bindings`.

## Children
- `hpc_prediction` (`to_child_hpc_resource_prediction.py`):
  - sends: the same commission identity plus `owner_episode_id` = this episode;
  - takes back: its typed form, through `receive_prediction_report` (receipts, progress provider, timing receipts, tool attributions).
- `hpc_execution` (`to_child_hpc_allocation_execution.py`): same rule, received by `receive_allocation_report`.
- `launch` → `launch_hpc` (`to_child_execution_job_submission.py`):
  - `authenticate_launch`: only the exact planned launch assignment may consume a plan's launch slot, once, and never after closure;
  - `initial_decision_context` for the child: `hpc_execution_job`, with the plan written as a supplied input file, objective, manifest, acceptance, coordinator workspace and execution instructions (no setup recipe);
  - takes back: the handoff via `hpc_launch_report_form` (`execution_handoff_refs`);
  - `original_launch_handoff` recovers the plan's receipt from committed native outcomes across Launch report repair.
- `monitor`: sends a validated monitor assignment (the child's `_ASSIGNMENT`). Takes back progress refs with the same receiver as the monitor episode.
- `results`: the assignment is passed through unchanged.
- `create_execution_bindings` builds its own private execution_job_submission (api/local/hpc) and execution_result_acquisition children under `hpc_work_planning/`.

## Decision state shown to the model
- The generic state without annotation-axis branches, plus `internal_summary.decision_context`:
  - `hpc_commission`, `hpc_owner_episode_id`, `hpc_candidates`, `hpc_resource`;
  - `hpc_child_scope`, `hpc_child_commission`;
  - `hpc_launch_deliveries`, `hpc_launch_report_form`, `hpc_tool_request`;
  - `hpc_model_ref`, `hpc_credit`, `hpc_latest_comparison`, `hpc_model_support`, `hpc_report_form`;
  - `hpc_plans`, `hpc_latest_monitor`, `hpc_monitor_controllers`;
  - `hpc_activity_decision` (wait/collect advice from the last controller diagnostic);
  - `hpc_queue_refs`, shared memory/history refs and `hpc_available_training_ids`.
- Renderer: `render_hpc_prompt`.

## Tools
- `hpc.read`, `hpc.compare`, `hpc.history.refresh` (with shared memory), `hpc.discovery.run`, `hpc.candidate.propose`, `hpc.queue.observe`, `hpc.plan`, `hpc.handoff`, `hpc.monitor`, `hpc.monitor.wait`, `hpc.results`, `hpc.allocation.order`.
- Each is cached by operation key in the owner-scoped `HPCLedger`.
- Common actions: `tool`, `child`, `redeliver_report`, plus `wait` unless the commission has `monitoring`.

## Credit
- Kind `operational`. The credit is the ledger's `credit_view()`, which has three contributions:
  - accepted actual obligations;
  - model improvement;
  - fixed prospective forecast validation slots.
- Repeated polling adds none.

## Continuation
- Yield binding from `commission['yield_bindings']['hpc']` {cutoff, parameters}.
- Old estimator: `HPCContinuationEstimator(verify).with_continuation_cost(cutoff)`, fed by `continuation_for_action`. That evidence holds:
  - pending expected credit per unresolved obligation;
  - collect upper bounds for ready outputs;
  - an active credit ceiling of 0 when everything remaining is pending and nothing new can be trained;
  - active (non-passive) action indices.
- This is a target-completion estimate with pending value. The nearest new estimator is **completion with a target**.
- Note: `continuation_for_action` scales the forecast by `min(1.0, valuation/total)`. This is a clamp on the expected continuation value, not on earned credit.

## Report to parent
- Fact sources: `hpc_credit` (signed measured credit), `hpc_model_ref`, `hpc_accepted_obligations`, `hpc_result_refs` (received result sources).
- `validate_report` requires fact equality. `frozen_reference` validates a closed `hpc_model` ref read-only.

## Hard-limit observations in its own files
- `resource_discovery.py` calls `subprocess.run(..., timeout=90)`. This is an elapsed-time limit, which the carry-over must not keep.
- It truncates stdout to 64 KiB and stderr to 8 KiB.
- `measured_history._shared_history` caps the imported observations at `[:2000]`. This is a count limit.
- `queue_observations.py` uses the commission's `queue_max_age_seconds` as a freshness rule. This is a scientific validity setting, not a stopping budget.

## Differences visible
- It is the only one of these four that:
  - owns its own ledger store (`hpc/<digest>/hpc.sqlite`);
  - has several child kinds;
  - gets its credit from accepted obligations instead of receipts or bytes.
- Its task copy records failures only for `tool` actions. The monitor's copy also records `reason`.
- Its `decision_state` drops `_completed_work_axis_results`.

## File by file

Old-runner names column: `imp:` = `import gene_annotation_episode.episodic_workflow.root.a102.<module>` (old runner or old shared non-episode module; see runs/placement_plan/placement.tsv and runs/placement_merge/plan.tsv for where non-episode modules went). `runtime.X` = name used through `_live_original_runtime` (root.a102.runtime). `table:` = old journal/receipt SQLite table. ×N = number of uses. Per-use detail: runs/carry_over/calls/a102_02.tsv.

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| __init__.py | 0 | Empty package marker. | none |
| allocation_handoff.py | 35 | `hpc.handoff`: bind a received PBS handoff to the frozen plan (assignment must equal the plan's practical assignment); optionally attach a `MonitorCronController` when the commission has `monitoring`. Routing of monitor / monitor.wait / allocation.order / results on an attached plan; refusal with recovery guidance when no handoff is attached (redeliver the Launch report, do not relaunch). | imp:episode_bindings×1, imp:hpc_monitoring×1 |
| allocation_observations.py | 83 | Target reader over pbs_ssh resources; `_target` from the attached handoff; bounded file windows; `allocation-status.json` identity checks; one native status + allocation snapshot per operation, telemetry, unit progress, phase change and recent rate, measurement; then monitor or results. | imp:episode_bindings×1, imp:execution_progress×1, imp:hpc_campaign×3 |
| allocation_order.py | 16 | `hpc.allocation.order`: reorder only original work units via `write_allocation_control`. | none |
| allocation_results.py | 74 | `hpc.results`: for completed/failed units read the original `result.json` (hash must match the recorded completion), publish an `episode.hpc_result` source, accept obligations whose acceptance predicate holds; record closure, measured success, export to shared history. | imp:communication×1, imp:hpc_campaign×1, imp:hpc_queue×1 |
| binding_record.py | 10 | Binding identity `structural_homology_evidence/hpc_work_planning`, version `hpc_episode_v1`, configuration: resources, commissions, shared execution memory, commission yield flag. | none |
| closed_models.py | 27 | `frozen_reference` for namespace `hpc_model`: a closed episode's model ref is valid only if it is the recorded `hpc_model_ref` and exists in the owner's read-only ledger. | EpisodeReturnRecords×2, imp:communication×1, imp:episode_return_records×1, imp:hpc_queue×1, table:runtime_forms×1 |
| configuration.py | 32 | Constructor: services, store, run_id, directory, resources (at least one `pbs_ssh`), commissions validated by `validate_commission`, `require_commission_yield` (then every commission needs `yield_bindings`), optional shared `ExecutionMemory`. | imp:communication×1, imp:execution_memory×1, imp:hpc_campaign×1 |
| credit.py | 16 | Credit kind `operational`; credit view = the HPC ledger's `credit_view()` (accepted accomplishment, model improvement, fixed prospective forecast validation). | none |
| decision_inputs.py | 53 | Decision inputs (no shared information context; no annotation-axis branch; `hpc` execution expectations). | imp:episode_work_report×2, imp:library.hpc_prompt×1, imp:runtime×2, runtime.child_option_information×1, self.workflow.available_child_roles×1, self.workflow.binding_context×1, self.workflow.episode_bindings×1, self.workflow.execution_expectations×1, self.workflow.launch_instructions×2, self.workflow.native_estimation_context×1, self.workflow.pending_work×1, self.workflow.permits_common_action×1, self.workflow.resource_context×1, self.workflow.resource_estimator×4, self.workflow.waiting_support×1 |
| decision_state.py | 31 | Decision state without annotation-axis branches or `_completed_work_axis_results`. | imp:runtime×2, runtime.FACT_MEANINGS×1, runtime.FACT_SOURCES×1, runtime.json×1, runtime.Mapping×2, runtime._plain×2, runtime._references_in×1, self.workflow.binding_context×1, self.workflow.catalog×1, self.workflow.controller_binding×1, self.workflow.delivery_status×1, self.workflow.extra_report_sources×1, self.workflow.job_episode_options×1, self.workflow.journal×2, self.workflow.knowledge×1, self.workflow.local_outcome_preview×1, self.workflow.pending_work×1, self.workflow.receipt_projection×1, self.workflow.run_id×1, self.workflow.source_credit_binding×1, self.workflow.source_credit_view×1, self.workflow.specialist×1, self.workflow.store×3, self.workflow.tools×1, self.workflow.working_state×1, table:runtime_actions×1 |
| episode.py | 87 | `binding_path structural_homology_evidence/hpc_work_planning`, `commissioning_parent structural_homology_evidence`, roles/entry_roles `('hpc',)`, decision source `HPCWorkTask`, renderer `render_hpc_prompt`. Child roles `hpc_prediction, hpc_execution, launch, monitor, results`; common actions `tool, child, redeliver_report` (+`wait` unless the commission has monitoring). Child request preparation and receivers per role. `create_execution_bindings` constructs its own private execution_job_submission (+api/local/hpc job execution) and execution_result_acquisition children. | imp:library.hpc_prompt×1, imp:structural_homology_evidence.hpc_work_planning.execution_job_submission.api_job_execution.episode×1, imp:structural_homology_evidence.hpc_work_planning.execution_job_submission.episode×1, imp:structural_homology_evidence.hpc_work_planning.execution_job_submission.hpc_job_execution.episode×1, imp:structural_homology_evidence.hpc_work_planning.execution_job_submission.local_job_execution.episode×1, imp:structural_homology_evidence.hpc_work_planning.execution_result_acquisition.episode×1 |
| forecast_observations.py | 80 | Freeze forecasts with validation slots; last forecast; measured metrics (queue, work, setup) from PBS observation/exit receipt/allocation; `hpc.monitor` updates conditional prediction (optional queue refresh), remaining work comparison, order-aware. | imp:hpc_campaign×1, imp:hpc_queue×1, imp:library×1, imp:library.hpc_resource_prediction×2 |
| from_child_execution_job_submission.py | 46 | `original_launch_handoff`: recover this plan's actual Launch receipt from committed native outcomes under the owning HPC path (not a sibling conversation). | imp:communication×1, imp:hpc_ledger×1, imp:hpc_queue×1, imp:method_loop.identities×1, table:runtime_actions×1, table:runtime_episodes×1 |
| from_child_execution_progress_assessment.py | 23 | Admit a monitor child's progress refs (same as the monitor episode's own receiver). | imp:communication×1, imp:domain×1, imp:method_loop.durable×1 |
| from_child_hpc_allocation_execution.py | 31 | Receive the allocation child's admitted form through receipts, progress provider, timing receipts and tool attributions. | EpisodeReturnRecords×2, imp:episode_return_records×1, imp:runtime×1, runtime._json×1, runtime.json×1, runtime._references_in×1, runtime.WorkflowError×1, self.workflow.binding_context×2, self.workflow.episode_bindings×1, self.workflow.is_job_source×2, self.workflow.job_episodes×2, self.workflow.native_timing_information×1, self.workflow.progress_provider×2, self.workflow.receipts×3, self.workflow.receive_tool_attributions×1, self.workflow.run_id×4, self.workflow.store×7, table:runtime_report_attempts×2 |
| from_child_hpc_resource_prediction.py | 31 | Same receiving path for the prediction child. | EpisodeReturnRecords×2, imp:episode_return_records×1, imp:runtime×1, runtime._json×1, runtime.json×1, runtime._references_in×1, runtime.WorkflowError×1, self.workflow.binding_context×2, self.workflow.episode_bindings×1, self.workflow.is_job_source×2, self.workflow.job_episodes×2, self.workflow.native_timing_information×1, self.workflow.progress_provider×2, self.workflow.receipts×3, self.workflow.receive_tool_attributions×1, self.workflow.run_id×4, self.workflow.store×7, table:runtime_report_attempts×2 |
| from_parent.py | 69 | Assignment: `commission_id` (enum of configured) or `commission_source_ref`, optional `tool_request` (name, resources, arguments_json, result_reader, objective). `prepare_assignment`: source ref must be received by the parent; tool request resolved against the real scientific tool library and an actual result reader; yield binding required when private. | imp:communication×1, imp:domain×1, imp:execution_contracts×1, imp:hpc_commission_sources×1, services.workflow (getattr)×1 |
| goal.py | 10 | Long goal text: iterate toward the original accomplishment balancing expected credit against elapsed time and resource demand; prediction/execution sisters; discovery and candidate proposal; per-unit `HPC_UNIT_DIRECTORY` outputs; freeze plan; Launch with `hpc_launch_report_form`; redeliver instead of relaunching; monitor once when it can change a decision; results; monitor.wait controller; no polling credit; credit = accepted accomplishment + model improvement + fixed forecast validation. | none |
| internal_summary.py | 56 | Decision context: commission, owner id, candidates, resource, child scope/commission, launch deliveries, launch/HPC report forms, tool request, model ref, credit, latest comparison, model support, plans, latest monitor, controllers, activity advice, queue refs, shared memory/history, training ids. | imp:communication×1, imp:library×1, table:runtime_episodes×1, table:runtime_report_attempts×1 |
| measured_history.py | 82 | History (commission history + latest shared snapshot + one latest measurement per closed allocation); shared history query (queue-wide timing, matching work profile, queue pooling rule); `export_closed`; `hpc.history.refresh`. | imp:execution_guidance×1, imp:hpc_history×1, imp:library.hpc_resource_prediction×1 |
| portfolio_candidates.py | 23 | `hpc.candidate.propose`: immutable candidate identity, validated against the commission. | imp:hpc_campaign×1 |
| portfolio_comparison.py | 44 | Candidates, features, `hpc.compare` (predict + compare each candidate, sorted by net expected value). | imp:hpc_queue×1, imp:library×1 |
| portfolio_planning.py | 38 | `hpc.plan`: fresh enabled execution queue within limits, `build_plan`, original/reference predictions, prediction episode id, freeze forecast. | imp:hpc_campaign×1, imp:hpc_queue×1, imp:library×1 |
| portfolio_state.py | 38 | `state`: owner-scoped `HPCLedger` at `hpc/<digest(run_id, episode_id)>`; `initialize` prior model and optional shared-history model fit; `_current_model`. | imp:communication×1, imp:domain×1, imp:hpc_ledger×1, imp:hpc_queue×1, imp:library×1 |
| queue_observations.py | 35 | Queue observation (memory cache if fresh within `queue_max_age_seconds`), freshness requirement for planning, `hpc.queue.observe`. | imp:execution_guidance×1, imp:hpc_queue×1 |
| received_evidence.py | 60 | Known refs, received `episode.hpc_result` source resolution, `hpc.read`. | imp:communication×1, self.services.record_selection×1 |
| report_delivery.py | 25 | Generic finish. | imp:library.private_policy_call×1, imp:library.report_fact_assembly×1, imp:runtime×2, runtime.form_with_facts×1, runtime._json×2, runtime.json×1, runtime.Record×2, self.workflow.binding_context×1, self.workflow.episode_bindings×1, self.workflow.facts×1, self.workflow.journal×2, self.workflow.pending_handles×1, self.workflow.release×2, self.workflow.source_credit_view×1, table:runtime_forms×2 |
| resource_discovery.py | 30 | `hpc.discovery.run`: one lightweight ssh command in `/lus/flare/projects/BioReason-Aurora-Test`, cached in memory when fresh; `subprocess.run(..., timeout=90)`, stdout truncated to 64 KiB, stderr 8 KiB. | imp:execution_guidance×1, imp:hpc_queue×1 |
| task.py | 186 | Generic loop with grain `hpc`; attaches `hpc_handoff_report_validator` from the old library. | imp:episode_source_failure×1, imp:library.action_contracts×1, imp:library.hpc_handoff_report_contract×1, imp:library.private_policy_call×1, imp:providers×1, imp:runtime×2, runtime.ActionFailure×1, runtime.ContractInformationError×1, runtime._decode_recorded_action_response×1, runtime.Draft202012Validator×2, runtime.EventTargetError×2, runtime.inspect×1, runtime._json×5, runtime.json×8, runtime.nullcontext×5, runtime.observes_action_outcome×1, runtime.ReportBoundaryError×1, runtime.ReportRedelivery×2, runtime.schema_failure_diagnostic×1, runtime.SourceEnd×2, runtime.validate_form×1, runtime.ValidationError×2, runtime._wait_target_feedback×2, runtime.WorkflowError×2, self.workflow.action_schema×1, self.workflow.completed_unit×3, self.workflow.completions×3, self.workflow.controller_value×2, self.workflow.decision_exchanges×3, self.workflow.delivery_resolution_inputs×1, self.workflow.execute×1, self.workflow.execution_binding×7, self.workflow.inprocess_replay×4, self.workflow.journal×7, self.workflow.last_observed_credit×1, self.workflow.next_return×1, self.workflow.pending_work×1, self.workflow.perform_selected_wait×1, self.workflow.receive_native_outcome×1, self.workflow.receive_outcome×1, self.workflow.resolve_pending_deliveries×1, self.workflow.resolver×1, self.workflow.run_id×2, self.workflow.selected×3, self.workflow.source_credit_view×1, self.workflow.store×7, self.workflow.validate_report×1, table:runtime_actions×8, table:runtime_episodes×1, table:runtime_model_calls×2 |
| task_decision.py | 289 | Generic `call` (no annotation-axis yield table branch); `complete_decision` always uses presentation when available. | imp:runtime×2, runtime._action_generation_schema×2, runtime.apply_state_frame×1, runtime._ASSIGNMENT_TRANSPORT×1, runtime._category_yield_parameters×1, runtime.child_option_information×1, runtime.composition_lookup_schema×2, runtime.CONTRACT_INFORMATION_OPERATIONS×1, runtime.DECISION_CONTEXT_VERSION×2, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest×1, runtime.Draft202012Validator×1, runtime.instructional_model_context×4, runtime.is_contract_information×1, runtime._json×14, runtime.json×3, runtime.lookup_attempts×1, runtime.Mapping×2, runtime.model_snapshot×2, runtime._object×3, runtime._plain×2, runtime._recorded_action_generation_schema×1, runtime._recorded_assignment_transport×1, runtime._references_in×1, runtime.requested_contract_information×2, runtime.schema_failure_diagnostic×2, runtime.sqlite3×1, runtime.state_frame×1, runtime.ValidationError×5, runtime.WorkflowError×14, runtime.yield_table×1, self.workflow.contract_information_profile×1, self.workflow.contract_information_reply×1, self.workflow.controller_binding×1, self.workflow.decision_exchanges×4, self.workflow.decision_protocol×3, self.workflow.execute×1, self.workflow.freeze_contract_information×1, self.workflow.history_preview×1, self.workflow.journal×3, self.workflow.numerical_contracts×1, self.workflow.provider×3, self.workflow.receipts×4, self.workflow.run_id×1, self.workflow.services×2, self.workflow.specialist×1, self.workflow.store×2, self.workflow.uses_received_record_context×2, self.workflow.validate_contract_information×5, table:runtime_model_calls×8 |
| task_instructions.py | 14 | Composition: specialist goal + tool knowledge + launch library + repair + wait + native event (no reasoning commit, no history swap). | self.workflow.binding_context×1, self.workflow.knowledge×1, self.workflow.launch_instructions×1, self.workflow.native_event_information×1, self.workflow.permits_common_action×2, self.workflow.specialist×1 |
| task_state.py | 108 | Generic state; `record_execution_failure` covers `tool` only. | imp:episode_source_failure×1, imp:runtime×2, runtime.ActionLeaf×1, runtime.EFFECT_VERSION×1, runtime.Episode×1, runtime.interpretation_schema×1, runtime._json×2, runtime.json×4, runtime._object×1, runtime._plain×1, runtime.Record×1, self.workflow.archive×1, self.workflow.completions×4, self.workflow.context×1, self.workflow.controller_value×1, self.workflow.execution_binding×4, self.workflow.grains×1, self.workflow.inprocess_replay×7, self.workflow.journal×5, self.workflow.progress_provider×2, self.workflow.recover_commissions×1, self.workflow.run_id×1, self.workflow.source_credit_view×1, self.workflow.store×2, table:runtime_actions×5 |
| task_waiting.py | 9 | `suspension_changed`. | self.workflow.execution_backend×1, self.workflow.execution_handle×2 |
| to_child_execution_job_submission.py | 67 | `authenticate_launch`: only the exact planned launch may consume a plan's launch slot, once, and not after closure. `initial_decision_context` for launch/launch_hpc children: the frozen plan as a supplied input file plus objective, manifest, acceptance, coordinator workspace and execution instructions (no setup recipe). | imp:communication×1, imp:hpc_ledger×1, imp:hpc_queue×1, imp:method_loop.identities×1, imp:practical_execution_state×1 |
| to_child_execution_progress_assessment.py | 12 | Monitor child request = validated monitor assignment (imports the child's `_ASSIGNMENT`). | imp:communication×1, imp:domain×1 |
| to_child_hpc_allocation_execution.py | 29 | Allocation child request: same commission identity and `owner_episode_id` = this episode. | imp:communication×1, imp:domain×1, imp:execution_contracts×1 |
| to_child_hpc_resource_prediction.py | 29 | Prediction child request: same rule. | imp:communication×1, imp:domain×1, imp:execution_contracts×1 |
| to_parent.py | 41 | Fact sources `hpc_credit`, `hpc_model_ref`, `hpc_accepted_obligations`, `hpc_result_refs`; facts from the ledger; resolve `hpc_model`; `validate_report` fact equality. | imp:communication×1, imp:episode_bindings×1 |
| waiting.py | 50 | `activity_advice` from the last controller diagnostic (wait/collect); `hpc.monitor.wait` (initial monitor, collect-now reasons, reserve schedule, wait, observe once). | imp:hpc_monitoring×1, table:runtime_observations×1 |
| work_operations.py | 54 | Tool catalog: `hpc.read`, `hpc.compare`, `hpc.history.refresh` (with memory), `hpc.discovery.run`, `hpc.candidate.propose`, `hpc.queue.observe`, `hpc.plan`, `hpc.handoff`, `hpc.monitor`, `hpc.monitor.wait`, `hpc.results`, `hpc.allocation.order`; `execute` caches by operation key in the ledger and dispatches. | imp:communication×1, imp:domain×1, imp:execution_contracts×1 |
| yield_estimator.py | 101 | `yield_controller`: commission `yield_bindings[role]` cutoff/parameters with `HPCContinuationEstimator(...).with_continuation_cost(cutoff)`. `continuation_for_action`: pending expected credit per unresolved obligation from open monitor controllers (`choose_schedule`, `prediction.compare`, scaled by `min(1.0, expected/total)`), collect upper bound for ready outputs, active ceiling 0 when nothing new can be trained, active (non-passive) history indices; saved in the ledger. | HPCContinuationEstimator×2, imp:hpc_monitoring×1, imp:library×1, imp:library.hpc_continuation×1, imp:numerical×1, table:runtime_actions×2, table:runtime_observations×1, YieldController×2, YieldParameters×2 |
