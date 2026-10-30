# A106 filled examples under the current proposal

All complete scores in this document use invented inputs and declared synthetic
models. They are not YeaG, Cas2, ybhP or new experimental observations. Published
subcomponents are printed separately in the [source assessment](SOURCE_COVERAGE_AND_COMPLETION_028.md).
The [current sheet](A106_NUMERICAL_SHEET_028.md) defines every operation. Existing
arithmetic receipts are reused with their meanings intact; this consolidation
does not manufacture additional checks or reinterpret historical scores.

## One complete restoration row and its deterministic box

The statement is that the component promotes an event in a fixed condition.
Endpoint units are validated events per 100,000 eligible cells in one time
window. Reference, selective reduction and restoration share the recipient and
measurement model; the perturbed arm has no coexisting WT copy. The intended
capacity reduction is excluded from comparability. Restored dosage is an
unintended comparison difference.

| Actual synthetic input | Value, unit and denominator |
| --- | --- |
| Three independent matched biological blocks | `(W,K,R)=(98,18,88),(100,20,90),(102,22,92)` events per 100,000 cells; one technical measurement per arm/block |
| Population means used at the point | `W=100,K=20,R=90` |
| Joint rectangular validation set | `W∈[98,102],K∈[18,22],R∈[88,92],B_pert∈[6,10]`; deterministic fixture bounds, not confidence intervals inferred from the three rows |
| Nuisance bounds | `B_pert=8` nominal; `B_rest=7` exact, same endpoint units; both cover the fixture's stated nuisance set including interactions |
| Restored/reference amount | `90/100` molecules per cell, exact fixture ratio |
| Relevant perturbed/reference capacity | `5/100` capacity units; `P_effective=.95`, reported but not multiplied into positive restoration |
| Molecular correspondence | 90 aligned target residues / 100 scope residues; 72 identical / 90 nongap pairs; 3 preserved / 4 required determinants |
| Scoped system distributions | Source `(1,0)`, target `(.8,.2)`, exact fixture frequencies |
| Orientation | `s=+1`, fixed by the promoting-function statement |

| Numerical cell | Calculation | Result |
| --- | --- | ---: |
| `D` | `100-20` | 80 endpoint units |
| `theta` | `80/120` | 0.666666666666667 |
| `restoration_fraction_raw,r` | `70/80`; `1-10/80` | 0.875 each |
| `C` | `90/100` | 0.9 |
| `I_pert` | `1-8/80` | 0.9 |
| `I_rest` | `1-7/70` | 0.9 |
| `I` | `min(.9,.9)` | 0.9 |
| `M` | `(90/100)*(72/90)*(3/4)` | 0.54 |
| `O` | `min(1,.8)+min(0,.2)` | 0.8 |
| `H` | `.54*.8` | 0.432 |
| `a` | `(2/3)*.875*.9*.9` | 0.4725 |
| `q_point` | `.432*.4725` | **0.20412** |

For this box, the whole region has `W>R>K>0`. Preserving the same primitive
values in each factor gives the exact simplified function:

```
q = .3888/(W+K) * min((R-K)*(1-B_pert/(W-K)), R-K-7)
```

The parent review proves both branches increase with `R` and decrease with
`W,K,B_pert` throughout this particular box. The exact extrema are:

| Bound type | Lower | Upper | Meaning |
| --- | ---: | ---: | --- |
| Current tight box image | `56133/310000 = .1810741935483871` | `16281/72500 = .2245655172413793` | Exact for the stipulated rectangle; lower at `(102,22,88,10)`, upper at `(98,18,92,6)` |
| Earlier factor-by-factor enclosure | .176418 | .233766 | Valid but loose outer enclosure of the same rectangle |

For a candidate consisting of this one statement/group, `T=.432,d=1` and the
nominal candidate is `.20412`. The proposed nearest-to-zero rule gives
**.1810741935483871** using the tight box. The historical `.176418` used the
looser enclosure. This difference reflects arithmetic enclosure quality, not a
new measurement or changed model. Neither is a confidence probability.

Evidence: [parent review and analytic argument](../a106_sheet_construction_001/A106_PARENT_NUMERICAL_REVIEW_001.md)
and its [176-assertion receipt](../a106_sheet_construction_001/parent_arithmetic_001.json).
Many of those assertions are repeated grid cases; they are not 176 distinct
scientific validations. The proof, not grid sampling alone, establishes extrema.

## One candidate with two required statements, shared data and contrary evidence

Candidate C-plus says: **the invented target T promotes event X AND event Y
under condition C**. T is a complete supplied 100-residue target. Both endpoints
are events per 100,000 eligible cells under the same defined time window. The
expression is `all_of(A,B)` with orientation +1 for both. This is not an
enzyme-reaction claim. Source molecule H1 is investigated in a matched recipient
using reference, reduction and restoration arms with no coexisting WT copy in
the perturbed arm.

