# A106: one persistent candidate's numerical contribution

2026-10-23. **Proposed research contract, not adopted policy.** This additive
document preserves all earlier sheets. It changes no prompt, production reader,
scorer, annotation, library or run. It does not mark any checklist item complete.
A105 remains first. The A105 source-pooling question remains unanswered.

## Goal and completion criteria

Supply the numerical reduction missing after A106 sheet 003: actual
perturbation/restoration operands → each scoped statement → one A106
contribution for one persistent candidate annotation.

This bounded deliverable is complete when it provides: (1) every intervening
sum, multiplier, denominator, sign and uncertainty operation; (2) numerical
consequences for zero correspondence, actual contrary findings, missing results,
shared observations and biological replication; (3) a full checked synthetic
multi-statement example; (4) exact additional cells and unimplemented functions
that populate them; and (5) the proposal's consequential conventions for judgment.
Reader implementation, scientific calibration and W05 consumption remain separate.

The three responsibilities remain: investigation prompt; numerical sheet; and
targeted readers/graders populating the sheet. No prompt is changed or invented
here. Investigation can start from supplied sequence, file selections or
snippets. Candidate statements can emerge afterward.

## 1. What this proposal retains and changes

Retain the native measurements, observation models, separate comparability and
isolation, molecular/system correspondence, two row modes and bounds in
../a106_perturbation_sheet_013/a106_numerical_sheet_003.md. Retain the parent's
tighter box calculation in
../a106_sheet_construction_001/A106_PARENT_NUMERICAL_REVIEW_001.md.

Replace, **only in this proposed candidate contract**, the current-roster 1/G
mean for assays of one exact statement. Add the missing candidate reduction.
This is an explicit alternative to sheet 003 section 6, not an interpretation
that the old mean already had these properties.

The old mean estimates the mean signed contribution of the selected experiments.
With one q=0.20412 experiment, its value is 0.20412. Adding an actually distinct
experiment with H=0 gives (0.20412+0)/2=0.10206. That decrease is mathematically
correct for an experiment-roster mean. It is undesirable if zero correspondence
means that the added experiment says nothing about this candidate. De-duplicating
reports alone cannot repair that denominator change.

## 2. Row calculations remain visible

For a restoration-effect row, with the definitions and admissibility conditions
of sheet 003:

    theta = (W-K)/(W+K)
    r = clip(1 - abs(R-W)/abs(W-K), 0, 1)
    C = product of the applicable distinct unintended-quantity agreements
    I = min(clip(1-B_pert/abs(W-K),0,1),
            clip(1-B_rest/abs(R-K),0,1))
    H = M * O
    a = orientation * theta * r * C * I
    q_point = H * a

Here a is only a factored intermediate of the existing row equation. It is not
another evidence axis, confidence scale or overall relevance judgment. W,K,R
and nuisance bounds retain endpoint units; C,I,M,O,H,a,q are dimensionless.
All original source measurements and each multiplier remain printable.

For a quantitative-necessity challenge:

    deficit = clip(theta_required - orientation*theta,0,1)
    I_cancel = clip(1-B_cancel/D_required,0,1)
    a = -deficit * P_effective * C * I_cancel
    q_point = H * a

The minimum must be entailed by that particular statement before interpreting
its test. A nonsignificant effect, a missing result or failed assay is not a
measured deficit. The positive restoration and necessity-challenge modes from
the same experiment are not two independent contributions to the same
statement. Choose the statement's estimand; preserve the other calculation as
a linked diagnostic or use it for a genuinely different statement.

## 3. Biological observations, assays and statements are different levels

First establish the experimental contribution identity from original sampling
units, controls, endpoint, conditions, constructs and measurement model.
Equal values do not establish duplicate identity; different articles do not
establish independent experiments.

1. Technical measurements estimate one biological unit. Their measurement model
   determines its value/uncertainty; they do not enlarge biological n.
2. Independent biological units under the same group sampling design enter that
   group's raw statistical calculation. They update its means, covariance and
   bounds. Reprinting them does not.
