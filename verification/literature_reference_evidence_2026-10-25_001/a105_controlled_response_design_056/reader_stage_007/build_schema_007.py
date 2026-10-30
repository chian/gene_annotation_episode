"""Emit review-only schema/interface artifacts; not an installed reader."""
from copy import deepcopy
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from gene_annotation_episode.domain import REF
from gene_annotation_episode.literature_partner_defined_units import defined_rate_unit_schema


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def ref(name):
    return {"$ref": "#/$defs/" + name}


def array(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}


def nullable(value):
    return {"anyOf": [value, {"type": "null"}]}


def enum(values):
    return {"enum": list(values)}


TEXT = {"type": "string", "minLength": 1}
OFFSET = {"type": "integer", "minimum": 0}
ROLES = ("protein_condition1", "empty_condition1", "protein_condition0", "empty_condition0")
WITNESS_FIELDS = {"source_ref": deepcopy(REF), "representation": enum(("original", "text")),
    "start": OFFSET, "end": {"type": "integer", "minimum": 1}, "quote": TEXT}
defs = {"NativeTextWitness": obj(WITNESS_FIELDS),
    "TextWitness": obj({"kind": {"const": "text"}, **WITNESS_FIELDS}),
    "Box": {"type": "array", "minItems": 4, "maxItems": 4, "items": OFFSET}}
defs["ImageWitness"] = obj({"kind": {"const": "image"}, "image_id": TEXT,
    "region": ref("Box"), "quote": TEXT})
defs["Witness"] = {"oneOf": [ref("TextWitness"), ref("ImageWitness")]}
defs["NumberSelector"] = obj({"witness": ref("NativeTextWitness"),
    "number_start": OFFSET, "number_end": {"type": "integer", "minimum": 1}})
defs["UnitSelection"] = {"anyOf": [ref("NativeTextWitness"), defined_rate_unit_schema()]}


def interpretation(values):
    return obj({"value": enum(values), "witnesses": array(ref("Witness"))})


defs["Correspondence"] = interpretation(("same", "unknown", "conflicting"))
defs["Meaning"] = obj({"status": enum(("known", "unknown", "conflicting")),
    "label": nullable(TEXT), "witnesses": array(ref("Witness")),
    "canonical_witness": nullable(ref("Witness")), "canonical_correspondence": ref("Correspondence")})
defs["Literal"] = obj({"status": enum(("exact", "ambiguous", "unreadable", "conflicting")),
    "candidates": array(ref("NumberSelector")), "fragments": array(ref("Witness"))})
defs["AxisLiteral"] = obj({"status": enum(("exact", "ambiguous", "unreadable", "conflicting")),
    "candidates": array(ref("Witness")), "fragments": array(ref("Witness"))})
defs["Image"] = obj({"image_id": TEXT, "source_ref": deepcopy(REF),
    "original_source_ref": deepcopy(REF), "mapping": nullable(obj({"original_region": ref("Box"),
        "colour_conversion": enum(("preserve", "rgb"))}))})
defs["TextMeasurement"] = obj({"kind": {"const": "source_literal"},
    "literal": ref("Literal"), "unit": nullable(ref("UnitSelection"))})
defs["BarSelection"] = obj({
    "roi": obj({name: OFFSET for name in ("left", "top", "right", "bottom")}),
    "rgb_min": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 255}, "minItems": 3, "maxItems": 3},
    "rgb_max": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 255}, "minItems": 3, "maxItems": 3},
    "minimum_row_fraction": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
    "minimum_run_rows": {"type": "integer", "minimum": 1},
    "edge_tolerance_pixels": {"type": "number", "minimum": 0}})
defs["GraphMeasurement"] = obj({"kind": {"const": "linear_bar"}, "image_id": TEXT,
    "bar_selection": ref("BarSelection"), "axis": obj({
        "first": obj({"pixel": {"type": "number", "minimum": 0}, "tick": ref("AxisLiteral")}),
        "second": obj({"pixel": {"type": "number", "minimum": 0}, "tick": ref("AxisLiteral")}),
        "unit": ref("AxisLiteral")})})
defs["CISelector"] = obj({"witness": ref("NativeTextWitness"),
    **{name: OFFSET for name in ("lower_start", "lower_end", "upper_start", "upper_end")}})
