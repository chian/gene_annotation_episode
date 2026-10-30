# A106: parent numerical review of perturbation/restoration sheet 003

The parent read the complete current numerical sheet, the complete reader IO
003 and the final index/clarification. This is a mathematical and interface
review of the cross-case proposal. The YeaG and Cas2 paper-specific packets
have not yet been read by the parent, and their primary inspection is not
claimed here. No new paper or paper-specific packet was opened in this review.
No historical record, prompt, production reader, scorer or annotation run was
changed. The research contribution remains proposed, not adopted.

## The complete proposed calculation, with component meanings

For a reference mean W, perturbed mean K and restored mean R, measured on the
same nonnegative ratio-scale endpoint:

    perturbation_effect = (W-K)/(W+K)
    restoration = clip(1-abs(R-W)/abs(W-K),0,1)
    comparability = product of the declared unintended-quantity agreement ratios
    isolation = min(clip(1-B_pert/abs(W-K),0,1),
                    clip(1-B_rest/abs(R-K),0,1))
    correspondence = molecule_correspondence * system_overlap
    point_contribution = orientation * perturbation_effect * restoration
                         * comparability * isolation * correspondence

The nuisance bounds B_pert and B_rest have the same endpoint units as their
own contrasts. They preserve the distinct attribution questions for the
perturbation and restoration. An unrelated bypass rescue cannot be made
specific simply by showing that the original perturbation was selective.

The endpoint zero and denominator must be meaningful. Protein amount is not
automatically activity. An amount change deliberately caused by the intended
perturbation is not an additional comparability penalty. A 0.64 expression
ratio alone establishes neither a mixed WT/variant population nor a linear
phenotype correction. The reader interface explicitly preserves these
experimental distinctions.

## Complete synthetic example and tighter joint bounds

All inputs below are invented fixed-example data, not published measurements.

| Component | Numerical inputs and calculation | Value |
|---|---|---:|
| Perturbation effect | W=100, K=20; (100-20)/(100+20) | 2/3 |
| Restoration | R=90; 1-10/80 | 0.875 |
| Experimental comparability | Rescue amount 90/reference amount 100 | 0.9 |
| Isolation | B_pert=8, B_rest=7; min(1-8/80,1-7/70) | 0.9 |
| Molecular correspondence | 90/100 scope coverage, 72/90 identity, 3/4 required features | 0.54 |
| System overlap | min(1,0.8)+min(0,0.2) | 0.8 |
| Point contribution | (2/3)*0.875*0.9*0.9*0.54*0.8 | 0.20412 |

The stipulated joint input box is W in [98,102], K in [18,22], R in [88,92],
B_pert in [6,10], with B_rest=7, comparability=0.9 and correspondence=0.432
exact. These are synthetic validation bounds, not sampling intervals inferred
from the three example replicates. The whole box stays on W>R>K>0.

On this branch, keeping the same W,K,R in every factor gives exactly:

    point = 0.3888/(W+K)
            * min((R-K)*(1-B_pert/(W-K)), R-K-7)

The first branch is positive throughout this particular box. Both branches
increase with R and decrease with K and B_pert (the second is constant in
B_pert). Both decrease with W throughout the supplied box. For the first,
the derivative's numerator is -W^2+2W(K+B_pert)-K^2; its larger zero is at
K+B_pert+sqrt(2*K*B_pert+B_pert^2), no greater than 32+sqrt(540)<98 here.
The second is a positive constant divided by W+K. These facts establish the
extrema, not just a numerical grid search:

| Bound | Shared input tuple (W,K,R,B_pert) | Exact contribution |
|---|---|---:|
| Lower | (102,22,88,10) | 56133/310000 = 0.181074193548 |
| Upper | (98,18,92,6) | 16281/72500 = 0.224565517241 |

These bounds are tight for the declared rectangular input set. Additional
joint constraints could narrow them further. They are inside the worker's
valid but looser enclosure [0.176418,0.233766]. The narrower interval is not
new experimental precision; it follows from retaining the same shared inputs
in the existing formula. No point measurement or source fact changed.

The worker's proposed nearest-to-zero uncertainty reduction would therefore
retain 0.181074193548 under this tighter box calculation, rather than 0.176418
under the loose enclosure. Both reductions implement the same proposed
conservative rule using different-quality enclosures. This sensitivity to the
enclosure method is a material scoring choice, not evidence of a published
biological result or a calibrated function probability.

## Counterevidence and aggregation reviewed

The sheet has a separate numerical necessity challenge. The functional claim
must actually entail its minimum effect before the observed result is seen.
With the documented synthetic point theta=3/197 versus required theta=1/3,
effective perturbation=0.95, cancellation isolation=0.9 and exact other factors
one, the point is -0.271979695431. Its stipulated effect bounds [-0.02,0.05]
give [-0.3021,-0.24225], with nearest-to-zero counterevidence -0.24225.
This challenges that quantitative necessity statement, not all possible roles.

Across comparable experiment groups, the worker averages signed point
contributions and their joint interval with weights 1/G, then applies the
nearest-to-zero reduction once. Actual duplicate representations do not change
G. This is explicitly an average over experimental designs; it is not cumulative
evidence. Adding a genuinely different zero-correspondence group can dilute it
because the denominator changes. That is the same important estimand choice
exposed elsewhere in the scoring review and must be judged as such.

## Exact interface and completion limits

The current IO targets the actual sheet operands. It distinguishes biological
units from technical observations, original experiment identities, ratio versus
logged scales, molecular coexistence, perturbation extent, two nuisance bounds,
sequence/structural/replacement correspondence and source/target contexts.
Unknown inputs can exist without fabricated primitive observations, as the
final index explicitly clarifies. Readers remain unimplemented, as required
for this research increment; the numerical functions are proposed contracts.

The source-grounded experimental portions have not been independently checked
by the parent here. The current proposal also leaves a general multi-inference
candidate reducer to later work. If a single A106 coordinate for a whole
persistent candidate is promised, that numerical meaning must be supplied;
calling it wiring alone would not satisfy the goal.

Finite review choices remain: the ratio-scale effect, restoration overshoot
penalty, possible repeated penalization through comparability and isolation,
molecular/system correspondence routes, nearest-to-zero uncertainty reduction,
and the equal-group average. Native inputs and calculations are explicit, but
the user has not adopted these conventions. The sheet remains unchecked.

The parent checker verifies the complete point, exact box bounds, rescaling,
orientation reversal, necessity example and the aggregate-denominator effect.
It establishes arithmetic under the declared fixture, not causal calibration,
primary source validity, production behavior or a completed evidence axis.
