"""Original optical return declarations and schema; no service execution."""
from copy import deepcopy
import json
from gene_annotation_episode.domain import obj

INTERPRETATIONS = {
    "signal_kind": ("absorbance_slope", "absorbance_difference", "static_absorbance", "unknown"),
    "relation": ("applicable_extinction_relation", "not_applicable", "unknown", "conflicting"),
    "blank_role": ("matched_no_reaction_background", "condition_reference", "component_omission", "unknown", "conflicting"),
    "same_endpoint": ("same", "different", "unknown"),
    "matched_window": ("same", "different", "unknown"),
    "rate_window": ("source_supported_rate_interval", "interval_mean_only", "static_only", "unknown"),
}

LITERAL_FIELDS = ("molecule", "construct", "preparation", "condition", "measured_entity")

PRIMITIVE_ORDER = ("sample_slope", "blank_slope", "epsilon", "path_length")

QUALIFICATIONS = ("reported_point", "source_qualified_approximate", "unknown", "conflicting")

SOURCE_KINDS = ("primary_source", "retained_extraction", "synthetic_fixture")

COMPONENTS = ("net_rate", "variance_net_rate")

EVALUATION_SCOPE = "source_nadh_depletion_endpoint"

FORMULA_CODES = {"net_rate": "nadh_extinction_net_rate", "variance_net_rate": "first_order_nadh_extinction_variance"}

REASONS = ("missing_sample_slope", "missing_blank_slope", "missing_epsilon", "missing_path_length",
    "optical_relation_unknown", "optical_relation_conflicting", "optical_relation_not_applicable",
    "blank_role_unresolved", "blank_role_not_background", "endpoint_mismatch_or_unknown",
    "window_mismatch_or_unknown", "rate_interval_unestablished", "covariance_unreported",
    "covariance_status_unknown", "numerical_model_range", "invalid_propagated_variance")

INPUT_REASONS = ("source_measurement_unreported", "source_optical_unit_unreported",
    "unsupported_source_optical_unit", "censored_source_operand", "approximate_source_operand",
    "source_operand_qualification_unknown", "source_operand_qualification_conflicting",
    "optical_signal_not_slope", "optical_signal_kind_unknown", "optical_signal_unit_mismatch")

CONDITIONS = ("source_optical_relationship_assignments", "first_order_covariance_propagation")

ORIGINS = ("reported", "derived", "synthetic")

_OPERAND_REFS = ("measurement_ref", "physical_observation_ref", "semantic_owner_ref", "local_reuse_ref",
    "condition_ref", "measured_entity_ref", "interval_ref")

def optical_cells_schema():
    def enum(values, nullable=False):
        return {"type": ["string", "null"] if nullable else "string", "enum": [*values, None] if nullable else list(values)}
    def ref(namespace="reference", nullable=True):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference", "x-reference-namespace": namespace}
    def refs():
        return {"type": "array", "uniqueItems": True, "items": ref(nullable=False)}
    context = {name: obj({"ref": ref("context" if name == "condition" else "reference"),
        "unavailable_reason": enum(["source_context_unreported"], True)}) for name in LITERAL_FIELDS}
    operand = obj({**{name: ref("context" if name == "condition_ref" else "reference") for name in _OPERAND_REFS},
        "measurement_source_ref": ref("source"),
        "qualification": enum(QUALIFICATIONS), "approximate": {"type": ["boolean", "null"]},
        "observed_relation": enum(["point", "lt", "le", "gt", "ge"], True),
        "observation_status": enum(["observed", "censored", "unavailable", "unreported"]),
        "source_origin": enum(ORIGINS, True), "converted_origin": enum(ORIGINS, True),
        "canonical_unit": enum(["absorbance/min", "absorbance", "mM_inverse_cm_inverse", "cm", "nm"], True),
        "input_status": enum(["available", "unavailable", "context_only"]),
        "input_unavailable_reasons": {"type": "array", "uniqueItems": True, "items": enum(INPUT_REASONS)}})
    return {"type": "array", "x-source": "literature_optical_cells", "items": obj({
        "sheet_ref": ref("source", False), "evidence_source_ref": ref("source", False),
        "component": enum(COMPONENTS), "value": {"type": ["number", "null"]}, "unit": enum(["uM/min", "uM2/min2"]),
        "status": enum(["populated", "unavailable"]), "origin": enum(["derived"]),
        "unavailable_reason": enum(REASONS, True), "formula_code": enum(FORMULA_CODES.values()),
        "conditional_on": {"type": "array", "uniqueItems": True, "items": enum(CONDITIONS)},
        "evaluation_scope": enum([EVALUATION_SCOPE]), "endpoint_kind": enum(["NADH_depletion"]),
        "endpoint_assignment": enum(["conditional_on_selected_extinction_relation"]),
        "source_kind": enum(SOURCE_KINDS), "source_origin": enum(ORIGINS), "context": obj(context),
        "interpretations": obj({name: obj({"value": enum(values), "witness_refs": refs()}) for name, values in INTERPRETATIONS.items()}),
        "covariance": obj({"source_ref": ref("source"), "binding_ref": ref(), "status": enum(["known", "estimated", "unknown"]),
            "origin": enum(ORIGINS, True), "unavailable_reason": enum(["covariance_unreported", "covariance_status_unknown"], True)}),
        "operands": obj({name: deepcopy(operand) for name in (*PRIMITIVE_ORDER, "wavelength_context")})})}



