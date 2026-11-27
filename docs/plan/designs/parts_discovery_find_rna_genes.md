# `find_rna_genes` of the parts discovery head: inventory and mapping

Written 2026-11-24 by the procedure of `parts_discovery_handoff.md`, Part 2, steps 1 and 2, for ONE tool of the head,
against the reference's `hmmer_profile_scan`. The tree is at `71f721701`. Nothing is built. Step 3 (copy) waits for the
owner to see the mapping table and to answer the questions under it.

Why this tool first: of the head's tools it is the closest to the reference tool. Both scan one sequence
against a database of family models with each family's own threshold, as one native job on a local resource, and grade
the table the program writes.

Short names: REF = `gene_annotation_episode/episodic_workflow/root/sequence_homology_evidence`, LIB =
`gene_annotation_episode/episodic_workflow/episode_support`.

## 1. Inventory (facts only)

### What the tool measures (measured on real DNA)

- The program is Infernal 1.1.5 `cmscan` over the covariance models of Rfam 15.1 (4,227 families), by Rfam's documented
  command for annotating a sequence: `cmscan -Z <Mb> --cut_ga --rfam --nohmmonly --cpu 1 --tblout <file> --fmt 2 --clanin
  Rfam.clanin -o <file> Rfam.cm <sequence>`, `Z` = the nucleotides searched in millions times 2 (both strands).
- It reports, per hit: the family (accession, name), its clan, the positions on the sequence, the strand, the bit score,
  the E-value (it depends on `Z`), the span on the model, whether the hit is cut off at an end, and a mark when a better
  hit of the same clan overlaps it. With `--cut_ga` every reported hit is at or above its family's own threshold.
- One family is reported at every place it is found. The E. coli chromosome (4.64 million nt) gave 446 hits; the
  60,001-nt stretch gave 7 (five tRNA, MicA, naRNA4). Files: `runs/parts_survey_1/infernal/`.
- Cost, measured on the chromosome: 19 min 21 s on one CPU, 1.8 GB of memory at most
  (`runs/parts_survey_1/infernal/chrom.time.txt`). The time on the 60,001-nt stretch is in no file I found.
- Installed: `resources/software/infernal-1.1.5-install/bin`, `resources/software/rfam-15.1/Rfam.manifest.json` (name
  `rfam`, version `15.1`, `model_count` 4227; files: the covariance database with its four pressed files, the clan file, a
  family index with each family's name, model length and threshold).

### The reference tool, as it stands in the code

| Where | Pieces |
|---|---|
| `LIB/tools/similarity_search/sequence_homology_evidence/hmmer_profile_scan.py` | Constants `JOB_NAME`, `PROGRAM`, `PROVIDER`, `QUERY_ROLE`, `QUERY_FILE`, `OPTIONS`, `OUTPUTS`, `GRADED_ROLES`, `PRODUCT_KIND`, `PRODUCT_KINDS`. Functions `scan_settings`, `check_profile_scan_request`, `record_scan_product`, `_outcome`, `_job`, `_blocks`, `_families`, `hmmer_profile_scan`. |
| Library it calls | `forms/similarity_search/native_hmmer_contracts.requested_job_from_native` (builds the job); `jobs/resource_local.execute_on_local_resource` (runs it); `grading/similarity_search/sequence_homology_evidence/hmmer_graders.grade_hmmer_native_artifacts` (grades the three texts); `grading/sequence_homology_evidence/scoring` (`hmmer_comparisons`, `comparison_weight`); `grading/sequence_homology_evidence/tool_grading_artifacts` (`retain_tool_grading`, `record_grading_product`); `records/data_products.record_product`; `tools/sequence_homology_evidence/tools` (`enum`, `measurements`, `number`, `ref`). |
| `REF/task.py` | `PROFILE_TOOL`, `DESCRIPTIONS[PROFILE_TOOL]`, `profile_scan_options`, `scans_made`, the tool's option in `selection_schema`, its name in `offered_actions`, its row in `decide` (`tools`, `held_profile_scans`), its check in `action` (`check_profile_scan_request`, rejection category `hmmer_profile_scan_request`), the tool function `profile_scan`, its entry in `TOOLS`. Settings `profile_databases` (`{name: manifest path}`) and `hmmer_executable_directory`. |
| `REF/credit.py` | Its entry in `CEILINGS`; its branch in `found_ceiling` (at most `model_count` families, each at most once); its family `profile_scan` in `grouping_room`. The credit itself reads the scan through the library: `candidate_measurements._profile_scan` (each matched family a candidate `profile_family:<accession>`, value its match strength) and `differential_credit.SHEET_WEIGHT['profile_scan']`. |
| `REF/messages/internal_summary.py` | `PROFILE_PROVIDER`, `_held_profile_scans`, the unit row's `scan` and `features`, the tool in `CREDITED_TOOLS`, the summary key `held_profile_scans`. |
| `LIB/records/data_products.py` | Kinds `profile_scan_results`, `profile_scan_sequence_hits`, `profile_scan_report`. |

What the unit keeps: the source record, the grading, one `reference` record of type `family` per matched family, one
`observation` of kind `profile_match` per matched domain with its interval on the query, and each graded text as a
labelled data product.

### What the library already holds for this job

| What | Where | Facts |
|---|---|---|
| An Infernal job contract | `LIB/forms/similarity_search/native_infernal_contracts.py` | The Infernal counterpart of the contract the reference builds its job with (`requested_job_from_infernal`; programs `cmsearch`, `cmscan`, `cmalign`). It admits `-Z`, `--cut_ga`, `--rfam`, `--fmt`, `--clanin`, `--tblout`, `-o`. It does NOT admit `--nohmmonly`, which Rfam's command has. Not read in full. |
| A reader and grader of Infernal tables | `LIB/readers/similarity_search/infernal_search_inputs.py`, `LIB/grading/similarity_search/infernal_search_grader.py` | The reader's own text: it supports `cmscan` table format 2. They sit where the reference's HMMER grader sits (`grading/similarity_search/`). The grader is imported by the Rfam batch graders and `tools/partner_presence_evidence/tools.py`. Not read in full; not run. |
| The structure head's RNA family scan | `LIB/tools/structure_search/structural_homology_evidence/rna_family_scan.py`, `LIB/grading/structural_homology_evidence/rna_family_scan_sheet.py` | The same `cmscan` command on one RNA of the scope. It builds the command by hand (not through the job contract), has its own check in the library file, and its own sheet: per family the value of its best hit, `x^2/(1+x^2)` with `x` = bits over the family's threshold. It belongs to another head. |
| The first build's RNA tool | `LIB/tools/rna_gene_finding/find_rna_genes.py`, `LIB/grading/rna_gene_finding/rna_gene_sheet.py`, `LIB/grading/tool_grading/tool_grading_artifacts.py` | The same command on a DNA piece; a sheet with begin, end and strand per hit. It does not import (`records/dna_sequence.py` is deleted). It has no request check, keeps no `reference` or `observation` records, and builds the command by hand. Not conforming (the handoff). |
| Grading records | `LIB/grading/sequence_homology_evidence/tool_grading_artifacts.py` | The module the reference calls. Five other head folders under `LIB/grading/` hold copies; `LIB/grading/tool_grading/` is the first build's copy. |
| Data-product kinds | `LIB/records/data_products.py` | `rna_gene_scan_results` and `rna_gene_scan_report` are in `KINDS` (added by the first build); `rna_family_scan_results` and `rna_family_scan_report` are the structure head's. |
| The first build's head | `root/parts_discovery/task.py` | Settings `infernal_executable_directory` and `covariance_database_manifest` (one path, not a `{name: path}` map as in the reference). The structure head's setting for the same thing is `covariance_databases`. |

## 2. Mapping

### The library function

The library is shared functions, filed by what they are. The scan this tool needs is already there: `rna_family_scan`
(`LIB/tools/structure_search/structural_homology_evidence/rna_family_scan.py`) runs this same `cmscan` command on one
sequence and keeps every hit in its sheet with its positions, strand, bit score and the family's threshold. This head's
tool calls that function. No new library file is written. The first build's copies of it (`LIB/tools/rna_gene_finding/`,
`LIB/grading/rna_gene_finding/`, `LIB/grading/tool_grading/`, and the two `rna_gene_scan_*` kinds in
`records/data_products.py`) are deleted.

