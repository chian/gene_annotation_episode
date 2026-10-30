# A107 exact cell crosswalk and targeted population contracts

This is the current proposed input/output specification for [the numerical sheet](A107_NUMERICAL_SCORING_SHEET_001.md). The functions below are **unimplemented production readers/calculators**. The 87-check script is a bounded research calculation, not their implementation. This file is not an investigation prompt, generic evidence interpreter or new episode design. W05 owns eventual credit consumption.

The parent's missing-panel correction governs the old `source_blocks:[{H0,C,D,r,R,E}]` output: that representation is too ambiguous. The current record explicitly distinguishes paired expression, growth-adjustable expression, subset statistics and full-panel score operands. A reader must not populate full-panel r/R/E from the subset merely because some data are present.

## 1. Shared data types

`Cell` contains the exact fields below. Numeric primitives are finite; null is distinct from zero. Bounds are ordered and retain their meaning. These fields are an internal record, not model-facing context.

| Field | Type and constrained meaning |
|---|---|
| `cell_id` | Persistent identifier for this mathematical variable; reused wherever the same variable occurs. |
| `point` | finite number or null. Null unless the quantity is measured/defined or a known operand fixes the result algebraically. |
| `unit` | One of `dimensionless`, `fraction`, `raw_alignment_score`, `bit_score`, `count_loci`, `count_conditions`, `count_biological_units`, `log2_TPM_plus_1`, `TPM`, `h^-1`, `percent_of_own_WT`, `molecules_per_generation`, `micromolar`, `amino_acids`, `nucleotides`. |
| `numerator`, `denominator` | Finite number/null, positive number/null. Count ratios additionally require integer counts. Use null for a scalar without a meaningful count denominator; never disguise a score's raw operands as biological counts. |
| `input_range` | `[lower,upper]` or null; missing-input/representation outer domain. Point measurements use `[point,point]` for algebra when needed. |
| `range_basis` | `none`, `missing_operands_outer_domain`, `unresolved_representation_envelope`, `known_zero`, `input_bound_propagation`. A representation envelope is a range over declared representations, not a sampling interval. |
| `ordinary_ci95`, `family_ci95` | Separate `[lower,upper]` or null. Conditional on the named statistical model and known operands. Missing data do not create a CI. |
| `statistical_model_id`, `family_id` | Declared model/family identifiers or null; M and the participating relation/block keys are recorded explicitly in the statistical record. |
| `statistical_conditioning_cell_ids` | IDs of fixed count/genomic/correspondence operands when an interval covers only correlation uncertainty. |
| `sensitivity_range` | `[lower,upper]` or null; accompanied by a sensitivity method and any invalid deletion IDs. Never relabeled CI. |
| `joint_outer_range` | Optional separate outer enclosure when both missing operands and statistical ranges are propagated. It is not a confidence interval. |
| `missing_reason` | null or one of `not_measured`, `not_reported`, `unavailable_artifact`, `incomplete_genome_scope`, `threshold_filtered_output`, `unresolved_molecular_mapping`, `unknown_condition_mapping`, `no_matching_native_conditions`, `missing_covariate`, `invalid_or_failed_assay`, `zero_residual_variance`, `insufficient_units`, `shared_units_unresolved`, `conflicting_records`, `unsupported_measurement_type`, `unspecified_partner_set`. |
| `interval_unavailable_reason` | null or one of `missing_statistic`, `insufficient_interval_df`, `perfect_correlation`, `zero_residual_variance`, `unsupported_covariance_model`, `incomplete_family_coverage`, `unquantified_input_uncertainty`. Separate from a defined point. |
| `origin` | `reported_measurement`, `reported_derived`, `new_derivation_of_public_data`, `proposed_transform`, `synthetic_input`, `synthetic_derivation`. A scoring transform of measured inputs is still a proposed transform. |
| `source_record_ids`, `input_cell_ids`, `calculation_id` | Exact source/input references and named formula. Preserve the measured inputs and proposed transformation separately. |
| `scope_id` | Identity of the requested full panel or explicit observed subset. Scope cannot be inferred from equal n. |

