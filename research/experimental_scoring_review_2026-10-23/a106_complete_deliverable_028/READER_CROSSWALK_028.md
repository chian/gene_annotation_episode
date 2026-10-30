# Exact population contract for the consolidated A106 sheet

All functions below are **UNIMPLEMENTED**. This is the targeted reader/field
specification for [the current numerical proposal](A106_NUMERICAL_SHEET_028.md),
not a prompt, executable schema, generic grading interpreter or production
publication. Literature and dataset paths populate the same cells. The current
formula identifier is `a106_consolidated_proposal_028`; its same-statement
pooling identifier is `correspondence_sum_floor_one_v1`.

This specification joins [row IO 003](../a106_perturbation_sheet_013/reader_io_003.md),
the [candidate additions](../a106_candidate_reduction_019/READER_IO_ADDITIONS_001.md)
and [final clarifications](../a106_candidate_reduction_019/FINAL_CLARIFICATIONS_002.md).
It preserves their underlying cells while correcting the aggregate path
throughout. The historical `compile_a106_groups` equal-`1/G` behavior is not
the current reader contract. Group count remains provenance and never becomes
the current numerical denominator. No additional source interpretation is claimed.

## Common value types

Every numeric field below is a `NumberCell` unless specified as `CountCell`,
an exact finite enum, or a literal formula constant. No NaN/infinity is allowed.

| `NumberCell` field | Exact type and meaning |
| --- | --- |
| `status` | `known`, `unknown`, `censored`, `not_applicable`, `conflicting` |
| `point` | Finite real or null; unavailable nominal values remain null |
| `lower,upper` | Finite real or null; ordered and containing an available point when both exist |
| `unit` | Declared measurement unit or `dimensionless`, with scale/normalization linked to the endpoint/quantity definition |
| `value_kind` | `native_measurement`, `derived_quantity`, `proposed_score_transform`, `synthetic_input`, `synthetic_derived` |
| `uncertainty_kind` | `none_exact_fixture`, `exact_count`, `sd`, `sem`, `confidence_interval`, `deterministic_bound`, `detection_interval`, `rounding_interval`, `mathematical_domain`, `unreported`, `source_conflict` |
| `coverage_probability` | Number in (0,1) or null; populated only for supported statistical coverage |
| `numerator_refs,denominator_refs` | Lists of exact input-cell references for a ratio; non-ratio values may use empty lists |
| `primitive_refs` | Unique observation/validation dependencies; derived values retain their union |
| `source_locators` | List of `{source_ref,locator_kind,locator}`; `locator_kind` is `page`, `table_cell`, `figure_panel`, `paragraph`, `dataset_rows`, `synthetic_definition` |
| `unknown_reason` | Null or one code below; required when an expected operand is unavailable |
| `alternate_values` | Source-conflicting alternative `NumberCell` values with their own locators; not new observations |

Unknown reasons are `not_reported`, `source_conflict`, `denominator_unknown`,
`calibration_unavailable`, `measurement_scale_incompatible`,
`detection_limit_unknown`, `uncertainty_unreported`, `dependence_unknown`,
`target_unobserved`, `no_correspondence_measurement`,
`perturbation_capacity_unmeasured`, `dose_response_unmeasured`,
`nuisance_interactions_unbounded`, `condition_scope_mismatch`,
`claim_minimum_unspecified`, `zero_denominator`, `not_applicable_to_inference`.

Known/censored measured or derived values require actual primitive references.
An unknown cell may have none if its point is null and its missing reason plus
source locator/requested-input reference identify the absent evidence. This
retains the final correction to the old unconditional nonempty rule. A domain
bound does not invent an empirical point. A native exact count is conditional
on the actual counting observation; it is not an exact population probability.

`CountCell` retains the same status/provenance/uncertainty fields and adds
`count: nonnegative integer|null` and
`count_relation: exact|at_least|at_most|unknown`. At-least-three repetition is
not an exact biological n for variance calculation.

An inapplicable measured component has no invented measurement. Its declared
identity multiplier, where the formula permits one, is a separate derived
cell with the applicability basis. Unknown and inapplicable are different.

## Exact design and native input records

