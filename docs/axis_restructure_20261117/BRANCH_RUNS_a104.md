# BRANCH_RUNS_a104 (19 November 2026)

## Branch 1: monitor `execution_progress_assessment` on a real local job (1a running, 1b finished): FAIL

Test written: `gene_annotation_episode/episodic_workflow/root/a104/evolutionary_history_evidence/execution_progress_assessment/tests/test_branch_execution_progress_assessment_model_run.py`
(two tests, `@pytest.mark.model_run`). World: real Store, RunJournal, `job_services(configuration)` with the local route.
`job_probe` launches a real detached local job through `job_access.launch` (1a: left running; 1b: released and waited
to its end); the job's handle is the monitor's `target_handle` in the entry assignment (`monitor_assignment_v1`, all
fields requested, return fields selected). Real `ModelProvider`.

Run dir: `runs/brm_a104_2` (log `runs/brm_a104_2/log.txt`). The `hpc_work_planning/execution_progress_assessment`
copy was not run (the branch fails at the first branch; its `task.py` differs but has the same job-service block).

Journal facts: the launch run (job_probe) completed for both cases (a real local job was started; handoff row written).
The monitor run has no unit and no model call: it fails in its first `decide`, before the model is asked. Neither the
estimate table nor the native events service was called by the monitor (the monitor declares only `job_access`).
Model decisions: none. Credit: none. ended_by: none (exception). Resume: not reached.

Error (both 1a and 1b):
`task.py:185 decide`: `ctx.services['job_access'].read('describe_progress_target', summary['target_handle'])` ->
`episode_runtime/services.py:80`: `AttributeError: 'JobAccess' object has no attribute 'describe_progress_target'`.

Classification: EPISODE (the monitor was not ported to the Stage 1b `job_access`), with a LIBRARY/RUNNER gap behind it.
Diagnosis: the monitor still names the old progress provider. `JobAccess` (`episode_runtime/job_access.py`) offers
`launch`, `check`, `fetch`, `cancel`, `run` and the reads `resources` and `describe(resource_id)`; it has no
`describe_progress_target`, no `observe_progress` and no `read_progress`. `task.py:_observe_progress` (line ~100) and
`credit.py:_SummaryProgress.read_progress` raise `NotImplementedError('BLOCKED-ON-JOB-SERVICE ...')`, so even past
`decide`, `progress_observe` could never deliver a `progress_snapshot_v1`. The monitor also never uses the
`native_events` service (`wait`) or the `estimate_table` service (`expect`/`resolve`/`kind_statistics`) and does not
declare them in `SERVICES`; the offered tools are only `progress_observe`, `progress_read`, `progress_log`, no wait.
Further: `read_from_parent.ASSIGNMENT_FORM` has no `record_refs` field, so a handoff record cannot be passed to the
monitor in custody as the commissioner would (the job is named only by `target_handle`); and the old `ProgressInformationCredit`
wants snapshots of the old shape.
Smallest suspected fix: rewrite the monitor on `job_access.check(ctx, handoff_ref, assess=...)`: add a `handoff_refs`
`record_refs` field to `read_from_parent.py` ASSIGNMENT_FORM; replace `task.py:185/:198` `describe_progress_target` with the
`resources`/`describe` reads (or drop it); turn `progress_observe` (task.py ~100-113) into a unit calling
`ctx.services['job_access'].check(ctx, arguments['handoff_ref'])` returning the `check` row (state, `result_available`); add `native_events.wait` as a
`progress_wait` tool and `estimate_table` reads/`resolve` to `SERVICES`; make `credit.py` score the check rows
(`job_records.checks`) instead of `read_progress` snapshots; adjust `final_to_parent.py` to the check-row fields.

The test is ready to rerun unchanged in structure once the monitor takes a handoff reference (the assignment in
`monitor()` in the test then needs `handoff_refs=[handoff_ref]`; `started_job` already returns the ref).

## Branch 1 after the port (19 November 2026): PASS

The monitor was rewritten on the job services (`MONITOR_PORT_RECIPE.md`; open items in
`BRANCH_FIX_BLOCKERS_a104.md`). The test above was corrected in its world only: the job's handoff row is passed as a
record (`handoff_refs` of `monitor_assignment_v2`), the journal path uses the binding's grain name, the monitor's
`cost` is 0.2. Two cases were added: the monitor commissions a monitor of its own kind for a dependency, and the
A104 head commissions the monitor on a job it holds.

Run dir `runs/fixmon_9` (log `runs/fixmon_9.log`), real model, 4 passed. Every Episode `ended_by: yield_stop`; each
entry run resumed to the same result with no new model call.

| Case | Model decisions, in order | Result |
|---|---|---|
| 1a job still running | `progress_observe` (probability 0.99), `progress_log` (stdout.log, 0 to 127), `progress_read` twice, `progress_observe` (0.8), `progress_read` | credit 1.0; state `running`, results not available; elapsed 22.4 s known, return code unknown; 2 check rows and 1 log window returned in custody |
| 1b job already finished | `progress_observe` (0.99), `progress_read` six times | credit 1.0; state `finished`, results available; return code 0, duration known; 1 check row |
| 1c dependency monitor (commissioned by `run_unit`) | child: `progress_observe` (0.99), `progress_log`, `progress_read` six times | child credit 1.0, state `finished`; its check row returned to the parent monitor, whose credit counts it |
| 1d head commissions the monitor (by `run_unit`) | monitor: `progress_observe` (0.99), `progress_read` four times, `progress_log`, `progress_read` | handoff row `commissioned`; monitor credit 1.0, state `finished`, return code 0; check row `returned` to the head |

Services built: `estimate_table` (read by each decision, written by each check) and `job_access`. No wait was
selected in these runs. In an earlier run of 1a (`runs/fixmon_4`, stopped) the request did not say what a wait costs:
the model checked, read the log, checked again and then waited 60 and 300 seconds for a job the test never ends.
The request now says that a wait is spent inside the Episode and that the commissioner receives nothing until the
controller ends it; with that text the model read a held check again (no request, no time) until the controller
stopped the Episode.

The model request, before and after. Before (`decide` raised before it was built; from the code): the old goal text
(report forms, private reasoning, "information-credit projector and bound yield rule"), the resource-estimate
guidance for inputs that were never supplied, and a context of `goal`, `monitor_assignment` (the assignment again),
`monitor_target_description`, `monitor_received_progress_refs`, `monitor_information_meaning`, a `tools` catalog of
JSON schemas, the raw last outcome, the credit three times (`current_credit`, `monitoring_information_credit`,
`monitoring_information_binding` with its formula record), the controller's whole state and `time_accounting`.
After (printed by `tests/test_monitor_units.py`, first test): the purpose in the first sentence, the actions offered
now with what each does, what each context field is, what earns credit, what returns, and that only the controller
ends the Episode; a context of `job` (once), `now`, `checks`, `units` with the credit each earned, `credit`
(current, unit, cost of one action) and `earlier_checks_of_this_kind`.
