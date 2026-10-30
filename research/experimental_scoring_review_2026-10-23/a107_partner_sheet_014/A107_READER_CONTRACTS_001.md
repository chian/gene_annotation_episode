# A107 exact field and targeted reader contracts — unimplemented proposal

These are restricted data contracts for populating the research sheet, not prompts or implemented production functions. The only executed code in this directory is a one-off reproducibility calculation on the pinned tables and a synthetic-vector check. All fields below belong to the research sheet unless explicitly marked source metadata. JSON is an interchange format; it does not replace detailed investigation guidance or user-facing explanations.

## Common value and provenance types

`NumericCell = {value: finite_number|null, unit: string_enum, numerator: finite_number|null, denominator: positive_number|null, interval: [finite_number,finite_number]|null, interval_kind: enum, missing_reason: enum|null, origin: enum, source_record_ids: string[], calculation_id: string|null}`.

Allowed interval kinds: `none`, `conditional_statistical_95`, `conditional_family_statistical_95`, `missing_input_range`, `sensitivity_range`. Statistical and missing-input intervals are separate cells when both exist; never store a hull and call it a confidence interval. Origins: `reported_measurement`, `reported_derived`, `new_derivation_of_public_data`, `proposed_transform`, `synthetic_input`, `synthetic_derivation`. Units include `raw_alignment_score`, `bit_score`, `dimensionless`, `fraction`, `count_loci`, `count_conditions`, `count_biological_units`, `log2_TPM_plus_1`, `TPM`, `h^-1`, `percent_of_own_WT`, `molecules_per_generation`, `micromolar`, `amino_acids`, `nucleotides`, `angstrom`.

Missing-reason enum: `not_measured`, `not_reported`, `unavailable_artifact`, `incomplete_genome_scope`, `threshold_filtered_output`, `unresolved_molecular_mapping`, `unknown_condition_mapping`, `no_matching_native_conditions`, `missing_covariate`, `invalid_or_failed_assay`, `zero_residual_variance`, `insufficient_independent_units`, `shared_units_unresolved`, `conflicting_records`, `unsupported_measurement_type`, `unspecified_partner_set`. These are status meanings, not numbers or score categories.

`SourceRecord = {source_id, source_url, doi_or_accession|null, retrieved_utc, version_or_commit|null, local_path|null, sha256|null, source_location, original_quantity_name, upstream_measurement_ids: string[], biological_unit_ids: string[], technical_unit_ids: string[], source_block_id, dependence_block_id, inspected: boolean}`. Every string identifier is persistent. A citation and a second citation to the same experiment share upstream IDs. `source_location` identifies figure/panel/table row or matrix row/column, not just the paper title. Uninspected objects may be catalogued but cannot populate measured cells.

## 1. Investigation handoff / candidate declaration

Inputs may be `query_sequence` or `input_refs[]` identifying a selected file and byte/line span with checksum. `public_gene_name` and `candidate_id` are nullable at initial investigation. Once a hypothesis exists, create `CandidateRecord`:

| Exact field | Type and constrained meaning |
|---|---|
| `candidate_id` | Persistent string; distinct proposed annotations remain separate entities |
| `query_id`, `query_sequence_ref` | Persistent supplied molecule/input identity; no searchable name required |
| `hypothesis_label` | Human-readable proposed function; not a measured score |
| `target_assembly_accession_version` | String or null; a taxon name is insufficient for genomic presence |
| `target_locus_or_sequence_id` | String or null; explicit object to be scored |
| `clauses` | Nonempty array of nonempty arrays of relation IDs; alternatives are complete sets |
| `optional_relation_ids` | Separate array; excluded from min/max score |
| `required_partner_rationale_refs` | Source claim IDs explaining each required/alternative set; not support multipliers |
| `stoichiometry` | Per relation positive rational requirement or null; diagnostic in current coordinate |
| `expression_layer` | `transcript_log2_TPM_plus_1` for this implemented-in-arithmetic branch; others preserved as unsupported |
| `target_condition_ids` | Explicit nonempty equally weighted condition cells; fixes m |
| `source_block_ids` | Metadata-eligible source blocks declared without looking at r |
| `relation_family_ids` | The M scored relations used for the family interval; optional diagnostics excluded |

A targeted hypothesis reader can extract source-described partners and their relationship types, but it may not label every mentioned molecule mandatory. Ambiguous necessity returns `unspecified_partner_set`; it does not create a flat average. Molecular alternatives and distinct candidate functions are separate records. This contract does not prescribe investigation order.

## 2. `read_partner_genome_correspondence` — proposed, unimplemented