3. Distinct assay designs bearing on one exact statement form that statement's
   groups. Shared controls, samples or calibration retain their joint dependency.
   Splitting one design's technical wells or figure panels into groups is invalid.
4. Different necessary statements in a candidate become different leaves of its
   meaning. Their assay rosters are never put in one denominator.

Use one declared primary endpoint per group for one statement. Complementary
readouts that measure a nuisance or validate the observation model populate its
existing operands; they do not add another q. If the actual scientific estimand
is a specified equal mean of J endpoints, keep the existing explicit composite:

    q_g = sum_j(q_gj)/J
    H_g = sum_j(H_gj)/J
    a_g = sum_j(q_gj)/sum_j(H_gj), if sum_j(H_gj)>0

Then q_g=H_g*a_g exactly. If all H_gj=0, H_g=q_g=0 and a_g is unidentified.
J and its endpoint membership define that composite before inspecting scores.
If all endpoints are required, represent them as required statements instead:
an endpoint-average is a different claim. A weighted population-scope mean is
permitted only when it is the actual declared estimand, with fixed nonnegative
population weights summing to one substituted for 1/J and measured denominators
retained. Weights are not chosen to improve the score.

## 4. Proposed same-statement reduction

For statement i and its nonempty observed group roster G_i:

    T_i = sum_g H_ig
    d_i = max(1, T_i)
    N_i = sum_g q_ig = sum_g H_ig*a_ig
    Q_i_point = N_i/d_i

Every coefficient is one. H is the existing measured correspondence product,
not a new reader-assigned relevance grade. The fixed lower denominator 1
preserves one group's original contribution. It is the declared full-
correspondence normalization anchor, not an empirical sample count.

When T<=1, partially corresponding groups accumulate their signed attenuated
contributions. When T>1, Q is the H-weighted mean of the source-effect products
a. Consequently abs(Q)<=min(T,1)<=1. This is a bounded scoring convention,
not a probability, likelihood or dependence-corrected effective sample size.

The arithmetic has these explicit consequences:

| Addition/change | Consequence |
| --- | --- |
| One group with H in [0,1] | Q=q, preserving sheet 003's single-group meaning |
| Exact H=0 group | Adds zero to both N and T; Q unchanged |
| Duplicate report of existing observations | Does not alter group inputs or roster; Q unchanged |
| Independent biological replication | Changes the group's actual estimate/bounds; no extra report/group vote |
| Contrary q<0, with H>=0 | Lowers a previously positive Q; if already opposed it can dilute opposition toward zero but cannot create positive support by itself |
| Measured q=0 with H>0 | Can lower positive Q when d increases; this is a relevant null effect, unlike H=0 |
| Missing q with known H>0 | Remains an unknown interval contribution in N and a known denominator term; not deleted or replaced with zero |
| Unknown H | Propagates through numerator and denominator as the same uncertain quantity |

For positive Q before adding a contrary group, N falls and d cannot fall, so
Q strictly falls. Candidate support can remain unchanged if another required
statement was already the weaker one; it cannot increase merely from a negative
update to a leaf. The candidate example deliberately crosses that weaker-leaf
boundary so the support decrease is visible.

This recommendation deliberately differs from the pending A105 strongest-
positive-minus-strongest-negative proposal. It uses all distinct assays and
retains cancellation. The A105 proposal is neither imported nor described as
accepted.

**Tradeoffs requiring judgment, now numerical rather than undefined:** many
distinct weakly corresponding groups can raise support until T reaches one;
this is a declared scoring convention, not proof that transfer uncertainty
vanishes. A positive but weak group can lower Q when T>1. Assay grouping matters,
as it does for the old group mean. Shared dependence must be propagated; the
normalizer itself does not correct correlation. A full-correspondence group
with a small negative result remains influential even if many low-
correspondence positive results exist. No source-count or laboratory-reputation
bonus is added.

## 5. One candidate coordinate

