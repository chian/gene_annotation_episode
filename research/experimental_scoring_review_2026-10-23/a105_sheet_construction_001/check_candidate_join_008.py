"""Check the synthetic composition in A105_CANDIDATE_SCORING_REVIEW_008.md.

Research arithmetic only: no production imports, data changes or adopted policy.
Inputs are reconstructed and compared with previously saved exact calculations.
"""

from fractions import Fraction
import json
import math
from pathlib import Path

import numpy as np


def main():
    directory = Path(__file__).resolve().parent
    review = directory.parent
    source_path = directory / "parent_joined_check_003.json"
    specificity_path = review / "a105_calibrated_contract_007/ARITHMETIC_RESULTS_001.json"
    source = json.loads(source_path.read_text())
    specificity = json.loads(specificity_path.read_text())
    checks = {}

    def equal(name, actual, expected):
        assert math.isclose(actual, expected, rel_tol=2e-12, abs_tol=2e-14), (
            name, actual, expected
        )
        checks[name] = True

    activity = (Fraction("1.20") - Fraction("0.20") - Fraction("0.15")) / Fraction("1.25")
    variance_terms = [Fraction(x) for x in (
        ".0256", ".001156", ".00296225", ".0144", ".004624", ".0625"
    )]
    variance = sum(variance_terms)
    source_separation = activity ** 2 / (2 * variance)
    source_index = math.tanh(float(source_separation) / 2)
    correspondence_components = {
        "compatible_raw_sequence_scores": float(Fraction(480, 620)),
        "directional_structure_minimum": min(.90, .85),
        "predefined_observed_sites": 8 / 10,
        "eligible_placement_replicates": 85 / 100,
        "declared_system_distance": math.exp(-.5 * (49 / 100 + .25)),
    }
    correspondence = math.fsum(correspondence_components.values()) / 5
    activity_index = source_index * correspondence
    equal("activity", float(activity), .68)
    equal("variance", float(variance), .11124225)
    equal("source_index_matches_saved_calculation", source_index, source["source_B"]["value"])
    equal("activity_index_matches_saved_calculation", activity_index, source["arithmetic_D"]["value"])

    values = np.array([.8, .6, .9])
    covariance = np.array([[.230, .115, .060], [.115, .300, .085], [.060, .085, .400]])
    ones = np.ones(3)
    precision_times_one = np.linalg.solve(covariance, ones)
    pooled_variance = 1 / (ones @ precision_times_one)
    weights = pooled_variance * precision_times_one
    pooled_effect = float(weights @ values)
    specificity_separation = pooled_effect * abs(pooled_effect) / (2 * pooled_variance)
    specificity_index = math.tanh(specificity_separation / 2)
    for name, actual, expected in (
        ("mapped_effect", pooled_effect, specificity["pool"]["theta_hat"]),
        ("mapped_variance", pooled_variance, specificity["pool"]["variance_V"]),
        ("mapped_separation", specificity_separation, specificity["pool"]["S_nats"]),
        ("mapped_index", specificity_index, specificity["pool"]["B"]),
    ):
        equal(name + "_matches_saved_calculation", actual, expected)

    # The current candidate explicitly asserts both statements. These two
    # calculations are not asserted to be independent evidence or a joint fit.
    signed_axis = min(activity_index, specificity_index)
    coordinate = max(0.0, signed_axis)
    equal("candidate_conjunction", coordinate, source["arithmetic_D"]["value"])
    equal("duplicate_activity_statement_invariance", min(activity_index, activity_index, specificity_index), signed_axis)
    equal("duplicate_specificity_statement_invariance", min(activity_index, specificity_index, specificity_index), signed_axis)
    equal("activity_rate_unit_change_invariance", (1000 * float(activity)) ** 2 / (2 * 1000 ** 2 * float(variance)), float(source_separation))

    result = {
        "synthetic": True,
        "policy_status": "proposal_not_adopted",
        "scope": "same invented target T and reference condition C, explicitly stipulated here",
        "input_artifacts": [str(source_path.relative_to(review)), str(specificity_path.relative_to(review))],
        "activity": {
            "corrected_rate_per_minute": float(activity),
            "variance_per_minute_squared": float(variance),
            "source_profile_separation": float(source_separation),
            "source_index": source_index,
            "correspondence_components": correspondence_components,
            "declared_equal_family_mean": correspondence,
            "target_activity_index": activity_index,
        },
        "specificity": {
            "mapped_log_ratio_estimates": values.tolist(),
            "joint_covariance": covariance.tolist(),
            "pooled_effect": pooled_effect,
            "pooled_variance": float(pooled_variance),
            "profile_separation": float(specificity_separation),
            "target_specificity_index": specificity_index,
        },
        "candidate": {
            "expression": {"all_of": ["activity_A_under_C", "activity_A_exceeds_B_under_C"]},
            "reducer": "minimum_of_signed_indexes_then_positive_part",
            "signed_axis_index": signed_axis,
            "coordinate": coordinate,
            "coordinate_bounds": [coordinate, coordinate],
            "status": "complete_synthetic_conventional_point",
            "full_joint_profile_separation": None,
            "independent_experiment_count": None,
        },
        "checks": checks,
        "limits": [
            "No biological source-to-target fit is supplied by this synthetic composition.",
            "The two fixture calculations are not counted as additional experiments.",
            "Minimum is a proposed assertion-combination convention, not joint statistical inference.",
            "A105 and all ten sheets remain unfinished; this does not implement a reader or scorer.",
        ],
    }
    output = directory / "candidate_join_parent_arithmetic_008.json"
    # Never overwrite a permanent result. A repeated verification prints only.
    if not output.exists():
        output.write_text(json.dumps(result, indent=2) + "\n")
    else:
        assert json.loads(output.read_text()) == result
    print(json.dumps({"checks_passed": len(checks), "candidate_coordinate": coordinate, "result_file": str(output)}, indent=2))


if __name__ == "__main__":
    main()