`SourceRecord` fields: `source_record_id`, `source_url`, `doi_or_accession|null`, `version_or_commit|null`, `retrieved_utc|null`, `local_path|null`, `sha256|null`, `source_location`, `original_quantity_name`, `upstream_measurement_ids[]`, `biological_unit_ids[]`, `technical_unit_ids[]`, `source_block_id`, `dependence_block_id`, `inspection_owner|null`, `inspection_coverage_ref|null`, `inspection_scope`.

`inspection_scope` is `primary_inspected`, `retained_crosscase_summary_inspected`, or `uninspected`. It describes the named inspector's actual coverage. Reusing an original worker's primary review does not make this worker a primary inspector. A matrix location records exact row/columns, and a paper location records panel/table/quantity; a title alone is insufficient. Uninspected source material cannot supply a measured cell merely because it was downloaded. Synthetic inputs have their own source record with `origin=synthetic_input`.

## 2. Candidate and condition declarations

The initial investigation can supply only `query_input_refs[]` (selected path/record/span and custody) or a sequence; public gene names and candidate IDs need not yet exist. Once a hypothesis and partner logic exist, the sheet requires:

| Exact field | Type and role |
|---|---|
| `candidate_id`, `query_id`, `query_sequence_ref` | Persistent identities; target input completeness is recorded separately. |
| `target_input_completeness` | `complete_sequence`, `selected_record`, `partial_sequence`, or `unresolved`. Partial material cannot establish byte-identical complete-sequence identity. |
| `candidate_function_ref` | Reference to the proposed function record; distinct possible functions remain distinct candidates. |
| `target_assembly_accession_version`, `target_locus_or_sequence_id` | Identifier or null; missing assembly is not filled by species name. |
| `clauses` | Nonempty array of `{clause_id, relation_ids[], rationale_source_ids[]}`; each relation list is nonempty, unique and describes a complete permitted set. |
| `partner_logic_status` | `declared_complete_alternatives` or `unresolved`. The latter returns coordinate point null/[0,1], not an empty max/min. |
| `optional_relation_ids[]` | Retained diagnostics excluded from the candidate calculation. |
| `partner_requirements[]` | `{relation_id, required_partner_identity_ref, sequence_ref|null, stoichiometric_requirement_rational|null, rationale_source_ids[], requirement_status}`. Status: `required_in_declared_clause`, `optional`, `unresolved`. Rationale is not a numeric multiplier. |
| `condition_panel_id`, `requested_condition_ids[]` | Nonempty unique IDs; length fixes m. |
| `condition_weight_convention` | Exactly `equal_declared_conditions` for this branch. |
| `expression_layer` | `transcript_log2_TPM_plus_1` for the specified calculation; other layers retained with `unsupported_measurement_type`. |
| `eligible_source_block_ids[]` | All blocks eligible by declared metadata scope, not selected by r or score. An empty roster leaves E unknown. |
| `interval_family` | `{family_id, relation_block_keys[], alpha:0.05}`; unique keys define M. Includes every consumed interval; may contain predeclared diagnostics. |

`ConditionDefinition` fields: `condition_id`, `organism`, `genotype`, `expression_layer`, `growth_phase|null`, `medium`, `carbon_source|null`, `carbon_amount_g_L|null`, `nitrogen_source|null`, `nitrogen_amount_g_L|null`, `electron_acceptor|null`, `supplement|null`, `supplement_amount_with_unit|null`, `temperature_C|null`, `pH|null`, `treatment|null`, `intended_varying_factor_names[]`, `declared_biological_unit_ids[]`, `source_condition_ref|null`.

Matching is either `same_source_defined_condition_id` or `complete_declared_tuple_equality`. The first defines the empirical question in the original measured source panel; it does not claim unknown attributes match another experiment. For tuple equality, compare all declared nonvarying fields and the declared condition's intended-varying levels; unknown required fields give `unresolved`. Record `known_condition_differences[]` and `unknown_condition_attributes[]` as field-name/value records, not prose relevance grades. A new panel/roster is a new scope, not a silent revision of an earlier observation.

