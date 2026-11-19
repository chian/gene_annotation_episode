# Intent: a110/biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution

Read from its own files at commit `97308b94c`. It is a leaf. Old role name: `launch_local`. Old commissioning parent: `execution_job_submission` (role `launch`).

This folder is a copy of `hpc_job_execution`. `git diff` between the two trees touches only 8 files and 23 lines. Everything below holds as in `a110__..._hpc_job_execution.md` unless listed here.

## Purpose (its own words)

It uses the same execution-agent instructions as its sibling (in its own identical `terminal_execution.py`): "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. ... The episode iterator decides continuation from credit; add no stopping budget."

It runs the actual job on the **local** resource, with the coordinator workspace as the run directory. It is also the only execution leaf here that may run native flux-balance (FBA) work: configuration refuses `native_flux_balance` on any non-local resource.

## Task and instructions

The text is identical to the hpc sibling.

## What it reads from its parent's assignment (`from_parent.py`, 87 lines)

- `assignment_schema`: anyOf the `practical_assignment_v1` schemas for configured `local` resources. With FBA configured, it also includes the compact `resource_assignment_schema` alternative.
- `child_assignment_schema`: no frozen-request restriction (the hpc sibling has one).
- `prepare_assignment`: also accepts a **compact flux-balance assignment**:
  - parent role must be `launch`;
  - it reads the Launch's request binding (`read_request_binding(store, run_id, parent.episode_id)`);
  - it selects the matching row and checks flux-balance inputs and input versions against that row.

  Otherwise it behaves like the sibling: validate the request, match kind, check against the parent Launch's `immutable_input_versions`.
- `NativeScienceInputs._flux_balance_inputs`: for role `launch_local` with a matching assignment, it reuses the frozen received flux-balance inputs.

## Children it may commission

None.

## Decision state and what the model sees

The same as the sibling, with one difference. For a non-compact assignment, `internal_summary._with_selected_execution_task` builds `selected_execution_task` from its single request (`{resource_id: assignment}`) when that request carries `native_flux_balance`. The task holds the scientific_question and selected_tool_info from the services hook `scientific_parent_task`, the scientific job view and the resource information. The hpc sibling returns the context unchanged in this case.

## Tools, credit, report

- **Tools:** identical, with `operation_catalog('local')`.
- **Credit:** identical: the PracticalState credit view plus the closed snapshot.
- **Report:** identical facts.

## Continuation

Old behaviour: `YieldController` with `PracticalYieldEstimator(verify_completion)`, profile `task_yield_profiles['launch_local:' + request yield class]`. The configuration also accepts `results_yield_profiles['native_unbounded_local']`.

Mapping: **CompletionYieldEstimator(initial_credit, target)** with the `launch_local:<class>` profile settings, as for the sibling.

## File-by-file

The line counts and old-runner names match the hpc sibling's table, except for the files below. Per-file counts for this episode are in `runs/carry_over/calls/a110_04.tsv`.

| Old file | Lines | Difference in own intent | Old-runner names |
|---|---|---|---|
| from_parent.py | 87 | Compact FBA assignment accepted; no frozen-hpc enum | Same helpers; uses Launch request binding (`flux_balance_request_binding`) |
| internal_summary.py | 78 | selected_execution_task for a single non-compact FBA request | Same as sibling |
| yield_estimator.py | 48 | Profile prefix `launch_local:` | `numerical.YieldController`, `YieldParameters`; `practical_yield.PracticalYieldEstimator`×4 |
| episode.py | 84 | role `launch_local`, own path | old hook names |
| binding_record.py | 8 | own binding_id | none |
| execution_contracts.py | 44 | Imports own terminal_execution | `communication.*` imports |
| initial_information.py | 8 | own path | old catalog protocol |
| received_execution_information.py | 4 | own path | old catalog protocol |

All the other files are byte-identical to `hpc_job_execution`: goal, terminal_execution, task, task_decision, task_instructions, task_state, task_report, task_suspension, waiting, presentation, configuration, credit, completion, to_parent, science, state, received_records, resource_information, work_operations and `__init__`. Their old-runner names are listed in that note.
