# A105 summary precision: frozen interface proposal248

PLAN ONLY, awaiting root interface review. No production or test file is created.
The full immutable supplied literature goal remains active, A105 first, exactly
ten axes A101–A108,A110,A111. This is a precision section of ONE logical A105
sheet. It is neither a new assay family nor a reliability/validity/relevance
module independent of that sheet. No A106, target transfer, W05, episode, loop,
controller or runtime changes are owned here.

## Proposed public interfaces and ownership

Only after release, create these NEW files:

* `gene_annotation_episode/literature_kinetic_summary_precision_inputs.py`
* `gene_annotation_episode/literature_kinetic_summary_precision_calculations.py`
* `gene_annotation_episode/literature_kinetic_summary_precision_prompt.py`
* `tests/test_literature_kinetic_summary_precision_components_248.py`

No existing production/test/authority file is changed. Agent244 owns separate
selected integration; this proposal supplies pure interfaces for a later binding.

Inputs module public functions:

```python
summary_precision_arguments_schema() -> dict
summary_precision_extraction_schema() -> dict
read_kinetic_summary_precision_inputs(selection: dict, *, read_source: Callable) -> dict
validate_kinetic_summary_precision_extraction(extraction: dict, *, read_source: Callable) -> dict
```

`read_source(source_ref, representation)` retains the existing exact result
`{artifact_ref: str, content: bytes}`; representation is original or text.
Reader calls existing `read_kinetic_inputs(selection['kinetic_selection'],
read_source=...)`, then authenticates supplemental witnesses with existing
`_Sources.witness`, count selections with existing `_count_reading`, and meanings
with existing `_interpret`. No source fetch, model call or Store access occurs.
Extraction validation rebuilds from saved selection and authorized original
bytes, compares exact canonical JSON, and returns a detached copy. The calculator
does not reacquire bytes. An installed integrator must authenticate source
access, dependencies and saved records; a caller-supplied dict alone does not do
that. Hashes/IDs stay outside scientific TASK and STEERING.

Calculator module public functions:

```python
summary_precision_inputs_schema() -> dict
summary_precision_sheet_schema() -> dict
validate_kinetic_summary_precision_inputs(inputs: dict) -> dict
populate_kinetic_summary_precision(inputs: dict) -> dict
```

Prompt module exports `KINETIC_SUMMARY_PRECISION_TASK` exactly equal to the
retained five-paragraph UTF8 proposal, and `SUMMARY_PRECISION_OPERATION_DESCRIPTION`
(one finite operation description, no complete sheet). No new model composer,
renderer, selected operation, repository or episode is included in these files.

All APIs raise existing `ExperimentalContractError(code, field, detail=...)` for
invalid closed structure or impossible field relationships. Scientific missing
conditions return cells with null and precise reasons, preserving valid source
cells. Copy inputs; no mutable aliases escape.

## Exact closed selection structure

All objects below require every listed key and have `additionalProperties:false`.
Null is allowed only where explicitly named. Lists are ordered, except lists
marked unique. Numbers are finite int/float, never booleans. Offset arithmetic
uses original UTF8 bytes outside a quote and Unicode character positions inside
the exact quote, following the existing reader.

```
Selection = {
 version: 'a105_kinetic_summary_precision_selection_v1',
 kinetic_selection: KineticSelection,
 interpretation: {
   row_footnote_applicability: Assessment,
   source_count_meaning: CountMeaning,
   statistical_count: NumberSelector|null,
   statistical_count_matches_sd: Assessment,
   one_estimate_per_preparation: Assessment,
   equal_weight_arithmetic_mean: Assessment,
   sample_sd_n_minus_one: Assessment,
   iid_common_mean_finite_variance: Assessment,
   normal_sampling_units: Assessment
 },
 scenario: Scenario|null,
 interval_request: 'none'|'student_t_95'
}

Assessment = {
 state: 'source_supported'|'source_contradicted'|'unknown'|'conflicting',
 witnesses: [Witness, ...]
}
CountMeaning = {
 value: 'physical_preparation_count'|'statistical_estimator_count'|
        'both_same_count'|'technical_measurement_count'|'unknown'|'conflicting',
 witnesses: [Witness, ...]
}
Scenario = {
 version: 'a105_summary_precision_scenario_v1',
 count_rule: 'source_statistical_count'|'one_per_physical_preparation',
 stipulated_assumptions: unique[AssumptionCode,...]
}
AssumptionCode =
 'one_estimate_per_preparation'|'equal_weight_arithmetic_mean'|
 'sample_sd_n_minus_one'|'iid_common_mean_finite_variance'|'normal_sampling_units'
```

