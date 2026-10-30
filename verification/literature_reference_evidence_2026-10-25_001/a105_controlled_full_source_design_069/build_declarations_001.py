"""Design declarations only. Does not implement or execute a source reader."""
from copy import deepcopy as cp
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent

def load(path):
    return json.loads((BASE / path).read_text())

def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")

def obj(p):
    return dict(type="object", properties=p, required=list(p), additionalProperties=False)

def ref(n): return {"$ref": "#/$defs/" + n}
def null(s): return {"anyOf": [s, {"type": "null"}]}
def arr(s, **kw): return dict(type="array", items=s, **kw)
def enum(*v): return {"enum": list(v)}

def embed(schema, prefix, target):
    def rename(value):
        if isinstance(value, dict):
            return {k: ("#/$defs/" + prefix + v[8:] if k == "$ref" and v.startswith("#/$defs/") else rename(v)) for k, v in value.items()}
        if isinstance(value, list): return [rename(v) for v in value]
        return value
    for key, val in schema.get("$defs", {}).items(): target[prefix + key] = rename(val)
    return rename({k: v for k, v in schema.items() if k not in ("$defs", "$schema")})

selection = load("a105_controlled_graph_design_061/SELECTION_SCHEMA_V2_001.json")
graph = load("a105_controlled_graph_design_061/GRAPH_RESULT_SCHEMA_002.json")
owner = load("a105_controlled_adapter_design_065/OWNER_INPUT_SCHEMA_004.json")
sheet = load("a105_controlled_adapter_design_065/OWNER_OUTPUT_SCHEMA_004.json")
old = load("a105_controlled_response_design_056/implementation_stage_008/CLOSED_RESULT_INTERFACE_008.json")

# Exact original selection bytes are copied by the verifier, not regenerated.
D = cp(selection["$defs"])
D["Selection"] = embed(selection, "S_", D)
D["GraphResult"] = embed(graph, "G_", D)
D["OwnerInputs"] = embed(owner, "O_", D)
D["OwnerSheet"] = embed(sheet, "H_", D)
T = {"type": "string", "minLength": 1}
N = {"type": "number"}
I = {"type": "integer", "minimum": 0}
B = {"type": "boolean"}
SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
rate = cp(D["G_GraphUnitRecord"]["properties"]["native_registry_unit"]["anyOf"][0])
canonical = cp(D["G_GraphUnitRecord"]["properties"]["canonical_unit"]["anyOf"][0])
for name in ("Rational", "TextLocator", "ImageLocator", "WitnessRecord", "SourceRecord", "ImageRecord", "CanonicalDisplay"):
    D[name] = cp(D["G_" + name])
codes = sorted(set(old["diagnostic_codes"] + D["G_Diagnostic"]["properties"]["code"]["enum"] + [
    "covariance_owner_subset", "covariance_incomplete_owner_binding", "covariance_owner_dimension_conflict",
    "unresolved_active_representation_model", "canceled_source_representation_difference",
    "source_reading_nomination_identity", "source_model_active_scope_unresolved",
    "source_covariance_full_scope_invalid", "source_covariance_projection_loss",
]))
D["Diagnostic"] = obj({"code": enum(*codes), "field": T,
    "domain": enum("source_representation", "source_binding", "reader_capability", "source_interpretation", "dependency"),
    "source_refs": arr(T, uniqueItems=True)})
AD = arr(ref("Diagnostic"))
# Shared saved records point to the union diagnostic vocabulary.
for name in ("WitnessRecord", "SourceRecord", "CanonicalDisplay"):
    D[name]["properties"]["diagnostics"] = cp(AD)

interpret_values = sorted({v for name in ("Relationships", "Arm") for p in D[name]["properties"].values()
    if p.get("type") == "object" and "value" in p.get("properties", {})
    for v in p["properties"]["value"].get("enum", [])} | {
        "known", "estimated", "sd", "sem", "ci", "unspecified", "unreported", "same_as_response", "explicit_unit",
        "biological_preparations", "technical_measurements", "fit_to_averaged_curve", "between_fitted_parameters", "none",
        "known_joint_normal_source_means"})
D["InterpretationExtraction"] = obj({"selection": obj({"value": enum(*interpret_values), "witnesses": arr(ref("Witness"))}),
    "witnesses": arr(ref("WitnessRecord")), "effective_value": enum(*interpret_values), "diagnostics": AD})
