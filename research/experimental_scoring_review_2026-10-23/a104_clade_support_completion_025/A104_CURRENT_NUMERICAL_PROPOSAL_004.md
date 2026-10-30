# A104 numerical proposal004: organismal history and function-conserving clade placement

Goal: provide a usable numerical A104 sheet for the user's two conditions,
including the stated HGT, functional-resolution and outlier limits. Success
here means explicit operands, denominators, arithmetic, missingness/dependence,
contrasting source-populated components, fully checked synthetic combinations,
and exact future-reader fields. It does not mean adopting a policy, implementing
a production reader, annotating the target, or declaring the axis/goal complete.

This is the current mathematical proposal in this folder. It supersedes the
endpoint/formula in `A104_POSITIVE_CLADE_PROPOSAL_001.md` and the strict
all-members-characterized treatment in `CURRENT_TWO_CONDITION_PROPOSAL_002.md`.
Those files remain unchanged. The user's exact two-condition definition,
organismal-tree clarification and HGT restriction are preserved once in
`CURRENT_TWO_CONDITION_PROPOSAL_002.md`, section “Current user definition.”
The later exact refunctionalization/outlier direction and request to find
metrics are preserved once in `CURRENT_USER_STEERING_003.md`. Both govern this
proposal. The compact metrics/plan were printed to the parent before this
expansion; the parent requested completion without another approval wait.

An additive verification correction: proposal002 said its checker enumerated
an unresolved organismal topology. No checker for proposal002 had then been
run. The earlier checker001 tested a different historical formula. The actual
current checks are `arithmetic_checks_005.py` and `arithmetic_results_005.json`.
Checker004's assertions passed but its JSON export failed on tuple keys;
checker005 is the preserved additive serialization correction and ran to exit0.

## 1. Scientific endpoint and the meaning of the output

A104 asks whether, within a meaningful lineage scope, the family follows the
organismal relationships **and** the target sits inside a function-conserving
reference clade. It does not require a group of incompatible-function proteins.
Different functional names are not automatically incompatible: functions can
coexist, names can be synonyms, and descriptions can occur at different levels.

The proposed compilable value is **observed positive phylogenetic association**:
resolved family/organismal agreement, interior placement, connection to the
characterized relatives, and the measured coverage of an observed homogeneous
functional assignment. It is in [0,1], not a probability of target function or
proof that every uncharacterized protein has that function. Its factors are
counts, native weights, geometric membership and an exposed reference-relative
distance transformation. No overall intuitive confidence grade replaces them.

Print a separate **full-clade claim** field: can all intended reference members
be assigned only this function at the declared resolution? Unknown members or
unresolved functional scope can leave that universal condition unknown even
when substantial positive association is measured. Its completion bounds can
include zero because an unknown member could reveal functional heterogeneity.
The observed value is not described as a guaranteed lower bound on a score
after every missing observation is supplied.

Known heterogeneity gives zero **precise positive** contribution for that fixed
clade. A small/zero value is not opposing evidence that the target lacks the
function. The observed function set and any justified broader common function
remain separate useful results. The previous signed classification contrast,
opposition subtraction and HGT-route rescue are not this A104 calculation.

## 2. Scope and applicability

The sheet records `applicable_lineage_scope`, `applicable_very_local_scope`,
`not_applicable` or `applicability_unknown`, with source-backed basis, exact
included lineages/copies/region and limitations. Broad organismal concordance
for a frequently transferred family is `not_applicable`, coordinate null.
A scientifically supported very local comparison may be evaluated only at
its actual very near relationships. No universal transfer-frequency or distance
cutoff is invented. An unresolved scope has conditional calculations/bounds,
not an unconditional candidate point.

This is the meaning of the measurement, not an execution or approval gate.
No compulsory HGT search is imposed. The reader preserves the basis actually
available; lack of a search is not proof of vertical inheritance. Low observed
concordance is not itself permission to relabel a difficult result inapplicable.
A favorable local subset or narrower clade cannot be chosen by maximizing the
score. Any scientifically justified scope revision is a new explicit assertion
and comparison, with the previous result retained.

## 3. Family versus organismal topology

Inputs are a homologous protein region, intended organism/copy manifest,
gene-tree sample and independently supported organismal-tree sample/scenario.
The organism tree must not merely be the focal-family tree relabeled with taxon
names. Record the actual organism/copy mapping and supporting source. Names
alone are not an organismal topology.

