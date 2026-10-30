# A105 relevance sensitivity: one unadopted continuous alternative

2026-10-23. **Every numerical example below is SYNTHETIC.** This is a bounded
arithmetic review of the existing [correspondence convention](../a105_target_relevance_003/UNCALIBRATED_CORRESPONDENCE_CONVENTION_002.md),
not a new assay, paper review, reader, production scorer or annotation-coordinate
rule. All ten sheets remain unfinished; A105 remains first.

The current mean permits high global correspondence to compensate substantially
for low local-site correspondence. A shifted harmonic mean limits that
compensation continuously, using the same inputs and family weights. It still
cannot establish activity, supply missing measurements or stop selective removal
of inconvenient inputs. Conditional points must retain their measured basis and
full-set bounds under either convention.

Let the declared relevant family values be `q` (sequence), `s` (structure), `p`
(phylogenetic placement), `l` (local functional-site correspondence), and `m`
(system similarity). Each lies in [0,1] under its explicitly defined numerical
conversion. They are **correspondence indices, not function probabilities**.
The source sheet supplies `B_source` in [-1,1] for a scoped directional molecular
finding. A negative B is opposing evidence for that direction, not necessarily
evidence for complete absence of activity. The source calculation is unchanged.

The original weights are retained: `w_q=w_s=w_p=w_l=w_m=1`. The proposed ONE
alternative changes only the outer averaging function:

```text
O = observed applicable families; W_O = sum_(j in O) w_j
R_A_available = sum_(j in O)(w_j*r_j) / W_O

delta = 0.1                       [explicit uncalibrated design constant]
R_H_available = W_O / sum_(j in O)[w_j/(delta+r_j)] - delta

C_A = B_source * R_A_available
C_H = B_source * R_H_available
```

If `O` is empty, both points are unknown. One observed family gives its actual
value under either formula; missing site/system measurements impose no veto.
No activity calibration is required to compute either conventional index. The
positive shift has no assay unit and is neither a pseudocount, functional-effect
weight nor uncertainty estimate. Its proposed value 0.1 controls how strongly
low correspondence limits compensation and needs user judgment.

For complete observations, `R_H <= R_A` by the weighted harmonic/arithmetic mean
inequality applied to `delta+r_j`. Both equal x when every family equals x.
Both are continuous and increase with every component. No threshold or required
modality is introduced. Global correspondence may be displayed as one block
only using `G_H=3/[1/(delta+q)+1/(delta+s)+1/(delta+p)]-delta`, giving
`R_H=5/[3/(delta+G_H)+1/(delta+l)+1/(delta+m)]-delta`. This is exactly the same
formula; an arithmetic global block would be a different convention.

With all other families at 1, a site value 0.1 has maximum `R_A=0.82` but maximum
`R_H=5/[4/1.1+1/0.2]-0.1=91/190=0.478947`. A site value 0 has maximum
`R_H=5/[4/1.1+1/0.1]-0.1=4/15=0.266667`, **not zero**. Losing exact identity at
a specified residue does not demonstrate lost activity; the synthetic examples
supply no measured residue-effect weights. Exact site identity also does not
prove activity. The proposed score only changes how correspondence is combined.

For missing values and partial within-family observation, preserve a full-scope
interval `[a_j,b_j]` per declared family. An entirely unknown relevant family
has [0,1]; a fully observed exact synthetic index has `[r_j,r_j]`. For m matching
sites among k observed of n predefined sites, the observed-only index is m/k,
its coverage is k/n, and its full-site bounds are `[m/n,(m+n-k)/n]`.

```text
W = sum_(j declared relevant) w_j
R_A_full bounds = [sum(w_j*a_j)/W, sum(w_j*b_j)/W]
R_H_full bounds = [W/sum(w_j/(delta+a_j))-delta,
                   W/sum(w_j/(delta+b_j))-delta]
C_full bounds = [min(B_source*R_lower, B_source*R_upper),
                 max(B_source*R_lower, B_source*R_upper)]
```

