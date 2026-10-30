# Current A104 proposal: organismal-history agreement and an only-function clade

Goal: turn the user's now-explicit A104 meaning into two measurable components
and a fully stated numerical contribution, without requiring an incompatible
functional reference group. The bounded criteria are defined measurements,
fixed denominators, explicit function/mapping/scope uncertainty, native sample
dependence, checked contrasting examples, and exact future-reader fields.
User approval of this transform, calibration and production implementation
are separate from whether its mathematics is defined.

This is the **current proposal in this folder**. It supersedes the scientific
endpoint in `A104_POSITIVE_CLADE_PROPOSAL_001.md` and its companion interface
file, which remain unchanged as historical proposals. Their arithmetic remains
an account of those earlier formulas, not the current definition of A104.
The current proposal was sent to the parent for the user's running feedback.
It is not an accepted transform or an axis/goal completion declaration.

## Current user definition, preserved verbatim once

> A104 works if the phylogeny of the proposed protein family matches the reference evolutionary tree and if it sits within a clade of only that function

> So if you have a protein that has conserved function across a lineage, then it's evolution should match the lineage. Does that make sense? In which case you are comparing to the organismal tree.

> Note that this does not work with genes that horizontally gene transfer a lot, let's say viral proteins or mobile genetic elements. If they work at all there, they work only with very very local trees with very near relationships.

These define two conditions together and restrict the scope in which they are
meaningful. They do not approve a particular normalization, product, distance
cutoff, transfer-frequency threshold, or stopping rule.

## 1. What the proposed number measures

Within a declared, scientifically meaningful lineage scope, measure:

1. Agreement of the protein family's phylogenetic relationships with the
   corresponding **organismal** relationships.
2. The target's placement inside a source-grounded reference clade whose
   members are established to have only the proposed function at the stated
   functional resolution.

The proposal multiplies these conditions within each native tree sample and
then takes that ensemble's weighted average. Its result is a bounded A104
compatibility contribution, not a probability that the target has the function.
The calculation has no positive-versus-negative classification profile, no
mandatory incompatible reference group, and no such profile used as a cap.

The prior query-distance ratio O, signed functional contrast P, opposing-score
term, and E=T*B*M rescue of discordance are **not factors in this current
coordinate**. Actual HGT explanations remain useful background. They cannot
turn a discordant split into organismal-tree agreement. Patristic distances and
transfer evidence can inform the declared locality/scope, retaining their
native values, without becoming invented cutoff rules or extra multipliers.

## 2. Applicability and scope are explicit, nonnumerical inputs

Use one of these typed states with its source basis:

| State | Meaning and numerical output |
| --- | --- |
| `applicable_lineage_scope` | The stated family/lineage comparison is meaningful for the user's conserved-lineage question. Calculate both components. |
| `applicable_very_local_scope` | For a frequently transferred family, the stated comparison is supported as meaningful within very local, very near relationships. Calculate only within those actual supplied taxa/relationships. |
| `not_applicable` | A broad organismal-tree comparison is inappropriate for this frequently transferred family, or no meaningful local comparison is part of the stated scope. Return `coordinate=null`, with no numerical zero, opposition or penalty. |
| `applicability_unknown` | The transfer regime or scientific meaning of the selected local comparison is unresolved. Return no unconditional point; retain the conditional component calculations/bounds and explicit missing scope evidence. |

Inputs include the selected taxa/lineage, gene and organism identities,
transfer-history evidence and its scope, native measures of relatedness if
available, and the scientific basis for treating this scope as appropriate.
The user supplied no universal numerical definition of “a lot,” “very local,”
or “very near.” This proposal invents none. A reader preserves source-backed
scope statements and constraints; an unresolved determination remains unknown.
These are meanings of the score, not runtime permission gates or instructions
to run another job.

A smaller taxon subset must be an explicitly declared local scientific scope,
not chosen by maximizing concordance after viewing the scores. Broad and local
results cannot be treated as repeated evidence for the same claim. A broad
inapplicable calculation is not silently replaced by a favorable local one.

