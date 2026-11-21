# A101: the conserved-site measurement of an alignment (and MetaCATS without a p-value choice)

Written 2026-11-21. HEAD = `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence`; LIB =
`gene_annotation_episode/episodic_workflow/episode_support`. Pattern and earlier runs: `a101_child_returns.md`, `bvbrc_msa_episode.md`,
`bvbrc_metacats_episode.md`, `a101_differential_credit.md`.

## The owner's words (verbatim; they govern)

- "MetaCATS doesn't even help reach much of a conclusion with p values.... that's not the part that matters"
- "the residue conservation pattern in one group vs another helps differentiate function, yes? so in theory, the same residue pattern on the same conserved sites should not add anything... and so maybe that is what you should be recording, i.e., the number of conserved region matches"
- On the lead's rule: "sure that works, just try it to see if the behavior is better now with those two fixes" (one test per job, `f227c34a8`; and this conserved-site measurement).

## The problem seen in run R1 (`runs/a101_returns_run_R1`, resumed as R1d)

The head commissioned 4 MSA jobs and 7 MetaCATS jobs (p 0.05 and 0.01 on each alignment), each earning credit though most repeated what earlier
jobs had shown.

## What is built

| written | the existing function it calls |
|---|---|
| `LIB/grading/sequence_homology_evidence/msa_alignment_sheet.conserved_sites(rows, groups, target_name)`; `grade_alignment` adds its result as the sheet's section `conserved_sites` (no new job) | `grade_alignment` (its parsed rows); constants `MINIMUM_SHARE = 0.8`, `MINIMUM_GROUP_SIZE = 3` ("the owner accepted: at least 80% of the group's sequences share the residue, and the group has at least 3 sequences") |
| `LIB/grading/sequence_homology_evidence/candidate_measurements.new_site_values(sites, seen, target)` and `_held_msa` (replaces the identity-fraction reading) | `_read` (arrival order of `held_sources`), then `differential_credit` unchanged |
| MetaCATS: `bvbrc_metacats_analysis.P_VALUE = 0.05` (fixed; the model no longer chooses it), the sheet's `meaning` text; `P_VALUES = (P_VALUE,)` stays only because the route (`bvbrc_job_route`, not to be edited) checks a job's p-value against it | `grade`, `prepare`, `settings_of`, `reusable_report` (the reuse key's settings no longer differ, so a second MetaCATS of the same alignment is refused by the existing reuse check) |
| MetaCATS's head commission: `p_value` removed from the head's commission fields (`task.bvbrc_metacats_fields`), `msg_to_child._bvbrc_metacats`, the child's `read_from_parent`, `task.py`, `bvbrc_metacats_search` (request and estimate fields, schemas, identity, checks) | the shared `bvbrc_job_child` (unedited: `estimate_fields=()`) |
| the head's `CHILD_DESCRIPTIONS` of `bvbrc_msa` and `bvbrc_metacats` rewritten in plain words | |

`candidate_measurements` no longer reads `metacats_sheet_v1`: MetaCATS gives no candidate measurement; its significant positions stay on its
sheet, which now says they confirm which distinguishing sites are statistically supported (using them as a filter of sites is not part of this
change).

## The rule (the lead's, built exactly)

- Groups: the alignment's candidate groups (the reference sequences of each product candidate); the target is in no group.
- A conserved site of group G: an alignment column where at least 80% of G's sequences carry the same residue (not a gap); G needs at least 3
  sequences in the alignment.
- A distinguishing site: a conserved site of G whose residue differs from the residue another group H conserves at the same column (H conserved
  there too). Each pair of groups at a column is recorded once (`pairs`); each group's site once (`sites`, with the groups it differs from).
- Every column maps to the target's residue position through the target's row; a column where the target has a gap maps to no position and is
  recorded as `target_gap` (neither matched nor mismatched, and identified by nothing).
- A site is identified by (target position, the group's conserved residue, the group's candidate), never by column or job.
- Per candidate group: `matched_sites` = distinguishing sites where the target carries the group's residue; `mismatched_sites` = where it
  carries another residue.
- The credit's measurement (cumulative over the head's alignments, in arrival order): only the sites not identified by an earlier alignment count;
  each candidate with at least one new distinguishing site gets one measurement, value = new matched / (new matched + new mismatched); an
  alignment that adds no new site gives no measurement. The test name stays kind + '@' + source (`f227c34a8`).

