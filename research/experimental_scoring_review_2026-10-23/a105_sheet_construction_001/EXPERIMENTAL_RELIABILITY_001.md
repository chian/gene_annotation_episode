# A105 numerical sheet: experimental reliability and comparability proposal 001

2026-10-23. New research proposal for the user's judgment. This is part of the
A105 scoring sheet, not a production scorer, reader, investigation prompt, or
completed axis. All ten scoring sheets remain unfinished. Original instructions,
earlier proposals, source packets and scores are unchanged.

The active goal is the user's attachment
`/home/chia/.codex/attachments/9a858f85-d1dc-4f59-b574-9988cc09dee2/pasted-text-1.txt`.
The earlier goal-creation failure remains a historical fact; the user has now
activated this ten-sheet goal.

## What this calculation evaluates

An experiment supplies a measured molecular activity and the uncertainty with
which it establishes that activity under specified conditions. A separate
calculation asks what the activity implies about a function of the annotation
target. The measured value, experimental reliability and functional relevance
must not become one reader's overall grade.

This proposal defines a numerical experimental reliability weight as inverse
variance of a common-condition activity estimate. Different sources of error
are explicit numerical cells that add to that variance. The weight then
multiplies a numerical comparison between specified activity predictions. This
is one proposed combination for quantitative assays, not a claim that all assay
outputs are Gaussian or that function can be identified by one universal rate.

Condition differences have two effects that must stay visible: how much they
change the expected measurement, and how uncertain the correction is. Effect
isolation asks a different question: how much measured activity belongs to the
assayed molecule instead of another contributor. Both receive numerical cells.

## Assay definitions and fields to populate

The example below is entirely synthetic. It is not a FrsA measurement, a ybhP
result, or extra data in the earlier three-preparation example. The measured
quantity is formation of a chemically identified product in a purified-protein
preparation. The sample contains the assayed protein and a quantified
contaminating activity; it does not mix mutant and wild-type copies of the
assayed protein. Growth, deletion and restoration outcomes are outside A105.

The independent condition comparison measures the SAME assayed protein at the
test condition and the chosen reference condition. This estimates the effect of
conditions outside the intended molecular-activity question. It is not a
sequence-homology transfer or a comparison of different protein functions.

All uncertainty inputs below are standard uncertainties of the stated estimate,
not unexplained error bars. Independence is an explicit synthetic assumption.
Real extractions must retain covariance, replication and fitted-parameter
uncertainty; the arithmetic cannot assume independence merely because a paper
omits those details.

| Numerical input | Filled value | Unit and meaning |
| --- | ---: | --- |
| Sample product-formation rate | 1.20 | micromolar product/minute, before background correction |
| Matched blank rate | 0.20 | same unit and measurement conditions |
| Standard uncertainty of sample-minus-blank rate | 0.20 | same unit; includes their actual covariance |
| Contaminating product-formation rate | 0.15 | same unit; independent quantitative activity measurement |
| Standard uncertainty of contaminating rate | 0.15 | same unit |
| Product recovery | 1.00 | measured product/known added product after matching the matrix |
| Standard uncertainty of recovery | 0.05 | dimensionless |
| Assayed-protein concentration | 1.00 | micromolar of the specified protein; not total preparation mass |
| Standard uncertainty of protein concentration | 0.10 | micromolar |
| Reference comparison: rate at test condition | 2.00 | micromolar/minute, same comparison preparation and known protein amount |
| Standard uncertainty of that rate | 0.10 | micromolar/minute |
| Reference comparison: rate at reference condition | 1.60 | micromolar/minute, matched comparison preparation and protein amount |
| Standard uncertainty of that rate | 0.10 | micromolar/minute |
| Variance across independent reference-condition preparations | 0.0900 | squared per-protein turnover units |
| Within-preparation measurement variance contributing to that estimate | 0.0275 | same squared unit; independently estimated |

These last two variance estimates are hypothetical input summaries, not new
published data. Their estimation uncertainty remains necessary in a real
application. The calculation below is conditional on their filled values.

## Calculated cells

Write `net_rate = sample_rate - blank_rate` and
`condition_ratio = comparison_test_rate / comparison_reference_rate`.

The corrected common-condition activity is

```
activity = (net_rate - contaminating_rate)
           / (product_recovery * assayed_protein_concentration * condition_ratio)
```

It has units of product molecules per assayed-protein molecule per minute.
Normalization uses the amount actually measured, not an invented fully active
protein concentration. A changing active fraction needs its own measured
relationship and uncertainty.

| Calculated cell | Explicit calculation | Result | Scoring use |
| --- | --- | ---: | --- |
| Net product rate | 1.20 - 0.20 | 1.00 micromolar/minute | Input before contamination correction |
| Measured attributable fraction | (1.00 - 0.15)/1.00 | 0.85 | Multiplies net rate once; equivalent to subtracting contamination |
| Condition response ratio | 2.00/1.60 | 1.25 | Divides activity to express it at reference conditions |
| Condition-response similarity | min(1.25, 1/1.25) | 0.80 | Shows the measured mismatch; not another penalty after the correction |
| Corrected common-condition activity | (1.00 - 0.15)/(1.00 * 1.00 * 1.25) | 0.68 per minute | Effect estimate used by a stated functional comparison |

