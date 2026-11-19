# a103 / gene_context_evidence / hpc_work_planning / execution_job_submission / hpc_job_execution

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a103/gene_context_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution/<file>` (files directly in the folder; no grading/ or scoring/ subfolder; `tests/` not read). Old role: `launch_hpc`. `binding_path = '.../execution_job_submission/hpc_job_execution'`, `commissioning_parent = 'gene_context_evidence/hpc_work_planning/execution_job_submission'`, `roles = ('launch_hpc',)`, `entry_roles = ()`, `replaces_default_instructions = True`, renderer `present_native_task`.

## Purpose (goal, in its own words)

`goal.py` delegates to the resource's terminal behaviour; the text is in `terminal_goal.py` `TerminalGoal.instructions`:

> You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit enter the iterator, including failure or zero progress. Host bookkeeping records command versions and actual native job identities; do not maintain a parallel receipt ledger. If a submission outcome is uncertain, investigate that original submission rather than create a duplicate. Use the provided resource-specific instructions, account, storage and existing authentication route. workdir and env apply to the selected command only. target=resource runs on the assigned resource; target=coordinator runs in the local run directory for supplied-input and transport work. Both are ordinary journaled actions; resource computation belongs on its actual allocation. For coordinator-side transfers, execution_resource.ssh_argv, when present, is the exact configured transport prefix. Append the remote shell command as its final argument and preserve stdin. The supplied configuration gives the existing connection details. target=resource uses that transport directly. The episode iterator decides continuation from credit; add no stopping budget.

When the frozen launch instruction library has sections for this resource (`launch_instructions.for_resource(resources[kind])`), they are appended under "Resource instructions supplied from the frozen library:".

It is the agent that runs the launch parent's chosen HPC (`pbs_ssh`) request on the assigned resource by writing and running shell commands, until the requested endpoint predicates have a validated completion.

## Task and instructions

- `instructions.py`: the binding's goal (above), `REASONING_COMMIT_REQUIREMENT` if `reason` were permitted (it is not), tool-knowledge and launch-library instructions when in context, the pending_child_delivery repair paragraph, wait / native_event paragraphs only if `wait` is permitted (it is not), and the exchange-protocol history rewrite.
- `task.py` (`NativeTask`): the parent's loop without the empty-reasoning check; report updates validated with `grain='launch_hpc'`.

## What it reads from its parent's assignment

`from_parent.py` `NativeAssignment`:
- `child_assignment_schema(parent, role)`: when the parent role is `launch`, the child role is `launch_hpc`, and an ancestor role is `hpc`, the schema is a closed `enum` of the parent's already-authorized, permitted HPC requests (`frozen_hpc_launch_request_missing` if none) — "A frozen HPC launch exposes only its already authorized request." Otherwise `assignment_schema(role)` = anyOf of the practical `ASSIGNMENT_SCHEMA` request schemas for every configured `hpc` resource (`resource_id`, `resource_kind` const, `requested_job` alternatives).
- `prepare_assignment`: validate; kind must be `hpc`; parent role must be `launch` (`resource_child_role_owned_by_launch`); parent's launch assignment re-validated; masking/utility inputs; parent's immutable input versions; native BLAST database / standard database input validation. No API validation and no BLAST launch selection check (those are API-only).
- `operations._check_parent_inputs` (initialize and every execute): reads the parent's saved launch request (`runtime_episodes` by path) and re-checks inputs and versions; `execution_original_launch_assignment_unavailable` if missing.
- `_validate_request` also confines the assignment's `workspace` to the resource workspace and runs the terminal operations' `validate_assignment`.

## Children

None (`child_eligibility.py`).

## Decision state and what it shows the model

`decision_state.py` / `decision_inputs.py`: the parent's copies (execution expectations role `launch_hpc`). The binding's decision context is the terminal summary's (`terminal_summary.py`): `execution_assignment`, `execution_resource` (`resource_kind`, `workspace`, `kind`, `policy`, `account`, `ssh_argv`, `python_executable`, `scheduler`, `inventory_snapshot`), `coordinator_workspace`, `execution_progress` (practical state credit view) and `execution_completion` (completion proof). `internal_summary._with_selected_execution_task` returns the value unchanged (no `selected_execution_task` for HPC), unlike local_job_execution. `initial_decision_context` is the parent's resource capability view. Presentation: `present_native_task` (same renderer choice as the parent; HPC contexts get the HPC prompt).

## Tools it offers

`exec_command` only (`terminal_contracts.operation_catalog('hpc')`): "Execute the shell command you write on the assigned resource. Use normal shell/file tools to inspect files, author scripts, prepare an environment, run software, or submit/observe the actual job as needed. Returns its actual output and saved action receipt. workdir and env apply to this command; select them explicitly on each action." Arguments `{cmd: string | [string], workdir, target: resource|coordinator, env: {string}}`, `cmd`, `workdir`, `env` required.

Execution (`terminal_operations.py`): validate arguments and action against the assignment; begin an intent in the practical state (a completed intent replays its receipt); run through `TerminalExecution` (artifact paths from `terminal_scientific_evidence`); failures become `native_outcome.failure` `execution_action_failed`; `finalize_scientific_command`; update cwd/environment revision only for resource-side commands inside the workspace; assess validations; finish the receipt; publish it as a practical receipt record. Always returns `completed` with the receipt (failure is recorded inside the receipt, not as an action failure).

Action policy: `('tool',)` only.

## Credit

`credit.py`: kind `operational`; closed view if saved; native result family view if one applies; otherwise `_delegate(context).credit_view(...)` = `TerminalCredit.credit_view` = `PracticalState.credit_view()` (the practical execution state's own operational credit from validated endpoint predicates). Unbounded.

`completion.py`: completion proofs from native families, else the terminal behaviour's `completion_for_action` (state completion proof when its `operation_key` matches); `verify_completion` = closed recorded verdict, native family, else `state.verify_completion(proof)`.

## Continuation (yield estimator and settings)

`yield_estimator.py` `_launch_hpc_yield_controller` (requires `require_private_yield=True`): profile key `'launch_hpc:' + request_class` with class `practical_hpc[_native_...]_{handoff|outputs}` (from `requested_job` native keys and `endpoint`). Old `YieldController(epoch, initial_credit, cutoff, YieldParameters(**parameters), estimate_with_context=PracticalYieldEstimator(verify_completion))`; `practical_estimator` delegates to the terminal behaviour (`PracticalYieldEstimator(state.verify_completion)`). Settings: `task_yield_profiles['launch_hpc:<class>'] = {cutoff > 0, parameters}`. New-layout counterpart: completion-with-a-target estimator (inferred).

## What it reports to its parent

`to_parent.py` `NativeReport`: the parent's fact catalogue plus, for roles `launch_local`/`launch_hpc`, the terminal sources `practical_completed`, `practical_receipt_digests`, `practical_receipt_refs`. Live facts: native family facts if one applies; otherwise the terminal facts (`practical_completed`, digests, receipt refs) merged with `execution_handoff_refs` = received handoffs plus any own practical receipt refs that read as returnable handoffs for this context, `execution_result_refs`, file sources/outcomes, `execution_result_origin`, `execution_completed = practical_completed`. Closed credit facts merged; reports must match recorded facts.

## Configuration

`configuration.py` = the parent's configuration body (`NativeConfiguration`). `binding_record.py`: `binding_id = '.../execution_job_submission/hpc_job_execution'`, `VERSION = 'execution_episode_v1'`. Terminal behaviour (`terminal_execution.py`): resources limited to `local`/`hpc`, record `binding_id 'terminal_execution'`, `VERSION 'terminal_execution_episode_v1'`, practical state directory `practical-execution/<digest(run_id, episode_id)>`.

## Differences from sibling/similar episodes

- vs local_job_execution: identical except names, role `launch_hpc`, the frozen-HPC `child_assignment_schema` enum (only HPC), and no `selected_execution_task` in the decision context (local builds it).
- vs api_job_execution: tool is `exec_command` on a resource instead of service operations; no `wait`; credit/completion from the practical state, not `api_execution`; handoff refs include own practical receipts; terminal behaviour split into seven `terminal_*.py` mixins (api/parent keep a single-class `terminal_execution.py`).
- vs the launch parent: no children, no `execution.capabilities`, no handoff-count credit.

## File by file

`wf.` = `self.workflow.` / `source.workflow.`. Imports are old shared-root modules (not read).

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| `__init__.py` | 0 | — | — |
| `goal.py` | 7 | Goal delegated to terminal behaviour. | — |
| `instructions.py` | 22 | Parent paragraphs (wait parts inactive). | wf.specialist, wf.binding_context, wf.permits_common_action×3, wf.knowledge, wf.launch_instructions, wf.native_event_information, wf.decision_protocol; runtime_prompt.INSTRUCTIONS×3, .REASONING_COMMIT_REQUIREMENT, .DECISION_EXCHANGE_PROTOCOL; import runtime_prompt |
| `task.py` | 226 | Loop with grain `launch_hpc`. | wf.journal×7, wf.store×8, wf.execution_binding×7, wf.inprocess_replay×4, wf.completions×3, wf.completed_unit×3, wf.selected×3, wf.decision_exchanges×3, wf.run_id×3, wf.controller_value×2, wf.action_schema, wf.automatic_score_updates, wf.binding_context, wf.delivery_resolution_inputs, wf.execute, wf.last_observed_credit, wf.next_return, wf.pending_work, wf.perform_selected_wait, wf.permits_common_action, wf.receive_native_outcome, wf.receive_outcome, wf.resolve_pending_deliveries, wf.resolver, wf.retain_shared_grading_results, wf.source_credit_view, wf.specialist, wf.validate_report; runtime.*; ModelCallError; record_source_failure; tables runtime_actions×8, runtime_model_calls×2, runtime_episodes; imports runtime, providers, episode_source_failure, library.action_contracts, library.private_policy_call, read_mapping |
| `task_state.py` | 108 | Generic. | same as parent task_state.py |
| `decision_state.py` | 45 | Generic copy. | same as parent decision_state.py |
| `decision_inputs.py` | 70 | Expectations role `launch_hpc`. | same as parent decision_inputs.py |
| `decision_presentation.py` | 59 | Renderer choice (parent's copy, renamed). | providers.* (as parent); imports providers, library.hpc_prompt, library.monitor_prompt, receiver_prompt, native_profile_presentation, gene_context_evidence_prompt |
| `decision_delivery.py` | 82 | Generic. | same as parent |
| `decision_exchange.py` | 116 | Generic. | same as parent |
| `saved_decision_exchange.py` | 82 | Generic. | same as parent |
| `decision_contracts.py` | 36 | Generic. | same as parent |
| `decision_provider.py` | 18 | Dispatch with this renderer. | wf.provider×2, wf.specialist |
| `waiting.py` | 9 | Generic (unused: no wait). | wf.execution_handle×2, wf.execution_backend |
| `report_delivery.py` | 25 | Generic finish. | same as parent |
| `episode.py` | 31 | Composition, role `launch_hpc`. | — |
| `action_policy.py` | 9 | `('tool',)`. | — |
| `binding_record.py` | 9 | Binding record. | — |
| `child_eligibility.py` | 10 | No children. | — |
| `parent_launch_contract.py` | 8 | Parent launch schema independent of this role. | — |
| `configuration.py` | 65 | Parent's configuration body. | YieldController×3, YieldParameters×3; imports numerical, api_service_execution, execution_progress |
| `contracts.py` | 60 | Constants; imports own terminal behaviour and `terminal_contracts.operation_catalog`. | shared-root imports as parent |
| `from_parent.py` | 131 | Frozen HPC enum; HPC preparation. | imports native_blast_database_result_publication, native_blast_standard_database_result_publication |
| `operations.py` | 48 | Delegation to terminal behaviour; parent input checks; `state()` for practical roles. | table runtime_episodes; imports native_blast_*_result_publication |
| `internal_summary.py` | 94 | Terminal decision context; no selected task. | — |
| `credit.py` | 39 | Practical-state credit. | — |
| `closed_credit.py` | 117 | Identical to parent. | same as parent |
| `completion.py` | 65 | Practical-state completion verification. | UnitRef×2, NumericBand×2, ESTIMATOR_VERSION×2; table runtime_observations; imports method_loop.identities, episode_return_records, numerical, practical_yield |
| `yield_estimator.py` | 50 | `launch_hpc:<class>` profile + completion estimator. | YieldController×2, YieldParameters×2, PracticalYieldEstimator×2; imports numerical, practical_yield |
| `to_parent.py` | 132 | Terminal facts + own receipt handoffs. | result-view imports (as parent) |
| `received_information.py` | 113 | Same as parent. | result-view imports |
| `received_record_selection.py` | 35 | Same as parent. | — |
| `received_reference_custody.py` | 160 | Same as parent. | imports bvbrc_homology_returns, hmmer_native_result_views |
| `report_reference_access.py` | 115 | Same as parent (`practical_receipt` resolution for launch_local/launch_hpc). | imports episode_bindings and result modules |
| `result_records.py` | 260 | Same as api copy. | EpisodeReceipts×2; tables runtime_actions×2, runtime_episodes, runtime_receipt_inheritance×2; imports episode_receipts, execution_input_versions, result views |
| `terminal_execution.py` | 41 | Terminal behaviour composition and resource validation. | PracticalYieldEstimator×2; import practical_yield |
| `terminal_goal.py` | 18 | Execution-agent instructions (quoted) + frozen-library resource sections. | — (reads `services.workflow.launch_instructions`) |
| `terminal_contracts.py` | 24 | `exec_command` catalog, ROLE_KINDS, VERSION. | imports communication, domain, acquisition, practical_execution_operations, practical_execution_records, practical_execution_state, terminal_execution |
| `terminal_operations.py` | 47 | Command execution and receipt. | imports terminal_scientific_evidence, practical_receipt_information |
| `terminal_assignment.py` | 22 | Assignment/role kind validation. | — |
| `terminal_state.py` | 18 | Practical state directory/initialization. | — |
| `terminal_summary.py` | 16 | Terminal decision context. | — |
| `terminal_report.py` | 31 | Practical fact sources/facts/resolve/validate. | import practical_receipt_information |
| `terminal_credit.py` | 11 | Practical credit view and completion proof. | — |

Per-use counts: `runs/carry_over/calls/a103_03.tsv`.

## Carried over

Carried 19 November 2026 into the ten-file form (class `HpcJobExecution` in `episode.py`; tool `exec_command`, service `job_access`, no children). Rows are the 177 rows of `runs/carry_over/functions/a103__gene_context_evidence__hpc_work_planning__execution_job_submission__hpc_job_execution.tsv`. Library candidates (kept in the episode file because no library function exists): `messages/internal_summary.py completion_proof` (old `PracticalState._completion`, a private copy), `messages/read_from_parent.py _request_yield_class`, `task.py _history`. Already in library and called: `records/gene_context_evidence/practical_execution_records.py`, `grading/gene_context_evidence/practical_execution_credit.py`, `findings/gene_context_evidence/terminal_scientific_evidence.py`, `jobs/local_execution/gene_context_evidence/terminal_execution.py` (TerminalExecution.validate_action), `instructions/launch_instructions.py`, `model_exchange/gene_context_evidence/action_transport.py`, `model_exchange/rejection_feedback.py`, the `readers/**/gene_context_evidence` result-view fact-source functions.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| action_policy.py | NativeActionPolicy | episode function | task.py action (returns only the exec_command ToolCall; the old ("tool",) policy) |
| action_policy.py | NativeActionPolicy.permitted_common_actions | episode function | task.py action (returns only the exec_command ToolCall; the old ("tool",) policy) |
| binding_record.py | NativeBindingRecord | machinery | binding_record.py and the binding's own as_record() (README 3e) |
| binding_record.py | NativeBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record() (README 3e) |
| child_eligibility.py | NativeChildEligibility | episode function | task.py CHILD_SLOTS = {} (no children) |
| child_eligibility.py | NativeChildEligibility.child_roles | episode function | task.py CHILD_SLOTS = {} (no children) |
| child_eligibility.py | NativeChildEligibility.allowed_children | episode function | task.py CHILD_SLOTS = {} (no children) |
| closed_credit.py | ClosedExecutionCredit | machinery | closed recorded credit view and receipts re-validation; the result credit is completion['credit'] (README 3d, D1) |
| closed_credit.py | ClosedExecutionCredit._closed_credit_carrier | machinery | closed recorded credit view and receipts re-validation; the result credit is completion['credit'] (README 3d, D1) |
| closed_credit.py | ClosedExecutionCredit._closed_credit_receipts | machinery | closed recorded credit view and receipts re-validation; the result credit is completion['credit'] (README 3d, D1) |
| closed_credit.py | ClosedExecutionCredit._closed_credit_value | machinery | closed recorded credit view and receipts re-validation; the result credit is completion['credit'] (README 3d, D1) |
| closed_credit.py | ClosedExecutionCredit._closed_credit_facts | machinery | closed recorded credit view and receipts re-validation; the result credit is completion['credit'] (README 3d, D1) |
| closed_credit.py | ClosedExecutionCredit._closed_operational_credit_view | machinery | closed recorded credit view and receipts re-validation; the result credit is completion['credit'] (README 3d, D1) |
| completion.py | ExecutionCompletion | machinery | class of the completion-proof producers and verifiers (README 3d) |
| completion.py | ExecutionCompletion.completion_for_action | machinery | completion proof as controller input (README 3d, section 5 item 5); the proof itself is computed by messages/internal_summary.py completion_proof |
| completion.py | ExecutionCompletion._closed_completion_verdict | machinery | reads runtime_observations of earlier controller records (README 3d) |
| completion.py | ExecutionCompletion.verify_completion | machinery | PracticalYieldEstimator completion verification (README 3d, 7b); the completion controller reads credit |
| configuration.py | NativeConfiguration | machinery | configuration values: the episode's settings (ctx.settings: resource, coordinator_workspace, initial_information, launch_instruction_directory, task_yield_profiles); YieldController construction goes to yield_estimator.py |
| configuration.py | NativeConfiguration.__init__ | machinery | configuration values: the episode's settings (ctx.settings: resource, coordinator_workspace, initial_information, launch_instruction_directory, task_yield_profiles); YieldController construction goes to yield_estimator.py |
| contracts.py | launch_operation_catalog | episode function | not an operation of launch_hpc (the launch parent's execution.capabilities catalogue): unplaced, see report |
| contracts.py | native_result_operation_catalog | episode function | not an operation of launch_hpc (the results role's catalogue): unplaced, see report |
| contracts.py | _outcome | machinery | operation outcome envelope (status, record_refs, changed_record_refs); a tool returns its own outcome (README 3c) |
| credit.py | ExecutionEpisodeCredit | episode function | credit.py credit |
| credit.py | ExecutionEpisodeCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | ExecutionEpisodeCredit.project_credit | episode function | credit.py credit (the closed-credit branch is machinery) |
| credit.py | ExecutionEpisodeCredit._live_project_credit | episode function | credit.py credit (practical branch; the native result-family branches belong to the results role) |
| credit.py | ExecutionEpisodeCredit.credit_view | episode function | credit.py credit; the view fields are in messages/internal_summary.py (execution_progress) |
| decision_contracts.py | NativeDecisionContracts | machinery | decision-exchange loop (exchange_decision, exchange_schema, exchange_response) |
| decision_contracts.py | NativeDecisionContracts.exchange_schema | machinery | decision-exchange loop (exchange_decision, exchange_schema, exchange_response) |
| decision_contracts.py | NativeDecisionContracts.exchange_response | machinery | decision-exchange loop (exchange_decision, exchange_schema, exchange_response) |
| decision_delivery.py | NativeDecisionDelivery | machinery | decision-exchange loop and recorded model call delivery |
| decision_delivery.py | NativeDecisionDelivery.call | machinery | decision-exchange loop and recorded model call delivery |
| decision_delivery.py | NativeDecisionDelivery.instructions | machinery | decision-exchange loop and recorded model call delivery |
| decision_exchange.py | NativeDecisionExchange | machinery | decision-exchange loop (exchange_decision, interpretation_context) |
| decision_exchange.py | NativeDecisionExchange.interpretation_context | machinery | decision-exchange loop (exchange_decision, interpretation_context) |
| decision_exchange.py | NativeDecisionExchange.exchange_decision | machinery | decision-exchange loop (exchange_decision, interpretation_context) |
| decision_inputs.py | NativeDecisionInputs | episode function | task.py decide (context of the model request: resource, launch instructions, tools, history, progress); exchange and job-planning context parts are machinery or other roles |
| decision_inputs.py | NativeDecisionInputs.decision_inputs | episode function | task.py decide (context of the model request: resource, launch instructions, tools, history, progress); exchange and job-planning context parts are machinery or other roles |
| decision_presentation.py | present_native_task | episode function | task.py decide (the context mapping replaces the renderer choice; the HPC prompt renderer text is not placed: see report) |
| decision_provider.py | NativeDecisionProvider | machinery | provider dispatch and conversation_key (model call recording, README 3a) |
| decision_provider.py | NativeDecisionProvider.conversation_key | machinery | provider dispatch and conversation_key (model call recording, README 3a) |
| decision_provider.py | NativeDecisionProvider.complete_decision | machinery | provider dispatch and conversation_key (model call recording, README 3a) |
| decision_state.py | NativeDecisionState | episode function | messages/internal_summary.py internal_summary (state) and task.py decide (context) |
| decision_state.py | NativeDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary (state) and task.py decide (context) |
| episode.py | ExecutionEpisode | episode function | episode.py HpcJobExecution |
| from_parent.py | NativeAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | NativeAssignment.child_assignment_schema | machinery | parent-side schema of the commission (the frozen-HPC enum); the parent's msg_to_child writes the assignment and a wrong commission fails (README 3b C3) |
| from_parent.py | NativeAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM |
| from_parent.py | NativeAssignment._permitted | machinery | parent-side filter of permitted requests (README 3b C3) |
| from_parent.py | NativeAssignment.prepare_assignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent (validate_assignment); the parent-input and input-version checks of the commission are not carried (a wrong commission fails) |
| from_parent.py | NativeAssignment._request_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (resource_kind and version declared) |
| from_parent.py | NativeAssignment._validate_request | episode function | messages/read_from_parent.py read_from_parent (validate_assignment) and task.py action (TerminalExecution.validate_action confines the workspace to the resource) |
| from_parent.py | NativeAssignment._launch | machinery | re-validation of the parent's launch assignment (README 3b C3, F8) |
| from_parent.py | NativeAssignment._constraints | machinery | constraint check of the parent's launch assignment (README 3b C3) |
| from_parent.py | NativeAssignment.required_return_sources | machinery | return sources written by the parent (README 3b C4); it returned () |
| from_parent.py | NativeAssignment.initial_references | machinery | records handed down by reference; now record_refs fields (README 3b P2); it returned no reference for launch_hpc |
| goal.py | NativeGoal | episode function | goal.py and task.py INSTRUCTIONS (delegated to the terminal goal text) |
| goal.py | NativeGoal.instructions | episode function | goal.py and task.py INSTRUCTIONS (delegated to the terminal goal text) |
| instructions.py | instructions | episode function | task.py decide (INSTRUCTIONS plus the frozen-library resource sections); the pending-delivery, wait and exchange-protocol paragraphs are machinery |
| internal_summary.py | NativeSummary | episode function | messages/internal_summary.py and task.py decide |
| internal_summary.py | NativeSummary.initial_decision_context | episode function | task.py decide (_resource_information; the parent's all-resource capability view belongs to the launch parent) |
| internal_summary.py | NativeSummary.decision_context | episode function | messages/internal_summary.py internal_summary and task.py decide |
| internal_summary.py | NativeSummary._with_selected_execution_task | episode function | no-op for this role (returns the value unchanged): nothing to place |
| internal_summary.py | NativeSummary._resource_information | episode function | not this role's (all-resource listing for the launch parent); this role's is task.py _resource_information: unplaced, see report |
| internal_summary.py | NativeSummary.capabilities | episode function | not an operation of launch_hpc (the launch parent's capability listing): unplaced, see report |
| internal_summary.py | NativeSummary.resource_tool_contracts | episode function | not an operation of launch_hpc (contract catalogue for the launch parent and the results role): unplaced, see report |
| operations.py | NativeOperations | episode function | task.py TOOLS |
| operations.py | NativeOperations._delegate | machinery | delegation to the terminal behaviour object |
| operations.py | NativeOperations._practical_context | machinery | old BindingContext adaptation |
| operations.py | NativeOperations.initialize | machinery | practical state directory initialisation (checkpoint/restore family) |
| operations.py | NativeOperations._check_parent_inputs | machinery | re-reads runtime_episodes for the parent's saved launch request (journal/runtime_* re-validation) |
| operations.py | NativeOperations.state | machinery | practical state object lookup (durable intents and receipts are the system's attempts journal and the receipts in outcomes) |
| operations.py | NativeOperations.catalog | episode function | task.py EXEC_COMMAND (shown in decide) |
| operations.py | NativeOperations.execute | episode function | task.py exec_command |
| parent_launch_contract.py | parent_launch_schema | machinery | schema of the parent's launch assignment (parent-side, README 3b C3) |
| received_information.py | ReceivedExecutionInformation | machinery | forwarding of received result-family reports to an axis head (README 3b R3, F5); not an operation of launch_hpc |
| received_information.py | ReceivedExecutionInformation._forwards_bvbrc_reports | machinery | forwarding of received result-family reports to an axis head (README 3b R3, F5); not an operation of launch_hpc |
| received_information.py | ReceivedExecutionInformation._forwards_minhash_reports | machinery | forwarding of received result-family reports to an axis head (README 3b R3, F5); not an operation of launch_hpc |
| received_information.py | ReceivedExecutionInformation.received_report_sources | machinery | forwarding of received result-family reports to an axis head (README 3b R3, F5); not an operation of launch_hpc |
| received_information.py | ReceivedExecutionInformation.received_report_facts | machinery | forwarding of received result-family reports to an axis head (README 3b R3, F5); not an operation of launch_hpc |
| received_information.py | ReceivedExecutionInformation.received_report_closure_facts | machinery | forwarding of received result-family reports to an axis head (README 3b R3, F5); not an operation of launch_hpc |
| received_record_selection.py | ReceivedRecordSelection | machinery | received-record selection (README F2: record_selection, custody) |
| received_record_selection.py | ReceivedRecordSelection._received | machinery | received-record selection (README F2: record_selection, custody) |
| received_reference_custody.py | ReceivedReferenceCustody | machinery | receipt ledger of received references and received-report validation (README F1, F5) |
| received_reference_custody.py | ReceivedReferenceCustody.resolve_received_reference | machinery | receipt ledger of received references and received-report validation (README F1, F5) |
| received_reference_custody.py | ReceivedReferenceCustody.validate_received_report | machinery | receipt ledger of received references and received-report validation (README F1, F5) |
| received_reference_custody.py | ReceivedReferenceCustody.received_form_references | machinery | receipt ledger of received references and received-report validation (README F1, F5) |
| report_delivery.py | NativeReportDelivery | machinery | report_form machinery: saved form, form_with_facts, release (README D1, D3) |
| report_delivery.py | NativeReportDelivery.finish | machinery | report_form machinery: saved form, form_with_facts, release (README D1, D3) |
| report_reference_access.py | ReportReferenceAccess | machinery | old reference resolver (README D2); the own-receipt check is final_to_parent.py validate_report |
| report_reference_access.py | ReportReferenceAccess.resolve | machinery | old reference resolver (README D2); the own-receipt check is final_to_parent.py validate_report |
| result_records.py | ExecutionResultRecords | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._masking_selector | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._masking_inputs | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._retained_masking_target | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._masking_reference_access | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._utility_selector | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._utility_inputs | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._retained_utility_target | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._utility_reference_access | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._versions | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._target | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._selector | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._result_directory | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._windows | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._selected_result_action | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._validate_result_body | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._read_result | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._selection | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._context_target | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._has_appservice | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._has_uniprot | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| result_records.py | ExecutionResultRecords._appservice_sources | machinery | results-role record selection and the receipt ledger (EpisodeReceipts, runtime_* tables); not an operation of launch_hpc |
| saved_decision_exchange.py | NativeSavedDecisionExchange | machinery | saved decision-exchange checks (README 3a: deleted) |
| saved_decision_exchange.py | NativeSavedDecisionExchange.validate_contract_exchange_request | machinery | saved decision-exchange checks (README 3a: deleted) |
| saved_decision_exchange.py | NativeSavedDecisionExchange.validate_contract_exchange_history | machinery | saved decision-exchange checks (README 3a: deleted) |
| task.py | NativeTask | episode function | task.py decide / action / exec_command |
| task.py | NativeTask.next | episode function | task.py decide (the decision); the closed-episode and replay branches are machinery |
| task.py | NativeTask.apply_response | episode function | task.py action (validation of the answer; the report-update and redelivery parts are machinery) |
| task.py | NativeTask.execute | episode function | task.py exec_command (the unit); the journal rows, receipts and controller input are the system's |
| task_state.py | NativeTaskState | machinery | checkpoint, restore, record_effect, record_execution_failure (README 3e) |
| task_state.py | NativeTaskState.__init__ | machinery | checkpoint, restore, record_effect, record_execution_failure (README 3e) |
| task_state.py | NativeTaskState.bind_execution_context | machinery | checkpoint, restore, record_effect, record_execution_failure (README 3e) |
| task_state.py | NativeTaskState.record_execution_failure | machinery | checkpoint, restore, record_effect, record_execution_failure (README 3e) |
| task_state.py | NativeTaskState.restore_checkpoint | machinery | checkpoint, restore, record_effect, record_execution_failure (README 3e) |
| task_state.py | NativeTaskState.restore | machinery | checkpoint, restore, record_effect, record_execution_failure (README 3e) |
| task_state.py | NativeTaskState.record_effect | machinery | checkpoint, restore, record_effect, record_execution_failure (README 3e) |
| task_state.py | NativeTaskState.checkpoint | machinery | checkpoint, restore, record_effect, record_execution_failure (README 3e) |
| terminal_assignment.py | TerminalAssignment | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM, read_from_parent) and task.py action (TerminalExecution.validate_action) |
| terminal_assignment.py | TerminalAssignment._assignment | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM, read_from_parent) and task.py action (TerminalExecution.validate_action) |
| terminal_assignment.py | TerminalAssignment.prepare_assignment | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM, read_from_parent) and task.py action (TerminalExecution.validate_action) |
| terminal_assignment.py | TerminalAssignment.assignment_schema | episode function | messages/read_from_parent.py (ASSIGNMENT_FORM, read_from_parent) and task.py action (TerminalExecution.validate_action) |
| terminal_contracts.py | operation_catalog | episode function | task.py EXEC_COMMAND (the operation catalogue) |
| terminal_credit.py | TerminalCredit | episode function | credit.py credit |
| terminal_credit.py | TerminalCredit.credit_view | episode function | credit.py credit (project_practical_credit over the summary) |
| terminal_credit.py | TerminalCredit.completion_for_action | episode function | messages/internal_summary.py completion_proof (the operation_key match with a controller proof is machinery) |
| terminal_execution.py | TerminalExecutionBehavior | episode function | task.py (see methods) |
| terminal_execution.py | TerminalExecutionBehavior.__init__ | machinery | resource configuration of the behaviour object: the episode's settings (ctx.settings) |
| terminal_execution.py | TerminalExecutionBehavior.as_record | machinery | the behaviour's own as_record() (README 3e) |
| terminal_execution.py | TerminalExecutionBehavior.child_roles | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.credit_kind | machinery | credit_kind is deleted (README 3d) |
| terminal_execution.py | TerminalExecutionBehavior.permitted_common_actions | episode function | task.py action (only the exec_command tool unit) |
| terminal_execution.py | TerminalExecutionBehavior.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| terminal_execution.py | TerminalExecutionBehavior.practical_estimator | machinery | PracticalYieldEstimator (README 3d, 7b); yield_estimator.py builds a completion controller |
| terminal_goal.py | TerminalGoal | episode function | task.py INSTRUCTIONS and decide |
| terminal_goal.py | TerminalGoal.instructions | episode function | task.py INSTRUCTIONS and decide (frozen-library resource sections via LaunchInstructions.for_resource) |
| terminal_goal.py | TerminalGoal._resource_instructions | episode function | task.py decide (LaunchInstructions(ctx.settings['launch_instruction_directory']).for_resource) |
| terminal_operations.py | TerminalOperations | episode function | task.py exec_command |
| terminal_operations.py | TerminalOperations._operations | episode function | task.py action (TerminalExecution.validate_action) and the job_access service (the execution; BLOCKED-ON-JOB-SERVICE) |
| terminal_operations.py | TerminalOperations.catalog | episode function | task.py EXEC_COMMAND |
| terminal_operations.py | TerminalOperations.execute | episode function | task.py exec_command (intent journaling and replay are the system's attempts; the receipt publication is reported) |
| terminal_report.py | TerminalReport | episode function | messages/final_to_parent.py |
| terminal_report.py | TerminalReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (practical_completed, practical_receipt_digests, practical_receipt_refs) |
| terminal_report.py | TerminalReport.facts | episode function | messages/final_to_parent.py _facts |
| terminal_report.py | TerminalReport.resolve | machinery | old reference resolver (README D2); own receipts are checked in final_to_parent.py validate_report |
| terminal_report.py | TerminalReport.validate_report | episode function | messages/final_to_parent.py validate_report |
| terminal_state.py | TerminalState | machinery | practical state directory and its initialisation (durable intents and receipts on disk): the system's attempts journal and the receipt in the outcome |
| terminal_state.py | TerminalState._state_directory | machinery | practical state directory and its initialisation (durable intents and receipts on disk): the system's attempts journal and the receipt in the outcome |
| terminal_state.py | TerminalState.initialize | machinery | practical state directory and its initialisation (durable intents and receipts on disk): the system's attempts journal and the receipt in the outcome |
| terminal_state.py | TerminalState.state | machinery | practical state directory and its initialisation (durable intents and receipts on disk): the system's attempts journal and the receipt in the outcome |
| terminal_summary.py | TerminalSummary | episode function | messages/internal_summary.py and task.py decide |
| terminal_summary.py | TerminalSummary.initial_decision_context | episode function | task.py decide (execution_resource) |
| terminal_summary.py | TerminalSummary._resource_information | episode function | task.py _resource_information |
| terminal_summary.py | TerminalSummary.decision_context | episode function | task.py decide and messages/internal_summary.py internal_summary |
| to_parent.py | NativeReport | episode function | messages/final_to_parent.py |
| to_parent.py | NativeReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (terminal sources, result-family sources from the library, execution_handoff_refs, execution_result_refs, execution_completed, execution_result_origin, execution_blast_hsps) |
| to_parent.py | NativeReport.facts | episode function | messages/final_to_parent.py final_to_parent |
| to_parent.py | NativeReport._live_facts | episode function | messages/final_to_parent.py _facts (execution_handoff_refs raises: BLOCKED-ON-JOB-SERVICE) |
| to_parent.py | NativeReport.validate_report | episode function | messages/final_to_parent.py validate_report |
| waiting.py | NativeWaiting | machinery | wait/suspension machinery (suspension_changed) |
| waiting.py | NativeWaiting.suspension_changed | machinery | wait/suspension machinery (suspension_changed) |
| yield_estimator.py | ExecutionEpisodeYield | episode function | yield_estimator.py and messages/read_from_parent.py |
| yield_estimator.py | ExecutionEpisodeYield._request_yield_class | episode function | messages/read_from_parent.py _request_yield_class (practical branch; the api branches do not apply to hpc) |
| yield_estimator.py | ExecutionEpisodeYield._task_yield_profile | episode function | yield_estimator.py yield_controller (profile lookup in settings) |
| yield_estimator.py | ExecutionEpisodeYield.yield_controller | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | ExecutionEpisodeYield._launch_hpc_yield_controller | episode function | yield_estimator.py yield_controller (CompletionYieldController) |
| yield_estimator.py | ExecutionEpisodeYield.practical_estimator | machinery | PracticalYieldEstimator (README 3d, 7b) |