IDs, hashes, revisions and custody references below stay in implementation and
research records. They are not instructions for future model-facing TASK or
STEERING. Source-linked literal descriptions may supply definitions; no free
generated confidence, findings or instruction field supplies a number.

| Record | Exact fields |
| --- | --- |
| `Material` | `material_ref`; `material_kind∈{sequence,selected_file_record,selected_region,snippets,assayed_construct}`; `selected_boundaries`; nullable `observed_sequence`; `alphabet∈{protein,nucleotide,unknown}`; `completeness∈{complete,partial,unknown}`; `declared_scope_length:CountCell`; `construct_changes[]` with coordinate, numbering basis, change and source locator. Public name/accession optional |
| `InferenceScope` | `statement_ref`; `target_material_ref`; `inference_kind∈{component_promotes_endpoint,component_represses_endpoint,quantitative_necessity,residue_required,activity_required,measured_interchangeability}`; `endpoint_definition_ref`; `condition_scope_ref`; `orientation∈{-1,+1}`; `intended_change_ref`; `required_determinants[]`; `determinant_applicability∈{applicable,not_applicable,unknown}`; `determinant_basis_ref`; nullable `minimum_effect_definition_ref` |
| `MinimumEffectDefinition` | `minimum_effect_ref`; `statement_ref`; actual `minimum_basis_ref`; `W_required,K_required,D_required,theta_required`; `translation_model_ref`; `primitive_dependency_refs`. Supplied `D_required,theta_required` must have the same claimed meaning; a raw p-value cannot supply them |
| `Arm` | `arm_ref`; `role∈{reference,perturbed,restored,nuisance_only,measurement_validation}`; `population_ref`; `recipient_background_ref`; `chromosomal_changes[]`; `plasmid_construct_refs[]`; `expressed_protein_refs[]`; `coexisting_same_protein_wt∈{present,absent,unknown}`; `coexistence_basis∈{explicit_source,linked_experimental_design,unknown}`; `protein_donor_ref`; `partner_refs[]`; `intended_change_ref`; `additional_change_refs[]`; typed `condition_values[]`; `time_origin∈{start_starvation,start_recovery,start_induction,other_declared}`; `sample_time`; `original_experiment_ref` |
| `EndpointDefinition` | `endpoint_ref`; `kind∈{count_per_exposure,fraction,positive_rate,lag_duration,survival_ratio,calibrated_concentration,other_declared_ratio_scale}`; `unit`; `meaningful_zero_definition_ref`; `eligibility_population_ref`; `exposure_denominator`; `normalization_basis∈{per_cell,per_volume,per_input_population,per_time,other_declared}`; `raw_scale∈{linear,log10,log2,ln,instrument_signal}`; `reported_summary∈{arithmetic_mean,geometric_mean,median,single_measurement,unknown}`; `transform_parameters`; `measurement_model_ref`; `detection_limit,counting_limit`; `censoring_ref` |
| `Observation` | `original_observation_ref`; `representation_refs[]`; nullable `correction_of_ref`; `arm_ref`; `endpoint_ref`; `biological_unit_ref`; `technical_measurement_ref`; `sampling_design_ref`; `independence_basis_ref`; `raw_value`; `eligible_denominator`; `sample_time`; `unit`; `calibration_batch_ref`; `shared_control_refs[]`; `censoring_ref`; `source_locators[]` |
| `PairedBiologicalBlock` | `biological_unit_ref`; `sampling_design_ref`; ordered `paired_endpoint_vector[]` of `{endpoint_ref,arm_ref,value_cell_ref}`; `covariance_model_ref`; `primitive_dependency_refs` |
| `SamplingDesign` | `sampling_design_ref`; eligible `biological_unit_refs[]`; technical-to-biological mapping; `sampling_weights[]` with unit refs, nonnegative numeric weights and denominator refs; `weighting_basis_ref`; `covariance_model_ref`; `independence_basis_ref` |
| `MeasurementModel` | `measurement_model_ref`; `kind∈{identity_validated,linear_calibration,binary_misclassification,count_volume_dilution,threshold_crossing}`; `validation_population_ref`; `blank_ref`; `calibration_ref`; `valid_range`; `slope,intercept,sensitivity,false_positive_rate,plated_volume,dilution` when applicable; `threshold`; exact `interpolation_or_fit_ref`; `model_parameter_dependencies[]`. Unused model-specific fields are explicitly inapplicable |
| `ComparabilityInput` | `quantity_ref`; `statement_ref`; `comparison_arm_refs`; `x0,x1`; `unit`; `ratio_comparison_basis_ref`; `intended_change_ref`; `component_applicability∈{applicable,not_applicable,unknown}`; `applicability_basis_ref`; `distinct_quantity_identity`; `primitive_refs` |
| `ComparabilitySet` | `statement_ref`; `component_refs[]`; `nominated_quantity_set_ref`; `scope_status∈{declared_for_question,unresolved}`; `empty_set_identity_basis_ref` when empty. No nomination alone does not establish comparability 1 |
| `NuisanceBoundInput` | `bound_ref`; `contrast∈{perturbation,restoration,cancellation}`; `statement_ref`; `endpoint_ref`; `nuisance_set_ref`; `bound_method∈{direct_joint_contrast,justified_triangle_sum,measured_response_model}`; `nuisance_control_refs[]`; `component_bounds[]`; `interaction_bound`; `triangle_bound_basis_ref`; `response_model_ref`; `control_scope_ref`; `coverage_basis_ref`; `joint_dependency_refs` |
| `CapacityInput` | `statement_ref`; `required_capacity_kind∈{amount,relevant_activity}`; `capacity_basis_ref`; `reference_amount,perturbed_amount,restored_amount`; `reference_activity,perturbed_activity`; `normalization_basis_ref`; `A_mutant,A_WT`; `mixture_design_ref`; `primitive_refs` |

