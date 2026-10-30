# Additive clarification002 — still PLAN ONLY

This corrects three specific parts of frozen PLAN001. All001 artifacts remain
unchanged. The proposed production ownership and public function signatures
remain the same. No TASK change, production/test edit, runtime binding or claim
of completed A105 work follows. Machine-readable002 schemas and the JSON Patch
delta identify the exact changes before release.

## 1. General precision limit

Replace the unconditional LimitCode
`pNPP_repeatability_not_physiological_specificity` with
`measurement_repeatability_does_not_establish_physiological_specificity`.
Its meaning is that repeatability of the measured endpoint does not by itself
establish physiological substrate specificity. The generic route does not name
pNPP. Actual242 context still supports the specific pNPP interpretation in its
worked example and unchanged TASK; unrelated kinetic summaries do not inherit it.

## 2. Exact physical-to-statistical count mapping

PLAN001 left one relationship insufficiently explicit. One estimate per
preparation does not alone establish that the *selected SD* summarizes exactly
that roster of estimates. Add one Assessment and one permissible stipulation:

`reported_sd_summarizes_counted_preparation_estimates` means that the selected
SD summarizes **exactly the one estimator value per each of the source-counted
preparations**. It excludes an SD of pooled technical readings, an averaged
curve's fit uncertainty, a subset of preparations or an additional uncounted
set. This is an estimator-ownership statement, not a new preparation or assay.
It requires its own authenticated supporting witness when source_supported;
unknown/conflicting/contradicted meanings follow the existing Assessment rules.

The eight Assessment fields are now row_footnote_applicability,
statistical_count_matches_sd, one_estimate_per_preparation,
reported_sd_summarizes_counted_preparation_estimates,
equal_weight_arithmetic_mean, sample_sd_n_minus_one,
iid_common_mean_finite_variance and normal_sampling_units.

The six AssumptionCodes are the last six fields after
statistical_count_matches_sd, beginning with one_estimate_per_preparation.
Only these six can be stipulated. Neither row/footnote applicability nor the
separately selected statistical count's applicability can be stipulated.

Exact count routes:

* A separately selected statistical_count requires an exact positive numeral,
  source-supported row applicability and source-supported
  statistical_count_matches_sd. The latter applies only to that separately
  selected count, as already specified in001. Unknown/conflicting/contradicted
  applicability cannot be repaired by stipulation.
* An original nested uncertainty.count interpreted as
  statistical_estimator_count, technical_measurement_count or both_same_count
  means **the count of estimator units summarized by the selected SD**. That
  source CountMeaning requires authenticated witnesses and source-supported
  row applicability. It does not turn a technical count into biological n.
* For an original count established only as physical_preparation_count,
  mapping to statistical n requires source-supported row applicability, exact
  positive physical n, biological_preparations basis, and BOTH
  one_estimate_per_preparation and
  reported_sd_summarizes_counted_preparation_estimates. In source_cells both
  relationships must be source_supported. In the explicitly selected
  one_per_physical_preparation scenario each may instead be explicitly
  stipulated while unknown. Contradictions/conflicts cannot be overridden.

All matching statistical-count routes, if more than one is supplied, must agree.
No route enlarges the actual physical count. `statistical_count_matches_sd`
remains unknown when no separately selected count exists; this is neither
silently changed to source_supported nor a prerequisite for the separately
defined physical-roster mapping. Unknown extra counts do not corroborate n.

For actual242: source physical n2 and source row/footnote applicability survive.
The preparation-to-estimator relationship and exact SD-roster relationship
are unknown. The ordinary statistical n, mean variance and SE remain null.
The explicit scenario now stipulates BOTH relationships, sample n−1 SD and
IID common-mean finite-variance estimates. Under those assumptions alone it
uses n2 and computes s²/n=.005 and SE=.07071067811865475 in native units.
Normality and a known central mean identity are NOT prerequisites for that SE.
Relative SE additionally stipulates equal-weight central mean identity; the
optional t interval also stipulates normal sampling units. Actual242's full
illustrative interval scenario therefore names all SIX assumptions. The source
assessment statistical_count_matches_sd stays unknown throughout.

If either preparation-to-estimator or exact SD-roster relationship is unknown
and unstipulated, scenario statistical n remains unavailable. The new specific
reason is `sd_preparation_estimator_ownership_unknown` for the latter. Existing
sample-SD convention and IID requirements are checked separately after n is
known. Sample n−1 convention does not itself establish estimator ownership.

## 3. Separate parameter and SD unit scales, preserving partial precision

PLAN001's use of the parameter-native scale for SD was too restrictive when
the parameter unit is absent. Replace that convention with two independent
source scale records in CalculationInputs:

```
parameter_native_exact: Rational|null    # source printed central number
canonical_scale_exact: Rational|null    # ONLY the source parameter unit scale
canonical_unit: CanonicalUnit|null      # ONLY the source parameter unit

sd_native_exact: Rational|null          # source printed SD on its OWN unit scale
sd_scale_exact: Rational|null           # scale of the actual effective SD unit
sd_canonical_unit: CanonicalUnit|null   # dimension selected by that SD unit
sd_unit_basis: 'explicit_source_unit'|'inherited_parameter_unit'|'unavailable'
```

Add nullable parameter_unit_source and spread_unit_source Locator fields to
CalculationInputs.dependencies. Existing authenticated parameter/SD unit
witnesses supply them; no model-provided unit labels or scales are accepted.
No direct/cached canonical float is reverse-converted to a source decimal.