D["MeaningExtraction"] = obj({"selection": ref("Meaning"), "witnesses": arr(ref("WitnessRecord")),
    "canonical_witness": null(ref("WitnessRecord")), "canonical_correspondence": ref("InterpretationExtraction"),
    "resolved_state": enum("known", "unknown", "conflicting"), "canonical_id": null(T), "diagnostics": AD})
D["NumberCandidate"] = obj({"selection": ref("NumberSelector"), "witness": ref("WitnessRecord"),
    "raw_expression": null(T), "native_value": null(N), "relation": enum("point", "lt", "le", "gt", "ge", "unresolved"),
    "approximate": null(B), "source_locator": null(ref("TextLocator")),
    "status": enum("parsed", "unsupported", "numeric_range", "dependency_unavailable"), "diagnostics": AD})
D["DefinitionWitnesses"] = obj({k: ref("NumberCandidate") if k == "amount" else ref("WitnessRecord")
    for k in ("bridge", "clause", "amount", "amount_unit", "time_unit", "endpoint", "endpoint_entity", "definition_entity")})
D["TextUnitRecord"] = obj({"selection": null(ref("UnitSelection")), "witness": null(ref("WitnessRecord")),
    "raw_unit": null(T), "canonical_unit": null(canonical), "exact_scale": null(ref("Rational")),
    "native_registry_unit": null(rate), "definition_witnesses": null(ref("DefinitionWitnesses")),
    "status": enum("supported", "unknown", "unsupported", "numeric_range", "dependency_unavailable", "endpoint_correspondence_unknown"), "diagnostics": AD})
D["UnitCarrier"] = {"oneOf": [obj({"kind": {"const": "text"}, "record": ref("TextUnitRecord")}),
    obj({"kind": {"const": "graph"}, "record": ref("G_GraphUnitRecord")})]}
# Tags belong to the shared host carrier. Original v1/063 records stay unchanged.
D["TextMeasurementExtraction"] = obj({"selection": null(ref("TextMeasurement")), "candidates": arr(ref("NumberCandidate")),
    "fragments": arr(ref("WitnessRecord")), "unit": null(ref("TextUnitRecord")), "graph_witnesses": arr(ref("WitnessRecord"), maxItems=0),
    "reading_status": enum("not_selected", "exact", "ambiguous", "unreadable", "conflicting", "unsupported", "dependency_unavailable"),
    "source_observation_id": null(T), "canonical_display": ref("CanonicalDisplay"), "pixel_result": {"type": "null"}, "diagnostics": AD})
D["MeasurementExtraction"] = {"oneOf": [ref("TextMeasurementExtraction"), ref("G_MeasurementExtractionV2")]}
piece_states = enum("parsed", "unsupported", "numeric_range", "dependency_unavailable")
D["IntervalRecord"] = obj({"selection": ref("CISelector"), "witness": ref("WitnessRecord"),
    "raw_values": null(arr(T, minItems=2, maxItems=2)), "values": null(arr(N, minItems=2, maxItems=2)), "status": piece_states, "diagnostics": AD})
