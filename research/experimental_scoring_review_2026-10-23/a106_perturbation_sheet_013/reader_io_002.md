# Exact proposed population interface for the A106 sheet — revision 002

Additive revision preserving `reader_io.md`: adds separate perturbation/restoration nuisance bounds and corrects aggregation to combine point contributions before applying the joint uncertainty bound. No reader is implemented.

These are **unimplemented function specifications**, targeted to the numerical cells in `a106_numerical_sheet_002.md`. They are not investigation prompts, production schemas, generic grading rules or a new runtime workflow. Literature and dataset inputs populate the same cells. Any scientific interpretation referenced here can be formed after investigating supplied material; no initial annotation or public identifier is required.

## Shared typed values

`NumberCell` has exactly these fields:

| Field | Type / constraint |
|---|---|
| `status` | enum `known`, `unknown`, `censored`, `not_applicable`, `conflicting` |
| `point` | finite real or null; never NaN/Infinity |
| `lower`, `upper` | finite real or null; ordered when both present |
| `unit` | declared endpoint unit, `dimensionless`, `residue`, `bp`, `molecule_per_cell`, or a supplied measurement unit with its scale/normalization declaration |
| `value_kind` | enum `native_measurement`, `derived_quantity`, `proposed_score_transform`, `synthetic_input`, `synthetic_derived` |
| `uncertainty_kind` | enum `none_exact_fixture`, `sd`, `sem`, `confidence_interval`, `deterministic_bound`, `detection_interval`, `rounding_interval`, `unreported`, `source_conflict` |
| `coverage_probability` | real in (0,1) or null; only populated for an actual supported statistical interval |
| `numerator_refs`, `denominator_refs` | lists of exact input-cell references; empty only when the value is not a ratio/count fraction |
| `primitive_refs` | nonempty references to the actual underlying observations/validation records; a derived value carries the union of its dependencies |
| `source_locators` | list of `{source_id, locator_kind, locator}` with `locator_kind` enum `page`, `table_cell`, `figure_panel`, `paragraph`, `dataset_rows`, `synthetic_definition` |
| `unknown_reason` | null or enum from the list below |
| `alternate_values` | list of other `NumberCell` records with their own locators; use for actual source conflicts, not as extra experiments |

Unknown reason codes: `not_reported`, `source_conflict`, `denominator_unknown`, `calibration_unavailable`, `measurement_scale_incompatible`, `detection_limit_unknown`, `uncertainty_unreported`, `dependence_unknown`, `target_unobserved`, `no_correspondence_measurement`, `perturbation_capacity_unmeasured`, `dose_response_unmeasured`, `nuisance_interactions_unbounded`, `condition_scope_mismatch`, `claim_minimum_unspecified`, `zero_denominator`, `not_applicable_to_inference`.

`CountCell` uses the same status/provenance fields plus nonnegative integer `count` or null and `count_relation∈{exact,at_least,at_most,unknown}`. Thus “at least three repeats” is not silently changed to `n=3` in a variance calculation.

No unrestricted generated findings or instructions are needed in these outputs. Source labels and literal experimental descriptions can be retained as scoped source text with locators. Numeric scores must come from the listed measurements/calculations, not a prose-to-confidence conversion.

## Common design and material input

`Material`:

* `material_kind`: `sequence`, `selected_file_record`, `selected_region`, `snippets`, `assayed_construct`.
* `material_ref`, `selected_boundaries`, `observed_sequence` (nullable), `alphabet` (`protein`, `nucleotide`, `unknown`), `completeness` (`complete`, `partial`, `unknown`).
* `declared_scope_length`: CountCell, distinct from number of observed snippet residues.
* `construct_changes`: explicit coordinate/substitution/deletion/tag records, with numbering basis and source locator. Public name/accession optional.

`InferenceScope`:

* `inference_ref`: local identity for an interpretation that has emerged; nullable during discovery.
* `inference_kind`: `component_promotes_endpoint`, `component_represses_endpoint`, `quantitative_necessity`, `residue_required`, `activity_required`, `measured_interchangeability`.
* `endpoint_definition_ref`, `condition_scope_ref`, `orientation`: +1 or −1 when needed, `intended_change_ref`.
* `required_determinants`: explicit finite feature/coordinate requirements or `not_applicable`; unknown required positions cannot become an empty applicable list.
* `minimum_expected_effect`: NumberCell, required only for the quantitative negative route; linked to its endpoint-scale `D_required`.

`Arm`:

* `arm_id`, `role` (`reference`, `perturbed`, `restored`, `nuisance_only`, `measurement_validation`), `population_ref`, `recipient_background_ref`.
* `chromosomal_changes`, `plasmid_construct_refs`, `expressed_protein_refs`, `coexisting_same_protein_wt` (`present`, `absent`, `unknown`), `coexistence_basis` (`explicit_source`, `linked_experimental_design`, `unknown`).
* `protein_donor_ref`, `partner_refs`, `intended_change_ref`, `additional_change_refs`.
* `condition_values`: typed quantity records (time, dose, temperature, medium constituent, induction, etc.) with actual units and source; they are not automatically scores.
* `time_origin` (`start_starvation`, `start_recovery`, `start_induction`, `other_declared`), `sample_time`: NumberCell.
* `biological_unit_ids`, `technical_measurement_ids`, `shared_control_ids`, `validation_batch_ids`, `original_experiment_ref`.

`EndpointDefinition`:

* `kind`: `count_per_exposure`, `fraction`, `positive_rate`, `lag_duration`, `survival_ratio`, `calibrated_concentration`, `other_declared_ratio_scale`.
* `unit`, `meaningful_zero_definition`, `eligibility_population_ref`, `exposure_denominator`, `normalization_basis` (`per_cell`, `per_volume`, `per_input_population`, `per_time`, `other_declared`).
* `raw_scale` (`linear`, `log10`, `log2`, `ln`, `instrument_signal`), `reported_summary` (`arithmetic_mean`, `geometric_mean`, `median`, `single_measurement`, `unknown`), `transform_parameters`.
* `measurement_model`: `identity_validated`, `linear_calibration`, `binary_misclassification`, `count_volume_dilution`, `threshold_crossing`.
* `blank_ref`, `calibration_ref`, `valid_measurement_range`, `detection_limit`, `counting_limit`, `censoring`.

The distinction between mean log counts and log mean counts is mandatory; do not exponentiate one as if it were the other. A native zero is permitted only when the measurement supports exact zero rather than nondetection.

## Proposed targeted functions, all unimplemented

