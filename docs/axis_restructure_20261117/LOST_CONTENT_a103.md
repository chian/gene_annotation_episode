# A103 (gene_context_evidence): graders and grading sheets, old versus now

Scope (owner narrowing, 19 November 2026): only graders, subscoring and scoring sheets. That means grader
definitions and prompts, sheet schemas, cells and components, how a grader fills a sheet, and which sheet an
episode writes or reads. Goals, instruction text, yield and credit logic, thresholds, tools and messages are out of
scope and are not listed.

Commits compared: `97308b94c` (carry-over source), `60889621e`, `d2f371805`, `d7c6cf6f9`, `6a02e91ba` (all
pre-restructure, axis folder `root/a103/`) and `b5d7c94e2` (the import, flat `gene_annotation_episode/`).
Every grader and sheet module below has the same blob at all five axis-era commits (for example `a103_scoring.py`
`dbef03`, `nhmmer_grader.py` `124b92`, `bvbrc_comparative_systems_sheet.py` `be111c`, `xmfa_calculators.py`
`500e96`). The tool graders and sheets (nhmmer, hmmer, ComparativeSystems, GenomeAlignment, Mauve, XMFA,
genomic overlap, phmmer) have that same blob at the import too. The A103 context sheet modules
(`a103_scoring.py`, `a103_credit.py`, `a103_contribution.py`, `a103_attachments.py`, `a103_publication.py`) do not
exist at the import; they first appear by `6a02e91ba` and do not change after that. The best version of each item is
therefore the single version that exists. It is quoted from `97308b94c:gene_annotation_episode/episodic_workflow/root/a103/<file>`
unless the row says otherwise.
The sentence about the authority of the grading sheet was in `root/a103/scientific_process_prompt.py` before the
restructure, in the same text as `gene_context_evidence_prompt.py` at `97308b94c`. It is not at the import.

## Items that are WEAKER, LOST or VIOLATES

