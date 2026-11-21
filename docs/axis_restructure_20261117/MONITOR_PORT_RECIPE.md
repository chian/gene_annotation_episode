# Monitor port recipe: `execution_progress_assessment` on the job services (19 November 2026)

The A104 monitor `root/a104/evolutionary_history_evidence/execution_progress_assessment` runs on the built job
services. It is the worked example. This file says, for every other monitor, which files an agent changes and how.
Nothing outside A104 was edited.

Read first: `LAUNCH_MONITOR_EXTRACT_MECHANICS.md` (sections 3, 5, 6, 7 and "Provided now"), `TRANSFORM_GUIDE.md`,
and the ten files of the A104 monitor with its two test files.

## What the port is

| Old (carried, did not run) | Now |
|---|---|
| job named by `target_handle` (text) | job named by a record: `handoff_refs` (`record_refs`, exactly one job ledger handoff row) |
| `known_progress_refs` (a list of provider identities) | `known_progress_refs` (`record_refs`: the check rows of the job the commissioner holds) |
| exposed dependencies read from a progress snapshot | `dependency_handoff_refs` (`record_refs`: the handoff rows of the jobs the target directly depends on) |
| `permitted_committed_record_types`, committed record refs | not carried: a job's results are records only after the result-acquisition child fetched them |
| `job_access.read('describe_progress_target', handle)` in `decide` and `action` | the held handoff row, read in `internal_summary` through `view.records` |
| `observe_progress` (raised `BLOCKED-ON-JOB-SERVICE`) | `job_access.check(ctx, handoff_ref, assess=job_progress.status_reading)` |
| `read_progress` of a snapshot | the held check row: `ctx.store.table(JOB_LEDGER).get(check_ref)`; `job_progress.check_view` |
| a retained log window of a snapshot | `job_access.window(ctx, handoff_ref, name, offset=, limit=)` (new member of `JobAccess`) |
| the wait on native event targets (`selected_wait` on a provider) | `await native_events.wait(ctx, condition)` on `handoff['detail']['native']['event_target']` |
| `ProgressInformationCredit` over `progress_snapshot_v1` with a provider | `job_progress.progress_information(records, baseline_refs, fields, information_unit)` over held check rows |
| nothing | the expectation of each check in the estimate table: `expect` before the status request, `resolve` after it |
| return: snapshots, free `record` fields, a qualification text | return: `credit`, `finding` (boolean, state from the job service's vocabulary, Unix seconds), `check_refs`, and selectable `{'known', 'value'}` measurements and record references |
| the model request: old-runner text, the assignment three times, the controller's internals | the request the first test of `test_monitor_units.py` prints: purpose, the actions offered now and what each does, what earns credit; the job once; no controller internals |

The model is the router. It picks one defined action with controlled arguments; code carries it out through the
job services. No monitor runs a command the model wrote. A handoff record of the library that carries
`'monitor_operation': 'exec_command'` is a legacy label: the monitor does not read such a record and does not act
on the label. It acts only on job ledger rows.

Shared library (already written, do not copy it): `episode_support/jobs/job_progress.py` (`FIELDS`, `LOG_NAMES`,
`JOB_STATES`, `status_reading`, `check_view`, `check_facts`, `held_checks`, `progress_information`,
`check_expectation`, `check_resolution`) and `episode_support/jobs/job_records.py`. System: `JobAccess.window` in
`episode_runtime/job_access.py`.

## Steps for one monitor (folder `M`, its commissioner's folder `P`)

Delete the old path first (the `BLOCKED-ON-JOB-SERVICE` functions, the snapshot readers, the provider imports), then
write each file from the A104 file of the same name. The files are private copies: copy the A104 file into `M` and
change what the table below names. Do not import from A104.

1. `M/goal.py`: copy; set `BINDING_PATH` to the monitor's own path. Keep the sentences of that axis's old goal that
   carry a decision, in the owner's wording.
2. `M/messages/read_from_parent.py`: copy unchanged (the form `monitor_assignment_v2`).
3. `M/messages/internal_summary.py`: copy unchanged.
4. `M/credit.py`: copy unchanged. The per-axis `grading/<axis>/progress_information_credit.py` is no longer
   imported by the monitor; leave the library file.
5. `M/task.py`: copy; change `CHECK_KIND` to the axis (`'A101 job progress check'`, ...) and the `action_transport`
   import to the one the monitor already used (table below). `SERVICES` is `('job_access', 'estimate_table',
   'native_events')`; `TOOLS` is the four `progress_*` functions. Remove the imports of `progress_provider`,
   `selected_wait`, `LaunchInstructions`, `ToolKnowledge`, `extend_context`, `time_accounting`, the record
   `domain` schemas and `deepcopy`.
6. `M/messages/msg_to_child.py`, `M/messages/read_from_child.py`, `M/messages/final_to_parent.py`,
   `M/yield_estimator.py`, `M/episode.py`: copy; in `yield_estimator.py` keep the monitor's own controller name
   and settings; `episode.py` keeps the monitor's own class name.
7. `M/tests/`: delete the old `test_binding_form.py` assertions on the old forms and the `BLOCKED` test; copy the
   three A104 test files (`test_binding_form.py`, `test_monitor_units.py`,
   `test_branch_execution_progress_assessment_model_run.py`) and change the package path, the class name and
   `CHECK_KIND`. The model-run test's last case (the head commissions the monitor) uses the axis's own head world;
   drop that case where the head has no stepping world yet and say so in the report.
8. `P/messages/msg_to_child.py`: the function that builds the monitor's assignment (table below) returns the new
   assignment: `{'version': 'monitor_assignment_v2', 'handoff_refs': [the held handoff row], 'known_progress_refs':
   [the held check rows of that job], 'dependency_handoff_refs': [...], 'requested_fields': [...],
   'information_unit': ...}`. The handoff row is one the commissioner holds: the launch child returned it in a
   `record_refs` field (`execution_handoff_refs`) or the commissioner's own commissioner passed it. Remove
   `monitoring_progress_refs`, `monitoring_progress_snapshots`, `monitoring_execution_state` and every other
   `monitoring_*` name from the selection: `credit`, `finding` and `check_refs` are always returned; the selectable
   fields are `job_returncode`, `job_duration_seconds`, `job_elapsed_seconds`, `stdout_bytes`, `stderr_bytes`,
   `log_window_refs`, `event_receipt_refs`.
9. `P/messages/internal_summary.py`: add `'outstanding_jobs': outstanding_jobs(view.records)`
   (`episode_support/jobs/job_records.py`); `msg_to_child` finds the job's handoff and check rows there
   (`job['handoff_ref']`, `job['record_refs'][1:]`), as `_monitor` of the A104 head does.
10. `P/messages/read_from_child.py`: where it read `monitoring_progress_refs` or snapshots from the monitor's
    result, read `finding` and `check_refs`. `P/task.py`: where the model is offered the monitor, its arguments are
    a held handoff reference (an `enum` of `summary['outstanding_jobs']` references), `requested_fields` and the
    return fields; no assignment the model writes.
11. Run: `M/tests` offline (15 tests in A104), then the model-run file with `-m model_run`; then the commissioner's
    own tests.

Settings of a monitor (its entry of `continuation`): `cost` (the cost of one action in units of `information_unit`;
also the cost of a check in the estimate table) and `parameters` (`uncertainty_alpha`). The A104 tests use
`information_unit` 1.0, `cost` 0.2 and `uncertainty_alpha` 0.05: in the stepped test, after one informative check,
the accumulation controller stops the Episode at the seventh action that earns nothing (at `cost` 0.001 at the
eleventh); in the real model runs it stopped after five to seven. A wait is an action of the length the model
gives it, spent inside the monitor; the request says so.

## The monitors

`ES` is `gene_annotation_episode/episodic_workflow/episode_support`; paths are below
`gene_annotation_episode/episodic_workflow/root/`.

| Axis | Monitor folder `M` | `action_transport` import in `M/task.py` today | Commissioner `P` and its function for the monitor | Notes |
|---|---|---|---|---|
| a101 | `a101/sequence_homology_evidence/execution_progress_assessment` | `ES/model_exchange/sequence_homology_evidence/action_transport` | `a101/sequence_homology_evidence/messages/msg_to_child.py`: `_monitor(arguments, summary)`, `MONITOR_VERSION`, `required = ('monitoring_progress_refs',)` | old tools: observe, read, log; `SERVICES = ('job_access',)` |
| a102 | `a102/structural_homology_evidence/execution_progress_assessment` | `ES/model_exchange/strict_output` | `a102/structural_homology_evidence/messages/msg_to_child.py`: `monitor(chosen, units, summary)`, `MONITOR_VERSION` | imports `ES/jobs/service_calls/structural_homology_evidence/progress_provider` and `ES/jobs/waiting.selected_wait`: both go; the old wait tool becomes `progress_wait` |
| a103 | `a103/gene_context_evidence/execution_progress_assessment` | `ES/model_exchange/gene_context_evidence/action_transport` | `a103/gene_context_evidence/messages/msg_to_child.py`: the selection `('monitoring_progress_refs',)` and the assignment passed on unchanged | old tools: observe, read, log |
| a105 | none | | | not applicable |
| a106 | `a106/perturbation_evidence/execution_progress_assessment` | `ES/model_exchange/perturbation_evidence/action_transport` | `a106/perturbation_evidence/messages/msg_to_child.py`: `monitor(arguments, summary)`, `MONITOR_VERSION`, `REQUIRED['monitor']` and the summary-informing selection (`monitoring_progress_snapshots`, `monitoring_execution_state`, `monitoring_result_available`) | imports `progress_provider`, `selected_wait`, `forms/perturbation_evidence/communication.plain`: all go |
| a107 | `a107/partner_presence_evidence/execution_progress_assessment` | `ES/model_exchange/strict_output` | `a107/partner_presence_evidence/messages/msg_to_child.py` (the monitor's return fields are listed there under `'monitor'`: replace the list by the new selectable fields) | imports `progress_provider`, `selected_wait`, `communication.plain`: all go |
| a110 | `a110/biochemical_feasibility_evidence/execution_progress_assessment` | `ES/model_exchange/strict_output` | `a110/biochemical_feasibility_evidence/messages/msg_to_child.py`: `MONITOR_VERSION`, the forced `monitoring_progress_refs` | imports `progress_provider`, `selected_wait`: both go |

The same recipe applies to the nested copies, each a private episode with its own binding path and its own
commissioner (`hpc_work_planning` or `hpc_allocation_execution`), which is step 8's `P`:

- `a102/structural_homology_evidence/hpc_work_planning/execution_progress_assessment` and
  `.../hpc_work_planning/hpc_allocation_execution/execution_progress_assessment`;
- the same two folders under `a103/gene_context_evidence`, `a104/evolutionary_history_evidence`,
  `a107/partner_presence_evidence` and `a110/biochemical_feasibility_evidence`.

The two nested A104 copies were not ported with the A104 monitor.

## What a monitor of another route needs

`job_progress.status_reading` reads the reply of a route by the route's `kind` (`READINGS`: `local`, `pbs`, `api`).
A route of a further kind needs its reading added there, with a real test, before a monitor can check a job of it;
without one the check fails with `KeyError(kind)`. The wait is offered only where the handoff's `native` names an
`event_target` (local jobs).

### A job of the API route (19 November 2026; the A101 monitor is the worked example)

- **The reading.** `READINGS['api']` holds the four `MEASUREMENTS` (all unknown: a web service reports no return
  code, duration, elapsed time or log) and `PROVIDER_MEASUREMENTS`: `provider_status` (the service's own word,
  for NCBI BLAST `WAITING`, `READY`, `FAILED`, `UNKNOWN`) and `has_hits` (`None` until the job finished). The
  state is the route's (`WAITING` is `queued`, `READY` is `finished` with `result_available` true). `check_view`
  shows every measurement the reading holds; the provider's status and `has_hits` count as facts (`FACTS`).
- **A check the provider's spacing does not permit yet** is not sent: `job_access.check` returns `{'status':
  'failed', 'failure': {'code': 'provider_spacing_required', 'detail': {'action', 'sent': False,
  'retry_after_seconds', 'earliest_at'}}}` and writes no row. The monitor's unit returns it as its outcome; it
  earns nothing and its expectation in the estimate table stays open.
- **What such a job has.** `job_progress.LOGS` names the logs of a job by route kind (`LOG_NAMES` for `local` and
  `pbs`, none for `api`). The A101 monitor puts `log_names` into its summary's `job` and offers `progress_log`
  only when the commissioner asked for log windows and the list is not empty (`task.offered`,
  `task.selection_schema`). The other monitors still offer `progress_log` for a job of any kind (their `task.py`
  uses `LOG_NAMES`): each needs the same three lines before it is handed an API job.
- **The request.** The A101 monitor writes the check's description and the credit rule for the job's kind
  (`task.JOB_KINDS`) and, for an API job, shows `seconds_between_status_requests` with the job (read in `decide`
  from `job_access.read('describe', resource_id)['poll_spacing_seconds']`).
- **An ended API job is answered from the route's record**, with the time it was first observed, so a second check
  of it in the same Episode writes the same check row again. The A101 monitor therefore calls a check informative
  when the information credit of its held rows rose (`progress_observe`), not when the row is among the
  contributions; the other monitors' `progress_observe` still use the second rule.
- Tests: `episode_support/jobs/tests/test_api_job_route.py` (the reading on real replies of the protocol test
  service; a copied workspace) and the A101 monitor's `tests/test_monitor_api_job.py` (queued, refused by the
  spacing, finished, failed, unknown; two visits; a still-waiting visit ended by its controller).