Input: candidate/relation identity, query and partner reference sequence records if available, versioned target assembly feature/placement records, and complete alignment output including self alignments if correspondence is not exact object identity.

Output fields:

* `relation_id`, `partner_query_id`, `partner_target_locus_id`, `assembly_accession_version`, `feature_start`, `feature_stop`, `coordinate_convention`, `strand`, `feature_type`, `coding_integrity_observation|null`, `genome_record_source_id`.
* `presence_observation`: `present_feature`, `resolved_absence_in_declared_scope`, or `unknown`; `presence_numerator`:1,0,or null; `presence_denominator`:1. A feature coordinate establishes a reference genomic observation, not every sample's allele integrity.
* `absence_scope_ref|null`, `assembly_gaps_intersecting_region: integer|null`, `searched_sequence_fraction: number|null`, `search_output_was_threshold_filtered: boolean|null`, `unobserved_region_refs[]`. A zero hit count is retained separately as `reported_hit_count`; it never automatically becomes P=0.
* `identity_basis`: `same_versioned_molecular_object`, `byte_identical_complete_sequence`, `normalized_alignment`, or `unresolved`.
* `raw_pair_score`, `raw_self_query_score`, `raw_self_reference_score`, `program`, `program_version`, `matrix`, `gap_open`, `gap_extend`, `database_version`, `e_value|null`, `bit_score|null`, `identical_positions|null`, `aligned_positions|null`, `query_length`, `reference_length`, `query_aligned_length`, `reference_aligned_length`, `alignment_coordinates_ref|null`.
* `H_partner`, `P_genomic`, `G_partner` NumericCells, calculated exactly as in the main sheet. If raw scores and full-sequence identity are both absent, H remains null even if an E-value or a prose homolog claim exists.
* `structural_correspondence`: optional separate object `{program,version,TM_score_query_normalized|null,TM_score_reference_normalized|null,RMSD_angstrom|null,aligned_residues|null,query_residues|null,reference_residues|null,source_id}`. These fields do not populate H or P and do not earn another A107 term.

Validation: the alignment's target object must be the feature's translated/nucleotide sequence; accession/version mismatch is an unresolved correspondence, not an implicit match. Self-score units and parameters must equal pair-score units and parameters. Preserve pident/E-values if available; never convert a cutoff label to a numeric grade. Multiple possible loci remain explicit alternatives. A reader validates records; it does not run an unrequested remote alignment job.

## 3. `read_native_expression_block` — proposed, unimplemented

Input: a matrix and sample metadata, query/partner molecular mappings, a declared candidate condition panel and source/dependence identifiers. Output a **long table**, one measured gene per primitive sample row:

`{source_block_id, dependence_block_id, gene_id, assembly_accession_version, biological_unit_id, technical_unit_id|null, sample_id, condition_id, value, unit, assay_valid, missing_reason|null, growth_rate_per_hr|null, growth_phase|null, organism, genotype, medium, carbon_source, carbon_amount_g_L|null, nitrogen_source, nitrogen_amount_g_L|null, electron_acceptor, supplement, supplement_amount_with_unit|null, temperature_C, pH, treatment, batch_id|null, platform, normalization_method, source_record_id}`.

Biological unit IDs refer to cultures/organisms, not lanes, temperature aliquots, technical libraries or database rows. Repeated sample accessions across publications share identity. A technical-repeat aggregation rule must be the source protocol's rule; it is not invented here. If only processed biological-sample values exist, preserve their source preprocessing and do not claim fresh read-level analysis.

The condition matching reader returns `requested_m`, `matched_q`, `matched_condition_ids`, `unmatched_condition_ids`, `C=q/m`, and exact known differences/unknown metadata. Its matching tuple consists of the target panel's declared organism/genotype, expression layer, growth phase, medium/carbon/nitrogen/supplement, temperature,pH,electron-acceptor,treatment fields. Intended varying factors define separate condition cells; they are not accidentally matched away. Source target panel identity is allowed when it is explicitly the same dataset-defined panel.

The native statistical reader returns:

* `condition_means_ref`, `condition_sample_membership_ref`, `n_biological_samples`, `n_condition_units`, `n_technical_measurements|null`, `growth_condition_means_ref`.
* `codetection_threshold_TPM`:1; `codetection_threshold_origin`:`proposed_analytical`; `codetection_numerator`, `codetection_denominator`, `D`, `sample_codetection_numerator`, `sample_codetection_denominator`; repeat counts at thresholds5 and10.
* `raw_pearson_r`, `growth_covariates_k`, `residual_df`, `partial_r`, `residual_cross_product`, `residual_ss_target`, `residual_ss_partner`, `t_statistic`, `p_two_sided`, `fisher_z_se`, `ordinary_r_ci95`, `family_size_M`, `family_r_ci95`, `leave_one_condition_out_r_min`, `leave_one_condition_out_r_max`.
* `H0_target_correspondence`, with the same raw mapping fields/record reference as the genome-correspondence reader; `R_positive_squared`, `E_observed_block`, and missing-scope interval if C<1.

