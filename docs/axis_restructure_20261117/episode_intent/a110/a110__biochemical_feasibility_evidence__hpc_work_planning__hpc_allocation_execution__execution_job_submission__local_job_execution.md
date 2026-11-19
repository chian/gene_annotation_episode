# Intent: a110/biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution

Read from its own files at commit `97308b94c`. It is a leaf. Old role name: `launch_local`. Old commissioning parent: `execution_job_submission` (role `launch`).

This folder is a copy of `hpc_job_execution`. `git diff` between the two trees touches only 8 files and 23 lines. Everything below holds as in `a110__..._hpc_job_execution.md` unless listed here.

## Purpose (its own words)

It uses the same execution-agent instructions as its sibling (in its own identical `terminal_execution.py`): "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. ... The episode iterator decides continuation from credit; add no stopping budget."

It runs the actual job on the **local** resource, with the coordinator workspace as the run directory. It is also the only execution leaf here that may run native flux-balance (FBA) work: configuration refuses `native_flux_balance` on any non-local resource.

## Task and instructions

The text is identical to the hpc sibling.

## What it reads from its parent's assignment (`from_parent.py`, 87 lines)

- `assignment_schema`: anyOf the `practical_assignment_v1` schemas for configured `local` resources. With FBA configured, it also includes the compact `resource_assignment_schema` alternative.
- `child_assignment_schema`: no frozen-request restriction (the hpc sibling has one).
- `prepare_assignment`: also accepts a **compact flux-balance assignment**:
  - parent role must be `launch`;
  - it reads the Launch's request binding (`read_request_binding(store, run_id, parent.episode_id)`);
  - it selects the matching row and checks flux-balance inputs and input versions against that row.

  Otherwise it behaves like the sibling: validate the request, match kind, check against the parent Launch's `immutable_input_versions`.
- `NativeScienceInputs._flux_balance_inputs`: for role `launch_local` with a matching assignment, it reuses the frozen received flux-balance inputs.

## Children it may commission

None.

## Decision state and what the model sees

The same as the sibling, with one difference. For a non-compact assignment, `internal_summary._with_selected_execution_task` builds `selected_execution_task` from its single request (`{resource_id: assignment}`) when that request carries `native_flux_balance`. The task holds the scientific_question and selected_tool_info from the services hook `scientific_parent_task`, the scientific job view and the resource information. The hpc sibling returns the context unchanged in this case.

## Tools, credit, report

- **Tools:** identical, with `operation_catalog('local')`.
- **Credit:** identical: the PracticalState credit view plus the closed snapshot.
- **Report:** identical facts.

## Continuation

Old behaviour: `YieldController` with `PracticalYieldEstimator(verify_completion)`, profile `task_yield_profiles['launch_local:' + request yield class]`. The configuration also accepts `results_yield_profiles['native_unbounded_local']`.

Mapping: **CompletionYieldEstimator(initial_credit, target)** with the `launch_local:<class>` profile settings, as for the sibling.

## File-by-file

The line counts and old-runner names match the hpc sibling's table, except for the files below. Per-file counts for this episode are in `runs/carry_over/calls/a110_04.tsv`.

| Old file | Lines | Difference in own intent | Old-runner names |
|---|---|---|---|
| from_parent.py | 87 | Compact FBA assignment accepted; no frozen-hpc enum | Same helpers; uses Launch request binding (`flux_balance_request_binding`) |
| internal_summary.py | 78 | selected_execution_task for a single non-compact FBA request | Same as sibling |
| yield_estimator.py | 48 | Profile prefix `launch_local:` | `numerical.YieldController`, `YieldParameters`; `practical_yield.PracticalYieldEstimator`×4 |
| episode.py | 84 | role `launch_local`, own path | old hook names |
| binding_record.py | 8 | own binding_id | none |
| execution_contracts.py | 44 | Imports own terminal_execution | `communication.*` imports |
| initial_information.py | 8 | own path | old catalog protocol |
| received_execution_information.py | 4 | own path | old catalog protocol |

All the other files are byte-identical to `hpc_job_execution`: goal, terminal_execution, task, task_decision, task_instructions, task_state, task_report, task_suspension, waiting, presentation, configuration, credit, completion, to_parent, science, state, received_records, resource_information, work_operations and `__init__`. Their old-runner names are listed in that note.

## Carried over

Carried over on 19 November 2026 to the ten-file form (private binding `LocalJobExecution`, `episode.py`). Columns: old file (under the old episode folder at `97308b94c`), kind of the old name, old name, whether it is old-runner machinery or an episode function, and its new place (file and name, or the machinery reason). A row marked `unplaced` is an episode function of another role (results) that this launch role does not use. Library candidates (kept in the file that uses them): `messages/internal_summary.py::_completion` (the old `PracticalState._completion` over receipts), `yield_estimator.py::_request_yield_class`, `yield_estimator.py::_task_yield_profile`. Already in library and called from here: `grading/biochemical_feasibility_evidence/practical_execution_credit.py::project_practical_credit`, `records/biochemical_feasibility_evidence/practical_execution_records.py` (`validate_assignment`, `assess_validations`, `canonical`, `digest`), `records/biochemical_feasibility_evidence/domain.py` (`validate_schema`, `ContractError`), `jobs/local_execution/biochemical_feasibility_evidence/terminal_execution.py::TerminalExecution`, `findings/biochemical_feasibility_evidence/terminal_scientific_evidence.py::terminal_artifact_paths`, `tools/metabolic_feasibility/native_flux_balance_bindings.py::validate_flux_balance_bindings`, `instructions/launch_instructions.py`, `tools/tool_knowledge.py`, `records/progress_views.py`, `model_exchange/rejection_feedback.py`.

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
| terminal_execution.py | method | TerminalExecutionBehavior.validate_report | episode function | not carried: redundant, the system admits the result against RETURN_FORM (validate_report and validate_form deleted) |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_view | episode function | credit.py::credit |
| to_parent.py | class | NativeParentReturns | episode function | messages/final_to_parent.py |
| to_parent.py | method | NativeParentReturns.required_return_sources | machinery | old required return sources (always empty); RETURN_FORM declares what is returned |
| to_parent.py | method | NativeParentReturns.facts | episode function | messages/final_to_parent.py::_facts and final_to_parent |
| to_parent.py | method | NativeParentReturns._live_facts | episode function | messages/final_to_parent.py::_facts (the flux-balance empty result sources fba_fact_sources and the result-origin value are not carried: blocked file) |
| to_parent.py | method | NativeParentReturns.validate_report | episode function | not carried: redundant, the system admits the result against RETURN_FORM (validate_report and validate_form deleted); the flux-balance return validation stays unplaced (blocked file) |
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
