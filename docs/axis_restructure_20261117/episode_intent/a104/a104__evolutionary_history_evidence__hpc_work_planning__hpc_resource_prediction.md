# a104 / evolutionary_history_evidence / hpc_work_planning / hpc_resource_prediction

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/hpc_work_planning/hpc_resource_prediction/<file>`. I read the 32 files directly in this folder. It has no `grading/` or `scoring/` subfolder. It has a `tests/` subfolder (`test_calculation_connections.py`, `test_prediction_behavior.py`, `test_prediction_prompt.py`, `test_prediction_task.py`), which I did not read because it is outside this task's scope.

## Purpose (its own words)
"Iterate on a generalized time/resource model using measured historical cases. Refresh shared history, inspect support and held-out quality, fit a disjoint training selection, and compare useful portfolios. Inspect missing capacity, launcher and queue facts with lightweight discovery; propose executable resource alternatives when the parent has not supplied them. Preparation and submission belong to the execution sister. Forecast CPU time and memory demand as well as queue, setup and work time. Compare node/worker counts, memory capacity, workload parameters and elapsed cost. The paired execution episode owns Launch, monitoring and parsing. Both sisters use this parent-owned ledger; preserve model and comparison identities for that sibling. The fixed reference and validation set cannot change. Model credit is modest measured improvement; the HPC parent later scores frozen predictions against real outcomes. Unknown inputs stay unknown. Return when further model improvement is less useful than running the next worthwhile portfolio." (`goal.py`)

## Task and instructions
- Role `hpc_prediction`. No entry roles. Commissioning parent `evolutionary_history_evidence/hpc_work_planning`. `replaces_default_instructions = True`.
- Instructions (`task_instructions.py`): the own goal + tool knowledge + launch instruction library. No reasoning-commit, redelivery, wait or exchange-history additions.

## What it reads from its parent's assignment
- `owner_episode_id` (required) plus `commission_id` (one of the configured commissions) or `commission_source_ref` (read through `hpc_commission_sources`), as a `oneOf` (`from_parent.py`).
- `prepare_assignment` requires the parent role to be `hpc`, the owner to be the parent episode, and the commission identity to equal the parent's. With a private yield binding, the commission must carry `yield_bindings`.
- The assignment opens the parent-owned HPC ledger at `<directory>/hpc/<digest(run_id, owner)>/hpc.sqlite`. The ledger's owner scope and commission identity must equal this assignment (`prediction_state.py`: "sister_scope_must_equal_original_parent_scope").

## Children
None.

## Decision state shown to the model
- Generic old-runner decision state (`decision_state.py`).
- Own `internal_summary.decision_context`: `hpc_commission`, `hpc_owner_episode_id`, `hpc_candidates`, `hpc_resource`, `hpc_tool_request`, `hpc_model_ref`, `hpc_credit`, `hpc_latest_comparison`, `hpc_model_support`, `hpc_report_form` (credit, model ref, result refs), `hpc_plans`, `hpc_latest_monitor`, `hpc_monitor_controllers`, `hpc_queue_refs`, optional `hpc_shared_memory` / `hpc_shared_history_refs`, and `hpc_available_training_ids` (history minus validation ids).
- `decision_inputs.py` adds resource context, the launch library and selected launch instructions, completed action reports, HPC requested-action history, pending work, `hpc_prediction` execution expectations and job execution options, resource/native estimates, and native event targets.
- Renderer `present_task_context` (`presentation.py`, `presentation_selection.py`): HPC prompt first, then published-scientific, API launch, selected execution, monitor or receiver.

## Tools (`prediction_operations.py`)
- `hpc.read`: read retained HPC evidence by identity (history row, ledger record, or an owned received `episode.hpc_result` source whose body equals its ledger receipt).
- `hpc.compare`: compare every approved portfolio for a `model_ref` and a `queue_ref`. It selects and launches nothing, and returns comparisons sorted by net expected value.
- `hpc.history.refresh` (only with shared memory): read the age-weighted shared timing history once.
- `hpc.discovery.run`: one lightweight remote inspection through the established SSH transport, run from `/lus/flare/projects/BioReason-Aurora-Test`. It submits, installs and computes nothing. stdout is capped at 64 KiB and stderr at 8 KiB, the subprocess has a 90 s timeout, and the result is cached in shared memory.
- `hpc.candidate.propose`: retain an executable portfolio (id, queue, nodes, wall_seconds, features, optional resource_capacity, units, files, preparation instructions). Candidate identities are immutable, and the commission is re-validated.
- `hpc.queue.observe`: acquire the PBS queue and ALCF score/status once, using a fresh shared-memory value within `queue_max_age_seconds`.
- `hpc.model.fit`: fit the selected measured history. Training must exclude the validation ids and precede the temporal validation set. Credit is quality − reference quality. Later-allocation training gets 0 now and earns prospective credit later.
- Only the common action `tool`. Actions are cached per operation key in the ledger (`ledger.cached` / `save_action` / `once`).

## Credit (`credit.py`)
- Kind `operational`.
- `credit = commission.credit.model_scale × (current model held-out quality − quality at this episode's entry) + Σ prospective validation contributions whose evidence names this prediction episode`.
- `actual_job_credit_counted_here: False`. Real outcomes are credited to the HPC parent.
- No bound, clamp or rescale.

## Continuation (`yield_estimator.py`)
- Private yield binding required. The commission's `yield_bindings[role]` supplies `cutoff` and `parameters`.
- YieldController with the practical HPC continuation estimator (`HPCContinuationEstimator`), given `with_continuation_cost(cutoff)`.
- `continuation_for_action` records a ledger `continuation` evidence with zero expected continuation credit when all of these hold:
  - there are no validation ids;
  - every available history case is already trained;
  - current comparisons exist for the current model and candidates;
  - the latest queue observation is fresh.
  - Reason: "prediction_ready_without_new_measured_improvement_opportunities". New observations reopen prediction. The verifier checks that the packet equals the ledger record.
- New estimator: **bounded quality** (held-out model quality improvement), with the zero-gain continuation evidence as its endpoint.

## What it reports to its parent (`to_parent.py`)
- Fact sources:
  - `hpc_credit` (signed measured credit; repeated polling adds none);
  - `hpc_model_ref` (namespace `hpc_model`);
  - `hpc_accepted_obligations` (obligations with accepted actual results);
  - `hpc_result_refs` (received result sources known to this episode).
- `validate_report`: the form must equal the recorded facts. `hpc_model` references resolve against the ledger. After closure, `closed_models.frozen_reference` authenticates them from the saved form facts and a read-only ledger.

## Differences from similar episodes
- Its goal, tools, credit, yield, assignment, report and ledger use are identical to A102's `structural_homology_evidence/hpc_work_planning/hpc_resource_prediction`, apart from module paths. Two things differ. (1) The renderer: A104 uses its own `present_task_context` state machine (HPC prompt first, then the other contexts). A102 uses `render_hpc_prompt` directly. (2) Decision inputs: A104 captures `hpc_prediction` execution expectations with the job assignment and planning scopes (prospective execution options/classes, `job_execution_options`) and adds `native_event_targets`. A102 calls `binding.capture('hpc_prediction')` only.
- A104 also splits the old task into `action_admission.py`, `action_execution.py`, `decision_contracts.py`, `decision_exchange.py` and `decision_provider.py`. That split is runner plumbing only.
- Its sister is `hpc_allocation_execution`. Both read and write the same parent-owned HPC ledger.

## Old-runner names (summary)
- `self.workflow.*` / `source.workflow.*` members: action_schema, archive, binding_context, catalog, completed_unit, completions, context, contract_information_profile, contract_information_reply, controller_binding, controller_value, decision_exchanges, decision_protocol, delivery_status, episode_bindings, execute, execution_backend, execution_binding, execution_expectations, execution_handle, extra_report_sources, facts, freeze_contract_information, grains, history_preview, inprocess_replay, job_episode_options, job_episodes, journal, knowledge, launch_instructions, local_outcome_preview, native_estimation_context, native_event_information, numerical_contracts, pending_handles, pending_work, progress_provider, provider, receipt_projection, receipts, receive_native_outcome, receive_outcome, recover_commissions, release, resolver, resource_context, resource_estimator, run_id, selected, services, source_credit_binding, source_credit_view, specialist, store, tools, uses_received_record_context, validate_contract_information, validate_report, working_state.
- Old-runner imports: runtime, providers (ModelCallError, presentation identities), root.providers, communication, episode_bindings (`reference_in_context`), numerical (YieldController, YieldParameters), library.hpc_continuation (HPCContinuationEstimator), episode_return_records, episode_source_failure, episode_work_report, library.live_runtime_functions (`bind_functions`), plus old shared-root modules hpc_ledger (HPCLedger), hpc_queue, hpc_campaign, hpc_commission_sources, execution_memory, execution_guidance, execution_contracts, domain, library.hpc_prediction, library.hpc_resource_prediction, library.hpc_prompt, library.monitor_prompt, receiver_prompt, native_profile_presentation, evolutionary_history_evidence_prompt.
- Journal tables: runtime_actions, runtime_model_calls, runtime_forms, runtime_episodes. The HPC ledger is its own sqlite (`evidence` table), not a runner table.
- Old services callbacks: `record_selection`, `instructions`, `decision_exchange_instructions`.

## File by file

| old file | lines | this episode's own intent | old-runner names used |
|---|---|---|---|
| action_admission.py | 61 | Old-runner response admission; report grain `hpc_prediction`. Generic runner plumbing. | `import:library.live_runtime_functions`, `import:runtime`×2, `name:bind_functions`×2, `name:SourceEnd`, `self.workflow.decision_exchanges`×3, `self.workflow.execution_binding`, `self.workflow.journal`×2, `self.workflow.resolver`, `self.workflow.selected`, `self.workflow.store`, `self.workflow.validate_report`, `table:runtime_actions`, `table:runtime_model_calls` |
| action_execution.py | 66 | Old-runner action execution, result journal, credit, controller staging; adds `pending_work_after_action`. Generic runner plumbing. | `import:library.live_runtime_functions`, `import:runtime`×2, `name:bind_functions`×2, `name:SourceEnd`, `self.workflow.completions`, `self.workflow.controller_value`×2, `self.workflow.execute`, `self.workflow.execution_binding`×4, `self.workflow.journal`, `self.workflow.pending_work`, `self.workflow.receive_native_outcome`, `self.workflow.receive_outcome`, `self.workflow.run_id`, `self.workflow.source_credit_view`, `self.workflow.store`×3, `table:runtime_actions`×5 |
| binding_record.py | 12 | Binding identity `evolutionary_history_evidence/hpc_work_planning/hpc_resource_prediction`, `hpc_episode_v1`, configuration (resources, commissions, shared_execution_memory, require_commission_yield). | none |
| closed_models.py | 29 | `frozen_reference`: authenticates a closed `hpc_model` reference against saved form facts and the read-only parent HPC ledger. | `import:communication`, `import:episode_return_records`, `import:hpc_queue`, `name:EpisodeReturnRecords`×2, `table:runtime_forms` |
| configuration.py | 30 | Requires explicit commissions and at least one `pbs_ssh` resource; validates commissions; optional private yield binding (every commission must carry `yield_bindings`); optional shared ExecutionMemory. | `import:communication`, `import:execution_memory`, `import:hpc_campaign` |
| credit.py | 31 | Credit kind `operational`. credit = model_scale × (current held-out quality − quality at this episode's entry) + prospective validation credit attributed to this prediction episode; actual job credit is not counted here. | `import:library` |
| decision_contracts.py | 128 | Old decision-exchange envelope/replay validation. Generic runner plumbing. | `import:library.live_runtime_functions`, `import:runtime`×2, `name:bind_functions`×2, `self.workflow.contract_information_reply`, `self.workflow.decision_exchanges`×2, `self.workflow.journal`, `self.workflow.store`×2, `self.workflow.validate_contract_information`×2, `table:runtime_model_calls` |
| decision_exchange.py | 107 | Old multi-exchange decision loop. Generic runner plumbing. | `import:library.live_runtime_functions`, `import:runtime`×2, `name:bind_functions`×2, `self.workflow.controller_binding`, `self.workflow.decision_exchanges`, `self.workflow.execute`, `self.workflow.journal`, `self.workflow.run_id`, `self.workflow.services`, `self.workflow.validate_contract_information`, `table:runtime_model_calls`×2 |
| decision_inputs.py | 68 | Adds resource context, launch library, initial binding context, completed action reports, HPC requested-action history, pending work, `hpc_prediction` execution expectations and job options, resource/native estimates, native event targets. | `import:episode_work_report`×2, `import:library.hpc_prompt`, `import:library.live_runtime_functions`, `import:runtime`, `name:bind_functions`×2, `name:binding_context`×2, `self.workflow.binding_context`×2, `self.workflow.episode_bindings`, `self.workflow.execution_expectations`, `self.workflow.job_episodes`×2, `self.workflow.launch_instructions`×2, `self.workflow.native_estimation_context`, `self.workflow.native_event_information`×2, `self.workflow.pending_work`, `self.workflow.resource_context`, `self.workflow.resource_estimator`×4, `self.workflow.store`×2 |
| decision_provider.py | 61 | Old provider-identity sniffing to pass the own renderer. Generic runner plumbing. | `import:providers`×2, `import:root.providers`, `import:runtime`, `self.workflow.provider`, `self.workflow.specialist`×2 |
| decision_state.py | 40 | Old-runner decision state assembly plus the specialist decision context. Generic runner plumbing. | `import:library.live_runtime_functions`, `import:runtime`×2, `name:bind_functions`×2, `name:binding_context`, `self.workflow.binding_context`, `self.workflow.catalog`, `self.workflow.controller_binding`, `self.workflow.delivery_status`, `self.workflow.extra_report_sources`, `self.workflow.job_episode_options`, `self.workflow.journal`×2, `self.workflow.knowledge`, `self.workflow.local_outcome_preview`, `self.workflow.pending_work`, `self.workflow.receipt_projection`, `self.workflow.run_id`, `self.workflow.source_credit_binding`, `self.workflow.source_credit_view`, `self.workflow.specialist`, `self.workflow.store`×3, `self.workflow.tools`, `self.workflow.working_state`, `table:runtime_actions` |
| episode.py | 38 | `HPCEpisode`: role `hpc_prediction`, no entry roles, no children, commissioning parent `evolutionary_history_evidence/hpc_work_planning`, `replaces_default_instructions`, common action `tool` only, renderer `present_task_context`. | none |
| from_parent.py | 44 | Assignment: `owner_episode_id` + `commission_id` or `commission_source_ref` (oneOf). Must belong to its original `hpc` parent (same owner, same commission identity); private yield requires commission `yield_bindings`. | `import:communication`, `import:domain`, `import:execution_contracts`, `import:hpc_commission_sources` |
| goal.py | 20 | The goal text (see Purpose). | none |
| __init__.py | 0 | Empty package marker. | none |
| internal_summary.py | 36 | Decision context: commission, owner, candidates, resource, tool requests, current model ref, credit view, latest comparison, model support, HPC report form, plans, latest monitor, monitor controllers, queue refs, shared memory/history refs, available training ids. | `import:library` |
| portfolio_comparison.py | 31 | Candidates = commission candidates + proposed; features; comparisons sorted by net expected value using model forecast against obligations/preferences, excluding already-credited obligations. | `import:hpc_queue`, `import:library` |
| prediction_history.py | 63 | Training history: commission history + latest shared-history snapshot + one latest measured observation per closed allocation (censored on failure); shared-history query by execution profile with queue pooling rules, ≤2000 rows. | `import:execution_guidance`, `import:library.hpc_resource_prediction` |
| prediction_operations.py | 147 | Tools `hpc.read`, `hpc.compare`, `hpc.history.refresh` (with memory), `hpc.discovery.run`, `hpc.candidate.propose`, `hpc.queue.observe`, `hpc.model.fit`; ledger-cached idempotent actions; fit validates temporal disjoint training and credits quality−baseline. | `import:communication`, `import:domain`, `import:execution_contracts`, `import:execution_guidance`, `import:hpc_campaign`, `import:hpc_queue`, `import:library` |
| prediction_state.py | 43 | Opens the parent-owned HPC ledger (sister scope check), initializes the reference prior model, optional shared-history initial fit, entry quality record. | `import:communication`, `import:domain`, `import:hpc_ledger`, `import:hpc_queue`, `import:library` |
| presentation.py | 42 | Prompt renderer state machine (decision_bootstrap/update/lookup_result). | `import:providers` |
| presentation_selection.py | 30 | Renderer selection (HPC, published-scientific, API launch, selected execution, monitor, receiver). | `import:evolutionary_history_evidence_prompt`×2, `import:library.hpc_prompt`, `import:library.monitor_prompt`, `import:native_profile_presentation`, `import:providers`, `import:receiver_prompt` |
| queue_observations.py | 27 | PBS queue observation with fresh shared-memory cache bounded by commission `queue_max_age_seconds`; freshness check. | `import:execution_guidance`, `import:hpc_queue` |
| received_evidence.py | 51 | Known refs; resolves received `episode.hpc_result` sources in scope; `read_evidence` (history, ledger, or owned result source with receipt equality). | `import:communication` |
| report_delivery.py | 32 | Old-runner `finish` with `runtime_forms`. Generic runner plumbing. | `import:library.live_runtime_functions`, `import:runtime`×2, `name:bind_functions`×2, `name:binding_context`, `self.workflow.binding_context`, `self.workflow.episode_bindings`, `self.workflow.facts`, `self.workflow.journal`×2, `self.workflow.pending_handles`, `self.workflow.release`×2, `self.workflow.source_credit_view`, `table:runtime_forms`×2 |
| task_decision.py | 92 | Old-runner model call/journal. Generic runner plumbing. | `import:library.live_runtime_functions`, `import:runtime`×2, `name:bind_functions`×2, `self.workflow.contract_information_profile`, `self.workflow.decision_exchanges`, `self.workflow.decision_protocol`×3, `self.workflow.freeze_contract_information`, `self.workflow.history_preview`, `self.workflow.journal`, `self.workflow.numerical_contracts`, `self.workflow.provider`×2, `self.workflow.receipts`×4, `self.workflow.services`, `self.workflow.uses_received_record_context`×2, `self.workflow.validate_contract_information`×2, `table:runtime_model_calls`×5 |
| task_instructions.py | 11 | Instructions = own goal (via specialist) + tool knowledge + launch library (no reasoning/redelivery/wait additions). | `name:binding_context`, `source.workflow.binding_context`, `source.workflow.knowledge`, `source.workflow.launch_instructions`, `source.workflow.specialist` |
| task.py | 85 | Old-runner `next` loop. Generic runner plumbing. | `import:episode_source_failure`, `import:library.live_runtime_functions`, `import:providers`, `import:runtime`×2, `name:bind_functions`×2, `name:SourceEnd`×3, `self.workflow.action_schema`, `self.workflow.completed_unit`, `self.workflow.completions`, `self.workflow.execution_binding`×2, `self.workflow.inprocess_replay`×4, `self.workflow.journal`×4, `self.workflow.run_id`, `self.workflow.selected`×2, `self.workflow.store`×3, `table:runtime_actions`×2, `table:runtime_episodes`, `table:runtime_model_calls` |
| task_state.py | 117 | Old-runner state/restore/checkpoint (failure kinds `tool` only). Generic runner plumbing. | `import:episode_source_failure`, `import:library.live_runtime_functions`, `import:runtime`×2, `name:ActionLeaf`×2, `name:bind_functions`×2, `name:Episode.identity`, `self.workflow.archive`, `self.workflow.completions`×4, `self.workflow.controller_value`, `self.workflow.execution_binding`×4, `self.workflow.inprocess_replay`×7, `self.workflow.journal`×5, `self.workflow.progress_provider`×2, `self.workflow.recover_commissions`, `self.workflow.run_id`, `self.workflow.source_credit_view`, `self.workflow.store`×2, `table:runtime_actions`×5, `workflow.context`, `workflow.grains` |
| to_parent.py | 40 | Fact sources `hpc_credit`, `hpc_model_ref`, `hpc_accepted_obligations`, `hpc_result_refs`; `validate_report` requires form to equal recorded facts. | `import:communication`, `import:episode_bindings` |
| waiting.py | 9 | Old-runner suspension hook. Generic runner plumbing. | `self.workflow.execution_backend`, `self.workflow.execution_handle`×2 |
| yield_estimator.py | 60 | Private yield required; commission `yield_bindings[role]` gives cutoff+parameters; practical HPC continuation estimator with continuation cost; `continuation_for_action` records a zero-gain continuation evidence once no held-out cases, all available history trained, and current comparisons with a fresh queue exist. | `import:library.hpc_continuation`, `import:numerical`, `name:HPCContinuationEstimator`×2, `name:YieldController`×2, `name:YieldParameters`×2 |

## Carried over

Old files at 97308b94c (`episodic_workflow/root/a104/evolutionary_history_evidence/hpc_work_planning/hpc_resource_prediction/`), one row per function, class and method of `runs/carry_over/functions/a104__evolutionary_history_evidence__hpc_work_planning__hpc_resource_prediction.tsv`. New files are in the episode folder `gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/hpc_work_planning/hpc_resource_prediction/`. Rows marked "library candidate" stay in the episode file that uses them (no new file under `episode_support/` in this step). Old library modules the episode calls are already in `episode_support/` and are imported by name (`jobs/hpc/evolutionary_history_evidence/hpc_prediction.py`, `hpc_resource_prediction.py`, `hpc_campaign.py`, `jobs/hpc/hpc_queue.py`, `instructions/evolutionary_history_evidence/execution_guidance.py`, `instructions/launch_instructions.py`, `tools/tool_knowledge.py`, `model_exchange/evolutionary_history_evidence/action_transport.py`, `model_exchange/rejection_feedback.py`, `model_exchange/presentation.py`, `records/progress_views.py`, `forms/evolutionary_history_evidence/{communication,execution_contracts}.py`). Machinery rows give their reason.

| old file | name | kind (machinery or episode function) | new place, or machinery reason |
|---|---|---|---|
| action_admission.py | ResourcePredictionTaskAdmission | machinery | old-runner response admission (journal rows, decision exchanges, report_update); replaced by the system loop and `action` (task.py) |
| action_admission.py | ResourcePredictionTaskAdmission.apply_response | machinery | old-runner response admission (journal rows, decision exchanges, report_update); replaced by the system loop and `action` (task.py) |
| action_admission.py | _bind_preserved_runtime_providers | machinery | provider patching (`bind_functions`); deleted |
| action_execution.py | ResourcePredictionTaskExecution | machinery | old-runner action execution, result journal, credit and controller staging, pending_work_after_action; replaced by the system loop, tool units and `credit` |
| action_execution.py | ResourcePredictionTaskExecution.execute | machinery | old-runner action execution, result journal, credit and controller staging, pending_work_after_action; replaced by the system loop, tool units and `credit` |
| action_execution.py | _bind_preserved_runtime_providers | machinery | provider patching (`bind_functions`); deleted |
| binding_record.py | PredictionBindingRecord | machinery | binding identity as_record() of the old binding; deleted (README 3e) |
| binding_record.py | PredictionBindingRecord.as_record | machinery | binding identity as_record() of the old binding; deleted (README 3e) |
| closed_models.py | ClosedModels | machinery | re-validation of a closed model identity from the saved closure form (runtime_forms, EpisodeReturnRecords) and a read-only ledger connection; the system admits the result and `final_to_parent` checks it |
| closed_models.py | ClosedModels.frozen_reference | machinery | re-validation of a closed model identity from the saved closure form (runtime_forms, EpisodeReturnRecords) and a read-only ledger connection; the system admits the result and `final_to_parent` checks it |
| configuration.py | PredictionConfiguration | episode function | task.py: `resources_of`, `memory_configured` (settings); the commission check is the ledger records read; `require_commission_yield` and `directory` not carried |
| configuration.py | PredictionConfiguration.__init__ | episode function | task.py: `resources_of` (at least one pbs_ssh resource), `memory_configured` (shared_execution_memory setting); commissions, directory, require_commission_yield not carried (library candidate) |
| credit.py | HPCEpisodeCredit | episode function | credit.py: `credit_view`, `credit` |
| credit.py | HPCEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d); the kind text is `CREDIT_BINDING` in task.py |
| credit.py | HPCEpisodeCredit._quality | episode function | task.py: `model_quality` (library candidate; the fit tool uses it too) |
| credit.py | HPCEpisodeCredit.credit_view | episode function | credit.py: `credit_view`; `credit(summary, records)` returns its credit |
| decision_contracts.py | PredictionTaskDecisionContracts | machinery | old decision-exchange envelope and replay validation (saved-request checks); deleted, the system compares a rebuilt model request with its record |
| decision_contracts.py | PredictionTaskDecisionContracts.interpretation_context | machinery | old decision-exchange envelope and replay validation (saved-request checks); deleted, the system compares a rebuilt model request with its record |
| decision_contracts.py | PredictionTaskDecisionContracts.exchange_schema | machinery | old decision-exchange envelope and replay validation (saved-request checks); deleted, the system compares a rebuilt model request with its record |
| decision_contracts.py | PredictionTaskDecisionContracts.exchange_response | machinery | old decision-exchange envelope and replay validation (saved-request checks); deleted, the system compares a rebuilt model request with its record |
| decision_contracts.py | PredictionTaskDecisionContracts.validate_contract_exchange_request | machinery | old decision-exchange envelope and replay validation (saved-request checks); deleted, the system compares a rebuilt model request with its record |
| decision_contracts.py | PredictionTaskDecisionContracts.validate_contract_exchange_history | machinery | old decision-exchange envelope and replay validation (saved-request checks); deleted, the system compares a rebuilt model request with its record |
| decision_contracts.py | _bind_preserved_runtime_providers | machinery | provider patching (`bind_functions`); deleted |
| decision_exchange.py | PredictionTaskDecisionExchange | machinery | old multi-exchange decision loop (exchange_decision); not carried, a lookup is a tool |
| decision_exchange.py | PredictionTaskDecisionExchange.exchange_decision | machinery | old multi-exchange decision loop (exchange_decision); not carried, a lookup is a tool |
| decision_exchange.py | _bind_preserved_runtime_providers | machinery | provider patching (`bind_functions`); deleted |
| decision_inputs.py | PredictionDecisionInputs | episode function | task.py: `decide`, `execution_context`; messages/internal_summary.py: completed_action_reports, history |
| decision_inputs.py | PredictionDecisionInputs.decision_inputs | episode function | task.py `decide` (launch library, selected launch instructions, initial information, requested_action_history, completed_action_reports) and `execution_context` (execution_expectations, job_execution_options, resource_tool_estimates, native_event_targets: BLOCKED-ON-JOB-SERVICE service reads); pending_work, contract_information_profile, binding_context not carried (machinery) |
| decision_inputs.py | _bind_preserved_runtime_providers | machinery | provider patching (`bind_functions`); deleted |
| decision_provider.py | PredictionTaskDecisionProvider | machinery | provider-identity sniffing and presentation patching; deleted with provider patching |
| decision_provider.py | PredictionTaskDecisionProvider.decision_completion | machinery | provider-identity sniffing and presentation patching; deleted with provider patching |
| decision_state.py | PredictionDecisionState | episode function | messages/internal_summary.py: `internal_summary` (last outcome, history, controller state as `action_yields`); the rest of the old state assembly is machinery |
| decision_state.py | PredictionDecisionState.decision_state | episode function | messages/internal_summary.py `internal_summary` and task.py `decide` (goal, current_credit, credit_binding, last_local_outcome, tools, tool_knowledge, time_accounting, action_yields, feedback); visual_evidence, report_deliveries, pending_work, available_report_facts, requested_form, current_report_update/basis, report_lifecycle, job_episode_options, restored_episode_history: machinery or not carried |
| decision_state.py | _bind_preserved_runtime_providers | machinery | provider patching (`bind_functions`); deleted |
| episode.py | HPCEpisode | episode function | episode.py: class HPCResourcePrediction(EpisodeBinding); goal.py BINDING_PATH; role hpc_prediction, entry_roles, replaces_default_instructions are old-runner declarations (not carried) |
| episode.py | HPCEpisode.child_roles | episode function | task.py: CHILD_SLOTS = {} (no children) |
| episode.py | HPCEpisode.allowed_children | machinery | old child-role lookup (README C2); replaced by CHILD_SLOTS = {} |
| episode.py | HPCEpisode.permitted_common_actions | episode function | task.py: the only unit is a tool call (the schema of `selection_schema` offers tools only) |
| from_parent.py | PredictionAssignment | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM, `commission_identity`, `read_from_parent` |
| from_parent.py | PredictionAssignment.assignment_schema | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM (owner_episode_id; commission_id or commission_source_ref; new: ledger_refs, yield_binding) |
| from_parent.py | PredictionAssignment.commission_identity | episode function | messages/read_from_parent.py: `commission_identity` |
| from_parent.py | PredictionAssignment._commission | episode function | task.py: `ledger_commission` (the commission is the ledger commission record; the old hpc_commission_sources.read and the static commissions table are not carried) |
| from_parent.py | PredictionAssignment.prepare_assignment | episode function | messages/read_from_parent.py: `read_from_parent` (exactly one commission identity); the parent/owner/commission-identity refusal and the yield_bindings check are checks of a commission and are not carried (rule 1) |
| goal.py | PredictionGoal | episode function | goal.py: GOAL, UNIT, RESULT |
| goal.py | PredictionGoal.instructions | episode function | goal.py: GOAL (text unchanged); composed into the instructions by task.py `instructions` |
| internal_summary.py | PredictionSummary | episode function | messages/internal_summary.py: `ledger_state`, `internal_summary` |
| internal_summary.py | PredictionSummary.decision_context | episode function | messages/internal_summary.py: `ledger_state` (hpc_commission ... hpc_available_training_ids); hpc_resource and hpc_shared_memory in task.py `decide`; hpc_report_form not carried (RETURN_FORM replaces it) |
| portfolio_comparison.py | PortfolioComparison | episode function | task.py: `candidates`, `candidate_features`, `comparisons` |
| portfolio_comparison.py | PortfolioComparison._candidates | episode function | task.py: `candidates` (library candidate) |
| portfolio_comparison.py | PortfolioComparison._features | episode function | task.py: `candidate_features` (library candidate) |
| portfolio_comparison.py | PortfolioComparison._comparisons | episode function | task.py: `comparisons` (library candidate) |
| prediction_history.py | PredictionHistory | episode function | task.py: `history_cases`, `shared_history` |
| prediction_history.py | PredictionHistory._history | episode function | task.py: `history_cases` (library candidate) |
| prediction_history.py | PredictionHistory._shared_history | episode function | task.py: `shared_history` (library candidate; estimate_table reads are BLOCKED-ON-JOB-SERVICE) |
| prediction_operations.py | PredictionOperations | episode function | task.py: CATALOG, TOOLS and the tool functions |
| prediction_operations.py | PredictionOperations.catalog | episode function | task.py: CATALOG, `operation_catalog` |
| prediction_operations.py | PredictionOperations.execute | episode function | task.py: tools `hpc_read`, `hpc_history_refresh`, `hpc_discovery_run`, `hpc_candidate_propose`, `hpc_queue_observe`, `hpc_model_fit`, `hpc_compare` (and `hpc_initialize`); the ledger.cached/save_action/action_intent operation cache is machinery (the system journals the unit under ctx.operation_key) |
| prediction_state.py | PredictionState | episode function | task.py: `state_of`, `initialize`, `current_model`, ledger primitives |
| prediction_state.py | PredictionState.state | episode function | task.py: `state_of` (owner, commission, resource); opening the ledger by path is BLOCKED-ON-JOB-SERVICE (the ledger primitives); the sister-scope comparison is not carried |
| prediction_state.py | PredictionState.initialize | episode function | task.py: `initialize`, the first unit tool `hpc_initialize` |
| prediction_state.py | PredictionState._current_model | episode function | task.py: `current_model` (library candidate) |
| presentation.py | present_task_context | episode function | not placed: the renderer state machine over old shared-root prompt renderers (render_hpc_prompt, ...) and provider state frames; the context travels as the ModelRequest.context mapping (see unplaced in the blocked file) |
| presentation_selection.py | task_presentation_selection | episode function | not placed: renderer selection (is_hpc_context, render_hpc_prompt, render_monitor_prompt, ...) lives in the old shared root; see the blocked file |
| queue_observations.py | QueueObservations | episode function | task.py: `observed_queue`, `queue_snapshot` |
| queue_observations.py | QueueObservations._observe_queue | episode function | task.py: `observed_queue` (the acquisition is BLOCKED-ON-JOB-SERVICE job_access.observe_queue; the cache read/write is estimate_table) |
| queue_observations.py | QueueObservations._queue | episode function | task.py: `queue_snapshot` (library candidate) |
| received_evidence.py | ReceivedEvidence | episode function | task.py: `resolve_result_source`, `read_evidence` |
| received_evidence.py | ReceivedEvidence._known | machinery | the set of received record references; custody (`holds`) |
| received_evidence.py | ReceivedEvidence.resolve_received_reference | episode function | task.py: `resolve_result_source` (held source of provider episode.hpc_result whose body belongs to this run); scope comparison is custody |
| received_evidence.py | ReceivedEvidence.read_evidence | episode function | task.py: `read_evidence` |
| report_delivery.py | PredictionReportDelivery | machinery | old report finish with runtime_forms, release and pending_handles; replaced by `final_to_parent` |
| report_delivery.py | PredictionReportDelivery.finish | machinery | old report finish with runtime_forms, release and pending_handles; replaced by `final_to_parent` |
| report_delivery.py | _bind_preserved_runtime_providers | machinery | provider patching (`bind_functions`); deleted |
| task.py | ResourcePredictionTask | machinery | old runner `next` loop (journal rows, replay, SourceEnd); replaced by the system loop (`decide`, `action`) |
| task.py | ResourcePredictionTask.next | machinery | old runner `next` loop (journal rows, replay, SourceEnd); replaced by the system loop (`decide`, `action`) |
| task.py | _bind_preserved_runtime_providers | machinery | provider patching (`bind_functions`); deleted |
| task_decision.py | PredictionTaskDecision | machinery | old runner model call with journal, receipts, contract-information freezing and session state; replaced by `decide` returning a ModelRequest (the instruction composer is carried, see task_instructions.py) |
| task_decision.py | PredictionTaskDecision.call | machinery | old runner model call with journal, receipts, contract-information freezing and session state; replaced by `decide` returning a ModelRequest (the instruction composer is carried, see task_instructions.py) |
| task_decision.py | PredictionTaskDecision.instructions | machinery | old composer call through workflow.services.instructions; the composition is `instructions` in task.py |
| task_decision.py | PredictionTaskDecision.conversation_key | machinery | old runner model call with journal, receipts, contract-information freezing and session state; replaced by `decide` returning a ModelRequest (the instruction composer is carried, see task_instructions.py) |
| task_decision.py | _bind_preserved_runtime_providers | machinery | provider patching (`bind_functions`); deleted |
| task_instructions.py | instructions | episode function | task.py: `instructions(*, knowledge, launch_library)` (own goal + tool knowledge + launch library) |
| task_state.py | PredictionTaskState | machinery | old state/restore/checkpoint/record_effect and failure recording; deleted (system journal and resume) |
| task_state.py | PredictionTaskState.__init__ | machinery | old state/restore/checkpoint/record_effect and failure recording; deleted (system journal and resume) |
| task_state.py | PredictionTaskState.bind_execution_context | machinery | old state/restore/checkpoint/record_effect and failure recording; deleted (system journal and resume) |
| task_state.py | PredictionTaskState.record_execution_failure | machinery | old state/restore/checkpoint/record_effect and failure recording; deleted (system journal and resume) |
| task_state.py | PredictionTaskState.restore_checkpoint | machinery | old state/restore/checkpoint/record_effect and failure recording; deleted (system journal and resume) |
| task_state.py | PredictionTaskState.restore | machinery | old state/restore/checkpoint/record_effect and failure recording; deleted (system journal and resume) |
| task_state.py | PredictionTaskState.record_effect | machinery | old state/restore/checkpoint/record_effect and failure recording; deleted (system journal and resume) |
| task_state.py | PredictionTaskState.checkpoint | machinery | old state/restore/checkpoint/record_effect and failure recording; deleted (system journal and resume) |
| task_state.py | _bind_preserved_runtime_providers | machinery | provider patching (`bind_functions`); deleted |
| to_parent.py | PredictionReport | episode function | messages/final_to_parent.py: RETURN_FORM, `validate_report`, `final_to_parent`; messages/internal_summary.py: `facts` |
| to_parent.py | PredictionReport.fact_sources | episode function | messages/final_to_parent.py: RETURN_FORM fields hpc_credit, hpc_model_ref, hpc_accepted_obligations, hpc_result_refs (selectable) and REPORT_SCHEMAS |
| to_parent.py | PredictionReport.facts | episode function | messages/internal_summary.py: `facts`; `final_to_parent` returns them for the selected fields (hpc_credit is completion credit) |
| to_parent.py | PredictionReport.resolve | episode function | messages/final_to_parent.py: the `resolve` of `validate_report` (hpc_model against summary model_ids; sources against held result refs) |
| to_parent.py | PredictionReport.validate_report | episode function | messages/final_to_parent.py: `validate_report` (validate_form of the evolutionary_history library, then the agreement with the recorded facts), called by `final_to_parent` |
| waiting.py | PredictionSuspension | machinery | old suspension hook (execution_handle, set_suspension); wait machinery, deleted |
| waiting.py | PredictionSuspension.suspension_changed | machinery | old suspension hook (execution_handle, set_suspension); wait machinery, deleted |
| yield_estimator.py | HPCEpisodeYield | episode function | yield_estimator.py: `yield_controller` (AccumulationYieldController) |
| yield_estimator.py | HPCEpisodeYield.yield_controller | episode function | yield_estimator.py: `yield_controller` (yield_bindings[hpc_prediction] -> parent_input yield_binding; cutoff is the cost) |
| yield_estimator.py | HPCEpisodeYield.continuation_for_action | machinery | zero-continuation packet and its ledger evidence for the HPCContinuationEstimator; an episode cannot supply a forecast (README 3d, 7b); nothing but the controller stops the Episode |
| yield_estimator.py | HPCEpisodeYield.practical_estimator | machinery | HPCContinuationEstimator verifying the packet against the ledger; deleted (README 7b) |
