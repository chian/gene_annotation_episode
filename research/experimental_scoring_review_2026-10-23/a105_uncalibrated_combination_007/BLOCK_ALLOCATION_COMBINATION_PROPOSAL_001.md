# A105: one bounded combination for uncalibrated source relationships

2026-10-23. **Recommendation for judgment, not an adopted policy.** All examples
are synthetic. No paper or paper-specific packet was read. This work supplies
single-statement sheet mathematics only. It changes no investigation prompt,
reader, production scorer, library publication, episode or saved scientific run.
The ten-sheet goal remains at **0/10**.

Recommend a bounded signed accumulation of the existing correspondence-adjusted
source indexes, with an explicit **accounting allocation** for sources that
share a declared block. Each block receives one unit of influence; its members
share that unit equally. These allocations are proposed scoring inputs. They
are neither covariance estimates nor a claim that different blocks are
independent. A common clade, paper, laboratory or annotation does not determine
them numerically.

For one declared molecular statement, the complete proposal is

```
B_i = tanh(S_i / 2)                         source-scoped index
D_i = R_i * B_i                             conventional source-to-target index
q_i = atanh(D_i)                            transformed conventional index
a_i = 1 / n_g, for source i in block g      proposed accounting allocation
Q   = sum_g [sum_(i in g) q_i / n_g]
K   = tanh(Q)                               combined signed conventional index
c   = max(0, K)                             proposed nonnegative sheet coordinate
```

All opposing terms enter Q before the final c projection. K and the source
measurements remain in the sheet when c is zero. **Both the block allocation
policy and c projection remain proposals.** This is one recommendation with a
specified bounded conversion, not a claim that the user has selected cumulative
evidence over represented-source strength. The unanswered choice is substantive:
this convention averages transformed strength within a block and accumulates
across allocated blocks. It is not the previous mean of D values, a calibrated
target likelihood, a probability, or an estimate of target activity.

## Scope and dependency on the existing component calculations

The target is the supplied sequence, selected file contents or snippets. A
molecular statement may emerge during investigation; no candidate annotation
or public name is required to start. This calculation begins once that
statement has a defined molecular endpoint, numerator/denominator, direction,
comparison boundary, material span, state and condition scope.

The example statement is preferential molecular activity on X rather than Y,
with source parameter `theta_i = log(activity_X,i / activity_Y,i)` and boundary
zero. Different homologs have different source parameters. This convention
does not pretend those parameters are repeated measurements of one target
parameter. Binding, catalytic preference and transport do not become the same
endpoint because their indexes are dimensionless.

If a compound molecular statement has its own specified joint observation
model and source S, that S can be an input. This document does **not** create
such a model or aggregate several unrelated endpoints into a whole annotation
or axis. That separate question remains outside the calculation. The bounded
single-statement c above is defined here; its range conversion has not been
deferred to W05. Connecting this proposal to production annotation credit is
still separate W05 work.

The prerequisite numerical cells retain their meanings:

1. Native observations are canonicalized by actual experimental identity, not
   by paper count or equality of reported numbers. Compatible observations of
   one source/state and one parameter enter that source's joint model once.
   Shared controls, denominators and calibration observations remain shared
   variables with their actual dependencies. Do not sum separately optimized
   profile S values to fit a common effect.
2. Experimental comparability and isolation remain separate measured correction
   and uncertainty cells in that source calculation. Comparability concerns
   differences other than the deliberately varied X versus Y. Isolation
   concerns the fraction of the observed outcome attributable to the intended
   molecule. An R value or block allocation repairs neither one.
3. Source S is the existing signed source-model contrast. B is its proposed
   bounded transformation. Source S/B do not become target S/B after multiplying
   by R. Missing source-model inputs leave S unknown.
4. R comes from declared, normalized numerical correspondence components and
   their stated family weights. The earlier available-component R convention
   and `R*B` remain unadopted. They are explicit inputs to this recommendation,
   not empirical calibration established by this document. No overall intuitive
   relevance grade is inserted.

For relevant families j with weights w_ij, the inspected R proposal is
`R_available = sum_observed(w_ij*r_ij)/sum_observed(w_ij)`. It retains observed
weight coverage and hypothetical full-family bounds. The single-source result
here is **exactly D_i**, because `tanh(atanh(D_i)) = D_i`. Therefore the
proposal preserves the proposed single-source convention, rather than quietly
changing its scale.

