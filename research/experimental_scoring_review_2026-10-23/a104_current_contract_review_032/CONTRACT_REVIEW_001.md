# Bounded review of current A104 proposal004

This additive review concerns goal criteria 1, 2, 4 and 6: numerical meanings,
combination, dependence/missingness and exact reader inputs. The ten-sheet goal
and its seven criteria were read from the actual attachment. No axis or goal
completion is declared. All original proposal/checker/receipt files remain
unchanged; the corrections below belong only to this review directory.

The main proposal defines its numerical transforms and their missing-data
meanings. I found one algebraic qualification missing from the print handoff
and two concrete limitations in the synthetic checker. The sheet already gives
the correct rules for both checker cases. I did not find another essential
undefined arithmetic dependency in the inspected main proposal and reader
contract. This is a bounded mathematical/interface conclusion, not empirical
calibration, source verification or proof of implemented readers.

## Human definition and scope

The exact definition was read in the complete
`../a104_clade_support_completion_025/CURRENT_TWO_CONDITION_PROPOSAL_002.md`:

> A104 works if the phylogeny of the proposed protein family matches the reference evolutionary tree and if it sits within a clade of only that function

The next two user quotations identify the reference as the organismal tree
and restrict frequently transferred families to meaningful very local, very
near relationships. The complete `CURRENT_USER_STEERING_003.md` preserves the
later rapid-refunctionalization/mixed-function and outlier qualification.
Proposal004 is assessed against that latest direction; proposal002's old
equations are not treated as the current sheet.

Proposal004 retains an independently justified organismal comparison, a fixed
reference crown, and explicit scope for frequent HGT. A mixed precise-function
clade gives zero precise positive support, while any genuinely shared broader
function requires a separate justified assertion. The outlier ratio attenuates
distance from characterized references. No incompatible-function reference
group is required. These are consistent proposed conversions of the stated
definition, with their assumptions exposed.

The observed C_f=k_f/n contribution is expressly not full-clade purity, proof
that unknown members have f, or a probability of function. Q_f separately
qualifies the stronger all-clade statement. The reader must preserve this
distinction in any downstream use; this review does not silently promote the
observed association value into proof of the user's universal condition.

## D1 — correct the general formula printed in the handoff

`../a104_clade_support_completion_025/PRINT_HANDOFF_004.md:14` prints:

```text
A_observed = C_f * sum_z w_z * F_z * J_z * O_z
```

This is valid only when C_f is constant over the native draws in that sum.
The main proposal's section 6 permits C_f,r(z), and its exact-reader contract
matches C,F,J,O by sample/scenario. The general expression is:

```text
A_observed,r = sum_z w_z * C_f,r(z) * F_r(z) * J_r(z) * O_r(z)
```

All operands belong to the same supplied joint draw and globally consistent
source scenario. A function-coverage factor may be moved outside the sum only
after its constancy over those draws is established. Averaging an unresolved
source interpretation to manufacture such a constant is not allowed.

The additive arithmetic receipt includes a pure algebra fixture with two
equal-weight supplied draws, (C,F)=(1,0) and (0,1), with J=O=1. The within-draw
result is 0; multiplying the separate means gives 1/4. These are invented
algebraic inputs, not function probabilities or biological observations.
No change to the main proposal's correct equation is needed.

## D2 — checker score() did not establish its known-zero rule

The unchanged `arithmetic_checks_005.py:219` helper returns null when O is
missing unless C is already zero. This misses zero absorption by F, J or O.
Its actual stem fixture with only a characterized has:

| C | F | J | O | Old helper result | Correct product |
| ---: | ---: | ---: | --- | --- | ---: |
| 1/2 | 3/4 | 0 | null | null | 0 |

The old line 338, `known_stem_missing_branches = Q(0)`, assigns a literal zero.
It does not call score() or validate that the helper implements this behavior.
The main sheet's section 6 and exact-reader lines 141–143 already state the
correct rule: the identified zero product does not make the missing operand
known.

The additive `contribution_product` fixture helper checks each possible known
zero factor C, F, J and O while all other factors remain null. Each product is
0; all missing factor cells and their identities remain unchanged. A positive
control gives 3/4, and a case with missing O and no known zero stays null.
This repairs bounded research verification, not a production scorer.

## D3 — an unrelated polytomy must not erase a resolved clade crossing

The unchanged `arithmetic_checks_005.py:152` helper treats any polytomy anywhere
in a tree as unresolved membership when no exact crown node is found. This
counterexample uses fixed crown C={a,b}:

```text
((((q:.1,a:.1):.1,c:.2):.1,b:.4):.1,(d:.1,e:.1,f:.1):.1)root;
```

After pruning q, the already resolved {a,c} descendant cluster crosses {a,b}.
Resolving the unrelated (d,e,f) node cannot create the desired crown. The old
helper returns J in [0,1]. All three allowed binary refinements instead give
J=0 with resolved nonmonophyly.

