# A105: a numerical contribution from the particular molecular inference

2026-10-23. **Unadopted mathematical proposal for discussion.** This adds to the
parent's `a105_sheet_construction_001/EXPERIMENTAL_RELIABILITY_001.md`; it does not
change that file or any previous record. A105 is unfinished and the ten-sheet
completion count is unchanged. This work supplies scoring-sheet mathematics,
not prompts, readers, production scoring, episode behavior, or scientific runs.

The parent owns applying these calculations to the published transport and
binding cases. This document uses only explicitly synthetic examples from the
supplied proposals and new, labeled synthetic illustrations. No primary paper
or retained paper-specific packet was opened in this assignment. It is not an
additional published-case review. The full authority reading is recorded in
`AUTHORITY_READ_001.md`.

## Proposed numerical contribution

Use an actual measured contrast and its experimental uncertainty to compare the
two sides of the **particular molecular statement**. Do not invent an absolute
rate for every possible protein function.

Examples of statements that can emerge during investigation are:

- This identified product forms above the measured background in this
  preparation and these conditions.
- This assayed molecule has a greater common-condition rate for substrate A
  than for substrate B.
- This assayed molecule has greater affinity for A than B under the specified
  equilibrium binding model.

Those are different statements. None alone is “this is the physiological
function of the annotation target.” The statement is defined when evidence
permits it; the investigation still starts from supplied material and does not
require a candidate annotation.

The proposed primary contribution is a **directional profile log-likelihood
contrast**, in nats. Write the joint log likelihood of the actual measurements
as `ell(theta, nuisance)`. The nuisance parameters include relevant background,
calibration, preparation and comparison terms. Let `H+` be the parameter region
that expresses the scoped statement, and `H-` the opposed region in the SAME
measurement model. Boundary points use closures so a maximum can be defined.

```
S = sup_(theta,nuisance in H+) ell(theta,nuisance)
    - sup_(theta,nuisance in H-) ell(theta,nuisance)
```

This is a generalized/profile likelihood comparison of two specified regions.
It is **not** a Bayes factor between fully specified functions, a posterior
annotation probability, or a calibrated probability of being correct. The
effect magnitude and the actual model remain separate sheet cells.

If the sheet needs a bounded contribution, the proposed conversion is

```
B = tanh(S / 2)
  = (exp(S) - 1) / (exp(S) + 1)
  = (best_likelihood_Hplus - best_likelihood_Hminus)
    / (best_likelihood_Hplus + best_likelihood_Hminus)
```

The last expression defines the scale: a normalized difference between the two
best fits to the SAME observations. `B=0` means equal best likelihoods; positive
and negative values indicate the favored side; swapping the two regions changes
the sign. `S` retains the amount of likelihood separation hidden by saturation
of `B`. This normalization has no selected ordinal anchors or arbitrary rate
unit. **Choosing this normalization for the sheet is still a policy proposal.**
Its boundedness does not calibrate it to annotation accuracy. An absent value is
`null/unknown`, never a silently inserted zero.

## Interface from the measurement and reliability cells

For the parent's purified-protein synthetic illustration, preserve the distinct
measured components:

```
net_rate = sample_rate - matched_blank_rate
attributable_rate = net_rate - measured_contaminating_rate
condition_ratio = comparison_test_rate / comparison_reference_rate
activity = attributable_rate
           / (recovery * measured_protein_amount * condition_ratio)
```

The condition comparison concerns differences OTHER THAN the intended variable.
The contamination term concerns isolation of the measured effect. They do not
answer the same question, even when both enter the activity calculation.

For a specified contrast `theta_hat = h(measured_inputs)`:

```
V_theta = gradient(h)^T * input_covariance * gradient(h)
          + distinct_residual_variance
```

With independent components this is the sum of each propagated variance. With
dependence it includes the cross terms `2 * derivative_i * derivative_j *
covariance_ij`. A cross term must remain a cross term; it cannot be assigned to
two separate quality scores. The inverse variance multiplies the contrast's
squared separation in the likelihood calculation below. Thus the numerical
measurement, comparability, isolation, calibration and replication cells combine
through explicit sums, products and covariance, rather than an overall verbal
grade.

The parent example's six variance terms are:

