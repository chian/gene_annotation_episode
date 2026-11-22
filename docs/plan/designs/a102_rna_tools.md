# A102 tools for an RNA target: `rna_family_scan` (R1) and `rna_structure_agreement` (R2)

Design by the lead, 2026-11-21. Facts: `runs/a102_rna_probe/NOTES.md` (probe of 2026-11-21: Rfam 15.1, Infernal 1.1.5, three
E. coli RNAs scanned and aligned; every fact there has its path or URL; what is marked NOT VERIFIED there is not relied on).
The tree: `a102_tree.md`, rows R1 to R4.

## The question, and why the tree is not the protein tree

For a protein the axis asks which characterized proteins have this three-dimensional shape and whether their machinery and
partners are in place. An RNA's function is carried first by its secondary structure, and the field's instrument for it is the
covariance model: a family's consensus sequence AND consensus base pairs, built from an alignment in which paired columns
covary. So for an RNA target the questions are (R1) which structured RNA family is this, and (R2) can the target form that
family's base pairs. None of the protein tools is offered for an RNA target and neither RNA tool for a protein.

Today the head offers an RNA target nothing (`credit.py` `queries()` keeps protein targets; `task.py` says a non-protein target
gets no commission). Molecule comes from the held sequence record (`init --molecule rna`). A gene for an RNA supplied as `dna`
is not handled in this round.

## R1 `rna_family_scan` (tool)

One local job of Infernal's `cmscan` over Rfam, by Rfam's documented command for annotating a sequence (docs.rfam.org, quoted
in the notes): `cmscan -Z <Mb> --cut_ga --rfam --nohmmonly --tblout <file> --fmt 2 --clanin Rfam.clanin Rfam.cm <sequence>`,
with `--cpu 1`; `Z` as Rfam defines it (the nucleotides searched, in millions, times 2 for the two strands). It answered in
0.25 to 1.4 s for the three probe RNAs. A tool, shaped as A101's `hmmer_profile_scan` (a local job through the job service,
the database found through a manifest named in the head's settings), in A102's own modules.

The database is Rfam 15.1 (4227 families, CC0), installed under `resources/software/` with a manifest (file, digest, release,
family count), as Pfam is for A101; the Infernal binaries are those already in `resources/software/infernal-1.1.5-install/bin`.

Candidates: kind `rna_family`, named `rna_family:<Rfam accession>` (the name shown is Rfam's identifier of the family; both from
the model file, a looked-up list). Format 2 with the clan file keeps a hit that a better hit of the same clan overlaps and marks
it; such a hit is a candidate too: it is the competing family.

Measurement (sheet `a102_rna_family_scan_sheet_v1`), per hit: family accession and name, clan, bit score, E-value, the family's
gathering threshold GA (from the model file), model from/to and model length, sequence from/to, strand, truncation, the overlap
mark. Facts that weigh nothing: E-value (it depends on `Z`), spans, truncation.

A hit's value: with `x = bits / GA`, `value = x^2 / (1 + x^2)` (one minus the axis's kernel). GA is the bit score Rfam's
curators set per family as the lowest for a member, so a hit at the curated boundary has value one half and the rise is gradual:
probe values rnpB 310.2/100.0 -> 0.906, tRNA-Phe 66.2/29.0 -> 0.839, thiM leader 71.2/54.3 -> 0.632. A family's value in the
test is its BEST hit's (several hits of one family on one sequence are several places, not replicates).

Test `rna_family_scan:rfam@<source>`, family `rna_family_scan`, `TYPICAL_STRONG_VALUE` 1.0 until real runs give it. Credit:
the head's unchanged rule; a family first valued here earns its entry. Ceiling, proved: a candidate is a family of the
database, a value is at most 1, and no RNA family can be listed before the only test that lists them, so there is no
differential: `w x (families in the manifest)`; 0 once the target has been scanned. Constant and loose.

Outcome with no hit: a graded sheet with no rows (`no_family`), no candidate, the test counts as run.

## R2 `rna_structure_agreement` (tool)

