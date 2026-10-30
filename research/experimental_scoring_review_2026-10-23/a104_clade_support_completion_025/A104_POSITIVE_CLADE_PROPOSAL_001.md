# A104 positive clade placement with the received contrary evidence

Goal: supply a complete numerical A104 contribution when the evidence locates
the query inside a characterized reference clade but no incompatible
characterized reference has been received. Success means a defined scientific
endpoint, numerical operands and reductions through the whole candidate,
contrasting checked trees/placements, explicit missingness and dependencies,
and exact fields for future readers. It does not mean another paper survey,
production implementation, calibration, acceptance of this proposal, or a claim
that A104/the global goal is complete.

This is an additive correction to the **scope** of the sparse-reference row in
`../a104_history_completion_020/A104_HISTORY_AND_CANDIDATE_PROPOSAL_002.md`.
That row correctly leaves a discrimination-only result unidentified without an
incompatible reference. It should not also make positive clade association and
its candidate contribution unidentified solely for that reason. The old
contrast profile remains defined and unchanged. The new profile below adds an
explicit positive-clade term and uses received contrasts when they exist.

No primary paper or retained paper-specific packet was opened for this work.
The source trace below reuses coverage reported in the complete cross-case
sheets; it does not claim a new primary inspection. All new complete examples
are synthetic. All equations introduced here are proposals, not source facts.

## 1. Scientific endpoint before arithmetic

For one homologous query region and one declared, source-grounded reference
clade, measure the native tree/placement weight that puts the query **inside
that clade's crown**, discounted by its distance from actually characterized
function references and by its agreement or explained disagreement with
organism history. Limit that support by any included, scientifically comparable
contrasts with actually characterized incompatible functions. Retain their
opposing contributions separately.

This is a phylogenetic compatibility contribution for the current candidate
and received evidence. It is neither a probability of function nor a claim
that every member of the clade has the same function. It does not establish
that every possible competing function has been investigated. The positive
question is available without such an investigation.

Three profiles/outputs must remain distinguishable:

| Output | Question | No received incompatible reference |
| --- | --- | --- |
| `crown_association` diagnostic | How much native placement/tree weight is inside the declared reference crown? | Fully calculable when its own tree operands exist. |
| `contrast_only_v2` | Does the query lie preferentially with f rather than each included g? | Unidentified, as in proposal002. |
| `clade_received_contrasts_v1` | How much positive clade/history support remains after included contrary comparisons? | Fully calculable; the received-opposition sum/set has no contributions. |

The final proposed A104 coordinate in this document uses the third profile.
The profile is selected by the question, not by which output is larger. The
two profiles from the same data are never added as two sources. A missing
clade definition does not silently switch this calculation to contrast-only.

## 2. Reference scope and functional heterogeneity

Before evaluating placement numbers, supply these finite source-backed sets:

* `V`: the intended query-free backbone tip inventory, with actual sequence,
  organism/copy and region identities. An outside tip need not have a known
  function, but the root and the clade's external boundary must be identifiable.
* `C_f`: a fixed set of at least two backbone tips defining the candidate
  reference crown at the functional/lineage scope being evaluated. It must be
  a proper subset of V. Its source boundary and membership mapping are explicit.
  It is not `MRCA(query, all attractive references)` and is not recut after
  observing a favorable query placement.
* `R_f`: the nonempty set of distinct, actually characterized f references
  within C_f. Their measured endpoint must support f at the stated resolution.
  A predicted name, untested nearest sister or source author's generic family
  label cannot become a characterized anchor.
* `G`: the current included, comparable incompatible-function comparisons,
  each with its fixed `R_g`. Include eligible contrary evidence actually
  received anywhere on the intended backbone, including inside C_f. A genuine
  missing record for an included comparison remains in G with unknown operands.

`C_f` may include uncharacterized leaves. They define geometry, not additional
positive experiments. Only R_f enters the positive reference-distance scale.
Keep the counts/identities of positive, incompatible, nonexclusive/other,
uncharacterized and unmapped leaves visible; do not convert these inventories
into a functional-purity probability. Known incompatible leaves are evaluated
through G, including when the broad clade is functionally heterogeneous. Thus
the clade name cannot override contrary reference placement.