`Witness`, `NumberSelector`, and `KineticSelection` are the exact closed schemas
returned by existing `_witness_schema`, `number_selector_schema`, and
`kinetic_arguments_schema`, respectively. They are embedded by deepcopy, not
reimplemented. A supplemental authenticated witness gains artifact_ref in
extraction and loses none of its original fields. No unrestricted findings,
interpretation notes, model-provided numerical outputs, or report prose exist.

This operation permits exactly one kinetic summary: numerator selected,
denominator null, and every comparison meaning unknown with no witnesses. It
does not ask the contrast calculator to assert identical distinct constructs.
The reusable reader still handles parameter kinds Km/kcat/catalytic_efficiency
and their declared units. Parameter/SD/count reading is not rebuilt.

Assessment semantics are fixed per named field. For example,
`sample_sd_n_minus_one` means the selected spread is the sample SD of the
selected estimator units with denominator n−1, not SD of pooled technical
readings. `iid_common_mean_finite_variance` concerns those same units.
`statistical_count_matches_sd` means the separately selected statistical count
enumerates exactly the estimates summarized by this SD. `row_footnote_applicability`
means the uncertainty/count footnote and Methods information used actually
apply to the selected construct/row; it does not endorse unrelated footnotes.

Every supported or contradicted Assessment needs >=1 distinct authenticated
witness; conflicting needs >=2 distinct witnesses; unknown needs no witnesses
but retains any selected ones. CountMeaning requires >=1 witness for a concrete
meaning and >=2 for conflicting. Exact quote validation is custody, not proof
of scientific interpretation. Model interpretation remains constrained and
explicit. The source reader must not infer # meaning generically across papers.

Physical count is drawn from the existing exact source count only when the
source_count_meaning is physical_preparation_count or both_same_count, repetition
basis is biological_preparations, and row applicability is source_supported.
The native numeral and reason survive when those conditions do not hold.

Statistical count is drawn from a separately authenticated exact count when
statistical_count_matches_sd is source_supported, or from the original count
when its meaning is statistical_estimator_count, technical_measurement_count or
both_same_count. Multiple supplied statistical-count descriptions must agree;
disagreement returns `statistical_count_conflicting`, never a chosen favorable n.
An exact physical count is NEVER copied into an ordinary statistical count
without a source-supported one_estimate_per_preparation relationship.

The scenario one_per_physical_preparation rule uses source physical n only when
one_estimate_per_preparation is source_supported or explicitly stipulated and
is not contradicted/conflicting. No direct model numeric n is accepted. Thus
physical n remains source-established while scenario statistical n is a
conditional mapping. A separately stipulated n when source n is unknown is
outside this finite interface; no generic synthetic n fallback is installed.

Stipulated codes must be known unique codes. They may fill unknown assumptions
only. A source-constrained false/conflicting assumption cannot be silently
overridden: affected scenario cells are unavailable with
`scenario_assumption_conflicts_with_source`. Redundant stipulation of an already
source-supported assumption is rejected as `redundant_stipulated_assumption`.
No scenario is selected merely because it would populate more cells.

## Exact extraction and calculator input

The retained reader output is:

```
Extraction = {
 version: 'a105_kinetic_summary_precision_extraction_v1',
 selection: Selection,
 kinetic_extraction: ExistingKineticExtractionV3,
 interpretation: AuthenticatedInterpretation,
 source_refs: unique[Reference,...],
 calculation_inputs: CalculationInputs
}
```