The additive `fixture_membership_with_cluster_check` checks that resolved
crossing before retaining the old unresolved result. It returns J=0 for this
fixture. The original four placements retain their original membership
outputs, and the genuine crown-boundary fixture remains [0,1]. This is a
bounded correction for complete-label rooted fixtures, not a general tree
parser, unrooted membership implementation or arbitrary-completion solver.
The main proposal's section 4 and exact-reader section 4 already distinguish
relevant from unrelated unresolved topology correctly.

## Criteria 1, 2, 4 and 6: inspected evidence and limits

| Concern | Current contract and result of review |
| --- | --- |
| Topology denominator and missingness | Fixed intended slots give N=choose(m,s), with M+D+U=N and F_supported=M/N. Missing intended tips retain slots; raw common-leaf native agreement has a separate denominator. N=0 has explicit insufficient-taxa/no-observed-topology meaning. Per-subset states are not independent trials. |
| Function denominator and contradiction | Canonical unique reference members define n and k_f. A known other class inside the crown fixes precise C_f=0, including multifunctionality; a known other class outside it is not an added requirement. Unknown functions, broader-only labels and source conflict have separate constraints/scenarios. |
| Distance and units | Same-tree path distances define d and the median reference nearest-neighbor distance b, including the even-count median. O=min(1,b/d) has stated exact-zero, single-reference, missing, censored, incompatible-scale and invalid-value cases. The attenuation is explicitly a proposal. |
| Joint combination | Product within draw, required-region minimum within the documented joint draw, native weighted averaging, then minimum over included comparable analyses. It is not a product of marginal means. D1 corrects the abbreviated handoff only. |
| Scenario coupling | Shared identity, function, organism-tree and branch variables remain shared across dependent regions/analyses. Alternative source scenarios are not native replicate mass. For region marginals alone, the finite admissible-coupling optimization states variables, marginal constraints and objective. No default independent pairing is supplied. |
| Missing included information | Known missing mass retains its original normalization; included unavailable regions retain their slots. Unknown normalization permits a conditional retained-subset calculation only. Known zero products preserve null factor cells, as repaired in D2. |
| Replication and duplication | Same-molecule aliases do not add reference members; repeated representations do not add native sample mass or requirements. Distinct actual native replicates may have identical topologies; their actual sample identities and weights distinguish them from repeated reports. Equal weighting of distinct sampled proteins is an exposed sampling-density choice, not a claim of biological independence. |
| Nondetection | Assay inactivity, expression/preparation failure, scoped negatives and an established other function remain distinct. No nondetection is automatically converted into B_f, an alternative activity or opposing evidence. |
| Uncertainty and exact fields | Every numerical cell distinguishes point/null, identification bounds, bound kind, native uncertainty, units, operands and null/zero meanings. Tree/mapping, clade/function, graft/branch, ensemble mass and shared-scenario inputs are separately specified. Native branch support is not a reconstructed joint sample. |

The native-uncertainty output must retain which actual score distribution it
describes. A region distribution or a per-analysis candidate distribution is
available when supplied draws define it. The final minimum of analysis means
does not by itself define a new distribution or posterior. Do not replace it
with a per-draw minimum across analyses to manufacture quantiles; that changes
the equation. Leaving native uncertainty null when its required distribution
is unavailable follows the current contract. This is a clarification of its
existing condition, not an additional score or new completion requirement.

The finite coupling and global-completion equations are specified. A generic
optimizer, source adapters, complete native uncertainty type validator and
production readers are not implemented by these research files, and this
review does not count their absence as an undefined proposed equation. The
choice of equal subset/reference weighting, C_f, crown convention, b/d and
pooling remains exposed for judgment; the formulas are not claimed adopted
or empirically calibrated.

## What was actually checked

The complete current proposal, reader fields, print handoff, checker source
and saved receipt were read. The full receipt was displayed losslessly as
compact JSON, including all rows and limits. A fresh checker run reproduced
the parsed saved receipt exactly, including 256 original range-grid checks,
3/4 ordinary placement, 3/40 far-query placement, 8/25 joint required-region
result and the original shared-function/missing-mass examples. The receipt's
labels were not treated as proof of unexercised branches.

The additive checker ran to exit 0 and its complete result was read. It checks
D1's algebra, D2's actual failing stem plus all four zero-factor positions,
and D3's exact three refinements plus unchanged original membership controls.
See `arithmetic_review_001.py` and `arithmetic_review_results_001.json`.

Exploratory inspection also confirmed that the old outlier helper is not an
invalid-input validator: outlier_factor(-1,0) returns 1 before checking the
negative operand. Proposal004 already labels negative/incompatible branch
operands invalid. No invalid-input-validation claim is made for either
research fixture helper; this did not prompt production reader work.

`READ_AND_VERIFICATION_004.md` did not exist at the initial or final check.
The complete authority-read inventory is in `READ_AND_VERIFICATION_001.md`.
No primary paper or retained paper-specific source packet was opened. The
published source tables were inspected as parts of the current sheet; this
review does not newly verify their biological observations or source ratios.
No native phylogenetic program, target annotation, HPC work, production
prompt/scorer/library change or goal-status change occurred.
