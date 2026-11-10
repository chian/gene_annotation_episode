# A105 joined numerical sheet — proposal for judgment

2026-10-23. This document joins the numerical work into one reviewable proposal.
It adopts no scoring policy and changes no production scorer, reader, prompt,
episode or scientific run. Prior research records remain unchanged. A105 is
measured molecular conversion, transport or binding; perturbation/restoration
belongs to A106. A109 remains removed and A110 remains separate. The ten-axis
checklist remains A105, A101, A102, A103, A104, A106, A107, A110, A111.

## 1. Investigation prompt, separate from the numerical sheet

The following preserves the task text from the corrected discovery proposal
`verification/a105_three_parts_review_2026-10-23_001/prompt_insert_003.md`.
It is not a production prompt change.

> Find and evaluate experimental evidence to determine what molecular activities the supplied gene or protein may perform. Start from the supplied sequence, specified file record or region, or snippets. A candidate annotation or searchable public name is not required; possible functions should emerge from the evidence.
>
> Examine measurements of substrate conversion, transport or binding from published findings or experimental datasets, including measurements on relevant homologs. Distinguish what was measured on the actual assayed subject from what can be inferred about the supplied target.
>
> Retain the assayed subject/preparation, molecular endpoint, native quantities/units, controls, conditions and source experiment/dataset. Distinguish direct molecular measurements from proxies, including proteomic abundance or association. For homolog evidence, retain the correspondence and limitations connecting the measured activity to the supplied target. Preserve negative results, uncertainty, and the boundaries of partial sequences or snippets. Binding, conversion, transport and physiological role remain distinct conclusions.

The assignment can therefore start from a sequence alone. A particular molecular
statement is specified when evidence is evaluated and scored; it is not a
required initial hypothesis. This detailed recurring task remains separate from
terse steering about actual previous results and next-action expectations.

## 2. Numerical scoring sheet

### A. Experimental comparability, isolation and reliability

The first worked calculation is entirely **synthetic**. It illustrates an
assayed protein's reaction rate. It is not a ybhP result or a published assay.
Other molecular endpoints retain their actual physical measurement equations.

For this experiment:

`corrected_activity = (sample_rate - blank_rate - contaminant_rate)`
`                     / (recovery * protein_amount * condition_response)`.

The condition response is a measured change in this same endpoint outside the
variable deliberately under investigation. A temperature or pH similarity by
itself is not a measured rate correction. Background/contamination addresses
isolation, which remains a separate question from condition comparability.

| Numerical cell | Actual operands in this synthetic example | Calculation | Value |
|---|---|---|---:|
| Net preparation rate | sample 1.20 and blank 0.20 micromolar/minute | 1.20 - 0.20 | 1.00 micromolar/minute |
| Contaminating activity | independently quantified contributor | supplied measured component | 0.15 micromolar/minute |
| Protein-attributed rate | net preparation minus contaminant | 1.00 - 0.15 | 0.85 micromolar/minute |
| Recovery | measured/reference calibration response | supplied ratio | 1.00 |
| Protein amount | measured assayed concentration | supplied concentration | 1.00 micromolar |
| Condition response | same-endpoint rates 2.00 and 1.60 under the two conditions | 2.00/1.60 | 1.25 |
| Corrected molecular activity | preceding cells | 0.85/(1.00*1.00*1.25) | 0.68 per minute |
| Measurement variance contribution | propagation of net-rate uncertainty 0.20 micromolar/minute | (0.80*0.20)^2 | 0.02560000 |
| Recovery variance contribution | recovery standard uncertainty 0.05 | (0.68*0.05)^2 | 0.00115600 |
| Condition-response variance contribution | independent standard uncertainties 0.10 and 0.10 on rates 2.00 and 1.60 | propagated through their ratio and the correction | 0.00296225 |
| Contamination variance contribution | contaminant standard uncertainty 0.15 micromolar/minute | (0.80*0.15)^2 | 0.01440000 |
| Protein-amount variance contribution | amount standard uncertainty 0.10 micromolar | (0.68*0.10)^2 | 0.00462400 |
| Distinct residual variance contribution | synthetic between-preparation variance 0.09 minus already represented contribution 0.0275 | 0.09 - 0.0275 | 0.06250000 |
| Total activity variance | sum of the six nonoverlapping terms | 0.0256+0.001156+0.00296225+0.0144+0.004624+0.0625 | 0.11124225 per minute squared |
| Standard uncertainty | square root of total variance | sqrt(0.11124225) | 0.33352998 per minute |
| Precision | inverse variance | 1/0.11124225 | 8.98939027 minutes squared |

