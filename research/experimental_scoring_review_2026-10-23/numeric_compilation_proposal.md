# Incomplete compilation proposal — correction, 2026-10-23

The original proposal below is preserved unchanged. Its claims to supply a
complete calculation or a fully calculable experimental-reliability sheet are
withdrawn as claims of delivery against the user's template.

Its experimental relevance, measurement validity and attribution inputs depend
on rejected overall category grades. Its qualitative signal fallback likewise
assigns fixed fractions instead of using the individual quantitative inputs.
The transfer placeholder does not supply the requested relevance calculation.
Consequently, its worked final scores do not establish the requested sheet.

Sums and multipliers are required, not the mistake. The numerical
signal-to-uncertainty formula, accumulation formula and positive/opposing
combination contain explicit arithmetic; they are assistant proposals whose
inputs and scientific meanings still require assessment within the user's
template. They are not made valid by replacing only the transfer input, and
they are not rejected merely because they use arithmetic. The draft's choices
of confidence-interval format, aggregation ceilings, primary endpoints and
output fields must not become requirements attributed to the user.

Return to the user's template before converting the research into component
calculations and their combination. Use prior measured examples as inputs,
with their experimental definitions and limitations. Do not change production
credit or write readers from this rejected overall sheet. The preserved
arithmetic and source examples are research material, not completed scoring.

<!-- PRESERVED ORIGINAL BELOW -->

# Candidate numerical compilation for experimental evidence

Later clarification: see the evidence-transfer addendum in
docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md. The user
did not restrict evidence transfer to sequence homology or prohibit a scored
transfer assessment. References below to "native correspondence" mean the
original measurements or observations establishing the relevant relationship;
they do not define the relationship, a complete transfer score or an exclusive
set of methods. The unadopted T ladder in the companion draft remains available
for review alongside this draft's conditional calculation.

**Research proposal for feedback, 2026-10-23. Not an adopted scorer.** This is
one concrete candidate for W04 part 2. It supplies numerical signal,
uncertainty, replication and compilation cells to accompany the interpretation
cells in [numeric_rubric_proposal.md](numeric_rubric_proposal.md). The numerical
policy is deliberately explicit so that the user can change it. Its constants,
grade spacings and aggregation are **not empirically calibrated probabilities**.
No reader, production rubric, annotation-credit function, model prompt, episode,
continuation rule or stored observation is changed here. W05 retains ownership
of connection to annotation credit.

This proposal uses the supplied instructions, research scope,
[synthesis](SYNTHESIS.md) and all three lane summaries. Biological examples below
are carried from those reviews; this workload did not reread primary papers or
reanalyze experimental data. All invented measurements are identified as
synthetic. The numerical examples were evaluated with a disposable Python
arithmetic command; no reader or scoring implementation was written.

## What is scored

The unit is an observed result's bearing on a **bounded inference in stated
conditions**. The inference can emerge after investigation starts from sequence,
selected file contents or snippets. It is not required in the initial task.
The same result may be direct evidence for binding and indirect evidence for a
physiological mechanism; these are different scored inferences with shared
experimental provenance.

The candidate returns two requested kinds of number:

1. **Experimental reliability for the assayed-subject inference**, with positive
   and contrary components retained. It evaluates whether the experiment
   resolves that inference about the actual assayed subject.
2. **Annotation-support contribution for the declared target and conditions**,
   with positive and contrary components retained. It additionally accounts for
   relation to the proposed annotation and source-to-target correspondence.

These are numerical components of the proposed annotation scoring sheet, not
new goal-credit channels. The final nonnegative support projection below is a
candidate value of the current annotation, not an operation on observed yield.
A later decrease in support is preserved. This proposal never clips, smooths,
rescales or rewrites a completed action's actual gain or saved yield history.

## 1. Numerical sheet cells

The source identity, exact endpoint, conditions, experimental-unit hierarchy,
named weaknesses and figure/data locators accompany these cells as supporting
records. They are not points merely for being present. Every filled evaluative
cell must distinguish a native calculation from a stated rubric judgment.
Implementation of the future functions that populate the settled cells remains
part 3 work.