## 3. Component F: family-tree agreement with the organismal tree

Define a fixed comparable taxon/copy manifest of m members, including the
query's organism where its identity/mapping is known. The gene region must be
homologous across that family scope. A source-supported gene-to-organism and
copy mapping supplies the actual comparison; one cannot arbitrarily choose
one of several paralogs to improve agreement. Unresolved duplication/copy
mapping remains a set of possible mappings or a missing operand.

Use the organismal tree from information independent of the focal family sites.
Taxonomic names alone are not a constructed organismal topology. The primary
proposal here uses rooted trees and every unordered three-taxon subset of the
fixed manifest, so:

    N = choose(m,3), m >= 3
    n_match + n_discordant + n_unresolved = N
    F = n_match/N                       when n_unresolved=0
    F in [n_match/N, (n_match+n_unresolved)/N] otherwise

A triplet matches when its resolved rooted grouping is identical in the family
and organismal trees under the supplied taxon/copy mapping. Resolved disagreement
contributes zero to the numerator. Unknown taxa, missing tips, unresolved roots,
polytomies or ambiguous copies retain their fixed slots in the denominator.
If constraints allow only matching or only disagreeing resolutions for a slot,
that slot can be resolved accordingly. Enumerating compatible full completions
can tighten the simple bound without assuming independent triplets.

These are **all family-scope triplets**, not only query-anchored triplets and
not pairs of function labels. Their equal weighting is a proposed normalization:
F is the fraction of comparable rooted evolutionary relationships that agree.
The triplets share branches; N is not an independent biological sample count.
If m<3 or no mapped rooted comparison is established, F is unknown [0,1],
unless the entire scientific scope is not applicable. Do not divide by zero,
invent an organismal tree, discard missing taxa, or force a root from the gene
tree's preferred topology.

Root uncertainty is propagated over the allowed rootings. An unrooted quartet
version is not silently substituted in this proposal. A future such version
would state its own endpoint and denominator; none is needed to execute the
defined rooted version when its operands are supplied.

## 4. Component K: inside a clade of only the stated function

Declare a source-grounded query-free crown C before evaluating the query's
placement. Use an explicit, fixed inventory of its reference members and its
boundary on the intended backbone. It has at least two members and a defined
external boundary. This is the characterized lineage/function scope, not a
query-dependent `MRCA(q, references)` or a boundary selected to omit a known
different-function member. A bare single reference is missing crown-definition
information; it does not acquire a clade by naming its terminal branch.

Prune q from each gene-tree sample, preserving the root and summed branch
lengths when unary nodes are suppressed. Keep its graft location. Define J=1
for an attachment strictly inside C's crown and J=0 for its entering stem,
outside, or a resolved complete tree in which C is not monophyletic. A missing
member, unresolved identity or relevant unresolved boundary gives bounds over
compatible completions. Exact crown-node attachment is [0,1] between an
interior resolution and sister-on-stem resolution; an internal polytomy wholly
below a fixed crown can still have J=1. These are explicit geometric conventions
proposed here, not definitions supplied by the user.

Next assign each **reference member** of C an evidence-backed function state
at the same declared resolution:

* `only_f_established`: its resolved function set for this scope is {f}.
* `non_only_f_established`: its resolved set contains a distinct function class,
  including a multifunctional set {f,g} at this resolution, or establishes a
  different function without f.
* `function_scope_unresolved`: uncharacterized, uncertain identity, unresolved
  functional assignment, conflicting source information, or only a partial
  observed function set that cannot establish the scoped only-f assignment.

Collapse synonymous/entailed names before defining distinct function classes.
Binding and catalysis described at different levels are not automatically two
incompatible classes. The explicit functional scope determines which stated
functions are alternatives for the user's only-function condition.

