# Fresh repository coding ownership

Additive ownership refinement to BINDING_MODEL_RUNTIME_001.md: a fresh worker
owns ONLY new literature_binding_model_storage.py and
tests/test_literature_binding_model_storage.py. Root retains services/binding/
prompt integration and assembled tests/examples. Consume the full two model
interface/runtime documents and the final pure model/parser code; no papers or
packets, active Store/pin, historical sheet or other file edits. Synthetic source
fixtures suffice. Coordinate pure interfaces with binding_joint_model agent.

Export LiteratureBindingModelRepository,PROVIDER,COMPONENTS,
binding_model_population_schema,binding_model_cells_schema. Model components come
from literature_binding_models. Reuse LiteratureBindingRepository._source via
inheritance and common saved operation validation, but override population and
projection. Source_ref MUST be a received actual selected binding-parameter
sheet, checked with a separate ordinary LiteratureBindingRepository.read.

Persist payload version,input_source_ref,input_source_refs,input_artifact_ref,
sheet,experimental_bindings,original_evidence_source_ref,model_source_ref,
model_source_provenance,model_witnesses,comparison(original binding comparison).
Keep raw covariance/measurement keys only in host artifacts. Present model source
requires >=1 exact witness. Any model-source declared parent must be received,
same scope and assigned-page lineage; retain it. Inherited binding source/raw
original evidence are scoped provenance, not a hidden reparse of source bytes.
Projection is saved numerical copying only. Replay revalidates all saved direct
inputs/signature and does not invoke parser/calculator or original image reads.

Exact tool args source_ref,model_source_ref(number-free nullable REF),model_witnesses
(existing literal witness array). No model numerical operands. It is not necessary
to invent another interpretation enum or model selector: model kind and covariance
declarations are in the retained model source. Witness custody is not scientific
proof; every model outcome stays conditional. Missing model source is valid and
returns useful partial native e plus dependent model-unreported cells.

Typed row: sheet_ref,evidence_source_ref (=input binding sheet),
original_evidence_source_ref,model_source_ref,
all five original binding refs,component,all pure cell fields EXCEPT formula,
formula_code=binding_model_<component>_v1,
parameter_kind,contrast_meaning=test_parameter_exceeds_reference,
evaluated_scope=interpreted_source_parameter_contrast,
model_kind=unreported|known_normal_log_parameters,
variance_status=not_supplied|known|estimated|unknown,
censoring_model=not_supplied|none|threshold_of_log_estimate|unknown,
model_origin=not_supplied|reported|derived|synthetic,
source_uncertainty_basis,minimum_experiment_count,independent_preparation_count:null,
design,protein_arrangement. All code strings finite, formulas in saved host
sheet with declared code mapping. Confidence/identification bounds remain null.
No raw measurement-hash tracking text in typed prompts. Original bindings and
declared source provenance refs appear in outcome.record_refs (newly created
source alone in changed_record_refs); this selected result supplies their scoped
metadata without scientific credit. Never add a receiver receipt yourself.

Tests: original selected binding output required (forged provider source rejected),
actual received covariance/witness/declared-parent scope & lineage, numerical
selection/no-model partial behavior, exact typed-subset schema/values/conditions,
saved original return/provenance, no full private-sheet expansion on forwarding,
closed-form validator as well as JSON schema, source-only zero extra observations,
immutable operation replay and fresh reopen with reads/parsing/calculation disabled.
Root's connected Workflow test will cover actual selected execution/observations.
