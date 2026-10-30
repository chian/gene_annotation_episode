"""Source-free arithmetic verification; no production scoring or data extraction.

All observations, models and allocation scenarios are explicitly synthetic.
Run from any directory; writes only its sibling arithmetic_001.json.
"""

import json
import math
from pathlib import Path


checks = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def close(name, actual, expected, tol=2e-13):
    check(name, math.isclose(actual, expected, rel_tol=tol, abs_tol=tol))


def directional_normal(y, variance):
    if not math.isfinite(y) or not math.isfinite(variance) or variance <= 0:
        raise ValueError("invalid normal model operands")
    return math.copysign(y * y / (2 * variance), y) if y else 0.0


def canonicalize(rows):
    canonical = {}
    for identity, value, variance in rows:
        operands = (value, variance)
        if identity in canonical and canonical[identity] != operands:
            raise ValueError("conflicting representations of one observation")
        canonical[identity] = operands
    return canonical


def known_independent_fit(rows):
    """Used only for fixtures explicitly declaring zero covariance."""
    values = list(canonicalize(rows).values())
    precision = math.fsum(1 / variance for _, variance in values)
    variance = 1 / precision
    mean = math.fsum(value / v for value, v in values) / precision
    score = directional_normal(mean, variance)
    return {"mean": mean, "variance": variance, "S": score,
            "B": math.tanh(score / 2)}


def q_value(S, R):
    if R is not None and (not math.isfinite(R) or not 0 <= R <= 1):
        raise ValueError("invalid R")
    if S is not None and not math.isfinite(S):
        raise ValueError("original finite S required")
    if R == 0 or S == 0:
        return 0.0
    if S is None or R is None:
        return None
    if R == 1:
        return S / 2
    if abs(S) < 30:
        return math.atanh(R * math.tanh(S / 2))
    t = math.exp(-abs(S))
    magnitude = 0.5 * (math.log((1 + R) + (1 - R) * t)
                       - math.log((1 - R) + (1 + R) * t))
    return math.copysign(magnitude, S)


def fixed_allocation(qs, coefficients):
    if not qs or len(qs) != len(coefficients):
        raise ValueError("complete declared nonempty roster required")
    if any(not math.isfinite(a) or a < 0 for a in coefficients):
        raise ValueError("finite nonnegative coefficients required")
    terms = []
    for q, a in zip(qs, coefficients):
        if a == 0:
            terms.append(0.0)
        elif q is None:
            return {"Q": None, "K": None, "c": None}
        else:
            terms.append(a * q)
    Q = math.fsum(terms)
    if not math.isfinite(Q):
        raise ArithmeticError("finite result not representable")
    K = math.tanh(Q)
    return {"Q": Q, "K": K, "c": max(0.0, K)}


def image_bounds(q_bounds, coefficients):
    def endpoint(which):
        return math.fsum(0.0 if a == 0 else a * b[which]
                         for b, a in zip(q_bounds, coefficients))
    low, high = math.tanh(endpoint(0)), math.tanh(endpoint(1))
    c_low, c_high = max(0.0, low), max(0.0, high)
    return {"K_bounds": [low, high], "c_bounds": [c_low, c_high],
            "K_point": low if low == high else None,
            "c_point": c_low if c_low == c_high else None}


H1_rows = [("H1-preparation-1", 2.0, 1.0),
           ("H1-preparation-2", 2.0, 1.0)]
H2_rows = [("H2-preparation-1", -2.0, 1.0)]
H1, H2 = known_independent_fit(H1_rows), known_independent_fit(H2_rows)
R1_components = [2 * 240 / (300 + 300), min(.92, .90), 7 / 10, 60 / 100,
                 math.exp(-((25 - 25) ** 2) / (2 * 100))]
R2_components = [2 * 90 / (300 + 300), min(.45, .40), 2 / 10, 10 / 100,
                 math.exp(-((25 - 25) ** 2) / (2 * 100))]
R1, R2 = math.fsum(R1_components) / 5, math.fsum(R2_components) / 5
D1, D2 = R1 * H1["B"], R2 * H2["B"]
q1, q2 = q_value(H1["S"], R1), q_value(H2["S"], R2)
close("H1 source S after joint fit", H1["S"], 4)
close("H2 source S", H2["S"], -2)
close("native five-family R1", R1, .8)
close("native five-family R2", R2, .4)
close("single-source identity", fixed_allocation([q1], [1])["K"], D1)

unit = fixed_allocation([q1, q2], [1, 1])
half = fixed_allocation([q1, q2], [.5, .5])
close("unit pair against two-input rational identity", unit["K"],
      (D1 + D2) / (1 + D1 * D2))
close("half allocation against double-angle identity", unit["K"],
      2 * half["K"] / (1 + half["K"] ** 2))
check("two allocations yield distinct outputs", unit["K"] != half["K"])