For model calculations, `slope>0`, `sensitivity>false_positive_rate`, and
physical/proportional domains are checked against their actual meaning. These
are population responsibilities; they add no runtime approval stage.

## Exact correspondence inputs

`CorrespondenceInput` has `relation_ref`, `target_material_ref`,
`assayed_material_ref`, `route∈{verified_identity,sequence,structure,independent_replacement}`,
`route_basis_ref`, `identity_boundary_ref`, `sequence_mapping_ref`,
`structure_mapping_ref`, `replacement_ref`, `context_comparison_ref`,
`primitive_refs`. Only the scientifically selected applicable route is used;
other route fields are explicitly inapplicable. A reader does not maximize over
routes or equate missing correspondence with no correspondence.

| Route input record | Exact native fields and output mapping |
| --- | --- |
| `SequenceMapping` | `alignment_ref`; `target_scope_length,paired_target_residue_count,nongap_pair_count,identical_pair_count:CountCell`; `alignment_coordinates_ref`; `raw_alignment_score,E_value`; `required_determinant_count,preserved_determinant_count:CountCell`; `determinant_mapping_ref`; `determinant_applicability`; `determinant_basis_ref`. Ratios populate `coverage`, `identity`, `determinant_agreement`; the applicable or justified-identity `determinant_multiplier` supplies the product |
| `StructureMapping` | `comparison_ref`; `TM_target_normalized,TM_assayed_normalized`; both normalization lengths; `structure_region_refs`; required/preserved determinant counts and mapping/basis as above; native feature uncertainty. `M=min(TM_target_normalized,TM_assayed_normalized)*determinant_multiplier` |
| `ReplacementComparison` | `replacement_ref`; `K,R_target,R_homolog`; `recipient_background_ref`; `endpoint_ref`; `condition_scope_ref`; `amount_control_refs`; `original_observation_refs`; `independence_from_scored_restoration_basis_ref`; joint dependencies. Output `replacement_agreement` uses the exact restoration-like ratio in the sheet |
| `ContextComparison` | `context_comparison_ref`; fixed `joint_partition_ref`; `condition_scope_ref`; `source_population_ref,target_population_ref`; `source_states[],target_states[]`, each `{state_ref,count,denominator,frequency}`; `verified_same_scoped_system_basis_ref`; shared dependencies. Outputs empirical vectors and `O=sum min`; same-scope identity supplies 1 only with its basis |

## Numerical row and group outputs

`A106NumericRow` contains exactly the fields below. The names `source_effect`
and `a` denote one cell, and `q_point=H*a` always denotes the unreduced row.