| # | Old file @ commit | Old text or logic (exact) | Decision (one sentence) | Current file | Class | Where it belongs now |
|---|---|---|---|---|---|---|
| 1 | `bvbrc_comparative_systems_sheet.py`, `bvbrc_comparative_systems_sheet_contracts.py`, `bvbrc_comparative_systems_calculators.py`, `bvbrc_comparative_systems_calculation_contracts.py`, `bvbrc_comparative_systems_returns.py` @ 97308b94c (same blob back to b5d7c94e2) | "The builder copies native measurements and retains associations/populations. It does not acquire data, repair source losses or run the separate scientific component calculators. Population IDs are exclusively caller assignments." / "The native reports and supplied snapshots stay separate. Ratios retain their operands and named populations. Counts describe stored assignment records, never physical absence, biochemical completion, or annotation probability." / sheet rows `_SHEET_LIST = {"plfam": "family_rows", "pgfam": "family_rows", "pathway": "pathway_rows", "ecnumber": "pathway_ec_rows", "subsystems": "subsystem_rows", "variant_matrix": "variant_rows"}`; quantities such as `"observed_family_set_intersection_count"`, `"family_occurrences_per_positive_genome"`, `"subsystem_explicit_category_genome_count"` | The BV-BRC ComparativeSystems sheet records the reported family, pathway, EC, subsystem and variant-matrix values with their units and named populations. Its counts are counts of assignment records, never evidence of absence or of function. | none (only `forms/bvbrc_comparative_systems_handoff_schemas.json` survives) | LOST | A sheet builder and calculator in a new `grading/service_calls/gene_context_evidence/` module (with its contracts in `forms/service_calls/gene_context_evidence/`), called from the A103 tool that publishes a ComparativeSystems result (`tools/gene_context_evidence/tools.py`). Note: at 97308b94c the only caller was `bvbrc_comparative_systems_bundle_adapter.py`, which no A103 module imported, so it was not wired then either. |
| 2 | `bvbrc_genome_alignment_sheet.py`, `bvbrc_genome_alignment_calculators.py`, `bvbrc_genome_alignment_calculation_contracts.py`, `bvbrc_genome_alignment_returns.py` @ 97308b94c (same blob back to b5d7c94e2) | "The data record keeps the original task, parsed native values and supplied C relationships. The sheet keeps that data alongside separately calculated full components. Building or validating either record never recalculates science." / "Each original request receives one outcome. Only the exact D002 native target errors become local incompatible outcomes; every other exception propagates." | The GenomeAlignment sheet keeps the native parsed values and the separately calculated components apart, and saving a sheet never recomputes it. | none | LOST | `grading/sequence_alignment/gene_context_evidence/` (sheet builder and calculator), called from the A103 tool that publishes a GenomeAlignment result. It was also unwired at 97308b94c (only `bvbrc_genome_alignment_bundle_adapter.py` called it). |
| 3 | `mauve_v4_calculators.py`, `mauve_backbone_calculators.py`, `mauve_v4_calculation_contracts.py`, `mauve_backbone_contracts.py` @ 97308b94c (same blob back to b5d7c94e2) | "No interval reconstruction is attempted. Coverage uses only actual selected residue positions. Coordinates without characters never establish identity. Source length is a staged-input denominator, not a whole-genome census." / "Unions, placement sums, multiply represented positions and excess placements are separate quantities. No backbone/BBCols row-index correspondence is used." | The Mauve cells count only selected residue positions and keep unions, placement sums and multiply represented positions as separate quantities. | none | LOST | `calculations/sequence_alignment/gene_context_evidence/` (the GenomeAlignment components of row 2). |
| 4 | `xmfa_calculators.py`, `xmfa_calculation_contracts.py` @ 97308b94c (same blob back to b5d7c94e2) | "Native-axis coverage counts survive missing source files. Fractions and source complements require a complete, matching source binding and selected population. These pure calculations neither acquire data nor assign annotation credit." | XMFA coverage counts are kept even without source files, but fractions are reported only with a complete, matching source binding and population. | none | LOST | `calculations/sequence_alignment/gene_context_evidence/` (with row 2). |
| 5 | `genomic_overlap_calculations.py`, `genomic_overlap_result_views.py`, `genomic_overlap_return_views.py`, `genomic_overlap_returns.py` @ 97308b94c (same blob back to b5d7c94e2) | "Every base count is in bp under exact-chromosome, zero-based half-open outer span coordinates. Counts retain occurrence multiplicity; union quantities do not. Ratios retain integer numerators/denominators and have no invented statistical uncertainty. Parameters filter recorded native pairs by integer cross-products; they never recover absent edges or repeat an overlap analysis." | The genomic-overlap sheet keeps occurrence counts and union quantities apart, keeps ratio operands, and adds no uncertainty that was not measured. | none. The driver, inputs and contracts survive in shared `tools/`, `readers/` and `forms/sequence_and_context_sources/`; the calculator does not. | LOST | `calculations/sequence_and_context_sources/genomic_overlap_calculations.py` (the library function that fills the sheet), called by the result path of `native_genomic_overlap_driver`. No A103 file references genomic overlap now. |
| 6 | `gene_context_evidence_prompt.py` @ 97308b94c, lines 257-260 (`root/a103/scientific_process_prompt.py` @ 60889621e … 6a02e91ba) | "return their actual saved grading results, numerical status, qualifications and missing inputs. Reporting does not require another supported/contradicted, function, path or scope verdict: use the grading sheet's existing criteria and status, without inventing a score threshold or asking a child to judge the same result again." | The grading sheet's own criteria and status are final: no episode adds a threshold or asks a child to grade the same result again. | none (the phrase is absent from every current A103 file and from the A103 library folders) | LOST | Head `task.py` (the decision instruction), next to the `a103_sheet` view that `messages/internal_summary.py` shows. |
| 7 | `nhmmer_grader.py` @ 97308b94c (= b5d7c94e2, blob `124b92`) | `_COUNTS = ("paired_positions", "insert_positions", "delete_positions", "alignment_columns")`; `def _alignment_components(row)`, `def _cutoff_margins(row, sheet, native_score)`, `def _score_locus(row, sheet)`, `def calculate_nhmmer_scores(sheet, *, parameters=None): """Calculate inspectable locus components; only None/{} is supported. The sheet's parsed native values are authoritative inputs. This function does not read/reparse ``sheet.native.artifacts``; removing retained raw text leaves all numerical calculations unchanged."""` | The nhmmer sheet has cells for paired, insert and delete positions, alignment columns, posterior bounds and cutoff margins, and these are calculated only from the parsed native values. | `grading/similarity_search/gene_context_evidence/nhmmer_grader.py`: 89 lines, only the definitions; the calculator, the alignment components and the cutoff margins are gone. The full text is unchanged in the shared `grading/similarity_search/nhmmer_grader.py`. | WEAKER | Delete the partial A103 copy and call the shared `grading/similarity_search/nhmmer_grader.calculate_nhmmer_scores` where A103 grades nhmmer output. At 97308b94c, A103 reached it only through the unused `grade_hmmer_native_artifacts` (row 8). |
| 8 | `hmmer_graders.py` @ 97308b94c (= b5d7c94e2, blob `f00cc3`) | `def grade_hmmer_native_artifacts(...)`: "Searches take stdout/tblout/domtblout as applicable. hmmalign takes the actual Stockholm under the ``stockholm`` role; a log or HTML page is not an alignment." | A native HMMER grader fills a sheet only from the native format that holds the measurement; a log or HTML page is never graded as an alignment. | `grading/similarity_search/gene_context_evidence/hmmer_graders.py` keeps only `grade_hmmer_api_result` and `api_domain_scores`. The dispatcher survives verbatim in the copies for sequence_homology, structural_homology, evolutionary_history and partner_presence. | WEAKER | `grading/similarity_search/gene_context_evidence/hmmer_graders.py`, if A103 grades native HMMER artifacts. No A103 module called it at 97308b94c. |
| 9 | `gene_context_evidence/published_evidence_assessment/.../source_evidence_examination/decision_state.py` line 43, and the same line in `passage_evidence_extraction`, `table_evidence_extraction` and `source_coverage_improvement` @ 97308b94c (= `root/a103/scientific_process/...` @ 60889621e) | `context['_completed_work_axis_results'] = {key: credit_view[key] for key in ('a103_sheet', 'target_sheets', 'tool_attachments', 'source_contributions') if key in credit_view}`. Labels in `gene_context_evidence_prompt.py`: `('a103_sheet', 'Current gene-context scoring sheet')`, `('tool_attachments', 'Saved measurement-specific context attribution')`, `('literature_current_scoring_sheets', 'Saved received gene-context evidence sheets')` | The literature-reading episodes decide while seeing the current A103 scoring sheet, the per-target sheets and the attributions specific to each measurement. | Only the head's `messages/internal_summary.py` (`CREDIT_KEYS = ('credit', 'axis_components', 'a103_sheet', 'target_sheets', 'tool_attachments', ...)`) shows them; the four source-reading episodes do not. | WEAKER | `messages/internal_summary.py` of `source_evidence_examination`, `passage_evidence_extraction`, `table_evidence_extraction` and `source_coverage_improvement`, from the `A103ContextCredit` view their `credit.py` already computes. |