Can the target form each candidate family's consensus base pairs? For EVERY family the held scan lists (one call measures the
candidate set, as `site_correspondence` measures a search's candidate set): `cmfetch` the family's model, `cmalign` the hit span
of the target to it (the span, not the whole sequence: with flanks the probe's thiM leader aligned with no pair kept), read the
Stockholm `#=GC SS_cons` line and the target row. Pairs are the matched `<>`, `()`, `[]`, `{}` of the WUSS notation (Infernal
guide, quoted in the notes); pseudoknot letters name no pair here.

Per family: consensus pairs `P`; pairs with both partners present in the target; of those the canonical ones (AU, GC, GU).
Value = canonical pairs / `P`, in [0, 1]: the share of the family's base pairs this sequence can form. Probe: rnpB 98/102 =
0.961; thiM span 21/28 = 0.750; tRNA-Phe 21/21 = 1.0. Facts on the sheet that weigh nothing: per consensus stem (the maximal
helices of `SS_cons`, by `calculations/rna_structure_topology.parse_rna_topology` on the nested brackets) its pairs, pairs
present and canonical; the counts of stems wholly formable, partly, and not at all; inserted target residues and consensus
positions with no target residue. No boundary decides "kept" or "lost": the fractions are the record.

It tells candidates apart only when at least two families are listed (an RNA that hits two families of one clan, such as the
small-subunit rRNAs of the three domains, or tRNA and selenocysteine tRNA): then the top two differ by the pairs each lets the
target form. With one family listed it can earn nothing under the head's rule (no new candidate, no pair to compare), so it is
offered only when the held scan lists at least two families and they are not yet measured. Ceiling: `w` (one differential);
0 otherwise. Test `rna_structure_agreement:rfam@<source>`, family `rna_structure_agreement`, 1.0 until real runs.

The bit score already rewards pairs, so R2 is not independent of R1; what it adds is the explicit structural count per family,
compared between families. Later, light, and recorded here so they are not lost: the target's own thermodynamic fold compared
with the consensus (ViennaRNA 2.8.0: a 13.9 MB wheel exists, its licence allows research use; not installed) is the independent
form of R2; a curated structure of the exact RNA (RNAcentral `/api/v1/rna/<URS>/2d/`, found by sequence md5) is R3, to be used
only when its source is not Rfam's own model (else it is circular). Probing data (R4) has no reachable source.

## Head

For an RNA target of the scope: `rna_family_scan` offered until run; `rna_structure_agreement` offered as above. Candidates of
kind `rna_family` are shown in the decision and the final output as the other kinds are. Nothing else of the head changes; the
credit definition's version rises (new families of tests).

## Prediction (written before the real runs)

E. coli RNase P RNA (rnpB, 377 nt): the scan lists RF00010, value 0.906, rise 0.906; one family, so `rna_structure_agreement` is
not offered; the head ends after the scan. thiM leader (181 nt with flanks): RF00059, 0.632; the same. A third RNA expected to
hit two families (selenocysteine tRNA, E. coli selC: RF01852 and RF00005; NOT VERIFIED before the direct check) is the test of
`rna_structure_agreement` and of a differential between RNA families. CORRECTED by the direct check (below): selC hits ONE family,
RF01852 (tRNA-Sec), value 0.761; RF00005 (tRNA) does not reach its GA on it. So selC ends like rnpB, after the scan, and is no test
of `rna_structure_agreement`; the test is E. coli 16S rRNA (four families of one clan, differential 0.0663).

## Direct check (not a real run)

2026-11-21. Run through the launcher (`runs/a102_rna_build_*`), scripts outside the repository, no head episode and no model. The
units were run against an in-memory store and a stand-in for the job service that runs the very command the unit builds, so the
custody writes and the job service are NOT verified. Test sequences (not in the repository): `runs/a102_rna_probe/seq/`: `rnpB.fa`,
`trna_phe.fa`, `thiM_leader.fa` (probe), `selC.fa` (RNAcentral URS00005A30CB, `https://rnacentral.org/api/v1/rna/URS00005A30CB/`,
91 nt, "Escherichia coli K-12 Selenocysteine transfer RNA"; found by `https://www.ebi.ac.uk/ebisearch/ws/rest/rnacentral?query=
selenocysteine AND TAXONOMY:83333`) and `rrs16S.fa` (URS00005CADE5, 1542 nt, "Escherichia coli K-12 Bacterial small subunit
ribosomal RNA"). Rfam 15.1 installed in `resources/software/rfam-15.1/` (not committed: `resources/` is ignored as a whole).

**Scan sheet** (`a102_rna_family_scan_sheet_v1`), from the three probe tblout files and from a fresh `cmscan` by the command
`job_argv` builds (same bit scores; E-values follow `-Z` of each run):

| RNA | family | bits | GA | x | value | olp |
|---|---|---|---|---|---|---|
| rnpB (377 nt) | RF00010 RNaseP_bact_a | 310.2 | 100.0 | 3.102 | 0.9059 | `*` |
| tRNA-Phe (76 nt) | RF00005 tRNA | 66.2 | 29.0 | 2.283 | 0.8390 | `*` |
| thiM leader (181 nt) | RF00059 TPP | 71.2 | 54.3 | 1.311 | 0.6323 | `*` |
| selC (91 nt) | RF01852 tRNA-Sec | 83.8 | 47.0 | 1.783 | 0.7607 | `*` |
| 16S rRNA (1542 nt) | RF00177 SSU_rRNA_bacteria | 1579.1 | 50.0 | 31.58 | 0.9990 | `^` |
| | RF01959 SSU_rRNA_archaea | 1024.6 | 50.0 | 20.49 | 0.9976 | `=` |
| | RF02542 SSU_rRNA_microsporidia | 724.7 | 50.0 | 14.49 | 0.9953 | `=` |
| | RF01960 SSU_rRNA_eukarya | 693.9 | 50.0 | 13.88 | 0.9948 | `=` |

The three expected values 0.906, 0.839, 0.632 are reproduced. selC: one hit (tRNA-Sec), no tRNA hit. The 16S hits are all of clan
CL00111 members overlapped by the better bacterial hit and are kept, with the mark (`^` the best of the overlap, `=` overlapped by a
better hit): the scan has three overlapped hits. Note for the real runs: a hit far above GA has a value near 1 (x^2 / (1 + x^2)), so
the scan's value separates the 16S families by thousandths; the structure test separates them by tenths.

**Agreement sheet** (`a102_rna_structure_agreement_sheet_v1`; one cmfetch + cmalign of the hit span per family, by
`infernal_align_driver`): the probe's counts are reproduced exactly, and the stems, computed on the consensus (match columns, so an
insertion of the target cuts no helix), are the probe's (rnpB 21 stems, 17 wholly formable; thiM 7 and 4; tRNA 4 and 4).

| RNA vs family | consensus pairs | both present | canonical | value | stems (formable / partly / not) | inserted residues | unoccupied positions |
|---|---|---|---|---|---|---|---|
| rnpB vs RF00010 (span 2-377) | 102 | 101 | 98 | 0.9608 | 21 (17 / 4 / 0) | 26 | 17 |
| thiM span vs RF00059 (49-145) | 28 | 23 | 21 | 0.7500 | 7 (4 / 2 / 1) | 3 | 11 |
| tRNA-Phe vs RF00005 (1-73) | 21 | 21 | 21 | 1.0000 | 4 (4 / 0 / 0) | 2 | 0 |
| selC vs RF01852 (1-91) | 30 | 30 | 30 | 1.0000 | 5 (5 / 0 / 0) | 1 | 1 |
| 16S vs RF00177 (1-1542) | 462 | 455 | 433 | 0.9372 | 107 (85 / 19 / 3) | 26 | 17 |
| 16S vs RF01959 (6-1540) | 457 | 423 | 398 | 0.8709 | 99 (69 / 24 / 6) | 20 | 93 |
| 16S vs RF02542 (6-1537) | 366 | 359 | 334 | 0.9126 | 84 (62 / 18 / 4) | 124 | 53 |
| 16S vs RF01960 (6-1537) | 447 | 376 | 348 | 0.7785 | 109 (71 / 22 / 16) | 19 | 476 |

**Credit** (`candidate_measurements.candidate_table` over the held sources; fake reader holding the real sheets):

* one family (rnpB, selC): the scan earns the entry, = the family's value (0.905859; 0.760709), no differential; ceiling of
  `rna_family_scan` before 4227.0 (= w x families of the manifest), after 0.0; `rna_structure_agreement` is not offered and its
  ceiling asked for the scan is 0.0; the request is refused (`scan_lists_fewer_than_two_families`).
* four families (16S): the scan earns the four entries, 3.98672, no differential. `rna_structure_agreement` offered with ceiling
  1.0; the test earns exactly one differential, of the top two after the scan (RF00177 0.999 and RF01959 0.9976), value
  |0.9372 - 0.8709| = 0.066332 (credit 4.053052), at or below the ceiling 1.0; a second agreement request for the scan, and a second
  scan of the target, are refused.

**The head's offered actions** (`task.offered_actions`, settings with one local resource; made-up summaries of the real sheets): RNA
target before the scan: `rna_family_scan` (ceiling 4227.0, one request option). After a one-family scan: `rna_family_scan` with
ceiling 0.0 and no option (the estimator then finds nothing worth its cost and stops, as for a protein with nothing left to search).
After a two-family (here four-family) scan: `rna_family_scan` (0.0) and `rna_structure_agreement` (1.0, one option). After the
agreement test: `rna_family_scan` (0.0) only. Protein target: none of the RNA tools (with a Foldseek resource: `structure_search`
only; an `rna_family_scan` request for a protein target is rejected by the schema). All edited and new modules, and the head
`episode`, import.

**Units against a stand-in store** (16S): `rna_family_scan`: completed, 4 hits (3 overlapped), 4 candidates; `rna_structure_agreement`:
completed, 4 families aligned and measured, 1732 consensus pairs and 1513 canonical in all; data products: the table, the report, the
grading, four `rna_family_alignments` and the grading; credit 4.053052 as above.

Not verified: the units against the real store and the job service (custody, the job ledger, the fetch of the job's files), the
model's choice of the tools, the forecast controller with the new ceiling versions (`a102_ceiling_v1` for both) and the credit
definition v6, the minus-strand span (`span_of` reverse complements; no minus-strand hit occurred), a family whose consensus has no
pair.

## Real runs (2026-11-21; worktree `gae_rna_bb77b45c1`, commit `bb77b45c1`, real model, local Infernal jobs through the job service, exchange rate 0.002)

The first RNA targets the head has run. Each a fresh workspace and run id (builder: the scratchpad `build_ws_rna.py`: `init --molecule
rna`, the settings `infernal_executable_directory` and `covariance_databases`). All three: exit 0, empty `stderr.log`, `ended_by`
`yield_stop`, no `action_forecast_not_worth_its_cost` refusal, no rise above a ceiling; every credit equals its prediction. Read from
the journals by the lead; no independent check yet.

| target | workspace, run dir, run id | s | unit | action | ceiling | rise | credit after | unit s |
|---|---|---|---|---|---|---|---|---|
| rnpB (377 nt) | `runs/a102_rna_ws_rnpb_1`, `runs/a102_rna_run_rnpb_1_bb77b45c1`, `a102_rna_rnpb_1` | 19 | 0 | `rna_family_scan` | 4227 | 0.9059 | 0.9059 | 13.0 |
| thiM leader (181 nt) | `runs/a102_rna_ws_thim_1`, `runs/a102_rna_run_thim_1_bb77b45c1`, `a102_rna_thim_1` | 17 | 0 | `rna_family_scan` | 4227 | 0.6323 | 0.6323 | 11.7 |
| 16S rRNA (1542 nt) | `runs/a102_rna_ws_rrs_1`, `runs/a102_rna_run_rrs_1_bb77b45c1`, `a102_rna_rrs_1` | 46 | 0 | `rna_family_scan` | 4227 | 3.9867 | 3.9867 | 27.4 |
| | | | 1 | `rna_structure_agreement` | 1 | 0.0663 | 4.0531 | 14.1 |

Families at the end: rnpB RNaseP_bact_a 0.906; thiM TPP 0.632; 16S SSU_rRNA_bacteria 1.936 (scan 0.999, agreement 0.937),
SSU_rRNA_microsporidia 1.908 (0.995, 0.913), SSU_rRNA_archaea 1.869 (0.998, 0.871), SSU_rRNA_eukarya 1.773 (0.995, 0.779). The true
family leads in each. After a one-family scan the only offered action had ceiling 0 and the estimator ended the head after one unit.

What the runs show and is left as it is: the scan's value saturates for a hit far above its family's threshold, so the four 16S
families enter at nearly 1 each (bit scores 1579, 1025, 725, 694) and it is the agreement test that separates them; the agreement
value is a share of each family's OWN consensus pairs, so a smaller model (microsporidia, 366 pairs) can stand above a larger one
(archaea, 457) that fits worse in absolute pairs. Not exercised in a real run: a hit on the minus strand; `no_family`; a family with
no consensus pair.

### The protein side after the RNA change, and the independent check (2026-11-21)

RecA again from the same worktree (`bb77b45c1`): workspace `runs/a102_lt_ws_reca_2`, run dir `runs/a102_lt_run_reca_2_bb77b45c1`, run id
`a102_lt_reca_2`, exit 0, 1052 s, 5 units (search, `ligand_transplants`, search, `partner_contacts`, `site_correspondence`), `yield_stop`,
no refusal, credit 29.047012492406107: equal to the last digit to the run before the RNA change (`a102_lt_reca_1`), the units in another
order. Leading: Protein RecA 1.782; ligands MN 1.432, MG 1.100, CA 1.085.

An independent read-only check of the six runs (three with `ligand_transplants`, three RNA) found no discrepancy: every credit, unit
table and stop matches the journals; five RecA ligand values recomputed by hand from the stored AlphaFill answer and every RNA family
value recomputed from bits and GA match; the 16S differential equals |0.93723 - 0.87090| exactly; the `cmscan` command run is the
design's. Not confirmable from the final output, which lists the leading 10 products and 20 partners only: the hidden part (0.426) of
RecA's `partner_contacts` rise and RecA's one nucleic-acid candidate, which the output does not show.
