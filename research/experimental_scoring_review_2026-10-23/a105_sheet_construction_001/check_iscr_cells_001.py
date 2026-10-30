"""Arithmetic for the proposed IscR cells, without production scoring.

Point-estimate-derived censoring limits are not confidence bounds. Variance
calculations using the quoted fit spreads remain explicitly conditional.
"""

import json
import math


def log_ratio(other, reference):
    return math.log(other / reference)


def evaluate():
    reference = 32.0
    limits = {
        "shuffled": 1000.0,
        "hya_7C_to_G": 510.0,
        "hya_8C_to_G": 740.0,
        "hya_8C_to_A": 1000.0,
        "hya_8C_to_T": 1000.0,
    }
    rows = []
    for competitor, lower in limits.items():
        ratio = lower / reference
        d = log_ratio(lower, reference)
        assert math.isclose(math.exp(d), ratio, rel_tol=1e-15)
        assert math.isclose(log_ratio(reference, lower), -d, rel_tol=1e-15)
        assert math.isclose(log_ratio(lower * 1000, reference * 1000), d,
                            rel_tol=1e-15)
        assert log_ratio(lower * 2, reference) > d
        rows.append({
            "competitor": competitor,
            "reported_midpoint_bound_nM": {"greater_than": lower},
            "ratio_bound_using_reference_point_estimate": {"greater_than": ratio},
            "log_ratio_bound_using_reference_point_estimate": {"greater_than": d},
            "confidence_coverage": None,
        })

    other, ref = 17.0, 11.0
    rel_other, rel_ref = 3 / other, 1 / ref
    marginal_sum = rel_other**2 + rel_ref**2
    correlation_coefficient = -2 * rel_other * rel_ref
    # Independently expand variance of a difference of two correlated log values.
    for rho in (-1.0, -0.5, 0.0, 0.5, 1.0):
        expanded = marginal_sum + rho * correlation_coefficient
        direct = rel_other**2 + rel_ref**2 - 2*rho*rel_other*rel_ref
        assert math.isclose(expanded, direct, abs_tol=1e-15)
        assert expanded >= 0.0
    assert math.isclose(marginal_sum + correlation_coefficient,
                        (rel_other-rel_ref)**2, rel_tol=1e-12)
    assert math.isclose(marginal_sum - correlation_coefficient,
                        (rel_other+rel_ref)**2, rel_tol=1e-12)

    return {
        "source": "10.1038/nsmb.2568",
        "wild_type_apo_reference_midpoint_nM": reference,
        "wild_type_apo_selectivity": rows,
        "apo_E43A_measured_point_contrast": {
            "ratio": other/ref,
            "log_ratio": log_ratio(other, ref),
        },
        "CONDITIONAL_spreads_are_standard_uncertainties": {
            "variance_intercept": marginal_sum,
            "coefficient_of_unknown_correlation": correlation_coefficient,
            "standard_uncertainty_at_assumed_zero_correlation": math.sqrt(marginal_sum),
            "variance_over_allowed_correlations": [
                (rel_other-rel_ref)**2, (rel_other+rel_ref)**2],
            "shared_wild_type_reference_log_variance": (2/reference)**2,
        },
        "checks_passed": True,
        "complete_annotation_score": None,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