Incompatibility is scoped to the actual inference. Two different substrate
names alone do not establish it: a multifunctional protein can support both.
A shared broad function may put both characterized proteins in R_f; a narrower
exclusive claim may require a real activity contrast. A reference cannot be
used in both incompatible roles for the same contrast. If the relation itself
is unresolved, retain role-assignment scenarios/bounds; do not decide it from
the convenient sign of the score.

The source-defined clade may contain only one characterized reference and
several uncharacterized leaves. Crown membership can still be measured, while
the existing within-function distance normalization is missing. A singleton
tip by itself supplies no crown interior: this profile then reports a missing
multi-tip clade scope, rather than inventing a crown or counting its terminal
stem as an interior. Neither situation requires an incompatible reference.

A claim that *all* members have f or that this lineage is exclusively f exceeds
the association endpoint. Uncharacterized members cannot establish that
universal claim. The sheet preserves that qualification instead of supplying
a guessed prevalence or treating the claim as established by a clade label.

## 3. Query pruning, edges and native support

For each complete query-bearing rooted tree, prune q first. Suppress resulting
unary nodes, adding the two adjacent lengths in their original units. Retain
where the q graft occurred on the resulting backbone. The query must not help
define the very clade whose membership is being measured.

For an ordinary binary graft, deleting q suppresses its parent. Its other
child identifies the merged backbone edge; the original child-edge length is
the distance from that edge's distal end to the graft. Keep q's pendant length
separately. An attachment at a retained multifurcating node stays a node
attachment. If pruning removes the root, preserve the original rooting and
virtual root attachment; it is outside any proper reference crown. Do not
reroot to improve membership.

In a resolved, complete query-free tree, let v_f be the node whose descendant
tip set is exactly C_f. Define J_f for a point placement:

* `J_f=1` if v_f exists and the attachment is strictly below v_f, on an edge
  or at a node in its descendant subtree. Terminal edges below the crown count.
* `J_f=0` if v_f exists but the attachment lies on its entering stem, outside
  its subtree, or above it. A query sister to the entire crown is not an
  interior member. The stem still has its own reported native placement mass.
* `J_f=0` in a resolved complete tree when C_f is nonmonophyletic. That is a
  failure of this particular clade association, not evidence for an invented g.
* An attachment exactly at v_f is a boundary unresolved between an interior
  resolution and a sister-on-stem resolution: J_f in [0,1]. Do not arbitrarily
  split its mass in half. A node strictly below v_f is inside regardless of a
  polytomy wholly internal to the crown.

An unrooted topology, missing intended tips, ambiguous query/reference copy,
uncertain tip identity, unresolved relevant polytomy or uncertain boundary is
evaluated over the compatible rooted completions. Set J_L=min J and J_U=max J
over those completions. A common inside result is [1,1], a common outside result
is [0,0], and an unresolved result is [0,1]. A fully resolved nonmonophyly is
different from an unresolved node that can resolve into C_f. Never drop missing
members from C_f or replace them with the tips that happened to be returned.

For a fixed backbone with edge-placement weights, each row specifies an exact
edge, its distal position, the query pendant length, and native weight. Graft q
at that position to obtain the tree needed for distances, contrasts and history.
Validate `0 <= distal <= edge_length`; an equality maps to the corresponding
node and receives the node rule above. An unknown position on an ordinary
edge does not necessarily obscure membership, but can obscure distance.

Let z index the supplied complete native samples/placements, with normalized
weights w_z. The raw crown diagnostic is:

    L_f = sum_z w_z J_f,z.

For a bootstrap tree ensemble w=1/R is resampling weight. A posterior ensemble
retains its documented sampling weights and diagnostics. A normalized
likelihood-placement weight is a model-conditional relative placement weight;
it is not relabeled as a posterior or a function probability. Do not combine
these ensemble types as interchangeable repetitions. A single point tree uses
w=1 and reports `point_tree; ensemble_uncertainty_unavailable`.

If topology and placement weights form a documented conditional sampling model,
use its joint weight `w_tree * w_placement_given_tree`; otherwise do not invent
that product. The same rule applies to joint history/event samples. A clade's
printed branch-support label alone does not provide the joint distribution of
interior placement, stem placement, O and H. Preserve it as its exact native
split diagnostic; do not multiply several labels or substitute a nearest-sister
label for L_f.

