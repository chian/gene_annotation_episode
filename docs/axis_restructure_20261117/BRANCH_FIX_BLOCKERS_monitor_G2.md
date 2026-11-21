# BRANCH_FIX_BLOCKERS_monitor_G2: the monitor port of A106, A107 and A110 (19 November 2026)

Scope: the top-level monitors `root/a106/perturbation_evidence/execution_progress_assessment`,
`root/a107/partner_presence_evidence/execution_progress_assessment` and
`root/a110/biochemical_feasibility_evidence/execution_progress_assessment`, ported by `MONITOR_PORT_RECIPE.md` as
private copies of the A104 monitor, and steps 8 to 10 of the recipe in their three heads. No file of
`episode_support/` or `episode_runtime/` was edited. Runs: `runs/mong2_1` to `runs/mong2_12`.

## 1. Missing library members (not written here: the library is not this port's)

1. **`job_progress.READINGS` has no reading for the route kind `api`.** Run on a real job of `ApiJobRoute` (the
   BLAST URL test service of `episode_support/jobs/tests/blast_url_api_server.py`) handed to the A106 monitor
   (`runs/mong2_11`, a probe file outside the repository):
   - the first request shows the job (`resource_kind: 'api'`, `launch_estimates: null`) and offers
     `progress_observe` and `progress_log`; no wait (the handoff names no event target);
   - a check the provider's spacing does not permit yet is the returned outcome `failed`
     (`provider_spacing_required`, `retry_after_seconds` in the failure detail), one unit, no check row;
   - a check the route answers raises `KeyError('api')` in `job_progress.status_reading`; the run ends with it
     (`journal.run_failure`: `KeyError: 'api'`).
   Wanted in `episode_support/jobs/job_progress.py`: `READINGS['api']`, a function of the route's status reply that
   returns `{'returncode': None, 'duration_seconds': None, 'elapsed_seconds': None, 'outputs': []}` (the state and
   the availability of results already come from the route's status), with a real test on the test service. The
   monitors need no change for it.
2. **`progress_log` is offered for a job of any route; `job_progress.LOG_NAMES` is `stdout.log`, `stderr.log`.** A
   job of the API route has no such file (its files are its results). Not run: what
   `job_access.window(ctx, handoff_ref, 'stdout.log', ...)` returns for an API job. Wanted: the log names of a job
   by route kind (a member of `job_progress`, or of the handoff row), so that a monitor offers `progress_log` only
   where the route keeps a log.
3. **`api_job_route.PROTOCOLS` holds one protocol, `ncbi_blast`.** The jobs of A106 are BV-BRC application-service
   jobs. No protocol object exists for them, so no A106 job can be launched on a route; "Not provided yet" item 3 of
   `LAUNCH_MONITOR_EXTRACT_MECHANICS.md` stands for A106.

## 2. A106: how far the monitor is ported, and what is left

- Ported as far as the recipe goes without an API route: the ten files, the four defined actions, the credit, the
  return, the request. It runs on local jobs and on the remote (login-mode) route, as the A104 monitor does.
- Not reachable from A106's own work: `execution_job_submission` and its only route child `api_job_execution` of
  A106 still raise `BLOCKED-ON-JOB-SERVICE`; no A106 episode writes a job ledger handoff row. The jobs the A106
  monitor was run on were launched by the job services' test episode `job_probe`.
- Left, in this order: the BV-BRC protocol object of the API route (item 1.3); the `api` reading (item 1.1); the
  port of the A106 launch onto `job_access.launch`. Then the monitor checks an A106 job without a change of its own.

## 3. The three heads

Changed in each head (recipe steps 8 to 10): `messages/msg_to_child.py` builds `monitor_assignment_v2` from one job of
`summary['outstanding_jobs']` (the held handoff row and the check rows held of it); `messages/internal_summary.py`
adds `outstanding_jobs`; `task.py` offers the monitor only while a job is outstanding, with a held handoff reference
(an `enum`), `requested_fields` (an `enum`) and the return fields as its arguments.

1. **None of the three heads can be stepped to a decision in a world**, so the model-run case "the head commissions
   the monitor" of the A104 test file was dropped in all three: A106 (`internal_summary` reads the finding progress
   through `project_finding_progress`, which opens `read_snapshot` on the reader), A107 (`decide` reads the declared
   services `tool_catalog` and `tool_library`, which nothing implements), A110 (the first unit `decide` names is the
   lookup `process_entry`, which raises). In its place each monitor's `tests/test_monitor_units.py` runs the head's
   own `msg_to_child` on the rows of a real job (`job_records.outstanding_jobs` over the records of an Episode that
   holds the handoff row and a check row) and links the monitor on that commission. The heads' `internal_summary`
   line and their `task.py` offer were not run in a world.
2. **The A107 and A110 heads still pass text the model wrote to their other children** (`objective` and `purpose` in
   `msg_to_child` of every slot but the monitor). Only the monitor commission was made controlled (the objective
   names the job by its handle; the message is empty). The A106 head already used fixed objectives.
3. **A107: `information_unit` is an optional field of the head's own assignment** (`assignment.get(
   'information_unit')`). A head commissioned without it builds a monitor assignment whose `information_unit` is
   `None`, which the monitor's form (a number) does not take. Not run and not changed.
4. **`root/a107/partner_presence_evidence/tests/test_binding.py::test_the_selectable_names_are_the_names_the_child_
   declares[hpc]` fails** on the return fields of `hpc_work_planning` (`BRANCH_FIX_BLOCKERS_a107.md`, section 4). It
   failed before this port and is not the monitor's.

## 4. Local launches refused while other agents run local jobs (test world, not the monitors)

The two-job test (`test_a_dependency_the_commissioner_passes_is_offered_and_its_commission_passes_its_handoff_row`)
failed twice at its second launch and passed in every other run of it:

| Run | Launch outcome of the second job |
|---|---|
| `runs/mong2_3` | `local_job_boundary_unavailable`, `reason: service_did_not_initialize` |
| `runs/mong2_4` | `local_resource_busy`: the reservation view lists a unit `gene-local-job-*.service` as `untracked_running` with the whole budget as its allocation (`available: 0`) |
| `runs/mong2_2`, `_5`, `_7`, `_9`, `_12` | handed off |

Both refusals come from `gene_annotation_episode/native_lifecycle.py` and `local_resources.py` (not edited). The
launch is a returned `failed` outcome of `job_probe`; the test helper `started_job` then has no `handoff_ref`. Runs
`runs/fixrace_*` of another agent work on this.

## 5. Limits carried unchanged from the A104 monitor (`BRANCH_FIX_BLOCKERS_a104.md`)

No time-remaining estimate and no score of the earlier estimate (item 1 there); `launch_estimates` is shown to the
model as the launch wrote it (item 6); the reading of a batch job's scheduler reply has never run (item 5).

## 6. Not ported

The nested copies `hpc_work_planning/execution_progress_assessment` and
`hpc_work_planning/hpc_allocation_execution/execution_progress_assessment` of A107 and A110 (A106 has none). Their
commissioners are the HPC planning episodes.

## 7. Left in place, no longer imported by these monitors

`grading/<axis>/progress_information_credit.py`, `jobs/service_calls/<axis>/progress_provider.py` and
`jobs/waiting.selected_wait` for the three axes. `docs/EVIDENCE_AXIS_LEDGER.md` and the table of
`MONITOR_PORT_RECIPE.md` were not edited.