The six variance entries are not arbitrary quality weights. Their values follow
from the declared uncertainty in measured operands and the measurement equation.
In general use `V = J*Sigma*J_transpose + V_distinct_residual`, retaining all
known covariance terms. Independence is explicitly assumed in this synthetic
example. Unknown covariance or an applicable unquantified bias is not zero.
An estimated between-preparation variance is not added again if the preceding
error model already includes it. The numerical difference 0.09-0.0275 here is
a constructed positive example, not a universal variance-estimation rule.

The attributed fraction 0.85 and condition similarity 1/1.25=0.80 can be
displayed to explain this experiment, but they are not additional multipliers
after the same observations have already corrected the rate and its error.
Whether the original mismatch should incur an additional penalty was asked
separately; no user approval of that extra penalty is recorded.

### B. How the numerical components contribute

For this example only, the molecular statement is positive activity under the
declared conditions versus zero activity. With the hypothetical known-normal
error model and nonnegative activity parameter, the observed positive estimate
gives:

`S = corrected_activity^2 * precision / 2 = 2.078347030917`

`B = tanh(S/2) = 0.777561486079`.

Here S is the difference between the best log likelihoods under the stated
alternatives, and B is their normalized best-fit difference. **Neither is a
probability that the annotation is correct.** The raw activity and uncertainty
remain available; a precisely measured tiny activity does not become a large
physiological activity. A negative measured rate does not become positive
evidence by squaring it: under the nonnegative-activity model its best fit is
at zero. An ordered specificity contrast can instead have genuinely signed S.

The proposed general definition is

`S = best_log_likelihood(statement) - best_log_likelihood(opposed_statement)`
`B = tanh(S/2)`.

It combines the actual observation model before optimization. It does not add
individually optimized scores from overlapping summaries. Defined examples in
`a105_contribution_math_003/CONTRIBUTION_PROPOSAL_001.md` include paired finite
normal samples, known covariance, censored nondetection and joint statements.
For paired finite normal differences, with n observations, sample mean d and
sample SD s, `t=d/(s/sqrt(n))` and
`S=sign(d)*(n/2)*log(1+t^2/(n-1))`. That formula is not a general conversion of
reported p values, Welch statistics or arbitrary error bars.

Transport uses a quantified transport endpoint; binding uses its actual curve
or competition endpoint. An IC50 is not silently substituted for Kd. Different
endpoint equations can fill the same roles of measured effect, uncertainty,
defined comparison and numerical contribution without making every assay a
reaction-rate calculation.

### C. Relevance of an assayed molecule to the supplied target

When measured response relationships exist, transform the effect through those
relationships and propagate their covariance before calculating target S/B.
That route predicts a target-scoped quantity under its actual fitted model.
It does not multiply by the same correspondence observations a second time.

For an ordinary novel target without such calibration, the following is an
explicit **uncalibrated scoring convention**. It uses individual native
measurements and declared sums, rather than one intuitive transfer grade.
It does not predict a target rate or function probability. These five rows are
components of this source-to-target relationship, not five replacement axes.

| Relationship component | Synthetic native operands | Proposed numerical conversion | Result |
|---|---|---|---:|
| Sequence correspondence | comparable local raw pair score 240; source and target self scores 300,320 | 2*240/(300+320) | 0.77419355 |
| Structural correspondence | TM scores with source/target normalization 0.90,0.85 | min(0.90,0.85) | 0.85000000 |
| Functional-site correspondence | 8 exact matches among 10 predefined, observed sites | 8/10 | 0.80000000 |
| Phylogenetic placement | 85 supporting placements among 100 eligible replicates | 85/100 | 0.85000000 |
| System similarity | temperature difference 7 degrees, pH difference 0.5; proposed reference variances 100 degrees squared and 1 pH-unit squared | exp[-0.5*(49/100+0.25/1)] | 0.69073433 |
| Combined relationship R | explicit equal family weights | sum(the five rows)/5 | 0.79298558 |
| Signed target contribution D | source B multiplied once by R | 0.777561486079*0.792985575805 | 0.61659504 |

The sequence normalization applies only to the defined compatible raw-scoring
setup; it is not a conversion of arbitrary HMM bits or E values. Site identity
does not establish the effect of a substitution. Placement frequencies are not
probabilities of function. The system scales are proposed constants in this
synthetic example, not measured enzyme response. These limitations matter to
the interpretation of the resulting conventional score.

Multiple tools share a declared component's fixed weight; another tool output
does not add a new family or an independent experiment. Native output and
normalization details remain in the sheet. The exact component definitions,
including applicability of the sequence normalization and partial-site bounds,
are in `a105_target_relevance_003/UNCALIBRATED_CORRESPONDENCE_CONVENTION_002.md`.

