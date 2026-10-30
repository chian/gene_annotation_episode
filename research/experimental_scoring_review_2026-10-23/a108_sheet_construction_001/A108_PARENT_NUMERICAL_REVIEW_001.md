# A108 parent numerical review: contextual compatibility fraction

The complete joined numerical proposal, its qualifications 002, proposed
reader contracts, local outcome statement and arithmetic checker were read.
The parent has not opened the Huc or tetrathionate paper-specific conversion
packets or independently inspected those primaries in this review. The source
numbers in the joined proposal remain attributed to the worker's inspections.
The experiment-definitions addendum 003 remains a source-basis follow-up and
is not claimed as parent-reviewed here.

No permanent document, production scorer, reader, prompt, library or episode
was changed. The proposal remains unadopted. The goal is usable scoring sheets;
later runtime implementation is not represented as a prerequisite to finish
this research deliverable.

## What the current numerical branch means

For a proposed function with specific necessary contextual requirements,
define the sample population by the meaning of that function. For each unique
sample opportunity i and each relevant requirement j, the sheet derives a
binary compatibility event from actual measured quantities and the supported
or contradicted operating domain. An unresolved event has bounds [0,1]; it
is not given an ordinal quality score. Let each unit's joint bounds be
L_i=product_j lower_ij and U_i=product_j upper_ij, and its recorded sampling
weight be w_i. Then:

    supported_fraction = sum(w_i*L_i) / sum(w_i)
    possible_fraction  = sum(w_i*U_i) / sum(w_i)
    unresolved_fraction = possible_fraction - supported_fraction
    contradicted_fraction = 1 - possible_fraction

These are bounds on a contextual compatibility fraction. The proposed credit
input is the supported lower fraction, accompanied by the upper bound and
missingness. It is not a calibrated probability of the annotation being true.
The 0-to-100 display is redundant with the 0-to-1 fraction; it is not another
term and must not be added to it.

All requirements refer to the same sampled opportunity. Joint support must
actually cover the combined conditions, as qualification 002 specifies.
Separate favorable one-variable experiments do not prove every unmeasured
joint combination. The products of logical lower/upper bounds are conservative
when unknown events share constraints; they need not be the tightest attainable
bounds. A narrowed result requires the actual joint constraints. Contradicted
joint combinations cannot be turned into supported ones by multiplying isolated
one-variable scores.

## Complete constructed calculation

All inputs here are synthetic. Among ten equally weighted independent
opportunities, eight are accessible, six of those have suitable concentration,
and five of those six also have suitable oxygen conditions. Thus:

    8/10 * 6/8 * 5/6 = 5/10 = 0.5

The unconditional marginal fractions are 8/10 for access, 8/10 for suitable
concentration and 9/10 for suitable oxygen. Their product is 0.576, which is
not the actual joint fraction. If only these marginals were known and they
covered the same population, the valid general joint bounds would be
[max(0,.8+.8+.9-2), min(.8,.8,.9)] = [.5,.8]. They cannot supply a .576 point.

The physical concentration component has actual operands: apparent 4.2 mM,
blank 0.2 mM and measured recovery .8 produce (4.2-.2)/.8=5 mM. Bounds
[4.1,4.3], [.19,.21], [.78,.82] produce [389/82,137/26] mM, approximately
[4.743902439,5.269230769]. This interval is wholly inside the stipulated
synthetic 2.5-to-10 mM domain. Recovery is corrected once. The source's real
sufficient-dose result is not a measured failure threshold for this fixture.

If one of the two currently incompatible concentration observations straddles
the required boundary, the joint result becomes [.5,.6] with no point. If one
currently favorable oxygen observation is contradictory and unresolved, it
becomes [.4,.5]. Missing pairing, missing inputs, measurement uncertainty and
sampling uncertainty remain different causes of different intervals.

For ten stipulated independent equal-probability opportunities, the proposed
Hoeffding 95% sampling interval is .5 +/- sqrt(log(40)/20), clipped to [0,1]:
[.07053059165,.92946940835]. This is conditional on the stated sampling design.
It is not licensed by ten technical repeats, correlated adjacent measurements,
or an arbitrary set of studies. A finite-frame census needs no claim of
sampling uncertainty for that frame's descriptive fraction.

## Defined behavior and remaining gap

The current branch specifies measured-input membership, non-detection bounds,
contradictions, same-unit dependence, duplicate neutrality, conditional
fractions and a full numerical reduction. Readers have explicit quantities,
units, censoring, sampling design and operating-domain fields. They remain
unimplemented by design of this research phase.

It does not yet provide a numerical interpretation of every argument allowed
by the user's A108 wording: plausibility given the sample, organism and
general clade. A clade label alone is not an exposure fraction. A narrowly
defined literature/organism-trait argument may supply a necessary contextual
requirement, but that relationship must be explicit; a reader cannot turn
unstructured 'typical for this clade' prose into a compatibility probability.
The draft's qualification 002 acknowledges this limitation. The remaining
design work is to identify and define those additional relevant components
from cases, or to have the user judge that the stated compatibility coordinate
is the desired scope. It must not be called a completed general A108 sheet
merely because its existing synthetic branch computes a number.

The parent arithmetic receipt checks the conditional versus marginal result,
measurement conversion, missingness changes, duplicate neutrality and the
stated sampling bound independently of the worker code. No primary-source
validation, biological calibration or production execution is claimed.