Positive activity alone need not establish the complete scoped function set.
The evidence underlying `only_f_established` must actually justify that scoped
assignment; no absence-of-search argument supplies it. This is a finite
reference-classification statement under the source's supported resolution,
not a claim to rule out every conceivable biochemical activity. If that meaning
is unavailable or too broad for the evidence, the member remains unresolved.
The exact interpretation of such source assignments is a scientific input
exposed for feedback, not an invented numerical confidence.

Let n_f, n_other and n_unknown count these unique reference members, with
n_f+n_other+n_unknown=|C|. The proposed numerical only-function operand is the
universal predicate U_C:

    U_C = 1       if n_f=|C| and n_other=n_unknown=0
    U_C = 0       if n_other>0
    U_C in [0,1]  otherwise

It is a measured/constraint-derived truth indicator for the stated condition,
not an ordinal grade. The component is:

    K_z = J_z * U_C,z

Counts remain visible, but `n_f/|C|` is not substituted for “only”: a clade
containing a known different function does not partially satisfy that literal
condition because it contains many other f references. Unknown members are
neither matches nor established different functions. Duplicate records add no
members. Multifunctionality across the stated classes violates only-f for this
fixed clade; changing to a broader function or different clade is a scope
revision, not silent removal of contrary data.

The query is the target of inference and is excluded from the reference
characterization predicate; requiring its function to be established first
would be circular. This must be printed with the result. Likewise the condition
applies to the declared reference-clade inventory, not to unseen organisms in
the entire biosphere. Missing intended members stay unknown; never-sampled
organisms are a limit on generalizing that inventory, not verified matches.

## 5. Numerical combination and native uncertainty

For one actual gene-tree/placement sample z and compatible organism-tree,
mapping and function-state scenario, propose:

    a_z = F_z * K_z = F_z * J_z * U_C,z
    A_region = sum_z w_z*a_z, where sum_z w_z=1

All values are in [0,1]. The product expresses the user's two conditions
together. It is a proposal, not an independence claim. F and J can share the
same tree sites and branches; they must be calculated within the same sample
before averaging. A shared unresolved reference function assignment is varied
once across its dependent samples/regions, not independently to improve a bound.

Use actual bootstrap weights, documented posterior weights, or native weighted
edge placements with their original meanings. Graft edge placements into their
backbone to calculate F and J together. Never relabel likelihood-placement
weights or bootstrap frequencies as probabilities of function. Printed branch
labels do not reconstruct the needed joint F/J distribution.

If the organismal tree also has uncertainty, use an actually documented joint
sampling model or separate organism-tree scenarios and their envelope. Do not
pair arbitrary replicate indices or multiply independent marginal means.
Missing native mass stays unknown mass; it is not renormalized away. With
unidentified factors, report numerical identification bounds and null points;
these differ from bootstrap spread or posterior uncertainty.

A point tree yields a point-tree result with ensemble uncertainty unavailable.
For a full equally weighted ensemble, preserve its sample distribution and the
earlier explicitly defined empirical quantiles. No amount of sampling creates
new biological replication.

## 6. Complete small synthetic example

All trees, function assignments and weights here are invented fixtures. The
four gene tips map one-to-one to the four organisms q,a,b,c. The independently
supplied organismal topology is U. C={a,b}; c is an outside homolog whose
function need not be known. a and b are stipulated only-f references.

```text
Gene T_in   = (((q,a),b),c)
Gene T_stem = ((q,(a,b)),c)
Organism U  = (((q,b),a),c)
```

| Fixed taxon triplet | T_in grouping | T_stem grouping | U grouping | Match in each gene tree? |
| --- | --- | --- | --- | --- |
| q,a,b | qa|b | ab|q | qb|a | no |
| q,a,c | qa|c | qa|c | qa|c | yes |
| q,b,c | qb|c | qb|c | qb|c | yes |
| a,b,c | ab|c | ab|c | ab|c | yes |