ExistingKineticExtractionV3 is the existing complete reader result with exact
fields `version,source_ref,source_kind,operands,comparison,calculation_inputs,
input_unavailable_reasons,source_refs,implementation_dependencies`. The NEW
extraction schema embeds a closed schema of that existing result: its operands
are the existing retained shape, including `parameter_kind,subject,context,
measurement_identity,number,unit,qualification,approximate,source_origin,
canonical_value,uncertainty,calculation_operand,unavailable_reasons`; uncertainty
contains the existing `meanings,magnitude,interval,unit,effective_unit,
confidence_level,count,canonical,unavailable_reason`. No extension of that
existing shape or claim of new source data is permitted. Rebuild equality is
the authoritative validation of values in this embedded existing result.
AuthenticatedInterpretation has exactly the nine interpretation keys above;
its count becomes existing count-reading output or null, its meanings retain
their declared state/value plus authenticated witnesses. Full nested reused
shapes will be embedded mechanically and checked against the existing reader
output; this is schema reuse, not a new numerical parsing route.

The narrow exact calculator input is independently closed:

```
CalculationInputs = {
 version: 'a105_kinetic_summary_precision_inputs_v1',
 source_kind: 'primary_source'|'synthetic_fixture',
 parameter_kind: 'Km'|'kcat'|'catalytic_efficiency'|'unknown'|'conflicting',
 source_origin: 'reported'|'synthetic',
 source_parameter_status: 'point'|'censored'|'missing'|'conflicting',
 source_parameter_reason: ExistingKineticInputReason|null,
 parameter_approximate: bool,
 parameter_native_exact: Rational|null,
 sd_native_exact: Rational|null,
 canonical_scale_exact: Rational|null,
 canonical_unit: 'uM'|'per_min'|'uM^-1min^-1'|null,
 uncertainty_statistic: 'sd'|'sem'|'ci'|'unspecified'|'unreported',
 uncertainty_reason: 'source_uncertainty_unit_unavailable'|'source_numeric_range'|null,
 source_count: CountReading|null,
 source_statistical_count: CountReading|null,
 source_count_meaning: CountMeaningValue,
 repetition_basis: 'biological_preparations'|'technical_measurements'|'unspecified',
 estimate_basis: 'fit_to_averaged_curve'|'between_fitted_parameters'|'unknown',
 assessments: {each of the seven Assessment field names: AssessmentState},
 scenario: Scenario|null,
 interval_request: 'none'|'student_t_95',
 dependencies: {
   parameter_source: Locator|null,
   spread_source: Locator|null,
   count_source: Locator|null,
   statistical_count_source: Locator|null,
   physical_measurement_id: str|null
 }
}
Rational = {numerator: canonical decimal integer string,
            denominator: canonical positive decimal integer string}
Locator = {source_ref:Reference, artifact_ref:str,
 representation:'original'|'text', start:nonnegative int,end:positive int}
```

Here the seven Assessment fields are row_footnote_applicability,
statistical_count_matches_sd, one_estimate_per_preparation,
equal_weight_arithmetic_mean, sample_sd_n_minus_one,
iid_common_mean_finite_variance, normal_sampling_units. CountReading is exactly
existing `_count_reading` output: selector,raw_number,value,notation,relation,
approximate,status,unavailable_reason; its selector's witness is authenticated.

Source native exact rational comes from existing number.raw_number and existing
`_literal_fraction`. Exact scale comes from existing `_UNIT_TABLES` using the
authenticated raw_unit and `_normalize`; never reverse canonical floats.
SD with a different explicit but compatible native unit is converted exactly
onto the parameter-native scale before storing sd_native_exact. Unsupported
units preserve reader reasons. An existing canonical finite number mismatch
with the exact conversion is rejected. Source count is exact only when the
existing reader labels it exact; qualified/range/unsupported counts remain
records with no estimator n.

Rationals must be reduced with positive denominator; numerator sign canonical,
no -0 or leading zeros. Zero SD is allowed; negative SD is invalid. Booleans,
nonfinite or underflowing conversions, arbitrary string fractions, mismatched
parameter units, reversed spans and wrong closed fields fail specifically.
Source parameter missingness remains separate from SD/count availability.

## Exact sheet and cells

