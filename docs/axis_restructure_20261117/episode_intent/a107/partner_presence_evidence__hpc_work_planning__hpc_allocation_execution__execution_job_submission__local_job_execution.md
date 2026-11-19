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
