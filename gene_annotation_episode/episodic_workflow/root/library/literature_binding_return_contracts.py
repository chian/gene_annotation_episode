"""Original binding-family return contracts; no numerical or repository activation."""
from gene_annotation_episode.domain import obj

COMPONENTS = (
    "reference_parameter", "test_parameter", "reference_reported_spread",
    "test_reported_spread", "reference_relative_spread", "test_relative_spread",
    "native_parameter_ratio", "log_native_parameter_ratio",
    "source_profile_log_ratio", "source_signed_index",
)
REASONS = (
    "missing_reference_arm", "missing_test_arm", "conflicting_source_identity",
    "ambiguous_reference_arm", "ambiguous_test_arm", "source_measurement_unavailable",
    "reported_spread_requires_point_operand", "reported_spread_unavailable",
    "nonfinite_calculation", "calculation_underflow", "two_censored_operands_unsupported",
    "comparison_context_mismatch", "binding_observation_model_unimplemented",
)
PARAMETER_KINDS = ("ic50", "reported_hill_kd")
DESIGNS = ("equilibrium_competition", "direct_binding_isotherm", "other", "unknown", "conflicting")
ARRANGEMENTS = ("single_preparation", "separate_preparations", "protein_mixture", "unknown", "conflicting")
BINDINGS = ("subject_ref", "state_ref", "experiment_ref", "reference_ligand_ref", "test_ligand_ref")
FORMULA_CODES = {name: "binding_" + name + "_v1" for name in COMPONENTS}
def binding_cells_schema():
    """Closed numerical parent form; null statistical bounds retain their meaning."""
    reference = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    properties = {"sheet_ref": dict(reference), "evidence_source_ref": dict(reference),
        **{name: {"type": ["string", "null"], "format": "reference", "x-reference-namespace": "reference"}
           for name in BINDINGS},
        "component": {"type": "string", "enum": list(COMPONENTS)},
        "value": {"type": ["number", "null"]},
        "relation": {"type": "string", "enum": ["eq", "gt", "ge", "lt", "le", "unreported"]},
        "unit": {"type": "string", "enum": ["nM", "fraction", "dimensionless"]},
        "status": {"type": "string", "enum": ["populated", "reported_limit", "unavailable", "conflicting"]},
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "origin": {"type": "string", "enum": ["derived", "proposed"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]},
        "bound_kind": {"type": ["string", "null"], "enum": [None, "reported_limit_arithmetic"]},
        "confidence_bound": {"type": "null"}, "parameter_identification_bound": {"type": "null"},
        "parameter_kind": {"type": "string", "enum": list(PARAMETER_KINDS)},
        "uncertainty_basis": {"type": "string", "enum": ["fit_to_averaged_curve", "between_independent_fitted_parameters", "unknown"]},
        "minimum_experiment_count": {"type": ["integer", "null"], "minimum": 1},
        "independent_preparation_count": {"type": "null"},
        "source_origins": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": ["reported", "synthetic", "visual_transcription"]}},
        "design": {"type": "string", "enum": list(DESIGNS)},
        "protein_arrangement": {"type": "string", "enum": list(ARRANGEMENTS)},
        "interpretation_kind": {"type": "string", "enum": ["episode_source_interpretation"]}}
    # The common form language supports finite enums, while repository value
    # validation binds each formula to its actual saved component.
    return {"type": "array", "items": obj(properties), "x-source": "literature_binding_cells"}