An explicit alternative to the arithmetic mean is the shifted harmonic mean
`R_H = 5 / sum(1/(0.1+r_j)) - 0.1`. The shape constant 0.1 is proposed, not
calibrated. For this balanced example R_H=0.78889948 and D_H=0.61341785.
For an uneven synthetic vector [0.95,0.95,0.95,0.10,1.00], arithmetic R=0.79,
but harmonic R=0.47037037. The alternative gives a low local correspondence
component more influence. Neither declares that a changed residue loses function.
This is a choice for judgment, not an adopted replacement.

If the evolutionary component is unknown, do not fill it with zero or one:

- Four-observed-family arithmetic R is 0.77873197 and D is 0.60551199. This is
  explicitly conditional on the four observed families.
- The possible complete-five-family R lies in [0.62298558,0.82298558], giving
  D in [0.48440959,0.63992189] for this positive source B.
- These are identification bounds, not confidence intervals. A conditional
  point is not a completed five-family score. A negative B reverses the bounds
  before ordering them. No midpoint is silently selected.
- Unknown full-sequence coverage cannot be replaced by perfect identity within
  a supplied snippet. Preserve the actual supplied-material scope.

### D. Proposed nonnegative annotation-coordinate handoff

The existing retained hypervolume helper requires each numerical coordinate
in [0,1]. It currently supplies no adopted A105 mapping or ten-axis parameters.
The smallest explicit positive-support proposal is:

`A105_coordinate = max(0, D)`; unknown D remains unknown.

For the fully specified single-source synthetic example it gives **0.61659504**.
The signed D and the native measurements remain in the sheet. Contrary compatible
evidence must enter the combined calculation before this projection; it is not
clipped out experiment by experiment. Once the coordinate is zero, this scalar
cannot express increasing opposition. The retained signed sheet can. This
information loss is an explicit choice for judgment.

The source-scoped check using known variance 0.11124225 illustrates combination:

| Evidence for one compatible signed contrast | Combined estimate | Signed B before any correspondence multiplier |
|---|---:|---:|
| One observation +0.68 | +0.68 | +0.77756149 |
| Same original observation delivered twice | +0.68 | unchanged +0.77756149 |
| Independent +0.68 and -0.34 | +0.17 | +0.12917100 |
| Independent +0.68 and -0.68 | 0 | 0, with disagreement retained separately |
| Independent +0.68 and +0.78 | +0.73 | +0.98351943 |
| Same two positive values with covariance 0.08564225 | +0.73 | +0.87483734 |

Different conditions/endpoints need their actual relationship before pooling.
Nondetection contributes its censoring likelihood when the detection threshold
and noise model are known; it is not a zero observation. Missing inputs remain
unknown. Repeated representations are identified by actual measurement identity,
not equality of values or number of publications. Compound molecular statements
require their joint comparison; a binding result does not alone fill a conversion
or physiological-role endpoint.

The separate proposal for multiple differently related assayed homologs must
be attached before this becomes a general multi-source axis calculation.
Multiplying R by a source B does not create a target likelihood that can be
independently multiplied across homologs. There is no maximum-positive-source
fallback in this sheet.

## Published examples informing the numerical cells

These are source-grounded measurements or explicit derived calculations. They
are not values for the project's target and are not the synthetic complete chain.

| Inspected source | Numerical example | Scoring component exposed | Constraint preserved |
|---|---|---|---|
| Knorr et al. 2018, DOI 10.1038/s41467-018-07563-6, CsiD Supplementary Figure 5 and electrode Methods | Graph-derived oxygen rates about 0.16062 and 0.10484 micromoles/min; difference 0.05578; conditional profile S=5.50823, B=0.991926 | Actual data, endpoint comparison, error type and conditional measurement model | Preparation oxygen rate is not isolated product formation; graph values are not raw instrument data; target correspondence unknown |
| BtsT 2018, DOI 10.1128/JB.00599-17, whole-cell kinetic figure/Methods | Km=16.5 micromolar; fractional saturation at 10 and 40 micromolar is 0.37736 and 0.70796; same-system rate ratio 0.53302 | A measured nonlinear condition response, with covariance from the shared Km | Do not apply this curve to a different vesicle system or call reported spread a known SE |
| IscR 2013, DOI 10.1038/nsmb.2568, competition tables/Methods | 32 nM versus >510 nM gives a point-derived selectivity ratio >15.9375 and log ratio >2.76867 | Censored specificity, denominator and shared-reference error | Not Kd; not a confidence bound; binding does not itself score activation |
| IscR 2025, DOI 10.1111/mmi.70021, binding/state Methods and Figure 4 | Apparent Kd 22 nM versus >1000 nM; ratio >45.4545; after air then anaerobic treatment 26/22=1.18182 | Measured binding contrast versus state at the time of measurement; qualifications of an earlier interpretation | Preparation labels need not identify the measured state; missing numerical fit uncertainty remains unknown |