For a direct common-leaf comparison, a source-supported ortholog/copy scope
maps one intended gene lineage to each organism. Duplications and paralogs are
real scientific inputs. Do not arbitrarily choose the best-matching copy.
Alternative supported mappings stay scenarios, missing mappings stay missing,
and family members excluded from this direct one-copy comparison remain in
the functional inventory if they belong to its clade. No invented reconciliation
algorithm or compulsory additional job is supplied by the sheet.

Choose the comparison from the tree information: justified roots permit rooted
triplets; an explicitly justified unrooted comparison uses quartets. Do not
calculate both and select the higher score. If a rooted question was specified
but its root is uncertain, propagate the allowed roots; do not quietly switch
its endpoint. Let s=3 for triplets or s=4 for quartets, m the fixed intended
mapped-taxon slots, and N=choose(m,s). For each unordered subset, compare the
induced rooted grouping or unrooted split:

    M = number with identical resolved topology
    D = number with different resolved topology
    U = number unresolved or missing on at least one side
    M + D + U = N
    F_supported = M/N,                 N > 0
    F_completed in [M/N,(M+U)/N]

`F_supported` measures the fraction of intended evolutionary relationships
with observed resolved agreement. Print D/N and U/N alongside it, so unresolved
information is not confused with demonstrated discordance. Full compatible
tree/root/copy completions can tighten the completion bound. Per-subset states
share branches; they are not independent trials and do not justify a binomial
standard error or an effective sample size of N.

The native tqDist distance has a different unresolved convention: identical
unresolved subtrees can count as agreement, and resolved/unresolved pairs as
differences. Preserve that native result and its common-leaf denominator; do
not call `1-native_distance` the resolved-support component above. Native
common-leaf pruning also cannot silently remove intended missing taxa. If only
3 of 4 intended rooted taxa remain and their one triplet agrees, print native
agreement 1/1, comparison coverage 1/4, and F_supported=1/4 with three unknown
slots—not a complete four-taxon agreement of1.

If m<s, there is no topology evidence at that scope: native normalized topology
fraction is null (`insufficient_taxa`), and the supported-information contribution
F_supported is defined as0. This convention means no observed relationship,
not a disagreement. There is no completion of an empty within-scope comparison
that supplies a topology score; adding taxa changes the scope. Missing intended
tips in an otherwise adequate manifest instead leave U slots as above. Missing
the entire intended manifest/denominator leaves F null/bounded, not a fabricated
N. Never-included taxa remain a generalization limit, not missing experimental
observations in an invented denominator.

Use native tree/placement ensembles for support uncertainty. Branch support
labels alone do not reconstruct their joint distribution. A supplied point
tree has a conditional point-tree calculation, with ensemble uncertainty
unavailable. No universal bootstrap cutoff collapses its branches. Zero-length
edges retain the source's topology convention; no hidden epsilon or support
threshold invents a resolution.

## 4. Fixed clade, actual placement and function resolution

Declare reference crown C and its complete intended member inventory before
evaluating target placement. C contains characterized and uncharacterized
members, with canonical molecule/copy identities. Source-backed membership and
boundary are necessary; an `MRCA(query, convenient positives)` is not a fixed
reference clade. It must not omit a known differently functioning descendant
or be narrowed after observing the score. Query function is not required:
the query is excluded from the reference characterization inventory.

For a rooted tree, prune the query q and preserve its graft location, summing
adjacent branch lengths when a unary node is suppressed. An unrooted tree can
use a source-defined oriented split side C with a supplied external side;
it must not invent a root. The designated crown may be the root only if that
root/reference-universe boundary is actually supplied; it then has explicit
restricted reference coverage. Without a defined boundary, J is unknown.

For each actual tree or weighted edge placement z, define:

    J_z = 1 for attachment strictly within the fixed crown
    J_z = 0 for its entering stem, outside, or resolved nonmonophyly of C
    J_z in [0,1] when allowed completions give both outcomes

At the exact crown node, unresolved sister-on-stem versus interior resolution
is a boundary interval. An unresolved node wholly inside the crown need not
make J unknown. Missing intended tips or ambiguous identities do not shrink C
to convenient present tips. Propagate their allowed memberships. A bare one-tip
reference cannot by itself supply the missing multi-member crown boundary.

