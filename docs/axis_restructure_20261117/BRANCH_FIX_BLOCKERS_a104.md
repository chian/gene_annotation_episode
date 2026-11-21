# BRANCH_FIX_BLOCKERS_a104: the monitor port (19 November 2026)

Scope: `root/a104/evolutionary_history_evidence/execution_progress_assessment` on the built job services
(`BRANCH_RUNS_a104.md`, branch 1). The port itself is described in `MONITOR_PORT_RECIPE.md`.

## Runner

No runner file is at fault. `store_scope.py`, `runner.py`, `journal.py`, `recording.py`, `services.py` and
`work_tables.py` were not edited and nothing in them stopped the port. One member was added to
`episode_runtime/job_access.py`: `JobAccess.window`.

## What limits the monitor now

1. **No time-remaining estimate and no score of the earlier estimate** (design sections 7 and 11). The monitor
   records, before each check, the expectation of that check in the estimate table (the gain band in its own credit
   units, the cost, the probability the model gave that the check is informative) and resolves it after the check.
   It does not compute a distribution of the seconds remaining, and scores none. Missing: a duration estimate in a
   defined form in the handoff row. `handoff['detail']['estimates']` is whatever the launching tool passed; no
   launch episode of A104 writes a job ledger handoff yet (`execution_job_submission` and its three route children
   still raise `BLOCKED-ON-JOB-SERVICE`), and the time model (`hpc_prediction.distribution`, `log_score`) is the
   per-axis library copy of "Not provided yet" item 6. Wanted: the launch writes `estimates['duration']` as a
   `hpc_prediction.distribution`; `job_progress.status_reading` then returns the remaining-time summary and the
   score of the previous check's estimate, and the monitor returns them as numbers.
2. **The A104 head never offers the monitor.** Its `task.py` offers the model only its own kind and `hpc`
   (`OFFERED_CHILDREN`). The head's `msg_to_child` now builds the monitor's commission from a job the head holds
   (`_monitor`, with `outstanding_jobs` in its summary), and the model-run test commissions it by `run_unit`. In a
   run decided by the head's model no monitor is commissioned, and the head's return form has no field for the
   records of a job it leaves outstanding. Offering the slot and returning outstanding jobs are the head's own
   work (design section 8).
3. **No launch and no extraction in A104 yet.** `execution_job_submission` and `execution_result_acquisition`
   were not ported. A handoff row reaches the head only through the `record_refs` of its own assignment. The
   monitor was run on jobs launched by the job services' test episode `job_probe`.
4. **Legacy `exec_command` labels.** Library handoff records (`records/*/practical_execution_records.py`,
   `findings/*/terminal_scientific_evidence.py`, `jobs/local_execution/*/terminal_execution.py`) set
   `'monitor_operation': 'exec_command'` and `'results_operation': 'exec_command'`. The monitor reads none of
   those records and acts on no such label: its job is the job ledger row `job_access.launch` wrote, and its
   actions are the five defined ones, carried out by code. The library files were not edited. A launch episode
   that returns such a record in `execution_handoff_refs` instead of a job ledger handoff row gives the monitor
   nothing to check: the head's `outstanding_jobs` lists job ledger rows only.
5. **The reading of a batch job's scheduler reply has not run.** `job_progress.status_reading` for the route kind
   `pbs` reads `returncode` of a login-mode job (run by the test through the route's shell transport) and
   `Exit_status` of a batch job's `qstat` fields; no PBS scheduler exists where the tests run (the same limit as
   "Not provided yet" item 4). A route to API services has no reading.
   The route kind `api` (`episode_support/jobs/api_job_route.py`, written by another agent during this work)
   has no reading in `job_progress.READINGS`: a check of an API job fails with `KeyError('api')`. The old
   `api_observer.py`, `appservice_observer.py` and `hmmer_observer.py` of this episode (at `97308b94c`) are the
   source of what that reading keeps.
6. **`launch_estimates` is shown to the monitor's model as the launch wrote it** (`handoff['detail']['estimates']`,
   closed JSON of any shape). The design expects numbers there (the prediction, the expected gain, the duration
   estimate, the expected cost). A launch episode that writes prose there would pass it to the monitor's model
   through a record. Nothing in the monitor checks the shape.
7. **The two nested A104 monitor copies** (`hpc_work_planning/execution_progress_assessment`,
   `hpc_work_planning/hpc_allocation_execution/execution_progress_assessment`) were not ported; their
   commissioners are the unported HPC chain (`AXIS_WAVE_BLOCKERS_a104.md` item 1).

## Where the test of `JobAccess.window` is

`episode_runtime/tests/` holds no test of `job_access`: its real tests are
`episode_support/jobs/tests/test_job_services.py`, run through the test episode `job_probe` on real local jobs. The
test of `window` is there (`test_a_window_of_a_running_jobs_log_comes_into_custody_and_does_not_close_the_job`),
with a `window` tool added to `job_probe/task.py`. The monitor's own tests run `window` again on the local and on
the remote route.
