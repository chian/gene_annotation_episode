# A102 (structural homology evidence): the tree, built the way A101 was built

Status: design, 2026-11-21. Follows `docs/sop/evidence_axis_build_sop.md` step by step. Facts it rests on:
`a102_inventory.md` (what code exists) and `a102_services.md` (what was verified live). The owner's order (2026-11-21):
"can we move to A102 head and follow the same SOP here."

Names: HEAD = `gene_annotation_episode/episodic_workflow/root/a102/structural_homology_evidence`; LIB =
`gene_annotation_episode/episodic_workflow/episode_support`; A101HEAD = `.../root/a101/sequence_homology_evidence`.

## What the axis is for (the process library entry A102, unchanged)

From a supplied sequence only (no name, no accession, no structure): compare the target's structure or model with
functionally characterized proteins; keep each structure's origin (experimental or predicted), the matched extent and the
actual structural statistics; a prediction's confidence describes the model and is not similarity.

## Step 0A: what structure can show that sequence cannot (the derivation; SOP Step 0A)

The first design of this note mapped A101's nodes onto structure. The owner (2026-11-21): "This is all just sequence homology
under another name which is not the point". This section replaces it. Facts: `a102_inventory_structure_specific.md` (the
entry's 14 evidence cases; what code exists) and `a102_tool_survey.md` (what runs today).

Targets: protein (3D) and RNA (2D, rarely 3D). The head learns the molecule type from the subject record
(`ScopedStore.subject_molecule`) and offers only the analyses of that kind.

What the axis's own 14 cases rest on: conserved catalytic residues (Arad3529, TM0936); machinery that is ABSENT in a matching
fold (EnvC resembles LytM but lacks its zinc ligands); an inserted loop that blocks an interaction (BC1793); a ligand-bound
homolog that locates the pocket and its contacts (Cc0300, Cc2672, MJ0056, RidA, Pa0142); docking that proposed a substrate
(HpbD, Lmo2620); and twice that a fold search alone was uninformative (DUF1537, MJ0577). The direct check of the fold search
on CspA shows the same: 130 candidate products, the cold shock family within a few hundredths of each other, CspA not first
(`a102_structure_search_episode.md`).

| # | Evidence | Question it answers | Needs first | Does it today (verified) | Measured | Tells candidates apart? | Another axis could give it? |
|---|---|---|---|---|---|---|---|
| P1 | Fold resemblance | which characterized proteins have this shape | a model | Foldseek server (built: `structure_search`) | B per hit | admits a family; not its members | A101 in spirit (search, name, score) |
| P2 | Functional machinery present or absent | does the target have the candidate's catalytic, binding or metal residues, in place | P1's alignment and coordinates; the candidate's sites | sites: M-CSA API, UniProt features (sparse: CspA none, RecA one), ligand contacts from the candidate's experimental structure (mmCIF) | per candidate: its site residues carried through the structural alignment, residue class kept, distance after superposition (the existing kernel `1/(1+(d/1 A)^2)`, `scoring.py`) | yes: same fold, different machinery | no |
| P3 | A place for the ligand | which ligands or cofactors fit the target as they sit in homologs | a model (an AlphaFold accession for AlphaFill) | AlphaFill API (RecA: 21 transplants, 15 ligand types, with identity, local RMSD, clash) | per ligand: transplant quality | yes, between ligand classes | no |
| P4 | Seen bound, in experiment | what the same or a near-identical protein is bound to in solved structures (ligand, nucleic acid, partner) | the sequence | RCSB sequence search, entry files; contacts computed from coordinates | per partner: contact residues, kept as an observation separate from resemblance | yes | no (A105 reads the papers, not the coordinates) |
| P5 | Arrangement of elements and regions | which helices, strands and loops correspond; what is inserted or missing, and where relative to the sites | P1's alignment; element ranges (already in AlphaFold mmCIF `_struct_conf`) | computed locally | per candidate: elements matched in order; inserted and deleted segments with their place | partly (distant candidates; loops at sites) | no |
| P6 | Surface for a partner | is there an exposed basic or aromatic face (nucleic-acid binders; not everything is an enzyme) | a model | solvent accessibility in the repository's Python (Biopython) | exposed residues by class, clustered | weakly; supports P4 | no |
| P7 | Does the proposed ligand fit | docking of the ligands P3 and P4 name, against decoys | a model, a pocket, ligand files | nothing installed (Vina wheel 6.9 MB, rdkit, meeko; CPU only, no GPU here) | score against decoys; compatibility, never measured binding | yes, between ligands | no |
| P8 | Domains and confidence | which residues are confidently modelled; where the domains are | a model | TED API by accession (RecA 2 domains, CspA 1); pLDDT in the model | boundaries and labels (facts; they shape P1 and P2) | prerequisite | no |
| R1 | RNA family by covariance | which structured RNA family | the sequence | Rfam batch service (tRNA found as RF00005); Infernal installed, `Rfam.cm` (46 MB) not on disk | bit score, model and sequence spans (grader exists) | admits families | A101 in spirit, with base pairs |
| R2 | Does the target form the family's structure | are the family's stems, loops and junctions formable and present | R1's alignment; the consensus structure; a predicted fold | consensus from Rfam; folding needs ViennaRNA (wheel 14 MB, not installed); comparison and topology code exist | consensus pairs the target can form; elements kept, lost, gained | yes | no |
| R3 | Known structure of this RNA | has this exact RNA a curated 2D structure | the sequence | RNAcentral lookup (dot-bracket) | fact; input to R2 | prerequisite | no |
| R4 | Probing assays (SHAPE, DMS) | does measured reactivity agree with the pairing | data for this RNA | no API found (RMDB) | - | - | not reachable now |