# Zero R has its own fully specified one-family correspondence example.
R0 = 2 * 0 / (300 + 300)
q0 = q_value(None, R0)
close("R=0 is algebraically neutral even if source S unknown", q0, 0)
for name, coefficients, expected in [
        ("unit", [1, 1], unit["K"]), ("half", [.5, .5], half["K"])]:
    for zero_allocation in [0, .5, 1, 10]:
        close(f"{name} neutral append allocation {zero_allocation}",
              fixed_allocation([q1, q2, q0], coefficients + [zero_allocation])["K"],
              expected)
close("H1 alone plus R0", fixed_allocation([q1, q0], [1, 1])["K"], D1)
old_zero_dilution = math.tanh(q1 / 2)
check("007 old denominator dilution", old_zero_dilution < D1)

duplicate_fit = known_independent_fit(H1_rows + [H1_rows[0]])
check("reprinted observation gives identical complete source fit", duplicate_fit == H1)
new_preparation_fit = known_independent_fit(H1_rows + [("H1-preparation-3", 2., 1.)])
close("new preparation fits before source score", new_preparation_fit["S"], 6)
try:
    canonicalize(H1_rows + [("H1-preparation-1", -2., 1.)])
except ValueError:
    check("conflicting representation rejected as duplicate resolution failure", True)
else:
    raise AssertionError("conflicting representation silently accepted")

# Exact source model with known shared variance .75 and independent variance .25.
known_shared_V = .75 + .25 / 2
known_shared_S = directional_normal(2, known_shared_V)
known_shared_D = R1 * math.tanh(known_shared_S / 2)
known_shared = fixed_allocation([q_value(known_shared_S, R1), q2], [1, 1])
close("shared model S", known_shared_S, 16 / 7)

# Unknown residual covariance preserves independent .25 I and residual diag .75.
# E=[[.75,r],[r,.75]] is PSD iff -.75 <= r <= .75; C=.25 I+E.
shared_bounds = []
for residual_covariance in [-.75, .75]:
    V = (1 + residual_covariance) / 2
    S = directional_normal(2, V)
    q = q_value(S, R1)
    shared_bounds.append({"residual_covariance": residual_covariance,
                          "source_variance": V, "source_S": S,
                          "source_D": math.tanh(q),
                          "conditional_unit_pair": fixed_allocation([q, q2], [1, 1])})
close("unknown shared lower V retains known independent component",
      shared_bounds[0]["source_variance"], .125)
close("unknown shared upper V", shared_bounds[1]["source_variance"], .875)
close("unknown shared upper S", shared_bounds[0]["source_S"], 16)

baseline = known_independent_fit([("a", .8, .25)])
measured_zero = known_independent_fit([("a", .8, .25), ("b", 0., .25)])
weak_positive = known_independent_fit([("a", .8, .25), ("b", .1, .25)])
close("measured zero updates common source effect", measured_zero["S"], .64)
close("weak positive updates common source effect", weak_positive["S"], .81)
check("measured zero is not omitted", measured_zero["B"] < baseline["B"])
check("positive measurement need not raise directional support", weak_positive["B"] < baseline["B"])
close("separate optimized S differ from joint common-effect result",
      baseline["S"] + directional_normal(.1, .25), 1.30)

equal_opposition = fixed_allocation([q1, -q1], [1, 1])
strong_opposition = fixed_allocation([q1, q_value(-4, 1)], [1, 1])
close("opposition cancels before projection", equal_opposition["c"], 0)
check("negative unprojected score retained", strong_opposition["K"] < 0)
close("negative final projection", strong_opposition["c"], 0)
check("clip before combine is a different result", D1 != equal_opposition["c"])

missing_R2 = image_bounds([(q1, q1), (-1, 0)], [1, 1])
missing_S2 = image_bounds([(q1, q1), (-math.atanh(.4), math.atanh(.4))], [1, 1])
projection_only_zero = image_bounds([(-2, -2), (-math.atanh(.4), math.atanh(.4))], [1, 1])
check("nonpoint signed score with identified projected zero",
      projection_only_zero["K_point"] is None and projection_only_zero["c_point"] == 0)
check("missing R2 does not become zero",
      fixed_allocation([q1, q_value(-2, None)], [1, 1])["K"] is None)

saturation_pair = fixed_allocation([q_value(1000, 1), q_value(-1000, 1)], [1, 1])
close("finite saturated opposite S cancel", saturation_pair["Q"], 0)
close("R below one limits transformed saturation", q_value(1000, .8), math.atanh(.8))
close("finite S=1000 with R=1 retains q=500", q_value(1000, 1), 500)
check("display saturation is not mathematical infinity", math.tanh(500) == 1)