## What the allocation means, including what remains unmeasured

A complete allocation is a partition of the declared distinct source/state
roster. Every source occurs in exactly one nonempty block. For block g containing
n_g sources, its coefficients sum to one. Two members have coefficients 1/2;
ten members have coefficients 1/10. Every block has total influence one in Q.
The raw membership count is the denominator; it is not a publication count,
estimated effective sample size or measured correlation coefficient.

The practical proposed meaning is: **allocate one unit to the average transformed
source index represented by this group of related evidence relationships**.
Choosing that accounting group is a policy input. A declared shared-family or
shared-calibration concern can motivate showing a grouping scenario, but does
not establish complete redundancy, rho=1, or exactly one statistical observation.
Likewise, separate groups receive two scoring units by convention, not because
different molecules or papers establish independence.

Source identity and actual shared measurements are factual inputs. The proposed
influence allocation is an additional explicit design choice. A block label
does not determine a missing native covariance and cannot repair an unavailable
source S. Different source-model uncertainty, family transfer uncertainty and
the accounting allocation remain distinguishable.

No source is removed because its result is unfavorable. Declare the roster and
allocation rationale without selecting a partition to maximize K. If a relation
crosses the chosen block boundary, retain that unresolved relation; do not label
the scalar "corrected for correlation." If block allocation is unresolved, the
exact proposed output is the set/range over declared admissible partitions,
with no point selected. With no allocation information, all set partitions of
the finite declared roster are admissible accounting scenarios. These are
sensitivity calculations, not inferred probabilities for partitions.

This intentionally simple partition policy cannot encode an arbitrary network
of partial overlaps. No hidden fractional discounts or phylogenetic cutoffs are
added. A user who requires measured partial-dependence calibration needs those
measurements and an applicable response model; a partition cannot supply them.

## Complete synthetic operands and main calculation

The assayed subjects are invented purified homologs H1 and H2 in stated states;
no organism or real protein is asserted. Only X versus Y is deliberately varied.
For this fixture, other conditions are matched, the comparability log correction
is exactly zero, and the attribution fractions are `f_X=f_Y=1`, so the separate
isolation log correction is `-log(f_X/f_Y)=0`. Correction uncertainties are
exactly zero in this hypothetical model. These assumptions are not defaults
for real assays or evidence that a whole real preparation is pure.

Each molecular activity denominator is 1 in a common rate-per-molecule unit;
the numerators are exp(y) in that same unit. The measured log ratio y is
dimensionless; known variance is in squared log-ratio units. The stated normal
sampling model is an input. The two H1 preparations have zero covariance in this
synthetic model, explicitly supplied rather than inferred from identities.

| Original observation | Source/state | y | Known variance | Activity X/Y |
| --- | --- | ---: | ---: | ---: |
| H1 preparation 1 | H1, purified stated state | 2 | 1 | 7.389056099 |
| H1 preparation 2 | Same H1/state | 2 | 1 | 7.389056099 |
| H2 preparation 1 | H2, purified stated state | -2 | 1 | 0.135335283 |

For a source's known-normal joint fit,
`S_i = sign(ybar_i)*ybar_i^2/(2*V_i)`. Thus H1 has mean 2, variance 1/2,
S_1=4 and B_1=0.9640275800758169. H2 has mean -2, variance 1,
S_2=-2 and B_2=-0.7615941559557649. Source preparations were combined before B.

The correspondence calculations use the earlier proposal's five relevant
families with equal weights. All inputs are synthetic, and all source/target
spans are complete for this fixture:

| Component | H1-to-target operands → r_1j | H2-to-target operands → r_2j |
| --- | --- | --- |
| Sequence score fraction | Valid local pair score 240, self scores 300 and 300: `2*240/600 = .8` | Pair score 90, self scores 300 and 300: `2*90/600 = .3` |
| Structural correspondence | Native TM scores .92 and .90: minimum .9 | Native TM scores .45 and .40: minimum .4 |
| Defined functional site | 7 exact matches / 10 predefined fully observed sites = .7 | 2/10 = .2 |
| Declared phylogenetic placement | 60 supporting / 100 eligible tree replicates = .6 | 10/100 = .1 |
| Declared system descriptor | Source and target 25 degrees C, scale 100 degrees C squared: `exp[-(25-25)^2/(2*100)] = 1` | Same operands = 1 |
| Available five-family mean | `(.8+.9+.7+.6+1)/5 = .8` | `(.3+.4+.2+.1+1)/5 = .4` |