These are identification bounds under the chosen scoring convention. They are
not confidence intervals, probability limits, or imputed observations. They
allow all combinations of unknown [0,1] values; additional justified joint
constraints could narrow them. Dependence is not assumed away. Synthetic inputs
are treated as exact for this arithmetic exercise; real measurement uncertainty
would need separate propagation from actual bounds or joint measurements.

The table uses family order `(q,s,p,l,m)`. Brackets give the possible FULL
result; a single number means no missing-input width in this synthetic example.

| SYNTHETIC comparison | Inputs and exact construction | Current mean `R_A` | Proposed `R_H` | Consequence |
|---|---|---:|---:|---|
| High global match; low site match | `(0.95,0.95,0.95,0.1,1)`; site 1/10 | 0.790000 | 0.470370 | The low local component has more influence under H. |
| Same, zero exact site matches | `(0.95,0.95,0.95,0,1)`; site 0/10 | 0.770000 | 0.263208 | Neither value establishes activity loss; H has no zero-site veto. |
| Low site observation unavailable | `(0.95,0.95,0.95,?,1)` | 0.962500 [0.770000,0.970000] | 0.962069 [0.263208,0.969444] | Both conditional points rise; uncertainty widens. A known unfavorable result cannot legitimately be relabeled unknown. |
| Unknown site removed from declaration | Four-family `(q,s,p,m)=(0.95,0.95,0.95,1)` | 0.962500 | 0.962069 | Point unchanged; bounds collapse because this is a DIFFERENT scope. Silently dropping an applicable family falsely removes uncertainty. |
| High global/site match; low system similarity | `(0.95,0.95,0.95,1,0.1)` | 0.790000 | 0.470370 | The same continuous limitation applies to measured condition-descriptor similarity. |
| Full-span sequence comparison only | `q=180/200=0.9`; other four unknown | 0.900000 [0.180000,0.980000] | 0.900000 [0.021951,0.978431] | A single measured family provides a conditional point, with broad bounds. |
| Small local alignment on complete inputs | Complete source/target spans both 200 aa; local alignment contains 20 identical residues; `q=20/200=0.1` | 0.100000 [0.020000,0.820000] | 0.100000 [0.011111,0.478947] | The alignment's local identity 20/20 does not replace the declared full-span denominator. |
| Only a 20-aa snippet supplied | 20/20 snippet identity; whole sequence length/coverage unknown; all full-scope components unknown | unknown [0,1] | unknown [0,1] | A snippet-scope value 1 cannot become a full-molecule point. |
| Full site set, two matches | `(0.95,0.95,0.95,2/10,1)` | 0.810000 | 0.604268 | Ten sites were observed; eight actual mismatches. |
| Only two of those ten sites observed | Both match: conditional `l=2/2=1`; coverage 2/10; full `l` bounds [0.2,1] | 0.970000 [0.810000,0.970000] | 0.969444 [0.604268,0.969444] | The favorable observed-only point does not erase eight unknown positions. |
| Sequence method A alone | `(0.9,0.8,0.7,0.6,0.9)` | 0.780000 | 0.763605 | One sequence method occupies the sequence family's weight 1. |
| Two declared sequence methods | `q=0.5*0.9+0.5*0.5=0.7`; other values `(0.8,0.7,0.6,0.9)` | 0.740000 | 0.727858 | Methods share the family's fixed weight; no new family or experiment is created. |
| Add duplicate of method A | Same unique measurements and weights as previous row | 0.740000 | 0.727858 | Both results are unchanged. |
| **Invalid** duplicate averaging | Wrong `q=(0.9+0.9+0.5)/3=23/30` | 0.753333 | 0.741251 | Counting the repeated representation raises both values without new evidence. |

The small-alignment row measures how much of the fully supplied comparison is
covered by identical aligned residues; it does not label every unaligned residue
an actual mismatch. If instead only 20 positions were supplied and the other
180 residues were unknown, a full-set identity fraction would require bounds,
not the exact 0.1 whole-sequence value shown for the completed local comparison.

For the first row the exact sums and products are:

```text
R_A = (0.95+0.95+0.95+0.1+1)/5 = 79/100 = 0.79
R_H = 5/[3/1.05+1/0.2+1/1.1]-0.1 = 127/270 = 0.4703703704
C_A with B=+0.9: (9/10)*(79/100) = 711/1000 = +0.711
C_H with B=+0.9: (9/10)*(127/270) = 127/300 = +0.4233333333
C_A with B=-0.9: -0.711; C_H with B=-0.9: -0.4233333333
```

