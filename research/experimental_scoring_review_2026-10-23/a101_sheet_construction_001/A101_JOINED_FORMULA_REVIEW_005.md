# A101 joined native-score proposal: parent mathematical review 005

The parent read all of `a101_complete_sheet_015/CURRENT_PROPOSED_SHEET.md`,
including clarifications 001 and 002, all proposed reader IO and the complete
synthetic example. This is review of a cross-case mathematical proposal, not
a new primary-paper or paper-specific packet inspection. The three worker
source packets were not reopened for this increment. Prior source conversions
remain their own records. No production reader, scorer, prompt, library or
native sequence job was changed or executed.

## The actual proposed calculation

For a scope-compatible BLAST comparison with measured bit score B, paired
reference fraction r and all-alignment-column identity i:

    weight = (1-exp(-.025*max(B,0))) * r * (.5+.5*i)

For the corresponding HMMER profile comparison:

    weight = (1-exp(-.020*max(B,0))) * r

The inverse-bit constants and identity mixture are proposed numerical
conventions. They are not measured functional probabilities or fitted tool
equivalences. Native E-values, search spaces, bias, coordinates and settings
remain available with their native meanings; they are not added as repeated
evidence. The HMMER orientation clarification defines the reference denominator
both for a reference profile and for a supplied-query-derived profile.

At each target position, the strongest compatible reference for the function
supplies M; the strongest explicitly incompatible, same-scope reference
supplies O. Within a tool and required target region, the index is the mean
of M*(1-O). No independent vote is assigned to another overlapping hit,
copied report, related profile or software run on the same evidence.

The declared BLAST/HMMER profile averages the two tool results with weights
.5/.5. A one-tool profile is allowed and is separately named. A missing result
from an included tool remains an unknown operand; it cannot be dropped to
select whichever named profile returns the larger number.

Several genuinely required regions combine by their geometric mean. The
feature-qualified output multiplies by the mean of the declared relevant
feature-panel fractions and by the logical conjunction of independently
established necessary sequence predicates. A merely conserved site does not
become necessary by declaration. Incompatible functions, optional features,
partial sequences and molecular scopes retain their separate meanings.

## Complete synthetic instance

All inputs and labels here are constructed, not native output or a published
protein result. The target has 100 residues. The complete input table and
scope definitions are in the worker's WORKED_EXAMPLE.md.

| Component | BLAST | HMMER |
|---|---:|---:|
| Mean strongest function correspondence | .731054692602 | .640085084208 |
| Mean overlapping alternative penalty | .328105010628 | .184053960533 |
| Remaining per-tool index | .402949681974 | .456031123675 |

The declared two-tool average is .429490402824. The feature panels have
3/5 and 1/1 compatible questions, giving (.6+1)/2=.8. No necessary predicate
is established, so its empty conjunction is explicitly neutral. The selected
feature-qualified index is .429490402824*.8 = **.3435923222594366**.

Repeating a comparison and removing the weaker overlapping HMMER profile
leave this result unchanged. Removing the actually recorded incompatible
comparison raises it to .548455910724; that is a different evidence set, not
a demonstration that no other functions are possible. Leaving one formerly
incompatible site unassessed gives bounds [.343592322259,.386541362542].

If two regions 1–50 and 51–100 are biologically required, their per-region
indices are .195007885999 and .663972919649. The geometric mean is
.359833232792 and feature-qualified result .287866586234. The region meaning
must justify that distinct calculation; a text-formatting boundary does not.

The parent reproduces these values by separately building position arrays
from the explicit synthetic comparison table, without importing the worker
calculator. Native programs are not run. The receipt is
`joined_formula_parent_arithmetic_005.json`.

## Numerical choices available for human judgment

These are explicit choices, not missing equations: the .025/.020 inverse-bit
scales, .5 identity mixture, maxima over references, multiplicative alternative
penalty, equal tool/panel weights and geometric mean across required regions.
The same synthetic inputs give .278513274975 when both inverse-bit scales are
halved and .363839961812 when doubled. The native measurements are unchanged.
Thus the numerical scale needs judgment; successful arithmetic does not select
or validate these policy values.

The formula does not correct search multiplicity or database composition, and
the bit-score index is conditional on the recorded comparisons. Unknown
unobserved alternatives have a separate sensitivity range, not an invented
competitor row or a required search gate. Missing included results use the
explicit availability envelopes. Uncertain function membership and uncertain
coordinates have lower/upper envelopes, with shared constraints retained.

All proposed populating functions have specific numeric inputs/outputs and
typed failure meanings. They do not execute new searches or decide episode
continuation. Their production implementation is outside this research goal,
not an excuse to leave the numerical sheet's aggregation undefined.

The existing published cases populate contrasting source components, but the
complete raw native-score/map operands for a real-case final index are not
present in those packets. The current complete end-to-end number is synthetic.
User feedback and the scientific adequacy of these explicit conventions remain
outstanding. No axis or whole goal is marked complete by this review.
