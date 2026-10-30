# Executable A111 source-model geometry components

This additive sheet specifies the first implemented structural component path
under the adopted literature objective. The complete A111 proposal027 remains
historical/current research authority for its broader specification. This
source-only path does not provide T, target correspondence, aggregate A111 or
annotation credit. It does not add another evidence axis.

## Paired extraction and numerical meanings

One sheet concerns one exact selected deposited model/assignment and a fixed
physical question. The question's geometry panel supplies complete author
chain/residue/insertion/component/atom-group/alternate selectors, proposed
supporting and incompatible distance cutoffs in Å, and identity coordinates
without symmetry transformation. The local panel fixes required residue-level
RSCC selections. The panel length is the denominator, not independent sample n.

The original coordinate file supplies actual atom rows, Cartesian points,
deposited occupancy and B parameters, model and revision metadata. The original
wwPDB validation supplies actual selected row attributes and source version.
Their entry/revision and endpoint identities are joined explicitly; missing
or mismatched validation preserves coordinates but cannot supply a local-fit
index. Report metadata agreement does not expose a coordinate-byte digest or
establish independent map recomputation.

The exact extraction, all native selected rows, pair distances, scientific
selectors, units, origins and source/artifact custody are retained in the saved
payload. Literal molecule/construct/experimental-system/partner/condition/
experiment fields have byte witnesses or remain null. The separate recurring
STRUCTURE_TASK asks the scientific questions; it is not this numerical sheet.

| Executable numeric cell | Exact calculation | Meaning | Original4HF1 example |
| --- | --- | --- | ---: |
| local_fit_index | D=min_j(max(0,RSCC_j)^2) over fixed nonempty residue panel | Proposed weakest-endpoint local map/model agreement | .815409 |
| geometry_support_fraction | Gplus=count(group_distance≤positive_max)/J | Fraction meeting the declared supporting geometry | 3/4=.75 |
| geometry_opposition_fraction | Gminus=count(group_distance≥incompatible_min)/J | Fraction meeting the separate incompatible geometry | 0/4=0 |
| source_geometry_positive | D*Gplus | Proposed source-only supporting product under selected-model conditioning | .61155675 |
| source_geometry_opposing | D*Gminus | Corresponding opposing product | 0 |
| source_geometry_signed | D*(Gplus-Gminus) | Directed difference with the same shared D | .61155675 |

The source example uses six native RSCCs .911,.903,.963,.944,.960,.939 and
four model-derived group distances2.814260471,3.504470573,2.648124053,3.056920182Å.
Supporting cutoff3.5Å and incompatible cutoff4.5Å are illustrative proposals;
they leave a gap. A3.6Å supporting cutoff instead gives Gplus1 and product
.815409. No native measurement uncertainty resolves the3.504Å threshold case.

These products correspond to proposal027's detected source row under the
**explicitly conditional** selected model/atom assignment, q=C=I=1 by that
definition. No measured occupancy, causal comparison or unconditional assignment
claim is assigned1. There is no T operand or silent T=1. The output scope is
conditional_deposited_model_geometry; it cannot answer a population, causal or
holo-state question without additional experiments and calculations.

Squaring RSCC, taking its minimum and the geometry predicate sets are proposed
conventions. All six score-cell origins are proposed; original reported RSCCs
and coordinate-derived distances remain separately recorded. They reuse one
fitted model/dataset and are not independent evidence or probabilities.

## Missingness, bounds and source limitations

Each cell has value,lower,upper,unit,status,origin,unavailable_reason,
conditional_on and a closed formula_code. Bounds are conditional arithmetic or
logical outer enclosures. They are not confidence intervals, error bars or
statistical population precision. Coordinate/measurement uncertainty remains
unreported even when an arithmetic point can be calculated.

Missing required atoms retain their geometry-panel position; the distance is
unknown. Missing local members retain their local-panel position. Empty panels
have invalid/unknown denominators rather than perfect scores. Different or
unreported entry/revision binding leaves D unknown. Known geometry remains
useful when local validation is absent. In the same source without validation,
Gplus=.75,Gminus=0 while D and positive/signed products remain null. The
opposing product can be algebraically0 because Gminus is known0 and D has
domain[0,1]; D itself remains unknown.

Exact factor/count arithmetic and outward rounding preserve valid float
enclosures. Nonzero underflow and nonfinite distance output are explicit range
failures. Paired geometry uses disjoint predicates; a failed supporting
predicate is not automatically opposition. The signed calculation retains D
as one variable, including exact shared-factor cancellation.

One crystal dataset, its two asymmetric-unit interfaces, original article,
coordinates and validation report remain one dependent source chain. Deposited
occupancy1.00 is a parameter with unestablished population/refinement meaning.
Rfree, global resolution and B factors do not replace local fit. The IscR case
uses engineered clusterless3CA protein; proposed holo-state mechanisms are not
directly observed contacts. Between-crystal construct and condition differences
prevent an unqualified causal inference.

## Selected operation and typed handoff

literature.structure.populate runs as a selected ordinary operation inside the
existing LiteratureEpisodes. structure_population_schema/read_structure_inputs
nominate/read actual source operands; populate_source_geometry calculates;
LiteratureStructureRepository saves the original request, extraction, numeric
sheet and selected outcome transactionally. requested_structure_components
chooses exact typed rows from literature_structure_cells. The ordinary parent
form preserves source/construct bindings and explicit scientific conditions.

Every returned score also carries the actual model number, geometry_definition,
local_validation_definition, residue granularity and identity-transform basis.
The receiving parent therefore receives its exact criteria and denominators.
Those source selectors have constrained semantic types and are validated against
the saved values; they are not unrestricted generated findings. Deterministic
STEERING renders a sheet's physical definitions once alongside requested cells,
while the parent retains its own full TASK.

Saved replay must use committed sheet/request bytes with original paper,
coordinates, validation, parsing and calculation disabled. Source custody,
selected-output authority, scoped page lineage and exact admitted subsets remain
checked. The operation creates no synthetic scientific/controller observations.

General symmetry/assembly transforms, alternative assignment/model scenarios,
measured occupancy, causal comparability/isolation, calibrated nondetection,
other structural methods, observation/candidate aggregation and actual model-backed
structural work remain unfinished. Missing scientific inputs and unimplemented
functions are different limits; neither disappears because this path passes.
