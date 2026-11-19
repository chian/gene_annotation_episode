# Episode intent: `a102/structural_homology_evidence/hpc_work_planning/hpc_allocation_execution`

Source: this episode's own files at commit `97308b94c` (38 Python files, 2,016 lines, directly in the folder; its
`tests/` folder and its three child folders were not read). Old role name: `hpc_execution`. Old class: `HPCEpisode`,
task class `HPCWorkTask`. Old `binding_path`: `structural_homology_evidence/hpc_work_planning/hpc_allocation_execution`;
old `commissioning_parent`: `structural_homology_evidence/hpc_work_planning`.

## What this episode is for

It turns the HPC parent's commission into work actually done on one real allocation: it prepares candidate
portfolios, freezes a plan with its forecast, has the job launched, attaches the returned handoff, observes the job,
and parses and accepts the results. It works on the ledger owned by its `hpc` parent, as the sister of the
resource-prediction episode. Its goal text (`goal.py`), in its own words, abridged only by omission:

> Iterate toward the original accomplishment while balancing expected credit against real elapsed time and resource
> demand. The hpc parent can commission hpc_prediction and hpc_execution as sisters: prediction
> fits/measures/compares; execution prepares, launches, monitors and parses the selected work. Both assignments copy
> hpc_child_commission exactly and carry the hpc parent owner_episode_id. Both sisters inherit exactly
> hpc_child_scope [...] Use hpc_report_form as the return contract. [...] Queue/setup costs belong to an allocation,
> which should carry enough useful work. When candidates are absent, discover the remote environment and
> documentation with hpc.discovery.run, then design candidate portfolios with hpc.candidate.propose. Discover is for
> lightweight inspection; leave installation and file staging to Launch, and scientific computation to the actual
> allocation. You choose the real inputs, database, executable commands, resources, worker code and preparation
> instructions. Never fabricate inputs or receipts. Every work unit writes result.json and progress.json under
> os.environ["HPC_UNIT_DIRECTORY"] [...] Compare portfolios using current queue features and measured history. A
> plan freezes its original forecast, scientific manifest and acceptance criteria. Commission launch -> launch_hpc
> with that actual job and resource. [...] Use hpc_launch_report_form as the Launch return contract. If a completed
> Launch return omitted its receipt, use redeliver_report with the existing delivery_ref and hpc_launch_report_form;
> report repair must not commission another Launch. Attach that received handoff. Use hpc.monitor once when another
> observation can affect your decision [...] Use hpc.results directly for known parsing. Commission monitor/results
> children only for actual investigation. [...] When hpc_monitor_controllers is present, select hpc.monitor.wait for
> a scheduled observation [...] Do not poll for credit or duplicate a submitted attempt. Never replace an uncertain
> submission. Accepted accomplishment, model improvement, and fixed prospective forecast validation are the only
> parent credit components; launch-local credits are not added again.

The full text is one paragraph of about 3,900 characters in `goal.py` and should be carried over whole.

## Task and instructions

One unit is one model-selected action: a tool call, a child commission (launch, monitor or results), a report
redelivery, or a wait. Wait is permitted only when the commission has no `monitoring` section; with `monitoring`,
waiting is done through the tool `hpc.monitor.wait`. There is no reasoning-commit action.

Instructions (`task_instructions.py`): the goal text; tool-knowledge and launch-instruction library text when
present; the report-repair paragraph; the wait and native-event paragraphs when wait is permitted. The episode
supplies its whole instructions.

## What it reads from its parent's assignment

| Field | Meaning | Check |
|---|---|---|
| `owner_episode_id` (required) | The `hpc` parent episode that owns the ledger | Must be the commissioning parent's own episode id; the parent's role must be `hpc` |
| `commission_id` or `commission_source_ref` (exactly one) | Which commission: a statically configured one, or one read from a Store source | Must be the same commission identity as the parent's own assignment |

From the commission it then reads: `objective`, `resource_id`, `obligations` (each with its credit and acceptance
predicate), `preferences`, `candidates`, `history`, `validation_ids`, `model`, `credit.validation_slots`,
`limits` (`queue_max_age_seconds`, `result_limit_bytes`), optional `monitoring`, optional `execution_profile`, and
`yield_bindings` (required when a commission yield is required). Its scope must equal the owner's scope
(`sister_scope_must_equal_original_parent_scope`).

## Children

