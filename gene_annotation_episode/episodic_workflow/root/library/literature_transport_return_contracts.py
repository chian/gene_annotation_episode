"""Original pure schema construction; numerical and custody services remain separate."""
from gene_annotation_episode.domain import obj

COMPONENTS = ("substrate_test", "substrate_reference", "apparent_km",
              "test_saturation", "reference_saturation", "condition_response",
              "log_condition_response", "condition_response_variance",
              "condition_response_standard_uncertainty")
FORMULA_CODES = {name: "transport_" + name + "_v1" for name in COMPONENTS}
BINDINGS = {"reported_subject_ref": "reference", "analyte_ref": "term",
            "test_curve_ref": "reference", "reference_curve_ref": "reference",
            "km_curve_ref": "reference"}
REASONS = ("concentration_unreported", "concentration_inputs_unreported",
           "concentration_not_supplied", "concentration_inputs_not_supplied",
           "kinetic_curve_identity_not_supplied", "primitive_covariance_not_supplied",
           "primitive_measurement_identity_not_supplied",
           "positive_concentration_required", "kinetic_curve_identity_unreported",
           "different_kinetic_curves", "observation_model_unspecified",
           "primitive_covariance_unreported", "primitive_measurement_identity_unreported",
           "primitive_variance_status_unknown", "numerical_model_range")
CONDITIONS = ("same_kinetic_curve", "michaelis_menten_response", "first_order_covariance_propagation")
SOURCE_KINDS = ("primary_source", "retained_extraction", "graph_extraction", "synthetic_fixture")
UNCERTAINTY_KINDS = ("unspecified", "unreported", "not_supplied")


def transport_response_cells_schema():
    """Closed typed numerical rows; scientific operands and hashes stay saved."""
    reference = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    properties = {"sheet_ref": dict(reference), "evidence_source_ref": dict(reference),
        **{field: {**reference, "type": ["string", "null"]}
           for field in ("km_sheet_ref", "covariance_source_ref")},
        **{field: {"type": ["string", "null"], "format": "reference", "x-reference-namespace": namespace}
           for field, namespace in BINDINGS.items()},
        "component": {"type": "string", "enum": list(COMPONENTS),
            "description": "condition_response is test substrate saturation divided by reference substrate "
                "saturation under the same fitted kinetic curve. It can divide an appropriate source effect "
                "once as a conditional response correction; it is not a reliability grade."},
        "value": {"type": ["number", "null"]},
        "unit": {"type": "string", "enum": ["uM", "dimensionless", "dimensionless_squared"]},
        "status": {"type": "string", "enum": ["populated", "unavailable"]},
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "origin": {"type": "string", "enum": ["reported", "derived", "graph_derived", "synthetic"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]},
        "conditional_on": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": list(CONDITIONS)}},
        "variance_status": {"type": "string", "enum": ["known", "estimated", "unknown"]},
        "observation_model": {"type": "string", "enum": ["michaelis_menten", "unknown"]},
        "operand_source_kind": {"type": "string", "enum": list(SOURCE_KINDS)},
        "covariance_origin": {"type": ["string", "null"], "enum": [None, "reported", "derived", "synthetic"]},
        "reported_km_uncertainty_kind": {"type": "string", "enum": list(UNCERTAINTY_KINDS)},
        "evaluated_scope": {"type": "string", "enum": ["interpreted_source_kinetic_response"]}}
    return {"type": "array", "items": obj(properties), "x-source": "literature_transport_cells"}


