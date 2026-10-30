# A108 current numerical research proposal — 2026-10-24

This is the current combined reading of the sample-context sheet 014, its
qualifications, and organism-context proposal 018 with its qualifications.
All original records remain unchanged. It defines a numerical research sheet,
not an adopted scoring policy, prompt, implemented reader or production change.

The user's definition remains:

> (8) This is a pseudo-grader/literature reading exercise - does the proposed function seem plausible given what we know about the sample and the organism? Does it make sense with the general clade of the organism (if we know that).

The measurable question is contextual compatibility with the actual function
and scope. It has two distinct forms: whether an organism admits a required
biological situation, and what fraction of a specified sample's opportunities
satisfies the relevant contextual requirements. They must not be combined as
independent confirmations or selected according to which score is larger.

## 1. Numerical inputs

Investigation can start with a sequence, selected file record or snippets.
An organism assignment or possible function may emerge later. Extraction does
not require an initially named candidate. A persistent candidate's meaning and
scope determine which contextual relations are relevant before calculation.

| Input | Exact numerical meaning, units and limits |
|---|---|
| Native trait or exposure | A measured number/interval in its physical unit, or an observed biological state set: compartment, accessible route, life stage, host relation, concentration, distance, time or other defined trait. A taxon name alone supplies no numeric value. |
| Measurement correction | For an apparent calibrated concentration y, procedural blank b in the same unit and measured recovery r>0, x=(y-b)/r. Recovery is measured spike increment divided by known spike concentration. Preserve actual dilution and local-mapping operands. Do not correct an already corrected value again. |
| Observation uncertainty B | Admissible corrected local values, retaining censor limits, open/closed boundaries, reported uncertainty and source conflicts. Bulk concentration is not automatically local exposure. |
| Supported domain D+ | States/values where the specified contextual requirement is supported, conditional on its measured background. Sufficient operation at one dose does not establish a minimum or continuous interval. |
| Incompatible domain D- | States/values with demonstrated incompatibility or an actual necessary physical exclusion. Untested values are not automatically incompatible. D+ and D- must be disjoint; unresolved conflicts retain both source records and unknown membership. |
| Requirement set | Necessary contextual relations for this role in the stated scope, including genuine alternative routes. Joint combinations require joint support or a justified model; favorable marginal experiments do not establish every combination. |
| Sample denominator | Unique opportunities in a fixed sample frame. Positive weights are 1 for equal-probability units, actual measured duration/volume, or documented inverse-inclusion weights 1/p. No source-count/reputation weights. |
| Organism-state scope | Biologically permitted situations, plus an unresolved remainder whenever permitted states have not been exhaustively examined. A finite observation list is not automatically the whole organism's capability. |

For nonnegative concentration under the stated linear recovery model:

`x_lower=max(0,(y_lower-b_upper)/r_upper)`;
`x_upper=max(0,(y_upper-b_lower)/r_lower)`, requiring r_lower>0.

These are outer bounds under a physical nonnegative model, not permission to
hide an incompatible calibration. Unknown calibration or local mapping leaves
the local value unknown. Native quantities retain their own units; oxygen gas
volume fraction and dissolved oxygen saturation are not interchangeable.

## 2. Membership and joint components

For state/sample unit i and requirement j:

`ell_ij = 1 if all admissible values B_ij are in D+_j, otherwise 0`;
`u_ij = 0 if all admissible values B_ij are in D-_j, otherwise 1`.

Domain uncertainty and actual shared model parameters are included in these
admissible evaluations. [1,1] denotes an established compatible event, [0,0]
an established incompatible event, and [0,1] an unresolved event. These are
logical bounds, not ordinal quality grades or reader-assigned probabilities.

For necessary conditions on the SAME unit:

`L_i=product_j ell_ij`; `U_i=product_j u_ij`.

The products express conjunction, not statistical independence. Duplicate
predicates refer to one event. Genuine alternative routes use logical OR after
each route's required conjunction. An unsupported joint operating domain is
unresolved even when separate favorable measurements exist. An irrelevant
requirement is absent; a relevant but missing one remains [0,1]. An empty
external-environment requirement set means no relevant external requirement,
not that an environment was measured. An unspecified overall question or
requirement meaning does not earn a perfect score.

Native margins such as x-a and b-x can be displayed for a sourced interval
[a,b]. They are not extra points added to membership. A negative margin outside
D+ is not counterevidence unless the value also lies in D-.

## 3. Complete numerical combinations

**Sample-context coverage**, with fixed W=sum_i w_i>0:

`C_lower=sum_i w_i*L_i/W`; `C_upper=sum_i w_i*U_i/W`.

The supported, unresolved and incompatible masses are respectively
`C_lower`, `C_upper-C_lower`, `1-C_upper`. They sum to one. A fully identified
descriptive point is C_lower=C_upper. Otherwise keep point=null and both bounds;
the proposed conservative supported contribution is the explicitly labeled
lower bound, not a point estimate of the unknown true fraction.