The corresponding parent conversion records are CSID_NUMERICAL_CELLS_003.md,
BTST_NUMERICAL_CELLS_001.md, ISCR_NUMERICAL_CELLS_001.md and
ISCR_STATE_QUALIFICATION_002.md in this directory. They record actual inspection,
complete per-paper authority resets, source locations, arithmetic and limitations.

## 3. Exact inputs for the readers that populate this sheet

These are reader responsibilities and numerical field meanings, **not implemented
readers** and not additional prompt text. Literature extraction and dataset
analysis can provide the same numerical operands; deterministic calculations
then fill the same derived cells under the declared model.

| Exact cell or input group | Type and units | How populated |
|---|---|---|
| `sample_rate`, `blank_rate`, `contaminant_rate` | nullable finite numbers in one declared rate unit, with numerical uncertainty/bounds | Read measured assay results or calculate them from actual traces; preserve the actual control meaning |
| `recovery`, `protein_amount`, `condition_response` | nullable finite numerical operands with their units and joint covariance | Read calibration/concentration/condition-comparison measurements; no generic condition grade |
| `input_covariance`, `distinct_residual_variance` | declared square covariance matrix and nonoverlapping residual variance | Derive from actual independent replicates/calibration or preserve supplied estimates; unknown is not independence |
| `corrected_effect`, `effect_variance` | nullable derived numbers with endpoint-specific units | Apply the declared measurement equation and covariance propagation |
| `comparison_boundary`, `measurement_model_inputs` | endpoint boundary and exact numerical operands of the selected calculation | The scoped molecular comparison and actual error/censoring design; no default universal consequential-activity threshold |
| `profile_log_ratio`, `source_signed_index` | nullable S in log-likelihood units and B in [-1,1] | Defined joint comparison, then tanh(S/2) |
| `pair_raw_score`, `source_self_score`, `target_self_score` | actual compatible raw scores | Selected sequence comparison and its two self comparisons |
| `tm_source`, `tm_target` | actual dimensionless native scores | Selected structural comparison with both normalization meanings |
| `site_matches`, `sites_observed`, `sites_declared` | nonnegative integer counts with 0<=matches<=observed<=declared | Actual mapping of the predefined sites; partial observation stays partial |
| `placement_support_count`, `placement_replicate_count` | integer counts with a declared placement event | Actual phylogenetic replicates, not an intuitive tree-placement grade |
| `condition_differences`, `condition_scale_covariance` | measured numerical differences and an explicitly measured or proposed scale matrix | Actual system descriptors; keep a descriptive similarity separate from a calibrated effect response |
| `correspondence_components`, `component_weights` | values/bounds and explicitly declared numerical weights | Defined conversions of preceding native inputs; multiple tools share fixed component weight |
| `relationship_index`, `target_signed_index` | nullable R in [0,1] and D in [-1,1], with observation scope and bounds | The selected explicit combination; no implicit unknown-value fill |
| `annotation_coordinate`, `coordinate_bounds` | nullable proposed c in [0,1] and optional ordered bounds | The explicitly elected nonnegative conversion after compatible evidence is combined |

Actual assayed subject, supplied target boundaries, experiment identities,
conditions, endpoint meaning, source locations and dependence groups accompany
these cells as provenance and interpretation constraints. They are not numeric
scores themselves. Readers populate cells; they do not choose a hidden scoring
policy or turn citation counts into independent replications.

## What this delivery establishes and what remains

This supplies a joined, numerically checked single-source example, component
formulas, contrasting published cases, explicit missing/dependence handling and
the fields that targeted readers would populate. Independent arithmetic is in
`a105_joined_arithmetic_005/`; the parent also reran the CsiD graph calculation.

Still requiring judgment: the normalized contribution S/B, arithmetic versus
the precisely defined harmonic relevance convention, partial-observation point
versus bounds handling, and the support-only nonnegative projection. The
multi-homolog combination is a separately owned research handoff, not hidden
inside these choices. These are work-review decisions, not runtime gates.

Reader implementation, current nullable annotation-score handling, ten-axis
parameters and full annotation-path verification remain separate W04/W05 work.
The old five-dimensional projector remains retired. No whole-annotation score
or successful scientific run follows from this A105 arithmetic proposal.
