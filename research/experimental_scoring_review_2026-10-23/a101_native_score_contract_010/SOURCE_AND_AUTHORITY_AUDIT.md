# Source and authority audit for A101 native-score contract 010

## Work identity and authority

Assigned directory: `research/experimental_scoring_review_2026-10-23/a101_native_score_contract_010/`. All authored and retained-source files for this task are new files in that directory. No production, runtime, prompt, reader, library, existing research record, or saved scientific run was edited. No alignment, search, scientific job, fitted model, or annotation-scoring run was executed. Public documentation/source retrieval and explicitly synthetic arithmetic were performed.

The bounded deliverable's goal and criteria are in `README.md`. The controlling overall goal attachment was read in full from `/home/chia/.codex/attachments/9a858f85-d1dc-4f59-b574-9988cc09dee2/pasted-text-1.txt`. It says ten numerical evidence-axis sheets, starting with A105, with 0/10 complete; examples, formulas and unresolved choices must be shown to the user and feedback incorporated. This task does not complete any sheet.

The following complete authority set was actually read before source conversion. Paths are relative to `/home/chia/repos/gene_annotation_episode` unless absolute. Long files were read in the shown sequential portions, not headings or summaries.

| Authority | Actual read scope |
| --- | --- |
| `AGENTS.md` | Complete file |
| `GOAL.md` | Complete file |
| `docs/EPISODE_STRUCTURE.md` | Lines 1–180, then 181–351, covering the complete file |
| `docs/TIME_AWARE_ESTIMATION.md` | Lines 1–195, then 196–388, covering the complete file |
| `docs/TOOL_KNOWLEDGE.md` | Complete file |
| `docs/TASK_AND_STEERING.md` | Complete file |
| `docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md` | Complete file |
| `docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md` | Complete file |
| `research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md` | Complete file, including original user correction |
| `research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md` | Complete file, including historical assistant messages and later user correction; assistant historical claims not treated as authority |
| `docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md` | Complete file, including preserved original and additive corrections; separately read again in full after an initially overlarge tool-output batch |
| `verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md` | Complete file; treated as a synthetic historical proposal, not a paper packet or accepted policy |
| `research/experimental_scoring_review_2026-10-23/AGENTS.md` | Complete file, including all subsequent verbatim user instructions; separately reread in full after the initial aggregate tool output was truncated |
| Current goal attachment above | Complete file at the start and again after the main authority reads |

The parent's self-contained assignment and subsequent additions were read in full. The latest human reminder carried in that assignment was:

> Remember a goal is a goal - so you have to set the goal and the goal criteria more than the instructions

The assignment also preserved these controlling user statements:

> Sequence homology is already scored - all homology programs lead to a score. The interpretation of the score will need some weighting and so on for the mixture of tools, but you do not need to create a psuedo judgement score when you have a score.

> These individual scores need to be multipliers or sum in some way.

> The PAPERS DO NOT OVERRIDE THE TEMPLATE. THEY GET CONVERTED THOUGHTFULLY

The final compilation deliverable incorporates the parent's later request for an explicit bounded, completely filled synthetic route including alternative-function comparison, and the clarification that a computable declared scoring convention differs from a calibrated probability. The initial native contract is preserved; `COMPILATION_PROPOSAL.md` is the additive expanded route.

`authority_read_manifest.json` identifies the authority paths, current file lengths, and SHA-256 values observed when the manifest was written. Those hashes identify observed file bytes; they are not substituted for reading, and are not claimed to prove which bytes were present at an earlier read time.

## Per-paper reset status

No primary journal paper or retained paper-specific evidence packet was opened for this task. Incidental paper references/snippets appeared in web searches for official manuals; they were not used as sources for measurements or scoring conversions. HMMER's manual tutorial is software documentation, not a new primary-paper review. The numerical fixtures do not repurpose its biological examples.

Accordingly there is no claimed post-paper reread event. The complete initial authority read is recorded above; it is not mislabeled as a reset after every paper. If the parent later opens a paper or retained paper-specific packet while combining this work, the complete post-paper authority reset remains required before conversion or another paper.

Official documentation and versioned public source were sufficient for this bounded task. No sequence-submission, PubMed/PMC article-retrieval, or other research API skill was needed or invoked. No source-access limitation was bypassed. The ordinary NCBI `/books/` route showed a browser challenge; its public `/sites/books/` documentation route returned the requested manual. HMMER's official documentation page linked the inspected user guide.

## Inspected sources and exact sections