The attribution fraction describes measured ACTIVITY, not protein mass purity.
A noisy estimate outside its physical range is a model/measurement issue, not a
reason to silently clamp it. A zero denominator cannot yield an invented
attribution fraction. The condition ratio is a measured response ratio, not a
ratio of temperature, pH or nominal incubation time.

The proposed treatment of condition similarity is a specific choice for user
review: after a valid quantitative correction, its uncertainty reduces precision;
the raw 0.80 similarity does not also multiply the corrected result. This avoids
penalizing the same condition effect twice. If the correction cannot be
established, the common-condition activity remains uncomputed; raw activity and
the known differences are preserved.

## Numerical reliability components and their combination

For inputs `x` with covariance matrix `input_covariance`, use the gradient of the
activity calculation:

```
measurement_variance = gradient(activity)^T * input_covariance * gradient(activity)
total_variance = measurement_variance + residual_between_preparation_variance
experimental_precision = 1 / total_variance
```

This is first-order propagation, appropriate only when the local approximation
is supported. Broad uncertainty, ratios near zero, nonlinear depletion or
censored measurements require the corresponding distribution/likelihood rather
than forcing this approximation. Unknown uncertainty is not zero uncertainty.

For the declared independent synthetic inputs, the variance calculation splits
into the following additive cells. Each is in squared per-minute turnover units.

| Component | Calculation | Variance contribution |
| --- | --- | ---: |
| Sample and blank measurement | (0.20/1.25)^2 | 0.02560000 |
| Recovery calibration | (0.68 * 0.05/1.00)^2 | 0.00115600 |
| Differences between assay conditions | (0.68/1.25)^2 * [(0.10/1.60)^2 + (2.00 * 0.10/1.60^2)^2] | 0.00296225 |
| Isolation from contaminating activity | (0.15/1.25)^2 | 0.01440000 |
| Amount of assayed protein | (0.68 * 0.10/1.00)^2 | 0.00462400 |
| Unexplained variation between independent preparations | 0.0900 - 0.0275 | 0.06250000 |
| TOTAL | Sum of the six distinct contributions | 0.11124225 |

Thus the standard uncertainty is `sqrt(0.11124225) = 0.333529984` per minute,
and the experimental precision weight is `1/0.11124225 = 8.989390272`
in inverse squared turnover units. This is an actual calculation, not a
reliability category. Relative to measurement error alone, retained precision
is `0.0256/0.11124225 = 0.230128391`; that number is not a probability that the
annotation is correct.

The between-preparation term is excess variability after accounting for the
measurement variability already represented. Do not add a preparation SD and
the SE derived from the same observations as two independent error sources.
When an excess-variance estimate is negative, do not treat it as demonstrated
zero heterogeneity. Retain the estimate's uncertainty and fit or bound a
nonnegative variance model explicitly. No unknown component is silently set to
zero to permit an overall score.

## How the numerical components enter an evidence score

To show an explicit combination, consider two SYNTHETIC fixed predictions for
this same reference-condition measurement: `activity_if_function = 1.00` per
minute and `activity_if_alternative = 0.00` per minute. These numbers are not a
universal function threshold. In real work the predictions and uncertainty
must come from the actual competing explanations or measured references.
Possible functions can emerge during investigation; this does not require an
initial candidate annotation in the investigation prompt.

Under the stated equal-variance Gaussian measurement model:

```
log_evidence_ratio = experimental_precision / 2
                    * [(activity - activity_if_alternative)^2
                       - (activity - activity_if_function)^2]
```

Here:

```
log_evidence_ratio = (8.989390272/2) * (0.68^2 - (0.68 - 1.00)^2)
                   = 1.618090249
evidence_ratio     = exp(1.618090249) = 5.043449381
```

The measured data are about five times as likely under the first of these two
specified numerical predictions. This is not posterior annotation probability.
No generic "direct/transfer/contextual" multiplier appears. The known
contamination has already changed the activity and supplied its uncertainty;
multiplying by 0.85 again would repeat that correction. The condition correction
has likewise already been applied, with its measured uncertainty.

This likelihood comparison is a proposed numerical contribution interface, not
an adopted bounded A105 axis value. Predictions for broader functions, source-
to-target correspondence, nonlinear assays, and the final annotation-axis
combination are unfinished. A detected product can establish activity in the
assayed preparation without yet establishing which physiological annotation
should receive the score.

## Independent, shared and conflicting measurements

Independent evidence blocks contribute products of their likelihood ratios, or
sums of their log ratios. Different representations of one experiment do not
create extra blocks. Different detectors applied to one preparation can share
preparation, calibration, contamination and condition errors.

