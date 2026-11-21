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
   chloroplastic 0.4786; DNA repair protein recA homolog 2, mitochondrial 0.4449; Protein RecA, chromosomal 0.4401; Putative DNA repair protein recA
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

## The tool `site_correspondence` in the head (wired 2026-11-21)

Step zero: called as it is: `check_site_correspondence_request`, `search_inputs`, `site_correspondence(ctx, *, search_ref,
site_source)`, `held_site_tests`, `differential_credit.site_test_ceiling`, `ToolCall`. New in the head: `task.site_options` (the
request schema), `task.check_site_request` (the library check fed with the summary's `site_searches` and `held_site_tests`),
`task.site_correspondence_tool` (the tool function), `credit.offered_site_pairs`, `credit.graded_site_pairs`, `credit.site_value`, the
`ceiling` and `best_arguments` branches, `internal_summary` rows for tool units, `final_to_parent` `site_tests`.

* Request: action `site_correspondence`, fields `search_ref` and `site_source`. The schema is one option per graded search of a
  protein sequence of the scope whose raw result and model the head holds, with the site sources left for it (`annotated`,
  `catalytic`; the graded pairs are not offered), so a request that passes the check works. The tool is offered only while such a
  pair exists. The description states facts only (what the test does, the two sources, what it needs, that a repeat is refused).
* Credit: the definition record is version `a102_differential_credit_v2` (it names the site measurement and the second test kind,
  and its `sheet_weights` carry `site_correspondence` 1.0); the test is `site_correspondence:<site source>@<source>`.
* Ceiling: `differential_credit.site_test_ceiling` over the product candidates of the named search's own sheet (`mean_B` not null);
  0 for a graded pair; with arguments `None` the largest over the pairs still offered; `best_arguments` the first pair (searches in
  order, `annotated` before `catalytic`) with the largest value; `CEILING_VERSIONS['site_correspondence']` `a102_ceiling_v1`.
* Custody: the tool opens the search's source, its retained grading (artifact), its raw result (artifact), the model (artifact) and
  the target's sequence; `search_inputs` reports `result_held` and `model_held` and the schema offers only held ones.

Two changes in the library: (a) an absent residue records WHERE: `outside_the_alignment` or `within_the_alignment` (counts per hit and
per candidate; the value rule is unchanged); (b) the grader no longer calls `_fit` (the search sheet keeps no transform to hand over
and no hit is fitted twice in one call; 90 percent of `_fit`'s 0.23 s per hit is the record-shape validation of the general fit
result): `superposed_distances` repeats the same numerical operations. RecA, 397 hits with sites, stored result: 88.1 s before,
0.1 s after; all 3179 residue rows of the sheet equal in every field (`runs/a102_site_wire/sheet_before.json`, `sheet_after.json`).

## Prediction for the runs with site_correspondence, written before them

RecA (P0A7G6, 353 residues), CspA (P0A9X9, 70 residues). The head's tool and the child as in the runs above.

RecA:
1. Unit 0 `structure_search` (credit about 6.25 if the child picks the AlphaFold model, as in run 3). Then `site_correspondence`
   `annotated` is offered with a ceiling `w (u + k^2 // 4)` over the 18 candidates (small, tens); `catalytic` is offered too.
2. If the model takes `annotated`: about 397 hits with sites of 399 asked, 3 or more candidates measured (the direct check: 3),
   a credit rise near 0.30 (direct check 0.3016), below the ceiling. The unit takes about 10 s (4 UniProt batches) plus grading
   (0.1 s per hit-set after the change).
3. `catalytic`: RecA is no M-CSA reference entry, so 0 hits with sites, a unit that measures nothing and earns 0; the learned share
   of the tool then falls and a further unit is not worth its cost. The head ends by its estimator, `outstanding_handoff_count` 0.
4. No custody error; no ceiling breach.

CspA:
5. `annotated` measures only unrelated hits (lin-28 homologs, CcmE, EfpL, Y-box-binding protein 1): with the stored AlphaFold-model
   search the direct check measured 9 candidates of 69 and a rise of about 0.81. With an ESMFold model (the child picked `esmfold`
   in run 2) the search has other hits (754, 135 candidates) and the numbers differ; I predict a few candidates measured (under 15),
   a rise under 2, below the ceiling (which is large, `u + k^2 // 4` over 135 candidates, about 4000). `catalytic`: 0 measured.

## What happened with site_correspondence (real runs, 2026-11-21)

Runs used: 2 of 5. Foldseek tickets: RecA 1, CspA 2 (afdb-swissprot, then pdb100 chosen by the model). Workspaces are built by
`/tmp/.../build_ws.py`-style scripts: `init`, `propose-annotation`, a continuation written with `A102DifferentialCredit().as_record()` imported from
the PINNED worktree, `freeze-libraries --axis A102 --source research/slotted_process_library/publications/2026-10-24-001`
(the new `freeze_selection` worked first time), then the commission; every run a fresh workspace and run id.

* RecA: `runs/a102_site_ws_reca_1`, run dir `runs/a102_site_run_reca_1`, run id `a102_site_reca_1`, worktree `gae_a102_4f840abe6`, commit
  `4f840abe6` (no pdb100). Ended `yield_stop`, 3 units, credit 43.5737, no failure.
* CspA: `runs/a102_site_ws_cspa_1`, run dir `runs/a102_site_run_cspa_1`, run id `a102_site_cspa_1`, worktree `gae_a102_4acf9f254`, commit
  `4acf9f254` (pdb100 present; `site_correspondence` refuses and does not offer a pdb100 search). Ended `yield_stop`, 4 units, credit 307.7405, no failure.

Per-unit tables (ceiling = offered ceiling of the chosen action; forecast and threshold as the controller showed them for the NEXT decision):

| run | unit | action, arguments | ceiling | rise | credit after | next decision: site forecast / threshold |
| --- | --- | --- | --- | --- | --- | --- |
| RecA | 0 | structure_search afdb-swissprot, obtain_one | 1000 | 6.2504 | 6.2504 | 40.5 / 1.915 |
| RecA | 1 | site_correspondence annotated | 81 | 37.3233 | 43.5737 | 37.32 / 0.238 |
| RecA | 2 | site_correspondence catalytic | 81 | 0 | 43.5737 | none offered; stop |
| CspA | 0 | structure_search afdb-swissprot, obtain_one | 1000 | 41.4080 | 41.4080 | 973.4 / 0.154 |
| CspA | 1 | site_correspondence annotated | 4225 | 3.6510 | 45.0590 | 488.5 / 0.238 |
| CspA | 2 | structure_search pdb100 (held model) | 9255 | 262.6816 | 307.7405 | 488.5 / 0.238 |
| CspA | 3 | site_correspondence catalytic | 4225 | 0 | 307.7405 | none offered; stop |

### Predicted against observed

RecA. (1) Unit 0 as predicted (AlphaFold model, 353 residues, mean pLDDT 91.38; credit 6.2504, as run 3); `annotated` and `catalytic` both offered, ceiling 81 =
18 candidates, 18 squared over 4 (I predicted "tens"). (2) The model took `annotated`: NOT as predicted in size: 899 hits asked (the naming settled this time, 899
named, not the 399 of the direct check), 889 with sites, 18 candidates measured (predicted 3 or more), rise 37.32 (predicted near 0.30). Cause: with 18 listed
candidates measured, the rise is the sum of 153 pairwise differentials; the direct check had 3 candidates. Below the ceiling 81. (3) `catalytic`: the model took it;
0 hits with sites, 18 candidates without a site, rise 0, as predicted. The learned share did NOT make it unworthy beforehand (the forecast is per action type, not per site
source: 37.32 against a threshold 0.238 after unit 1); it ended because no pair was left offered. (4) No custody error, no ceiling breach.

CspA. The child's model was the AlphaFold one this time (P0A9X9, mean pLDDT 88.44), 976 hits, 975 asked, 130 candidates; search credit 41.408 (the prediction of the
first runs). `annotated`: 975 asked, 221 with sites, 37 candidates measured (predicted under 15; the direct check measured 9 of 69 on 404 hits), rise 3.651 (predicted
under 2; direct check 0.81 on fewer hits); Y-box-binding protein 1 matches the direct check exactly (8/9 hits, E 0.101, F 0.487). Ceiling 4225 = 130 squared over 4. `catalytic`:
0 measured, rise 0, as predicted. The model also chose a pdb100 search (unit 2: rise 262.68, ceiling 9255) and the tool was not offered for it.

