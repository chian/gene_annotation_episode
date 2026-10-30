# Experimental context compatibility: paired extraction and numerical cells

Additive executable design for current A108 sheet003 and uncertainty004. Exactly
ten axes remain A101–A108,A110,A111; these are components of A108, not a new axis.
No A101, target-transfer weights or final credit aggregation is implemented.

## Original case and its bearing on the sheet

Grinter et al., Structural basis for bacterial energy extraction from atmospheric
hydrogen, PMC10017518, DOI10.1038/s41586-023-05781-7. Root read the relevant
full Results, experimental design and Methods paragraphs recorded in
primary_huc_compatibility/PARENT_RESET001, viewed original Fig1 and read complete
native XLSX panels A/C. The required authority/sheet reset preceded conversion.

Huc was purified from engineered M.smegmatis mc2-155 PRC1 with gylR frameshift,
hhyS inactivation and a chromosomal N-terminal2xStrepII-tagged HucS. It is not an
untagged wildtype preparation. Purification occurred from stationary-phase
cultures. Purified protein, not a natural habitat survey, supplied the assays.

For Fig1a,100nM Huc was added to5mL pH8 buffer with200uM menadione in sealed
120mL vials, initially3ppm H2 in an atmospheric gas mix. The source workbook
PanelA at4h gives three separate Huc-vial values .50115962885744503,
.23266425465749799,.42499064389735502 ppmv and two no-enzyme values
2.7573862695865201,2.7766710015482299. The native workbook has no unit beside
these particular columns; Fig1 supplies ppmv. At22h the three printed .04 values
represent the reported detection floor, not three exactly measured residuals.
Missing cells remain missing, not zeros. The GC source reports four biological
preparations per acceptor, three technical vials each, but the figure/workbook
panel shows one preparation. Its three technical vials are not three biological
replications or three habitat samples.

Fig1c uses dissolved H2 and0/10/100% dissolved O2 saturation, including residual
oxygen in nominally0% buffer. The percentages are not gas oxygen volume fractions.
The workbook contains three technical traces per oxygen setting for one enzyme
preparation; three biological preparations are reported separately. A missing
B5 measurement is not a zero rate. Positive measured rates at selected conditions
do not identify every intervening combination or an equivalence interval from
the phrase 'no significant differences'. The paper's general atmospheric530ppbv
benchmark is not a measured local substrate concentration in a target organism.

These distinctions require separate fields for physical unit/basis, operating
domain, observed local context, mapping/background, joint-domain support and the
actual sample frame. Source quantities remain useful while native organism/sample
coverage is unknown. No fraction of assay vials is relabeled environmental
compatibility, and purified-enzyme operation alone is not whole-organism capability.

## Numerical sheet

For each requirement j on the SAME context unit i, B is an admissible local
value interval or unknown; D+ and D- are sourced supported/incompatible interval
unions. Their unit bases and backgrounds must match. Supported membership
ell=1 only if B is wholly inside D+; upper u=0 only if B is wholly inside D-.
Otherwise preserve [0,1]. A value outside a supported domain is not thereby
incompatible. Overlapping contradictory domains or unresolved mapping preserve
unknown membership and specific reasons. SD/SEM/unspecified+- remain separate
reported fields, never automatically converted into admissible intervals.

Within each genuine route: L=product(ell),U=product(u). Unsupported joint-domain
construction suppresses positive L, retaining known necessary-condition failures.
Across genuine alternative routes: lower=1-product(1-L),upper=1-product(1-U).
These are logical conjunction/disjunction, not statistical independence or grades.
Relevant missing requirements/routes remain unknown. An explicitly complete empty
requirement set is meaningful only for a defined question, not automatic success
for an unspecified role.

With fixed paired sample weights W=sum(w)>0:
C_lower=sum(w*L)/W, C_upper=sum(w*U)/W. Supported, unresolved, incompatible
fractions are C_lower,C_upper-C_lower,1-C_upper. A point exists only when the
bounds coincide. One original opportunity has one weight despite repeated
representations or technical measures. For a biological capability question,
O_lower=1-product(1-L_state), O_upper=1-product(1-U_state), retaining an unknown
permitted remainder unless actual exhaustive scope is established. No compatible
witness plus incomplete scope is [0,1], not zero. An actual whole-scope physical
exclusion must retain its scope proof; none is invented from a taxon name.

Select the originally requested C or O. Do not choose the larger result, add
the two or multiply source assay reliability again. Exact numerator/denominator
cells and source/model dependencies accompany the numerical components.

For only same-frame unpaired necessary-condition fractions, retain Frechet
bounds max(0,sum(lower)-(J-1)) through min(upper). Never multiply unpaired
marginals. Route alternatives cannot be manufactured from such marginal data.
Optional equal-weight independent-unit Hoeffding bounds use the actual context
sample n and specified alpha; technical repeats or enzyme preparation counts do
not supply that context n. Analytical/model domains are not confidence intervals.

Synthetic ten-unit example: eight pass access, six of those pass exposure and
five pass oxygen. C=8/10*6/8*5/6=.5; O=1. One uncertain supported unit gives
C=[.4,.5]; one uncertain failed unit may give [.5,.6]. With no compatible witness
and unexamined states, O=[0,1]. Unpaired .8,.8,.9 gives C=[.5,.8], not .576.
These examples are invented arithmetic fixtures, not the Huc source measurements.

Original Huc contextual example: the measured gas/depletion and dissolved-oxygen
facts are retained, but local organism exposure/access, exhaustive states and
natural sampling denominator are not measured by those assays. Native context
point remains unknown with [0,1]. Mapping or an operating-domain interpolation
must be explicitly supplied and justified before it changes membership.

## Separate reader instructions

Identify the organism, strain, molecular preparation and biological situation
for the assigned possible function. Specify necessary environmental/access
conditions, genuine alternative routes and the meaning of capability versus
sample coverage. Read actual native quantities and their unit bases, source
uncertainty, censor limits, technical/biological replication and dependencies.
Keep assay conditions separate from measured local exposure in the organism.
State which contexts/domains are supported, excluded or unresolved and why;
never score biological plausibility by a taxon label or overall confidence word.
Preserve missing mapping and unexamined states. Models identify meanings and
operands; deterministic functions perform domain membership and combinations.

## Remaining boundaries

The finite first implementation does not establish general biological relation
inference, native local-exposure calibration, arbitrary correlated uncertainty,
all organism traits or actual-model investigation. Numerical operating-domain
input can come from retained structured extraction, not a claim that arbitrary
paper prose was deterministically understood. Complete episode delivery/reopen
and contrasting source arrangements require separate evidence. W05 remains later.
