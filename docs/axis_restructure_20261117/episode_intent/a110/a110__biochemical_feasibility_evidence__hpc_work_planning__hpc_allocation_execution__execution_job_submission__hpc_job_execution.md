# Intent: a110/biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution

Read from its own files at commit `97308b94c`. It is a leaf, with no child folders. Old role name: `launch_hpc`. Old commissioning parent: `execution_job_submission` (role `launch`).

## Purpose (its own words)

`goal.py` delegates to the per-resource `TerminalExecutionBehavior.instructions` in this episode's own `terminal_execution.py`:

"You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit enter the iterator, including failure or zero progress. Host bookkeeping records command versions and actual native job identities; do not maintain a parallel receipt ledger. If a submission outcome is uncertain, investigate that original submission rather than create a duplicate. ... target=resource runs on the assigned resource; target=coordinator runs in the local run directory for supplied-input and transport work. ... execution_resource.ssh_argv, when present, is the exact configured transport prefix ... The episode iterator decides continuation from credit; add no stopping budget."

After this text it appends the frozen launch-instruction-library sections for the resource (`launch_instructions.for_resource`).

The episode runs the actual PBS job on Aurora. Through the transport, it writes and runs whatever commands the job needs until the requested endpoint predicates hold. The parent HPC episode supplies the frozen job (`hpc_execution_job`).

## Task and instructions

`task_instructions.py` composes the full text. The specialist instructions above replace the shared INSTRUCTIONS (`replaces_default_instructions`). Old-runner blocks follow: tool_knowledge, launch_instruction_library, `pending_child_delivery` repair, and the exchange-protocol history guidance. Unlike the Launch parent, there is no reason/wait text.

## What it reads from its parent's assignment (`from_parent.py`)

- `assignment_schema(role)`: anyOf the per-resource `practical_assignment_v1` schemas for configured resources of kind `hpc` (pbs_ssh), with `resource_id` required.
- `child_assignment_schema`: when the commissioning Launch sits under an `hpc` ancestor, the assignment must be one of the Launch's permitted frozen `hpc` requests (`enum`). This is how the HPC plan's request is held unchanged.
- `prepare_assignment`:
  - validate the request;
  - check its resource kind matches the role;
  - require parent role `launch`;
  - check the flux-balance inputs and input versions against the parent Launch's `immutable_input_versions`.
- `NativeScienceInputs._check_parent_inputs` re-reads the parent Launch's recorded request (`runtime_episodes` by path) and re-validates before every execute and initialize.
- The parent HPC binding's `LaunchPreparation.initial_decision_context` adds `hpc_execution_job` (plan_id, objective, scientific_manifest, acceptance, supplied_input_file, coordinator_workspace, instructions) for role `launch_hpc`.

## Children it may commission

None. `child_roles` and `allowed_children` are `()`.

## Decision state and what the model sees

`native_decision_snapshot` builds the old generic context (as in the Launch episode). The episode's own `NativeInternalSummary.decision_context` adds:
- the delegate's `decision_context`: `execution_assignment`, `execution_resource` (resource_kind, workspace, kind, policy, account, ssh_argv, python_executable, scheduler, inventory_snapshot), `coordinator_workspace`, `execution_progress` (PracticalState credit view), `execution_completion` (completion proof);
- for a compact flux-balance assignment: `practical_assignment`, `practical_progress` and `practical_completed`.

`presentation.present_context` is the same renderer choice as the Launch episode, but goes through the old `providers` module alias. Decision inputs are as in Launch. Execution expectations are keyed by the path role, and a job-source branch calls `resource_estimator.estimate`.

## Tools it offers

`catalog` = `operation_catalog('hpc')` from library `execution_operation_information`, i.e. `exec_command` per the instructions. Arguments include `target` (resource|coordinator), `workdir` and `env`. `TerminalExecutionBehavior.execute`:
- validates the action through `TerminalExecution.validate_action`;
- begins or finishes an intent in `PracticalState`, so a completed intent replays its receipt;
- runs the command, finalizes the scientific command, and updates cwd/env and the revision when workdir is inside the assignment workspace;
- assesses validations;
- publishes a practical receipt Source (`PracticalReceiptInformation`).

Failure becomes a factual `execution_action_failed` outcome. Common actions: `tool` only.

## Credit

