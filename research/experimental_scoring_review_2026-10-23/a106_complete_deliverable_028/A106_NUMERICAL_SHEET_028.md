# A106 perturbation/restoration: consolidated numerical proposal

2026-10-24. Research proposal, not adopted scoring policy.

**Goal:** turn measured perturbation/restoration evidence into one explicitly
calculated A106 contribution for one persistent candidate annotation. This
consolidation supplies the numerical cells, their complete combination, the
population contract, worked examples, source coverage and consequential choices.
It completes this bounded consolidation; it does not mark a ten-sheet checklist
entry complete, claim user acceptance, calibrate biological truth, or implement
a prompt, reader, library, scorer or W05 connection.

This is the current proposal assembled from [row sheet 003](../a106_perturbation_sheet_013/a106_numerical_sheet_003.md),
the [parent's tighter row bounds](../a106_sheet_construction_001/A106_PARENT_NUMERICAL_REVIEW_001.md),
and the [candidate reduction](../a106_candidate_reduction_019/A106_CANDIDATE_REDUCTION_001.md)
with its [final clarifications](../a106_candidate_reduction_019/FINAL_CLARIFICATIONS_002.md).
All prior files remain historical records. The current statement normalizer
below supersedes the historical equal-roster mean in this proposal and in its
[current reader crosswalk](READER_CROSSWALK_028.md).

## Scope and meaning

A106 evaluates the bearing of a selective perturbation and restoration, or a
quantitative necessity challenge, on a particular functional statement. An
experiment on the supplied target or a relevant measured source molecule can
populate it. Investigation starts from supplied sequence, selected file
contents, regions or snippets; a statement may emerge afterward. Neither a
publicly searchable name nor an initial annotation is required.

The scored statement fixes target-material boundaries, endpoint, population,
condition, time origin/window, intended change and predicted direction. A105
owns direct molecular activity evidence; it excludes the perturbation score
constructed here. A phenotype does not by itself establish catalysis. A109
remains deleted; A110 remains separate. No global annotation formula or
investigation-progress score is supplied here.

There are three responsibilities: investigation prompt text; this numerical
sheet; separate targeted readers that populate it. The readers are specified
but unimplemented. This document is not inserted wholesale into a prompt.

`clip(z)=min(1,max(0,z))`. Every number retains its unit, numerator/denominator,
actual observation references and uncertainty. Native measurements, derived
quantities, proposed scoring transformations and synthetic inputs are distinct.
Source labels and experimental descriptions provide provenance, not points.

## Measurement and numerical row

Let `W`, `K`, `R` be reference, perturbed and restored population means of the
same nonnegative ratio-scale endpoint. Its zero has an experimental meaning.
Each arm retains its actual independent biological units, technical readings,
eligibility/exposure denominator, corrections and sampling weights. Examples
include events per eligible population, CFU/volume, survival ratios at one time,
or recovery lag at one declared OD threshold. Logged counts, signed residuals
and arbitrary intensity offsets cannot be treated as these means. Mean log
counts and log mean counts are different quantities.

| Cell | Actual inputs, units and denominator | Calculation / range | What it evaluates |
| --- | --- | --- | --- |
| `W,K,R` | Corrected endpoint values; explicit biological-unit sampling design and denominator; same endpoint units | Declared population mean in each arm, nonnegative | Measured phenotype under each intervention |
| `D` | `W,K` | `W-K`, endpoint units | Perturbation difference |
| `theta` | `W,K`, `W+K>0` | `(W-K)/(W+K)`, [-1,1] | Symmetric proportional effect; invariant to common unit scaling |
| `restoration_fraction_raw` | `W,K,R`, `D!=0` | `(R-K)/D`, unrestricted | Observed reversal fraction, preserving overshoot |
| `r` | Same three means and shared `D` | `clip(1-abs(R-W)/abs(D))`, [0,1] | Return toward the reference phenotype, including an overshoot penalty |
| `C_components[j]` | One nominated unintended quantity in two arms, `x0,x1>=0`, same proportional scale, `max(x0,x1)>0` | `min(x0,x1)/max(x0,x1)`, [0,1] | Agreement of that measured nuisance condition |
| `C` | Distinct applicable `C_components`; dependencies retained | Product of those agreements, [0,1] | Experimental comparability outside the deliberately changed variable |
| `B_pert,B_rest` | Applicable nuisance-only controls/response model; each bound covers its stated nuisance set and interactions | Nonnegative upper bounds, endpoint units, respectively for `W-K` and `R-K` | Magnitude potentially attributable to alternative changes |
| `I_pert,I_rest` | Bounds and the corresponding nonzero contrasts | `clip(1-B_pert/abs(W-K))`; `clip(1-B_rest/abs(R-K))` | Residual attribution after each supplied nuisance bound |
| `I` | Two isolation fractions | `min(I_pert,I_rest)`, [0,1] | The weaker of forward and restoration isolation |
| `M` | A selected, supported molecular relationship below | Explicit route calculation, [0,1] | Source-molecule correspondence to the supplied target |
| `O` | Empirical source/target frequencies on the same scoped joint condition partition | `sum_c min(p_source[c],p_target[c])`, [0,1] | Measured system overlap within the actual statement scope |
| `H` | `M,O` | `M*O`, [0,1] | Molecular and system correspondence |
| `source_effect` (`a`) | Direction `s` and the preceding effect/control cells | `s*theta*r*C*I`, [-1,1] | Signed source-effect product before correspondence |
| `q_point` | The same row's `H,a` | `H*a`, [-1,1] | Signed, correspondence-attenuated row contribution |

`s=+1` means the statement predicts a larger reference endpoint than after
perturbation; `s=-1` predicts a smaller reference endpoint. It is fixed by the
statement before inspecting its result. A nondirectional statement keeps
explicit directional alternatives rather than silently replacing `theta` by its
absolute value. `a` is a factored intermediate, not another overall grade.

The optional diagnostic `B=max(B_pert,B_rest*abs(D)/abs(R-K))` gives
`I=clip(1-B/abs(D))` when both contrasts are nonzero. Its rescaling must use
the same `W,K,R`. Directly measured joint bounds may replace component sums
when their coverage is recorded. A proposed sum `B=sum(b_j)+b_interaction`
requires actual component bounds and a justified triangle bound; unmeasured
interactions cannot be silently set to zero.

`C` and `I` answer different questions. Similar protein amounts do not prove
that an effect is specific; a dosage mismatch does not imply a linear phenotype
change. A source value reused in both calculations remains one shared primitive.
The product `C*I` is a proposed conservative convention and can penalize both
condition mismatch and residual attribution ambiguity arising from that mismatch.

Intended depletion is excluded from `C`. Do not multiply mRNA amount, nominal
inducer and measured protein amount as three copies of the same exposure.
Distinct measured direct effects need distinct scientific reasons. Matching
medium names remain design facts; ratios of categorical codes or Kelvin
temperatures do not measure biological comparability. Nonproportional conditions
require measured responses or matched strata. Unknown consequential mismatches
remain unknown; an empty list does not imply complete matching. A component
may contribute identity 1 only when its inapplicability to this statement is
established explicitly.

Measurement validity precedes these scores. A declared linear relation
`signal=slope*endpoint+intercept` gives `(signal-intercept)/slope`, propagating
all calibration uncertainty. A validated binary detection model gives
`p_true=(p_observed-false_positive_rate)/(sensitivity-false_positive_rate)`
when the denominator is positive and validation populations match. CFU uses
`count*dilution/plated_volume`, then its declared exposure normalization.
Threshold lag uses observed time/OD values and an explicit interpolation or fit.
An impossible calibrated point remains a model failure/interval, not a clipped
valid measurement. Do not apply a second calibration penalty after correcting
the same bias. These are applicable measurement models, not universal factors.

## Perturbation extent and transfer

| Cell | Exact inputs and calculation | Limit |
| --- | --- | --- |
| `residual_amount_fraction` | Perturbed/reference measured amount, same normalization | Amount is not catalytic capacity |
| `residual_activity_fraction` | Perturbed/reference activity relevant to this statement, with matching protein normalization | A different assay does not establish the required residual capacity |
| `P_effective` | `clip(1-residual_capacity_fraction)` for the capacity named by the statement | Amount substitutes only for an amount-removal claim; positive restoration rows report this without automatically multiplying it |
| `mutant_molecule_fraction` | `A_mutant/(A_mutant+A_WT)` in a verified mixture | Does not predict phenotype or oligomer activity without a measured response model |
| `rescue_amount_ratio` | Restored/reference measured amount | Can supply one justified `C` component or an actual dose-response model |

Choose the actual relationship answering the transfer question, not whichever
route scores highest. Other available measurements remain visible but are not
averaged as interchangeable relevance votes.

| Selected route | Molecular correspondence `M` | Exact required evidence |
| --- | --- | --- |
| Verified target identity | 1 within verified boundaries | Supplied material and actual construct identity; labels and unobserved full-length sequence are insufficient |
| Sequence correspondence | `coverage*identity*determinant_agreement` | Coverage = target residues paired to actual assayed nongap residues / declared target-scope length; identity = identical nongap pairs / aligned nongap pairs; determinant agreement = preserved required determinants / all required determinants |
| Structural correspondence | `min(TM_target_normalized,TM_assayed_normalized)*determinant_agreement` | Actual comparison scores, normalization lengths and mapped relevant features; TM already incorporates its length/distance normalization, so no second coverage multiplier |
| Independent measured interchangeability | `clip(1-abs(R_homolog-R_target)/abs(R_target-K))` | Independent amount-controlled replacement measurements in the matched recipient and endpoint, with nonzero denominator |

Retain native alignment scores/E-values and coordinates even though this proposed
sequence route uses explicit residue fractions. Determinants apply only if the
statement depends on an actual defined set. Unknown applicable determinants
are not an empty set, and chemically unsupported substitution grades are not
invented. A genuinely inapplicable determinant term contributes 1 with its reason.
Replacement data already used as the restoration experiment cannot also supply
an independent transfer multiplier. These routes are not sequence-only.

For `O`, both empirical frequency vectors sum to one over the same states and
have their measured denominators. State boundaries are set by the question,
not by favorable overlap. A statement conditional on starvation compares
systems within starvation; the fraction of all time spent starving is not an
additional penalty. Verified identity of the scoped systems gives `O=1`.
Organism names or absent measurements cannot supply an intuitive substitute.

## Quantitative necessity challenge

This separate mode challenges a statement that actually entails a quantitative
minimum effect. It does not turn a nonsignificant p-value, uncalibrated band or
missing result into evidence that a protein has no role.

```
deficit = clip(theta_required - s*theta)
I_cancel = clip(1 - B_cancel/D_required)
a = -deficit * P_effective * C * I_cancel
q_point = H * a
```

`theta_required` is in (0,1]; `D_required>0` has endpoint units and expresses
the same claimed minimum. Retain the source of the minimum and its endpoint
translation. Where the claim supplies reference/required perturbed values,
`theta_required=s*(W_required-K_required)/(W_required+K_required)` and
`D_required=abs(W_required-K_required)` express that translation. Any shared
or uncertain reference stays in the same joint model. For a 50% loss from a
reference of 100, `K_required=50`, `D_required=50`, `theta_required=1/3`.

`B_cancel` bounds nuisance changes capable of hiding that required effect, on
the same endpoint scale. `P_effective` measures the actual relevant molecular
perturbation. The capped deficit is a proposed saturation convention; the
necessity row lies in [-1,0]. A positive-effect and necessity calculation from
the same experiment are not two independent contributions to the same statement.
Choose its estimand; retain other calculations as linked diagnostics or use
them for genuinely different stated meanings with shared dependencies intact.

## Row to statement to candidate

Representations of one observation share an identity. Technical measurements
remain inside their biological unit. Independent biological repetitions of
the same sampling design update that group's means, covariance and bounds;
they do not add report votes. Distinct assay designs addressing one exact
statement form its groups. Shared controls/calibration/data remain linked even
across groups and statements. Equal numbers alone establish neither identity
nor independence.

Use one declared primary endpoint per group and statement. Complementary
readouts normally populate a control, observation model or transfer cell.
When the actual scientific estimand is a declared endpoint/population mean,
retain fixed nonnegative weights `w_j` summing to one and their denominators:

```
q_g = sum_j(w_j*q_j)
H_g = sum_j(w_j*H_j)
a_g = q_g/H_g, if H_g>0
```

Equal endpoint means use `w_j=1/J`. If all `H_j=0`, `H_g=q_g=0` and `a_g`
is unidentified. These are composite estimands, not optional score optimizers.
If all endpoints are required, use required statements instead of averaging.

For statement `i`, using its unique actually observed group roster:

```
T_i = sum_g H_ig
d_i = max(1, T_i)
positive_numerator_i = sum_g max(q_point_ig, 0)
negative_numerator_i = sum_g max(-q_point_ig, 0)
N_i = positive_numerator_i - negative_numerator_i = sum_g(H_ig*a_ig)
Q_i_point = N_i/d_i
consistency_i = abs(N_i)/(positive_numerator_i+negative_numerator_i)
                when that denominator is positive
```

The same `H` occurs in numerator and denominator. `d` is a dimensionless
normalizer, never biological sample size. A single group retains `Q=q_point`.
An exact `H=0` addition changes neither sum. When `T<=1`, contributions
accumulate; when `T>1`, the result is an `H`-weighted mean of `a`.
Thus `abs(Q)<=min(T,1)<=1`. Consistency is a diagnostic, not a second multiplier.

**Consequential proposed choice:** one distinct group with `H=.1,a=.8`
contributes `.08`; ten genuinely distinct such groups contribute `.8`.
This is accumulation under a normalization convention, not evidence that
transfer uncertainty disappears. Shared uncertainty is still shared; the
normalizer does not estimate an effective independent sample count. A weak
positive assay can lower a normalized positive mean. A negative addition
lowers a positive statement point while its previous operands are held fixed;
new observations can separately change an actual fitted model.

The candidate declares canonical statement leaves and its actual meaning:

```
F(leaf i) = Q_i_point
F(all_of children) = min(F(child) for child in children)
F(any_of children) = max(F(child) for child in children)
```

All required statements use `all_of`; genuinely sufficient alternatives for
the same assertion use `any_of`. Different assays are not alternatives in this
expression. Competing candidate annotations remain separate. Duplicated leaves
and declared synonyms retain the same leaf; min/max repetition and absorption
do not create credit. Empty operators mean unspecified meaning, not perfect
support. An annotation with no A106 question returns `no_axis_question`.

## Joint uncertainty, missingness and one final reduction

Every occurrence of a primitive measurement, control, calibration and
correspondence relation refers to the same variable. Source SD, SEM, confidence
intervals, deterministic validation bounds, rounding intervals, censoring and
mathematical domains keep their meanings. Marginal 95% intervals do not imply
joint 95% coverage. Unknown covariance is not zero.

The complete candidate function is evaluated over a declared joint admissible
set. Row intervals are diagnostics; already reduced row values are never
pooled. One valid deterministic fallback is:

1. Obtain row `a,H` bounds from the actual joint model, or conservative interval
   arithmetic on the defined row formulas. Standard signed interval products,
   sums, division with nonzero denominator, absolute values, minima and clips
   give outer bounds. If a contrast interval reaches zero, retain the singular
   diagnostic and use the bounded factor domain `[0,1]` instead of dividing
   by zero. Unknown source-effect domains are `[-1,1]` for restoration and
   `[-1,0]` for necessity; unknown `H` is `[0,1]`. These domains are not data.
2. For a statement's rectangular `a,H` enclosure, lower/upper extrema occur
   with all `a` at lower/upper endpoints respectively, because its fraction
   is nondecreasing in every `a` for `H>=0`.
3. For each fixed `a` vector, evaluate every `H`-box vertex **and** every
   feasible intersection of `sum(H)=1` with a box edge. An edge fixes all but
   one `H` at a bound; the remaining coordinate is determined by the equation.
   The minimum and maximum are exact for this relaxed box. Each side is linear
   or linear-fractional with positive denominator; the boundary vertices matter.
4. Collapse exact reused `H` variables first. If `n_m` groups share `H_m`, use
   numerator `sum_m H_m*sum_(g in m) a_g` and denominator
   `max(1,sum_m n_m*H_m)`. Edge intersections use `sum_m n_m*H_m=1`.
   Nonidentical `H` expressions sharing an upstream factor keep that factor;
   relaxing them to containing boxes is explicit and yields an outer enclosure.
5. Evaluate the candidate min/max expression at all leaf lower bounds and at
   all upper bounds. Monotonicity gives outer bounds with shared data. A
   complete finite joint-scenario enumeration or a proved analytic joint
   extremum can tighten these; method and relaxed constraints are recorded.

For identified nominal inputs and a valid candidate interval `[F_L,F_U]`:

```
nearest_zero([L,U]) = L if L>0; U if U<0; 0 otherwise
signed_A106 = nearest_zero([F_L,F_U])
A106_coordinate = max(0, signed_A106)
coordinate_lower = max(0,F_L)
coordinate_upper = max(0,F_U)
```

The nearest-to-zero and positive-part operations occur once, at the candidate
boundary. Keep nominal `F_point`, the interval and the signed result separately.
These are bounded scoring quantities, not posterior function probabilities.

| Situation | Current numerical treatment |
| --- | --- |
| Required nominal operand unavailable | Point and coordinate remain null unless algebraically identified; retain mathematical image bounds and missing reason |
| Known interval crosses/touches zero, identified point | Resolved signed contribution and coordinate are 0; retain point/interval and uncertainty meaning |
| Missing inputs but entire candidate image nonpositive | Coordinate is identified as 0; signed value remains null unless itself identified |
| Empty observed roster for a required statement | Point null, domain [-1,1], `no_data`; do not invent unperformed rows |
| Exact `H=0` with a valid bounded source-effect domain | Row contribution is algebraically 0; unknown source cells remain unknown; an invalid measurement model is not repaired |
| Exact `W=K`, `W+K>0`, valid bounded factors | `theta=0`; source effect is algebraically 0 while undefined restoration/isolation ratios remain undefined |
| `R=K`, nonzero `D`, otherwise valid bounded factors | `r=0`; bounded contribution 0, restoration-isolation ratio undefined |
| `W+K=0` | Effect ratio undefined; no functional absence inferred |
| Zero versus positive unintended amount | `C_j=0` if scientifically applicable; two zeros have undefined ratio |
| `K<LOD`, actual calibrated `[0,LOD]`, known `W>0` | `theta` lies in `[(W-LOD)/(W+LOD),1]`; point stays censored unless supplied by a justified model |
| Nondetection without a detection limit or both arms nondetected | Missing/censored measurements; no exact zero or absence-of-function claim |
| Relevant measured `q=0,H>0` | May enlarge `d` and lower positive support; distinct from `H=0` and missing results |
| Conflicting source values | Alternatives under one observation identity; no averaging without a model and no extra group |

When a missing `a` has known `H>0`, that `H` still enters `d` and its bounded
`H*a` stays in `N`; do not renormalize a favorable known subset. An unknown `H`
enters both places as one unknown variable. Algebraic zeroes are identities on
valid domains, not invented observations or a general conversion of null to 0.

## Reviewable choices and deliverable boundary

The proposed choices are the symmetric contrast, restoration-to-reference
penalty, product of distinct comparability ratios, weakest-comparison isolation,
their joint use, the explicit transfer routes and context overlap, bounded
necessity deficit, floor-one statement normalization, min/max candidate meaning,
and nearest-to-zero uncertainty treatment. Their arithmetic is defined; their
biological calibration and user adoption are not claimed. No A105 pooling rule
is adopted by this A106 proposal.

The [worked examples](WORKED_EXAMPLES_028.md) print complete synthetic positive,
contrary, missing, replication and necessity calculations. The [source and
completion assessment](SOURCE_COVERAGE_AND_COMPLETION_028.md) distinguishes
inherited published component coverage from this worker's mathematical reading
and identifies every retained source-specific unfillable operand. The
[printable handoff](PRINTABLE_HANDOFF_028.md) is self-contained for conversation.

One persistent candidate receives new evidence/meaning snapshots. Recompute
from current unique observations; retain previous snapshots without summing or
maximizing historical scores. Scope qualification is visible and cannot be
reported as new support for the old broader claim. Useful corrections may lower
annotation support while advancing investigation. Nothing here changes episode
credit, continuation, execution or scientific ownership.