| Cell | Numerical type and range | Input and calculation or grading meaning |
| --- | --- | --- |
| `R` | Real in `[0,1]`, a grade range, or unknown | Relation between the actual measured endpoint and the particular inference, assuming measurement and attribution are correct. Use the counterpart's explicit rubric. |
| `V` | Real in `[0,1]`, a grade range, or unknown | Validity of the measured readout under its assay type. Does not duplicate attribution, target transfer or measured precision. |
| `A` | Real in `[0,1]`, a grade range, or unknown | Attribution to the assayed protein, component or molecular property. A demonstrated competing source that defeats attribution can give `A=0` for that attribution while the preparation-level measurement remains valid. |
| `T` | Unresolved native-correspondence interface; conditional scalar in `[0,1]` only under an explicitly justified contract | Additional correspondence from assayed subject/system to the declared annotation target. Preserve native homology, structure, context and matched-transfer measurements. No blanket transfer-grade ladder, raw-identity conversion or general scalar mapping is supplied here. For a source-scope demonstration with no transfer, `T=1`; otherwise leave the scalar interface unknown unless its meaning is established. |
| `theta_hat`, `delta_native` | Real, in declared native units; unknown allowed | The measured estimand and, when applicable, its matched treatment/control contrast. Preserve original operands and units. Ratios require a meaningful denominator; log ratios require positive operands. |
| `theta_0` | Real in the same units as `theta_hat`, or unknown | The discriminating boundary entailed by the particular inference. Zero is appropriate for a difference/existence contrast; a physiological adequacy claim requires its own justified nonzero boundary. This is part of what the inference asserts, not a runtime acceptance threshold. |
| `direction` | `+1` or `-1` | Orient the prediction: `+1` when larger values support the inference, `-1` when smaller values support it. |
| `m` | Signed real, native units | Oriented margin `direction * (theta_hat - theta_0)`. Native signal relative to the declared inference, not a confidence measure. |
| `L95`, `U95` | Native-unit bounds; unknown allowed | Lower and upper bounds of a documented 95% confidence interval for that estimand. Retain interval method, uncertainty type and experimental-unit meaning. Do not substitute an SD, SEM or unidentified ±. |
| `h95` | Nonnegative real, native units; unknown allowed | `max(theta_hat-L95, U95-theta_hat)` when both bounds and the estimate describe the same estimand. This conservative radius retains an asymmetric interval without pretending it is symmetric. |
| `H` | Real in `[0,1]`, a grade range, or unknown | Resolution of the observed signal relative to uncertainty or a documented qualitative separation, defined below. It is not effect magnitude and not probability of function. |
| `s` | `-1`, `0`, `+1`, or unknown | Direction of the observed outcome relative to this inference: `sign(m)` in the numerical branch; explicitly supported direction in the qualitative branch. `0` denotes a measured non-discriminating outcome, not an unavailable experiment. |
| `n_bio`, `n_prep`, `n_technical` | Nonnegative integers or unknown | Actual numbers at the documented hierarchy levels. They are inputs to justified uncertainty calculations and dependency classification, never independent point bonuses. |
| `k_plus`, `k_minus`, `k_unresolved` | Nonnegative integers or unknown | Counts of established independent experiment groups with supporting, contrary or unresolved outcomes in the same comparison scope. Counts remain visible; publication count is not their substitute. |
| `B_E`, `e` | Real or interval in `[0,1]` | Per-group maximum experimental contribution `B_E=V*A`; per-group resolved reliability `e=B_E*H`. |
| `B_C`, `c` | Real or interval in `[0,1]` | Conditional maximum annotation contribution `B_C=R*V*A*T`; per-group contribution magnitude `c=B_C*H`, with direction stored in `s`. |
| `E_plus`, `E_minus`, `E`, `K` | Reals or intervals in `[0,1]` | Compiled experimental reliability and consistency, defined in section 5. |
| `P`, `N`, `C` | Reals or intervals in `[0,1]` | Compiled target support, opposing evidence and nonnegative annotation-support contribution, defined in section 5. |

`R,V,A` are declared quality-index inputs. Their multiplication is a proposed
cardinal **policy interpretation** of the grades, not multiplication of measured
probabilities. `T` is an unresolved interface to native correspondence evidence,
not adoption of the counterpart's provisional transfer ladder. If a future
native-correspondence contract supplies a scalar compatible with this formula,
that contract must define what the scalar measures and prevent counting the same
homology/structure/context evidence again in another annotation-credit axis.
Until then, target calculation is explicitly conditional or bounded; actual
assayed-subject reliability remains fully calculable. A single named weakness
receives one primary cell. For example,
nonselectivity of a mutation belongs in `A`; it is not penalized again in `R`,
`V` and `T`. Native measurements remain available when a compressed grade omits
important detail.

