# a110 / biochemical_feasibility_evidence / hpc_work_planning / hpc_resource_prediction

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a110/biochemical_feasibility_evidence/hpc_work_planning/hpc_resource_prediction/<file>`. Only this folder and its `tests/` were read. Old binding class `HPCEpisode`, decision source `ResourcePredictionTask`. Old role name: `hpc_prediction`.

## What it is for (its own words)

`goal.py`: "Iterate on a generalized time/resource model using measured historical cases. Refresh shared history, inspect support and held-out quality, fit a disjoint training selection, and compare useful portfolios. Inspect missing capacity, launcher and queue facts with lightweight discovery; propose executable resource alternatives when the parent has not supplied them. Preparation and submission belong to the execution sister. Forecast CPU time and memory demand as well as queue, setup and work time. Compare node/worker counts, memory capacity, workload parameters and elapsed cost. The paired execution episode owns Launch, monitoring and parsing. Both sisters use this parent-owned ledger; preserve model and comparison identities for that sibling. The fixed reference and validation set cannot change. Model credit is modest measured improvement; the HPC parent later scores frozen predictions against real outcomes. Unknown inputs stay unknown. Return when further model improvement is less useful than running the next worthwhile portfolio."

## Task and instructions

`replaces_default_instructions = True`; `task_instructions.py` uses only the binding's text plus tool-knowledge and launch-instruction text. No report/repair/wait guidance is added (unlike the monitor). HPC prompt renderer (`library.hpc_prompt.render_hpc_prompt`).

## What it reads from its parent's assignment

`from_parent.py`: `owner_episode_id` (required; must be the parent hpc episode), and exactly one of `commission_id` (enum of configured commissions) or `commission_source_ref` (read from the store). The commission identity must equal the parent's. With private yield, the commission must carry `yield_bindings`. The commission supplies resource_id, candidates, history, validation_ids, model spec, obligations, preferences, credit.model_scale, limits.queue_max_age_seconds and execution_profile. State lives in the parent-owned HPC ledger at `<directory>/hpc/<digest(run, owner)>/`, opened existing; its scope and commission must equal the original (`prediction_state.py`).

## Children

None. Only `tool` actions.

## Decision state shown to the model

Shared state fields (`decision_state.py`, no annotation-axis or monitoring branches). Decision inputs (`decision_inputs.py`): resource context, launch instruction library and selection, initial binding context, completed action reports, `requested_action_history` for HPC contexts, pending work, execution expectations for `hpc_prediction`, resource and native estimates, contract-information profile; no child options and no waiting support.
Its own part (`internal_summary.py`): `hpc_commission`, `hpc_owner_episode_id`, `hpc_candidates`, `hpc_resource`, `hpc_tool_request`, `hpc_model_ref`, `hpc_credit`, `hpc_latest_comparison`, `hpc_model_support`, `hpc_report_form` (hpc_credit, hpc_model_ref, hpc_result_refs), `hpc_plans`, `hpc_latest_monitor`, `hpc_monitor_controllers`, `hpc_queue_refs`, shared memory and history refs, `hpc_available_training_ids` (history minus validation).

## Tools

`prediction_operations.py`, all idempotent by operation key through the ledger: `hpc.read`, `hpc.compare` (rank all candidates by net expected value; nothing launched), `hpc.history.refresh` (when shared memory is configured), `hpc.discovery.run` (one read-only SSH command run under `/lus/flare/projects/BioReason-Aurora-Test`; stdout/stderr truncated; cached in memory), `hpc.candidate.propose` (candidate JSON with id, queue, nodes, wall_seconds, features, optional resource_capacity, units, files, preparation instructions; identity immutable), `hpc.queue.observe` (PBS queue and ALCF status once), `hpc.model.fit` (training ids must be non-validation and precede temporal validation).
Noted old limits in this file: `subprocess.run(..., timeout=90)` on discovery, stdout cut at 65536 bytes and stderr at 8192, shared history observations cut to 2000. These are fixed time/count cutoffs; the carry-over must not keep them as stopping limits.

## Credit

Kind `operational` (`credit.py`): `credit = commission.credit.model_scale * (current model quality - this episode's entry quality) + prospective validation credit of this episode's predictions`; `actual_job_credit_counted_here: False`. Model fit records `quality - baseline` (or 0 when trained on later allocations; those earn prospective credit when real outcomes arrive). Signed; not bounded.

## Continuation

Old `yield_estimator.py`: `YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters), estimate_with_context=HPCContinuationEstimator(verify).with_continuation_cost(cutoff))` from `commission.yield_bindings['hpc_prediction']`. `continuation_for_action` writes a continuation evidence record with expected continuation 0 when there are no validation ids, all available training is used, and comparisons for every candidate exist with a fresh queue ("prediction ready without new measured improvement opportunities"). Nearest new estimator: bounded quality is not a fit (signed, unbounded quality gain); accumulation with the commission's cutoff/parameters, with the zero-continuation evidence as an explicit exhaustion signal. This needs the owner's choice among the three.

## What it reports to its parent

`to_parent.py`: `hpc_credit`, `hpc_model_ref` (immutable selected model; namespace `hpc_model`), `hpc_accepted_obligations`, `hpc_result_refs` (received result Sources). `validate_report` requires x-source fields equal facts. Closed model refs are checked read-only against the ledger (`closed_models.py`).

## Differences from similar episodes

- Sister of `hpc_allocation_execution` sharing one parent-owned ledger.
- Task files are the slimmest of the four: no delivery_ref, wait, redelivery or reason paths.
- Its tests are shared HPC mixins parameterised by axis/path/role.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| __init__.py | 0 | empty | none |
| binding_record.py | 12 | binding record hpc_episode_v1 with resources, commissions, shared execution memory and require_commission_yield | none |
| closed_models.py | 29 | a closed hpc_model reference is valid only if this episode's saved facts name it and the parent-owned ledger (read-only) owns it for this run, owner episode and scope | import root.a110.communication x1, import root.a110.episode_return_records x1, table runtime_forms x1 |
| configuration.py | 30 | services, store, run_id, directory; explicit resources with at least one pbs_ssh; explicit commissions validated against resources; optional require_commission_yield requiring yield_bindings in every commission; optional shared ExecutionMemory | import root.a110.communication x1, import root.a110.execution_memory x1, import root.a110.hpc_campaign x1 |
| credit.py | 31 | credit kind operational; credit = model_scale * (current model quality - quality at this episode's entry) + prospective validation credit of this episode's predictions; actual job credit is not counted here | import root.a110.library x1 |
| decision_inputs.py | 46 | resource context, launch instruction library, initial binding context, completed action reports, requested_action_history for HPC contexts, pending work, execution expectations 'hpc_prediction', resource/native estimates, contract-information profile (no child options, no waiting support) | import root.a110.episode_work_report x2, import root.a110.library.hpc_prompt x1, workflow.binding_context x1, workflow.episode_bindings x1, workflow.execution_expectations x1, workflow.launch_instructions x2, workflow.native_estimation_context x1, workflow.pending_work x1, workflow.resource_context x1, workflow.resource_estimator x4 |
| decision_state.py | 31 | model-facing state (same shared fields; no annotation-axis branch, no monitoring fields) | import root.a110.runtime x1, journal.db x1, journal.elapsed_view x1, runtime.FACT_MEANINGS x1, runtime.FACT_SOURCES x1, runtime.json x1, runtime.Mapping x2, runtime._plain x2, runtime._references_in x1, table runtime_actions x1, workflow.binding_context x1, workflow.catalog x1, workflow.controller_binding x1, workflow.delivery_status x1, workflow.extra_report_sources x1, workflow.job_episode_options x1, workflow.journal x2, workflow.knowledge x1, workflow.local_outcome_preview x1, workflow.pending_work x1, workflow.receipt_projection x1, workflow.run_id x1, workflow.source_credit_binding x1, workflow.source_credit_view x1, workflow.specialist x1, workflow.store x3, workflow.tools x1, workflow.working_state x1 |
| episode.py | 42 | composes the binding; path .../hpc_resource_prediction, commissioning parent hpc_work_planning; role hpc_prediction, not an entry; no children; only tool actions; own instructions replace the default; HPC prompt renderer | import root.a110.library.hpc_prompt x1 |
| from_parent.py | 44 | assignment {owner_episode_id, commission_id (enum of configured commissions) or commission_source_ref}; must belong to its original hpc parent with the same commission identity; with private yield, commission must carry yield_bindings | import root.a110.communication x1, import root.a110.domain x1, import root.a110.execution_contracts x1, import root.a110.hpc_commission_sources x1 |
| goal.py | 20 | instructions: iterate on a generalized time/resource model from measured historical cases; refresh shared history, inspect support and held-out quality, fit a disjoint training selection, compare portfolios; lightweight discovery of capacity/launcher/queue; propose executable alternatives; forecast CPU time, memory, queue, setup and work time; preparation/submission/monitoring/parsing belong to the execution sister; shared parent-owned ledger; fixed reference and validation set; return when further model improvement is less useful than running the next portfolio | none |
| initial_information.py | 8 | selects this path's declared resource readers | import root.a110.library.execution_initial_information.presentation x1 |
| internal_summary.py | 36 | decision_context: commission, owner, candidates, resource, tool requests, current model ref, credit, latest comparison, model support, report form, plans, latest monitor, monitor controllers, queue refs, shared memory and history refs, available training ids | import root.a110.library x1 |
| portfolio_comparison.py | 31 | candidates = commission candidates + proposed; features; comparisons of every candidate by net expected value using the model, queue features, obligations, preferences and already-credited actual results | import root.a110.library x1 |
| prediction_history.py | 63 | training history = commission history + latest shared history (no duplicate physical attempts) + one latest measured observation per closed allocation; shared history query by execution profile; queue pooling rules | import root.a110.execution_guidance x1, import root.a110.library.hpc_resource_prediction x1 |
| prediction_operations.py | 147 | tools hpc.read, hpc.compare, hpc.history.refresh (with memory), hpc.discovery.run (one read-only SSH command under the project directory), hpc.candidate.propose (immutable candidate identity), hpc.queue.observe, hpc.model.fit (training must be non-validation and precede temporal validation; credit = quality - baseline, or 0 when trained on later allocations); idempotent by operation key | import root.a110.communication x1, import root.a110.domain x1, import root.a110.execution_contracts x1, import root.a110.execution_guidance x1, import root.a110.hpc_campaign x1, import root.a110.library x1 |
| prediction_state.py | 43 | opens the parent-owned HPC ledger for (run, owner); scope and commission must equal the original; initialize puts the reference model, may fit an initial model from shared history, and records entry quality once per episode | import root.a110.communication x1, import root.a110.domain x1, import root.a110.hpc_ledger x1, import root.a110.library x1 |
| queue_observations.py | 27 | queue observation from memory if fresh within queue_max_age_seconds, else PBS/ALCF observation; freshness check for planning | import root.a110.execution_guidance x1 |
| received_evidence.py | 51 | known records; resolve received episode.hpc_result Sources in scope; read_evidence from history, ledger or owned result Source with receipt match | import root.a110.communication x1 |
| received_execution_information.py | 4 | selects configured/received result readers declared for this path | none |
| report_delivery.py | 23 | finish (same structure as siblings) | import root.a110.runtime x1, journal.row x1, journal.save x1, runtime.form_with_facts x1, runtime._json x2, runtime.json x1, runtime.Record x2, table runtime_forms x2, workflow.binding_context x1, workflow.episode_bindings x1, workflow.facts x1, workflow.journal x2, workflow.pending_handles x1, workflow.release x2, workflow.source_credit_view x1 |
| task.py | 148 | decision iterator without delivery_ref handling, wait, redelivery or reason (tool actions only) | import root.a110.episode_source_failure x1, import root.a110.providers x1, import root.a110.runtime x1, journal.measure x1, journal.row x7, journal.save x3, runtime.ActionFailure x1, runtime.ContractInformationError x1, runtime._decode_recorded_action_response x1, runtime.Draft202012Validator x1, runtime.EventTargetError x1, runtime.inspect x1, runtime._json x5, runtime.json x8, runtime.nullcontext x5, runtime.observes_action_outcome x1, runtime.ReportBoundaryError x1, runtime.schema_failure_diagnostic x1, runtime.SourceEnd x2, runtime.validate_form x1, runtime.ValidationError x2, runtime._wait_target_feedback x1, runtime.WorkflowError x1, table runtime_actions x8, table runtime_episodes x1, table runtime_model_calls x2, workflow.action_schema x1, workflow.completed_unit x1, workflow.completions x2, workflow.controller_value x2, workflow.decision_exchanges x3, workflow.execute x1, workflow.execution_binding x7, workflow.inprocess_replay x4, workflow.journal x7, workflow.pending_work x1, workflow.receive_native_outcome x1, workflow.receive_outcome x1, workflow.resolver x1, workflow.run_id x2, workflow.selected x3, workflow.source_credit_view x1, workflow.store x7, workflow.validate_report x1 |
| task_decision.py | 288 | model call / exchange protocol (no child_options lookup, no annotation-axis yield table) | exchanges.measure x1, exchanges.prepare x1, exchanges.resolve_lookup x1, exchanges.respond x1, exchanges.rows x1, import root.a110.runtime x1, journal.measure x2, journal.row x2, journal.save x4, runtime._action_generation_schema x2, runtime.apply_state_frame x1, runtime._ASSIGNMENT_TRANSPORT x1, runtime._category_yield_parameters x1, runtime.composition_lookup_schema x2, runtime.CONTRACT_INFORMATION_OPERATIONS x1, runtime.DECISION_CONTEXT_VERSION x2, runtime.DECISION_EXCHANGE_PROTOCOL x5, runtime._digest x1, runtime.Draft202012Validator x1, runtime.instructional_model_context x4, runtime.is_contract_information x1, runtime._json x14, runtime.json x3, runtime.lookup_attempts x1, runtime.Mapping x2, runtime.model_snapshot x2, runtime._object x3, runtime._plain x2, runtime._recorded_action_generation_schema x1, runtime._recorded_assignment_transport x1, runtime._references_in x1, runtime.requested_contract_information x2, runtime.schema_failure_diagnostic x2, runtime.sqlite3 x1, runtime.state_frame x1, runtime.ValidationError x5, runtime.WorkflowError x14, runtime.yield_table x1, table runtime_model_calls x8, workflow.contract_information_profile x1, workflow.contract_information_reply x1, workflow.controller_binding x1, workflow.decision_exchanges x4, workflow.decision_protocol x3, workflow.execute x1, workflow.freeze_contract_information x1, workflow.history_preview x1, workflow.journal x3, workflow.numerical_contracts x1, workflow.provider x3, workflow.receipts x4, workflow.run_id x1, workflow.services x1, workflow.specialist x1, workflow.store x2, workflow.uses_received_record_context x2, workflow.validate_contract_information x5 |
| task_instructions.py | 11 | the binding's instructions plus tool knowledge and launch instruction text only | workflow.binding_context x1, workflow.knowledge x1, workflow.launch_instructions x1, workflow.specialist x1 |
| task_state.py | 108 | per-episode decision state (only tool actions recorded on failure) | import root.a110.episode_source_failure x1, import root.a110.runtime x1, journal.row x3, journal.save x2, runtime.ActionLeaf x1, runtime.EFFECT_VERSION x1, runtime.Episode x1, runtime.interpretation_schema x1, runtime._json x2, runtime.json x4, runtime._object x1, runtime._plain x1, runtime.Record x1, table runtime_actions x5, workflow.archive x1, workflow.completions x4, workflow.context x1, workflow.controller_value x1, workflow.execution_binding x4, workflow.grains x1, workflow.inprocess_replay x7, workflow.journal x5, workflow.progress_provider x2, workflow.recover_commissions x1, workflow.run_id x1, workflow.source_credit_view x1, workflow.store x2 |
| to_parent.py | 40 | facts hpc_credit, hpc_model_ref, hpc_accepted_obligations, hpc_result_refs; resolve hpc_model refs from the ledger; validate_report checks facts | import root.a110.communication x1, import root.a110.episode_bindings x1 |
| waiting.py | 9 | suspension_changed (no wait action is permitted) | workflow.execution_backend x1, workflow.execution_handle x2 |
| yield_estimator.py | 60 | yield_controller from the commission's yield_bindings[role] (cutoff, parameters) with the HPC continuation estimator plus continuation cost; continuation_for_action records zero expected continuation when no validation ids, all training used and current comparisons with a fresh queue exist | import root.a110.library.hpc_continuation x1, import root.a110.numerical x1 |
| tests/__init__.py | 0 | empty | none |
| tests/test_calculation_connections.py | 7 | shared HPC calculation mixin for this path and role | import root.tests.hpc_calculation_behavior x1 |
| tests/test_prediction_behavior.py | 6 | shared prediction behaviour mixin | import root.tests.hpc_prediction_behavior x1 |
| tests/test_prediction_prompt.py | 6 | shared prediction prompt mixin | import root.tests.hpc_prediction_prompt_behavior x1 |
| tests/test_prediction_task.py | 6 | shared prediction task mixin | import root.tests.hpc_prediction_task_behavior x1 |

Per-name rows with counts: `runs/carry_over/calls/a110_05.tsv`.

## Carried over

Source of the old rows: `runs/carry_over/functions/a110__biochemical_feasibility_evidence__hpc_work_planning__hpc_resource_prediction.tsv`. New files are under `gene_annotation_episode/episodic_workflow/root/a110/biochemical_feasibility_evidence/hpc_work_planning/hpc_resource_prediction/`. "library candidate" marks an episode function that is not in the library and stays in the episode file that uses it.

| old file | name | kind | new place / machinery reason |
|---|---|---|---|
| binding_record.py | PredictionBindingRecord | machinery | binding's own as_record (binding_record.py), deleted (README 3d/3e) |
| binding_record.py | PredictionBindingRecord.as_record | machinery | binding's own as_record(): hpc_episode_v1 record of resources, commissions, shared memory; settings are journaled by the system |
| closed_models.py | ClosedModels | machinery | closed-run authentication of a model ref by EpisodeReturnRecords / runtime_forms and a read-only open of the ledger file (receipts bookkeeping, runtime_* re-validation) |
| closed_models.py | ClosedModels.frozen_reference | episode function | messages/final_to_parent.py resolve_reference (the model identity must be a model row of the held ledger); the EpisodeReturnRecords.authenticate / runtime_forms / sqlite read-only parts are machinery |
| configuration.py | PredictionConfiguration | machinery | configuration class; its values are settings (ctx.settings) or constants of the file that uses them |
| configuration.py | PredictionConfiguration.__init__ | machinery | operands: resources -> ctx.settings['resources'], shared_execution_memory -> ctx.settings['shared_execution_memory'] and the estimate_table service, require_commission_yield/yield_bindings -> settings cost and parameters (yield_estimator.py), commissions -> the commission row of the ledger; run_id/store/directory/services are the system's |
| credit.py | HPCEpisodeCredit | episode function | credit.py (module functions) |
| credit.py | HPCEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | HPCEpisodeCredit._quality | episode function | credit.py quality |
| credit.py | HPCEpisodeCredit.credit_view | episode function | credit.py credit (formula), quality_improvement, prospective_validation_credit; components computed in messages/internal_summary.py |
| decision_inputs.py | PredictionDecisionInputs | episode function | task.py decide |
| decision_inputs.py | PredictionDecisionInputs.decision_inputs | episode function | task.py decide (launch instruction library and selection, tool knowledge, requested_action_history as outcome_page, controller, time accounting); resource context from settings; completed_action_reports, pending_work, execution_expectations, resource estimates, native expectations and contract-information profile not carried (see unplaced) |
| decision_state.py | PredictionDecisionState | episode function | messages/internal_summary.py internal_summary |
| decision_state.py | PredictionDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary and task.py decide; the runtime_actions visual_evidence read, delivery status, report_update/report basis and extra report sources are old-runner machinery |
| episode.py | HPCEpisode | episode function | episode.py HpcResourcePrediction |
| episode.py | HPCEpisode.child_roles | machinery | no children: CHILD_SLOTS = {} |
| episode.py | HPCEpisode.allowed_children | machinery | no children: CHILD_SLOTS = {} |
| episode.py | HPCEpisode.permitted_common_actions | episode function | task.py action (only tool actions exist) |
| from_parent.py | PredictionAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | PredictionAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | PredictionAssignment.commission_identity | episode function | messages/read_from_parent.py read_from_parent (identity of the assignment), task.py check_owner |
| from_parent.py | PredictionAssignment._commission | machinery | reads the commission by commission_source_ref (hpc_commission_sources.read, no A110 copy) or the configured commissions; the commission is the 'commission' row of the held ledger (task.py read_ledger) |
| from_parent.py | PredictionAssignment.prepare_assignment | machinery | admission of the commission by the child (owner must be the hpc parent, identity equal to the parent's, yield_bindings present): a check of a commission, not carried (rule 1) |
| goal.py | PredictionGoal | episode function | goal.py GOAL |
| goal.py | PredictionGoal.instructions | episode function | goal.py GOAL (text unchanged); composed into the instructions in task.py instructions |
| initial_information.py | initial_information | episode function | not placed: resource_information (library.execution_initial_information.presentation) is in no library module; listed in unplaced_old_functions |
| internal_summary.py | PredictionSummary | episode function | messages/internal_summary.py |
| internal_summary.py | PredictionSummary.decision_context | episode function | messages/internal_summary.py internal_summary (decision_context); hpc_report_form not carried (report-form machinery) |
| portfolio_comparison.py | PortfolioComparison | episode function | task.py candidates, candidate_features, comparisons (library candidate) |
| portfolio_comparison.py | PortfolioComparison._candidates | episode function | task.py candidates (library candidate) |
| portfolio_comparison.py | PortfolioComparison._features | episode function | task.py candidate_features (library candidate) |
| portfolio_comparison.py | PortfolioComparison._comparisons | episode function | task.py comparisons (library candidate) |
| prediction_history.py | PredictionHistory | episode function | task.py history, shared_history (library candidate) |
| prediction_history.py | PredictionHistory._history | episode function | task.py history (library candidate) |
| prediction_history.py | PredictionHistory._shared_history | episode function | task.py shared_history (library candidate; the memory reads are the estimate_table service, BLOCKED-ON-JOB-SERVICE; the cut of the observations to 2000 is not carried) |
| prediction_operations.py | PredictionOperations | episode function | task.py TOOLS and tool functions |
| prediction_operations.py | PredictionOperations.catalog | episode function | task.py catalog |
| prediction_operations.py | PredictionOperations.execute | episode function | task.py hpc_read, hpc_history_refresh, hpc_discovery_run, hpc_candidate_propose, hpc_queue_observe, hpc_model_fit, hpc_compare; the old ledger.cached/save_action/once operation ledger, the schema validation (task.py action) and tool_not_available_to_hpc_role (LookupError of the system) are the system's |
| prediction_state.py | PredictionState | episode function | task.py read_ledger, check_owner, current_model; messages/internal_summary.py |
| prediction_state.py | PredictionState.state | episode function | task.py read_ledger and check_owner (the ledger opened by directory is the held work table hpc_evidence; the scope comparison is not carried) |
| prediction_state.py | PredictionState.initialize | episode function | messages/internal_summary.py (reference model = prior_model of the commission, entry model and entry quality computed from the rows named in ledger_refs); the initial model fitted from shared history is not carried (unplaced) |
| prediction_state.py | PredictionState._current_model | episode function | task.py current_model |
| queue_observations.py | QueueObservations | episode function | task.py observe_queue, queue_observation (library candidate) |
| queue_observations.py | QueueObservations._observe_queue | episode function | task.py observe_queue (library candidate; hpc_queue.observe and the memory are services, BLOCKED-ON-JOB-SERVICE) |
| queue_observations.py | QueueObservations._queue | episode function | task.py queue_observation (library candidate) |
| received_evidence.py | ReceivedEvidence | episode function | task.py read_evidence, _result_source_received (library candidate) |
| received_evidence.py | ReceivedEvidence._known | machinery | record_selection / received_record_refs hand-kept known set: replaced by records.holds / ctx.store.holds (README 3c) |
| received_evidence.py | ReceivedEvidence.resolve_received_reference | episode function | task.py _result_source_received (held source of provider episode.hpc_result, run id, scope validation without a parent scope) |
| received_evidence.py | ReceivedEvidence.read_evidence | episode function | task.py read_evidence (library candidate) |
| received_execution_information.py | received_execution_information | episode function | not placed: catalog.configured/received readers of the old execution information catalog are in no library module; listed in unplaced_old_functions |
| report_delivery.py | PredictionReportDelivery | machinery | report delivery: saved forms in runtime_forms, form_with_facts, release (report_form machinery, README 3b D1/D3) |
| report_delivery.py | PredictionReportDelivery.finish | machinery | runtime_forms save, form_with_facts, workflow.release, pending_handles; the result is final_to_parent (messages/final_to_parent.py) |
| task.py | ResourcePredictionTask | episode function | task.py decide, action |
| task.py | ResourcePredictionTask.next | episode function | task.py decide (journal replay, SourceEnd, restore_checkpoint, inprocess_replay and the transaction wrapping are machinery) |
| task.py | ResourcePredictionTask.apply_response | episode function | task.py action (validation of the answer and Rejected); the report_update admission, record_effect and report basis are machinery |
| task.py | ResourcePredictionTask.execute | episode function | task.py tool functions; the runtime_actions rows, journal.measure, receive_outcome, completions.stage, controller_value and ActionFailure are machinery |
| task_decision.py | PredictionTaskDecision | episode function | task.py decide; the exchange protocol is machinery |
| task_decision.py | PredictionTaskDecision.call | machinery | model call with runtime_model_calls rows, saved exchange replay and conversation state (README 3a) |
| task_decision.py | PredictionTaskDecision.instructions | episode function | task.py instructions |
| task_decision.py | PredictionTaskDecision.complete_decision | machinery | provider.complete wrapper with the prompt renderer (the system calls the provider for a ModelRequest) |
| task_decision.py | PredictionTaskDecision.conversation_key | machinery | conversation state (README 3a) |
| task_decision.py | PredictionTaskDecision.interpretation_context | machinery | decision-exchange loop: lookup results into the context (a lookup is a tool) |
| task_decision.py | PredictionTaskDecision.exchange_schema | machinery | decision-exchange loop schema (request_context / select_action) |
| task_decision.py | PredictionTaskDecision.exchange_response | machinery | decision-exchange loop envelope validation |
| task_decision.py | PredictionTaskDecision.validate_contract_exchange_request | machinery | saved-request check of the decision exchange (README 3a) |
| task_decision.py | PredictionTaskDecision.validate_contract_exchange_history | machinery | saved-request check of the decision exchange (README 3a) |
| task_decision.py | PredictionTaskDecision.exchange_decision | machinery | decision-exchange loop (exchange_decision), not carried |
| task_instructions.py | instructions | episode function | task.py instructions (goal text, ToolKnowledge and launch instruction INSTRUCTIONS when the libraries are configured) |
| task_state.py | PredictionTaskState | machinery | per-episode decision state with checkpoint/restore; the state is the view |
| task_state.py | PredictionTaskState.__init__ | machinery | state of the old decision source |
| task_state.py | PredictionTaskState.bind_execution_context | machinery | execution_binding / inprocess_replay binding |
| task_state.py | PredictionTaskState.record_execution_failure | machinery | record_execution_failure into runtime_actions rows (a failed tool returns its outcome) |
| task_state.py | PredictionTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | PredictionTaskState.restore | machinery | restore from runtime_actions and the journal |
| task_state.py | PredictionTaskState.record_effect | machinery | record_effect (the system journals each unit) |
| task_state.py | PredictionTaskState.checkpoint | machinery | checkpoint |
| to_parent.py | PredictionReport | episode function | messages/final_to_parent.py |
| to_parent.py | PredictionReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM |
| to_parent.py | PredictionReport.facts | episode function | messages/final_to_parent.py facts and final_to_parent (hpc_credit is completion['credit']) |
| to_parent.py | PredictionReport.resolve | episode function | messages/final_to_parent.py resolve_reference |
| to_parent.py | PredictionReport.validate_report | episode function | messages/final_to_parent.py validate_report; the validate_form step raises NotImplementedError(validate_form_not_built:A110) in final_to_parent |
| waiting.py | PredictionSuspension | machinery | wait/suspension machinery |
| waiting.py | PredictionSuspension.suspension_changed | machinery | suspension of the execution handle (wait/suspension machinery) |
| yield_estimator.py | HPCEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | HPCEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (accumulation controller; cutoff -> settings cost, parameters -> settings parameters) |
| yield_estimator.py | HPCEpisodeYield.continuation_for_action | machinery | episode-local continuation estimator packet (HPCContinuationEstimator, README 3d/7b); no other stop test |
| yield_estimator.py | HPCEpisodeYield.practical_estimator | machinery | episode-local estimator HPCContinuationEstimator (README 3d/7b) |