defs["Uncertainty"] = obj({
    "statistic": interpretation(("sd", "sem", "ci", "unspecified", "unreported", "unknown", "conflicting")),
    "magnitude": nullable(ref("NumberSelector")), "interval": nullable(ref("CISelector")),
    "unit": nullable(ref("UnitSelection")),
    "unit_relationship": interpretation(("same_as_response", "explicit_unit", "unknown", "conflicting")),
    "confidence_level": nullable(ref("NativeTextWitness")), "count": nullable(ref("NumberSelector")),
    "repetition_basis": interpretation(("biological_preparations", "technical_measurements", "unspecified", "unknown", "conflicting")),
    "estimate_basis": interpretation(("fit_to_averaged_curve", "between_fitted_parameters", "unknown", "conflicting"))})
defs["Arm"] = obj({"source_kind": enum(("primary_source", "retained_extraction", "synthetic_fixture")),
    "context": obj({name: nullable(ref("Witness")) for name in
        ("subject", "organism", "genotype", "construct", "preparation", "experimental_system")}),
    "protein_arrangement": interpretation(("protein_present", "protein_free_control", "empty_vector_control", "other_specified", "unknown", "conflicting")),
    **{name: ref("Meaning") for name in ("subject_construct", "condition", "endpoint", "normalization", "physical_observation")},
    "intended_factor_level": nullable(ref("Witness")),
    "measurement": nullable({"oneOf": [ref("TextMeasurement"), ref("GraphMeasurement")]}),
    "reported_uncertainty": ref("Uncertainty")})
defs["Relationships"] = obj({"condition1_target": ref("Meaning"), "condition0_target": ref("Meaning"),
    "condition_levels_relation": interpretation(("same", "different", "unknown", "conflicting")),
    "subject_construct_across_conditions": interpretation(("same", "different", "unknown", "conflicting")),
    **{name: interpretation(("matched_condition_control", "shared_reference_assumption", "unknown", "conflicting"))
        for name in ("condition1_control_application", "condition0_control_application")},
    "control_reference_reuse": interpretation(("distinct_observations", "same_reference_with_stated_invariance", "unknown", "conflicting")),
    "nonintended_conditions": interpretation(("matched", "different", "unknown", "conflicting")),
    "intended_factor": nullable(ref("Witness"))})
defs["CovarianceBinding"] = obj({"variable_index": OFFSET, "label_witness": ref("NativeTextWitness"),
    "owner_witness": ref("Witness"), "correspondence": ref("Correspondence")})
selection = obj({"version": {"const": "controlled_response_source_selection_v1"},
    "source_ref": deepcopy(REF), "images": array(ref("Image")),
    "arms": obj({role: nullable(ref("Arm")) for role in ROLES}), "relationships": ref("Relationships"),
    "covariance": nullable(obj({"source_ref": deepcopy(REF),
        "bindings": obj({role: nullable(ref("CovarianceBinding")) for role in ROLES})})),
    "variance_status": interpretation(("known", "estimated", "unknown")),
    "model_kind": interpretation(("none", "known_joint_normal_source_means"))})
selection["$defs"] = defs
selection["$schema"] = "https://json-schema.org/draft/2020-12/schema"
covariance_source = obj({"version": {"const": "controlled_response_covariance_source_v1"},
    "variables": array(obj({"label": TEXT, "unit": TEXT, "description": TEXT}), 1),
    "covariance": array(array({"type": "number"}, 1), 1),
    "origin": enum(("reported", "derived", "synthetic")),
    "variance_status": enum(("known", "estimated", "unknown")),
    "model_kind": enum(("none", "known_joint_normal_source_means"))})
covariance_source["$schema"] = selection["$schema"]

