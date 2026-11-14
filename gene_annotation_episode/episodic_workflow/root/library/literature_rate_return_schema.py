"""Original source-rate numerical return schema; no storage or assessment."""

# Values are (physical dimension, multiplier into that dimension's base unit).
# Concentration/time and amount/time intentionally have different dimensions.
RATE_UNITS = {
    "umol/min": ("amount_rate", 1.0),
    "nmol/min": ("amount_rate", 0.001),
    "mmol/min": ("amount_rate", 1000.0),
    "uM/min": ("concentration_rate", 1.0),
    "nM/min": ("concentration_rate", 0.001),
    "per_min": ("turnover_rate", 1.0),
    "per_s": ("turnover_rate", 60.0),
    "umol/min/mg": ("specific_amount_rate", 1.0),
    "nmol/min/mg": ("specific_amount_rate", 0.001),
}
COMPONENTS = ("reference_rate", "test_rate", "rate_difference", "retained_fraction",
              "fractional_decrease", "reference_mean_se", "test_mean_se", "difference_se",
              "signed_profile_log_ratio", "source_signed_index")
UNAVAILABLE_REASONS = ("nonfinite_calculation", "missing_reference_arm", "missing_test_arm",
    "conflicting_source_identity", "ambiguous_reference_arm", "ambiguous_test_arm",
    "source_measurement_unavailable", "censored_measurement", "conflicting_measurement",
    "mean_uncertainty_unreported", "observation_model_unspecified", "measurement_count_unreported",
    "insufficient_measurement_count", "positive_sd_required", "zero_reference_rate",
    "dependence_unknown", "profile_requires_sample_sd", "numerical_model_range")
def rate_cells_schema():
    """Closed numerical parent form fragment; native units use declared codes."""
    reference = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    properties = {"sheet_ref": dict(reference), "evidence_source_ref": dict(reference),
        "component": {"type": "string", "enum": list(COMPONENTS)},
        "value": {"type": ["number", "null"]},
        "unit": {"type": ["string", "null"],
                 "enum": [*RATE_UNITS, "fraction", "dimensionless", None]},
        "status": {"type": "string", "enum": ["populated", "unavailable"]},
        "origin": {"type": "string", "enum": ["reported", "graph_derived", "synthetic", "derived", "proposed"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [*UNAVAILABLE_REASONS, None]},
        "conditional_on": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": ["independent_normal_groups", "independent_groups"]}}}
    for field, namespace in (("assayed_subject_ref", "reference"), ("experiment_ref", "reference"),
            ("reference_condition_ref", "context"), ("test_condition_ref", "context"),
            ("endpoint_ref", "term"), ("normalization_ref", "term")):
        properties[field] = {"type": ["string", "null"], "format": "reference",
                             "x-reference-namespace": namespace}
    return {"type": "array", "items": {"type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False}, "x-source": "literature_rate_cells"}


