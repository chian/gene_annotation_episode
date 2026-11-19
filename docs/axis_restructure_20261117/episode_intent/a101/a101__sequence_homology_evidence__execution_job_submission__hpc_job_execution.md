# a101/sequence_homology_evidence/execution_job_submission/hpc_job_execution — intent carried over from 97308b94c

Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/execution_job_submission/hpc_job_execution/<file>`
(files directly in this folder; `tests/` not covered). Old binding class `ExecutionEpisode` (`binding_path =
'sequence_homology_evidence/execution_job_submission/hpc_job_execution'`, `commissioning_parent =
'sequence_homology_evidence/execution_job_submission'`, `roles = ('launch_hpc',)`, `entry_roles = ()`,
`replaces_default_instructions = True`), decision source `OperationalTask`. A leaf.

## What it is for (its goal, in its own words)

`goal.py` returns the delegate `TerminalExecutionBehavior.instructions` (`terminal_execution.py`):

> You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run
> the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery
> from the actual resource instructions and observed results. No sequence of setup or job-stage operations is
> prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical
> inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual
> result and earned credit enter the iterator, including failure or zero progress. Host bookkeeping records
> command versions and actual native job identities; do not maintain a parallel receipt ledger. If a submission
> outcome is uncertain, investigate that original submission rather than create a duplicate. Use the provided
> resource-specific instructions, account, storage and existing authentication route. workdir and env apply to
> the selected command only. target=resource runs on the assigned resource; target=coordinator runs in the local
> run directory for supplied-input and transport work ... For coordinator-side transfers,
> execution_resource.ssh_argv, when present, is the exact configured transport prefix ... The episode iterator
> decides continuation from credit; add no stopping budget.

followed by "Resource instructions supplied from the frozen library:" and the sections that the launch
instruction library selects for this resource. For A101 this runs a native BLAST/HMMER (or other requested job)
on Aurora via PBS over the configured SSH route.

## Task and instructions

`task_instructions.py` identical to the Launch parent's (the goal replaces the generic prompt). `task.py`: the
Launch loop **without reasoning and without wait** — every action is a tool execution; credit is always the
current credit view (no wait carry-over). `task_decision.py`, `task_state.py`, `report_delivery.py`,
`decision_state.py` are the Launch parent's rules (separate copies). `waiting.py` keeps only
`suspension_changed`.

## What it reads from its parent's assignment

`from_parent.py`: one practical request (`ASSIGNMENT_SCHEMA`, `practical_assignment_v1`) for one configured HPC
resource (`resource_kind` const `hpc`, `resource_id` const, `requested_job` generic or native alternatives,
`workspace` confined to the resource workspace, endpoint `usable_handoff` / `completed_job_outputs`,
`initial_context`). The terminal behaviour additionally validates it against its resource operations.
`prepare_assignment`: request validation, kind must be `hpc`, parent role must be `launch`, re-reads the parent
Launch assignment, masking/utility inputs, the parent's immutable input versions, native and standard BLAST
database job inputs. Unlike the API sibling it does **not** apply the BLAST graded-selection check.
`initial_references` = none.

## Children it may commission

None.

## Decision state and what it shows the model

Same presentation shell as Launch. `decision_context` is the terminal behaviour's: `execution_assignment`,
`execution_resource` (kind, workspace, policy, account, ssh_argv, python_executable, scheduler, inventory
snapshot), `coordinator_workspace`, `execution_progress` (practical state credit view), `execution_completion`
(completion proof or null). `initial_decision_context` = resource capabilities, initial information, received
BV-BRC/MinHash values. `decision_inputs.py`: as Launch without `waiting_support`.

## Tools it offers

`permitted_common_actions = ('tool',)`. Catalog = `exec_command` (cmd string or argv, required `workdir` and
`env`, optional `target` resource|coordinator). Each command begins/finishes a `PracticalState` intent keyed by the
operation key (a completed intent is replayed, not re-run), finalizes scientific command artifacts, tracks cwd and
environment revisions, assesses endpoint validations, and publishes a practical receipt record
(`PracticalReceiptInformation`). Argument errors return `invalid`; execution exceptions become a failed native
outcome that still enters the iterator.

## How its credit is counted

`credit.py`: kind `operational`; same closed-credit snapshot rules (role `launch_hpc`). Live credit:
`self._delegate(context).credit_view(...)` = the practical state's credit view (operational progress from
validated endpoint predicates). Completion: terminal `completion_for_action` (the state's completion proof for that
operation key); verification: `self.state(context).verify_completion(proof)`.

## Continuation (yield estimator and settings)

`yield_estimator.py` (requires `require_private_yield`): **accumulation** estimator with cutoff and parameters from
the task profile `launch_hpc:<request class>` (class = `practical_hpc_<native_* names>_{handoff|outputs}`), and
`estimate_with_context = PracticalYieldEstimator(state.verify_completion)` via the terminal delegate.

## What it reports to its parent

`to_parent.py`: no required return sources. Facts: the terminal delegate's `practical_completed`,
`practical_receipt_digests`, `practical_receipt_refs`, plus `execution_handoff_refs` = received usable handoffs
extended by every practical receipt reference that reads back as a returnable handoff target,
`execution_completed` = `practical_completed`, result refs, file sources/outcomes, appservice support refs, and
the closed credit snapshot. `validate_report` (terminal) requires fact fields to equal the recorded facts.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| goal.py | 9 | Goal = terminal execution instructions + frozen resource sections. | none (delegate reads `services.workflow.launch_instructions`). |
| task_instructions.py | 26 | Same inlined prompt copy as Launch. | `source.workflow.specialist`, `.binding_context`, `.permits_common_action`×3, `.knowledge`, `.launch_instructions`, `.native_event_information`, `.decision_protocol`. |
| configuration.py | 119 | Same configuration as Launch (separate copy). | as Launch. |
| binding_record.py | 8 | `as_record()` (binding_id differs). | none. |
| execution_contracts.py | 59 | Same contracts; imports `hpc_job_execution.terminal_execution`. | as Launch. |
| from_parent.py | 111 | One HPC practical request; parent must be `launch`. | native database publication validators; `hpc_launch_authentication` guarded off. |
| from_parent_launch.py | 9 | Parent Launch form schema. | none. |
| execution_state.py | 89 | Delegate = TerminalExecutionBehavior for the resource; parent input re-check. | `self.store.db` on `runtime_episodes`, `runtime_actions`, `runtime_receipt_inheritance`×2; `self.services.record_selection`; `episode_receipts`. |
| execution_operations.py | 174 | Catalog/execute delegated to the terminal behaviour. | as API sibling. |
| terminal_execution.py | 242 | exec_command behaviour, instructions, decision context, facts, credit (the substantive HPC intent). | imports `acquisition`, `communication`, `domain`, `practical_execution_operations/records/state`, `practical_receipt_information`×3, `practical_yield`, `terminal_execution`, `terminal_scientific_evidence`×2; `services.workflow.launch_instructions.for_resource`. |
| native_input_custody.py | 313 | Same input custody. | as Launch. |
| received_evidence.py | 351 | Same received-evidence rules. | as Launch. |
| result_acquisition.py | 209 | Same result acquisition. | `self.store.db` on `runtime_actions`×2, `runtime_episodes`. |
| internal_summary.py | 25 | Terminal decision context; no selected execution task. | none. |
| decision_inputs.py | 76 | Per-call inputs without waiting_support. | as Launch minus `.waiting_support`. |
| decision_state.py | 55 | Same presentation. | as Launch. |
| task.py | 214 | Tool-only loop. | as API sibling minus `.perform_selected_wait`/`.last_observed_credit`. |
| task_decision.py | 294 | Model-call/exchange rules. | as Launch. |
| task_state.py | 115 | Per-episode state. | as Launch. |
| waiting.py | 9 | Only suspension registration. | `self.workflow.execution_handle`×2, `.execution_backend`. |
| report_delivery.py | 34 | Final form fill. | as Launch (`runtime_forms`×2). |
| credit.py | 260 | Practical-state credit and verification. | as API sibling (`runtime_*` tables via `self.store.db`, `episode_receipts`, `episode_return_records`, `method_loop.identities`, `numerical.NumericBand`, `practical_yield`). |
| yield_estimator.py | 58 | Accumulation + practical forecast, key `launch_hpc:<class>`. | imports `numerical.YieldController, YieldParameters`, `practical_yield.PracticalYieldEstimator`. |
| to_parent.py | 296 | Practical facts and receipt-derived handoffs. | as Launch. |
| episode.py | 52 | Identity, no children, `('tool',)`, `context_hook_applies` only for `launch_hpc`. | old registry declarations (`binding_path`, `commissioning_parent`, `roles`, `entry_roles`, `decision_source_type`, `_private_practical_estimator_owner`). |

## Differences from similar episodes

- vs `api_job_execution`: tool-only (no wait), goal from the terminal behaviour, credit/verification from the
  practical state, handoffs also derived from practical receipts, no BLAST selection check against the parent,
  no `blast_request_custody.py`, no waiting_support input, `decision_context` without selected execution task.
- vs Launch parent: one practical request, no children, no reason/wait, accumulation estimator.
- The `local_job_execution` sibling (not covered here) is the local-resource counterpart of this episode.
