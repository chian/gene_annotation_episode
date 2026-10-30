# A102 formula review against the numerical-sheet goal

Parent read the complete worker draft 002, its checker, both source conversions,
and the primary material documented in the separate parent conversions. The
full per-paper rereads are complete. The earlier general-coverage attribution
error is corrected in COVERAGE_CORRECTION_002.md; AF2372's numeric result did
not change.

## What the current proposal actually computes

For an RMSD comparison with paired-position count n and declared lengths Lt,Lr:

    C = 2*n/(Lt+Lr)
    G = 1/(1+(rmsd/2 angstrom)^2)
    B = C*G
    F = mean(1/(1+(feature_distance/1 angstrom)^2))
    E = B*F
    S = max(E over supporting references)
    O = max(E over explicitly incompatible references)
    axis = max(0,S-O)

The feature set, its physical definitions and denominator must be supplied at
the particular functional scope. A feature missing from an incomplete model is
unknown, while an established incompatible/absent required feature has zero
compatibility. Equal feature weights, the two distance scales, max pooling, and
unit subtraction are proposed scoring conventions, not paper-derived truths.

The separate TM profile uses the smaller of the two length-normalized native
TM scores for the same map/transform, without another coverage multiplier.
The draft does not define a common numerical calibration between that profile
and its RMSD profile. Mixed-profile evidence therefore has separate outputs
and no single combined point value. Native Z is preserved but not independently
multiplied into another score derived from the same alignment.

## Complete synthetic arithmetic, printed for review

This is invented example data, not a biological result. Both scopes are 100
residues and both references use four separately defined functional anchors.

| Component | Supporting reference | Incompatible reference |
|---|---:|---:|
| Matched positions | 90 | 80 |
| RMSD, angstrom | 1 | 2 |
| C | 0.9 | 0.8 |
| G | 0.8 | 0.5 |
| B | 0.72 | 0.40 |
| Feature distances, angstrom | 0,1,1,2 | 1,2,2,3 |
| F | (1+0.5+0.5+0.2)/4 = 0.55 | (0.5+0.2+0.2+0.1)/4 = 0.25 |
| E | 0.396 | 0.100 |

The difference is 0.296. An unresolved last supporting feature yields
F in [0.5,0.75] and the difference in [0.26,0.44], with a null point. An
established absent last supporting feature gives 0.26. Duplicate publication
of the same comparison does not change either maximum. The synthetic
0.2-angstrom hard-bound illustration yields [0.1910171542,0.4001224025];
it does not supply error bars for either published protein.

## Completion gaps and choices requiring explicit judgment

1. The current proposal makes the axis a discrimination margin. Without an
   evaluated alternative-function panel it supplies no axis point, even if
   positive structural correspondence is measured. This is a substantive
   scoring restriction. The user's requirement to use native structural scores
   does not by itself require that restriction. It must not silently become
   an annotation gate or an execution prerequisite. No replacement aggregation
   is adopted in this review.
2. Published examples fill native and derived geometric components, but not
   the exact function-specific site maps or the complete contrast panel. The
   complete compilation example is synthetic. The missingness behavior is
   explicit, but a fully measured published function-specific compilation has
   not been demonstrated.
3. Mixed native metric profiles lack a defined common contribution. Keeping
   native outputs is correct; producing a usable single coordinate from a
   mixture still needs an explicit policy or a clearly accepted narrower scope.
   It is not completed merely by calling the mixed output null.
4. The supplied numerical feature average needs judgment for the particular
   functional scope. A minor anchor and a uniquely required catalytic feature
   do not become biologically interchangeable because each has weight 1/K.
   The draft exposes this convention; it is not calibrated by the examples.

These are research completion boundaries, not new runtime approvals. No
production policy or implementation is changed. A102 and the overall 0/10
checklist remain unfinished. Next work should resolve these specific numerical
choices rather than collect more unrelated case descriptions.

The new parent checker independently evaluates the formulas, native-component
arithmetic, missingness behavior and scope-denominator distinctions. The
worker's 43-check receipt is preserved and was not rerun over its output files.
Passing either checker establishes arithmetic only, not biological calibration.