# This is an exact closed field/type declaration for review, deliberately not
# a pretend deployed validator. Nested legacy/native records name their frozen
# versioned structures; the future dedicated tests must validate each relationship.
result = {
    "scope": "Proposed exact closed extraction interface; no implemented reader",
    "version": "controlled_response_source_extraction_v1",
    "root_fields": {
        "version": "constant controlled_response_source_extraction_v1",
        "selection": "exact unmodified selected request matching SELECTION_SCHEMA_007.json",
        "sources": "array SourceRecord", "images": "array frozen049 ImageRecord",
        "arms": {role: "null|ArmExtraction" for role in ROLES},
        "relationships": "RelationshipExtraction", "covariance": "null|CovarianceExtraction",
        "requested_model": "RequestedModel", "effective_model": "EffectiveModel",
        "calculation_inputs": "exact frozen controlled_response_inputs_v1, never selected arguments",
        "diagnostics": "array Diagnostic", "implementation_dependencies": "DependencyRecord"},
    "types": {
        "Diagnostic": {"code": "one finite diagnostic code", "field": "actual deterministic field path",
            "domain": ["source_representation", "source_binding", "reader_capability", "source_interpretation", "dependency"],
            "source_refs": "unique actual selected source references"},
        "SourceRecord": {"source_ref": "persistent reference", "representation": ["original", "text"],
            "artifact_ref": "null|string", "byte_sha256": "null|sha256", "state": ["available", "unavailable"],
            "diagnostics": "array Diagnostic"},
        "WitnessRecord": {"selection": "exact selected tagged Witness", "artifact_ref": "null|string",
            "byte_sha256": "null|sha256", "canonical_locator": "null|TextLocator|ImageLocator",
            "authentication": ["exact_utf8_byte_span", "image_bytes_and_geometry_only", "unavailable"],
            "attribution": ["literal_source_record", "investigating_episode_interpretation"],
            "diagnostics": "array Diagnostic"},
        "TextLocator": {"kind": "text", "source_ref": "persistent reference", "artifact_ref": "string",
            "byte_sha256": "sha256", "start": "UTF8 integer", "end": "UTF8 integer"},
        "ImageLocator": {"kind": "image", "original_source_ref": "persistent reference",
            "original_artifact_ref": "string", "original_byte_sha256": "sha256", "region": "mapped integer box"},
        "InterpretationExtraction": {"selection": "original finite interpretation",
            "witnesses": "array WitnessRecord", "effective_value": "original enum value or unknown/conflicting if dependency unresolved",
            "diagnostics": "array Diagnostic"},
        "MeaningExtraction": {"selection": "original Meaning", "witnesses": "array WitnessRecord",
            "canonical_witness": "null|WitnessRecord", "canonical_correspondence": "InterpretationExtraction",
            "resolved_state": ["known", "unknown", "conflicting"], "canonical_id": "null|generated meaning ID",
            "diagnostics": "array Diagnostic"},
        "NumberCandidate": {"selection": "original native NumberSelector", "witness": "WitnessRecord",
            "raw_expression": "null when dependency_unavailable; otherwise actual exact authenticated selected string", "native_value": "null|finite number",
            "relation": ["point", "lt", "le", "gt", "ge", "unresolved"], "approximate": "null|boolean",
            "source_locator": "null when dependency_unavailable; otherwise actual TextLocator", "status": ["parsed", "unsupported", "numeric_range", "dependency_unavailable"],
            "diagnostics": "array Diagnostic"},
        "UnitRecord": {"selection": "original nullable UnitSelection", "witness": "null|WitnessRecord",
            "raw_unit": "null|exact string", "canonical_unit": "null|rate canonical unit",
            "exact_scale": "null|Rational", "native_registry_unit": "null|RATE_UNITS key",
            "definition_witnesses": "null|exact source-defined bridge/clause/amount/amount_unit/time_unit/endpoint/endpoint_entity/definition_entity records",
            "status": ["supported", "unknown", "unsupported", "numeric_range", "dependency_unavailable", "endpoint_correspondence_unknown"],
            "diagnostics": "array Diagnostic"},
        "Rational": {"numerator": "signed integer decimal string", "denominator": "positive integer decimal string"},
        "CanonicalDisplay": {"value": "null|finite number", "threshold": "null|finite number", "unit": "null|canonical rate unit",
            "relation": ["eq", "lt", "le", "gt", "ge", "none"], "approximate": "boolean", "diagnostics": "array Diagnostic"},
        "MeasurementExtraction": {"selection": "original nullable measurement", "candidates": "array NumberCandidate",
            "fragments": "array WitnessRecord", "unit": "null|UnitRecord", "graph_witnesses": "array WitnessRecord",
            "reading_status": ["not_selected", "exact", "ambiguous", "unreadable", "conflicting", "unsupported", "graph_unimplemented", "dependency_unavailable"],
            "source_observation_id": "null|actual source token/recipe generated ID", "canonical_display": "CanonicalDisplay",
            "pixel_result": "null in first text/JSON stage", "diagnostics": "array Diagnostic"},
        "UncertaintyExtraction": {"selection": "original Uncertainty", "meanings": "exact statistic/unit_relationship/repetition_basis/estimate_basis InterpretationExtraction records",
            "magnitude": "null|NumberCandidate", "interval": "null|IntervalRecord", "unit": "null|UnitRecord",
            "effective_unit": "null|UnitRecord", "confidence_level": "null|ConfidenceRecord", "count": "null|CountRecord",
            "canonical": "UncertaintyCanonical", "diagnostics": "array Diagnostic"},
        "IntervalRecord": {"selection": "original CISelector", "witness": "WitnessRecord", "raw_values": "null|two exact strings",
            "values": "null|two finite native numbers", "status": ["parsed", "unsupported", "numeric_range", "dependency_unavailable"], "diagnostics": "array Diagnostic"},
        "ConfidenceRecord": {"selection": "original native text witness", "witness": "WitnessRecord", "value": "null|finite fraction strictly0..1",
            "status": ["parsed", "unsupported", "numeric_range", "dependency_unavailable"], "diagnostics": "array Diagnostic"},
        "CountRecord": {"selection": "original NumberSelector", "witness": "WitnessRecord",
            "reading": "null|exact released055 count reading (selector,raw_number,value,notation,relation,approximate,status,unavailable_reason)",
            "diagnostics": "array Diagnostic"},
        "UncertaintyCanonical": {"statistic": "finite selected statistic enum or conflicting", "magnitude": "null|finite nonnegative",
            "interval": "null|two finite canonical values", "confidence_level": "null|finite0..1", "count": "null|positive exact count only",
            "repetition_basis": "actual finite enum", "estimate_basis": "actual finite enum"},
        "ArmExtraction": {"selection": "original arm", "context": "exact six nullable WitnessRecord fields",
            "protein_arrangement": "InterpretationExtraction", "meanings": "exact five MeaningExtraction fields",
            "intended_factor_level": "null|WitnessRecord", "measurement": "MeasurementExtraction", "reported_uncertainty": "UncertaintyExtraction",
            "calculation_operand": "exact frozen nullable arm contract", "diagnostics": "array Diagnostic"},
        "RelationshipExtraction": {"condition1_target": "MeaningExtraction", "condition0_target": "MeaningExtraction",
            "condition_levels_relation": "InterpretationExtraction", "subject_construct_across_conditions": "InterpretationExtraction",
            "condition1_control_application": "InterpretationExtraction", "condition0_control_application": "InterpretationExtraction",
            "control_reference_reuse": "InterpretationExtraction", "nonintended_conditions": "InterpretationExtraction",
            "intended_factor": "null|WitnessRecord"},
        "CovarianceBindingExtraction": {"selection": "original nullable binding", "label_witness": "null|WitnessRecord",
            "owner_witness": "null|WitnessRecord", "correspondence": "null|InterpretationExtraction", "source_variable_index": "null|integer",
            "resolved_owner_id": "null|actual generated physical ID", "state": ["known", "unknown", "conflicting"], "diagnostics": "array Diagnostic"},
        "CovarianceSourceVariable": {"index": "actual zero-based integer", "label": "decoded string", "label_witness": "WitnessRecord",
            "unit": "decoded string", "unit_witness": "WitnessRecord", "description": "decoded source string", "description_witness": "WitnessRecord",
            "native_registry_unit": "null|RATE_UNITS key", "exact_scale": "null|Rational", "diagnostics": "array Diagnostic"},
        "CovarianceExtraction": {"selection": "original covariance nomination", "source_ref": "persistent reference", "artifact_ref": "null|string",
            "byte_sha256": "null|sha256", "raw_text": "null|actual UTF8 JSON source", "variables": "array CovarianceSourceVariable",
            "matrix_tokens": "null|full NxN exact source number token strings", "exact_matrix": "null|full NxN Rational records",
            "source_model": "null|literal actual origin/variance_status/model_kind", "bindings": {role: "CovarianceBindingExtraction" for role in ROLES},
            "projection_indices": "null|exact four source indices", "projected_exact_matrix": "null|4x4 Rational",
            "calculation_covariance": "null|exact frozen parsed covariance structure",
            "source_validation": ["valid", "invalid", "unassessed"],
            "projection_state": ["available", "unavailable", "numeric_range", "precision_invalid", "source_invalid", "binding_unresolved", "binding_conflicting", "unsupported_format"],
            "diagnostics": "array Diagnostic"},
        "RequestedModel": {"variance_status": "InterpretationExtraction", "model_kind": "InterpretationExtraction"},
        "EffectiveModel": {"variance_status": ["known", "estimated", "unknown"], "model_kind": ["none", "known_joint_normal_source_means"], "diagnostics": "array Diagnostic"},
        "DependencyRecord": {"reader_contract_version": "controlled_response_source_extraction_v1",
            "calculator_contract_version": "controlled_response_inputs_v1", "expected_module_fingerprints": "closed map of reviewed module names to expected sha256, not runtime file IO attestation"}},
    "diagnostic_codes": ["measurement_not_selected", "source_literal_unreadable", "source_literal_ambiguous", "source_literal_conflicting",
        "unsupported_complete_source_expression", "source_numeric_range", "numeric_projection_rounding", "source_rate_unit_unknown", "source_rate_unit_unsupported",
        "source_defined_unit_definition_not_selected", "unit_endpoint_correspondence_unknown", "custom_unit_projection_unrepresentable",
        "source_dependency_unavailable", "source_text_encoding_unsupported", "source_image_format_unsupported", "source_image_decode_failed",
        "source_uncertainty_meaning_conflict", "source_uncertainty_piece_unsupported", "source_uncertainty_unit_unknown", "source_uncertainty_unit_conflicting",
        "qualified_confidence_unsupported", "source_confidence_sentence_stop_unsupported", "unsupported_covariance_representation", "source_json_duplicate_key", "source_json_nonfinite",
        "source_covariance_shape_invalid", "source_covariance_asymmetric", "source_covariance_not_psd", "source_covariance_origin_invalid",
        "covariance_owner_unresolved", "covariance_owner_conflicting", "covariance_shared_values_conflicting", "covariance_shared_rows_conflicting",
        "source_covariance_unit_unsupported", "covariance_projection_numeric_range", "covariance_projection_precision_invalid",
        "variance_status_not_selected", "source_variance_status_unknown", "requested_source_variance_status_conflict",
        "normal_model_not_selected", "source_normal_model_unsupported", "source_model_witness_unavailable", "source_model_projection_rounding",
        "synthetic_covariance_with_reported_operands", "graph_rate_reader_unimplemented"],
    "structural_checks_beyond_schema": ["known/conflicting witness cardinality after actual canonical locator deduplication",
        "actual source roster preauthorization and all image ID references", "positive box ordering and actual crop/region identity",
        "complete scalar/unit token guards and exact source-defined endpoint associations", "literal candidate state/cardinality",
        "covariance exact NxN shape, numeric lexical validity, all full-matrix PSD and owner/model interpretation relationships",
        "covariance label nomination is exact corresponding structural JSON token, not only equal decoded label",
        "effective parsed inputs match frozen calculator contract; no calculator call inside reader"],
    "not_implemented": True}

