# A104 numerical research delivery

This is the parent-reviewed research proposal for A104. It preserves all
earlier records, incorporates the user's organismal-tree/function-conserved-
clade definition, and identifies the current mathematics, exact population
fields, filled examples and verification limits in one place. It is not a
production scoring change or approval of proposed numerical conventions.

## Current documents

- Mathematical sheet: `a104_clade_support_completion_025/A104_CURRENT_NUMERICAL_PROPOSAL_004.md`.
- Exact reader inputs/outputs: that directory's `EXACT_READER_FIELDS_004.md`.
- Additive handoff/fixture corrections: `a104_current_contract_review_032/CONTRACT_REVIEW_001.md`.
- Published numerical cells: `a104_published_scoring_inputs_033/SOURCE_TO_CANONICAL_CELLS_001.md`,
  its input specimen/arithmetic receipt, **with** `SPECIFICITY_SCOPE_ADDENDUM_002.md`.
- Final source-limited presentation: `a104_published_scoring_inputs_033/PRINTABLE_HANDOFF_002.md`.

The old001/002 proposals and abbreviated PRINT_HANDOFF004 are historical where
these records correct them. In particular, C cannot be factored outside a
sample sum unless it is constant across those samples. No incompatible-function
reference group is a required operand.

## Numbers and combination

| Component | Exact current calculation | Interpretation |
|---|---|---|
| Resolved family/organism agreement F | M/N, N=choose(m,3) for justified rooted triplets or choose(m,4) for a justified unrooted question; M+D+U=N | Matching resolved relationships, conflicts and unresolved/missing relationships retain separate counts. Native common-leaf distance does not replace this fixed intended denominator. |
| Observed functional coverage C | k_f/n when no known other function class occurs in the fixed intended reference clade;0 when a known other class occurs | Characterized coverage under observed homogeneity. Unknown references do not establish full-clade purity. |
| Interior placement J |1 strictly inside the query-pruned fixed crown;0 for stem/outside/resolved nonmonophyly; bounds for relevant unresolved membership | Evaluated on actual tree/graft samples. Native weights supply placement mass, not a probability of target function. |
| Reference-relative distance O | min(1,b/d), d=nearest characterized query path distance; b=median nearest-other distance among characterized references | An exposed proposed attenuation, not a native confidence score. Distances share a tree/model scale and retain pendant length. |

For an applicable region r in a supplied native joint sample z:

    a_r(z) = C_r(z) * F_r(z) * J_r(z) * O_r(z)
    A_r = sum_z w_z * a_r(z)

Use the same draw and globally consistent source assignments for every factor.
For several distinct necessary applicable regions, take their minimum within
each actual joint draw, then average with its supplied weights. The proposed
final reducer is the minimum of the resulting means over included comparable
analyses. Only marginal samples permit the specified finite-coupling bounds,
not an invented pairing or independence assumption. Repeated representations
are not new samples or requirements.

Exact-zero distance cases are specified: d=0 gives O=1 under the declared
coincidence convention; b=0,d>0 gives0. Missing or rounded values retain their
actual bounds; one characterized reference with positive d does not invent b.
A known zero factor identifies the product while other factor cells remain
missing. Nonnegative/incompatible-scale input validation is specified by the
sheet, not claimed implemented by its bounded fixtures.

Broad organismal-tree scoring for frequent-HGT families is not applicable.
Only an actually justified very local, near-relative scope can use this
comparison. There is no numerical applicability grade, compulsory HGT search,
universal distance cutoff or favorable-scope selection by score maximization.
Low positive support does not become opposing evidence.

## Checked complete synthetic examples

The base fixed two-reference clade has measured f assignments on both members.
Four stipulated placements have native-style weights(.6,.2,.1,.1),
F=(1,.75,.75,.25), J=(1,1,0,0), C=1. Interior b=.6,d=.3 gives O=1.

    A = .6*1 + .2*.75 = .75

Changing only the query pendant length makes the interior d=6, hence O=.1:

    A_far = .6*.1 + .2*.075 = .075

Attachment dispersion EDPL remains46/325 in both. It is a diagnostic, not a
second uncertainty penalty. A known different function outside the crown does
not change .75; a known different class inside it gives precise C=0. A shared
broader function requires a separately defined assertion, never score rescue.

With three reference members but only two characterized f, an otherwise fully
specified matching fixture gives observed2/3. Full-clade purity remains unknown
and the full-claim completion range is[0,1]. The observed2/3 is not a probability
or a guaranteed lower bound after discovering a different function.

A second necessary region scoring.4 in every shared base draw gives
.6*.4+.2*.4=.32. Taking min(.75,.4)=.4 instead would combine different levels
of aggregation and is not the stated equation. Anti-correlated binary required
regions can give0 despite each marginal mean.5; without their pairing the
exact admissible-coupling interval is[0,.5].

## Published contrast converted into actual scoring cells