The candidate record declares its actual scoped A106 statements and a nonempty
expression using canonical leaves, all_of and any_of. Leaves have specified
target material, condition/endpoint meanings and predicted direction. A105
reaction evidence is not recoded as perturbation evidence. No favorable
statement subset is selected after seeing scores.

    F(leaf i) = Q_i_point
    F(all_of children) = min(F(child) for child in children)
    F(any_of children) = max(F(child) for child in children)

All_of means the candidate actually requires every child. Any_of means any
child is sufficient for the same asserted meaning. Competing candidate
annotations are separate records, not an any_of used to select the winner.
Different assays of one statement go through section 4, not through any_of.

Min/max is a noncompensatory conventional reduction consistent with A105's
scoped-claim proposal; it is not a joint probability law. Duplicated clauses and
declared synonyms do not add support. The identities min(x,x)=max(x,x)=x and
max(x,min(x,y))=x give exact repetition and absorption behavior. Biological
entailment between differently worded claims still requires its actual semantic
basis; equal scores do not establish it. Empty all_of/any_of is unspecified
candidate meaning, not a vacuous perfect score.

The expression is the candidate's declared question for A106. Its other axis
questions are not silently scored here, and an annotation with no defined A106
question returns not_applicable/unavailable with no fabricated coordinate.
This proposal returns one axis contribution, not a global annotation hypervolume.

## 6. Complete uncertainty and missing-data contract

Maintain one shared variable for each primitive observation, fitted quantity
and correspondence relation. Keep the joint model and original primitive
identities with the expression. Do not combine already nearest-to-zero reduced
q values: evaluate signed points and propagate their measurement/model intervals
through the statement and candidate equations first.

The deterministic fallback below specifies all bound operations. It yields
outer enclosures when the actual joint admissible set is not rectangular.
It does not turn marginal 95% intervals into a simultaneous 95% interval.

1. The existing row reader supplies source-effect a bounds and H bounds from its
   declared joint model. Unknown source-effect factors retain the mathematical
   domain [-1,1], or [-1,0] for a necessity challenge; unknown H retains [0,1].
   These domain bounds are not measurements or statistical intervals.
2. For each statement, optimize the explicit fraction over those boxes, keeping
   the same H in numerator and denominator. Because it is nondecreasing in
   every a, fix all a at their lower endpoints for the lower result and all at
   their upper endpoints for the upper result.
3. For either fixed a vector, form V from every H-box vertex and every feasible
   intersection of sum(H)=1 with a box edge. An edge fixes all but one coordinate
   at a lower/upper endpoint and obtains the remaining coordinate by subtraction.
   Evaluate sum(H*a)/max(1,sum(H)) at every member of V. The minimum and maximum
   give the exact extrema for that H box: on each side of the hyperplane the
   expression is respectively linear or linear-fractional with positive
   denominator, whose extrema occur at vertices. The hyperplane vertices are
   included, so no undefined global optimization remains.
4. If groups explicitly reuse the exact same H variable, collapse to unique H_m
   before that enumeration: denominator max(1,sum_m n_m H_m), numerator
   sum_m H_m sum_{g in m} a_g. Enumerate intersections with sum_m n_m H_m=1.
   Other known covariance/shared constraints remain attached; relaxing them to
   their containing box is labeled conservative_outer, never independence.
5. Set each statement interval to the resulting [Q_iL,Q_iU]. Evaluate the
   candidate min/max expression once at all leaf lower bounds for F_L and
   once at all upper bounds for F_U. Monotonicity makes these valid outer
   bounds even when statements share data. Repeated leaves use the same leaf.
6. A tighter supplied joint bound can instead be used if its declared method
   evaluates this same candidate function on the same shared primitives.
   Finite joint scenarios are evaluated exhaustively. For the continuous
   synthetic example, analytic monotonicity proves the exact extrema.
   Record which enclosure was used; different enclosures can change the
   conservative score, as the A106 parent review already demonstrated.

