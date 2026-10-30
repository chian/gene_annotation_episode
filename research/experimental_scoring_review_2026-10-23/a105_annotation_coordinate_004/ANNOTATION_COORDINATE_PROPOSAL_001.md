# A105 signed evidence → annotation coordinate: proposal 001

2026-10-23. **Unadopted numerical-interface proposal.** This work changes no
production scorer, reader, prompt, library entry, run, controller, or permanent
record. All ten sheets remain unfinished. Every numerical assay example below
is synthetic. No primary paper or paper-specific evidence packet was reviewed.

The smallest zero-based handoff is an **explicit one-sided support projection**
of the completed signed evidence calculation. It is not a lossless conversion:
the scalar necessarily loses the distinction between equal fits and different
amounts of contrary evidence. The sheet must retain that distinction. Whether
the user wants this support-only coordinate is a real unresolved design choice,
not something the existing code already decides.

## What the current code actually accepts

The five old dimensions and their categorical projector are retired. The live
`credit.py` has `AXES=()`, no default policy, and retired `CreditPolicy` and
`project_credit` entry points that raise an explicit error. Neither a 100-point
scale nor the former scope-cell/account aggregation is currently installed.

The retained arithmetic is only

\[
H(c;w,\epsilon)=
\frac{\prod_{k\in K}[\epsilon+(1-\epsilon)c_k]^{w_k}
      -\epsilon^{\sum_k w_k}}
     {1-\epsilon^{\sum_k w_k}}.
\]

The caller must explicitly supply unique axes K, nonnegative finite weights w
with at least one positive weight, and `0 < epsilon < 1`. Every axis named in
that policy requires an explicit finite `c_k in [0,1]`, including axes assigned
weight zero. Missing keys, null, negative coordinates and nonfinite values are
rejected. The helper does not calculate a component, choose ten-axis weights,
deduplicate experiments, identify a claim, or define a probability.

| Actual inspected boundary | Current behavior and implication |
|---|---|
| `evidence_axis_contracts.native_metric_facts` | Copies actual received typed numbers; unbound extractors/missing measurements remain unavailable. It does not produce an A105 coordinate. |
| `evidence_axis_scoring.score_axis` and its complete helper path | Preserves native units/bounds, merges representations by original experiment/measurement identity, reports conflicting representations, withdraws categorical routes, and always returns `annotation_aggregate=None`. No A105→H mapper exists here. |
| `credit.HypervolumeParameters`, `softened_hypervolume`, and `evidence_geometry._number` | Enforce the explicit policy and the [0,1] coordinate domain above. They supply arithmetic only. |
| `default_scientific_binding.bind_default_science`; `investigation_policy.create_policy` | Bind received-finding progress separately; leave annotation scoring unbound while the numerical sheets are unfinished. |
| `case_execution.PolicyBindings`, `_load_policy`, `prepared_case_bindings`, `run_prepared_case` | An optional annotation scorer has its own declared definition and saved source/parameters, then passes through to the runtime. Case bindings require both callable and nonempty definition. |
| `runtime.Workflow.projection_view`, `annotation_context` | Call the explicitly injected scorer on a store snapshot and fixed scope. A scalar, object `.credit`, or mapping `credit` is converted to a finite float. Runtime itself does not enforce [0,1]; that stricter domain belongs to the retained H helper. An optional `axis_components` mapping becomes `annotation_evidence_vector`. |
| `runtime.DecisionSource.next`, `annotation_score_read`, `projection_read` | Show/read that separate annotation channel. The score is not the controller's progress observation. A detail read invokes the same scorer's declared `read_details`, without a numerical fallback. |
| `runtime.report_sources`, `facts`, `redeliver` | A bound annotation score is a number in the closing facts; redelivery reuses the saved facts. It does not recompute the old child result under new evidence. |
| `runtime.assemble_workflow`, `run_workflow`, `_run_bound_workflow`; `independent_execution._standard_bindings`, `_check_bindings` | Retain the selected annotation executable/definition through assembly and original-binding checks. A finished run returns its saved summary. An unbound current scorer yields `annotation_score_status=unavailable_no_scorer_bound`. |
| `scientific_support_metadata.annotation_policy_routes` | Returns unavailable rather than inferring a numeric axis from an observation type or an arbitrary callable. |

