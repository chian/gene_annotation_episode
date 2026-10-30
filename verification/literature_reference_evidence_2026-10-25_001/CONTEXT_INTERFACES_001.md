# Fixed contextual compatibility interface and exclusive owners

Read paired A108_REFERENCE_CONTEXT_SHEET001 and current A108003/uncertainty004.
This finite implementation uses interval/state relations, logical conjunction/
disjunction, paired coverage, unpaired Frechet bounds and organism capability.
Not a universal plausibility judge, target transfer or new episode/credit rule.

## Shared calculator input / retained dataset payload

`populate_context_compatibility(inputs)` input is exactly the following object.
Reader data source is exactly `{version:'a108_source_context_measurements_v1',
inputs:<this object>}`. No numeric operands in selected operation arguments.

```
question_kind: organism_capability | sample_context_coverage | unreported
origin: reported | graph_derived | synthetic
scope_status: defined | unreported
frame_status: defined | unreported
pairing: paired | unpaired_marginals | unknown
weight_basis: equal_units | measured_duration | measured_volume | inclusion_weight
sampling_design: census | independent_equal_weight | unknown
alpha: finite(0,1) | null
permitted_remainder: boolean | null
requirements: Requirement[]
routes: Route[] | null
contexts: Context[]
marginals: Marginal[]
```

All nested objects closed. Nonemptystring keys are physical/model identifiers,
not scientific prose or scores. Finite numbers exclude booleans. Exact native
unit codes: ppbv_H2_gas, ppmv_H2_gas, uM_H2_solution,
percent_O2_gas, percent_O2_saturation_solution, mM, uM, nm, minutes, state.
Do not silently convert bases or infer Henry-law mappings. Even compatible
scale codes must match exactly in this first interface; a missing conversion
preserves unresolved membership with native operands.

Interval exactly `{lower:number|null,upper:number|null,lower_closed:boolean,
upper_closed:boolean}`. Null bounds mean open -infinity/+infinity. Unbounded
ends must have closed=false. Finite endpoints ordered; singleton requires both
closed. No empty intervals. Intervalnull means unknown values, not exactzero.

Requirement `{key,unit,supported:Interval[],incompatible:Interval[]}`.
Domain is a union, preserving gaps/open endpoints. An observation interval must
be wholly covered by the relevant union to establish membership. Overlapping
D+/D- gives unresolved membership with domain_conflict, not favorable selection.
No complement of D+ is automatically D-. Requirementkeys unique.

Route `{key,requirements:string[],requirements_complete:boolean,
joint_support:established|unresolved|conflicting}`. Keys unique, requirementlist
unique and refers to defined requirementkeys. routes=null means unknown route
definition. Non-null routes must be nonempty. A complete empty requirementlist
is permitted for a defined question; unknown question never gives support.
An incomplete route has an extra unknown required predicate. More than one
required predicate needs established joint support for positive conjunction;
a known necessary failure still gives upper0. Single requirement needs no
multivariate interpolation. Unsupported unknown alternatives are represented
by an explicit incomplete empty route, never silently omitted.

Context `{key,weight:positivefinite|null,cluster_key:string|null,
scope_match:matched|unresolved|conflicting,observations:Observation[]}`.
Unknown weight retains capability information but cannot supply sampledenominator.
equal_units requires every known weight=1. measured_duration/volume/inclusion
weights are declared measured operands; deriving inverseprobabilities or
calibrations is not implemented. ContextIDs denote original opportunities.
Exact repeated Context rows with samekey coalesce; samekey with different
facts/weight fails duplicate_context_conflict. Do not dedupe equal values under
different keys. Technical repeats are not independent Context rows.

Observation exactly:
`{requirement_key,measurement_key,unit,interval:Interval|null,
relation: numeric|supported|incompatible|unresolved,
reported_sd:nonnegative|null,reported_sem:nonnegative|null,
reported_plusminus:nonnegative|null,
reported_count:integer>=0|null,count_relation:exact|at_least|at_most|unknown,
replicate_kind:biological|technical|timepoint|unknown}`.
Keys nonempty; oneobservation per requirement percontext. Numeric intervals use
relation=numeric; narrow biological state relations use unit=state and
intervalnull. State domainregions must be empty, since the explicit narrow
relation supplies membership. Numeric unknown interval retains missing value.
SD/SEM/unspecified+- are native separate magnitudes, never confidence domains.
Equal measurementkeys must have exactly consistent unit/value/error meanings;
aliases are retained as dependencies, not extra biological replication.
The reader namespaces Context/measurement/cluster IDs with actual dataset source
and artifact; requirement/route keys are fixed model identities, not physical IDs.

Marginal `{requirement_key,lower:finite[0,1],upper:finite[0,1]}`, ordered, keys
unique. Valid unpaired mode has contexts empty, defined frame, onecomplete route
over exactly those required marginals (missing ones become[0,1]); same-frame
joint domain must not be invented. Only necessary AND supported in this mode;
other route designs preserve unknown coverage. Paired mode requires marginals
empty. Unknown pairing preserves unknown coverage. Capability cannot be derived
from unpaired marginal fractions; preserve unknown even when coverage is positive.

## Calculator meaning and output

Global undefinedscope or percontext unresolved/conflicting scope gives [0,1]
for that context. For matched scope, missing requirements, wrong unitbases,
missing numericintervals and overlapping domains preserve structured reasons.
Exact logical ell/u apply intervalunion containment or explicit narrow state
relations. Route AND and alternative OR use the current sheet formulas; these
are logical events, not categories coded as numerical quality grades.