### Candidates measured, search value against site value

RecA (hits with sites of hits asked; search mean B; site mean E; mean F), sorted by E:
Protein RecA 2 1/1, 0.615, 0.596, 0.969; Protein RecA 644/652, 0.613, 0.535, 0.859; Mitochondrial DNA repair protein recA homolog 1/1, 0.535, 0.508, 0.951;
Protein RecA 1 1/1, 0.549, 0.452, 0.824; DNA repair protein recA homolog 1, chloroplastic 1/1, 0.479, 0.441, 0.921; Protein RecA, chromosomal 1/1, 0.440, 0.400,
0.909; recA homolog 3, mitochondrial 1/1, 0.514, 0.390, 0.758; Protein RecA, plasmid 1/1, 0.501, 0.366, 0.730; recA homolog 2, mitochondrial 1/1, 0.445, 0.339, 0.762;
Putative recA homolog 4 1/1, 0.327, 0.192, 0.589; RadB 3/5, 0.313, 0.165, 0.515; RadA 47/47, 0.228, 0.075, 0.329; rhp55 1/1, 0.154, 0.036, 0.232; ATP synthase
subunit alpha (five names, 185 hits), B 0.106 to 0.109, E 0.015 to 0.023, F 0.14 to 0.21. The test separates the RecA family (E 0.34 to 0.60) from RadA/RadB (0.075,
0.165) and ATP synthase alpha (0.02) that the fold search has at B 0.11 to 0.31; the ordering of the top RecA names changes little. All 7276 residues were aligned
(absent outside 0, within 0): the global alignment of RecA covers the P-loop.