```
Sheet = {
 version:'a105_kinetic_summary_precision_sheet_v1',axis:'A105',
 evaluation_scope:'source_kinetic_summary_precision',
 inputs:CalculationInputs,
 source_cells:{each Component:Cell},
 scenario_cells:{each Component:Cell}|null,
 contribution:{
   kind:'one_summary_precision_contribution',
   dependency_sources:unique[Locator,...],
   physical_measurement_id:str|null,
   independence_inferred:false
 },
 limits:unique[LimitCode,...],
 total_uncertainty:null,assay_error_probability:null,annotation_credit:null
}
Cell = {
 value:finite number|null,unit:Unit|null,
 status:'populated'|'unavailable',
 qualification:'source_reported'|'derived_source_supported_conditions'|
               'conditional_on_stipulated_assumptions'|'unavailable',
 formula_code:FormulaCode,
 origin:'reported'|'derived'|'proposed'|'synthetic',
 approximate:bool,
 source_exact_value:Rational|null,
 conditional_on:unique[AssumptionCode,...],
 stipulated_assumptions:unique[AssumptionCode,...],
 unavailable_reason:ReasonCode|null
}
```

Unit values are canonical parameter unit, its explicit squared form
`uM_squared`, `per_min_squared`, `uM_inverse_squared_min_inverse_squared`,
`dimensionless`, or `count`. No standalone native display unit is guessed;
native ratios/operands and exact scale remain in inputs and examples.

Every fixed Component and FormulaCode (one code per row):

| Component | Formula | Meaning / prerequisites |
|---|---|---|
| reported_parameter | x × scale | Reported magnitude of this kinetic parameter, point required |
| reported_sd | s × scale | Reported SD, statistic must be SD; does not assert sample denominator |
| source_summary_count | selected exact count | Source's count with separately retained meaning |
| independent_preparation_count | source physical count | Extent of physical preparation replication, never extra quality weight |
| statistical_estimator_count | explicit matching n, or justified mapping | Estimator denominator, distinct from physical count |
| relative_reported_sd | s / abs(x) | Relative reported dispersion, x≠0; no mean identity or normality needed; no CV label |
| mean_variance | s² / n × scale² | Estimated random variance of equal-weight estimator mean; n≥2, sample-SD convention, IID finite variance, SD ownership/count mapping |
| mean_standard_error | sqrt(s²/n) × scale | Estimated random mean precision, same conditions; no normality |
| relative_mean_standard_error | sqrt(s²/n)/abs(x) | Also requires central estimate equal-weight mean and x≠0 |
| mean_interval_df | n−1 | Only for explicitly requested normal-mean t interval |
| mean_interval_confidence_level | 0.95 | Proposed two-sided confidence level, never reported by this source |
| mean_interval_t_multiplier | t.ppf(0.975,n−1) | Student-t quantile under normal IID units |
| mean_interval_halfwidth | t × sqrt(s²/n) × scale | Optional uncertainty halfwidth |
| mean_interval_lower | (x−t × sqrt(s²/n)) × scale | Optional precision-qualified lower mean endpoint |
| mean_interval_upper | (x+t × sqrt(s²/n)) × scale | Optional upper mean endpoint |

Source_cells never borrow scenario assumptions. Scenario_cells exist only when
explicit Scenario is supplied; valid source/descriptive cells remain copied
with source qualifications, while affected model cells carry the exact
stipulated list and conditional qualification. Mean variance/SE may be useful
without the central reported parameter being known as the mean. The selected
source must still establish that SD/count belong to the same estimator units.

Optional interval scope: ONLY a proposed two-sided 95% Student-t interval for an
equal-weight mean of normal IID sampling-unit estimates, with n integer≥2,
strictly positive sample SD, matched estimator count/SD, and central mean
identity. Existing SciPy1.18.1 `scipy.stats.t.ppf` is available, no install.
SE supports s=0 as an estimate; interval with s=0 remains unavailable
`positive_sd_required_for_student_t` (no repaired/infinite evidence). Other
confidence levels, reported SEM-to-SD inversion, CI-to-SE inversion, unequal
weights, fitted-curve covariance, hierarchical pooling and raw rows are outside
this route. Reported SEM/CI remain in retained existing extraction, while new
SD-derived components return `reported_statistic_not_sd`. No quota of new
routes is invented.