## 2. Signal and uncertainty

### Numerical branch

For a documented 95% confidence interval on the appropriate estimand, propose:

`H = abs(m) / (abs(m) + kappa*h95)`, with default `kappa=1`.

Examples: margin equal to the uncertainty radius gives `H=0.5`; a margin four
times that radius gives `H=0.8`. These are quality-index anchors. They are not
95%, 50% or 80% probabilities that the inference is true. The formula has no
significance cutoff: an interval crossing the boundary can supply a small
directional contribution, qualified by its uncertainty. A nonzero estimate with
genuinely zero uncertainty would yield 1, but missing uncertainty is never zero
uncertainty. For `m=0`, set `s=0,H=0`, including the algebraic `0/0` case.

Do not put a raw binding `Kd`, a fold induction, a product fraction or a p-value
straight into `H`. The quantity must resolve a contrast relevant to the specific
inference. For example, a 20 nM fitted `Kd` does not itself provide the
signal-versus-control uncertainty needed to score existence of binding; nor does
strong affinity measure origin anchoring. A p-value is not converted to a
probability of function.

The following restrictions are part of the cell definition:

- **SD is dispersion, not uncertainty of an estimated mean.** `SD/sqrt(n)` is
  usable only with the appropriate independent experimental units and a
  justified sampling model. Technical-well count cannot replace culture or
  preparation count. A paired contrast requires its pairing/covariance.
- **SE is not a confidence half-width.** A conversion needs the applicable
  distribution/quantile, degrees of freedom and model. Under a justified
  normal-mean model with estimated variance, for example,
  `h95=t_(0.975,n-1)*SE`. The proposal does not silently impose that model on
  kinetic fits, censored measurements, clustered cultures or nonlinear ratios.
- **Unidentified ± cannot populate `h95`.** It remains an unclassified native
  quantity. A bootstrap interval, profile-likelihood interval or other reported
  95% interval can be used with its actual method retained; a 90% interval or a
  Bayesian credible interval is not relabeled as this 95% confidence cell.
  Harmonization requires an explicit justified model; otherwise use an
  admissible qualitative assessment or leave `H` unknown.
- **Native arithmetic retains uncertainty meaning.** Given genuine bounds,
  differences have bounds `[L_a-U_b,U_a-L_b]`; positive-denominator ratios have
  `[L_a/U_b,U_a/L_b]`. These are algebraic envelopes. They are not automatically
  a new 95% confidence interval for a contrast. Unknown dependence or coverage
  cannot be repaired by calling the envelope a confidence interval.
- **Changing units does not change `H`.** Both `m` and `h95` change together.
  Changing the biological inference or its adequacy boundary can change it.
  Unlike native units are never added across experiments.

A mean estimated very precisely can support a small biochemical effect without
establishing physiological adequacy. If that adequacy has a documented native
threshold, use it in `theta_0`. If the inference requires an unmeasured biological
connection, keep that gap in `R` or a genuinely unknown cell; do not invent an
adequacy threshold or treat high precision as the missing connection.

### Explicit qualitative branch

A missing numerical interval does not automatically yield either `H=0` or a
default positive grade. It can be possible to read actual outcome separation
without a compatible numerical interval. The following are proposed anchors
for that narrower judgment; they apply to the result, not the reputation of
the paper or an author's confidence adjective.

| `H` | Required observed basis |
| ---: | --- |
| 0 | An actually measured comparison is non-discriminating for the specified boundary, with no resolved direction. An unavailable or failed assay is not assigned 0 by this rule. |
| 0.25 | An inspectable matched result establishes an observed direction, but neither a usable uncertainty measure nor the degree of separation from variability/background can be obtained. A generic claim sentence alone is insufficient. |
| 0.50 | An inspectable categorical endpoint or displayed comparison distinguishes the relevant outcomes under an explicit readout/detection rule, but uncertainty around the separation cannot be quantified. Examples include identified versus unidentified product under a stated identification rule, or signal visibly separated from its matched blank without extractable error information. |
| 0.75 | A documented bound or descriptive uncertainty range lies entirely on the required side of the inference boundary, although no compatible 95% confidence interval is available. Examples include a calibrated upper detection bound below a stated nonzero adequacy requirement. The source must supply the bound/range and its meaning. |
| 1 | Not available from qualitative wording alone. |
| unknown | Actual separation, direction, boundary or comparability cannot be determined from the evidence inspected. No automatic middle grade. |