result["semantic_conventions"] = {
    "numeric_projection_rounding": "Compare the exact source-decimal rational, with actual source unit factors, against Fraction(str(projected_float)) with actual frozen pure-unit factors; never Fraction.from_float. Preserve original lexemes and exact source rationals. Ordinary source0.1 versus float0.1 is equal; source0.10000000000000000001 versus float0.1 loses digits.",
    "saved_validation": "Saved consistency only; original authoritative runtime custody must bind selected request, admitted sources, operation and immutable extraction/output. Self-consistent hashes or quotes do not independently authenticate source evidence or authorize access."}


def finalize_result_interface():
    combined = {}
    for filename in ("BASELINE_007.json", "BASELINE_008.json"):
        combined.update(json.loads((HERE / filename).read_text())["files"])
    names = ("literature_assay_inputs.py", "literature_rate_native_inputs.py",
        "literature_partner_source_fields.py", "literature_partner_defined_units.py",
        "literature_kinetic_inputs.py", "literature_binding_visual_inputs.py",
        "literature_binding_reader.py", "literature_controlled_response_calculations.py")
    result["types"]["DependencyRecord"]["expected_module_fingerprints"] = {
        name: combined["gene_annotation_episode/" + name]["sha256"] for name in names}
    return result


def main():
    finalize_result_interface()
    for name, value in (("SELECTION_SCHEMA_007.json", selection),
                        ("COVARIANCE_SOURCE_SCHEMA_007.json", covariance_source),
                        ("RESULT_INTERFACE_007.json", result)):
        with (HERE / name).open("x") as stream:
            json.dump(value, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({"scope": "proposal only", "schemas_emitted": 3}))


if __name__ == "__main__":
    main()
