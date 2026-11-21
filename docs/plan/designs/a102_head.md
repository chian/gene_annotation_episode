# The A102 head `structural_homology_evidence` (round 1: one child, `structure_search`)

Status: built 2026-11-21, not yet run for real (see "Prediction for the first real run"). Design: `a102_tree.md`; the child:
`a102_structure_search_episode.md`; the SOP: `docs/sop/evidence_axis_build_sop.md` (Steps 1, 5, 7, 8, 9, 10, 11, 12, 13).
HEAD = `gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence`; LIB = `.../episode_support`;
A101HEAD = `.../root/a101/sequence_homology_evidence` (the pattern, read only).

## What was deleted (AGENTS.md, "Removing unwanted code")

The old children `execution_job_submission`, `execution_progress_assessment`, `execution_result_acquisition`, `hpc_work_planning`,
`resource_work_submission`, `resource_result_acquisition`, the head's `tests/` and the old head files (`task.py`, `credit.py`,
`yield_estimator.py`, `messages/*`) were removed with `git rm` before the new files were written. Old library modules the old head
used are left alone. The goal text of the old `goal.py` (the instruction-entry goal text and the guidance sentences of the merged
A102 axis, `97308b94c`) is carried into the new `goal.py`; the sentence that named the old machinery (a thought pattern and tool
selection prepared for a new child) is not.

## Step zero: what is called, what is new

| Need | Called as it is | New in the head, and why |
| --- | --- | --- |
| The episode contract | `EpisodeBinding` (the class inherits only it), `method_loop.RecordForm`, `ChildCall`, `Rejected`, `ModelRequest` | `episode.py` (the same member list as A101HEAD, minus nothing: the head has `resume_action`, `best_arguments`, `outcome_pending`, `offered_actions`) |
| The child's commission check | `foldseek_search.check_commission` (the child's library check: query, database, model, resource, continuation of an outstanding job, repeat of a graded or commissioned search) fed with the credit's own reader `candidate_measurements.held_searches` and the jobs `structure_search_child.held_jobs` read from the job ledger rows | `task.check_structure_search`: the same check plus two facts only the head can state (the model is of the query; `obtain_one` while a model of the query is held) |
| The credit | `candidate_measurements.candidate_table` / `candidate_standing` / `held_sources`, `differential_credit.test_ceiling` and `SHEET_WEIGHT` (the other agent's files: called, not edited) | `credit.A102DifferentialCredit` (the definition record), `credit.ceiling`, `best_arguments`, `outcome_pending`, `CEILING_VERSIONS` |
| The controller | `yield_declarations.checked_yield_declaration`, `forecast_definitions`, `open_yield_controller` | `yield_estimator.py` (one call each, as A101HEAD) |
| Returned lists closed under naming | `job_records.returned_with_names`, `named_records`, `outstanding_jobs` | `messages/internal_summary.py` |

## The files

* `goal.py`: the axis's goal (above). `task.py`: `CHILD_SLOTS = {'structure_search': 'structural_homology_evidence/structure_search'}`,
  `TOOLS = {}` (no tool yet: `site_correspondence` is wired in later), `SERVICES = ('job_access',)`; `decide`, `offered_actions`,
  `action`, `resume_action`; no `reason` action. Round 1 of the head has exactly one action, the child slot.
* The commission of `structure_search` is five controlled fields, each from a fixed set: `query_ref` (a protein sequence of the
  scope: a target whose molecule is not protein gets no commission, the slot is then not offered), `database` (`foldseek_job_route.
  DATABASES`), `resource_id` (a bound resource of kind `foldseek`), `model_ref` (a held `protein_structure_model` product row of
  that query, or the fixed value `obtain_one`, which tells the child to obtain one itself) and `until` (`launched`, `extracted`).
  `COMMISSION_CHECKS` is ONE check: a search of the same (query, database, model SHA-256) already graded or commissioned is refused
  with its fix list, except the resume of the parked job (the same fields, `until` `extracted`), as A101 treats a parked
  `bvbrc_blast`.
* `credit.py`: `A102DifferentialCredit` (test = one graded source `structure_search:foldseek:tmalign:<database>@<source>`; sheet
  weights from `SHEET_WEIGHT`); `credit` = the candidate table's credit; `ceiling` (below); `best_arguments` (the resume commission of
  the parked job, else the first database not searched with a held model, else `None`); `outcome_pending` (a child unit that returned
  parked); `CEILING_VERSIONS = {'structure_search': 'a102_ceiling_v1'}`. No `UNBOUNDED`.
