# A107 HPC planning fix: blockers and open points (19 November 2026)

Written with the port of `root/a107/partner_presence_evidence/hpc_work_planning` (the planning head),
`hpc_resource_prediction` and `hpc_allocation_execution` onto the `HpcLedger` work table (`HPC_PORT_RECIPE.md`).
Nothing in `episode_runtime/` was edited. There is no HPC where the tests run: nothing authenticated to Aurora and
nothing remote was contacted.

## 1. Members of the services that the episodes wanted and that do not exist: the call used instead

| Wanted call (the old `BLOCKED-ON-JOB-SERVICE` note) | Real call used | Where |
|---|---|---|
| `job_access.run_remote(ssh_argv, command, key=)`, `job_access.run_command(configuration, command, key=)` | `await job_access.run(ctx, resource_id, {'mode': 'login', 'script': command, 'arguments': [], 'env': {}}, name=)`, then the reply artifact for the return code and the fetched `stdout.log` / `stderr.log` | `episode_support/jobs/hpc/hpc_remote.py` `command` |
| `job_access.observe_queue(configuration, key=)` (the old `hpc_queue.observe(configuration)`: `subprocess` over `ssh_argv`, `urlopen` of the ALCF activity page) | one login-mode command through `hpc_remote.command` that writes `jobs.json`, `queues.json` and `activity.json` in the job directory; the old function is deleted | `episode_support/jobs/hpc/hpc_queue.py` `observe(ctx, resource_id, *, name='queue')` |
| `job_access.read_file(target, path=, offset=0, limit=, key=)` for a file of the allocation workspace (outside the job directory, which is all `route.read` reaches) | a login-mode `head -c <limit + 1> -- <path> > window.bin`, fetched as an artifact | `hpc_remote.read_file` |
| `job_access.write_allocation_control(target, unit_ids=, key=)` | a login-mode `cp` and `mv` of a staged artifact (`inputs={'content.bin': ref}`) | `hpc_remote.write_file` |
| `job_access.observe_target(target, key=, resumed=)` | `job_access.check(ctx, handoff_ref)` and its reply artifact (`reply['native']` are the `qstat` fields) | `hpc_remote.job_status` |
| `store.table(JOB_LEDGER).get(handoff_ref)` "as the execution target" | the same call; the target is `{'handoff_ref', 'job', 'resource_id', 'execution_id' (detail.native.job_id)}` | `hpc_remote.handoff_target` |
| `estimate_table.read('resource_tool_estimates', 'hpc' / 'hpc_execution')` (the old `resource_estimator.estimate_context(execution_expectations.capture(...))`) | `estimate_table.read('profiles')` (the execution profiles that have a measurement), shown as `shared_timing_profiles` only when `shared_execution_memory` is true | the two `decide` of the head and the allocation |
| `estimate_table.observe(..., key=)`, `.record(**measurement, key=)` | the same members without `key` (the table writes an observation by content and an attempt by `attempt_id`) | `task.py` of the three episodes |

If the owner of `job_access.py` adds a file read and write outside the job directory, or a command call that
returns the return code, `hpc_remote.py` is the one place to change.

## 2. What could not be run here, and why

- **Everything after a real queue observation.** No scheduler is installed and the model runs use a route whose
  transport does not exist (`transport_unavailable`). `hpc_queue.observe` is run to the failed scheduler command
  (`queue_observation_failed`, real local-shell route). Its success path (`hpc_queue.snapshot` of real `qstat` JSON),
  `hpc_compare` with a real observation, `hpc_plan` to a frozen plan with its launch-input artifact, `hpc_handoff`,
  `hpc_monitor`, `hpc_monitor_wait`, `hpc_results` and `hpc_allocation_order` are written and have never executed.
  The offline tests reach the planning tools as far as their refusals (`unknown_hpc_evidence:<queue_ref>`,
  `unknown_candidate`); the tools that need a frozen plan are not reached (`action` rejects an unknown plan).
- **`hpc_remote.handoff_target` and `job_status`** need a batch-mode handoff row (`qsub`); never executed.
  `read_file`, `write_file` and `command` run in `jobs/tests/test_job_services.py` through the local-shell route.
- **The launch, monitor and results children** (six episodes under the head, six under the allocation sister) are
  still on their `BLOCKED-ON-JOB-SERVICE` stubs. They are registered and linked by the branch tests and were never
  commissioned (the model had no plan to launch). A model that commissions `monitor` with a made-up target handle
  would reach a stub and end the run with its error. They are not part of this port.

## 3. Behaviour that changed or was not carried, each for a stated reason

1. **The exit receipt of the old `TerminalExecution`** (`observation['native']['exit_receipt']`: the job's own
   duration and finish time) is not in the reply of `JobAccess.check`. `measure` takes the work time from the
   allocation's own status file when it has one and from the scheduler's start time otherwise (censored). This is
   item 5 of "Not provided yet" in `LAUNCH_MONITOR_EXTRACT_MECHANICS.md`.