For fully observed access A, exposure E and oxygen O on paired units:

`C=(W_A/W)*(W_AE/W_A)*(W_AEO/W_AE)=W_AEO/W`.

If an intermediate denominator is zero its conditional ratio is undefined;
the direct final fraction remains defined. The result does not depend on the
display order. When only unpaired marginal fractions p_j are available, use
`max(0,sum_j p_j-(J-1)) <= C <= min_j p_j`; use marginal lower/upper endpoints
on the respective sides when uncertain. Do not multiply unpaired marginals.

**Organism capability** asks whether at least one permitted biological state
supports the role:

`O_lower=1-product_s(1-L_s)`;
`O_upper=1-product_s(1-U_s)`.

This is OR on logical events. It is not an independence calculation. A verified
compatible witness establishes O=1 for that stated capability. Repeating the
witness in more papers adds nothing. Without a witness, unexamined permitted
states remain an unresolved [0,1] remainder. O=0 requires actual whole-scope
exclusion; zero sightings in a finite sample does not establish impossibility.

`question_kind=organism_capability` selects O; `sample_context_coverage`
selects C. The question follows the candidate's meaning, not the available
numeric result. Return both diagnostics when useful, but do not add them or
take their maximum. The proposed 100-point display is just 100 times the
selected bounds. Neither number is the probability of a correct annotation.

A rare-use function is evaluated in its stated use context. The fraction of
an organism's life spent in that context is a separate observation and is not
automatically an additional penalty. A broader or narrower revised claim must
retain the original scope/result; it is not silently repriced history.

## 4. Uncertainty and evidence handling

Analytical uncertainty, missing inputs, source disagreement and sampling error
remain distinct. All-missing inputs give point=null, [0,1] and no-data status.
A zero lower bound with upper one means no established lower support, not a
measured incompatible organism. Unknown target identity or unsupported transfer
from another organism makes the relevant trait unresolved.

For the explicitly independent, equal-weight sample design, a proposed
distribution-free sampling enclosure uses
`epsilon=sqrt(log(2/alpha)/(2*n))`, alpha=.05. Around resolved C use
`[max(0,C-epsilon),min(1,C+epsilon)]`; with analytical bounds use the conservative
outer endpoints C_lower-epsilon and C_upper+epsilon and retain both uncertainty
meanings. This is conditional on the actual independent-unit design. A finite
census needs no population-sampling claim. Correlated images/aliquots do not
increase n; use an explicitly defined independent cluster-average estimand or
leave the sampling interval unavailable. Weighted/complex-design inference
is not supplied by this equal-weight formula.

Duplicates use one original unit and weight. Technical repeats refine its
measurement without creating sample opportunities. New independent specimens
can expand a sample only within its declared design. Studies of different
habitats remain separate strata unless actual population mixing weights exist.
A same-state unresolved conflict has [0,1]; distinct states can differ without
contradiction. Nondetection uses a measured limit, not a fabricated zero.

An activity measurement defining an operating domain remains a shared
dependency of A105/A108. It is not a new independent activity experiment or a
second reliability multiplier. Partner and pathway results retain A107/A110
ownership. Gene/organism tree concordance and functional clades remain A104;
a clade name cannot generate an A108 tree or trait score.

## 5. Filled and checked examples

**Synthetic paired environmental example:** ten independent equally weighted
microhabitats, eight accessible, six of those within a supported concentration
domain and five of those also within the supported oxygen domain. Thus
`8/10 * 6/8 * 5/6 = .5`. The separately stipulated jointly supported domain is
2.5–10 mM acceptor and 0–1% oxygen; these are fixture conditions, not thresholds
inferred from a paper. A corrected measurement is `(4.2-.2)/.8=5 mM`, with
bounds `[3.89/.82,4.11/.78]=[4.743902439,5.269230769]`, inside that domain.
The conditional independent-sampling interval is [.07053059165,.92946940835].

The unpaired marginal product .8*.8*.9=.576 is invalid for this joint event;
its legitimate marginal-only bounds are [.5,.8]. Making one relevant unit
uncertain gives [.5,.6]; a conflict in one formerly supported unit gives
[.4,.5]. A genuine below-limit interval wholly in a demonstrated failure domain
remains incompatible; a limit spanning both domains remains uncertain.

**Synthetic organism-state example:** twelve division contexts; ten give
physical access to the proposed site, and nine of those satisfy the measured
width requirement. Sample coverage is `10/12 * 9/10 = .75`; capability is 1
because a compatible state is witnessed. With only one compatible context,
coverage is 1/12 while capability remains 1. With twelve incompatible observed
contexts but an unexamined permitted remainder, capability is [0,1], not zero.
One unresolved formerly compatible context gives coverage [2/3,3/4]. The full
native-valued synthetic rows remain in the original fixture, not new data.

