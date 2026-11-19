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
