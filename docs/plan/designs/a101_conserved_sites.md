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
- The credit's measurement: see the section of 2026-11-21 (the count of new sites x the weight W = 1 / E) at the end of this note.

## Direct check on R1's stored records (NOT a real run; recomputed from a copy of `runs/a101_returns_ws_R1`, `runs/a101_conserved_direct`)

R1's four alignments, graded by `conserved_sites` with no service and no model: MSA1 29 new distinguishing sites; MSA2 5 new sites (one measurement, of the generic "Cold shock protein of CSP family" product only: no other candidate underwent that test, so no differential); MSA3 2 new sites (the same single candidate); MSA4 0 new sites (no measurement). 3 of R1's 4 alignments add new sites; the large gain is the first.

## Run C1: setting

Target CspA (UniProt P0A9X9, 70 residues), a FRESH workspace `runs/a101_conserved_ws_C1`, run `runs/a101_conserved_run_C1`, run id `a101_conserved_C1`; local and BV-BRC resources, Pfam, the yield and children settings of R1's continuation file, the global ledger. Live limits: at most 1 Homology, 3 MSA and 2 MetaCATS jobs; I stop the run's unit at the commission that would exceed one.

## Run C1: observed (`runs/a101_conserved_run_C1`, workspace `runs/a101_conserved_ws_C1`, run id `a101_conserved_C1`; completed, exit 0, 791 s)

Head's actions in order, credit after each: (1) `hmmer_profile_scan` 0.8198; (2) child `bvbrc_blast` (blastp, bacteria-archaea, until extracted; 4 child units, credit 4.0) 5.1003; (3) to (18) sixteen `reason` commits, credit 5.1003 each (marginal 0.0); the estimator stopped the head at the 16th of them (18 units, `yield_stop`). 16 units followed the last gain.
Jobs: 1 Homology, 0 MSA, 0 MetaCATS (no limit was approached; I did not stop the run). No alignment, so no conserved-site measurement was exercised in a real run.
Cause, from the model's own request (call 7): `msa_options` showed the held search with `candidates: []`, so `bvbrc_msa` was never offered (and so `bvbrc_metacats` was not). `bvbrc_msa_alignment.msa_options` (LIB/tools/.../bvbrc_msa_alignment.py, line 109) builds the test name `database_search:<provider>:<program>:<database>` without the `@<source reference>` that commit `f227c34a8` added to every test name in `candidate_measurements`, so no candidate's `tests` list matches it. This is a defect brought in by `f227c34a8`; the file is outside what this change may edit, so it is not fixed here. Against the prediction: scan, blast and credit 5.1003 as predicted; no MSA (predicted 0.9) because it was not offered.

## Run C2: setting

After the lead's fix `2111b654f`; a FRESH workspace `runs/a101_conserved_ws_C2`, run `runs/a101_conserved_run_C2`, run id `a101_conserved_C2`; everything else exactly as C1. Limits: at most 1 Homology, 3 MSA, 2 MetaCATS jobs; a guard stops the run's unit at the commission that would exceed one.

## Run C2: observed (`runs/a101_conserved_run_C2`, workspace `runs/a101_conserved_ws_C2`, run id `a101_conserved_C2`; STOPPED BY ME at the 3rd MetaCATS commission)

Head actions in order: scan; `bvbrc_blast`; `bvbrc_msa` (3 candidates, per_candidate 10); `bvbrc_metacats` (alignment 1); `reason`; `bvbrc_msa`; `bvbrc_msa`; `bvbrc_metacats` (alignment 2); then a 3rd `bvbrc_metacats` commission (alignment 3), at which the guard stopped the unit (`systemctl --user stop`) before any estimate or launch. Jobs submitted: 1 Homology, 3 MSA, 2 MetaCATS (the limits exactly); no second MetaCATS on one alignment was tried, so no reuse refusal was seen.
New distinguishing sites per alignment (direct recomputation on a copy of the stored records, `runs/a101_conserved_direct_c2`): A1 29 new; A2 5 new (one measurement, of the generic "Cold shock protein of CSP family" product); A3 2 new (the same candidate). 5 completed head units followed the last gain and the estimator had not stopped the head.