If the evidence warrants only two adjacent anchors, retain the interval between
them; do not insert its midpoint. A single result uses one branch, never a
numerical score plus an additional qualitative bonus. If control specificity is
already scored in `V` or `A`, it is not counted again as extra `H` points. `H`
asks how resolved the outcome is; `V/A` ask whether that outcome was validly
measured and attributed.

For **nondetection**, the claim matters. “No signal observed,” with unknown
sensitivity, cannot become strong contrary evidence to all possible activity.
It may be `s=0,H=0` for an existence comparison only when the observed outcome is
known to be non-discriminating; if its interpretation cannot be determined, use
unknown. A validated upper bound below a specified nonzero activity/adequacy
requirement can give `s=-1,H=0.75` under the qualitative bound rule. Retain the
bound and tested conditions. This does not establish an exactly zero rate.

## 3. Dependence and complementarity before aggregation

Numerical compilation needs a defensible experimental unit; papers, citations,
panels, technical repeats and record copies are not units by default.

- **Known copies of one result:** collapse to the same experimental result.
  Another review, database row, published representation or repeated extraction
  changes no numerical cell unless it provides genuinely new information about
  that result. Equal numerical values alone do not prove identity.
- **Technical repetitions and correlated readouts:** use a justified native
  summary of the primary estimand when available. They do not each enter the
  independent-replication product below. Their actual spread and hierarchy can
  improve or worsen the summary's `H`.
- **Complementary experiments:** update the specific `R,V,A,T` interpretation
  that they resolve, with the named weakness and result link retained. The
  revised bundle replaces the old interpretation for current scoring; the old
  record remains historical. A product-identification experiment may repair an
  endpoint gap; a component substitution may repair attribution. Neither
  automatically creates another replication of the functional endpoint.
- **Control reuse:** a control that validly applies to several independent runs
  may inform those runs' interpretation grades. It is not also a new replication.
  The common control and its unresolved limitations remain shared.
- **Genuine independent replication:** a distinct experimental run with
  disjoint relevant biological/preparation units and no known shared unresolved
  measurement dependency can enter independently. A new laboratory or paper is
  neither necessary nor sufficient. Known common system/model limitations stay
  in interpretation cells and cannot be washed away by repetition.
- **No double use of sample size:** if several runs are pooled into one
  justified estimate and its uncertainty, score that combined estimate once.
  Do not also give the same runs separate replication contributions. Within-run
  `n` used in a confidence interval receives no additional count multiplier.
  Splitting one run into arbitrary chunks does not create replications.

Each group has one appropriate primary functional estimand for this inference.
Choose that endpoint by its scientific relation, not by which observed signal
is largest. Other endpoints can supply named complements or their own bounded
inferences. If multiple dependent estimates have no defensible joint summary or
primary endpoint, retain the range of possible contributions and any conflict;
do not silently choose the most favorable point. A contrary result that
invalidates an earlier attribution updates that earlier `A` and is not also
automatically counted as independent negative replication of the chemistry.

When otherwise distinct experiments have **unknown dependence**, do not report
an established independent count. For concordant same-scope results, this
candidate reports an aggregation range from the strongest single-result
contribution (no replication increment) to the independently aggregated value.
This is a policy sensitivity range, not a statistical confidence interval. For
mixed directions, do that separately for positive and contrary components and
propagate conservative bounds. An explicitly known duplicate never gets this
independence upper bound. An existing informative result can therefore retain
support while dependence of another result remains unresolved.

## 4. One bounded accumulation rule

For each independent group `g`, let `B_g` be its maximum contribution and
`H_g` its resolution. A single group contributes `B_g*H_g`. Repetition should
increase resolution while retaining interpretation limitations. In particular,
arbitrarily many repeats of a binding proxy must not turn that proxy into a
direct measurement of physiological mechanism.

Let `0=b_0 < b_1 < ... < b_J` be the distinct positive values of `B_g`, together
with the zero starting point. Define:

```text
Q(B,H) = sum over j=1..J of
         (b_j - b_(j-1)) *
         [1 - product over groups with B_g >= b_j of (1 - H_g)]
```

