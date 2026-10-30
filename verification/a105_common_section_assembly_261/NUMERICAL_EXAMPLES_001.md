# Proposed numerical worksheet examples and their dependencies

The worksheet organization/link template below is a PROPOSAL. Arithmetic is
copied from root's already-converted scientific meanings, not new paper
interpretation. Actual controlled use of the existing AP native/summary path
is separately retained in ADMITTED_JOINT_FORM_001.json and
JOINT_BOUNDARY_RESULT_003.json. That actual form has the two original numerical
fields and a restricted systematics qualification; it does not claim execution
of the proposed new assessment_context link validator.

## One AP source assessment: magnitude and random precision

Actual assayed reference: E.coli AP D101A/E322Y, with separately assayed
constructs not coexisting. The selected endpoint is pNPP cleavage measured as
p-nitrophenolate at400nm; parameter kcat/KM, not a per-molecule turnover rate.
Root246's converted conditions include25C, pH8 MOPS,0.5M NaCl,100uM Zn and the
E322Y Mg-omission exception. MBP–AP–strepII purification constructs are reported;
assayed tag state and exact preparation identities remain unknown. Physiological
substrate preference, molecular contamination correction, active fraction and
total systematic uncertainty are not established by these source summaries.

There is one ordinary worksheet with `native_parameter` and `precision` fields.
The native operation selects the summary selection's original kinetic_selection
with denominator null. Its valid numerator result does not require inventing a
second estimate. Its delivered denominator metadata is unresolved/null, and
pairwise contrast values are not selected.

| Selected numerical cell | Value | Explicit input/calculation | Meaning and dependency |
|---|---|---|---|
| native_parameter.numerator_parameter | 0.000186 uM^-1 min^-1 | 3.1 * (60/10^6) = 93/500000 | Source efficiency magnitude for this construct/endpoint. Existing native wire unit code is uM_inverse_min_inverse. |
| precision.source_reported_parameter | 0.000186 uM^-1 min^-1 | Same exact printed3.1 and canonical conversion | Same source report, not a second assay; exact parameter token/anchor and original kinetic_selection match. |
| precision.source_reported_sd | 0.000006 uM^-1 min^-1 | 0.1 * (60/10^6) = 3/500000 | Source SD, also delivered by native numerator's uncertainty_values; one spread report. |
| precision.source_independent_preparation_count | 2 | Source row-footnote count with its preparation meaning | Physical repetition; not statistical n by default. Same count also accompanies native numerator. |
| precision.source_statistical_estimator_count | unavailable | Source preparation count does not establish SD/estimator hierarchy | Exact reason statistical_estimator_count_unknown. |
| precision.source_mean_standard_error | unavailable | Requires supported statistical n plus SD convention/IID premises | Same reason; valid SD and physical n2 survive. |
| precision.scenario_mean_variance | 1.8e-11 (uM^-1 min^-1)^2 | (3/500000)^2 / 2 = 9/500000000000 | Estimated random mean variance under four explicit stipulations below. |
| precision.scenario_mean_standard_error | 4.242640687119285e-6 uM^-1 min^-1 | sqrt(9/500000000000) | Same conditional variance contribution, not a new observation or total accuracy. |

This is the COMPLETE requested numerical section roster in the concrete
two-family proposal: one native cell and seven summary cells. The full original
row contracts carry origin/qualification/status, source_context, unit, statistical
conditions and dependency meanings. They are not flattened to the table above.

The source p and SD are printed nominal decimals. Exact rational arithmetic
describes those operands; it does not invent experimental significant digits.
The summary source p/SD cells are `qualification=source_reported` with
`origin=derived` for deterministic unit conversion. Preparation count has
reported origin. The source unknown cells retain null values and their exact
unavailable reason.

For the scenario only, stipulate:

1. one_estimate_per_preparation;
2. reported_sd_summarizes_counted_preparation_estimates;
3. sample_sd_n_minus_one;
4. iid_common_mean_finite_variance.