Parameter scale is populated only from a recognized selected parameter unit.
No parameter unit is inferred from parameter_kind, the SD's unit or a default.
The SD scale is independently populated from its explicit recognized source
unit when the existing reader's uncertainty.unit_relationship is explicit_unit.
For same_as_parameter it may inherit only a recognized selected parameter unit.
An explicit unit labelled same_as_parameter cannot serve as an independent
fallback when the parameter unit is unknown: existing reader contracts require
that relationship to be changed, with source support, to explicit_unit.

The existing reader ALREADY parses an explicit SD unit even when measurement
is null or its unit is null. Reuse its uncertainty.effective_unit and exact
_UNIT_TABLES scale. This correction requires no new scalar/unit parser. An
unsupported parameter_kind cannot establish SD's kinetic dimension and remains
unavailable. If parameter and SD canonical units are both available, they must
match; incompatible dimensions are not combined.

Let X=x_native*parameter_scale when available and S=sd_native*sd_scale when
available. Formulas become:

* reported_parameter = X with the parameter canonical unit.
* reported_sd = S with the SD canonical unit.
* relative_reported_sd = S/abs(X), requiring a point X≠0 and matching dimensions.
* mean_variance = S²/n in the SD canonical unit squared; no X prerequisite.
* mean_standard_error = sqrt(S²/n) in the SD canonical unit; no X prerequisite.
* relative_mean_standard_error = sqrt(S²/n)/abs(X), requiring point X≠0,
  matching dimensions and the specified central mean identity.
* Optional interval halfwidth = t*sqrt(S²/n), in the SD canonical unit; endpoints
  additionally require X and its equal-weight mean identity. Missing X leaves
  the valid halfwidth and SE available, without inventing an interval center.

No known parameter unit is needed for the dimensional SD-only variance/SE.
No known parameter VALUE is needed even if the parameter unit is known.
Unknown SD unit prevents dimensional SD/variance/SE; source count can survive.
Missing X cannot be replaced with zero or the SD magnitude.

Exact partial reasons: if X's value is absent, parameter-dependent cells use
source_measurement_unreported; if only its unit is absent, they use
source_kinetic_unit_unreported. SD-dependent cells use the independent
source_uncertainty_unit_unavailable or source_numeric_range from that SD
reading, rather than borrowing an unrelated parameter failure. If both
canonical quantities exist with incompatible dimensions, validation fails
`parameter_sd_canonical_dimension_mismatch`. Value/scale/unit/basis and source
locator relationships are validated together; sd_unit_basis=unavailable means
both SD scale and SD canonical unit null, while raw SD may remain retained.

Optional interval prerequisites are now explicit per cell: confidence level.95
is the selected proposed level when requested; df=n−1 requires an applicable
integer n≥2 and sample-SD convention; t multiplier also requires IID/normal
units; halfwidth also requires supported positive SD and the available mean SE.
Only lower/upper endpoints additionally require X and central mean identity.
All interval cells are null with interval_not_requested when no interval is
requested. No nonnormal interval, SEM/CI inversion or calibration inference is
added. Normality remains unnecessary for SE.

## Concrete IO and verification at this plan stage

ACTUAL_SOURCE_SELECTION_PROPOSAL002 adds the unknown exact SD-roster assessment
and the sixth explicit stipulation to001. Numerical arithmetic is unchanged:
source physical n2, ordinary estimator n null; canonical SD.000006;
conditional variance1.8e−11 and SE.000004242640687119285.

The synthetic contrast uses kcat summary SD0.2 s^-1 and exact n4 with explicit
sample-SD/IID/ownership statements; these are invented source snippets. The
existing reader is actually called for these snippets. Expected NEW-cell
outputs are labelled PROPOSED and are not executions of unimplemented modules:

| Synthetic input | Parameter result | SD / mean variance / SE | Relative results |
|---|---|---|---|
| Central value absent, SD unit explicit | null, source_measurement_unreported; parameter scale/unit null | 12 per_min;36 per_min_squared;6 per_min | null, source_measurement_unreported |
| Central10, parameter unit absent, SD unit explicit | null, source_kinetic_unit_unreported; native10 retained; parameter scale/unit null | 12 per_min;36 per_min_squared;6 per_min | null, source_kinetic_unit_unreported |
| Central10 s^-1, SD0.2 s^-1 | 600 per_min | 12 per_min;36 per_min_squared;6 per_min | relative SD.02, relative SE.01 |
| Central10 without unit, SD0.2 without unit | null, source_kinetic_unit_unreported | dimensional SD/variance/SE null, source_uncertainty_unit_unavailable; native SD.2/count4 retained | null |

All four retain source physical n4/statistical n4 under the synthetic supported
count meanings. Unknown X does not make n or SD unknown. If the selected SD
unit instead uses a valid different spelling/scale of the same dimension,
convert each independently before ratios (e.g. central10 s^-1, SD12 min^-1
gives the same canonical SD12 and relative SD.02).

The002 check also leaves exact SD-roster ownership unknown and unstipulated in
an actual-source scenario: it expects no statistical n/SE despite the physical
n2. Adding only the explicit missing relationship enables the conditional
count; changing source assessments to supported is never an arithmetic step.
The actual interval endpoint rounding differs by a few final floating-point
digits between SciPy and the independent reference quantile. Preserve the
exact source rationals and use numerical tolerances for t results; this is
numerical approximation, not extra experimental uncertainty.

The frozen001 manifest is reverified byte-for-byte. TASK bytes remain identical.
No new paper, provider material or model call was inspected. All processes are
terminal. Full A105/literature goal and selected integration remain unfinished.