```
row_ref, statement_ref, scoring_mode, material_ref, source_experiment_refs,
arm_refs, endpoint_definition_ref, intended_change_ref,
W, K, R, D, theta, restoration_fraction_raw, r,
C_components, C, comparability_set_ref,
B_components, B_interaction, B_pert, B_rest, B, I_pert, I_rest, I,
residual_amount_fraction, residual_activity_fraction,
P_effective, mutant_molecule_fraction, rescue_amount_ratio,
correspondence_relation_ref, correspondence_route,
coverage, identity, determinant_agreement, determinant_multiplier,
raw_alignment_score, E_value, TM_target_normalized, TM_assayed_normalized,
replacement_agreement, M,
context_frequencies_source, context_frequencies_target, O, H,
minimum_effect_definition_ref, theta_required, D_required,
B_cancel, I_cancel, deficit_point, deficit_lower, deficit_upper,
source_effect, source_effect_lower, source_effect_upper,
q_point, q_lower, q_upper, row_resolved_diagnostic,
joint_uncertainty_ref, primitive_dependency_refs,
n_biological, n_technical, shared_control_refs, biological_unit_refs,
original_experiment_ref, contribution_group_ref,
validity_failure_code, unresolved_inputs, reader_status
```

`scoring_mode∈{restoration_effect,necessity_challenge}`. Nonapplicable mode fields
retain that status. The necessity mode outputs negative `source_effect` and
`q_point` in the same cells; there is no second counterevidence row to add.
Historical `q_counter_point,q_counter_L,q_counter_U` are aliases, not separate
contributions. `row_resolved_diagnostic` may display a nearest-to-zero row bound
when identified, but is never an input to statement pooling. The historical
uncertainty ratio `U` is unnecessary for calculation and is omitted from this
current returned contract; there is no missing factor to fill in its place.

`validity_failure_code` is null or `unit_mismatch`,
`nonpositive_calibration_slope`, `misclassification_model_unidentified`,
`outside_calibration_range`, `unresolved_censoring`, `unmatched_endpoint`,
`unknown_mean_transform`, `invalid_physical_value`, `missing_eligible_denominator`.

`A106ContributionGroup` contains exactly:

```
group_ref, statement_ref, original_group_ref,
sampling_design_ref, primary_endpoint_ref, unique_biological_unit_refs,
row_refs, within_group_estimand, endpoint_weights,
correspondence_relation_refs, source_effect, H, q_point,
composite_q_sum, composite_H_sum,
joint_dependency_refs, missing_input_refs, reader_status
```

`within_group_estimand∈{primary_endpoint,declared_endpoint_mean,declared_population_mean}`.
`endpoint_weights` is empty for primary or a list of
`{endpoint_ref,weight,denominator_ref}` with nonnegative weights summing to one.
For a composite, output `sum(w*q)` and `sum(w*H)` explicitly and factor their
ratio only when the second is positive. The primary case uses its row's `a,H,q`.
All-zero composite H identifies q=0 without identifying a. Required endpoints
cannot be converted to an average for convenience.

## Statement and candidate inputs/outputs

`StatementPoolingInput` has exactly `statement_ref`, `observed_group_refs`,
`unavailable_group_refs`, `H_equality_classes`, `shared_primitive_refs`,
`source_effect_domain`, `pooling_rule`, `normalization_floor`.
`pooling_rule` is the literal `correspondence_sum_floor_one_v1`; floor is the
proposed exact constant 1. H equality classes identify exact shared variables,
not similar molecules or correlation clusters. Unavailable groups already
observed remain in the roster; unperformed experiments are not fabricated.

`A106StatementReduction` contains exactly:

```
statement_ref, formula_ref, current_group_refs,
group_source_effect_cells, group_H_cells, group_q_cells,
unique_biological_counts, T, d,
positive_numerator, negative_numerator, N,
Q_point, Q_lower, Q_upper, consistency,
bounds_method, joint_uncertainty_ref, primitive_dependency_refs,
missing_input_refs, result_status, reader_status
```