Song et al.2005, DOI10.1186/1741-7007-3-13, supplies a selected TyrA family
tree and reported biochemical assignments. The source-defined displayed
Pseudomonas/Azotobacter subgroup has five intended reference slots; adding its
displayed Acinetobacter sister gives a separate six-member comparison.
These are complete inventories of the declared displayed groups, not complete
natural families and not a newly chosen favorable subset.

Under the explicit author-assignment and assay-to-tip correspondence conditions:

| Distinct comparison | Numerical inputs | Existing C calculation |
|---|---|---:|
| Five-reference group, NAD+-specific use of both prephenate (PPA) and arogenate (AGN) |2 assigned;3 uncharacterized; no received other class |2/5=.4 |
| Six-reference group, same precise cofactor/substrate profile |2 assigned; Acinetobacter has the reported NADP+-specific profile |0 from known heterogeneity |
| Same six references, positive use of both substrates without a cofactor restriction |3 assigned at the broader resolution;3 uncharacterized |3/6=.5 |

The narrower assignments use the Results' explicit specificity statements;
Table4 listing one cofactor alone would not establish specificity. Original
selectivity assays, tested ranges and detection limits were not independently
inspected. Therefore these are conditional formal cells using reported
experimental assignments, not newly measured selectivity or unconditional
canonical points. The additive specificity qualification is part of the
current specimen's assumptions and missing-operand interpretation.

Three shared mapping variables give current-observation envelopes[0,.4],
[0,1/3] and[0,.5]. The Avin identifier discrepancy remains one uncharacterized
slot under both possible identifiers; it does not manufacture another member.
Eight mapping combinations times those two identity choices give16 checked
scenarios. Their weights are not probabilities. The three comparisons share
evidence and are not added together.

Independent organismal topology, actual query placement and numerical branch
paths remain absent. The paper's16S congruency grouping does not establish
F=1. Thus the real source fills C and its population fields; it does not supply
a whole-target A104 point. CLC-F8/29 remains a screening-panel diagnostic,
and Wege40/9 an assay contrast, not substitutes for complete-clade C.

## Goal criteria and actual verification

1. Current sheet004 and exact fields004 define inputs, units, intended
   denominators, arithmetic, uncertainty and missing/zero meanings.
2. The component product, native average, shared necessary-region minimum,
   comparable-analysis reducer and finite-coupling bounds are explicit. No
   intuitive overall grade supplies a missing relationship.
3. The TyrA published contrasts fill formal C cells with checked arithmetic
   and explicit conditional assignments. Fully synthetic complete examples
   demonstrate the remaining joins without inventing source tree quantities.
4. Same-molecule duplicates, shared sources, native samples, conflicting
   assignments, multifunctionality, nondetection and unexamined members retain
   distinct meanings. Missing observations are not negative assays.
5. The main source table identifies native tqDist/pplacer methods and original
   biological examples. The TyrA source-to-canonical table identifies figure,
   table, member, assignment and inspection extent for each new scoring input.
6. Exact future-reader inputs and outputs remain separate from prompts and
   numerical formulas. Readers are specified, not implemented by this work.
7. The parent delivers the metrics, equation, synthetic and published numerical
   examples, assumptions and exposed policy choices in the conversation. The
   user's latest organismal/HGT/mixed-function/outlier direction governs them.

Parent read main531 lines, exact-fields175 lines, old checker408 lines, current
handoff, full contract-review032/read record/new checker/new receipt, and the
complete033 source conversion/input specimen/checker/receipt/specificity note.
It did not reopen the original TyrA paper. After reading the retained TyrA
packet, it reread the complete required authority set before interpretation:
root AGENTS/GOAL; complete EPISODE_STRUCTURE/TIME_AWARE_ESTIMATION;
TOOL_KNOWLEDGE/TASK_AND_STEERING; both task/evidence amendments; full VERBATIM
DIRECTION/RECOVERY002; full EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS; numeric review002;
research AGENTS/SOURCE_CORRECTIONS/A105 assignments; goal attachment; then the
latest user instructions. Sequential outputs were complete; no truncated
portion was accepted as read in this reset.

Owner025's checker005 ran, but its literal-zero line did not validate the
helper's known-zero behavior. Fresh reviewer032 reproduced the entire saved
receipt and added actual corrected cases for all four zero-factor positions,
plus resolved nonmonophyly obscured by an unrelated polytomy. All bounded
checks passed. Original records remain intact. The reviewer also corrected
the handoff's missing qualification about factoring C. Parent inspected these
results without another redundant execution. No general source reader, native
tree program, biological calibration or production test is claimed.

The source workers retain their actual reset records and provisional-message
ordering errors. Their final conversions followed completed rereads; these
records do not claim flawless earlier ordering. Parent conversion followed its
own completed packet reset.

Equal subset/reference weighting, C coverage under observed homogeneity, b/d
attenuation, exact-zero distance conventions and the stated pooling remain
fully specified proposals for human judgment. They are not adopted policy.
No essential calculation is left undefined in this research proposal; actual
missing empirical operands stay missing. The all-ten research goal is distinct
from W04/W05 production implementation and the repository's annotation goal.