| Component | Variance in squared per-minute turnover units |
|---|---:|
| Sample and blank measurement | 0.02560000 |
| Recovery calibration | 0.00115600 |
| Comparison of assay conditions | 0.00296225 |
| Isolation from contaminating activity | 0.01440000 |
| Amount of assayed protein | 0.00462400 |
| Distinct variation between preparations | 0.06250000 |
| Sum | **0.11124225** |

The corrected activity is `0.68 per minute`; its conditional standard uncertainty
is `0.333529984 per minute`. These are inherited **synthetic** inputs, not new
measurements. The numerical calculations below condition on the stated error
model and variance values. The source proposal does not supply real finite
degrees of freedom for those six variance estimates.

The measured condition similarity `0.80` and attributable fraction `0.85` stay
visible. This document neither adopts nor rejects a separate mismatch penalty.
The user's feedback on that question is pending. The calculations here condition
on the parent's proposed quantitative correction, and do not silently multiply
those same corrections into the result a second time. If the user chooses an
additional similarity penalty, it will need an explicit purpose and numerical
definition distinct from the correction already made.

## Natural contrasts, magnitude and their inference limits

| Scoped inference | Numerical contrast, boundary and magnitude cells | What it does not establish |
|---|---|---|
| Signal above matched background | `theta = sample - matched_background`, after applicable quantitative corrections; boundary `0`; preserve the corrected rate and units | Attribution to one protein when mixed contributions remain unknown; product identity from a nonspecific detector |
| Positive attributed catalytic activity | Nonnegative physical rate `a >= 0`; compare `a > 0` with `a = 0`; preserve the rate and uncertainty | A biologically important rate, a preferred substrate, or physiological relevance |
| Greater rate for A than B | `theta = a_A - a_B`, boundary `0`; preserve both rates and `a_A/a_B` when defined | An untested substrate panel or an unspecified in vivo condition |
| Fold preference for A over B | `theta = log(a_A/a_B)`, boundary `0`; preserve ratio and both rates; positive rates and an appropriate ratio model are required | The same quantity as an arithmetic-mean rate difference; logs cannot be created using pseudocounts for nondetections |
| Catalytic-efficiency preference | `theta = log((kcat/Km)_A / (kcat/Km)_B)`; retain the fit covariance and the native efficiencies | A measured flux at arbitrary concentrations, or whole-cell substrate access |
| Affinity preference | `theta = log(Kd_B/Kd_A)` so positive means stronger binding to A; preserve native Kd values, units and fit covariance | Activation, repression, transport, turnover, or a Kd when the experiment only measures an assay-specific IC50/EC50 |
| Occupancy preference at declared free concentration | Under the stated one-site model, `f_j = L_j/(Kd_j+L_j)` and `theta = f_A - f_B`; the free concentrations are explicit operands | Native occupancy when concentrations, competition or the binding model are unknown |

The intended changed variable is not a condition mismatch. When asking whether
A or B is preferred, changing the substrate identity is the comparison itself.
Other condition differences need the separate comparability calculation.

**Strong direction is not necessarily substantial specificity.** For example,
the synthetic log ratio `0.001` with known standard error `0.00001` gives
`z=100` and `S=5000`, although the rate ratio is only `exp(0.001)`, about
`1.0010005` (a `0.10005%` difference). The supported statement is “the ratio
exceeds one,” not “the molecule is substantially selective.” A claim requiring a
specific, scientifically justified fold preference instead uses

```
theta = log(measured_ratio) - log(required_ratio)
```

The required ratio belongs to that actual inference and needs its own basis. It
is not a universal default such as “twofold means function.” If consequential
specificity has not been defined quantitatively, its score stays unresolved
while the raw ratio and evidence about any preference remain useful. Assay
detectability, positive rate and biologically consequential rate are different
questions.

## Exact scalar calculations under explicit error models

For a genuinely signed contrast with known normal measurement variance,
`theta_hat ~ Normal(theta, V)`, and the two half-lines `theta >= 0` and
`theta <= 0`:

```
z = theta_hat / sqrt(V)
S = sign(theta_hat) * theta_hat^2 / (2*V)
  = sign(z) * z^2/2
```

The unconstrained best fit is `theta_hat`; the opposite side's best fit is the
natural boundary `0`. No positive expected rate has been invented. Changing
units multiplies the estimate by `c` and variance by `c^2`, leaving `S` unchanged.

For a **physically nonnegative** attributed activity, use its actual parameter
space instead:

