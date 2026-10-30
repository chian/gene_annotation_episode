# Fully filled organism-context example — all inputs synthetic

Every observation, domain boundary and subject in this example is invented for
sheet checking. No value is measured from Cdv, porphyran, ybhP, or a new
experiment. The source papers motivated the distinction between a compatible
cellular opportunity and the prevalence of that opportunity; they supply none
of these numerical inputs.

The supplied material is a hypothetical unnamed sequence from one known
organism. Investigation has produced a candidate role acting on the cytosolic
face of a membrane neck during the organism's stated division interval. A
separate synthetic characterized system defines a **jointly demonstrated**
operating domain: cytoplasmic access and neck width 90–140 nm. Widths at most
80 nm or at least 150 nm, and a membrane-separated site, are incompatible for
that exact reference endpoint. Intermediate untested widths are unknown.
These boundaries are not general cell-biology thresholds.

The organism is witnessed in twelve division episodes in one fixed image
dataset, treated as a finite-frame census. Each episode is observed once for
this calculation; multiple images of that episode are technical observations.
No random population sample or independent-culture confidence interval is
claimed. The capability question concerns whether the organism admits this
cellular context at all; the coverage question concerns these twelve episodes.

| Episode | Cytoplasmic access | Neck width, nm | Measurement interval, nm | Lower margin to 90 nm | Upper margin to 140 nm | Joint membership |
|---|---|---:|---|---:|---:|---|
| 1 | connected | 100 | [98,102] | 10 | 40 | [1,1] |
| 2 | connected | 103 | [101,105] | 13 | 37 | [1,1] |
| 3 | connected | 106 | [104,108] | 16 | 34 | [1,1] |
| 4 | connected | 109 | [107,111] | 19 | 31 | [1,1] |
| 5 | connected | 112 | [110,114] | 22 | 28 | [1,1] |
| 6 | connected | 115 | [113,117] | 25 | 25 | [1,1] |
| 7 | connected | 118 | [116,120] | 28 | 22 | [1,1] |
| 8 | connected | 121 | [119,123] | 31 | 19 | [1,1] |
| 9 | connected | 124 | [122,126] | 34 | 16 | [1,1] |
| 10 | connected | 170 | [168,172] | 80 | −30 | [0,0] |
| 11 | membrane-separated | 110 | [108,112] | 20 | 30 | [0,0] |
| 12 | membrane-separated | 120 | [118,122] | 30 | 20 | [0,0] |

The two margin columns use point measurements for display; membership uses the
full measurement interval and the jointly supported domain. For episode 1 the
margin intervals are [8,12] nm and [38,42] nm. A negative margin alone does not
establish failure outside the demonstrated incompatible range; e.g. an interval
[82,86] nm is unknown in this fixture.

| Numerical sheet cell | Numerator / denominator or exact calculation | Filled result |
|---|---|---:|
| Physical access among the fixed division episodes | 10/12 | 0.8333333333 |
| Compatible width among accessible episodes | 9/10 | 0.9 |
| Joint organism-state coverage C | (10/12)×(9/10)=9/12 | 0.75 |
| Supported / unresolved / incompatible sample mass | 9/12, 0/12, 3/12 | 0.75 / 0 / 0.25 |
| Organism admits at least one compatible context O | 1−product(1−L_s); at least one L_s=1 | 1 |
| Capability S108 | 100×O | 100 |
| Coverage S108, if that is the stated question | 100×C | 75 |
| Environmental conjunction | No external requirement in this deliberately scoped geometric example | 1, logical identity |
| Sampling uncertainty beyond the finite dataset | Sampling design absent | null |

The 100 and 75 answer different questions. They are not summed, averaged or
chosen after calculation. The primary A108 question “does this role make sense
in this organism?” uses the capability result here. The 75-point coordinate
describes coverage of these division episodes and preserves the existing
sample-opportunity branch. Molecular identity/activity and functional causation
remain unscored by either number.

Checks performed by the local fixture script:

1. Base: organism O=[1,1]; sample C=[3/4,3/4].
2. Duplicate report of episode 1: unchanged results and denominator.
3. Episode 1's width becomes [82,86] nm: C=[2/3,3/4]; O=[1,1] because other
   witnessed compatible contexts remain.
4. Only episode 1 is compatible, with eleven known incompatible sample episodes:
   C=1/12; O=1. Rarity is not a capability penalty.
5. Every examined episode is incompatible, but permitted unexamined organism
   states remain: O=[0,1], point=null. Nondetection is not proved impossibility.
6. A hypothetical necessary organism-wide architectural constraint excludes all
   allowed states: O=[0,0]. This is an explicit synthetic constraint, not an
   inference from the finite negative sample.
7. In the base frame, width compatibility alone is 11/12 and access is 10/12.
   Their marginal product is 55/72≈0.763889, different from the paired 3/4.

All input cells are populated in `synthetic_context_units_001.json`; numerical
results are in `arithmetic_receipt_001.json`. The script checks arithmetic and
declared logical semantics only. It is not a reader, biological calibration,
target investigation, library change or production credit implementation.
