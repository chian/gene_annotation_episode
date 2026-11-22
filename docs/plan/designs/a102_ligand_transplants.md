# A102 tool `ligand_transplants` (P3 of `a102_tree.md`): a place for the ligand

Design by the lead, 2026-11-21. Facts of the service: `runs/a102_service_probe/alphafill/NOTES.md` (probe of 2026-11-21, every
fact there has its URL; what is marked NOT VERIFIED there is not relied on here).

## The question, and why it is this axis's own

Which ligands and cofactors have a place in the target's model, as they sit in solved homologs? AlphaFill
(https://alphafill.eu, Hekkelman et al. 2023, https://www.nature.com/articles/s41592-022-01685-y) takes an AlphaFold DB model,
finds solved homologs (PDB-REDO; more than 25% identity over at least 85 aligned residues), superposes each ligand's surroundings
locally on the model (all backbone atoms within 6 A of the ligand) and reports, per transplant, how well the surroundings fit
(`local_rmsd`) and how much the placed ligand collides with the model's atoms (the transplant clash score). No sequence method and
no other test of this axis measures either: `structure_search` measures the fold, `site_correspondence` the candidate's site
residues, `partner_contacts` what a hit is bound to in experiment and whether the contact residues correspond. This test asks
whether the ligand physically fits where the homolog holds it.

It is a tool (one request that answers in about a second, then arithmetic), offered only for a held model whose origin is
`alphafold_db` (AlphaFill is keyed by the accession). A target with an ESMFold model is not offered it. Uploading a model to
AlphaFill is possible by its manual and is not used (a job on someone's server: a heavy route, recorded for later).

## Candidates

Kind `ligand`, named exactly as `partner_contacts` names them: `ligand:<PDB chemical component id>`, the component of the SOLVED
donor entry (AlphaFill's `compound_id`). AlphaFill's `analogue_id` (what it placed in the model, e.g. ATP for a donor's ANP) is
kept on the sheet as a fact and names no candidate. Reason: a ligand seen bound by `partner_contacts` and transplanted here from
the same solved entry must be ONE candidate, so that the second test measures a candidate the first listed and the top-two
differential can act between ligands. (Known and not solved here: ADP, ANP, AGS and ATP at one site are four candidates.)

The additive list (BioLiP's list under `forms/structural_homology_evidence/biolip_ligand_list/`) is applied as in
`partner_contacts`: a listed component is recorded on the sheet as `additive` and gives no candidate (RecA: the five sodium rows).

## Measurement (the sheet `a102_ligand_transplants_sheet_v1`)

Per transplant (a row; facts copied from the response, weighing nothing unless stated): donor `pdb_id`, `pdb_asym_id`,
`compound_id`, `analogue_id`, alignment `identity` and `length`, `global_rmsd_A`, `local_rmsd_A`, `clash_score_A`, `clash_count`,
`transplant_atom_count`, `pae_mean`, `additive`, and `target_residues` (the distinct target residue numbers of the response's
clash `distances` rows: the model's residues near the placed ligand; UniProt numbering).

Two degrees, each the axis's kernel `1 / (1 + (x / s)^2)` with the scale `s` set at AlphaFill's own published boundary between
high and medium confidence (the paper's validation; the web table colours by the same values), so that a transplant at the
boundary has degree one half and the fall is gradual, never a cut:

| degree | fact | scale `s` | AlphaFill's boundaries (paper) |
|---|---|---|---|
| `fit` | `local_rmsd_A` | 0.92 A | above 0.92 A medium, above 3.10 A low confidence |
| `no_clash` | `clash_score_A` | 0.64 A | above 0.64 A medium, above 1.27 A low confidence |

A transplant's value is `fit x no_clash`, in [0, 1]. At the low-confidence boundaries the degrees are 0.081 and 0.203.
The donor's identity, the global RMSD and the PAE weigh nothing: fold resemblance is `structure_search`'s measurement and is not
counted again here; the paper gives no boundary for PAE.

A candidate's value in the test is the value of its BEST transplant, not a mean. Reason (AlphaFill's placement rule, paper,
Methods step 6, quoted in the notes): it places a compound again only when its centroid is at least 3.5 A from an identical one
already placed, so several transplants of one compound are different places, not replicates of one measurement; the question is
whether the ligand has a place. The sheet lists every transplant with its value; `candidate_measurements` gives the credit one
row per candidate, the best.

The grader holds no boundary: it copies the facts and applies the two scales, which are constants of the sheet with their source.

Outcomes that are not failures: HTTP 200 with `hits` null (the model exists, nothing was transplanted: CspA) is a graded sheet
with no rows, status `no_transplants`; HTTP 404 with AlphaFill's not-found body is `no_alphafill_entry`. Both count as the test
having been run for that model (not offered again) and give no candidate. Any other status, a body of another shape, or more
distinct non-additive compounds than `ELIGIBLE_COMPOUNDS` raises.

Recorded as facts: `alphafill_version`, `date`, the model file AlphaFill used (AlphaFold DB v4 at the probe) and whether its
version differs from the held model's. Only AlphaFill's numbers are used, never its coordinates, so the held model's frame does
not enter.

## Test, weight, credit, ceiling

Test name `ligand_transplant:alphafill@<source>`; family `ligand_transplant`, `TYPICAL_STRONG_VALUE` 1.0 until real runs give
the family's typical strong value (as the other families). Credit is the head's unchanged top-two rule: a ligand first valued
here earns its entry once; if the test measures at least two ligand candidates listed before it, the top two earn the
difference of their moves.

Ceiling, proved: every candidate is a non-additive compound AlphaFill can transplant, and AlphaFill transplants a fixed list
("Currently, we are transplanting 2,694 different compounds", paper); the unit raises if a response holds more distinct
non-additive compounds than that, so the bound holds by construction. A value is at most 1, so the entries of new candidates
are at most `w x ELIGIBLE_COMPOUNDS` and the one differential at most `w`: `ligand_transplant_test_ceiling = w x (2694 + 1)`
when at least two ligand candidates are listed, else `w x 2694`; 0 once the test has been run for the held model. The bound is
constant and loose (RecA: 14 candidates); with a constant ceiling the forecast (share x ceiling) is the mean past gain.

## Records

The response is kept as a labelled data product of a new kind `ligand_transplant_results`; the sheet as `tool_grading_sheet`
(`record_grading_product`), as the other two tools.

## Prediction (written before the real runs; numbers from the direct check on the stored probe responses go below)

CspA (P0A9X9): status `no_transplants`, no candidate, rise 0. RecA (P0A7G6): 33 transplants, 5 additive (NA), 14 ligand
candidates; rise = the sum of the 14 best-transplant values when no ligand is listed before (no differential).

### Prediction filled from the direct check (2026-11-21)

RecA (P0A7G6): 33 transplants, 5 additive (NA), 14 candidates; CspA (P0A9X9): `no_transplants`, no candidate, rise 0; `ZZZZZ9`:
`no_alphafill_entry`, no candidate. Best value per RecA candidate (value = fit x no_clash of its best transplant):

| candidate | transplants | best value | best transplant (donor, local RMSD, clash score) |
|---|---|---|---|
| ligand:MG | 9 | 0.9997 | 1XMV A, 0.017 A, 0.000 A |
| ligand:CA | 4 | 0.9665 | 5JRJ A, 0.162 A, 0.038 A |
| ligand:ALF | 2 | 0.9606 | 3CMT A, 0.186 A, 0.000 A |
| ligand:MN | 1 | 0.9537 | 1XMS A, 0.107 A, 0.119 A |
| ligand:POP | 1 | 0.8613 | 2W0M A, 0.354 A, 0.069 A |
| ligand:D48 | 1 | 0.8412 | 5QUB A, 0.153 A, 0.253 A |
| ligand:1NP | 1 | 0.7591 | 4B33 A, 0.179 A, 0.332 A |
| ligand:ADP | 2 | 0.7442 | 3CMT A, 0.194 A, 0.343 A |
| ligand:LZ1 | 1 | 0.7393 | 4B2I A, 0.174 A, 0.354 A |
| ligand:1F1 | 1 | 0.7271 | 5J4H A, 0.182 A, 0.364 A |
| ligand:ANP | 1 | 0.6144 | 1XMS A, 0.481 A, 0.338 A (AlphaFill placed ATP) |
| ligand:GTP | 1 | 0.5852 | 4B2P A, 0.605 A, 0.281 A |
| ligand:DTP | 2 | 0.4530 | 1UBG A, 0.835 A, 0.293 A |
| ligand:TYD | 1 | 0.3596 | 5LKM A, 0.557 A, 0.651 A |

Predicted rise when no ligand is listed before: the sum, 10.5648 (no differential), at or below the ceiling 2694 w (w = 1). With
ligand:ADP (0.8) and ligand:MG (0.3) listed before: the 12 new entries 8.8209 + one differential |0.7442 - 0.9997| = 0.2554 = 9.0763
(ceiling 2695 w). CspA: 0.

## Direct check (not a real run)

Run through the launcher (`runs/a102_ligand_transplants_check`), script outside the repository; no head episode was run.

* The sheet grader on the stored responses `alphafill_P0A7G6.json` (21 hits, 33 rows, 5 additive, 14 candidates, the table above;
  the ANP row has analogue ATP and 14 target residues 68-75, 97, 101, 104, 263, 265, 266, as the notes record), on
  `alphafill_P0A9X9.json` (`no_transplants`, no rows) and on the not-found body (`no_alphafill_entry`).
* The credit (`differential_credit`) over the RecA candidates as one test: no ligand before, credit 10.564769 = the sum, no
  differential, below the ceiling 2694.0; with ligand:ADP and ligand:MG listed before by an earlier test, exactly one differential,
  of that pair (moves 0.7442 and 0.9997, value 0.2554), rise 9.076339 = 8.820895 + 0.255445; ceiling 2695.0.
* Live: `fetch_alphafill('P0A7G6')`: 200, 141,905 bytes, 21 hits, AlphaFill 2.1.1, graded to the same 33 rows, 5 additive, 14
  candidates; `fetch_alphafill('ZZZZZ9')`: 404, `no_alphafill_entry`.
* The head's check and options on a made-up summary: an AlphaFold DB model is offered once; an ESMFold model, an unknown model and a
  model already tested are refused with the fix list. All edited modules and the head episode import.
* Not verified: the unit `ligand_transplants` against a real store (custody writes), the model's choice of the tool, the forecast
  controller with the new ceiling version (`a102_ceiling_v1`).
