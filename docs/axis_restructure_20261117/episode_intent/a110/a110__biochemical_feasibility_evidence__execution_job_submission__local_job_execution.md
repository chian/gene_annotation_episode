# a110/biochemical_feasibility_evidence/execution_job_submission/local_job_execution — episode intent at 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a110/biochemical_feasibility_evidence/execution_job_submission/local_job_execution/<file>`. All files directly in this folder (no subfolders). 28 files, 1,965 lines. Its files are copies of `hpc_job_execution`'s with the differences listed below; everything not listed is the same.

Names in the tables: `workflow.<member>` = the old runner object (`self.workflow` / `source.workflow`); `services.<member>` = old services callback; `import:<module>` = old shared `root/a110/<module>`; `table:<name>` = old journal/receipt table.

## Purpose (own words)

The A110 local resource executor (role `launch_local`): run the one concrete job assigned by the launch parent on a configured `local` resource by choosing and running shell commands, until the requested endpoint is validated. It is the leaf where native flux-balance (FBA) jobs run (FBA resources must be local). Instructions are its own `terminal_execution.TerminalExecutionBehavior.instructions` (identical text to the hpc leaf: "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job ... The episode iterator decides continuation from credit; add no stopping budget.") plus the frozen resource instruction sections; `replaces_default_instructions = True`.

## Task and instructions

As `hpc_job_execution`: terminal text replaces the default; tool knowledge; launch library; pending-child redelivery; decision-exchange history replacement; no reasoning or wait paragraphs. Shared-shape loop with `native_decision_snapshot` and `perform_selected_native_wait`.

## What it reads from its parent's assignment

`assignment_schema(role)`: `anyOf` concrete request schemas of configured resources of kind local (practical `ASSIGNMENT_SCHEMA`, resource consts, generic or FBA requested job; for a local FBA resource also the compact FBA resource-assignment alternative). No frozen-enum restriction. `prepare_assignment`: a **compact FBA assignment** is accepted when the parent is `launch`: it must match a row of the launch's request binding, and that row's FBA inputs and input versions are checked; otherwise the request is validated, its kind must be local, the parent must be `launch`, and FBA inputs/input versions are checked against the parent's launch assignment. Initialisation re-checks the recorded parent launch inputs, initialises FBA inputs when the requested job is FBA.

## Children it may commission

None.

## Decision state and what the model sees

Terminal decision context (assignment, resource, coordinator workspace, execution progress, completion) and `execution_resource_information`; plus `selected_execution_task` for FBA requests — for a compact assignment from the request binding, and also for an ordinary single request (`{resource_id: assignment}`), so the model sees the scientific question, selected tool info, the FBA job view and resource information. For a compact assignment: `practical_assignment`, `practical_progress`, `practical_completed`. Plus the common decision state.

## Tools offered

`tool` only; catalog `operation_catalog('local')`; commands run through the local `TerminalExecution`, recorded in practical state, finalised, validated, published as practical receipts; compact FBA outcomes are shown through `practical_outcome_view`.

## Credit

`operational`; closed view reused when closed; otherwise the practical-state credit view of the assigned resource. Unbounded.

## Continuation

Accumulation: `task_yield_profiles['launch_local:' + request class]` → `YieldController(..., estimate_with_context=PracticalYieldEstimator(verify_completion))`; requires `require_private_yield`. `practical_estimator` for a non-compact assignment is the terminal behaviour's own estimator.

## Report to parent

As `hpc_job_execution`: practical facts, handoff refs including its own returnable practical receipts, result/file facts, result origin, completed flag, FBA fact sources, closed credit snapshot; no required return sources.

## Differences from similar episodes

- Versus `hpc_job_execution`: `binding_path`/`binding_id`/reader path `.../local_job_execution`, role `launch_local`; accepts compact FBA assignments from `launch`; no frozen-request `enum` under an hpc ancestor; shows the selected FBA task for an ordinary single request as well; yield profile key `launch_local:<class>`.
- FBA (`native_flux_balance`) is accepted only on local resources, so this leaf, unlike its hpc sibling, is where A110's flux-balance execution happens.

## Files

