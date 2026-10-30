# Exact populating-reader crosswalk for the current A110 sheet

This is the IO specification for
[the current numerical sheet](A110_CURRENT_NUMERICAL_SHEET_026.md). All functions
below are **UNIMPLEMENTED application readers/scorers**. The research arithmetic
script accepts manually entered fixtures; it is not a publication reader,
dataset pipeline or callable episode tool. Investigation prompts remain separate.
No full sheet or host provenance record is proposed as model-facing context.

Literature tables and calibrated dataset rows populate the same numerical
fields. A source reader identifies quantities and experimental meanings; a
deterministic calculator uses the declared equations. If prose interpretation
is needed to identify a subject, denominator or alternative, retain the cited
interpretation and its missing fields. Do not replace unreported measurements
with an unrestricted model confidence.

## Shared types used by every number

`Ref` is an identifier that resolves to a retained source, actual observation,
parameter, model or declared scope. It is not itself a scoring value. All arrays
have explicitly aligned axes and dimensions; missing entries use null, not zero.

| Type/field | Exact population type | Constraint/meaning |
|---|---|---|
| `Origin.kind` | enum: `reported_measurement`, `derived_from_reported`, `derived_from_plot`, `author_proposed_model`, `proposed_scoring_transform`, `synthetic_arithmetic_check` | No synthetic value enters an empirical row |
| `Origin.source_ref`, `locator` | Ref or null; document/table/figure/page/row/window locator or null | Required for reported/plotted inputs |
| `Origin.input_refs` | ordered Ref array, possibly empty for an original measurement | Every derived operand remains traceable; repeated refs expose dependence |
| `Quantity.value` | finite real or null | Nominal value, not an ordinal category |
| `Quantity.unit`, `dimension` | unit text plus powers of amount/time/mass/energy/charge and species basis | Unit conversions must preserve chemical species and denominator meaning |
| `Quantity.denominator_ref` | Ref or null | Supplies/consumption, wet mass, time, pool total or turnover actually used |
| `Quantity.lower`, `upper` | finite real or null; companion `lower_unbounded`, `upper_unbounded` booleans | Ordered domain endpoints if known; null without unbounded flag means unknown |
| `Quantity.uncertainty_kind` | enum: `none_exact`, `reported_sd`, `reported_se`, `reported_ci`, `reported_range`, `reported_unspecified_plusminus`, `plot_extraction_bound`, `model_parameter_bound`, `joint_parameter_domain`, `unknown` | SD/SE is stored as such, not automatically converted into a value interval |
| `Quantity.uncertainty_value` | nonnegative real or null, in Quantity unit | Reported SD/SE/± amount where applicable |
| `Quantity.confidence_level` | real strictly between 0 and 1, or null | Only for a defined confidence/credible interval; otherwise null |
| `Quantity.n`, `sample_unit` | nonnegative integer or null; enum `independent_experiment`, `biological_preparation`, `culture`, `technical_injection`, `timepoint`, `source_summary`, `not_applicable`, `unknown` | Three injections are not three cultures |
| `Quantity.covariance_ref`, `joint_domain_ref` | Ref or null | Null covariance does not assert independence; domains retain shared parameters |
| `Quantity.missing_reason` | enum: `not_missing`, `not_measured`, `not_reported`, `not_retrieved`, `nonidentifiable`, `invalid_denominator`, `unmapped_subject_relation`, `outside_declared_scope` | Missingness is not a numerical source grade |
| `Quantity.origin` | Origin | Every input and derived result has one |
| `Dependence.observation_refs`, `experiment_ref`, `preparation_ref`, `technical_unit_refs`, `shared_axis_refs` | Ref arrays and nullable Ref fields | Deduplicate actual identity, never equality of values |

An approximate source value has unknown uncertainty unless the source supplies
more. `none_exact` is for exact algebra or stipulated synthetic inputs, not a
way to give a published mean zero measurement error.

## Required input records

