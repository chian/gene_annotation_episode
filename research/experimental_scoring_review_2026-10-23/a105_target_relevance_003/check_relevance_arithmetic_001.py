"""Research arithmetic only. No production reader, scorer, or target findings.

All calibration data below are explicitly synthetic. The published quantities
are restricted to arithmetic already described in the two source packets.
"""

import json
import math
from pathlib import Path


def inverse(matrix):
    n = len(matrix)
    aug = [list(row) + [float(i == j) for j in range(n)] for i, row in enumerate(matrix)]
    for k in range(n):
        pivot = max(range(k, n), key=lambda j: abs(aug[j][k]))
        aug[k], aug[pivot] = aug[pivot], aug[k]
        scale = aug[k][k]
        if abs(scale) < 1e-12:
            raise ValueError("singular matrix")
        aug[k] = [v / scale for v in aug[k]]
        for i in range(n):
            if i == k:
                continue
            factor = aug[i][k]
            aug[i] = [a - factor * b for a, b in zip(aug[i], aug[k])]
    return [row[n:] for row in aug]


def quadratic(x, matrix):
    return sum(x[i] * matrix[i][j] * x[j] for i in range(len(x)) for j in range(len(x)))


published_arithmetic = {
    "TriA_identity": 466 / 475,
    "TriA_two_substrate_preference_lower_bound": 245 / (245 + 0.01),
    "FolE2_Zn_Mn_recipe_response_ratio": 14 / 100,
    "FolE2_log_Zn_Mn_recipe_ratio": math.log(14 / 100),
    "FolE2_saturation_50uM": 50 / (9.87 + 50),
    "FolE2_saturation_10uM": 10 / (9.87 + 10),
    "FolE2_response_ratio_10_to_50uM": (10 / (9.87 + 10)) / (50 / (9.87 + 50)),
    "FolE2_turnover_50uM_per_s": 0.0011 * 50 / (9.87 + 50),
    "FolE2_turnover_10uM_per_s": 0.0011 * 10 / (9.87 + 10),
    "FolE2_log_ratio_dKm_per_uM": 1 / (9.87 + 50) - 1 / (9.87 + 10),
}
published_arithmetic["FolE2_log_ratio_Km_variance_coefficient"] = (
    published_arithmetic["FolE2_log_ratio_dKm_per_uM"] ** 2
)

# Each group contains FOUR independent synthetic pairs with y=[-a,-a,a,a].
# Thus mean=0 and ML residual variance=sum(y**2)/4 equals a**2.
# The known measurement variance of each observed log contrast difference is .01.
# The beta mean model is a fitted intercept; all groups are symmetric about 0.
calibration = []
for bit_score, site_rmsd, residual_variance in [
    (60.0, 0.0, 0.16),
    (120.0, 0.0, 0.04),
    (60.0, 2.0, 0.36),
    (120.0, 2.0, 0.09),
]:
    total_variance = 0.01 + residual_variance
    a = math.sqrt(total_variance)
    calibration.append({
        "bit_score": bit_score,
        "site_rmsd_A": site_rmsd,
        "observed_contrast_differences": [-a, -a, a, a],
        "known_measurement_variance": 0.01,
        "ML_total_variance": total_variance,
        "ML_residual_variance": residual_variance,
    })

# Center and scale observed comparison measurements for stable arithmetic.
# q_b=(bit_score-90)/30, q_r=(site_rmsd**2-2)/2.
gamma_b = math.log(0.25) / 2
gamma_r = math.log(2.25) / 2
gamma_0 = math.log(0.12)
information_gamma = [[0.0] * 3 for _ in range(3)]
information_beta = 0.0
for row in calibration:
    q = [1.0, (row["bit_score"] - 90) / 30, (row["site_rmsd_A"] ** 2 - 2) / 2]
    pred = math.exp(gamma_0 + gamma_b * q[1] + gamma_r * q[2])
    assert math.isclose(pred, row["ML_residual_variance"], rel_tol=1e-12)
    n = len(row["observed_contrast_differences"])
    v = row["ML_total_variance"]
    t = row["ML_residual_variance"]
    information_beta += n / v
    # Exact observed gamma information for these symmetric, exact-variance data.
    weight = n / 2 * (t / v) ** 2
    for i in range(3):
        for j in range(3):
            information_gamma[i][j] += weight * q[i] * q[j]