```
a_hat_constrained = max(0, observed_corrected_rate)
S_presence = a_hat_constrained^2 / (2*V)
```

Here the opposed region is exactly `a=0`. Negative measured sample-minus-blank
is preserved as an observed contrast, but does not create negative catalytic
activity. Under this particular nonnegative model it gives `S_presence=0`.
That means the broad alternative allowing arbitrarily small positive activity
has no improved fit; it does not prove absence. A negative contrast can also
expose unresolved background, quenching or model problems. Which interpretation
is supported is separate from this calculation.

With `0.68` and `V=0.11124225`, the known-variance calculation gives:

```
z = 2.038797210
S = 0.68^2 / (2*0.11124225) = 2.078347031 nats
B = tanh(2.078347031/2) = 0.777561486
```

This differs deliberately from the parent's `1.618090249` fixed-prediction
example. That example compares two imposed rates, `1` and `0`; this proposal
compares the best nonnegative activity fit with zero activity. They answer
different questions and are not interchangeable contributions.

### Variance estimates and finite samples

An estimated variance is not automatically a known variance. For `n` genuinely
independent normal paired contrasts `d_i`, an unknown common variance, mean
`d_bar`, sample SD `s` and standard error `s/sqrt(n)`:

```
t = d_bar / (s/sqrt(n)); df = n-1
S = sign(d_bar) * (n/2) * log(1 + t^2/(n-1))
```

Derivation: profile the normal likelihood over the common variance. At the
unconstrained fitted mean, `RSS_fit = sum((d_i-d_bar)^2)`; at the boundary,
`RSS_0 = RSS_fit + n*d_bar^2`. The maximized log-likelihood separation is
`n/2 * log(RSS_0/RSS_fit)`. The sign identifies the better half-line. For positive
nonnegative activity the same calculation compares its interior maximum with
zero; for a negative mean its nonnegative presence score is zero.

This formula is exact for the stated iid normal model. It is not a rule that
every reported t statistic can be treated this way. In particular:

- Welch, clustered, repeated-measure, bootstrap and nonlinear-fit standard errors
  need their actual likelihood or their native uncertainty model. Their reported
  degrees of freedom are not replaced by an invented sample size.
- A sum of propagated estimated variances does not acquire `df=n-1` by default.
  When independent chi-square-based variance estimates permit it, a
  Welch–Satterthwaite approximation is
  `df_eff=(sum v_j)^2 / sum(v_j^2/df_j)`. Known terms have infinite df. Correlated
  components and a difference of estimated variances do not meet that premise
  automatically. Even an approximate t pivot is not the above iid normal
  profile likelihood.
- A reported confidence interval, t/p statistic, standard error and raw fitted
  likelihood are different native quantities. A p-value is not a likelihood
  ratio. Do not manufacture `S` from `-log(p)`, an omnibus F test or a q-value.
- With one result and no uncertainty model, preserve its effect/ratio and the
  missing fields. With no residual spread in a tiny sample, do not assert
  perfect precision or an infinite score; instrument uncertainty, censoring
  and the fitted error model still matter.

As a scale check, the SAME numerical standardized effect `2.038797210` gives
`S=1.686589162, B=0.687550149` if it arises from three iid normal paired values
with an unknown common variance. This is a **new synthetic model comparison**,
not a claim that the parent's six variance components have two degrees of
freedom. Its known-variance result was `S=2.078347031, B=0.777561486`.

## Checked opposing specificity examples

These reuse the explicitly synthetic three-preparation example in
`verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md`.
They are not paper measurements. Rates are micromolar/minute after the stated
matched-blank correction. Preparation identities are paired across substrates.

| Independent preparation | A rate | B rate | A minus B |
|---|---:|---:|---:|
| 1 | 1.6 | 0.2 | 1.4 |
| 2 | 1.8 | 0.3 | 1.5 |
| 3 | 2.0 | 0.4 | 1.6 |

The intended variable is substrate/reaction identity. Assume, for this synthetic
calculation only, matched other conditions, adequate product identification,
applicable attribution and iid normal preparation contrasts. Three technical
readings from one preparation would not satisfy this independence assumption.