# Two deliberately different unobserved mappings, not proposed empirical fits.
# Source data, source uncertainties, and correspondence measurements stay equal.
target_worlds = []
for name, offsets in [("positive_target_world", [-1, 3]),
                       ("negative_target_world", [-3, 1])]:
    mapped = [2 + offsets[0], -2 + offsets[1]]
    fit = known_independent_fit([("mapped-H1", mapped[0], .5),
                                ("mapped-H2", mapped[1], 1)])
    target_worlds.append({"name": name, "target_minus_source_offsets": offsets,
                          "mapped_contrasts": mapped, "target_fit": fit})
close("positive mapping completion target S", target_worlds[0]["target_fit"]["S"], 1.5)
close("negative mapping completion target S", target_worlds[1]["target_fit"]["S"], -1.5)
close("opposite target conclusions from same source inputs",
      target_worlds[0]["target_fit"]["B"], -target_worlds[1]["target_fit"]["B"])

# Additional two-source sensitivity result preserves known independent .10 I.
target_covariance_worlds = []
for residual_cov in [0, .15, -.15]:
    V = (.25 + residual_cov) / 2
    S = directional_normal(.8, V)
    target_covariance_worlds.append({"known_independent_diagonal": .10,
                                     "residual_diagonal": .15,
                                     "residual_covariance": residual_cov,
                                     "target_mean_variance": V, "S": S,
                                     "B": math.tanh(S / 2)})
close("independent target model variance", target_covariance_worlds[0]["target_mean_variance"], .125)
close("shared target model variance", target_covariance_worlds[1]["target_mean_variance"], .2)
close("retained independent component lower bound", target_covariance_worlds[2]["target_mean_variance"], .05)

# Independent rational-form and odd/permutation checks across positive/negative inputs.
for d1 in [-.9, -.3, 0, .4, .85]:
    for d2 in [-.8, -.2, 0, .1, .9]:
        got = fixed_allocation([math.atanh(d1), math.atanh(d2)], [1, 1])["K"]
        close(f"rational identity {d1},{d2}", got, (d1 + d2) / (1 + d1 * d2))
        close(f"permutation {d1},{d2}", got,
              fixed_allocation([math.atanh(d2), math.atanh(d1)], [1, 1])["K"])
        close(f"odd signed combination {d1},{d2}", -got,
              fixed_allocation([-math.atanh(d1), -math.atanh(d2)], [1, 1])["K"])

for S, R in [(float("inf"), 1), (2, -1), (2, 1.01)]:
    try:
        q_value(S, R)
    except ValueError:
        check(f"invalid source operand {S},{R}", True)
    else:
        raise AssertionError("invalid source operand accepted")

output = {
    "status": "SOURCE-FREE SYNTHETIC MATHEMATICS; no adopted allocation or scorer",
    "source_observations": {"H1": H1_rows, "H2": H2_rows},
    "source_models": {"H1": H1, "H2": H2},
    "R_components": {"H1": R1_components, "H2": R2_components},
    "per_source": {"R": [R1, R2], "D": [D1, D2], "q": [q1, q2]},
    "allocation_completions_for_nonidentifiability": {
        "unit_each": {"coefficients": [1, 1], **unit},
        "half_each": {"coefficients": [.5, .5], **half},
        "allowed_set_if_exactly_these_two_allocations_declared": sorted([unit["K"], half["K"]])},
    "neutral_append": {"R0": R0, "source_S": None, "source_q": q0,
                        "H1_fixed_unit_result": D1,
                        "007_denominator_result": old_zero_dilution,
                        "fixed_half_H1_result": math.tanh(.5 * q1)},
    "same_source_new_independent_preparation": new_preparation_fit,
    "known_shared_source": {"shared_variance": .75, "independent_variance": .25,
                            "V_H1_mean": known_shared_V, "S_H1": known_shared_S,
                            "D_H1": known_shared_D, "conditional_unit_pair": known_shared},
    "unknown_shared_source_sensitivity_endpoints": shared_bounds,
    "common_effect_comparison": {"original": baseline, "plus_measured_zero": measured_zero,
                                 "plus_weak_positive": weak_positive},
    "conflict": {"equal": equal_opposition, "stronger_negative": strong_opposition},
    "missing_inputs_fixed_unit_allocation": {"H2_R": missing_R2, "H2_S": missing_S2,
                                             "identified_projected_zero": projection_only_zero},
    "finite_saturation": {"opposite": saturation_pair, "q_at_S1000_R0_8": q_value(1000, .8),
                           "q_at_S1000_R1": q_value(1000, 1)},
    "mapping_nonidentifiability_worlds": target_worlds,
    "target_covariance_nonidentifiability_worlds": target_covariance_worlds,
    "count_amplification_if_unit_each": fixed_allocation([q1] * 10 + [q2], [1] * 11),
    "checks": checks,
    "checks_passed": len(checks),
}
destination = Path(__file__).with_name("arithmetic_001.json")
destination.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
print(json.dumps({"checks_passed": len(checks), "output": str(destination),
                  "unit_pair_K": unit["K"], "half_pair_K": half["K"],
                  "H1_R0_append_K": D1}))