One thing in it must become the caller's: its check (`check_rna_family_scan_request`) admits only a query whose molecule
is `rna`, so a piece of DNA is refused. The molecules admitted become an argument of the check. Not yet run on a piece
of DNA through this function (the first build's copy ran the same command on DNA: 7 hits on the stretch).

The table below is the head only. Left: the piece of the reference. Right: this head's piece, with the same kind of name
in the same file.

### The head (`REF/...`; new: `root/parts_discovery/...`)

| File | Reference piece | New piece | What must differ, and why |
|---|---|---|---|
| `task.py` | `PROFILE_TOOL = 'hmmer_profile_scan'` | `RNA_GENES_TOOL = 'find_rna_genes'` | the tool's name |
| `task.py` | `DESCRIPTIONS[PROFILE_TOOL]` | `DESCRIPTIONS[RNA_GENES_TOOL]` | the text says what this scan does and returns |
| `task.py` | `profile_scan_options(summary, resources, databases)` | `rna_gene_scan_options(summary, resources, databases)` | nothing but the tool's name |
| `task.py` | `scans_made(summary)` | `rna_gene_scans_made(summary)` | reads `held_rna_gene_scans` |
| `task.py` | the tool's option in `selection_schema`, its name in `offered_actions`, its rows in `decide`, its check and rejection in `action` | the same, in the same functions | nothing but the tool's name |
| `task.py` | `profile_scan(arguments, ctx)` | `rna_gene_scan(arguments, ctx)` | reads the two settings below |
| `task.py` | `TOOLS[PROFILE_TOOL]` | `TOOLS[RNA_GENES_TOOL]` | nothing |
| settings | `profile_databases`, `hmmer_executable_directory` | `covariance_databases`, `infernal_executable_directory` | the other program; `covariance_databases` is the name the structure head already uses |
| `credit.py` | `CEILINGS['hmmer_profile_scan']` | `CEILINGS['find_rna_genes']` | nothing |
| `credit.py` | the `hmmer_profile_scan` branch of `found_ceiling` | the `find_rna_genes` branch | see question 2 |
| `messages/internal_summary.py` | `PROFILE_PROVIDER`, `_held_profile_scans`, `held_profile_scans`, the unit row's `scan` and `features`, the tool in `CREDITED_TOOLS` | `RNA_GENES_PROVIDER`, `_held_rna_gene_scans`, `held_rna_gene_scans`, the same row fields, the tool in `CREDITED_TOOLS` | the tool's name |
| `records/data_products.py` | the three `profile_scan_*` kinds | `rna_family_scan_results`, `rna_family_scan_report` (in the file already, written by the shared function) | nothing to add |

### What has no counterpart in the reference tool (not built)

1. **Candidates, score and ceiling.** In the reference a candidate is a family name of one target, the library's
   `candidate_measurements` and `differential_credit` turn sheets into candidates and credit, and the scan's ceiling rests
   on a family being reported at most once. Here a candidate is a part (kind, positions, strand), one family is reported
   at many places (446 hits on the chromosome), and those two library modules do not read parts. What turns this tool's
   sheet into parts with scores, and what bounds its credit, is not derived.