These four conditions are carried on both scenario rows with
`qualification=conditional_on_stipulated_assumptions`, not changed in source
assessments. Normality is not needed for this estimated SE. Interpreting the
central parameter as an equal-weight arithmetic mean is a further premise for
relative mean SE or a centered mean interval; neither is requested here.

The AP numerical combination is the actual s^2 * (1/n) followed by sqrt; no
generic reliability multiplier is needed. If a future physical activity
calculation uses a truly matching estimated mean, the matching variance could
contribute within its actual J Sigma J^T. That requires a new explicit bridge
and supported covariance/estimator meanings, and must replace any already
included variability. It cannot turn this scenario into source-supported total
uncertainty.

Proposed dependency links (not yet executed):

| Left allowed quantity | Right allowed quantity | Relationship |
|---|---|---|
| native numerator cell_value | summary source_reported_parameter.cell_value | same_reported_parameter |
| native numerator reported_spread | summary source_reported_sd.cell_value | same_reported_spread |
| native numerator reported_count | summary source_independent_preparation_count.cell_value | same_count_report, preserving biological-preparation meaning |
| summary source_reported_sd.cell_value | summary scenario_mean_variance.cell_value | conditional_precision_of_report, preserving the four stipulations |

Only the first link is positively checked by the bounded261 script through
the exact shared parameter source/artifact/span and original selection. The
script retains the complete other original data for review but does not claim
the proposed general link validator has been implemented. Distinct receipt
identities do not create distinct physical estimates or preparation IDs.

## Separate MvhADG/HdrABC endpoint worksheet

This is a different molecule/experiment and therefore a SEPARATE assessment,
not additional AP support. Root240 converted the coexisting native six-subunit
M.marburgensis complex's finite320nm MTZ reporter trace. Its stated Fig4A
conditions include60C, H2,1.6M phosphate pH7 and0.75mL; missing trace path length
and molecular activity attribution stay unknown. An artificial reporter
endpoint is not identified product formation by a single isolated subunit.

| Numerical cell | Explicit arithmetic/result | Evaluation |
|---|---|---|
| total amplitude D | 181-39 =142 direction-oriented pixels | Finite total reporter amplitude. |
| corrected amplitude C | 170-39 =131 pixels | Retained component under the selected baseline model. |
| additional amplitude G | 181-170 =11 pixels | Additional reporter contribution under that model. |
| retained fraction F | 131/142 =0.9225352112676056 | Retained reporter fraction, conditional in the actual244 selected example. |
| additional fraction H | 11/142 =0.07746478873239436 | H=1-F, dependent view of the same trace. |
| retained-fraction reading enclosure | [128/143,67/71] approximately[0.8951048951,0.9436619718] | Joint corner calculation with one shared initial ordinate, not experimental CI. |
| physical retained-fraction variance | unavailable | Original source physical covariance not supplied; manual enclosures cannot substitute. |

The explicit combinations are D=C+G and C=F*D. All five quantities depend on
the same selected three-ordinate trace. In the actual retained-source selected
example ordinary corrected values remain null where correction applicability
is stipulated; the conditional values carry the result. No dimensionless F is
multiplied into AP efficiency, an initial rate, independent preparation count,
or an overall quality score. Source's already-corrected later ratio does not
receive the correction again. Useful readout-validity information survives
unknown molecular effect isolation.

## Existing physical corrected-activity section stays available

When actually selected source quantities establish their roles, reuse the
already implemented within-assay equation a=(q-g)v/(k E u). Here q is the
background-corrected endpoint rate, g an additional applicable contributor,
k reporter-standard recovery, E the applicable molecular amount and u/v a
nuisance response excluding the intended change. Its source scope must be
established before use. The implementation already distinguishes q/E and
q/(kE) partials from full isolation/correction and propagates matching joint
operand uncertainty. This plan invents no AP or endpoint values for these
missing operands, and no numerical example that forces distinct scientific
quantities into them.