## Direct check on R1's stored records (NOT a real run; recomputed from a copy of `runs/a101_returns_ws_R1`, `runs/a101_conserved_direct`)

(Filled in below after the check; see the report of the work.)

R1's 13 graded sources in the head's receipt order, credit after each (conserved-site measurement and one test per job, no service, no model):
scan 0.8198; search 5.1003; MSA1 5.9645 (+0.8642: CspA 1.0, CspB/CspG/CspI 0.4, CspC 0.0 on 29 new distinguishing sites); MetaCATS 4 (0 measurements);
MSA2 5.9645 (5 new sites, one measurement, of the generic "Cold shock protein of CSP family" product only, value 0.0: no other candidate underwent
that test, so no differential); MetaCATS 3 x (0); MSA3 5.9645 (2 new sites, one measurement, 1.0, same single candidate); MSA4 (0 new sites, no
measurement); MetaCATS 3 x (0). 3 of R1's 4 alignments add new sites; the credit moves only on the first.

## Run C1: prediction (written before the run)

Target CspA (UniProt P0A9X9, 70 residues), a FRESH workspace `runs/a101_conserved_ws_C1`, run `runs/a101_conserved_run_C1`, run id `a101_conserved_C1`;
local and BV-BRC resources, Pfam, the yield and children settings of R1's continuation file, the global ledger. Live limits: at most 1 Homology,
3 MSA and 2 MetaCATS jobs; I stop the run's unit at the commission that would exceed one.

1. The head starts as in H1/R1: the profile scan (credit about 0.82), then `bvbrc_blast` (until extracted; credit about 5.0 to 5.1 after it), with the
   search admitting product candidates (CspA product about 0.96, CspB/CspG/CspI and CspC products 0.80 to 0.83, "Cold shock protein of CSP family",
   "hypothetical protein").
2. The model commissions `bvbrc_msa` at least once (probability 0.9) with 3 or 4 candidates and `per_candidate` 10. The first alignment adds many new
   distinguishing sites (R1's first alignment gave 29) and its extract earns about +0.8 (R1 by direct check: +0.86 with CspA 1.0, CspB/CspG/CspI
   0.4, CspC 0.0; the live search may change which products are offered and the numbers).
3. MetaCATS is commissioned at most once per alignment (a second one on the same alignment is refused by the reuse check and comes back as
   feedback without a unit). Every MetaCATS extract earns 0.0 (marginal credit 0.0). Probability the model commissions MetaCATS at all: 0.6.
4. A second or third MSA with another candidate set (probability 0.5 for a second, 0.2 for a third) adds few new sites (R1: 5, 2, 0) and earns 0.0
   to 0.1; an alignment with no new site earns exactly 0.
5. The estimator stops the head after 2 to 5 units that follow the last gain (R1 had 3 + 4 units after the first gain and stopped at 16 units); the
   head makes 6 to 11 units in all, against R1's 16, with at most 2 MSA and 1 or 2 MetaCATS jobs against R1's 4 and 7.
6. No custody error; the ledger gets one row per launch (Homology, MSA, MetaCATS).

## Run C1: observed (`runs/a101_conserved_run_C1`, workspace `runs/a101_conserved_ws_C1`, run id `a101_conserved_C1`; completed, exit 0, 791 s)

Head's actions in order, credit after each: (1) `hmmer_profile_scan` 0.8198; (2) child `bvbrc_blast` (blastp, bacteria-archaea, until extracted; 4 child units, credit 4.0) 5.1003; (3) to (18) sixteen `reason` commits, credit 5.1003 each (marginal 0.0); the estimator stopped the head at the 16th of them (18 units, `yield_stop`). 16 units followed the last gain.
Jobs: 1 Homology, 0 MSA, 0 MetaCATS (no limit was approached; I did not stop the run). No alignment, so no conserved-site measurement was exercised in a real run.
Cause, from the model's own request (call 7): `msa_options` showed the held search with `candidates: []`, so `bvbrc_msa` was never offered (and so `bvbrc_metacats` was not). `bvbrc_msa_alignment.msa_options` (LIB/tools/.../bvbrc_msa_alignment.py, line 109) builds the test name `database_search:<provider>:<program>:<database>` without the `@<source reference>` that commit `f227c34a8` added to every test name in `candidate_measurements`, so no candidate's `tests` list matches it. This is a defect brought in by `f227c34a8`; the file is outside what this change may edit, so it is not fixed here. Against the prediction: scan, blast and credit 5.1003 as predicted; no MSA (predicted 0.9) because it was not offered.
