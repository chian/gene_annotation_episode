# a103/gene_context_evidence/hpc_work_planning/hpc_resource_prediction — episode intent

Source: this episode's own files at commit `97308b94c`, folder
`gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/hpc_work_planning/hpc_resource_prediction/`
(25 files directly in the folder; no `grading/` or `scoring/` subfolder). The `tests/` subfolder
(`test_calculation_connections.py`, `test_prediction_behavior.py`, `test_prediction_prompt.py`,
`test_prediction_task.py`) exists but was not read. Nothing from the old shared root was read.

Old binding: class `HPCEpisode`, `binding_path = 'gene_context_evidence/hpc_work_planning/hpc_resource_prediction'`,
`commissioning_parent = 'gene_context_evidence/hpc_work_planning'`, role `hpc_prediction`, no entry roles,
record version `hpc_episode_v1`, `replaces_default_instructions = True`. Decision source:
`ResourcePredictionTask`. Prompt renderer: `render_hpc_prompt`.

## What this episode is for

It forecasts the time and resource use of HPC allocations and compares portfolios before execution. Its
own words (`goal.py`):

> Iterate on a generalized time/resource model using measured historical cases. Refresh shared history,
> inspect support and held-out quality, fit a disjoint training selection, and compare useful portfolios.
> Inspect missing capacity, launcher and queue facts with lightweight discovery; propose executable
> resource alternatives when the parent has not supplied them. Preparation and submission belong to the
> execution sister. Forecast CPU time and memory demand as well as queue, setup and work time. Compare
> node/worker counts, memory capacity, workload parameters and elapsed cost. The paired execution episode
> owns Launch, monitoring and parsing. Both sisters use this parent-owned ledger; preserve model and
> comparison identities for that sibling. The fixed reference and validation set cannot change. Model
> credit is modest measured improvement; the HPC parent later scores frozen predictions against real
> outcomes. Unknown inputs stay unknown. Return when further model improvement is less useful than running
> the next worthwhile portfolio.

## Task and instructions

- One unit is one tool action. The only permitted common action is `tool` (`episode.py`): no reason, no
  wait, no child, no redelivery.
- Instructions (`task_instructions.py`): only the goal text above (it replaces the default
  instructions), plus tool knowledge and the launch instruction library when they are in context.

## What it reads from its parent's assignment

`from_parent.py`: `{owner_episode_id: text, commission_id: one of the configured commissions | commission_source_ref: reference}`.
Exactly one of the two commission fields is required when commissions are configured, otherwise
`commission_source_ref`. The parent must have role `hpc`, `owner_episode_id` must equal the parent's
episode id, and the commission identity must equal the parent's own assignment
(`prediction_or_execution_must_belong_to_its_original_hpc_parent`). With private yield on, the commission
must carry `yield_bindings` (`hpc_commission_yield_binding_required:<role>`). A `commission_source_ref`
commission is read with `hpc_commission_sources.read` (old shared root).

The commission supplies: `history`, `validation_ids`, `model` (spec and features), `candidates`,
`obligations`, `preferences`, `credit.model_scale`, `limits.queue_max_age_seconds`, `resource_id`,
optional `execution_profile`, and `yield_bindings`.

## Children

None (`child_roles` returns `()`). Its sister is the execution episode (`hpc_allocation_execution`). Both
read and write the parent-owned `HPCLedger`, which `prediction_state.py` opens at
`<directory>/hpc/<digest(run_id, owner_episode_id)>`. The scope and commission identity must equal the
ledger owner's.

## Decision state and what it shows the model

State (`task_state.py`): the same source state as the other tasks. A failure is recorded and enters the
iterator only for `tool` actions.

Model inputs (`decision_state.py`): goal, scope, working state, visible refs, credit, evidence vector,
credit binding, controller state, last outcome, feedback, child reports (none), and available report
facts. There is no annotation-axis mode and no annotation context.

The binding's own block (`internal_summary.py`; on first use it initializes the ledger): `hpc_commission`,
`hpc_owner_episode_id`, `hpc_candidates`, `hpc_resource`, `hpc_tool_request`, `hpc_model_ref`,
`hpc_credit`, `hpc_latest_comparison` (without episode id or operation key), `hpc_model_support`,
`hpc_report_form` (closed form `hpc_credit, hpc_model_ref, hpc_result_refs`), `hpc_plans`,
`hpc_latest_monitor`, `hpc_monitor_controllers`, `hpc_queue_refs`, `hpc_shared_memory` and
`hpc_shared_history_refs` (with memory), and `hpc_available_training_ids` (history minus validation).