D["ConfidenceRecord"] = obj({"selection": ref("NativeTextWitness"), "witness": ref("WitnessRecord"),
    "value": null({"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1}), "status": piece_states, "diagnostics": AD})
# The native count reading is preserved exactly; lexical/dependent semantics are
# checked by the shared saved validator rather than inferred from the numeral.
D["NativeSavedWitness"] = obj({**cp(D["NativeTextWitness"]["properties"]), "artifact_ref": T})
D["NativeSavedNumberSelector"] = obj({**cp(D["NumberSelector"]["properties"]), "witness": ref("NativeSavedWitness")})
D["CountReading"] = obj({"selector": ref("NativeSavedNumberSelector"), "raw_number": T, "value": null({"type": "integer"}),
    "notation": enum("decimal_digits", "english_cardinal", "unsupported"), "relation": enum("point", "lt", "le", "gt", "ge", "unresolved"),
    "approximate": null(B), "status": enum("exact", "qualified", "not_positive", "unsupported", "range_or_alternatives"),
    "unavailable_reason": null(enum("count_range_or_alternatives", "unsupported_count_literal", "positive_count_required", "exact_count_qualified"))})
D["CountRecord"] = obj({"selection": ref("NumberSelector"), "witness": ref("WitnessRecord"), "reading": null(ref("CountReading")), "diagnostics": AD})
D["UncertaintyCanonical"] = obj({"statistic": enum("sd", "sem", "ci", "unspecified", "unreported", "unknown", "conflicting"),
    "magnitude": null({"type": "number", "minimum": 0}), "interval": null(arr(N, minItems=2, maxItems=2)),
    "confidence_level": null({"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1}),
    "count": null({"type": "integer", "minimum": 1}), "repetition_basis": cp(D["Uncertainty"]["properties"]["repetition_basis"]["properties"]["value"]),
    "estimate_basis": cp(D["Uncertainty"]["properties"]["estimate_basis"]["properties"]["value"])})
D["UncertaintyExtraction"] = obj({"selection": ref("Uncertainty"),
    "meanings": obj({k: ref("InterpretationExtraction") for k in ("statistic", "unit_relationship", "repetition_basis", "estimate_basis")}),
    "magnitude": null(ref("NumberCandidate")), "interval": null(ref("IntervalRecord")), "unit": null(ref("TextUnitRecord")),
    "effective_unit": null(ref("UnitCarrier")), "confidence_level": null(ref("ConfidenceRecord")), "count": null(ref("CountRecord")),
    "canonical": ref("UncertaintyCanonical"), "diagnostics": AD})
roles = list(selection["properties"]["arms"]["properties"])
D["ArmScience"] = obj({"selection": ref("Arm"), "context": obj({k: null(ref("WitnessRecord")) for k in D["Arm"]["properties"]["context"]["properties"]}),
    "protein_arrangement": ref("InterpretationExtraction"), "meanings": obj({k: ref("MeaningExtraction") for k in
    ("endpoint", "normalization", "subject_construct", "condition", "physical_observation")}), "intended_factor_level": null(ref("WitnessRecord"))})
D["ArmExtraction"] = obj({**cp(D["ArmScience"]["properties"]), "measurement": ref("MeasurementExtraction"),
    "reported_uncertainty": ref("UncertaintyExtraction"), "calculation_operand": null(ref("O_Arm")),
    "graph_details": null(ref("GraphResult")), "diagnostics": AD})
D["RelationshipExtraction"] = obj({k: ref("MeaningExtraction") if k.endswith("_target") else null(ref("WitnessRecord")) if k == "intended_factor"
    else ref("InterpretationExtraction") for k in D["Relationships"]["properties"]})
D["CovarianceBindingExtraction"] = obj({"selection": null(ref("CovarianceBinding")), "label_witness": null(ref("WitnessRecord")),
    "owner_witness": null(ref("WitnessRecord")), "correspondence": null(ref("InterpretationExtraction")),
    "source_variable_index": null(I), "resolved_owner_id": null(T), "state": enum("known", "unknown", "conflicting"), "diagnostics": AD})
D["CovarianceSourceVariable"] = obj({"index": I, "label": T, "unit": T, "description": T,
    **{k + "_witness": ref("WitnessRecord") for k in ("label", "unit", "description")},
    "native_registry_unit": null(rate), "exact_scale": null(ref("Rational")), "diagnostics": AD})
D["SourceModel"] = obj({"origin": enum("reported", "derived", "synthetic"), "variance_status": enum("known", "estimated", "unknown"),
    "model_kind": enum("none", "known_joint_normal_source_means")})
D["OwnerProjection"] = obj({"physical_observation_id": T, "source_variable_index": I,
    "roles": arr(enum(*roles), minItems=1, uniqueItems=True), "native_registry_unit": rate})
D["CovarianceExtraction"] = obj({"selection": cp(selection["properties"]["covariance"]["anyOf"][0]), "source_ref": T,
    "artifact_ref": null(T), "byte_sha256": null(SHA), "raw_text": null(T), "variables": arr(ref("CovarianceSourceVariable")),
    "matrix_tokens": null(arr(arr(T))), "exact_matrix": null(arr(arr(ref("Rational")))), "source_model": null(ref("SourceModel")),
    "bindings": obj({r: ref("CovarianceBindingExtraction") for r in roles}),
    "provided_owner_projection": arr(ref("OwnerProjection"), maxItems=4), "projected_exact_matrix": null(arr(arr(ref("Rational")))),
    "calculation_covariance": null({"oneOf": [ref("O_RoleCovariance"), ref("O_OwnerCovariance")]}),
    "source_validation": enum("valid", "invalid", "unassessed"),
    "projection_state": enum("available", "unavailable", "numeric_range", "precision_invalid", "source_invalid", "binding_unresolved", "binding_conflicting", "unsupported_format"),
    "diagnostics": AD})
D["ExactResponse"] = obj({"point": null(ref("Rational")), "lower": null(ref("Rational")), "upper": null(ref("Rational")),
    "relation": enum("eq", "lt", "le", "gt", "ge", "interval", "none"), "approximate": B, "unit": null(canonical)})
D["MeasurementReading"] = obj({"selection": null({"oneOf": [ref("TextMeasurement"),ref("GraphMeasurement")]}),
    "extraction": ref("MeasurementExtraction"), "operand_projection": obj({k: cp(D["O_Arm"]["properties"][k]) for k in
        ("value","threshold","relation","approximate","unit","status","origin","digitization_interval")}),
    "unit_semantics": null(ref("UnitCarrier")),"exact_response": null(ref("ExactResponse")),
    "source_observation_id": null(T),"graph_details": null(ref("GraphResult"))})
D["RetainedRepresentation"] = obj({"role": enum(*roles), "source_reading_id": null(T), "exact_domain": null(ref("ExactResponse"))})
D["ReconciliationRecord"] = obj({"physical_observation_id": null(T), "roles": arr(enum(*roles), minItems=1, uniqueItems=True),
    "readings": arr(ref("RetainedRepresentation"), minItems=1), "net_coefficient": {"type": "integer"},
    "method": enum("single_reading", "owner_cancellation", "exact_equivalence", "unresolved"),
    "state": enum("single", "exact_equivalent", "canceled_readings_retained", "unresolved_active_model", "conflicting_active_domains", "unresolved_science"),
    "canonical_source_reading_id": null(T), "qualifications": arr(enum("conditional_digitization_not_sampling", "canceled_numeric_conflict", "canceled_numeric_unavailable", "canceled_unit_unknown", "active_reconciliation_unimplemented"), uniqueItems=True), "diagnostics": AD})
D["RequestedModel"] = obj({k: ref("InterpretationExtraction") for k in ("variance_status", "model_kind")})
D["EffectiveModel"] = obj({"variance_status": enum("known", "estimated", "unknown"), "model_kind": enum("none", "known_joint_normal_source_means"), "diagnostics": AD})
D["DependencyRecord"] = obj({"reader_contract_version": {"const": "controlled_response_source_extraction_v2"},
    "calculator_contract_version": {"const": "controlled_response_owner_inputs_v2"},
    "expected_module_fingerprints": obj({k: SHA for k in [*old["types"]["DependencyRecord"]["expected_module_fingerprints"],
        "literature_controlled_response_inputs.py", "literature_controlled_response_v2_inputs.py",
        "literature_controlled_response_figure_inputs.py", "literature_controlled_response_owner_calculations.py"]})})
root = obj({"version": {"const": "controlled_response_source_extraction_v2"}, "selection": ref("Selection"),
    "sources": arr(ref("SourceRecord")), "images": arr(ref("ImageRecord")), "arms": obj({r: null(ref("ArmExtraction")) for r in roles}),
    "relationships": ref("RelationshipExtraction"), "covariance": null(ref("CovarianceExtraction")),
    "requested_model": ref("RequestedModel"), "effective_model": ref("EffectiveModel"), "calculation_inputs": ref("OwnerInputs"),
    "representation_reconciliations": arr(ref("ReconciliationRecord")), "diagnostics": AD, "implementation_dependencies": ref("DependencyRecord")})
root.update({"$defs": D, "$schema": "https://json-schema.org/draft/2020-12/schema"})
write("EXTRACTION_SCHEMA_V2_001.json", root)

# A distinct additive proposal addresses the demonstrated active-companion gap.
# Its base object is byte-identical in schema meaning to061; no role is reused
# as a numerical alternative. It is not a released/accepted scientific model.
companion = obj({"reading_key": T, "primary_role": enum(*roles), "reading": ref("Arm")})
selection3 = cp(selection)
selection3["properties"]["version"] = {"const": "controlled_response_source_selection_v3"}
selection3["properties"]["companion_readings"] = arr(companion)
selection3["required"].append("companion_readings")
assignment = obj({r: null(T) for r in roles})
selection3["properties"]["joint_reading_assignments"] = arr(obj({"assignment": assignment,
    "admissibility": obj({"value": enum("compatible", "unknown", "conflicting"), "witnesses": arr(ref("Witness"))})}))
selection3["required"].append("joint_reading_assignments")
write("COMPANION_SELECTION_SCHEMA_V3_PROPOSAL_001.json", selection3)
v3 = cp(root)
v3["$defs"]["Selection"] = embed(selection3, "C_", v3["$defs"])
v3["properties"]["version"] = {"const": "controlled_response_source_extraction_v3"}
v3["properties"]["companion_extractions"] = arr(obj({"reading_key": T, "primary_role": enum(*roles), "reading": ref("ArmExtraction")}))
v3["properties"]["calculation_inputs"] = null(ref("OwnerInputs"))
v3["properties"]["projection_status"] = enum("ready", "unresolved_active_reconciliation")
v3["$defs"]["ReadingAssignment"] = obj({r: null(T) for r in roles})
v3["properties"]["partial_calculation_inputs"] = null(ref("OwnerInputs"))
v3["properties"]["partial_projection_state"] = enum("not_required","ready","unsupported_origin_projection","unavailable_group_identity")
v3["properties"]["alternative_inputs"] = arr(obj({"reading_assignment": ref("ReadingAssignment"), "calculation_inputs": ref("OwnerInputs")}))
v3["required"] += ["companion_extractions", "projection_status", "alternative_inputs", "partial_calculation_inputs", "partial_projection_state"]
v3["$defs"]["DependencyRecord"]["properties"]["reader_contract_version"] = {"const": "controlled_response_source_extraction_v3"}
v3["$defs"]["RetainedRepresentation"]["properties"]["reading_key"] = null(T)
v3["$defs"]["RetainedRepresentation"]["required"].append("reading_key")
v3["$defs"]["DependencyRecord"]["properties"]["expected_module_fingerprints"]["properties"]["literature_controlled_response_v3_inputs.py"] = SHA
v3["$defs"]["DependencyRecord"]["properties"]["expected_module_fingerprints"]["required"].append("literature_controlled_response_v3_inputs.py")
write("COMPANION_EXTRACTION_SCHEMA_V3_PROPOSAL_001.json", v3)
components = list(sheet["properties"]["cells"]["properties"])
cell = cp(D["H_Cell"])
partial = obj({"version": {"const": "controlled_response_conditional_population_v3"},
    "projection_status": enum("ready", "unresolved_active_reconciliation"),
    "final_sheet": null(ref("OwnerSheet")),
    "partial_sheet": null(ref("OwnerSheet")),
    "unresolved_roles": arr(enum(*roles), uniqueItems=True),
    "component_dependencies": obj({c: obj({"scientific_roles": arr(enum(*roles),uniqueItems=True),
        "numeric_roles": arr(enum(*roles),uniqueItems=True),"covariance_owner_ids": arr(T,uniqueItems=True),
        "model_active_roles": arr(enum(*roles),uniqueItems=True)}) for c in components}),
    "alternatives": arr(obj({"reading_assignment": ref("ReadingAssignment"), "sheet": ref("OwnerSheet")})),
    "unaffected_cells": obj({c: null(ref("H_Cell")) for c in components}),
    "conditional_cells": arr(obj({"alternative_index": I, "component": enum(*components), "cell": ref("H_Cell")}))})
partial.update({"$defs": cp(v3["$defs"]), "$schema": "https://json-schema.org/draft/2020-12/schema"})
write("CONDITIONAL_POPULATION_SCHEMA_V3_PROPOSAL_001.json", partial)
write("API_001.json", {
    "status": "design_only_no_production_release",
    "shared_module": "gene_annotation_episode/literature_controlled_response_inputs.py",
    "shared_host_signatures": [
      "open_controlled_response_sources(arguments, *, read_source) -> SourceContext",
      "read_controlled_response_arm_science(context, selected_arm) -> ArmScience",
      "read_controlled_response_text_measurement(context, selected, *, endpoint) -> MeasurementReading",
      "finish_controlled_response_arm(context, arm_science, *, measurement) -> ArmExtraction",
      "finish_controlled_response_inputs(context, *, arms) -> SourceExtraction",
      "validate_controlled_response_saved_science(arguments, extraction, *, measurement_checks) -> SourceExtraction"],
    "v2_module": "gene_annotation_episode/literature_controlled_response_v2_inputs.py",
    "public_signatures": ["controlled_response_v2_arguments_schema() -> dict",
      "validate_controlled_response_v2_selection(arguments) -> dict",
      "read_controlled_response_v2_inputs(arguments, *, read_source) -> dict",
      "validate_controlled_response_v2_extraction(arguments, extraction) -> dict"],
    "callback": "read_source(source_ref: str, representation: Literal['original','text']) -> exactly {artifact_ref: nonempty str, content: built-in immutable bytes}",
    "host_measurement_check": "validate_measurement(selected, saved_measurement, *, source_records, image_records) -> MeasurementReading",
    "separate_calculator": "populate_controlled_response_owner(extraction['calculation_inputs']) -> controlled_response_owner_sheet_v2",
    "source_calls_calculator": False,
    "v3_proposal": "Separate four-function API with v3 names; not an overload of v1/v2; nullable calculation_inputs only in explicit unresolved v3 result",
})
print("Wrote five design declarations; no source reader or calculator executed.")