**Account.** `account_ref:Ref`, `candidate_ref:Ref`, `account_text:string`,
`scope:enum(specified_reaction,specified_atom_source,specified_pathway_budget)`,
`target_material:{kind:enum(sequence,file_selection,snippet),content_ref:Ref,
record_ref:Ref|null,start:int|null,end:int|null,completeness:enum(complete,
partial,unknown)}`, `assayed_subject_ref:Ref`, `target_relation_refs:Ref[]`,
`target_relation_missing:Ref[]`, `turnover_basis:Quantity`, `direction:enum(forward,
reverse,reversible_with_named_test_direction)`, `questions:Question[]`,
`balance_input:BalanceInput`. A candidate_ref can be assigned after discovery;
it is not required to start an investigation. A public protein name is optional.

**Question.** `question_ref:Ref`, `physical_quantity_definition:string`,
`kind:enum(scalar_stoichiometry,isotope_distribution,resource_budget)`,
`weight:{numerator:int>=0,denominator:int>0}`, `parent_block_ref:Ref|null`,
`diagnostic_only:boolean`, `observation_refs:Ref[]`, `alternative_refs:Ref[]`,
`scope_ref:Ref`, `prediction_refs:Ref[]`. Effective block weights multiply and
leaf weights sum to one. A diagnostic has zero added weight; a duplicate
physical question does not obtain another slot. Required-but-missing questions
remain present. Empty alternatives leave a chemical comparison unpopulated.

**ConditionComparison.** `test_condition_ref`, `reference_condition_ref`,
`intended_changed_variable`, and `nonintended_differences[]`; each difference
has `covariate_name`, `x_test:Quantity`, `x_reference:Quantity`,
`beta:Quantity`, `response_calibration_ref:Ref|null`, `model_domain_ref:Ref|null`.
`beta.unit` must equal corrected-quantity-unit/covariate-unit. It is not derived
by counting matching metadata. If a covariate is proven absent from the selected
prediction, record `invariant_model_ref`, not a fabricated measured beta=0.

**CalibrationInput.** `mode:enum(already_calibrated,linear_response,
linear_internal_standard_ratio,explicit_other)`, `reported_quantity:Quantity|null`,
`response:Quantity|null`, `internal_standard_response:Quantity|null`,
`internal_standard_amount:Quantity|null`, `standard_amounts:Quantity[]`,
`standard_responses:Quantity[]`, `alpha:Quantity|null`, `gamma:Quantity|null`,
`dilution_factor:Quantity`, `normalizer:Quantity`, `equation_ref:Ref|null`.
For already_calibrated, reported_quantity is copied with provenance; calibration
is not reapplied. For the two linear modes, alpha/gamma are the actual supplied
calibration coefficients. An explicit_other record must include the actual
equation and parameters; its absence produces a missing calibrated quantity.
This specification does not claim a fit to the source's calibration standards.

**CorrectionInput.** `measurement_equation_ref:Ref`, `background:Quantity`,
`recovery:Quantity`, `intended_fraction:Quantity`, `other_response:Quantity`,
`condition_comparison:ConditionComparison`, `joint_domain_ref:Ref|null`.
Recovery is positive; fraction is in (0,1]. Background shares q_read units,
other_response and b_comp share the corrected quantity unit. The established
physical meaning of lambda is recorded at measurement_equation_ref. Corrections
that are only assumptions go in `conditional_parameters`, with Origin
author_proposed_model/proposed_scoring_transform/synthetic_arithmetic_check.
They do not overwrite missing measured parameters.

**ScalarInput.** `experiment_ref`, `subject_ref`, `direction`,
`numerator_calibration:CalibrationInput`, `denominator_calibration:CalibrationInput`,
`numerator_correction:CorrectionInput`, `denominator_correction:CorrectionInput`,
`ratio_kind:enum(formed_per_consumed,formed_per_supplied,net_signal_per_supplied,
other_explicit)`, `net_terms[]:{quantity_ref:Ref,coefficient:rational}`,
`prediction_inputs:PredictionInput[]`, `dependence:Dependence`.
An optional `SummaryInput` has `mean:Quantity`, `sample_sd:Quantity`,
`independent_n:int|null`, `constant_prediction:Quantity`, `independent_unit_refs:Ref[]`.
Mean/SD/n may replace raw observations only for the Eq. 5 identity's conditions.
Missing source summary variance remains missing.