CspA, top by E (hits with sites/asked, B, E, F, residues absent outside / within the alignment): Y-box-binding protein 1 8/9, 0.203, 0.101, 0.487, 10/0;
lin-28 (four names) 0.258 to 0.374, E 0 (F 0; 8 to 32 residues absent outside the alignment: the zinc knuckles, another domain); CcmE (three names) 0.179 to 0.206, E 0
(4 to 34 outside); EfpL 29/29, 0.175, 0 (22 outside, 7 within); RsgA 16/16, 0.160, 0 (272 outside); ModC 24/24, 0.105, 0 (192 outside). Over the test: 1376 residues, 1345
absent outside the alignment, 12 within: the new split shows that the zero of the lin-28, CcmE and RsgA families is another domain, and only EfpL has a gap inside the aligned span.

### Timing

Grader, RecA 397 hits with sites (stored result, direct check): 88.1 s before, 0.1 s after, all 3179 residue rows equal in every field. The unit in the real RecA
run (899 hits asked, 889 with sites, 10 UniProt requests) took about 40 s per decision to decision (controller `expected_seconds` 39.65 for the site tool).

### Not exercised / unverified

A failed site source (a fault of UniProt or M-CSA after a passed check); a model request refused by the check (the model never asked a graded pair: the schema offers only
valid pairs); a pdb100 search through the tool (refused by construction, not tried); a second search of the same target for the tool; resume.

## The tool `partner_contacts` in the head (wired 2026-11-21)

Step zero: called as it is: `check_partner_contacts_request`, `partner_search_inputs`, `partner_contacts(ctx, *, search_ref, resource_id)`
(async), `held_partner_analyses`, `differential_credit.site_test_ceiling` and `bound_partner_test_ceiling`, `ToolCall`. New in the
head: `task.partner_options` (one option per graded pdb100 search whose request passes the check, with the bound local resources),
`task.check_partner_request`, `task.partner_contacts_tool`, `credit.analysed_searches`, `credit.offered_partner_searches`,
`credit.partner_value`, the `ceiling` and `best_arguments` branches, `internal_summary` (`search_inputs` replaces `site_searches`
and is `partner_search_inputs`; `partner_test_rows`, `held_partner_analyses`; candidates BY KIND), `final_to_parent` (partner
candidates, counts per kind, `partner_tests`). SERVICES stays `('job_access',)` (the job goes through `execute_on_local_resource`,
as A101's `hmmer_profile_scan`); the head's continuation settings gain `python_executable` and `usalign_executable_directory`
(`resources/software/usalign.json`: `resources/software/usalign-20261019/bin`). The credit definition is version
`a102_differential_credit_v3` (it names the partner measurement and candidates and the two new test kinds; `sheet_weights` carries
`bound_partner` 1.0). `CEILING_VERSIONS['partner_contacts']` = `a102_ceiling_v1`.

* Request: action `partner_contacts`, fields `search_ref` (a held graded pdb100 search with raw result, model, hit metadata and the
  partner metadata, not yet analysed) and `resource_id` (a bound local resource). A search graded before the entry contents existed
  in the hit metadata is refused by the check with `search_predates_the_partner_metadata`.
* Ceiling = `site_test_ceiling` over the product candidates of the named search + `bound_partner_test_ceiling` over the set of
  partner candidates the search's entries make possible (`partner_contacts.possible_partners`; the proof is in the docstring: the
  entry contents RCSB lists are an upper set, and the unit fails with `grading_refused` if a file shows a partner outside it).
  0 for an analysed search; with arguments `None` the largest over the searches still offered. Direct check on the stored data
  (not a real run): CspA P = 79 candidates, ceiling 79 (rise 0.8985 earlier); RecA P = 72, ceiling 72 (rise 2.826).