| Inference | Actual contrast | Uncertainty | Numerical contribution |
|---|---|---|---|
| Positive A activity | Mean `1.8`; SD `0.2` | SE `0.115470054`; `t=15.58845727`, df `2` | `S=7.212166545`; `B=0.998525972` |
| A rate greater than B | Paired mean `1.5`; paired SD `0.1` | SE `0.057735027`; `t=25.98076211`, df `2` | `S=8.736786139`; `B=0.999678913` |
| Opposite statement: B rate greater than A | Same data, contrast `-1.5` | Same SE; `t=-25.98076211`, df `2` | `S=-8.736786139`; `B=-0.999678913` |

For the A-minus-B calculation:

```
S = (3/2) * log(1 + 25.98076211^2/2)
  = (3/2) * log(338.5)
  = 8.736786139
```

These are conditional model calculations with only three synthetic preparations,
not validation that a real preparation distribution is normal. The native
two-sided t-test p-values are `0.004089997` for A activity and `0.001478197` for
the paired preference; they are retained as different statistics, not substituted
for annotation probabilities.

The ratio of arithmetic means is `1.8/0.3 = 6`. A calculation on within-pair log
ratios instead gives

```
mean(log(8), log(6), log(5)) = 1.826879641
geometric mean ratio = exp(1.826879641) = 6.214465012
SE of mean log ratio = 0.136809993
t = 13.35340788, df=2
S = 6.752324749; B = 0.997666404
```

These are two different estimands. The reader must populate the one used by the
actual inference, retaining the other's name if also reported. Neither is an
extra independent experiment. The activity, rate difference, arithmetic ratio
and log ratio all reuse these same six measurements.

## Combining observations, not counting representations

For independent observation blocks with the SAME linked parameters:

```
L_joint(parameters) = product_b L_b(observed_block_b | parameters)
ell_joint(parameters) = sum_b ell_b(observed_block_b | parameters)
S_joint = max_Hplus ell_joint - max_Hminus ell_joint
```

**Maximize after combining the likelihoods.** Summing per-experiment maximized
directional scores generally allows a separate fitted rate in every experiment,
which is a different hypothesis. It is valid to add fixed-hypothesis log ratios
when the corresponding likelihoods factor. It is not valid to assume the same
factoring after independently fitting every alternative rate. Do not add or
multiply bounded `B` values as if they were independent probabilities.

For estimates of one common signed effect with known joint normal covariance
`V` and vector `y`, an explicit closed form is

```
precision_total = 1^T inverse(V) 1
effect_pooled = (1^T inverse(V) y) / precision_total
variance_pooled = 1 / precision_total
S_pooled = sign(effect_pooled) * effect_pooled^2/(2*variance_pooled)
```

All calibration, condition-response, preparation and shared-control dependence
must be represented in `V`. Native common nuisance parameters can instead stay
in the joint likelihood and be profiled there. A shared multiplicative factor
can cancel from a rate ratio; propagating its two appearances as independent
errors would invent uncertainty. Conversely, technical repetitions do not
reduce a shared calibration or preparation uncertainty by `1/n`.

New **synthetic** examples use observations `0.68, 0.78`, each with variance
`0.11124225`, to demonstrate this difference:

| Model | Pooled mean | Pooled variance | S | B |
|---|---:|---:|---:|---:|
| Independent observations of one common effect | 0.73 | 0.055621125 | 4.790446076 | 0.983519432 |
| Same preparation/calibration, shared covariance `0.08564225` | 0.73 | 0.098442250 | 2.706663044 | 0.874837344 |

The shared example leaves only the `0.0256` measurement component independent.
That covariance is an explicit synthetic assumption, not inferred from a paper
or adopted for all experiments. An exact duplicate has covariance equal to its
variance and supplies one observation, not two. Its singular matrix is handled
by representing the original measurement once, not by adding invented noise.
Unknown dependence stays unresolved or is explored over a specified, justified
covariance range; it is not defaulted to independence.

For independent signed contrasts `+0.68` and `-0.68` with the same variance,
the common-effect mean and directional score are zero. Their residual
heterogeneity remains

```
Q = (y - mean)^T inverse(V) (y - mean) = 8.313388124
```

Under that known-covariance common normal model, Q has one residual degree of
freedom. The zero mean is not evidence that both preparations lacked an effect.
It exposes disagreement with a single common direction. Preserve the two
effects and their conditions. A random-effects likelihood
`y_i ~ Normal(mu, v_i + tau^2)` can estimate distinct between-preparation variance
when its exchangeability assumptions are justified, with uncertainty/profile
over `tau`; it is not a license to pool unrelated endpoints. Do not simply
subtract an estimated noise variance and treat the remaining tau estimate as
known. Q is a model diagnostic, not an extra arbitrary multiplicative penalty.