The local-score normalization retains the scoring assumptions in the inspected
R proposal; arbitrary HMM scores do not enter that formula. Temperature equality
scores only that descriptor. It does not predict the enzyme's temperature
response or establish complete system correspondence. These component values
are correlated descriptions if derived from common data; the equal-weight mean
does not assert five independent experimental confirmations.

```
D_1 = .8*tanh(4/2)   = +.7712220640606535
D_2 = .4*tanh(-2/2)  = -.30463766238230594
q_1 = atanh(D_1)     = +1.0233365989890952
q_2 = atanh(D_2)     = -.3146237845286479
```

| Explicit proposed allocation | Coefficients | Q | K | c |
| --- | --- | ---: | ---: | ---: |
| H1 alone | 1 | 1.023336599 | .771222064 | .771222064 |
| H1 and H2 in separate blocks | 1, 1 | .708712814 | **.609869038** | .609869038 |
| H1 and H2 sharing one block | 1/2, 1/2 | .354356407 | **.340233353** | .340233353 |
| Block relationship unknown | Unknown | No point | **{.340233353, .609869038}** | Same two possible values |

For unknown membership there are exactly two set partitions. The tight hull is
`K in [.34023335299867896, .6098690379571441]`; it is not a claim that every value
between those endpoints is attained. No midpoint or preferred partition is
filled. The same inputs thus demonstrate why the allocation cannot be recovered
from R and B alone. The missing input is a scoring allocation, not undefined
arithmetic. The previous arithmetic mean of D would be .233292201; it is not
mathematically equivalent to either result here.

## Opposing measurements, weak positives, duplicates and a related cluster

| Synthetic case | Proposed allocation | K | Meaning |
| --- | --- | ---: | --- |
| H1 plus original opposing H2 | Two blocks | .609869038 | Negative contribution retained |
| Change H2 to y=+2, variance 1; R=.4 | Two blocks | .871181485 | A smaller positive allocated contribution raises this convention |
| Add weak H2 with y=.1, variance .25, S=.02, R=.4 | Two blocks | .772837892 | D_weak=.003999867; increase from .771222064 is small |
| Same weak H2 shares H1's block | One block | .472798385 | Reallocation changes the within-block transformed mean; this can lower K |
| Reprint H1 preparation 1, with identical original identity | Original two blocks | .609869038 | Same observations, same source fit, same allocation |
| Ten distinct H1-like sources assigned one block, H2 assigned another | Coefficients .1 for each positive; 1 for H2 | .609869038 | One proposed unit allocated to the positive group |
| The same eleven sources assigned eleven blocks | All coefficients 1 | .999999995 | The convention's large count effect is exposed |
| H1 and a source with S=-4, R=.8 | Two blocks | 0 | Two nonzero opposing results cancel; neither measured zero |
| H1 and stronger opposition S=-4, R=1 | Two blocks | -.751617886 | c=0, with negative K retained |

The ten-source cluster can represent a shared transfer concern of unknown
magnitude. Assigning its total influence one is a proposed accounting policy;
it is **not** a measured correction for correlation. A tree label does not say
which of the two ten-source rows is empirically right. No covariance or
effective sample size was manufactured for this example.

Three limitations of the specific recommendation are material:

- Adding a source with D=0 in its own block has no effect. Adding it to an
  existing block changes that block's mean: H1 plus a zero member gives
  `K=tanh(q_1/2)=.4712440374967983`. This dilution is a declared consequence of
  equal influence per represented member within a fixed block. It is not
  contrary evidence. The policy does not satisfy universal invariance to
  adding zero-contribution members.
- Different block rosters change existing coefficients. The one-unit allocation
  is a convention about representation, not an independently additive history
  of information gained. Saved scores and observations are not rewritten.