An empty collection returns 0. The operation is symmetric in the groups and
monotone in each known `B_g,H_g`. It is a proposed bounded quality index, not a
noisy-OR probability model or an independence likelihood calculation. Known
experimental independence permits the **policy increment**; the formula does
not infer independence from the numerical values.

For a common maximum contribution `B`, the expression is simply:

`Q = B * (1 - product_g(1-H_g))`.

Consequences:

- One experiment: `Q=B*H`.
- Two independent experiments with `B=0.5,H=0.5`: `Q=0.375`.
- Any number of repetitions with `B=0.25`: `Q <= 0.25`.
- A result with zero applicable interpretation factor (`B=0`) contributes zero for that
  inference, regardless of signal strength or repetitions.
- A result with a high maximum contribution but nearly unresolved signal has a
  correspondingly small increment. It does not confer its interpretation grades
  on all weaker results.

The last property is why this uses the displayed piecewise expression rather
than normalizing every result to the best `B` and doing a single product. The
latter would allow one nearly unresolved direct result to inflate previous proxies.

## 5. Experimental reliability, consistency and annotation contribution

Compile only within a defensible **comparison scope**. Its identity includes
the inference, relevant subject, estimand, intervention, required conditions,
dose and time window. Different readout technologies can measure the same
estimand. Different biological endpoints or required environments are not
automatically interchangeable because the paper uses the same gene name.

For experimental reliability, use `B_E=V*A`, excluding source-to-target
correspondence and the endpoint-to-broader-annotation gap:

```text
E_plus  = Q(B_E,H) over supporting independent groups
E_minus = Q(B_E,H) over contrary independent groups
E       = abs(E_plus - E_minus)
K       = abs(E_plus - E_minus) / max(E_plus,E_minus)
          when max(E_plus,E_minus)>0; otherwise unknown
```

`E` is the proposed **compiled experimental reliability for a resolved
direction**. `K` is a numerical consistency balance: 1 for support in only one
direction, 0 for equally weighted opposing directions. It is not the proportion
of experiments reproduced, and a one-experiment `K=1` does not establish
replication; the counts remain visible. A high-quality negative can have high
`E` with negative direction. Equal credible conflict gives `E=0` while both
`E_plus` and `E_minus` remain high. The score then means the shared inference is
unresolved, not that both assays were defective. Because a scalar cannot
distinguish no evidence from balanced conflict, retaining those two components
is part of the sheet, not an optional explanation.

For the declared target annotation and conditions, use `B_C=R*V*A*T`:

```text
P = Q(B_C,H) over supporting independent groups
N = Q(B_C,H) over contrary independent groups
C = max(0, P - lambda*N), with default lambda=1
```

`C` is the candidate nonnegative **annotation-support contribution**. It is not
probability of correct annotation. This policy makes equally strong comparable
opposition cancel positive support; weaker opposition reduces it continuously.
`P` and `N` are retained so cancellation cannot erase evidence. The `K` factor
is not multiplied into `C` again: opposition has already entered its calculation.

An inference boundary must actually predict the contrary result before it is
included in `N`. A native pathway phenotype and a negative purified assay with
unknown required partners can expose a mechanistic gap without being opposite
measurements of the same claim. Distinct endpoints/time windows/conditions get
separate rows and numerical results. For a universal annotation spanning those
conditions, the conditions become part of its declared assertion and require a
separate, justified logical comparison; they are not silently pooled by gene.

No cross-axis mean, hypervolume replacement or new global credit combination is
proposed. This supplies per-inference numerical sheet values for the later W05
decision, with their inputs and limitations visible.

## 6. Missing inputs and ranges

Unknown is not a zero measurement or an automatic middle grade. A genuinely
unknown multiplier is represented for sensitivity calculation by `[0,1]`, while
the field remains explicitly `unknown`. A justified narrower grade range is
used as such. These are **policy/knowledge bounds**, kept distinct from the
native confidence interval.

There is no complete-field prerequisite for recording, evaluating or returning
partial evidence:

- `V,A,H` can give a numerical experimental reliability even when target `T` is
  unknown. Target-specific contribution is then a range, not a fabricated
  applicability weight.
- If one result has unknown uncertainty and no defensible qualitative
  resolution, its `H` remains `[0,1]`; known contributions from other results
  still compile. A weakly documented additional result does not erase existing
  evidence.
- A valid qualitative observation can provide its explicitly anchored `H`
  despite missing numerical error bars. The absence of error bars itself never
  supplies the grade.
