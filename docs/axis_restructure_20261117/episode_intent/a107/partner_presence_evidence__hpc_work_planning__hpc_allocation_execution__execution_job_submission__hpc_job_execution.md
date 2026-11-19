# Episode intent: A107 `hpc_job_execution`

Episode path: `root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution`
Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a107/.../execution_job_submission/hpc_job_execution/<file>` (29 files, no `grading/` or `scoring/` subfolder).
Binding class: `ExecutionEpisode`. Role: `launch_hpc`. Commissioning parent: `execution_job_submission` (role `launch`). Binding version `execution_episode_v1`.

The file set is a copy of `api_job_execution`'s. The eleven files that are byte-identical across all three siblings are described in the api_job_execution intent file; this file covers them only where HPC behaviour flows through them.

## What this episode is for (its goal, in its own words)

goal.py returns `self._delegate(context).instructions(self._practical_context(context))`. That is the `TerminalExecutionBehavior.instructions` text in terminal_execution.py:

> You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit enter the iterator, including failure or zero progress. Host bookkeeping records command versions and actual native job identities; do not maintain a parallel receipt ledger. If a submission outcome is uncertain, investigate that original submission rather than create a duplicate. Use the provided resource-specific instructions, account, storage and existing authentication route. workdir and env apply to the selected command only. target=resource runs on the assigned resource; target=coordinator runs in the local run directory for supplied-input and transport work. Both are ordinary journaled actions; resource computation belongs on its actual allocation. For coordinator-side transfers, execution_resource.ssh_argv, when present, is the exact configured transport prefix. Append the remote shell command as its final argument and preserve stdin. The supplied configuration gives the existing connection details. target=resource uses that transport directly. The episode iterator decides continuation from credit; add no stopping budget.

After that text comes "Resource instructions supplied from the frozen library:", followed by the sections returned by `launch_instructions.for_resource(resource)` for the PBS/SSH resource (Aurora). `replaces_default_instructions = True`.

So the episode runs one HPC (PBS over SSH) job for the parent's selected request, with the model writing shell commands, until the requested endpoint predicates (`usable_handoff` or `completed_job_outputs`) are validated.

## Task and instructions

- task.py, task_state.py, task_report.py, task_suspension.py and waiting.py are identical to the api copy (see that file).
- task_instructions.py differs from the api copy:
  - no REASONING_COMMIT_REQUIREMENT;
  - no wait paragraph;
  - the native-event line is the no-op expression `source.workflow.native_event_information is not None`.
  - The rest is the same: specialist replacement, tool_knowledge and launch_instruction_library text, the pending_child_delivery repair paragraph, and the exchange-protocol history replacement.
- presentation.py is identical. The HPC context is rendered by `render_hpc_prompt` when `is_hpc_context(state)`.

## What it reads from its parent's assignment

- The `assignment_schema(role)` alternatives are hpc resources. The base is `ASSIGNMENT_SCHEMA` (practical_assignment_v1) with `resource_id` and `resource_kind='hpc'` as consts. `requested_job` is an anyOf of the generic job schema, the requested native job schemas, NMF/RNA/Infernal contracts and the preparation job schemas.
- **`child_assignment_schema` is HPC-specific.** When `parent.role == 'launch'` and `'hpc'` is among the parent path's grains, the parent's already-authorized HPC requests are frozen: the schema is `{'type': 'object', 'enum': requests}`, holding the permitted requests whose `resource_kind == 'hpc'`. Without one it raises `frozen_hpc_launch_request_missing`. The docstring reads: "A frozen HPC launch exposes only its already authorized request."
- `prepare_assignment` matches the api copy without `_validate_blast_launch_selection`. It re-validates the parent launch and checks the masking, utility, input-version, native BLAST DB, standard BLAST DB and RNA-structure inputs.
- science.py `_check_parent_inputs` does the same without the API BLAST grader binding.

## Children

None (`child_roles`, `allowed_children` and `entry_roles` are all empty).

## Decision state and what it shows the model

- `native_decision_snapshot` is the same as the api copy.
- `NativeInternalSummary.decision_context` is `self._delegate(context).decision_context(context, view)`. The TerminalExecutionBehavior provides:
  - `execution_assignment`;
  - `execution_resource`: resource_kind, workspace, kind, policy, account, ssh_argv, python_executable, scheduler and inventory_snapshot;
  - `coordinator_workspace`;
  - `execution_progress` (`state.credit_view()`);
  - `execution_completion` (`state.completion_proof()`).
- **`_with_selected_execution_task` is a no-op in the HPC copy** (`return value`), so no `selected_execution_task` view is added. The api and local copies build one.
- task_decision.py adds the same context as the api copy except `waiting_support`. `requested_action_history` is added when `is_hpc_context(context)`.

## Tools it offers

- `permitted_common_actions` is `('tool',)` only.
- The catalog is `TerminalExecutionBehavior.catalog`, i.e. `operation_catalog('hpc')`: the exec_command family from the library execution_operation_information.
- `execute` validates the arguments against the catalog and runs `TerminalExecution.validate_action`, then begins or finishes a `PracticalState` intent.
  - `finalize_scientific_command` is applied to the outcome.
  - cwd and env are tracked only for `target=resource` inside the workspace.
  - Validations are assessed and the receipt is published through `PracticalReceiptInformation`.
  - An invalid argument returns `status: invalid` with feedback.

## Credit

- `credit_kind` is `'operational'`.
- The live credit is `_delegate(context).credit_view(...)` = `PracticalState.credit_view()`, the terminal state's progress credit.
- The closed-credit snapshot (`execution_closed_operational_credit_v1`) is the same as the api copy. It reads runtime_forms, runtime_episodes, runtime_observations and the receipt inheritance tables.
- Credit is never bounded.

## Continuation

- `yield_controller` requires `require_private_yield`. It builds `YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters), estimate_with_context=PracticalYieldEstimator(verify_completion))`.
- Profile key: `'launch_hpc:' + _request_yield_class(request)`. For practical_assignment_v1 the class is `practical_hpc[_native_*...]_handoff|_outputs`, built from the `requested_job` native keys and `endpoint`.
- `practical_estimator` delegates to `TerminalExecutionBehavior.practical_estimator` (PracticalYieldEstimator over `state.verify_completion`).
- New estimator: **completion with a target**. The target is the validated endpoint (`completion_proof`), and verified completion gives zero future gain. Settings: `task_yield_profiles['launch_hpc:<class>'] = {cutoff, parameters}`.
- completion.py: `_closed_completion_verdict` as in the api copy; otherwise `self.state(context).verify_completion(proof)`.

## What it reports to its parent

to_parent.py `_live_facts` (HPC and local):
- the empty native fact families;
- the delegate facts: `practical_completed`, `practical_receipt_digests`, `practical_receipt_refs`;
- `execution_handoff_refs`: returnable handoff targets from the received refs and practical receipt refs, checked by `_context_target` (assignment equality);
- `bvbrc_appservice_support_refs`, when an AppService is configured;
- `execution_blast_hsps: []`;
- `execution_result_refs`: result bodies that have windows;
- `execution_file_source_refs` and `execution_file_capture_outcomes`;
- `execution_result_origin`: `NATIVE_RESULT_ORIGIN` when any windows exist;
- `execution_completed`.

`validate_report` is the same as the api copy: the adapters, UniProt and Rfam, then every x-source field must equal its fact. `finish` is the same as task_report.py.

## Configuration

Identical to the api copy (configuration.py): resources with kind `pbs_ssh` map to `hpc`, and a `TerminalExecutionBehavior` is built per resource.

## File-by-file

Lines for the files identical to the api copy are as listed there. `w.` = `self.workflow.`.

| file | lines | own intent | old-runner names |
|---|---|---|---|
| binding_record.py | 8 | binding id = own path | none |
| completion.py | 51 | endpoint verification through terminal state | runtime_observations(1), episode_return_records(1), method_loop.identities(1), numerical(1), ESTIMATOR_VERSION(2) |
| configuration.py | 119 | identical to api | numerical YieldController(3)/YieldParameters(3) |
| credit.py | 136 | live credit from terminal state; closed snapshot | runtime_episodes(2), runtime_forms(3), runtime_observations(1), runtime_receipt_inheritance(2), runtime_record_receipts(2), episode_receipts(1), episode_return_records(3) |
| episode.py | 103 | role `launch_hpc`; tool only | communication(1), runtime(1) |
| execution_contracts.py | 57 | constants (imports own terminal_execution path) | communication(1) |
| from_parent.py | 117 | frozen HPC child_assignment_schema; no BLAST launch selection check | none |
| goal.py | 6 | delegate to terminal instructions | none |
| initial_information.py | 9 | readers for own path | none |
| internal_summary.py | 58 | delegate decision_context; selected task no-op | `_live_original_runtime`(11), runtime(6), runtime_actions(2), w.journal(3), w.store(3), plus the same w.* single uses as api |
| presentation.py | 74 | identical | `_live_original_providers`(20), decision_context(1) |
| received_api_reports.py / received_execution_information.py | 4 / 4 | own path | none |
| received_records.py | 127 | identical | none |
| resource_information.py | 70 | identical | none |
| science.py | 57 | parent input re-validation without the API grader | runtime_episodes(1) |
| state.py | 19 | `state` delegates to terminal state | none |
| task.py | 225 | identical | as api (`_live_original_runtime`(51), runtime_actions(8), w.execution_binding(7), w.store(9), w.journal(7)...) |
| task_decision.py | 357 | no waiting_support | as api minus w.waiting_support and one w.permits_common_action |
| task_instructions.py | 20 | no reason, wait or event paragraphs | `_live_original_runtime_prompt`(6), w.native_event_information(1), w.binding_context, w.decision_protocol, w.is_job_source, w.job_episodes, w.knowledge, w.launch_instructions, w.specialist |
| task_report.py, task_state.py, task_suspension.py, waiting.py | 22/107/8/10 | identical | as api |
| terminal_execution.py | 226 | the HPC instructions, catalog, execution and receipts | communication(1), PracticalYieldEstimator(2) |
| to_parent.py | 100 | practical facts and handoffs | none |
| work_operations.py | 35 | identical | none |
| yield_estimator.py | 50 | `launch_hpc:` profile; delegate practical_estimator | numerical YieldController(2)/YieldParameters(2), PracticalYieldEstimator(2) |

The exact per-file counts are in `runs/carry_over/calls/a107_05.tsv`.

## Differences from siblings

- Compared with **local_job_execution**: hpc's own pieces are the frozen-HPC `child_assignment_schema` (from_parent.py) and the no-op `_with_selected_execution_task` (internal_summary.py: the HPC copy shows no selected_execution_task). Everything else matches local, including the `launch_hpc:` versus `launch_local:` yield prefix, which follows the role.
- Compared with **api_job_execution**: see that file's "Differences from siblings". In short, hpc has no wait, uses the terminal-delegate goal, credit, state, completion and facts, has no BLAST API grader binding, and has no `_validate_blast_launch_selection`.

## Carried over

One row per row of `runs/carry_over/functions/a107__partner_presence_evidence__hpc_work_planning__hpc_allocation_execution__execution_job_submission__hpc_job_execution.tsv`. Columns: old file, kind and name (copied), then whether it is old-runner machinery or an episode function, then its new place (or the machinery reason). Rows whose place begins "unplaced:" are also listed in `carry_over_blocked/a107__partner_presence_evidence__hpc_work_planning__hpc_allocation_execution__execution_job_submission__hpc_job_execution.md`.

| old file | kind | name | class | new place or machinery reason |
|---|---|---|---|---|
| binding_record.py | class | NativeBindingRecord | machinery | binding record and the binding's own as_record() (README 3e: settings/declaration recorded by the system) |
| binding_record.py | method | NativeBindingRecord.as_record | machinery | the binding's own as_record() (README 3e) |
| completion.py | class | NativeCompletion | machinery | completion mix-in of the old runner; its methods are listed below |
| completion.py | method | NativeCompletion.completion_for_action | machinery | per-action completion proof as a controller packet (README 3d: the controller input is built by the system); the completion controller is chosen in yield_estimator.py |
| completion.py | method | NativeCompletion._closed_completion_verdict | machinery | reads runtime_observations of the old journal to reuse a recorded verification (README 3d: deleted) |
| completion.py | method | NativeCompletion.verify_completion | machinery | estimator completion verification (README 3d/7b PracticalYieldEstimator(verify_completion)); the proof it verified is rebuilt from the held receipts in messages/internal_summary.py completion_proof |
| configuration.py | class | NativeConfiguration | episode function | values the run sets: ctx.settings read in task.py (resource, initial_information, coordinator_workspace, launch_instructions_directory, knowledge_library_directory) and settings in yield_estimator.py (task_yield_profiles); adapters, providers and Store handles of the old construction are machinery |
| configuration.py | method | NativeConfiguration.__init__ | episode function | the same settings values (README 3 configuration.py row); old-runner adapters/providers built there are not carried |
| credit.py | class | ExecutionEpisodeCredit | episode function | credit.py credit (project_practical_credit) |
| credit.py | method | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind 'operational' (README 3d: deleted) |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_carrier | machinery | closed credit snapshot: reads runtime_episodes/runtime_actions (journal) |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_receipts | machinery | closed credit snapshot: reads the receipt inheritance tables |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_value | machinery | closed credit snapshot sanity check; the system hands the controller-seen credit to final_to_parent |
| credit.py | method | ExecutionEpisodeCredit._closed_credit_facts | machinery | closed credit snapshot written into the closing facts, reads runtime_forms; replaced by completion[credit] |
| credit.py | method | ExecutionEpisodeCredit._closed_operational_credit_view | machinery | closed credit snapshot re-validation over runtime_forms/sqlite_master |
| credit.py | method | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (live projection; the closed branch is machinery) |
| credit.py | method | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit (PracticalState.credit_view = library project_practical_credit over summary receipts) |
| credit.py | method | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit |
| episode.py | class | ExecutionEpisode | episode function | episode.py HpcJobExecution |
| episode.py | method | ExecutionEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | method | ExecutionEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} (no children) |
| episode.py | method | ExecutionEpisode.permitted_common_actions | episode function | task.py selection_schema / action (the tool action only) |
| execution_contracts.py | function | native_result_operation_catalog | episode function | unplaced: the execution.results.* operations belong to the results role (execution_result_acquisition), not to launch_hpc |
| from_parent.py | class | NativeParentRequests | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | method | NativeParentRequests._permitted | episode function | unplaced: filter of the parent launch's frozen requests by the parent's constraints (reads the parent's assignment, README 5 item 14) |
| from_parent.py | method | NativeParentRequests._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (the ASSIGNMENT_SCHEMA properties with resource_id and resource_kind fixed) and library validate_assignment in read_from_parent |
| from_parent.py | method | NativeParentRequests._launch | episode function | unplaced: validation of the parent launch's execution_launch_assignment_v1 (reads the parent's assignment) |
| from_parent.py | method | NativeParentRequests._constraints | episode function | unplaced: validation of the parent launch's allowed_resource_ids/allowed_kinds |
| from_parent.py | method | NativeParentRequests.child_assignment_schema | episode function | unplaced: the frozen HPC launch request exposed from the parent's assignment (frozen_hpc_launch_request_missing); the parent copies the chosen request into this child's assignment in its msg_to_child |
| from_parent.py | method | NativeParentRequests.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | method | NativeParentRequests.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent (library validate_assignment); the re-validation against the parent launch (masking, utility, input-version, native BLAST DB, standard BLAST DB, RNA-structure inputs) is unplaced: it reads the parent's assignment |
| goal.py | class | NativeGoal | episode function | goal.py GOAL/UNIT/RESULT; the instruction text in task.py |
| goal.py | method | NativeGoal.instructions | episode function | task.py INSTRUCTIONS and instructions() |
| initial_information.py | function | initial_information | episode function | task.py decide: resource_information(settings) with the recorded inventory_snapshot shown at every decision; the received_api_information part is the API role's and is not carried |
| internal_summary.py | function | native_decision_snapshot | machinery | decision snapshot over runtime_actions/journal/credit view/receipts of the old runner; the model context is built in task.py decide from the summary |
| internal_summary.py | class | NativeInternalSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | method | NativeInternalSummary._with_selected_execution_task | episode function | unplaced: identity function in this HPC copy (it returned its value unchanged), so no selected_execution_task exists to carry |
| internal_summary.py | method | NativeInternalSummary.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide (execution_assignment, execution_resource, coordinator_workspace, execution_progress, execution_completion) |
| presentation.py | function | present_context | episode function | unplaced: the per-context prompt renderer (render_hpc_prompt of the old shared root, which is not read) and the replay of saved state frames; decide hands the plain JSON context in ModelRequest.context |
| received_api_reports.py | function | received_api_reports | episode function | unplaced: selects the API reader authority of the old reader catalog; launch_hpc receives no API report |
| received_execution_information.py | function | received_execution_information | episode function | unplaced: selects the result readers of the old reader catalog (names an a110 path); launch_hpc receives no result |
| received_records.py | class | NativeReceivedRecords | episode function | messages/internal_summary.py returnable_handoff and messages/final_to_parent.py facts (the received-record readers are the results role's) |
| received_records.py | method | NativeReceivedRecords._context_target | episode function | messages/internal_summary.py returnable_handoff (the handoff must be for this exact assignment; the launch/results branches are other roles') |
| received_records.py | method | NativeReceivedRecords._received | episode function | unplaced: reads the known record refs of the binding context through the old handoff reader and result readers; this role received none, so execution_result_refs and file source facts are empty (messages/final_to_parent.py) |
| received_records.py | method | NativeReceivedRecords.initial_references | episode function | unplaced: for launch_hpc it returned no initial references (the validations of masking, utility, NMF and RNA inputs ran only for roles launch and launch_local) |
| resource_information.py | class | NativeResourceInformation | episode function | unplaced: commissionable operation contracts of every configured resource for the parent roles; not this episode's tools |
| resource_information.py | method | NativeResourceInformation.resource_tool_contracts | episode function | unplaced: commissionable launch/results operation contracts of every resource, for the parent roles (launch, results) |
| science.py | class | NativeScienceInputs | episode function | unplaced: re-validation of the parent launch's science inputs (reads the parent's recorded request) |
| science.py | method | NativeScienceInputs._masking_inputs | episode function | unplaced: validates masking inputs against the parent launch (reads the parent's assignment, README 5 item 14) |
| science.py | method | NativeScienceInputs._utility_inputs | episode function | unplaced: validates BLAST utility inputs against the parent launch |
| science.py | method | NativeScienceInputs._expression_nmf_inputs | episode function | unplaced: validates expression NMF inputs against the parent launch |
| science.py | method | NativeScienceInputs._versions | episode function | unplaced: validates the parent launch's immutable input versions |
| science.py | method | NativeScienceInputs._check_parent_inputs | episode function | unplaced: re-read the parent launch request from runtime_episodes before every command (README 5 item 14) |
| state.py | class | NativeState | machinery | practical state mix-in (file-backed PracticalState); the state is the view outcomes (messages/internal_summary.py) |
| state.py | method | NativeState.initialize | machinery | creates the file-backed PracticalState and runs _check_parent_inputs |
| state.py | method | NativeState.state | machinery | returns the file-backed PracticalState |
| task.py | class | NativeTask | episode function | task.py decide/action/exec_command; the loop is the system's |
| task.py | method | NativeTask.next | episode function | task.py decide (the model request) and the tool unit; the loop and the replay/checkpoint branches are the system's |
| task.py | method | NativeTask.apply_response | episode function | task.py action (validate the answer, return the exec_command ToolCall or Rejected) |
| task.py | method | NativeTask.execute | episode function | task.py exec_command (tool) |
| task_decision.py | class | NativeTaskDecision | episode function | task.py decide/action; its exchange methods are machinery (listed below) |
| task_decision.py | method | NativeTaskDecision.call | machinery | model call wrapped in runtime_model_calls and the decision exchange; the system records the ModelRequest |
| task_decision.py | method | NativeTaskDecision.instructions | episode function | task.py instructions() |
| task_decision.py | method | NativeTaskDecision.conversation_key | machinery | conversation sessions (README 3a: deleted) |
| task_decision.py | method | NativeTaskDecision.interpretation_context | machinery | context of the old report_update interpretation (the parent-written form is gone) |
| task_decision.py | method | NativeTaskDecision.exchange_schema | machinery | decision-exchange loop (request_context/select_action) |
| task_decision.py | method | NativeTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | method | NativeTaskDecision.validate_contract_exchange_request | machinery | saved-request check of the decision-exchange loop |
| task_decision.py | method | NativeTaskDecision.validate_contract_exchange_history | machinery | saved-request check of the decision-exchange loop |
| task_decision.py | method | NativeTaskDecision.exchange_decision | machinery | decision-exchange loop (exchange_decision); a lookup is a tool |
| task_decision.py | method | NativeTaskDecision.decision_completion | machinery | decision completion record of the old runner |
| task_instructions.py | function | instructions | episode function | task.py instructions() (the resource instructions, tool-knowledge and launch-library texts); the pending_child_delivery and decision-exchange history paragraphs describe actions that no longer exist |
| task_report.py | class | NativeTaskReport | machinery | report_form machinery (form_with_facts, runtime_forms, release) |
| task_report.py | method | NativeTaskReport.finish | machinery | saves runtime_forms and releases the episode; the facts are messages/final_to_parent.py final_to_parent |
| task_state.py | class | NativeTaskState | machinery | task state with checkpoint/restore |
| task_state.py | method | NativeTaskState.__init__ | machinery | task state of the old decision machine (identity, calls, restored flags) |
| task_state.py | method | NativeTaskState.bind_execution_context | machinery | binds the old execution context |
| task_state.py | method | NativeTaskState.record_execution_failure | machinery | writes a failure into runtime_actions and the credit; the tool returns its failure as its outcome (task.py exec_command) |
| task_state.py | method | NativeTaskState.restore_checkpoint | machinery | restore_checkpoint (README 3e) |
| task_state.py | method | NativeTaskState.restore | machinery | restore (README 3e) |
| task_state.py | method | NativeTaskState.record_effect | machinery | record_effect (README 3e) |
| task_state.py | method | NativeTaskState.checkpoint | machinery | checkpoint (README 3e) |
| task_suspension.py | class | NativeTaskSuspension | machinery | wait/suspension machinery |
| task_suspension.py | method | NativeTaskSuspension.suspension_changed | machinery | wait/suspension machinery |
| terminal_execution.py | class | TerminalExecutionBehavior | episode function | task.py (terminal(), exec_command, instructions, resource_information), messages/read_from_parent.py, messages/internal_summary.py, messages/final_to_parent.py |
| terminal_execution.py | method | TerminalExecutionBehavior.__init__ | episode function | settings read in task.py (resource, initial_information, coordinator_workspace); the explicit_execution_resources_required and initial_inventory_resource_not_bound checks have no counterpart: one resource, supplied as settings |
| terminal_execution.py | method | TerminalExecutionBehavior._operations | episode function | task.py terminal(settings) (TerminalExecution with terminal_artifact_paths) |
| terminal_execution.py | method | TerminalExecutionBehavior._assignment | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py decide (terminal.validate_assignment) |
| terminal_execution.py | method | TerminalExecutionBehavior._state_directory | machinery | location of the file-backed practical state (PracticalState) |
| terminal_execution.py | method | TerminalExecutionBehavior.initialize | machinery | creates the file-backed PracticalState with the initial validations; the initial validations are messages/internal_summary.py |
| terminal_execution.py | method | TerminalExecutionBehavior.state | machinery | returns the file-backed PracticalState |
| terminal_execution.py | method | TerminalExecutionBehavior.as_record | machinery | the binding's own as_record() |
| terminal_execution.py | method | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_kind | machinery | credit_kind 'operational' (README 3d: deleted) |
| terminal_execution.py | method | TerminalExecutionBehavior.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| terminal_execution.py | method | TerminalExecutionBehavior.permitted_common_actions | episode function | task.py selection_schema / action (tool only) |
| terminal_execution.py | method | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent |
| terminal_execution.py | method | TerminalExecutionBehavior.initial_decision_context | episode function | task.py decide (execution_resource.inventory_snapshot from settings initial_information) |
| terminal_execution.py | method | TerminalExecutionBehavior._resource_information | episode function | task.py resource_information(settings) |
| terminal_execution.py | method | TerminalExecutionBehavior._resource_instructions | episode function | task.py decide (LaunchInstructions.for_resource of the configured resource) |
| terminal_execution.py | method | TerminalExecutionBehavior.instructions | episode function | task.py INSTRUCTIONS and instructions() |
| terminal_execution.py | method | TerminalExecutionBehavior.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide |
| terminal_execution.py | method | TerminalExecutionBehavior.catalog | episode function | task.py operation_catalog (EXEC_COMMAND) |
| terminal_execution.py | method | TerminalExecutionBehavior.execute | episode function | task.py exec_command (tool); the begin/finish intent ledger is the system's attempts journal; run_command is BLOCKED-ON-JOB-SERVICE |
| terminal_execution.py | method | TerminalExecutionBehavior.completion_for_action | machinery | per-action completion proof as a controller packet (README 3d) |
| terminal_execution.py | method | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator(verify_completion) (README 7b): the completion controller in yield_estimator.py |
| terminal_execution.py | method | TerminalExecutionBehavior.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (practical_completed, practical_receipt_digests, practical_receipt_refs) |
| terminal_execution.py | method | TerminalExecutionBehavior.facts | episode function | messages/final_to_parent.py facts (receipts published by their own units, not at the report) |
| terminal_execution.py | method | TerminalExecutionBehavior.resolve | machinery | resolver of report-form references (receipt digests, PracticalReceiptInformation sources); held-ness is records.holds and the system admits the result |
| terminal_execution.py | method | TerminalExecutionBehavior.validate_report | episode function | messages/final_to_parent.py validate_report (fact agreement; the validate_form step is a contract misfit) |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_view | episode function | credit.py credit |
| to_parent.py | class | NativeParentReturns | episode function | messages/final_to_parent.py RETURN_FORM / facts / validate_report |
| to_parent.py | method | NativeParentReturns.required_return_sources | episode function | messages/final_to_parent.py RETURN_FORM: returned no required source here (an empty tuple) |
| to_parent.py | method | NativeParentReturns.facts | episode function | messages/final_to_parent.py facts (the closed-credit facts are machinery) |
| to_parent.py | method | NativeParentReturns._live_facts | episode function | messages/final_to_parent.py facts (handoff refs, empty result and native families, execution_completed); bvbrc_appservice_support_refs and the adapter-conditional families are not carried (contract_misfits) |
| to_parent.py | method | NativeParentReturns.validate_report | episode function | messages/final_to_parent.py validate_report (fact agreement; adapter received-report checks belong to result acquisition; the validate_form step is a contract misfit) |
| waiting.py | function | perform_selected_native_wait | machinery | wait machinery (perform_selected_wait); this episode has no wait |
| work_operations.py | class | NativeWorkOperations | episode function | task.py TOOLS / exec_command |
| work_operations.py | method | NativeWorkOperations.catalog | episode function | task.py operation_catalog |
| work_operations.py | method | NativeWorkOperations.execute | episode function | task.py exec_command (the _check_parent_inputs re-validation before every command is unplaced) |
| yield_estimator.py | class | ExecutionEpisodeYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | method | ExecutionEpisodeYield._request_yield_class | episode function | messages/read_from_parent.py request_yield_class (the practical_assignment_v1 branch; the API versions it also classified are the API sibling's) |
| yield_estimator.py | method | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py yield_controller (profile lookup, execution_original_task_yield_profile_required) |
| yield_estimator.py | method | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller (require_private_yield has no meaning: the profile is always required) |
| yield_estimator.py | method | ExecutionEpisodeYield._launch_hpc_yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController from the profile cutoff and the commissioned target) |
| yield_estimator.py | method | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator delegate (README 7b) |
