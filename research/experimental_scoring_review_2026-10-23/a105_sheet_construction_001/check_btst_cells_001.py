"""Check proposed BtsT numerical cells; no production imports or state writes.

The 6.4 micromolar reported spread is NOT established as a standard uncertainty.
Its use as one is explicitly conditional arithmetic, not a source assertion.
"""

import json
import math


def correction(km, assay_concentration, reference_concentration):
    return reference_concentration * (km + assay_concentration) / (
        assay_concentration * (km + reference_concentration)
    )


def evaluate():
    km, reported_spread = 16.5, 6.4
    assay, reference = 40.0, 10.0
    f_reference = reference / (km + reference)
    f_assay = assay / (km + assay)
    value = correction(km, assay, reference)
    derivative = reference * (reference - assay) / (
        assay * (km + reference) ** 2
    )
    d_reference = -reference / (km + reference) ** 2
    d_assay = -assay / (km + assay) ** 2
    variance_reference = (d_reference * reported_spread) ** 2
    variance_assay = (d_assay * reported_spread) ** 2
    shared_covariance = d_reference * d_assay * reported_spread**2
    marginal_sum = (
        variance_reference / f_assay**2
        + f_reference**2 * variance_assay / f_assay**4
    )
    covariance_term = -2 * f_reference * shared_covariance / f_assay**3
    joint_variance = marginal_sum + covariance_term

    # Independent derivations: quotient Jacobian versus direct single-parameter
    # derivative, a numerical derivative, and invariance to concentration units.
    assert math.isclose(joint_variance, (derivative * reported_spread) ** 2,
                        rel_tol=1e-12)
    step = 1e-4
    finite_difference = (
        correction(km + step, assay, reference)
        - correction(km - step, assay, reference)
    ) / (2 * step)
    assert math.isclose(derivative, finite_difference, rel_tol=1e-9)
    assert math.isclose(value, correction(km * 1000, assay * 1000,
                                         reference * 1000), rel_tol=1e-15)
    assert math.isclose(value, f_reference / f_assay, rel_tol=1e-15)
    assert reference / assay < value < 1.0
    assert math.isclose(correction(km, assay, assay), 1.0)
    assert math.isclose(value * correction(km, reference, assay), 1.0)
    # Equality and saturation limits keep a concentration correction distinct
    # from a generic similarity score or a raw concentration ratio.
    assert math.isclose(correction(0.0, assay, reference), 1.0)
    assert math.isclose(correction(1e12, assay, reference), reference / assay,
                        rel_tol=1e-9)

    return {
        "source": "10.1128/JB.00599-17",
        "reported_Km_micromolar": km,
        "reported_plus_minus_micromolar": reported_spread,
        "reported_uncertainty_definition": None,
        "fractional_rate_at_10_micromolar": f_reference,
        "fractional_rate_at_40_micromolar": f_assay,
        "same_system_rate_correction_40_to_10": value,
        "same_system_rate_ratio_40_over_10": f_assay / f_reference,
        "derivative_per_micromolar": derivative,
        "sensitivity_without_coverage_claim": {
            "correction_at_Km_minus_reported_spread": correction(
                km - reported_spread, assay, reference),
            "correction_at_Km_plus_reported_spread": correction(
                km + reported_spread, assay, reference),
        },
        "CONDITIONAL_if_reported_spread_is_standard_uncertainty": {
            "shared_parameter_covariance": shared_covariance,
            "marginal_variance_sum": marginal_sum,
            "covariance_term": covariance_term,
            "joint_variance": joint_variance,
            "standard_uncertainty": math.sqrt(joint_variance),
            "incorrect_independence_standard_uncertainty": math.sqrt(marginal_sum),
        },
        "count_normalization_if_not_already_applied": {
            "cold_carryover_micromolar": 10000 / 200,
            "total_external_micromolar": 10000 / 200 + 4.7,
            "labelled_fraction": 4.7 / (10000 / 200 + 4.7),
            "total_over_labelled": (10000 / 200 + 4.7) / 4.7,
        },
        "checks_passed": True,
        "production_scoring_or_annotation_probability": False,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
