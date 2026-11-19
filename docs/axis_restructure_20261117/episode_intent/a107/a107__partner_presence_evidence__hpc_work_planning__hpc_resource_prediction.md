# a107/partner_presence_evidence/hpc_work_planning/hpc_resource_prediction — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/hpc_resource_prediction/<file>`
(only files directly in this folder; it has a `tests/` folder, not covered here, and no `grading/`/`scoring/`
folder or child episodes).
Old binding class: `HPCEpisode` (`binding_path = 'partner_presence_evidence/hpc_work_planning/hpc_resource_prediction'`,
`commissioning_parent = 'partner_presence_evidence/hpc_work_planning'`, `roles = ('hpc_prediction',)`,
`entry_roles = ()`), decision source `ResourcePredictionTask`, prompt renderer library `render_hpc_prompt`,
contract version `hpc_episode_v1`.

## What it is for (its goal, in its own words)

`goal.py` (replaces the default instructions):

> Iterate on a generalized time/resource model using measured historical cases. Refresh shared history, inspect
> support and held-out quality, fit a disjoint training selection, and compare useful portfolios. Inspect missing
> capacity, launcher and queue facts with lightweight discovery; propose executable resource alternatives when the
> parent has not supplied them. Preparation and submission belong to the execution sister. Forecast CPU time and
> memory demand as well as queue, setup and work time. Compare node/worker counts, memory capacity, workload
> parameters and elapsed cost. The paired execution episode owns Launch, monitoring and parsing. Both sisters use
> this parent-owned ledger; preserve model and comparison identities for that sibling. The fixed reference and
> validation set cannot change. Model credit is modest measured improvement; the HPC parent later scores frozen
> predictions against real outcomes. Unknown inputs stay unknown. Return when further model improvement is less
> useful than running the next worthwhile portfolio.

## Task and instructions

`task_instructions.py`: the goal text + tool knowledge instructions + launch instruction library instructions; no
generic `INSTRUCTIONS`, no reasoning/wait/redelivery texts. Only the `tool` action is permitted.

## What it reads from its parent's assignment

`from_parent.py`: `owner_episode_id` (required) plus exactly one of `commission_id` (enum of the configured
commissions) or `commission_source_ref` (read through `hpc_commission_sources.read`). `prepare_assignment` requires
the parent role `hpc`, `owner_episode_id == parent.episode_id`, the same commission identity as the parent's
assignment, and a commission `yield_bindings` when `require_commission_yield` is configured.
`prediction_state.py` then opens the parent-owned ledger `hpc/<digest(run_id, owner)>/` (it must already exist) and
requires its recorded owner scope and commission identity to equal this assignment's.

## Children

None (`child_roles` returns `()`).

## Decision state and what it shows the model

`internal_summary.py` (initializing the ledger model on first use): `hpc_commission`, `hpc_candidates`,
`hpc_resource`, `hpc_tool_request` records, `hpc_model_ref` (current model), `hpc_credit` (credit view),
`hpc_latest_comparison` (without episode id / operation key), `hpc_model_support`, `hpc_report_form` (the typed form
hpc_credit / hpc_model_ref / hpc_result_refs), `hpc_plans`, `hpc_latest_monitor`, `hpc_monitor_controllers`,
`hpc_queue_refs`, shared memory policy and shared history refs when memory is configured,
`hpc_available_training_ids` (history minus validation ids). Around this, `decision_state.py` /
`decision_inputs.py` assemble the old generic snapshot plus resource context, launch instruction library, initial
binding context, completed action reports, `requested_action_history` (HPC context), pending work, execution
expectations for `hpc_prediction`, resource tool estimates and native execution expectations.

## Tools it offers

`prediction_operations.py`:
- `hpc.read` — read retained HPC evidence by identity (history row, ledger record, or a received owned
  `episode.hpc_result` source whose body equals the ledger receipt);
- `hpc.compare` — compare all approved portfolios with a model and a queue observation; no work is launched;
- `hpc.history.refresh` (only with shared memory) — read age-weighted shared timing history once;
- `hpc.discovery.run` — one lightweight read-only remote command through the established SSH transport, run from
  `/lus/flare/projects/BioReason-Aurora-Test`, cached as fresh inventory; old code passes `timeout=90` to
  `subprocess.run` and truncates stdout to 64 KiB / stderr to 8 KiB;
- `hpc.candidate.propose` — retain an executable portfolio (`candidate_json`; immutable identity; validated with
  the commission);
- `hpc.queue.observe` — acquire PBS queue and ALCF score/status once (memory freshness reuse within
  `commission.limits.queue_max_age_seconds`);
- `hpc.model.fit` — fit selected measured history; training ids must be non-validation and precede the temporal
  validation; validate on the fixed disjoint cases.