| ID | Primary documentation/source and inspected section | Numerical cells or boundary informed |
| --- | --- | --- |
| B1 | [NCBI, The Statistics of Sequence Similarity Scores](https://www.ncbi.nlm.nih.gov/BLAST/tutorial/Altschul-1.html): “The statistics of local sequence comparison,” “Bit scores,” “P-values,” “Database searches,” “The statistics of gapped alignments,” “Edge effects.” Formula images (1), (2), (3) were retrieved and visually inspected. | Raw/bit/E equations, effective search-space qualification, statistical-null interpretation. |
| B2 | [NCBI BLAST Glossary](https://www.ncbi.nlm.nih.gov/sites/books/NBK62051/): “bit score,” “composition-based statistics,” “E value,” “identity,” “K,” “lambda,” “raw score.” | Exact score names, dependence on scoring/statistical regime, gap-cost convention. |
| B3 | [BLAST+ Command Line Applications User Manual, Appendices](https://www.ncbi.nlm.nih.gov/sites/books/NBK279684/): Table C1 native output fields, `max_hsps`, `max_target_seqs`, `dbsize`, `searchsp`; Table C3 `comp_based_stats`, `matrix`, `gapopen`, `gapextend` and filter options. | HSP/subject distinction, parser input names, incomplete reporting and configuration custody. The page is dated 2021 and Table C3 says it reflects 2.2.27; no current default was inferred from that table. |
| B4 | [NCBI blast_stat.c](https://www.ncbi.nlm.nih.gov/IEB/ToolBox/CPP_DOC/doxyhtml/blast__stat_8c_source.html): `BLAST_KarlinStoE_simple`, source lines 4158–4172; `BLAST_SpougeStoE`, 5177–5235, including score-dependent area and database multiplier. Retained matching raw current source, file ID dated 2026-01-08. | Prevents treating the simple E equation as every BLAST reporting regime. |
| H1 | [HMMER User's Guide 3.4, Aug 2023](https://eddylab.org/software/hmmer/Userguide.pdf): pages 10–11 ensemble/optimal scoring distinction; pages 33–39 full/domain output, E-values, envelopes, alignments and PP symbols; 67–72 target/domain tables; 100–101 model thresholds, filters, `-Z`, `--domZ`; 213–214 profile `STATS` header semantics. Targeted pipeline text was also inspected at pages 62–63. | HMMER native scopes, model/sequence role normalization, coverage operands, bias and accuracy fields, Forward tail statistics and search-space definitions. All pages stated here were read as returned text; later source reads supplied exact numerical implementation details. |
| H2 | [HMMER 3.4 `src/p7_pipeline.c`](https://github.com/EddyRivasLab/hmmer/blob/hmmer-3.4/src/p7_pipeline.c): lines 725–945, especially 774–884. | Final null2 correction, reconstruction-score option, domain envelope score and Forward-tail calculation. |
| H3 | [HMMER 3.4 `src/p7_tophits.c`](https://github.com/EddyRivasLab/hmmer/blob/hmmer-3.4/src/p7_tophits.c): lines 929–994; complete `p7_tophits_TabularDomains`, lines 1697–1787. | domZ determination, native table fields and their precision, repeated full-sequence values, `hmmscan`/`hmmsearch` role swap, E multipliers, and native `acc` denominator. |
| H4 | [Easel 0.49 `esl_exponential.c`](https://github.com/EddyRivasLab/easel/blob/easel-0.49/esl_exponential.c): `esl_exp_surv` and `esl_exp_logsurv`, lines 122–145. | The exact piecewise exponential-tail formula used in the shown score-statistics conversion. |
| P1 | [Pfam glossary](https://pfam-docs.readthedocs.io/en/latest/glossary.html): “Alignment coordinates,” “Clan,” “Domain score,” “Gathering threshold,” “Sequence score,” and “Posterior probability.” | Profile-family relationships, separate sequence/domain thresholds and coordinate meaning; legacy-description inconsistency noted below. |
| P2 | [Pfam entry documentation](https://pfam-docs.readthedocs.io/en/latest/pfam-entry.html): “Profile HMM,” “Alignment,” “Pfam entries creation and annotation.” | Source of model thresholds and seed/full alignment information; descriptive annotations and model membership do not substitute for functional characterization. |
| P3 | [HMMER web documentation, Results](https://hmmer-web-docs.readthedocs.io/en/latest/result.html): “Customisation of Results” score field; “Profile HMM Matches”; “Database specific result fields → Pfam.” | Documents this wrapper's same-clan competition and distinction between alignment and envelope displays. |

The HMMER PDF, inspected HMMER/Easel/NCBI source files, and three NCBI formula images are retained in `source_documents/`. `source_manifest.json` records their exact bytes and URLs. Source files were read, not compiled or executed. Web pages are source links and inspection records; no claim is made to have archived every web page.

## Source reconciliation and derived-design provenance

1. **Pfam sequence/domain summation:** the glossary's “Sequence score” entry retains a simple sum statement, while its “Domain score” entry qualifies HMMER3. The versioned HMMER manual and inspected 3.4 scoring code establish the contract used here: do not recreate full-sequence scores by blindly summing displayed domain bits. This resolution does not revise the source.
2. **Native accuracy denominator:** the manual's general accuracy description is accompanied here by the actual 3.4 writer's `oasc/envelope_length`. The contract preserves native `acc` rather than inventing an aligned-residue expected count from it.
3. **BLAST HSP terminology:** historical descriptions begin with ungapped HSP theory. The current contract separately records gapped scoring mode and reported HSP fields; the original ungapped theory is not silently imposed on every native result.
4. **Coverage/site formulas:** coordinate definitions come from B3/H1/H3. Union counts, separately named coverage ratios, assessed-site decomposition, and missing-site bounds are explicit arithmetic definitions proposed for the user's sheet. They are not attributed to a paper or to Pfam as a functional scoring policy.
5. **Combination formulas:** the native documents establish score meanings, not the proposed logistic index, its feature choice, synthetic coefficients, family grouping, or experimental calibration. Those are separately labeled, unadopted design choices. The product term is not claimed to prove independence or fully remove shared evidence. A network threshold is excluded by measurement scope, not used as a numeric substitute.

## Checks performed and limits

The two arithmetic scripts ran successfully; their result JSON files preserve the synthetic label and absence of scientific-program execution. The second script adds strict relative checks for small E-value calculations, so those checks do not rely on the first script's permissive absolute tolerance. The expanded example also checks alternative contrasts, a fully populated point, incomplete-site bounds and duplicate-group reuse.

The outputs are source-traced numerical field/combination proposals. They do not demonstrate a real parser, real score extraction, published functional cases, experimental reference grounding, fitted calibration, valid biological probabilities, user adoption, multi-group total aggregation, or an end-to-end A101 score. Those remain unresolved work, not an excuse to create an operational approval gate or compel more tool use. Arithmetic unavailability constrains only the claimed numerical output; it does not control investigation, execution or continuation.