Once this candidate interval is available:

    nearest_zero([L,U]) = L if L>0; U if U<0; 0 otherwise
    signed_A106 = nearest_zero([F_L,F_U])
    A106_coordinate = max(0,signed_A106)
    coordinate_identification_bounds = [max(0,F_L), max(0,F_U)]

Use these numerical signed/coordinate outputs when a nominal candidate
calculation is identified and its uncertainty enclosure is valid. A known
measurement interval crossing zero gives resolved support 0 and retains its
known point and interval. The uncertainty step happens once, at the candidate
boundary; intermediate resolved rows may be displayed but are not inputs.

When a necessary nominal input is missing, preserve F_point=null and the
coordinate as null unless its allowed coordinate image is a singleton. For
example F_U<=0 identifies coordinate=0 even if the signed value remains unknown.
Do not call the zero lower bound of [0,0.8] a completed score. An empty observed
roster for a required statement gives point=null, domain [-1,1], and no-data
status; it does not create a negative finding. Unknowns that are algebraically
absorbed by candidate meaning do not prevent an otherwise identified result.

An established H=0 yields an exactly zero candidate contribution for a row
whose source effect has a valid bounded domain, even if its nominal a is
unavailable. This is an algebraic identification, not an imputed measurement.
Unknown component cells remain unknown; an invalid endpoint model does not
become a valid experiment simply because a factor is zero.

Intervals are conditional on the actual bounds/model. Shared calibration,
controls and source-to-target uncertainty are never averaged away merely
because evidence is used for two statements. No score is labeled a posterior
function probability. The actual statement points and both positive/negative
numerator terms remain printable:

    positive_numerator = sum_g max(q_g,0)
    negative_numerator = sum_g max(-q_g,0)
    N = positive_numerator - negative_numerator

If desired for the same declared diagnostic as sheet 003:

    consistency = abs(N)/(positive_numerator+negative_numerator)

Its denominator-zero result is undefined; do not multiply it into Q again.

## 7. Persistence, competing candidates and revisions

The same fixed target material and persistent candidate identity receive new
evidence revisions. Recompute from the current unique observations and current
meaning; retain former input/result snapshots as history. Do not sum historical
scores or keep the largest historical result. Correcting a source replaces its
current mathematical input, while preserving the old record as superseded.

Independent alternative annotations have distinct candidate identities, even
for the same material. They each receive their own predicted orientations,
statements and coordinate. If a revision qualifies a condition or changes what
the candidate asserts, record that scope change: a higher score after narrowing
the claim is not new support for the old broader claim. No duplicate candidate
is created just because one candidate's evidence or wording was revised.

Useful contrary findings can improve the investigation while lowering its
annotation support. This contract does not score investigation progress, alter
continuation, or create a scientific acceptance/approval step.

## 8. Evidence trace and review limits

| Inspected mathematical source | Contribution retained or corrected |
| --- | --- |
| A106 numerical sheet 003, complete | Native row formulas, two nuisance bounds, C/M/O arithmetic, signed modes and missing-input domains retained |
| A106 reader IO 003 and final index, complete | Exact NumberCell, identities, mode aliases and unknown provenance retained; new population contract is additive |
| A106 parent review 001, complete | Shared-variable box bounds and enclosure sensitivity retained; candidate and roster-denominator gaps addressed here |
| A105 candidate review 008, complete | Scoped all_of/any_of semantics used as an explicitly proposed convention; source and candidate levels kept separate |
| A105 source pooling decision 009, complete | Pending strongest-side rule contrasted, not adopted |
| Required authority set | User template, native arithmetic, separate readers, additive records and fixed-target persistence govern this proposal |

No new primary paper or retained paper-specific packet was opened. Source tables
embedded in the mathematical reference sheets were read as part of those
documents; they were not independently reinterpreted as experimental evidence.
The YeaG/Cas2 source packets remain the earlier authors' empirical work, with
their missing quantities unchanged. The new complete example is explicitly
synthetic. This reduction supplies arithmetic; it does not complete source
validation, biological calibration, reader implementation or any evidence axis.