`T=sum H`, `d=max(1,T)`, `N=sum(H*a)`, `Q_point=N/d`. There are no `1/G`
weights, known-subset renormalization, per-row uncertainty weights or aggregated
row-resolved values. `consistency=abs(N)/(positive_numerator+negative_numerator)`
when defined and is diagnostic only. `result_status` is `observed_point`,
`measurement_interval_crosses_zero`, `missing_inputs`, `algebraically_identified`,
`no_data` or `invalid_inputs`. `d` is never labeled sample size.

`CandidateA106Definition` contains exactly `candidate_ref`,
`target_material_ref`, `revision_ref`, `previous_revision_ref`,
`definition_origin∈{emerged_from_investigation,supplied_candidate}`,
`a106_statement_refs`, `expression`, `canonical_statement_aliases`,
`content_change∈{initial,evidence_only,source_correction,scope_qualification,asserted_meaning_change}`,
`prior_scope_ref`, `current_scope_ref`, `competing_candidate_refs`, `formula_ref`.
Aliases are `{alias_ref,canonical_ref,basis_ref}` with actual declared semantic
basis. Empty statement refs are allowed only with explicit no-axis-question
status. The expression is the tagged union:

```
{kind: leaf, statement_ref}
{kind: all_of, children: nonempty list[CandidateExpression]}
{kind: any_of, children: nonempty list[CandidateExpression]}
```

The reader parses already declared biological meaning. Missing relationships
remain missing; scores do not determine whether a condition is necessary or
sufficient. Competing candidates are not inserted as an any-of shortcut.

`CandidateJointUncertainty` contains exactly `primitive_variables`,
`joint_model_ref`, `shared_variable_occurrences`, `covariance`,
`continuous_bounds`, `finite_joint_scenarios`, `method`,
`analytic_derivation_ref`, `relaxed_constraints`, `interval_meaning`,
`coverage_probability`, `missing_input_refs`.

Each primitive lists its unique reference, nominal cell, bounds and scientific
meaning. Method is `box_linear_fractional_vertices`, `joint_finite_enumeration`
or `joint_analytic_monotonicity`; an analytic method requires its complete
domain/proof reference. Row interval arithmetic may provide the containing
boxes. Interval meaning is `deterministic_domain`, `deterministic_exact`,
`conservative_outer` or `joint_confidence_region_image`. Exact-for-a-relaxed-box
does not mean exact for the original shared admissible set. Covariance is an
actual named-variable matrix or null, never an invented diagonal matrix.

`A106CandidateReduction` contains exactly:

```
candidate_ref, target_material_ref, revision_ref, previous_revision_ref,
current_scope_ref, content_change, expression, canonical_statement_refs,
statement_reduction_refs,
candidate_point, candidate_lower, candidate_upper,
signed_A106, A106_coordinate, coordinate_lower, coordinate_upper,
coordinate_status, unresolved_statement_refs, missing_input_refs,
shared_primitive_refs, joint_uncertainty_ref, bounds_method,
coverage_probability, interval_meaning, formula_ref, reader_status
```

`coordinate_status` is `observed_resolved_support`, `observed_unresolved_sign`,
`observed_opposition`, `identified_zero_with_missing_inputs`, `missing_inputs`,
`no_data`, `no_axis_question`, `invalid_candidate_meaning` or `invalid_inputs`.
Point and conservative signed value are separate cells. Missing signed values
stay null even when an entirely nonpositive image identifies coordinate 0.
W05 would consume the accepted candidate coordinate and its missingness contract;
this proposal does not adopt that connection or change a global formula.

## Exact targeted function-to-cell crosswalk

Every listed function has `reader_status=unimplemented`.

