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