## Nondetection without an invented alternative rate

Suppose the actual report is `Y < L`, where L is a calibrated threshold and
the detector model is `Y ~ Normal(a, sigma^2)`. Its likelihood factor is

```
L_censored(a) = Phi((L-a)/sigma)
```

This factor can be combined with other observations and profiled over the same
unknown rate `a`. The observed value is NOT replaced by zero or half the limit.
If the detector reports an interval, the factor is the difference between its
two CDF values. Unknown limits, unexplained “not detected” calls or unmeasured
sensitivity do not supply these operands.

For a physically nonnegative activity, nondetection by itself cannot distinguish
zero from every arbitrarily small positive rate. Both regions' supremum is at
the zero boundary, so `S_presence=0`. A separate upper confidence bound remains
useful. At stated level `1-alpha`, inversion of the event yields the conservative
bound

```
a_upper = L + z_(1-alpha) * sigma
```

For the synthetic `L=0.10`, `sigma=0.20`, a 95% upper bound is `0.428970725`
in the same rate units. The 95% level is an explicitly declared reporting
choice, not an annotation-score threshold. This upper bound can limit a
specificity comparison to a genuinely measured positive alternative; no
infinite selectivity ratio is inferred from the nondetection.

Nondetection still changes an existing activity inference. Combine the parent's
synthetic positive estimate `0.68`, variance `0.11124225`, with the independent
censored observation above, assuming both measure one nonnegative rate:

```
ell(a) = -(0.68-a)^2/(2*0.11124225)
         + log(Phi((0.10-a)/0.20)) + constant
```

Numerical maximization gives:

| Quantity | Positive observation alone | Positive plus censored observation |
|---|---:|---:|
| Nonnegative maximum-likelihood rate | 0.68 | 0.147958504 |
| S against zero activity | 2.078347031 | 0.271726302 |
| B | 0.777561486 | 0.135033321 |

The censored observation reduces support without a fabricated zero-rate datum.
Its own contribution is not “zero and therefore irrelevant”; it enters the
joint likelihood. A claim that the rate exceeds a particular nonzero boundary
can receive negative support, but that boundary must define a real scoped
inference, not an invented universal function rate.

## Unknown weaknesses and useful conditional calculations

No requirement is introduced to measure every conceivable assay-quality
property before retaining a useful result. Preserve the largest defensible
scope: a preparation measurement can be quantified even when single-protein
attribution is unresolved; a source activity can be quantified while transfer
to the annotation target is unresolved.

Distinguish four situations explicitly:

1. **Measured correction and uncertainty:** apply the correction, with its
   covariance, to the inference it actually measures.
2. **Quantified residual bias bounds:** propagate a sensitivity interval in
   addition to statistical uncertainty.
3. **Known applicable weakness with unquantified effect:** preserve a conditional
   calculation and name the unresolved operand; do not set its variance or bias
   to zero in an unconditional result.
4. **No demonstrated applicability of a proposed metric:** do not demand that
   metric merely to fill every column. Mark its relationship as inapplicable or
   unestablished without converting that label into a numerical quality score.

For residual comparison bias `b_cmp` and residual isolation bias `b_iso`, define
the sign so the actual contrast is estimated by

```
theta_corrected = theta_hat - b_cmp - b_iso
```

For known variance and justified bounds, evaluate S over the joint allowed bias
set. Do not assume independence or uniform distributions from bounds alone.
In a new **synthetic** illustration, `b_cmp in [0,0.10]` and
`b_iso in [0,0.20]` yield `theta_corrected in [0.38,0.68]` for the parent's
`0.68` example. Holding its statistical variance fixed gives

```
S in [0.649033978, 2.078347031]
B in [0.313585477, 0.777561486]
```

These are sensitivity ranges, not confidence intervals. An unbounded unknown
bias cannot support a finite unconditional range; the conditional measured
contrast and its numerical calculation remain recorded. A sensitivity interval
never becomes a midpoint score without an explicitly justified additional
model.

## Compound molecular inference and cross-endpoint dependence

Activity and specificity are not two independent confirmations when calculated
from the same rates. Binding and catalytic activity are different endpoints.
An endpoint's well-measured contrast does not establish an unmeasured
consequence. If a particular inference requires several measured statements,
declare that relationship and use their joint data model rather than multiplying
bounded scores.