## 3. Targeted readers and exact component crosswalk

### `read_partner_genome_correspondence` — proposed, unimplemented

Input: one declared relation, versioned assembly feature/placement record, the genomic molecule's sequence, partner reference sequence if present, and either exact-object equality records or complete pair/self/self alignment output. The analogous target-mapping invocation produces H0 for the matrix target. It reads supplied outputs; it does not initiate an unrequested alignment or remote job.

| Output field | Exact type and population |
|---|---|
| `relation_id`, `partner_genome_object_id`, `partner_reference_object_id`, `assembly_accession_version` | Referenced identities; must match the candidate and the expression partner row's native molecular object. |
| `feature_start`, `feature_stop`, `coordinate_convention`, `strand`, `feature_type`, `feature_source_record_id` | Integer coordinates, declared convention, allowed strand/type values and record reference. Validate ordering under that convention; do not substitute a gene label for placement. |
| `coding_integrity_observation_ref` | Reference/null; no integrity or active-protein inference from presence alone. |
| `presence_observation` | `present_feature`, `resolved_absence_in_declared_scope`, or `unknown`. |
| `presence_numerator`, `presence_denominator` | 1/1, 0/1 or null/1. |
| `absence_scope_ref`, `assembly_gaps_intersecting_region`, `searched_sequence_fraction`, `search_output_was_threshold_filtered`, `reported_hit_count`, `unobserved_region_refs[]` | Scope/censoring facts; nullable. A zero hit count never automatically sets P=0. |
| `identity_basis` | `same_versioned_molecular_object`, `byte_identical_complete_sequence`, `normalized_alignment`, or `unresolved`. |
| `raw_pair_score`, `raw_self_query_score`, `raw_self_reference_score` | Cell, unit `raw_alignment_score`; required and same scoring definition for normalized alignment. |
| `alignment_program`, `program_version`, `scoring_matrix`, `gap_open`, `gap_extend`, `database_version`, `alignment_coordinates_ref` | Actual scoring/sequence identity and coordinate operands. Null for unrun alignments under exact-object equality. |
| `e_value`, `bit_score`, `identical_positions`, `aligned_positions`, `query_length`, `reference_length`, `query_aligned_length`, `reference_aligned_length` | Native diagnostics with units; no E-value-to-H or pident-to-H fallback. |
| `H_partner`, `P_genomic`, `G_partner` | Cell: H from the raw-score normalization/equality, P from the genomic observation, G=P*H. |
| `H0_target_correspondence`, `target_mapping_record_ref` | Cell and reference, produced by the analogous target/matrix mapping. Shared by relations using that target. |

An alignment against a different locus/version is an unresolved mapping, not an implicit match. Unknown H remains [0,1]. Exact absence fixes G=0 only if the genome/expression records are consistent. Multiple ambiguous genomic features remain distinct relation alternatives. Optional structure/network diagnostics retain original units in separate records; they cannot populate H.

### `read_native_expression_block` — proposed, unimplemented

Inputs: matrix and sample metadata; query/partner molecular row mappings; condition declaration and biological rosters; source/dependence identifiers; source-defined technical aggregation. It produces the following primitive long-table record for each gene/culture measurement:

`ExpressionSample = {source_block_id, dependence_block_id, gene_object_id, assembly_accession_version, biological_unit_id, technical_unit_id|null, sample_id, condition_id, value|null, unit:log2_TPM_plus_1, assay_valid:boolean, missing_reason|null, growth_rate_per_hr|null, batch_id|null, platform, normalization_method, technical_aggregation_method_ref|null, source_record_id}`.

Values in this branch must be nonnegative transformed expression. Repeated biological IDs are not extra cultures. All source rows used for the same growth measurement must agree or produce a conflict. Technical replicates use the source protocol before culture means; `source_processed_biological_value` records when only such processed inputs are supplied. Unknown necessary aggregation leaves a mean unavailable.