The check of Step 0A: only P1 and R1 have a counterpart in A101. The first design was P1 alone.

## The tree derived from the table

```
structural_homology_evidence          HEAD (forecast controller, differential credit). No `reason` action.
│  protein target
├─ structure_search                   CHILD  P1. Built. get_model is its tool (P8's confidence facts come with the model).
├─ site_correspondence                TOOL   P2. One candidate set of one graded search, one site source per call:
│                                            catalytic (M-CSA), annotated (UniProt features), ligand_contacts (the candidate's
│                                            experimental structure). The functional-pocket comparison is this tool with
│                                            ligand_contacts. Inserted and missing segments at the sites (P5) are on its sheet.
├─ ligand_transplants                 TOOL   P3. AlphaFill for the model's accession. BUILT 2026-11-21 (design: `a102_ligand_transplants.md`).
├─ bound_in_experiment                TOOL   P4. Solved structures of the same sequence and what they hold.
├─ surface_faces                      TOOL   P6.
├─ ligand_docking                     CHILD  P7. Local job per ligand, minutes each, iterates over a panel. Needs installs.
│  RNA target
├─ rna_family_scan                    TOOL   R1. Local Infernal against Rfam (the counterpart in kind of A101's Pfam scan).
└─ rna_structure_agreement            TOOL   R2 (with R3 as its input when the RNA is known).
```

Tool or child (SOP Step 2): the tools end within the turn (one to a few requests that answer in seconds, then arithmetic);
`structure_search` is a ticketed job on an outside service; `ligand_docking` runs local jobs of minutes and iterates.

Candidates are of more than one kind: `product` (P1, P2), `ligand` (P3, P4, P7: a chemical component identifier, a controlled
name), `rna_family` (R1, R2). A test measures candidates of one kind; the differential credit is unchanged.

Dependencies: P2 reads P1's alignments and coordinates, so it is offered only when a graded search is held. P3 needs a model
with an AlphaFold accession. P7 needs P3 or P4 to name ligands. R2 needs R1. A model is a product of `structure_search`; no
head action exists only to make one.