Formulas are exactly main-sheet§2. Means use log2(TPM+1) inputs, not a silently substituted transformation. Missing paired values reduce q and remain in the requested m. If n≤k+3, the bounded interval/scoring branch is unresolved; report raw measurements and `insufficient_independent_units`. With zero residual variance, r is null; biological constitutive expression is not negated. If D=0 by valid observations, positive jointly detected association support is0 even if an irrelevant r cannot be calculated. These mathematical zero cases must be distinguished from failed measurements.

An existing program output can be read without recomputation only when it supplies the same statistic, transform, n, covariates, units and dependence scope. Preserve the native program's statistics verbatim. A network confidence/combined score is not Pearson r and cannot be squared as if it were; it returns `unsupported_measurement_type` for this branch while retaining the raw score.

## 4. `read_published_partner_quantities` — proposed, unimplemented

Targeted inputs: an inspected figure/table/caption and experimental definitions. Output rows:

`{quantity_id, organism, strain|null, genotype, target_construct, partner_construct, coexistence_arrangement, intended_changed_variable, other_differences, sample_condition, measurement_name, value, unit, numerator_identity, denominator_identity, normalization_already_applied|null, biological_n|null, technical_n|null, uncertainty|null, source_location, origin, dependence_block_id, candidate_component_role}`.

`candidate_component_role` is one of `genomic_observation`, `native_expression_input`, `comparability_diagnostic`, `supply_diagnostic`, `partner_relationship_hypothesis`, `neighbor_axis_only`. It is not a number. The reader preserves a loading-normalization ambiguity; it may output conditional derived variants with explicit assumptions, but neither variant silently replaces the printed measurement. A molecules-per-generation table keeps that unit and cannot fill steady-state concentration unless its assumptions are also supplied. Binding/perturbation values can explain a relationship but cannot be inserted into E or G.

For the two retained papers, `partial_r`, `n_condition_units`, and native co-expression intervals remain null. Their protein panels do not populate an invented statistic. Their candidate-specific source-only coordinate remains null because required native inputs are absent.

## 5. `compile_a107_sheet` — proposed, unimplemented

Input: immutable candidate/clauses, validated component cells, source and dependence records, exact formulas/version. Output:

`{candidate_id, formula_version, partner_components:[{relation_id,H,P,G,source_blocks:[{H0,C,D,r,R,E}],combined_E,s}], clause_components:[{clause_id,relation_ids,point,statistical_interval,missing_input_range}], coordinate:{point,statistical_interval,missing_input_range}, unresolved_operand_ids[], contradiction_records[], dependence_block_ids[], proposed_weight_genomic:0.5, proposed_weight_expression:0.5, calculation_trace_refs[], status}`.

Status enum: `computed_conditional_research_coordinate`, `computed_interval_with_missing_inputs`, `unresolved_partner_definition`, `unsupported_branch`. It is not an annotation decision or completion gate. Ordinary observations and all original raw values remain in the sheet.

Deterministic sequence: validate source-target identities and units; deduplicate identical measurement IDs; preserve unresolved overlaps; calculate H/P/G; obtain matching C and measured statistics; calculate R and E with explicit missing domains; apply the same-scope source-block minimum; calculate s, clause minima, then alternative maximum. Generate no new evidence events from these transformations. No whole A101 coordinate, physical-binding score, perturbed-growth effect or structural score is accepted as an input multiplier.

All min/max/product endpoint propagation is defined in the main sheet. A numerical point is emitted only when all contributing operands are known or the expression is mathematically fixed despite an irrelevant missing operand. A typed failure preserves the valid partial cells. Current-state calculation does not rewrite earlier saved observations or change their annotation credit.

## Exact local reference artifacts

`PRECISE_RETRIEVAL.json` identifies all primary table versions. `PRECISE_SELECTED_SAMPLE_INPUTS_001.csv` and `PRECISE_CONDITION_INPUTS_001.csv` instantiate the expression input contract. `CHECKED_NUMERICAL_CELLS_001.json` contains the native coefficients, source-based arithmetic, complete synthetic component values and candidate coordinates. `SYNTHETIC_EXPRESSION_INPUTS_001.csv` provides the complete constructed expression matrix. The checked calculator's JSON is a research artifact, not a claim that these proposed production readers have been implemented.
