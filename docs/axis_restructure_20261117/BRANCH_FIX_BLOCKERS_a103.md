# A103 launch fix: blockers and open points (19 November 2026)

Written with the fix of `root/a103/gene_context_evidence/execution_job_submission/local_job_execution` and its
parent `execution_job_submission` (`LAUNCH_PORT_RECIPE.md`, `LOCAL_WRAPPER.md`). Nothing in `episode_runtime/` was
edited.

## 1. No member of `JobAccess` is missing for the local launch

The launch uses `JobAccess.launch(ctx, resource_id, job)` (through the local wrapper) and the read handle
`ctx.services['job_access'].read('describe', resource_id)`. Both exist. Nothing was needed from another owner.

## 2. A real launch is sometimes refused although the job's service started (fixed 19 November 2026, see the note)

Note (19 November 2026, later): the cause below is confirmed and fixed in `native_lifecycle.resume_start`: an
`inactive` unit is final only when it has no queued job (`Job` is now among the properties `_properties` reads).
The reproduction is `episode_support/jobs/tests/test_local_launch_repeated.py` (30 launches in sequence through the
runner, 30 in bursts of five through the route): before the fix 6 of 60 burst launches were refused with
`service_did_not_initialize`; after it 0 of 360 launches (`runs/fixrace_3` to `runs/fixrace_8`). The same test
found a second false refusal, `local_resource_busy` (1 of 60 sequential launches, `runs/fixrace_2`):
`LocalResources._refresh` counted a job of another workflow's slice that ended between its listing and the read of
its slice as an untracked job that occupies the whole budget; it now skips a unit that read reports ended. The side
effect in the last bullet is unchanged for the other refusals of `resume_start` (a ready or cgroup mismatch).

Observed once in six real-model launches (`runs/fixlaunch_3`; its output was not kept in a log file; journal
`runs/fixlaunch_3/tmp/test_the_model_launches_the_lo0/journal.sqlite3`); the offline runs (about twenty-five launches)
never showed it.

- The launch unit's outcome was `{'status': 'failed', 'failure': {'code': 'local_job_boundary_unavailable',
  'detail': {'operational': {'reason': 'service_did_not_initialize', ...}, 'phase': 'local_preflight'}}}`.
- The systemd journal of the job's unit says it was started in the same second and stopped three seconds later,
  when the test's workflow ended, and the job's directory holds the service's `.ready` file. So the service did
  initialize; the lifecycle gave up before it saw that.
- Where: `gene_annotation_episode/native_lifecycle.py`, `resume_start`, lines 237 to 244. After
  `systemd-run --no-block` it polls `systemctl --user show <unit>` and treats `ActiveState` `inactive` (as well as
  `failed`, and `LoadState` `not-found`) as "the service did not initialize". Right after a `--no-block`
  submission a unit whose start job is still queued is `inactive`. When the user manager is busy (about ten agents
  share this machine) the first poll can arrive before the start job is dispatched.
- Smallest suspected fix (not applied): in that loop, do not treat `inactive` as final while the unit still has a
  queued job (add `Job` to the properties `_properties` reads; a nonzero `Job` means the start is pending).
  `failed` and `not-found` stay final.
- Effect on the tests: the branch runs 1a and 1b can fail on this refusal. The episode itself then behaves as
  designed, which the same run shows: the failed launch earned 0, the model was shown the failure code and chose
  `hold_launch` with reason `launch_failed`, the yield controller ended the Episode after that unit, and the return
  was `{'credit': 0.0, 'finding': {'launches_handed_off': 0, 'launches_failed': 1, 'holds': 1},
  'execution_handoff_refs': [], 'execution_completed': false}`.
- A side effect of the same refusal: the refused job's service stays alive, waiting for its release file, until
  the workflow's slice ends: `LocalJobRoute.submit` turns the error of `native.start_prepared` into the failed
  request and does not cancel the unit it had submitted.

## 3. Inputs of a job are not staged (owner decision needed)

The wrapper and `JobAccess.launch` stage inputs given as `{file name: reference}`. A `practical_assignment_v1`
names no file name for a record: its generic job is an argv and an environment, and a native job family keeps its
input references inside its own entry. The old shell flow staged them with commands the model wrote. So the local
launch child now receives the request alone (its assignment form has no `record_refs` and no `scientific_task`
field any more, and `msg_to_child` of `execution_job_submission` passes neither to `launch_local`), and a job runs
on what its argv names. To stage Store records, the request has to carry `{file name: reference}` (for example a
field `input_files`), the launch child's form has to declare it with a `record_refs` field, and `action` has to
hand it to the wrapper as `inputs`.

## 4. An assignment whose endpoint is the job's outputs

A launch ends at handoff. Its credit and its completion target are the credit of the assignment's
`requested_job_handoff` requirements only; the other predicate kinds (path, digest, command exit, job outputs) are
facts of a job that ran and are earned by the Episodes that check and fetch. A local launch assignment that has no
`requested_job_handoff` requirement at all (endpoint `completed_job_outputs` with only an outputs requirement) has
a target of zero, and the completion controller refuses it (`completion_target_must_be_positive`): the commission
is wrong for a launch child and fails with that error. Whether the head should stop sending such requests to a
launch child, or give them a handoff requirement, is the head's `msg_to_child`.

## 5. What is still raising in the parent `execution_job_submission` (unchanged by this fix)

- A launch assignment with an API request: `job_access.validate_assignment`, `capabilities`,
  `received_bvbrc_context` do not exist (`NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')`, `task.py`). There is
  no API route yet (`LAUNCH_MONITOR_EXTRACT_MECHANICS.md`, "Not provided yet", item 3).
- A configured resource that carries `native_*` bindings: `NotImplementedError('unplaced:a103_execution_bindings
  .validate_primary_resource_bindings')` (`task.py`, `_resources`).
- An unknown request version: `NotImplementedError('unplaced:a103_homology_execution.BLAST_GRADED_REQUEST_SCHEMA:...')`
  (`messages/read_from_parent.py`).
- `_bound` still validates a practical request against the configured resource with the library's
  `TerminalExecution.validate_assignment` (settings `resources`, `coordinator_workspace`).
- The parent's assignment still admits `scientific_task` (a record with the scientific question as text) from the
  head and still passes it to the API child. It is no longer passed to the local child and no longer shown to the
  parent's model.

## 6. Not done in this fix

- The other launch episodes of A103 still offer the old shell tool: `execution_job_submission/hpc_job_execution`,
  and the two nested trees `hpc_work_planning/execution_job_submission/**` and
  `hpc_work_planning/hpc_allocation_execution/execution_job_submission/**` (their `local_job_execution`,
  `hpc_job_execution` and parent `task.py`). The list and the steps are in `LAUNCH_PORT_RECIPE.md`.
- `docs/EVIDENCE_AXIS_LEDGER.md` was not edited (it is modified in the working tree by other work).
- `root/tests/test_private_bindings.py` fails for every axis (36 failed in `runs/fixlaunch_9`): it still states
  the old rule and counts each `messages/` folder as an episode folder without `episode.py`. Not caused by and not
  changed in this fix.
