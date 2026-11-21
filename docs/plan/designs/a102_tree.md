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

## The tree (round 1 is the pattern; the owner's plan decision D27: one pattern in one branch first)

```
structural_homology_evidence      HEAD. Model-routed. Forecast yield controller, differential credit (SOP 7 to 9).
└─ structure_search               CHILD. One search of one structure database with one model of the target = one test.
│     get_model   tool of the child: obtain a model of the target from one source (round 1: alphafold_db, esmfold)
│     estimate    gated, from the estimate ledger          (the job-child shape of SOP Step 4)
│     launch      submit the search to the Foldseek server
│     fix         only after a failed launch
│     monitor     one status request after a stated wait
      extract     fetch the result, name the hits, grade: one unit
```

The head has no `reason` action (the owner, 2026-11-21: "i don't see why reason needs to be an explicit child"). In A101
it is an action whose ceiling is always 0, so the gate never lets it run; an action that can never be taken is not offered
here. The head's actions are only the ones that can earn; when none is worth its cost the yield controller stops the episode.

Later rounds, in this order, each only after the one before ran for real: (2) `pdb100` and `cath50` as databases of
`structure_search` (their hits need a name lookup: PDB chain to UniProt; CATH domain to superfamily), and the model source
`rcsb_pdb` (an experimental structure of the identical sequence); (3) the head tool `pairwise_structure_alignment`
(US-align, local; the counterpart of `pairwise_blast`); (4) a local structural all-vs-all of the candidates' structures
(the counterpart of `all_vs_all`). Functional-site geometry (catalytic residues, pockets, interfaces) is deferred as
functional regions were in A101 (`docs/plan/DEFERRED_functional_regions_joint_credit.md`).

## Tool or child (SOP Step 2), one line each

- `structure_search` is a child: the search is a ticketed job on an outside service (submit, poll, fetch), which SOP Step 4
  makes a job child; and its steps are choices of its own model (which model source, when to monitor).
- `get_model` is a tool OF THAT CHILD, not a head action. Reason: a model of the target is a prerequisite, not evidence for
  an annotation, so as a head action its ceiling would be 0 and the forecast gate would never let it run. The owner's
  precedent: database preparation "almost is a tool of the all vs all blast" (`all_vs_all_episode.md`). The child's own
  credit counts the held model as one of its units (completion controller), and the child returns the model as a labelled
  data product, so a later commission passes the held model and `get_model` is not needed again.
- Why `get_model` is the model's choice and not code inside `launch`: whether a source has the target is unknown until
  asked (AlphaFold DB holds only sequences in UniProt), so a source can answer `not_found` (a completed unit that holds
  nothing) and the child's model then chooses another source. The sources differ in origin, which the axis must keep.
- The lookups inside `get_model` are single HTTP requests that answer in under 20 s (`a102_services.md`): one unit.

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

- Credit: the owner's differential credit, unchanged in rule (entry on positive evidence, differentials for tests after both
  candidates are listed, never falls). A102 has its own definition record (`A102DifferentialCredit`) and its own copies of
  the arithmetic and the measurements reader under `LIB/grading/structural_homology_evidence/` (the repository's per-axis
  library convention; A101's modules name A101's sheet families and stay untouched).
- Ceilings: `structure_search` = the proved bound of one search test (the hits it can name x the family weight, by
  `test_ceiling`, as A101's `bvbrc_blast`); 0 for a search of a database and model already held or commissioned.
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
