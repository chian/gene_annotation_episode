# Selected binding-parameter population and typed delivery

Uses BINDING_PARAMETER_INTERFACES001–003 unchanged. Root owns glue in
episode_services.py, literature_episodes.py, literature_experimental_prompt.py,
new literature_binding_prompt.py and assembled integration examples/checks.
Fresh repository worker owns ONLY new literature_binding_storage.py and
tests/test_literature_binding_storage.py. Do not open a primary source/packet;
synthetic retained-table/image fixtures suffice. Live pins/state are immutable.

Export LiteratureBindingRepository, PROVIDER, COMPONENTS, binding_population_schema,
binding_cells_schema. Inherit LiteratureRateRepository for persisted selected-
operation proof, exact returned-value validation, received subset and forwarding.
provider=literature.experimental.binding_parameter;
record_version=literature_binding_parameter_record_v1;
operations_table=literature_binding_operations;
received_table=literature_binding_received.

Selected tool literature.binding.populate arguments exact:
source_ref,representation(retained_visual_transcription|primary_table|synthetic_fixture),
subject,state,experiment,reference_ligand,test_ligand (nonempty strings),
parameter_kind(ic50|reported_hill_kd),
design(equilibrium_competition|direct_binding_isotherm|other|unknown|conflicting),
protein_arrangement(single_preparation|separate_preparations|protein_mixture|unknown|conflicting),
interpretation_witnesses(existing exact literal witness schema).
Known design/arrangement requires>=1 witness; conflicting requires>=2 distinct
witnesses. Those are episode interpretations with exact custody, not semantic
proof. A declaration of kind/design mismatch is preserved with numerical cells;
never relabel IC50 as Kd. No numbers or fit covariance are model tool operands.

Load exact original UTF8 table source, call reader with selected labels, then
calculator. Validate root table and every witness/image source against actual
context receipts, same scope and assigned-page source lineage. Use original
ratio repository's source checks as guide, no globally available source fallback.
For visual rows validate every original source/artifact against table's declared
parent_source_refs and actual image bytes/dimensions (PIL). Box inbounds, original
source actually received; preserve all input parents. No pixel/OCR claim.
Use existing _Sources to validate source interpretation witnesses. No paper reads,
model calls, tool dispatch, auto-child, observation/receipt injection or decisions.

Publish immutable payload {version,input_source_ref,input_source_refs,input_artifact_ref,
sheet,comparison,interpretation_kind:episode_source_interpretation,
interpretation_witnesses,experimental_bindings} in ordinary source record, with
request_ref containing run_id,episode_id,operation_key,arguments. Base read checks
actual selected output identity, run/version/parents. Replay validates exact
signature/scope and all original received inputs before returning saved outcome;
does not parse/recalculate again. Completed outcome includes sheet_ref,cells,
comparison and interpretation_kind, normal record_refs and changed_record_refs.

Bindings (all reference records of type literature_result) identify subject_ref,
state_ref,experiment_ref,reference_ligand_ref,test_ligand_ref with source labels;
these are reported/interpreted source identities, not proven target correspondence.

Typed namespace literature_binding_cells; requested_binding_components selects
exact subset of the ten calculator components. Each projected row contains
sheet_ref,evidence_source_ref,all five binding refs,component, all numerical
cell fields (including relation/bound_kind/confidence_bound/parameter_identification_bound),
parameter_kind,uncertainty_basis,minimum_experiment_count,
independent_preparation_count:null,source_origins,
design,protein_arrangement,interpretation_kind:episode_source_interpretation.
All strings/enums closed to calculator's finite meanings; no unrestricted return
summary. Formula is a finite component-specific literal from calculator, not
unrestricted prose. Preserve unit nM/fraction/dimensionless. Null confidence and
parameter bounds must survive parent receipt. Source origins reported/synthetic/
visual_transcription. No private full-sheet expansion when forwarding subset.

Root glue includes operation/schema/route, saved descriptor code hashes,
source-lineage argument validation, services repository and typed fact meanings
through existing shared LiteratureEpisodes. Full child TASK gets separate
aspect-specific binding questions; STEERING shows relation and reported-limit
meaning with values. Parent retains its own TASK and admitted typed meanings.
No per-axis episode, numerical stopping/progress change, complete sheet prompt
dump, new scientific acceptance gate or eleventh axis.
