# BRANCH_FIX_BLOCKERS_monitor_api_G2: the API-job changes of the A101 monitor in six more monitors (19 November 2026)

Scope: the top-level monitors `root/<axis>/<head>/execution_progress_assessment` of A102, A103, A104, A106, A107 and
A110. Each got the changes the A101 monitor got (`MONITOR_PORT_RECIPE.md`, "A job of the API route"), as a private
copy: `goal.py`, `task.py`, `messages/internal_summary.py` and a new `tests/test_monitor_api_job.py`. No file of
`episode_support/` or `episode_runtime/` was edited. The nested copies under `hpc_work_planning` were not touched.
Runs: `runs/monapi_1` to `runs/monapi_15`.

After this change two sentences of `MONITOR_PORT_RECIPE.md` ("The other monitors still offer `progress_log` for a
job of any kind", "the other monitors' `progress_observe` still use the second rule") hold only for the nested
copies. That file was not edited here.

## 1. Missing library members (not written here: the library is not this change's)

1. **`job_wait.wait_for_job` makes its status request without the caller's reading.** It calls
   `job_access.check(ctx, handoff_ref)` with no `assess`, so the check row it writes has `assessment: None`. A
   monitor reads every held check row of its job with `job_progress.check_view` and `check_facts`
   (`internal_summary`, `credit`), and both take the row's `assessment` as a mapping when `measurements` is among
   the requested fields (`view.update(row['detail']['assessment'])`, `name in reading`). The first summary after a
   wait would raise `TypeError`. Read from the code; not run. Wanted: `wait_for_job(ctx, handoff_ref, *, seconds,
   assess=None)` that passes `assess` on to `job_access.check`. The monitor would pass
   `job_progress.status_reading`.
2. **No way to leave a held check row out of the information credit.** `WAIT_ACTION.md` says a wait earns
   nothing and "where a check row earns credit, do not count the wait's row". In a monitor every held check row
   outside the baseline earns credit when it shows a new fact (`job_progress.progress_information`). The only way
   to leave a row out is to name it in the baseline, and then its facts count as known. For an API job the status
   request the wait makes is the one the provider's spacing permits: the check after it is refused, or, once the
   job has ended, is the same row again. A visit that waited and found the job finished would return that state
   with credit 0. This needs the owner's decision between: (a) in a monitor the state read after a wait counts as
   a check and earns like one; (b) a monitor's wait makes no status request and the model checks afterwards, as
   `progress_wait` does today.
3. **The remaining time until the next permitted status request is not readable by a decision.**
   `job_access.read('describe', resource_id)` gives `poll_spacing_seconds` (the full spacing). The remaining
   seconds are known only from a refused check (`retry_after_seconds` in the failure detail);
   `ApiJobRoute.spacing` is not a member the route protocol offers to `job_access`. A wait "until the route's next
   permitted poll" can therefore be told only the full spacing, or the `retry_after_seconds` of the last refused
   check.
4. **A106's own service has no protocol.** `api_job_route.PROTOCOLS` holds `ncbi_blast` only. The jobs of A106 are
   BV-BRC application-service jobs: none can be launched on a route (item 1.3 of
   `BRANCH_FIX_BLOCKERS_monitor_G2.md` stands). The A106 monitor's by-kind offer and its API-job request were
   tested only on a BLAST job of the protocol test service (`episode_support/jobs/tests/blast_url_api_server.py`),
   as the A101 monitor's were. The request text of an API job names `provider_status` and `has_hits`, the two
   measurements `job_progress.READINGS['api']` holds; a BV-BRC protocol may measure other things.

## 2. The wait: what was found, and why none was added

- All six monitors (and A101) already offer `progress_wait` for a local job, while no end event of it was
  received. It waits for the job's end event or until `reconsider_after_seconds` have passed, whichever comes
  first (`native_events.wait`). It makes no status request, earns nothing, and the event's receipt comes into
  custody. This is a timed wait already, so no second wait was added for a local job.
- It is not in the form of `WAIT_ACTION.md`: its argument is `reconsider_after_seconds` (a number from 0, with no
  range from the settings), it is selected as `{'kind': 'tool', 'tool': 'progress_wait', 'arguments': {...}}`, and
  its runner is `native_events.wait`, not `job_wait.wait_for_job`. `WAIT_ACTION.md` names a runner that waits on a
  job event as the later replacement of the body of `wait_for_job` and says it is not built.
- For a PBS job and an API job no wait is offered: their handoff rows name no event target.
- `wait` in the form of `WAIT_ACTION.md` (`seconds` in the range of the setting `wait_seconds`, the runner
  `wait_for_job`) was not added to any of the six monitors, because of items 1.1 and 1.2. Nothing was stubbed.

## 3. Runs

| Run | What | Result |
|---|---|---|
| `runs/monapi_1` | before the change, offline: the request of each of the six monitors for an API job and for a local job | printed; the six API-job tests failed on the missing `log_names`, as expected; the six local-job tests passed |
| `runs/monapi_2` | after the change, offline: the whole `tests/` folder of each of the six monitors | 131 passed (20 real-model tests deselected) |
| `runs/monapi_3` | A102, real model, a running local job | passed: 7 decisions, ended by its yield controller, credit 1.0 |
| `runs/monapi_9` | A103, the same | passed: 7 decisions, credit 1.0 |
| `runs/monapi_10` | A104, the same | passed: 6 decisions, credit 1.0 |
| `runs/monapi_11` | A106, the same | passed: 6 decisions, credit 1.0 |
| `runs/monapi_4` (A103), `runs/monapi_12` and `runs/monapi_15` (A107) | real-model runs cut while they ran | `OSError: [Errno 122] Disk quota exceeded` on `/tmp` (the RAM disk that holds the repository and `runs/`), in the model provider's own files |
| `runs/monapi_5` (A104) | did not start | `sqlite3.OperationalError: disk I/O error` when the test's Store was created, at the same time |
| `runs/monapi_6` to `monapi_8`, `monapi_13`, `monapi_14` | did not start | the launcher ended with exit 120 or 1 and empty logs while `/tmp` reported its quota used up |

**Not done: the real-model run of A107 and of A110.** The two A107 attempts that started (`runs/monapi_12`,
`runs/monapi_15`) were cut by the disk quota of `/tmp`; no attempt for A110 started. Their offline tests passed in
`runs/monapi_2`. The two runs have to be made once `/tmp` has room. No job or process of these runs was left
running (checked after `runs/monapi_15`: no `gene-*` unit, the release file of each cut run exists). Nothing was deleted to
make room. The logs of the runs from `monapi_14` on, and a copy of this file, are in `runs/monapi_diag/` of the
disk checkout (`/home/chia/repos/gene_annotation_episode_disk`), because `/tmp` did not take them.