If received placement mass is .85 of a documented unit-total distribution,
retain .15 as unknown mass. Do not renormalize .85 to one. If a source reports
weights normalized only over a retained subset and supplies no total omitted
mass, those weights give a result conditional on that subset; the full-scope
result has an unidentified missing-mass operand. The sheet defines its bounds
using possible total missing mass rather than asserting complete support.

## 4. Existing operands and the new regional equation

All O, P and history meanings below are the current proposal002 meanings:

    d_qf = minimum patristic distance from q to a reference in R_f
    s_f = median, over R_f, of distance to its nearest OTHER R_f member
    O_f = min(1, s_f/d_qf), with O_f=1 when d_qf=0 and s_f>0
    P_fg = (n_f - n_g)/(|R_f|*|R_g|)
    H = (n_vertical + sum_k d_k E_k)/N_hist

Lengths are consistent substitutions/site, and all fixed triplet denominators
retain unresolved or missing slots. For P, each resolved rooted q/r_f/r_g
triplet favors f, favors g, or places the references together outside q; the
last case contributes zero. An unresolved triplet contributes an interval
[-1,1] within that fixed denominator. s_f uses distinct reference identities,
not papers or repeated labels. Missing branch units/lengths, fewer than two
positive references, or zero s_f give O_f in [0,1]. A known zero product may
still be zero while its unused factor remains unknown.

History is unchanged:

    B_ka = sum_h min(sum_e d_e K_eh, r_h)
    M_ka = sum_j length_j*m_j / total_unique_cargo_length
    T_ka = weighted fraction of temporally feasible native history samples
    E_ka = T_ka * B_ka * M_ka
    E_k = max_a E_ka, including the proposal002 unknown other_routes slot

Where these factors vary jointly, calculate the product and route maximum
within each joint sample before averaging, as proposal002 requires. Preserve
its route inventories, factual scenarios, cargo scope and chronology rules.
One event explaining many history triplets is one reused event operand, not
several independent transfers. Unknown/unassigned history slots remain bounds.

For one complete native sample z, define the new profile:

    s_z = O_f,z * H_z * min({J_f,z} union {max(P_fg,z,0): g in G})
    o_z = max({0} union {max(-P_fg,z,0)*O_g,z: g in G})
    A+ = sum_z w_z*s_z
    A- = sum_z w_z*o_z
    Z_region = A+ - A-

For G empty this is exactly `s_z=J_f,z*O_f,z*H_z` and `o_z=0`.
The zero is the identity of the maximum over **received opposing contributions**,
not a finding that competing functions do not exist. `opposition_scope` must
say `received_included_comparisons`; `unexamined_alternatives` remains
`not_assessed`, not `excluded`. A never-included alternative adds no synthetic
negative experiment and no artificial unknown comparison.

For a genuinely included comparison with missing reference identities or tree
operands, keep its P/O intervals in the min/max. It can reduce identified
support and broaden opposition. A known eligible contrary record cannot be
deleted from G simply because it lowers the result. Revised scopes/received
evidence recalculate the persistent candidate; previous scores are not added.

When G is nonempty, the new support equals the smaller of the positive-clade
term and the existing contrast-only support, within the same sample. The
existing opposing term is unchanged. This cap is an explicit proposal: both
inside-crown placement and each included discrimination must support the stated
positive inference. It prevents a heterogeneous clade's name from overruling
its characterized internal alternatives. It also makes a stem placement differ
from an interior placement even if both favor f over a distant g.

As in proposal002, H discounts positive support but not observed contrary
placement. Thus changing candidate orientation need not negate Z. It is a
compatibility coordinate, not a symmetric probability model. There is no
additional branch-support multiplier, evidence-count multiplier, or new HGT
score. All complete factors are evaluated together before the native average.

## 5. Whole-candidate contribution, unchanged reduction

Use proposal002's source-grounded requirement map: distinct A104-relevant
inferences i, necessary homologous regions r, and distinct valid comparable
analysis scenarios j. Deduplicate aliases, redundant claims and repeated
representations; separate incompatible factual or requirement-map scenarios.

    S_r = min_j A+_rj                 O_r = max_j A-_rj
    S_i = min_(r required by i) S_r  O_i = max_(r required by i) O_r
    S_C = min_i S_i                  O_C = max_i O_i
    Z_C = S_C - O_C
    c_A104(C) = max(0, Z_C)