Thus both gene samples have F=3/4. T_in has J=1; T_stem has J=0. Under
native-style synthetic weights .8 and .2, U_C=1 and:

    mean(F)=.75; mean(K)=.8
    A_region = .8*(.75*1*1) + .2*(.75*0*1) = .60

This does not use an incompatible characterized reference, a distance-normalizer,
or an HGT explanation. The same example is changed one input at a time:

| Change | Exact current-proposal result |
| --- | --- |
| b is uncharacterized/its scoped function set is unresolved | U_C in [0,1]; A in [0,.60], no midpoint. |
| b is established to have a distinct function, or {f,g} at this scope | U_C=0; A=0 for this fixed clade; counts preserve the reason. |
| Two of four organismal comparisons agree, one disagrees, and one is unresolved | F in [.5,.75]; with the same .8 interior mass and shared uncertainty, A in [.40,.60]. |
| Entire meaningful organismal comparison unavailable | F in [0,1]; A in [0,.8] when placement/only-f are known. |
| Unknown placement between T_in and T_stem | F=.75; J in [0,1]; A in [0,.75], unless native placement weights constrain it. |
| A broad viral/mobile-family comparison is not applicable | A=null, status=not_applicable; none of the values above becomes an axis penalty. |
| The same family has a justified very local, very near lineage scope with these actual inputs | A=.60 for that declared local scope only; no extrapolation to its broad family. |

The partial organismal-comparison row is an interval illustration for supplied
comparison constraints. Its feasible full-tree completions must be retained
when available; the bound is not a claim that arbitrary per-triplet states can
always coexist. The checker also uses a concrete unresolved organism topology
and enumerates its small rooted refinements.

A separate dependence fixture has equally weighted (F,J,U)=(1,0,1) and
(.5,1,1). Its correct contribution is .25, while mean(F)*mean(J)=.375.
This demonstrates why averaging native components separately is wrong.

## 7. Candidate contribution and partial applicability

For the existing persistent candidate, retain a source-grounded map of distinct
A104-relevant inferences and their necessary homologous regions. Aliases and
entailed restatements are one requirement. For the current proposal, let
`I_app` be the declared applicable requirements and j the distinct comparable
analysis/organismal/mapping scenarios for each. Propose:

    A_r = min_j A_region,rj
    A_i = min_(necessary applicable regions r) A_r
    c_A104,covered = min_(i in I_app) A_i

The retained conservative minimum means all evaluated necessary applicable
conditions constrain the common support. There is no subtractive opposing
functional-classification term in this current coordinate. A conflicting
applicable tree changes the measured concordance or clade condition itself.

`coverage` must separately list applicable, not-applicable and
applicability-unknown requirements. A declared not-applicable requirement is
outside this axis's scope and never enters as zero. If all requirements are
not applicable, the coordinate is null/not_applicable, not zero or one.
If some are not applicable, the numerical coordinate pertains to the printed
covered subset and cannot be reported as evidence for the excluded assertion.

An applicability-unknown necessary requirement is not silently removed to
improve a coordinate. Return `candidate_status=scope_unresolved`, an optional
covered-subset diagnostic, and no unconditional whole-candidate point. Its
conditional bound treats an applicable-but-missing required score as [0,1];
with known covered minimum s, the conservative conditional bound is [0,s].
If it is later established not applicable, the existing covered value remains
the axis's partial-scope contribution. W05's handling of a null/inapplicable
axis among other axes is separate from defining this A104 measurement.

Example: two applicable necessary regions .60 and .45 give c=.45. Adding a
duplicate .60 representation leaves .45. A third inapplicable broad-HGT region
does not insert zero: output .45 with explicit partial coverage. If the third
region's applicability is unknown, the unconditional candidate point is null
and the conditional bound is [0,.45]. These are explicit scope distinctions,
not artificial approval or continuation rules.

## 8. Exact fields for future readers — unimplemented

All numerical cells carry value/null, bounds, units, source operands, shared
measurement identities and separate statistical-uncertainty metadata. No
investigation prompt or new production reader is created by this definition.