**Missing-data boundary:** nullable sheet cells are possible; a nullable runtime
score is not currently supported. `projection_view` would call `float(None)`.
The separate `unavailable_annotation_score()` helper is not consumed by that
runtime path. A completed W05 must address availability in its receiving
contracts if it installs a scorer that can encounter unknown axes. This proposal
does not solve that by returning zero, omitting unknown axes, or changing H.

## Exact proposed numerical handoff

The evidence scope is a particular molecular statement about the actual supplied
target and conditions. It may emerge during investigation. It is not a required
starting candidate or a publicly searchable gene name. A105 concerns measured
conversion, transport or binding. Perturbation/restoration remains A106.

The source sheet and contribution proposal already define the component path:

\[
a=\frac{y_{sample}-y_{blank}-y_{contaminant}}
        {recovery\;protein\_amount\;condition\_response},\qquad
V_\theta=J\Sigma J^T+V_{distinct\ residual}.
\]

The condition-response terms assess comparability outside the deliberately
changed variable. The contaminating/background terms assess isolation. They
stay separate cells even where both enter this equation. Native magnitude,
units, uncertainty, covariance and remaining bias limitations accompany the
calculation; no second generic reliability/applicability multiplier is added.

For genuinely compatible observation blocks about the same declared claim,
first combine the actual joint likelihood, retaining shared nuisance parameters:

\[
\ell_{joint}=\sum_b\ell_b\quad\text{only when that factorization is justified},
\qquad S=\sup_{H_+}\ell_{joint}-\sup_{H_-}\ell_{joint},
\qquad B=\tanh(S/2).
\]

`S` is a signed profile-fit contrast, not a Bayes factor or annotation
probability. `B` is its normalized best-fit difference, not a probability.
Maximize **after** combining the measurements. Do not sum independently profiled
S values, average activity and specificity summaries as separate experiments,
or combine bounded B values as independent probability estimates.

For known joint normal covariance V and a common signed scalar effect:

\[
W=\mathbf1^TV^{-1}\mathbf1,\quad
\hat\theta=\frac{\mathbf1^TV^{-1}y}{W},\quad
V_{pooled}=1/W,\quad
S=\operatorname{sign}(\hat\theta)\hat\theta^2/(2V_{pooled}).
\]

Finite-sample, censored and physically nonnegative-activity cases retain the
contribution proposal's own likelihood models. A physically impossible negative
rate is not manufactured to obtain a signed score. Unknown variance or an
unquantified applicable bias is not silently set to zero.

### Proposal F: explicitly zero-based positive-support coordinate

For a completed, declared target-scoped signed index D, propose

\[
c_{A105}=
\begin{cases}
\text{unknown},&D\text{ is unknown},\\
D,&D>0,\\
0,&D\le0.
\end{cases}
\]

For the likelihood route, `D=B_target`. This is exactly `max(0,B_target)` **as an
explicit proposed boundary policy**. It does not overwrite the negative contrast
or B in the sheet, and it is not applied to individual observations before
pooling. The coordinate's meaning is “positive directional support margin for
this stated molecular claim under the declared model.” It is not the chance
that the annotation is true, a measurement of activity size, or an experimental
reliability grade.

The implications are deliberate and must be reviewed:

- A known zero gives `c=0`; unknown gives null. A negative D remains negative
  in the evidence sheet while the positive-support coordinate is zero.
- New contrary compatible observations enter the joint fit and can lower a
  previously positive c. There is no running maximum and no discarded negative
  experiment. Once c is zero, increasingly negative evidence cannot lower this
  scalar further; S/D still records the increased opposition.
