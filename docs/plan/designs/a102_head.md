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