For jointly normal observations with a declared covariance matrix `covariance`,
the equal-covariance log ratio is

```
0.5 * [(observations - alternative_predictions)^T * inverse(covariance)
       * (observations - alternative_predictions)
       - (observations - function_predictions)^T * inverse(covariance)
       * (observations - function_predictions)]
```

If the two models have different covariance, include the corresponding
log-determinant and quadratic terms; the shortened expression is not valid.
Positive and negative log ratios can offset each other under compatible models;
do not retain only the maximum positive experiment. Incompatible endpoints or
conditions require an actual model relating them before this combination.
An exact duplicate is represented once; a singular covariance is not repaired
by inventing independent noise. Unknown dependence must remain unresolved or
be handled through an explicit sensitivity analysis.

## Nondetection: a different observation form

For a calibrated detection threshold `limit`, a standard uncertainty `noise`,
and a candidate predicted signal `predicted_activity`, the Gaussian censored
observation has likelihood

```
P(not detected | prediction) = normal_CDF((limit - predicted_activity)/noise)
```

This is not a measured value of zero. In a separate SYNTHETIC illustration with
noise 0.20 and predictions 1.00 versus 0.00 per minute:

| Detection limit | Likelihood under 1.00 | Likelihood under 0.00 | Log evidence ratio |
| --- | ---: | ---: | ---: |
| 0.10 per minute | 0.000003397673 | 0.6914624613 | -12.2234733204 |
| 2.00 per minute | 0.9999997133 | approximately 1 | -0.0000002867 |

The same words, "not detected," can therefore carry strong evidence against a
specified rate or almost no numerical discrimination. A different detector
distribution needs its own censored likelihood. Unknown detection thresholds
cannot be filled using either synthetic row.

## Inspected sources and component trace

| Source or retained example | What was actually inspected by the parent | Component implication |
| --- | --- | --- |
| Kellett et al. 2013, DOI 10.1021/bi400093y; supplement DOI 10.1021/bi400093y.s001 | Subagent paper note and the complete retained 15-page supplement text; direct web pages were inaccessible | Nondetection requires calibrated thresholds; different methods need condition-response information; qualitative assay checks do not supply numerical recovery |
| Muraoka & Zhang, DOI 10.1128/JB.01252-10 | The transport subagent's one-paper handoff, followed by a complete authority reread | Growth ratios remain outside A105 molecular-activity cells and are preserved for A106 |
| scoring_sheet_numeric_review_002.md | Complete earlier synthetic numerical example, repeatedly reread as required authority | Actual values, standard deviations, calibration and selectivity need arithmetic; their repeated representations are not independent proofs |

For the FrsA supplement specifically, the mass-spectrometry assay uses 0.05
micromolar protein for 720 seconds, and the NMR assay uses 5 micromolar for
5,400 seconds. The exposures are 36 and 27,000 micromolar-seconds. Their 750-fold
ratio does not establish a sensitivity ratio. Numerical detection limits,
blank uncertainty and recovery are absent from the inspected assay descriptions.
No numerical contradiction score or rate bound is assigned to that paper here.

The equations in this proposal are our conversion into the user's template;
they are not scoring rules asserted by those papers.

## Exact remaining work in A105

- Test these fields against the completed reaction, transport and binding
  examples, reading one source packet at a time with the required full reset.
- Finish numerical experimental relatedness to the inferred function and
  correspondence from the assayed molecule/system to the annotation target.
  Keep sequence, structure and other measured relationships available; no
  generic overall transfer grade substitutes for them.
- Define activity-model predictions and their uncertainty for each relevant
  measurement type. A binding EC50 is not automatically a dissociation constant
  or an activation measurement.
- Resolve how missing components and dependent measurements constrain a
  contribution without inventing defaults or discarding valid partial evidence.
- Define and review the final A105 contribution to annotation scoring, with
  contrasting filled published cases and numerical dataset examples.

No item above is marked complete by the calculations in this document.

## Parent's per-paper authority rereads

After the FucP handoff, the parent reread the complete authority set in the local
AGENTS.md plus the assignment brief and active goal. One output truncated part
of the earlier numerical example; that complete example, local instructions,
assignment and goal were reread to repair it before interpretation.

After the FrsA2013 note and complete supplement text, the parent again reread
the complete authority set: root AGENTS.md and GOAL.md; EPISODE_STRUCTURE.md;
TIME_AWARE_ESTIMATION.md; TOOL_KNOWLEDGE.md; TASK_AND_STEERING.md; its amendment;
EVIDENCE_AXIS_REVIEW amendment; VERBATIM_DIRECTION and VERBATIM_RECOVERY_002;
EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS amendment; the complete earlier numerical
example; the local AGENTS.md and A105_REVIEW_ASSIGNMENTS brief; and finally the
complete active user-goal attachment. No later paper packet was interpreted
before writing this proposal.