For edge placements, retain actual edge, distal attachment and pendant length,
and graft the query to compute F, J and distance on that same sample. Native
placement mass inside C is `sum(w_z*J_z)` where J is known. Stem mass, outside
mass and unresolved/missing mass are printed separately. No clade label or
branch support is used as a guessed placement probability.

For each unique reference i, record the experimentally supported function set
S_i at the **same stated resolution**, assay/assignment scope and unresolved
additional functions. Empty S_i means no resolved assignment at that resolution.
An inferred annotation or a motif is not experimental characterization.
Synonyms and entailed descriptions are normalized explicitly. A broad “ion
transporter” observation does not resolve sodium versus potassium. Binding and
catalysis need not be different alternatives. Multifunctionality within the
declared comparison dimension is kept as a set, not forced into one class.

For exact assertion f, let n be the intended unique reference count and k_f
the members with observed supported set {f}. Let B_f indicate any received
reference function class outside {f} in this fixed clade at that resolution.
The current **observed association coverage** proposal is:

    C_f = 0,             if B_f is true
    C_f = k_f/n,         otherwise, n > 0

No observed assignments gives C_f=0 available positive information, with all
members still unknown. An unknown intended inventory/denominator does not
create n; C_f then has bounds from the known count constraints. Equal weight
per unique sampled protein is an explicit proposal, sensitive to reference
sampling density. It does not count independent evolutionary or experimental
replicates. Report organism/copy composition; repeated accessions, citations,
figures and same-molecule aliases do not add members. Distinct proteins with
identical sequence remain distinct inventory members, but not new independent
phylogenetic evidence.

The observed {f} label means only f was established in the declared evidence
scope; it does not claim that all conceivable other activities were excluded.
If f itself implies selectivity or exclusivity, the assignment requires the
corresponding measured specificity, not just activity on f. Absence of a search
for other functions is never a negative assay. This preserves actual measured
association without imposing an exhaustive alternative-function experiment.

Separately define full-clade purity Q_f=1 only when the evidence/constraints
establish every intended reference's function set as {f} at that finite scope;
Q_f=0 if a received function class makes that impossible; otherwise Q_f is
unresolved [0,1]. Even C_f=1 need not make Q_f=1 when functional completeness
is unknown. Q_f is not a second numeric confidence factor used to erase C_f.
It is the explicit truth-condition qualification and completion analysis of
the user's stronger all-clade statement.

If the known clade contains f and g, exact f receives C_f=0 regardless of a
99-to-1 majority. Retain the observed set {f,g}, unresolved additions, and
source-supported shared broader description h if one exists. Computing h
requires a separate assertion with an explicit f→h/g→h mapping; it is not
choosing a favorable score for f. Never add scores for f and its entailed h
as two independent assertions, and never choose a narrower clade to hide g.
A multifunctional {f,g} member can fail “only f” without proving that f is
absent. Nondetection with limited activity/expression controls remains a scoped
negative observation, not automatically a known new function or verified loss.

## 5. Distance and outliers, separate from placement uncertainty

Use actual nonnegative patristic branch lengths on the same gene tree/model
scale. Let K be the set of experimentally characterized clade references at
this functional resolution (all known classes are retained). Define:

    d_z = min_(r in K) distance_z(q,r)
    b_z = median_(r in K) min_(t in K, t!=r) distance_z(r,t)
    O_z = min(1,b_z/d_z),                  d_z > 0 and b_z measured

For an even number of nearest-neighbor distances, median is the arithmetic
mean of the two central ordered values. Query distance includes its pendant
branch. b is computed without the query. This is our continuous attenuation,
not a native pplacer confidence or a universal biological distance cutoff.
It limits transfer of an otherwise certain placement to a distant query.
Sampling density, lineage rate differences and model uncertainty limit it;
its numeric inputs and the unattenuated F/J result remain visible.

The proposal has explicit zero and missing cases, without epsilon:

| Inputs | O and interpretation |
| --- | --- |
| d=0, b>0 | 1; the query is coincident with a characterized reference on the supplied scale. |
| b=0, d>0 | 0; the query has positive separation relative to a measured zero reference spacing. This is no positive locality credit, not contradiction. |
| b=d=0 | 1 by an explicit coincidence convention; no distance distinguishes query from those references. Topology/function uncertainty is not repaired by this convention. |
| d=0, b missing | 1 under the same coincidence convention; missing b is still recorded. |
| d>0, b missing (e.g. one usable reference) | null with bounds [0,1] unless actual constraints narrow them. No opposite-function reference is demanded. |
| d missing or relevant reference distances/identities missing | evaluate over their nonnegative allowed values; generally [0,1], with no midpoint. |
| Rounded/censored zeros or unknown common branch scale | preserve their intervals/scale uncertainty, not the exact-zero convention. |
| Negative or incompatible branch values | invalid/mismatched operand, not a zero-length branch. Preserve valid partial components. |

For posterior/likelihood placement edges, use the native pendant and attachment
quantities available. ML optimal branch lengths give a conditional ML distance.
Integrated edge posteriors alone do not supply a posterior branch-length sample;
do not invent one. Where joint branch samples are unavailable, retain the
conditional distance or its missing uncertainty explicitly.

EDPL is retained only as a diagnostic:

    EDPL = sum_i sum_j p_i*p_j*distance(attachment_i,attachment_j)/L_tree

L_tree is the supplied reference tree's total branch length. Zero L_tree gives
undefined normalized EDPL, with the unnormalized distance retained. EDPL can
be0 for one certain placement with a very long pendant branch. It is therefore
not the outlier measure, and multiplying it into the score would penalize the
same placement uncertainty twice. An absent EDPL is not an essential operand
of the score. Native likelihood weights, posterior weights and bootstrap
frequencies keep their distinct meanings.

## 6. Region and whole-candidate equations

For one applicable necessary region r and native joint draw z:

    a_r(z) = C_f,r(z) * F_supported,r(z) * J_r(z) * O_r(z)
    A_observed,r = sum_z w_z*a_r(z),        sum_z w_z = 1

All operands are evaluated on the same actual tree/graft, copy mapping and
reference-function scenario. This is an explicit product, not an independence
claim. Do not multiply separately averaged factors. Known mixed function sets
can fix a_r=0 even if an irrelevant distance operand is missing; retain the
missing field rather than claiming it was measured.

The persistent candidate has a declared set R_app of distinct necessary
applicable inference/region requirements. Aliases and entailed restatements
are one requirement. For documented joint native draws across these regions:

    a_candidate(z) = min_(r in R_app) a_r(z)
    c_observed,j = sum_z w_jz*a_candidate,j(z)
    c_A104,observed = min_(included scientifically comparable analyses j) c_observed,j

The per-draw minimum before averaging is a **new explicit pooling proposal**
in this revision. It requires the candidate's necessary conditions together
in each shared sample. It replaces proposal002's min-of-region-means, which
can combine support obtained in different mutually exclusive samples. The
per-region means remain diagnostics. Alternative analyses of the same data
are not added as independent evidence. The last minimum is a stated conservative
choice across included comparable analyses, not a claim that all methods are
equally accurate. Identical received representations are deduplicated.

If only region marginals w_r(s_r) are supplied, do not invent replicate pairing
or independence. Define admissible joint couplings pi(s_1,...,s_R)>=0 with:

    sum_(all coordinates except r) pi = w_r(s_r) for every r,s_r
    pi = 0 for combinations violating supplied shared-sample constraints
    lower/upper = min/max_pi sum_s pi(s)*min_r a_r(s_r)

This is a finite linear optimization with explicit coefficients/constraints.
It yields a bound instead of an invented joint point. A product coupling is
permitted only as a declared additional modeling assumption, not a default.
The same shared source function assignment, reference identity, branch value
or organism-tree scenario is used across every dependent region/analysis.
Contradictory sources become explicit allowed scenarios or inconsistent-input
status; they are not averaged into a fabricated function confidence.

If all requirements are inapplicable, return null/not_applicable, not min(empty)
or0. If only some are applicable, c concerns the printed covered subset.
An applicability-unknown necessary requirement leaves the unconditional point
null; its conditional applicable score remains [0,1] unless constrained.
Never-included function alternatives or taxa add no fictitious requirement.
An **included but unavailable** sample/reference/necessary comparison remains
an unknown operand with its original slot or weight.

## 7. Missingness, uncertainty and the stronger all-clade claim

Each cell prints point/null, identification bounds, native uncertainty type,
source operands and the reason for a null. These are separate from empirical
bootstrap/posterior spread. A fully supplied conditional point tree can produce
a conditional point score; it does not establish sampling precision.