No VIOLATES item was found inside this scope.

## A sheet decision that no commit ever implemented (for the owner's attention, not a carry-over loss)

`research/experimental_scoring_review_2026-10-23/a103_complete_deliverable_023/NUMERICAL_SHEET.md` (present at
b5d7c94e2 and still in the repository) defines an A103 numerical sheet that no code has ever implemented at any of
the six commits. `a103_scoring.py` measures arrangement (`'gap_bp'`, `'overlap_bp'`, `'intervening_annotated_cds'`)
but has none of the contrast cells below. The document calls itself a proposal ("It proposes an A103 contribution;
it does not mark the axis complete, adopt policy, implement readers"). The decisions it states:

- "Each question is one biological spatial relation and one comparison population, not one publication, gene hit,
  sliding window or model turn."
- "`g(p,b) = 0 if p=b; (p-b)/(1-b) if p>b; (p-b)/b if p<b`" and "Matched contrast `E_j` … It remains separate from
  comparability `C`."
- "Native neighborhood contribution … Uses the program's neighborhood score. Low score is not opposition; never
  substitute `1-s`."
- "Supporting total `S` … Opposing total `O`, … retained separately", and "**`c=S*(1-O)`** … neither an
  exact-function probability nor investigation-progress credit."
- "Never turn a filtered-out, top-k-omitted or unmapped result into zero."

If the owner adopts it, it belongs in `grading/gene_context_evidence/scoring.py`, as new sheet cells beside the
arrangement measurements.

## PRESERVED / RESHAPED counts

The scope is the graders and sheets, so the counts are by library module and not by episode. Of the 34 A103
episodes, all score against the one A103 context sheet (`A103ContextCredit`). The head and the four
source-reading episodes are the only ones that show sheets to their model.

- In the A103 library folders, unchanged apart from imports (PRESERVED, 14): `grading/gene_context_evidence/scoring.py`
  (A103 measured-context sheet, `VERSION = 'a103_measured_gene_context_v1'`), `credit.py` (`A103ContextCredit`,
  including `'missing':'unknown_qualification_retained; no_fabricated_association'`), `contribution.py`,
  `tool_grading_artifacts.py`; `grading/sequence_alignment/gene_context_evidence/` `biopython_pairwise_grader.py`,
  `minimap2_grader.py`, `native_correspondence_scoring.py`; `grading/similarity_search/gene_context_evidence/`
  `blast_database_grader.py`, `blast_graders.py`, `bvbrc_homology_grader.py`, `hmmer_search_grader.py`;
  `calculations/gene_context_evidence/bvbrc_data_calculators.py`; `forms/service_calls/gene_context_evidence/bvbrc_appservice_schemas.json`;
  `literature/prompts/gene_context_evidence/literature_investigation_prompt.py`.
- RESHAPED (3): `records/gene_context_evidence/attachments.py` and `records/gene_context_evidence/publication.py`.
  These carry the same grading-at-publication and attachment cells, with only the store access changed
  (`store.db` became `TableDeclaration`/`store.table`). The third is the head's
  `messages/internal_summary.py`, which shows the `a103_sheet`, `target_sheets` and `tool_attachments` that the
  old prompt showed.
- PRESERVED in shared or other-axis library folders, unchanged apart from imports and paths (23). These are
  `hmmalign_grader`, `minimap2_grading_inputs`, `blast_grading_inputs`, `blast_pairwise_grader`,
  `bvbrc_minhash_grader`, the sequence composition, extraction and translation graders, and the full
  `nhmmer_grader`. They also include the ProteomeComparison sheet family: `bvbrc_proteome_sheet`,
  `bvbrc_proteome_directional_sheet`, `bvbrc_proteome_numerical_sheet`, `bvbrc_proteome_sheet_contracts`, the
  proteome and directional calculators, and seven `bvbrc_proteome_*_schemas.json`. The last is
  `bvbrc_comparative_systems_handoff_schemas.json`. No current A103 file references the proteome sheets. At
  97308b94c they were reached only through `bvbrc_proteome_bundle_adapter.py`, which no A103 module imported, so
  which sheet A103 writes is unchanged.