| Function | Exact inputs | Exact output fields populated | Deterministic responsibility and interpretive boundary |
|---|---|---|---|
| `extract_a106_source_design` | Selected source text/figures/tables, `Material`, optional emerged `InferenceScope`, extraction locators | `Arm[]`, `EndpointDefinition`, native `NumberCell[]`, `CountCell[]`, coexistence basis, exact compared constructs, source conflicts | Parses explicit quantities and context. Linked source interpretation is recorded as such; it never assigns an overall quality/relevance score |
| `read_a106_observation_dataset` | Data table with `biological_unit_id`, `arm_id`, `time`, `value/count`, `unit`, `eligible_denominator`, `technical_id`, `calibration_batch`, `censoring`; matching design table | Same native measurement cells and design fields as literature extraction; `raw_observations[]`; observed missingness | Deterministic parsing and unit checks. Repeated rows are not assumed independent |
| `populate_measurement_values` | Raw observations and selected `EndpointDefinition`; actual blank/calibration/reference records | `corrected_observations[]`, calibrated `W_input,K_input,R_input`, `measurement_bounds`, `model_parameters`, `validity_failure_code` | Identity: retain validated values; linear: `(x−b)/a`; binary: `(p−f)/(t−f)`; counts: `count*dilution/plated_volume` then declared exposure denominator; threshold: declared interpolation of the observed curve. Retain uncertainty from all operands; reject a fabricated model fit |
| `summarize_a106_arms` | Corrected values, independent block IDs, weights specified by sampling design, shared controls | `W,K,R`, `D`, `theta`, `n_biological`, `n_technical`, paired covariance or `dependence_unknown`, primitive-reference graph | Average biological units according to the declared design, keeping technical replication inside its unit. A plotted mean without raw units remains an extracted mean with its reported uncertainty |
| `populate_a106_restoration` | Matched `W,K,R` and their joint dependency graph | `restoration_fraction_raw`, `r`, `restoration_bounds`, `restoration_dose_ratio` | Exact formulas in the sheet. Different endpoints/time origins cannot be silently combined. Preserve overshoot and zero-denominator status |
| `populate_a106_comparability` | `intended_change_ref`; nominated distinct nuisance quantities `{quantity_ref,x0,x1,unit,ratio_comparison_justification}`; excluded intended variables; shared primitive refs | `C_components[]`, `C`, bounds and `component_applicability` | Calculates only explicit quantity ratios with meaningful denominators. Does not grade media names or infer matching protein levels from matching inducer instructions |
| `populate_a106_isolation` | Nuisance-only endpoint contrasts or an actual fitted response surface, nuisance set, interaction bounds, control scope, `D` | `B_components`, `B_interaction`, `B_pert`, `B_rest`, `B`, `I`, `B_cancel`, `I_cancel`, `control_coverage_refs` | Computes the two contrast-specific joint bounds or justified sums, then `B=max(B_pert,B_rest*abs(D)/abs(R−K))`; a direct already-combined bound must supply its derivation. A qualitative off-target assurance cannot supply 0 units of nuisance |
| `populate_a106_perturbation_extent` | Reference/perturbed amount and activity measurements; same-protein WT/variant mixture amounts; statement of which molecular capacity the inference requires | `residual_amount_fraction`, `residual_activity_fraction`, `P_effective`, `mutant_molecule_fraction`, activity/amount uncertainty | Uses the capacity named in the inference. Protein abundance does not become activity; molecule fraction does not become phenotype fraction |
| `populate_a106_correspondence` | Supplied target material; actual assayed construct; selected relation code; alignment coordinates/scores or structure scores/feature mapping or independent matched-replacement data; exact condition distributions | `coverage`, `identity`, `determinant_agreement`, native alignment scores, `TM_target_normalized`, `TM_assayed_normalized`, `replacement_agreement`, `M`, `context_frequencies_source`, `context_frequencies_target`, `O`, `H` | Calculates the selected explicit route. No correspondence mean across unrelated metrics, no automatic best-route selection, no evidence transfer to unobserved target residues |
| `propagate_a106_bounds` | All input cells; source-provided intervals/covariance or raw independent blocks; declared joint uncertainty model and coverage; reuse graph | `q_point`, `q_L`, `q_U`, `bound_type` (`conservative_outer`, `joint_confidence`, `deterministic_exact`), `coverage_probability`, `U`, `q`, `unresolved_inputs[]` | Evaluates the single defined formula with shared variables. Interval branches around absolute values/clips are retained. Unknown covariance is not set to zero |
| `populate_a106_counterevidence` | Necessity scope, `theta_required`, `theta_upper`, `D_required`, `B_cancel`, `P_effective`, `C,H` | `deficit`, `I_cancel`, `q_counter`, bounds and applicability reason | Exact negative-route equation; no equivalence from a nonsignificant p-value or qualitative “similar” |
| `compile_a106_groups` | Populated rows, original experiment/biological-unit/endpoint identities, dependence links, one inference and fixed scope | `unique_group_ids`, `primary_endpoint_by_group`, `group_q_point`, `group_bounds`, `weights`, `G`, `Q_point`, `Q_L`, `Q_U`, `Q`, `positive_mass`, `negative_mass`, `consistency`, `A106_support`, `A106_counter`, aggregate bounds, known-subset denominator | Deduplicates actual representations; equal `1/G` weights for signed points; applies the aggregate joint interval once; never silently excludes unknown groups or counts shared controls twice |
| `count_selected_spacer_rows` | Complete selected spacer table, explicit row inclusion and repeated-sequence policy | `listed_total`, `listed_count_by_length`, `listed_count_by_source`, corresponding conditional fractions | Deterministic counts of listed entries; does not infer cells tested, acquisition frequency or independence from distinct sequence strings |

