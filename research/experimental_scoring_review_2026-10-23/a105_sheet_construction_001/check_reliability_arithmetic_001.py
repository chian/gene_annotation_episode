"""Standalone research arithmetic; no production imports or scientific records.

All assay values are synthetic. This checks equations in the accompanying
proposal, not the scientific adequacy of its model or completion of A105.
Run with --output PATH to save a new immutable arithmetic report.
"""

import argparse
import json
import math
from pathlib import Path


def close(actual, expected, *, label):
    if not math.isclose(actual, expected, rel_tol=1e-8, abs_tol=1e-10):
        raise AssertionError(f"{label}: {actual!r} != {expected!r}")


def corrected_activity(values):
    net, contaminant, recovery, amount, comparison_test, comparison_reference = values
    return ((net - contaminant) * comparison_reference
            / (recovery * amount * comparison_test))


def normal_cdf(value):
    return 0.5 * math.erfc(-value / math.sqrt(2.0))


def log_ratio(value, variance, prediction, alternative):
    return ((value - alternative)**2 - (value - prediction)**2) / (2 * variance)


def paired_joint_log_ratio(values, variance, covariance, prediction, alternative):
    determinant = variance**2 - covariance**2
    if determinant <= 0:
        raise ValueError("Singular/dependent observations cannot be inverted this way")

    def quadratic(mean):
        first, second = (item - mean for item in values)
        return (variance * (first**2 + second**2)
                - 2 * covariance * first * second) / determinant

    return (quadratic(alternative) - quadratic(prediction)) / 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    inputs = [1.0, 0.15, 1.0, 1.0, 2.0, 1.6]
    uncertainties = [0.20, 0.15, 0.05, 0.10, 0.10, 0.10]
    activity = corrected_activity(inputs)
    gradient = [0.8, -0.8, -0.68, -0.68, -0.34, 0.425]
    for index, derivative in enumerate(gradient):
        above, below = inputs.copy(), inputs.copy()
        step = 1e-6
        above[index] += step
        below[index] -= step
        numerical_derivative = (corrected_activity(above) - corrected_activity(below)) / (2 * step)
        close(numerical_derivative, derivative, label=f"derivative {index}")

    propagated = [(derivative * uncertainty)**2
                  for derivative, uncertainty in zip(gradient, uncertainties)]
    components = {
        "sample_and_blank_measurement": propagated[0],
        "recovery_calibration": propagated[2],
        "condition_response_comparison": propagated[4] + propagated[5],
        "contaminating_activity": propagated[1],
        "assayed_protein_amount": propagated[3],
        "residual_between_preparations": 0.30**2 - 0.0275,
    }
    variance = sum(components.values())
    score = log_ratio(activity, variance, 1.0, 0.0)
    close(activity, 0.68, label="corrected activity")
    close(variance, 0.11124225, label="total variance")
    close(score, 1.6180902489836364, label="filled log ratio")

    # Every measured rate and uncertainty gets the same change of units.
    # Dimensionless evidence must remain invariant.
    close(log_ratio(activity * 1000, variance * 1000**2, 1000, 0),
          score, label="score invariant under activity unit conversion")

    # A larger known contaminating contribution changes the corrected activity;
    # it is not scored again as a second multiplier.
    higher_contamination = inputs.copy()
    higher_contamination[1] = 0.40
    close(corrected_activity(higher_contamination), 0.48,
          label="measured contamination changes the estimate")

    # Independent factors combine additively in log space. Shared errors reduce
    # the extra information of the second measurement in this example.
    paired_values = [0.68, 0.78]
    independent_sum = sum(log_ratio(value, variance, 1, 0) for value in paired_values)
    independent_joint = paired_joint_log_ratio(paired_values, variance, 0.0, 1, 0)
    close(independent_joint, independent_sum, label="independent joint likelihood")
    shared_covariance = variance - components["sample_and_blank_measurement"]
    shared_joint = paired_joint_log_ratio(paired_values, variance, shared_covariance, 1, 0)
    variance_of_shared_mean = (variance + shared_covariance) / 2
    close(shared_joint, log_ratio(sum(paired_values) / 2, variance_of_shared_mean, 1, 0),
          label="shared-error mean agrees with joint likelihood")
    if not 0 < shared_joint < independent_joint:
        raise AssertionError("Shared errors did not reduce additional information")
    try:
        paired_joint_log_ratio([activity, activity], variance, variance, 1, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("Exact dependency incorrectly accepted as invertible")

    # Censoring observes an event, not a measured rate of zero.
    nondetection = []
    for limit in [0.1, 2.0]:
        first = normal_cdf((limit - 1.0) / 0.2)
        second = normal_cdf(limit / 0.2)
        evidence = math.log(first) - math.log(second)
        nondetection.append({"detection_limit": limit, "standard_uncertainty": 0.2,
                             "likelihood_if_one": first, "likelihood_if_zero": second,
                             "log_evidence_ratio": evidence})
    close(nondetection[0]["log_evidence_ratio"], -12.223473320424421,
          label="sensitive nondetection")
    if abs(nondetection[1]["log_evidence_ratio"]) > 1e-6:
        raise AssertionError("Insensitive nondetection treated as strong contradiction")

    # Independent contrary evidence remains negative and offsets compatible
    # positive evidence. This does not pool incompatible endpoints.
    opposing_score = log_ratio(0.10, variance, 1, 0)
    if opposing_score >= 0 or score + opposing_score >= score:
        raise AssertionError("Contrary evidence failed to reduce the combined score")

    report = {
        "scope": "research arithmetic only; all assay inputs synthetic",
        "axis_complete": False,
        "unit": "product molecules per assayed-protein molecule per minute",
        "activity": activity,
        "attributable_activity_fraction": 0.85,
        "condition_response_ratio": 1.25,
        "condition_response_similarity_diagnostic": 0.8,
        "variance_components": components,
        "total_variance": variance,
        "standard_uncertainty": math.sqrt(variance),
        "experimental_precision": 1 / variance,
        "retained_precision_fraction": components["sample_and_blank_measurement"] / variance,
        "fixed_prediction": 1.0,
        "fixed_alternative": 0.0,
        "log_evidence_ratio": score,
        "evidence_ratio": math.exp(score),
        "two_independent_measurements_log_ratio": independent_joint,
        "two_shared_error_measurements_log_ratio": shared_joint,
        "shared_covariance": shared_covariance,
        "contrary_measurement_log_ratio": opposing_score,
        "combined_with_contrary_log_ratio": score + opposing_score,
        "nondetection_examples": nondetection,
        "checks": ["finite-difference derivatives", "filled arithmetic",
                   "unit invariance", "measured contamination correction",
                   "independent likelihood combination", "shared-error combination",
                   "singular covariance rejection", "censored nondetection",
                   "contrary evidence retained"],
        "unverified": ["scientific model adequacy", "variance-estimate uncertainty",
                       "non-Gaussian assay behavior", "source-to-target relevance",
                       "final annotation-axis conversion", "production integration"],
    }
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        with args.output.open("x") as destination:
            destination.write(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
