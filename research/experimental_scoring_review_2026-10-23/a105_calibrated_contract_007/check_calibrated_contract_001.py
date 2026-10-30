#!/usr/bin/env python3
"""Independent source-free research arithmetic. No reader or scorer integration.

Uses exact rational linear algebra for the finite decimal fixture operands.
Only log/exp/sqrt/tanh comparisons use floating point. Writes a NEW result file;
never imports or executes another worker's code and never overwrites artifacts.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKS = []


def equal(name, actual, expected):
    if actual != expected:
        raise AssertionError(f"{name}: {actual!r} != {expected!r}")
    CHECKS.append(name)


def near(name, actual, expected):
    def matches(a, b):
        if isinstance(a, (list, tuple)):
            return len(a) == len(b) and all(matches(x, y) for x, y in zip(a, b))
        return math.isclose(float(a), float(b), rel_tol=2e-12, abs_tol=2e-12)
    if not matches(actual, expected):
        raise AssertionError(f"{name}: {actual!r} != {expected!r}")
    CHECKS.append(name)


def number(v):
    if v is None or isinstance(v, bool):
        raise ValueError("unresolved_missing_or_invalid_numeric_operand")
    if isinstance(v, F):
        return v
    if not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError("unresolved_missing_or_invalid_numeric_operand")
    return F(str(v))


def matrix(a):
    if not a or not all(isinstance(row, list) and len(row) == len(a[0]) for row in a):
        raise ValueError("unresolved_covariance_shape")
    return [[number(v) for v in row] for row in a]


def transpose(a):
    return [list(row) for row in zip(*a)]


def dot(a, b):
    return sum((x * y for x, y in zip(a, b)), F(0))


def mv(a, x):
    return [dot(row, x) for row in a]


def mm(a, b):
    return [[dot(row, col) for col in transpose(b)] for row in a]


def identity(n):
    return [[F(int(i == j)) for j in range(n)] for i in range(n)]


def check_positive_definite(c):
    if c != transpose(c):
        raise ValueError("invalid_covariance_not_symmetric")
    # Exact symmetric elimination: no tolerance, jitter, or pseudo-inverse.
    work = deepcopy(c)
    for k in range(len(c)):
        pivot = work[k][k]
        if pivot == 0:
            raise ValueError("unresolved_singular_or_degenerate_covariance")
        if pivot < 0:
            raise ValueError("invalid_covariance_not_positive_definite")
        for i in range(k + 1, len(c)):
            for j in range(k + 1, len(c)):
                work[i][j] -= work[i][k] * work[k][j] / pivot


def solve(a, b):
    work = [row[:] + [value] for row, value in zip(a, b)]
    for k in range(len(a)):
        pivot_row = next((i for i in range(k, len(a)) if work[i][k]), None)
        if pivot_row is None:
            raise ValueError("unresolved_singular_linear_system")
        work[k], work[pivot_row] = work[pivot_row], work[k]
        divisor = work[k][k]
        work[k] = [v / divisor for v in work[k]]
        for i in range(len(a)):
            if i != k:
                multiple = work[i][k]
                work[i] = [v - multiple * p for v, p in zip(work[i], work[k])]
    return [row[-1] for row in work]


def conditional_fit(z, covariance, covariance_status="declared_known"):
    if covariance_status != "declared_known":
        raise ValueError("unresolved_estimated_covariance_sampling_model")
    z = [number(v) for v in z]
    c = matrix(covariance)
    if not z or len(c) != len(z) or any(len(row) != len(z) for row in c):
        raise ValueError("unresolved_covariance_shape")
    check_positive_definite(c)
    one = [F(1)] * len(z)
    ci_one = solve(c, one)
    p = sum(ci_one)
    w = [v / p for v in ci_one]
    theta = dot(w, z)
    variance = 1 / p
    residual = [v - theta for v in z]
    q = dot(residual, solve(c, residual))
    theta_plus, theta_minus = max(F(0), theta), min(F(0), theta)
    rp, rm = [v - theta_plus for v in z], [v - theta_minus for v in z]
    qp, qm = dot(rp, solve(c, rp)), dot(rm, solve(c, rm))
    s = (qm - qp) / 2
    equal("profile_difference_equals_signed_closed_form", s, theta * abs(theta) / (2 * variance))
    equal("normal_equation", dot(one, solve(c, residual)), F(0))
    return dict(precision_P=p, weights=w, theta_hat=theta, variance_V=variance,
                standard_uncertainty=math.sqrt(float(variance)), Q=q,
                Q_df_conditional_on_known_C=len(z) - 1, theta_plus=theta_plus,
                theta_minus=theta_minus, Q_plus=qp, Q_minus=qm, S_nats=s,
                B=math.tanh(float(s) / 2))


def distinct_records(records):
    by_id = {}
    for record in records:
        key = record["observation_id"]
        if key in by_id and record != by_id[key]:
            raise ValueError("unresolved_conflicting_representations")
        by_id[key] = record
    return list(by_id.values())


def caught(name, function):
    try:
        function()
    except ValueError as exc:
        CHECKS.append(name + "_without_zero_fill_or_jitter")
        return str(exc)
    raise AssertionError(name + " was silently accepted")


def numerical(value):
    if isinstance(value, F):
        return float(value)
    if isinstance(value, list):
        return [numerical(v) for v in value]
    if isinstance(value, dict):
        return {k: numerical(v) for k, v in value.items()}
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="ARITHMETIC_RESULTS_001.json",
                        help="new filename inside this research directory")
    args = parser.parse_args()
    if Path(args.output).name != args.output:
        raise ValueError("output must be a filename within the owned directory")
    output = HERE / args.output
    if output.exists():
        raise FileExistsError("additive output only: choose a new output filename")
    record = json.loads((HERE / "SYNTHETIC_RECORD_001.json").read_text())
    inp, expected = record["input"], record["derived"]
    rows = inp["observations"]
    equal("three_distinct_source_molecules", len({r["source_molecule_id"] for r in rows}), 3)
    equal("three_distinct_observations", len(distinct_records(rows)), 3)
    for row in rows:
        tag = row["source_molecule_id"]
        a, c, d = row["assay"], row["comparability"], row["isolation"]
        equal(tag + "_native_rate_unit", a["rate_unit"], "min^-1")
        near(tag + "_y_from_native_rates", math.log(a["net_rate_A"] / a["net_rate_B"]), a["log_ratio_y"])
        near(tag + "_c_from_attributed_condition_controls", math.log(c["attributed_ratio_A_over_B_at_source_condition"] / c["attributed_ratio_A_over_B_at_reference_condition"]), c["log_condition_ratio_c"])
        equal(tag + "_physical_fraction_bounds", 0 < d["fraction_A"] <= 1 and 0 < d["fraction_B"] <= 1, True)
        near(tag + "_d_from_attribution_fractions", -math.log(d["fraction_A"] / d["fraction_B"]), d["negative_log_fraction_ratio_d"])
        descriptor = row["descriptor"]
        equal(tag + "_descriptor_difference", descriptor["target_value"] - descriptor["source_value"], descriptor["target_minus_source_x"])
    u = [number(v) for v in inp["primitive"]["values"]]
    sigma = matrix(inp["primitive"]["covariance_matrix"])
    j = matrix(inp["primitive"]["jacobian_J"])
    equal("primitive_count", len(u), 17)
    equal("covariance_shape", [len(sigma), len(sigma[0])], [17, 17])
    equal("jacobian_shape", [len(j), len(j[0])], [3, 17])
    check_positive_definite(sigma)
    CHECKS.append("declared_full_primitive_covariance_positive_definite")
    # Independent reconstruction from the named cells; checks primitive order
    # and signs rather than trusting a repeated C result in the record.
    x = matrix(inp["response"]["prediction_design_X"])
    beta = [number(v) for v in inp["response"]["coefficient_values_beta"]]
    y = [number(r["assay"]["log_ratio_y"]) for r in rows]
    c = [number(r["comparability"]["log_condition_ratio_c"]) for r in rows]
    d = [number(r["isolation"]["negative_log_fraction_ratio_d"]) for r in rows]
    source_corrected = [a - b - k for a, b, k in zip(y, c, d)]
    response_mean = mv(x, beta)
    z = [a + b for a, b in zip(source_corrected, response_mean)]
    near("source_corrected_contrast", source_corrected, expected["source_corrected_contrast"])
    near("response_mean", response_mean, expected["response_mean"])
    near("mapped_target_contrast", z, expected["mapped_target_contrast_z"])
    equal("linear_primitive_map", mv(j, u), z)
    target_c = mm(mm(j, sigma), transpose(j))
    near("full_covariance_by_exact_propagation", target_c, expected["target_covariance_C"])
    components = {k: matrix(v) for k, v in expected["covariance_components"].items()}
    component_sum = [[sum(m[i][k] for m in components.values()) for k in range(3)] for i in range(3)]
    equal("covariance_components_sum_once", target_c, component_sum)
    for block_name, row_name, variance_key in (("assay", "assay", "variance_y"), ("comparability", "comparability", "variance_c"), ("isolation", "isolation", "variance_d")):
        expected_block = [[number(rows[i][row_name][variance_key]) if i == k else F(0) for k in range(3)] for i in range(3)]
        equal(block_name + "_independent_error_block", components[block_name], expected_block)
    equal("correlated_coefficients_propagated", components["response_coefficients"], mm(mm(x, matrix(inp["response"]["coefficient_covariance"])), transpose(x)))
    for name, field in (("source_residual", "source"), ("target_residual", "target"), ("family_residual", "family")):
        res = inp["residuals"][field]
        loading = matrix(res["loadings"])
        equal(name + "_ownership_loadings", components[name], mm(mm(loading, matrix(res["covariance"])), transpose(loading)))
    fit = conditional_fit(z, target_c)
    for key, value in expected["pool"].items():
        near("stored_pool_" + key, fit[key], value)
    # Same target residual contributes a variance floor; it cannot be averaged
    # away by pretending every source owns a fresh target error.
    without_target = [[target_c[i][k] - F(".06") for k in range(3)] for i in range(3)]
    conditional = conditional_fit(z, without_target)
    equal("target_shared_variance_floor", fit["variance_V"] - conditional["variance_V"], F(".06"))
    equal("shared_target_term_preserves_mean", fit["theta_hat"], conditional["theta_hat"])
    equal("shared_target_term_preserves_weights", fit["weights"], conditional["weights"])
    reversed_fit = conditional_fit([-v for v in z], target_c)
    equal("direction_reversal_S", reversed_fit["S_nats"], -fit["S_nats"])
    near("direction_reversal_B", reversed_fit["B"], -fit["B"])
    scaled_fit = conditional_fit([7 * v for v in z], [[49 * v for v in row] for row in target_c])
    equal("positive_unit_rescaling_S", scaled_fit["S_nats"], fit["S_nats"])
    reuse = record["auxiliary_checks"]["covariance_reuse"]
    r_sigma = matrix(reuse["covariance"])
    check_positive_definite(r_sigma)
    reuse_variance = dot([F(1), F(1)], mv(r_sigma, [F(1), F(1)]))
    equal("negative_reuse_covariance_cancels_source_error", reuse_variance, F(".09"))
    equal("treating_reuse_as_independent_would_double_count", r_sigma[0][0] + r_sigma[1][1] - reuse_variance, F(".08"))
    original = {"observation_id": "D1", "source_molecule_id": "H1", "preparation_id": "P1", "effect": .8}
    equal("exact_rerepresentation_deduplicated_by_identity", len(distinct_records([original, deepcopy(original)])), 1)
    distinct_equal = {**original, "observation_id": "D2", "preparation_id": "P2"}
    equal("equal_numbers_preserve_distinct_identity", len(distinct_records([original, distinct_equal])), 2)
    canonical = conditional_fit([.8], [[.25]])
    independent_equal = conditional_fit([.8, .8], [[.25, 0], [0, .25]])
    same_source_preps = conditional_fit([.8, .8], [[.25, .19], [.19, .25]])
    equal("canonical_duplicate_variance", canonical["variance_V"], F(".25"))
    equal("distinct_equal_with_explicit_independence_variance", independent_equal["variance_V"], F(".125"))
    equal("new_preparations_retain_source_mapping_uncertainty", same_source_preps["variance_V"], F(".22"))
    opposing = conditional_fit([.8, -.8], [[.25, 0], [0, .25]])
    equal("opposition_zero_direction_retains_conflict", [opposing["S_nats"], opposing["Q"]], [F(0), F("5.12")])
    weaker_positive = conditional_fit([.8, .1], [[.25, 0], [0, .25]])
    equal("additional_positive_can_reduce_common_effect_support", weaker_positive["S_nats"], F(".81"))
    equal("no_sum_of_individually_optimized_scores", weaker_positive["S_nats"] != F("1.30"), True)
    zero = conditional_fit([0], [[.25]])
    equal("measured_zero_is_finite_neutral_direction", [zero["S_nats"], zero["B"]], [0, 0])
    unresolved = {
        "missing_covariance": caught("missing_covariance", lambda: conditional_fit([.8, .8], [[.25, None], [None, .25]])),
        "missing_effect": caught("missing_effect", lambda: conditional_fit([None], [[.25]])),
        "singular_duplicate_uncanonicalized": caught("singular_duplicate", lambda: conditional_fit([.8, .8], [[.25, .25], [.25, .25]])),
        "singular_nondeduplicable": caught("singular_nondeduplicable", lambda: conditional_fit([.8, .8], [[.25, -.25], [-.25, .25]])),
        "all_zero_covariance": caught("all_zero_covariance", lambda: conditional_fit([.8], [[0]])),
        "invalid_covariance": caught("invalid_covariance", lambda: conditional_fit([.8, .8], [[.25, .3], [.3, .25]])),
        "estimated_covariance_without_model": caught("estimated_covariance", lambda: conditional_fit([.8], [[.25]], "estimated_without_sampling_model")),
        "conflicting_same_observation": caught("conflicting_representation", lambda: distinct_records([original, {**original, "effect": .9}])),
    }
    # Preserve known .10 I; vary only PSD residual R with diagonal .15.
    # The exchangeable residual extrema here attain the bounds over ALL PSD R
    # with that diagonal, by the proof in the accompanying contract/addendum.
    sensitivity = []
    n = 10
    for label, a, b, expected_v in (
        ("fully_shared_residual", F(0), F(".15"), F(".16")),
        ("independent_residual", F(".15"), F(0), F(".025")),
        ("zero_sum_residual", F(1, 6), F(-1, 60), F(".010")),
    ):
        equal(label + "_residual_PSD", a >= 0 and a + n * b >= 0, True)
        residual_c = [[(a if i == k else 0) + b for k in range(n)] for i in range(n)]
        equal(label + "_residual_diagonal", [residual_c[i][i] for i in range(n)], [F(".15")] * n)
        full_c = [[v + (F(".1") if i == k else 0) for k, v in enumerate(row)] for i, row in enumerate(residual_c)]
        result = conditional_fit([.8] * n, full_c)
        equal(label + "_attainable_variance", result["variance_V"], expected_v)
        sensitivity.append({"case": label, "residual_R": residual_c, "C": full_c, "fit": result})
    equal("known_component_exact_variance_bounds", [min(x["fit"]["variance_V"] for x in sensitivity), max(x["fit"]["variance_V"] for x in sensitivity)], [F(".010"), F(".160")])
    equal("known_component_exact_S_bounds", [min(x["fit"]["S_nats"] for x in sensitivity), max(x["fit"]["S_nats"] for x in sensitivity)], [F(2), F(32)])
    equal("maximum_total_pair_correlation_with_known_independent_part", F(".15") / F(".25"), F(".6"))
    # Compare to the retained numerical result without importing its code.
    previous = HERE.parent / "a105_correlated_bridge_006" / "arithmetic_001.json"
    old = next(f for f in json.loads(previous.read_text())["fixtures"] if f["name"] == "asymmetric_three_sources")
    near("independent_reproduction_previous_C", target_c, old["target_covariance"])
    for new, old_name in (("theta_hat", "effect"), ("variance_V", "variance"), ("S_nats", "S_nats"), ("B", "B"), ("Q", "Q"), ("weights", "weights")):
        near("independent_reproduction_" + new, fit[new], old["fit"][old_name])
    repo = HERE.parents[2]
    manifest = json.loads((HERE / "INPUT_MANIFEST_001.json").read_text())
    preserved = []
    for entry in manifest["inputs"]:
        name = entry["path"]
        if "/a105_correlated_bridge_006/" in name or "/a105_sheet_cells_005/" in name:
            digest = hashlib.sha256((repo / name).read_bytes()).hexdigest()
            equal("preserved_" + Path(name).name, digest, entry["sha256"])
            preserved.append({"path": name, "sha256": digest})
    result = {
        "status": "PASS: SYNTHETIC research arithmetic only; no empirical calibration or policy adoption",
        "method": "independent Python standard-library Fraction algebra; no upstream module imported or executed",
        "record_sha256": hashlib.sha256((HERE / "SYNTHETIC_RECORD_001.json").read_bytes()).hexdigest(),
        "corrected_source_contrasts": source_corrected, "mapped_target_contrasts": z,
        "C": target_c, "pool": fit,
        "exact_rational_pool": {k: [str(v) for v in value] if isinstance(value, list) else str(value) for k, value in fit.items() if isinstance(value, (F, list))},
        "covariance_cancellation_variance": reuse_variance,
        "duplicate_and_equal_observation_cases": {"canonical_duplicate": canonical, "distinct_equal_known_independent": independent_equal, "same_source_new_preparations": same_source_preps},
        "contradictory_and_weaker_positive_cases": {"opposing_equal": opposing, "weaker_positive": weaker_positive},
        "unresolved_cases": unresolved, "known_component_sensitivity": sensitivity,
        "preserved_prior_artifacts": preserved,
        "check_count": len(CHECKS), "checks_passed": CHECKS,
        "limits": ["No source paper or scientific target calculation", "No reader implemented", "No estimated-covariance or censored-data likelihood fitted", "No singular model repaired", "B is not a probability", "No R multiplier", "Pending user aggregation convention and W05 projection remain unresolved", "0/10 sheets complete; A105 first"],
    }
    with output.open("x") as stream:
        json.dump(numerical(result), stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "checks": len(CHECKS), "theta_hat": float(fit["theta_hat"]), "variance_V": float(fit["variance_V"]), "S": float(fit["S_nats"]), "B": fit["B"], "Q": float(fit["Q"]), "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