S_C, O_C and Z_C accompany c. This supplies the explicit proposed [0,1]
annotation contribution without altering the cross-axis formula or wiring.
Scopes and current-candidate identities have the exact meanings in proposal002.
Missing required regions/scenarios stay included; empty/unknown requirement
maps return missing-scope bounds, not one. Independent studies and alternative
models do not add votes; the retained conservative min/max is a pooling choice.

Native joint samples and shared source identities are retained. For bounds,
propagate interval min/max/products and use `[S_L-O_U,S_U-O_L]` for Z; apply
positive-part to its endpoints for c. These bounds are conservative when
dependencies constrain which extrema can coexist. Enumerating known joint
completions may tighten them. Missingness bounds and resampling/posterior
spread remain separately named.

## 6. Complete synthetic tree contrast, with and without g

All values in sections 6–8 are invented arithmetic fixtures, not paper data or
results for the project's target. The independent organism tree is stipulated
as U=topology(T_out); this is not inferred from the gene tree in a real analysis.
All leaves represent distinct mapped species/copies. Fixed C_f={f1,f2} and
R_f={f1,f2}; x1/x2 initially have no characterized function.

```text
T_in  = (((q:.6,f1:.2):.1,f2:.3):.2,(x1:.2,x2:.2):.2);
T_out = ((f1:.2,f2:.2):.2,((q:.6,x1:.2):.1,x2:.1):.2);
U     = topology(T_out)
```

Use the current proposal002's completely specified synthetic event operands:
d=(.8,.2,0), r=(0,.75,.25); K_marine,int=.75,
K_marine,coastal=.125, K_int,int=1, other cells zero. Thus routed d=(0,.8,.1)
and B=.85. Cargo has 600/1000 bp at membership 1, 200/1000 at the explicitly
synthetic judgment .5, and 200/1000 at 0: M=.7. Nine of ten compatible
chronology samples with invariant B/M give T=.9. A closed one-route fixture
universe gives E=.9*.85*.7=.5355. Real route searches do not establish closure.

| Derived cell | T_in | T_out |
| --- | ---: | ---: |
| Query-pruned C_f displayed | yes | yes |
| J_f | 1 | 0 |
| s_f / d_qf | .6 / .8 | .4 / 1.3 |
| O_f | .75 | 4/13 |
| History concordant / discordant / total | 0 / 6 / 6 | 6 / 0 / 6 |
| H | .5355 | 1 |
| No-comparator s / o | .401625 / 0 | 0 / 0 |
| Native synthetic tree weight | .8 | .2 |

Therefore **L_f=.8, A+=.3213, A-=0, Z=.3213, c=.3213** for a one-region,
one-inference candidate. The .2 outside mass is not contrary functional
evidence. The contrast-only profile remains unidentified because G is empty.

Now receive actual incompatible characterizations for the same x1/x2 tips,
and include g with R_g={x1,x2}. The geometry and histories do not change:
P_in=+1, P_out=-1, O_g,out=.5. The new profile gives
**A+=.3213, A-=.1, Z=.2213, c=.2213**. This agrees with proposal002's R1
contrast result because J adds no further restriction in these two trees.
The only changed scientific input is the newly received functional contrast.

For the full three-region candidate from proposal002, use the same geometry
with R1 weights .8/.2 and E=.5355, R2 weights .9/.1 and E=.6, and R3 weights
.6/.4 and E=1. I1 requires R1 and R2; I2 requires R3.

| Received characterization scope | Regional A+ (R1,R2,R3) | Regional A- | S_C | O_C | c_A104 |
| --- | --- | --- | ---: | ---: | ---: |
| No included g | .3213, .405, .45 | 0, 0, 0 | .3213 | 0 | **.3213** |
| x1/x2 characterized as incompatible g in each region | .3213, .405, .45 | .1, .05, .2 | .3213 | .2 | **.1213** |

Thus the accepted current arithmetic is preserved where its comparison exists,
and the positive-placement question has a complete numerical route where it
does not. Adding aliases, repeated papers or an irrelevant longer tail changes
neither row.

