"""Original binding-family return contracts; no numerical or repository activation."""
from gene_annotation_episode.domain import obj
from . import literature_binding_return_contracts as native
from .literature_binding_return_contracts import BINDINGS, PARAMETER_KINDS, DESIGNS, ARRANGEMENTS

COMPONENTS = (
    "log_parameter_contrast", "log_contrast_noise_variance", "log_contrast_noise_sd",
    "source_profile_log_ratio", "source_signed_index",
)
REASONS = tuple(dict.fromkeys((*native.REASONS,
    "binding_sampling_model_unreported", "binding_sampling_model_not_supplied", "known_log_covariance_required",
    "covariance_status_unknown", "binding_censoring_mechanism_unreported",
    "two_censored_observations_unsupported", "numerical_model_range")))
CONDITIONAL_CODES = ("supplied_log_covariance", "known_normal_log_parameters",
                     "threshold_censoring_of_log_estimate")
FORMULA_CODES = {name: "binding_model_" + name + "_v1" for name in COMPONENTS}
def binding_model_cells_schema():
    """Closed parent rows omit host-only covariance, hashes and diagnostics."""
    reference = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    properties = {**{field: dict(reference) for field in (
        "sheet_ref", "evidence_source_ref", "original_evidence_source_ref")},
        "model_source_ref": {**reference, "type": ["string", "null"]},
        **{field: {"type": ["string", "null"], "format": "reference",
                  "x-reference-namespace": "reference"} for field in BINDINGS},
        "component": {"type": "string", "enum": list(COMPONENTS)},
        "value": {"type": ["number", "null"]},
        "relation": {"type": "string", "enum": ["eq", "gt", "ge", "lt", "le", "unreported"]},
        "unit": {"type": "string", "enum": ["dimensionless", "log_parameter_squared"]},
        "status": {"type": "string", "enum": ["populated", "reported_limit", "unavailable", "conflicting"]},
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "origin": {"type": "string", "enum": ["derived", "proposed"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]},
        "bound_kind": {"type": ["string", "null"], "enum": [None, "reported_limit_arithmetic"]},
        "confidence_bound": {"type": "null"}, "parameter_identification_bound": {"type": "null"},
        "conditional_on": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": list(CONDITIONAL_CODES)}},
        "parameter_kind": {"type": "string", "enum": list(PARAMETER_KINDS)},
        "contrast_meaning": {"type": "string", "enum": ["test_parameter_exceeds_reference"]},
        "evaluated_scope": {"type": "string", "enum": ["interpreted_source_parameter_contrast"]},
        "model_kind": {"type": "string", "enum": ["unreported", "not_supplied", "known_normal_log_parameters"]},
        "variance_status": {"type": "string", "enum": ["not_supplied", "known", "estimated", "unknown"]},
        "censoring_model": {"type": "string", "enum": ["not_supplied", "none", "threshold_of_log_estimate", "unknown"]},
        "model_origin": {"type": "string", "enum": ["not_supplied", "reported", "derived", "synthetic"]},
        "source_uncertainty_basis": {"type": "string", "enum": ["fit_to_averaged_curve", "between_independent_fitted_parameters", "unknown"]},
        "minimum_experiment_count": {"type": ["integer", "null"], "minimum": 1},
        "independent_preparation_count": {"type": "null"},
        "design": {"type": "string", "enum": list(DESIGNS)},
        "protein_arrangement": {"type": "string", "enum": list(ARRANGEMENTS)}}
    return {"type": "array", "items": obj(properties), "x-source": "literature_binding_model_cells"}


