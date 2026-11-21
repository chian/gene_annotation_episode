# bvbrc_blast: a child episode of the A101 head (BLAST through the BV-BRC application service)

Written 2026-11-20. Pattern: the shared job-child shape (`LIB/tools/similarity_search/sequence_homology_evidence/bvbrc_job_child.py`). This episode searches one protein query against a precomputed
BV-BRC database with the `Homology` application of the BV-BRC application service, on the owner's account, through an
authenticated route of the job service. Its actions are the owner's (below).

## What exists, and what is written (step zero)

| Function (file) | What exists and is called | What is new, and why an existing one could not be used as is |
|---|---|---|
| `BvbrcJobRoute` (`jobs/bvbrc_job_route.py`) | `BVBRCAnalysisClient` (transport: login from the environment variable `authorization_env`, sent only to the configured origins), `prepare_rpc_request`, `decode_rpc_response`, `parse_task_records`, `parse_workspace_records`, `prepare_application('Homology', ...)` (retained definition), `parse_sequences`, from `ApiJobRoute` (subclassed; every contacting method replaced, `_send` made unreachable): `spacing`, `_contact`, `_directory`, `_recorded`, `_publish`, `wait`; `JobAccess` calls it | the route protocol over this service: submit = `Workspace.ls /` (the login's home) + `Workspace.create` (one folder per job) + `AppService.start_app2`; status = `AppService.query_tasks`; results = `Workspace.ls` of the result folder; read = `Workspace.get_download_url` + `download`. The public route sends no credential and is not changed. `api_bvbrc_appservice.py` (per-axis copies) is the old selected-call service with effect reservation and publication, not a job route: not used; I did not edit any file under another axis's name. The state map (`queued`, `pending`, `running`, `in-progress`, `completed`, `failed`, `deleted`) is a private name in the gene_context copy of that service, so it is written again here (7 entries). |
| registration (`jobs/job_services.py`) | the `remote` list of the other people's uncommitted `api` change | one optional key `bvbrc`; **this file carries the other people's uncommitted `api` change and is NOT committed by me** |
| `record_estimate`, `launch_search`, `monitor_search`, `fetch_and_grade_search` (`tools/.../bvbrc_blast_search.py`) | `JobAccess.launch/check/fetch`, `wait_for_job`, `EstimateTable.expect/resolve/kind_statistics`, `database_blast_search`: `search_facts`, `timing`, `seconds_until_allowed`, `failure_code`, `now_text`, `seconds_between`, `_failed`, `_ended`, `_observations`; `grade_blast_result` (database mode), `retain_tool_grading`, `SEARCHES`, `progress_information` | `database_blast_search.submit_search` / `check_search` / `fetch_and_grade_search` are specific to the public service (job fields read by `checked_analysis_kind`, handle-keyed estimates, report name, database name, one-handoff `search_view`); the estimate is now its own earlier action (own key), so the status request resolves that key |
| the five checks (`check_estimate`, `check_launch`, `check_fix`, `check_monitor`, `check_extract`), `check_commission`, `episode_state`, `search_view` (latest handoff) | the pattern of the checks of `database_blast_search` (a library module kept for its helpers) | new conditions below; `search_state` of the public module knows one handoff and no fix |
| `credit.py`, `yield_estimator.py` | `progress_information`, `AccumulationYieldController` | units: estimate held, handoff, new status facts, graded |
| the head's wiring | `selection_schema`, `child_option`, `CHILD_SLOTS`, `COMMISSIONS`, `COMMISSION_CHECKS`, `SELECTABLE`, `CHILD_DESCRIPTIONS`, `_custody` | entries of its own (the head's `bvbrc_searches` view of held searches came with parking, below) |

## Actions

Owner: "okay, so you must make this kind of controlled. one child with 6 actions. make estimate/reason, [must be gated on
having made an estimate] launch job, fix mistakes/reason, monitor/update estimate, extract results"

Owner: "I think we can work on that in one loop first and then we can practice the detaching while monitoring (i.e., come
back to this process later or wait overall) after we get these basic forms down"