Missing native mass R is not renormalized away. With known subtotal s and an
unconstrained missing contribution in [0,1], bounds are [s,s+R], narrowed by
known C/J/F constraints. If the original normalizer itself is unavailable,
only a retained-subset conditional calculation is available; its weights are
not a complete ensemble. Printed branch supports cannot reconstruct missing
joint sample weights. Repeated reports of one tree/assay are not more samples.

For allowed global completions theta, recompute topology, function sets,
membership, branch ratios and the whole candidate jointly. The full-clade
claim uses Q_f(theta), not observed C_f as purity:

    a_full,r(z;theta) = Q_f,r(theta) * F_completed,r(z;theta)
                      * J_r(z;theta) * O_r(z;theta)
    c_full(theta) = the same per-draw/candidate/analysis compilation
    full_claim_bounds = [inf_theta c_full(theta), sup_theta c_full(theta)]

Completions preserve observed negatives, source scope, native mass, whole-tree
compatibility and shared identities; they do not fill never-included alternatives.
If completing reference functions changes which characterized references enter
b/d, recompute them rather than freeze a favorable normalizer. Simple interval
arithmetic may provide outer bounds; label them as such if full compatible
completions were not enumerated. Exact bounds and outer bounds are not confidence
intervals. No default 0.5 imputes unresolved topology, identity or function.

If a full native weighted sample distribution is available, report its weighted
empirical quantile Q(p)=inf{x:sum_(z:a(z)<=x) w_z>=p}; for example p=.025,.5,.975.
Label it posterior or bootstrap spread according to its source, never a
calibrated probability of the annotation. Missing mass or unknown coupling
prevents an unconditional quantile unless its quantile bounds are calculated.

## 8. Full contrasting synthetic placement examples

All trees, weights and function labels below are invented arithmetic fixtures.
Branch lengths use one common synthetic substitutions/site scale. The same
organismal topology is independently stipulated; it is not inferred here.

```text
Query-free backbone B = ((a:0.3,b:0.3)C:0.2,c:0.5)root
Fixed crown C={a,b}; a and b characterized f; c function unknown.
Organism topology U  = (((q,a),b),c)

Placement a: (((q:0.1,a:0.2):0.1,b:0.3)C:0.2,c:0.5)
Placement b: ((a:0.3,(q:0.1,b:0.2):0.1)C:0.2,c:0.5)
Stem:        ((q:0.1,(a:0.3,b:0.3)C:0.1):0.1,c:0.5)
Outside:     ((a:0.3,b:0.3)C:0.2,(q:0.1,c:0.2):0.3)
```

For all four intended taxa, N=4 rooted triplets. The native-style weights are
.6,.2,.1,.1. They are not claimed to come from a real run.

| Placement | M,D,U | F_supported | J | b | d | O | a=C_f F J O |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| a | 4,0,0 | 1 | 1 | .6 | .3 | 1 | 1 |
| b | 3,1,0 | .75 | 1 | .6 | .3 | 1 | .75 |
| stem | 3,1,0 | .75 | 0 | .6 | .5 | 1 | 0 |
| outside c | 1,3,0 | .25 | 0 | .6 | .9 | 2/3 | 0 |

    C_f=2/2=1; interior placement mass=.8
    A_observed=.6*1 + .2*.75 + .1*0 + .1*0 = .75

No characterized contrary group was required. If c is actually characterized
as g, the result is still .75 because c is outside the fixed C; its topology
was already included. If b instead has g, or has {f,g}, C_f=0 and precise f
receives0. Neither case says that q cannot have f.

The inter-attachment distance matrix, in row order a,b,stem,outside, is:

```text
0  .2  .2  .6
.2  0  .2  .6
.2 .2   0  .4
.6 .6  .4   0
```

Total reference length is1.3. EDPL=.184/1.3=46/325=.141538. Now change only
all query pendant lengths from .1 to5.8. The interior d becomes6, O=.1, so
A_observed=.075. Attachment weights, topology and EDPL are unchanged. A
one-edge version has EDPL=0 both near and far. Thus a certain placement can
still supply little transferable information. There is no subtractive penalty.

The separate-factor product is wrong even here:
mean(F)=.85, mean(J)=.8, mean(O)=29/30, product=.657333, whereas the actual
within-draw average is .75. The shared sample is essential.

### Unknown membership/function, mixed clade and broader assertion