Added before each decision (`decision_inputs.py`): resource context, the launch instruction library and
selected instructions, initial binding context, completed action reports, requested action history (HPC
context), pending work, execution expectations for grain `hpc_prediction`, resource and native estimates,
native event targets, and the profile. Unlike the literature episodes it has no shared-information
context and no child options.

## Tools it offers

`prediction_operations.py`. Each tool is idempotent per operation key through the ledger
(`cached`/`save_action`):

| Tool | Meaning (own words) | Operands |
|---|---|---|
| `hpc.read` | Read retained HPC evidence by its exact identity. | `reference` |
| `hpc.compare` | Compare all approved portfolios; no work is selected or launched. | `model_ref`, `queue_ref` |
| `hpc.history.refresh` (only with shared memory) | Read age-weighted shared timing history once. No remote discovery, polling credit, or new scientific work. | none |
| `hpc.discovery.run` | Run one lightweight remote inspection or documentation retrieval through the established SSH transport. No job submission, installation or scientific computation. | `command` (run as `cd /lus/flare/projects/BioReason-Aurora-Test && <command>` via the resource's `ssh_argv`) |
| `hpc.candidate.propose` | Retain an executable portfolio selected by this episode (candidate JSON: id, queue, nodes, wall_seconds, features, optional resource_capacity, units ...). Candidate identity is immutable; the commission is revalidated with it. | `candidate_json` |
| `hpc.queue.observe` | Acquire PBS queue and ALCF score/status once and transform them. | none |
| `hpc.model.fit` | Fit selected measured history; validate on the fixed disjoint cases. Training ids must be non-validation cases, and historical training must precede temporal validation. | `training_ids` |

Old limits in `hpc.discovery.run` that must not be carried over: `subprocess.run(..., timeout=90)` is an
elapsed-time cutoff, and stdout/stderr are truncated to 65536/8192 bytes. `prediction_history._shared_history`
also caps imported observations at `[:2000]`, which is a count cutoff. Queue freshness
(`limits.queue_max_age_seconds`) is a data-freshness rule taken from the commission, not a runtime limit.

## How its credit is counted

Credit kind `operational` (`credit.py`):

`credit = commission.credit.model_scale × (Q(current model) − Q(model at entry)) + Σ validation contributions of predictions made by this episode`

Here Q is `prediction.quality` on the fixed `validation_ids` cases. It is `None` when the model trained on
cases outside the commission history, in which case the gain is 0. The entry quality is saved once per
episode (`model_entry`). Actual job credit is not counted here (`actual_job_credit_counted_here: False`).
`hpc.model.fit` also records `ledger.model_credit(model_ref, quality − baseline)`, or 0 when quality is
unknown. The credit is unbounded and signed ("Signed measured credit; repeated polling adds none").

## Continuation

`yield_estimator.py`: with private yield required (`require_commission_yield`), the commission's
`yield_bindings['hpc_prediction']` supplies `cutoff` and `parameters`. The old controller is
`YieldController` (accumulation) with `estimate_with_context = HPCContinuationEstimator(verify).with_continuation_cost(cutoff)`.
`continuation_for_action` writes a ledger `continuation` packet with zero expected continuation credit.
It does so when there are no validation ids, every available case is already in the current model's
training set, candidates exist and all were compared against the current model, and the latest queue
observation is fresh. Its reason is `prediction_ready_without_new_measured_improvement_opportunities`,
and the code comment says "This bounds available action value, not action count." Today this maps to
the accumulation estimator with the commission's cutoff and parameters. The zero-forecast packet is this
episode's own evidence for that estimator.

## What it reports to its parent

`to_parent.py` fact sources:

- `hpc_credit`: signed measured credit.
- `hpc_model_ref`: the selected model, namespace `hpc_model`.
- `hpc_accepted_obligations`: actual-kind contribution slots.
- `hpc_result_refs`: ledger result Sources that this episode knows.

Every report field that names one of these sources must equal the recorded fact
(`hpc_report_disagrees_with_recorded_evidence`). `closed_models.py` lets the parent check a closed
`hpc_model_ref` read-only afterwards. `report_delivery.py` saves the form once.

## Differences from similar episodes

- Tool-only and childless, with operational credit. It has a private accumulation yield binding taken
  from the commission, and it replaces the default instructions.
- Its sister `hpc_allocation_execution` shares the same ledger and commission (the same assignment
  shape is enforced by "prediction_or_execution_must_belong_to_its_original_hpc_parent").
- Its `task_decision.py` merges the literature episodes' `call.py` and `decision_*` files into one class.
  It has no child options lookup, no literature numerical contracts, and no annotation-axis yield table.

## Files

Names: `self.workflow.<m>` = old runner member; `runtime.<x>` = `_live_original_runtime.<x>` (old `root.a103.runtime`); `import:root.a103.<m>` = import from the old shared root; `table:<t>` = old journal/receipt table; `yield:<n>` = old yield name; `BindingContext.<f>` = old binding-context field; `services.<m>` = old binding services callback. Every row is also in `runs/carry_over/calls/a103_06.tsv`.

| Old file | Lines | This episode's own intent | Old-runner names (uses) |
|---|---|---|---|
| `binding_record.py` | 12 | binding record `hpc_episode_v1` with resources, commissions, shared memory, yield requirement | none |
| `closed_models.py` | 29 | validates a closed `hpc_model_ref` read-only from the saved form and the ledger sqlite | `BindingContext.assignment`×1, `BindingContext.episode_id`×1, `BindingContext.role`×1, `BindingContext.run_id`×2, `BindingContext.scope`×1, `import:root.a103.communication`×1, `import:root.a103.episode_return_records`×1, `import:root.a103.hpc_queue`×1, `table:runtime_forms`×1 |
| `configuration.py` | 30 | settings: `store`, `run_id`, `directory`, `resources` (needs a `pbs_ssh` one), validated `commissions`, optional `shared_execution_memory`, `require_commission_yield` | `import:root.a103.communication`×1, `import:root.a103.execution_memory`×1, `import:root.a103.hpc_campaign`×1 |
| `credit.py` | 31 | credit kind `operational`; credit = `model_scale` × (current held-out quality − quality at entry) + prospective validation credit from this episode's predictions; actual job credit not counted here | `BindingContext.episode_id`×2, `import:root.a103.library`×1 |
| `decision_inputs.py` | 57 | context additions as the literature episodes but no shared information/child options; execution expectations grain `hpc_prediction` | `import:root.a103.episode_work_report`×2, `import:root.a103.library.hpc_prompt`×1, `self.workflow.binding_context`×2, `self.workflow.episode_bindings`×1, `self.workflow.execution_expectations`×1, `self.workflow.job_episodes`×2, `self.workflow.launch_instructions`×2, `self.workflow.native_estimation_context`×1, `self.workflow.native_event_information`×2, `self.workflow.pending_work`×1, `self.workflow.resource_context`×1, `self.workflow.resource_estimator`×4, `self.workflow.store`×2 |
| `decision_state.py` | 31 | model inputs (no annotation-axis mode; no annotation context): goal, scope, working state, visible refs, credit, evidence vector, controller state, binding block, available report facts | `import:root.a103.runtime`×2, `runtime.FACT_MEANINGS`×1, `runtime.FACT_SOURCES`×1, `runtime.json`×1, `runtime.Mapping`×2, `runtime._plain`×2, `runtime._references_in`×1, `self.workflow.binding_context`×1, `self.workflow.catalog`×1, `self.workflow.controller_binding`×1, `self.workflow.delivery_status`×1, `self.workflow.extra_report_sources`×1, `self.workflow.job_episode_options`×1, `self.workflow.journal`×2, `self.workflow.knowledge`×1, `self.workflow.local_outcome_preview`×1, `self.workflow.pending_work`×1, `self.workflow.receipt_projection`×1, `self.workflow.run_id`×1, `self.workflow.source_credit_binding`×1, `self.workflow.source_credit_view`×1, `self.workflow.specialist`×1, `self.workflow.store`×3, `self.workflow.store.reference_subset`×1, `self.workflow.tools`×1, `self.workflow.tools.model_contract_catalog`×1, `self.workflow.working_state`×1, `table:runtime_actions`×1 |
| `episode.py` | 38 | `HPCEpisode` composed from the mixins; role `hpc_prediction`, `commissioning_parent='gene_context_evidence/hpc_work_planning'`, `replaces_default_instructions=True`, no children, common actions `tool` only, HPC prompt renderer | `import:root.a103.library.hpc_prompt`×1 |
| `from_parent.py` | 44 | assignment {`owner_episode_id`, one of `commission_id` (enum of configured commissions) or `commission_source_ref`}; parent must be the `hpc` role with the same episode id and commission identity; yield binding required in the commission when private yield is on | `import:root.a103.communication`×1, `import:root.a103.domain`×1, `import:root.a103.execution_contracts`×1, `import:root.a103.hpc_commission_sources`×1 |
| `goal.py` | 20 | the prediction goal text (generalized time/resource model from measured history; sister execution episode owns launch/monitor/parse; fixed reference and validation set; modest measured improvement credit; return when running the next portfolio is more useful) | none |
| `__init__.py` | 0 | empty package marker | none |
| `internal_summary.py` | 36 | model block: commission, owner, candidates, resource, tool requests, current model, credit, latest comparison, model support, report form, plans, latest monitor, monitor controllers, queue refs, shared memory/history refs, available training ids | `import:root.a103.library`×1 |
| `portfolio_comparison.py` | 31 | candidates (commission + proposed); features; comparison of every candidate with the current model and queue, sorted by net expected value | `import:root.a103.hpc_queue`×1, `import:root.a103.library`×1 |
| `prediction_history.py` | 63 | training history: commission history + latest shared snapshot (dedup by physical attempt) + one latest measured observation per closed allocation; shared-history query by execution profile and queue pooling rule | `import:root.a103.execution_guidance`×1, `import:root.a103.library.hpc_resource_prediction`×1 |
| `prediction_operations.py` | 147 | tools `hpc.read`, `hpc.compare`, `hpc.history.refresh` (with memory), `hpc.discovery.run`, `hpc.candidate.propose`, `hpc.queue.observe`, `hpc.model.fit`; idempotent per operation key in the ledger | `BindingContext.episode_id`×3, `import:root.a103.communication`×1, `import:root.a103.domain`×1, `import:root.a103.execution_contracts`×1, `import:root.a103.execution_guidance`×1, `import:root.a103.hpc_campaign`×1, `import:root.a103.hpc_queue`×1, `import:root.a103.library`×1 |
| `prediction_state.py` | 43 | opens the parent-owned `HPCLedger` (`directory/hpc/<digest(run, owner)>`), checks scope/commission identity; `initialize` writes the reference model, imports shared history (fits an initial model) and the entry quality | `BindingContext.assignment`×4, `BindingContext.episode_id`×1, `BindingContext.role`×1, `BindingContext.scope`×2, `import:root.a103.communication`×1, `import:root.a103.domain`×1, `import:root.a103.hpc_ledger`×1, `import:root.a103.hpc_queue`×1, `import:root.a103.library`×1 |
| `queue_observations.py` | 27 | queue observation via shared memory cache (fresh within `queue_max_age_seconds`) or `hpc_queue.observe`; `_queue` with optional freshness requirement | `import:root.a103.execution_guidance`×1, `import:root.a103.hpc_queue`×1 |
| `received_evidence.py` | 51 | `_known` refs; resolves an `episode.hpc_result` Source only if received, same run and scope; `read_evidence` reads history, ledger records or an owned result Source with receipt match | `BindingContext.received_record_refs`×1, `BindingContext.scope`×1, `import:root.a103.communication`×1, `services.record_selection`×1 |
| `report_delivery.py` | 25 | finish: form from report values + assembled facts, saved once | `import:root.a103.library.private_policy_call`×1, `import:root.a103.library.report_fact_assembly`×1, `import:root.a103.runtime`×2, `runtime.form_with_facts`×1, `runtime._json`×2, `runtime.json`×1, `runtime.Record`×2, `self.workflow.binding_context`×1, `self.workflow.episode_bindings`×1, `self.workflow.facts`×1, `self.workflow.journal`×2, `self.workflow.pending_handles`×1, `self.workflow.release`×2, `self.workflow.source_credit_view`×1, `table:runtime_forms`×2 |
| `task_decision.py` | 288 | call + exchange decision (same text family as the literature `call.py`/`decision_*` files, without child options and literature numerical contracts) | `import:root.a103.runtime`×2, `runtime._action_generation_schema`×2, `runtime.apply_state_frame`×1, `runtime._ASSIGNMENT_TRANSPORT`×1, `runtime._category_yield_parameters`×1, `runtime.composition_lookup_schema`×2, `runtime.CONTRACT_INFORMATION_OPERATIONS`×1, `runtime.DECISION_CONTEXT_VERSION`×2, `runtime.DECISION_EXCHANGE_PROTOCOL`×5, `runtime._digest`×1, `runtime.Draft202012Validator`×1, `runtime.instructional_model_context`×4, `runtime.is_contract_information`×1, `runtime._json`×14, `runtime.json`×3, `runtime.lookup_attempts`×1, `runtime.Mapping`×2, `runtime.model_snapshot`×2, `runtime._object`×3, `runtime._plain`×2, `runtime._recorded_action_generation_schema`×1, `runtime._recorded_assignment_transport`×1, `runtime._references_in`×1, `runtime.requested_contract_information`×2, `runtime.schema_failure_diagnostic`×2, `runtime.sqlite3`×1, `runtime.state_frame`×1, `runtime.ValidationError`×5, `runtime.WorkflowError`×14, `runtime.yield_table`×1, `self.workflow.contract_information_profile`×1, `self.workflow.contract_information_reply`×1, `self.workflow.controller_binding`×1, `self.workflow.decision_exchanges`×4, `self.workflow.decision_protocol`×3, `self.workflow.execute`×1, `self.workflow.freeze_contract_information`×1, `self.workflow.history_preview`×1, `self.workflow.journal`×3, `self.workflow.numerical_contracts`×1, `self.workflow.provider`×3, `self.workflow.provider.conversation_key`×1, `self.workflow.provider.has_session`×1, `self.workflow.receipts`×4, `self.workflow.run_id`×1, `self.workflow.services`×2, `self.workflow.specialist`×1, `self.workflow.store`×2, `self.workflow.store.reference_subset`×1, `self.workflow.uses_received_record_context`×2, `self.workflow.validate_contract_information`×5, `table:runtime_model_calls`×8 |
| `task_instructions.py` | 11 | instructions = binding goal only (replaces the default), plus tool knowledge and launch library when present | `self.workflow.binding_context`×1, `self.workflow.knowledge`×1, `self.workflow.launch_instructions`×1, `self.workflow.specialist`×1 |
| `task.py` | 150 | decision loop like the literature task but tool-only (no reason/wait/redelivery), report grain `hpc_prediction` | `import:root.a103.episode_source_failure`×1, `import:root.a103.library.action_contracts`×1, `import:root.a103.library.private_policy_call`×1, `import:root.a103.providers`×1, `import:root.a103.runtime`×2, `runtime.ActionFailure`×1, `runtime.ContractInformationError`×1, `runtime._decode_recorded_action_response`×1, `runtime.Draft202012Validator`×1, `runtime.EventTargetError`×1, `runtime.inspect`×1, `runtime._json`×5, `runtime.json`×8, `runtime.nullcontext`×5, `runtime.observes_action_outcome`×1, `runtime.ReportBoundaryError`×1, `runtime.schema_failure_diagnostic`×1, `runtime.SourceEnd`×2, `runtime.validate_form`×1, `runtime.ValidationError`×2, `runtime._wait_target_feedback`×1, `runtime.WorkflowError`×1, `self.workflow.action_schema`×1, `self.workflow.completed_unit`×1, `self.workflow.completions`×2, `self.workflow.controller_value`×2, `self.workflow.decision_exchanges`×3, `self.workflow.execute`×1, `self.workflow.execution_binding`×7, `self.workflow.inprocess_replay`×4, `self.workflow.journal`×7, `self.workflow.pending_work`×1, `self.workflow.receive_native_outcome`×1, `self.workflow.receive_outcome`×1, `self.workflow.resolver`×1, `self.workflow.run_id`×2, `self.workflow.selected`×3, `self.workflow.source_credit_view`×1, `self.workflow.store`×7, `self.workflow.validate_report`×1, `table:runtime_actions`×8, `table:runtime_episodes`×1, `table:runtime_model_calls`×2 |
| `task_state.py` | 108 | source state; failure recording that enters the iterator only for `tool` | `import:root.a103.episode_source_failure`×1, `import:root.a103.runtime`×2, `runtime.ActionLeaf`×1, `runtime.EFFECT_VERSION`×1, `runtime.Episode`×1, `runtime.interpretation_schema`×1, `runtime._json`×2, `runtime.json`×4, `runtime._object`×1, `runtime._plain`×1, `runtime.Record`×1, `self.workflow.archive`×1, `self.workflow.completions`×4, `self.workflow.context`×1, `self.workflow.controller_value`×1, `self.workflow.execution_binding`×4, `self.workflow.grains`×1, `self.workflow.inprocess_replay`×7, `self.workflow.journal`×5, `self.workflow.progress_provider`×2, `self.workflow.recover_commissions`×1, `self.workflow.run_id`×1, `self.workflow.source_credit_view`×1, `self.workflow.store`×2, `table:runtime_actions`×5 |
| `to_parent.py` | 40 | fact sources `hpc_credit`, `hpc_model_ref`, `hpc_accepted_obligations`, `hpc_result_refs`; report fields with those sources must equal the recorded facts; `hpc_model` namespace resolves ledger models | `import:root.a103.communication`×1, `import:root.a103.episode_bindings`×1 |
| `waiting.py` | 9 | `PredictionSuspension`: records suspension on the execution handle | `self.workflow.execution_backend`×1, `self.workflow.execution_handle`×2 |
| `yield_estimator.py` | 60 | `YieldController` with the commission's `yield_bindings[role]` cutoff/parameters and an `HPCContinuationEstimator` (with continuation cost = cutoff); `continuation_for_action` writes a zero-expected-continuation packet when no held-out cases, everything trained, all candidates compared and the queue observation is fresh | `BindingContext.assignment`×1, `BindingContext.episode_id`×2, `BindingContext.role`×5, `BindingContext.run_id`×1, `BindingContext.scope`×1, `import:root.a103.library.hpc_continuation`×1, `import:root.a103.numerical`×1, `yield:HPCContinuationEstimator`×2, `yield:YieldController`×2, `yield:YieldParameters`×2 |

## Carried over

One row per old function of the episode folder at `97308b94c` (`runs/carry_over/functions/`). New places are in `gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/hpc_work_planning/hpc_resource_prediction/`. Rows marked "library candidate" stay in the episode file that uses them. Items that wait on the system are in `carry_over_blocked/a103__gene_context_evidence__hpc_work_planning__hpc_resource_prediction.md`.

| old file | old kind | name | classification | new place or reason |
|---|---|---|---|---|
| binding_record.py | class | PredictionBindingRecord | machinery | the binding's own record class (README 3e: binding_record.py) |
| binding_record.py | method | PredictionBindingRecord.as_record | machinery | the binding's own as_record(): deleted; the settings are recorded by the system |
| closed_models.py | class | ClosedModels | episode function (not placed) | reads runtime_forms and the closed ledger file; see unplaced_old_functions |
| closed_models.py | method | ClosedModels.frozen_reference | episode function (not placed) | the parent's later read-only check of a closed hpc_model_ref over runtime_forms, EpisodeReturnRecords and the ledger sqlite: needs the hpc_ledger custody (BLOCKED-ON-JOB-SERVICE); the system admits the result and the parent holds what is returned |
| configuration.py | class | PredictionConfiguration | episode function | values become the episode's settings (`resources`, `commissions`, `shared_execution_memory`, directories of the launch and knowledge libraries); `store`, `run_id`, `services` are the system's |
| configuration.py | method | PredictionConfiguration.__init__ | episode function | task.py reads `ctx.settings['resources']`; yield_estimator.py reads `settings['commissions']`; `shared_execution_memory` is the `estimate_table` service plus its settings flag; `require_commission_yield` is always required in yield_estimator.py; the construction-time validations (explicit commissions, a pbs_ssh resource, boolean flag) are not carried: settings are the caller's |
| credit.py | class | HPCEpisodeCredit | episode function | credit.py credit and model_quality_improvement; task.py credit_inputs |
| credit.py | method | HPCEpisodeCredit.credit_kind | machinery | credit_kind deleted (README 3d) |
| credit.py | method | HPCEpisodeCredit._quality | episode function | task.py quality |
| credit.py | method | HPCEpisodeCredit.credit_view | episode function | credit.py credit(summary, records) over task.py credit_inputs (read from the ledger by the tool); messages/internal_summary.py hpc_credit (improvement, validation credit, actual_job_credit_counted_here) |
| decision_inputs.py | class | PredictionDecisionInputs | episode function | task.py decide |
| decision_inputs.py | method | PredictionDecisionInputs.decision_inputs | episode function | task.py decide: launch instruction library and selected instructions (from read_from_parent), execution expectations through the estimate_table read handle (BLOCKED-ON-JOB-SERVICE); resource context is hpc_resource from settings. Not carried: completed_action_reports and pending_work (old runner), resource_tool_estimates and native_* contexts (workflow collaborators, see unplaced_old_functions) |
| decision_state.py | class | PredictionDecisionState | episode function | messages/internal_summary.py and task.py decide |
| decision_state.py | method | PredictionDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary (credit, controller state, last outcome, feedback, own action history) and task.py decide (goal, tools, tool knowledge, instruction libraries, time); the old runner's visible refs, visual evidence, report lifecycle, report deliveries and report_update are machinery |
| episode.py | class | HPCEpisode | episode function | episode.py HpcResourcePrediction |
| episode.py | method | HPCEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} |
| episode.py | method | HPCEpisode.allowed_children | machinery | child lookup of the old registry (README 3b C1, C2) |
| episode.py | method | HPCEpisode.permitted_common_actions | machinery | common actions of the old action schema: the task offers tool units only (README 3a) |
| from_parent.py | class | PredictionAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | method | PredictionAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (oneOf kept as the raise in read_from_parent) |
| from_parent.py | method | PredictionAssignment.commission_identity | episode function | messages/read_from_parent.py read_from_parent (parent_input['commission_identity']) |
| from_parent.py | method | PredictionAssignment._commission | episode function | yield_estimator.py (the configured commission by id from settings); a commission_source_ref is read by hpc_commission_sources.read, absent for A103: see unplaced_old_functions |
| from_parent.py | method | PredictionAssignment.prepare_assignment | machinery | the child's check of its own commission (owner, role and identity must equal the parent's, yield binding present): deleted by the owner's rule 1; the yield binding is required in yield_estimator.py |
| goal.py | class | PredictionGoal | episode function | goal.py (GOAL, UNIT, RESULT) and task.py INSTRUCTIONS |
| goal.py | method | PredictionGoal.instructions | episode function | task.py INSTRUCTIONS (the goal text, one sentence added: the episode cannot end itself) |
| internal_summary.py | class | PredictionSummary | episode function | messages/internal_summary.py and task.py ledger_view |
| internal_summary.py | method | PredictionSummary.decision_context | episode function | task.py ledger_view (the ledger block, read by each tool) shown by decide; messages/internal_summary.py (commission, credit); the hpc_report_form block is report_form machinery (RETURN_FORM replaces it); initialization on first use is the tool hpc_initialize |
| portfolio_comparison.py | class | PortfolioComparison | episode function | task.py candidates, features, comparisons |
| portfolio_comparison.py | method | PortfolioComparison._candidates | episode function | task.py candidates (library candidate) |
| portfolio_comparison.py | method | PortfolioComparison._features | episode function | task.py features (library candidate) |
| portfolio_comparison.py | method | PortfolioComparison._comparisons | episode function | task.py comparisons (library candidate) |
| prediction_history.py | class | PredictionHistory | episode function | task.py history, shared_history |
| prediction_history.py | method | PredictionHistory._history | episode function | task.py history (library candidate) |
| prediction_history.py | method | PredictionHistory._shared_history | episode function | task.py shared_history (library candidate); the `[:2000]` count cutoff is not carried |
| prediction_operations.py | class | PredictionOperations | episode function | task.py TOOLS and catalog |
| prediction_operations.py | method | PredictionOperations.catalog | episode function | task.py catalog (names `hpc.x.y` became `hpc_x_y`) |
| prediction_operations.py | method | PredictionOperations.execute | episode function | task.py tools hpc_read, hpc_compare, hpc_history_refresh, hpc_discovery_run, hpc_candidate_propose, hpc_queue_observe, hpc_model_fit; the operation-key ledger (cached, save_action) is the system's attempts journal; the 90 s timeout and the output truncation of discovery are not carried |
| prediction_state.py | class | PredictionState | episode function | task.py open_ledger, initialize, current_model |
| prediction_state.py | method | PredictionState.state | episode function | task.py open_ledger (BLOCKED-ON-JOB-SERVICE: hpc_ledger); the scope and identity equality checks against the ledger owner are the child's check of its commission: not carried |
| prediction_state.py | method | PredictionState.initialize | episode function | task.py initialize, called by the tool hpc_initialize (the first unit) |
| prediction_state.py | method | PredictionState._current_model | episode function | task.py current_model (library candidate) |
| queue_observations.py | class | QueueObservations | episode function | task.py observe_queue, queue |
| queue_observations.py | method | QueueObservations._observe_queue | episode function | task.py observe_queue (the queue read goes through the job_access service, the cache through estimate_table) |
| queue_observations.py | method | QueueObservations._queue | episode function | task.py queue (library candidate) |
| received_evidence.py | class | ReceivedEvidence | episode function | task.py resolve_received_reference, read_evidence |
| received_evidence.py | method | ReceivedEvidence._known | machinery | known-reference set: custody (`ctx.store.holds`) |
| received_evidence.py | method | ReceivedEvidence.resolve_received_reference | episode function | task.py resolve_received_reference (held Source of provider episode.hpc_result of this run; the scope check is not carried: the assignment has no scope) |
| received_evidence.py | method | ReceivedEvidence.read_evidence | episode function | task.py read_evidence |
| report_delivery.py | class | PredictionReportDelivery | machinery | report delivery and release of the old runner (README 3b D1, D3) |
| report_delivery.py | method | PredictionReportDelivery.finish | machinery | form_with_facts, runtime_forms and release: the result is built by messages/final_to_parent.py |
| task.py | class | ResourcePredictionTask | episode function | task.py decide, action and tools |
| task.py | method | ResourcePredictionTask.next | machinery | the old decision loop, replay and source-end handling (README 3a, 3e) |
| task.py | method | ResourcePredictionTask.apply_response | episode function | task.py action (the validation of the model's answer against the tool schemas); report_update admission is report machinery |
| task.py | method | ResourcePredictionTask.execute | machinery | runtime_actions rows, journal.measure, controller_value and failure feedback: the system's unit, journal and controller input |
| task_decision.py | class | PredictionTaskDecision | machinery | the decision-exchange class (README 3a) |
| task_decision.py | method | PredictionTaskDecision.call | machinery | model call recording and the exchange (README 3a) |
| task_decision.py | method | PredictionTaskDecision.instructions | episode function | task.py _instructions |
| task_decision.py | method | PredictionTaskDecision.complete_decision | machinery | the provider call: decide returns a ModelRequest |
| task_decision.py | method | PredictionTaskDecision.conversation_key | machinery | conversation sessions (README 3a) |
| task_decision.py | method | PredictionTaskDecision.interpretation_context | machinery | exchange lookup results (README 3a) |
| task_decision.py | method | PredictionTaskDecision.exchange_schema | machinery | decision-exchange schema (README 3a) |
| task_decision.py | method | PredictionTaskDecision.exchange_response | machinery | decision-exchange response (README 3a) |
| task_decision.py | method | PredictionTaskDecision.validate_contract_exchange_request | machinery | saved-request check (README 3a) |
| task_decision.py | method | PredictionTaskDecision.validate_contract_exchange_history | machinery | saved-request check (README 3a) |
| task_decision.py | method | PredictionTaskDecision.exchange_decision | machinery | decision-exchange loop (README 3a) |
| task_instructions.py | function | instructions | episode function | task.py _instructions (goal text plus the tool knowledge and launch instruction constants) |
| task_state.py | class | PredictionTaskState | machinery | checkpoint and replay state (README 3a, 3e) |
| task_state.py | method | PredictionTaskState.__init__ | machinery | checkpoint and replay state |
| task_state.py | method | PredictionTaskState.bind_execution_context | machinery | execution binding of the old runner |
| task_state.py | method | PredictionTaskState.record_execution_failure | machinery | failure rows: a tool returns its failure as its outcome |
| task_state.py | method | PredictionTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | method | PredictionTaskState.restore | machinery | checkpoint/restore |
| task_state.py | method | PredictionTaskState.record_effect | machinery | record_effect (README 3a) |
| task_state.py | method | PredictionTaskState.checkpoint | machinery | checkpoint/restore |
| to_parent.py | class | PredictionReport | episode function | messages/final_to_parent.py |
| to_parent.py | method | PredictionReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (hpc_credit, hpc_model_ref, hpc_accepted_obligations, hpc_result_refs, selectable) |
| to_parent.py | method | PredictionReport.facts | episode function | messages/final_to_parent.py final_to_parent (hpc_credit is completion['credit']; the other facts come from the summary) |
| to_parent.py | method | PredictionReport.resolve | episode function | messages/final_to_parent.py validate_report (the hpc_model namespace is the ledger's model identities in the summary); the other namespaces were the old resolver |
| to_parent.py | method | PredictionReport.validate_report | episode function | messages/final_to_parent.py validate_report (equality with the recorded facts, hpc_report_disagrees_with_recorded_evidence); validate_form of the JSON-schema form is not carried: RETURN_FORM admits the result |
| waiting.py | class | PredictionSuspension | machinery | suspension on the execution handle (README 3b: wait/suspension machinery) |
| waiting.py | method | PredictionSuspension.suspension_changed | machinery | suspension on the execution handle |
| yield_estimator.py | class | HPCEpisodeYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | method | HPCEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (accumulation; the commission's cutoff is the cost) |
| yield_estimator.py | method | HPCEpisodeYield.continuation_for_action | machinery | estimator packet with a zero expected continuation (README 3d: estimator packets are deleted; only the controller stops the Episode) |
| yield_estimator.py | method | HPCEpisodeYield.practical_estimator | machinery | HPCContinuationEstimator (README 7b: deleted; accumulation is chosen) |