ReasonCode closed set proposal (plus existing input/count reasons):
`source_measurement_unreported`, `source_kinetic_unit_unreported`,
`unsupported_source_kinetic_unit`, `source_operand_qualification_unknown`,
`source_operand_qualification_conflicting`, `source_numeric_range`,
`source_uncertainty_unit_unavailable`, `censored_parameter`,
`conflicting_parameter`, `reported_sd_unreported`, `reported_statistic_not_sd`,
`source_summary_count_unreported`, `source_count_not_exact`,
`row_footnote_applicability_unknown`, `row_footnote_applicability_conflicting`,
`row_footnote_applicability_contradicted`, `physical_preparation_count_unknown`,
`statistical_estimator_count_unknown`, `statistical_count_conflicting`,
`statistical_count_sd_relationship_unknown`, `insufficient_estimator_count`,
`sample_sd_convention_unknown`, `iid_model_unknown`, `mean_identity_unknown`,
`normality_unknown`, `source_condition_contradicted`,
`source_condition_conflicting`, `zero_parameter_for_relative_precision`,
`interval_not_requested`, `positive_sd_required_for_student_t`,
`scenario_assumption_conflicts_with_source`, `numerical_model_range`.

FormulaCode is exactly `summary_precision_` plus its Component name. First
missing condition follows the table's prerequisite order; all supplied facts
remain in inputs, allowing repair. Unavailable cells have value/exact null,
status unavailable, qualification unavailable and a nonnull closed reason.
Populated cells have no unavailable reason; no numeric-only metadata scores.
All outputs including t quantiles/endpoint subtraction are checked for finite
range and underflow. Interval endpoints are ordered; no truncation at zero.

LimitCode closed set:
`source_summaries_do_not_reconstruct_raw_measurements`,
`physical_count_does_not_define_statistical_count`,
`source_conditions_and_stipulations_distinct`,
`random_precision_does_not_include_unknown_systematics`,
`shared_calibration_does_not_shrink_with_preparation_count`,
`dependent_precision_representations_not_independent_assays`,
`pNPP_repeatability_not_physiological_specificity`,
`no_cross_construct_contrast`, `no_assay_error_probability`,
`no_target_transfer_or_annotation_credit`.

## Numerical examples and contrasting cases

Actual source: Sunden2015 Table1 D101A/E322Y#; parameter 31/10, SD1/10
M^-1 s^-1, source physical preparation n2. Methods omit Mg for both selected
E322Y variants. Complete estimator hierarchy, n−1 SD convention, explicit
equal-weight mean and normality remain unknown. Independently expressed
preparations are source-established; full IID common-distribution model is not.

Ordinary source_cells: parameter0.000186, SD0.000006 uM^-1min^-1;
source summary count2 and physical count2; statistical estimator count null
`statistical_estimator_count_unknown`; relative SD1/31=0.03225806451612903.
Mean variance/SE and interval stay unavailable under their prerequisite reasons.

Explicit illustrative scenario count_rule=one_per_physical_preparation,
stipulated assumptions all five codes: n2 is scenario statistical count;
mean variance native1/200=.005, SE0.07071067811865475; canonical variance
9/500000000000=1.8e-11 and SE0.000004242640687119285; relative SE
0.022809896167307983. Optional proposed interval df1, confidence.95,
t12.706204736174707; native halfwidth.8984643532093762; native endpoints
[2.201535646790624,3.998464353209376]. Canonical endpoints are these values
times60/1000000, not new observations. No ordinary source value is replaced.

Required meaningful contrasting fixtures after release:

1. Actual K328A comparison row1.1(SD.1), no#: physical count unknown, no
   scenario mapping; descriptive parameter/SD/relative SD survive. Do not
   assign count2 from generic duplicate kinetic measurements.
2. SYNTHETIC explicitly supported summary one estimate/preparation, matching
   count4, equal-weight mean10, sample SD2, IID finite-variance support, no
   normality: Vmean1, SE1; relative SE.1; t interval unavailable normality.