Use the independently stipulated matching organism/gene tree:

```text
((((q:.1,a:.1):.1,b:.2):.1,u:.3)C:.2,c:.5)
```

C={a,b,u}; n=3. Only a,b have measured function f. All10 rooted comparisons
agree, J=1, b=.4, d=.2, O=1. C_f=2/3 and observed contribution=2/3.
Full-clade purity is unknown: u=f would give full score1, while u=g would
give0. The exact completion range is[0,1]. The measured 2/3 is neither a
probability nor a claim that u has f. If u is known g, precise f is0; if
both f and g genuinely entail shared function h, the separately stated h
assertion has C_h=3/3 and contribution1. This changes the assertion, not the
score assigned to precise f. Duplicate a aliases/citations change no result.

### Boundary and data-availability checks

| Actual change to supplied information | Defined result |
| --- | --- |
| Only a is characterized in the four-tip fixture | C_f=1/2, d=.3, b missing. Observed region point null, bounds [0,.375]. A positive/negative comparator search is not an operand. |
| Organism tree lacks intended taxon c; gene tree/placement a still complete | Native common-leaf agreement1/1; fixed N=4, M=1,U=3; F_supported=.25, observed point=.25, completed range[.25,1]. |
| Fewer than3 intended rooted taxa, or fewer than4 unrooted taxa | Native topology fraction null; F_supported=0 because no topology evidence. Not a conflicting relationship. |
| Same four-topology fixture under a justified unrooted quartet question | F values1,0,0,0; observed score=.6. It is a different endpoint, not an alternative chosen because it scores better. |
| Both supplied unrooted trees are four-tip stars | Native unresolved agreement can be1; M=0,U=1, F_supported=0 and completed bound[0,1]. |
| Query attaches at unresolved crown node: ((q:.1,a:.3,b:.3)C:.2,c:.5) | J=[0,1], observed F_supported=.75; observed score outer bound[0,.75]. Three binary refinements give exact full scores1,.75,0, full bound[0,1]. |
| C is resolved nonmonophyletic | J=0 for the declared clade; no automatic redefinition. |
| Intended reference identity/tip is missing | Preserve that slot; J/membership and relevant functions/distances have bounds. |
| Branch lengths on a required query path are unmeasured | O unknown, generally[0,1]; do not read absent values as native zero. |
| Included native sample with weight .2 is unavailable; known .6 sample contributes1 and two .1 samples are known outside | Region[.6,.8], point null; no renormalization to .75 or1. |
| A received sample has known J=0 but its branch lengths are unavailable | Its contribution is exactly0; missing O is preserved but cannot affect that product. |
| No incompatible-function comparison was ever included | No missing comparator slot; the main .75 remains calculable. |
| A required additional region/comparison was included but unavailable | Candidate conditional bounds[0,.75], point null, instead of dropping it. |
| Broad frequent-HGT family scope | null/not_applicable, not zero. A meaningful very local comparison requires its own actual scope and operands. |

### Whole candidate and dependence

The main region has per-draw values(1,.75,0,0) with weights(.6,.2,.1,.1).
If a second necessary applicable region contributes .4 in every same joint
draw, candidate values are(.4,.4,0,0), so c=.32. The min of the region means
would be .4 and is not this proposal's joint calculation. Adding duplicate
requirements changes nothing. A declared inapplicable requirement is listed
outside covered scope and does not insert0; an applicability-unknown necessary
requirement prevents an unconditional point.

A second fixture has two equal-weight joint draws: required regions (1,0)
then(0,1). The candidate is0, though each region mean is.5. If only those two
marginals were supplied, the coupling has P(1,1)=P(0,0)=t, other cells=.5−t,
0<=t<=.5; candidate=t and exact bounds[0,.5]. Independence would select.25,
but is not inferred. Shared unknown function u is completed once across all
regions: with a second fixed requirement .4, full candidate outcomes are.4
if u=f and0 if u=g, not two independently chosen member assignments.

## 9. Source-populated published contrasts and actual coverage