2. **The handoff is bound to its plan by the unit that launched it**, not by comparing an `assignment` in the
   handoff record: a `JOB_LEDGER` handoff row has no assignment. `action` rejects `hpc_handoff` unless the handoff
   reference is one the launch commissioned for that plan returned (`handoff_does_not_match_frozen_portfolio`);
   the tool checks the resource id.
3. **The tool request of the head's assignment** (`tool_request`) is kept in the ledger as given (tool name,
   resources, parsed arguments, result reader, objective, the execution rule). The old code also resolved the
   tool's contract and the result-reader options from the A107 head's tool library
   (`binding.tool_library.resolve_invocations`, `parent_tool_info`). That library is not carried
   (`AXIS_WAVE_BLOCKERS_a107.md`, section 2); when the service `tool_library` exists the head can add the contract
   in `tool_request_record`.
4. **A commission by source** (`commission_source_ref`): `hpc_commission_sources.read` needs the source record,
   its artifact and its `hpc_commission_sources` row in custody; the three assignment forms admit exactly one
   reference. Only `commission_id` is tested. Fix when used: pass the three references (a `record_refs` field).
5. **`EstimateTable.history` keeps at most 2000 rows** (`limit=2000`, its own maximum). The episodes pass no
   limit; the cap is the service's.
6. **`hpc_plan` returns an invalid unit** for a model-named queue observation or model that the ledger does not
   hold, a stale observation, a queue that is not an enabled execution queue and a candidate outside the queue's
   limits. The old tool raised, which would end a run on a model's wrong argument.
7. **The launch-instruction and tool-knowledge library texts are not in the three prompts.** The old `decide`
   read the libraries from a directory named in the settings (a read of the outside world that goes round `ctx`)
   and added their instruction text although none of the three episodes offers a tool that looks anything up in
   them. The `launch` commission still takes a `launch_instructions` selection from the model. To show a library,
   declare the service `instruction_libraries` and read `.read('context')` in `decide`.

## 4. The returns changed: a file I may not edit names the old fields

The three returns are now controlled data: `credit`, `finding` (counts and one boolean), `hpc_ledger_refs`
(required: the rows of the ledger and the records they name) and the selectable `hpc_result_refs` and
`hpc_result_artifact_refs`. Removed: `hpc_credit` (it restated the credit), `hpc_model_ref` and
`hpc_accepted_obligations` (text and a list; both are rows of the returned ledger) and `qualification` (prose).

`root/a107/partner_presence_evidence/messages/msg_to_child.py` (the A107 head, outside this port) still offers its
model the three removed names in `SELECTABLE['hpc']` (lines 206 to 212), and its own test
`root/a107/partner_presence_evidence/tests/test_binding.py::test_the_selectable_names_are_the_names_the_child_declares[hpc]`
fails for exactly that reason since this port (the only failing test of the folders run). A model that selects one of them makes a
wrong commission (`FormError`). The table must become `{'hpc_result_refs', 'hpc_result_artifact_refs'}`, and the
head's `read_from_child` for the slot `hpc` must read `credit`, `finding` and the two record fields. To continue the
HPC work of a commission later, the head passes the returned `hpc_ledger_refs` back in `received_record_refs`
(tested: `hpc_work_planning/tests/test_hpc_work_planning_runs.py`).

## 5. Credit attribution on a shared ledger

The ledger is shared, so "the ledger's credit" is not one episode's credit. The prediction's credit was already its
own (model improvement since its entry). The allocation sister's and the head's credit are now the ledger's credit
minus the ledger's credit when the episode first read or opened it: before this, the allocation sister reported
the prediction sister's 0.14 as its own in the first run of the head. A sister's `finding` says nothing about
productivity; its credit does.

## 6. A race in the PBS route's login mode (changed; the reasoning is not proven by a reproduction)

`jobs/tests/test_job_services.py::test_the_remote_route_submits_a_handle_once_and_reports_cancels_and_reads_its_job`
failed in two offline runs (`runs/fixhpc_16`, `runs/fixhpc_18`) after passing in two (`runs/fixhpc_11`, `runs/fixhpc_15`): `RouteRequestError: job_state_unknown`
from `PbsSshRoute.wait`). `hpc_remote.command` waits the same way, so a discovery or a queue observation could
have come back as a failed unit for the same reason. Reading of `pbs_job_route.py` `REMOTE`: the login wrapper ended
with `mv exit_code.writing exit_code` as its last command, which a shell may run by replacing itself; that process
no longer carries the job's handle, so between the end of the script and the rename the job was neither running
nor finished (`unknown`). Changed: the wrapper ends with `; :` so that the shell stays until the code is published,
and `state` looks for the process before it looks for the exit code. After the change the same files passed three
times in a row (`runs/fixhpc_19` to `runs/fixhpc_21`, 61 passed each). The failure was not reproduced on purpose.
