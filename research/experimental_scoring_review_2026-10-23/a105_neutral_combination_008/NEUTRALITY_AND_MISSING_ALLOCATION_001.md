# A105: neutral addition and the exact missing allocation input

2026-10-23. **Source-free mathematical result; all numbers are synthetic.**
No paper or paper-specific packet was inspected, no formula was adopted, and no
production scorer, reader, prompt, saved run or old record changed. Completion
remains **0/10**. The user's cumulative-versus-average choice is unanswered.

The 007 denominator defect has a precise repair: **keep numerical source
allocations fixed when genuinely irrelevant information is appended**. The
current S/R inputs do not determine those allocations. This document gives one
conditional calculation and a concrete nonidentifiability result, not another
menu of combinations or a claim that the A105 calculation is settled.

For a declared allocation vector a, use

```
B_i = tanh(S_i/2)
D_i = R_i B_i
q_i = atanh(D_i)
Q = sum_i a_i q_i             a_i >= 0, finite, explicitly supplied
K = tanh(Q)
c = max(0,K)
```

There is **no division by a current roster size or current sum of weights**.
All opposition enters Q before projection. K is retained when c is zero.
This remains a conventional index, not target activity, a likelihood ratio,
functional probability, calibrated directional support, or an uncertainty
estimate. The c projection also remains an unadopted proposal.

## Data to numerical operands

Define the same molecular endpoint, direction, comparison boundary, material
span, state and condition scope for every source relationship. These can emerge
from investigation of supplied sequence/file material; no initial annotation
or publicly searchable name is required.

**S_i:** canonicalize actual experimental observations and fit the source's
joint model before computing its directional score. In the known-normal
fixture, `S_i=sign(ybar_i)*ybar_i^2/(2 V_i)`. Comparability and effect isolation
remain distinct measured correction and uncertainty inputs to that source
model. A new source allocation does not compensate for a missing correction.
Shared controls and denominators remain shared variables. A second optimized
score from the same observations is not another source contribution.

**R_i:** the existing native-measurement convention supplies
`sum_observed(w_ij r_ij)/sum_observed(w_ij)`, with its actual normalized
measurements, family weights, observed basis and full-family bounds retained.
It measures the stated correspondence, not a predicted response or probability.
Missing applicable families are not zero. The chosen available/full basis and
native normalizations remain unresolved policy inputs inherited from 003.

**a_i:** a dimensionless, fixed numerical scoring allocation keyed to the
canonical source/state identity. It comes from an explicitly declared allocation
policy or table, **not** from a measured covariance, a paper count, S, R, a clade
label or a favorable observed sign. The smallest new required input is the
complete numerical vector a, or an explicitly constrained allowed set A of
such vectors. No generic reader can infer that normative input from the current
native measurements. Every result includes its allocation table. A new table
is a new conditional calculation, not a rewrite of completed history.

The original H1/H2 fixture provides concrete native operands:

| Input | H1 | H2 |
|---|---:|---:|
| Corrected measured log ratios; known variances | 2, 2; 1, 1; zero covariance explicitly supplied | -2; 1 |
| Native activity numerators / denominator | exp(2)/1 twice | exp(-2)/1 |
| Joint source mean; variance | 2; 1/2 | -2; 1 |
| Source S; B | 4; .964027580 | -2; -.761594156 |
| Sequence: compatible local raw pair/self scores | 240/300/300: `2*240/600=.8` | 90/300/300: .3 |
| Structure: native two-direction TM scores | min(.92,.90)=.9 | min(.45,.40)=.4 |
| Predefined, fully observed functional sites | 7/10=.7 | 2/10=.2 |
| Supporting/eligible tree replicates | 60/100=.6 | 10/100=.1 |
| Declared condition descriptor | Both 25 C; scale 100 C²; exp(0)=1 | Same operands, 1 |
| R, five declared family weights all 1 | .8 | .4 |
| D | .771222064060654 | -.304637662382306 |
| q | 1.023336598989095 | -.314623784528648 |

