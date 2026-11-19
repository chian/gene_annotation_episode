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