| Targeted function | Exact principal inputs | Numerical/scoped outputs |
| --- | --- | --- |
| `read_A104_lineage_applicability` | family/region; selected taxon and lineage scope; transfer-regime source evidence; actual relatedness measurements with units; source-backed local-scope basis; unresolved alternatives | applicability state above; precise assessed/excluded scope; basis and missing fields; no numeric grade or invented cutoff |
| `read_family_organism_mapping` | family gene tips; actual organism identities; region homology; gene-copy relationships; independent organismal-tree identity; fixed intended comparable taxa; root constraints | fixed mapping/possible mappings; m; N=choose(m,3); exact triplet manifest; unresolved/missing identities; no dropped denominators |
| `calculate_family_concordance` | one gene sample and compatible organism sample/scenario; fixed manifest and mapping/root constraints | per-triplet gene/organism grouping and match/disagree/unresolved state; n_match,n_discordant,n_unresolved; F or bounds; original sample keys |
| `read_only_function_clade` | source-grounded query-free C and external boundary; all intended member identities; characterized function sets, resolution, assay/assignment scope, completeness/limits and source conflicts; alias/entailment mapping | member state only-f/non-only-f/unresolved; n_f,n_other,n_unknown; U_C or bounds; exact functional scope; query excluded as inferential target; no assumed functions for unknown members |
| `calculate_target_crown_placement` | native gene tree or weighted backbone edge/graft; q identity; fixed C/boundary/root; intended missing members | preserved query-pruned backbone and graft; J or bounds; interior/stem/outside/unresolved class; native mass and missing mass |
| `compile_A104_two_conditions` | matched F,J,U_C for each native sample; weights and normalization meaning; shared dependency constraints; applicability | K=J*U_C; a=F*K; A_region; missingness bounds; sample distribution; native uncertainty kind; null/not_applicable or scope-unresolved when required |
| `compile_A104_covered_candidate` | persistent candidate; distinct inference/necessary-region map; comparable scenario identities; A_region values/bounds; applicability states | per-region/inference minima; c_A104,covered; coverage lists; unconditional status; conditional bounds; unknown operands and dependencies |

Future reader code must validate meaning while preserving valid partial data.
No model is needed to recompute counts, predicates, products or weighted means.
Where lineage applicability, function scope or identity remains interpretive,
its source-backed constraints are explicit rather than compressed into one
numeric confidence.

## 9. Source coverage, remaining choices and criterion assessment

No new paper or retained paper-specific packet was opened. The complete
earlier numerical sheets were read, including their source traces and examples;
their original primary-source coverage belongs to their authors. They report
contrasting Hehemann 2010 placements and native split-support labels, with
missing complete branch/tree/organismal operands. Those inherited examples
do not supply a new fully populated F/K score under this latest definition.
The older Smillie/ecology and HGT-route operands are not substituted for F.

The current proposal's mathematical choices are explicit: all fixed rooted
family triplets with equal normalization, a query-free fixed crown, the
only-function universal predicate at a declared resolution, a within-sample
product followed by native averaging, and minimum over necessary applicable
scopes. These are proposed conversions of the user's definition, not formulas
attributed to the papers or accepted by the user.

The two-component plan, complete synthetic results, exact missingness rules,
function/identity/scope dependencies and future-reader fields are specified.
The meanings of source-backed only-function assignments and meaningful very
local HGT scopes require actual evidence and remain exposed for feedback; no
numerical cutoff is missing from an equation that secretly requires one.
There is no fully populated empirical example of this new definition in this
worker's inspected material. Existing published source contrasts remain
inherited, not newly verified under this current endpoint. This is a real
coverage limit, not an excuse to invent tree or characterization data.

No production code, annotation, phylogenetic job, HPC job, permanent record,
goal status or axis checklist was changed. This document does not mark A104
complete or claim that the user's feedback on the numerical choices is settled.
