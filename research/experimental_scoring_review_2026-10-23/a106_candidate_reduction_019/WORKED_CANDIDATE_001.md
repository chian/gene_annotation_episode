# Checked complete synthetic A106 candidate sheet

Every value below is invented for a mathematical example. These are not new
YeaG, Cas2, ybhP or other biological findings. The known sampling model and
validation bounds are fixture assumptions, not quantities inferred from a
paper or from the range of three observations.

## Candidate and experimental meaning

Supplied material is a complete invented 100-residue target T. A candidate
formed during investigation asserts:

**C-plus: T contributes positively to event X AND event Y under condition C.**

Both endpoints are validated events per 100,000 eligible cells in the same
defined time window. They are distinct contribution inferences A and B. The
candidate makes no catalytic-reaction claim. Orientation is +1 for both before
examining results. Its A106 expression is all_of(A,B).

The first assayed molecule is homolog H1 in a defined recipient. Matched
reference, selective perturbation and restoration arms use the same recipient,
condition, measurement model and eligibility denominator. The perturbed arm has
no coexisting WT copy. The intended change reduces relevant component capacity;
the restored construct adds it back. Its dosage difference is an unintended
comparison component. Endpoints X and Y come from the same biological blocks.
They are not independent experiments merely because two readouts exist.

## Full input sheet: shared group G1

| Independent biological block | W_X | K_X | R_X | W_Y | K_Y | R_Y |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| b1 | 98 | 18 | 88 | 78 | 38 | 73 |
| b2 | 100 | 20 | 90 | 80 | 40 | 75 |
| b3 | 102 | 22 | 92 | 82 | 42 | 77 |
| Arithmetic means | 100 | 20 | 90 | 80 | 40 | 75 |

There is one technical observation per endpoint/arm/block. Measurement values
are already validated and have no remaining blank or calibration correction.
The fixture specifies a known-normal common block error: each vector equals
its population vector plus epsilon_b times the six-entry vector of ones, with
epsilon_b independent across biological blocks and distributed N(0,4).
The covariance of one vector is 4 times the 6-by-6 all-ones matrix. This is a
known fixture model; sample SD=2 for the first three observations is not being
treated as known population SD. For the sample-mean vector, every covariance
entry is 4/n. No off-diagonal entry is discarded.

The true vector in the simultaneous interval is the displayed mean vector plus
one common delta. With alpha=0.05 and z=Phi_inverse(0.975):

    z = 1.9599639845400536
    t_n = z*2/sqrt(n)
    delta in [-t_n,t_n]
    t_3 = 2.263171468152343

Because the model has one common unknown error, this single normal interval is
simultaneous for the six means. It is not six unrelated 95% intervals. It
conditions on the fixture's known error model. All contrasts keep their
differences throughout this interval.

| Other native input | X | Y | Meaning |
| --- | ---: | ---: | --- |
| Reference protein amount | 100 | same measurement | molecules per cell |
| Restored protein amount | 90 | same measurement | molecules per cell; C=90/100=0.9 |
| Nuisance-only perturbation bound | 8 | 4 | endpoint units; exact fixture bounds including interactions |
| Nuisance-only restoration bound | 7 | 3.5 | endpoint units; exact fixture bounds including interactions |
| Relevant reference capacity | 100 | same measurement | capacity units |
| Perturbed relevant capacity | 5 | same measurement | residual fraction 0.05; P_effective=0.95, reported but not multiplied into this positive-effect mode |

These bounds are actually supplied for the fixture's entire nuisance set.
No off-target bound is inferred from an absent description.

One measured correspondence relation connects this assayed material to T:

    scope coverage = 90 aligned target residues / 100 target residues = 0.9
    identity = 72 identical pairs / 90 nongap aligned pairs = 0.8
    determinant agreement = 3 retained / 4 required determinants = 0.75
    M = 0.9*0.8*0.75 = 0.54

The experiment's source context frequencies are (1,0). Target frequencies in
the same scoped condition partition are (o,1-o), with measured nominal o=0.8
and stipulated deterministic validation bounds o in [0.7,0.9]. Thus O=o and
H=0.54o is the same shared variable for both inferences:

    H_point = 0.432
    H_bounds = [0.378,0.486]

No second correspondence measurement or uncertainty reduction arises from
using this relation for two statements. Its bounds do not shrink when n grows.

## Native factors to signed rows

| Calculation | Inference A, event X | Inference B, event Y |
| --- | ---: | ---: |
| W,K,R | 100,20,90 | 80,40,75 |
| D=W-K | 80 | 40 |
| theta=D/(W+K) | 2/3 | 1/3 |
| Raw restored fraction | 70/80=0.875 | 35/40=0.875 |
| r | 0.875 | 0.875 |
| C | 0.9 | 0.9 |
| I_pert | 1-8/80=0.9 | 1-4/40=0.9 |
| I_rest | 1-7/70=0.9 | 1-3.5/35=0.9 |
| I=min(I_pert,I_rest) | 0.9 | 0.9 |
| a=s*theta*r*C*I | 189/400=0.4725 | 189/800=0.23625 |
| H | 0.432 | same 0.432 |
| q=H*a | 5103/25000=0.20412 | 5103/50000=0.10206 |