Built (the five things named; a sixth may be added later): `estimate`, `launch`, `fix`, `monitor`, `extract`. No `hold`.
A repeat commission of the same query, program and database is refused (it would submit again), unless it continues a
search that is outstanding (parking, below).

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
1. The head's model is offered `reason` and `bvbrc_blast` (not `pairwise_blast`: one held sequence) and commissions `bvbrc_blast` with blastp, bacteria-archaea, resource `bvbrc`.
2. The child: `estimate` first (basis `no_earlier_measurement`: the table is new; the number is the model's guess), then
   `launch` (accepted after about 30 s of spacing sleeps inside the unit), then `monitor` two to four times (queued or
   running, then finished: the one outside run took about 2 minutes), `extract` (graded: 300 hits, features with no function rows).
   State `extracted`.
3. The estimate table: one resolved search of the kind `bvbrc_blast:bvbrc_homology:bacteria-archaea:blastp` whose duration is
   the first observation of `finished` (about 120 to 180 s).
4. No file of the run, the workspace, the journal or the model-call folders contains `sig=` followed by hex.

## Names of the hits: multistep extract (owner's instruction, 2026-11-20)

Owner: "there are other bv-brc functions that will get names for you, perhaps you need to add those to the episode and make
that part of the multistep grading". `extract` stays one action and one unit; inside it: fetch the report, look up the hits in
BV-BRC's public Data API, grade with the result as reference metadata, keep the records. No model step in between.

- Hit id to feature id (verified live, 300 of 300 hits): the report's description has `accession` `<genome_id>.peg.<n>` and `id`
  `gnl|fig|<genome_id>.peg.<n>`; the Data API's `genome_feature` `patric_id` is `fig|<accession>`.
- Requests (`bvbrc_hit_metadata.py`, calling `encode_native_query` and `BVBRCDataClient.query_prepared`; public, NO login sent,
  none was refused): `genome_feature` by `patric_id` in batches of 100 (fields `patric_id`, `feature_id`, `product`,
  `annotation`, `pgfam_id`, `plfam_id`, `genome_id`, `taxon_id`, `aa_length`, `aa_sequence_md5`), `protein_family_ref` by
  `family_id` (`family_type`, `family_product`), `genome` by `genome_id` in batches of 100 (`genome_name`, `taxon_id`),
  10 s apart (7 requests for all 300 hits). How many hits are named is set by `bvbrc_hit_metadata.name_hits`: batches of 100 in the order of the per-hit value,
  stopping when a batch adds no new product and moves no candidate's score by more than 0.01 (`bvbrc_msa_episode.md`, follow-on 1). `genome_name` is not a `genome_feature` field of the registry, hence the third collection.
  Lineage nodes need a rank, which the genome record does not give: no lineage is supplied.
- The grader's metadata row (legacy association, `blast_database_grader._attach_metadata`: matched on `accession` and the native
  `taxid`; a differing taxon is refused as `metadata_taxon_conflicts_with_native`): `{'accession', 'taxid', 'source', 'functions':
  [{'function', 'source', ...}], 'origin' (dict)}`; optional `lineage`, `assembly`, `sequence_group`, `study_groups`. The
  registry's `_import_blast` (`tools.py`) joins no metadata at all: the join is the grader's.
- Terms (BV-BRC to this project): `product` = the hit's function (name); `annotation` = who assigned the name, kept as the
  function row's `source`, never as a function or label; `patric_id` = accession (with `fig|`); `pgfam_id` / `plfam_id` = the
  cross-genus and genus-level family ids. The stored responses (an artifact of the unit, with its source of provider
  `bvbrc_data`) keep BV-BRC's field names, and each function row carries `bvbrc_feature` and `bvbrc_families` with them.
- `annotation` on the live service: over the 300 hits of the stored report only the value `PATRIC` came back and no feature id
  came back twice (checked outside a run, `runs/bvbrc_meta_probe_1`). If one did, the record whose `annotation` sorts first as
  text is taken (a stated rule, independent of arrival order) and `duplicate_feature_ids` counts it.
