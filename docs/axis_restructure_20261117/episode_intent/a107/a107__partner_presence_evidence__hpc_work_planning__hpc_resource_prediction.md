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

## Carried over

Old files at 97308b94c (read with `git show`; the repository `.git` is in `gene_annotation_episode_disk`). One row per row of `runs/carry_over/functions/a107__partner_presence_evidence__hpc_work_planning__hpc_resource_prediction.tsv`. New files are in `gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/hpc_resource_prediction/`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | PredictionBindingRecord (class) | machinery | binding_record.py (README 3e: binding record, as_record, version and configuration record) |
| binding_record.py | PredictionBindingRecord.as_record (method) | machinery | the binding's own as_record() (README 3e) |
| closed_models.py | ClosedModels (class) | episode function | unplaced: see frozen_reference |
| closed_models.py | ClosedModels.frozen_reference (method) | episode function | unplaced (carry_over_blocked): validated a closed hpc_model reference through runtime_forms and EpisodeReturnRecords (machinery) and a second read-only connection to the ledger; the model-identity check of the Episode's own report is messages/final_to_parent.py resolve/validate_report (hpc_model namespace over summary hpc_model_refs) |
| configuration.py | PredictionConfiguration (class) | episode function | values become ctx.settings (task.py docstring: resources, commissions, shared_execution_memory, launch/knowledge directories) and settings cost/parameters (yield_estimator.py) |
| configuration.py | PredictionConfiguration.__init__ (method) | episode function | task.py _commission (validate_commission of the configured commission with resources) and _memory; yield_estimator.py (require_commission_yield -> hpc_commission_yield_binding_required); store, run_id, directory: machinery (the custody store, ctx.run_id, the hpc_ledger service) |
| credit.py | HPCEpisodeCredit (class) | episode function | credit.py credit_view and credit |
| credit.py | HPCEpisodeCredit.credit_kind (method) | machinery | credit_kind is deleted (README 3d) |
| credit.py | HPCEpisodeCredit._quality (method) | episode function | task.py _quality (called by the tools; the quality reaches credit.py through the ledger view of the outcome) (library candidate) |
| credit.py | HPCEpisodeCredit.credit_view (method) | episode function | credit.py credit_view(state) and credit(summary, records); ledger reads replaced by the ledger view of the latest tool outcome (task.py _ledger_view) |
| decision_inputs.py | PredictionDecisionInputs (class) | episode function | task.py decide (context); see the method row |
| decision_inputs.py | PredictionDecisionInputs.decision_inputs (method) | episode function | task.py decide: launch instruction library and selected instructions (settings directory). Machinery, not carried: binding_context, initial_decision_context, completed_action_reports, pending_work (old runner); requested_action_history is rebuilt from view.outcomes in messages/internal_summary.py. BLOCKED-ON-JOB-SERVICE estimate_table, not carried: resource_context, execution_expectations, resource_tool_estimates, native_execution_expectations |
| decision_state.py | PredictionDecisionState (class) | machinery | old generic decision snapshot over self.workflow (journal, receipts, pending work, delivery status); the view-derived parts are messages/internal_summary.py |
| decision_state.py | PredictionDecisionState.decision_state (method) | machinery | old generic decision snapshot over self.workflow (journal, receipts, pending work, delivery status) |
| episode.py | HPCEpisode (class) | episode function | episode.py HPCResourcePrediction; binding_path in goal.py; commissioning_parent, roles, entry_roles, decision_source_type, decision_prompt_renderer: machinery of the hook-era binding |
| episode.py | HPCEpisode.child_roles (method) | episode function | task.py CHILD_SLOTS = {} |
| episode.py | HPCEpisode.allowed_children (method) | machinery | allowed_children (README 3b C2: CHILD_SLOTS) |
| episode.py | HPCEpisode.permitted_common_actions (method) | episode function | task.py action: only the tool action exists (no wait, reason or redelivery action) |
| from_parent.py | PredictionAssignment (class) | episode function | messages/read_from_parent.py |
| from_parent.py | PredictionAssignment.assignment_schema (method) | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (oneOf of commission_id/commission_source_ref in read_from_parent) |
| from_parent.py | PredictionAssignment.commission_identity (method) | episode function | task.py _identity |
| from_parent.py | PredictionAssignment._commission (method) | episode function | task.py _commission (library hpc_commission_sources.read for commission_source_ref) |
| from_parent.py | PredictionAssignment.prepare_assignment (method) | episode function | messages/read_from_parent.py: schema admission (ASSIGNMENT_FORM, exactly one commission identity). Not carried: the parent role, owner and commission-identity equality checks and the yield-binding check (a check of a commission, README rule 1; the yield binding is read from settings) |
| goal.py | PredictionGoal (class) | episode function | goal.py GOAL |
| goal.py | PredictionGoal.instructions (method) | episode function | goal.py GOAL (text unchanged); composed into the instructions by task.py instructions |
| initial_information.py | initial_information (function) | episode function | unplaced (carry_over_blocked): selected declared readers of the old catalog and library.execution_initial_information.presentation (old shared root, no home found) |
| internal_summary.py | PredictionSummary (class) | episode function | messages/internal_summary.py internal_summary and task.py _ledger_view |
| internal_summary.py | PredictionSummary.decision_context (method) | episode function | messages/internal_summary.py internal_summary (hpc_* keys) over task.py _ledger_view; hpc_report_form not carried (report-form machinery) |
| portfolio_comparison.py | PortfolioComparison (class) | episode function | task.py _candidates, _features, _comparisons |
| portfolio_comparison.py | PortfolioComparison._candidates (method) | episode function | task.py _candidates (library candidate) |
| portfolio_comparison.py | PortfolioComparison._features (method) | episode function | task.py _features (library candidate) |
| portfolio_comparison.py | PortfolioComparison._comparisons (method) | episode function | task.py _comparisons (library candidate) |
| prediction_history.py | PredictionHistory (class) | episode function | task.py _history, _shared_history |
| prediction_history.py | PredictionHistory._history (method) | episode function | task.py _history (library candidate) |
| prediction_history.py | PredictionHistory._shared_history (method) | episode function | task.py _shared_history (the [:2000] slice not carried: a count cutoff) (library candidate) |
| prediction_operations.py | PredictionOperations (class) | episode function | task.py catalog and the tools |
| prediction_operations.py | PredictionOperations.catalog (method) | episode function | task.py catalog (tool names with _ for .) |
| prediction_operations.py | PredictionOperations.execute (method) | episode function | task.py tools hpc_read, hpc_history_refresh, hpc_discovery_run, hpc_candidate_propose, hpc_queue_observe, hpc_model_fit, hpc_compare. Machinery, not carried: ledger.cached/save_action/action_intent (the system journals attempts), discovery timeout=90 and output truncation (cutoffs) |
| prediction_state.py | PredictionState (class) | episode function | task.py hpc_open, _open_ledger, _initialize, _current_model |
| prediction_state.py | PredictionState.state (method) | episode function | task.py hpc_open (owner scope and commission identity equality) with _open_ledger (BLOCKED-ON-JOB-SERVICE hpc_ledger) |
| prediction_state.py | PredictionState.initialize (method) | episode function | task.py _initialize (called by hpc_open every time: idempotent; see contract_misfits) (library candidate) |
| prediction_state.py | PredictionState._current_model (method) | episode function | task.py _current_model (library candidate) |
| queue_observations.py | QueueObservations (class) | episode function | task.py _observe_queue, _queue |
| queue_observations.py | QueueObservations._observe_queue (method) | episode function | task.py _observe_queue (the acquisition is _acquire_queue, BLOCKED-ON-JOB-SERVICE job_access) (library candidate) |
| queue_observations.py | QueueObservations._queue (method) | episode function | task.py _queue (library candidate) |
| received_api_reports.py | received_api_reports (function) | episode function | unplaced (carry_over_blocked): selected declared API readers of the old catalog |
| received_evidence.py | ReceivedEvidence (class) | episode function | task.py _resolve_received_source, _read_evidence |
| received_evidence.py | ReceivedEvidence._known (method) | machinery | hand-kept held set of received references (README 3e F2: records.holds) |
| received_evidence.py | ReceivedEvidence.resolve_received_reference (method) | episode function | task.py _resolve_received_source (held check through ctx.store.holds) (library candidate) |
| received_evidence.py | ReceivedEvidence.read_evidence (method) | episode function | task.py _read_evidence (library candidate) |
| received_execution_information.py | received_execution_information (function) | episode function | unplaced (carry_over_blocked): selected declared execution readers of the old catalog |
| report_delivery.py | PredictionReportDelivery (class) | machinery | report_delivery.py finish: saved/filled form, pending handles, release (README 3b D1, D3); the result is messages/final_to_parent.py final_to_parent |
| report_delivery.py | PredictionReportDelivery.finish (method) | machinery | report_delivery.finish: saved/filled form, pending handles, release (README 3b D1, D3) |
| task.py | ResourcePredictionTask (class) | episode function | task.py decide, action, TOOLS |
| task.py | ResourcePredictionTask.next (method) | episode function | task.py decide |
| task.py | ResourcePredictionTask.apply_response (method) | episode function | task.py action (Rejected(feedback) for a malformed answer) |
| task.py | ResourcePredictionTask.execute (method) | episode function | task.py TOOLS (ToolCall); wait, reason, child and redelivery branches are machinery |
| task_decision.py | PredictionTaskDecision (class) | episode function | task.py decide and instructions |
| task_decision.py | PredictionTaskDecision.call (method) | episode function | task.py decide (ModelRequest); the provider call and its journal rows are machinery |
| task_decision.py | PredictionTaskDecision.instructions (method) | episode function | task.py instructions |
| task_decision.py | PredictionTaskDecision.complete_decision (method) | machinery | model call recording (README 3a: ModelRequest, runtime_model_calls) |
| task_decision.py | PredictionTaskDecision.conversation_key (method) | machinery | conversation state (README 3a) |
| task_decision.py | PredictionTaskDecision.interpretation_context (method) | machinery | decision-exchange interpretation context (README 3a) |
| task_decision.py | PredictionTaskDecision.exchange_schema (method) | machinery | decision-exchange loop (README 3a) |
| task_decision.py | PredictionTaskDecision.exchange_response (method) | machinery | decision-exchange loop (README 3a) |
| task_decision.py | PredictionTaskDecision.validate_contract_exchange_request (method) | machinery | saved-request checks (README 3a) |
| task_decision.py | PredictionTaskDecision.validate_contract_exchange_history (method) | machinery | saved-request checks (README 3a) |
| task_decision.py | PredictionTaskDecision.exchange_decision (method) | machinery | decision-exchange loop (README 3a) |
| task_instructions.py | instructions (function) | episode function | task.py instructions |
| task_state.py | PredictionTaskState (class) | machinery | task_state.py: source state restore, checkpoint, recorded failures (README 3e) |
| task_state.py | PredictionTaskState.__init__ (method) | machinery | checkpoint/restore/record_effect/failure recording (README 3e F6, F8) |
| task_state.py | PredictionTaskState.bind_execution_context (method) | machinery | checkpoint/restore/record_effect/failure recording (README 3e F6, F8) |
| task_state.py | PredictionTaskState.record_execution_failure (method) | machinery | checkpoint/restore/record_effect/failure recording (README 3e F6, F8) |
| task_state.py | PredictionTaskState.restore_checkpoint (method) | machinery | checkpoint/restore/record_effect/failure recording (README 3e F6, F8) |
| task_state.py | PredictionTaskState.restore (method) | machinery | checkpoint/restore/record_effect/failure recording (README 3e F6, F8) |
| task_state.py | PredictionTaskState.record_effect (method) | machinery | checkpoint/restore/record_effect/failure recording (README 3e F6, F8) |
| task_state.py | PredictionTaskState.checkpoint (method) | machinery | checkpoint/restore/record_effect/failure recording (README 3e F6, F8) |
| to_parent.py | PredictionReport (class) | episode function | messages/final_to_parent.py |
| to_parent.py | PredictionReport.fact_sources (method) | episode function | messages/final_to_parent.py RETURN_FORM (hpc_credit, hpc_model_ref, hpc_accepted_obligations, hpc_result_refs selectable; credit and finding required) |
| to_parent.py | PredictionReport.facts (method) | episode function | messages/final_to_parent.py hpc_facts (and messages/internal_summary.py for the ledger view) |
| to_parent.py | PredictionReport.resolve (method) | episode function | messages/final_to_parent.py resolve |
| to_parent.py | PredictionReport.validate_report (method) | episode function | messages/final_to_parent.py validate_report (called by final_to_parent; the first step validate_form of the parent form is not carried: the parent writes no form) |
| waiting.py | PredictionSuspension (class) | machinery | wait/suspension machinery |
| waiting.py | PredictionSuspension.suspension_changed (method) | machinery | wait/suspension machinery |
| yield_estimator.py | HPCEpisodeYield (class) | episode function | yield_estimator.py |
| yield_estimator.py | HPCEpisodeYield.yield_controller (method) | episode function | yield_estimator.py yield_controller (AccumulationYieldController; cutoff -> settings cost) |
| yield_estimator.py | HPCEpisodeYield.continuation_for_action (method) | machinery | estimator packet and exact-zero continuation evidence (README 3d, 7b: nothing but the controller stops the Episode) |
| yield_estimator.py | HPCEpisodeYield.practical_estimator (method) | machinery | HPCContinuationEstimator (README 7b: no estimator of its own) |