| Proposed function | Exact required inputs | Cells/records populated and calculation |
| --- | --- | --- |
| `extract_a106_source_design` | Selected text/figures/tables, Material, optional emerged scope, locators | Arm, EndpointDefinition, Observation, CapacityInput, actual comparability/control/correspondence operands; preserves explicit versus linked-design interpretations and source conflicts |
| `read_a106_observation_dataset` | Native rows `biological_unit_id,arm_id,time,value_or_count,unit,eligible_denominator,technical_id,calibration_batch,censoring`, plus actual design mapping | The same Observation/design records as literature extraction; no inference of independent n from row count |
| `identify_a106_observations` | Original experiment/design records, dataset custody, representation/correction links | Canonical observation IDs, aliases and supersession; repeated representations/current corrections consume one observation |
| `populate_measurement_values` | Observation, selected MeasurementModel, actual validation/calibration/blank data | Corrected endpoint observations, parameter/bound dependencies and validity failures; uses exactly the applicable measurement equation |
| `update_a106_group_statistics` | Corrected unique observations, SamplingDesign, PairedBiologicalBlock, actual covariance/model | `W,K,R,n_biological,n_technical,covariance_of_mean`, primitive graph; updates real sampling information without report votes |
| `summarize_a106_arms` | Those current means and endpoint definition | `D=W-K`, `theta=D/(W+K)` with domains and uncertainty; no arbitrary conversion from mean-log to arithmetic mean |
| `populate_a106_restoration` | Matched W,K,R, shared dependencies and dose inputs | `restoration_fraction_raw,r,rescue_amount_ratio`; preserves overshoot and undefined denominator cells |
| `populate_a106_comparability` | ComparabilitySet and distinct ComparabilityInput records | `C_components,C`; exact min/max ratios and product; excludes the intended change and repeated proxies |
| `populate_a106_isolation` | NuisanceBoundInput records, W,K,R and MinimumEffectDefinition where needed | `B_components,B_interaction,B_pert,B_rest,B,I_pert,I_rest,I,B_cancel,I_cancel`; explicit joint bounds/justified sums and appropriate denominators |
| `populate_a106_perturbation_extent` | CapacityInput and the statement's actual required capacity | `residual_amount_fraction,residual_activity_fraction,P_effective,mutant_molecule_fraction`; no abundance-to-activity or molecule-to-phenotype substitution |
| `populate_a106_correspondence` | CorrespondenceInput and selected route/context records | `coverage,identity,determinant_agreement,determinant_multiplier`, native comparison scores, `replacement_agreement,M`, context vectors, `O,H`; retain original primitive reuse |
| `populate_a106_counterevidence` | Quantitative necessity scope, MinimumEffectDefinition, theta, P_effective,C,I_cancel,H | `theta_required,D_required,deficit_point,deficit_lower,deficit_upper` and the necessity-mode a/q; no minimum invented after seeing results |
| `factor_a106_row_contribution` | Selected mode and its actual factors | `source_effect=s*theta*r*C*I` or `-deficit*P_effective*C*I_cancel`; `q_point=H*source_effect`; necessity aliases refer to this same row |
| `propagate_a106_bounds` | Row operands, unique primitive graph and actual joint uncertainty | `source_effect_lower,source_effect_upper,q_lower,q_upper`; optional `row_resolved_diagnostic`; domain, singularity and outer-bound labels remain explicit |
| `assemble_a106_group` | Current row refs, actual primary/composite estimand and weights, design/control identities | A106ContributionGroup; `q=sum(w*q)`, `H=sum(w*H)`, `a=q/H` if H>0; retains all dependencies |
| `populate_a106_statement_pool` | StatementPoolingInput plus current groups | T,d,positive_numerator,negative_numerator,N,Q_point,consistency exactly as above; empty roster gives no-data, missing operands stay present |
| `bound_a106_statement_pool` | Row a/H intervals, exact H equality classes, shared joint uncertainty | Q_lower/Q_upper from box vertices plus floor-one hyperplane-edge intersections, or actual joint method; reused H is collapsed with multiplicity coefficients |
| `read_declared_candidate_a106_definition` | Current candidate content with target/scope, explicitly declared statements/directions/all-any relations and alias bases | CandidateA106Definition/Expression or exact missing/invalid-meaning status; deterministic parsing of declared relations, never numerical invention |
| `populate_candidate_a106_expression` | Definition and statement reductions | Canonical leaf mapping, candidate_point via min/max, algebraically identified constants; competing candidates remain separate |
| `bound_candidate_a106_expression` | Same expression, shared uncertainty and leaf bounds | Candidate lower/upper via monotone min/max enclosure or complete joint method; actual coverage and relaxed constraints retained |
| `reduce_candidate_a106_uncertainty` | Candidate point/bounds and missing-input dependencies | One nearest-to-zero signed_A106, one positive-part A106_coordinate, coordinate image bounds and precise null/identified-zero status |
| `retain_candidate_a106_revision` | Persistent material/candidate identities, prior immutable snapshot, current inputs/results | Current evidence/meaning snapshot and predecessor links; no historical summation/maximization. This is a future IO responsibility, not implemented storage |
| `count_selected_spacer_rows` | Complete selected table, actual inclusion and repeated-sequence policy | `listed_total,listed_count_by_length,listed_count_by_source`, corresponding conditional fractions with listed-entry denominators. These diagnostic cells are not acquisition probability or independent n |

