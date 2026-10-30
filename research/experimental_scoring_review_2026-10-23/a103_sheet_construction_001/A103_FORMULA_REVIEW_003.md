# Parent review of the proposed A103 numerical sheet

Additive review. The worker draft and its 44-check receipt remain unchanged.
The parent read the complete numerical sheet, exact fields, component/source
table, checker and handoff. Both paper packets received separate parent reviews
and complete post-paper resets before their conversions. This does not adopt
the proposal or implement A103.

## Explicit proposed compilation

For a fixed contextual relation, retain either an actual documented native
neighborhood score or the proposed matched-count calculation. A count route is
not substituted for an available native measurement without identifying that
change. The two routes do not supply independent additions for the same data.

For a count route, within each declared comparison stratum let p be the
foreground endpoint fraction and b the corresponding background fraction.
The normalized contrast is `(p-b)/(1-b)` when p>b, `(p-b)/b` when p<b, and 0
when p=b. Its range is [-1,1]. With foreground/background stratum shares a and
a0, the common share is m=min(a,a0). Summing m gives comparison overlap C.
Summing `m*contrast` gives signed contribution t. When C>0, `t/C` is the
within-comparable-strata contrast. These quantities stay separately visible.

For fixed question weights summing to 1:

```
supporting_total = sum(weight * max(signed_contribution, 0))
opposing_total   = sum(weight * max(-signed_contribution, 0))
A103_coordinate = supporting_total * (1 - opposing_total)
```

All of these transformations are proposed index conventions. Neither the
normalized contrast nor the final product is a calibrated probability of exact
function. Weights apply to biological relations, not papers or repeated rows.

The worker's fully synthetic example has contributions `7/12, 1/2, -1/2`, each
weighted 1/3. The supporting total is 13/36, opposing total 1/6 and coordinate
65/216 = 0.3009259259. The second relation has overlap 3/4 and matched contrast
2/3; their product is 1/2. These are calculated quantities, not category grades.
If that relation is wholly unknown, its contribution is bounded by [-1,1] and
the coordinate is bounded by [7/72,95/216], with a null point estimate.

## Numerical gap found and checked

The worker's text permits a stratum with zero foreground or background
opportunities. Its checker nevertheless evaluates k/n and k0/n0 before testing
for zero common mass. The parent reproduced `ZeroDivisionError` with two
disjoint strata, even though both complete populations have positive size.
The previous 44 passing checks do not cover this case.

The separate parent research calculation skips contrast evaluation for a
zero-common-mass stratum. It does not replace an unknown contrast with zero.
For known disjoint stratum distributions, comparison overlap is 0, contrast is
unestimated, and the overlap-weighted evidence contribution is 0 by this
proposal's definition. That is no usable comparison evidence, not a measured
absence of genomic association. If an entire population is empty, even its
stratum distribution is undefined: the contribution remains null rather than
returning a zero-point result.

The parent script also checked partial overlap, empty extra strata, boundedness
and monotonicity under equal and unequal fixed question weights. Its **19
checks passed**. The synthetic coordinate, missing-question bounds and actual
native field selection reproduce the values above. This is independent
research arithmetic, not a repair or test of a production reader. A checker
label says “published synthetic cells”; this refers to the worker's written
research fixture, not measurements from a scientific publication.

## Scope and missing inputs

This parent review covers genomic organization and the documented neighborhood
channel. The worker's broader `genomic_cooccurrence`/phyletic-profile options
are not adopted here. They must not quietly reintroduce the evolutionary
co-distribution concept the user rejected for A104 or duplicate A107 partner
presence. The A103 proposal can operate on the reviewed neighborhood channel
without settling those extra options.

The two historical studies do not supply full matched-cohort operands. Their
filled cells and bounded results are valid partial examples; the complete
count-based compilation is synthetic. A separate actual native datum supplies
a complete one-question numerical example. Those three kinds of input remain
distinct. No invented target-to-locus mapping, sampling independence or native
calibration interval is supplied.

The native score and count contrast are on different scales. Mixing them is
explicitly an index convention requiring review; calling the result a
probability would require additional calibration. The source studies do not
endorse this formula. A changed question set or changed weights changes the
index definition and must not silently reprice an earlier observation.

## Goal criteria, rather than activity counts

The draft now has exact numerical cells and field contracts, complete proposed
sums/products with a checked zero-overlap clarification, contrasting source
limitations, a source trace, missing/dependent/opposing-data treatment, and
checked examples. It still needs the user's numerical-policy review and any
resulting corrections. The exact fields are a research handoff; targeted
production populating functions and W05 wiring are unimplemented and are not
completion evidence for this research goal.

Completion remains 0/10 in the fixed checklist. Paper inspection and passing
arithmetic do not alone finish a sheet. A105 remains the first review item.