`credit_kind` = 'operational'. Live credit = the delegate `PracticalState.credit_view()`: credit earned through validated receipts and satisfied keys. The closed-credit snapshot machinery is identical to the Launch episode (`runtime_forms`, receipt inheritance, history digest).

## Continuation (`yield_estimator.py`)

Old behaviour: `YieldController(epoch, initial_credit, cutoff, YieldParameters, estimate_with_context=PracticalYieldEstimator(verify_completion))`.
- The profile is `task_yield_profiles['launch_hpc:' + request yield class]`.
- `require_private_yield` must be true.
- The estimator forecasts exact zero once a verified completion proof (all requested endpoint predicates validated) exists. `verify_completion` replays the closed verdict from `runtime_observations` once the episode has closed.

Mapping: work proceeds until the requested endpoint completes, so the fit is **CompletionYieldEstimator(initial_credit, target)**:
- target = the assignment's total endpoint credit, as defined by its validations;
- settings come from the `launch_hpc:<class>` task yield profile (cutoff, parameters).

## What it reports to its parent (`to_parent.py`)

Facts:
- the delegate's `practical_completed`, `practical_receipt_digests` and `practical_receipt_refs` (namespace `practical_receipt`);
- `execution_handoff_refs`: received handoffs plus its own returnable practical receipts;
- `execution_result_refs`, `execution_file_source_refs`, `execution_file_capture_outcomes`, `execution_result_origin`;
- `execution_completed` = `practical_completed`;
- empty FBA fact sources;
- the closed-credit snapshot.

`required_return_sources` returns `()`. The Launch episode's version returns `execution_handoff_refs`. The report must equal the recorded facts.

## Differences from its sibling `local_job_execution`

The two folders are copies. They differ in:
- the role (`launch_hpc` vs `launch_local`) and binding path;
- `child_assignment_schema`: hpc restricts to the frozen HPC request enum when under an `hpc` ancestor;
- `prepare_assignment`: local also accepts a compact flux-balance resource assignment from the Launch's request binding;
- `internal_summary`: for a non-compact assignment, local builds `selected_execution_task` from its single request; hpc shows nothing extra;
- the yield profile key prefix.

Native flux balance is only allowed on `local` resources (configuration raises `native_flux_balance_resource_execution_binding_unfinished:hpc`).

## File-by-file

Full counts are in `runs/carry_over/calls/a110_04.tsv`.

| Old file | Lines | Own intent | Old-runner names |
|---|---|---|---|
| goal.py | 6 | Delegate instructions | none |
| terminal_execution.py | 226 | Execution-agent instructions, resource info, decision context, exec_command execute, practical facts/credit/completion | BindingContext.assignment×9/episode_id/run_id/role; `communication.plain`×9, `validate_form`; `practical_yield.PracticalYieldEstimator` |
| task_instructions.py | 20 | Composition | `runtime_prompt.INSTRUCTIONS`×4, `DECISION_EXCHANGE_PROTOCOL`; `self.workflow.job_episodes`, `.is_job_source`, `.specialist`, `.binding_context`, `.knowledge`, `.launch_instructions`, `.native_event_information`, `.decision_protocol` |
| task.py | 217 | Action loop (reason-commit validation present but not permitted) | As Launch's task.py plus `self.workflow.reasoning_action_schema`; `runtime.*`; `providers.ModelCallError`; tables `runtime_actions`, `runtime_model_calls`, `runtime_episodes` |
| task_decision.py | 357 | Decision inputs, exchange protocol, provider call | As Launch's task_decision.py; `self.workflow.job_episodes`, `.is_job_source` |
| task_state.py | 107 | Source state | As Launch's task_state.py |
| task_report.py | 22 | Finish | `runtime.form_with_facts`, `Record`; `self.workflow.journal`, `.facts`, `.release`, ...; table `runtime_forms` |
| task_suspension.py | 8 | Suspension | `self.workflow.execution_handle`, `.execution_backend` |
| waiting.py | 10 | Wait wrapper | `self.workflow.perform_selected_wait`; `runtime.EventTargetError`, `_wait_target_feedback` |
| internal_summary.py | 78 | native_decision_snapshot + decision_context | About 20 `self.workflow.*` names; `runtime.FACT_*`; `self.services.scientific_parent_task`; table `runtime_actions` |
| presentation.py | 61 | Renderer choice | `providers.*` alias (apply_state_frame×3, render_biochemical_feasibility_evidence_prompt, text_instructions, ...) |
| episode.py | 84 | Binding: role launch_hpc, no children, tool only | old hook names; many redundant imports |
| configuration.py | 73 | Same as Launch's configuration.py | `numerical.YieldController`×2, `YieldParameters`×2 |
| credit.py | 136 | Closed/live operational credit (live = delegate) | As Launch's credit.py (tables `runtime_episodes`, `runtime_forms`, `runtime_observations`, `runtime_receipt_inheritance`, `runtime_record_receipts`) |
| yield_estimator.py | 48 | Continuation (above) | `numerical.YieldController`, `YieldParameters`; `practical_yield.PracticalYieldEstimator`×4 |
| completion.py | 49 | Delegate completion / closed verdict | `UnitRef`, `NumericBand`, `ESTIMATOR_VERSION`, `_same`×4; table `runtime_observations` |
| from_parent.py | 85 | Assignment (above) | none beyond helpers |
| to_parent.py | 53 | Facts/validate | BindingContext.scope; `self.services.annotation_task_required` |
| science.py | 51 | Flux inputs, input versions, _check_parent_inputs | BindingContext.path×3/assignment/role; `EpisodeReturnRecords`; table `runtime_episodes` |
| state.py | 27 | initialize/state via delegate | BindingContext.assignment |
| received_records.py | 87 | _context_target, _received, initial_references | BindingContext.assignment×8/role×7 |
| resource_information.py | 62 | resource_tool_contracts (copy) | none |
| work_operations.py | 32 | catalog/execute via delegate (+ compact outcome view) | BindingContext.* |
| execution_contracts.py | 44 | Constants and op catalog | `communication.*` imports |
| binding_record.py | 8 | as_record | none |
| initial_information.py | 8 | catalog readers | old catalog protocol |
| received_execution_information.py | 4 | catalog configured/received | old catalog protocol |
| __init__.py | 0 | none | none |