- All other H operands remain unchanged. H is monotone in each positive-weight
  coordinate, so lowering c lowers H. The softened product can stay positive
  when A105 is zero and other axes have support. Making A105 a veto would be a
  different global formula/acceptance rule and is not proposed here.
- Strongly measured preference can approach c=1 even if the preference is tiny.
  That applies only to the exact directional claim. Native magnitude cannot be
  silently enlarged or the claim widened to physiological function.

This floor is the unresolved human choice, not an assertion that clipping has
already been authorized. It is not hidden inside a reader.

There is a simple reason the choice cannot be avoided with another smooth
zero-based transform. If a nondecreasing `f: R→[0,1]` has `f(0)=0`, then for
every `s<0`, `0<=f(s)<=f(0)=0`. Every such scalar loses degrees of opposition
below zero. Retaining all negative ordering requires a positive zero-contrast
anchor, a signed/multicomponent boundary, or another stated change of meaning.

### A mathematically explicit alternative with a positive anchor

For comparison only, an unadopted anchored coordinate convention is

\[
c_\alpha(S)=\frac{\alpha e^S}{1-\alpha+\alpha e^S},\quad 0<\alpha<1.
\]

It preserves the order of negative and positive S, but assigns `c_alpha(0)=alpha`
to a measured equal-fit result. Unknown S still remains unknown. Alpha is a
declared coordinate anchor, **not** an inferred prior; the profile ratio does
not acquire Bayesian meaning through this formula. No 0.5 default is proposed.
With the explicitly arbitrary illustrative anchor `alpha=0.2`, S values
`-2.078347031, 0, +2.078347031` give `0.030335209, 0.2, 0.666423398`.
That positive baseline is the price of retaining negative ordering within one
monotone nonnegative coordinate. It is extra scoring convention, so Proposal F
is smaller if the intended coordinate means zero-based positive support.

Changing H to take signed values, adding an opposing axis, or using a posterior
probability would require different global inputs or a scientifically specified
probabilistic model. None is silently adopted here.

## Source-to-target correspondence: two explicitly different routes

The relevance worker owns these components. The interface consumes its outputs
without inventing another overall grade.

1. **Measured/fitted response route.** Use
   `theta_target=h(theta_source, bridge_operands)` and its complete covariance
   or likelihood. Form S and B on that target quantity once. For positive
   activities, `a_target=a_source*product(r_j)` where supported; for specificity,
   `log(aA/aB)_target=log(aA/aB)_source+sum(dA_j-dB_j)`. Shared factors may cancel.
   Do not multiply B again by a precision fraction or the same correspondence
   measurements. The mapping can alter the magnitude and reverse specificity.
2. **Native-component score convention where no calibrated response exists.**
   The relevance proposal defines numerical `r_j in [0,1]`, explicit family
   weights, `R_available=sum_observed(w_j*r_j)/sum_observed(w_j)`, and
   `D_conventional=R_available*B_source`. If elected, Proposal F supplies
   `c=max(0,D_conventional)`. This is a correspondence-adjusted **conventional
   support index**, not target likelihood, predicted target rate or probability.
   It permits a conditional number for an ordinary novel target with measured
   correspondence and no target assay. Absence of calibration alone is not a
   universal veto on that explicit alternative.

These are alternative routes for the same evidence chain, not independent
confirmations. Unknown correspondence makes the target result unknown only
when neither a response mapping nor the elected numerical convention supplies
it. The source-scoped S/B remains usable. No measured correspondence at all
means no invented `R=1`. A compound inference requiring a different endpoint
cannot be repaired by a large similarity score.

Checked synthetic correspondence example, with the relevance worker's proposed
equal family weights:

| Quantity | Calculation | Result |
|---|---|---:|
| Complete R | mean(480/620, 0.85, 8/10, 85/100, exp(-0.37)) | 0.792985576 |
| Source B | tanh(log(19)/2) | 0.900000000 |
| Conventional signed target index | R × 0.9 | +0.713687018 |
| Proposed F coordinate | positive part of the preceding signed index | 0.713687018 |
| Reversed signed index from the same source direction reversal | R × (-0.9) | -0.713687018 |
| Reversed F coordinate | explicit positive-support floor; negative index retained | 0 |
| Missing evolutionary family: conditional R | mean of the four available values | 0.778731970 |
| Conditional F coordinate | 0.9 × conditional R | 0.700858773 |
| Observed family-weight fraction | 4/5 | 0.8 |
| Identification bounds for the hypothetical complete coordinate | 0.9 × [sum_observed(r)/5, (sum_observed(r)+1)/5] | [0.560687018, 0.740687018] |

Missing-family bounds are not confidence intervals and their midpoint is not a
score. A conditional available-family point and a complete-family point have
different meanings. The user must choose whether the conditional point is the
declared operand or whether only the bounds are retained. Under a bounds-only
choice, the current scalar H/runtime channel has no nullable/interval handoff.
One can evaluate H at interval endpoints as sensitivity results without calling
either endpoint the observed score.

For multiple distinct assayed proteins with different uncalibrated R values,
this multiplication does **not** provide a combined target likelihood. Keep
their signed conventional indexes separate unless a further explicitly elected
combination is supplied. A source-level joint fit followed by one common R is
defined when that same relationship applies to the whole source inference.
Do not back-convert `R*B` into S and claim an independent likelihood contribution.
Unknown relations or dependencies cannot be resolved by taking the largest
positive source. Cross-axis reuse of a correspondence metric must likewise be
declared in W05; the retained H itself asserts no statistical independence.

## Checked contrasting numerical examples

The table uses known-normal signed contrasts, natural boundary zero, and
`V=0.11124225` from the parent's **synthetic** reliability example. A105's input
components are therefore actual numbers in the proposed calculation, not
categories. The `H_fixture` column uses the **explicitly synthetic two-axis**
policy `w_A105=w_other=1`, `epsilon=0.2`, `c_other=0.6`, so

\[
H_{fixture}=0.1+\frac{17}{30}c_{A105}.
\]

It is an arithmetic demonstration of the unchanged formula, not an adopted
ten-axis weighting, a real gene score, or reinstatement of a 100-point scale.

| Case | Actual contrast input and resulting uncertainty | Joint S | Signed B | Proposal F c | H_fixture |
|---|---|---:|---:|---:|---:|
| Unknown evidence | No usable contrast/error model | unknown | unknown | unknown | unknown |
| Measured zero contrast | 0, variance V | 0 | 0 | 0 | 0.100000000 |
| Positive contrast | +0.68, variance V | +2.078347031 | +0.777561486 | 0.777561486 | 0.540618175 |
| Reversed specificity | -0.68, variance V | -2.078347031 | -0.777561486 | 0 | 0.100000000 |
| Conflicting compatible observations | +0.68 and -0.34, independent, each variance V; pooled +0.17, variance V/2 | +0.259793379 | +0.129170998 | 0.129170998 | 0.173196899 |
| Equal opposing observations | +0.68 and -0.68, independent, each variance V; pooled 0, variance V/2 | 0 | 0 | 0 | 0.100000000 |
| Duplicate return | Same original +0.68 measurement returned a second time; still one observation of variance V | +2.078347031 | +0.777561486 | 0.777561486 | 0.540618175 |
| Independent confirmation | +0.68 and +0.78, each variance V; pooled 0.73, variance V/2 | +4.790446076 | +0.983519432 | 0.983519432 | 0.657327678 |
| Shared calibration/preparation | Same two values, covariance 0.08564225; pooled variance 0.09844225 | +2.706663044 | +0.874837344 | 0.874837344 | 0.595741161 |
| Sensitive nondetection joins positive result | One +0.68 observation plus independent `Y<0.1`, detector SD 0.2; fitted nonnegative activity 0.147958501 | +0.271726302 | +0.135033321 | 0.135033321 | 0.176518882 |