Using the same primitive variables through the full sampling region gives:

    q_A1(H,delta) = 56.7*H/(120+2*delta)
    q_B1(H,delta) = 28.35*H/(120+2*delta)

They are perfectly linked in this fixture: q_A1=2*q_B1. Treating them as
independent likelihood contributions would invent precision and contribution.

With only G1, each statement's denominator is 1. C-plus therefore has nominal
min(0.20412,0.10206)=0.10206. Both functions increase with H and decrease with
delta. Its exact stipulated-region interval is:

    [0.08605649011535974, 0.11931812285463511]

Nearest-to-zero candidate support is **0.08605649011535974**.

## A genuinely contrary assay for the same statement

A different source molecule H2 is assayed in another independent design for
the same event-X statement and condition scope. It is group G2 for A, not a
third required statement. Its exact synthetic population/validation operands
are:

| Native input or factor | Value and arithmetic |
| --- | --- |
| W,K,R | 60,100,70 events per 100,000 cells |
| Intended perturbation / coexistence | Same component-reduction question; no coexisting WT |
| D | -40 |
| theta | -40/160=-1/4 |
| r | 1-abs(70-60)/40=3/4 |
| Restored/reference protein amount | 80/100; C=0.8 |
| B_pert,B_rest | 0,0 endpoint units, exact supplied fixture bounds |
| I | 1 |
| Source-to-target scope coverage | 100/100=1 |
| Sequence identity | 80/100=0.8 |
| Required determinant multiplier | Inapplicable for this explicitly stated inference; identity multiplier 1 |
| M,O,H | 0.8,1,0.8 |
| a | (-1/4)*(3/4)*0.8*1=-0.15 |
| q_A2 | -0.15*0.8=-0.12=-3/25 |

These are exact synthetic inputs for the contrast, not empirical claims of
zero variance or flawless control. Restoration returns the increased
perturbed endpoint toward reference, so it specifically supports the opposite
effect direction relative to C-plus. A measured opposite sign is not missing
data or a mere absence of support.

## Complete candidate reduction after the contrary result

For A:

    T_A = 0.432 + 0.8 = 1.232
    d_A = max(1,1.232) = 1.232
    positive_numerator = 0.20412
    negative_numerator = 0.12
    N_A = 0.20412 - 0.12 = 0.08412
    Q_A_point = 0.08412/1.232
              = 2103/30800 = 0.06827922077922077

For B:

    T_B = 0.432
    d_B = 1
    N_B = 0.10206
    Q_B_point = 0.10206

The candidate's nominal signed value is:

    F_point = min(Q_A_point,Q_B_point)
            = 2103/30800 = 0.06827922077922077

The same joint variables, not independent interval copies, enter:

    Q_A(H,delta) = [56.7*H/(120+2*delta) - 0.12]/(H+0.8)
    Q_B(H,delta) = 28.35*H/(120+2*delta)
    F(H,delta) = min(Q_A(H,delta),Q_B(H,delta))

H+0.8>1 everywhere in this fixture. For k=56.7/(120+2delta)>0,
dQ_A/dH=(0.8k+0.12)/(H+0.8)^2>0; dQ_A/ddelta<0. Q_B has the same monotonic
directions. The minimum therefore has its lower extreme at H=0.378,
delta=+t_3 and upper extreme at H=0.486,delta=-t_3. This proof, not a grid
search, establishes the exact interval for the declared rectangle:

| Bound | q_A1 | Q_A | Q_B | Candidate min |
| --- | ---: | ---: | ---: | ---: |
| Lower | 0.17211298023071947 | 0.04423852311606068 | 0.08605649011535974 | 0.04423852311606068 |
| Upper | 0.23863624570927022 | 0.09225213507719301 | 0.11931812285463511 | 0.09225213507719301 |

The single uncertainty-resolved candidate contribution is therefore
**A106_coordinate=0.04423852311606068**, with nominal
0.06827922077922077 and interval
[0.04423852311606068,0.09225213507719301].

There is one normal-error interval plus the deterministic transfer bounds. The
95% coverage statement is conditional on that fixture model, not a probability
that the annotation is correct. No second row-level uncertainty factor is
multiplied into this result.

## Replication, duplication and zero correspondence

A second batch supplies independent biological blocks b4,b5,b6 with the same
six numerical vectors as b1,b2,b3. Their different values are not required for
independence; the fixture explicitly stipulates distinct biological units and
independent epsilon errors. There are now six unique vectors. Means stay the
same, while the covariance of each pair of sample-mean components changes from
4/3 to 4/6=2/3. The exact statistical input changes:

    t_6 = 1.6003038921184365
    H interval remains [0.378,0.486]
    candidate interval =
       [0.04581073927568406,0.09014587678339729]
    A106_coordinate = 0.04581073927568406