Paired C uses actual positiveweights and fixed defined frame; unknown frame,
weight or zero units leaves Cpointunknown and bounds[0,1]. Keep usable W and
logical percontext results separately. Capability OR includes an unknown
permitted remainder whenever permitted_remainder is true ORnull. Only explicit
false asserts exhaustive scope; source interpretation must justify it. Empty
observed states with unknown remainder does not imply impossibility. Undefined
scope prevents both C and O support. Never substitute C for O or choose maximum.

Return exactly `{version:'a108_context_compatibility_v1',inputs,cells,
memberships,routes_by_context,contexts,counts,qualifications}`.
Deepcopy inputs. COMPONENTS fixed order:
sample_weight,supported_weight,unresolved_weight,incompatible_weight,
coverage_lower,coverage_upper,coverage_point,
capability_lower,capability_upper,capability_point,
selected_lower,selected_upper,selected_point,
sampling_lower,sampling_upper.
Cellshape `{value,unit,status,formula,origin,unavailable_reason,conditional_on}`,
same as reactioncalculator; fixed exposed FORMULAS/REASONS/CONDITIONAL_CODES.
Use context_weight unit for weightcells, dimensionless for fractions/bounds.
Bounds round outward; exact rational intermediates avoid avoidable range loss;
each unrepresentable cell gets numerical_model_range without erasing others.
Memberships retain context/requirement keys, native B/domains, ell/u and reasons;
context rows retain final L/U and uniqueweight. counts includes deduplicated
context_units, distinct_known_clusters, actual_sampling_n(nullable).
qualifications fixed reasoncodes, not unrestricted composed prose.

Unreported question_kind preserves selected bounds[0,1] and unknown selectedpoint;
it must not default to organism capability when source inputs are absent.
Sampling only when question_kind=sample_context_coverage, paired, definedscope/
frame, equal_units, independent_equal_weight, everycontext has a unique known
cluster_key, alpha given, and all admissible values are deterministic/model
domains (this interface never uses confidence domains). n=actual dedup contexts.
Use Hoeffding epsilon=sqrt(log(2/alpha)/(2n)); outer interval from Cbounds.
Retain analytical bounds separately. Census and other designs leave sampling
interval null, with specific reason. Unit count is not enzyme preparation count.
All missing C/O retain physical[0,1]; point only if lower=upper. No100scale or
final annotation policy is installed. Diagnostic shared cells not new evidence.

## Reader and operation boundary

Exclusive reader owner: gene_annotation_episode/literature_context_inputs.py,
tests/test_literature_context_inputs.py. No calculator imports, arithmetic,
network, model or SQL. Reuse _Sources and ordinary source witnesses.
`context_population_schema()` arguments exactly source_ref,
data_source_ref(nullableREF),source_kind(SOURCE_KINDS),literals object with
molecule,organism,strain,experiment,function,biological_context,sample_frame,
endpoint,condition each nullablewitness,interpretation_witnesses arraywitnesses.
Numeric source records are the retained dataset above, not model-selected
numbers in operation args. StrictduplicateJSON, finitevalues, closed designs/
units, intervals, relation rules, meaningful references and duplicate checks.
No dataset returns calculation_inputs=None (calculator must offer
`empty_context_inputs()` canonical unreportedquestion with unknownscope/frame
and noobservations; rootstorage uses that only to preserve physicalunknowns).
Reader return exactly version,arguments,sources,literals,interpretations,
observations(rawdataset|null),calculation_inputs(inputs|null).
Version a108_context_inputs_v1. Missing source preserves literal facts.
Namespace physical IDs deterministically, retain raw IDs in observations.

## Storage and selected typed return boundary

Exclusive storage owner: gene_annotation_episode/literature_context_storage.py,
tests/test_literature_context_storage.py. Reuse LiteratureRateRepository selected
authority, transactional publication and exact admitted subsets as in current
reaction_storage, including transitive scoped provenance and fixed directsource
order. provider literature.experimental.context; recordversion
literature_context_record_v1; operations/received tables literature_context_*.
Export LiteratureContextRepository,context_population_schema,context_cells_schema,
COMPONENTS,PROVIDER. Populate reader then calculator; missinginput uses calculator
empty_context_inputs(). Same-run request/scope/selected operation authority.
Replay must never reopen original bytes or recompute. Schema closed and exact
saved values validated; no observations/credit/decisions in repository.

ScientificBINDINGS molecule/reference->assayed_subject_ref,organism/reference,
strain/reference,experiment/reference,function/term->function_ref,
biological_context/context,sample_frame/context,endpoint/term,condition/context.
Use source byteanchors and unique fieldmeaning in generated identities.
Typedrow includes sheet/evidence/data refs,9bindings, component/cell minusformula
plusfixedformula_code, and metadata copied from savedinputs/results:
question_kind,origin(as operand_origin),scope_status,frame_status,pairing,
weight_basis,sampling_design,alpha,permitted_remainder,context_units,
distinct_known_clusters,actual_sampling_n,requirement_count,route_count(nullable),
native_unit_bases(uniqueenumarray),qualifications(fixedcodesarray),
evaluation_scope='reference_organism_sample_compatibility',
bound_kind='logical_domain_not_confidence_interval',
measurement_corrections='not_applied',target_correspondence='not_evaluated'.
Sampling cells additionally carry their conditional Hoeffding interpretation;
do not call the analytical bounds statistical confidence.

## Coordinator

Owns sheets/interfaces/source/reset evidence, complete affected-consumer reads,
existing LiteratureEpisodes/WorkflowServices/prompt integration, source/synthetic
examples and joined verification. No edits to original case Store, livepin,
toolgrader paths, controller/credit math, new episodeclass or private workflow.
Original Huc sourcecase must not turn purifiedenzyme assays into habitat samples
or a proven whole-organism witness. Full objective remains open beyond subset.