| Source sign and site-unknown example | Current mean contribution | Proposed harmonic contribution |
|---|---:|---:|
| `B=+0.9` | point +0.866250; full bounds [+0.693000,+0.873000] | point +0.865862; full bounds [+0.236887,+0.872500] |
| `B=-0.9` | point -0.866250; full bounds [-0.873000,-0.693000] | point -0.865862; full bounds [-0.872500,-0.236887] |

Negative-source bounds reverse before being sorted. The alternative attenuates
both supporting and opposing source indices more strongly when correspondence
is uneven. It does not reverse the source direction. This symmetry is a material
choice: lowering correspondence also reduces transferred counterevidence.

The synthetic native operands are explicit. Sequence 0.95 is 190 identical
aligned residues over known 200-residue spans; structure 0.95 can be
`min(TM_source=0.95,TM_target=0.98)`; placement 0.95 is 95/100 eligible replicates
supporting a predefined placement; site values are counts over ten predefined
sites. In the methods example each sequence method has self scores 200 and 200,
with pair scores 180 and 100, yielding 0.9 and 0.5 by `2*S_pair/(S_self1+S_self2)`.
These are synthetic compatible score configurations, not measured tool runs.
Other structure/placement values in that example are native normalized 0.8 and
70/100 respectively. No method weight depends on which result is more favorable.

System values use the existing declared kernel, not an invented functional
response: source pH 7; proposed reference variance 1 pH-unit squared; target pH
`7+sqrt(-2*ln(m))`. Values m=1,0.9,0.1 correspond to target pH approximately
7,7.459044,9.145966, respectively. All are synthetic. Thus
`exp[-(target_pH-7)^2/2]=m`. Similarity of these descriptors is not a measurement
of retained enzyme activity. If a measured functional response mapping h is
supplied, use the separate [measured-mapping interface](../a105_target_relevance_003/TARGET_RELEVANCE_INTERFACE_002.md)
on its endpoint and uncertainty; do not reuse those observations as this system
multiplier. No such response data or measured functional-effect site weights
were supplied here.

Multiple tools remain within a fixed family weight. Repeated representations
are recognized by their measurement provenance, not numeric equality. Alignment,
mapped-site and tree results can share data, and predicted structure can share
sequence information. Neither average turns these correlated measurements into
independent assays, independent likelihood terms or additional replication.
Replacing the mean does not resolve that dependence or make the mixture
predictively calibrated. Direct contradictory molecular observations retain
their actual scope and sign; correspondence cannot overrule them. Nondetection
remains a source measurement/likelihood issue, not a fabricated zero site or
system similarity here.

The handoff to the separately owned annotation-coordinate work is only
`C=B_source*R`, with its sign, conditional basis, identification bounds and
conventional meaning retained. C cannot be transformed back into a calibrated
likelihood or combined as independent likelihood evidence. This study does not
choose a nonnegative coordinate, a multi-source combination or a global score.

**Remaining user choice:** keep the current arithmetic convention, or use the
specific shifted harmonic alternative with delta=0.1 to limit compensation;
and decide whether an incompletely measured result contributes its explicitly
conditional point or only its full-set bounds. The alternative cannot cure
selective missingness. A general scalar cannot simultaneously ignore every
missing family and guarantee that losing an unfavorable observation never
raises its point. None of these choices is adopted here.

[Exact operands/results](sensitivity_arithmetic_001.json) retain rational values,
both signs and intervals for all rows. The [standalone calculation](sensitivity_arithmetic_001.py)
ran successfully with Python 3, checking exact arithmetic, duplicate invariance,
missing-input bounds, idempotence and 1,024 synthetic vectors for `0<=H<=A<=1`.
Those checks establish the stated arithmetic, not biological calibration.
[Read provenance](AUTHORITY_READS_001.md) records the complete instructions and
proposal files inspected. No paper packet, production test suite, scientific
run, prompt, library or reader was opened or changed as part of this study.