The activity units are the same positive molecular rate unit, making the log
ratios dimensionless; variances have squared log-ratio units. Only X versus Y
is deliberately varied. The synthetic comparability correction is exactly
zero with zero uncertainty; isolation fractions are exactly f_X=f_Y=1 with
zero correction uncertainty. These are fixture assumptions, not real-data
defaults. The sequence normalization uses 003's supported local-score
conditions. Descriptor equality does not establish complete system identity.

## Finite correction and numerical nonidentifiability

The following two numerical tables are **completions of the missing design
input used to prove nonidentifiability**, not two new recommendations:

| Declared fixed allocation | Q | K=c |
|---|---:|---:|
| a=(1,1) | .708712814460447 | .609869037957144 |
| a=(1/2,1/2) | .354356407230224 | .340233352998679 |

Both use exactly the same S/R data. If the allowed set is explicitly
`A={(1,1),(1/2,1/2)}`, the exact output set is
`K,c in {.340233352998679,.609869037957144}`; its interval hull is not a claim
that intermediate values are attained. No preferred point or midpoint follows.
That two-vector A is itself a declared sensitivity scenario, not information
provided by a family label. Merely knowing that H1/H2 are related does not
identify A or justify choosing its largest output.

For a genuinely irrelevant appended source, R_0=0 gives q_0=0. A concrete exact
R_0 example is a fully declared **sequence-only** correspondence basis with
compatible local pair score 0 and self scores 300/300: `2*0/600=0`. If other
applicable families are unobserved, this establishes only the zero on that
available basis, not a fully measured zero correspondence. R=0 is a zero of
the convention, not proof of biological nonfunction.

Keep old coefficients unchanged and extend them by any finite a_0:

```
Q_new = sum_old a_i q_i + a_0*0 = Q_old.
```

H1 alone with a_1=1 stays **K=.771222064060654** after this append. The old 007
denominator change produced **.471244037496798**. For the pair above, appending
R_0=0 preserves .609869038 under the first table and .340233353 under the second.
Fixed finite coefficients are also continuous as an appended q approaches zero;
merely excluding exact zeros from a roster denominator would retain an abrupt
dilution for arbitrarily small nonzero contributions.

There is an exact tradeoff in this fixed-coefficient family. Suppose every
source, when present alone, must retain its original D_i for every nonzero D_i.
Then

```
tanh(a_i*atanh(D_i)) = D_i  ==>  a_i=1.
```

Thus **fixed coefficients plus universal single-source equality force a_i=1**.
Those same coefficients cannot also allocate only one total unit to a group of
two or ten distinct sources. A half-allocation H1 gives .471244037 even before
H2 arrives; it preserves neutrality but sacrifices the original singleton
scale. Declaring a different singleton table and then changing it on expansion
is reallocation, not preservation of fixed coefficients.

This is a proof about this specified mathematical family, not an impossibility
theorem about all conceivable scoring rules. It identifies the unavoidable
decision left by the current proposal. Unit coefficients preserve singleton
semantics but can amplify ten H1-like sources plus H2 to **.999999995150243**.
No covariance or target-transfer correction is supplied by that count effect.

## Actual shared data are handled before S; related sources are not duplicates

An exact second representation of H1 preparation 1 leaves the joint H1 fit
unchanged: S_1=4. A genuinely new, explicitly independent preparation of the
same source with y=2 and variance 1 changes that source fit to S_1=6; it is not
another homolog vote. Equal numbers alone establish neither identity nor
independence. Conflicting versions of one observation require reconciliation
or their explicit allowed alternatives, not two scientific contributions.

Known shared source error has a measured/model-defined numerical route. In the
earlier synthetic model `y_j=theta_H1+U+e_j`, with `Var(U)=.75` and independent
`Var(e_j)=.25`, H1's mean variance is `.75+.25/2=.875`. Therefore

```
S_1=16/7=2.285714286; D_1=.652299154.
With explicitly supplied a=(1,1): K=.433879884994061.
```

The covariance is a stated synthetic operand, not inferred from a source name.
For **unknown** shared covariance, preserve any known components. If the actual
information is only `C=.25 I+E`, `diag(E)=.75`, `E positive semidefinite`, then
for these two equal observations `E_12 in [-.75,.75]`, giving

