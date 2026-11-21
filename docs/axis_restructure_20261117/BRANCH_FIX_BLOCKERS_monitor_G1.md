# BRANCH_FIX_BLOCKERS_monitor_G1: the monitor port of A101, A102 and A103 (19 November 2026)

Scope: the top-level monitors `root/a101/sequence_homology_evidence/execution_progress_assessment`,
`root/a102/structural_homology_evidence/execution_progress_assessment` and
`root/a103/gene_context_evidence/execution_progress_assessment`, ported by `MONITOR_PORT_RECIPE.md` as private
copies of the A104 monitor, and steps 8 to 10 of the recipe in their three heads. No file of `episode_support/` or
`episode_runtime/` was edited. Runs: `runs/mong1_b0` (the requests before the port), `runs/mong1_1` to
`runs/mong1_12`, `runs/mong1_p1` (the API probe).

## 1. Missing library members (not written here: the library is not this port's)

1. **`job_progress.READINGS` has no reading for the route kind `api`.** The jobs of A101 are BLAST jobs of
   `ApiJobRoute`. Run on a real job of that route (the BLAST URL test service of
   `episode_support/jobs/tests/blast_url_api_server.py`, launched by `job_probe`) handed to the A101 monitor with
   `blast_status_target: true` (`runs/mong1_p1`, a probe file outside the repository):
   - the first request shows the job (`resource_kind: 'api'`, `launch_estimates: null`) and offers
     `progress_observe` and `progress_log`; no wait (the handoff names no event target);
   - a check the provider's spacing does not permit yet is the returned outcome `failed`
     (`provider_spacing_required`, `retry_after_seconds` in the failure detail): one unit, no check row;
   - the check the route answers raises `KeyError('api')` in `job_progress.status_reading`; the run ends with it
     (`journal.run_failure`: `KeyError: 'api'`).
   So the A101 monitor cannot check a job of A101's own kind. Wanted in `episode_support/jobs/job_progress.py`:
   `READINGS['api']`, a function of the route's status reply that returns `{'returncode': None,
   'duration_seconds': None, 'elapsed_seconds': None, 'outputs': []}` (the state and the availability of results
   already come from the route's status), with a real test on the test service. The monitor needs no change for
   it. (The same member is item 1.1 of `BRANCH_FIX_BLOCKERS_monitor_G2.md`.)
2. **`progress_log` is offered for a job of any route; `job_progress.LOG_NAMES` is `stdout.log`, `stderr.log`.** The
   request of 1.1 offers `progress_log` for the API job, which keeps no such file. Not run: what
   `job_access.window` returns for it. Wanted: the log names of a job by route kind.
3. **No time-remaining estimate and no score of the earlier estimate**, as for A104 (`BRANCH_FIX_BLOCKERS_a104.md`,
   item 1): the three monitors record and resolve the expectation of each check in the estimate table and compute
   no remaining-time distribution.

## 2. A101: one field more than the A104 copy

The old A101 monitor completed its visit after one BLAST status observation (`blast_monitor_yield`; in the carried
`yield_estimator.py` the completion controller with the information unit as its target). The controller is chosen
from the parent input, and `read_from_parent` is handed no record, so the commissioner states it:
`blast_status_target` (a boolean) is a field of A101's `monitor_assignment_v2`. Four files of the A101 monitor
therefore differ from the A104 files beyond the path: `messages/read_from_parent.py` (the field),
`yield_estimator.py` (completion controller when it is true, accumulation otherwise; controller name `monitor`),
`messages/internal_summary.py` (each dependency carries the flag, read from its handoff row: kind `api`, native
service `ncbi_blast`) and `messages/msg_to_child.py` (the dependency's commission passes it). The A101 head reads
the flag from the held handoff row in its `internal_summary` (`_outstanding`).

Run: on a local job with the flag given by the test, the controller stops the Episode at the first informative
check (`test_a_blast_status_target_is_complete_after_its_first_informative_check`). Not run: the same on a BLAST
job, because of item 1.1.

## 3. The three heads (recipe steps 8 to 10)

Changed in each head: `messages/msg_to_child.py` builds `monitor_assignment_v2` from one job of
`summary['outstanding_jobs']` (the held handoff row and the check rows held of it) with a fixed objective and an
empty message; `messages/internal_summary.py` adds `outstanding_jobs`; `task.py` offers the monitor only while a
job is outstanding, with a held handoff reference (an `enum`), `requested_fields` (an `enum`) and the return fields
as its arguments; `messages/read_from_child.py` reads the monitor's finding and check rows.

1. **No head has a field for the rows of an outstanding job**, in its assignment form or in its return form. In
   the tests the handoff row reaches the head through a `record_refs` field meant for other records (A101:
   `scope_refs`; A103: `evidence_refs`). A head that ends with a job outstanding returns nothing that names it
   (design section 8). This is the heads' own work.
2. **A101 head.** While this port ran, another agent rebuilt the head's commissions on the same pattern
   (`commission_fields`, `offered_children(summary, resources)`, `tests/test_commissions.py`); the monitor's
   commission and `_monitor` are kept there. Four tests of that new file fail offline with an
   `AcquisitionError` of a library tool (`runs/mong1_11`); they are not the monitor's.
3. **A102 head cannot be stepped to a decision in a world** (`tests/test_decision_schema.py` says why: its
   `internal_summary` reads the finding progress through `project_finding_progress`, which opens `read_snapshot`
   on the reader). The model-run case "the head commissions the monitor" was dropped for A102. In its place
   `test_monitor_units.py` runs the head's `offered_children`, `child_arguments` and `msg_to_child` on the rows of
   a real job (`job_records.outstanding_jobs` over the records of an Episode that holds the handoff row and a
   check row) and links the monitor on that commission. The head's `internal_summary` line and the offer inside
   its `decide` were not run in a world.
4. **The A102 and A103 heads still pass text the model wrote to their other children** (`goal` and `purpose`, or
   `objective` and `purpose`, in `msg_to_child`). Only the monitor commission was made controlled.
5. **A103: the monitor's `information_unit` is the head's setting** `child_values['execution_progress_assessment']`.
   A run whose settings lack it builds an assignment the monitor's form refuses (`assignment_missing_field`); the
   commission fails with that error. `a103_world` sets no `child_values`; the tests add it.
6. **A103: the head's operands are JSON text the model writes** (`arguments_json`). For the monitor they are
   admitted against a closed form in `monitor_operands` (a held handoff reference, fields and measurements of
   fixed sets; anything else is rejected with feedback). The other children's operands are as before.

## 4. Not ported, not run

- The nested copies under `hpc_work_planning/` of A102 and A103 (two each): not in this scope.
- Every job of these tests was launched by the job services' test episode `job_probe` (local route, and the remote
  route through a local shell). No run here monitored a job launched by an episode of A101, A102 or A103.
- The reading of a batch job's scheduler reply (`pbs`, `Exit_status`) has not run: no PBS scheduler exists where the
  tests run (`BRANCH_FIX_BLOCKERS_a104.md`, item 5).
- The library files the old monitors imported and the new ones do not (`grading/<axis>/progress_information_credit.py`,
  `jobs/service_calls/structural_homology_evidence/progress_provider.py`, `jobs/waiting.selected_wait`) were left as
  they are. Whether a library record of these axes still carries the label `'monitor_operation': 'exec_command'`
  was not examined; the monitors read job ledger rows only and offer no action that runs a command.

## 5. Items 1.1 and 1.2 are done (19 November 2026, later the same day)

- 1.1: `job_progress.READINGS['api']` exists (`provider_status`, `has_hits` beside the four measurements); the A101
  monitor checks a job of `ApiJobRoute`. Run offline on the BLAST URL test service: queued, a check the provider's
  spacing refuses (`provider_spacing_required`, a failed unit, no row), finished, failed, unknown, two visits of a
  BLAST status target (`tests/test_monitor_api_job.py`), and with the real model on a job of the public NCBI
  service (`tests/test_branch_api_job_monitor_model_run.py`).
- 1.2: `job_progress.LOGS` names a job's logs by route kind; the A101 monitor offers `progress_log` only for a job
  that has logs. The A102 and A103 monitors (and the other copies) still use `LOG_NAMES` for every job: see
  `MONITOR_PORT_RECIPE.md`, "A job of the API route".
- Section 2, "Not run: the same on a BLAST job": run now
  (`test_two_visits_of_a_blast_status_target_return_queued_and_then_finished`).