## 7. Weighted edge placement, stems and heterogeneous clades

Use this fixed, query-free synthetic backbone:

```text
((f1:.3,f2:.3)C:.2,(x1:.2,x2:.2)X:.2)root;
```

C_f={f1,f2}. Four received normalized edge weights sum to one. Distal is
distance from the edge's child to the attachment. Let the independent U be
the topology from the f1 graft. For each other sample, its discordant triplets
are assigned once to its stipulated route with B=1, M=.6, T=1, E=.6.

| Edge / distal / pendant | w | J_f | O_f | Concordant/discordant | H | w*s, G empty |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| f1 / .2 / .6 | .6 | 1 | .75 | 6/0 | 1 | .45 |
| f2 / .2 / .3 | .2 | 1 | 1 | 5/1 | 14/15 | 14/75=.1866667 |
| stem entering C / .1 / .3 | .1 | 0 | 6/7 | 5/1 | 14/15 | 0 |
| x1 / .1 / .6 | .1 | 0 | 3/7 | 0/6 | .6 | 0 |

Here L_f=.8; stem mass=.1; other outside mass=.1; **A+=191/300=.6366667**.
No g gives A-=0 and c=191/300. If x1/x2 are characterized incompatible g,
the x1 graft has O_g=4/7, adding opposition 2/35. The final new-profile
coordinate is **1217/2100=.5795238**. The unchanged contrast-only profile
also counts the stem's .08 support and gives 277/420=.6595238. This numerical
difference is intentional: being closer to f than g does not establish being
inside the declared f crown.

For actual internal functional heterogeneity, use:

```text
((((q:.2,g1:.2):.1,g2:.3):.1,(f1:.2,f2:.2):.2):.2,
 (x1:.2,x2:.2):.2);
```

Declare C_f={f1,f2,g1,g2}, R_f={f1,f2}, with x outside. In a stipulated
concordant independent organism history, J_f=1, O_f=.5, H=1. If g1/g2 are
uncharacterized, the association contribution is .5, explicitly conditional
on that sparse functional sampling. If they are actual incompatible g
references, P=-1 and O_g=1; support=0, opposition=1, signed=-1 and c=0.
The broad clade's name cannot make this opposite placement support f.

## 8. Missing operands, boundaries and dependence: checked examples

| Changed input / case | Numerical result and meaning |
| --- | --- |
| No g was ever included | No received opposing term; complete no-g example c=.3213. This does not establish global absence of alternatives. |
| A specific g comparison was included but its reference/placement record is unavailable | Keep unknown P/O; in section 6 the known J=0 trees cap support at zero, while the other .8 mass allows support up to .3213. A conservative region result is S in [0,.3213], O in [0,1], Z in [-1,.3213], c in [0,.3213]. No known zero is substituted. |
| Only f1 is characterized, while C_f still has f1/f2 | J and raw L_f=.8 remain known. s_f and O_f are missing; R1 S in [0,.4284], O=0, c in [0,.4284]. Whole three-region no-g c in [0,.405]. This is missing within-function normalization, not a compulsory alternative search. |
| Positive reference aliases f1,f1_alias,f2 | Collapse identity aliases before defining R_f; O_f and the coordinate remain unchanged. Two distinct zero-distance references do not fix s_f=0. |
| Branch lengths or units unavailable | J may remain known; O is [0,1]. Preserve the same support bounds where only O is missing. Figure pixels and percent identity do not fill branch lengths. |
| An intended C_f leaf or its identity is missing | C_f is not shrunk. J bounds [0,1] unless further constraints establish membership. If its length scale is also missing, the broad support bound is [0,1] per affected sample. |
| `(((q:.6,f1:.2):.1,f2:.3,u:.3):.2,(x1:.2,x2:.2):.2)`; C_f={f1,f2} | The three rooted binary resolutions give both J=0 and J=1: [0,1]. With C_f={f1,f2,u}, all give J=1; an internal polytomy does not necessarily obscure the outer boundary. |
| q attached exactly at crown C, giving `(q,f1,f2)` there | Compatible resolutions include an interior graft and a sister-to-crown graft: J in [0,1], not .5. |
| Resolved backbone `((f1,u),(f2,x))`, C_f={f1,f2} | C_f is not a clade in that complete tree; J=0. It supplies no positive clade contribution and no invented contrary function. |
| Returned weight .7 inside, .15 outside, missing .15; known O=.75,H=.8 throughout | S in [.42,.51], not .42/.85=.494118. Missing mass contributes between zero and .15*.75*.8. |
| Two equally weighted samples: (J,O,H)=(1,1,.2) and (0,.5,1) | Correct A+=.1. Product of the three means is .225 and is wrong. |
| Same event/environment/cargo observation reused across regions or tree triplets | One shared operand is varied once in compatible completions, not independently resampled for each appearance; candidate extrema follow proposal002. |