* `yield_estimator.py`: the forecast controller, opened as A101HEAD does. The run's declaration (continuation settings, key
  `A102:a102_structural_correspondence`): kind `forecast`, `exchange_rate` 0.006, `forget_old_rows` true, `job_kinds` `{}`.
  **PROVISIONAL: 0.006 is A101's value** (the owner on a first figure: "you have to start somewhere that's fine"); it is A101's
  rate for A101's credit scale and is to be re-derived from A102's own resolved forecast rows after the first real runs (SOP Step 9).
* `messages/`: `read_from_parent` (the assignment form the root sends an axis head, with `child_credit_units` carrying `model_unit`),
  `msg_to_child` (objective; custody: the query and its sequence; a held model passed as the product row in `model_refs` and, in
  `input_refs`, the artifact it names; a resume passes the held handoff, check and closure rows with everything they name and no
  model; `REQUIRED_RETURN` = `execution_handoff_refs`, `execution_check_refs`, `execution_closure_refs`, `graded_refs`),
  `read_from_child`, `internal_summary` (pure function of the view), `final_to_parent` (below).

## The ceiling of `structure_search` (SOP Step 8)

The proved bound of one search test: `differential_credit.test_ceiling(standing, products, 'structure_search', unseen=1000,
limit=1000)`, the number of products one search can measure being at most the number of hits it can name. A value of one hit is B,
in [0, 1], and the weight of the family is 1, so a test moves a score by at most 1: a pair of listed candidates earns at most 1, a
candidate the search admits earns at most its entry, 1.