- Separate blocks can drive K close to one despite weak/unmodeled relationships.
  Bounded arithmetic does not calibrate source-to-target uncertainty. Changing
  blocks after seeing effects can manipulate the score; all scenarios and the
  stated allocation must remain visible.

These consequences are reasons for user judgment, not silently repaired with
floors, quality thresholds, best-source selection or extra numerical rules.

Positive observations also need not raise the **source's** directional evidence.
For one common-effect source model, `.8` alone with variance `.25` gives
`S=1.28, B=.564899553`. Adding independent `.1` with variance `.25` gives mean
`.45`, variance `.125`, and **S=.81, B=.384219009**. The small positive result
changes the fitted magnitude. Its independently optimized S=.02 is not simply
added to 1.28 in that common-effect fit. If .8 and .1 are instead observations
of different source parameters with R=1 and separate allocated blocks, this
conventional formula gives `K=tanh((1.28+.02)/2)=.571669966`. The difference is
intentional: different mathematical questions, with no asserted equivalence.

## Finite evaluation, saturation and exact endpoint handling

Require a finite original S for the point calculation, or a nonsaturated B with
its actual numerical precision and source-model provenance. With finite S and
`0 <= R <= 1`, the exact D satisfies `-1 < D < 1`; every q and Q is finite for a
finite roster. Consequently exact K lies in (-1,1) and c in [0,1). Domain-only
missing-data bounds may reach -1 or +1 as limits.

Do not evaluate atanh on a display rounded to +1 or -1. For original S and R,
the following equivalent expression avoids that error. With `a=abs(S)` and
`t=exp(-a)`:

```
R=0 or S=0: q = 0
R=1:        q = S/2
otherwise: q = sign(S)/2 * [
                log((1+R)+(1-R)*t)
              - log((1-R)+(1+R)*t)]
```

Small/moderate values can use `atanh(R*tanh(S/2))` directly. Large finite Q may
produce a floating-point display K=+1 or -1. Retain Q and original operands and
mark that display saturation; it is not mathematical certainty. No epsilon,
artificial noise or clipping of native S is introduced.

Checked example: S_1=+1000, S_2=-1000, R_1=R_2=1 in separate blocks.
Binary64 displays B as +1 and -1, while exact finite q values are +500 and -500.
Q=0 and K=0. Using the original finite operands resolves the otherwise undefined
product form 0/0. With S=1000 and R=.8, q approaches `atanh(.8)=1.098612289`;
the smaller correspondence does not inherit an infinite transformed value.

If only saturated B values are retained and original S/rounding information is
lost, the point is **unknown** (`original_source_score_needed`). Known rounding
bounds can constrain B. Without such bounds use its domain [-1,1] and any actual
sign constraints supplied by the source record; do not reconstruct finite S
from a displayed endpoint. Contradictory exact infinities are not accepted as
finite empirical source inputs. A numerical evaluator that cannot represent a
finite calculation returns `numerical_evaluation_failure`, with operands kept;
that is different from a missing scientific input.

## Missing inputs and the exact meaning of bounds

For a fixed partition, define each source's allowed transformed-index set from
its actual allowed S/B and R values. If its tight bounds are `[q_i^-,q_i^+]`,
then under a rectangular allowed set:

```
Q^- = sum_i a_i*q_i^-             Q^+ = sum_i a_i*q_i^+
K bounds = [tanh(Q^-), tanh(Q^+)]
c bounds = [max(0,tanh(Q^-)), max(0,tanh(Q^+))]
```

This follows coordinate-wise monotonicity, because a_i is nonnegative and tanh
is increasing. Box bounds assert only permitted numerical ranges, **not
statistical independence**. If shared observations impose joint constraints,
take infimum/supremum of the same defined formula over that joint allowed set;
the box calculation is then only an outer enclosure. Retain known constraints
rather than discarding them to get a favorable endpoint.

Unknown R with known finite S gives
`q in [min(0,S/2), max(0,S/2)]`. Unknown source B with known R<1 gives
`q in [-atanh(R), +atanh(R)]`. With both unknown, q ranges over the whole real
line, with extended limits -infinity/+infinity. Known R=0 makes q=0 even when B
is unknown; known S=0 likewise makes q=0, while the missing operand remains
marked missing. Neither is a zero imputation.

