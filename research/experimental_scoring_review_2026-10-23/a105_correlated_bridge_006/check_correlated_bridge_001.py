#!/usr/bin/env python3
"""Source-free SYNTHETIC research arithmetic; no reader or production scorer.

Run with python3. Requires NumPy; writes only adjacent research artifacts.
All covariance operands are declared fixture inputs, not learned biology.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
CHECKS: list[str] = []


def checked(name, actual, expected, *, atol=1e-11):
    if not np.allclose(actual, expected, rtol=1e-11, atol=atol):
        raise AssertionError(f"{name}: {actual!r} != {expected!r}")
    CHECKS.append(name)


def block_diagonal(*matrices):
    size = sum(len(matrix) for matrix in matrices)
    output = np.zeros((size, size))
    offset = 0
    for matrix in matrices:
        n = len(matrix)
        output[offset : offset + n, offset : offset + n] = matrix
        offset += n
    return output


def fit_common_effect(z, covariance):
    """Known-covariance normal example, conditional on ONE shared target effect."""
    z = np.asarray(z, dtype=float)
    c = np.asarray(covariance, dtype=float)
    if z.ndim != 1 or len(z) == 0 or c.shape != (len(z), len(z)):
        raise ValueError("missing_or_wrong_covariance_shape")
    if not np.isfinite(z).all() or not np.isfinite(c).all():
        raise ValueError("missing_or_nonfinite_operand")
    if not np.allclose(c, c.T, rtol=0, atol=1e-13):
        raise ValueError("covariance_not_symmetric")
    try:
        np.linalg.cholesky(c)
    except np.linalg.LinAlgError as error:
        raise ValueError("degenerate_or_invalid_covariance_requires_its_own_model") from error
    one = np.ones(len(z))
    inverse_times_one = np.linalg.solve(c, one)
    precision = float(one @ inverse_times_one)
    weights = inverse_times_one / precision
    theta = float(weights @ z)
    variance = 1.0 / precision
    residual = z - theta
    q = float(residual @ np.linalg.solve(c, residual))
    q_zero = float(z @ np.linalg.solve(c, z))
    # Fit the common effect once, then evaluate its two directional constraints.
    theta_plus, theta_minus = max(0.0, theta), min(0.0, theta)
    rp, rm = z - theta_plus, z - theta_minus
    q_plus = float(rp @ np.linalg.solve(c, rp))
    q_minus = float(rm @ np.linalg.solve(c, rm))
    s = 0.5 * (q_minus - q_plus)
    checked("profile_quadratic_equals_closed_form", s, theta * abs(theta) / (2 * variance))
    checked("GLS_normal_equation", one @ np.linalg.solve(c, residual), 0.0)
    return {
        "effect": theta,
        "variance": variance,
        "standard_error": math.sqrt(variance),
        "standardized_effect": theta / math.sqrt(variance),
        "precision": precision,
        "weights": weights.tolist(),
        "S_nats": s,
        "B": math.tanh(s / 2),
        "Q": q,
        "Q_degrees_of_freedom_conditional_on_fixed_C": len(z) - 1,
        "Q_at_zero": q_zero,
        "Q_Hplus": q_plus,
        "Q_Hminus": q_minus,
    }


def construct_fixture(name, y, cmp, iso, design, beta, assay_var, cmp_var,
                      iso_var, beta_cov, source_cov, target_var,
                      family_design, family_cov, identities):
    """Populate h and C from explicit synthetic primitive inputs and loadings."""
    y, cmp, iso = (np.asarray(v, dtype=float) for v in (y, cmp, iso))
    x, beta = np.asarray(design, dtype=float), np.asarray(beta, dtype=float)
    n = len(y)
    identity = np.eye(n)
    ones = np.ones((n, 1))
    f = np.asarray(family_design, dtype=float)
    blocks = [np.diag(assay_var), np.diag(cmp_var), np.diag(iso_var),
              np.asarray(beta_cov), np.asarray(source_cov),
              np.asarray([[target_var]]), np.asarray(family_cov)]
    jacobian = np.concatenate([identity, -identity, -identity, x, identity, ones, f], axis=1)
    joint = block_diagonal(*blocks)
    components = {
        "assay": blocks[0],
        "comparability": blocks[1],
        "isolation": blocks[2],
        "fitted_response_coefficients": x @ blocks[3] @ x.T,
        "source_specific_response_residual": blocks[4],
        "shared_target_response_residual": ones @ blocks[5] @ ones.T,
        "shared_family_response_residual": f @ blocks[6] @ f.T,
    }
    target_covariance = jacobian @ joint @ jacobian.T
    checked(name + " covariance component sum", target_covariance, sum(components.values()))
    z = y - cmp - iso + x @ beta
    labels = ([f"y[{i+1}]" for i in range(n)]
              + [f"comparability_bias[{i+1}]" for i in range(n)]
              + [f"isolation_bias[{i+1}]" for i in range(n)]
              + [f"beta[{i}]" for i in range(len(beta))]
              + [f"source_residual[{i+1}]" for i in range(n)]
              + ["target_residual"]
              + [f"family_residual[{i+1}]" for i in range(f.shape[1])])
    return {
        "name": name,
        "status": "SYNTHETIC_declared_known_covariance_model",
        "contrast": "theta = log(attributed_rate_A_target / attributed_rate_B_target), common reference state",
        "units": "dimensionless log ratio; covariance in squared log-ratio units",
        "identities": identities,
        "y": y.tolist(), "comparability_bias": cmp.tolist(), "isolation_bias": iso.tolist(),
        "source_corrected_contrast": (y - cmp - iso).tolist(),
        "X": x.tolist(), "beta": beta.tolist(),
        "fitted_response_mean": (x @ beta).tolist(),
        "source_residual_mean": [0.0] * n, "target_residual_mean": 0.0,
        "family_residual_mean": [0.0] * f.shape[1],
        "family_design": f.tolist(),
        "primitive_order": labels,
        "primitive_joint_covariance": joint.tolist(),
        "jacobian": jacobian.tolist(),
        "covariance_components": {key: value.tolist() for key, value in components.items()},
        "mapped_target_estimates": z.tolist(),
        "target_covariance": target_covariance.tolist(),
        "fit": fit_common_effect(z, target_covariance),
    }


def balanced_fixture(n, mode="correlated", *, effects=None):
    """Equal-marginal-variance scenarios, with declared DIFFERENT error models."""
    effects = [0.8] * n if effects is None else effects
    omega = np.asarray([[0.02, 0.005], [0.005, 0.02]])
    if mode == "independent":
        # Distinct supported calibrations, no shared-target/family error in this
        # hypothetical model; independent residual .14 replaces .04+.06+.04.
        design = np.zeros((n, 2 * n))
        for i in range(n):
            design[i, 2 * i:2 * i + 2] = [1, 1]
        beta = [0.1, 0.1] * n
        beta_cov = block_diagonal(*([omega] * n))
        source_cov, target_var = 0.14 * np.eye(n), 0.0
        family_design, family_cov = np.zeros((n, 1)), np.zeros((1, 1))
    else:
        design, beta, beta_cov = np.ones((n, 2)), [0.1, 0.1], omega
        source_cov = 0.04 * (np.ones((n, n)) if mode == "new_preparations_same_source" else np.eye(n))
        target_var = 0.06
        family_design, family_cov = np.ones((n, 1)), np.asarray([[0.04]])
    fixture = construct_fixture(
        f"{n}_{mode}", effects, [0.1] * n, [0.1] * n, design, beta,
        [0.04] * n, [0.01] * n, [0.01] * n, beta_cov, source_cov,
        target_var, family_design, family_cov,
        [{"source": "H1" if mode == "new_preparations_same_source" else f"H{i+1}",
          "preparation": f"P{i+1}", "observation": f"O{i+1}"} for i in range(n)],
    )
    if mode == "independent":
        expected = .25 * np.eye(n)
        expected_var = .25 / n
    else:
        independent = .06 if mode == "new_preparations_same_source" else .10
        shared = .19 if mode == "new_preparations_same_source" else .15
        expected = independent * np.eye(n) + shared * np.ones((n, n))
        expected_var = independent / n + shared
    checked(fixture["name"] + " full matrix", fixture["target_covariance"], expected)
    checked(fixture["name"] + " compound symmetry pooled variance", fixture["fit"]["variance"], expected_var)
    return fixture


def distinct_observations(records):
    """Demonstrate identity-based deduplication, never equality-based deduplication."""
    distinct = {}
    for record in records:
        key = record["observation"]
        if key in distinct and distinct[key] != record:
            raise ValueError("conflicting_representations_of_one_observation")
        distinct[key] = record
    return list(distinct.values())


def main():
    fixtures = [balanced_fixture(n, mode) for mode in ("independent", "correlated") for n in (1, 2, 10)]
    fixtures.append(balanced_fixture(2, "new_preparations_same_source"))
    for label, effects, mode in [
        ("positive_but_smaller_independent", [0.8, 0.1], "independent"),
        ("positive_but_smaller_correlated", [0.8, 0.1], "correlated"),
        ("opposing_equal_independent", [0.8, -0.8], "independent"),
        ("opposing_stronger_independent", [0.8, -1.2], "independent"),
        ("opposing_stronger_correlated", [0.8, -1.2], "correlated"),
    ]:
        f = balanced_fixture(2, mode, effects=effects)
        f["name"] = label
        fixtures.append(f)
    asymmetric = construct_fixture(
        "asymmetric_three_sources", [0.9, 0.6, 0.95], [0.1, 0.05, 0.2], [0.1, 0.1, 0.05],
        [[1, -1], [1, 0], [1, 1]], [.15, .05], [.04, .09, .16], [.01, .01, .04],
        [.01, .04, .01], [[.02, .005], [.005, .02]], .04 * np.eye(3), .06,
        [[1, 0], [1, 0], [0, 1]], .04 * np.eye(2),
        [{"source": f"G{i+1}", "preparation": f"GP{i+1}", "observation": f"GO{i+1}"} for i in range(3)],
    )
    checked("asymmetric target values", asymmetric["mapped_target_estimates"], [.8, .6, .9])
    checked("asymmetric full covariance", asymmetric["target_covariance"],
            [[.23, .115, .06], [.115, .30, .085], [.06, .085, .40]])
    fixtures.append(asymmetric)
    lookup = {f["name"]: f for f in fixtures}
    positive = lookup["positive_but_smaller_independent"]["fit"]
    checked("positive contradictory magnitude joint S", positive["S_nats"], .81)
    checked("positive contradictory magnitude Q", positive["Q"], .98)
    assert positive["S_nats"] < lookup["1_independent"]["fit"]["S_nats"]
    CHECKS.append("a_positive_added_observation_can_reduce_directional_support")

    profile_examples = []
    for effects in ([.8, .8], [.8, .1], [.8, -1.2]):
        individual_s = [v * abs(v) / (2 * .25) for v in effects]
        joint = fit_common_effect(effects, .25 * np.eye(2))
        # Independent observation likelihoods add at each common trial theta.
        at_common_theta = []
        for theta in (0, .1, .45, .8):
            summed = sum(-.5 * (v - theta) ** 2 / .25 for v in effects)
            residual = np.asarray(effects) - theta
            vector = -.5 * float(residual @ np.linalg.solve(.25 * np.eye(2), residual))
            checked("sum_likelihood_before_profile", summed, vector)
            at_common_theta.append({"theta": theta, "summed_log_likelihood_without_constant": summed})
        profile_examples.append({"effects": effects, "individual_S": individual_s,
                                 "sum_individually_optimized_S_not_joint_S": sum(individual_s),
                                 "joint": joint, "common_parameter_likelihood_checks": at_common_theta})

    original = {"observation": "original_O1", "source": "H1", "preparation": "P1", "effect": .8, "variance": .25}
    records = distinct_observations([original, dict(original)])
    checked("duplicate_observation_count", len(records), 1)
    duplicate_fit = fit_common_effect([r["effect"] for r in records], [[.25]])
    singular = .25 * np.ones((2, 2))
    pinv_precision = np.ones(2) @ np.linalg.pinv(singular) @ np.ones(2)
    checked("exact_duplicate_singular_likelihood_equivalence", 1 / pinv_precision, .25)
    distinct_same_values = distinct_observations([original, {**original, "observation": "new_O2", "preparation": "P2"}])
    checked("equal_values_do_not_establish_duplicate_identity", len(distinct_same_values), 2)
    caught = {}
    for name, fn in {
        "duplicate_conflict": lambda: distinct_observations([original, {**original, "effect": .9}]),
        "missing_covariance": lambda: fit_common_effect([.8, .8], [[.25, None], [None, .25]]),
        "all_zero_covariance": lambda: fit_common_effect([.8, .8], np.zeros((2, 2))),
        "singular_duplicate_needs_deduplication": lambda: fit_common_effect([.8, .8], singular),
        "invalid_covariance": lambda: fit_common_effect([.8, .8], [[.25, .3], [.3, .25]]),
    }.items():
        try:
            fn()
        except ValueError as error:
            caught[name] = str(error)
            CHECKS.append(name + " preserved_without_zero_fill_or_jitter")
        else:
            raise AssertionError(name + " was silently accepted")

    correlation_points = []
    for rho in (0.0, .2, .6, .8):
        c = .25 * ((1 - rho) * np.eye(10) + rho * np.ones((10, 10)))
        result = fit_common_effect([.8] * 10, c)
        checked("correlation_sensitivity_analytic_variance", result["variance"], .25 * (1 + 9 * rho) / 10)
        correlation_points.append({"rho": rho, "C": c.tolist(), "fit": result})
    sensitivity = {
        "status": "SYNTHETIC_sensitivity_set_not_empirical_correlation_bounds",
        "rho_interval": [0.0, .8],
        "S_range": [correlation_points[-1]["fit"]["S_nats"], correlation_points[0]["fit"]["S_nats"]],
        "B_range": [correlation_points[-1]["fit"]["B"], correlation_points[0]["fit"]["B"]],
        "points": correlation_points,
        "no_bound_result": "No point estimate: covariance unknown. In this exchangeable family, PSD alone permits rho approaching -1/9 and hence unbounded S for ten equal positive observations.",
    }

    # An independently measured target/source ratio reusing the same source
    # assay must retain its NEGATIVE source/ratio covariance.
    source_and_difference_cov = np.asarray([[.04, -.04], [-.04, .13]])
    checked("shared_denominator_error_cancels", np.ones(2) @ source_and_difference_cov @ np.ones(2), .09)
    # Affine unit changes do not alter the dimensionless directional index.
    native = asymmetric["fit"]
    scaled = fit_common_effect(7 * np.asarray(asymmetric["mapped_target_estimates"]),
                              49 * np.asarray(asymmetric["target_covariance"]))
    checked("unit_scaling_invariance", scaled["S_nats"], native["S_nats"])
    reversed_fit = fit_common_effect(-np.asarray(asymmetric["mapped_target_estimates"]), asymmetric["target_covariance"])
    checked("contrast_direction_reversal", reversed_fit["S_nats"], -native["S_nats"])

    output = {
        "status": "All numerical inputs and outcomes are SYNTHETIC research illustrations.",
        "numpy_version": np.__version__, "fixtures": fixtures,
        "duplicate": {"original_records": [original, original], "unique_records": records,
                      "raw_duplicate_C": singular.tolist(), "unique_fit": duplicate_fit},
        "profile_sum_comparison": profile_examples, "correlation_sensitivity": sensitivity,
        "missing_and_zero_handling": caught,
        "missing_h_result": {"target_contribution": None, "status": "unresolved_response_mapping", "source_measurement_retained": True},
        "reused_source_ratio_covariance": source_and_difference_cov.tolist(),
        "reused_source_ratio_output_variance": .09,
        "checks_passed": CHECKS,
    }
    path = HERE / "arithmetic_001.json"
    path.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    lines = ["All entries are SYNTHETIC, conditional on the declared h and C.", "",
             "| Scenario | Target estimate | Variance | S (nats) | B | Q |",
             "|---|---:|---:|---:|---:|---:|"]
    for f in fixtures:
        r = f["fit"]
        lines.append(f"| {f['name']} | {r['effect']:.9f} | {r['variance']:.9f} | {r['S_nats']:.9f} | {r['B']:.9f} | {r['Q']:.9f} |")
    r = duplicate_fit
    lines.append(f"| Exact repeat of original observation | {r['effect']:.9f} | {r['variance']:.9f} | {r['S_nats']:.9f} | {r['B']:.9f} | {r['Q']:.9f} |")
    lines.extend(["", f"Checked {len(CHECKS)} arithmetic/model relationships; NumPy {np.__version__}.", ""])
    (HERE / "NUMERICAL_TABLE_001.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
