"""Original binding-family return contracts; no numerical or repository activation."""
from gene_annotation_episode.domain import obj
from .literature_binding_interaction_model_metadata import COMPONENTS, FORMULA_CODES, VIEW
from .literature_binding_interaction_return_contracts import binding_interaction_cells_schema, CALCULATION_REASONS, ROLES, UNCERTAINTY_PARTIAL_CODES

REASONS = (*CALCULATION_REASONS, "observation_model_missing", "covariance_status_unknown",
    "variance_representation_range", "censored_joint_likelihood_unimplemented", "covariance_estimated_not_known",
    "normal_log_observation_model_unspecified", "zero_interaction_variance",
    "profile_log_ratio_representation_range", "signed_index_representation_range",
    "common_parameter_kind_unknown", "common_parameter_kind_conflicting", "common_parameter_kind_source_unavailable")
QUALIFICATIONS = (
    "dependent_representations", "reported_parameter_not_intrinsic_affinity",
    "physical_owners_do_not_establish_independence", "common_conditions_claim_conflicts_with_canonical_ids",
    "signed_index_rounded_endpoint_not_certainty", "printed_limits_are_not_parameter_or_confidence_bounds",
    "censored_joint_likelihood_unimplemented", "censor_reporting_event_unknown",
    *("common_conditions_" + status for status in ("matched", "not_matched", "unknown", "conflicting")),
    *(code + ":" + role for code in UNCERTAINTY_PARTIAL_CODES for role in ROLES),
    *("canonical_" + field + suffix for field in ("readout", "normalization", "preparation", "experiment", "conditions", "tracer")
        for suffix in ("_partly_unknown", "_differs")),
)
def binding_interaction_model_cells_schema():
    schema = binding_interaction_cells_schema()
    schema["x-source"] = "literature_binding_interaction_model_cells"
    fields = schema["items"]["properties"]
    def enum(values):
        return {"type": "string", "enum": list(values)}
    def ref(namespace, nullable=False):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference", "x-reference-namespace": namespace}
    fields.update({"component": enum(COMPONENTS), "formula_code": enum(FORMULA_CODES.values()),
        "unit": enum(["dimensionless", "dimensionless_squared"]), "origin": enum(["derived"]),
        "status": enum(["populated", "unavailable"]), "relation": enum(["eq", "none"]),
        "threshold": {"type": "null"}, "bound_kind": {"type": "null"},
        "unavailable_reason": {"type": ["string", "null"], "enum": [*REASONS, None]},
        "calculation_unavailable_reason": {"type": ["string", "null"], "enum": [*REASONS, None]},
        "view": enum([VIEW]), "binding_interaction_sheet_ref": ref("source"), "model_source_ref": ref("source", True),
        "model_support_refs": {"type": "array", "items": ref("reference")},
        "model_support_locations": {"type": "array", "items": obj({"kind": enum(["utf8_span"]),
            "source_ref": ref("source"), "artifact_ref": ref("artifact"),
            "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1}})},
        "model_input_status": enum(["supplied", "not_supplied", "supplied_native_inputs_unavailable"]),
        "model_reader_capability": enum(["implemented"]),
        "variance_status": enum(["known", "estimated", "unknown", "not_supplied"]),
        "distribution": enum(["normal", "unspecified", "not_supplied"]),
        "log_basis": enum(["natural_log_nM", "not_supplied"]),
        "reporting_event": enum(["unknown", "source_defined", "not_supplied"]),
        "source_kind": enum(["synthetic_fixture", "primary_source"]),
        "qualifications": {"type": "array", "uniqueItems": True, "items": enum(QUALIFICATIONS)},
        "contrast_meaning": enum(["reference_form_log_ligand_ratio_minus_test_form_log_ligand_ratio"])})
    schema["items"]["required"] = list(fields)
    return schema


