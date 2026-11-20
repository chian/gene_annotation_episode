# database_blast: a child episode of the A101 head (hosted NCBI BLAST search)

Written 2026-11-20. Governs where it differs from `a101_tree.md` about this episode's leaves: `launch_api`, `monitor` and
`results` are not folders; they are the tools `submit`, `check` and `fetch_and_grade` of this one episode (each one shot,
each with one deterministic check of the model's JSON). `launch_hpc` stays an empty folder (cluster work later).

## What exists, and what is written (step zero)

| Function (file) | What exists and is called | Why it is not used as is / what is new |
|---|---|---|
| `submit_search` (`tools/similarity_search/sequence_homology_evidence/database_blast_search.py`) | `checked_analysis_kind` (declared against derived kind of the job `{program, database, hitlist_size, query_file}`), `JobAccess.launch` (handoff row, reply artifact, `estimates` kept in the row), `job_handle`, `ApiJobRoute` (one POST, spacing, intent file), `EstimateTable.expect` / `kind_statistics` | composition only; new: the duration prediction recorded before the submission and its resolution on a failed submission |
| `check_search` (same) | `wait_for_job` (the wait, then `JobAccess.check`), `ApiJobRoute.status`, `job_records.checks`, `EstimateTable.resolve` | `wait_for_job` makes the check without the monitor's `assess`: the check row's `assessment` is empty and `job_progress.progress_information` is used on the state and the availability only (`STATUS_FIELDS`); new: the seconds the spacing needs (`seconds_until_allowed`) and the duration measurement |
| `fetch_and_grade_search` (same) | `JobAccess.fetch`, `grade_blast_result` (database mode), `retain_tool_grading`, `native_correspondence.SEARCHES`, the source of provider `ncbi_blast`: exactly the old `blast_grade` | the old `blast_grade` was a separate model choice after a separate fetch; here fetch and grade are one unit |
| `check_submit`, `check_status_request`, `check_fetch_request`, `check_hold`, `check_commission` | nothing (the pairwise check `check_pairwise_request` is the pattern) | the conditions below |
| `search_view`, `search_state`, `search_facts`, `seconds_until_allowed`, `timing`, `graded_rows`, `held_searches` | `job_records` (`job_rows`, `checks`, `closure`), `saved_grading_features` (the database feature reader) | the readers of this episode's states |
| credit (`credit.py`) | `job_progress.progress_information` (one unit per check row that shows a fact the earlier ones did not, baseline = the parent's check records) | handoff and graded units |
| features of the return | `blast_database_features.grading_features` and its `SHEET_FEATURES`, `FUNCTION_FEATURES`, `MEANINGS` (the form is built from them) | nothing; `context_features` (taxonomy, source classes) is not sent up in this step |
| the head's wiring | the head's `selection_schema`, `child_option`, `offered_children`, `CHILD_SLOTS`, `COMMISSIONS`, `SELECTABLE`, `CHILD_DESCRIPTIONS` and `_custody` pattern of the earlier `msg_to_child` | entries added; the one new thing is `COMMISSION_CHECKS`, a table of one check per slot, so a later child is only entries |

Not used: the grader's `calculation_context`, `database_profile`, `target_context` and reference metadata (the design record
`database-search.md` says nothing supplies them yet): the sheet has hits but no function labels. The features therefore
report groups and E-values; `functions` is empty.

## Hosted databases (vocabulary)

The service documents `swissprot` and `core_nt` as the values of its `DATABASE` parameter
(https://blast.ncbi.nlm.nih.gov/doc/blast-help/urlapi.html, read 2026-11-20; the launch instruction entry `api-blast.md`
lists no database). Only those two are offered (`swissprot` protein, `core_nt` nucleotide); a name is added when the
documentation names it. Hit-list size 1 to 200 (the documentation: an integer above zero, default 100, no upper limit
stated; the upper bound is this episode's).

## The checks (each: the model's JSON and what the episode holds; problems as `{field, code, ...}`)

- `submit` {program, database, hitlist_size, resource_id}: the resource is a bound API service; every value equals the
  commission's; the program takes the query's molecule; the database holds what the program searches; the hit-list size
  is in range; no search is held (`search_already_held`); no submission failed before (`submission_already_failed_and_cannot_be_retried`).
- `check` {handoff_ref}: the handoff is the held search; the state is `outstanding` (not finished, not graded, not failed).
- `fetch_and_grade` {handoff_ref}: the handoff is the held search; the state is `finished` (the latest held check shows
  finished with results available).
- `hold` {reason}: the reason is the one the state gives (outstanding: `search_not_finished`; failed:
  `failure_not_retryable`; graded: `graded_result_established`); a finished or unsubmitted search has no hold.
- the head's commission {query_ref, program, database, hitlist_size, resource_id}: the query is a sequence of the scope; the
  program takes its molecule; the database fits the program; the size is in range; the resource is a bound API service;
  an outstanding search of the query is continued (same values, no other); a closed search is not commissioned again; a
  search whose child reported it failed is not commissioned again.

After a passed check a failure is the environment's: `failed`, one code of `FAILURE_CODES`, `retryable` false. The one
exception: the service's spacing refusal of a status request (nothing was sent): retryable.

## Credit and yield

Credit (from the records held, only what is new since what the parent passed back): `handoff_unit` for a handoff not passed
back; `information_unit` for each check row that shows a state or availability fact the earlier rows of the job did not;
`graded_unit` for a graded source not passed back. The head's `acquired_record_unit` is the graded unit, its
`handoff_unit` and `information_unit` the others.

Controller: `AccumulationYieldController`, cost 0.5 of a unit. Reason: the count of informative checks is not fixed by the
commission, so a completion controller (finite target; it raises when the credit passes the target) does not fit, and the
credit is not a bounded quality. The forecast falls with each unit that earns nothing, so a held, unfinished search ends
after several holds.

## Duration: predicted, run, measured, learned (the estimate table)

The file is `runs/a101_dbblast_estimates/table.sqlite3`, shared by every run of this note (outside the per-run directories).
Before `submit`: the expectation is recorded under the key of the job handle, of the kind
`database_blast:ncbi_blast:<database>:<program>`, with `duration_seconds` the median of the measured durations of that kind
(`kind_statistics`) or `None` with `duration_basis` `no_earlier_measurement` when none exists. The service's own estimate
(RTOE) is known only from its reply: it is kept in the handoff row and shown beside the prediction (the owner's "fall back to
the service's estimate" is therefore a display, not a recorded prediction). The resolution is recorded when a `check` first
shows the search ended (finished, failed or unknown) or the service did not answer (`check_failed:<code>`), or when a
submission fails: `duration_seconds` is the time from the submission to that observation, so it is an upper bound at the
granularity of the checks (60 s apart at least). The model is shown the seconds since the submission and how far past the
prediction and the service's estimate it is; nothing is a deadline or a cancel.

## Predictions

Run A (the head with only the target; query human ubiquitin, 76 aa, MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG; Swiss-Prot):
1. The head's model is offered `reason` and `database_blast` (not `pairwise_blast`: it needs two held sequences). It
   commissions `database_blast` with blastp, swissprot, a hit-list size of tens, the `ncbi` resource.
2. The child: unit 1 `submit` (accepted; predicted duration none: the table is empty; the service's RTOE a few seconds);
   unit 2 `check` (waits about 10 s of spacing, queued or finished); then `hold` while outstanding, or `fetch_and_grade` when
   finished. Swiss-Prot with a 76-residue query usually finishes within the first minute.
3. If finished by the first check: credit = handoff + two information units (queued is not seen, so one: finished) +
   graded; more likely: handoff (1) + finished fact (1) + graded (1) = 3. The top hits are ubiquitin entries
   (UBIQ_HUMAN and other UBB/UBC/RL40 products; the sheet's hit count is at most the hit-list size).
4. The head's credit rises through its existing credit function once the graded sheet is held (the sheet is blastp, so it
   feeds the correspondence): near 1 for the 76 positions covered by identical hits.
5. The first measured duration enters the table; the second search's prediction is that measured value.

## Observed

### Run A1 (`runs/a101_dbblast_run_A1`, workspace `runs/a101_dbblast_ws_A`, journal `journal_A1.sqlite3`, report `report_A1.json`)

Predicted against observed:
1. Head offered `reason` and `database_blast`: as predicted; the model's first choice was the commission of `database_blast`
   with blastp, swissprot, hit-list 50, resource `ncbi` (call 1). Not `reason`.
2. Child: `submit` (accepted; RID G1FEGRZW014, the service's RTOE 3 s; predicted duration none, basis
   `no_earlier_measurement`), then `check` three times (waits of 5.0, 54.8 and 54.7 s), each `queued` (service
   `WAITING`). Not as predicted: the search did not finish. The child's credit: 1.0 (handoff) then 2.0 (the first `queued` is
   a fact), the next checks 0; the controller stopped it after the third check (units 4). The model never held: it chose
   `check` every time (the instruction text then said only that a check waits the spacing; changed afterwards).
3. The head commissioned the child four times (the later three continue the held search: the records were passed back by
   code: `check_refs` grew 3, 5, 7): two checks each, all `queued`; the head's yield estimator stopped it at its fourth unit.
   Head credit 0.0 (nothing graded). Return: 1 handoff row, 9 check rows, `outstanding_handoff_count` 1. The search was
   still `WAITING` at its ninth status request, about 9 minutes after the submission.

### Run A2: a later visit (prediction written before it)

`runs/a101_dbblast_run_A2`: the commission is the one of A1 plus, in `evidence_refs`, the ten records the head returned (the
handoff row and the nine check rows). Its API workspace is the one of A1 (`runs/a101_dbblast_run_A1/api_jobs`: the job's
record and the spacing file are there).
1. The head holds the outstanding search (`database_searches`) and its model commissions `database_blast` with the same
   values: the check passes (it continues the search).
2. The child holds the handoff and nine checks: its credit starts at 0; its first `check` waits only what the spacing leaves
   (the last contact was minutes ago: none) and shows either `queued` (nothing new: 0 credit; then a hold) or `finished`
   (the new fact: 1.0), after which `fetch_and_grade` (graded 1.0).
3. If finished: the sheet's hits are Swiss-Prot entries; the top hits are ubiquitin entries (UBIQ_HUMAN, UBB/UBC products and
   the ubiquitin-ribosomal fusion proteins); the head's credit rises through the existing credit function, near 1 for the
   covered positions. The measured duration (first `finished` observation minus the submission, at least 9 minutes)
   is recorded and resolves the expectation of this search.

### Run B (prediction written before it)

`runs/a101_dbblast_run_B1`, workspace `runs/a101_dbblast_ws_B`: the target (ubiquitin, 76 aa) and one reference (78 aa, one
substitution and two added residues), both held; the head is offered `reason`, `pairwise_blast` and `database_blast`.
Prediction: the model picks `pairwise_blast` first (blastp, target against reference, local): the reference is at hand, the
comparison runs in about a second, and the pairwise tool is described first. Then, with the head's credit at 0.947 (the
estimator cutoff of these runs is 0.1, so the head's units end soon after), it either stops or commissions
`database_blast` once more; I do not predict that second choice. No outcome is wrong here.

### Offline protocol check O1 (not the public service; prediction written before it)

The public service answered `WAITING` for every search of runs A1 to A7 (see Observed). To exercise `fetch_and_grade`, the grading,
the child's return and the head's credit, `runs/a101_dbblast_run_O1` runs the same command (`run`, through the head) against the
library's local server that speaks the NCBI URL API (`jobs/tests/blast_url_api_server.py`; a fixed one-hit report over the
submitted query: hit `sp|TEST1|TEST_HIT`, 5 identical residues), with its own estimate table
(`runs/a101_dbblast_estimates_offline/table.sqlite3`), so no fake duration enters the table of the public runs.
Prediction: the model commissions `database_blast`; `submit`; a first `check` (queued), a second (queued: nothing new), a
third (finished: new fact); `fetch_and_grade` (graded, 1 hit, the sheet's features with no function rows); the child's credit
1 + 1 + 1 + 1 = 4 (handoff, queued, finished, graded); the head's credit small but above 0 (5 of 76 positions covered through
the sheet's blastp hit), so the head's estimator stops it shortly after.

### Offline check O1 observed, the defect it showed, and the prediction for O2

Observed in `runs/a101_dbblast_run_O1` (journal `runs/a101_dbblast_ws_A/journal_O1.sqlite3`): the child's flow worked as
predicted (submit; three checks with the local service's two `WAITING` answers; `fetch_and_grade`; then holds with
`graded_result_established` until the estimator stopped it, six holds after the graded unit); the model then commissioned the child two more times
for different searches (tblastn on `core_nt`, then blastp with hit-list 200), each also graded. Not as predicted: **the head's credit stayed 0.0**
(`comparison_count` 0 in its finding) although the sheets were saved and the scoring raised no error.
Cause, read in `native_correspondence.read_details`: the head's credit scores the graded cell of each held *observation*
(`alignment` or `comparison`, origin `tool`), not a saved sheet; a source with a search row only enters the tool profile.
The old `blast_grade` kept no observation (the registry's `_import_blast` did). Fix: `fetch_and_grade_search` now also keeps,
in the same transaction, one `reference` record per hit and one `comparison` observation per alignment with the address of its graded cell
(`blast_search.shared_hsp_component`, `hsp_row`, as `_import_blast` does; without its taxon terms and processing context), and
returns the references in `graded_refs`.
Prediction O2 (`runs/a101_dbblast_run_O2`, same local server and commission): the child's flow as in O1; the head's credit
above 0 and small: the fixed hit covers 5 of the 76 positions, so the credit is under 0.1.

Observed O2 and O3 (offline): O2 failed with `operand_interval_unit_mismatch` (my observation's reference unit came from the
program, the store's from the held reference record: fixed, units now read from the held records). O3 then failed in the head's
credit with `A101ScoringUnavailable: a101_translated_or_nucleotide_map_not_bound` (program `tblastn`, offered by me to
the head's model, which chose it): the A101 native-correspondence projection scores a `blastp` sheet only. The head
therefore commissions `database_blast` with `blastp` only (`COMMISSION_PROGRAMS` in the head's `task.py`, enum and check;
the child itself takes every program of the service). Prediction O4: as O2 (flow as O1, head credit above 0 and under 0.1).

### Observed: public service, later visits and run B (all in `runs/a101_dbblast_ws_A` and `_B`; run directories `runs/a101_dbblast_run_<tag>`)

- A2, A3, A4, A6, A8 continue the search of A1 (records passed back by code and by the commission's `evidence_refs`; the API
  workspace is that of A1, so the spacing file is shared): in each the head commissioned the child four times (A8 made two checks, the others one); in the first
  visit the child made one `check` (`queued`, nothing new: 0 credit) then held (`search_not_finished`) until the estimator
  stopped it (two holds); no check was made after the first of a visit (the model held when the next request was not yet
  allowed). Every visit's credit 0.0; every return `outstanding_handoff_count` 1. A7 does the same for the search of A5.
  The search of A1 was still `WAITING` ("Status Searching", the page of the service) 74 minutes after its submission
  (21:38 to 22:52 UTC), the search of A5 still after 45 minutes.
- Surprise about the service: the RTOE it returns with the submission is not a duration to rely on: A1 got 3 s (at 21:38),
  A5 16969 s (22:06), and a probe submission of mine by `curl` (a 76-residue query, hit-list 5, 22:52) 24273 s. The
  service's queue of the day is hours, not seconds. Predicted by me: finished within a minute. Not as predicted. The
  model saw `service_estimate_seconds` and `seconds_past_service_estimate` as facts and held.
- No public search finished, so no public duration was measured: `runs/a101_dbblast_estimates/table.sqlite3` holds two open
  expectations (`no_earlier_measurement`, one per submission) and no resolution.
- B1 (`runs/a101_dbblast_run_B1`): as predicted, the head's first and only decision was `pairwise_blast` (blastp, target
  against reference, `local`); credit 0.9471855819086874 (the same sheet as the earlier pairwise runs: 76 paired positions,
  E-value 3.9499e-56) stopped its estimator at one unit; the model had no occasion to choose `database_blast`.
- O4 (offline, local protocol server, own estimate table `runs/a101_dbblast_estimates_offline`): the flow as predicted:
  child `submit` (predicted 17.07 s, learned from the median of earlier offline searches of the kind; measured 17.79 s: the
  duration is submission to the observation of the first `finished` check and includes the model's own decision time),
  three checks (queued, queued, finished), `fetch_and_grade` (1 hit, 1 observation), then five holds; the child's credit
  4.0 (handoff, queued, finished, graded); the finding carries the controlled sheet features (`total_group_count` 1,
  `groups_without_function` 1, `unannotated_fraction` 1.0, E-value 1e-09, `functions` empty) and the three durations; the
  head's credit 0.002735978873046042 (5 of 76 positions; its finding `comparison_count` 1), as predicted (above 0, under 0.1),
  then six `reason` commits of the head with `revision_conflict` outcomes (the head's own tool, not this episode's).
  The offline table's resolutions (seconds): 17.03, 17.50, 18.64, 17.11, 17.99, 15.94, 16.87, 17.79: each prediction after
  the first was the median of the earlier ones.
- Refusals: the checks were called directly (not by a real run: the model never made a wrong request), through the
  launcher (`runs/a101_dbblast_refuse_1`): a commission with blastn on a protein query and swissprot gives
  `program_does_not_take_the_query_molecule` and `database_does_not_hold_what_the_program_searches` with their `choose_from`;
  a commission with a local resource and hit-list 500 gives `hitlist_size_out_of_range` and `resource_is_not_an_api_service`; a
  second `submit` while a search is held gives `search_already_held`; `fetch_and_grade` on an outstanding search gives
  `search_not_known_to_be_finished`. A database outside the vocabulary, or a program outside the set, is refused earlier by the
  answer schema (an enum).