## Population relationships to preserve

W,K,R must share endpoint, units, eligibility and scope. Recovery growth and
survival cannot be joined merely because the same gene is studied. Relative
amount cannot establish WT/variant coexistence. Perturbation and restoration
need their own nuisance bounds; a selective perturbation alone does not exclude
a bypass rescue. Unknown interactions remain unknown. Control and transfer
variables reused in multiple cells or statements retain exact identities.

The current row-to-candidate path is always unreduced `a,H,q` → `N/max(1,T)`
per statement → declared min/max candidate → joint interval → one final
uncertainty reduction. Historical fields `G,weights,Q,A106_support,A106_counter`
from the equal-roster aggregate are not current candidate fields. They may only
be read as historical versioned output, not silently mapped into the new result.

Actual biological blocks alter the sampling model; citations, time points,
technical wells, selected clones and duplicate panels do not automatically add
independent units. A quantity used in two score components is one observation,
not independent corroboration. No function asks a model for an overall intuitive
relevance or reliability grade. Semantic scope decisions remain explicit
scientific inputs; their numerical consequences are the defined calculations.

## Additive clarification: preserve the actual reported SD and SEM

The parent review identified an omission in the first `NumberCell` table:
`uncertainty_kind=sd|sem` names an error measure but does not store its numeric
magnitude. The table is extended by these exact fields. Its earlier contents
remain preserved; `lower,upper` must not be used to encode point ± SD or SEM
as if these were confidence or deterministic bounds.

| Additional `NumberCell` field | Exact type and meaning |
| --- | --- |
| `reported_sd` | Finite nonnegative real or null, in the same unit as `point`; the actual reported/calculated SD magnitude |
| `reported_sem` | Finite nonnegative real or null, in the same unit as `point`; the actual reported/calculated SEM magnitude |
| `reported_sd_basis_ref` | Reference to the exact `ReportedErrorBasis` record or null with missingness retained |
| `reported_sem_basis_ref` | Reference to the exact `ReportedErrorBasis` record or null with missingness retained |

`ReportedErrorBasis` contains exactly:

```
error_basis_ref, estimand_ref,
sampling_unit_kind, sampling_unit_definition_ref, sampled_unit_refs,
reported_count, count_relation, count_basis_ref,
calculation_method_ref, source_locators, unknown_reason
```

`sampling_unit_kind` is `biological_unit`, `technical_measurement`,
`paired_biological_block`, `other_declared` or `unknown`.
`reported_count` is a nonnegative integer or null;
`count_relation` is `exact`, `at_least`, `at_most` or `unknown`.
`sampled_unit_refs` lists actual known units and may be empty when their
identities were not supplied; a source-locator/count basis then retains what
was actually reported. `estimand_ref` names the quantity whose variability or
standard error is being described. `calculation_method_ref` identifies the
actual source calculation, supplied analysis model or explicit missing method.
Unknown basis/count is not inferred from the number of plotted points.

`extract_a106_source_design` and `read_a106_observation_dataset` populate these
reported magnitudes and their actual bases. `update_a106_group_statistics`
can calculate them only from the declared sampling design/model and unique
observations, retaining that derivation and count. `propagate_a106_bounds`
consumes the actual statistical model, not an implicit SD/SEM-to-interval
conversion. Neither `SEM=SD/sqrt(n)` nor a confidence multiplier is applied
without the corresponding valid sampling/model basis and exact applicable n.
An at-least-three count cannot silently become exact n=3. Reported error-bar
type with unread/unreported magnitude remains explicitly unresolved.

These fields preserve reported uncertainty; they add no scoring multiplier,
new empirical observation, or biological precision. Confidence/deterministic/
detection/rounding bounds remain separate with their own actual coverage basis.