`validity_failure_code` is null or one of `unit_mismatch`, `nonpositive_calibration_slope`, `misclassification_model_unidentified`, `outside_calibration_range`, `unresolved_censoring`, `unmatched_endpoint`, `unknown_mean_transform`, `invalid_physical_value`, `missing_eligible_denominator`. These are specific missing/invalid population facts, not a new runtime acceptance gate.

## Returned numerical row

`A106NumericRow` consists of exactly:

```
inference_scope, scoring_mode, material_ref, source_experiment_refs,
arm_refs, endpoint_definition_ref, intended_change_ref,
W, K, R, D, theta,
restoration_fraction_raw, r,
C_components, C,
B_components, B_interaction, B_pert, B_rest, B, I,
residual_amount_fraction, residual_activity_fraction,
P_effective, mutant_molecule_fraction, rescue_amount_ratio,
correspondence_route, coverage, identity, determinant_agreement,
TM_target_normalized, TM_assayed_normalized, replacement_agreement,
M, context_frequencies_source, context_frequencies_target, O, H,
joint_uncertainty, primitive_dependency_refs,
q_point, q_L, q_U, U, q,
theta_required, D_required, B_cancel, I_cancel, deficit, q_counter,
n_biological, n_technical, shared_control_ids, biological_unit_ids,
original_experiment_ref, contribution_group_ref,
unresolved_inputs, reader_status
```

All numeric fields are `NumberCell`/`CountCell` as appropriate; nonapplicable route fields are explicitly `not_applicable`, not unexplained empty numbers. `reader_status` is `unimplemented` for this draft. The scope and primitive references are implementation/provenance fields, not proposed additions to model-facing prompts.

`A106Compilation` returns `inference_scope`, `group_rows`, `G`, `weights`, `Q_point`, `Q_L`, `Q_U`, `Q`, `positive_mass`, `negative_mass`, `consistency`, `A106_support`, `A106_counter`, `aggregate_bounds`, `known_subset_denominator`, `unresolved_group_refs`, `formula_version`, `reader_status`. No output calls this an adopted annotation policy, scientific completion, or information-yield observation. W05 remains responsible for connecting accepted numeric outputs to annotation credit.

## Meaningful relationship checks

The proposed reader must preserve these relationships rather than merely validating JSON types:

1. `W,K,R` share endpoint units, eligibility, time origin, intended question and applicable conditions. A recovery lag cannot be paired with a survival CFU value.
2. Denominator controls and repeated measurements refer to actual records. Replication counts distinguish independent biological units from technical measurements and from lower bounds.
3. An intended amount decrease cannot also be a `C_j` nuisance penalty. A shared expression quantity cannot appear twice in `C` through renamed measurements.
4. A `B` bound evaluates the same endpoint and covers the declared nuisance set; individual bounds require an explicit interaction treatment before they become a sum.
5. Variant and WT coexistence is established independently of relative expression values. A 0.64 signal ratio does not encode a 64%/36% mixture.
6. A homolog relationship uses actual observed correspondence to supplied material. Missing sequence boundaries or critical residues remain unknown, and the same replacement dataset is not used twice.
7. Every uncertainty bound retains its actual meaning; no independence is inferred from separated table rows. The aggregate retains conflicting observations and unknown groups.
8. Numerical source conflicts remain alternatives under one experiment identity. They are not averaged without a defined reconciliation model and not counted as replication.

These checks state implementation responsibilities for later targeted readers. They do not implement a scheduler, reviewer, approval step, stopping criterion or experimental run.

`scoring_mode` is `restoration_effect` or `necessity_challenge`. It selects the scientific estimand, not the most favorable result. `B_pert` and `B_rest` retain independent primitive references and units; they may share controls, whose dependence remains explicit. For aggregate uncertainty, weights apply to the signed point formula and its joint enclosure. A nearest-to-zero aggregate bound supplies `Q`; per-row uncertainty factors are not multiplied again.