For example, if an inference explicitly means two signed contrasts are both
positive, its region is

```
H+ = {theta_1 > 0 AND theta_2 > 0}
H- = {theta_1 <= 0 OR theta_2 <= 0}
S = max_Hplus ell_joint - max_Hminus ell_joint
```

For known multivariate normal measurements, each maximization is a covariance-
aware constrained quadratic fit. With two independent unit-variance contrasts
whose observed standardized effects are `(2,3)`, `S=min(2^2/2,3^2/2)=2` and
`B=0.761594156`. Changing the first measured effect to `-2` gives `S=-2` and
`B=-0.761594156`. The joint likelihood is the product of the two measurement
likelihoods; the implication requires both directions, so adding their two
favorable individual scores would answer a different question.

These are synthetic mathematical contrasts, not a prescribed checklist of
assays. The required conditions come from the stated inference; no new
scientific acceptance gate is introduced. When a consequence is unmeasured,
retain contributions to the measured statements instead of silently scoring
the broader function. Different constraint geometries have different null
distributions; do not label `2*abs(S)` a universal chi-square statistic.

## Source-to-target interface agreed with the parallel relevance worker

The primary interface is a measured or fitted response mapping plus its
uncertainty, not one intuitive transfer multiplier. The relevance worker owns
the component measurements and any fitted correspondence model. The present
sheet consumes its output as follows.

For positive common-endpoint activities with supported response ratios
`r_j = exp(d_j)`:

```
a_target = a_source * product_j r_j
log(a_target) = log(a_source) + sum_j d_j
V_log_target = J * Sigma_source_and_bridge * J^T
               + distinct_residual_correspondence_variance
```

For a fold-preference inference, the natural contrast is

```
theta_target = log(a_A_source/a_B_source)
               + sum_j d_Aj - sum_j d_Bj
```

Common response factors can cancel; source/bridge and A/B covariance must be
retained. The resulting contrast and appropriate target uncertainty enter S
once. For a claim above a specified fold boundary, subtract its log boundary
only after defining that claim.

For activity above background, map the actual sample and background endpoints
before subtracting them. Multiplying a net contrast is justified only when the
mapping model says it is. A log transformation cannot represent a zero-activity
null; the original-scale activity likelihood or a corresponding generative
model must be used for that null.

The relevance worker's retained-precision diagnostic
`V_source/(V_source+V_bridge)` applies only to distinct independent errors on
the same stated scale. It is not an extra multiplier after using target
variance, a probability of transfer, or a substitute for the signed response
mapping. The mapping can change the effect as well as its precision, including
reversing a preference. Unknown bridge coefficients/covariance leave the target
contribution unknown and the source-scoped contribution intact. Native sequence,
structure or phylogenetic scores do not by themselves supply missing activity
response coefficients.

## Exact sheet fields and population contract

This is a schema proposal, not reader implementation. Numbers populated from a
source must remain distinguishable from deterministic derived values and from
assumed model parameters.

| Field | Type and numerical meaning | Population/calculation |
|---|---|---|
| `endpoint_values` | Numeric vector with units, uncertainty form and censoring | Actual assay outputs, controls, thresholds or fitted parameters |
| `contrast_coefficients` / `contrast_function` | Numeric coefficients or fully defined function and numerical operands | Chosen from the specific measured inference; no candidate-name prerequisite |
| `contrast_boundary` | Number in contrast units; normally zero for the listed natural contrasts | Mathematical equality boundary, or justified claim-specific boundary |
| `effect_estimate`, `native_ratio` | Number or interval with precise denominator | Deterministic contrast; ratio only when defined |
| `comparability_corrections`, `comparability_covariance` | Numeric response corrections and their covariance | Same-endpoint experimental comparisons excluding the intended variable |
| `isolation_corrections`, `isolation_covariance` | Numeric contaminating/background contributions and covariance | Measurements that address attribution of this endpoint |
| `other_covariance`, `shared_nuisance_parameters` | Matrices/parameter values with common units and relationships | Calibration, preparation, technical/biological replication, condition and endpoint sharing |
| `independent_unit_count`, `error_df` | Counts/df for the actual estimation model; unknown permitted | Preparation/subject/randomization identities and uncertainty procedure, not paper count |
| `likelihood_operands` | Numerical parameters and observation form | Stated error/fit model, including censored events and uncertainty estimation |
| `profile_log_ratio` | S in nats, or an explicitly conditional value/range | Two constrained maximizations; closed form only under its assumptions |
| `bounded_profile_contrast` | B in `[-1,1]`, or conditional range | `tanh(S/2)`; proposed scoring scale, not annotation probability |
| `native_test_statistic`, `native_p_or_interval` | Original statistic/p/interval with test and parameter meaning | Preserve directly; no automatic conversion to likelihood |
| `heterogeneity_statistic` | Q or model-specific fit statistic, with df where justified | Joint-model residual calculation; not extra independent evidence |
| `residual_bias_bounds` | Numeric allowed sets, split by comparability and isolation | Actual measured bounds or explicitly labeled sensitivity assumptions |
| `source_target_response_operands` | Numeric response mapping, covariance and residual model | Parallel relevance sheet; target contribution calculated after mapping |
| `selection_count_or_model` | Tested panel count or actual selection model when known | Required to understand discovery-selected contrasts; unknown preserved |

