"""Research arithmetic for an unadopted A105 contribution proposal.

All examples are synthetic or reuse explicitly synthetic values from the supplied
research proposals. No production imports, readers, scientific data, or runs.
The output path is opened exclusively to preserve prior records.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy import optimize, stats


def close(actual, expected, label, atol=1e-9):
    if not math.isclose(float(actual), float(expected), rel_tol=1e-8, abs_tol=atol):
        raise AssertionError(f"{label}: {actual!r} != {expected!r}")


def signed_normal_profile(estimate, variance):
    return math.copysign(estimate * estimate / (2 * variance), estimate)


def nonnegative_normal_profile(estimate, variance):
    return max(0.0, estimate) ** 2 / (2 * variance)


def bounded_profile(score):
    return math.tanh(score / 2)


def paired_normal_profile(values):
    values = np.asarray(values, dtype=float)
    n = values.size
    if n < 2:
        raise ValueError("Unknown-variance normal profile requires residual data")
    estimate = float(values.mean())
    sd = float(values.std(ddof=1))
    se = sd / math.sqrt(n)
    if se <= 0:
        raise ValueError("Zero observed spread is not demonstrated zero uncertainty")
    t_stat = estimate / se
    score = math.copysign(n / 2 * math.log1p(t_stat**2 / (n - 1)), estimate)
    # Direct maximized normal likelihood from two residual sums of squares.
    rss_fit = float(np.square(values - estimate).sum())
    rss_zero = float(np.square(values).sum())
    direct = math.copysign(n / 2 * math.log(rss_zero / rss_fit), estimate)
    close(score, direct, "profile t formula versus residual likelihood")
    return {
        "n_independent_preparations": n,
        "mean": estimate,
        "sample_sd": sd,
        "standard_error": se,
        "t": t_stat,
        "df": n - 1,
        "two_sided_p": float(2 * stats.t.sf(abs(t_stat), n - 1)),
        "profile_log_ratio": score,
        "bounded_profile_contrast": bounded_profile(score),
    }


def common_effect(values, covariance):
    values = np.asarray(values, dtype=float)
    covariance = np.asarray(covariance, dtype=float)
    if np.linalg.eigvalsh(covariance).min() <= 0:
        raise ValueError("Duplicates/dependence need a reduced observation basis")
    ones = np.ones(values.size)
    precision_sum = float(ones @ np.linalg.solve(covariance, ones))
    estimate = float(ones @ np.linalg.solve(covariance, values) / precision_sum)
    variance = 1 / precision_sum
    residual = values - estimate
    q = float(residual @ np.linalg.solve(covariance, residual))
    score = signed_normal_profile(estimate, variance)
    return {
        "common_effect": estimate,
        "variance_of_common_effect": variance,
        "profile_log_ratio": score,
        "bounded_profile_contrast": bounded_profile(score),
        "heterogeneity_Q": q,
        "heterogeneity_df_if_common_normal_model": values.size - 1,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    effect = 0.68
    variance = 0.11124225
    se = math.sqrt(variance)
    z = effect / se
    s_normal = signed_normal_profile(effect, variance)
    close(s_normal, z * z / 2, "normal profile versus squared standardized contrast")
    close(signed_normal_profile(effect * 1000, variance * 1000**2),
          s_normal, "activity unit invariance")
    close(signed_normal_profile(-effect, variance), -s_normal, "signed reversal")
    close(nonnegative_normal_profile(-effect, variance), 0, "nonnegative activity boundary")
    close(bounded_profile(-s_normal), -bounded_profile(s_normal), "bounded reversal")
    likelihood_ratio = math.exp(s_normal)
    close(bounded_profile(s_normal), (likelihood_ratio - 1) / (likelihood_ratio + 1),
          "bounded normalized likelihood contrast")

    original_a = np.array([1.6, 1.8, 2.0])
    original_b = np.array([0.2, 0.3, 0.4])
    activity = paired_normal_profile(original_a)
    preference = paired_normal_profile(original_a - original_b)
    reverse_preference = paired_normal_profile(original_b - original_a)
    close(reverse_preference["profile_log_ratio"], -preference["profile_log_ratio"],
          "opposite finite-sample preference")
    ratio_of_means = float(original_a.mean() / original_b.mean())
    log_ratios = paired_normal_profile(np.log(original_a / original_b))
    close(ratio_of_means, 6, "ratio of arithmetic means")
    geometric_ratio = math.exp(log_ratios["mean"])
    close(geometric_ratio, 240 ** (1 / 3), "geometric paired preference")

    # Known-variance numbers for the same observed t are a different model.
    # A Student t pivot is not substituted into a known-variance z formula.
    same_standardized_value_unknown_n3 = 1.5 * math.log1p(z*z / 2)

    shared = variance - 0.0256
    independent = common_effect([0.68, 0.78], [[variance, 0], [0, variance]])
    shared_result = common_effect([0.68, 0.78], [[variance, shared], [shared, variance]])
    close(shared_result["variance_of_common_effect"], (variance + shared) / 2,
          "shared-control variance of mean")
    if not 0 < shared_result["profile_log_ratio"] < independent["profile_log_ratio"]:
        raise AssertionError("Shared uncertainty did not reduce the extra information")
    try:
        common_effect([effect, effect], [[variance, variance], [variance, variance]])
    except ValueError:
        duplicate_status = "represented once; singular duplicate covariance was not inverted"
    else:
        raise AssertionError("Duplicate was incorrectly treated as independent evidence")

    contradiction = common_effect([0.68, -0.68], [[variance, 0], [0, variance]])
    close(contradiction["common_effect"], 0, "opposite signed contrasts average to zero")
    close(contradiction["profile_log_ratio"], 0, "opposite contrasts common-direction score")
    if contradiction["heterogeneity_Q"] <= 0:
        raise AssertionError("Conflicting observations lost their inconsistency")

    # Independent second measurement is an event Y < limit, not a rate of zero.
    limit = 0.1
    censor_noise = 0.2

    def detected_plus_censored_log_likelihood(mu):
        return -0.5 * (effect - mu)**2 / variance + float(stats.norm.logcdf((limit - mu) / censor_noise))

    optimized = optimize.minimize_scalar(
        lambda mu: -detected_plus_censored_log_likelihood(mu),
        bounds=(0, 3), method="bounded", options={"xatol": 1e-13},
    )
    fitted = float(optimized.x)
    joint_profile = detected_plus_censored_log_likelihood(fitted) - detected_plus_censored_log_likelihood(0)
    if not 0 < joint_profile < s_normal:
        raise AssertionError("Censored nondetection failed to reduce presence support")
    normal_pdf_over_cdf = math.exp(stats.norm.logpdf((limit-fitted)/censor_noise)
                                 - stats.norm.logcdf((limit-fitted)/censor_noise))
    derivative = (effect - fitted) / variance - normal_pdf_over_cdf / censor_noise
    close(derivative, 0, "censored likelihood optimum derivative", atol=1e-6)
    upper_95 = limit + float(stats.norm.ppf(0.95)) * censor_noise
    # This is a bound from one censored observation, not a fitted point estimate.
    close(float(stats.norm.cdf((limit - upper_95) / censor_noise)), 0.05,
          "nondetection upper-bound inversion")

    # Unknown residual biases remain explicit operands, not zero-valued variances.
    cmp_bias = [0.0, 0.1]
    isolation_bias = [0.0, 0.2]
    total_bias = [cmp_bias[0] + isolation_bias[0], cmp_bias[1] + isolation_bias[1]]
    effect_interval = [effect - total_bias[1], effect - total_bias[0]]
    score_interval = [signed_normal_profile(value, variance) for value in effect_interval]
    bounded_interval = [bounded_profile(value) for value in score_interval]

    # Joint positivity of two independent, signed necessary contrasts.
    # The competing region is the union in which at least one contrast is <=0.
    # For positive estimates, its best fit moves only the nearest standardized
    # boundary to zero. This is not a sum of two independent supports for one claim.
    joint_positive = [2.0, 3.0]
    joint_positive_score = min(value*value/2 for value in joint_positive)
    joint_violation = [-2.0, 3.0]
    joint_violation_score = -sum(min(0.0, value)**2/2 for value in joint_violation)
    close(joint_positive_score, 2, "two required directions positive")
    close(joint_violation_score, -2, "one required direction reversed")

    report = {
        "status": "unadopted research arithmetic; no evidence axis completed",
        "input_origin": "all values synthetic; source references are listed in the proposal",
        "known_variance_parent_example": {
            "effect": effect, "variance": variance, "standard_error": se, "z": z,
            "two_sided_normal_p": float(2 * stats.norm.sf(abs(z))),
            "profile_log_ratio": s_normal,
            "bounded_profile_contrast": bounded_profile(s_normal),
            "same_t_with_n3_unknown_common_variance_profile": same_standardized_value_unknown_n3,
            "same_t_with_n3_unknown_common_variance_bounded": bounded_profile(same_standardized_value_unknown_n3),
            "negative_estimate_nonnegative_activity_score": nonnegative_normal_profile(-effect, variance),
        },
        "three_preparation_activity": activity,
        "three_preparation_preference_A_minus_B": preference,
        "three_preparation_preference_B_minus_A": reverse_preference,
        "ratio_of_arithmetic_means": ratio_of_means,
        "log_paired_ratios": log_ratios,
        "geometric_mean_paired_ratio": geometric_ratio,
        "two_independent_measurements": independent,
        "two_measurements_with_shared_preparation_and_calibration": shared_result,
        "shared_covariance": shared,
        "exact_duplicate": duplicate_status,
        "opposite_signed_contrasts_under_common_effect_model": contradiction,
        "nondetection": {
            "limit": limit, "noise_standard_deviation": censor_noise,
            "one_censored_observation_nonnegative_presence_profile": 0.0,
            "nonnegative_rate_upper_95_bound": upper_95,
            "detected_plus_censored_same_rate_MLE": fitted,
            "detected_plus_censored_presence_profile": joint_profile,
            "detected_plus_censored_bounded": bounded_profile(joint_profile),
            "likelihood_derivative_at_optimum": derivative,
        },
        "bounded_residual_bias_illustration": {
            "comparability_bias_range": cmp_bias,
            "isolation_bias_range": isolation_bias,
            "total_residual_bias_range": total_bias,
            "adjusted_contrast_range": effect_interval,
            "profile_log_ratio_range": score_interval,
            "bounded_profile_contrast_range": bounded_interval,
        },
        "two_necessary_independent_contrasts": {
            "standardized_estimates_positive": joint_positive,
            "positive_joint_profile": joint_positive_score,
            "positive_joint_bounded": bounded_profile(joint_positive_score),
            "standardized_estimates_one_reversed": joint_violation,
            "reversed_joint_profile": joint_violation_score,
            "reversed_joint_bounded": bounded_profile(joint_violation_score),
        },
        "verified": [
            "known-variance profile algebra and unit invariance",
            "finite-sample paired-normal profile versus maximized residual likelihood",
            "opposite specificity outcomes and bounded antisymmetry",
            "physical nonnegative-activity boundary",
            "arithmetic-mean versus geometric paired-ratio distinction",
            "shared covariance and exact duplicate treatment",
            "contradictory signed contrasts with retained heterogeneity",
            "censored event likelihood and nonnegative constrained optimum",
            "upper-bound inversion for nondetection",
            "separate comparability/isolation bias sensitivity",
            "compound-inference likelihood regions",
        ],
        "not_verified": [
            "scientific model adequacy for any paper",
            "any target sequence or functional annotation",
            "external literature examples",
            "source-to-target fitted bridge parameters",
            "score calibration to annotation accuracy",
            "adoption or production integration",
        ],
    }
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    with args.output.open("x") as destination:
        destination.write(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