Every action is cached by operation key in the ledger (`ledger.cached`/`save_action`); invalid references return
`invalid` outcomes.

## How its credit is counted

Operational (`credit.py`): `credit = commission.credit.model_scale * gain + validation`, where `gain` = held-out
quality of the current model minus the quality recorded at this episode's entry (`model_entry`), and `validation` =
sum of the ledger's `validation` contributions attributed to this prediction episode. Model fit records
`ledger.model_credit(model_ref, quality - reference quality)` or 0 when trained on later allocations ("those
updates earn prospective credit when the next real outcomes arrive"). Actual job credit is not counted here.

## Continuation (yield estimator, settings)

`yield_estimator.py`: requires `require_commission_yield`; the commission's
`yield_bindings['hpc_prediction'] = {cutoff, parameters}` configure an old `YieldController` with an
`HPCContinuationEstimator` (continuation cost = cutoff). `continuation_for_action` records an exact-zero
continuation evidence packet ("prediction_ready_without_new_measured_improvement_opportunities") when there are no
validation ids, all available history is already trained, and a comparison over every candidate with a fresh
queue observation exists; "This bounds available action value, not action count". New observations reopen
prediction.

## What it reports to its parent

`to_parent.py`: fact sources `hpc_credit` (signed measured credit; polling adds none), `hpc_model_ref` (immutable
selected model identity, namespace `hpc_model`), `hpc_accepted_obligations` (obligations with accepted actual
results), `hpc_result_refs` (received owned result sources). `validate_report` requires every `x-source` field
equal the recorded facts. After close, `closed_models.py` validates an `hpc_model` reference read-only from the
saved facts and the ledger.

## Differences from similar episodes

- Shares the parent-owned HPC ledger with its sibling execution episode (`hpc_allocation_execution`), unlike every
  other A107 episode; the ledger, not the journal, is its state.
- Only `tool` actions; its instructions replace the default prompt and omit reasoning/wait/delivery texts; its task
  has no delivery-repair branch and no `reason` execution.
- Old code contains a 90 s subprocess timeout on discovery and a 2000-observation slice of shared history; both
  are count/time cutoffs to be reviewed against the no-limit rule when porting.

## Files

| old file | lines | this episode's own intent | old-runner names used (uses) |
|---|---|---|---|
| `__init__.py` | 0 | empty package marker | none |
| `binding_record.py` | 12 | binding id `.../hpc_resource_prediction`, version `hpc_episode_v1`, configuration: resources, commissions, shared_execution_memory, require_commission_yield | none |
| `closed_models.py` | 29 | `frozen_reference`: an `hpc_model` reference is valid after close only if the saved facts name it and the parent-owned HPC ledger (read-only) records it with matching owner run/episode/scope | `import:communication`, `import:episode_return_records`, `table:runtime_forms` |
| `configuration.py` | 30 | constructor: store, run_id, directory, resources (needs a `pbs_ssh` resource), explicit commissions validated against resources, `require_commission_yield` (then every commission needs `yield_bindings`), optional shared ExecutionMemory | `import:communication` |
| `credit.py` | 31 | operational credit = `commission.credit.model_scale * (current model quality - quality at this episode's entry) + prospective validation credit attributed to this prediction episode`; `actual_job_credit_counted_here: False` | none |
| `decision_inputs.py` | 46 | old decision input assembly (resource context, launch instruction library, initial binding context, completed action reports, requested_action_history for HPC context, pending work, execution expectations for `hpc_prediction`, resource estimates, contract profile) | `binding_context`, `import:episode_work_report` (2), `self.workflow.binding_context`, `self.workflow.episode_bindings`, `self.workflow.execution_expectations`, `self.workflow.launch_instructions` (2), `self.workflow.native_estimation_context`, `self.workflow.pending_work`, `self.workflow.resource_context`, `self.workflow.resource_estimator` (4) |
| `decision_state.py` | 31 | old generic decision snapshot (no annotation-axis branch) | `binding_context`, `import:runtime`, `runtime.FACT_MEANINGS`, `runtime.FACT_SOURCES`, `runtime.json`, `runtime.Mapping` (2), `runtime._plain` (2), `runtime._references_in`, `self.workflow.binding_context`, `self.workflow.catalog`, `self.workflow.controller_binding`, `self.workflow.delivery_status`, `self.workflow.extra_report_sources`, `self.workflow.job_episode_options`, `self.workflow.journal` (2), `self.workflow.knowledge`, `self.workflow.local_outcome_preview`, `self.workflow.pending_work`, `self.workflow.receipt_projection`, `self.workflow.run_id`, `self.workflow.source_credit_binding`, `self.workflow.source_credit_view`, `self.workflow.specialist`, `self.workflow.store` (3), `self.workflow.tools`, `self.workflow.working_state`, `table:runtime_actions` |
| `episode.py` | 44 | `HPCEpisode`: binding_path `partner_presence_evidence/hpc_work_planning/hpc_resource_prediction`, commissioning_parent `partner_presence_evidence/hpc_work_planning`, roles `('hpc_prediction',)`, no entry roles, no children, actions `('tool',)` only, `replaces_default_instructions = True`, prompt renderer `render_hpc_prompt` | none |
| `from_parent.py` | 44 | assignment: `owner_episode_id` plus exactly one of `commission_id` (enum of configured commissions) or `commission_source_ref`; parent must be role `hpc`, owner must be that parent, commission identity must equal the parent's; yield binding required when configured | `import:communication` |
| `goal.py` | 20 | instructions text (the goal; see above) | none |
| `initial_information.py` | 9 | resource information and received API information from this binding's declared readers | none |
| `internal_summary.py` | 36 | decision context: hpc_commission, candidates, resource, tool requests, current model ref, hpc_credit, latest comparison, model support, hpc_report_form, plans, latest monitor, monitor controllers, queue refs, shared memory and history refs, available training ids (history minus validation) | none |
| `portfolio_comparison.py` | 31 | candidates = commission candidates plus proposed ones; features; comparisons: predict each candidate with queue features and `prediction.compare` against obligations/preferences (already credited actual obligations excluded), sorted by net expected value | none |
| `prediction_history.py` | 63 | training history: commission history + latest shared history snapshot (no duplicate physical attempts) + one latest measured observation per closed plan (censored for failures); `_shared_history` reads age-weighted ExecutionMemory (queue-only resource-wide, work timing only for an explicit execution profile), queue-pooling rule, first 2000 new observations | none |
| `prediction_operations.py` | 147 | tools: hpc.read, hpc.compare, hpc.history.refresh (with memory), hpc.discovery.run (one read-only SSH command under the project directory, cached inventory, `timeout=90`, output truncated to 64 KiB/8 KiB), hpc.candidate.propose (immutable candidate identity, validated commission), hpc.queue.observe, hpc.model.fit (training ids must be non-validation and precede temporal validation; later-allocation training earns 0 retrospective credit; model credit = quality - reference quality) | `import:communication` |
| `prediction_state.py` | 43 | `state` opens the parent-owned HPC ledger (`hpc/<digest(run_id, owner)>`) and requires equal scope and commission; `initialize`: reference prior model, optional shared-history initial model, one model_entry record per episode | `import:communication` |
| `queue_observations.py` | 27 | queue observation with ExecutionMemory freshness reuse (`queue_max_age_seconds`); `_queue` with optional freshness requirement | none |
| `received_api_reports.py` | 4 | selects API reports declared for this binding path | none |
| `received_evidence.py` | 51 | resolves received `episode.hpc_result` sources owned by this run and within parent scope; `read_evidence` by history id, ledger id or owned result source (body must equal ledger receipt) | `import:communication` |
| `received_execution_information.py` | 4 | selects execution readers declared for this binding path | none |
| `report_delivery.py` | 23 | `finish`: same as other episodes (credit+pending handles or saved/filled form) | `binding_context`, `import:runtime`, `runtime.form_with_facts`, `runtime._json` (2), `runtime.json`, `runtime.Record` (2), `self.workflow.binding_context`, `self.workflow.episode_bindings`, `self.workflow.facts`, `self.workflow.journal` (2), `self.workflow.pending_handles`, `self.workflow.release` (2), `self.workflow.source_credit_view`, `table:runtime_forms` (2) |
| `task.py` | 148 | `ResourcePredictionTask`: old generic next/apply_response/execute (no reason, wait or delivery repair branches) | `import:episode_source_failure`, `import:providers`, `import:runtime`, `runtime.ActionFailure`, `runtime.ContractInformationError`, `runtime._decode_recorded_action_response`, `runtime.Draft202012Validator`, `runtime.EventTargetError`, `runtime.inspect`, `runtime._json` (5), `runtime.json` (8), `runtime.nullcontext` (5), `runtime.observes_action_outcome`, `runtime.ReportBoundaryError`, `runtime.schema_failure_diagnostic`, `runtime.SourceEnd` (2), `runtime.validate_form`, `runtime.ValidationError` (2), `runtime._wait_target_feedback`, `runtime.WorkflowError`, `self.workflow.action_schema`, `self.workflow.completed_unit`, `self.workflow.completions` (2), `self.workflow.controller_value` (2), `self.workflow.decision_exchanges` (3), `self.workflow.execute`, `self.workflow.execution_binding` (7), `self.workflow.inprocess_replay` (4), `self.workflow.journal` (7), `self.workflow.pending_work`, `self.workflow.receive_native_outcome`, `self.workflow.receive_outcome`, `self.workflow.resolver`, `self.workflow.run_id` (2), `self.workflow.selected` (3), `self.workflow.source_credit_view`, `self.workflow.store` (7), `self.workflow.validate_report`, `table:runtime_actions` (8), `table:runtime_episodes`, `table:runtime_model_calls` (2) |
| `task_decision.py` | 288 | old generic model call / decision exchange (uses own `decision_inputs`; `complete_with_presentation` with own renderer; no child_options view) | `import:runtime`, `runtime._action_generation_schema` (2), `runtime.apply_state_frame`, `runtime._ASSIGNMENT_TRANSPORT`, `runtime._category_yield_parameters`, `runtime.composition_lookup_schema` (2), `runtime.CONTRACT_INFORMATION_OPERATIONS`, `runtime.DECISION_CONTEXT_VERSION` (2), `runtime.DECISION_EXCHANGE_PROTOCOL` (5), `runtime._digest`, `runtime.Draft202012Validator`, `runtime.infernal_receiver_context` (2), `runtime.instructional_model_context` (4), `runtime.is_contract_information`, `runtime._json` (14), `runtime.json` (3), `runtime.lookup_attempts`, `runtime.Mapping` (2), `runtime.model_snapshot` (2), `runtime._object` (3), `runtime._plain` (2), `runtime._recorded_action_generation_schema`, `runtime._recorded_assignment_transport`, `runtime._references_in`, `runtime.requested_contract_information` (2), `runtime.schema_failure_diagnostic` (2), `runtime.sqlite3`, `runtime.state_frame`, `runtime.ValidationError` (5), `runtime.WorkflowError` (14), `runtime.yield_table`, `self.workflow.contract_information_profile`, `self.workflow.contract_information_reply`, `self.workflow.controller_binding`, `self.workflow.decision_exchanges` (4), `self.workflow.decision_protocol` (3), `self.workflow.execute`, `self.workflow.freeze_contract_information`, `self.workflow.history_preview`, `self.workflow.journal` (3), `self.workflow.numerical_contracts`, `self.workflow.provider` (3), `self.workflow.receipts` (4), `self.workflow.run_id`, `self.workflow.services`, `self.workflow.specialist`, `self.workflow.store` (2), `self.workflow.uses_received_record_context` (2), `self.workflow.validate_contract_information` (5), `table:runtime_model_calls` (8) |
| `task_instructions.py` | 11 | instructions = binding instructions + tool knowledge + launch instruction library text (no generic INSTRUCTIONS) | `binding_context`, `self.workflow.binding_context`, `self.workflow.knowledge`, `self.workflow.launch_instructions`, `self.workflow.specialist` |
| `task_state.py` | 108 | old generic source state (execution failure only for `tool`) | `import:episode_source_failure`, `import:runtime`, `param:workflow.context`, `param:workflow.grains`, `runtime.ActionLeaf`, `runtime.EFFECT_VERSION`, `runtime.Episode`, `runtime.interpretation_schema`, `runtime._json` (2), `runtime.json` (4), `runtime._object`, `runtime._plain`, `runtime.Record`, `self.workflow.archive`, `self.workflow.completions` (4), `self.workflow.controller_value`, `self.workflow.execution_binding` (4), `self.workflow.inprocess_replay` (7), `self.workflow.journal` (5), `self.workflow.progress_provider` (2), `self.workflow.recover_commissions`, `self.workflow.run_id`, `self.workflow.source_credit_view`, `self.workflow.store` (2), `table:runtime_actions` (5) |
| `to_parent.py` | 40 | fact sources hpc_credit, hpc_model_ref, hpc_accepted_obligations, hpc_result_refs; facts from ledger; `hpc_model` resolution; report must equal recorded facts | `import:communication`, `import:episode_bindings` |
| `waiting.py` | 9 | `suspension_changed` on old execution backend | `self.workflow.execution_backend`, `self.workflow.execution_handle` (2) |
| `yield_estimator.py` | 60 | `yield_controller` requires `require_commission_yield` and the commission's `yield_bindings['hpc_prediction']` {cutoff, parameters}; estimator HPCContinuationEstimator with continuation cost = cutoff; `continuation_for_action` writes a zero-continuation evidence packet when there are no validation ids, all available history is trained, and a current full-candidate comparison with fresh queue exists | `import:library.hpc_continuation`, `import:numerical`, `yield:HPCContinuationEstimator` (2), `yield:YieldController` (2), `yield:YieldParameters` (2) |
