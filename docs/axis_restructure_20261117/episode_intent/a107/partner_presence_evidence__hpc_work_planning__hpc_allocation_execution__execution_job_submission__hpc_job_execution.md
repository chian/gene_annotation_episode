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