- A known zero attribution supplies zero contribution for that particular
  attribution, even if unrelated fields are unknown. It does not mean zero
  activity of every possible preparation or system.

For fixed outcome directions, `Q` is monotone. Calculate its lower value from
the lower `B,H` bounds and its upper value from the upper bounds. If
`P=[P_l,P_u]` and `N=[N_l,N_u]`, a conservative support range is:

`C = [max(0,P_l-lambda*N_u), max(0,P_u-lambda*N_l)]`.

Shared uncertain inputs can make this rectangular bound wider than necessary;
retain their linkage and evaluate common assignments when a tighter bound is
needed. For unknown direction, take bounds across permitted direction
assignments, with a group used once in each assignment. Never put the same
unknown result into both directions as independent evidence. For `E`, propagate
the interval of `E_plus-E_minus` through absolute value; if it crosses zero,
the lower bound is zero. `K` remains unknown if its denominator may be zero.

Report the known native measurements, known components, interval contribution
and missing cell names. Do not silently select an interval midpoint. A
conditional number may be displayed only with its condition, for example
“0.8 if the source result applies fully to the target”; it is the upper-bound
scenario, not a target score already established.

## 7. Worked comparisons

The table below uses default `kappa=1`, unit interpretation-factor exponents and
`lambda=1`. Native values invented for arithmetic are marked **synthetic**.
`T=1` in source-scope examples means the demonstration target is explicitly the
assayed subject in the tested system. It does not assign correspondence to an
unsupplied user sequence. All worked single-group examples with one direction
have `E=e` and `K=1`, with the direction and experiment count still shown.

### A. Strong signal cannot rescue known wrong attribution

The retained HFP case distinguishes real preparation-level sugar conversion
from assignment to HFP: other preparations and host RpiA detection challenge the
assignment. Its reported mixture fractions do not provide a compatible
uncertainty radius. The following strong margin is therefore **synthetic**, not
a reconstruction of that paper: `m=100`, `h95=1` native rate units,
`H=100/101=0.990099`.

| Inference | R | V | A | T | H | E | C |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The contaminated signal establishes target-protein isomerization | 1 | 1 | 0 | 1 | 0.990099 | 0 | 0 |
| The assayed preparation catalyzes the observed conversion | 1 | 1 | 1 | 1 | 0.990099 | 0.990099 | 0.990099 |

Increasing the first signal a millionfold keeps `A=0`, hence `B_C=C=0`.
Increasing its measured precision has the same limit. The second result is a
different, narrower attribution. Zero positive contribution from the
contaminated signal is not proof of zero intrinsic target activity. Here `N=0`:
the contamination finding revises the attribution of the existing positive
observation; it does not manufacture an independent negative experiment proving
HFP lacks isomerase capacity. A later genuinely target-specific negative assay
could supply separate opposition within its demonstrated sensitivity and scope.

### B. A complement changes the dimension it addresses, once

The FtsW review distinguishes coupled polymer production from assignment of
catalysis to FtsW. Selective FtsW and partner controls address component
attribution. Use the counterpart's candidate grades `A=0.5` before and `A=1`
after those controls. For arithmetic, use **synthetic** fixed `m=4,h95=1`, so
`H=0.8`, with `R=V=T=1` in both rows:

| Evidence bundle | B_E=B_C | E=C | Independent groups |
| --- | ---: | ---: | ---: |
| Coupled product, component attribution unresolved | 0.5 | `0.5*0.8=0.4` | 1 |
| Same functional endpoint plus discriminating component controls | 1 | `1*0.8=0.8` | 1 |
| The control result is copied into another paper/database row | 1 | 0.8 | 1 |

There is one `A` transition and no new replication factor. The same rule would
put CsiD product identification primarily into the relevant endpoint-to-product
relation gap, rather than also awarding automatic validity and replication
bonuses. An additional unresolved native-system transfer would remain in `T`.

For another explicit partial repair, the counterpart assigns YeaG recovery-growth
failed-rescue `A=0.25` for K116A and `A=0.5` for K426A after considering their
64% versus 100% WT abundance. With **synthetic** `H=0.8,R=V=T=1`, contributions
are `0.20` versus `0.40`. Correcting the abundance concern does not assert that
folding, localization or selective catalytic loss is fully resolved. These are
recovery-growth comparisons; they are not relabeled as the later CFU endpoint.