| Old file | Lines | This episode's own intent | Old-runner names used (uses) |
|---|---|---|---|
| __init__.py | 0 | empty | none |
| binding_record.py | 8 | `as_record` with binding_id `.../local_job_execution` (same configuration fields as launch). | none |
| completion.py | 49 | `completion_for_action` delegated to the resource's terminal behaviour; closed verdict reuse; `verify_completion` against practical state. | `import:episode_return_records`, `import:flux_balance_request_binding`, `import:method_loop.identities`, `import:numerical`, `import:practical_yield`, `table:runtime_observations`, `yield:NumericBand`×2 |
| configuration.py | 73 | Same operands and construction as launch (resources, units, logs, yield profiles, terminal behaviours, progress provider, FBA readers; FBA rejected on non-local resources). | `import:execution_progress`, `import:flux_balance_execution_inputs`, `import:flux_balance_request_binding`, `import:flux_balance_returns`, `import:library.received_execution_information.received_result_readers`, `import:native_flux_balance_bindings`, `import:native_flux_balance_results`, `import:numerical`, `yield:YieldController`×3, `yield:YieldParameters`×3 |
| credit.py | 136 | Operational credit: closed-view reuse; live credit delegated to the practical state of the assigned resource (`TerminalExecutionBehavior.credit_view`). | `import:episode_receipts`, `import:episode_return_records`×3, `table:runtime_episodes`×2, `table:runtime_forms`×3, `table:runtime_observations`, `table:runtime_receipt_inheritance`×2, `table:runtime_record_receipts`×2 |
| episode.py | 84 | Assembly; `binding_path=.../local_job_execution`, commissioning parent `.../execution_job_submission`, roles `(launch_local,)`, no entry roles, no children, permitted actions `tool` only, replaces default instructions. | `import:communication`, `import:domain`, `import:execution_contracts`, `import:launch_instructions`, `import:library.execution_operation_information`, `import:library.execution_request_compatibility`, `import:library.execution_resource_information`×2, `import:library.execution_result_contract`, `import:library.received_execution_information.received_result_readers`×3, `import:local_file_capture_results`, `import:practical_execution_operations`, `import:practical_execution_records`, `import:practical_execution_state`, `import:practical_receipt_information`, `import:resource_records`, `import:runtime` |
| execution_contracts.py | 44 | Re-exported contracts and constants for this leaf (versions, roles, kinds, result origin, selector schema, results catalog). | `import:communication`, `import:domain`, `import:execution_contracts`, `import:launch_instructions`, `import:library.execution_operation_information`, `import:library.execution_result_contract`, `import:library.received_execution_information.received_result_readers`, `import:local_file_capture_results`, `import:practical_execution_operations`, `import:practical_execution_records`, `import:practical_execution_state`, `import:practical_receipt_information`, `import:resource_records` |
| from_parent.py | 87 | Assignment: one concrete request for a configured local resource (anyOf over resources of kind local); no frozen-enum restriction; only `launch` may commission it; a compact FBA assignment is accepted from `launch` and checked against the launch request binding (input versions, FBA inputs); otherwise input versions and FBA inputs from the parent launch assignment. | `import:flux_balance_contracts`, `import:flux_balance_request_binding`×2, `import:library.execution_request_compatibility` |
| goal.py | 6 | Instructions delegated to the terminal behaviour (execution-agent text + frozen resource instructions). | none |
| initial_information.py | 8 | Readers declared for this path. | `import:library.execution_initial_information.presentation` |
| internal_summary.py | 78 | `decision_context`: terminal decision context + `selected_execution_task` for FBA requests, including an ordinary (non-compact) single request (`{resource_id: assignment}`) - the hpc copy shows it only for compact assignments; `native_decision_snapshot`. | `BindingContext`, `import:flux_balance_request_binding`×2, `import:runtime`×7, `services.scientific_parent_task`, `table:runtime_actions`×2, `workflow.binding_context`, `workflow.catalog`, `workflow.controller_binding`, `workflow.delivery_status`, `workflow.extra_report_sources`, `workflow.job_episode_options`, `workflow.journal`×3, `workflow.knowledge`, `workflow.local_outcome_preview`, `workflow.pending_work`, `workflow.run_id`, `workflow.source_credit_binding`, `workflow.source_credit_view`, `workflow.specialist`, `workflow.store`×3, `workflow.tools`, `workflow.working_state` |
| presentation.py | 61 | Presentation precedence (same renderer set). | `import:decision_context`, `import:library.hpc_prompt`, `import:library.monitor_prompt`, `import:library.scientific_decision_presentation`×2, `import:providers`, `import:receiver_prompt` |
| received_execution_information.py | 4 | Readers declared for this path. | none |
| received_records.py | 87 | Context target, received handoffs/results, initial references. | `import:flux_balance_request_binding`×2, `import:library.received_execution_information.received_result_readers`×7 |
| resource_information.py | 62 | Resource tool contracts (same as launch). | `import:library.execution_operation_information`, `import:library.execution_resource_information`×2, `import:native_flux_balance_tool_info` |
| science.py | 51 | Input versions, FBA inputs, parent-input check against the recorded parent launch assignment. | `import:episode_return_records`, `import:execution_input_versions`, `import:flux_balance_request_binding`×2, `import:library.received_execution_information.received_result_readers`×3, `table:runtime_episodes` |
| state.py | 27 | Initialise (compact FBA paths or parent-input check + FBA inputs + terminal initialise); `state` delegated to the terminal behaviour. | `import:flux_balance_request_binding`, `import:library.received_execution_information.received_result_readers`×2 |
| task.py | 217 | Shared-shape loop (decision state via `native_decision_snapshot`; wait through `perform_selected_native_wait`). | `BindingContext`×2, `import:episode_source_failure`, `import:providers`, `import:runtime`×2, `table:runtime_actions`×8, `table:runtime_episodes`, `table:runtime_model_calls`×2, `workflow.action_schema`, `workflow.automatic_score_updates`, `workflow.binding_context`×2, `workflow.completed_unit`×3, `workflow.completions`×3, `workflow.controller_value`×2, `workflow.decision_exchanges`×3, `workflow.delivery_resolution_inputs`, `workflow.execute`, `workflow.execution_binding`×7, `workflow.inprocess_replay`×4, `workflow.journal`×7, `workflow.last_observed_credit`, `workflow.next_return`, `workflow.pending_work`, `workflow.permits_common_action`, `workflow.reasoning_action_schema`, `workflow.receive_native_outcome`, `workflow.receive_outcome`, `workflow.resolve_pending_deliveries`, `workflow.resolver`, `workflow.retain_shared_grading_results`, `workflow.run_id`×3, `workflow.selected`×3, `workflow.source_credit_view`, `workflow.specialist`×2, `workflow.store`×9, `workflow.validate_report` |
| task_decision.py | 357 | Model call loop; execution expectations captured for its own grain; no waiting support. | `BindingContext`×2, `import:episode_work_report`×2, `import:library.hpc_prompt`, `import:providers`, `import:runtime`×2, `table:runtime_model_calls`×8, `workflow.available_child_roles`, `workflow.binding_context`, `workflow.contract_information_profile`, `workflow.contract_information_reply`, `workflow.controller_binding`, `workflow.decision_exchanges`×4, `workflow.decision_protocol`×3, `workflow.episode_bindings`, `workflow.execute`, `workflow.execution_expectations`, `workflow.freeze_contract_information`, `workflow.freeze_literature_numerical_contracts`, `workflow.history_preview`, `workflow.is_job_source`×3, `workflow.job_episodes`×2, `workflow.journal`×3, `workflow.launch_instructions`×2, `workflow.native_estimation_context`, `workflow.numerical_contracts`, `workflow.pending_work`, `workflow.provider`×3, `workflow.receipts`×4, `workflow.resource_context`, `workflow.resource_estimator`×5, `workflow.run_id`, `workflow.services`×2, `workflow.shared_information_context`, `workflow.specialist`, `workflow.store`×2, `workflow.uses_received_record_context`×2, `workflow.validate_contract_information`×5 |
| task_instructions.py | 20 | Composition without the reasoning-commit and wait paragraphs (tool-only leaf). | `BindingContext`, `import:library.scientific_instruction_text`, `import:runtime_prompt`, `workflow.binding_context`, `workflow.decision_protocol`, `workflow.is_job_source`, `workflow.job_episodes`, `workflow.knowledge`, `workflow.launch_instructions`, `workflow.native_event_information`, `workflow.specialist` |
| task_report.py | 22 | Finish (same shape). | `BindingContext`, `import:runtime`×2, `table:runtime_forms`×2, `workflow.binding_context`, `workflow.episode_bindings`, `workflow.facts`, `workflow.journal`×2, `workflow.pending_handles`, `workflow.release`×2, `workflow.source_credit_view` |
| task_state.py | 107 | Decision-source state (same shape). | `import:episode_source_failure`, `import:runtime`×2, `table:runtime_actions`×5, `workflow.archive`, `workflow.completions`×4, `workflow.context`, `workflow.controller_value`, `workflow.execution_binding`×4, `workflow.grains`, `workflow.inprocess_replay`×7, `workflow.journal`×5, `workflow.progress_provider`×2, `workflow.recover_commissions`, `workflow.run_id`, `workflow.source_credit_view`, `workflow.store`×2 |
| task_suspension.py | 8 | Suspension condition to the external backend. | `workflow.execution_backend`, `workflow.execution_handle`×2 |
| terminal_execution.py | 226 | Its own `TerminalExecutionBehavior` (execution-agent instructions text, `exec_command` actions, receipts, practical completion, facts, credit view); see below. | `import:acquisition`, `import:communication`, `import:domain`, `import:library.execution_operation_information`, `import:practical_execution_operations`, `import:practical_execution_records`, `import:practical_execution_state`, `import:practical_receipt_information`×3, `import:practical_yield`, `import:terminal_execution`, `import:terminal_scientific_evidence`×2, `yield:PracticalYieldEstimator`×2 |
| to_parent.py | 53 | Facts: terminal facts (`practical_completed`, receipt digests/refs) + handoffs found in its practical receipts + execution result/file facts + closed credit; no required return sources. | `import:flux_balance_return_views`, `import:library.received_execution_information.received_result_readers`×2, `services.annotation_task_required` |
| waiting.py | 10 | `perform_selected_native_wait`. | `import:runtime`×2, `workflow.perform_selected_wait` |
| work_operations.py | 32 | Catalog and execution delegated to the terminal behaviour after the parent-input check; compact FBA outcome view. | `import:flux_balance_request_binding`×2, `import:library.execution_resource_information`, `import:library.received_execution_information.received_result_readers` |
| yield_estimator.py | 48 | Accumulation controller with `PracticalYieldEstimator` (verify_completion), profile `launch_local:<request class>`; requires private yield binding. | `import:flux_balance_request_binding`, `import:library.execution_result_contract`, `import:numerical`, `import:practical_yield`×2, `yield:PracticalYieldEstimator`×4, `yield:YieldController`×2, `yield:YieldParameters`×2 |

