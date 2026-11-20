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

(filled after each run)