Repeated topology values in genuine bootstrap draws retain their original
multiplicity; duplicate exported rows of the same draw do not create a new draw.
Repeated source representations are one evidence block. Missing draw identities
leave multiplicity uncertain rather than automatically deduplicating equal trees.
Different alignments, methods, roots or taxon subsets are declared analysis
scenarios; the candidate reduction is not a sum of their support values.

The existing reference-spacing scale remains a proposed normalization, sensitive
to which distinct positive references were characterized. Near-identical
biological references can reduce s_f; distant references can increase it.
Reference pruning/resampling and root/model sensitivity are reported scenarios,
not new independent evidence or favorable-score selection.

## 9. Source trace, finite choices and criterion assessment

| Existing source trace actually read here | Source-derived coverage inherited from it | Use and limit in this proposal |
| --- | --- | --- |
| Complete `a104_phylogeny_sheet_012/A104_NUMERICAL_SHEET_DRAFT_001.md`, sections 4 and 7 | Its worker reports Hehemann 2010 Fig.3/Methods: Bp1689 P=+1 and Bp1670 P=-1 for PorA/PorB versus AgaA/AgaB; native split labels 99/100 and 55/100; PorE uncharacterized. | Demonstrates distinct opposite reference placements and why a nearest-sister label cannot certify function. This worker did not newly read that paper or reconstruct its branch lengths/crown ensemble. |
| Same complete sheet | Its worker reports no usable native phylogenetic inputs in inspected Hehemann 2012 main article and Leduc 2007 ThyX article; 2012 supplement uninspected. | Missing tree data stay missing. Nonorthologous replacement is not a common-tree placement. No newly filled empirical clade endpoint is claimed. |
| Complete `a104_history_completion_020/A104_HISTORY_AND_CANDIDATE_PROPOSAL_002.md`, sections 6 and 8 | Its worker reports Smillie 2011 enrichment 25 and inverse diagnostic .04, 23% missing quartet comparators, >99% support among those analyzed; Hehemann context and cohort numbers. | These aggregate/context quantities are not substituted for this target's J, weights, O or H. The existing B/M/T definitions and reference-source meanings are retained. |
| Complete `a104_sheet_construction_001/A104_FORMULA_REVIEW_001.md` | Parent's cross-case mathematical review, not independent primary extraction. | Identifies the comparator scope gap and preserves asymmetric history and normalization limitations. |
| User's recovered A104 direction and current numerical-sheet goal | Positive placement inside characterized clades, organism history, outliers/HGT explanation; measurable cells and explicit combination. | Defines the endpoint that discrimination alone did not cover. |

The proposed choices are fully specified: fixed source-grounded query-free crown;
strict stem exclusion with unresolved boundary nodes; normalized native sample
weight; retained within-positive-reference distance ratio; conjunction with
history; minimum with each included contrast; zero identity for an empty set
of received opposing contributions; and the unchanged whole-candidate min/max
and positive-part reducer. No guessed purity coefficient or calibration constant
is needed. These choices are open to judgment, not missing formula operands.

Against the bounded task criteria: the scientific endpoint, all equations,
normalizations, uncertainty/missingness, complete synthetic contrasts, dependency
handling, source-coverage attribution, exact proposed reader fields and bounded
arithmetic are supplied. Existing published contrasting cells are retained with
their actual data gaps; no fully populated empirical no-comparator score is
invented. The new reader/calculator bindings remain unimplemented, and nothing
has been calibrated or adopted. Those are implementation/validation status,
not extra undefined mathematical completion criteria. This worker makes no
goal/axis completion declaration and does not alter the ten-axis checklist.