For uncertain allocation, evaluate every admissible partition using the same
formula and constraints, retain its result, and take the smallest lower and
largest upper bound for the hull. A finite roster has finitely many partitions.
This is a fully specified calculation; the arithmetic checker enumerates the
two-source case. No partition is chosen because its score is largest.

| Missing input, original two separate blocks unless stated | Point result | Tight domain/identification result |
| --- | --- | --- |
| H2 R entirely unknown; S_2=-2 retained | K and c unknown | `q_2 in [-1,0]`; `K,c in [.023332364,.771222064]` |
| H2 source S/model unknown; R_2=.4 retained | K and c unknown | `q_2 in [-atanh(.4),atanh(.4)]`; `K,c in [.536827282,.895095198]` |
| H1 evolutionary family unknown | Full-family point unknown | `R_1 in [.68,.88]`; `K,c in [.438462925,.733190652]` |
| Same preceding row, elected available-family calculation | Conditional K=.686040072 | `R_available=3.4/4=.85`; observed weight fraction .8; not the full-family point |
| Every source S and R unknown; finite nonempty roster | K and c unknown | K bounds [-1,1]; c bounds [0,1], including when allocation is also unknown |
| Source roster unknown or empty | `no_declared_source_roster`; point unknown | No complete-roster score or inferred contribution count; universal output domain only |

These intervals describe possible outputs of this conventional formula. They
are **not confidence intervals for the target's function**. Endpoints -1 and +1
are limiting bounds when source S is required finite. The all-unknown result
does not become neutral .5, support zero, a midpoint, or an available-subset
score masquerading as the full-roster result.

Conflicting representations of one original observation remain an unresolved
source conflict. If its alternative values are known, use their actual allowed
set before source fitting; do not count each version as another source. A
nondetection uses the actual source censoring model and detection limit. A
known source S=0 under that model can enter the formula, but is not a measured
zero molecular rate. An unknown limit/model yields missing S and the stated
missing-input calculation, without a fabricated negative finding.

## Sampling uncertainty is separate from allocation and missing-data bounds

The allocation supplies no numerical covariance. If a supported joint covariance
of D is available, a local propagation calculation for fixed a is

```
dK/dD_i = (1-K^2) * a_i/(1-D_i^2)
Var_delta(K) = sum_i sum_j [(dK/dD_i)*(dK/dD_j)*Cov(D_i,D_j)]
```

Cov(D) must include the actual source-model and R-operand uncertainties and
their shared measurements. An external supplied joint simulation/bootstrap can
instead propagate through the same deterministic formula. The delta expression
is approximate for nonlinear score sampling variation, not target-function
uncertainty. Unknown covariance gives `sampling_variance = null` with reason
`joint_sampling_covariance_missing`; it is not replaced by diagonal covariance,
block membership, a fixed correlation, or an effective sample count. All examples
leave that field null. Empirical transfer uncertainty remains uncalibrated even
if the score's laboratory sampling variance were known.

## Exact sheet fields and separate population responsibilities

The following are proposed numerical-sheet inputs/outputs and field meanings.
They are not prompt text or implemented readers. A targeted reader must obtain
these exact inputs; this research arithmetic checker does not perform extraction.