| Inspected source | Populated current fields / derived arithmetic | What remains missing or must not be inferred |
| --- | --- | --- |
| [Sand et al.2014, tqDist](https://doi.org/10.1093/bioinformatics/btu157), complete two-page author paper | Definitions of rooted-triplet/unrooted-quartet native distances and unresolved convention; proposed M,D,U conversion above | No characterized biological functions, target placement or organismal-case score. Method definitions do not supply assay labels. |
| [Matsen et al.2010, pplacer](https://doi.org/10.1186/1471-2105-11-538), relevant methods in author manuscript | Per-edge optimized likelihood normalization, marginalized posterior placement, attachment/pendant quantities and EDPL | Weights condition on tree/model/alignment; no function probability, no actual A104 target run. Our b/d factor is not their native transform. |
| [Wege et al.2010](https://doi.org/10.1111/j.1365-313X.2010.04288.x), primary Results/Methods/Table1 | AtCLCa WT and engineered P160S have different ion preference while retaining broader anion/proton exchange. Table1 current-ratio means4.0 and.90 give derived ratio-of-ratios40/9=4.4444 under their stated comparison. | One natural reference plus its engineered variant, not two independent evolutionary tips. No natural change-rate estimate, full crown, independent organism tree, target J or branch normalizer. Neither ratio is an A104 score; both proteins transport multiple assayed anions. |
| [Stockbridge et al.2012](https://doi.org/10.1073/pnas.1210896109), primary Results/Methods/Table1 and captions | Eight natural CLC-F homologs supply observed fluoride/proton-antiport assignments among29 screened: panel coverage8/29=.275862. Exact1:1 stoichiometry is directly measured for1/8 of the successful transport panel. Family phylogeny construction and a source-defined clade are reported. | Screened panel is not the complete crown inventory. Four assay-inactive proteins and expression/purification failures are not known alternative substrate functions. No independent organism tree, complete native tree/branch sample or target placement was supplied here; full C_f, F,J,O and final coordinate remain null/qualified. |

These experimental papers give contrasting **populated components**, not
fabricated complete native A104 scores. Their molecular experiments establish
the functional labels/limits used by the phylogenetic sheet; their activity
magnitudes and rescue experiments are not added to A104 as separate credits.
The direct source notes preserve experimental arrangements, controls and
uncertainties. The three published-ratio calculations are checked in checker005.

The retained Hehemann/Smillie source trace was read only through prior complete
cross-case sheets. Its primary inspection belongs to those earlier workers.
Transfer/ecology observations are not positive vertical-concordance examples
under the user's current definition, and route overlap/cargo/chronology cannot
restore F. Their original B,M,T,E equations remain historical background,
not redesigned here. Worker029 separately owns the independent vertical-case
source; no fresh read or result from that lane is claimed in this file.

Primary source access actually used: tqDist author PDF
<https://cs.au.dk/~gerth/papers/bioinformatics14.pdf>; pplacer author manuscript
<https://matsen.fhcrc.org/pplacer/pplacer.pdf>; Wege publisher article; CLC-F
PMC then PNAS article after a PMC access challenge. No raw phylogenetic dataset,
native program or target annotation was run. Per-paper authority receipts are
`AUTHORITY_RESET_PAPER01_001.json` through `...PAPER04_001.json`. Paper04 records
the provisional-message ordering slip, withdrawal and completed reassessment;
the record does not claim perfect ordering compliance.

## 10. Criterion assessment and exposed proposals

Exact future-reader inputs/outputs are in `EXACT_READER_FIELDS_004.md`, and the
print-ready handoff is `PRINT_HANDOFF_004.md`. All readers remain unimplemented;
the synthetic fixture is not a production reader. No prompt insert or execution
behavior was changed. The sheet can be populated from actual native data or
literature where those exact operands exist, with the same null/bounds meanings.

Defined mathematical choices: equal fixed-subset topology weighting; separating
resolved support from raw native distance; strict crown-interior geometry;
unique-reference coverage C_f conditional on observed functional homogeneity;
the b/d attenuation and exact-zero conventions; within-draw products and
candidate minima; native weighted averaging; conservative included-analysis
minimum; joint-completion/coupling bounds. These are explicit proposals for
judgment, not user-approved transformations or claims from the papers.

The current formula, denominators, boundaries, dependence, contradictory/missing
data, sparse references, actual source coverage and deterministic fields are
specified and the complete synthetic arithmetic is checked. Published cases
populate function/coverage components with real limits; complete empirical
native F/J/O coordinates are not claimed for these sources. Missing biological
operands are distinct from an undefined formula. User approval, calibration,
production readers and W05 wiring are not silently added as mathematical
completion criteria. This worker does not mark A104 or the overall goal complete.
