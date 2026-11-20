# bvbrc_blast: a child episode of the A101 head (BLAST through the BV-BRC application service)

Written 2026-11-20. Pattern: `database_blast_episode.md`. This episode searches one protein query against a precomputed
BV-BRC database with the `Homology` application of the BV-BRC application service, on the owner's account, through an
authenticated route of the job service. Its actions are not those of `database_blast` (owner's decision below).

## What exists, and what is written (step zero)

| Function (file) | What exists and is called | What is new, and why an existing one could not be used as is |
|---|---|---|
| `BvbrcJobRoute` (`jobs/bvbrc_job_route.py`) | `BVBRCAnalysisClient` (transport: login from the environment variable `authorization_env`, sent only to the configured origins), `prepare_rpc_request`, `decode_rpc_response`, `parse_task_records`, `parse_workspace_records`, `prepare_application('Homology', ...)` (retained definition), `parse_sequences`, from `ApiJobRoute` (subclassed; every contacting method replaced, `_send` made unreachable): `spacing`, `_contact`, `_directory`, `_recorded`, `_publish`, `wait`; `JobAccess` calls it | the route protocol over this service: submit = `Workspace.ls /` (the login's home) + `Workspace.create` (one folder per job) + `AppService.start_app2`; status = `AppService.query_tasks`; results = `Workspace.ls` of the result folder; read = `Workspace.get_download_url` + `download`. The public route sends no credential and is not changed. `api_bvbrc_appservice.py` (per-axis copies) is the old selected-call service with effect reservation and publication, not a job route: not used; I did not edit any file under another axis's name. The state map (`queued`, `pending`, `running`, `in-progress`, `completed`, `failed`, `deleted`) is a private name in the gene_context copy of that service, so it is written again here (7 entries). |
| registration (`jobs/job_services.py`) | the `remote` list of the other people's uncommitted `api` change | one optional key `bvbrc`; **this file carries the other people's uncommitted `api` change and is NOT committed by me** |
| `record_estimate`, `launch_search`, `monitor_search`, `fetch_and_grade_search` (`tools/.../bvbrc_blast_search.py`) | `JobAccess.launch/check/fetch`, `wait_for_job`, `EstimateTable.expect/resolve/kind_statistics`, `database_blast_search`: `search_facts`, `timing`, `seconds_until_allowed`, `failure_code`, `now_text`, `seconds_between`, `_failed`, `_ended`, `_observations`; `grade_blast_result` (database mode), `retain_tool_grading`, `SEARCHES`, `progress_information` | `database_blast_search.submit_search` / `check_search` / `fetch_and_grade_search` are specific to the public service (job fields read by `checked_analysis_kind`, handle-keyed estimates, report name, database name, one-handoff `search_view`); the estimate is now its own earlier action (own key), so the status request resolves that key |
| the five checks (`check_estimate`, `check_launch`, `check_fix`, `check_monitor`, `check_extract`), `check_commission`, `episode_state`, `search_view` (latest handoff) | the pattern of `database_blast_search.check_*` | new conditions below; `search_state` of the public module knows one handoff and no fix |
| `credit.py`, `yield_estimator.py` | `progress_information`, `AccumulationYieldController` | units: estimate held, handoff, new status facts, graded |
| the head's wiring | `selection_schema`, `child_option`, `CHILD_SLOTS`, `COMMISSIONS`, `COMMISSION_CHECKS`, `SELECTABLE`, `CHILD_DESCRIPTIONS`, `_custody` | entries beside `database_blast`'s; no summary view of held searches (one loop, nothing is passed back) |

## Actions

Owner: "okay, so you must make this kind of controlled. one child with 6 actions. make estimate/reason, [must be gated on
having made an estimate] launch job, fix mistakes/reason, monitor/update estimate, extract results"

Owner: "I think we can work on that in one loop first and then we can practice the detaching while monitoring (i.e., come
back to this process later or wait overall) after we get these basic forms down"

Built (the five things named; a sixth may be added later): `estimate`, `launch`, `fix`, `monitor`, `extract`. No `hold`,
no later-visit path: the head commissions the child once and passes nothing back; a repeat commission of the same query,
program and database is refused (it would submit again).

- `estimate` {program, database, expected_seconds, basis}: no search is running or waiting for a fix; program/database fit the
  query; seconds in range; `basis` agrees with the learned statistics (`learned_from_earlier_searches` only when the table
  has resolved searches of that kind). Records the expectation in the estimate table before any launch. May be repeated
  (also after the result is extracted: the one action then left, earning nothing).
- `launch` {program, database, resource_id}: GATED: an estimate is held (`estimate_required`, take first `estimate`), for
  this program and database; the resource is a bvbrc service; no search running/finished/extracted; the first request is the
  commission's; after a failure only after a `fix`, with a request that differs from the failed one in the fixed field.
- `fix` {failure_code, field} (offered only in state `failed`): the code is the last failure's; the field is one of the
  request's.
