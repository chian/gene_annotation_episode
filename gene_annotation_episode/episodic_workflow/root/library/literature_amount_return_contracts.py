"""Original amount return declarations and schema; no service execution."""
from copy import deepcopy
import json
from gene_annotation_episode.domain import obj

AMOUNT_ROLES = ("target_mass_estimate", "total_protein_mass_estimate",
                "nominal_molecule_amount", "unknown", "conflicting")

AMOUNT_KINDS = ("measured", "estimated", "nominal", "unknown", "conflicting")

RELATIONSHIPS = ("supported", "unknown", "conflicting")

QUALIFICATIONS = ("reported_point", "source_qualified_approximate", "unknown", "conflicting")

UNCERTAINTY_KINDS = ("sd", "sem", "ci", "untyped", "unreported", "unknown", "conflicting")

COMPARISON_KINDS = ("stock_target_mass_estimate_over_total_mass_estimate",
                    "between_arm_nominal_molar_amount", "unknown", "conflicting")

STOCK_RELATIONSHIPS = ("same", "different", "not_applicable", "unknown", "conflicting")

COMPONENTS = ("numerator_amount", "denominator_amount", "amount_difference", "amount_ratio",
    "reciprocal_amount_ratio", "conditional_mass_denominator_factor", "amount_difference_variance",
    "amount_difference_standard_uncertainty", "amount_ratio_variance", "amount_ratio_standard_uncertainty",
    "reciprocal_amount_ratio_variance", "reciprocal_amount_ratio_standard_uncertainty")

REASONS = ("source_measurement_unavailable", "censored_measurement", "conflicting_measurement",
    "source_amount_unit_unreported", "unsupported_source_amount_unit",
    "amount_qualification_unknown", "amount_qualification_conflicting", "comparison_kind_unknown",
    "comparison_kind_conflicting", "pair_relationship_unknown", "pair_relationship_conflicting",
    "amount_basis_unknown", "amount_basis_conflicting", "amount_role_mismatch", "amount_kind_unresolved",
    "stock_relationship_unknown", "stock_relationship_conflicting", "different_stocks",
    "incompatible_amount_dimensions", "reused_source_observation", "zero_denominator_amount",
    "zero_numerator_amount", "mass_factor_not_applicable", "positive_mass_estimates_required",
    "amount_covariance_unreported", "numerical_model_range", "invalid_propagated_variance")



CONDITIONS = ("source_role_and_pair_interpretations", "linear_covariance_propagation",
    "first_order_covariance_propagation", "same_stock_rate_with_total_mass_denominator_required_before_application")

_QUANTITY_REF_FIELDS = ("subject_ref", "construct_ref", "preparation_ref", "stock_ref", "method_ref",
    "reported_basis_ref", "condition_ref", "measurement_ref", "physical_observation_ref", "reported_uncertainty_ref")



def amount_cells_schema():
    def reference(namespace, nullable=True):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference", "x-reference-namespace": namespace}
    quantity = obj({**{name: reference("context" if name == "condition_ref" else "reference") for name in _QUANTITY_REF_FIELDS},
        "amount_role": {"enum": list(AMOUNT_ROLES)}, "amount_kind": {"enum": list(AMOUNT_KINDS)},
        "basis_status": {"enum": list(RELATIONSHIPS)}, "qualification": {"enum": list(QUALIFICATIONS)},
        "approximate": {"type": "boolean"}, "reported_uncertainty_kind": {"enum": list(UNCERTAINTY_KINDS)}})
    schema = {"type": "array", "items": obj({"sheet_ref": reference("source", False),
        "evidence_source_ref": reference("source", False), "experiment_ref": reference("reference"),
        "intended_change_ref": reference("reference"), "covariance_source_ref": reference("source"),
        "component": {"enum": list(COMPONENTS)}, "value": {"type": ["number", "null"]},
        "threshold": {"type": ["number", "null"]}, "bound": {"enum": ["none", "lt", "le", "gt", "ge"]},
        "unit": {"enum": ["mg/ml", "uM", "mg2/ml2", "uM2", "dimensionless", None]},
        "status": {"enum": ["populated", "unavailable"]}, "origin": {"enum": ["reported", "derived", "synthetic"]},
        "unavailable_reason": {"enum": [*REASONS, None]},
        "conditional_on": {"type": "array", "uniqueItems": True, "items": {"enum": list(CONDITIONS)}},
        "approximate": {"type": "boolean"}, "evaluation_scope": {"const": "source_amount_comparison"},
        "comparison_kind": {"enum": list(COMPARISON_KINDS)}, "pair_relationship": {"enum": list(RELATIONSHIPS)},
        "stock_relationship": {"enum": list(STOCK_RELATIONSHIPS)}, "variance_status": {"enum": ["known", "estimated", "unknown"]},
        "covariance_origin": {"enum": ["reported", "derived", "synthetic", None]},
        "numerator": quantity, "denominator": json.loads(json.dumps(quantity)),
        "input_measurement_refs": {"type": "array", "uniqueItems": True, "items": reference("reference", False)},
        "mass_factor_applied_to_rate": {"const": False}}), "x-source": "literature_amount_cells"}
    # The application return boundary requires explicit types even for closed
    # enums/consts. All enum codes here are strings with declared nullable cases.
    def typed(node):
        if not isinstance(node, dict):
            return
        if "enum" in node and "type" not in node:
            node["type"] = ["string", "null"] if None in node["enum"] else "string"
        if "const" in node and "type" not in node:
            node["type"] = "boolean" if type(node["const"]) is bool else "string"
        for child in node.get("properties", {}).values():
            typed(child)
        if "items" in node:
            typed(node["items"])
    typed(schema)
    return schema