### C. Precision and genuine independent replication both matter

All inputs here are **synthetic**. Use one native-rate inference with
`R=V=T=1,A=0.5`, hence `B_E=B_C=0.5`.

| Available evidence | Resolution calculation | E=C |
| --- | --- | ---: |
| One group, `m=4,h95=4` | `H=4/(4+4)=0.5` | `0.5*0.5=0.25` |
| One improved estimate of that group, `m=4,h95=1` | `H=4/(4+1)=0.8` | `0.5*0.8=0.40` |
| Original estimate plus one genuinely independent matching group, each `H=0.5` | `0.5*(1-(1-0.5)^2)` | 0.375 |
| Improved first estimate plus an independent `H=0.5` group | `0.5*(1-(1-0.8)*(1-0.5))` | 0.450 |
| Ten new source copies of the original single result | Same one group, `H=0.5` | 0.250 |

The improved estimate replaces the earlier estimate for current scoring; both
are not counted as independent data. If independence of the second experiment
is unknown, the two-original-estimate result is `[0.25,0.375]`, with no
established independent count of two. If technical repeats were the cause of
the smaller interval, their information is already in `H`, not added again.

### D. Repeating a proxy cannot erase its inferential limit

All numbers are **synthetic**, using the PopZ binding-versus-anchoring distinction
as the design challenge. For the broader inference, let
`R=0.25,V=A=T=1,H=0.8`. One result gives `C=0.2`. Three independent repetitions
give:

`C=0.25*(1-0.2^3)=0.248`, and even indefinitely many cannot exceed `0.25`.

Suppose a genuinely independent, direct endpoint then becomes available with
`B_C=1,H=0.1`. The exact piecewise calculation is:

`C=0.25*(1-0.2^3*0.9) + (1-0.25)*0.1 = 0.3232`.

The increment is `0.0752`, not an automatic upgrade of all proxy evidence to
direct evidence. Its experimental reliability can still be evaluated separately:
the original three valid binding results have
`E=1*(1-0.2^3)=0.992` for binding, while their contribution to the broader
anchoring inference is only `0.248`.

### E. Comparable contrary evidence reduces support

All measurements here are **synthetic** matched contrasts on the same endpoint,
subject and conditions. Let `R=V=T=1,A=0.5` for each independent group, with
`abs(m)=4,h95=1`, hence `H=0.8`.

| Evidence | E_plus | E_minus | E | K | P | N | C |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| One positive group | 0.40 | 0 | 0.40 | 1 | 0.40 | 0 | 0.40 |
| Add one equally resolved negative group | 0.40 | 0.40 | 0 | 0 | 0.40 | 0.40 | 0 |
| Two independent positive groups and one negative | 0.48 | 0.40 | 0.08 | `0.08/0.48=0.166667` | 0.48 | 0.40 | 0.08 |

The balanced case retains two individually valid results of reliability 0.40;
the scalar says their common inference is unresolved. A weak contrary result
with `H=0.5` instead gives `N=0.25` and reduces single-positive support to
`0.40-0.25=0.15`. None of these changes rewrites the earlier measured result
or an earlier completed-action yield.

### F. Different contexts do not create false contradiction

Use **synthetic** independent measurements of gene contribution in two declared
environments: low-sulfide/passaged condition `m=4,h95=1`, and a different
high-sulfide condition `m=-4,h95=1`. Suppose their other grades give `B_C=0.5`.
This is inspired by the ComF review's conditionality, not those paper's measured
effect sizes.

- For the low-sulfide conditional inference: `P=0.40,N=0,C=0.40`.
- For the high-sulfide conditional inference with the same directional wording:
  `P=0,N=0.40,C=0`.

The high-sulfide result is outside the first assertion's comparison scope, so it
does not create the balanced-conflict row from example E. A universal claim
would need to include and confront both conditions explicitly. Likewise,
shorter recovery lag and later survival loss are different endpoints and cannot
be treated as repeat signs of one response. An accumulation measurement and an
initial-rate measurement also do not become contradictory replications merely
because they suggest different practical interpretations.

### G. A tiny precise effect and a bounded nondetection

All quantities are **synthetic**, with `R=V=A=T=1` where the assay directly tests
the stated inference. Let a native rate be `0.010` with `h95=0.001`.

- For “detectable positive rate above the matched zero background,”
  `m=0.010,H=0.010/0.011=0.909091`, so `P=C=0.909091`.
