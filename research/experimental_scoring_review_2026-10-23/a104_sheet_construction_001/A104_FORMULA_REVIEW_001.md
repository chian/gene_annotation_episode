# Parent review of the proposed A104 numerical calculation

This is a source-free review of the complete cross-case numerical sheet and its
research arithmetic script. The parent has not read the three paper-specific
packets or independently verified the worker's phylogenetic figure extraction.
Their documented coverage is not claimed as parent source inspection. No new
paper or paper-specific packet was opened for this review.

The user-defined subject is evolutionary history and phylogeny, including
placement within characterized clades, agreement with organism history,
outliers, and explanation of possible horizontal transfer. It is not a
replacement phyletic co-occurrence axis. The worker's tree placement and
distance formulas address that subject explicitly.

## Numerical proposal actually supplied

For one declared target region and reference comparison, the proposed placement
P is the number of query-anchored reference triplets favoring the candidate
minus the number favoring the alternative, divided by the fixed pair count.
An unresolved triplet retains its place in that denominator and contributes
an unknown state, not a dropped row or measured zero.

The distance factor O is min(1, within-function median nearest-neighbor
distance / query-to-nearest-characterized-reference distance), with consistent
branch units. A single characterized reference cannot fill the proposed
within-function spacing. Equal reference sequence labels do not manufacture
independent reference members.

The history factor H is the fraction of query-anchored gene/species triplets
that agree, plus weighted numerical explanations for explicitly assigned
discordances. Every calculation occurs within each sampled tree before
averaging across that one declared ensemble:

    support = max(P,0)*O_candidate*H
    opposition = max(-P,0)*O_alternative
    signed contribution = mean(support)-mean(opposition)

For multiple declared functional alternatives, the worker takes minimum support
and maximum opposition within each tree before averaging. The uncertainty
ensemble is not treated as independent scientific replication. Different
domain histories remain separate and a whole-protein reducer is not supplied.

## Complete synthetic example

All these inputs are invented fixture data; none is a result for the target gene.
Eight of ten trees have P=1, O_candidate=0.75 and H=0.7. Two have P=-1 and
O_alternative=0.5. Thus:

    positive = (8*1*0.75*0.7)/10 = 0.42
    opposing = (2*1*0.5)/10 = 0.10
    signed = 0.42-0.10 = 0.32

The factor H=0.7 comes from an explicit hypothetical explanation, not a phrase
assigned grade 0.7: contact 8/10 hours = 0.8; matched transfer/background/control
rates give (32-2)/(52-2)=0.6; their proposed equally weighted mean is 0.7.
Those physical quantities and the mean's meaning still need scrutiny below.

If that explanation is entirely unknown, the same synthetic ensemble has signed
bounds [-0.10,0.50], not the point 0.32. With only contact 0.8 known, the
explanation is in [0.4,0.9]. The resulting signed ensemble bounds are
[0.14,0.44]. These are identification bounds, not statistical confidence limits.

A proposed positive-part handoff would give c_A104=max(0,signed), retaining all
signed/positive/opposing cells. It would give 0.32 for the full fixture and
[0,0.50] with unknown explanation. That 0-to-1 mapping is NOT adopted here;
the worker delivered a signed regional endpoint and explicitly left later
annotation consumption unresolved.

## Finite review questions and gaps

1. **Explanation scope.** The worker defines HGT explanation using measured
   contact-time fractions and normalized laboratory transfer rates. These can
   answer specified present-day route questions. The user also explicitly
   allowed assessing whether inferred transfer makes sense from environmental
   similarity and other historical biological evidence. The current optional
   grader can only estimate those two physical coordinates. It has not
   demonstrated that this narrow rubric covers that broader intended question.
   A defensible native reconciliation statistic or a decomposed explanation
   rubric for the actual available evidence still needs a worked example.
   This is not permission to invent ancient contact durations or transfer rates.
2. **Required comparators.** At least two characterized references are needed
   by the distance normalization, and an alternative-function set is required
   by the proposed placement contrast. The draft therefore leaves common
   sparse-reference cases with a null compiled point. That is a specific
   consequence to judge, not an execution gate authorized by the user.
3. **Asymmetric history treatment.** H discounts positive placement but not
   opposing placement. This is an explicit convention. Swapping candidate and
   alternative need not negate the result when H differs from one. The effect
   should be printed and judged; it is not established by tree topology alone.
4. **Annotation-coordinate scope.** The sheet supplies a single homologous-
   region signed calculation. The stated goal requires its contribution to
   annotation scoring to be explicit. The positive-part proposal above shows
   one numerical handoff, but competing domain histories and a persistent
   multi-claim candidate still require a declared combination. Labeling that
   missing numerical meaning as wiring would not supply it.

The source-table numbers describe documented available cells and missing native
operands. This parent review does not certify the primary figure extraction.
The formulas are numerical and inspectable; that alone does not prove that
their biological scope meets the user-defined axis. A104 remains unchecked.

## Verification boundary

The worker script was read completely and rerun without changing it. It writes
only to stdout. A new parent receipt captures that output and independent
exact-fraction checks of the compiled point, contact-only interval and proposed
0-to-1 projection. The synthetic tree geometry and all 320 worker range checks
passed. That is arithmetic verification, not a new phylogenetic analysis,
source verification, calibration, implemented reader or adopted policy.