**IsotopeInput.** `experiment_refs:Ref[]`, `paired_baseline_refs:Ref[]`,
`subject_ref`, `genotype_background_ref`, `condition_comparison`,
`precursor_addition:Quantity`, `ion_windows[]:{index:int>=0,mz_lower:real,
mz_upper:real,adduct_ref:Ref,charge:int,calibration_ref:Ref}`,
`B_read[experiment][window]:Quantity`, `L_read[experiment][window]:Quantity`,
`B_corrections[experiment][window]:CorrectionInput`,
`L_corrections[experiment][window]:CorrectionInput`,
`precursor_area_labeled:Quantity`, `precursor_area_unlabeled:Quantity`,
`p_supplied:Quantity`, `p_pool:Quantity`,
`pool_mixing:{fraction:Quantity,background_fraction:Quantity,model_ref:Ref}|null`,
`models[]:{m:int>=0,model_ref:Ref,parameter_refs:Ref[]}`,
`selected_window_indices:int[]`, `covariance_ref:Ref|null`, `dependence`.
The same window selection applies to B, L and prediction. m must reflect the
declared atom-transfer model; a reader does not infer it from the best score.
No unobserved B/L cell is set to zero. No guessed mass bounds are filled from a
plot's short ion label. The published examples retain those unretrieved fields.

**PredictionInput.** `account_or_alternative_ref:Ref`, `model_kind:enum(
stoichiometric_readout,binomial_convolution,first_two_bin_diagnostic,
explicit_other)`, `reaction_ref:Ref`, `parameter_refs:Ref[]`,
`measurement_operator_ref:Ref`, `formula_text:string`, `formula_origin:Origin`,
`experiment_refs:Ref[]`, `unit`, `joint_domain_ref:Ref|null`.
For stoichiometric readouts, `numerator_terms[]` and `denominator_terms[]` each
contain `species_or_response_ref` and signed rational coefficient per turnover;
declared reporting efficiencies/consumption fractions are explicit parameters.
For isotope models use m, p_pool and B in Eq. 4. An explicit_other model with an
undefined equation stays unpopulated; the function cannot invent chemistry.

**Species / BalanceInput.** Species has `species_ref`, `element_counts:map(
element,nonnegative rational)` or a declared symbolic invariant skeleton,
`charge:rational|symbolic`, `protonation_ref`, `compartment_ref`, `origin`.
BalanceInput has `terms[]:{species_ref,nu:rational}`, `elements:string[]`,
`turnover_basis:Quantity`, `half_reactions[]:{donated:Quantity,accepted:Quantity,
origin}`, `closed_account:boolean`, `missing_terms:Ref[]`,
`cancellation_identity_refs:Ref[]`, `symbolic_cancellation_ref:Ref|null`.
Every element present in the terms must be included; unknown terms are not zero.

**BudgetInput.** `mode:enum(simple_batch,simple_flux,network_flux,energy)`,
`target_output_ref`, `target_direction:enum(nonnegative)`, `v_star:Quantity`,
`time_basis:Quantity|null`, `compartment_ref`,
`resources[]:{resource_ref,U:Quantity,a:Quantity,competition_refs:Ref[],
access_refs:Ref[],origin}`, `regeneration_reaction_refs:Ref[]`,
`S_internal:matrix<rational>|null`, `reaction_refs:Ref[]`,
`l:Quantity[]`, `u:Quantity[]`, `accumulation:Quantity[]`,
`G:matrix<rational>|null`, `h:Quantity[]`, `target_coordinate:int|null`,
`energy_available:Quantity|null`, `ATP_cost:Quantity|null`,
`ATP_demand:Quantity|null`, `joint_domain_ref:Ref|null`, `dependence`.
Every row/column has its identity and units. Bounds mark measurement versus
assumption/unconstrained through Origin/missing_reason. Unknown caps cannot
produce an empirically established f=1. One network already containing energy
does not get a second energy score. An optional NativeModelResult also retains
its actual objective, constraints, result, solver status and tolerance; none
was obtained from a native dataset in this workload.

## Exact output records

