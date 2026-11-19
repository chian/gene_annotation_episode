# Investigation finding features: A107 (partner_presence_evidence), 19 November 2026

Proposal for the owner to correct line by line. No code was changed and no Python was run.

An investigation finding is evidence for an annotation: its `evidence_type` (one value of a short fixed
vocabulary) and its strength, spread over controlled fields that code reads from the sheet the finding rests on.
Every proposed field is a number with range and unit, an integer count, a boolean, a value of a fixed vocabulary, a
record reference, or an annotation. No field holds prose and no field gathers several pieces of evidence. Credit is
not restated anywhere below. Lines are numbered (F1.3, E2, ...) so they can be corrected one at a time.

## 0. What was read, and what was not where the brief said

| # | Fact | Where |
|---|---|---|
| 0.1 | `literature/grading/partner_presence_evidence/` does not exist. A107 has no literature grader folder and no aggregation sheet. | `episode_support/literature/` listing |
| 0.2 | The A107 literature sheet is the partner component sheet: provider `literature.experimental.partner`, record version `literature_partner_record_v1`, eight cells per sheet. Its cell schema is `partner_cells_schema()` in the shared `literature/forms/literature_received_partner_contract.py` (the same schema is repeated in the shared `literature/readers/literature_partner_sheet_records.py`). The experiment type and its components are in the shared `literature/forms/literature_partner_models.py` (`EXPERIMENT_TYPES = {'partner_requirement': ...}`). | both forms files |
| 0.3 | The partner sheet is filled by shared files outside the named folders that the A107 episodes import directly (`literature/inputs/literature_partner_inputs.py`, `literature_partner_native_inputs.py`, `literature_partner_sheet_population.py`, `literature/readers/literature_partner_sheet_records.py`, `literature/storage/literature_partner_storage.py`). I read only the schema and check functions in them that the cells carry (`_saved_check`, `fact_cells`, `partner_experiment_assessment_schema`) and the shared `assessment_schema` of `literature/grading/literature_experiment_assessments.py`. No search was run outside the named folders. | those files |
| 0.4 | Today no episode can produce a partner sheet. `published_evidence_assessment`, `evidence_search_strategy_improvement`, `source_relevance_assessment`, `source_evidence_examination` and `passage_evidence_extraction` raise `NotImplementedError('partner_source_contracts_not_placed:...')` on population, `table_evidence_extraction` raises `NotImplementedError('partner_source_contracts_not_built:...')`, and `own_cells` raises when sheets are present. Only `source_coverage_improvement` imports the population route (`literature_partner_sheet_population.populate`). | the `task.py` and `internal_summary.py` of each |
| 0.5 | `literature/storage/partner_presence_evidence/literature_sheet_updates.py` has `_policy_for(provider) -> None`, so `current_scoring_sheets` returns `[]` for A107: there is no A107 scoring provider and no main sheet. | that file |
| 0.6 | `grading/partner_presence_evidence/scoring.py` is the measured gene-context calculator. It still carries A103 names (`VERSION = 'a103_measured_gene_context_v1'`, schemas `a103_recurrence_v1`, `a103_cooccurrence_v1`, `a103_fusion_v1`, error codes `a103_*`). The head reaches it through the selected tools `context.*`, `reference.neighborhood` and the `detection` operation of the A107 tool registry (`task.py` `action`, `permitted` list). | `scoring.py`, head `task.py` |
| 0.7 | `literature/forms/partner_presence_evidence/literature_experimental_contracts.py` (`a105_rate_extraction_v1`) and `literature/inputs/partner_presence_evidence/literature_rate_native_inputs.py` (`a105_rate_extraction_v2`), `literature_assay_inputs.py` (`a105_assay_inputs_v1`) carry A105 names. The partner population path imports only helpers from them (witness schema, `_Sources`, `SOURCE_KINDS`), not their row schemas. They are operands, not graders; see section 7. | the three files |
| 0.8 | The sequence detection graders of A107 are `grading/sequence_alignment/partner_presence_evidence/` (Biopython pairwise, minimap2, A107's own native correspondence projection) and `grading/similarity_search/partner_presence_evidence/` (BLAST database, BV-BRC Homology, HMMER). `blast_pairwise_sheet_v1` is graded by the shared `grading/similarity_search/blast_pairwise_grader.py`, which I did not read; its fields below come from what A107's `native_correspondence_scoring.blast_comparisons` reads. | those folders |
| 0.9 | `grading/partner_presence_evidence/contribution.py` defines a signed A107 root scalar (`signed_root_axis_scalar_mappings_v1`, `value` in [-1, 1], `direction`). No episode file calls it. | that file |
| 0.10 | Every A107 episode that returns an investigation finding today returns it as five text fields (`source_claim`, `source_subject`, `qualification`, `target_correspondence`, plus `source_refs`); two leaves add `readings`/`windows` lists of text. Section 5 replaces them. | the `final_to_parent.py` files |

## 1. Proposed `evidence_type` vocabulary for A107

| # | `evidence_type` | The finding rests on | Section |
|---|---|---|---|
| T1 | `partner_requirement_experiment` | one literature partner component sheet (reference / omitted / addback arms of a reported experiment) | 2 |
| T2 | `partner_sequence_detection` | one tool grading artifact of a sequence search or alignment for the partner (BLAST pairwise or database, HMMER, BV-BRC Homology, Biopython pairwise, minimap2) | 3 |
| T3 | `partner_gene_neighborhood` | one recurrence sheet `a103_recurrence_v1` (declared arrangement of target and partner genes over a genome panel) | 4.1 |
| T4 | `partner_cooccurrence` | one co-occurrence sheet `a103_cooccurrence_v1` (presence/absence contingency over a genome panel) | 4.2 |
| T5 | `partner_gene_fusion` | one fusion sheet `a103_fusion_v1` (target and partner regions in one coding product) | 4.3 |
| T6 | `not_reported` | nothing: the episode returned without a finding (replaces the `NOT_REPORTED` / `NOT_WRITTEN` prose) | 5 |

Fields common to every finding (all types):

| # | Field | Type | Values / range | Required | Read from |
|---|---|---|---|---|---|
| C1 | `evidence_type` | enum | T1 to T6 | yes | which sheet family `sheet_ref` is |
| C2 | `sheet_ref` | record ref | a sheet or tool grading artifact this episode holds | yes, except `not_reported` | the sheet |
| C3 | `partner_ref` | record ref | the partner reference record | when the sheet names one | T1: cell `partner_ref`; T2 to T5: the reference/locus binding the tool ran on |
| C4 | `partner_annotation` | annotation (gene/product name or ID), max 64 chars | taken as given, not looked up | optional | the partner the evidence is about |
| C5 | `target_correspondence` | enum | `established`, `unresolved`, `not_evaluated` | yes | T1: the cell's fixed `target_correspondence` (`not_evaluated`); T2 to T5: `unresolved` unless an established attribution record is held |
| C6 | `direction` | enum | `support`, `opposition`, `measured_neutral`, `unknown` | yes | computed by code per type (rules in each section); the vocabulary is `contribution.py`'s `direction` |

## 2. T1: literature partner component sheet

### 2.1 What it grades (one line)

The change of a measured rate when the partner is omitted and added back in one reported experiment: eight
components per sheet (`reference_rate`, `omitted_rate`, `addback_rate`, `partner_loss`, `partner_loss_fraction`,
`addback_gain`, `addback_fraction`, `restored_reference_fraction`).

### 2.2 Numeric, integer, boolean and enum fields of a cell, as the schema names them

`partner_cells_schema()`: every property is required (`obj()` makes all properties required); "nullable" means the
type admits `null`.

| # | Field | Type | Values / range | Required |
|---|---|---|---|---|
| F1.1 | `component` | enum | the eight `COMPONENTS` | yes |
| F1.2 | `value` | number, nullable | real; unit in `unit` | yes |
| F1.3 | `lower` | number, nullable | real; a censor/input domain, not a CI (`bound_kind`) | yes |
| F1.4 | `upper` | number, nullable | as `lower` | yes |
| F1.5 | `unit` | enum, nullable | `pmol/min/mg`, `nmol/min/mg`, `umol/min/mg`, `per_min`, `per_s`, `uM/min`, `nM/min`, `dimensionless` | yes |
| F1.6 | `origin` | enum, nullable | `reported`, `graph_derived`, `synthetic`, `derived` | yes |
| F1.7 | `bound_kind` | enum | `point_only_not_uncertainty`, `conditional_input_domain_not_CI` | yes |
| F1.8 | `status` | enum | `populated`, `bounded`, `unavailable` | yes |
| F1.9 | `unavailable_reason` | enum, nullable | `REASONS`: the 17 `CHECK_REASONS` plus `measurement_unreported`, `censored_point_unreported`, `nonpositive_reference_domain`, `zero_or_straddling_loss_domain`, `numerical_model_range` | yes |
| F1.10 | `formula_code` | enum | the eight `FORMULA_CODES` values | yes |
| F1.11 | `source_kind` | enum | `primary_source`, `retained_extraction`, `graph_extraction`, `synthetic_fixture` | yes |
| F1.12 | `comparison_checks.reference_omitted.status` | enum | `matched`, `different`, `unresolved` | yes |
| F1.13 | `comparison_checks.reference_omitted.unavailable_reason` | enum, nullable | `CHECK_REASONS` | yes |
| F1.14 | `comparison_checks.reference_omitted.differing_factor_refs` | list of term refs | condition factors that differ | yes |
| F1.15 | `comparison_checks.addback_omitted.*` | as F1.12 to F1.14 | | yes |
| F1.16 | `arm_metadata.<arm>` for `reference`, `omitted`, `addback` | object, nullable | | yes |
| F1.17 | `arm_metadata.<arm>.partner_state` | enum | `present`, `absent`, `unreported` | yes when the arm is present |
| F1.18 | `arm_metadata.<arm>.condition_coverage` | enum | `complete`, `partial`, `unreported` | yes when the arm is present |
| F1.19 | `arm_metadata.<arm>.spread.kind` | enum | `SD`, `SEM`, `CI`, `unspecified`, `unreported` | yes when the arm is present |
| F1.20 | `arm_metadata.<arm>.spread.magnitude` | number, nullable | >= 0, in the arm's rate unit | yes when the arm is present |
| F1.21 | refs: `sheet_ref`, `evidence_source_ref`, `data_source_ref`, `subject_ref`, `partner_ref`, `experiment_ref`, `endpoint_ref`, `normalization_ref`, `reference_condition_ref`, `omitted_condition_ref`, `addback_condition_ref`, `function_ref` | record refs (nullable except the three source refs) | | yes |
| F1.22 | constants: `evaluation_scope`, `target_correspondence` (`not_evaluated`), `partner_necessity` (`not_inferred`), `statistical_uncertainty` (`not_evaluated`), `measurement_corrections` (`not_applied`) | single-value enums | | yes |

The optional partner experiment assessment (`partner_experiment_assessment_schema`, shared `assessment_schema`) has
one controlled field: `experiment_type`, enum with the single value `partner_requirement`, plus `experiment_ref` and
`revises_sheet_ref` (record refs). Its other fields are prose (2.4).

### 2.3 Proposed finding for one partner sheet (`evidence_type = partner_requirement_experiment`)

"Cell X" means the cell of that component on the sheet named by `sheet_ref`.

| # | Feature | Type | Range / vocabulary | Unit | How code reads it |
|---|---|---|---|---|---|
| F1.a | `partner_loss_fraction` | number, nullable | real (negative = rate rose without the partner) | dimensionless | cell `partner_loss_fraction`.`value` |
| F1.b | `partner_loss_fraction_status` | enum | `populated`, `bounded`, `unavailable` | | that cell's `status` |
| F1.c | `partner_loss_fraction_lower` | number, nullable | real | dimensionless | that cell's `lower` (only when `bounded`) |
| F1.d | `partner_loss_fraction_upper` | number, nullable | real | dimensionless | that cell's `upper` (only when `bounded`) |
| F1.e | `partner_loss_unavailable_reason` | enum, nullable | `REASONS` | | that cell's `unavailable_reason` |
| F1.f | `addback_fraction` | number, nullable | real | dimensionless | cell `addback_fraction`.`value` |
| F1.g | `restored_reference_fraction` | number, nullable | real | dimensionless | cell `restored_reference_fraction`.`value` |
| F1.h | `reference_rate_unit` | enum, nullable | the seven native units | | cell `reference_rate`.`unit` |
| F1.i | `reference_omitted_check` | enum | `matched`, `different`, `unresolved` | | cell `partner_loss`.`comparison_checks.reference_omitted.status` |
| F1.j | `reference_omitted_check_reason` | enum, nullable | `CHECK_REASONS` | | same check's `unavailable_reason` |
| F1.k | `differing_condition_count` | integer | >= 0 | factors | `len(differing_factor_refs)` of the same check |
| F1.l | `addback_omitted_check` | enum | `matched`, `different`, `unresolved` | | cell `addback_gain`.`comparison_checks.addback_omitted.status` |
| F1.m | `observed_arm_count` | integer | 0 to 3 | arms | count of the three rate cells whose `status` is not `unavailable` |
| F1.n | `omitted_partner_state` | enum | `present`, `absent`, `unreported` | | `arm_metadata.omitted.partner_state` (of any cell; the arm metadata is per sheet) |
| F1.o | `addback_partner_state` | enum, nullable | as F1.n; null when no addback arm | | `arm_metadata.addback.partner_state` |
| F1.p | `conditions_complete_arm_count` | integer | 0 to 3 | arms | count of arms whose `condition_coverage` is `complete` |
| F1.q | `reference_spread_kind` | enum | `SD`, `SEM`, `CI`, `unspecified`, `unreported` | | `arm_metadata.reference.spread.kind` |
| F1.r | `reference_spread_magnitude` | number, nullable | >= 0 | F1.h | `arm_metadata.reference.spread.magnitude` |
| F1.s | `omitted_spread_kind` | enum | as F1.q | | `arm_metadata.omitted.spread.kind` |
| F1.t | `omitted_spread_magnitude` | number, nullable | >= 0 | F1.h | `arm_metadata.omitted.spread.magnitude` |
| F1.u | `value_origin` | enum, nullable | `reported`, `graph_derived`, `synthetic` | | cell `reference_rate`.`origin` |
| F1.v | `source_kind` | enum | the four `SOURCE_KINDS` | | any cell's `source_kind` |
| F1.w | `experiment_ref` | record ref, nullable | | | any cell's `experiment_ref` |
| F1.x | `function_ref` | record ref, nullable | the function term the source ties to the partner | | any cell's `function_ref` |
| C6 | `direction` | enum | | | `support` if F1.i is `matched` and F1.a > 0 (or F1.c > 0 when bounded); `opposition` if F1.i is `matched` and F1.a <= 0; `unknown` otherwise. Owner to confirm the rule. |

Uncertainty block: F1.q to F1.t give kind and magnitude. The partner sheet has no replicate count and no sampling
basis (the A105 rate rows have `uncertainty.count` and `uncertainty.sampling_basis`; see 7.1). Count of independent
units is therefore missing for T1 (owner line O1).

Agreement across sheets (no aggregator sheet exists for A107; 0.5). Proposed counts that code computes over the
partner sheets the episode holds, returned beside the per-sheet findings:

| # | Feature | Type | How |
|---|---|---|---|
| F1.y | `matched_sheet_count` | integer >= 0 | sheets whose F1.i is `matched` |
| F1.z | `matched_loss_sheet_count` | integer >= 0 | of those, sheets with F1.a > 0 |
| F1.aa | `distinct_experiment_count` | integer >= 0 | distinct non-null F1.w over those sheets (independent experiments, not sheets) |

### 2.4 Fields left out (prose or no information), and what carries their meaning

| # | Left out | Why | Carried by |
|---|---|---|---|
| F1.L1 | finding `source_claim` | prose | C1 + F1.a/F1.f/F1.g (what was measured and its size) |
| F1.L2 | finding `source_subject` | prose | C3 `partner_ref`, F1.21 `subject_ref` stays on the sheet, C4 `partner_annotation` |
| F1.L3 | finding `qualification` | prose | F1.b to F1.e, F1.i to F1.p, F1.q to F1.t (conditions, censoring, uncertainty, unresolved checks) |
| F1.L4 | finding `target_correspondence` (text) | prose | C5 enum |
| F1.L5 | assessment `conclusion`, `limitations`, `scientific_question`, `assessment_key`, `revision_reason` | prose | stay on the assessment record inside the episode; `experiment_type` is fixed by T1 |
| F1.L6 | F1.22 constants | one value each, carry nothing | C5 for `target_correspondence` |
| F1.L7 | cell `bound_kind`, `formula_code` | fixed by `component`/`status` | F1.b |
| F1.L8 | `addback_gain`, `partner_loss` values | absolute, unit-bearing duplicates of the fractions | F1.a, F1.f (owner may add `partner_loss` with F1.h if magnitude in native units is wanted) |
| F1.L9 | the `literature_partner_cells` list in returns | a list of whole cell records gathers several pieces of evidence in one field | F1.a to F1.x per sheet and `sheet_ref` (C2); the cells stay in the episode's cell table, passed by reference |

## 3. T2: partner sequence detection (tool grading artifacts)

### 3.1 What each grades (one line each)

| # | Grader / sheet | Grades |
|---|---|---|
| G1 | `biopython_pairwise_sheet_v1` -> `biopython_pairwise_scores_v1` | one supplied pairwise alignment: column counts, identity and coverage |
| G2 | `minimap2_placement_sheet` -> `minimap2_placement_scores_v1`; `minimap2_query_scores_v1` | one nucleotide placement; and all placements of one query |
| G3 | `hmmer_search_sheet_v1` -> `hmmer_search_scores_v1` | HMMER hits and domains: spans, coverage, identity, bits, E-values, posterior accuracy |
| G4 | `blast_database_sheet_v1/v2/v3` -> `blast_database_probabilities_v1` | database BLAST hits grouped into sequence groups, taxonomy, and model-conditional function weights |
| G5 | `bvbrc_homology_sheet_v1` -> `bvbrc_homology_scores_v1` | BV-BRC Homology: per query, either G4 weights or pairwise correspondence |
| G6 | `blast_pairwise_sheet_v1` (shared grader) | one BLAST pairwise search: HSP counts and native scores |
| G7 | A107 `native_correspondence_scoring.route_native_grading` | A107's own projection of G3/G4/G6 into one row per HSP/domain (scales `blast` 0.025, `hmmer` 0.020) |

### 3.2 Numeric, integer, boolean and enum fields, as the schemas name them

| # | Sheet | Field | Type | Values / range / unit |
|---|---|---|---|---|
| G1.1 | G1 sheet | `status` | enum | `complete`, `partial`, `no_alignment`, `alignment_data_unavailable` |
| G1.2 | G1 sheet | `molecule` | enum | `protein`, `dna`, `rna` |
| G1.3 | G1 sheet | `mode` | enum | `local`, `global` |
| G1.4 | G1 sheet | `aligned` | boolean | |
| G1.5 | G1 sheet | `alignment_state` | enum | `alignment`, `conflicting`, `no_alignment` |
| G1.6 | G1 scores | `alignment_columns`, `paired_positions`, `identical_positions`, `substituted_positions`, `query_gap_columns`, `reference_gap_columns`, `query_aligned_positions`, `reference_aligned_positions` | integer, nullable | positions or columns |
| G1.7 | G1 scores | `paired_identity`, `alignment_identity`, `query_paired_coverage`, `reference_paired_coverage`, `query_aligned_coverage`, `reference_aligned_coverage` | number, nullable | [0, 1] fraction |
| G1.8 | G1 scores | `native_score` | number, nullable | native alignment score |
| G2.1 | G2 placement | `status` | enum | `complete`, `partial`, `invalid` |
| G2.2 | G2 placement | `query_length`, `reference_length`, `query_span`, `reference_span`, `paired_positions`, `inserted_bases`, `deleted_bases`, `reference_skipped_bases`, `alignment_columns`, `native_matching_bases`, `native_block_length`, `native_ambiguity_count`, `original_symbol_equal_positions`, `original_symbol_substituted_positions` | integer, nullable | nucleotide positions / columns |
| G2.3 | G2 placement | `mapping_quality` | integer, nullable | 0 to 254 Phred (255 read as null) |
| G2.4 | G2 placement | `native_alignment_identity`, `query_span_coverage`, `reference_span_coverage`, `query_paired_coverage`, `reference_paired_coverage`, `query_aligned_coverage`, `reference_aligned_coverage` | number, nullable | [0, 1] |
| G2.5 | G2 query | `output_complete` | boolean, nullable | |
| G2.6 | G2 query | `result_meaning` | enum | `complete_output_has_zero_reported_placements_not_biological_absence`, `reported_placements_from_complete_output_not_independent_evidence`, `reported_placements_from_partial_or_unknown_output_no_absence_inference` |
| G2.7 | G2 query | `received_sheet_count`, `reported_placement_count`, `invalid_sheet_count`, `missing_sheet_count`, `metadata_invalid_count`, `geometry_missing_count`, `distinct_reference_count`, `exact_duplicate_row_count`, `query_span_union_positions`, `query_paired_union_positions` | integer (last nullable) | rows / references / positions |
| G2.8 | G2 query | `query_span_union_coverage`, `query_paired_union_coverage` | number, nullable | [0, 1] |
| G2.9 | G2 query | `paired_union_complete_for_supplied_rows` | boolean | |
| G3.1 | G3 domains | `model_length`, `sequence_length`, `model_span_positions`, `sequence_span_residues`, `sequence_envelope_residues`, `paired_positions`, `insert_positions`, `delete_positions`, `alignment_columns` | integer, nullable | positions / residues |
| G3.2 | G3 domains | `model_span_coverage`, `sequence_span_coverage`, `sequence_envelope_coverage`, `paired_model_coverage`, `paired_sequence_coverage`, `sequence_identity_fraction`, `consensus_identity_fraction`, `alignment_identity_fraction`, `api_identity_fraction`, `posterior_lower_mean`, `posterior_upper_mean` | number, nullable | [0, 1] |
| G3.3 | G3 domains | `native_domain_score_bits`, `native_domain_bias_bits` | number, nullable | bits |
| G3.4 | G3 domains | `native_conditional_evalue`, `native_independent_evalue` | number, nullable | >= 0 |
| G3.5 | G3 domains | `native_accuracy` | number, nullable | [0, 1] |
| G3.6 | G3 queries | `acquired_hit_row_count`, `acquired_reported_hit_row_count`, `acquired_included_hit_row_count`, `included_status_unavailable_rows`, `reporting_status_unavailable_rows` | integer, nullable | rows |
| G3.7 | G3 hits | `retained_domain_count` | integer | domains |
| G3.8 | G3 iterations | `acquired_hit_row_count` | integer; `dependent_round` boolean | |
| G4.1 | G4 per hit `measurements` | `maximum_bit_score` (bits), `minimum_evalue` (>= 0), `query_paired_coverage`, `reference_paired_coverage` ([0, 1]) | number, nullable | |
| G4.2 | G4 per hit `measurements` | `hsp_count`, `observed_paired_query_positions`, `observed_paired_reference_positions`, `unique_pair_count`, `identical_unique_pair_count`, `overlap_pair_representations` | integer, nullable | |
| G4.3 | G4 per hit `measurements` | `traceback_complete` | boolean | |
| G4.4 | G4 `sequence_groups[]` | `maximum_bit_score` | number, nullable | bits |
| G4.5 | G4 taxonomy `ranks[]` | `unambiguous_group_count`, `ambiguous_group_count`, `unknown_group_count`, `same_taxon_pair_count`, `comparable_pair_count`, `target_matching_groups`, `target_conflicting_groups`, `target_ambiguous_groups` | integer, nullable | groups / pairs |
| G4.6 | G4 taxonomy `ranks[]` | `same_taxon_pair_fraction`, `target_matching_fraction` | number, nullable | [0, 1] |
| G4.7 | G4 `database_representation` | `available_for_adjustment` | boolean | |
| G4.8 | G4 calculation context | `reporting.native_hit_array_present`, `reporting.producer_complete` (boolean, nullable); `native_hit_count`, `requested_hit_limit`, `requested_hsp_limit` (integer, nullable); `database_identity.preparation_type` enum `sequence_database`, `rps`, `delta`, `unknown` | | |
| G4.9 | G4 probabilities | `unadjusted_probabilities`, `representation_adjusted_probabilities` (map function -> [0, 1], nullable); `unannotated_reference_kernel_fraction` ([0, 1], nullable); `unscored_sequence_group_count` (integer); `calibrated_annotation_probability` (constant `false`); `parameters.temperature_bits` (> 0, bits) | | |
| G5.1 | G5 | `scientific_mode` | enum | `database_identification`, `pairwise_correspondence` |
| G5.2 | G5 `queries[]` | `status`; `conditional_function_weights` (a G4 probabilities record) or `pairwise_correspondence` | | |
| G7.1 | G7 row | `algorithm` | enum | `blast`, `hmmer` |
| G7.2 | G7 row | `program` | enum | `blastp`; `phmmer`, `hmmsearch`, `hmmscan` |
| G7.3 | G7 row | `native_scope` | enum | `blast_hsp`, `hmmer_domain_envelope` |
| G7.4 | G7 row | `bits` (bits), `native_evalue` (>= 0), `native_identity` (hmmer) or `alignment_identity` (blast) ([0, 1]) | number, nullable | |
| G7.5 | G7 row | `reference_paired_count`, `reference_length` | integer | residues |

### 3.3 Proposed finding for one grading artifact (`evidence_type = partner_sequence_detection`)

One finding per tool grading artifact (`retain_tool_grading` ref = C2).

| # | Feature | Type | Range / vocabulary | Unit | How code reads it |
|---|---|---|---|---|---|
| G.a | `detection_method` | enum | `blast_pairwise`, `blast_database`, `hmmer`, `bvbrc_homology`, `biopython_pairwise`, `minimap2` | | the artifact's sheet `schema` |
| G.b | `acquisition_complete` | boolean, nullable | | | G2: `output_complete`; G4: `reporting.producer_complete`; G3: the query's `completion`; G1/G6: null |
| G.c | `reported_hit_count` | integer | >= 0 | hits | G4: `len(sheet.hits)`; G3: sum of `acquired_included_hit_row_count` over queries; G2: `reported_placement_count`; G1: 1 if `aligned` else 0; G6: count of HSP rows |
| G.d | `independent_group_count` | integer, nullable | >= 0 | sequence groups / references | G4: `len(sequence_groups)`; G2: `distinct_reference_count`; others null |
| G.e | `best_bit_score` | number, nullable | >= 0 | bits | max of G7 `bits` over the artifact's rows; G4 also `maximum_bit_score`; G1/G2 null |
| G.f | `best_evalue` | number, nullable | >= 0 | expected hits | min of G7 `native_evalue` |
| G.g | `best_identity_fraction` | number, nullable | [0, 1] | fraction | G7 `native_identity`/`alignment_identity` of the row with G.e; G1 `paired_identity`; G2 `native_alignment_identity` |
| G.h | `best_reference_coverage` | number, nullable | [0, 1] | fraction | G7 `reference_paired_count / reference_length` of the row with G.e; G1 `reference_aligned_coverage`; G2 `reference_paired_coverage` |
| G.i | `query_union_coverage` | number, nullable | [0, 1] | fraction | G2 `query_paired_union_coverage`; G4 per-hit `query_paired_coverage` of the best hit; G1 `query_aligned_coverage` |
| G.j | `traceback_complete` | boolean, nullable | | | G4 best hit `traceback_complete`; G2 `paired_union_complete_for_supplied_rows`; G1 `status == complete` |
| G.k | `target_taxon_matching_fraction` | number, nullable | [0, 1] | fraction | G4 `ranks[rank].target_matching_fraction` at a rank the owner names (O3) |
| G.l | `posterior_accuracy` | number, nullable | [0, 1] | | G3 `native_accuracy` of the best domain |
| G.m | `mapping_quality` | integer, nullable | 0 to 254 | Phred | G2 `mapping_quality` (best placement) |
| C6 | `direction` | enum | | | `support` if G.c > 0; `measured_neutral` if G.c = 0 and G.b is true (a complete search that found nothing; this is nondetection in the searched set, not absence); `unknown` otherwise. Owner to confirm. |

### 3.4 Fields left out, and what carries their meaning

| # | Left out | Why | Carried by |
|---|---|---|---|
| G.L1 | `definitions`, `formula`, `assumptions`, `limitations`, `symbol_interpretation`, `meaning`, `counts_meaning`, `union_population` | fixed explanatory text of the grader | nothing needed; they are the same for every sheet |
| G.L2 | `issues` lists, `diagnostics`, `missing_inputs`, `reasons`, `representation_adjustment_unavailable_reasons` | lists of codes (several things per field) | G.b, G.j and nullness of each feature; a per-code boolean can be added if a parent needs one |
| G.L3 | `unadjusted_probabilities`, `representation_adjusted_probabilities`, `function_masses` | maps keyed by function label; model-conditional, `calibrated_annotation_probability` is false | not proposed for the partner finding (A107 asks whether the partner is present, not which function the hit has); owner line O4 |
| G.L4 | hit titles, `functions`, `function_assignments`, `taxids`, `study_groups`, `target_name`, lineage | names and lists | C4 `partner_annotation` (one name) when the parent needs it |
| G.L5 | `native_tag_quantities`, `counts_by_*`, `per_reference`, `query_span_intervals`, `residue_pairs`, `target_symbols` | raw maps and coordinate lists | G.c, G.d, G.h, G.i |
| G.L6 | `result_meaning` (G2.6) | its three values restate G.b and G.c | G.b, G.c |

## 4. Measured gene context (`grading/partner_presence_evidence/scoring.py`)

### 4.1 T3: neighbourhood recurrence `a103_recurrence_v1` (`compare_neighborhoods`)

What it grades: whether a declared arrangement of the target gene and the partner gene (gap, intervening genes,
orientation, order) holds at each locus of an explicit genome panel.

| # | Field | Type | Values / range / unit | Required |
|---|---|---|---|---|
| N1 | `definition.maximum_gap_bp` | integer | bp | yes (read unconditionally) |
| N2 | `definition.maximum_intervening_genes` | integer | genes | yes |
| N3 | `definition.orientation` | enum | `any`, `same`, `convergent`, `divergent` | yes |
| N4 | `definition.order` | enum | `any`, `left_before_right`, any other value is read as right-before-left | yes |
| N5 | `rows[].organization.state` | enum | `measured`, `unresolved`, `measured_nondetection` | yes |
| N6 | `rows[].organization.gap_bp`, `overlap_bp`, `intervening_annotated_cds` | integer | bp / CDS | when `measured` |
| N7 | `rows[].organization.orientation` | enum | `same`, `convergent`, `divergent`, `unknown` | when `measured` |
| N8 | `rows[].organization.right_direction_from_left` | integer | -1, 1 | when `measured` |
| N9 | `rows[].organization.circular_arc_used` | boolean | | when `measured` |
| N10 | `rows[].relationship_holds` | boolean, nullable | | yes |
| N11 | `supporting_loci`, `evaluable_loci`, `unknown_loci`, `evaluable_genomes`, `sampling_group_count` | integer | >= 0 | yes |
| N12 | `native_fraction` | number, nullable | [0, 1] | yes |
| N13 | `group_balanced_fraction` | number, nullable | [0, 1] (mean within genome, then within sampling group, then across groups) | yes |

Proposed finding (`evidence_type = partner_gene_neighborhood`):

| # | Feature | Type | Range | Unit | How |
|---|---|---|---|---|---|
| N.a | `supporting_loci` | integer | >= 0 | loci | N11 |
| N.b | `evaluable_loci` | integer | >= 0 | loci | N11 |
| N.c | `unknown_loci` | integer | >= 0 | loci | N11 |
| N.d | `nondetection_loci` | integer | >= 0 | loci | count of rows with N5 = `measured_nondetection` |
| N.e | `evaluable_genomes` | integer | >= 0 | genomes | N11 |
| N.f | `sampling_group_count` | integer | >= 0 | groups (independent units) | N11 |
| N.g | `group_balanced_fraction` | number, nullable | [0, 1] | fraction of loci | N13 |
| N.h | `maximum_gap_bp` | integer | >= 0 | bp | N1 |
| N.i | `maximum_intervening_genes` | integer | >= 0 | genes | N2 |
| N.j | `orientation_required` | enum | N3 values | | N3 |
| C6 | `direction` | enum | | | `support` if N.g > 0.5, `opposition` if N.g < 0.5 with N.b > 0, `unknown` if N.b = 0 (the 0.5 split is a placeholder; owner O5) |

Left out: `interpretation`, `sampling_aggregation` (constant text); `native_fraction` (unbalanced duplicate of N.g;
owner may keep it); `rows`, `sampling_groups` (per-locus lists; carried by N.a to N.f); `locus_measurement_key`,
`genome_key` (identities, stay in the sheet).

### 4.2 T4: co-occurrence `a103_cooccurrence_v1` (`cooccurrence`)

What it grades: one-sided Fisher enrichment of target-and-partner co-presence over a genome panel.

| # | Field | Type | Values / range / unit | Required |
|---|---|---|---|---|
| Q1 | `contingency.both`, `.left_only`, `.right_only`, `.neither` | integer | >= 0 genomes | yes |
| Q2 | `evaluable_genomes`, `unknown_genomes`, `sampling_group_count` | integer | >= 0 | yes |
| Q3 | `risk_difference` | number, nullable | [-1, 1] | yes |
| Q4 | `p_value` | number, nullable | [0, 1] | yes |
| Q5 | `log10_significance` | number, nullable | >= 0 | yes |
| Q6 | `native_significance_index` | number, nullable | [0, 1); null when rows are not independent | yes |
| Q7 | `independent_row_test_eligible` | boolean | | yes |
| Q8 | `rows[].left_present`, `rows[].right_present` | boolean, nullable | | yes |

Proposed finding (`evidence_type = partner_cooccurrence`):

| # | Feature | Type | Range | Unit | How |
|---|---|---|---|---|---|
| Q.a | `both_present_genomes` | integer | >= 0 | genomes | Q1 `both` |
| Q.b | `target_only_genomes` | integer | >= 0 | genomes | Q1 `left_only` |
| Q.c | `partner_only_genomes` | integer | >= 0 | genomes | Q1 `right_only` |
| Q.d | `neither_genomes` | integer | >= 0 | genomes | Q1 `neither` |
| Q.e | `unknown_genomes` | integer | >= 0 | genomes | Q2 |
| Q.f | `sampling_group_count` | integer | >= 0 | groups | Q2 |
| Q.g | `risk_difference` | number, nullable | [-1, 1] | fraction | Q3 |
| Q.h | `p_value` | number, nullable | [0, 1] | probability | Q4 |
| Q.i | `independent_rows` | boolean | | | Q7 |
| C6 | `direction` | enum | | | `support` if Q.g > 0, `opposition` if Q.g < 0, `measured_neutral` if Q.g = 0, `unknown` if null |

Left out: `log10_significance`, `native_significance_index` (transforms of Q.h); `null_model`,
`multiple_comparison_adjustment`, `normalization`, `interpretation` (constant text); `rows` (per-genome list; Q.a to
Q.e carry it). `left`/`right` are renamed target/partner here; owner confirm (O6).

### 4.3 T5: fusion `a103_fusion_v1` (`fusion`)

What it grades: that the attributed regions lie in one coding product.

| # | Field | Type | Values | Required |
|---|---|---|---|---|
| U1 | `same_coding_product` | boolean | always `true` | yes |
| U2 | `observed_link_fraction` | number | always 1.0 | yes |
| U3 | `regions[].start`, `.end` | integer | residues, 0 <= start < end <= length | yes, >= 2 regions |
| U4 | `coding_locus.translation.status` | enum | `verified`, `qualified` | yes |
| U5 | `coding_locus.translation.exact_boundaries` | boolean | | yes |
| U6 | `coding_locus.translation.qualification` | enum, nullable | `partial_codon`, `source_translation_exception`, `declared_translation_conflict`, `internal_stop`, `sequence_or_location_unavailable`, `partial_or_pseudogene_annotation` | yes |

Proposed finding (`evidence_type = partner_gene_fusion`):

| # | Feature | Type | Range | How |
|---|---|---|---|---|
| U.a | `region_count` | integer | >= 2 | `len(regions)` |
| U.b | `translation_verified` | boolean | | U4 = `verified` |
| U.c | `translation_qualification` | enum, nullable | U6 values | U6 |
| C6 | `direction` | enum | | `support` (a fusion sheet only exists when the regions are in one product) |

Left out: U1, U2 (constants); `interpretation` (constant text); `coding_locus` coordinates (stay in the sheet).

### 4.4 Operands of 4.1 to 4.3, not findings

`a103_locus_binding_v1` (`bind_locus`: `selection_status` enum `selected`, `not_found`, `ambiguous`;
`native_input_placement.state` enum `unique`, `ambiguous`, `not_found`; `candidate_limit_reached` boolean) and
`a103_neighborhood_v1` (`neighborhood`). They locate the loci the comparisons measure; they grade nothing. A locus
that is `not_found` is not partner absence.

## 5. Returns: what each parent decides next and the smallest set of controlled fields

Credit is always returned and is the productivity signal; it is not listed again below. "Finding" means the
controlled finding of sections 2 to 4 (C1 to C6 plus the type's features), one per sheet the child chose, or a single
`evidence_type = not_reported`.

| # | Child -> parent | What the parent decides next (its `task.py` `decide`/`action` and `msg_to_child`) | Smallest controlled return |
|---|---|---|---|
| E1 | head `partner_presence_evidence` -> root | Root's model chooses which axis to commission next, "judged from the credits, the findings and the forecast", and passes the head's earlier returned records back on the next A107 commission (`msg_to_child.partner_presence_evidence`, selection `committed_record_refs`). | credit; finding: C1 `evidence_type`, C6 `direction`, C5 `target_correspondence`, C2 `sheet_ref` of the finding the head chose as its strongest; `committed_record_refs` (record refs). Root does not need per-type features to choose an axis; the head keeps them. The four `a107_*`/`component_axis_*` record-ref fields are not selected by root and can stay as selectable refs. |
| E2 | head (recursive, prepared alternative process) -> head | Whether the alternative thought pattern / tools were productive enough to commission again or to return to its own tools (`CHILD_SLOTS['partner_presence_evidence']`, `process.revise`). | credit; finding (C1, C6, C2 and the type's features, one per sheet); `committed_record_refs`. |
| E3 | `published_evidence_assessment` -> head | Whether to commission literature again with other `source_refs` / `partner_components`, to run a genomic detection (launch/results) instead, or to commit its interpretation (`reason`, `report_finding`). | credit; one T1 finding per partner sheet (F1.a to F1.x, C1 to C6); F1.y to F1.aa; `sheet_refs`. Replaces `literature_partner_cells` (F1.L9) and the prose finding. |
| E4 | `evidence_search_strategy_improvement` -> `published_evidence_assessment` | Whether to commission another strategy child with other `question_context_refs` / `prior_search_refs`, or populate/report from held sources. | credit; T1 findings per sheet; `sheet_refs`. |
| E5 | `source_relevance_assessment` -> `evidence_search_strategy_improvement` | Whether the searched sources were worth examining: search again with revised terms, or commission relevance on other located sources. | credit; T1 findings per sheet; `sheet_refs`. Proposed addition, one integer: `examined_source_count` (sources commissioned to examination), so the parent can tell "searched sources examined, no partner sheet" from "nothing examined"; owner O7. |
| E6 | `source_evidence_examination` -> `source_relevance_assessment` | Which other located source to commission for examination, or whether to report. | credit; T1 findings per sheet; `sheet_refs`. |
| E7 | `table_evidence_extraction`, `passage_evidence_extraction`, `source_coverage_improvement` -> `source_evidence_examination` | Whether to read another table/window/passage set of the same source, switch reading mode, or populate/report. | credit; T1 findings per sheet the leaf populated; `sheet_refs` (the table leaf declares no cells or sheet refs today and its population raises, 0.4; it needs `sheet_refs` once population is built). Remove `written` (C1 = `not_reported` carries it), `readings`, `windows` (prose `statement`/`qualification`; the windows stay as the leaf's records). |

Not in this table: `execution_job_submission`, `execution_result_acquisition`, `execution_progress_assessment` and
`hpc_work_planning` return operational facts (handoffs, acquisitions, observations, obligations), not evidence for an
annotation. Their findings are outside this proposal; their T2 grading artifacts reach the head as record refs and
become T2 findings there.

Credit note: `credit.py` of the head and literature episodes projects `investigation_finding` of the held assessment
records (`FindingIdentity.finding` keys on the question, `source_claim` and `qualification`). Those records stay inside
the episode that wrote them, so their prose is not sent anywhere; nothing above changes credit.

## 6. Annotation fields

| # | Field | Meaning | Source list (not looked up) |
|---|---|---|---|
| A1 | `partner_annotation` (C4) | the partner gene or product the evidence is about | gene / protein names or accessions |
| A2 | (none for function) | the function the source ties to the partner stays a record ref (F1.x `function_ref`) | |

## 7. Read, nothing proposed

| # | File / schema | Why no finding |
|---|---|---|
| 7.1 | `literature_experimental_contracts.py` `a105_rate_extraction_v1` (`status`, `bound`, `approximate`, `origin`, `uncertainty.kind` {`sd`,`sem`,`unspecified`,`unreported`}, `uncertainty.magnitude`, `uncertainty.count` (int >= 1), `uncertainty.sampling_basis` {`biological_preparations`,`technical_measurements`,`unspecified`}) | A105 operand rows, not on the A107 partner path. They hold the replicate count and sampling basis T1 lacks (O1). |
| 7.2 | `literature_rate_native_inputs.py` `a105_rate_extraction_v2`, `literature_assay_inputs.py` `a105_assay_inputs_v1` (`endpoint`, `arrangement`, `variance_status`, `observation_model` enums) | A105 operand schemas; only helpers are used by A107. |
| 7.3 | `literature_partner_source_fields.py`, `literature_partner_defined_units.py` | readers of source numbers and units (relation enum `point`, `lt`, `le`; canonical units); operands of T1. |
| 7.4 | `readers/partner_presence_evidence/*` | PMC asset listing and sequence identity readers; acquisition. |
| 7.5 | `storage/partner_presence_evidence/*` | dependency refresh and literature context; no scoring policy (0.5). |
| 7.6 | `findings/partner_presence_evidence/*` | finding identity, validity closure, finding-progress credit projector, image frame preparation, native command custody. |
| 7.7 | `grading/partner_presence_evidence/progress_information_credit.py`, `practical_execution_credit.py` | credit projectors (monitoring, practical execution), not evidence. |
| 7.8 | `grading/partner_presence_evidence/tool_grading_artifacts.py` | custody of T2 grading artifacts. |
| 7.9 | `grading/partner_presence_evidence/contribution.py` | uncalled signed scalar; its `direction` vocabulary is reused as C6. |
| 7.10 | `records/partner_presence_evidence/*` | only `domain.obj`/`REF` were opened. By file name (construction, execution memory/recording, held inputs, practical execution, progress, publication, result inputs, library targets) they are records and contracts, not grading sheets; none of the graders above imports a sheet schema from them. Not verified further. |

## 8. Lines the owner may want to decide

| # | Question |
|---|---|
| O1 | T1 has no count of independent units. Add `replicate_count` and `sampling_basis` to the partner arm metadata (as in 7.1), or accept that T1 strength carries spread but no n? |
| O2 | C6 `direction` rules (2.3, 3.3, 4.1, 4.2, 4.3) are placeholders computed by code. Confirm, change, or drop `direction` and let the parent read the features. |
| O3 | G.k: at which taxonomic rank is `target_taxon_matching_fraction` read (species, genus, ...)? |
| O4 | Should a T2 finding carry any function weight from G4.9 (keyed by the partner annotation), or stay with detection strength only? |
| O5 | N.g split for `direction` (0.5 placeholder). |
| O6 | T4: `left` is the target and `right` the partner in every A107 call? The scoring code names neither. |
| O7 | E5: add `examined_source_count`, or is the credit trend enough? |
| O8 | 0.6: the gene-context calculator in A107's library still carries A103 names; rename to A107 names when it is next touched. |