## Carried over

Carried over on 19 November 2026 (copied privately from the shape of the identical sibling carry under `hpc_work_planning`; the old files differ only in path strings; the compact flux-balance assignment that this episode accepted from `launch` is not carried, see the blocked file) to the ten-file form (private binding `LocalJobExecution` under `execution_job_submission`, `episode.py`). Columns: old file (under the old episode folder at `97308b94c`), kind of the old name, old name, whether it is old-runner machinery or an episode function, and its new place (file and name, or the machinery reason). A row marked `unplaced` is an episode function of another role (results) that this launch role does not use. Library candidates (kept in the file that uses them): `messages/internal_summary.py::_completion` (the old `PracticalState._completion` over receipts), `yield_estimator.py::_request_yield_class`, `yield_estimator.py::_task_yield_profile`. Already in library and called from here: `grading/biochemical_feasibility_evidence/practical_execution_credit.py::project_practical_credit`, `records/biochemical_feasibility_evidence/practical_execution_records.py` (`validate_assignment`, `assess_validations`, `canonical`, `digest`), `records/biochemical_feasibility_evidence/domain.py` (`validate_schema`, `ContractError`), `jobs/local_execution/biochemical_feasibility_evidence/terminal_execution.py::TerminalExecution`, `findings/biochemical_feasibility_evidence/terminal_scientific_evidence.py::terminal_artifact_paths`, `tools/metabolic_feasibility/native_flux_balance_bindings.py::validate_flux_balance_bindings`, `instructions/launch_instructions.py`, `tools/tool_knowledge.py`, `records/progress_views.py`, `model_exchange/rejection_feedback.py`.