`ConditionMeans` records, one per relation/cell: `source_block_id`, `relation_id`, `condition_id`, `declared_biological_unit_ids[]`, `paired_valid_biological_unit_ids[]`, `target_mean_log2_TPM_plus_1`, `partner_mean_log2_TPM_plus_1`, `growth_mean_per_hr`, `required_expression_operand_ids[]`, `required_growth_operand_ids[]`, `observed_only_mean_refs[]`, `condition_match_status`.

Means use the entire declared roster for that mean; missing required values yield null. Preserve observed-only means separately. The paired-expression list and all adjustable-condition calculations use the declared full means, preventing a hidden available-case redefinition. Existing complete native and synthetic rosters are unchanged.

| Cell/sheet term | Exact populated fields | Calculation and validation |
|---|---|---|
| Requested scope m | `requested_condition_ids[]`, `requested_m` | Unique nonempty IDs, m=array length. |
| Expression coverage | `paired_expression_condition_ids[]`, `q_pair`, `C_pair` | Subset with both full valid expression means and matched condition; C_pair=q_pair/m. |
| Adjustment coverage | `adjustable_condition_ids[]`, `q_adjusted`, `C_adjusted` | Subset of paired IDs with required known growth means; C_adjusted=q_adjusted/m. |
| Biological units | `n_biological_samples`, `n_technical_measurements|null`, `condition_sample_membership_ref` | Unique biological IDs, separately from condition counts. |
| Co-detection | `codetection_threshold_TPM`, `codetection_threshold_origin`, `codetection_observed_count`, `codetection_requested_denominator` | Threshold=1, origin=`proposed_analytical`; a integer, 0<=a<=q_pair; requested denominator=m. Test both means >=log2(threshold+1). |
| Paired-subset diagnostic | `D_observed_subset` | Cell a/q_pair, or null when q_pair=0. |
| Full-panel co-detection | `D_full_panel` | If q_pair=m, point a/m; else point null, input range [a/m,(a+m-q_pair)/m]. The full denominator is m even if growth is missing. |
| Threshold sensitivity | `codetection_threshold_counts[]` | `{threshold_TPM:1|5|10, observed_count, q_pair, requested_m}`; counts must be realizable integers. Each threshold is a separate analysis. |
| Sample diagnostic | `sample_codetection_numerator`, `sample_codetection_denominator` | Integer counts for source samples; not silently substituted for condition D. |
| Missing operands | `missing_expression_operands[]`, `missing_growth_operands[]` | `{gene_object_id|null, condition_id, biological_unit_id|null, operand_id, unit, known_lower|null, known_upper|null, constraint_source_ref|null}`. Explicitly distinguish expression and covariate failures. |

### `calculate_native_expression_statistics` — proposed, unimplemented

Input: the declared full condition means, observed adjustable subset, required mapping H0, family membership and independence/covariance declaration. Outputs for **each of the two separate scopes** are:

`CorrelationRecord = {statistic_id, scope_id, exact_condition_ids[], n_condition_units, covariate_model:intercept_growth|intercept_only_constant_growth, growth_covariates_k, residual_df, raw_pearson_r, residual_cross_product, residual_ss_target, residual_ss_partner, partial_r, t_statistic, p_two_sided, fisher_z_se, family_id, family_size_M, ordinary_r_ci95, family_r_ci95, interval_unavailable_reason, leave_one_condition_out_records[], source_record_ids[], input_mean_cell_ids[]}`.

`leave_one_condition_out_records[]` contains `{omitted_condition_id, r|null, missing_reason|null}`. Min/max uses valid deletion values, but `sensitivity_complete:boolean` is false if any deletion is undefined. No hidden effective-n claim is made for dependent time series or repeated individual measures.

