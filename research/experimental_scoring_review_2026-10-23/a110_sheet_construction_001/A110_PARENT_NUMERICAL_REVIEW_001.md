# A110 parent review of the joined chemical-account calculation

The complete joined sheet, print-ready summary and reader IO were read. The
parent has not opened either paper-specific conversion in this review. Their
primary inspection, measurement interpretation and source coverage remain the
worker's recorded work. This review checks the mathematical proposal and IO;
it does not claim independent verification of primary figures or chemistry.
No production files, readers, prompts, libraries, annotations or jobs changed.

## Concrete scoring quantities and compilation

The sheet separates actual chemical measurements, predictions and proposed
transformations. For an observed corrected scalar y, claimed prediction c and
named alternative a, use e_claim=mean((y-c)^2), e_alternative=mean((y-a)^2):

    signed_constraint = (e_alternative-e_claim)/(e_alternative+e_claim)

When both errors are exactly zero the contrast is zero. Raw errors remain
visible, because a poor account can fit better than an even worse alternative.
An isotope vector uses the sum of squared fractional-bin residuals per
experimental unit, with covariance retained for uncertainty, not independent
votes from every bin. The proposed minimum over declared alternatives retains
all comparisons and is not an assertion that unexamined alternatives failed.

Measured background, recovery, mixture contributions and calibrated condition
differences correct the physical quantity before its residual is computed.
They do not become extra quality-score rows. Supplied and consumed amounts
have different denominators. Source-limited conditional points do not fill
unknown systematic corrections or replicate variance.

For an actual same-period resource budget, supportable output z is the limiting
resource amount divided by its stoichiometric requirement; a network instead
uses the explicitly defined shared-constraint optimization. Demand coverage
is f=min(1,z/required_output), and the proposed signed resource value is 2f-1.
Gene presence is not a measured capacity. Unknown demand, unknown capacities
and an infeasible model have different meanings.

The conservation calculation cancels identical species before counting
reactant/product atoms, formal charge and donated/accepted electrons. Its
maximum normalized deficit D is not a new observation when D=0. With distinct
question weights summing to one, S=sum(weight*constraint) and:

    contribution = (1-D)*S-D

This is a signed chemical-account index, not a probability. The weights,
error contrast, minimum over alternatives, 2f-1 mapping and conservation
penalty are explicit proposed policy choices. They remain unadopted.

## Source-filled conditional arithmetic reproduced

These ratios are taken from the worker's NfnAB conversion of the reported
purified-system experiments; their source uncertainties remain unverified by
the parent and unfilled where the publication did not supply them.

| Question | Observed / claimed / alternative | Claimed squared error | Alternative squared error | Signed contrast |
|---|---|---:|---:|---:|
| Reverse H2 per NADPH supplied | 5/11; 1/2; 1 | 1/484 | 36/121 | 143/145 |
| Forward net NAD(P)H per NADH supplied | 10/11; 1; 0 | 1/121 | 100/121 | 99/101 |

The equal mean is 14399/14645=.9832024581768521. Conditional on the worker's
specified formally balanced reaction basis, D=0 leaves that value unchanged.
This is a fully evaluated conditional reference-reaction example, not a score
for the current annotation target or a demonstrated native pathway budget.

The source-filled supplied-reagent budget 2.2/2=1.1 micromol H2 capacity for
a reported 1 micromol endpoint has f=1. It is the same observation as the
reverse ratio, so a second weighted contribution would duplicate it. Its
diagnostic value remains visible without another weight.

A broader three-question pathway proposal keeps the two unmeasured native
resource/energy terms in the denominator. Conditional on nominal stoichiometry
and D=0, its bounds are [(.983202458-2)/3,(.983202458+2)/3], approximately
[-.338932513941,.994400819392]. Unknown stoichiometry measurement corrections
can widen this to [-1,1]. Keeping a conditional point separately from these
bounds is essential; the precise displayed number does not repair missing data.

For the separate isotope model, p=.64 and three independently drawn donor
oxygen labels give the binomial prediction [.046656,.248832,.442368,.262144]
and expected label count 1.92. These are model predictions from the worker's
reported precursor fraction, not observed product fractions. The full
source-specific isotope convolution and reduced-image interpretation are in
the UbiUV packet, not independently inspected here. Intracellular donor
enrichment cannot be inferred by silently equating it to the supplied label.

## Missingness and IO examined

The exact reader IO resolves the 0/0 interval edge cases: when a proposed
lower/upper relaxed-error endpoint has zero denominator, that endpoint is
zero. If both entire error intervals are zero, the score interval is [0,0].
Unknown errors with no finite domain give [-1,1]. These enclosures may be
loose because the same measured y enters both errors; they do not assume that
the two residuals arose independently.

The compile bounds use monotonicity: with S in [S_low,S_high] and D in
[D_low,D_high], lower=(1-D_high)*S_low-D_high and
upper=(1-D_low)*S_high-D_low. Unknown questions keep their weights. Native
statistical uncertainty, model uncertainty and missingness remain separate.

The IO supplies actual chemical quantities/units, source/target relationships,
per-experiment identities, correction operands, isotope windows and label
models, reaction/species definitions, measured network bounds, absolute
residuals, conditional assumptions and original weights. Every proposed
reader remains unimplemented. That later implementation is outside the
scoring-sheet research goal; exact missing input definitions are not.

The parent arithmetic receipt covers the stated rational contrasts,
compilation, missing-question bounds, native-budget diagnostic, isotope
prediction and zero/error-bound cases. It is mathematical verification of
these inputs and conventions, not source validation or biological calibration.