| old file | kind | name | class | new place |
|---|---|---|---|---|
| binding_record.py | class | NativeBindingRecord | machinery | binding_record.py and the binding's own as_record() |
| binding_record.py | method | NativeBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record() |
| completion.py | class | NativeCompletion | machinery | completion proof as controller input and its re-validation against runtime_observations (README 5 item 5); the completion proof is derived from the held receipts in messages/internal_summary.py::_completion (library candidate) and the target comes from parent_input |
| completion.py | method | NativeCompletion.completion_for_action | machinery | completion proof as controller input and its re-validation against runtime_observations (README 5 item 5); the completion proof is derived from the held receipts in messages/internal_summary.py::_completion (library candidate) and the target comes from parent_input |
| completion.py | method | NativeCompletion._closed_completion_verdict | machinery | completion proof as controller input and its re-validation against runtime_observations (README 5 item 5); the completion proof is derived from the held receipts in messages/internal_summary.py::_completion (library candidate) and the target comes from parent_input |
| completion.py | method | NativeCompletion.verify_completion | machinery | completion proof as controller input and its re-validation against runtime_observations (README 5 item 5); the completion proof is derived from the held receipts in messages/internal_summary.py::_completion (library candidate) and the target comes from parent_input |
| configuration.py | class | NativeConfiguration | machinery | class of constructor values; the values are the episode's settings |
| configuration.py | method | NativeConfiguration.__init__ | episode function | settings read by task.py::_resource_configuration (explicit local resource, valid native flux-balance bindings), task.py::_resource and ::_capabilities (initial_information), yield_estimator.py::_task_yield_profile (task_yield_profiles); the other constructor parts (handoff_unit, acquired_record_unit, log window and roles, results yield profiles, progress provider, local file sources, flux-balance input/request/result/return helpers, HPC resources) belong to the results/monitor roles or are old-runner machinery and are not carried |
| credit.py | class | ExecutionEpisodeCredit | episode function | credit.py::credit (the operational practical credit over the summary; the frozen closed view is machinery) |
| credit.py | method | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind deleted |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_carrier | machinery | frozen closed-credit snapshot built from runtime_episodes, runtime_forms, runtime_observations and receipt tables; the system's closure credit (completion['credit']) is returned by final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_receipts | machinery | frozen closed-credit snapshot built from runtime_episodes, runtime_forms, runtime_observations and receipt tables; the system's closure credit (completion['credit']) is returned by final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_value | machinery | frozen closed-credit snapshot built from runtime_episodes, runtime_forms, runtime_observations and receipt tables; the system's closure credit (completion['credit']) is returned by final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_facts | machinery | frozen closed-credit snapshot built from runtime_episodes, runtime_forms, runtime_observations and receipt tables; the system's closure credit (completion['credit']) is returned by final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._closed_operational_credit_view | machinery | frozen closed-credit snapshot built from runtime_episodes, runtime_forms, runtime_observations and receipt tables; the system's closure credit (completion['credit']) is returned by final_to_parent |
| credit.py | method | ExecutionEpisodeCredit.project_credit | episode function | credit.py::credit |
| credit.py | method | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py::credit (project_practical_credit over the summary) |
| credit.py | method | ExecutionEpisodeCredit.credit_view | episode function | credit.py::credit |
| episode.py | class | ExecutionEpisode | episode function | episode.py::LocalJobExecution (binding_path, goal, tools, services, forms; the mix-ins and hook attributes are not carried) |
| episode.py | method | ExecutionEpisode.child_roles | episode function | task.py::CHILD_SLOTS = {} |
| episode.py | method | ExecutionEpisode.allowed_children | episode function | task.py::CHILD_SLOTS = {} |
| episode.py | method | ExecutionEpisode.permitted_common_actions | episode function | task.py::decide and ::action (only the exec_command tool is offered) |
| execution_contracts.py | function | native_result_operation_catalog | unplaced | results role operation catalogue (execution.results.*); this launch role does not use it |
| from_parent.py | class | NativeParentRequests | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM, read_from_parent) |
| from_parent.py | method | NativeParentRequests._permitted | machinery | checks a request against the launch parent's constraints; the parent builds the commission and a wrong one fails (rule 1) |
| from_parent.py | method | NativeParentRequests._request_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM (the practical assignment fields; the flux-balance requested_job alternative is validated by validate_assignment; the compact resource_assignment_schema alternative is not carried, blocked file) |
| from_parent.py | method | NativeParentRequests._launch | machinery | validation of the launch parent's own assignment; the child reads no other episode's request |
| from_parent.py | method | NativeParentRequests.child_assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| from_parent.py | method | NativeParentRequests.assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| from_parent.py | method | NativeParentRequests.prepare_assignment | episode function | messages/read_from_parent.py::read_from_parent (validate_assignment); the compact-assignment branch (read_request_binding), the launch parent check and the immutable input versions read runtime_episodes / the launch request binding and are not carried (a wrong commission fails) |
| goal.py | class | NativeGoal | episode function | task.py::_instructions (GOAL_INSTRUCTION) |
| goal.py | method | NativeGoal.instructions | episode function | task.py::_instructions (GOAL_INSTRUCTION) |
| initial_information.py | function | initial_information | episode function | task.py::_resource and ::_capabilities (the recorded inventory comes from settings['initial_information']); the result-reader catalog consumer (catalog.readers) is old-runner machinery of the results role |
| internal_summary.py | function | native_decision_snapshot | machinery | generic old-runner decision snapshot (journal reads of runtime_actions, working state, receipt projection, elapsed_view); the episode's own content is in messages/internal_summary.py and task.py::decide |
| internal_summary.py | class | NativeInternalSummary | episode function | messages/internal_summary.py::internal_summary |
| internal_summary.py | method | NativeInternalSummary._with_selected_execution_task | episode function | messages/internal_summary.py::_selected_execution_task (the flux-balance job view scientific_job_view is in no place now: raises NotImplementedError('unplaced:scientific_job_view')) |
| internal_summary.py | method | NativeInternalSummary.decision_context | episode function | messages/internal_summary.py::internal_summary (practical_assignment, execution_progress, execution_completion, selected_execution_task) |
| presentation.py | function | present_context | episode function | task.py::_task_text (the selected execution presentation over the summary); the state-frame routing, provider.scientific_prompt_states and renderer dispatch are old-runner machinery |
| received_execution_information.py | function | received_execution_information | machinery | catalog.received reader authority of the old runner (result readers of the results role) |
| received_records.py | class | NativeReceivedRecords | machinery | receipt scanning of received references (old receipts / result readers) |
| received_records.py | method | NativeReceivedRecords._context_target | machinery | read_request_binding of the old runner's tables |
| received_records.py | method | NativeReceivedRecords._received | machinery | scan of received receipts and result providers through the old Store (runtime receipts); results-role readers |
| received_records.py | method | NativeReceivedRecords.initial_references | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM record_refs (the records the job inputs name, passed in custody) |
| resource_information.py | class | NativeResourceInformation | episode function | task.py::EXEC_COMMAND and ::_capabilities (the one general capability; the flux-balance tool contracts native_flux_balance_tool_info.flux_balance_tool_contracts are in no place now: _capabilities raises NotImplementedError('unplaced:flux_balance_tool_contracts') for a resource that binds flux balance) |
| resource_information.py | method | NativeResourceInformation.resource_tool_contracts | episode function | task.py::EXEC_COMMAND and ::_capabilities (the one general capability; the flux-balance tool contracts native_flux_balance_tool_info.flux_balance_tool_contracts are in no place now: _capabilities raises NotImplementedError('unplaced:flux_balance_tool_contracts') for a resource that binds flux balance) |
| science.py | class | NativeScienceInputs | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM record_refs |
| science.py | method | NativeScienceInputs._versions | machinery | validate_execution_input_versions over the launch's immutable_input_versions read from runtime_episodes; the pinned input records are passed in custody (record_refs) |
| science.py | method | NativeScienceInputs._flux_balance_inputs | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM record_refs (the flux-balance input references); the receipts-based re-authentication (flux_balance_inputs.received/validate_selected) is old-runner machinery |
| science.py | method | NativeScienceInputs._matches_flux_balance_assignment | machinery | compact-assignment materialization through the request binding (old runner tables) |
| science.py | method | NativeScienceInputs._check_parent_inputs | machinery | reads the launch request from runtime_episodes (old runner tables) |
| state.py | class | NativeState | machinery | working state of the practical ledger kept on the old runner (PracticalState file ledger); the receipts are the tool outcomes in the view and the completion is derived in messages/internal_summary.py::_completion |
| state.py | method | NativeState.initialize | machinery | working state of the practical ledger kept on the old runner (PracticalState file ledger); the receipts are the tool outcomes in the view and the completion is derived in messages/internal_summary.py::_completion |
| state.py | method | NativeState.state | machinery | working state of the practical ledger kept on the old runner (PracticalState file ledger); the receipts are the tool outcomes in the view and the completion is derived in messages/internal_summary.py::_completion |
| task.py | class | NativeTask | episode function | task.py (decide, action, TOOLS) |
| task.py | method | NativeTask.next | machinery | the old decision loop (replay, pending deliveries, SourceEnd); decide returns the unit |
| task.py | method | NativeTask.apply_response | episode function | task.py::action (the answer selects one exec_command or is rejected) |
| task.py | method | NativeTask.execute | episode function | task.py::exec_command (the tool) through the job_access service; the begin/finish intent, receipt recording and report redelivery branches are machinery |
| task_decision.py | class | NativeTaskDecision | machinery | decision-exchange loop and its saved-request checks (README 3a) |
| task_decision.py | method | NativeTaskDecision.call | machinery | model call, conversation sessions and recording (decide returns ModelRequest) |
| task_decision.py | method | NativeTaskDecision.instructions | episode function | task.py::_instructions |
| task_decision.py | method | NativeTaskDecision.conversation_key | machinery | decision-exchange loop and its saved-request checks (README 3a) |
| task_decision.py | method | NativeTaskDecision.interpretation_context | machinery | decision-exchange loop and its saved-request checks (README 3a) |
| task_decision.py | method | NativeTaskDecision.exchange_schema | machinery | decision-exchange loop and its saved-request checks (README 3a) |
| task_decision.py | method | NativeTaskDecision.exchange_response | machinery | decision-exchange loop and its saved-request checks (README 3a) |
| task_decision.py | method | NativeTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop and its saved-request checks (README 3a) |
| task_decision.py | method | NativeTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop and its saved-request checks (README 3a) |
| task_decision.py | method | NativeTaskDecision.exchange_decision | machinery | decision-exchange loop and its saved-request checks (README 3a) |
| task_decision.py | method | NativeTaskDecision.decision_completion | machinery | decision completion record of the old exchange loop |
| task_instructions.py | function | instructions | episode function | task.py::_instructions (the specialist text replaces the default, then tool knowledge and the launch library; the child-delivery repair, wait/native-event and exchange-history paragraphs describe actions that do not exist and are not carried) |
| task_report.py | class | NativeTaskReport | machinery | report delivery (finish); final_to_parent returns the result |
| task_report.py | method | NativeTaskReport.finish | machinery | report delivery (finish); final_to_parent returns the result |
| task_state.py | class | NativeTaskState | machinery | checkpoint / restore of the old task state (README 3e); the system restores the view |
| task_state.py | method | NativeTaskState.__init__ | machinery | checkpoint / restore of the old task state (README 3e); the system restores the view |
| task_state.py | method | NativeTaskState.bind_execution_context | machinery | checkpoint / restore of the old task state (README 3e); the system restores the view |
| task_state.py | method | NativeTaskState.record_execution_failure | machinery | failure recording in the old tables; a failed command is a receipt returned by the tool and kept in the outcome |
| task_state.py | method | NativeTaskState.restore_checkpoint | machinery | checkpoint / restore of the old task state (README 3e); the system restores the view |
| task_state.py | method | NativeTaskState.restore | machinery | checkpoint / restore of the old task state (README 3e); the system restores the view |
| task_state.py | method | NativeTaskState.record_effect | machinery | checkpoint / restore of the old task state (README 3e); the system restores the view |
| task_state.py | method | NativeTaskState.checkpoint | machinery | checkpoint / restore of the old task state (README 3e); the system restores the view |
| task_suspension.py | class | NativeTaskSuspension | machinery | suspension / wait machinery |
| task_suspension.py | method | NativeTaskSuspension.suspension_changed | machinery | suspension / wait machinery |
| terminal_execution.py | class | TerminalExecutionBehavior | episode function | task.py (the tool, instructions, resource and capability views) and messages/ files |
| terminal_execution.py | method | TerminalExecutionBehavior.__init__ | episode function | settings (resources, initial_information, coordinator_workspace) read by task.py::_resource_configuration, ::_resource, ::_capabilities |
| terminal_execution.py | method | TerminalExecutionBehavior._operations | episode function | task.py::_operations |
| terminal_execution.py | method | TerminalExecutionBehavior._assignment | episode function | messages/read_from_parent.py::read_from_parent (validate_assignment) and task.py::_operations (the transport's validate_assignment) |
| terminal_execution.py | method | TerminalExecutionBehavior._state_directory | machinery | location of the PracticalState file ledger (job_access service state) |
| terminal_execution.py | method | TerminalExecutionBehavior.initialize | machinery | PracticalState creation with the initial validations; the baseline is messages/internal_summary.py (assess_validations over the assignment) |
| terminal_execution.py | method | TerminalExecutionBehavior.state | machinery | PracticalState lookup |
| terminal_execution.py | method | TerminalExecutionBehavior.as_record | machinery | the binding's own as_record() |
| terminal_execution.py | method | TerminalExecutionBehavior.child_roles | episode function | task.py::CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_kind | machinery | credit_kind deleted |
| terminal_execution.py | method | TerminalExecutionBehavior.assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| terminal_execution.py | method | TerminalExecutionBehavior.permitted_common_actions | episode function | task.py::decide and ::action (only the exec_command tool is offered) |
| terminal_execution.py | method | TerminalExecutionBehavior.allowed_children | episode function | task.py::CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.prepare_assignment | episode function | messages/read_from_parent.py::read_from_parent (validate_assignment) and task.py::_operations |
| terminal_execution.py | method | TerminalExecutionBehavior.initial_decision_context | episode function | task.py::decide (execution_initial_information from settings) |
| terminal_execution.py | method | TerminalExecutionBehavior._resource_information | episode function | task.py::_resource |
| terminal_execution.py | method | TerminalExecutionBehavior._resource_instructions | episode function | task.py::_instructions (LaunchInstructions.for_resource) |
| terminal_execution.py | method | TerminalExecutionBehavior.instructions | episode function | task.py::_instructions (GOAL_INSTRUCTION) |
| terminal_execution.py | method | TerminalExecutionBehavior.decision_context | episode function | task.py::decide and messages/internal_summary.py::internal_summary |
| terminal_execution.py | method | TerminalExecutionBehavior.catalog | episode function | task.py::EXEC_COMMAND |
| terminal_execution.py | method | TerminalExecutionBehavior.execute | episode function | task.py::exec_command (job_access service, BLOCKED-ON-JOB-SERVICE) and ::action (the validation of the arguments, rejected answers); PracticalState begin/finish, finalize_scientific_command, cwd/environment revision, assess_validations and PracticalReceiptInformation.publish are the service's and old-runner machinery |
| terminal_execution.py | method | TerminalExecutionBehavior.completion_for_action | machinery | completion proof as controller input (README 5 item 5) |
| terminal_execution.py | method | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator; yield_estimator.py::yield_controller |
| terminal_execution.py | method | TerminalExecutionBehavior.fact_sources | episode function | messages/final_to_parent.py::RETURN_FORM (practical_completed, practical_receipt_digests, practical_receipt_refs) |
| terminal_execution.py | method | TerminalExecutionBehavior.facts | episode function | messages/final_to_parent.py::_facts |
| terminal_execution.py | method | TerminalExecutionBehavior.resolve | machinery | reference resolution through the old runner (PracticalReceiptInformation); custody checks the returned records |
| terminal_execution.py | method | TerminalExecutionBehavior.validate_report | episode function | messages/final_to_parent.py::validate_report |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_view | episode function | credit.py::credit |
| to_parent.py | class | NativeParentReturns | episode function | messages/final_to_parent.py |
| to_parent.py | method | NativeParentReturns.required_return_sources | machinery | old required return sources (always empty); RETURN_FORM declares what is returned |
| to_parent.py | method | NativeParentReturns.facts | episode function | messages/final_to_parent.py::_facts and final_to_parent |
| to_parent.py | method | NativeParentReturns._live_facts | episode function | messages/final_to_parent.py::_facts (the flux-balance empty result sources fba_fact_sources and the result-origin value are not carried: blocked file) |
| to_parent.py | method | NativeParentReturns.validate_report | episode function | messages/final_to_parent.py::validate_report (no validate_form call: the axis has none and the system admits the result against RETURN_FORM; only the recorded-facts agreement check is kept; the flux-balance return validation native_flux_balance_returns.validate_received_report is of the unplaced flux_balance_returns) |
| waiting.py | function | perform_selected_native_wait | machinery | wait machinery (perform_selected_native_wait) |
| work_operations.py | class | NativeWorkOperations | episode function | task.py::TOOLS |
| work_operations.py | method | NativeWorkOperations.catalog | episode function | task.py::EXEC_COMMAND and ::decide |
| work_operations.py | method | NativeWorkOperations.execute | episode function | task.py::exec_command |
| yield_estimator.py | class | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | method | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py::_request_yield_class (library candidate) |
| yield_estimator.py | method | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py::_task_yield_profile (library candidate) |
| yield_estimator.py | method | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py::yield_controller |
| yield_estimator.py | method | ExecutionEpisodeYield._launch_local_yield_controller | episode function | yield_estimator.py::yield_controller (CompletionYieldController; the PracticalYieldEstimator completion proof is not a controller input) |
| yield_estimator.py | method | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator selection |