| Independent biological block | `W_X` | `K_X` | `R_X` | `W_Y` | `K_Y` | `R_Y` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| b1 | 98 | 18 | 88 | 78 | 38 | 73 |
| b2 | 100 | 20 | 90 | 80 | 40 | 75 |
| b3 | 102 | 22 | 92 | 82 | 42 | 77 |
| Means | 100 | 20 | 90 | 80 | 40 | 75 |

There is one technical reading per cell. Values are already validated without
remaining blank correction. A **stipulated known-error model** says each
six-entry vector equals its population vector plus a common `epsilon_b`
times the all-ones vector, with independent `epsilon_b∼N(0,4)` across biological
blocks. The entire block covariance is `4*J_6` and mean covariance is `4*J_6/n`;
off-diagonals are retained. This population variance is a fixture assumption,
not inferred as known from the three sample values.

The simultaneous mean region adds one shared `delta` to all six means:

```
z = Phi_inverse(.975) = 1.9599639845400536
t_n = z*2/sqrt(n)
delta ∈ [-t_n,t_n]
t_3 = 2.263171468152343
```

One normal interval supplies conditional 95% joint coverage because the model
has one common mean-error variable. It is not six independent 95% intervals.

For X/Y respectively, `B_pert=8/4` and `B_rest=7/3.5` endpoint units are exact
fixture nuisance bounds including interactions. One shared protein measurement
gives restored/reference amount `90/100`, hence `C=.9`; capacity `5/100` gives
reported `P_effective=.95`. Molecular correspondence is the same `.54` as above.
The source frequencies are `(1,0)` and target frequencies `(o,1-o)`, with
nominal `o=.8` and **stipulated deterministic** bounds `[.7,.9]`. Thus the
same `H=.54*o` enters both statements: nominal `.432`, bounds `[.378,.486]`.
These bounds do not shrink with biological replication.

| Cell | A: event X | B: event Y |
| --- | ---: | ---: |
| `W,K,R` | 100,20,90 | 80,40,75 |
| `D,theta` | 80,2/3 | 40,1/3 |
| `r,C,I_pert,I_rest,I` | .875,.9,.9,.9,.9 | .875,.9,.9,.9,.9 |
| `a` | `189/400=.4725` | `189/800=.23625` |
| Shared `H` | .432 | .432 |
| `q_point` | `5103/25000=.20412` | `5103/50000=.10206` |

The exact shared functions are `q_A1=56.7*H/(120+2*delta)` and
`q_B1=28.35*H/(120+2*delta)`. They are linked by `q_A1=2*q_B1`.
Before contrary evidence, each denominator is 1. The candidate point is
`.10206`, interval `[.08605649011535974,.11931812285463511]`, and conservative
coordinate **.08605649011535974**.

An independent assay design G2 on source molecule H2 addresses the **same A
statement**, not a third required statement. Its exact invented values are:

| Input/cell | Value and calculation |
| --- | --- |
| Endpoint means | `W=60,K=100,R=70`, same events/100,000-cell scale and scope |
| Intended change/coexistence | Component reduction; no coexisting WT copy |
| Effect and restoration | `theta=-40/160=-.25`; `r=1-10/40=.75` |
| Comparability | Restored/reference amount `80/100`; `C=.8` |
| Isolation | Supplied `B_pert=B_rest=0`; `I=1` within this exact fixture |
| Correspondence | Coverage `100/100`, identity `80/100`, determinants explicitly inapplicable; `M=.8,O=1,H=.8` |
| Signed row | `a=(-.25)*.75*.8=-.15`; `q_A2=.8*(-.15)=-.12` |

Restoration returns the increased perturbed endpoint toward reference. It
therefore supports the opposite direction to C-plus. It is an observed contrary
result rather than an unavailable result or generic absence of support.

```
T_A = .432+.8 = 1.232; d_A = 1.232
positive_numerator_A = .20412; negative_numerator_A = .12
N_A = .08412
Q_A_point = .08412/1.232 = 2103/30800 = .06827922077922077
T_B = .432; d_B = 1; Q_B_point = .10206
F_point = min(Q_A_point,Q_B_point) = .06827922077922077
```

The full shared candidate function is:

```
Q_A(H,delta) = [56.7*H/(120+2*delta)-.12]/(H+.8)
Q_B(H,delta) = 28.35*H/(120+2*delta)
F(H,delta) = min(Q_A,Q_B)
```

