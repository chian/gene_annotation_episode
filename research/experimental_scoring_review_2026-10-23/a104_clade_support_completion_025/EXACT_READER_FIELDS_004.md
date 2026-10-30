# Exact fields for A104 proposal004 — targeted readers unimplemented

This is the input/output contract for `A104_CURRENT_NUMERICAL_PROPOSAL_004.md`.
It is a scoring-sheet research interface, not an investigation prompt, generic
reader deployment, episode, execution requirement or production implementation.
The arithmetic checker uses finite explicit fixtures; it does not implement
these source readers. Existing proposal001/002 interfaces remain historical.

## Common numerical cell

Every numerical output has the following fields:

| Field | Type / exact meaning |
| --- | --- |
| `point` | number or null; the value actually identified by the stated data/assumptions |
| `lower`, `upper` | numbers or null; identification bounds, with `bound_kind=exact/outer/not_defined` |
| `units` | `fraction`, native branch-length unit, native distance, count or another stated unit |
| `status` | `measured`, `derived`, `conditional`, `missing_operand`, `insufficient_taxa`, `not_applicable`, `scope_unresolved`, `inconsistent_inputs` |
| `meaning` | constrained cell meaning, e.g. `observed_resolved_agreement`, `observed_association_coverage`, `full_clade_claim`, not generic confidence |
| `numerator`, `denominator` | exact counts/sums or references to their operands, nullable when genuinely absent |
| `unknown_operands` | exact included inputs whose values/identities are missing; never-included alternatives are not listed here |
| `assumptions` | declared calculation/normalization/scenario choices; no inferred approval |
| `source_locations` | article figure/table/method/native artifact locations establishing values |
| `shared_evidence_keys` | identities connecting repeated measurements/trees/mappings; not additional score components |
| `native_uncertainty` | kind, actual samples/weights or reported uncertainty; separately nullable |
| `zero_reason` | null or `no_topology_evidence`, `no_characterized_assignment`, `known_functional_heterogeneity`, `outside_or_stem`, `resolved_nonmonophyly`, `measured_zero_spacing`, or the exact combined reasons |

No generic `negative_support=1-point` is emitted. A bound [0,1] has no default
midpoint. Numeric0 with a defined zero reason is different from a missing point.

## 1. Scope and assertion inputs

`read_A104_scope` receives and preserves:

* Supplied target material/selected region, query identity or unresolved identity,
  boundary and completeness; a public accession or initial candidate is optional.
* `assertion_id`, direct function description, `functional_dimension` (e.g.
  transported-ion preference), resolution, allowed class identifiers, synonym
  map, entailment map and unresolved class mappings. Assertions may emerge from
  investigation; no prior annotation is required to collect these observations.
* Intended lineage/taxon scope, homologous region/copy scope, biological basis,
  transfer-regime observations, local-relatedness measurements and limitations.
* Applicability state from proposal004, source/assumption basis, included/excluded
  requirements. No transfer-frequency or distance cutoff is supplied by default.

It returns a source-grounded scope record, not a numeric applicability weight.
The resolved function description is an input meaning, not an activity score.

## 2. Intended taxa and actual tree samples

`read_A104_tree_inputs` receives these exact records:

| Record | Required fields and constraints |
| --- | --- |
| Intended mapping row | intended organism/taxon slot, canonical gene/protein/copy identity or allowed identities, supplied organism identity, mapping evidence, homologous region, duplicate/alias relation, included/missing state |
| Gene tree | native tree identity, actual tip labels, topology, roots/orientations and source basis, branch lengths with units/model/rounding/missingness, source support representation |
| Organism tree | native tree identity and topology, actual taxon labels, independently justified origin, roots/orientations, source uncertainty and mapping; taxonomic names alone do not fill this |
| Comparison endpoint | `rooted_triplet` or `unrooted_quartet`, selection basis, s=3 or4, fixed intended m and subset manifest, actually common leaf set |
| Copy alternatives | allowed complete mappings and shared constraints; neither arbitrary favorable paralog selection nor a fabricated reconciliation result |
| Native sample row | source sample identity, actual joint-sample key, gene/backbone/graft identity, compatible organism sample/scenario, raw weight, original normalization denominator, weight kind and scope, availability |
| Ensemble | full native total mass, received mass, reported missing mass, conditional subset scope if original total is absent, posterior/bootstrap/likelihood meaning, effective-sample information only if actually supplied |

`calculate_A104_topology` produces one row per fixed triplet/quartet:
tip slots, mapped labels, induced gene grouping/split, organism grouping/split,
`resolved_match/resolved_conflict/unresolved_or_missing`, and the reason.
It returns N,M,D,U, F_supported, D/N,U/N, feasible completion bounds, native
common-leaf distance/convention/denominator, and intended comparison coverage.
When m<s, normalized native fraction is null and F_supported=0 with
`insufficient_taxa`. With an unknown intended manifest, N is null. Missing tips
in a known manifest retain their subset slots. No binomial SE is manufactured.

## 3. Clade membership and characterization inputs

`read_A104_reference_clade` receives:

| Record | Fields |
| --- | --- |
| Clade definition | source clade name/location, fixed intended inventory, crown anchors, rooted crown or oriented-split boundary, outside-side identities/reference-universe limit, scope-selection basis |
| Reference identity row | canonical protein and organism/copy identity, accession/version aliases, same-molecule duplicate records, identity conflict/allowed resolutions, actual tree-tip mapping |
| Reference function row | actual experimental subject/construct, natural versus engineered status, supported positive classes at this resolution, broader-only assignment, known multifunctional set, excluded classes if measured, unresolved additional functions, source locations and scope closure |
| Characterization experiment | endpoint/assay, relevant conditions, native units/readout/uncertainty, controls and detectability, experimental versus inference-only status, preparation/readout identities and shared evidence |
| Negative/failure observation | measured nondetection with conditions/limit, no expression, unstable preparation, no tested alternative, unresolved attribution, or an actually established different function; never collapse these states |

`calculate_A104_function_coverage` canonicalizes identities once and emits:
n intended unique members; k_f observed {f} members; known-other/multifunctional
members; uncharacterized/broader-only/unresolved rows; exact known class union;
observed coverage k_f/n; B_f; and C_f=0 if B_f else k_f/n. `scope_closure` and
all allowed unresolved function sets separately produce Q_f and its [0,1]
identification result for the full-clade claim. It does not treat C_f as Q_f.

If identity/assignment ambiguity changes these values, the output includes
allowed globally consistent scenarios and bounds, not two counted copies of
one uncertain protein. Known other functions outside C remain in the evidence
record but do not become mandatory contrast groups. The same protein's assays
can refine S_i; they do not add a second member or independent topology.

`map_A104_broader_assertion` is an explicit separate transformation receiving
the justified class→broader-description mapping and a new assertion identity.
It preserves precise-assertion failure and exact known function sets. It neither
selects the highest score nor silently narrows the clade. The original function
set can restrict plausible descriptions with the unknown-member qualification;
it is not proof that every untested function is excluded.

## 4. Placement and branch measurements

`calculate_A104_crown_placement` receives each actual query-bearing tree or:

`backbone_id, edge_id/child_id, native_edge_length, distal_attachment_length,
pendant_length, branch_units/model, sample_key, native_weight, uncertainty`.

It prunes q, preserves graft position and reference path lengths, and checks
the complete intended C inventory and boundary. Output fields are:
query-pruned backbone/graft, actual C descendant set or missing-members list,
`interior/stem/outside/nonmonophyletic/boundary/unresolved`, J point/bounds,
native interior/stem/outside/unknown mass. Relevant unresolved topology uses
allowed full refinements; an unrelated polytomy does not automatically make
interior membership unknown. Numeric support labels are not substitute weights.

`calculate_A104_locality` receives the same sample and canonical characterized
set K. It emits every required pairwise path distance, the nearest-other
reference distance for each r, its ordered list, median b, query-to-reference
distances, nearest d, pendant length, O and its reason/bounds. For even |K|,
the median is the mean of the two central values. Fewer than2 usable reference
identities leaves b missing. The exact-zero conventions are those in proposal004;
rounded/censored zero and absent branch values are different inputs. Unknown
common scale prevents a cross-scale ratio. Required distances cannot be copied
from a different favorable tree sample.

`calculate_A104_EDPL` separately receives native placement weights, optimal
attachment distances and total reference length. It returns the unnormalized
double weighted distance and normalized EDPL if the total is positive. This
diagnostic is not a score factor and its absence does not stop scoring. It
does not contain the query pendant length or a probability of function.

## 5. Region, candidate, scenarios and uncertainty

`compile_A104_region` receives matched C,F,J,O records, sample keys/weights,
native denominator, missing mass and source constraints. It returns each
`a_r(z)=C*F*J*O`, its region native weighted mean, intermediate known subtotal,
unknown-mass bounds, point/conditional status and actual sample distribution.
Missing included weights/values are not renormalized or imputed. A factor fixed
at0 may identify a product despite another missing factor, which remains null
in its own cell. Component means remain diagnostics only.

`compile_A104_candidate` receives:

* Persistent candidate identity/current assertions, canonical entailed aliases,
  necessary regions and their applicability states; exact covered-scope map.
* Included comparable analysis identities and reasons, duplicate measurement
  identities, whole-analysis/mapping/function scenarios and their constraints.
* Joint sample vectors across necessary regions with actual native weights;
  alternatively exact marginal weights plus allowed coupling constraints.
* Shared reference/function/organism/branch variables and allowed completions,
  including their use in multiple regions/analyses.

It calculates min_r a_r within a joint draw, weighted averaging within each
included analysis, and the conservative minimum across included comparable
analyses. It outputs candidate point/bounds, per-region diagnostics, covered
requirements, inapplicable/unknown requirements, and every binding null reason.
With only marginals, the specified finite coupling optimization gives bounds;
independence is never silently selected. Repeated representations cannot add
requirements or sample mass. An empty applicable set returns null/not_applicable.

`bound_A104_full_clade_claim` receives the same global constraints and Q_f
instead of C_f, completed topology and all affected distances. It recomputes
the whole compilation for admissible completions and returns infimum/supremum,
with exact versus outer-bound status. Unknown members may introduce heterogeneity
and make the lower bound0 even when observed association is positive. This is
an epistemic qualification, not a compulsory search for an incompatible group.

`summarize_A104_native_uncertainty` computes the stated weighted empirical
quantiles only from an actual joint native score distribution. It keeps
posterior, bootstrap, likelihood-profile and identification meanings separate.
No function probability, calibration, new run, approval step, monitoring rule
or tool execution is inferred from the contract.