**The number 1000 and where it comes from.** The Foldseek server's documentation (`LIB/forms/application_service_specs/original/
StructureSearch_server_api_docs.html`) names no limit on the hits of a result. The Foldseek README (`runs/a102_measure_check/
foldseek_README.md`, line 161) gives `--max-seqs` ("the amount of prefilter handed to alignment; increasing it can lead to more
hits (default: 1000)"): one query keeps at most 1000 results. The server's own search parameters per database are not published
(its `worker.go` appends `params.Search`, read from a file on the server; retained at `runs/a102_head_sources/worker.go`, line 489),
so that the server leaves the default is OBSERVED, not documented: the stored results of the live tickets hold 976 hits (tmalign,
afdb-swissprot), 548 (tmalign, pdb100), and 982, 481, 549 (3diaa; afdb-swissprot, cath50, pdb100): the largest is 982. A result of
more than 1000 hits would exceed the ceiling and the run would end with `episode_ceiling_exceeded`; the figure is then wrong and is
changed with the action's `CEILING_VERSIONS` entry.

A commission the check would refuse as a repeat has ceiling 0; the resume of a parked job has the search's ceiling.

## The return (`final_to_parent`)

`credit` and `finding`. The finding, per protein target: `target_ref`, `molecule`, `search_count`, `hit_count`, `named_count`,
`not_asked_count`, `candidate_count`, the LEADING 10 candidates (`name`, `score`, `sheets`; leading first), the model's `model_origin`,
`model_residues`, `model_mean_plddt`; and `outstanding_handoff_count` (handoffs without a closure), `waiting_searches` while a search
is parked. Selectable lists (each closed under naming): `committed_record_refs`, `execution_handoff_refs`, `execution_check_refs`,
`execution_closure_refs`, `data_product_refs`.

## Needs outside this note's files (not made here)

* `root/messages/msg_to_child.py` builds the A102 assignment without `child_credit_units`; the head requires it (with `model_unit`).
  A real run through the root needs that line (the owner's files).
* `episode_support/configuration/structural_homology_evidence/process_options.py` has no `freeze_selection`, so
  `freeze-libraries --axis A102` reports the axis as not frozen; the runs below copy the frozen library of A101's workspace
  (it already holds the entry `A102.json`) and write the selection by hand.

## Prediction for the first real run (CspA), written before it

Target: E. coli CspA (P0A9X9), 70 residues, protein. Run: from a pinned worktree, afdb-swissprot is the only database.

1. The head's first and only unit is the child `structure_search` on `afdb-swissprot` (the commission's other fields: the one
   `foldseek` resource, `model_ref` `obtain_one`, `until` `extracted` or `launched`; with `launched` the head resumes it as a second
   unit). Inside the child its model chooses `get_model` `alphafold_db` (P0A9X9, 70 residues, mean pLDDT 88.4), then `estimate`
   (10 s, `no_earlier_measurement`: no Foldseek job is in the ledger), `launch`, `monitor`, `extract`.
2. The sheet: 976 hits or close; the model's own entry is a control (`control_count` 1, no value to any candidate); about 130
   product candidates (130 in the direct check); the leading candidates CspG (mean B about 0.95), CapB (0.92), CspC (0.91), with
   CspA near 0.90 (0.897) and not first. Naming: all 10 batches asked (976 asked, 975 named).
3. The head's credit rises by the sum of the candidates' entry values (one test, so no differential): **41.41** (the sum of the
   mean B of the 130 candidates in `runs/a102_child_check/ws_shared/store`, grading artifact `11e9cd63...`: 41.408; the weight of the
   family is 1). The rise is below the ceiling (1000).
4. After that unit the same search has ceiling 0 (a graded search of the query and database; the only database), nothing is worth
   its cost (forecast 0), and the head ends by its estimator with `outstanding_handoff_count` 0.
5. No custody error.

## Prediction for the RecA run, written before it (after the CspA runs)

Target: E. coli RecA (P0A7G6), 353 residues (`runs/a101_goal12_ws_reca/target.fasta`). Same head, same worktree commit (`24c08fa33`).

1. One head unit, `structure_search` on `afdb-swissprot`, then a yield stop (as in the CspA run). Inside the child: `get_model`, estimate, launch,
   monitor, extract. The model: AlphaFold DB (P0A7G6, 353 residues, mean pLDDT in the 90s) if the child's model picks it; the CspA run
   showed it picks `esmfold` first, and an ESMFold model of 353 residues was folded live before (18 s), so that is as likely. With an
   ESMFold model there is no self control; with an AlphaFold model the own entry is the control.
2. The sheet: close to 1000 hits; candidates dominated by RecA and RadA/Rad51/DMC1-like recombinases (names such as "Protein RecA",
   "DNA repair protein RadA", "DNA repair protein RAD51 homolog"), the leading candidates with mean B above 0.8.
3. Credit: the sum of the candidates' entry values (tens, below the ceiling 1000); one unit; ceiling after it 0; the head ends by its
   estimator with `outstanding_handoff_count` 0. The Foldseek duration observed: tens of seconds (CspA: 16.7 s). No custody error.

## What happened (real runs, 2026-11-21, worktree `gae_a102_24c08fa33`, commit `24c08fa33`)

Runs used: 3 of 5 (1 failed at the start, CspA 2, RecA 3). Foldseek tickets: 0 (run 1), 1 (CspA), 1 (RecA).

* Run 1 `runs/a102_head_ws_cspa_1`, run dir `runs/a102_head_run_cspa_1`: `ValueError scientific_yield_credit_definition_mismatch`. The continuation
  file's `credit_definition` was written by importing the head's `A102DifferentialCredit` from the MAIN checkout, where the other agent had since
  changed `differential_credit.SHEET_WEIGHT`; the pinned worktree's record differed. Fix: the workspace builder imports from the pinned worktree
  (not a code defect of the head). No model call, no ticket.
* Run 2 CspA, `runs/a102_head_ws_cspa_2` (journal `journal_cspa.sqlite3`, run dir `runs/a102_head_run_cspa_2`), run id `a102_head_cspa_2`, ended by
  `yield_stop` after 1 unit, 6 model calls, credit 39.3438, `outstanding_handoff_count` 0.
* Run 3 RecA, `runs/a102_head_ws_reca_3` (run id `a102_head_reca_3`, run dir `runs/a102_head_run_reca_3`), 1 unit, 6 model calls, credit 6.2504.

### CspA: predicted against observed

1. Prediction: child's model picks `get_model` `alphafold_db`. OBSERVED otherwise: it picked `esmfold` (70 residues, mean pLDDT 88.54, no accession); the
   rest as predicted (estimate 10 s `no_earlier_measurement`, launch, monitor 9 s, extract). One head unit `structure_search` (`until` extracted).
2. Prediction: 976 hits, own entry a control, about 130 candidates, CspG/CapB/CspC leading, CspA about 0.90. OBSERVED: 754 hits (the ESMFold model has
   another shape from the AlphaFold one), `control_count` 0 (an ESMFold model is no entry of the database), 135 candidates, 8 naming batches, all 754
   named. Leading 10 (score): Probable cold shock protein A 0.9295; Cold shock protein CspC 0.9013; Cold shock-like protein CspC 0.8974; Cold
   shock-like protein CspLA 0.8971; Cold shock protein CspD 0.8880; Cold shock protein 0.8811; Cold shock-like protein CspLB 0.8795; Cold shock protein
   ScoF 0.8727; Cold shock-like protein CspE 0.8667; Cold shock protein CspB 0.8587. All in the cold shock family; CspG and CapB were not first (the
   numbers of the prediction were those of the AlphaFold model).
3. Prediction: credit 41.41 = the sum of the entry values. OBSERVED 39.3438 (the sum for these 135 candidates; one test, no differential); the
   journal: offered ceiling 1000.0, chosen ceiling 1000.0, rise 39.3438 (below the ceiling).
4. Prediction: after the unit the ceiling is 0, nothing is worth its cost, the head ends by its estimator. OBSERVED: the controller step rows show
   `structure_search` ceiling 0.0, forecast 0.0, expected seconds 125.74 (the unit's measured seconds), threshold 0.7544 (= 125.74 x 0.006), worth false,
   `decision_basis` `no_offered_action_forecast_exceeds_expected_seconds_times_exchange_rate_and_no_started_work_to_finish`; `outstanding_handoff_count` 0.
5. Prediction: no custody error. OBSERVED: none; every record list the child returned was held by the head (the head's summary read the job rows and
   the graded sheet after the child returned, and the closed lists went to the root form).

The ledger: the head's row `structural_homology_evidence:structure_search` (forecast 500.0 = share 1/2 x ceiling 1000; no expected seconds; gain
39.3438; unit seconds 125.74; outcome finished) and the Foldseek job row (estimate 10 s `no_earlier_measurement`; the observed duration 16.74 s,
`duration_source` `first_status_showing_the_end`; the ticket carries no task times).

### RecA: predicted against observed

1. One head unit, then a yield stop: as predicted. The child's model picked `alphafold_db` this time: AlphaFold DB model, 353 residues, mean pLDDT 91.38;
   the estimate was `learned_from_earlier_jobs` 16.7 s (the CspA job); the job took 24.34 s observed.
2. Prediction: close to 1000 hits, RecA and RadA/Rad51-like recombinases dominate with mean B above 0.8. OBSERVED: exactly 1000 hits (the cap),
   `control_count` 1, 9 naming batches (899 named, 100 not asked: the naming settled), only 18 candidates; the leading are RecA products and
   homologs, with mean B 0.61 down to 0.33: Protein RecA 2 0.6147; Protein RecA 0.6126; Protein RecA 1 0.5486; Mitochondrial DNA repair protein recA
   homolog 0.5346; DNA repair protein recA homolog 3, mitochondrial 0.5142; Protein RecA, plasmid 0.5007; DNA repair protein recA homolog 1,
   chloroplastic 0.4786; DNA repair protein recA homolog 2, mitochondrial 0.4445; Protein RecA, chromosomal 0.4401; Putative DNA repair protein recA
   homolog 4 0.3266. NOT as predicted: no RadA/Rad51-named candidate among the 18, and the B values are lower than 0.8 (the target is 353
   residues and a hit's B is divided by the target length plus the hit length, so partial matches score low).
3. Credit 6.2504 (below the ceiling 1000; the ceiling after the unit 0, threshold 1.3037 = 217.28 s x 0.006); `outstanding_handoff_count` 0; no custody error.

The cap: the RecA search returned exactly 1000 hits, the `--max-seqs` default, which supports the bound `HIT_BOUND` = 1000 (it is reached, not
exceeded).

## Not exercised

`until` `launched` (a parked job and `resume_action`), the resume commission, a passed model (`model_refs` with its artifact), a refused
commission (a repeat) through the model, `fix` and a failed launch, the second database, a non-protein target. The exchange rate 0.006 is A101's
and was not re-derived: the two head rows so far (CspA: gain 39.34 over 125.7 s = 0.313 per second; RecA: 6.25 over 217.3 s = 0.029 per second) are
far above 0.006 per second, so it never stopped a first search; with one database the rate decides nothing yet.