- A hit with no metadata is counted as missing by `metadata_accounting` (`covered_count`, `missing_accessions`), never as a hit
  with no function; a data request that fails leaves its hits without rows and is counted.
- The reference records of the hits take the product as label (a copy of the report with titles set is given to the shared
  `_observations`; the stored report and the grading are not changed).
- Estimate table: one expectation per launch, written by `launch` just before the submission (the `estimate` action records
  nothing on the table: a revised estimate, or one made when no launch can follow, leaves no row).

Prediction, run C (`runs/bvbrc_a101_run_C1`, fresh workspace `runs/bvbrc_a101_ws_C`, same estimate table; 4th submission):
1. The head commissions `bvbrc_blast`; the child's estimate is `learned_from_earlier_searches` near 76 s (median of 66.4 and
   85.5); `launch`; one or two `monitor`; `extract` takes about 70 to 80 s longer than before (7 data requests, 10 s apart).
2. The Store accepts the source of provider `bvbrc_homology`.
3. The sheet's `functions` has one row, `RecA protein`, with `supporting_group_count` about 300 (the hits are distinct
   accessions), `groups_without_function` 0, the metadata accounting 300 of 300, 7 data requests, no failure; the top hits are
   RecA proteins of Enterobacterales with `PGF_00047078` and a genus-level `PLF_...` family.
4. The estimate table gains one row for this launch (open until resolved, then resolved) and none from the repeated `estimate`
   actions after the extract.

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
   9 units). Child credit 4.0 (estimate 1, handoff 1, finished fact 1, graded 1). Predicted two to four monitors:
   not as predicted (the search was faster than the first wait: 66.4 s from submission to the first observation of `finished`,
   the earlier outside run took about 110 s).
3. The estimate table: the kind `bvbrc_blast:bvbrc_homology:bacteria-archaea:blastp` got the resolution 66.443147 s
   (outcome `finished`). The five estimate repeats after the extract read it (`learned_from_earlier_searches`, 66.443147 s).
4. Token search: no file of any run directory, workspace, journal or model-call folder holds `sig=` followed by hex
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
duration of the second search resolved at 85.452264 s. 

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
- A search still running when the child's controller winds the child down did not occur: not verified.

### Run C: the names of the hits (`runs/bvbrc_a101_run_C1`, workspace `runs/bvbrc_a101_ws_C`, journal `journal_C1.sqlite3`, report `report_C1.json`)

4th `Homology` submission (4 of 6 used). Predicted against observed:
1. As predicted: commission of `bvbrc_blast`; estimate `learned_from_earlier_searches`, 76 s (the model rounded the median
   75.95); `launch`; two `monitor` (11 s: `running`; 61 s: `finished`); `extract`; five `estimate` repeats; `yield_stop` at 10
   units; child credit 5.0 (estimate, handoff, running, finished, graded). The duration measured and recorded: 87.169109 s.
2. The Store admitted the extract with the source of provider `bvbrc_homology` (the coordinator's change of `state.py` worked at
   its first run).
3. The finding's identification: one function row, `RecA protein`, `supporting_group_count` 300, `groups_without_function` 0,
   `conditional_weight` 1.0, `max_bit_score` 717.613, `unannotated_fraction` 0.0; `metadata_hit_count` 300,
   `metadata_covered_count` 300, `data_request_count` 7, no failed data request, none refused (the Data API was used without the
   login). Annotation: only `PATRIC` came back and no feature id twice (the rule for a duplicate was not needed).
4. The estimate table gained ONE row for this launch (expectation 76 s, resolved 87.169109 s, `finished`), one open
   `<kind>:remaining` row from the first monitor, and none from the five estimate repeats (earlier open rows of runs A and B stay).
   The data lookups added about 70 s to the extract unit as predicted.