## Carried over

One row per old function, class and method (`runs/carry_over/functions/...tsv`, 124 rows). Kind: `machinery` (old runner, not carried), `episode function` (new place), `unplaced` (not carried, reported with its reason in the blocked file). Carried 19 November 2026 into the ten-file form; the library calls are `episode_support/...` names; the job service is BLOCKED-ON-JOB-SERVICE (see the blocked file). Library candidates (episode-local copies of what the library keeps only inside the file-backed `PracticalState`): `messages/internal_summary.py` `completion_proof`, `returnable_handoff`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| binding_record.py | NativeBindingRecord | machinery | the binding's own as_record() (README 3) |
| binding_record.py | NativeBindingRecord.as_record | machinery | the binding's own as_record() (README 3) |
| completion.py | NativeCompletion | machinery | completion proof as a controller input and its re-validation against runtime_observations: the controller is CompletionYieldController in yield_estimator.py; the proof itself is computed in messages/internal_summary.py completion_proof (library candidate) |
| completion.py | NativeCompletion.completion_for_action | machinery | completion proof as a controller input and its re-validation against runtime_observations: the controller is CompletionYieldController in yield_estimator.py; the proof itself is computed in messages/internal_summary.py completion_proof (library candidate) |
| completion.py | NativeCompletion._closed_completion_verdict | machinery | completion proof as a controller input and its re-validation against runtime_observations: the controller is CompletionYieldController in yield_estimator.py; the proof itself is computed in messages/internal_summary.py completion_proof (library candidate) |
| completion.py | NativeCompletion.verify_completion | machinery | completion proof as a controller input and its re-validation against runtime_observations: the controller is CompletionYieldController in yield_estimator.py; the proof itself is computed in messages/internal_summary.py completion_proof (library candidate) |
| configuration.py | NativeConfiguration | episode function | the values become ctx.settings: resources, initial_information, coordinator_workspace, launch_instructions_directory, tool_knowledge_directory, task_yield_profiles (task.py _resource_configuration, terminal, resource_information, decide; yield_estimator.py); the old-runner wiring (store, tool registry, progress provider, local file sources, flux balance input/request bindings, results yield profiles) is machinery and not carried |
| configuration.py | NativeConfiguration.__init__ | episode function | the values become ctx.settings: resources, initial_information, coordinator_workspace, launch_instructions_directory, tool_knowledge_directory, task_yield_profiles (task.py _resource_configuration, terminal, resource_information, decide; yield_estimator.py); the old-runner wiring (store, tool registry, progress provider, local file sources, flux balance input/request bindings, results yield profiles) is machinery and not carried |
| credit.py | ExecutionEpisodeCredit | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | constant 'operational': no credit kind in the final form; credit.py is the operational credit |
| credit.py | ExecutionEpisodeCredit._closed_credit_carrier | machinery | frozen closed credit re-checked against runtime_episodes, runtime_forms, runtime_observations and the receipt tables (journal re-validation); the system hands completion['credit'] to final_to_parent |
| credit.py | ExecutionEpisodeCredit._closed_credit_receipts | machinery | frozen closed credit re-checked against runtime_episodes, runtime_forms, runtime_observations and the receipt tables (journal re-validation); the system hands completion['credit'] to final_to_parent |
| credit.py | ExecutionEpisodeCredit._closed_credit_value | machinery | frozen closed credit re-checked against runtime_episodes, runtime_forms, runtime_observations and the receipt tables (journal re-validation); the system hands completion['credit'] to final_to_parent |
| credit.py | ExecutionEpisodeCredit._closed_credit_facts | machinery | frozen closed credit re-checked against runtime_episodes, runtime_forms, runtime_observations and the receipt tables (journal re-validation); the system hands completion['credit'] to final_to_parent |
| credit.py | ExecutionEpisodeCredit._closed_operational_credit_view | machinery | frozen closed credit re-checked against runtime_episodes, runtime_forms, runtime_observations and the receipt tables (journal re-validation); the system hands completion['credit'] to final_to_parent |
| credit.py | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (the closed-view branch is machinery: frozen closed credit re-checked against runtime_episodes, runtime_forms, runtime_observations and the receipt tables (journal re-validation); the system hands completion['credit'] to final_to_parent) |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit (project_practical_credit over the summary's receipts) |
| credit.py | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit |
| episode.py | ExecutionEpisode | episode function | episode.py HpcJobExecution |
| episode.py | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | ExecutionEpisode.permitted_common_actions | episode function | task.py action: only ToolCall exec_command is offered |
| execution_contracts.py | native_result_operation_catalog | unplaced | catalogue of the results role (execution.results.status/collect/read), which only the commissioning parent's resource_tool_contracts used; this episode offers exec_command only |
| from_parent.py | NativeParentRequests | episode function | messages/read_from_parent.py |
| from_parent.py | NativeParentRequests._permitted | unplaced | check of the commissioned resource against the launch parent's own constraints (allowed_resource_ids, allowed_kinds): a check of a commission (rule 1), not carried; reported in contract_misfits |
| from_parent.py | NativeParentRequests._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (the hpc request schema; the flux balance alternatives and compact local assignment are not offered for an hpc resource) |
| from_parent.py | NativeParentRequests._launch | unplaced | validation of the parent's own execution_launch_assignment_v1 (a child cannot read its parent's assignment); reported in contract_misfits |
| from_parent.py | NativeParentRequests.child_assignment_schema | unplaced | the frozen-request enum (a launch parent under an hpc ancestor may pass only its already authorised hpc request) is a check of a commission against the parent's assignment: not carried (rule 1); the parent's msg_to_child copies its authorised request. Reported in contract_misfits |
| from_parent.py | NativeParentRequests.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | NativeParentRequests.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment); the checks against the parent launch request (_flux_balance_inputs, _versions, resource kind of the parent) are checks of a commission and are not carried |
| goal.py | NativeGoal | episode function | goal.py GOAL and task.py INSTRUCTIONS |
| goal.py | NativeGoal.instructions | episode function | task.py instructions (the delegate's text, INSTRUCTIONS) and goal.py GOAL |
| initial_information.py | initial_information | episode function | task.py resource_information (settings['initial_information'] of the assigned resource, shown as execution_resource.inventory_snapshot); the old catalog.readers protocol is machinery |
| internal_summary.py | native_decision_snapshot | machinery | generic old-runner decision snapshot (working_state, visible_record_refs, pending_work, report_deliveries, runtime_actions, journal.elapsed_view); what is the episode's own is in messages/internal_summary.py and task.py decide |
| internal_summary.py | NativeInternalSummary | episode function | messages/internal_summary.py internal_summary and task.py decide |
| internal_summary.py | NativeInternalSummary._with_selected_execution_task | unplaced | only acts for compact flux balance assignments (read_request_binding over the old store, services.scientific_parent_task), which an hpc assignment never is; returned its value unchanged for hpc |
| internal_summary.py | NativeInternalSummary.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide (execution_assignment, execution_resource, coordinator_workspace, execution_progress, execution_completion); the compact flux balance branch is not for hpc |
| presentation.py | present_context | episode function | task.py _task_text and decide (the rendered text travels as the context field 'task'); the state-frame protocol (apply_state_frame, provider.scientific_prompt_states) is machinery and the old library render_hpc_prompt was not found (reported) |
| received_execution_information.py | received_execution_information | machinery | old catalog protocol (catalog.configured/received readers); this role selected no result readers |
| received_records.py | NativeReceivedRecords | episode function | messages/internal_summary.py (handoff_refs from the episode's own receipts) |
| received_records.py | NativeReceivedRecords._context_target | episode function | messages/internal_summary.py returnable_handoff (the receipt's handoff is for this exact assignment); the compact flux balance branch is not for hpc |
| received_records.py | NativeReceivedRecords._received | episode function | messages/internal_summary.py handoff_refs: the episode's own returnable receipts; the known-record and result reading (store.get over known_record_refs, _read_result) is old-runner custody and result acquisition, not carried (no records are received by this role) |
| received_records.py | NativeReceivedRecords.initial_references | machinery | returned [] for this role (requests is empty for launch_hpc; flux balance inputs are local-only); initial known records are custody |
| resource_information.py | NativeResourceInformation | unplaced | the commissioning parent's text about resources and commission routes |
| resource_information.py | NativeResourceInformation.resource_tool_contracts | unplaced | the commissioning parent's catalogue of resource tool contracts and commission routes; not this episode's |
| science.py | NativeScienceInputs | unplaced | flux balance input checks of a commission (local-only) and the re-validation against the parent's recorded request |
| science.py | NativeScienceInputs._versions | unplaced | check of the pinned immutable_input_versions of the parent launch request (a check of a commission, rule 1; flux balance inputs are local-only) |
| science.py | NativeScienceInputs._flux_balance_inputs | unplaced | flux balance input binding (a check of a commission); not for hpc: the flux balance requested job is refused on an hpc resource |
| science.py | NativeScienceInputs._matches_flux_balance_assignment | unplaced | compact flux balance assignment comparison (local sibling only) |
| science.py | NativeScienceInputs._check_parent_inputs | machinery | re-reading the parent launch's recorded request from runtime_episodes before every execute and initialize (journal re-validation) |
| state.py | NativeState | machinery | delegation to the file-backed PracticalState (initialize/state) and the compact flux balance bindings: replaced by view.outcomes (receipts) in messages/internal_summary.py |
| state.py | NativeState.initialize | machinery | delegation to the file-backed PracticalState (initialize/state) and the compact flux balance bindings: replaced by view.outcomes (receipts) in messages/internal_summary.py |
| state.py | NativeState.state | machinery | delegation to the file-backed PracticalState (initialize/state) and the compact flux balance bindings: replaced by view.outcomes (receipts) in messages/internal_summary.py |
| task.py | NativeTask | episode function | task.py decide, action and exec_command |
| task.py | NativeTask.next | episode function | task.py decide (the unit source); the old-runner replay/closed-run/SourceEnd branches are machinery |
| task.py | NativeTask.apply_response | episode function | task.py action (validation of the answer; Rejected for an invalid one) |
| task.py | NativeTask.execute | episode function | task.py exec_command (the tool branch); the reason/wait/child/redeliver branches are not offered by this role (permitted_common_actions is ('tool',)) |
| task_decision.py | NativeTaskDecision | episode function | task.py decide |
| task_decision.py | NativeTaskDecision.call | episode function | task.py decide (ModelRequest REASONING with the context and output schema); the provider call, saved decision inputs and conversation state are machinery |
| task_decision.py | NativeTaskDecision.instructions | episode function | task.py instructions |
| task_decision.py | NativeTaskDecision.conversation_key | machinery | conversation state across provider calls (every ModelRequest carries the full context) |
| task_decision.py | NativeTaskDecision.interpretation_context | machinery | decision-exchange loop / saved-request checks (exchange_decision, request_context) |
| task_decision.py | NativeTaskDecision.exchange_schema | machinery | decision-exchange loop / saved-request checks (exchange_decision, request_context) |
| task_decision.py | NativeTaskDecision.exchange_response | machinery | decision-exchange loop / saved-request checks (exchange_decision, request_context) |
| task_decision.py | NativeTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop / saved-request checks (exchange_decision, request_context) |
| task_decision.py | NativeTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop / saved-request checks (exchange_decision, request_context) |
| task_decision.py | NativeTaskDecision.exchange_decision | machinery | decision-exchange loop / saved-request checks (exchange_decision, request_context) |
| task_decision.py | NativeTaskDecision.decision_completion | machinery | provider routing of the decision prompt (complete_with_presentation, provider patching) |
| task_instructions.py | instructions | episode function | task.py instructions (goal text, resource sections, tool-knowledge and launch-library texts; the pending_child_delivery and decision-exchange paragraphs are old-runner text not carried) |
| task_report.py | NativeTaskReport | machinery | report_form machinery: form_with_facts over the parent-written form, runtime_forms, workflow.release; the episode's own report is messages/final_to_parent.py final_to_parent |
| task_report.py | NativeTaskReport.finish | machinery | report_form machinery: form_with_facts over the parent-written form, runtime_forms, workflow.release; the episode's own report is messages/final_to_parent.py final_to_parent |
| task_state.py | NativeTaskState | machinery | checkpoint/restore and source-state bookkeeping (restore_checkpoint, restore, record_effect, checkpoint, bind_execution_context): the system journals units and restores the view |
| task_state.py | NativeTaskState.__init__ | machinery | checkpoint/restore and source-state bookkeeping (restore_checkpoint, restore, record_effect, checkpoint, bind_execution_context): the system journals units and restores the view |
| task_state.py | NativeTaskState.bind_execution_context | machinery | checkpoint/restore and source-state bookkeeping (restore_checkpoint, restore, record_effect, checkpoint, bind_execution_context): the system journals units and restores the view |
| task_state.py | NativeTaskState.record_execution_failure | episode function | task.py exec_command (a failed command is a recorded failure in the receipt outcome, returned as the unit's outcome); the runtime_actions write is machinery |
| task_state.py | NativeTaskState.restore_checkpoint | machinery | checkpoint/restore and source-state bookkeeping (restore_checkpoint, restore, record_effect, checkpoint, bind_execution_context): the system journals units and restores the view |
| task_state.py | NativeTaskState.restore | machinery | checkpoint/restore and source-state bookkeeping (restore_checkpoint, restore, record_effect, checkpoint, bind_execution_context): the system journals units and restores the view |
| task_state.py | NativeTaskState.record_effect | machinery | checkpoint/restore and source-state bookkeeping (restore_checkpoint, restore, record_effect, checkpoint, bind_execution_context): the system journals units and restores the view |
| task_state.py | NativeTaskState.checkpoint | machinery | checkpoint/restore and source-state bookkeeping (restore_checkpoint, restore, record_effect, checkpoint, bind_execution_context): the system journals units and restores the view |
| task_suspension.py | NativeTaskSuspension | machinery | suspension/wait machinery (execution_backend.set_suspension) |
| task_suspension.py | NativeTaskSuspension.suspension_changed | machinery | suspension/wait machinery (execution_backend.set_suspension) |
| terminal_execution.py | TerminalExecutionBehavior | episode function | task.py (tools, decide, action), messages/*, credit.py |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | episode function | task.py _resource_configuration / terminal over ctx.settings (resources, initial_information, coordinator_workspace); the old checks explicit_execution_resources_required and initial_inventory_resource_not_bound are settings of the run, not re-checked here |
| terminal_execution.py | TerminalExecutionBehavior._operations | episode function | task.py terminal |
| terminal_execution.py | TerminalExecutionBehavior._assignment | episode function | task.py terminal (execution_resource_assignment_mismatch, validate_assignment) and messages/read_from_parent.py read_from_parent |
| terminal_execution.py | TerminalExecutionBehavior._state_directory | machinery | directory of the file-backed PracticalState (host receipts under the run directory): replaced by receipts written through ctx.store |
| terminal_execution.py | TerminalExecutionBehavior.initialize | machinery | initialises the file-backed PracticalState and its initial validations; the initial validations are recomputed in messages/internal_summary.py |
| terminal_execution.py | TerminalExecutionBehavior.state | machinery | the file-backed PracticalState handle |
| terminal_execution.py | TerminalExecutionBehavior.as_record | machinery | the binding's own as_record() (README 3) |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | machinery | constant 'operational': no credit kind in the final form |
| terminal_execution.py | TerminalExecutionBehavior.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | episode function | task.py action: only ToolCall exec_command |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) |
| terminal_execution.py | TerminalExecutionBehavior.initial_decision_context | episode function | task.py resource_information / decide (the initial inventory is execution_resource.inventory_snapshot) |
| terminal_execution.py | TerminalExecutionBehavior._resource_information | episode function | task.py resource_information |
| terminal_execution.py | TerminalExecutionBehavior._resource_instructions | episode function | task.py decide (LaunchInstructions.for_resource over the configured resource) |
| terminal_execution.py | TerminalExecutionBehavior.instructions | episode function | task.py INSTRUCTIONS and instructions |
| terminal_execution.py | TerminalExecutionBehavior.decision_context | episode function | task.py decide and messages/internal_summary.py internal_summary |
| terminal_execution.py | TerminalExecutionBehavior.catalog | episode function | task.py operation_catalog / EXEC_COMMAND |
| terminal_execution.py | TerminalExecutionBehavior.execute | episode function | task.py exec_command (BLOCKED-ON-JOB-SERVICE: job_access.exec_command and the job ledger handoff row; PracticalState begin/finish and PracticalReceiptInformation.publish are replaced by the receipt written with ctx.store.artifact) |
| terminal_execution.py | TerminalExecutionBehavior.completion_for_action | machinery | completion proof as a controller input (the controller is CompletionYieldController; the proof is computed in messages/internal_summary.py completion_proof) |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator(verify_completion) becomes CompletionYieldController in yield_estimator.py (README 7b) |
| terminal_execution.py | TerminalExecutionBehavior.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (practical_completed, practical_receipt_digests, practical_receipt_refs) |
| terminal_execution.py | TerminalExecutionBehavior.facts | episode function | messages/final_to_parent.py facts |
| terminal_execution.py | TerminalExecutionBehavior.resolve | machinery | resolution of a receipt reference against PracticalReceiptInformation / the old receipt digests: custody holds the receipt artifacts (returned in record_refs) |
| terminal_execution.py | TerminalExecutionBehavior.validate_report | episode function | messages/final_to_parent.py validate_report (fact comparison kept; the validate_form step is not carried: the parent-written form it checked no longer exists) |
| terminal_execution.py | TerminalExecutionBehavior.credit_view | episode function | credit.py credit |
| to_parent.py | NativeParentReturns | episode function | messages/final_to_parent.py |
| to_parent.py | NativeParentReturns.required_return_sources | machinery | returned () (the parent selects return fields, README 3b C4) |
| to_parent.py | NativeParentReturns.facts | episode function | messages/final_to_parent.py facts (the _closed_credit_facts part is machinery: the system hands completion['credit'] to final_to_parent) |
| to_parent.py | NativeParentReturns._live_facts | episode function | messages/final_to_parent.py facts (the received-result and handoff reading is over the episode's own receipts; the flux balance empty sources are not for hpc) |
| to_parent.py | NativeParentReturns.validate_report | episode function | messages/final_to_parent.py validate_report (the native_flux_balance_returns step was only for a configured flux balance adapter; the validate_form step is not carried) |
| waiting.py | perform_selected_native_wait | machinery | wait machinery (perform_selected_wait, EventTargetError); the wait action is not carried |
| work_operations.py | NativeWorkOperations | episode function | task.py operation_catalog and exec_command |
| work_operations.py | NativeWorkOperations.catalog | episode function | task.py operation_catalog |
| work_operations.py | NativeWorkOperations.execute | episode function | task.py exec_command (_check_parent_inputs is machinery; the compact flux balance outcome view is not for hpc) |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | messages/read_from_parent.py request_yield_class (read once; the class travels in the parent input) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py yield_controller (profile lookup, execution_original_task_yield_profile_required) |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (the private-yield flag is configuration machinery) |
| yield_estimator.py | ExecutionEpisodeYield._launch_hpc_yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController; target from read_from_parent) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator becomes CompletionYieldController (README 7b) |