- For “supplies the independently specified required flux of at least
  1 native rate unit under these same conditions,”
  `m=0.010-1=-0.990,H=0.990/0.991=0.998991`, so
  `N=0.998991,P=C=0`. This is reliable evidence against that adequacy claim.
- If no required flux has been established, the proposal does not manufacture
  1 as a biological threshold. A broader physiological inference instead keeps
  its missing implication visible in `R` or unknown inputs.

Separately, a **synthetic** calibrated nondetection upper bound of 1 native unit
can oppose a claim requiring at least 5 units, under the explicit qualitative
bound anchor `s=-1,H=0.75`. With the other grades equal to 1, `N=0.75`.
“Nondetected,” with no sensitivity bound, cannot receive that grade or refute all
nonzero activity. The missing sensitivity stays missing.

### H. Unknown target correspondence does not erase measured reliability

Take a **synthetic** actual-subject result with `R=V=A=1,H=0.8`. Its assayed-subject
reliability is `E=0.8`. If the supplied target has not yet been connected to that
assayed subject/system, `T=unknown`, represented as `[0,1]` for sensitivity:

`P=C=[0,0.8]`, with the known conditional upper case `0.8 if T=1`.

This is neither a default 50% applicability score nor zero target activity.
Native homology/structure/context and measured correspondence should be retained
in their own available numerical forms. A future justified interface value `t`
would give the conditional calculation `C=0.8*t`; this document supplies no
blanket grade ladder or conversion of those native values to `t`. Directly
matching the tested scope needs no transfer (`T=1`). A required correspondence
demonstrated incompatible supplies no positive transfer (`T=0`). The actual-
subject reliability stays 0.8 regardless of that unresolved target interface.

Missing information also does not null a separate known result. Suppose another
known positive experiment has `B_C=0.5,H=0.5`, contributing 0.25, and an
independent additional result has known `B_C=1` but unresolved `H in [0,1]`.
The combined contribution is `[0.25,1]`, not null or an automatic zero. If the
second result's actual observed evidence justifies `H in [0,0.8]`, the tighter
range is `[0.25,0.85]`, from
`0.5*(1-0.5*0.2)+0.5*0.8=0.85` at the upper endpoint. Those upper bounds are
explicit sensitivity cases, not new established measurements.

## 8. Adjustable choices, limitations and remaining review

The exact candidate above uses these declared settings:

| Policy choice | Default | What changing it would change |
| --- | --- | --- |
| Uncertainty scale `kappa` | 1 | Larger values reduce the quality index for the same native margin/uncertainty. It does not change the measured signal or interval. |
| Interpretation-factor exponents | All 1 | Optional strictly positive exponents in `R^a_R * V^a_V * A^a_A` and the corresponding `V,A` reliability product would change how intermediate grades restrict contribution. Zero remains zero. These exponents are not fitted here. The native-correspondence interface remains separately unresolved. |
| Independent replication accumulation | The explicit `Q` above | Sets diminishing returns within each maximum contribution. It is a policy choice rather than an experimentally identified sampling distribution. |
| Opposition strength `lambda` | 1 | Larger values make comparable contrary evidence reduce annotation support more; smaller values less. The raw `P,N` remain unchanged. |
| Qualitative `H` anchors | 0, 0.25, 0.50, 0.75 | Makes actual observed separation scorable without inventing unreported error bars. Anchors require user review across more examples. |

The proposal's most consequential assumptions are multiplicative interpretation
penalties, saturating independent increments, and symmetrical subtraction of
comparable opposing evidence. None is established by the retrospective corpus.
The proposal nonetheless supplies a complete calculation to accept, reject or
adjust; it does not stop at a list of dimensions or a claim that weights are
unjustified.

The compilation is intentionally scoped to a bounded inference/comparison. It
does not solve uncertainty about untested conditions by averaging them, infer
independence from publication count, or identify a native function from a small
precise artificial-substrate effect. Equal-grade products can conceal different
weaknesses, so the component sheet and named weakness links remain part of the
result. Many weak published results can still be affected by selection bias;
the independence rule is not a model of that bias. A shared untested assumption
must remain an interpretation limitation rather than being treated as another
independent random error.

Before adoption, the user can judge the grade spacing, qualitative anchors,
aggregation strength and cancellation policy on these explicit comparisons.
This document does not itself settle them, implement part 3 or complete W04.
