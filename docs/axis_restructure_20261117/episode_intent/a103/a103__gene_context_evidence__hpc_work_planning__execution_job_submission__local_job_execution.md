# a103 / gene_context_evidence / hpc_work_planning / execution_job_submission / local_job_execution

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/hpc_work_planning/execution_job_submission/local_job_execution/<file>` (files directly in the folder; no grading/ or scoring/ subfolder; `tests/` not read). Old role: `launch_local`. `binding_path = '.../execution_job_submission/local_job_execution'`, `commissioning_parent = 'gene_context_evidence/hpc_work_planning/execution_job_submission'`, `roles = ('launch_local',)`, `entry_roles = ()`, `replaces_default_instructions = True`, renderer `present_native_task`.

## Purpose (goal, in its own words)

`goal.py` delegates to the terminal behaviour; `terminal_goal.py` (byte-identical to hpc_job_execution's) gives:

> You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit enter the iterator, including failure or zero progress. Host bookkeeping records command versions and actual native job identities; do not maintain a parallel receipt ledger. If a submission outcome is uncertain, investigate that original submission rather than create a duplicate. Use the provided resource-specific instructions, account, storage and existing authentication route. workdir and env apply to the selected command only. target=resource runs on the assigned resource; target=coordinator runs in the local run directory for supplied-input and transport work. Both are ordinary journaled actions; resource computation belongs on its actual allocation. For coordinator-side transfers, execution_resource.ssh_argv, when present, is the exact configured transport prefix. Append the remote shell command as its final argument and preserve stdin. The supplied configuration gives the existing connection details. target=resource uses that transport directly. The episode iterator decides continuation from credit; add no stopping budget.

plus any frozen launch-library sections for this resource. It runs the launch parent's chosen request on a `local` resource by writing and running shell commands until the requested endpoint predicates have a validated completion.

## Task and instructions

- `instructions.py`: identical to hpc_job_execution's (goal, reasoning requirement only if `reason` permitted — it is not, tool knowledge, launch library, pending-delivery repair, wait/native-event paragraphs only if `wait` permitted — it is not, exchange-protocol rewrite).
- `task.py` (`NativeTask`): the parent's loop without the empty-reasoning check; `grain='launch_local'`.

## What it reads from its parent's assignment

`from_parent.py` `NativeAssignment`:
- `child_assignment_schema(parent, role)` = `assignment_schema(role)` = anyOf of the practical request schemas for every configured `local` resource (no frozen-enum branch; that exists only in hpc_job_execution).
- `prepare_assignment`: validate (workspace confinement, terminal operations' `validate_assignment`); kind must be `local`; parent role `launch`; parent launch assignment re-validated; masking/utility inputs; parent's immutable input versions; native BLAST database / standard database inputs.
- `operations._check_parent_inputs` on initialize and every execute (parent's saved launch request read from `runtime_episodes`).

## Children

None (`child_eligibility.py`).

## Decision state and what it shows the model

Parent copies of `decision_state.py` / `decision_inputs.py` (expectations role `launch_local`). Binding decision context: the terminal summary (`execution_assignment`, `execution_resource` with workspace/kind/policy/account/ssh_argv/python_executable/scheduler/inventory snapshot, `coordinator_workspace`, `execution_progress`, `execution_completion`) plus `selected_execution_task` (`internal_summary._with_selected_execution_task`): when `services.scientific_parent_task(context)` returns a task and the single local request names exactly one supported native job (`native_blast`, `native_blast_masking`, `native_blast_utility`, `native_blast_database`, `native_blast_standard_database`, `native_hmmer`, `native_hmmer_preparation`; HMMER via `native_profile_scientific_job_view`), the context carries `{version: 'selected_execution_task_v1', scientific_question, selected_tool_info, requests, constraints, selector, result_description}`. Presentation `present_native_task` (selected-execution prompt when that task is present).

## Tools it offers

`exec_command` only (catalog for kind `local`), same schema and execution path as hpc_job_execution (`terminal_operations.py`: intent/replay, `TerminalExecution`, `finalize_scientific_command`, cwd/env revision, validations, receipt publication). Action policy `('tool',)`.

## Credit

`credit.py`: closed view; native result family; else `PracticalState.credit_view()` via the terminal behaviour. Unbounded. `completion.py`: native families, else practical state completion proof / `state.verify_completion`.

## Continuation (yield estimator and settings)

`_launch_local_yield_controller`: profile key `'launch_local:' + request_class` (`practical_local[_native_...]_{handoff|outputs}`), old `YieldController` + `PracticalYieldEstimator(verify_completion)`; `practical_estimator` from the terminal behaviour. Settings: `task_yield_profiles['launch_local:<class>'] = {cutoff > 0, parameters}`. New-layout counterpart: completion-with-a-target estimator (inferred).

## What it reports to its parent

Same as hpc_job_execution (`to_parent.py` byte-identical): fact catalogue plus `practical_completed`, `practical_receipt_digests`, `practical_receipt_refs`; live facts = terminal facts + `execution_handoff_refs` (received handoffs plus own returnable practical receipts), `execution_result_refs`, file sources/outcomes, `execution_result_origin`, `execution_completed = practical_completed`; closed-credit facts; report must match recorded facts.

## Configuration

Parent's configuration body (`NativeConfiguration`); `binding_record.py` `binding_id = '.../execution_job_submission/local_job_execution'`, `VERSION = 'execution_episode_v1'`.

## Differences from sibling/similar episodes

- vs hpc_job_execution: role/kind `local`; no frozen-HPC enum in `child_assignment_schema`; builds `selected_execution_task` (hpc does not). All other files are byte-identical or differ only in names (`local` vs `hpc`).
- vs api_job_execution and the launch parent: see the hpc_job_execution note (exec_command, no wait, practical-state credit, terminal_* split).

## File by file

`wf.` = `self.workflow.` / `source.workflow.`. Imports are old shared-root modules (not read). Old-runner names are the same as in hpc_job_execution file for file (same counts); only the differences in intent are noted.

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | — | — |
| `goal.py` | 7 | Goal delegated to terminal behaviour. | — |
| `instructions.py` | 22 | As hpc. | wf.specialist, wf.binding_context, wf.permits_common_action×3, wf.knowledge, wf.launch_instructions, wf.native_event_information, wf.decision_protocol; runtime_prompt.INSTRUCTIONS×3, .REASONING_COMMIT_REQUIREMENT, .DECISION_EXCHANGE_PROTOCOL |
| `task.py` | 226 | Loop with grain `launch_local`. | as hpc task.py (wf.journal×7, wf.store×8, wf.execution_binding×7, ...; runtime.*; ModelCallError; record_source_failure; runtime_actions×8, runtime_model_calls×2, runtime_episodes) |
| `task_state.py` | 108 | Generic. | as parent task_state.py |
| `decision_state.py` | 45 | Generic. | as parent decision_state.py |
| `decision_inputs.py` | 70 | Expectations role `launch_local`. | as parent decision_inputs.py |
| `decision_presentation.py` | 59 | Renderer choice. | providers.* (as parent) |
| `decision_delivery.py` | 82 | Generic. | as parent |
| `decision_exchange.py` | 116 | Generic. | as parent |
| `saved_decision_exchange.py` | 82 | Generic. | as parent |
| `decision_contracts.py` | 36 | Generic. | as parent |
| `decision_provider.py` | 18 | Dispatch. | wf.provider×2, wf.specialist |
| `waiting.py` | 9 | Generic (unused). | wf.execution_handle×2, wf.execution_backend |
| `report_delivery.py` | 25 | Generic finish. | as parent |
| `episode.py` | 31 | Composition, role `launch_local`. | — |
| `action_policy.py` | 9 | `('tool',)`. | — |
| `binding_record.py` | 9 | Binding record. | — |
| `child_eligibility.py` | 10 | No children. | — |
| `parent_launch_contract.py` | 8 | Parent launch schema. | — |
| `configuration.py` | 65 | Parent's body. | YieldController×3, YieldParameters×3 |
| `contracts.py` | 60 | Constants; own terminal behaviour. | shared-root imports as parent |
| `from_parent.py` | 126 | Local assignment and preparation. | imports native_blast_*_result_publication |
| `operations.py` | 48 | Delegation; parent input checks. | table runtime_episodes |
| `internal_summary.py` | 121 | Terminal decision context + selected execution task. | import native_profile_presentation; `self.services.scientific_parent_task` |
| `credit.py` | 39 | Practical-state credit. | — |
| `closed_credit.py` | 117 | Identical to parent. | as parent |
| `completion.py` | 65 | Practical-state completion. | UnitRef×2, NumericBand×2, ESTIMATOR_VERSION×2; runtime_observations |
| `yield_estimator.py` | 50 | `launch_local:<class>` profile. | YieldController×2, YieldParameters×2, PracticalYieldEstimator×2 |
| `to_parent.py` | 132 | As hpc. | result-view imports |
| `received_information.py` | 113 | As parent. | result-view imports |
| `received_record_selection.py` | 35 | As parent. | — |
| `received_reference_custody.py` | 160 | As parent. | bvbrc_homology_returns, hmmer_native_result_views |
| `report_reference_access.py` | 115 | As parent. | episode_bindings and result modules |
| `result_records.py` | 260 | As api/hpc. | EpisodeReceipts×2; runtime_actions×2, runtime_episodes, runtime_receipt_inheritance×2 |
| `terminal_execution.py` | 41 | Terminal behaviour composition. | PracticalYieldEstimator×2 |
| `terminal_goal.py` | 18 | Execution-agent instructions. | — |
| `terminal_contracts.py` | 24 | `exec_command` catalog. | practical_execution_*, terminal_execution imports |
| `terminal_operations.py` | 47 | Command execution and receipt. | terminal_scientific_evidence, practical_receipt_information |
| `terminal_assignment.py` | 22 | Assignment validation. | — |
| `terminal_state.py` | 18 | Practical state. | — |
| `terminal_summary.py` | 16 | Terminal decision context. | — |
| `terminal_report.py` | 31 | Practical facts. | practical_receipt_information |
| `terminal_credit.py` | 11 | Practical credit/completion. | — |

Per-use counts: `runs/carry_over/calls/a103_03.tsv`.

## Carried over

Carried 19 November 2026 into the ten-file form (no children: no msg_to_child.py or read_from_child.py). One row per old function, class and method (`runs/carry_over/functions/...local_job_execution.tsv`). "library candidate": the function stays in the episode file that uses it. Machinery is not carried (reason given).

| old file | kind | name | class | new place or machinery reason |
|---|---|---|---|---|
| action_policy.py | class | NativeActionPolicy | machinery | the old loop's permitted common actions (the action policy ('tool',)); the system's decide/action produce only tool or child units |
| action_policy.py | method | NativeActionPolicy.permitted_common_actions | machinery | the old loop's permitted common actions (the action policy ('tool',)); the system's decide/action produce only tool or child units |
| binding_record.py | class | NativeBindingRecord | machinery | binding_record.py and the binding's own as_record() (README 3e) |
| binding_record.py | method | NativeBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record() (README 3e) |
| child_eligibility.py | class | NativeChildEligibility | episode function | task.py CHILD_SLOTS = {} (no children) |
| child_eligibility.py | method | NativeChildEligibility.child_roles | episode function | task.py CHILD_SLOTS = {} (no children) |
| child_eligibility.py | method | NativeChildEligibility.allowed_children | episode function | task.py CHILD_SLOTS = {} (no children) |
| closed_credit.py | class | ClosedExecutionCredit | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run (runtime_* table re-validation, recorded-run replay) |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_carrier | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run (runtime_* table re-validation, recorded-run replay) |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_receipts | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run (runtime_* table re-validation, recorded-run replay) |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_value | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run (runtime_* table re-validation, recorded-run replay) |
| closed_credit.py | method | ClosedExecutionCredit._closed_credit_facts | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run (runtime_* table re-validation, recorded-run replay) |
| closed_credit.py | method | ClosedExecutionCredit._closed_operational_credit_view | machinery | closed credit view rebuilt from receipts and the journal of an earlier closed run (runtime_* table re-validation, recorded-run replay) |
| completion.py | class | ExecutionCompletion | machinery | class shell |
| completion.py | method | ExecutionCompletion.completion_for_action | machinery | completion proof as a controller packet (estimator packet, not a controller input in the new system); the proof is read in messages/internal_summary.py::_completion |
| completion.py | method | ExecutionCompletion._closed_completion_verdict | machinery | re-reads runtime_observations of the old journal (README 3d: reading earlier controller records) |
| completion.py | method | ExecutionCompletion.verify_completion | episode function | messages/internal_summary.py::_completion (the verified completion of the assignment's endpoint, over held receipts); library candidate |
| configuration.py | class | NativeConfiguration | machinery | NativeConfiguration.__init__ values: the run's settings (ctx.settings / settings: resource, coordinator_workspace, launch_instructions_directory, tool_knowledge_directory, task_yield_profiles); YieldController/YieldParameters construction replaced by yield_estimator.py |
| configuration.py | method | NativeConfiguration.__init__ | machinery | NativeConfiguration.__init__ values: the run's settings (ctx.settings / settings: resource, coordinator_workspace, launch_instructions_directory, tool_knowledge_directory, task_yield_profiles); YieldController/YieldParameters construction replaced by yield_estimator.py |
| contracts.py | function | launch_operation_catalog | episode function | not this episode's: the catalogue of the parent 'launch' role (execution.capabilities); not carried here, see unplaced_old_functions |
| contracts.py | function | native_result_operation_catalog | episode function | not this episode's: the catalogue of the 'results' role (execution.results.*); not carried here, see unplaced_old_functions |
| contracts.py | function | _outcome | machinery | old tool outcome envelope (status/record_refs/feedback); the new tool returns its outcome and an invalid answer is a Rejected in task.py::action |
| credit.py | class | ExecutionEpisodeCredit | machinery | class shell |
| credit.py | method | ExecutionEpisodeCredit.credit_kind | machinery | credit kind label 'operational' of the old credit view |
| credit.py | method | ExecutionEpisodeCredit.project_credit | episode function | credit.py::credit |
| credit.py | method | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py::credit (the practical branch; the native family result branches belong to the results role) |
| credit.py | method | ExecutionEpisodeCredit.credit_view | episode function | credit.py::credit |
| decision_contracts.py | class | NativeDecisionContracts | machinery | decision-exchange loop (exchange_decision schema and response) |
| decision_contracts.py | method | NativeDecisionContracts.exchange_schema | machinery | decision-exchange loop (exchange_decision schema and response) |
| decision_contracts.py | method | NativeDecisionContracts.exchange_response | machinery | decision-exchange loop (exchange_decision schema and response) |
| decision_delivery.py | class | NativeDecisionDelivery | machinery | decision-exchange loop (delivery of a decision, conversation continuation) |
| decision_delivery.py | method | NativeDecisionDelivery.call | machinery | decision-exchange loop (delivery of a decision, conversation continuation) |
| decision_delivery.py | method | NativeDecisionDelivery.instructions | machinery | decision-exchange loop (delivery of a decision, conversation continuation) |
| decision_exchange.py | class | NativeDecisionExchange | machinery | decision-exchange loop (exchange_decision, interpretation_context) |
| decision_exchange.py | method | NativeDecisionExchange.interpretation_context | machinery | decision-exchange loop (exchange_decision, interpretation_context) |
| decision_exchange.py | method | NativeDecisionExchange.exchange_decision | machinery | decision-exchange loop (exchange_decision, interpretation_context) |
| decision_inputs.py | class | NativeDecisionInputs | episode function | task.py::decide (context keys launch_instruction_library, selected_launch_instructions); the planning expectations, resource estimator, native event, waiting and completed-work branches do not apply to launch_local (wait/redelivery machinery or other roles) and are not carried |
| decision_inputs.py | method | NativeDecisionInputs.decision_inputs | episode function | task.py::decide (context keys launch_instruction_library, selected_launch_instructions); the planning expectations, resource estimator, native event, waiting and completed-work branches do not apply to launch_local (wait/redelivery machinery or other roles) and are not carried |
| decision_presentation.py | function | present_native_task | episode function | task.py::_task_text and decide (the selected-execution prompt over the summary) |
| decision_provider.py | class | NativeDecisionProvider | machinery | provider dispatch and conversation key of the old decision loop |
| decision_provider.py | method | NativeDecisionProvider.conversation_key | machinery | provider dispatch and conversation key of the old decision loop |
| decision_provider.py | method | NativeDecisionProvider.complete_decision | machinery | provider dispatch and conversation key of the old decision loop |
| decision_state.py | class | NativeDecisionState | machinery | old decision-state snapshot over the journal and workflow store; replaced by messages/internal_summary.py::internal_summary |
| decision_state.py | method | NativeDecisionState.decision_state | machinery | old decision-state snapshot over the journal and workflow store; replaced by messages/internal_summary.py::internal_summary |
| episode.py | class | ExecutionEpisode | episode function | episode.py::LocalJobExecution |
| from_parent.py | class | NativeAssignment | episode function | messages/read_from_parent.py (class shell) |
| from_parent.py | method | NativeAssignment.child_assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| from_parent.py | method | NativeAssignment.assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| from_parent.py | method | NativeAssignment._permitted | episode function | not this episode's: resource permission test of the parent launch's requests (role launch); not carried, see unplaced_old_functions |
| from_parent.py | method | NativeAssignment.prepare_assignment | episode function | messages/read_from_parent.py::read_from_parent (validate_assignment); the masking, utility, input-version and native job input checks are unplaced (modules not in the library, commission checks) |
| from_parent.py | method | NativeAssignment._request_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM (one field per property of ASSIGNMENT_SCHEMA) |
| from_parent.py | method | NativeAssignment._validate_request | episode function | messages/read_from_parent.py::read_from_parent (validate_assignment) and task.py::_operations (the resource's own validate_assignment with workspace confinement, in action) |
| from_parent.py | method | NativeAssignment._launch | machinery | re-validation of the commissioner's launch contract read from runtime_episodes |
| from_parent.py | method | NativeAssignment._constraints | machinery | part of the launch contract re-validation (_launch) |
| from_parent.py | method | NativeAssignment.required_return_sources | machinery | returns () for this role: the old runner's required return sources; the child declares its return form |
| from_parent.py | method | NativeAssignment.initial_references | episode function | messages/read_from_parent.py ASSIGNMENT_FORM record_refs field (the masking and utility input references); computing them through _masking_inputs/_utility_inputs is unplaced |
| goal.py | class | NativeGoal | episode function | goal.py / task.py::GOAL_INSTRUCTION (class shell) |
| goal.py | method | NativeGoal.instructions | episode function | task.py::GOAL_INSTRUCTION (from terminal_goal, unchanged) |
| instructions.py | function | instructions | episode function | task.py::_instructions (goal text, tool knowledge and launch library text, the resource's frozen launch instructions); reasoning, pending-delivery, wait/native-event and exchange-protocol spans are dropped (actions that no longer exist) |
| internal_summary.py | class | NativeSummary | episode function | messages/internal_summary.py (class shell) |
| internal_summary.py | method | NativeSummary.initial_decision_context | episode function | messages/internal_summary.py::internal_summary and task.py::_resource/decide (execution_resource_capabilities of this resource); the received BLAST/BVBRC/minhash branches belong to other roles |
| internal_summary.py | method | NativeSummary.decision_context | episode function | messages/internal_summary.py::internal_summary |
| internal_summary.py | method | NativeSummary._with_selected_execution_task | episode function | messages/internal_summary.py::_selected_execution_task (scientific task from the new parent-input field scientific_task); library candidate |
| internal_summary.py | method | NativeSummary._resource_information | episode function | task.py::_resource |
| internal_summary.py | method | NativeSummary.capabilities | episode function | not this episode's: configured operation availability across all resources for the root's catalogue; not carried, see unplaced_old_functions |
| internal_summary.py | method | NativeSummary.resource_tool_contracts | episode function | not this episode's: the declaration of every bound launch/results/homology operation for the parent; not carried, see unplaced_old_functions |
| operations.py | class | NativeOperations | machinery | class shell of delegation |
| operations.py | method | NativeOperations._delegate | machinery | role dispatch to the practical resource operations |
| operations.py | method | NativeOperations._practical_context | machinery | identity wrapper of the old context |
| operations.py | method | NativeOperations.initialize | machinery | state initialization of the old practical state (file-backed PracticalState) |
| operations.py | method | NativeOperations._check_parent_inputs | machinery | re-validation of the parent's saved launch request from runtime_episodes (old-runner table); its input checks are listed in unplaced_old_functions |
| operations.py | method | NativeOperations.state | machinery | file-backed practical state of the old runner |
| operations.py | method | NativeOperations.catalog | episode function | task.py::TOOLS / EXEC_COMMAND |
| operations.py | method | NativeOperations.execute | episode function | task.py::exec_command (through the job_access service, BLOCKED-ON-JOB-SERVICE) |
| parent_launch_contract.py | function | parent_launch_schema | machinery | schema of the commissioner's launch contract, used only by _launch re-validation |
| received_information.py | class | ReceivedExecutionInformation | machinery | bookkeeping of received reports (bvbrc/minhash forwarding, received report facts) for the old report path; custody and receipts are the system's |
| received_information.py | method | ReceivedExecutionInformation._forwards_bvbrc_reports | machinery | bookkeeping of received reports (bvbrc/minhash forwarding, received report facts) for the old report path; custody and receipts are the system's |
| received_information.py | method | ReceivedExecutionInformation._forwards_minhash_reports | machinery | bookkeeping of received reports (bvbrc/minhash forwarding, received report facts) for the old report path; custody and receipts are the system's |
| received_information.py | method | ReceivedExecutionInformation.received_report_sources | machinery | bookkeeping of received reports (bvbrc/minhash forwarding, received report facts) for the old report path; custody and receipts are the system's |
| received_information.py | method | ReceivedExecutionInformation.received_report_facts | machinery | bookkeeping of received reports (bvbrc/minhash forwarding, received report facts) for the old report path; custody and receipts are the system's |
| received_information.py | method | ReceivedExecutionInformation.received_report_closure_facts | machinery | bookkeeping of received reports (bvbrc/minhash forwarding, received report facts) for the old report path; custody and receipts are the system's |
| received_record_selection.py | class | ReceivedRecordSelection | machinery | receipts bookkeeping (_received: handoffs and results the episode received) |
| received_record_selection.py | method | ReceivedRecordSelection._received | machinery | receipts bookkeeping (_received: handoffs and results the episode received) |
| received_reference_custody.py | class | ReceivedReferenceCustody | machinery | reference custody of received records (resolve/validate received references): the system's custody |
| received_reference_custody.py | method | ReceivedReferenceCustody.resolve_received_reference | machinery | reference custody of received records (resolve/validate received references): the system's custody |
| received_reference_custody.py | method | ReceivedReferenceCustody.validate_received_report | machinery | reference custody of received records (resolve/validate received references): the system's custody |
| received_reference_custody.py | method | ReceivedReferenceCustody.received_form_references | machinery | reference custody of received records (resolve/validate received references): the system's custody |
| report_delivery.py | class | NativeReportDelivery | machinery | report_form delivery (finish): the system admits the return form |
| report_delivery.py | method | NativeReportDelivery.finish | machinery | report_form delivery (finish): the system admits the return form |
| report_reference_access.py | class | ReportReferenceAccess | machinery | reference resolution of a report against the recorder and receipts: the system's custody |
| report_reference_access.py | method | ReportReferenceAccess.resolve | machinery | reference resolution of a report against the recorder and receipts: the system's custody |
| result_records.py | class | ExecutionResultRecords | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._masking_selector | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._masking_inputs | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._retained_masking_target | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._masking_reference_access | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._utility_selector | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._utility_inputs | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._retained_utility_target | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._utility_reference_access | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._versions | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._target | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._selector | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._result_directory | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._windows | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._selected_result_action | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._validate_result_body | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._read_result | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._selection | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._context_target | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._has_appservice | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._has_uniprot | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| result_records.py | method | ExecutionResultRecords._appservice_sources | episode function | not this episode's: the results role (result directory, windows, result bodies, selectors, retained targets, appservice sources); masking/utility/version input checks are in unplaced_old_functions |
| saved_decision_exchange.py | class | NativeSavedDecisionExchange | machinery | decision-exchange loop (saved exchange checks) |
| saved_decision_exchange.py | method | NativeSavedDecisionExchange.validate_contract_exchange_request | machinery | decision-exchange loop (saved exchange checks) |
| saved_decision_exchange.py | method | NativeSavedDecisionExchange.validate_contract_exchange_history | machinery | decision-exchange loop (saved exchange checks) |
| task.py | class | NativeTask | episode function | task.py::decide and action (class shell) |
| task.py | method | NativeTask.next | episode function | task.py::decide (context and request for the model) |
| task.py | method | NativeTask.apply_response | episode function | task.py::action (the answer names exec_command and valid operands, or Rejected) |
| task.py | method | NativeTask.execute | episode function | task.py::exec_command and the lookup tools |
| task_state.py | class | NativeTaskState | machinery | old task state (journal-backed) |
| task_state.py | method | NativeTaskState.__init__ | machinery | old task state (journal-backed) |
| task_state.py | method | NativeTaskState.bind_execution_context | machinery | old task state (journal-backed) |
| task_state.py | method | NativeTaskState.record_execution_failure | machinery | record_execution_failure: a tool's failure is its returned outcome |
| task_state.py | method | NativeTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | method | NativeTaskState.restore | machinery | checkpoint/restore |
| task_state.py | method | NativeTaskState.record_effect | machinery | effect record of the old journal (the system's attempts journal) |
| task_state.py | method | NativeTaskState.checkpoint | machinery | checkpoint/restore |
| terminal_assignment.py | class | TerminalAssignment | episode function | messages/read_from_parent.py |
| terminal_assignment.py | method | TerminalAssignment._assignment | episode function | task.py::_operations / messages/read_from_parent.py::read_from_parent |
| terminal_assignment.py | method | TerminalAssignment.prepare_assignment | episode function | messages/read_from_parent.py::read_from_parent (validate_assignment) and task.py::_operations |
| terminal_assignment.py | method | TerminalAssignment.assignment_schema | episode function | messages/read_from_parent.py::ASSIGNMENT_FORM |
| terminal_contracts.py | function | operation_catalog | episode function | task.py::EXEC_COMMAND (the exec_command catalogue entry, unchanged) |
| terminal_credit.py | class | TerminalCredit | episode function | credit.py::credit (practical credit over the receipts) |
| terminal_credit.py | method | TerminalCredit.credit_view | episode function | credit.py::credit (practical credit over the receipts) |
| terminal_credit.py | method | TerminalCredit.completion_for_action | machinery | completion proof as a controller packet; see messages/internal_summary.py::_completion |
| terminal_execution.py | class | TerminalExecutionBehavior | machinery | composition class shell of the terminal behaviour |
| terminal_execution.py | method | TerminalExecutionBehavior.__init__ | machinery | resources/initial_information held by the old composition: now settings (resource, coordinator_workspace) |
| terminal_execution.py | method | TerminalExecutionBehavior.as_record | machinery | the binding's own as_record() |
| terminal_execution.py | method | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.credit_kind | machinery | credit kind label |
| terminal_execution.py | method | TerminalExecutionBehavior.permitted_common_actions | machinery | action policy |
| terminal_execution.py | method | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | method | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator provider (estimate_with_context); the controller is yield_estimator.py (completion) |
| terminal_goal.py | class | TerminalGoal | episode function | task.py::GOAL_INSTRUCTION and goal.py GOAL |
| terminal_goal.py | method | TerminalGoal.instructions | episode function | task.py::GOAL_INSTRUCTION and goal.py GOAL |
| terminal_goal.py | method | TerminalGoal._resource_instructions | episode function | task.py::_instructions (resource instructions from the frozen launch library, LaunchInstructions.for_resource) |
| terminal_operations.py | class | TerminalOperations | episode function | task.py::exec_command |
| terminal_operations.py | method | TerminalOperations._operations | episode function | task.py::_operations (TerminalExecution of the resource); library candidate |
| terminal_operations.py | method | TerminalOperations.catalog | episode function | task.py::EXEC_COMMAND |
| terminal_operations.py | method | TerminalOperations.execute | episode function | task.py::exec_command (job_access service, BLOCKED-ON-JOB-SERVICE); the invalid-argument branch is task.py::action (Rejected) |
| terminal_report.py | class | TerminalReport | episode function | messages/final_to_parent.py |
| terminal_report.py | method | TerminalReport.fact_sources | episode function | messages/final_to_parent.py::RETURN_FORM (practical_completed, practical_receipt_digests, practical_receipt_refs) |
| terminal_report.py | method | TerminalReport.facts | episode function | messages/final_to_parent.py::_facts |
| terminal_report.py | method | TerminalReport.resolve | machinery | reference resolution of a report against receipts: the system's custody |
| terminal_report.py | method | TerminalReport.validate_report | episode function | messages/final_to_parent.py::validate_report |
| terminal_state.py | class | TerminalState | machinery | file-backed PracticalState directory and initialization of the old runner; the baseline is messages/internal_summary.py (assess_validations over the initial context), the receipts are tool outcomes |
| terminal_state.py | method | TerminalState._state_directory | machinery | file-backed PracticalState directory and initialization of the old runner; the baseline is messages/internal_summary.py (assess_validations over the initial context), the receipts are tool outcomes |
| terminal_state.py | method | TerminalState.initialize | machinery | file-backed PracticalState directory and initialization of the old runner; the baseline is messages/internal_summary.py (assess_validations over the initial context), the receipts are tool outcomes |
| terminal_state.py | method | TerminalState.state | machinery | file-backed PracticalState directory and initialization of the old runner; the baseline is messages/internal_summary.py (assess_validations over the initial context), the receipts are tool outcomes |
| terminal_summary.py | class | TerminalSummary | episode function | messages/internal_summary.py |
| terminal_summary.py | method | TerminalSummary.initial_decision_context | episode function | messages/internal_summary.py::internal_summary and task.py::decide |
| terminal_summary.py | method | TerminalSummary._resource_information | episode function | task.py::_resource |
| terminal_summary.py | method | TerminalSummary.decision_context | episode function | messages/internal_summary.py::internal_summary |
| to_parent.py | class | NativeReport | episode function | messages/final_to_parent.py |
| to_parent.py | method | NativeReport.fact_sources | episode function | messages/final_to_parent.py::RETURN_FORM (every old fact source of launch_local under its old name; the execution.<name> masking and utility sources are not form field names: contract misfit) |
| to_parent.py | method | NativeReport.facts | episode function | messages/final_to_parent.py::_facts |
| to_parent.py | method | NativeReport._live_facts | episode function | messages/final_to_parent.py::_facts (practical branch; handoff references are the receipts that handed a job off) |
| to_parent.py | method | NativeReport.validate_report | episode function | messages/final_to_parent.py::validate_report |
| waiting.py | class | NativeWaiting | machinery | wait/suspension machinery (suspension_changed; unused by this role) |
| waiting.py | method | NativeWaiting.suspension_changed | machinery | wait/suspension machinery (suspension_changed; unused by this role) |
| yield_estimator.py | class | ExecutionEpisodeYield | episode function | yield_estimator.py |
| yield_estimator.py | method | ExecutionEpisodeYield._request_yield_class | episode function | yield_estimator.py::request_yield_class; library candidate |
| yield_estimator.py | method | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py::task_yield_profile; library candidate |
| yield_estimator.py | method | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py::yield_controller |
| yield_estimator.py | method | ExecutionEpisodeYield._launch_local_yield_controller | episode function | yield_estimator.py::yield_controller (CompletionYieldController, README 7b) |
| yield_estimator.py | method | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator provider; replaced by the completion controller |
