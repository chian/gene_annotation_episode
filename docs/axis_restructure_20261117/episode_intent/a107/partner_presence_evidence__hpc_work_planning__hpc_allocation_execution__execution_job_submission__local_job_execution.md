# Episode intent: A107 `local_job_execution`

Episode path: `root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution`
Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/.../execution_job_submission/local_job_execution/<file>` (29 files, no `grading/` or `scoring/` subfolder).
Binding class: `ExecutionEpisode`. Role: `launch_local`. Commissioning parent: `execution_job_submission` (role `launch`). Binding version `execution_episode_v1`.

The file set is a copy of `api_job_execution`'s; the files identical across the three siblings are described there. Local matches hpc_job_execution except in two files, from_parent.py and internal_summary.py.

## What this episode is for (its goal, in its own words)

goal.py delegates to `TerminalExecutionBehavior.instructions`. That is the same exec_command execution-agent text quoted in the hpc_job_execution file ("You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. ... The episode iterator decides continuation from credit; add no stopping budget."), followed by the resource sections from the frozen launch instruction library for the local resource.

So the episode runs one job on the local resource (the coordinator machine's run directory or workspace) for the parent's selected request. It covers native BLAST, BLAST masking/utility/DB/standard DB, HMMER and preparation, Infernal and preparation, RNA structure and expression NMF; NMF, RNA structure and Infernal are allowed only on local resources (configuration.py). The episode ends when the requested endpoint is validated.

## Task and instructions

- task, task_state, task_report, task_suspension, waiting and presentation are the same as the api copy.
- task_instructions.py is the same as hpc's: no reasoning, wait or native-event paragraphs, with the no-op `native_event_information is not None` line.

## What it reads from its parent's assignment

- `assignment_schema(role)`: local resources, `ASSIGNMENT_SCHEMA` with `resource_kind='local'`, and `requested_job` alternatives that include the NMF, RNA structure, Infernal and preparation contracts configured on the local resource.
- `child_assignment_schema` is the plain `assignment_schema` (dead `and False` branch, as in api). There is **no frozen-request enum** as in hpc.
- `prepare_assignment` re-validates the parent launch, without `_validate_blast_launch_selection`. It then checks the masking, utility and input versions (NMF assignments included) and the native BLAST DB, standard BLAST DB and RNA-structure job inputs.
- received_records.py `initial_references` (identical file, but it only reaches here): for `launch_local` the episode's own assignment is the request. It returns the RNA-structure, masking, utility and expression-NMF input references, so local work starts with those received inputs.
- science.py `_check_parent_inputs` is the same as hpc.

## Children

None.

## Decision state and what it shows the model

- `native_decision_snapshot` is the same as the api copy.
- `decision_context` = `_delegate(context).decision_context(...)`, which supplies execution_assignment, execution_resource, coordinator_workspace, execution_progress and execution_completion. Then **`_with_selected_execution_task` builds `selected_execution_task`**: the scientific parent's question and selected_tool_info, plus the request's single native job chosen from native_blast, masking, utility, DB, standard DB, hmmer, hmmer_preparation and expression_nmf. NMF uses `expression_nmf_scientific_job_view`, and HMMER uses `native_profile_scientific_job_view`. If `services.scientific_parent_task` returns None, the view is omitted.
- task_decision.py is the same as hpc: no waiting_support.

## Tools it offers

Tool only. The catalog is `operation_catalog('local')`. The rest of the terminal execution path is as in hpc (exec_command, target=resource|coordinator, PracticalState receipts).

## Credit

Operational. Live credit is the terminal `PracticalState.credit_view()`, with the same closed-credit snapshot as the siblings. Never bounded.

## Continuation

Completion with a target. Profile key `'launch_local:' + _request_yield_class(request)`, for example `launch_local:practical_local_native_expression_nmf_outputs`. `practical_estimator` delegates to the terminal behaviour. Settings: `task_yield_profiles['launch_local:<class>'] = {cutoff, parameters}`, and `require_private_yield=True`.

## What it reports to its parent

Same as hpc (to_parent.py is byte-identical between hpc and local):
- the practical facts and `execution_handoff_refs`;
- the result refs and their file sources and capture outcomes;
- `execution_result_origin` and `execution_completed`;
- the empty native families and the adapter-based report validation.

## File-by-file

`w.` = `self.workflow.`.

| file | lines | own intent | old-runner names |
|---|---|---|---|
| binding_record.py | 8 | own path | none |
| completion.py | 51 | terminal-state verification | runtime_observations(1), episode_return_records(1), method_loop.identities(1), numerical(1), ESTIMATOR_VERSION(2) |
| configuration.py | 119 | identical | numerical YieldController(3)/YieldParameters(3) |
| credit.py | 136 | terminal live credit, closed snapshot | runtime_episodes(2), runtime_forms(3), runtime_observations(1), runtime_receipt_inheritance(2), runtime_record_receipts(2), episode_receipts(1), episode_return_records(3) |
| episode.py | 103 | role `launch_local`; tool only | communication(1), runtime(1) |
| execution_contracts.py | 57 | constants (own terminal_execution path) | communication(1) |
| from_parent.py | 113 | plain child schema; no BLAST launch selection check | none |
| goal.py | 6 | delegate | none |
| initial_information.py | 9 | own path readers | none |
| internal_summary.py | 88 | delegate decision_context + selected_execution_task (native jobs) | `_live_original_runtime`(11), runtime(6), runtime_actions(2), w.journal(3), w.store(3), plus the w.* single uses as api |
| presentation.py | 74 | identical | `_live_original_providers`(20), decision_context(1) |
| received_api_reports.py / received_execution_information.py | 4 / 4 | own path | none |
| received_records.py | 127 | identical; `launch_local` initial references | none |
| resource_information.py | 70 | identical | none |
| science.py | 57 | as hpc | runtime_episodes(1) |
| state.py | 19 | delegate state | none |
| task.py, task_report.py, task_state.py, task_suspension.py, waiting.py, work_operations.py | 225/22/107/8/10/35 | identical | as api |
| task_decision.py | 357 | no waiting_support | as hpc |
| task_instructions.py | 20 | as hpc | as hpc |
| terminal_execution.py | 226 | identical | communication(1), PracticalYieldEstimator(2) |
| to_parent.py | 100 | as hpc | none |
| yield_estimator.py | 50 | `launch_local:` profile | numerical YieldController(2)/YieldParameters(2), PracticalYieldEstimator(2) |

The exact per-file counts are in `runs/carry_over/calls/a107_05.tsv`.

## Differences from siblings

- Compared with **hpc_job_execution**, local differs in two places:
  - local keeps the full `_with_selected_execution_task`, whereas hpc's is a no-op;
  - local has no frozen-HPC `child_assignment_schema`.

  The yield prefix follows the role.
- Compared with **api_job_execution**: no wait; terminal-delegate goal, credit, state, completion and facts; no API BLAST grader binding; no `_validate_blast_launch_selection`. The `selected_execution_task` job view covers the native jobs, where the api copy covers only ebi_hmmer.

## Carried over

Rows are the old functions of the episode folder at `97308b94c` (`runs/carry_over/functions/a107__partner_presence_evidence__hpc_work_planning__hpc_allocation_execution__execution_job_submission__local_job_execution.tsv`), one per row. New files are in `gene_annotation_episode/episodic_workflow/root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/`. Rows beginning "unplaced" are also in `carry_over_blocked/a107__partner_presence_evidence__hpc_work_planning__hpc_allocation_execution__execution_job_submission__local_job_execution.md`. Library candidates (they stay in this episode's files): `messages/internal_summary.py` `_completion`, `yield_estimator.py` `_request_yield_class`, `messages/final_to_parent.py` `validate_report`, `_resolver`, `_facts`, `_report_schema`, `task.py` `_resource_configuration`, `_resource`, `_handoff`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | NativeBindingRecord | machinery | binding record / the binding's own as_record() (README 3e) |
| binding_record.py | NativeBindingRecord.as_record | machinery | binding record / the binding's own as_record() (README 3e) |
| completion.py | NativeCompletion | episode function | messages/internal_summary.py _completion (practical completion proof derived from the receipts; library candidate); the proof is not a controller input (README 5 item 5) |
| completion.py | NativeCompletion.completion_for_action | episode function | messages/internal_summary.py _completion (practical completion proof derived from the receipts; library candidate); the proof is not a controller input (README 5 item 5) |
| completion.py | NativeCompletion._closed_completion_verdict | machinery | closed completion verdict / verify_completion over runtime_observations and the PracticalYieldEstimator (README 3d) |
| completion.py | NativeCompletion.verify_completion | machinery | closed completion verdict / verify_completion over runtime_observations and the PracticalYieldEstimator (README 3d) |
| configuration.py | NativeConfiguration | episode function | settings (ctx.settings): task.py _resource_configuration, _resource_information; yield_estimator.py _task_yield_profile; handoff/acquired units, log window/roles, results profiles, API execution, progress provider, result readers = old-runner wiring or results/API role (not carried) |
| configuration.py | NativeConfiguration.__init__ | episode function | settings (ctx.settings): task.py _resource_configuration, _resource_information; yield_estimator.py _task_yield_profile; handoff/acquired units, log window/roles, results profiles, API execution, progress provider, result readers = old-runner wiring or results/API role (not carried) |
| credit.py | ExecutionEpisodeCredit | episode function | credit.py credit (practical credit: project_practical_credit over the summary's receipts) |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind deleted (README 3d) |
| credit.py | ExecutionEpisodeCredit._closed_credit_carrier | machinery | closed-credit capture and replay over runtime_episodes/runtime_observations/runtime_record_receipts/runtime_forms (README 3e); the system returns completion['credit'] |
| credit.py | ExecutionEpisodeCredit._closed_credit_receipts | machinery | closed-credit capture and replay over runtime_episodes/runtime_observations/runtime_record_receipts/runtime_forms (README 3e); the system returns completion['credit'] |
| credit.py | ExecutionEpisodeCredit._closed_credit_value | machinery | closed-credit capture and replay over runtime_episodes/runtime_observations/runtime_record_receipts/runtime_forms (README 3e); the system returns completion['credit'] |
| credit.py | ExecutionEpisodeCredit._closed_credit_facts | machinery | closed-credit capture and replay over runtime_episodes/runtime_observations/runtime_record_receipts/runtime_forms (README 3e); the system returns completion['credit'] |
| credit.py | ExecutionEpisodeCredit._closed_operational_credit_view | machinery | closed-credit capture and replay over runtime_episodes/runtime_observations/runtime_record_receipts/runtime_forms (README 3e); the system returns completion['credit'] |
| credit.py | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (practical credit: project_practical_credit over the summary's receipts) |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit (practical credit: project_practical_credit over the summary's receipts) |
| credit.py | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit (practical credit: project_practical_credit over the summary's receipts) |
| episode.py | ExecutionEpisode | episode function | episode.py LocalJobExecution (the one EpisodeBinding class) |
| episode.py | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.permitted_common_actions | episode function | task.py TOOLS (exec_command is the only action; no wait, no children) |
| execution_contracts.py | native_result_operation_catalog | episode function | unplaced: results role native result operation catalog (status/collect/read); not this launch role (carry_over_blocked) |
| from_parent.py | NativeParentRequests | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per property of practical_assignment_v1) |
| from_parent.py | NativeParentRequests._permitted | episode function | unplaced: launch parent's resource permission / launch assignment re-validation against the commissioning request; a wrong commission fails (rule 1), not carried |
| from_parent.py | NativeParentRequests._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per property of practical_assignment_v1) |
| from_parent.py | NativeParentRequests._launch | episode function | unplaced: launch parent's resource permission / launch assignment re-validation against the commissioning request; a wrong commission fails (rule 1), not carried |
| from_parent.py | NativeParentRequests._constraints | episode function | unplaced: launch parent's resource permission / launch assignment re-validation against the commissioning request; a wrong commission fails (rule 1), not carried |
| from_parent.py | NativeParentRequests.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per property of practical_assignment_v1) |
| from_parent.py | NativeParentRequests.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (one field per property of practical_assignment_v1) |
| from_parent.py | NativeParentRequests.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py _operations (TerminalExecution.validate_assignment); the checks against the parent's launch form and runtime_* tables are checks of a commission: not carried |
| goal.py | NativeGoal | episode function | goal.py GOAL; task.py GOAL_INSTRUCTION and _instructions |
| goal.py | NativeGoal.instructions | episode function | goal.py GOAL; task.py GOAL_INSTRUCTION and _instructions |
| initial_information.py | initial_information | episode function | task.py decide (settings['initial_information'] shown as execution_initial_information) |
| internal_summary.py | native_decision_snapshot | episode function | messages/internal_summary.py internal_summary and task.py decide; the old-runner fields of the snapshot (working_state, pending_work, report_deliveries, ...) are not carried |
| internal_summary.py | NativeInternalSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | NativeInternalSummary._with_selected_execution_task | episode function | messages/internal_summary.py _selected_execution_task (NMF and HMMER job views unplaced -> raise) |
| internal_summary.py | NativeInternalSummary.decision_context | episode function | messages/internal_summary.py internal_summary |
| presentation.py | present_context | episode function | task.py _task_text (the episode's own rendering of the task in decide); the per-context renderers and scientific_prompt_states are old-runner prompt machinery |
| received_api_reports.py | received_api_reports | machinery | selects the old reader catalog authority (catalog.configured/received); results/API role |
| received_execution_information.py | received_execution_information | machinery | selects the old reader catalog authority (catalog.configured/received); results/API role |
| received_records.py | NativeReceivedRecords | machinery | custody of received handoffs/results over self.store.read_snapshot and the old job_progress_provider reader (system custody, README 3c/3e); results role |
| received_records.py | NativeReceivedRecords._context_target | machinery | custody of received handoffs/results over self.store.read_snapshot and the old job_progress_provider reader (system custody, README 3c/3e); results role |
| received_records.py | NativeReceivedRecords._received | machinery | custody of received handoffs/results over self.store.read_snapshot and the old job_progress_provider reader (system custody, README 3c/3e); results role |
| received_records.py | NativeReceivedRecords.initial_references | episode function | messages/read_from_parent.py record_refs field of ASSIGNMENT_FORM |
| resource_information.py | NativeResourceInformation | episode function | unplaced: the parent-visible resource tool contract list; the parent writes its own text (README 5 item 10) |
| resource_information.py | NativeResourceInformation.resource_tool_contracts | episode function | unplaced: the parent-visible resource tool contract list; the parent writes its own text (README 5 item 10) |
| science.py | NativeScienceInputs | machinery | checks of the commission against the old runner's runtime_episodes request and Store (masking, utility, NMF, immutable versions); a wrong commission fails (rule 1) |
| science.py | NativeScienceInputs._masking_inputs | machinery | checks of the commission against the old runner's runtime_episodes request and Store (masking, utility, NMF, immutable versions); a wrong commission fails (rule 1) |
| science.py | NativeScienceInputs._utility_inputs | machinery | checks of the commission against the old runner's runtime_episodes request and Store (masking, utility, NMF, immutable versions); a wrong commission fails (rule 1) |
| science.py | NativeScienceInputs._expression_nmf_inputs | machinery | checks of the commission against the old runner's runtime_episodes request and Store (masking, utility, NMF, immutable versions); a wrong commission fails (rule 1) |
| science.py | NativeScienceInputs._versions | machinery | checks of the commission against the old runner's runtime_episodes request and Store (masking, utility, NMF, immutable versions); a wrong commission fails (rule 1) |
| science.py | NativeScienceInputs._check_parent_inputs | machinery | checks of the commission against the old runner's runtime_episodes request and Store (masking, utility, NMF, immutable versions); a wrong commission fails (rule 1) |
| state.py | NativeState | machinery | PracticalState delegate and parent-input re-check (file ledger and runtime_episodes); receipts are tool outcomes in the summary |
| state.py | NativeState.initialize | machinery | PracticalState delegate and parent-input re-check (file ledger and runtime_episodes); receipts are tool outcomes in the summary |
| state.py | NativeState.state | machinery | PracticalState delegate and parent-input re-check (file ledger and runtime_episodes); receipts are tool outcomes in the summary |
| task.py | NativeTask | episode function | task.py decide / action / exec_command (the generic old runner loop parts are machinery: journal, inprocess_replay, decision_exchanges, checkpoint restore) |
| task.py | NativeTask.next | episode function | task.py decide / action / exec_command (the generic old runner loop parts are machinery: journal, inprocess_replay, decision_exchanges, checkpoint restore) |
| task.py | NativeTask.apply_response | episode function | task.py decide / action / exec_command (the generic old runner loop parts are machinery: journal, inprocess_replay, decision_exchanges, checkpoint restore) |
| task.py | NativeTask.execute | episode function | task.py decide / action / exec_command (the generic old runner loop parts are machinery: journal, inprocess_replay, decision_exchanges, checkpoint restore) |
| task_decision.py | NativeTaskDecision | episode function | task.py decide and action (call: the model request and its answer; the exchange protocol around it is machinery) |
| task_decision.py | NativeTaskDecision.call | episode function | task.py decide and action (call: the model request and its answer; the exchange protocol around it is machinery) |
| task_decision.py | NativeTaskDecision.instructions | episode function | task.py _instructions |
| task_decision.py | NativeTaskDecision.conversation_key | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.interpretation_context | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.exchange_schema | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.exchange_response | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.exchange_decision | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_decision.py | NativeTaskDecision.decision_completion | machinery | decision-exchange loop / saved-request checks / conversation state (README 3a) |
| task_instructions.py | instructions | episode function | task.py _instructions (composition: specialist text, launch library, tool knowledge) |
| task_report.py | NativeTaskReport | machinery | report finish machinery (runtime_forms, release, pending_handles) |
| task_report.py | NativeTaskReport.finish | machinery | report finish machinery (runtime_forms, release, pending_handles) |
| task_state.py | NativeTaskState | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.__init__ | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.bind_execution_context | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.record_execution_failure | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.restore_checkpoint | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.restore | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.record_effect | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_state.py | NativeTaskState.checkpoint | machinery | checkpoint/restore/record_effect/execution-failure bookkeeping (README 3e); a failed command is a receipt returned by the tool |
| task_suspension.py | NativeTaskSuspension | machinery | wait/suspension machinery |
| task_suspension.py | NativeTaskSuspension.suspension_changed | machinery | wait/suspension machinery |
| terminal_execution.py | TerminalExecutionBehavior | episode function | task.py / messages/* (the terminal-execution intent) |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | episode function | settings: resources, initial_information (task.py _resource_configuration, _resource) |
| terminal_execution.py | TerminalExecutionBehavior._operations | episode function | task.py _operations |
| terminal_execution.py | TerminalExecutionBehavior._assignment | episode function | messages/read_from_parent.py read_from_parent and task.py _operations |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | machinery | PracticalState directory under the coordinator (old file ledger) |
| terminal_execution.py | TerminalExecutionBehavior.initialize | machinery | PracticalState initialization (file ledger); initial validations are messages/internal_summary.py internal_summary |
| terminal_execution.py | TerminalExecutionBehavior.state | machinery | PracticalState lookup (file ledger) |
| terminal_execution.py | TerminalExecutionBehavior.as_record | machinery | binding's own as_record() |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | machinery | credit_kind deleted (README 3d) |
| terminal_execution.py | TerminalExecutionBehavior.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | episode function | task.py TOOLS (tool only) |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent |
| terminal_execution.py | TerminalExecutionBehavior.initial_decision_context | episode function | task.py decide (execution_initial_information) |
| terminal_execution.py | TerminalExecutionBehavior._resource_information | episode function | task.py _resource |
| terminal_execution.py | TerminalExecutionBehavior._resource_instructions | episode function | task.py _instructions (LaunchInstructions.for_resource) |
| terminal_execution.py | TerminalExecutionBehavior.instructions | episode function | task.py GOAL_INSTRUCTION, _instructions |
| terminal_execution.py | TerminalExecutionBehavior.decision_context | episode function | task.py decide and messages/internal_summary.py internal_summary |
| terminal_execution.py | TerminalExecutionBehavior.catalog | episode function | task.py EXEC_COMMAND, _output_schema |
| terminal_execution.py | TerminalExecutionBehavior.execute | episode function | task.py exec_command (BLOCKED-ON-JOB-SERVICE: job_access.exec_command) and action (validation of the model's operands) |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | episode function | messages/internal_summary.py _completion |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator delegate (README 3d, 7b) |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (OWN_SOURCES, LIBRARY_SOURCES) |
| terminal_execution.py | TerminalExecutionBehavior.facts | episode function | messages/final_to_parent.py _facts |
| terminal_execution.py | TerminalExecutionBehavior.resolve | episode function | messages/final_to_parent.py _resolver |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | episode function | messages/final_to_parent.py validate_report (called from final_to_parent) |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | episode function | credit.py credit |
| to_parent.py | NativeParentReturns | episode function | messages/final_to_parent.py |
| to_parent.py | NativeParentReturns.required_return_sources | machinery | required_return_sources returned () (parent-form machinery, README 3b C4) |
| to_parent.py | NativeParentReturns.facts | episode function | messages/final_to_parent.py _facts (practical facts, handoff refs, empty result sources); native result family branches belong to the results role |
| to_parent.py | NativeParentReturns._live_facts | episode function | messages/final_to_parent.py _facts (practical facts, handoff refs, empty result sources); native result family branches belong to the results role |
| to_parent.py | NativeParentReturns.validate_report | episode function | messages/final_to_parent.py validate_report (the UniProt/Rfam/native adapters of the results role are unplaced) |
| waiting.py | perform_selected_native_wait | machinery | wait machinery (perform_selected_wait) |
| work_operations.py | NativeWorkOperations | episode function | task.py exec_command and action (the per-execute parent-input check is read_from_parent / _operations) |
| work_operations.py | NativeWorkOperations.catalog | episode function | task.py exec_command and action (the per-execute parent-input check is read_from_parent / _operations) |
| work_operations.py | NativeWorkOperations.execute | episode function | task.py exec_command and action (the per-execute parent-input check is read_from_parent / _operations) |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py (_request_yield_class, _task_yield_profile, yield_controller: completion controller) |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py (_request_yield_class, _task_yield_profile, yield_controller: completion controller) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py (_request_yield_class, _task_yield_profile, yield_controller: completion controller) |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py (_request_yield_class, _task_yield_profile, yield_controller: completion controller) |
| yield_estimator.py | ExecutionEpisodeYield._launch_local_yield_controller | episode function | yield_estimator.py (_request_yield_class, _task_yield_profile, yield_controller: completion controller) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator delegate (README 3d, 7b) |
