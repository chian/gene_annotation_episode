# A102 child `partner_cofolding`: does a proposed ligand fit the target (tree row P7)

Status: design, 2026-11-22. The owner: "6 seems like a very natural thing to do as a test and 7 follows naturally. go for it."
Tree row P7 of `a102_tree.md`; the Polaris setup and route are described there.

## What it measures

The target's sequence is co-folded by Chai-1 with one ligand at a time, the ligands being candidates the head already holds
(kind `ligand`, named `ligand:<PDB chemical component id>` by `partner_contacts` and `ligand_transplants`). The result is
structural compatibility as the model predicts it, never measured binding.

Fields Chai writes per sample (`scores.model_idx_<k>.npz`, read from the GPU check): `aggregate_score`, `ptm`, `iptm`,
`per_chain_ptm`, `per_chain_pair_iptm`, `has_inter_chain_clashes`, `chain_chain_clashes`. With two chains, `iptm` is the
interface score of that pair.

- A sample's value: `iptm`, or 0 when `has_inter_chain_clashes` is true. The grader holds no threshold.
- A candidate's value in the test: the mean over the five samples (replicates of one test).
- Kept on the sheet and weighing nothing: `ptm`, `per_chain_ptm`, `aggregate_score`, the clash matrix, the SMILES used and its
  source, the run's seconds.

## The child (SOP Step 4)

`root/a102/structural_homology_evidence/partner_cofolding`: a job child (`estimate`, `launch`, `fix`, `monitor`, `extract`) on a
resource of kind `pbs` (Polaris). The machinery is A102's own job-child module `structure_search_child.py`; its route kind
becomes a field of the application (`structure_search` keeps `foldseek`) and `get_model` is offered only to an application that
names model sources. `structure_search` behaves as before.

- Commission fields: `query_ref` (one protein subject record), `ligands` (2 to 4 distinct held ligand candidates not co-folded
  before for that query), `until` (`launched` or `extracted`), `resource_id` (a bound `pbs` resource). The allocation is the
  run's setting, not the model's: account `IMPROVE_Aim1` (owner, 2026-11-23), queue `debug`, `select` `1:system=polaris`, walltime `00:30:00`,
  filesystems `home:eagle`.
- Prepare: the target sequence from the subject record; each ligand's SMILES from the RCSB chemical-component service
  (`data.rcsb.org/rest/v1/core/chemcomp/<id>`, `pdbx_chem_comp_descriptor`, the `SMILES_CANONICAL` entry; checked live for ATP).
  Staged: `target.fasta`, `ligands.json`, `run_chai.py` (kept in the library). One ligand per GPU, seed 42, no MSA (compute
  nodes are offline), local weights. The job writes `scores.json` (the fields above per ligand and sample).
- Estimate: ledger kind `partner_cofolding:chai1:<number of ligands>`, size field `residues`, first figure 600 s (GPU check:
  133 s for five samples). The duration written is the observed one, queue wait included.
- Extract: fetch `scores.json` and grade in one unit; data product kind `cofolding_results`; sheet
  `a102_partner_cofolding_sheet_v1` as `tool_grading_sheet`. Credit and controller as `structure_search`.

## In the head

- Test `partner_cofolding:chai1@<source>`, family `partner_cofolding`, `TYPICAL_STRONG_VALUE` 1.0 until real runs give it.
- It admits no candidate (the ligands are already listed) and earns at most one differential, the top two it measures: ceiling `w`
  when at least two of its ligands are listed, proved as `site_test_ceiling` is.
- Offered while a protein query holds at least two ligand candidates not yet co-folded as a set. Parking and resume as
  `structure_search`.

## Later, same pattern

DNA and RNA partners (need a partner sequence), Boltz, and Vina docking with the bound cofactor in the receptor.

## Build order

1. Library: SMILES fetch, `run_chai.py`, sheet grader, candidate measurements and ceiling for the family.
2. The child and its head wiring; the route kind made a field of the application.
3. A real run on RecA (14 ligand candidates), prediction written first.

## Direct check on Polaris (2026-11-22)

Through the library's PBS route (`runs/cofold_route_check_1`, handle `cofold_check_20261122_1`, job 7878857): the job program ran
CspA with ATP and ADP, one ligand per GPU, five samples each, no clash flagged. The job waited about 49 minutes in the debug
queue (no free node) and then finished; `scores.json` came back through the route. The scores are one-element lists per field
(Chai's arrays carry a leading batch axis), so the program now writes the unwrapped values; the sheet grader on the real output
(unwrapped): `ligand:ATP` 0.6890, `ligand:ADP` 0.6821 (five samples each; samples within 0.005 of each other). This check
used the CspA sequence as a pipeline check only; it says nothing about whether either ligand binds CspA. The two ligands score
within 0.007, so the value alone does not separate them here. The queue wait is part of what the estimate must learn: the first
figure of 600 s is the run only, and the ledger's observed duration (launch to the first status that showed the end) includes the wait.

## Prediction for the RecA run (written 2026-11-23, before any run)

Setup: RecA (E. coli), a head run with `structure_search`, `ligand_transplants`, `partner_contacts` and `partner_cofolding` offered; the
child takes up to four of the 14 held ligand candidates (the first four available by `best_arguments`).

- The head commissions `partner_cofolding` once at least two ligand candidates are held; it is not commissioned before the ligand
  candidates exist, so it follows `ligand_transplants` or `partner_contacts`.
- The job waits in the debug queue 5 to 60 minutes (the one check waited 49); the child's first estimate (600 s) is therefore too low and
  the ledger row for `partner_cofolding:chai1:<n>` records a duration several times larger.
- Per-ligand mean iptm falls between 0.4 and 0.85. Nucleotide ligands (ATP, ADP, ANP-like) score above metal ions and small buffer
  molecules, which Chai handles less well. The two leading ligands differ by 0.02 to 0.2; a difference below 0.02 means the test earns
  almost nothing for that pair.
- No sample is flagged as clashing for the nucleotide ligands; a clash flag is possible for an ion.
- The credit the test earns is the differential of the top two ligands it measures, bounded by its ceiling `w`; it admits no candidate.