Top five hits by bit score (all 717.613; accession, product, `pgfam_id`, `plfam_id`, genome):
`300267.13.peg.3478` RecA protein PGF_00047078 PLF_620_00002096 (Shigella dysenteriae Sd197);
`511145.12.peg.2790` RecA protein PGF_00047078 PLF_561_00001771 (E. coli K-12 MG1655);
`556266.3.peg.1936` RecA protein PGF_00047078 PLF_561_00001771 (Shigella sp. D9);
`685038.3.peg.2689` RecA protein PGF_00047078 PLF_561_00001771 (E. coli O83:H1 NRG 857C);
`585057.6.peg.2993` RecA protein PGF_00047078 PLF_561_00001771 (E. coli IAI39). The reference records of the hits carry the accession
and the product as label.

What would let code call two hits "the same candidate" (over these 300 hits, `bvbrc_data` artifact of the run):
- `pgfam_id` (cross-genus family): the same value, `PGF_00047078`, for all 300: it says "the same protein family", not a duplicate.
- `plfam_id` (genus-level family): 53 distinct values; 15 hits have none (empty string): not usable alone.
- `aa_sequence_md5`: 251 distinct values among 300 hits: 49 hits repeat another hit's exact protein sequence. This is the
  exact-identity key. The sheet still reports `sequence_identity_unresolved: true` and counts 300 groups, because no
  `sequence_group` is supplied to the grader (the legacy association joins hits only by accession). Supplying it (for
  example `md5:<hash>`) would merge to 251 groups; not done, since it changes the sheet's counts and is the owner's choice.
- `genome_id` / `taxon_id` differ for every hit (300 genomes), so organism alone does not merge hits.

No `sig=` followed by hex in any file of runs C1, `bvbrc_a101_ws_C`, the estimate table or the data probes.

## The global estimate ledger (owner's next step 1), first wiring