| Field | Type, meaning, units, population |
| --- | --- |
| `statement_scope` | Declared material span, molecular endpoint, numerator, denominator, sign, boundary, state and conditions; identifies which source comparisons can enter this calculation |
| `source_roster` | Nonempty list of distinct assayed source/state units; not papers or database rows |
| `original_observation_refs` | Actual canonical observation identities and shared-control links; factual identity resolution precedes source fitting |
| `comparability_inputs`, `comparability_correction`, `comparability_uncertainty` | Separate native conditions and measured correction/model inputs; unknown remains unknown |
| `isolation_inputs`, `isolation_correction`, `isolation_uncertainty` | Separate measured attribution fractions, correction and uncertainty; unknown remains unknown |
| `source_S`, `source_S_allowed_set`, `source_model_ref` | Finite signed source fit value or explicit allowed set/null; computed from the defined source model, not assigned from qualitative categories |
| `source_B` | `tanh(source_S/2)`, signed and bounded, with original S retained |
| `correspondence_components` | Native numeric operands, defined r_ij, family weights, relevant/observed basis; reader preserves values and deterministic calculations |
| `R_available`, `observed_weight_fraction`, `R_full_bounds` | Prior R formula and its declared conditional/full basis; no observed family gives null point |
| `source_D`, `source_q` | `R*B`, and stable `atanh(R*B)` respectively; both conventional, not target activity |
| `allocation_blocks` or `admissible_allocations` | Explicit proposed accounting partition(s); each source once per partition; no inferred numerical correlation |
| `allocation_coefficient` | Deterministic `1/block_member_count` for the selected proposed accounting partition |
| `Q`, `K`, `c` | Defined sums and transformations above; Q finite for finite point operands, K signed in (-1,1), c nonnegative in [0,1); retained negative K |
| `K_allowed_set`, `K_bounds`, `c_bounds` | Exact image/set or stated enclosure; indicate full versus available basis, joint constraints and limiting endpoints |
| `sampling_covariance_D`, `sampling_variance_K` | Actual joint sampling input and defined propagation; null when absent; no block-to-covariance conversion |
| `numeric_precision`, `display_saturated` | Preserve original S/Q and distinguish rounded display endpoints from mathematical endpoints |
| `result_status`, `missing_inputs` | `computed`, `conditional_available_basis`, `bounded_only`, `no_declared_source_roster`, `original_source_score_needed`, `source_record_conflict`, `invalid_input`, or `numerical_evaluation_failure`, with exact affected operands |

The formula is complete conditional on these inputs. Lack of an empirical
source model, measured correspondence or chosen accounting allocation has a
defined nullable/bounded result. Those are absent inputs, not undefined sums.
For **calibrated** cumulative target evidence, the minimal additional scientific
inputs remain a supported source-to-target response relationship and its joint
residual/error structure; no scalar built only from R and B identifies them.

## Decisions exposed for the user and verification

The recommendation asks the user to judge this precise scoring meaning: one
unit per declared accounting block, equal allocation within each block in q
space, accumulation across blocks, and positive-part projection after retaining
opposition. The group dilution/count effects above are part of that choice.
The inherited R family normalization/weights and available-basis point policy
also remain unadopted inputs. No empirical calibration, selection, approval or
completed A105 sheet is claimed.

The inspected source-free records supply the trace:

| Component | Inspected input and relevant content |
| --- | --- |
| Native correspondence components, R and R*B | `a105_target_relevance_003/UNCALIBRATED_CORRESPONDENCE_CONVENTION_002.md`: component formulas, available/full bases and scope limits |
| Source-state pooling, M/K arithmetic and duplicate identity | `a105_multiple_sources_005/MULTIPLE_SOURCE_CONVENTION_001.md`: synthetic H1/H2 observations and correspondence operands |
| Unresolved aggregation meaning and corrected arithmetic | `a105_multiple_sources_005/INTERPRETATION_AND_ARITHMETIC_ADDENDUM_002.md`: distinction between means and cumulative conventions; no adopted combination |
| Common-effect fitting and positive .8/.1 counterexample | `a105_correlated_bridge_006/CORRELATED_RESPONSE_PROPOSAL_001.md`: source/target distinction, covariance and sum-before-profile |
| Retaining known constraints in sensitivity sets | `a105_correlated_bridge_006/SENSITIVITY_CONSTRAINT_ADDENDUM_001.md`: an unknown component does not erase known covariance information |
| Block accounting, stable q and current combination | This proposal: new explicit scoring convention and synthetic arithmetic, not a published or measured calibration |

`python3 research/experimental_scoring_review_2026-10-23/a105_uncalibrated_combination_007/check_block_combination_001.py`
passed **255 arithmetic/domain checks** using Python's standard library. They
cover source pooling, duplicate/conflicting representations, component means,
single-source equality, same/separate/unknown allocations, opposing and weak
positive measurements, ten-member allocation, all-unknown and partial bounds,
finite saturation, sign/permutation invariance, invalid inputs, and 81 interval
grid checks. `arithmetic_001.json` records all calculated results and check names.
The main examples use analytic formulas and explicit two-partition enumeration.

These checks verify the stated mathematics only. They do not validate a real
source model, calibration, block assignment, reader, production consumer, model
prompt or scientific investigation. Only new files in this owned directory
were written. The complete authority read is recorded separately.
