# A108 organism/clade-context numerical extension — research proposal

The organism question is **whether the organism admits the cellular or
ecological situation required by the emerged function**. That question does
not require a measured series of environmental exposures. A second question,
already handled by draft 014, is **what fraction of a stated sample's
opportunities meets the contextual requirements**. Keep these two numerical
meanings explicit. A rare but demonstrated opportunity can answer the first
question positively while occupying a small fraction in the second.

This extension supplies concrete organism-state operands and an existential
combination for the first question. It preserves draft 014's membership and
paired-fraction arithmetic for the second. It is a proposed interpretation for
the user's review, not an adopted formula or a new evidence axis.

## 1. Formal numerical cells

Begin with supplied sequence, selected file contents or bounded snippets.
Record organism/sample information actually supplied or subsequently established.
Possible functions can emerge later. The comparison below begins only once the
meaning of a function and its biological scope have been stated; no initial
candidate or public identifier is required for investigation or extraction.

| Cell | Numerical meaning and units | How obtained |
|---|---|---|
| Native organism trait x | Measurement in its physical units, or a directly observed discrete biological state | Cell anatomy, morphology, life-cycle state, host niche, trophic route, or another specifically relevant organism observation. Protein partners, pathway completion and gene-tree placement retain their other-axis owners. |
| Trait margin m | x−a in x's native units, for a stated necessary lower boundary a; reverse for an upper boundary | Calculated from an observed trait and a sourced necessary relation. No standard “close enough” threshold. Both operands and their uncertainty remain visible. |
| Lower/upper compatibility ell/u | Logical bounds in {0,1}, with ell≤u | The trait lies wholly within a supported biological state/domain → [1,1]; wholly within a demonstrated incompatible domain → [0,0]; otherwise [0,1]. This is the existing membership operation, now populated with organism traits. |
| Joint organism-context L_s/U_s | Bounds on all necessary contextual requirements holding in one admissible organism state s | Products over the relevant requirements on the same state, after shared predicates are deduplicated. |
| Organism capability O−/O+ | Bounds on at least one permitted organism state supporting the role | OR across state-level joint events, including an unresolved remainder for unexamined permitted states. Formula below. |
| Sample compatibility C−/C+ | Fraction of a fixed, measured sample frame jointly compatible | Draft 014's weighted sums over unique sample opportunities. This is not the prevalence of the function in a clade. |
| S108−/S108+ | 100 times the selected contextual quantity | The sheet explicitly records whether the candidate's A108 question is capability or sample coverage. The two displays are never added. |

Margins are native diagnostic components, not independent additional points.
For two-sided domains preserve both margins, x−a and b−x. For a discrete
observation such as a cellular compartment, the predicate is its physical
existence/access relation; it is not a grade for a clade name. A count, time,
distance, fraction or concentration already available is retained instead of
being replaced by a verbal adjective.

## 2. Exact organism comparison

For each stated organism state s and relevant contextual requirement j, retain:

* the actual target organism/strain or explicitly unresolved identity;
* the trait and the function's necessary relationship to that trait;
* the observed value set B_sj, preserving numerical uncertainty or alternatives;
* disjoint supported and incompatible domains D+_j and D−_j;
* the source that makes this relationship relevant to the specific role;
* the population/life-stage/host/compartment to which the statement applies;
* observed facts separately from any narrow contextual interpretation.

Use the existing arithmetic:

    ell_sj = 1 if B_sj is entirely inside D+_j, otherwise 0
    u_sj   = 0 if B_sj is entirely inside D−_j, otherwise 1
    L_s    = product_j ell_sj
    U_s    = product_j u_sj

All necessary relations must be about the same state and have joint support.
An unsupported Cartesian product of favorable marginal conditions stays unknown.
If the requirement itself is not justified as necessary, do not use it to
exclude the role. An observed counterexample can invalidate that requirement
without being a contradictory measurement of the target.

The paper conversions give two populated examples of that distinction:

| Source case | Relevant organism relation | Populated organism result | What is not inferred |
|---|---|---|---|
| Gut B. plebeius porphyran use | Dietary material can reach the intestinal niche of the named resident organism | Narrow habitat-route membership [1,1], conditional on the explicit route interpretation; current sample substrate quantity remains unknown | Marine origin of a characterized enzyme does not impose marine residence on the target. No fraction of the 291 screened strains is used as a penalty. |
| S. acidocaldarius Cdv | The native organism makes a cytokinetic constriction site | Existence of the cellular opportunity [1,1] for this strain; no cell-frequency estimate | Eukaryotic endosomal-sorting homology does not establish an endosomal compartment in the target. That compartment operand is missing in the inspected paper and remains [0,1]. |

These are limited contextual memberships, not “100% correct annotation.” For
another target, the organism comparison must be filled anew. The source's
characterized molecular activity is a dependency defining the role; it cannot
also be counted as independent new A108 activity evidence.

## 3. Explicit combination for organism capability

Let s enumerate distinct, biologically permitted contextual situations in
which the role could operate. This is not a list of publications or positive
examples. A witnessed situation may suffice for an existential question. An
unexamined permitted remainder is one unresolved state [0,1], regardless of
how many papers have been read.

    O− = 1 − product_s (1 − L_s)
    O+ = 1 − product_s (1 − U_s)

This OR evaluates the event “at least one admissible organism context is
compatible.” The products operate on logical indicators and do not assume
statistical independence. Additional observed occurrences do not increase O
after one compatible situation establishes O=1. A rare witnessed situation is
not diluted by counting unrelated life stages or other members of the clade.