One ledger file for every run: `resources/estimate_ledger.sqlite3` (outside version control, outlasts runs). It was
seeded with the three measured searches of runs A, B and C (their own keys, times and durations, with the job facts
they had: BV-BRC Homology, blastp, bacteria-archaea, query length 353). A launch now writes the job's facts into its
ledger row (`job`: service, program, database, query length); the status requests no longer write `:remaining` rows
(the revised remaining time stays in the unit's outcome), so the ledger holds one row per launch. The estimate action
is shown `duration_trend` of the kind (`episode_support/jobs/duration_trend.py`): how many were measured, the 10th,
50th and 90th percentile seconds, the latest durations newest first, and, once at least five searches of at least two
query lengths are measured, a least-squares line of seconds against query length with what it gives for this query.

### Run D1: prediction (written before the run)

Target: E. coli K-12 cold shock protein CspA (UniProt P0A9X9, 70 residues), a different size from RecA; fresh
workspace `runs/bvbrc_a101_ws_D`; the services file names the global ledger.
1. The child's first estimate has the basis `learned_from_earlier_searches` and rests on the ledger: about 85 s
   (the trend shows 3 measured, typical 85.45 s, latest 87.17, 85.45, 66.44; no size line yet).
2. `launch` writes exactly one ledger row, carrying `query_length` 70. One or two monitors; the measured duration
   is between 60 and 90 s (not known: a shorter query against the same database).
3. `extract`: products are cold shock proteins; because the Csp family has several paralogues, more than one
   product name is expected among the hits (unlike RecA, where all 300 were one product).
4. Afterwards the ledger holds 4 measured searches and no open row; the trend has two query lengths and still no
   line (fewer than five searches).

### Run D1: observed (`runs/bvbrc_a101_run_D1`, workspace `runs/bvbrc_a101_ws_D`)

1. As predicted: the first estimate was 85.45 s with the basis `learned_from_earlier_searches`; the decision showed
   the ledger's trend (3 measured, typical 85.45 s, latest 87.17, 85.45, 66.44, no size line).
2. As predicted: one ledger row for the launch, with `query_length` 70. Two monitors. NOT as predicted: the search
   measured 96.14 s (predicted 60 to 90): the shorter query was not faster.
3. As predicted: more than one product among the hits. Of the 100 hit records read: 58 "Cold shock protein of CSP
   family => CspB/CspG/CspI", 15 "... => CspA", 14 "Cold shock protein of CSP family", 12 "... => CspC", 1
   "hypothetical protein".
4. As predicted: the ledger holds 4 measured searches, no open row, one kind; the trend has two query lengths and
   no line. The ten repeat `estimate` units of the wind-down wrote nothing to the ledger.

### Run E1: prediction (written before the run)

Target: E. coli K-12 RNA polymerase subunit beta, RpoB (UniProt P0A8V2, 1342 residues): a third query length, so
that the ledger reaches five measured searches of three lengths and the size line can be fitted. Fresh workspace
`runs/bvbrc_a101_ws_E`, the global ledger. This is the sixth Homology submission.
1. The first estimate has the basis `learned_from_earlier_searches`, about 86 s (4 measured, typical 86.31 s, no
   line yet).
2. One ledger row for the launch with `query_length` 1342. The duration is not predictable from the ledger (the 70
   residue query took longer than the 353 residue ones): between 80 and 150 s.
3. `extract`: the products are RNA polymerase beta subunits, essentially one product.
4. Afterwards the ledger holds 5 measured searches of 3 query lengths and the trend carries `size_fit` (the
   least-squares line of seconds against query length).

## Parking and resuming (owner's instruction, 2026-11-20; "park" is the word)

Owner: "figure out how to "release" (dangerous word since it can be used multiple ways---find a better one) this child to run
in background while other pieces of the episodic workflow can do other work (i.e., bounce a waiting notice/info back up to
parent with about how long we expect to wait so parent can choose what to do next. it could just wait, it could send off
another tool, it could go all the way back up to root with the same info)".

Design (no action added; the rule that the head finishes a parked job is the system's, below):
- The commission has `until`: `launched` (estimate, launch, then the child returns: it parks) or `extracted` (follow the search
  to its result; also how a parked search is resumed).
- The child's credit is bounded: four units, each once and only when new in this commission: an estimate held
  (`information_unit`), the search launched (`handoff_unit`, once however many launches a fix needed), the search known ended
  (`information_unit`: the first status that shows finished, failed or lost; queued or running earns nothing) and the graded
  result (`graded_unit`). The target (`read_from_parent`) is the sum of the units obtainable under `until`: `launched` -> estimate
  + handoff; `extracted` -> all four, less what passed-back records hold (no estimate and handoff when a handoff is passed back;
  no ended-unit when a passed-back status already shows it ended). `credit.py` counts each term under exactly the same
  condition as the target term, so the credit cannot exceed it: on the fix path (a failed launch, a fix, a second launch) the
  estimate is counted once (any completed estimate unit), the handoff once (any completed launch unit), the ended unit once
  (any new status row that shows ended), so a second launch adds nothing. `until: launched` with a passed-back handoff is
  refused (target 0).
- Controller: `CompletionYieldController`, cost = `settings['cost']` (0.5) times the smallest unit of the commission: always below
  the target (which the controller requires) and below the one-unit credit still missing before the target, so it does not stop
  early on forecast; it stops at the target at once (exact zero remaining credit). A search that keeps running, or failed at the
  service, leaves the target unreached; the controller then winds the child down.
- Resume: the head's `held_searches` view of the job rows of kind `bvbrc`; its commission check admits a
  continuation (same query, program, database, resource, `until` extracted) and refuses a second submission; `msg_to_child` passes
  back, in custody, the handoff, status and closure records and `known_ended`; the child rebuilds its state from them
  (`resumed_rows`: the estimate recorded with the launch and the launch, and the state the latest status shows), so the launch
  and estimate checks refuse. The ledger row of the launch is resolved by the first status that shows it ended.
- Wait notice (the child's return when it ends with the search launched and not extracted): `parked`, `seconds_since_launch`
  (to the latest thing the child knew: the launch or its latest status), `estimated_seconds` and `expected_remaining_seconds`
  (estimate minus seconds since launch, not below zero; if a status came with a revised remaining time, that later fact).
  The head's model also sees `bvbrc_searches` with the seconds since the launch and the seconds still expected as of each of its
  own decisions, and its own return carries `waiting_searches` (slot, seconds since launch, expected remaining seconds) beside
  `outstanding_handoff_count`, with the handoff and status records in its selectable lists.
- The head finishes every job it parks (owner's decision, 2026-11-21: "the head must finish parked jobs"; it replaces "it could go
  all the way back up to root with the same info"). `HEAD/task.py` `resume_action`: while a child's BV-BRC job is parked
  (outstanding in `bvbrc_searches`, `bvbrc_msa_jobs` or `bvbrc_metacats_jobs`) it returns the resume, the job's own commission
  again with `until` extracted (`resume_commission`; it passes the head's check, else it raises), `due` once the job's expected
  remaining seconds (the estimate recorded with the launch minus the seconds since the launch at the decision's recorded time)
  have passed; the earliest launched due job first, else the earliest launched. The system (`method_loop/episode_type.py`,
  `forecast_yield_controller.md`): the head does not stop while a job is parked; once the job is due its resume is the only action
  offered and is taken without the model; before then the model may choose other work worth its cost, and when none is, the
  resume is taken instead of stopping; the forecast gate never refuses that resume. The child descriptions say so (`PARKED_TEXT`)
  and do not say whether to park.
- The head's forecast (2026-11-21, `forecast_yield_controller.md`): the unit of a commission whose child returned parked is
  pending (`HEAD/credit.py` `outcome_pending`): its rise (0, nothing extracted) is not learned as `bvbrc_blast`'s share and its
  seconds (the launch only) are not its unit seconds, in the run's own history or in the ledger (row resolved `pending`); the
  resuming commission is the observation. While a search is outstanding its ceiling stays the search's (the continuation
  extracts what the launch started; only a closed search gives 0), the head's check accepts only the continuation (same query,
  program, database, resource, `until` extracted; `until` launched is refused with
  `a_continuation_follows_the_search_to_its_result`), and the `bvbrc_blast` row shown to the model names it as
  `best_arguments` (`bvbrc_blast_best`). Found in the real run `runs/a101_goal7_ws_reca` (RecA, `until launched`): the parked
  unit's 0 made the resume not worth it (forecast 1.79 < threshold 2.09), the head stopped with the search outstanding and the
  RecA product never became a candidate; under the pending rule (direct check, not a real run) the resume row is forecast 3.589
  over 355.4 s (threshold 2.132), worth it, with `best_arguments` the continuation. Under the rule that the head finishes parked
  jobs (direct check, not a real run, `runs/parked_rule_check_2`, the run's journaled histories): at `call-00004` (search launched
  1.3 s before, estimate 35.9 s) the resume is owed, not due, and every action stays offered (`reason`, `hmmer_profile_scan`,
  `bvbrc_blast`); 1 s after the estimate has passed only `bvbrc_blast` is offered and its resume is the unit; after the scan
  `must_continue` is true and the controller does not stop, and with the controller as the run learned it (no pending rule:
  nothing worth its cost) the resume is taken in place of the stop and passes the gate as the owed resume (as a model choice the
  gate refuses it: 1.794 < 2.089).

### Run E1: observed (`runs/bvbrc_a101_run_E1`, workspace `runs/bvbrc_a101_ws_E`)

1. As predicted: the first estimate was 86.31 s, learned from the ledger.
2. One ledger row with `query_length` 1342; one monitor. NOT as predicted: the search measured 66.3 s (predicted
   80 to 150): the longest query was the fastest so far.
3. As predicted: one product, "DNA-directed RNA polymerase beta subunit (EC 2.7.7.6)", on all 100 hit records read.
4. As predicted: 5 measured searches of 3 query lengths, and the trend now carries the line:
   seconds = 89.74 - 0.0191 x query length (64.1 s for 1342 residues, 83.0 s for 353, 88.4 s for 70). The model's
   estimates after the extract used it (64.12 s). The slope is negative and small: over these five searches the
   query length explains little of the duration (three searches of the same length took 66.4, 85.5 and 87.2 s). The
   trend therefore also gives the median distance of the measured durations from the line
   (`typical_distance_seconds`), added after this run.

### Run P1: prediction (written before the run)

Query: E. coli K-12 chaperone protein DnaK (UniProt P0A6Y8, 638 residues: a fourth query length). Fresh workspace
`runs/bvbrc_a101_ws_F`, run `runs/bvbrc_a101_run_P1`; local and BV-BRC resources bound (no NCBI); the global ledger
(`resources/estimate_ledger.sqlite3`); the head's settings carry `profile_databases` (Pfam-A) so the head has
`hmmer_profile_scan` to send off. Homology submissions for this step: at most three; this run uses one.
1. The head's model is offered `reason`, `hmmer_profile_scan` and `bvbrc_blast` (and not `pairwise_blast`: one sequence). I do not
   predict `until`: the description says what each means and does not recommend. If it chooses `extracted` the run is a
   one-loop run (valid); then a second run follows in which the park path is taken, if the model ever takes it.
2. If `until` is `launched`: the child's units are `estimate` (learned, near 90 s with the ledger's trend) and `launch`, then it
   ends at once (credit 2.0 = the target, `yield_stop`, 2 units, no wind-down), returning the notice: `parked`, `seconds_since_launch`
   about 0, `estimated_seconds` about 90, `expected_remaining_seconds` about 90. The head is shown it in `child_reports` and
   `bvbrc_searches`. The head's next choice is not predicted (another tool, or the resuming commission).
3. The resuming commission (same query, program, database, resource, `until` extracted) passes the handoff and status records back;
   the child's state is `launched`; its units are `monitor` (one or two, wait at least the minimum, the search takes about 90 s) and
   `extract` (about 70 s longer for the 7 data requests); target 2.0 (ended + graded), `yield_stop` at the extract, no wind-down.
   The Homology service sees ONE job folder for this query; the ledger has one row for the launch, resolved with the measured
   duration (about 90 s, from the submission to the first `finished` status).
4. The identification names `Chaperone protein DnaK` (a single product or a few close variants of it).

### Run P1: observed (`runs/bvbrc_a101_run_P1`, workspace `runs/bvbrc_a101_ws_F`, journal `journal_P1.sqlite3`, report `report_P1.json`)

Submission 1 of 3 for this step. The head's model first sent off `hmmer_profile_scan` (Pfam-A, local), then commissioned `bvbrc_blast`
with `until: extracted`: a valid one-loop run, not the park path. Child: `estimate` (78 s, learned), `launch`, one `monitor` (wait 90 s: `finished`),
`extract` (300 hits, 300 of 300 metadata, 7 data requests): 4 units, credit 4.0 = the target, `yield_stop` exactly at the extract (no
wind-down unit; the completion controller did what it was built for). 2 head units, 6 model calls.
The model did not park. What in the description led it there: the description said what each `until` means but nothing that made
waiting cost anything; the head had also already used its other tool, so the work left was the search itself. The description now says
(a fact of the system, not a recommendation) that while a child runs the head does nothing else.

### Run P2a: prediction (written before the run)

Query: E. coli K-12 GroEL (UniProt P0A6F5, 548 residues), fresh workspace `runs/bvbrc_a101_ws_G`, run `runs/bvbrc_a101_run_P2a`; the head's
tools and the ledger as in P1; the description of the child as amended. I do not predict the model's `until`. If it parks: the child
ends at the launch (2 units, credit 2.0), the head's model then does something (not predicted), a resuming commission continues
the same search (one job, one ledger row) with the target 2.0 and ends at the extract. If it chooses `extracted` again: that is
reported as the model not parking.

### Run P2a: observed (`runs/bvbrc_a101_run_P2a`, workspace `runs/bvbrc_a101_ws_G`, journal `journal_P2a.sqlite3`, report `report_P2a.json`)

Submission 2 of 3 for this step. The model parked this time (with the amended description): `bvbrc_blast` with `until: launched`.
- Child 1: `estimate` (83 s, learned), `launch`; 2 units, credit 2.0 = the target, `yield_stop` at the launch, no wind-down unit. The
  return: `state launched`, `parked true`, `seconds_since_launch 0.0`, `estimated_seconds 83`, `expected_remaining_seconds 83.0`, with the
  handoff record.
- The head's model then sent off `hmmer_profile_scan` (Pfam-A, local; about 22 s), then commissioned `bvbrc_blast` again with the same query,
  program, database, resource and `until: extracted` (the resumption), about 28 s after the launch (model-call times).
- Child 2 (resumed): `monitor` (wait 60 s, expected remaining 55: `finished`), `extract` (300 hits, 300 of 300 metadata, 7 data requests): 2 units,
  credit 2.0 = the target (ended + graded), `yield_stop` at the extract, no wind-down. No second submission: one job folder
  (`job_fe0c02496d9e6d44e9bf832c7e7e63f8`) and one ledger row (query length 548) resolved with 93.671343 s (`finished`); the ledger holds 7
  measured searches and no open row.
- 3 head units; 7 model calls (the cold one-loop
  runs: B1 12, C1 11, D1 16, P1 6 calls); wall time from the first to the last model call 136 s (B1 264 s, C1 341 s, D1 356 s,
  P1 172 s). The one-loop runs lost most of their time to the repeated estimate units after the extract, which the completion
  controller has removed (P1 has none); the park path also overlapped the scan with the search.

### Run P2b: goal and setting

Goal: the head ends while the search is parked, and a later head run resumes the SAME search. Query: E. coli K-12 elongation factor Tu
(UniProt P0CE47, 394 residues), fresh workspace `runs/bvbrc_a101_ws_H`, run `runs/bvbrc_a101_run_P2b`. The head's yield setting (`cutoff`) of
that date was set above its credit's maximum, so that its estimator stopped it after its first unit (a setting of the run, not a choice of the
model: the model's `until` is its own). Submission 3 of 3 (the last). The return visit (`runs/bvbrc_a101_run_P2c`, the same workspace): the
commission passes the returned records in `evidence_refs`; the head's `bvbrc_searches` shows the search outstanding with the seconds since its
launch; its model commissions `bvbrc_blast` with `until: extracted`; the child's first `monitor` shows `finished`, then `extract`; one job
folder and one ledger row, resolved.

### Run P2b: observed (`runs/bvbrc_a101_run_P2b` ... `P2b7`, workspace `runs/bvbrc_a101_ws_H`)

NOT achieved: no head run ended while a search was parked, so the return visit (P2c) was not made. The head's cutoff was 2.0, so each
head run ended after its first unit; the model's first choice was `hmmer_profile_scan` in P2b, P2b2, P2b3, P2b5 and P2b7 (no search; P2b7
was stopped by me before any submission: no job folder, no ledger row) and `bvbrc_blast` with `until: extracted` in P2b4 and P2b6, each
a complete one-loop run (4 units, credit 4.0 = target, head credit about 1). So with the cutoff the model parked in none of the six
attempts; in P2a (normal cutoff) it did.

**Submission count for this step: 4, one over the limit of 3** (P1, P2a, P2b4, P2b6). Cause: my retry loop stopped only on a parked
search (`outstanding_handoff_count` 1) and not on a search that ran to its result, so P2b4's submission (a one-loop search) was not caught
before P2b5 and P2b6 ran. The ledger holds 9 measured searches of 5 query lengths (70, 353, 394 twice, 548, 638, 1342, ...) and no open row.

What is not exercised: the head's own return carrying `waiting_searches` and the handoff and status records, and a later head run resuming
a search from records passed back in `evidence_refs` (the head's `held_searches` view and `msg_to_child` were exercised only inside one
head run, P2a); a resumed search whose status already shows it ended (`known_ended`); a launch that fails and the `fix` path under the
completion controller; a search that keeps running until the controller winds the child down.