- `monitor` {handoff_ref, wait_seconds, expected_remaining_seconds}: a search is launched and not known to have ended; the
  wait is within [minimum, 1800 s] (minimum = what the spacing needs, 60 s per job, 10 s between contacts, plus a 1 s margin);
  while not finished the revised remaining time is recorded (a new expectation of kind `<kind>:remaining`, left open); the
  first request that shows the search ended resolves the launch's estimate with the measured duration.
- `extract` {handoff_ref}: the latest monitor shows finished with results; not already held. Fetch and grade in one unit; the
  sheet, one reference per hit and one comparison observation per alignment are kept (the head's credit reads them).

States: no_estimate, estimated, launched, finished, extracted, failed. The wait range's upper end (1800 s) is the size of one
wait the model may choose, not a limit on the search.

## Verified against the live service (2026-11-20; the route driven once outside a run, `runs/bvbrc_route_check_1*`, `runs/bvbrc_route_poll_1`)

- Endpoints `https://p3.theseed.org/services/app_service` and `.../Workspace`. The login's home workspace is the one
  workspace named `home` that the login owns in the listing of `/` (`Workspace.ls`); the user name is read from it at run time.
- The one folder written in the owner's home workspace: `gene_annotation_episode_a101` (created once by a one-off check);
  one subfolder per search (the job handle).
- Precomputed protein database: `db_type` `faa`, `db_source` `precomputed_database`, `db_precomputed_database`
  `bacteria-archaea` (reference and representative bacterial and archaeal genomes; source: `BV-BRC/homology_service`
  `HomologySearch.pm` and `databases.json`, and run). The report names `search_target.db` as
  `/vol/blastdb/bvbrc-service/data.2022-0916/ref/bacteria-archaea.features.faa`; 23,897,466 sequences. No other value was
  run; none is offered. The deployed definition (`enumerate_apps`) has no hit-list parameter; the service reports 300 hits.
- Result files in `<output_path>/.<output_file>/`: `blast_out.archive`, `blast_out.raw.json` (BLAST 2.15.0+, `-outfmt 15`: a
  `BlastOutput2` list of one report, hit ids `gnl|fig|<genome>.peg.<n>`, titles empty), `blast_out.json` (the same reports as a bare list,
  the service's "processed" file), `blast_out.metadata.json` (`{}` here), `blast_out.txt`, `blast_headers.txt`.
  `blast_out.raw.json` is exactly what `parse_blast_json` takes (`grade_blast_result`, database mode: 300 hits, 300
  sequence groups, no function labels, `blast_database_sheet_v1`). `blast_out.json` is not (a list, not an object): the extract
  fetches the raw file. The BV-BRC reader and grader (`bvbrc_homology_inputs`, `bvbrc_homology_grader`) need caller-built
  bindings and metadata and give no retained correspondence, which the head's credit reads: not used; this is the difference.
- Duration of the one outside run: submitted 23:21:08, started 23:22:05, completed 23:22:58 (UTC); first observed finished
  140 s after the submission (polls 70 s apart).

## Predictions

Run A (`runs/bvbrc_a101_run_A1`, workspace `runs/bvbrc_a101_ws_A`: the target only, E. coli K-12 RecA P0A7G6, 353 aa):
1. The head's model is offered `reason` and `bvbrc_blast` (not `pairwise_blast`: one held sequence; not `database_blast`: no
   `api` resource is bound) and commissions `bvbrc_blast` with blastp, bacteria-archaea, resource `bvbrc`.
2. The child: `estimate` first (basis `no_earlier_measurement`: the table is new; the number is the model's guess), then
   `launch` (accepted after about 30 s of spacing sleeps inside the unit), then `monitor` two to four times (queued or
   running, then finished: the one outside run took about 2 minutes), `extract` (graded: 300 hits, features with no function rows).
   Child credit about 1 (estimate) + 1 (handoff) + 2 or 3 (new facts) + 1 (graded) = 5 or 6; then a few `estimate` repeats
   (no credit) until the controller stops it; state `extracted`.
3. The head's credit is above 0 after the return: the hits cover the whole query (identical RecA proteins of E. coli
   genomes), so near 1 (above 0.9); the head's estimator then ends it.
4. The estimate table: one resolved search of the kind `bvbrc_blast:bvbrc_homology:bacteria-archaea:blastp` whose duration is
   the first observation of `finished` (about 120 to 180 s).
5. No file of the run, the workspace, the journal or the model-call folders contains `sig=` followed by hex.

## Observed

`Homology` submissions made: 3 in total (the one outside run `runs/bvbrc_route_check_1*` task 24003087; run A2; run B1).
Folders written in the owner's BV-BRC home workspace: `gene_annotation_episode_a101` and one subfolder per submission (3);
nothing else was written, deleted or changed. Spacing kept: 10 s between contacts (inside the route), 60 s or more per job.

### Run A (`runs/bvbrc_a101_run_A1` failed at link; `runs/bvbrc_a101_run_A2`, resumed as `runs/bvbrc_a101_run_A2r`;
workspace `runs/bvbrc_a101_ws_A`, journal `journal_A2.sqlite3`, report `report_A2.json`)