```
V_H1 in [.125,.875]; S_1 in [16/7,16].
Conditional on a=(1,1), K in [.433879884994061,.654989761494914].
```

Both bounds are attained by the stated allowed covariance matrices. Negative
residual covariance is allowed by those constraints; forbidding it would be an
additional assumption. No midpoint, independence default, invented effective
sample size or discarded known variance is used.

Phylogenetically related **distinct source molecules** are not repeated
observations. Native source-error covariance also does not identify their
source-to-target response uncertainty. To see this explicitly, retain the
original H1/H2 source means (2,-2), variances (.5,1), and all R measurements.
Two otherwise unconstrained hypothetical target mappings can be

```
world +: z=(y_H1-1, y_H2+3) = (1,1)
world -: z=(y_H1-3, y_H2+1) = (-1,-1).
```

With exact offsets and the same original independent assay variance model,
both have fitted target variance 1/3. The target S values are +1.5 and -1.5,
and B values are **+.635148952 and -.635148952**. These are logical completions
of unmeasured mappings, not asserted biological calibrations. Nothing in the
unchanged S/R inputs distinguishes them. A conventional allocation can be
declared without identifying the target mapping; it must retain its conventional
meaning. Calibrated target inference additionally requires an applicable h and
its joint error/residual model, as in 006. No new target experiment is mandated.

## A measured zero is not the same as an irrelevant append

An appended observation can change existing S through a source or supported
common-target model. Under explicitly independent, known variance .25:

| Observations of the same effect | Fitted mean | Variance | S | B |
|---|---:|---:|---:|---:|
| .8 | .8 | .25 | 1.28 | .564899553 |
| .8, measured 0 | .4 | .125 | .64 | .309506921 |
| .8, measured .1 | .45 | .125 | .81 | .384219009 |

These reductions follow a changed joint likelihood, not a roster denominator.
The separate optimized scores 1.28 and .02 do not add to the joint .81. No
promise that every positive measurement raises calibrated directional support
is made. A zero S on a distinct source produces q=0 in this conventional
compression, but that does not prove its full likelihood would be uninformative
under a calibrated target model. Nondetection requires its actual limit and
censoring likelihood, not substitution of a measured zero.

Likewise, an R=0 source that supplies a new shared-control measurement can alter
another source's S through that shared model. It is then not a genuinely
irrelevant append to unchanged operands. Neutrality applies when the existing
S, R and allocations remain unchanged.

Equal opposite q values give Q=K=c=0 while both findings remain recorded.
H1 plus S=-4, R=1, at a=(1,1) gives **K=-.751617886, c=0**. Clipping each source
before summation would erase that opposition and is not the defined calculation.

## Required input, allowed-set result, missingness and uncertainty

The complete conditional result is defined by the actual allowed joint set
Omega of source inputs and allocations:

```
mathcal_K = { tanh(sum_i a_i*q(S_i,R_i)) : (S,R,a) in Omega }
mathcal_c = { max(0,k) : k in mathcal_K }.
```

Fill a point exactly when the corresponding image is a singleton; otherwise
retain the set or justified bounds and a null point. Preserve known dependencies
and constraints in Omega. An explicit finite A is evaluated completely. For
fixed a and rectangular q bounds, the tight bounds are
`tanh(sum_i a_i*q_i_lower)` and `tanh(sum_i a_i*q_i_upper)`; project endpoints
afterwards. With coupled constraints these box bounds are only an outer bound.
These are identification/sensitivity results, not statistical confidence limits.

If there is **no allocation information beyond finite nonnegativity**, the two
original opposite-sign q values allow every finite Q. The exact sets are
`K in (-1,1)` and `c in [0,1)`; their tight closed bounds are [-1,1] and [0,1].
No point is identified. If a_1=1 is already fixed and only the new opposing
a_2 is unknown and nonnegative, the tighter sets are `K in (-1,D_1]` and
`c in [0,D_1]`. These use the known coefficient rather than discarding it.
Additional numeric allocation limits can narrow the set only when declared.
An unknown source roster does not supply an invented complete-roster count.