## 2026-11-21: the alignment's value is a count of new sites times a weight; the ceiling is read from the current state

The owner's words, verbatim: "ceiling is a function that has to be how much max credit from this current state"; "you should know that a second MSA is going to earn very very little. that's the point of tying to ceiling values. MSA can only add so much more now"; "the residue conservation pattern in one group vs another helps differentiate function ... the same residue pattern on the same conserved sites should not add anything... and so maybe that is what you should be recording, i.e., the number of conserved region matches"; "i think you have to add a weight factor to MSA scoring yes? that will fix it"; "so if you expect 10 conserve sites per protein on average, you would make the weighting 0.1 -- now I don't know how many conserved regions there generally are, so you will have to figure that out".

The measurement. Evidence is cumulative over the head's alignments in arrival order; only sites no earlier alignment identified count (a site is identified by target position, the group's conserved residue and the candidate, matched or mismatched). For each candidate with at least one new distinguishing site, one measurement in the alignment's test (none for a candidate with no new site):

- value = (number of its new matched sites) x W, with W = 1 / E and E = `EXPECTED_DISTINGUISHING_SITES`; mismatched sites give no value (the sheet records them);
- the measurement record also keeps fraction = new matched / (new matched + new mismatched), the weight W and the counts of new matched and new mismatched sites.

The measurement (count x W) is then weighted by the msa sheet's weight like every test's value (`differential_credit.SHEET_WEIGHT`: one over the sheet's typical strong value, 12 new sites x W for the msa sheet). The raw value is not capped at 1 (the other tests' raw values stay in [0, 1]); a candidate's msa sheet cannot exceed L x W before weighting, since a site counts once.

E = 7, derived (direct check, 2026-11-21; `runs/derive_e_1`, copies of the workspaces) from the stored real alignments graded by the current `conserved_sites`: runs a101_conserved_ws_C2 (3 alignments), a101_returns_ws_R1 (4; its first two equal C2's), a101_msa_ws_M1 (1), a101_msa_ws_M2 (1; the same as metacats_ws_C1's), 7 distinct alignments, all of E. coli CspA (70 residues). Per candidate per alignment, the distinguishing sites (matched + mismatched, at a target position), 23 values over the distinct alignments: 3 3 4 4 5 5 5 5 5 6 7 7 7 8 11 12 12 12 12 14 14 15 15; median 7, mean 8.3 (per 100 residues: median 10, from 4.3 to 21.4); including the duplicated alignments, 32 values, median 7, mean 8.7. Every target had 70 residues, so whether length matters cannot be told from this data: E is the median count. It is re-derived as more alignments (and targets of other lengths) accumulate; with other lengths a per-residue figure x the target's length may replace it.