Order (distinctive first, then what depends on it): P2 `site_correspondence`; then P4 and P3 (the ligand and partner
evidence, which is what serves a protein that is not an enzyme); then the RNA pair R1, R2; then P6; then P7 (installs,
least reliable); pairwise alignment and a structural all-vs-all of candidates repeat A101's shape and come last, if at all.
Other databases of `structure_search` (`pdb100`, `cath50`) are added when P2's `ligand_contacts` needs experimental hits.

## Heavy tools, later or on HPC (the owner, 2026-11-21: "Starting light is a good idea")

Recorded so they are not lost; none is built. Facts: `a102_structural_aligners.md`, `a102_tool_survey.md`.

| Tool | What it adds | Why not now |
|---|---|---|
| DALI (DaliLite, with a PDB set to search) | the distance-matrix search the axis entry names ("DALI Z score"); the standard for remote similarity; a second search method and so a separate test (Z, TM-score and RMSD are not interchangeable) | the web server works without an email (one search verified: 2.6 min, 2505 hits, 1MJC-A Z 15.4) but has no API and states that it mitigates automated traffic; locally DaliLite needs gfortran (not installed) and a database built from structure files. The owner: "a good reason to do it later or on hpc" |
| Co-folding models (Chai-1, Boltz, AlphaFold 3 class) | the target predicted together with a ligand, DNA or RNA that `partner_contacts` or the ligand transplants name: the proper form of row P7 (does the proposed partner fit), in place of rigid docking; a result is structural compatibility (interface and ligand confidence), never measured binding | need a GPU; this machine has none usable. The owner named Chai among the "other big tools" |
| Docking (AutoDock Vina, gnina, DiffDock) | row P7 in its light form | needs installs (Vina, rdkit, meeko); least reliable of the rows; after the partners are known |
| Local Foldseek with its databases; Merizo or Chainsaw domain splitting | searches without the server's 1000-hit cap; domains for a model with no AlphaFold accession | database downloads; torch |

The standalone aligner is no longer deferred: US-align is installed (`resources/software/usalign-20261019`) and is the
correspondence under `partner_contacts`; the RCSB alignment service (TM-align, FATCAT rigid and flexible, CE) was verified
and is a candidate for a flexible alignment when a rigid one fails.

## Services (verified live, `a102_services.md`)

| Step | Service | Request | Seconds seen |
|---|---|---|---|
| exact sequence to accession | UniProtKB REST | `uniprotkb/search?query=checksum:<CRC64>` | 0.8 |
| accession to model | AlphaFold DB | `/api/prediction/{accession}` then the file it names (needs a browser-like User-Agent) | 0.5 |
| sequence to predicted model | ESM Atlas | `POST api.esmatlas.com/foldSequence/v1/pdb/` (PDB text; pLDDT in the B-factor column, scale 0 to 1) | 0.3 (70 aa), 18 (353 aa) |
| structure search | Foldseek server | `POST /api/ticket` (structure file, `database[]`, `mode`), `GET /api/ticket/{id}`, `GET /api/result/{id}/0` | 6 to 10 |
| names of hits | UniProt REST | accessions with `fields=accession,protein_name,ec,go_id,annotation_score,reviewed` | 0.8 |

No request carries a name, an email or a key. The job route for the Foldseek server is library code (`LIB/jobs`, beside
`bvbrc_job_route.py`, on the generic `ApiJobRoute`); nothing in `episode_runtime`, `method_loop` or `yield_control` changes.

## The search and its measurement (SOP Step 6)

- Round 1 database: `afdb-swissprot` (AlphaFold models of reviewed UniProt entries: every hit is `AF-<accession>-F1-...`,
  so its function name comes from UniProt by accession). Mode: `tmalign`, fixed (the old A102 design pinned Foldseek to the
  global TM-align mode, `LIB/knowledge/structural_homology_evidence/native-structural-homology.md`). The model chooses the
  database; it does not choose the mode.
