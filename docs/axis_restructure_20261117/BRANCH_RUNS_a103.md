# A103 branch runs (19 November 2026)

Runner report. Nothing in episodes, library or runtime was changed. Two new test files (world fixtures, real model, real
Store, RunJournal, `job_services` real detached local route):

- `root/a103/gene_context_evidence/execution_job_submission/local_job_execution/tests/test_branch_local_job_execution_model_run.py`
- (no 1b test written: see 1b)

Offline check first: `local_job_execution/tests/test_local_job_execution_binding.py` 7 passed (run `runs/br_a103_2`).

## 1a. `execution_job_submission/local_job_execution` alone: FAIL

Run dir `runs/brm_a103_1`, log `runs/brm_a103_1.log` (9 s).

World: local resource `local_test` (workspace under the test's tmp path, 256 MiB / 64 MiB policy), a valid
`practical_assignment_v1` (generic argv job `python -c "write answer.txt; print"`, one requirement `handoff` credit 4.0,
`completion_keys ['handoff']`, endpoint `usable_handoff`), settings with the frozen launch-instruction and tool-knowledge
libraries and profile `launch_local:practical_local_handoff` (cutoff 0.5). Entry selects `execution_handoff_refs` and
`execution_completed`. The assignment was admitted by the form and `read_from_parent` (7 offline binding checks pass).

Journal facts: run state `active`, `run_failure` = the error below. One episode (the local job execution), no unit
recorded as completed (the first unit raised), one model call recorded at position 0, no controller step, no completion.
The run did not complete through the yield estimator; resume and RETURN_FORM admission were not reached.

Model decisions in order: `exec_command` with `cmd` = `ls -la /tmp/ramrepo; find /tmp/ramrepo -maxdepth 3 -type f -iname
'*launcher*' -o -iname '*workflow*' | head -50`, workdir the job workspace, target `resource`. That is exploration of the
repository, not the assigned job: the model ignored the assignment's `requested_job` as its first action (see the
INSTRUCTIONS note). (`action` accepted it: workdir inside workspace, schema valid.)

Failure:
`episodic_workflow/root/a103/gene_context_evidence/execution_job_submission/local_job_execution/task.py:102`, in `exec_command`:
`NotImplementedError: BLOCKED-ON-JOB-SERVICE: job_access.exec_command(assignment, arguments, *, key)`.

Classification: LIBRARY (service) with an EPISODE share. Diagnosis: the episode's only job-starting tool calls
`ctx.services['job_access'].exec_command(...)`, which the real `JobAccess` (`episode_runtime/job_access.py`) does not have.
`JobAccess` offers `launch(ctx, resource_id, job, *, inputs, estimates, name)` (writes the JOB_LEDGER `handoff` row, returns
`handoff_ref`), `check`, `fetch`, `cancel`, `run`; the local route (`episode_support/jobs/local_job_route.py`) takes a job
`{'command': [argv], 'env': {...}}`. Nothing in the episode calls `launch`, so no real job is started, no JOB_LEDGER
handoff row is written, and `internal_summary`/`final_to_parent` count handoffs from the receipt of an `exec_command`
(`outcome['handoff']`, `receipt_ref`), a shape the service does not produce.

Smallest suspected fix (not applied): in `local_job_execution/task.py` rewrite `exec_command` (line ~90-110) as a launch
tool: map the validated command to `{'command': argv, 'env': env}` (or the assignment's `requested_job`
`{'argv','environment'}`) and call `ctx.services['job_access'].launch(ctx, arguments['assignment']['resource_id'], job,
estimates=..., name='job')`; return `{'status', 'job', 'handoff_ref', ...}`; then rework `messages/internal_summary.py`
(lines ~63-75: `outcome['receipt']`, `receipt_ref`, `handoff`) and the credit/completion proof
(`_completion`, `project_practical_credit`, which verify `requested_job_handoff` from a receipt's validations) to read the
JOB_LEDGER handoff row instead, and `final_to_parent.execution_handoff_refs` to return its record ref. Also the tool is
`async` only to await a service reply; `launch` is synchronous.

INSTRUCTIONS note: the model's first command was unrelated to the assigned job (it listed `/tmp/ramrepo` looking for the
workflow launcher). `GOAL_INSTRUCTION` says "no sequence of setup or job-stage operations is prescribed" and offers a free
shell, so the model did not start from `requested_job`. A tool that launches the assignment's own request (above) removes
the freedom.

## 1b. `execution_job_submission` over `local_job_execution`: NOT RUN

Stopped at the failing branch of its chain (1a). No 1b test was written or run. Known without running: the parent's
`msg_to_child('launch_local')` builds the child's assignment from `requests[resource_id]` plus `record_refs`
and selects `execution_handoff_refs` and `execution_completed`; the parent's `credit`/`read_from_child` count a handoff from
the child's `execution_completed` and `execution_handoff_refs`, which 1a cannot produce today. The parent's own
`task.py` also has items that raise before the child is reached for a real run: `_resources` raises
`NotImplementedError('unplaced:a103_execution_bindings...')` for any resource carrying `native_*` bindings (not the
plain local resource here), and `settings['resources']` uses kind `local`. The check list for 1b (model launches the job,
JOB_LEDGER handoff row written, launching child ends at handoff, parent returns only controlled fields) is open until 1a is
fixed.