The ceiling of `bvbrc_msa` (`HEAD/credit.ceiling`, `msa_value` and `msa_best`; the arithmetic and its proof are in `differential_credit.msa_test_ceiling`; the positions from `candidate_measurements.matched_positions_taken`). For one commission the plan is deterministic (each candidate's top hits, one per distinct sequence), so each candidate's group size is known. A candidate with fewer than `MINIMUM_GROUP_SIZE` sequences is not measurable; fewer than two measurable candidates, or a plan exactly equal to a held alignment's input (a repeat), earns 0. For a measurable candidate c, m_c = (the target positions whose matched site of c, identified by the position, the target's own residue and c, no held alignment identified) x W x the weight of the msa sheet (`differential_credit.SHEET_WEIGHT`) is the most its value can be. The rise of the credit is the entries of the candidates the alignment admits (each at most its m_c) plus ONE differential, the absolute difference of the moves of the top two listed candidates it measures (the highest scores before it; which listed candidates are measured is the alignment's outcome, so any two can be the top two): at most the largest m_c among the listed candidates, and only with two listed candidates eligible. The bound is the sum of the m_c of the candidates not yet listed plus that largest listed m_c (`differential_credit.msa_test_ceiling`, proof in its docstring). With `arguments` None the ceiling is the largest over every commission the head's checks would accept now (`msa_best`), and `best_arguments` names that commission. A group context that differs from every held alignment keeps the open bound: the aligner's columns for a group depend on the other groups in the alignment, so nothing about a candidate already measured carries over.

## 2026-11-21: MetaCATS confirms conserved sites

The owner, verbatim: "It's wrong that it has no credit. i told you it gains credit by confirming conserved sites in comparison to a gene family."

The rule (`candidate_measurements._held_metacats`, `confirmed_site_values`). MetaCATS runs on a held alignment (a `multiple_sequence_alignment` data
product made by `bvbrc_msa`) with the alignment's candidate groups (each group one product candidate's reference sequences: a gene family) and
reports the alignment positions where the groups' residue frequencies differ significantly (p fixed at `bvbrc_metacats_analysis.P_VALUE` = 0.05). A
matched conserved site of a candidate (the `conserved_sites` section of that alignment's sheet: identity (target position, residue, candidate), the
group conserving the target's own residue) is CONFIRMED when MetaCATS finds its column significant. The report is one test,
`msa:bvbrc_metacats:confirmed_sites@<source>` (family `msa`, so the msa sheet weight applies). For each candidate with at least one matched site of
the alignment that no earlier held report confirmed, one measurement: value = (its matched sites confirmed by this report and by no earlier one) x W
(W = 1/E, the alignment's site weight: a confirmed site is one of the sites, so the same scale). Differential credit then works unchanged (a test earns the difference of the moves of the top two listed candidates it measures).

The column mapping. The job takes a DERIVED alignment: the held one without the target's row, every column kept (`derived_alignment`), so a
MetaCATS `Position` is the 1-based column of the held alignment; the sheet's sites carry that column and the target position read through the
target's row (`msa_alignment_sheet.conserved_sites`); a column where the target has a gap has no target position and is identified by nothing.
Verified (direct check, not a real run, on scratchpad copies of `runs/a101_conserved_ws_C2` and `runs/a101_returns_ws_R1`): for all 9 stored
reports (2 in C2, 7 in R1; 4 distinct alignments, 70 columns each, as many as the derived alignments), the residue counts per group of every
significant row equal the counts of the derived alignment's column of the same number (0 differences). Examples (C2, first report): position 3 =
column 3, target residue G = target position 3, CspA's matched site (3, G) confirmed; position 8 = column 8, target I = position 8, CspA's (8, I)
confirmed; position 15 = column 15, target D = position 15, CspA's and CspB/CspG/CspI's (15, D) confirmed. Not exercised by the stored data: none of
these alignments has a target gap or an all-gap derived column (every target row is ungapped). The same check found the table reader kept a comma in
a residue (`6 A, 1 P` read as `A,`); fixed in `read_chisq_table` (the per-group fractions of the sheet were affected, not the positions).

The ceiling (`HEAD/credit.metacats_value`, `metacats_best`; proof in `differential_credit.metacats_test_ceiling`). For the named alignment, per
candidate of its groups m_c = (its matched sites in that alignment not yet confirmed) x W x the msa sheet weight (a report can confirm only sites of
the alignment, each once); the bound is the entries of unlisted candidates (each at most its m_c) plus ONE differential, the difference of the moves of the top two listed
candidates the report measures (at most the largest listed m_c; `differential_credit.metacats_test_ceiling`, the same as for an alignment). 0 for an alignment whose report is held (the reuse check refuses it) or commissioned
and not continued. With no arguments: the largest over the alignments a commission may name now, and `best_arguments` names it (query and alignment).

Direct check (not a real run) on a scratchpad copy of `runs/a101_conserved_ws_C2`, current code: report 1 (alignment 1: CspA, CspB/CspG/CspI, CspC)
confirms CspA 12 of its 12 matched sites and CspB/CspG/CspI 2 of 2 (CspC has none): values 12/7 and 2/7, weighted 1.0 and 0.1667; both already
listed, so the test earns their difference 0.8333; ceiling before it 1.0 (rise 0.8333 <= 1.0). Report 2 (alignment 2) confirms nothing new: CspA's 7
and CspB/CspG/CspI's 1 matched sites there were all confirmed by report 1; ceiling before it 0.0, rise 0. Credit at the end 8.2955 with MetaCATS,
7.4622 without. The third commission the guard stopped (alignment 3) would have had ceiling 0: only the generic product has unconfirmed sites
there (2), and a test measuring one listed candidate earns nothing.
