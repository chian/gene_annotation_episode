# Lost grading content: A107 (`partner_presence_evidence`)

Scope, as the owner narrowed it on 2026-11-19: graders, subscoring sheets and scoring sheets only. That means
grader definitions and prompts, sheet schemas, cell components and columns, how a grader fills a sheet, and
which sheet an episode writes. Goals, instructions, credit, yield, thresholds, tools and messages are left out.

This is a read-only comparison. Old commits read: `b5d7c94e2` (import, flat `gene_annotation_episode/*.py`),
`6a02e91ba`, `d7c6cf6f9`, `d2f371805`, `60889621e` (the last state before the restructure, with A107 under
`root/a107/` and `root/a107/library/`) and `97308b94c` (the episode tree source). The partner grading text is
the same at `6a02e91ba`, `d2f371805` and `60889621e`. The import version is less complete: its
`literature_partner_prompt.py` lacks the `experiment_assessment` paragraph. Wherever a "best version" is named
below, it is therefore `60889621e`, unless another commit is given.

Abbreviations: `R = gene_annotation_episode/episodic_workflow/root/a107`,
`ES = gene_annotation_episode/episodic_workflow/episode_support`,
`LIT = R/partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination`.

## Items that are WEAKER, LOST or VIOLATES

| # | Episode path | Old file @ commit (best version) | Old text, quoted exactly (short) | Decision in one sentence | Current file | Class | Where it belongs |
|---|---|---|---|---|---|---|---|
| 1 | All A107 literature episodes (published_evidence_assessment down to the three readers) | `R/library/partner_source_instruction_text.py` @ `60889621e` (same at `6a02e91ba`, `d2f371805`; the import `b5d7c94e2:gene_annotation_episode/literature_partner_prompt.py` lacks paragraph 2) | "Identify the source-backed nonpartner condition factors relevant to the selected comparison and their reported levels before calling coverage complete. Complete coverage requires a nonempty selected factor set with known levels; do not invent factors or assume that unreported attributes match. Keep the intended partner change separate from these factors so its presence or absence is not penalized as a nonpartner difference." | The partner-sheet grader prompt (`PARTNER_TASK`) defines how the partner subscoring sheet is filled: omission and addback arms, nonpartner condition coverage, measured species and component role, direction of the relationship, and censoring kept apart from spread. | `ES/literature/prompts/literature_partner_prompt.py` holds the text word for word, but no A107 episode imports it. The ordered reader (`LIT/source_coverage_improvement/task.py`) populates partner sheets without it. | LOST (in use; the library copy is preserved) | In the `task.py` of each literature episode that runs `literature.partner.populate` / `literature.partner.source.populate`, imported from `ES/literature/prompts/literature_partner_prompt.py`, as the old `population_family_specs()` paired it with the `literature_partner_cells` family |
| 2 | Same | `R/library/partner_source_task.py` @ `60889621e` | "Select the relevant omission, addback and control observations, their experimental meanings and the applicable partner component readers and graders. Return the requested saved partner components with their actual subject, endpoint, conditions, uncertainty, provenance and unresolved inputs. Required partnership, genomic presence, coexpression, physical interaction and demonstrated function are distinct questions" | When partner components are requested, the reading opens with the partner-grading lead (`PARTNER_LEAD`), which chooses the partner readers/graders and keeps required partnership apart from presence, coexpression, interaction and function. | none | LOST | The literature episodes' `task.py`, ahead of `PARTNER_TASK`, chosen when the parent selected `requested_partner_components` (old `selected_family`) |
| 3 | `LIT/source_coverage_improvement` (and every literature episode that populates) | `R/library/partner_source_contracts.py` @ `60889621e` (same text at `b5d7c94e2:gene_annotation_episode/literature_episodes.py:152`) | "Censor domains are not confidence intervals; chemical bypass and partner swaps do not establish universal partner necessity, genomic presence, target transfer or annotation credit." | The grader operation `literature.partner.populate` fills the partner sheet from retained measurements and keeps censor domains apart from confidence intervals and bypass/swap results apart from necessity. | `LIT/source_coverage_improvement/task.py` `POPULATION_DESCRIPTIONS` (rewritten: "Preserve nonpartner conditions, physical measurement identity, source units and uncertainty. Missing inputs preserve partial or unavailable cells.") | WEAKER (drops the censor-domain and bypass/swap distinctions) | The `task.py` catalogue entry, using the old description verbatim |
| 4 | Same | `R/library/partner_source_contracts.py` @ `60889621e` | "For source-defined activity units such as U/mg, select the endpoint-specific definition, quantity, molecular entity and time basis; no universal U conversion is assumed. Deterministic readers preserve original tokens, convert supported rate units and retain unknown normalization, conditions or observation identity. A repeated representation is not a new measurement." | The grader operation `literature.partner.source.populate` fills cells from literal spans, ties activity units to their endpoint, does no universal U conversion, and never counts a repeated representation as a new measurement. | `LIT/source_coverage_improvement/task.py` (rewritten: "Only source offsets are numeric arguments; exact text witnesses are materialized from the received source bytes.") | WEAKER (drops the U/mg, unit-definition and repeated-representation decisions) | The `task.py` catalogue entry, using the old description verbatim |
| 5 | Same | `R/library/literature_partner_operand_information.py` @ `60889621e` (also `b5d7c94e2:gene_annotation_episode/literature_partner_operand_information.py`) | "A bare U/mg witness is rejected by this partner reader; use the source-defined unit form only when its actual supported source definition is available." / "Source support for the reported spread meaning; SD, SEM and CI require a basis witness and remain distinct." | The cell-input meanings of the partner sheet: unit witness rules, endpoint/definition entity matching, and SD/SEM/CI kept distinct, each needing a basis witness. | none (the file does not exist under `ES/`) | LOST | A library function in `ES/literature/forms/partner_presence_evidence/` (beside `literature_partner_source_fields.py`) that annotates `partner_source_population_schema()`. The populate entries in `task.py` call it. |
| 6 | Literature episodes and head (the reader of partner cells) | `R/library/partner_source_contracts.py` `fact_sources()` @ `60889621e` | "'literature_partner_cells': {'type': 'array', 'meaning': 'Saved experimental partner-removal and addback components with actual molecule/partner identities, nonpartner-condition comparisons, normalization, physical observation identity and reported spread meanings. Native rates survive unavailable controlled comparisons. Bounds condition on supplied censor domains and exact reported means; they are not sampling confidence.'" | The definition of what the partner sheet's cells record and how they are read: native rates are kept when controlled comparisons are unavailable, and bounds are not sampling confidence. | none (the `partner_cells_schema()` columns are preserved in `ES/literature/readers/literature_partner_sheet_records.py`; the meaning is not) | LOST | The `RETURN_FORM` field description of the partner-cells field in each literature episode's `messages/final_to_parent.py` |
| 7 | `published_evidence_assessment`, `evidence_search_strategy_improvement`, `source_relevance_assessment`, `source_evidence_examination`, `passage_evidence_extraction`, `table_evidence_extraction` | `R/partner_presence_evidence/published_evidence_assessment/**/contracts.py` `_population_catalog()` @ `97308b94c` (each literature role) | `def _population_catalog(): """A107 partner operations owned by this episode.""" ... return list(population_catalog_entries())` | Every literature episode, from the strategy level down to each reader, may run the partner graders and write partner sheets. | `task.py` of each: `raise NotImplementedError('partner_source_contracts_not_placed:population_catalog_entries')` / `...:populate_partner_sheet`; in table: `raise NotImplementedError('partner_source_contracts_not_built:' + operation)`. Only `source_coverage_improvement` populates. | VIOLATES (stub); the decision is LOST in 6 episodes | Each episode's `task.py`, calling `ES/literature/inputs/literature_partner_sheet_population.populate` the way `source_coverage_improvement/task.py` already does |
| 8 | `published_evidence_assessment`, `evidence_search_strategy_improvement`, `source_relevance_assessment`, `source_evidence_examination`, `passage_evidence_extraction` | old `internal_summary.py` / `received_reports.py` @ `97308b94c` (read the partner cells of held sheets through `LiteraturePartnerRepository`) | (old behaviour: the cells of the saved partner sheets this episode and its children committed) | An episode reads back the partner-sheet cells it holds, so that the sheets it wrote are part of what it reports. | `messages/internal_summary.py`: `raise NotImplementedError('partner_source_contracts_not_placed:fact_cells_over_held_sheets')` | VIOLATES (stub) | `messages/internal_summary.py`, through `ES/literature/readers/literature_partner_sheet_records.py` / `ES/literature/storage/literature_partner_storage.py` over the scoped store |
| 9 | Head `partner_presence_evidence` | `R/component_axis_reports.py` `current_scoring_sheets()` @ `60889621e` | "'numerical_results': originals, 'native_component_results': components, 'tool_qualifications': qualifiers, ... 'combined_scientific_score': None, 'combination_status': 'separate_named_components; no_new_axis_reducer', ... 'unqualified_uses': 'remain_unknown; do_not_suppress_the_original_scientific_components'" | The A107 scoring sheet (`component_axis_scoring_sheet_v1`) holds three separate named component groups: literature partner cells, native genomic/expression components and per-use tool qualifications. It has no axis reducer, and unqualified uses stay unknown rather than suppressed. | `R/partner_presence_evidence/messages/internal_summary.py` gathers `qualifications`, `native_components` and genomic execution findings, but no scoring sheet joins them with the partner cells | WEAKER (the sheet's assembly and its "separate, no reducer" rule are gone) | A library function under `ES/grading/partner_presence_evidence/` (for example `scoring_sheet.py`) that the head's `messages/internal_summary.py` calls |
| 10 | Head `partner_presence_evidence` | `R/component_axis_reports.py` `dependence()`, `native_dependence()`, `cross_dependence()` @ `60889621e` | "'missing_identity': 'unknown_dependence_not_independence', 'numerical_ownership': 'original_sheet_ref_and_component; repeated_views_are_not_new_measurements'" / "'native_and_literature_views': 'shared_origins_require_scientific_review; no_automatic_independence'" | The scoring sheet records shared origins (sheet, artifact, source, experiment, dataset, input bytes) across literature and native components. A shared or unknown origin is never counted as independent confirmation. | none (no `shared_origins` / `cross_dependence` anywhere under `ES/` or `R/`) | LOST | The same scoring-sheet library function as row 9 |
| 11 | Head `partner_presence_evidence` | `R/component_axis_reports.py` `PATHS` @ `60889621e` | "PATHS = {'A107': ('requirement', 'presence', 'expression', 'coexpression', 'interaction')}" | The A107 sheet keeps five evidence paths apart: requirement, presence, expression, coexpression and interaction. | none | LOST | The scoring-sheet library function of row 9 (as its path vocabulary) |
| 12 | Head (axis scoring) | `research/slotted_process_library/publications/2026-10-23-002/entries/A107.json` @ `b5d7c94e2`, still unchanged at HEAD; scored by `root/evidence_axis_scoring.py` `score_axis` @ `60889621e` (old shared root, consuming this axis's descriptors) | "\"criterion_id\": \"partner_count_scope_matched\", \"question\": \"Do numerator and denominator describe the same fixed required-partner set and examined genome?\"" / "\"route_id\": \"identified_partner_fraction\" ... \"score_unit\": \"fraction of the fixed required-partner set\"" | The A107 scoring sheet's metrics (partner E-value, bit score, coverage, coexpression statistic and significance, required/identified/coexpressed/absent partner counts), its 8 criteria and its 7 score routes. | The data is preserved in `research/`, and `ES/forms/partner_presence_evidence/evidence_axis_contracts.py` validates the entry form. No current code scores the routes (`score_axis` is absent from `ES/`). | LOST (the scorer) | A library function under `ES/grading/partner_presence_evidence/` that scores the entry's routes from the scoring sheet of row 9, called by the head's `messages/internal_summary.py` |

Not counted: `SCORING_RUBRICS_A107_A108_A110.md` (`b5d7c94e2`) states that it is "explicit **proposals**, not
previously approved numerical rules", so it is not an owner decision.

## PRESERVED / RESHAPED counts (grading items only)

Library items. The comparison is `60889621e` against now, ignoring import lines; "reshaped" means only the move
from `store.db` to declared custody tables:

- PRESERVED (content identical) – 10:
  - `literature_partner_calculations.py` (`COMPONENTS` reference/omitted/addback rate, partner loss, fractions)
  - `literature_partner_defined_units.py`
  - `literature_partner_source_fields.py`
  - `literature_partner_models.py`
  - `literature_partner_inputs.py`
  - `literature_partner_native_inputs.py`
  - `literature_partner_sheet_records.py` (`partner_cells_schema`)
  - `expression_nmf_sheet.py` (now under `ES/readers/expression_and_perturbation/`)
  - `native_correspondence_scoring.py`
  - `tool_grading_artifacts.py`
- PRESERVED as text but not wired – 1: `PARTNER_TASK` (row 1).
- RESHAPED (same decisions, custody tables) – 6:
  - `literature_partner_sheet_population.py`
  - `literature_partner_saved_validation.py`
  - `literature_experiment_assessments.py`
  - `literature_partner_storage.py`
  - `a107_qualification.py` → `ES/grading/qualification.py` (per-use A107 qualification sheet)
  - `component_axis_native_hpc.py` (native component records)
- RESHAPED in messages – 1: the parent's choice of `requested_partner_components` from `COMPONENTS` is in the
  literature `read_from_parent.py` / `msg_to_child.py`.
- Tool graders found at their new homes (BLAST, HMMER, BV-BRC homology/minhash, minimap2, Biopython pairwise,
  cmalign, hmmalign, infernal, nhmmer, Rfam, sequence composition/extraction/translation): located under
  `ES/grading/{similarity_search,sequence_alignment,sequence_operations}/`. They are general tool graders, not
  A107 decisions, and were not diffed line by line.

Per episode (grading items):

| Episode | Preserved/reshaped | WEAKER | LOST | VIOLATES |
|---|---|---|---|---|
| head `partner_presence_evidence` | 3 (qualification sheet, native components, component selection) | 1 (row 9) | 3 (rows 10, 11, 12) | 0 |
| `published_evidence_assessment` | sheet library reachable only through its children | 0 | rows 1, 2, 5, 6 shared | 2 (rows 7, 8) |
| `evidence_search_strategy_improvement` | same | 0 | shared | 2 (rows 7, 8) |
| `source_relevance_assessment` | same | 0 | shared | 2 (rows 7, 8) |
| `source_evidence_examination` | same | 0 | shared | 2 (rows 7, 8) |
| `passage_evidence_extraction` | same | 0 | shared | 2 (rows 7, 8) |
| `table_evidence_extraction` | same | 0 | shared | 1 (row 7) |
| `source_coverage_improvement` | population, storage and sheet records wired | 2 (rows 3, 4) | shared rows 1, 2, 5, 6 | 0 |
| execution / results / monitor / HPC episodes (all 21) | no grading sheets of their own | 0 | 0 | 0 |