Independent replication thus improves the conservative contribution by reducing
sampling uncertainty. It does not add a third source or sixth group. Reprinting
the original b1,b2,b3 in a second article leaves n=3, covariance=4/3 and the
original 0.04423852311606068 result unchanged. If new biological data changed
the mean adversely, replication could lower the score; it is not a mandatory
positive bonus.

An actually distinct additional design G0 has W=100,K=20,R=90, C=0.9,
B_pert=8,B_rest=7, and a=0.4725, but O=0 from disjoint measured source/target
context distributions, so H=q=0. Adding it to A adds zero to both N and T.
The candidate remains 0.04581073927568406 after the six-block revision.
Under the old 1/G mean, the single original 0.20412 row would instead fall to
0.10206 after this addition. This is a real estimand difference, not duplicate
handling or numerical roundoff.

## Measured zero, missing result and necessity challenge

These separate arithmetic contrasts use the original exact nominal G1 row
q=0.20412,H=0.432 to isolate the consequence; they do not overwrite the preceding
candidate's evidence.

| Addition to the same statement | Exact proposed output | Meaning |
| --- | --- | --- |
| H=0,q=0 | 0.20412 | No correspondence; no denominator dilution |
| H=0.8, measured exact source effect a=0 | 0.20412/1.232=0.16568181818181818 | Relevant measured zero reduces the normalized mean; it is not counterevidence to an unspecified minimum |
| H=0.8, source effect unavailable in [-1,1] | Point null; interval [-0.4836688311688312,0.8150324675324675] | A missing result is neither a measured zero nor a negative observation |

For the measured-zero row, validated W=K=R=100 makes theta=0; restoration and
isolation ratios at D=0 remain undefined diagnostics. The zero-effect branch
identifies its bounded effect contribution as zero. An unknown or censored
W-K would not justify this exact point.

The existing fully numerical necessity challenge provides a distinct valid
negative, copied as arithmetic input rather than a new observation:

    W=100; K=97; theta=3/197
    required endpoint loss=50; D_required=50; theta_required=1/3
    theta interval=[-0.02,0.05]
    residual relevant capacity=5/100; P_effective=0.95
    B_cancel=5; I_cancel=0.9; C=H=1
    q_point=-(1/3-3/197)*0.95*0.9=-0.2719796954314721
    q interval=[-0.3021,-0.24225]

As one group for the exact quantitative-necessity statement, d=1. A candidate
requiring that statement has coordinate 0, with its negative signed interval
retained. This contradicts that minimum; it does not prove absence of every
possible role. If relevant residual capacity were unmeasured, its point would
be null and its allowed negative interval would reach zero. One cannot report
the fully resolved -0.24225 counterevidence from the missing capacity.

## Shared missing input and distinct candidate identities

If the common target-context overlap o is unavailable, preserve H_point=null
and H in [0,0.54]. Recompute both statements with that one shared variable.
With the same three-block interval and contrary group, F has outer/exact
rectangle interval [-0.12,0.10832192844881446]. Its point is null and coordinate
is null with bounds [0,0.10832192844881446]. Choosing 0.8, averaging two copies,
or silently dropping the unknown transfer would invent information.

C-minus is a distinct competing candidate asserting suppression of X and
promotion of Y. Its A orientation is -1, so its Q_A is the negative of C-plus's
Q_A, with the same sources and denominators. Its nominal min is
-0.06827922077922077 and interval
[-0.09225213507719301,-0.04423852311606068]; its coordinate is 0.
C-plus's score is not replaced by max(C-plus,C-minus).

A genuinely disjunctive third statement, “T contributes positively to at least
one of X or Y,” would use any_of(A,B). That is a different assertion, not an
alternative pooling method for C-plus. Its nominal value here is 0.10206,
and its three-block interval is
[0.08605649011535974,0.11931812285463511].

| Persistent C-plus evidence revision | Nominal F | A106 coordinate | What changed |
| --- | ---: | ---: | --- |
| r1: shared G1, three blocks | 0.10206 | 0.08605649011535974 | Two required inferences from shared measurements |
| r2: add contrary G2 for A | 0.06827922077922077 | 0.04423852311606068 | Actual contrary evidence |
| r3: add independent b4-b6 to G1 | same | 0.04581073927568406 | Actual statistical input and precision |
| r4: duplicate representation | same | same | No new observations |
| r5: add distinct H=0 group | same | same | No correspondence to this candidate |

These are revisions of the same candidate, not five candidate annotations or
five support contributions. Historical snapshots remain preserved. The
arithmetic checker records exact rational point calculations and floating
normal-quantile bounds separately.