| Output record | Fields populated; all numerical fields use Quantity or stated rational weights |
|---|---|
| `CorrectionOutput` | `q_read`, `b_comp_terms[]`, `b_comp`, `b_iso`, `recovery`, `intended_fraction`, `other_response`, `q_corrected`, `joint_domain_ref`, `conditional_parameters[]`, `missing_inputs[]` |
| `MeasurementOutput` | `numerator_corrected`, `denominator_corrected`, `y`; for isotopes `B_corrected[][]`, `L_corrected[][]`, `baseline_total[]`, `labeled_total[]`, `b[][]`, `y[][]`, `selected_window_indices`, `dependence` |
| `PredictionOutput` | `model_ref`, `experiment_refs`, scalar `mu[]` or isotope `f[]`, `u[][]`, `window_total[]`, `mu[][]`, `conditional_parameters[]`, `missing_inputs[]` |
| `ConstraintOutput` | `question_ref`, `residuals_by_model[][]`, `errors_by_unit[]`, `e_claim`, `e_alternative_by_ref`, `s_pair_by_ref`, `s_question`, `pair_bounds_by_ref`, `question_bounds`, `independent_n`, `sample_sd`, `dependence`, `missing_inputs[]`, `conditional_parameters[]` |
| `BudgetOutput` | `status:enum(optimal,zero_capacity,infeasible,unbounded_model,missing_inputs,invalid_demand)`, `z`, `v_star`, `f`, `s_supply`, `active_constraint_refs`, `contradictory_constraint_refs`, `unmeasured_bound_refs`, `feasible_witness:Quantity[]|null`, `bound_certificate_ref:Ref|null`, `dependence` |
| `BalanceOutput` | `canceled_terms[]`, `remaining_terms[]`, `element_totals[]:{element,R,P,residual,d}`, `charge_residual`, `charge_denominator`, `d_Q`, `electrons_donated`, `electrons_accepted`, `electron_residual`, `d_e`, `D`, `D_bounds`, `closed_account`, `missing_terms[]`, `origin` |
| `CompilationOutput` | `account_ref`, `scope`, `question_refs`, `weights`, `question_values`, `question_bounds`, `S`, `S_bounds`, `D`, `D_bounds`, `C_conditional`, `C_bounds`, `unconditional_point:Quantity|null`, `missing_weight_by_question`, `conditional_parameters[]`, `dependence_refs` |

`C_conditional` can be present while `unconditional_point` is null. Unknown
questions retain bounds and weights. `missing_weight_by_question` copies the
weight of each missing required question; it is a coverage diagnostic, not a
penalty multiplied into the score. Diagnostics do not silently alter Eq. 10.

## Each function populates the named cells, in this order of dependency

