# A101 branch fix: what the extract port leaves open (19 November 2026)

Written by the fixer of `root/a101/sequence_homology_evidence/execution_result_acquisition` (the plain file result
of a job on the built `JobAccess`). `episode_runtime/` was not edited. The port itself and how to repeat it are in
`EXTRACT_PORT_RECIPE.md`.

## 1. A member of `JobAccess` the port would use, and the call used in its place

No member the port needs is missing. One would make it cheaper:

- **A bounded read of a result file that is not fetched whole.** Wanted:
  `job_access.fetch(ctx, handoff_ref, names=[name], offset=<int>, limit=<int>)`, returning for each name the
  artifact of that byte window with `{'name', 'ref', 'offset', 'bytes', 'file_bytes', 'sha256'}` and writing the
  closure row once every requested interval of the job is fetched. Used in its place:
  `job_access.fetch(ctx, handoff_ref, names=[...])`, which reads each requested file whole into memory and writes
  it as one artifact (`LAUNCH_MONITOR_EXTRACT_MECHANICS.md`, "Not provided yet", item 9); the episode then reads its
  windows from the held artifact with `ctx.store.open_artifact(ref)`. A requested interval of a very large file
  therefore costs the whole file.
- `JobAccess.window(ctx, handoff_ref, name, offset=, limit=)` appeared in `episode_runtime/job_access.py` while this
  port was written (the monitor's log window). It reads one window through the route and writes a `window` row; it
  does not ask the job's state and does not close the job. The extract episode does not call it: its fetch is the
  closure of the job. It is the nearest existing member to the wanted call above.

## 2. `wait` of the extract episode is still a stub

`task.py::wait` (the selected wait of an API service assignment) still raises `NotImplementedError('BLOCKED-ON-JOB-
SERVICE: job_access.validate_event_targets and wait_events ...')`. No placed family offers it (`_catalog` never
lists it), so no run reaches it. Its real call is `await ctx.services['native_events'].wait(ctx, condition)`, which
needs `'native_events'` in `SERVICES` (every world that links this episode then supplies that factory) and an API
route, which does not exist (`LAUNCH_MONITOR_EXTRACT_MECHANICS.md`, "Not provided yet", item 3). In the launch,
monitor, extract design the extract child does not wait for a job. Decision wanted: delete the tool, or keep it for
the API family.

## 3. The head does not build the results commission yet

Unchanged from `AXIS_WAVE_BLOCKERS_a101.md` section 1: `sequence_homology_evidence/messages/msg_to_child.py::_results`
takes the assignment from the model's open `assignment` object. For a plain file result the commissioner builds it
from the handoff row it holds: `handoff_ref` = the row's id, the row in `record_refs`, `target` with
`resource_id` = `detail['resource_id']`, `resource_kind` = `detail['kind']`, `execution_id` = the row's `job`, and
`assignment.workspace` = `detail['native']['directory']`; the selector's paths lie inside that directory. The test
world `execution_result_acquisition/tests/plain_world.py::entry_input` does exactly this.

The head's list of this child's selectable fields (`sequence_homology_evidence/task.py`, `SELECTABLE`) was brought
in line with the child's return form (two lines): `execution_result_origin` and `execution_file_capture_outcomes`
are gone, `execution_job_record_refs` is new.

## 4. Legacy `exec_command` labels (owner rule: the model is the router, code executes)

The extract episode reads no handoff label that names an operation. It reads the job ledger handoff row
(`detail`: `resource_id`, `kind`, `native`) and the assignment's `target` (`resource_id`, `resource_kind`, `handle`,
`assignment.workspace`, `assignment.requested_job` for the family). Its operations are fixed in code
(`JobAccess.check`, `JobAccess.fetch`, a window of a held artifact) and take controlled operands only: none, or
`path` from the fetched paths with integer `offset` and `limit`.

The library still writes `'monitor_operation': 'exec_command'` and `'results_operation': 'exec_command'` into old
handoff records (`episode_support/records/sequence_homology_evidence/practical_execution_records.py` line 495, read
here; the coordinator also names `records/*/practical_execution_records.py`,
`findings/*/terminal_scientific_evidence.py` and `jobs/local_execution/*/terminal_execution.py`, not opened here).
Those are legacy labels. Nothing in this episode reads or acts on them, and `target['assignment']` is an open object
(`TARGET_SCHEMA` in `forms/sequence_homology_evidence/execution_contracts.py`), so a commissioner could still copy
such a label into it; it would be ignored. The library files were not edited.

## 5. Typed result families stay unplaced

The `unplaced:<family>` raises of the typed native families, of the other API results and of the local file
sources (`read_from_parent.py`, `task.py::_catalog`, `credit.py`, `yield_estimator.py`) are not on the plain route
and were not touched.

## 6. Stopping after a complete plain acquisition takes many idle units under the test's settings

Not a defect of the system: with an unbounded selector the episode names the accumulation controller, and after
the fetch earned the whole unit the controller needed 10 to 12 more status requests that earned nothing before it
stopped (three real runs; settings of the test: cutoff 0.1, `uncertainty_alpha` 0.05). A finite selector (`path`, `offset`,
`limit`) names the bounded-quality controller and stops at its maximum on the unit that completes it. The old
exact-zero forecast for an exhausted selector is not a controller input and is not carried.
