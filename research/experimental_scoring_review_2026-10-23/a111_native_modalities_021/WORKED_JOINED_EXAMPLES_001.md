# Complete joined synthetic examples and published partial rows

All operands in the first two examples are explicitly synthetic. They are not new measurements of TRPV1, DkTx or the project's target. The numerical inputs are complete so the defined arithmetic can be checked. They do not establish empirical calibration or an accepted scoring policy.

## Cryo-EM: two independent synthetic datasets, one has two equivalent copies

Declared elementary question: the mapped local feature has four contact distances in [2.5,3.5] Å. The incompatible event is a fourth contact distance≥4.0 Å. There is one family and one elementary question, α=β=1. Distances between 3.5 and 4 Å would not silently be assigned either event. Source/target material is the supplied synthetic selected site `DY`→`DF`, with the explicit correspondence position1→1 and position2→2. Required source roles are Asp OD1, Asp OD2, Tyr aromatic CZ, and Tyr phenolic OH. The target retains the first three; Phe lacks phenolic OH. Thus K=4,c=3,d=1,u=0 and T=3/4. This is an actual supplied synthetic mapping, not a generic similarity number.

The local Q panel contains both source residues, covering all four distance endpoints. The four declared geometric operands are Asp OD1–Tyr OH, Asp OD2–Tyr OH, Asp OD1–Tyr CZ and Asp OD2–Tyr CZ. The numbers below are synthetic local coordinate-measurement outputs. All fixed endpoints are retained even when a geometric condition fails.

Dataset E1 has 80 eligible objects under the synthetic complete-sampling design and 60 observed in the selected feature state: q=60/80=.75. An independent attribution measurement bounds contributions from a specified other component at B=12 of those Y=60 objects, so I=1−12/60=.8. These counts are not selected cryo-EM class percentages with an unknown sampling denominator. Compared to the declared reference condition, measured pH is 7.5 versus 7.0 and temperature 298.15 K versus 298.15 K. The deliberately studied state is excluded from the nuisance list. Explicit proposed scales are τ_pH=1.0 pH unit and τ_temp=10 K:

`C=[exp(−.5²/(2×1²)) × exp(−0²/(2×10²))]^(1/2)=exp(−.0625)=.9394130628134758`.

| Row | q | Q panel | D | G distances, Å | G | T | C | I | h | Full product w |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E1 equivalent copy a | .75 | .80,.90 | .64 | 2.8,3.0,3.2,4.2 | 3/4 | .75 | .939413062813476 | .8 | +1 | .202913221567711 |
| E1 equivalent copy b | .75 | .70,.95 | .49 | 2.8,3.0,3.2,3.4 | 1 | .75 | .939413062813476 | .8 | +1 | .207140580350371 |
| E2 independent dataset | .50 | .60,.90 | .36 | fourth contact=4.5 | 1 for incompatible event | .75 | 1 | 1 | −1 | .135000000000000 |

For E2, q=40/80 eligible objects; the same role mapping applies. Both nuisance variables exactly equal the reference, so C=1. A synthetic attribution bound B=0 for Y=40 gives I=1. E2's fourth-distance event is an explicit contradiction, not a failed extraction assigned zero.

First reduce equivalent E1 copies over **their products**:

`w_E1=(.20291322156771086+.2071405803503714)/2=.20502690095904114`.

E1 and E2 have separate actual raw-dataset/preparation identities in this synthetic design; each is its own dependence cluster. Therefore:

\[
P=(.20502690095904114+0)/2=.10251345047952057,
\]
\[
O=(0+.135)/2=.0675,\quad Z=.035013450479520564,\quad A=.035013450479520564.
\]

The optional 100× display is 3.5013450479520564. The two copies are one dataset, not two experimental replicates. A paper table or alternate rendering of E1 has zero additional weight. Adding a third otherwise eligible cluster with known T=0 changes Z to .02334230031968037 under the original mean reducer. This illustrates its roster dependence; the reducer is not changed here.

## NMR: complete model-conditional scalar with explicit opposition

Declared question: both named local proton contacts are≤5 Å; the incompatible event is both>5 Å. Two synthetic independent solution preparations provide separately assigned NOE restraints and models. One model per experiment is explicitly selected for a model-conditional calculation; this is not a population average. Thus q=C=I=1 have the original conditional meanings. No conformer count or peak count estimates q. There is one family/question, α=β=1.