| Child (old role) | Folder | What it sends | What it takes back |
|---|---|---|---|
| `launch` | `execution_job_submission` | The launch assignment returned by `hpc.plan` for one frozen plan, unchanged; return contract `hpc_launch_report_form`. Only the exact planned launch is admitted, one reservation per plan, none after the plan is closed (`authenticate_launch`). At its first decision the launch side is given: plan id, objective, the frozen scientific manifest, the acceptance predicates, a local input file holding the plan, the coordinator workspace, and the instruction that reference files are inputs and not a required procedure. | A typed form with `execution_handoff_refs`. The handoff is then attached to the plan with `hpc.handoff` (it must be received and match the plan's practical assignment). If a completed launch omitted its receipt, the report is redelivered; another launch is never commissioned. `original_launch_handoff` can recover the plan's actual handoff from committed outcomes under the owning HPC path. Launch-local credit is not added to this episode's credit. |
| `monitor` | `execution_progress_assessment` | A `monitor_assignment_v1` passed through unchanged after validation (target, known observations, requested fields, permitted record types). "This parent requests information; it never polls here." | The monitor's typed form; `episode_progress` references in it become received progress. |
| `results` | `execution_result_acquisition` | The assignment as selected (no change by this episode). | The typed form with result references. Used "only for actual investigation"; known parsing is done directly with `hpc.results`. |

`episode.py` also holds `create_execution_bindings`, which constructed the launch binding, its three resource
children and the results binding with the caller's operands. That is old-runner construction, not episode intent.

## Decision state and what the model sees

Beyond the common decision fields, `internal_summary.py` shows: the commission; the owner episode id; all
candidates; the resource configuration; `hpc_child_scope` and `hpc_child_commission` (to copy into children);
launch deliveries with their delivered forms; `hpc_launch_report_form` (one field, `execution_handoff_refs`);
tool requests; the current model reference and its support; the current credit view; the latest comparison;
`hpc_report_form` (`hpc_credit`, `hpc_model_ref`, `hpc_result_refs`); plans; the latest monitor; monitor
controllers; activity advice; queue references; shared memory and shared history references; available training
ids. `decision_inputs.py` adds `requested_action_history` in an HPC context and execution expectations for role
`hpc_execution`.

Activity advice (`waiting.py`): when the last controller observation says the mode is `wait` or `collect` and a
monitor controller is attached, the model is told the suggested tool (`hpc.results` to collect; `hpc.monitor.wait`
or `hpc.monitor` to wait), the active next gain and the pending expected credit.

## Tools

| Tool | What it does |
|---|---|
| `hpc.read` | Read retained HPC evidence by exact identity (history rows, ledger records, received result sources). |
| `hpc.compare` | Compare all approved portfolios under a model and a queue observation; selects and launches nothing. |
| `hpc.history.refresh` | Read age-weighted shared timing history once (only when shared memory is configured). |
| `hpc.discovery.run` | One lightweight remote inspection or documentation retrieval over the established SSH transport; no submission, installation or computation. |
| `hpc.candidate.propose` | Retain an executable portfolio (`candidate_json`: id, queue, nodes, wall_seconds, features, units, optional files, preparation). Candidate identities are immutable. |
| `hpc.queue.observe` | Acquire the PBS queue and facility status once and derive features per candidate. |
| `hpc.plan` | Freeze one portfolio and its forecasts; return a concrete launch assignment. Needs a fresh queue observation and an enabled, started execution queue whose limits admit the candidate. |
| `hpc.handoff` | Bind the received PBS handoff to the frozen portfolio; attaches the monitor controller when the commission has `monitoring`. |
| `hpc.monitor` | Observe the original job and its progress once; update and freeze the conditional forecast. |
| `hpc.monitor.wait` | Use the attached forecast-valued controller: persist a timer, wait, then observe the original job exactly once. No credit for waiting. |
| `hpc.results` | Parse compact results from the original allocation and apply the original acceptance predicates. |
| `hpc.allocation.order` | Reorder pending original units at the next unit boundary. |

Every tool call is cached by operation key and its intent recorded before execution (`work_operations.py`).

## Credit

Credit kind `operational`. Credit is the owner ledger's credit view, read as it stands (`credit.py`). Its
components, from the goal text and the ledger calls: accepted accomplishment (an obligation whose unit completed
with return code 0 and whose result document satisfies the caller's acceptance predicate), model improvement, and
fixed prospective forecast validation (forecasts frozen into the commission's validation slots and later scored
against measurements). Polling and waiting add nothing; launch-local credit is not added again. The value is
described as "Signed measured credit".

## Continuation

Settings: the commission's `yield_bindings['hpc_execution']` = `{cutoff, parameters}`. Estimator: the old
`HPCContinuationEstimator` with the cutoff as continuation cost. After each action the episode records a
continuation packet (`continuation_for_action`): remaining obligations; per open plan the expected continuation
credit from the conditional forecast (or the upper bound of unresolved acceptance when outputs await collection);
`pending_action = collect` when outputs are ready; `active_credit_ceiling = 0` when every remaining obligation is
already pending in a single-unit allocation and no new training cases exist; the indices of active (non-wait,
non-monitor, non-results) actions; and zero earned credit for waiting.

This does not map one-to-one onto the three estimators of `yield_control`. The closest reading is **completion
with a target** (target: all original obligations accepted, with pending work valued by forecast). Which of the
three this episode should use is an open question for the owner; a fourth estimator is not an option.

## What it reports to its parent

The parent's typed form (`hpc_report_form`). Facts it can fill (`to_parent.py`):

| Fact | Meaning |
|---|---|
| `hpc_credit` | Signed measured credit; repeated polling adds none |
| `hpc_model_ref` | Immutable identity of the selected prediction model |
| `hpc_accepted_obligations` | Original obligations with accepted actual results |
| `hpc_result_refs` | Store sources holding original result bytes and attempt custody, restricted to those this episode received |

The report must agree with recorded evidence (`hpc_report_disagrees_with_recorded_evidence`).

## Differences from similar episodes

- Against its parent `hpc_work_planning` (same file names; compared by blob hash only): nine files are identical
  (`decision_state.py`, `from_child_execution_progress_assessment.py`, `report_delivery.py`, `task_decision.py`,
  `task_instructions.py`, `task_state.py`, `task_waiting.py`, `to_child_execution_progress_assessment.py`,
  `__init__.py`); the other 29 differ, and the parent additionally has `to_child_`/`from_child_` files for
  `hpc_allocation_execution` and `hpc_resource_prediction`.
- Its goal text addresses both sisters ("prediction fits/measures/compares; execution prepares, launches, monitors
  and parses"), so part of it reads as the parent's or the prediction sister's text.
- It holds nested copies of `execution_progress_assessment` and `execution_result_acquisition` that are almost
  byte-identical to the ones directly under `hpc_work_planning` (see those notes).
- Unlike the monitor, results and launch episodes it does not compute credit itself: credit lives in the owner's
  ledger.

## Points in the old text that conflict with standing rules

- `resource_discovery.py` runs the remote command with `timeout=90` and truncates output to 65,536 and 8,192 bytes;
  `measured_history.py` keeps only the first 2,000 shared-history rows. Standing rule: no elapsed-time or count
  limits anywhere.
- `resource_discovery.py` hard-codes the project directory `/lus/flare/projects/BioReason-Aurora-Test`.

## Old support modules this episode imports

Where each imported old module is now (looked up in `runs/placement_plan/placement.tsv` and by file name under
`episode_support/`; the modules themselves were not read):

| Old module (`root.a102.`...) | Files importing it | Home now |
|---|---|---|
| `communication` | 13 | no structural_homology_evidence copy found (same-named copies exist for seven other axes under episode_support/forms/AXIS/; top-level method_loop/communication.py exists) |
| `domain` | 5 | episode_support/records/structural_homology_evidence/domain.py |
| `episode_bindings` | 3 | the deleted old per-axis binding table |
| `episode_return_records` | 1 | no placed home found |
| `episode_source_failure` | 2 | no placed home found |
| `episode_work_report` | 1 | no placed home found |
| `execution_contracts` | 2 | episode_support/forms/structural_homology_evidence/execution_contracts.py |
| `execution_guidance` | 3 | episode_support/instructions/execution_guidance.py |
| `execution_memory` | 1 | episode_support/records/structural_homology_evidence/execution_memory.py |
| `execution_progress` | 1 | no placed home found |
| `hpc_campaign` | 6 | episode_support/jobs/hpc/structural_homology_evidence/hpc_campaign.py |
| `hpc_commission_sources` | 1 | episode_support/jobs/hpc/structural_homology_evidence/hpc_commission_sources.py |
| `hpc_history` | 1 | episode_support/jobs/hpc/structural_homology_evidence/hpc_history.py |
| `hpc_ledger` | 3 | episode_support/jobs/hpc/structural_homology_evidence/hpc_ledger.py |
| `hpc_monitoring` | 3 | episode_support/jobs/hpc/structural_homology_evidence/hpc_monitoring.py |
| `hpc_queue` | 10 | episode_support/jobs/hpc/hpc_queue.py |
| `library.action_contracts` | 1 | no placed home found |
| `library.hpc_continuation` | 1 | no placed home found |
| `library.hpc_handoff_report_contract` | 1 | no placed home found |
| `library.hpc_prediction` | 6 | episode_support/jobs/hpc/structural_homology_evidence/hpc_prediction.py |
| `library.hpc_prompt` | 2 | no placed home found |
| `library.hpc_resource_prediction` | 2 | episode_support/jobs/hpc/structural_homology_evidence/hpc_resource_prediction.py |
| `library.private_policy_call` | 2 | no placed home found |
| `library.report_fact_assembly` | 1 | no placed home found |
| `method_loop.durable` | 1 | top-level method_loop/durable.py (the only method_loop) |
| `method_loop.identities` | 2 | top-level method_loop/identities.py (the only method_loop) |
| `numerical` | 1 | old yield code; its names NumericBand, YieldParameters, YieldEstimate, estimate_nonnegative_yield, estimate_bounded_credit_yield are now in top-level yield_control; YieldController/BoundedYieldController are not (controllers there are Accumulation/BoundedQuality/Completion) |
| `practical_execution_state` | 1 | episode_support/jobs/structural_homology_evidence/practical_execution_state.py |
| `providers` | 1 | gene_annotation_episode/model_provider.py (defines ModelCallError) |
| `runtime` | 6 | the deleted old per-axis runner |

## File by file

Counts are occurrences in the file text. `self.workflow` also covers `source.workflow` and a `workflow` argument;
"BindingContext fields" are attribute reads on the old context object (`context`, `parent`, `child`); "old-runner
callbacks defined" are methods the old runner called on the binding or task. The same rows, one per name and file,
are in `runs/carry_over/calls/a102_04.tsv` (653 uses in this episode).

| Old file | Lines | This episode's own intent in it | Old-runner names used (name×uses) |
|---|---|---|---|
| `__init__.py` | 0 | Nothing (package marker). | none |
| `allocation_handoff.py` | 35 | Tool `hpc.handoff`: bind the received PBS handoff to the frozen plan (handoff must be received and match the plan's practical assignment); attach the monitor controller when the commission has `monitoring`. Routing of `hpc.monitor`, `hpc.monitor.wait`, `hpc.results`, `hpc.allocation.order`, which all require an attached handoff. | **BindingContext fields**: `scope`; **imports from old `root.a102`**: `episode_bindings`, `hpc_monitoring`; **per-axis providers**: `self.targets`; **old support classes**: `MonitorCronController`×2 |
| `allocation_observations.py` | 83 | One observation of the original job: native status, `allocation-status.json` (identity-checked against plan, job and manifest), the running unit's `progress.json`, phase change and recent rate; then a measurement. | **BindingContext fields**: `scope`; **imports from old `root.a102`**: `episode_bindings`, `execution_progress`, `hpc_campaign`×3; **per-axis providers**: `self.targets`×3; **old support classes**: `ExecutionTargetReader`×2 |
| `allocation_order.py` | 16 | Tool `hpc.allocation.order`: reorder pending original units at the next unit boundary; only original unit ids. | **per-axis providers**: `self.targets`×2 |
| `allocation_results.py` | 74 | Tool `hpc.results`: read each finished unit's `result.json` from its own unit directory, check path, ownership and completion hash, publish it as a Store source (`episode.hpc_result`), accept the obligation when the unit succeeded and the caller's acceptance predicate holds; close the plan when the job is complete or failed and export the measurement. | **BindingContext fields**: `episode_id`×2, `scope`; **imports from old `root.a102`**: `communication`, `hpc_campaign`, `hpc_queue` |
| `binding_record.py` | 10 | Its configuration record: resources, commissions, shared execution memory, whether a commission yield is required. | **old-runner callbacks defined**: `as_record`; **per-axis providers**: `self.memory`×2 |
| `closed_models.py` | 27 | Lets a closed episode's `hpc_model` reference be validated from the saved report facts and a read-only open of the owner's ledger. | **BindingContext fields**: `assignment`, `episode_id`, `role`, `run_id`×2, `scope`; **imports from old `root.a102`**: `communication`, `episode_return_records`, `hpc_queue`; **old-runner callbacks defined**: `frozen_reference`; **old support classes**: `EpisodeReturnRecords`×2; **journal/receipt tables**: `runtime_forms` |
| `configuration.py` | 32 | Settings and checks: resources must include a `pbs_ssh` resource; static `commissions` validated against resources; optional shared execution memory; `require_commission_yield` (then every commission must carry `yield_bindings`). | **imports from old `root.a102`**: `communication`, `execution_memory`, `hpc_campaign`; **per-axis providers**: `self.memory`; **old support classes**: `ExecutionMemory`×2 |
| `credit.py` | 16 | Credit kind `operational`; credit is the ledger's credit view (accepted obligations, model improvement, validated forecasts), never recomputed here. | **old-runner callbacks defined**: `credit_kind`, `credit_view` |
| `decision_inputs.py` | 53 | Additions to each decision: resource context, launch-instruction library, child options, completed-action reports, `requested_action_history` in an HPC context, pending work, execution expectations for role `hpc_execution`, resource estimates, waiting support. | **imports from old `root.a102`**: `episode_work_report`×2, `library.hpc_prompt`, `runtime`×2; **old-runner callbacks defined**: `decision_inputs`; **old runtime**: `child_option_information`; **self.workflow**: `available_child_roles`, `binding_context`, `episode_bindings`, `execution_expectations`, `launch_instructions`×2, `native_estimation_context`, `pending_work`, `permits_common_action`, `resource_context`, `resource_estimator`×4, `waiting_support` |
| `decision_state.py` | 31 | What the model is shown; no `annotation_axis_credit` branch. Byte-identical to the parent `hpc_work_planning` copy. | **imports from old `root.a102`**: `runtime`×2; **old-runner callbacks defined**: `decision_state`; **old runtime**: `FACT_MEANINGS`, `FACT_SOURCES`, `json`, `Mapping`×2, `_plain`×2, `_references_in`; **self.workflow**: `binding_context`, `catalog`, `controller_binding`, `delivery_status`, `extra_report_sources`, `job_episode_options`, `journal`×2, `knowledge`, `local_outcome_preview`, `pending_work`, `receipt_projection`, `run_id`, `source_credit_binding`, `source_credit_view`, `specialist`, `store`×3, `tools`, `working_state`; **journal/receipt tables**: `runtime_actions` |
| `episode.py` | 75 | The binding: path, parent `hpc_work_planning`, role `hpc_execution`, HPC prompt renderer; children `launch`, `monitor`, `results`; permitted actions tool, child, redeliver_report, plus wait only when the commission has no `monitoring`; also the constructor of the launch and results bindings (`create_execution_bindings`). | **BindingContext fields**: `assignment`, `role`, `scope`; **absolute imports inside the episode tree**: `structural_homology_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.api_job_execution.episode`, `structural_homology_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.episode`, `structural_homology_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.hpc_job_execution.episode`, `structural_homology_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.local_job_execution.episode`, `structural_homology_evidence.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.episode`; **imports from old `root.a102`**: `library.hpc_prompt`; **old binding attributes**: `binding_path`, `commissioning_parent`, `decision_prompt_renderer`, `decision_source_type`, `entry_roles`, `replaces_default_instructions`, `roles`; **old-runner callbacks defined**: `allowed_children`, `child_roles`, `permitted_common_actions`, `prepare_child_request`, `receive_child_progress_for_role` |
| `forecast_observations.py` | 80 | Freezing forecasts into validation slots, the last forecast of a plan, turning an observation into measured queue/setup/work durations (censored when unfinished), and tool `hpc.monitor`: update the conditional prediction, optionally with a refreshed queue observation, and compare remaining work. | **imports from old `root.a102`**: `hpc_campaign`, `hpc_queue`, `library.hpc_prediction`, `library.hpc_resource_prediction`×2 |
| `from_child_execution_job_submission.py` | 46 | Recovers the frozen plan's actual launch handoff from committed outcomes under the owning HPC path (used when a launch report is repaired). | **BindingContext fields**: `assignment`, `path`×2, `role`, `run_id`×3, `scope`×2; **imports from old `root.a102`**: `communication`, `hpc_ledger`, `hpc_queue`, `method_loop.identities`; **old-runner callbacks defined**: `original_launch_handoff`; **per-axis providers**: `self.targets`; **old support classes**: `HPCLedger`×2; **journal/receipt tables**: `runtime_actions`, `runtime_episodes` |
| `from_child_execution_progress_assessment.py` | 23 | Admits a monitor child's typed form: `episode_progress` references become received progress. Byte-identical to the parent's copy. | **BindingContext fields**: `episode_id`×3, `scope`×2; **imports from old `root.a102`**: `communication`, `domain`, `method_loop.durable` |
| `from_parent.py` | 43 | Admission of the parent's assignment: `owner_episode_id` plus `commission_id` or `commission_source_ref`; the parent must be the `hpc` episode that owns the commission; the commission must carry `yield_bindings` when required. | **BindingContext fields**: `assignment`, `episode_id`, `role`; **imports from old `root.a102`**: `communication`, `domain`, `execution_contracts`, `hpc_commission_sources`; **old-runner callbacks defined**: `assignment_schema`, `prepare_assignment` |
| `goal.py` | 10 | The goal text: balance expected credit against real elapsed time and resource demand; discover, propose candidates, compare, plan, commission launch, attach handoff, monitor, parse results; never fabricate, never duplicate a submission; the three parent credit components. | **old-runner callbacks defined**: `instructions` |
| `internal_summary.py` | 56 | Per-decision summary: commission, owner, candidates, resource, child scope and child commission to copy, launch deliveries, the launch report form and its own report form, current model and support, latest comparison, plans, latest monitor, monitor controllers, activity advice, queue refs, shared memory, available training ids. | **BindingContext fields**: `assignment`, `episode_id`, `run_id`, `scope`; **imports from old `root.a102`**: `communication`, `library.hpc_prediction`; **old-runner callbacks defined**: `decision_context`; **per-axis providers**: `self.memory`×2; **journal/receipt tables**: `runtime_episodes`, `runtime_report_attempts` |
| `measured_history.py` | 82 | The measured history used for fitting (one latest observation per closed allocation), import of shared timing history (queue timing pooled only for a matching queue; first 2000 rows), export of a closed allocation's measurement, tool `hpc.history.refresh`. | **imports from old `root.a102`**: `execution_guidance`, `hpc_history`, `library.hpc_resource_prediction`; **per-axis providers**: `self.memory`×5 |
| `portfolio_candidates.py` | 23 | Tool `hpc.candidate.propose`: retain a candidate portfolio; identities are immutable; validated together with the commission. | **imports from old `root.a102`**: `hpc_campaign` |
| `portfolio_comparison.py` | 44 | Candidate features, comparison of all candidates under a model and a queue observation ranked by net expected value, tool `hpc.compare`. | **BindingContext fields**: `episode_id`; **imports from old `root.a102`**: `hpc_queue`, `library.hpc_prediction` |
| `portfolio_planning.py` | 38 | Tool `hpc.plan`: requires a fresh queue observation, an enabled started execution queue and candidate limits within queue rules; builds the plan, freezes its prediction, reference prediction and forecast. | **imports from old `root.a102`**: `hpc_campaign`, `hpc_queue`, `library.hpc_prediction` |
| `portfolio_state.py` | 38 | Opens the owner's ledger (scope and commission must equal the owner's) and initialises the reference model, optionally fitting from shared history. | **BindingContext fields**: `assignment`×4, `role`, `scope`×2; **imports from old `root.a102`**: `communication`, `domain`, `hpc_ledger`, `hpc_queue`, `library.hpc_prediction`; **old-runner callbacks defined**: `initialize`; **per-axis providers**: `self.memory`; **old support classes**: `HPCLedger`×2 |
| `queue_observations.py` | 35 | Queue observation with shared-memory caching within `queue_max_age_seconds`, the freshness check before planning, tool `hpc.queue.observe`. | **imports from old `root.a102`**: `execution_guidance`, `hpc_queue`; **per-axis providers**: `self.memory`×4 |
| `received_evidence.py` | 60 | What it knows (received record refs plus the caller's selection), resolution of `episode.hpc_result` sources, tool `hpc.read`. | **BindingContext fields**: `received_record_refs`, `scope`; **imports from old `root.a102`**: `communication`; **old-runner callbacks defined**: `resolve_received_reference`; **self.services**: `record_selection` |
| `report_delivery.py` | 25 | Closure: typed form built once from saved facts and last interpretation. Byte-identical to the parent's copy. | **imports from old `root.a102`**: `library.private_policy_call`, `library.report_fact_assembly`, `runtime`×2; **old-runner callbacks defined**: `finish`; **old runtime**: `form_with_facts`, `_json`×2, `json`, `Record`×2; **self.workflow**: `binding_context`, `episode_bindings`, `facts`, `journal`×2, `pending_handles`, `release`×2, `source_credit_view`; **journal/receipt tables**: `runtime_forms`×2 |
| `resource_discovery.py` | 30 | Tool `hpc.discovery.run`: one lightweight remote command over the established SSH transport from the project directory, cached in shared memory. Contains a 90-second subprocess timeout and output truncation. | **imports from old `root.a102`**: `execution_guidance`, `hpc_queue`; **per-axis providers**: `self.memory`×4 |
| `task.py` | 186 | The decision loop; report grain name `hpc_execution`; attaches the HPC handoff return-contract validator. No reasoning-commit action. | **imports from old `root.a102`**: `episode_source_failure`, `library.action_contracts`, `library.hpc_handoff_report_contract`, `library.private_policy_call`, `providers`, `runtime`×2; **old binding attributes**: `hpc_handoff_report_validator`; **old-runner callbacks defined**: `apply_response`, `execute`, `next`; **old runtime**: `ActionFailure`, `ContractInformationError`, `_decode_recorded_action_response`, `Draft202012Validator`×2, `EventTargetError`×2, `inspect`, `_json`×5, `json`×8, `nullcontext`×5, `observes_action_outcome`, `ReportBoundaryError`, `ReportRedelivery`×2, `schema_failure_diagnostic`, `SourceEnd`×2, `validate_form`, `ValidationError`×2, `_wait_target_feedback`×2, `WorkflowError`×2; **self.workflow**: `action_schema`, `completed_unit`×3, `completions`×3, `controller_value`×2, `decision_exchanges`×3, `delivery_resolution_inputs`, `execute`, `execution_binding`×7, `inprocess_replay`×4, `journal`×7, `last_observed_credit`, `next_return`, `pending_work`, `perform_selected_wait`, `receive_native_outcome`, `receive_outcome`, `resolve_pending_deliveries`, `resolver`, `run_id`×2, `selected`×3, `source_credit_view`, `store`×7, `validate_report`; **journal/receipt tables**: `runtime_actions`×8, `runtime_episodes`, `runtime_model_calls`×2 |
| `task_decision.py` | 289 | The model call and exchange. Byte-identical to the parent's copy. | **imports from old `root.a102`**: `runtime`×2; **old binding attributes**: `instruction_composer`; **old-runner callbacks defined**: `call`, `complete_decision`, `conversation_key`, `exchange_decision`, `exchange_response`, `exchange_schema`, `instructions`, `interpretation_context`, `validate_contract_exchange_history`, `validate_contract_exchange_request`; **old provider interface**: `complete_with_presentation`, `has_session`×3, `prompt_renderer`; **old runtime**: `_action_generation_schema`×2, `apply_state_frame`, `_ASSIGNMENT_TRANSPORT`, `_category_yield_parameters`, `child_option_information`, `composition_lookup_schema`×2, `CONTRACT_INFORMATION_OPERATIONS`, `DECISION_CONTEXT_VERSION`×2, `DECISION_EXCHANGE_PROTOCOL`×5, `_digest`, `Draft202012Validator`, `instructional_model_context`×4, `is_contract_information`, `_json`×14, `json`×3, `lookup_attempts`, `Mapping`×2, `model_snapshot`×2, `_object`×3, `_plain`×2, `_recorded_action_generation_schema`, `_recorded_assignment_transport`, `_references_in`, `requested_contract_information`×2, `schema_failure_diagnostic`×2, `sqlite3`, `state_frame`, `ValidationError`×5, `WorkflowError`×14, `yield_table`; **self.workflow**: `contract_information_profile`, `contract_information_reply`, `controller_binding`, `decision_exchanges`×4, `decision_protocol`×3, `execute`, `freeze_contract_information`, `history_preview`, `journal`×3, `numerical_contracts`, `provider`×3, `receipts`×4, `run_id`, `services`×2, `specialist`, `store`×2, `uses_received_record_context`×2, `validate_contract_information`×5; **journal/receipt tables**: `runtime_model_calls`×8; **old yield names**: `_category_yield_parameters`×2, `yield_table`×2 |
| `task_instructions.py` | 14 | Instruction text: goal, tool knowledge, launch instructions, report-repair, wait and native-event guidance. Byte-identical to the parent's copy. | **old-runner callbacks defined**: `instructions`; **self.workflow**: `binding_context`, `knowledge`, `launch_instructions`, `native_event_information`, `permits_common_action`×2, `specialist` |
| `task_state.py` | 108 | Per-episode decision state and restore/checkpoint; only a failed tool action is recorded as a failed outcome. Byte-identical to the parent's copy. | **imports from old `root.a102`**: `episode_source_failure`, `runtime`×2; **old-runner callbacks defined**: `bind_execution_context`, `checkpoint`, `record_effect`, `record_execution_failure`, `restore`, `restore_checkpoint`; **old runtime**: `ActionLeaf`, `EFFECT_VERSION`, `Episode`, `interpretation_schema`, `_json`×2, `json`×4, `_object`, `_plain`, `Record`; **self.workflow**: `archive`, `completions`×4, `context`, `controller_value`, `execution_binding`×4, `grains`, `inprocess_replay`×7, `journal`×5, `progress_provider`×2, `recover_commissions`, `run_id`, `source_credit_view`, `store`×2; **journal/receipt tables**: `runtime_actions`×5 |
| `task_waiting.py` | 9 | Records the suspension condition and passes it to the external executor. Byte-identical to the parent's copy. | **old-runner callbacks defined**: `suspension_changed`; **self.workflow**: `execution_backend`, `execution_handle`×2 |
| `to_child_execution_job_submission.py` | 67 | Only the exact planned launch may use the allocation slot (one reservation per plan, none after closure); and what a launch child is given at its first decision: plan id, objective, frozen scientific manifest, acceptance, the supplied input file and the instruction not to prescribe a procedure. | **BindingContext fields**: `assignment`×2, `episode_id`, `path`×2, `role`×3, `run_id`×3, `scope`×2; **imports from old `root.a102`**: `communication`, `hpc_ledger`, `hpc_queue`, `method_loop.identities`, `practical_execution_state`; **old-runner callbacks defined**: `initial_decision_context`; **old support classes**: `HPCLedger`×3 |
| `to_child_execution_progress_assessment.py` | 12 | A monitor child receives the selected target, known observations, requested fields and permitted record types unchanged. Byte-identical to the parent's copy; imports the nested monitor folder's contracts. | **imports from old `root.a102`**: `communication`, `domain` |
| `to_parent.py` | 41 | The four report facts (`hpc_credit`, `hpc_model_ref`, `hpc_accepted_obligations`, `hpc_result_refs`), `hpc_model` reference resolution, and the rule that the report must agree with recorded evidence. | **imports from old `root.a102`**: `communication`, `episode_bindings`; **old-runner callbacks defined**: `facts`, `fact_sources`, `resolve`, `validate_report` |
| `waiting.py` | 50 | Activity advice from the last controller observation (wait or collect, with the suggested tool) and tool `hpc.monitor.wait`: reserve a forecast-valued schedule, wait, then observe the original job exactly once. | **BindingContext fields**: `episode_id`, `run_id`; **imports from old `root.a102`**: `hpc_monitoring`; **old-runner callbacks defined**: `activity_advice`; **old support classes**: `MonitorCronController`×2; **journal/receipt tables**: `runtime_observations` |
| `work_operations.py` | 54 | The tool list with descriptions and schemas, and the dispatcher: cached by operation key, intent recorded before execution. | **BindingContext fields**: `episode_id`; **imports from old `root.a102`**: `communication`, `domain`, `execution_contracts`; **old-runner callbacks defined**: `catalog`, `execute`; **per-axis providers**: `self.memory` |
| `yield_estimator.py` | 101 | Continuation: the commission's `yield_bindings[hpc_execution]` (cutoff, parameters) with the HPC continuation estimator carrying the cutoff as continuation cost; and the continuation packet computed after each action (remaining obligations, pending expected credit per allocation, pending action collect, active credit ceiling, active history indices, zero credit for waiting). | **BindingContext fields**: `assignment`, `episode_id`×3, `role`×5, `run_id`×3, `scope`; **imports from old `root.a102`**: `hpc_monitoring`, `library.hpc_continuation`, `library.hpc_prediction`, `numerical`; **old-runner callbacks defined**: `continuation_for_action`, `practical_estimator`, `yield_controller`; **journal/receipt tables**: `runtime_actions`×2, `runtime_observations`; **old yield names**: `HPCContinuationEstimator`×2, `YieldController`×2, `YieldParameters`×2 |