| Sheet term | Exact output | Calculation/status |
|---|---|---|
| Observed-subset r | `partial_r_observed_subset` | CorrelationRecord over q_adjusted exact IDs. It is never renamed full-panel r. |
| Full-panel r | `partial_r_full_panel` | CorrelationRecord over all m, or null partial_r with domain [-1,1] for unavailable operands. Raw full-panel Pearson can be retained separately when all expression is known but growth is missing. |
| Full-panel positive component | `R_positive_squared_full_panel` | Cell max(0,r_full)^2, or null/[0,1]. A negative defined r gives point 0; an undefined r does not. |
| Full-panel expression support | `E_full_panel` | Cell H0*D_full*R_full. Known H0=0 or D_full=0 fixes E=0. Otherwise missing r leaves a null point and corrected bounds. |
| Bound rule | `full_panel_missing_bound_method` | `complete_inputs` or `outer_domain` for this specified calculation. |
| Extra constraints | `joint_completion_constraints[]` | Typed operand bounds/relationships plus derivation references. The current calculation keeps conservative outer-domain bounds. The parent's optional `derived_joint_completion_bounds` requires a separately explicit mathematical derivation before use; this contract does not claim an unimplemented general optimizer narrows them. |

The descriptive r is computed when its required means and nonzero residual sums of squares exist. The statistical interval is separate: n<=k+3, |r|=1 or an unsupported covariance model yields null CI with reason. A computable descriptive R/E is not discarded solely because the CI is unavailable. The existing t/p require positive df and |r|<1; otherwise leave them null. Constant measured growth selects k=0; missing growth never does.

If the source supplies program output rather than data, it must declare exactly the same transform, units, sample/condition scope, covariates and statistic before it can populate r. A STRING/network score or categorical coexpression label cannot masquerade as Pearson r.

### `read_published_partner_quantities` — proposed, unimplemented

Input: an actually inspected figure/table/caption or an attributed retained extraction, plus its experimental definitions. Output:

`PublishedQuantity = {quantity_id, source_record_id, organism, strain|null, genotype, target_construct_ref, partner_construct_ref, coexistence_arrangement, intended_changed_variable, other_difference_records[], sample_condition_ref, measurement_name, measured_cell, numerator_identity, denominator_identity, normalization_already_applied:boolean|null, biological_n:int|null, technical_n:int|null, reported_uncertainty|null, conditional_derivation_refs[], dependence_block_id, candidate_component_role}`.

`candidate_component_role` is `genomic_observation`, `native_expression_input`, `comparability_diagnostic`, `supply_diagnostic`, `partner_relationship_hypothesis`, or `neighbor_axis_only`. It is not a numerical grade. Every conditional derivation records assumptions and the original measured cell; it does not overwrite a reported number.

| Retained value | Cell populated | Deliberately unfilled |
|---|---|---|
| PpiD 99%, Skp 131%, SurA 95%, loading 112%, each own WT=100 | Reported percent cells; conditional ratio/normalization diagnostics | Native full-panel r, D and E. Normalization status is unknown. |
| NlpI 389, PBP4 441, MepM 341, MepS 3931 molecules/generation | Reported-derived supply cells and explicit conditional arithmetic | Measured steady-state protein stock, demand stoichiometry, native coexpression. |
| Binding/perturbation results used to motivate a partner set | Hypothesis rationale reference | Extra A107 support term or mandatory-partner status without source support. |

### `compile_a107_sheet` — proposed, unimplemented

Inputs: candidate declaration, validated cells above, source/measurement identities, dependence grouping and the exact formula version `A107_complete_024_001_with_parent_missing_condition_correction`. Output fields are:

`{candidate_id, formula_version, proposed_weight_genomic:0.5, proposed_weight_expression:0.5, partner_components[], clause_components[], coordinate, unresolved_operand_ids[], contradiction_records[], dependence_records[], calculation_trace_refs[], status}`.

`partner_components[]` contains `{relation_id, H_partner, P_genomic, G_partner, source_blocks:[{source_block_id, dependence_block_id, H0_target_correspondence, requested_condition_ids, paired_expression_condition_ids, adjustable_condition_ids, q_pair, q_adjusted, C_pair, C_adjusted, codetection_observed_count, D_observed_subset, D_full_panel, partial_r_observed_subset, partial_r_full_panel, R_positive_squared_full_panel, E_full_panel, full_panel_missing_bound_method}], dependence_block_E_cells[], combined_E, s_partner}`.