An empty evidence set includes the unresolved remainder: O=[0,1], point=null.
To obtain O=[0,0], every permitted situation must be incompatible, or a sourced
necessary organism constraint must exclude the role across the entire scope.
Failure to observe the situation is not such a constraint. Thus zero sightings
in 50 cells does not, by itself, give a zero capability score.

For a role with alternative contextual routes, evaluate each route's necessary
conditions as an AND and the alternative routes as an OR. Do not require every
alternative route simultaneously. The same physical event has one identity
even if several sources describe it.

This existential component addresses the organism/clade gap without forcing
“this organism can have this contextual opportunity” into a frequency of
environmental encounters. It also represents a genuinely narrow literature
judgment as a stated biological relation, rather than a universal relevance
weight. When the relation cannot be resolved, it yields an interval, not 0.5.

## 4. Handoff with the existing sample branch

The sheet records `question_kind` from the biological meaning before scoring:

| A108 question | Exact proposed contribution |
|---|---|
| Is this role contextually possible for the named organism within its stated life-cycle/host scope? | S108 bounds = 100×[O−,O+] |
| Over what fraction of the stated sample opportunities are the organism and local circumstances jointly compatible? | S108 bounds = 100×[C−,C+] from draft 014 |

This is not a choice of whichever number is larger. A capability claim and a
population-coverage claim are different claims. Record both numbers when both
questions matter; only the quantity named by `question_kind` is the proposed
single A108 contribution. The scope cannot be changed after seeing the scores
without recording a revised biological claim and preserving the prior result.

For the sample branch, append the relevant organism predicates to each existing
ContextUnit. With O_i the joint organism-state event and E_i the already defined
local-environment/access event on that same unit:

    C− = sum_i w_i * O_i− * E_i− / sum_i w_i
    C+ = sum_i w_i * O_i+ * E_i+ / sum_i w_i

This is the same conjunction and weighted-fraction calculation as draft 014.
No separate clade multiplier is added. If an intrinsic organism predicate is
shared by every unit, its exact logical value can be factored outside the sum.
If the two branches are only unpaired marginal proportions, use the existing
Fréchet bounds; their product is not justified.

When there is no external environmental requirement for the scoped cellular
role, the empty environmental conjunction is 1 by definition. It is labeled
`no_relevant_external_requirement`, not `environment_measured=true`. If a
relevant environmental requirement exists but is unmeasured, E=[0,1].

The A108 handoff is `{question_kind, scope, lower, upper, point, component_cells,
missing_operands, shared_dependencies, source_basis}`. Use the lower bound as
the proposed conservative supported contribution, paired with its upper bound
and missingness. A lower bound of zero with upper one is not an observed
contradiction. Neither O nor C is a calibrated annotation probability.
W05 retains ownership of connection to annotation credit.

## 5. Clade information and narrowly defined judgment

Clade information is useful only through an explicit organism trait or relation.
For example, a trait record can identify the lineage, cell architecture,
life-cycle scope and documented exceptions to a physiological generalization.
The reader must establish that the actual target lies inside that record's
scope. A taxon name is not sufficient to fill any numeric cell.

Direct target observations take precedence over a transferred generalization
when their scopes match. A demonstrated exception is not downweighted for being
unusual. If target membership or trait transfer is unresolved, retain the
possible trait states in B; do not apply an ordinal transfer penalty. Gene-tree
placement, HGT plausibility and evolutionary frequencies remain A104. Partner
and pathway measurements remain A107/A110, even when their requirements are
referenced in an organism-context argument.

A genuinely nonquantifiable narrow interpretation requires these populated
fields: **exact proposition; biological subject; role; population/compartment/
life-stage; source facts; necessary relationship; permitted alternatives;
counterexamples/exceptions; outcome as a supported/incompatible/unresolved
state set**. It cannot emit an overall numerical confidence. The deterministic
membership/AND/OR operations supply the numerical result after this narrow
interpretation. If a measurement can answer the predicate, use the measurement.

For the porphyran example the proposition is specifically whether dietary
polysaccharides have a route to the named intestinal resident, not whether the
whole annotation is convincing. For Cdv it is whether the named organism
produces a relevant constriction site, not whether every ESCRT homolog is a
division factor. Those referents prevent a general “plausible” adjective from
being substituted for the actual sheet.

## 6. Uncertainty, conflicts and repeated evidence

* Analytical intervals, conflicting organism assignments, unobserved contexts
  and sampling uncertainty are distinct fields. An interval that crosses a
  required boundary stays [0,1].
* A contradictory measurement on the same subject/state retains both source
  records and gives unresolved membership until the difference is explained.
  Different life stages or compartments are not automatic contradictions.
* Native observations from independent specimens can increase the measured
  sample denominator only if they belong to its fixed sampling frame. Multiple
  reports, technical measurements, readers or database mirrors do not do so.
* A capability witness is not stronger because it is published repeatedly.
  Independent replications inform uncertainty about the original observation;
  they do not create more organisms or multiply O beyond one.
* A sampled clade trait fraction is descriptive of its measured organism frame.
  It is not the probability of the proposed target annotation. Prediction to an
  unobserved target requires its own actual sampling/transport model and is
  otherwise unresolved. Function prevalence is never used as a contextual
  requirement.
* One original assay may define a necessary operating domain while anatomy or
  sample data place the target in it. Keep the domain assay's original owner
  and dependency ID. Do not apply its reliability penalty or credit again.
* Source observations that define a domain are not held-out validation of that
  same domain. A context score can be filled for the original studied organism,
  but it is not claimed as new independent confirmation.

These are sheet semantics, not a runtime gate, prescribed experiment sequence,
new controller or mandatory approval stage. All readers described separately
remain UNIMPLEMENTED.