Synthetic supplied source site `WK` maps positionwise to target `WR`. The three required local roles are the Trp indole proton/atom group, the second residue's backbone HA position, and the Lys NZ terminal-ammonium group. Trp and the backbone role are retained; Arg lacks the stipulated Lys NZ group. The role predicate is this exact chemistry, not arbitrary functional equivalence of any positive charge. Therefore K=3,c=2,d=1,u=0 and T=2/3. The two source contact endpoints are Trp HE1–Lys HZ1 and Trp HD1–Lys HA; their assignments are synthetic single-proton selections with no ambiguous averaging.

| Dataset/event | Native bounds for two restraints, Å | Model distances, Å | Violations, Å | Individual s with τ=.50 Å | D | G | w=qDGT CI |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| N1 supporting portion | [0,4],[0,5] | 4,5.5 | 0,.5 | 1,.6065306597126334 | .8032653298563167 | 1/2 | .26775510995210555 |
| N2 incompatible event | [0,5],[0,6] | 5.25,6.75 | .25,.75 | .8824969025845955,.3246524673583497 | .6035746849714726 | 1 | .402383123314315 |

N1 has one of its two declared positive geometric predicates satisfied; this is the original fractional G, not a claim that both passed. N2's two distances both meet the separately declared incompatible event. The positive and negative means use the same two-cluster denominator:

\[
P=.26775510995210555/2=.13387755497605278,\quad
O=.402383123314315/2=.2011915616571575,
\]
\[
Z=-.06731400668110474,\qquad A=0.
\]

The opposition is retained even though the nonnegative display coordinate is zero. This example demonstrates model-conditional structural arithmetic only; it does not establish a physiological population or make a catalytic claim. If additional admitted models were present without physical weights, they would become complete-product scenarios with an envelope, not extra clusters.

## Published cells stay partial where measurements or target roles are absent

| Published case / scope | Measured native observation | Derived D | G | q,C,I scope | T | Source-to-target result |
| --- | --- | ---: | ---: | --- | --- | --- |
| Cao 3J5Q, two G643 diagonal pairs | local Q .385/.395 and .374/.430; distances 7.7311/7.7686 Å | copy mean .1440505 | 1 for width≥6 Å | 1,1,1 conditional on named state/model | null [0,1] | null [0,.1440505] |
| Cao 3J5R, corresponding distinct agonist state | local Q .337/.338 and .315/.372; distances 4.1573/4.7137 Å | copy mean .106397 | 1 for width<6 Å | same conditional scope | null [0,1] | null [−.106397,0] relative to the declared broader width question |
| Bae 2N9Z K1, medoid9 | two experimental upper-bound restraints; violations0,0 Å | 1 | 1 for cross-loop≤4 Å | 1,1,1 conditional on model/assignments | null [0,1] | null [0,1] |
| Bae 2NAJ K2, medoid3 | corresponding local violations .336511596354,0 Å | .8986676009902625 | 1 for cross-loop≤4 Å | same conditional scope | null [0,1] | null [0,.8986676009902625] |

The full-ensemble joint DG envelopes are K1 [0,1] and K2 [0,.9205446855153534]. They are model scenario ranges, not confidence intervals. Each deposited ensemble is one experimental dataset. The two agonist states and the two toxin lobes are not silently averaged into a scalar about one unchanged state or one-residue perturbation. Their native rows illustrate contrasting measurements and limitations; the complete examples above supply the otherwise missing synthetic target/condition operands.

## Checked missingness and interpretation limits

- Cryo-EM Q=.8 plus one unread required endpoint: D=null [0,.64]. The reader preserves the measured .8; it does not drop the second endpoint.
- NMR one restraint with v=.5 Å plus one unresolved required restraint: D=null [.3032653298563167,.8032653298563167], with J=2 retained.
- No calibrated upper detection limit: N remains null, even if no ligand density or no peak is reported. An observed surrounding site's local support cannot manufacture a sensitivity bound for the missing feature.
- G, D and T share the same physical assignments. Joint scenarios preserve this dependency; their product is an index, not an independence claim.

`research_arithmetic_001.py` derives the published local cells directly from retained XML/PDB/MR files and checks both joined synthetic examples. Exact machine outputs and all admitted NMR scenarios are in `ARITHMETIC_RESULTS_001.json`. Printed rounding here does not alter those operands.