| Source-filled contrast | Numerical cell and actual limit |
|---|---|
| Huc atmospheric-H2 work, Grinter 2023 | 530 ppbv benchmark, residual <approximately 40 ppbv and initial 3000 ppbv. The benchmark/residual bound is >approximately 13.25. A single-benchmark compatibility event can be 1 only under the explicit matched-context, monotone-depletion interpolation; without that model its membership is unresolved. This is not a surveyed target-habitat score. |
| Tetrathionate, Winter 2010 | Figure-derived bulk mean approximately 3.3 mM versus a separately sufficient broth dose 2.5 mM gives approximately 1.32. A visual reading range 3.2–3.4 gives [1.28,1.36]. A sufficient dose does not supply a minimum, local access or an individual sampling denominator; full context score remains unknown. |
| B. plebeius porphyran use, Hehemann 2012 | A narrowly interpreted dietary route to the named intestinal resident gives a contextual route [1,1], not a current sample concentration. The 35/40 expression coverage and 291 screened strains do not supply an A108 population denominator. |
| S. acidocaldarius Cdv, Lindås 2008 | A native cytokinetic constriction context is established [1,1] for the specified strain. An endosomal-context predicate remains [0,1]; the inspected source is not an endosome census. No clade-label absence is fabricated. |

Source links: [Huc](https://doi.org/10.1038/s41586-023-05781-7),
[tetrathionate](https://doi.org/10.1038/nature09415),
[porphyran](https://doi.org/10.1073/pnas.1211002109),
[Cdv](https://doi.org/10.1073/pnas.0809467105).
These source observations remain attributed to the original reviewers;
the parent did not reopen their primary papers or paper-specific packets in
this consolidation. Reported, graph-derived, interpreted and synthetic values
retain their different origins.

## 6. Exact population fields and separation from prompts

The complete retained input/output specifications are
`../a108_plausibility_sheet_014/READER_CONTRACTS_001.md` and
`../a108_organism_context_018/READER_FIELDS_UNIMPLEMENTED_001.md`.
They are separate, unimplemented reader specifications, not text to insert
into a scientific episode prompt. Their shared cells feed the following exact
current calculation:

| Targeted population responsibility | Required fields/output consumed by this sheet |
|---|---|
| Literature or dataset measurements | `original_measurement_id`, `unit_id/state_id`, `independent_cluster_id`, actual subject/scope, `value/lower/upper`, unit and boundary inclusivity, censor limit, uncertainty kind, origin, source locator, correction history. Both input routes populate the same numeric fields. |
| Calibration/local conversion | `blank`, measured spike/increment/recovery, correction status, actual bulk-to-local model and operands; corrected local B and unresolved quantities. |
| Contextual requirement | `role_meaning_ref`, `relationship_kind`, trait/unit map, disjoint supported/incompatible regions, joint support, interpolation model/parameters, alternative routes, exceptions and original axis/dependency identities. |
| Narrow literature interpretation where a quantity is unavailable | Exact proposition, subject, role, population/compartment/life stage, actual source facts, necessary relation, permitted alternatives and counterexamples; returns supported/incompatible/unresolved state sets. It does not return an overall numerical confidence grade. |
| Membership calculator | Native margins, `ell/u`, per-state/unit `L/U`, conflict and missing-operand identities. |
| Organism capability calculator | Unique state events, `permitted_unexamined_remainder`, any actual whole-scope exclusion record, `capability_lower/upper/point`. |
| Sample calculator | Fixed frame, unique units and actual weights, `sum_weights`, supported/unresolved/incompatible weights, conditional numerators/denominators, `coverage_lower/upper/point`; sampling interval with exact method/design or null. |
| Selected result | Original `question_kind` and scope, `selected_lower/upper/point`, both separately labeled O/C diagnostics when known, missing operands, source basis and shared dependencies. |

Scope interpretation is not an overall quality grade. Deterministic arithmetic
fills the score after the reader has supplied the exact observations/relations.
Unknown biological relationships cannot be repaired by inventing a percentage.

## 7. Criteria, verification and unresolved choices

The sheet defines numerical cells and units/denominators; explicit paired AND,
capability OR and sample-fraction combinations; contrasting source-filled and
complete synthetic examples; shared/replicated/negative/nondetected handling;
source-to-component trace; and exact separate population fields. Conversation
delivery remains necessary before counting the seven research criteria met.

Parent checks already recorded in `parent_arithmetic_001.json` and
`organism_context_parent_arithmetic_002.json` verify respectively 21 and 9
bounded arithmetic assertions. They were not rerun in this consolidation.
The parent reread the full core numerical sheet, both qualification documents,
the organism extension and both exact reader contracts. Earlier fixture and
source inspection coverage remains attributed in its original records.

The capability/coverage distinction, conservative lower-bound credit display,
100-point display scale and explicit domain interpolation remain proposals
for judgment, not accepted policy. Native missing data, unsupported trait
transfer and absent sampling designs remain unfilled with defined bounds.
This is a finite contextual compatibility proposal, not a universal solution
for every biological plausibility argument. No production scoring, readers,
prompts, target annotation or episode behavior was implemented or changed.