`clause_components[]` contains `{clause_id, relation_ids[], input_s_cell_ids[], value:Cell}`. `coordinate` is a Cell plus `input_clause_cell_ids[]`. No ambiguous `{C,D,r}` tuple is accepted for an incomplete panel.

Exact reduction:

1. Verify matching object/scope/unit identities and retain valid partial cells on failures. Canonicalize duplicate clause/relation IDs without multiplying credit.
2. Collapse exact duplicate measurement representations by original measurement IDs and values/analysis definition. Conflicting values under one purported measurement ID are a conflict, not silently averaged data.
3. Within each relation and scope, group unresolved overlaps by shared primitive biological/measurement identities (connected overlap groups); treat each as one dependence block. If the declared representations exhaust the permitted alternatives, its nonstatistical range is their range hull and point null. If alternative representations are not bounded/exhaustively specified, use [0,1]. Keep conditional statistical envelopes separate and only with adequate family coverage.
4. Calculate each complete expression block E or its corrected outer range. Across eligible same-question dependence blocks take the minimum. No block gives unknown E/[0,1]. Do not omit an eligible missing block because its score is unknown.
5. Calculate s=G(.5+.5E), required-set minimum and genuine-alternative maximum. Reuse the same cell IDs for shared H0 and shared partners. Optional relations are excluded. Empty/unresolved partner logic returns null/[0,1], not an empty reduction result.
6. Propagate missing domains and statistical intervals in distinct channels. The nonnegative/monotone expressions permit endpoint enclosure without assuming independence. A point is available when inputs are known or the missing-input range collapses; otherwise point remains null. Missing statistical uncertainty does not erase a defined descriptive point, and no missing-input hull is labeled CI.

`status` is `computed_conditional_research_coordinate`, `computed_interval_with_missing_inputs`, `unresolved_partner_definition`, or `unsupported_branch`. It is a result description, not an annotation acceptance or episode stopping condition.

`contradiction_records[]` fields: `{conflict_id, affected_cell_ids[], source_record_ids[], kind:genomic_identity_conflict|measurement_value_conflict|signed_association_discordance|scope_mismatch, resolution_status:unresolved|resolved_by_record, resolution_record_ref|null}`. A signed discordance can be numerically handled by the stated source-block minimum while remaining visible. Genomic identity conflict makes P unknown until resolved.

## 4. Exact end-to-end filled-field map

| Current example | Fields feeding E | Fields feeding G and s | Candidate result |
|---|---|---|---|
| Native YfgM–SecG limiting relation | m=q_pair=q_adjusted=12; a=12; D_full=1; H0=1; r_full=.47022511192948585; R=E=.2211116558890975 | Exact reference P=H=G=1; s=.6105558279445488 | Min with PpiD/SecY/SecE gives .6105558279445488. |
| Native NlpI–MepS shared relation | Complete 12; D_full=H0=1; r_full=−.18118135457850817; E=0 | G=1; s=.5 | The same s_MepS limits both permitted hydrolase alternatives to .5. |
| Synthetic Q complete | m=q_pair=q_adjusted=20; a=16; H0=180/sqrt(200*200)=.9; D_full=.8; r_full=.6; E=.2592 | P=1; H=135/sqrt(180*180)=.75; s=.4722 | max(min(.60736,.4722),min(.60736,.45))=.4722. |
| Corrected missing-panel relation | m=20;q_pair=q_adjusted=16;a=16; D_full point null/[.8,1]; observed r=.6; full r null/[−1,1]; H0=.9; E null/[0,.9] | G=.75; s point null/[.375,.7125] | Any candidate uses this range through its ordinary clause logic; no subset-r point. |
| Missing growth only | m=q_pair=20; a=16; q_adjusted=16; D_full=.8; H0=.9; full r null/[−1,1]; E null/[0,.72] | G=.75; s null/[.375,.645] | Synthetic candidate null/[.45,.60736]. |

These are precisely the cells a future targeted reader must populate. The raw matrix, measured source quantities, proposed scoring arithmetic and future prompt text remain separate responsibilities.