3. Same synthetic case normality source-supported and interval requested:
   df3, t3.182446305284263; mean interval[6.817553694715737,13.182446305284263].
4. SYNTHETIC technical observations count4, mean10, SD2 with supported sample
   SD/IID/mean meanings: statistical n4 and technical-mean SE1, physical
   preparation count unknown. Same arithmetic does not invent biological n.
5. Fit-to-averaged-curve SD or uncertain hierarchy, no supported count mapping:
   retain reported SD and physical n; mean precision unavailable unless an
   explicitly compatible conditional scenario fills only unknown assumptions.
6. Source SEM or CI and n known: retain original statistic/extraction; no SD
   reinterpretation or inversion; new SD arithmetic unavailable.
7. n1, qualified n, range n, absent n, conflicting counts, mismatched footnote:
   retain source readings and partials; never manufacture estimator denominator.
8. SD0: reported SD and conditional mean variance/SE0; relative SD0 if x≠0;
   t interval unavailable positive-SD prerequisite. x0: SD and mean SE survive,
   relative cells unavailable. Negative SD/booleans/nonfinite fail validation.
9. Exact unit conversion and extreme finite values: exact3.1/.1, scale60/1e6,
   squares use scale²; no reversed-float3.0999999999999996. Overflow/underflow
   fail locally rather than return inf or false zero.
10. Repeated selection of same source estimate preserves its dependency source
    locator and does not enlarge n. Different representations with unknown
    physical identity are not declared independent. No pooling API is offered.
11. Tampered supplemental witness bytes/offsets/source_ref and detached input
    modifications fail revalidation. Authenticated source support vs explicit
    stipulation remains visible. A contradicted SD convention cannot be changed
    by a scenario. No extra model numerical output is accepted.

All scenario mathematics is one contribution. In a later supported within-assay
equation a=f(theta), this estimator variance can occupy the matching entry in
Sigma and enter Var(a)=J Sigma J^T plus genuinely distinct residual terms.
If a=theta+c with Jtheta=1, its random contribution is exactly s²/n, added once
with covariance terms when known. It must replace an already represented copy
of the same preparation variation. No multiplying activity by a count grade,
no adding SD+SE+CI as separate evidence, no assumed zero systematics.

## Scientific limits retained

The two AP variants are distinct separately assayed constructs. Difference2.0
and ratio11/31 are descriptive research results, outside this single-summary
calculator. The difference SE/covariance is unknown. Do not mislabel them same
molecule/construct to use the existing preference route.

Purification MBP–AP–strepII construct and named SM547(DE3) host are supported;
actual assay tag cleavage, full host genotype, active fraction and quantitative
calibration are not. >95% purity is not attribution. The six-mutation S102G
control is a different construct, not a matched numeric blank or exact zero.
Methods enzyme dependence and fits concern validity; pNPP repeatability alone
does not establish physiological substrate specificity. Such weaknesses need
the corresponding matched blank, calibration, active-fraction or alternative
substrate measurements; this component does not supply them.

## TASK/STEERING decision and information trace

TASK copied byte-for-byte in TASK_PROPOSAL_001.txt; no gap found requiring a
change. It is repeated in full on each relevant iteration after root accepts
the interface. Source reading/interpretation is chosen within the existing
LiteratureEpisode. The pure operation consumes selected source operands and
declared interpretations; the source reader authenticates numbers and witnesses;
the calculator deterministically populates cells. No autonomous action follows
from count, significance, interval or null values.

STEERING from actual requested component returns should be concise tables:
parameter/SD/unit; physical count versus statistical count; relative dispersion;
available SE/interval with source-supported or stipulated conditions; precise
unavailable reasons; own action category and actual yield/expectation when
provided by the existing runtime. No host IDs, hashes, raw JSON, whole sheet,
invented controller estimates, narrative recap or second model composer.

Selected persistence/delivery, permitted return subset/schema, operation key
replay, child source access and reconstruction are NOT implemented or verified
by these pure modules; a later integration workload must trace them in existing
LiteratureEpisodes. Existing numerator_parameter return already carries SD/count;
the gap is additional summary-precision cells and conditions, not absent count
delivery. No tests or model/provider calls have run at this plan stage.