For the explicitly supplied unit allocation, exact examples are:

| Missing operand | Signed K bounds | c point |
|---|---:|---:|
| H2 R unknown in [0,1], S_2=-2 known | [.023332364,.771222064] | null |
| H2 S unknown, R_2=.4 known | [.536827282,.895095198] | null |
| One source S=-4,R=1; another S unknown,R=.4 | [-.984423152,-.918030123] | **0** |

The last zero follows from the complete allowed image; it is not missing-data
imputation. Known R=0 implies q=0 even with missing S while S remains marked
missing. If all required source information is unknown, no default support
value, neutral .5, available-subset result or midpoint is silently supplied.

Allocations supply no sampling covariance. If a supported joint covariance of
D exists, fixed-a delta propagation uses
`g_i=(1-K^2)*a_i/(1-D_i^2)` and `Var_delta(K)=g^T Cov(D) g`. This is approximate
sampling variance of the convention, not target-function uncertainty. Otherwise
it remains unknown. Family membership, shared ancestry and a numeric allocation
table do not populate Cov(D). The research script additionally verifies that
the same mapped effects .8/.8 and marginal variance .25 give B=.856484915 with
independent errors and .664036770 with shared covariance .15; both preserve a
known .10 I component and residual diagonal .15. Marginals do not select one.

## Finite evaluation and exact interface boundary

Retain original finite S. For R=1 use q=S/2; for R=0 or S=0 use q=0. Otherwise,
with t=exp(-abs(S)), the equivalent stable expression is

```
q = sign(S)/2 * [log((1+R)+(1-R)*t) - log((1-R)+(1+R)*t)].
```

Ordinary atanh(R*tanh(S/2)) is suitable before display saturation. S=1000 and
-1000 with R=1 give q=500 and -500 and exact cancellation at equal allocation,
even though their displayed B values are +1/-1. S=1000,R=.8 gives
q=1.098612289. Finite original inputs give finite Q and exact |K|<1; a display
rounded to 1 is not certainty. Saturated B without original S/rounding bounds
leaves the point unknown; arithmetic overflow is a numerical evaluation failure.

The exact additional sheet fields are small:

| Field | Population/meaning |
|---|---|
| `source_ids`, `original_observation_ids`, `source_model`, `source_S` | Existing source reader/model, identity resolution and joint fitting; no new extraction design |
| `correspondence_components`, `R_basis`, `R`, `R_allowed_set` | Existing decomposed native convention, with actual operands and missing-family bounds |
| `allocation_coefficients` **or** `allocation_allowed_set` | Required complete numerical design input keyed to the same source identities; not inferred from source signs or phylogeny |
| `source_q`, `Q`, `K`, `c` | Defined deterministic transformations, signed result retained |
| `K_allowed_set/bounds`, `c_allowed_set/bounds` | Image of actual joint allowed inputs; exact versus outer bounds labeled |
| `sampling_covariance_D`, `sampling_variance_K` | Supplied joint uncertainty or null; allocation is never substituted |
| `result_status`, `missing_inputs`, `original_numeric_operands` | Computed, bounded-only, missing allocation/model, conflict or numerical failure, with precise operands retained |

The only new normative input needed by this correction is a numeric allocation
table/set and its intended scoring meaning. It has not been chosen here. Actual
missing source models/measurements retain their existing nullable semantics.
The formula does not create a whole-annotation reducer or broaden A105 beyond
the declared molecular statement. Investigation prompts and populating readers
remain separate. This finite result adds no research quota or runtime gate.

`check_neutral_combination_001.py` passed **125 arithmetic checks**; its populated
`arithmetic_001.json` records operands and results. Checks cover independent
rational identities, fixed-allocation neutrality, canonical duplicates,
known/unknown shared-source covariance, common-effect zero/weak-positive
updates, conflict, missingness, singleton c=0, source-to-target nonidentifiability
and finite-S saturation. They verify conditional mathematics, not actual
biological calibration, reader implementation, production behavior or an
accepted scoring policy. The source-free mathematical records inspected are
listed in `AUTHORITY_READ_001.md`.
