# Fixed first reaction-constraint interfaces and ownership

Implements the finite subset in A110_REFERENCE_REACTION_SHEET_001.md, applying
A110026 Eqs3,5,6,7. No balance/global compilation, network, isotope model,
measurement correction or annotation transfer. Public functions are additive.

## Calculator owner

Exclusive files gene_annotation_episode/literature_reaction_calculations.py
and tests/test_literature_reaction_calculations.py. No source acquisition.

`populate_reaction_constraints(inputs)` accepts exactly:

```
{
 "ratio": null | {
   "mode": "independent_units" | "source_summary",
   "ratio_kind": "product_pair" | "formed_per_consumed" |
                 "formed_per_supplied" | "signal_ratio",
   "unit": "mol_per_mol" | "signal_per_signal",
   "origin": "reported" | "graph_derived" | "synthetic",
   "observations": [{"measurement_key": nonemptystring, "value": finite}],
   "mean": finite|null, "sample_sd": nonnegativefinite|null,
   "independent_n": integer>=1|null,
   "claim": finite|null,
   "alternatives": [{"key": nonemptystring, "prediction": finite|null}]
 },
 "budget": null | {
   "basis": "supplied_reagent_batch" | "usable_batch" | "usable_rate",
   "unit": "umol" | "uM" | "umol_per_min" | "uM_per_min",
   "origin": "reported" | "graph_derived" | "synthetic",
   "resources_complete": boolean,
   "resources": [{"resource_key": nonemptystring,
     "value": nonnegativefinite|null,
     "lower": nonnegativefinite|null,"upper": nonnegativefinite|null,
     "coefficient": strictlypositivefinite}],
   "demand": strictlypositivefinite|null
 }
}
```

Independent units require nonempty distinct observation keys, mean/SD/n allnull
(calculate their descriptive values). Summary requires observations empty;
mean/SD/n can be missing, SD with n=1 invalid. Duplicate keys cannot manufacture
replication; reject them. Alternative keys distinct and not silently dropped.
`signal_ratio` must use signal_per_signal; others mol_per_mol. Signed scalar
ratios are allowed (e.g. background-corrected net response); finite predictions
may be signed. No per-measurement uncertainty or confidence model is inferred.
The summary error identity is available only with mean,SD,exactn (for n=1
explicit single-unit summary may use SDnull but must be kept distinct from
unknownn source summaries). No empty alternatives score. Missing one alternative
keeps its effect unknown: minimum comparison bounds can narrow if others are
known but no invented point. Exact doublezero errors map0.

For budgets rate units only with usable_rate, batch units only with batchbases.
Resources nonempty, keys unique; bounds ordered and enclose any nominalvalue.
Known partialresources can bound capacity using explicit upperbounds even
resources_complete=false; unknown constraints have physical lower0 and unbounded
upper. Missing lower uses0; missing upper is unbounded. Unknown demand means
coverage and score remain unknown with physical coverage[0,1],score[-1,1].
No nominalcapacity unless resources_complete=true and everyvalue supplied.
Resource coefficient is a declared model coefficient, not a measured turnover
rate. Boundcapacity computed min(lower/a),min(upper/a); incomplete model adds
unknown resource lower0/unboundedupper. Coveragebounds apply positive point
demand; do not interpret them as CI. Explicit zero caps can determine z=0 even
otherresources unknown, via nonnegative minimum algebra.

Return exactly `{version,inputs,cells,comparisons,ratio_details,budget_details}`.
version `a110_reaction_constraints_v1`; inputs deepcopied.
`cells` in COMPONENTS fixed order:
ratio_mean, claim_nominal_squared_error, claim_mean_squared_error,
reaction_comparison, reaction_comparison_lower, reaction_comparison_upper,
resource_capacity, resource_capacity_lower, resource_capacity_upper,
resource_coverage, resource_coverage_lower, resource_coverage_upper,
resource_comparison, resource_comparison_lower, resource_comparison_upper.
Each cell `{value,unit,status,formula,origin,unavailable_reason,conditional_on}`
same shape as perturbation calculators. Bounded unpopulated cells retain null
point. Formula/reason/condition codes are fixed exposed constants for later
schema construction. No infinities/NaN: unboundedcapacityupper null withreason.
Mean-squared-error units squared_ratio, ratioscores dimensionless. Comparisons
retain each named alternative prediction, nominalerror, MSE and signedcontrast.
ratio_details retain residuals per model and actual independentn (unknown if
source summary lacks it), source SD, sampling/design assumptions. budget_details
retain basis/unit, completeness, limiting identities and bound semantics.
Exact rational intermediate arithmetic prevents avoidable overflow/underflow;
each final cell reports numerical_model_range independently. Bounded source
comparison range [-1,1] is a logical enclosure, not a confidence interval.

## Reader owner

Exclusive files gene_annotation_episode/literature_reaction_inputs.py and
tests/test_literature_reaction_inputs.py. Reuse _Sources/_witness_schema custody
from literature_assay_inputs. No calculator import, SQL, network or model calls.

`reaction_population_schema()` exact operation arguments:
source_ref, data_source_ref(nullable REF), source_kind(SOURCE_KINDS),
literals object with molecule,construct,experiment,numerator,denominator,
endpoint,condition,resource_context each nullable ordinary literal witness;
interpretation_witnesses array of ordinary witnesses. Numeric values never in
operation arguments. Supplied data_source_ref is an explicitly retained JSON
dataset boundary, not an original-PDF NMR or plot parser.

Retained dataset exact outerfields:
`{version:"a110_source_reaction_measurements_v1", ratio:<as above|null>,
budget:<as above|null>}`. Reject duplicate JSONkeys, nonfinite, invalid enums,
extra fields/shapes and invalid unit/design relationships as calculatorcontract
describes, without performing numerical calculations. At reader boundary ratio
observation keys are local measurementIDs; namespace them using source_ref,
actualartifact_ref and ID. Same namespace applies resourcekeys; alternativekeys
are model IDs and retain supplied identity. Preserve rawdata. Unknown dataset
returns ratio/budgetnull, not fabricatedempty known arrays.

`read_reaction_inputs(arguments, *, read_source)` returns exactly
version `a110_reaction_inputs_v1`, arguments deepcopy, sources registered by
_Sources, literals validated via sources.literal, interpretations array validated
via sources.literal, observations (retained rawdata ornull), calculation_inputs
{ratio,budget} (with namespacedphysicalkeys). Root source registered before
literal witnesses; dataset registered when present. Model/protocol meanings
are source-witnessed interpretations, not deterministically scientifically
verified by literal occurrence. A summary is not a replicate. Do not convert
SD/SEM/plusminus into intervals or assume omitted corrections equalidentity.

## Coordinator ownership

Owns source/reset records, sheet/interface documents, later storage/prompt and
existing LiteratureEpisodes/episode_services integration, concrete primary and
controlled examples and joined verification. Before modifying any consumer read
its complete affected path. No new episode class, private loop, creditformula,
controller change, A101 reader, tool-grader file, original case Store or livepin.