cov_gamma = inverse(information_gamma)
var_beta = 1 / information_beta

# New SYNTHETIC source/target pair: b=90 bits, site RMSD=1 Å.
q_star = [1.0, 0.0, -0.5]
log_tau_hat = gamma_0 + gamma_b * q_star[1] + gamma_r * q_star[2]
tau_hat = math.exp(log_tau_hat)
var_log_tau = quadratic(q_star, cov_gamma)
# Laplace normal approximation for gamma uncertainty, not exact small-sample inference.
tau_expected_laplace = math.exp(log_tau_hat + 0.5 * var_log_tau)
bridge_var = tau_expected_laplace + var_beta

theta_s = math.log(4)
var_source = 0.04
system_d = math.log(0.6)
var_system_d = 0.0025
theta_t = theta_s + system_d  # fitted molecular mean shift is exactly zero in the fixture
variance_t = var_source + bridge_var + var_system_d
stat_t = theta_t / math.sqrt(variance_t)
signed_profile_t = math.copysign(theta_t * theta_t / (2 * variance_t), theta_t)
bounded_t = math.tanh(signed_profile_t / 2)
signed_profile_source = theta_s ** 2 / (2 * var_source)
variance_conditional = var_source + tau_hat + var_system_d

shared_source_variance = 0.04
shared_target_variance = 0.09
shared_bridge_variance = shared_source_variance + shared_target_variance
shared_source_bridge_covariance = -shared_source_variance
cancelled = shared_source_variance + shared_bridge_variance + 2 * shared_source_bridge_covariance
assert math.isclose(cancelled, shared_target_variance, abs_tol=1e-12)

out = {
    "status": "research arithmetic; all calibration observations and target example are synthetic",
    "published_derived_arithmetic": published_arithmetic,
    "synthetic_calibration": calibration,
    "fitted_centered_variance_model": {
        "mean_beta": 0.0,
        "mean_beta_variance": var_beta,
        "gamma": [gamma_0, gamma_b, gamma_r],
        "gamma_information": information_gamma,
        "gamma_covariance": cov_gamma,
    },
    "synthetic_prediction": {
        "q_star": q_star,
        "intrinsic_bridge_variance_conditional": tau_hat,
        "variance_of_log_bridge_variance": var_log_tau,
        "intrinsic_bridge_variance_Laplace_averaged": tau_expected_laplace,
        "total_molecular_bridge_variance": bridge_var,
        "source_log_specificity_contrast": theta_s,
        "source_variance": var_source,
        "source_signed_profile_log_likelihood": signed_profile_source,
        "system_log_response_difference": system_d,
        "system_difference_variance": var_system_d,
        "target_specificity_ratio": math.exp(theta_t),
        "target_log_specificity_contrast": theta_t,
        "target_variance_conditional_parameters": variance_conditional,
        "target_variance_Laplace_averaged": variance_t,
        "target_standard_uncertainty": math.sqrt(variance_t),
        "target_standardized_statistic": stat_t,
        "target_signed_profile_log_likelihood": signed_profile_t,
        "target_bounded_directional_index": bounded_t,
        "retained_precision_diagnostic": var_source / variance_t,
    },
    "shared_measurement_cancellation": {
        "source_variance": shared_source_variance,
        "measured_bridge_variance": shared_bridge_variance,
        "source_bridge_covariance": shared_source_bridge_covariance,
        "target_variance_after_cancellation": cancelled,
    },
}
destination = Path(__file__).with_name("relevance_arithmetic_001.json")
destination.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