`H+.8>1` throughout this region. Both statement functions increase with `H`
and decrease with `delta`. For `k=56.7/(120+2*delta)>0`,
`dQ_A/dH=(.8*k+.12)/(H+.8)^2>0`. Thus their minimum has its extrema at
`(.378,+t_3)` and `(.486,-t_3)`; no favorable independent copies of shared
quantities are selected.

| Candidate value | Exact-region result |
| --- | ---: |
| Nominal | .06827922077922077 |
| Lower | .04423852311606068 |
| Upper | .09225213507719301 |
| One nearest-to-zero, then positive part | **.04423852311606068** |

The interval combines the conditional normal-error region with deterministic
transfer bounds. The 95% statement is conditional on that known fixture model,
not the chance the annotation is correct. The point and conservative coordinate
are not two contributions to add. No row-level uncertainty multiplier is applied
again. Evidence: [complete original example](../a106_candidate_reduction_019/WORKED_CANDIDATE_001.md),
[worker arithmetic](../a106_candidate_reduction_019/ARITHMETIC_RESULTS_001.json)
and [15 parent checks](../a106_sheet_construction_001/candidate_reduction_parent_arithmetic_002.json).

## Replication, duplicate reports, null results and candidate meaning

Three additional **synthetically stipulated independent biological blocks**
b4–b6 have the same numerical vectors as b1–b3. Distinct experimental identities
and the independent error model, not unequal values, establish independence.
The six-block means are unchanged. Mean covariance becomes `4*J_6/6` from
`4*J_6/3`, `t_6=1.6003038921184365`, while `H` remains in `[.378,.486]`.
The candidate interval is `[.04581073927568406,.09014587678339729]` and its
coordinate becomes **.04581073927568406**. Actual adverse means could instead
lower support; replication earns no automatic positive bonus.

| Revision/contrast | Current consequence |
| --- | --- |
| Duplicate report of b1–b3 | Still n=3; original .04423852311606068 coordinate |
| Add a distinct design with exact `H=0` | Adds 0 to `N,T`; current candidate unchanged |
| Add `H=.8,a=0` to the original exact single row | `.20412/1.232=.16568181818181818`; relevant measured zero can change the normalizer |
| Add `H=.8,a` unavailable in [-1,1] to that exact single row | Point null; statement interval `[-.4836688311688312,.8150324675324675]`; coordinate null |
| Shared target context unavailable, `H∈[0,.54]`, in the three-block candidate with contrary G2 | Point/coordinate null; candidate interval `[-.12,.10832192844881446]`, coordinate bounds `[0,.10832192844881446]` |
| Distinct C-minus: repress X AND promote Y | Nominal `-.06827922077922077`; interval `[-.09225213507719301,-.04423852311606068]`; coordinate 0 |
| Genuinely different assertion “promotes X OR Y” | `any_of(A,B)` gives point .10206 and interval `[.08605649011535974,.11931812285463511]` |

The measured-zero example has exact validated `W=K=R=100`. `theta=0` identifies
its bounded source effect as 0; restoration/isolation `0/0` cells remain
undefined. Uncertain or censored differences do not justify that exact point.
Different candidate meanings cannot be merged by choosing the maximum score.
Historical revisions of C-plus are neither separate candidates nor new evidence.

## Complete quantitative necessity challenge

The statement requires at least 50% loss of the endpoint after the specified
molecular perturbation, from reference `W=100`. Thus `K_required=50`,
`D_required=50` endpoint units and `theta_required=1/3`. These minima belong
to the statement before interpreting the test. Observed `W=100,K=97` gives
`theta=3/197`; a stipulated joint analysis gives `theta∈[-.02,.05]`.
Relevant residual capacity is `5/100`, so `P_effective=.95`; a nuisance
cancellation bound of 5 endpoint units gives `I_cancel=1-5/50=.9`.
The exact synthetic target/system has `C=H=1`.

```
deficit_point = 1/3 - 3/197 = 188/591
a = q_point = -(188/591)*.95*.9 = -.2719796954314721
deficit_bounds = [17/60,53/150]
q_bounds = [-.3021,-.24225]
```

One group has `d=1`. A candidate requiring this necessity statement has signed
A106 `-.24225` and coordinate **0**, with the opposing interval retained.
It contradicts the specified minimum, not every possible function. Unknown
relevant residual capacity leaves the signed point unresolved; one cannot
retain the fully resolved `-.24225` merely from an amount or mutation label.

Evidence: [revision-003 boundary receipt](../a106_perturbation_sheet_013/arithmetic_results_003.json)
and [parent arithmetic](../a106_sheet_construction_001/parent_arithmetic_001.json).
Cas2's retained qualitative “detectable acquisition” observation cannot fill
this synthetic challenge because the numerical acquisition interval and relevant
residual activity are absent.