| Proposed function (all UNIMPLEMENTED) | Exact selected input | Exact populated output | Calculation/extraction boundary |
|---|---|---|---|
| `read_account_and_comparison` | Supplied material boundaries, emerging account/alternative definitions, selected assay Methods and specified question weights | Account, Question, ConditionComparison, Dependence | Interpret actual subject/intended difference with source anchors; weights are declared proposal inputs, not read as paper facts |
| `read_chemical_amounts` | Exact source table/passage or dataset rows naming numerator, denominator and experimental unit | ScalarInput or SummaryInput, CalibrationInput, native Quantity fields | Parse actual numbers/units; distinguish supplied, consumed and net quantities |
| `read_isotope_amounts` | Selected window definition, experiment-paired baseline/labeled data or exact figure/table cells; precursor areas | IsotopeInput native arrays, p_supplied, missing p_pool where appropriate | Deterministic array extraction/integration if defined; plot values keep explicit extraction bounds; no invented raw replicates |
| `read_measurement_controls` | Matching blank/recovery/mixture measurements and response-versus-condition calibrations | CorrectionInput and condition beta terms | Populate measured controls and their domains; do not grade prose into a nuisance value |
| `calibrate_quantity` | CalibrationInput | measurement.q_read | Eq. 1; refuse only the undefined numerical conversion, preserving raw input |
| `apply_measurement_model` | q_read and CorrectionInput for each numerator, denominator or isotope bin | CorrectionOutput, MeasurementOutput | Eqs. 2–3; all components corrected before ratios/normalization; valid partial outputs remain |
| `predict_chemical_quantity` | PredictionInput, measured parameter fields and MeasurementOutput baseline/window | PredictionOutput | Eq. 3 stoichiometry or Eq. 4 convolution; model/scientific choice already explicit |
| `summarize_constraint_errors` | MeasurementOutput/valid SummaryInput, PredictionOutput, experiment/dependence identities | ConstraintOutput | Eqs. 5–6 and defined interval rules; one experiment vector remains one unit |
| `read_pathway_constraints` | Actual resource/uptake/flux/capacity tables, conditions and candidate network definition | BudgetInput | Preserve measured/assumed bounds and units; a partner hit is an identity, never capacity |
| `calculate_pathway_budget` | BudgetInput or actual NativeModelResult with same objective | BudgetOutput | Eqs. 7–8; optimal/infeasible/unbounded/missing statuses kept distinct |
| `read_reaction_terms` | Explicit reaction, identified formulas/charges/compartments and half-reactions | Species, BalanceInput | Extract the account; no insertion of an unidentified sink to force balance |
| `calculate_conservation` | BalanceInput | BalanceOutput | Eq. 9 after cancellation; open half-reaction cannot fill complete-net D |
| `compile_a110_sheet` | Fixed Account/Question weights, ConstraintOutput, BudgetOutput, BalanceOutput, dependency map | CompilationOutput | Eq. 10 and retained unknown bounds; does not implement global W05 credit or continuation |

## Filled population crosswalk for the new examples

| Sheet output | Synthetic scalar example 3 | Synthetic full isotope example 4 |
|---|---|---|
| `correction.b_comp` | Product: 1 µmol per preparation; consumption: 0 | 0 per bin, stipulated |
| `measurement.numerator_corrected` / labeled arrays | [7,9] µmol | [[12,31,36,18,3,0],[8,34,39,17,2,0]] pmol/mg |
| `measurement.denominator_corrected` / totals | [10,10] µmol consumed CH2O | [100,100] pmol/mg total selected labeled bins |
| `measurement.y` | [.7,.9] | Six-bin vectors obtained by dividing those rows by 100 |
| `constraint.e_claim` | .05 | .0009 |
| `constraint.e_alternative_by_ref` | Half: .10; zero: .65 | m0: .6784; m2: .0484; m4: .0324625 |
| `constraint.s_question` | 1/3 | 2525/2669 |
| `budget.z`, `f`, `s_supply` | 6 µmol CO2; 3/5; 1/5 | 2 µmol product; 2/3; 1/3 |
| `balance.D` | 0 on explicitly defined oxidation reaction | 0 on explicitly synthetic closed acceptor account |
| `compilation.weights` | [1/2,1/2] | [1/2,1/2] |
| `compilation.C_conditional` | 4/15 | 5122/8007 |
| Empirical status | Every datum synthetic; no biological CI | Every datum synthetic; no measured UbiUV sink/pool inferred |

For published NfnAB, the reader would populate approximate amounts and supplied
denominators while leaving recovery/consumption variance fields missing, with
conditional C=14399/14645 and unconditional bounds [−1,1]. For published UbiUV,
it would populate p_supplied and the limited plotted amounts as such; full B/L
arrays, p_pool and complete-net D remain missing. Neither source has its gaps
filled by the synthetic input records above.

No model prompt is defined or modified here. These field/type/function
declarations satisfy the targeted-reader design question for the numerical
sheet; they do not establish reader implementation or full W04/W05 delivery.

### Additive validation clarification from final review

For the specific Eq. 4 convolution, `selected_window_indices` must be contiguous
0,...,J and every intervening baseline coordinate must be available or explicitly
missing. All B/L amounts are nonnegative on the physical model domain and their
normalization totals positive. Preserve an out-of-domain corrected value as a
partial processing result, never a clamped zero. Add `invalid_model_domain` to
the allowed `Quantity.missing_reason` values for a conversion that lacks an
admissible domain; an applicable bounded censoring model can still yield valid
partial numerical ranges. Signed scalar changes have no nonnegativity rule.
