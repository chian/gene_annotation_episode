# Selected source model calculation and ordinary typed return

Root owns this integration; model/source-reader workers own their disjoint pure
files under BINDING_MODEL_INTERFACE_001.md. The new selected operation is
literature.binding.model.populate({source_ref,model_source_ref,model_witnesses}).
source_ref is an actually received authoritative literature.binding.populate
sheet. model_source_ref is null or an actually received retained model JSON source.
No caller/model numerical arguments; exact source witnesses establish custody,
not automatic scientific correctness. Present model source requires a witness.

Use LiteratureBindingRepository.read to validate the prior source's actual
selected-output identity, run/version/parents; do not trust provider label alone.
Use its _source receipt/scope/assigned-page checks for all actual input sources
and witnesses. Validate all model-source declared parents, retaining them. Model
source parsing and likelihood calculation happen only on the selected operation,
never on fact projection, admission or reopening. Missing model source preserves
the usable native log comparison and returns explicit missing-model cells.

New LiteratureBindingModelRepository inherits the existing saved-operation /
exact typed-receipt machinery. Provider literature.experimental.binding_model;
record_version literature_binding_model_record_v1; operation/received tables
literature_binding_model_operations/literature_binding_model_received.
Payload retains original binding sheet, original evidence source, all input source
parents, source-model JSON provenance, model witnesses, exact original bindings,
conditional model sheet and measurement keys. Measurement-key hash encoding is
sorted compact JSON, ensure_ascii=False, allow_nan=False over {parameter_kind,
physical}, full SHA256 prefixed binding_measurement_. It is not domain.identity's
shortened hash or its default ASCII serialization.

Returned namespace literature_binding_model_cells, subset selector
requested_binding_model_components. Each typed row retains the five original
subject/state/experiment/ligand refs; source/binding/original evidence/model source
refs; numerical value/relation/unit/status/conditions; finite formula_code;
parameter_kind,contrast_meaning,test_parameter_exceeds_reference evaluated scope,
model_kind,variance_status,censoring_model,model_origin; source uncertainty basis,
minimum experiment count, null independent preparation count; design and protein
arrangement. Raw measurement hashes/full covariance/numerical diagnostics stay in
the saved host payload and referenced model source. They are not tracking text
in prompts. Exact source-owner validation is performed before calculation.

An explicitly selected calculation may examine its received saved source artifact
and returns its declared provenance references. Automatic return forwarding copies
only the admitted cells, with no expansion to the original private full sheet.
No original paper/image is reread to apply/reopen the saved parameter calculation.
Outcome records actual scoped source/reference provenance, without source-ID credit.

Root glue adds descriptor hashes, one optional assignment field, one catalog
operation, existing service/repository route and one closed fact-source schema.
Nested model_source_ref/model_witnesses obey page lineage. Full recurring TASK
asks whether covariance belongs to these actual log estimates and whether a bound
is a stated threshold-reporting event. STEERING carries only returned model kind,
uncertainty/censoring status, conditions and numerical cells. No new episode,
mandatory extraction/model sequence, grader composer, controller observation,
target correspondence or W05 change. Old sheets/results/pins are preserved.