- One test is one graded source: `structure_search:foldseek:tmalign:<database>@<source reference>`.
- A candidate is a product: the UniProt recommended protein name of a hit (vocabulary `product`, as in A101). Hits are named
  in rank order in batches until the candidates settle (the rule of A101's `bvbrc_hit_metadata.name_hits`); hits never asked
  are reported as not asked.
- The value of one hit is the existing A102 index B (`LIB/grading/structural_homology_evidence/scoring.py`, `geometry`):
  `B = [2 n / (L_target + L_reference)] / [1 + (RMSD / 2 A)^2]`, with n the aligned residue pairs of the reported alignment,
  L_target the length of the supplied target sequence (the target stays the denominator), L_reference the hit's length
  (`dbLen`), and RMSD over the n aligned C-alpha pairs. The server returns the alignment and the hit's aligned C-alpha
  coordinates (`tCa`) but no superposition, so the pairs are superposed by least squares
  (`LIB/calculations/protein_structure_calculations.py`) and the distances given to `geometry`. The sheet keeps the facts
  the entry asks for beside B: aligned pairs, both lengths, coverage of the target, RMSD, sequence identity, and the
  server's own `score` and `eval` (in `tmalign` mode the Foldseek README defines them as the query-normalized TM-score x 100
  and the mean TM-score; kept as reported, labelled with that definition).
- A candidate's value in the test is the mean B of its hits (replicates inside one test, as in A101). The grader holds no
  threshold. The model's pLDDT and origin are kept as facts on the sheet and weigh nothing.
- Sheet weight of the `structure_search` family: 1 until real runs give its typical strong value; then one over that value,
  derived beside the constant (SOP Step 6).

## Credit, ceilings, controller (SOP Steps 7 to 9)

- Credit: the owner's differential credit as A101 counts it (entry on positive evidence; a test earns ONE differential, the
  difference of the moves of the top two candidates listed before it that it measures; never falls). A102 has its own definition record (`A102DifferentialCredit`) and its own copies of
  the arithmetic and the measurements reader under `LIB/grading/structural_homology_evidence/` (the repository's per-axis
  library convention; A101's modules name A101's sheet families and stay untouched).
- Ceilings: `structure_search` = the proved bound of one search test (the hits it can name x the family weight, by
  `test_ceiling`, as A101's `bvbrc_blast`: `w` for the one differential plus the entries of the candidates it can admit); 0 for a search of a database and model already held or commissioned.
- Controller: forecast, with `CEILING_VERSIONS` per action, `outcome_pending`, `resume_action` (the head finishes parked
  jobs) and `best_arguments`, as in A101's head. Exchange rate: 0.006 to start, PROVISIONAL (A101's value; the owner on a
  first figure: "you have to start somewhere that's fine"). It is re-derived from A102's own resolved forecast rows after
  the first real runs, because the rate depends on the credit's scale (SOP Step 9).
- The child's controller: completion, to the sum of its units (model held, estimate, launched, ended, graded).

## Data products (new kinds, EDAM terms to be read in EDAM.tsv by the builder)

`protein_structure_model` (the target's model, with origin `alphafold_db` or `esmfold`, the accession if any, the
residues it covers and the per-residue confidence), `structure_search_results` (the Foldseek result), and A101's existing
`search_hit_metadata` and `tool_grading_sheet`.

## What is deleted

The old A102 head and its children (`execution_job_submission`, `execution_progress_assessment`,
`execution_result_acquisition`, `hpc_work_planning`, `resource_work_submission`, `resource_result_acquisition`, their
`tests/`) are deleted, not kept as `old_*` (`AGENTS.md`, "Removing unwanted code"; SOP Step 14 calls A101's `old_*` folders
"not a pattern to copy"). The head does not import today (`a102_inventory.md`). The head's goal text is carried into the new
`goal.py`. Old library modules tied to the old store are deleted when the rebuild no longer calls them.

## Build order

1. Library, in parallel: (a) the Foldseek job route and the three request functions of `get_model`; (b) the result parser,
   the grader and sheet, the hit naming, the measurements reader and the credit arithmetic, checked directly on the stored
   probe result `runs/a102_service_probe/foldseek/result2_tmalign_0.json`.
2. The child `structure_search`, then the head.
3. Real runs on E. coli CspA and RecA from a pinned worktree, prediction written here first.