Supporting source/experiment identities, actual assayed subject, conditions,
parameter-space definition, claim scope, independence groups and unresolved
limitations accompany these numbers. They are not numerical scores themselves.
A typed status must distinguish a measured zero, a zero profile improvement,
an unknown number, a conditional calculation and an inapplicable operation.

For discovery-selected substrates/targets, S is conditional on the examined
comparison. Selecting the largest signal from a large panel can increase its
chance separation. Preserve the tested panel and selection process; a held-out
confirmation, a joint panel model, or a valid selection-aware inference can
address it. Do not pretend that an unknown panel size is one, silently rescale
S by a guessed count, or claim an uncalibrated selected result is an annotation
probability. This is a limitation of the score, not a mandatory new experiment.

## Trace, checks and exact remaining choices

| Inspected input | Numerical use here |
|---|---|
| Parent `EXPERIMENTAL_RELIABILITY_001.md`, its complete checker and `arithmetic_001.json` | Corrected synthetic activity, six variance contributions, uncertainty and condition/isolation distinction; its fixed-rate comparison remains a different example |
| Complete `scoring_sheet_numeric_review_002.md` | Three explicitly synthetic paired preparations, native calibration/ratio meanings; these values are reanalysed, not counted as new data |
| Full authority set and current assignment/goal | Numerical components must combine; source records alone are not a sheet; A106 remains separate; preservation and pending feedback |
| This document's explicit mathematical models | Profile likelihood, finite-sample paired-normal expression, bounded normalization, censoring, joint covariance and compound-inference examples; not claims attributed to papers |
| Direct coordination with `a105_target_relevance_003` | Response mapping/covariance interface only; no invented fitted coefficients or completed target calculation |

`check_contribution_arithmetic_001.py` ran successfully with Python 3 and SciPy
and created `arithmetic_001.json`. It checks likelihood algebra against residual
sums of squares, unit invariance, sign reversal, the nonnegative activity
boundary, both ratio estimands, shared errors, exact duplicates, opposing
contrasts, a censored-likelihood optimum and its derivative, upper-bound
inversion, bias ranges and the two-condition conjunction example. These are
research calculations, not evidence that any real assay obeys the models.

The remaining choices are exact rather than hidden in a single grade:

1. Whether S, the proposed B normalization, or another explicitly meaningful
   scale is adopted for A105. No calibration to annotation accuracy is supplied.
2. Whether an additional penalty for corrected experimental mismatches is
   desired, and what distinct measured quantity it should represent. Current
   conditional arithmetic does not presume the user's answer.
3. Each published case's actual error model, uncertainty type/df, covariance,
   background, attribution, censoring and relevant inference boundary. Parent
   case work supplies these; missing operands cannot be filled from this toy.
4. Any quantitatively consequential specificity boundary and any response model
   connecting the measured source to the annotation target. “Any preference”
   cannot silently be relabeled “physiological function.”
5. How selected comparisons and shared endpoints are handled in the particular
   annotation's evidence chain. The joint likelihood definitions supply a
   coherent route; an unidentified model remains unfinished work.

Scientific investigation progress remains separate from annotation support.
A newly discovered qualification or sensitive nondetection can reduce S or B
while advancing the investigation. This proposal neither calculates that
progress nor changes the continuation controller or W05 annotation-credit code.