“Compatible” here means the stated same-endpoint/common-effect model is being
evaluated. Equal opposition has residual `Q=8.313388124`; unequal opposition
has `Q=4.676280820`, each with one residual degree of freedom under the assumed
known-normal model. These diagnostics retain the disagreement: zero directional
score does not mean both experiments measured no effect. If the common-effect
model is not defensible, preserve the separate conditions and conditional
calculations; do not present the pooled result as unconditional. Q is not an
additional arbitrary multiplier. No diagnostic creates a runtime gate.

An exact duplicate is represented once, based on established experiment and
measurement identity. Equal numerical values do not establish duplication;
different representation IDs do not establish independence. Conflicting values
for one original measurement are a data-representation conflict, not two
independent biological results to average. Repeated delivery changes neither
coordinate nor H and creates no synthetic controller observation here.

For the nondetection row,
`ell(a)=-(0.68-a)^2/(2V)+log(Phi((0.1-a)/0.2))`, with `a>=0`, and
`S=max_a ell(a)-ell(0)`. The limit is not replaced by zero or half its value.
The new constraint lowers support while potentially advancing investigation.

## A compound annotation differs from one positive assay

The annotation records can contain coherent sets of multiple typed hypotheses;
their presence does not supply a numerical rule for combining those claims.
An axis is not a hypothesis ID. The A105 handoff needs the molecular claim it
actually evaluates, its target/material scope and its relationship to the
annotation being scored. Those definitions accompany the numerical cells.

If an annotation's molecular claim requires both `theta_1>0` and `theta_2>0`,
use the actual conjunction and its complement in the joint data model:

\[
H_+=\{\theta_1>0\ \land\ \theta_2>0\},\qquad
H_-=\{\theta_1\le0\ \lor\ \theta_2\le0\}.
\]

For the supplied synthetic independent unit-variance observations `(2,3)`,
`S=min(2²/2,3²/2)=2`, `B=c=0.761594156`. For `(-2,3)`, `S=-2`,
`B=-0.761594156`, and Proposal F c is zero. Adding the two favorable individual
S values or multiplying their bounded scores answers a different question.
Covariance changes the constrained fit and must be retained.

If only the first endpoint is measured at `2 ± 1` standard uncertainty, the
**narrower claim** has `S=2`, `B=c=0.761594156`; the broader conjunction's
coordinate is unknown under this proposed missing-endpoint contract. Do not
average the observed endpoint alone and label it the compound result. The
unidentified second parameter could make a formal supremum comparison equal
without experimental evidence; that algebraic equality is not a measured zero.

A binding experiment can score binding under its tested conditions. It does
not alone score activation, chemical conversion or a native physiological role.
For an annotation containing claims from several axes, A105 contributes only
its declared molecular portion; the annotation-wide combination remains W05's
explicit responsibility. This does not impose a universal list of assays or a
mandatory experimental sequence.

Likewise, `log(ratio)=0.001`, `SE=0.00001` gives `S=5000` and a rounded `B=1`,
but the native ratio is only `1.001000500`, a `0.100050017%` preference. It supports
the precisely scoped sign statement. For a **separate synthetic claim** that
the ratio exceeds two, the contrast becomes `0.001-log(2)=-0.692147181` and
`S=-2395338597.785407`; c is zero. Twofold is not proposed as a universal
threshold. A scientifically consequential magnitude needs the actual claim's
numerical boundary or model, not an unlabeled significance-to-importance jump.

## Exact cells and their separate populating responsibilities

This is an interface schema proposal, not implementation of a reader.