1. Head offered `reason` and `bvbrc_blast`: as predicted; its first and only decision was the commission of `bvbrc_blast`
   (blastp, bacteria-archaea, `bvbrc`). Predicted.
2. Child: `estimate` (basis `no_earlier_measurement`, 180 s), `launch` (accepted), ONE `monitor` (wait 60 s, expected remaining
   120 s: it showed `finished` already), `extract` (graded: 300 hits, 300 comparison observations, 0 unprojected), then five
   `estimate` repeats (the model's choice; the one action left; no credit), then the controller stopped it (`yield_stop`,
   9 units). Child credit 4.0 (estimate 1, handoff 1, finished fact 1, graded 1). Predicted two to four monitors and credit 5 or
   6: not as predicted (the search was faster than the first wait: 66.4 s from submission to the first observation of `finished`,
   the earlier outside run took about 110 s).
3. The head's credit after the graded return: 0.99999998 (comparison_count 300, one region, no uncovered region): predicted
   above 0.9, observed. Its estimator ended it after that one unit.
4. The estimate table: the kind `bvbrc_blast:bvbrc_homology:bacteria-archaea:blastp` got the resolution 66.443147 s
   (outcome `finished`). The five estimate repeats after the extract read it (`learned_from_earlier_searches`, 66.443147 s).
5. Token search: no file of any run directory, workspace, journal or model-call folder holds `sig=` followed by hex
   (`grep -rlaE 'sig=[0-9a-f]{16,}'` over every `runs/bvbrc_*`: 0 files). The name `KB_AUTH_TOKEN` appears (services file, journal).

Defects found and fixed in this run: (a) the continuation file must name the settings of every child slot of the head, also
the one that is not bound (`LinkError`); (b) `extract` raised `ContractError: native_blast_requires_native_tool_source`
(`gene_annotation_episode/state.py` line 1155 admits an observation with native BLAST rows only from a source of provider
`ncbi_blast`): the source now carries provider `ncbi_blast` with accession `bvbrc_homology`, which `graded_rows` and the credit
read. The failed run was resumed (`resume`, replay of the recorded units, the extract unit run again): no new submission.
Needed change outside my files: `state.py` could name a provider set instead of the one name.

### Run B (`runs/bvbrc_a101_run_B1`, workspace `runs/bvbrc_a101_ws_B`: a fresh workspace, the estimate table of run A)

Prediction written after A and before B: the model's first estimate is learned from A (basis `learned_from_earlier_searches`,
66.4 s); the second search measures near 60 to 130 s; the next learned value is the median of the two.
Observed: first estimate `learned_from_earlier_searches`, 66.443147 s (the measured duration of A, as predicted); `launch`;
`monitor` (wait 11 s: `running`), `monitor` (wait 61 s: `finished`), `extract` (300 hits), six `estimate` repeats (75.95 s,
the median of 66.44 and 85.45), `yield_stop`, 11 units, child credit 5.0 (estimate, handoff, running, finished, graded). The measured
duration of the second search resolved at 85.452264 s. Head credit 0.99999998 again.

### Refusals (direct calls of the checks, NOT a real run: `runs/bvbrc_refuse_check_1`; no service contacted)

`launch` without an estimate: `estimate_required`; launch on a local resource: `resource_is_not_a_bvbrc_service`; estimate
basis `learned_from_earlier_searches` with no measured search: `basis_does_not_match_the_learned_statistics`; estimate of 0 s:
`expected_seconds_out_of_range`; launch while launched: `search_already_launched`; extract before the handoff exists:
`no_search_held`, while launched: `search_not_known_to_be_finished`; monitor with a wait below the minimum:
`wait_seconds_out_of_range`; launch after a failure without a fix: `fix_required_after_the_failure`; fix with a wrong code:
`is_not_the_last_failure`; fix with nothing failed: `nothing_to_fix`; the same request again in the fixed field:
`repeats_the_failed_request_in_the_fixed_field`; a repeat commission: `search_already_commissioned`; a commission on a local
resource: `resource_is_not_a_bvbrc_service`. The model made no wrong request in a real run; the failure paths (`fix`, a failed
launch, a failed search) were not exercised against the service: not verified in a run.

### Surprises and open points

- The service answered faster than the hours-long public queue: 66 to 110 s for a 353-residue query over 23.9 million proteins.
- Hit titles are empty in the report (`blast_out.metadata.json` is `{}`): the sheet has no function labels (`functions` empty).
- The repeated `estimate` actions after the extract leave open expectation rows in the estimate table (they never resolve);
  `<kind>:remaining` revision rows stay open as well.
- A search still running when the estimator stops the child (the later "detaching" case) did not occur: not verified.