* The library fix (commit `0ff712e14`): the pdb100 hit lookup also asks `nonpolymer_entities { nonpolymer_comp { chem_comp { id } } }`
  (verified live; the polymer types were already asked); the hit rows carry `entry_nonpolymer_components` and `entry_polymer_types`;
  an entry whose contents show no non-additive ligand and no nucleic acid is not downloaded (`no_partner_in_entry`, counted on the
  sheet as `entries_skipped_no_partner`); an entry whose contents RCSB did not state is not asked (`entry_contents_unknown`);
  branched (glycan) entities are facts beside the protein partners, since RCSB's non-polymer entities do not list them (the
  branched entity's component ids could not be found in the GraphQL schema within the request limit).

## Prediction for the runs with partner_contacts, written before them

Direct-check numbers: `a102_partner_contacts.md` and the re-check of `runs/a102_partner_fix/` (stored searches, 80 files, the new
unit: the same candidate tables, CspA 25 files asked and 55 of the 80 skipped, RecA 43 asked and 37 skipped).

CspA (P0A9X9, 70 residues), if the model searches pdb100 and then takes `partner_contacts`:
1. Entries: of the 496 entry files of the stored pdb100 search, 233 are skipped without a download (no non-additive ligand and no
   nucleic acid in the entry), 263 are left to ask. I expect the settling rule to stop the unit after 4 to 10 batches (40 to 100
   files asked, a few `too_large` such as 4BTS), not to walk all 263. The unit takes about 1.5 s per file (download spacing 0.5 s plus
   one local US-align job per batch of 10): 60 to 180 s.
2. Nucleic acid found among the cold-shock, Y-box and Lin-28 structures: `nucleic_acid:rna` (about 17 hits in the direct check, mean E near
   0.24; with fewer files asked the count is lower, mean E 0.2 to 0.3) and `nucleic_acid:dna` (2 hits, E near 0.17); `ligand:ZN` at E 0
   (the zinc of the knuckles of Y-box and Lin-28, 4 hits) if those entries are reached; `ligand:MG` 0.49 only if CspB 2I5M is reached.
3. Product test: Cold shock protein CspB leads by it near 0.54 (2 of 16 hits with partners); Y-box-binding protein 1 about 0.37.
4. The best hit's contact residues (3PF5 chain B, CspB with RNA, TM 0.865 by the target) land on the target's K10, W11, N13, F18, F20,
   D29, F31, H33 (9 contact residues, all aligned): W11, F18, F20, F31, H33, K10 are among them.
5. Credit rise of the unit near 0.9 to 10 (the earlier rises: test 1 +9.64, test 2 +0.90 on the stored 80 files), far below its ceiling
   (about 6320 + 79 for the stored search).
RecA (P0A7G6, 353 residues): 193 of 597 files skipped; the partners ADP, the ATP analogue AGS, MG and DNA (`nucleic_acid:dna`: 3 hits, E near
0.42), DTP, ANP; product test RecA 0.22 against RadA 0.08 ("Protein RecA" 35/57 hits with partners; RadA 7/15).
Order I expect from the head's model: `structure_search` afdb-swissprot (as in the earlier runs), then either `structure_search` pdb100
(with the held model) or `site_correspondence annotated`, then `partner_contacts` on the pdb100 search; `site_correspondence catalytic`
for afdb; the head ends by its estimator when every offered action's forecast (share x ceiling, and the ceilings of repeats are 0)
is below the expected seconds times 0.006, or by having nothing left to offer. At most 1 pdb100 search per run (3 Foldseek tickets cap).