| Sheet cell | Meaning/range | Population responsibility |
|---|---|---|
| `effect_estimate`, `effect_unit`, `effect_covariance` | Native corrected molecular contrast and uncertainty; zero distinct from unknown | Assay/dataset reader and declared deterministic correction/propagation functions |
| `comparability_components`, `isolation_components` | Measured corrections, variances/covariances or explicit bias bounds, kept separately | The corresponding targeted reliability readers; no overall categorical grade |
| `claim_boundary`, `claim_region_parameters` | Explicit numerical operands defining the particular comparison; no default consequential rate | Declared scoped claim/model, with known endpoint relationships |
| `target_response_operands` | h operands and covariance, where supported | Relevance sheet's measured/fitted mapping |
| `correspondence_components`, `correspondence_weights` | Explicit normalized measurements and proposed weights, when that convention is elected | Relevance sheet's exact numerical functions; not a target-rate estimator |
| `profile_log_ratio` | S in nats, including negative values or null | Deterministic joint/profile calculation after deduplication and dependency modeling |
| `signed_index` | B or explicitly tagged conventional D, in [-1,1] or null | `tanh(S/2)` or declared `R*B`; cannot interchange their likelihood meanings |
| `coordinate_mapping` | Declared version of Proposal F, anchored alternative, or another reviewed rule | Caller-owned scoring definition; not reader choice |
| `coordinate_value` | c in [0,1], or null for unknown/bounds-only output | Deterministic elected map, after all compatible evidence is combined |
| `coordinate_bounds` | Optional ordered [lower,upper], with bound type and conditional scope | Image of the actual allowed parameter/index set; never its automatic midpoint |
| `heterogeneity`, `conditional_assumptions`, `missing_operands` | Model diagnostic and the precise limits of the computed number | Native/error model plus targeted extraction; not invented numeric penalties |

Original measurement identity, actual assayed subject, target material/scope,
claim meaning, conditions and route identity are supporting records rather than
scores. Availability states must distinguish observed zero, equal fits,
opposition, missing data, representation conflict, partial-family convention
and bounds-only output. The final H input is only the completed numerical
coordinate with its declared meaning; the accompanying sheet remains available
for inspection. None of this sheet belongs wholesale in the investigation TASK.

## Choices still requiring human judgment, and constraints already fixed

Already constrained by code/user direction: the removed five-axis projector
must remain retired; H's explicit numerical boundary/formula is retained;
unknown is not zero; signed/raw measurements and their units survive; source
and target scopes differ; compatible contrary observations can reduce support;
shared evidence is not duplicated; progress/continuation credit is separate;
readers populate the sheet and do not choose hidden scoring rules.

Actual unresolved choices:

1. Elect Proposal F's support-only floor, a positive-anchor convention, or a
   different explicit coordinate meaning. No choice has been adopted here.
2. Elect S/B's proposed normalization and the precise molecular comparison
   semantics; a measured tiny effect is not automatically substantial function.
3. Elect the native-component correspondence convention, its numerical weights
   and normalizations, and conditional points versus bounds where calibration
   is absent. Native correspondence can produce a proposed number without
   claiming measured target activity.
4. Supply each real case's actual model, error/covariance/censoring inputs and
   scientifically defensible compound-claim relationship. Synthetic arithmetic
   does not identify these empirical operands.
5. In W05, define the ten-axis parameters and annotation scope/claim assembly,
   field bindings, and nullable availability handling. A completed A105 value
   alone cannot determine a full score while other required H coordinates are
   unknown. Do not reuse the historical account rule or silently remove axes.

The checker executed 15 synthetic cases and 11 expected existing-boundary
rejections, plus unit/sign, duplication, range, censored-fit and unchanged-H
assertions. Details and exact inspected source paths are in
`INSPECTION_AND_AUTHORITY_001.md`; all operands/results are in
`arithmetic_001.json`. This verifies arithmetic and selected in-memory interface
behavior only. It does not finish A105, establish real-assay model validity,
implement any reader, or verify an executed scientific consumer path.
