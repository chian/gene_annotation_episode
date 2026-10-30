"""Source-free synthetic arithmetic for an UNADOPTED A105 sheet proposal.

This is a standalone research calculation, not a production scorer or reader.
It writes only beside itself. No paper data, scientific store, or runtime is read.
"""

import itertools
import json
import math
from pathlib import Path


OUT = Path(__file__).resolve().parent


def same(a, b, tol=1e-11):
    assert math.isclose(a, b, rel_tol=tol, abs_tol=tol), (a, b)


def interval_formula(node, values, aliases=None):
    """Only declared AND/OR semantics; no selection of semantic structure."""
    aliases = aliases or {}
    if isinstance(node, str):
        canonical = aliases.get(node, node)
        value = values[canonical]
        return [-1.0, 1.0] if value is None else (
            list(value) if isinstance(value, (list, tuple)) else [value, value]
        )
    assert len(node) == 1
    op, children = next(iter(node.items()))
    assert op in {"all_of", "any_of"} and children
    operands = [interval_formula(c, values, aliases) for c in children]
    reduce = min if op == "all_of" else max
    return [reduce(x[0] for x in operands), reduce(x[1] for x in operands)]


def leaf_ids(node, aliases=None):
    aliases = aliases or {}
    if isinstance(node, str):
        return {aliases.get(node, node)}
    return set().union(*(leaf_ids(c, aliases) for cs in node.values() for c in cs))


def conventional(node, values, aliases=None):
    lo, hi = interval_formula(node, values, aliases)
    assert -1 <= lo <= hi <= 1
    c_lo, c_hi = max(0.0, lo), max(0.0, hi)
    refs = leaf_ids(node, aliases)
    known = sum(values[x] is not None and not isinstance(values[x], (list, tuple)) for x in refs)
    return {
        "route": "declared_minmax_convention",
        "signed_value": lo if lo == hi else None,
        "signed_identification_bounds": [lo, hi],
        "coordinate_value": c_lo if c_lo == c_hi else None,
        "coordinate_identification_bounds": [c_lo, c_hi],
        "coverage": {
            "unique_formula_statement_count": len(refs),
            "complete_point_statement_count": known,
            "complete_point_statement_fraction": known / len(refs),
        },
    }


def q2(theta, y, covariance):
    a, b = covariance[0]
    b2, d = covariance[1]
    assert b == b2 and a > 0 and d > 0
    determinant = a * d - b * b
    assert determinant > 0
    u, v = theta[0] - y[0], theta[1] - y[1]
    return (d * u * u - 2 * b * u * v + a * v * v) / determinant


def orthant_minimum(y, covariance, signs):
    """Exact two-dimensional positive-definite quadratic, closed orthant.

    Enumerate the unconstrained solution, both single active faces, and corner.
    No independence approximation or local optimizer is used.
    """
    a, b = covariance[0]
    _, d = covariance[1]
    candidates = [
        list(y),
        [0.0, y[1] - b * y[0] / a],
        [y[0] - b * y[1] / d, 0.0],
        [0.0, 0.0],
    ]
    feasible = [p for p in candidates if all(s * x >= -1e-12 for s, x in zip(signs, p))]
    return min((q2(p, y, covariance), p) for p in feasible)


def joint_two(y, covariance, op):
    assert op in {"all_of", "any_of"}
    classes = {True: [], False: []}
    for signs in itertools.product((-1, 1), repeat=2):
        truth = all(s > 0 for s in signs) if op == "all_of" else any(s > 0 for s in signs)
        classes[truth].append(orthant_minimum(y, covariance, signs))
    q_plus, fit_plus = min(classes[True])
    q_minus, fit_minus = min(classes[False])
    s = (q_minus - q_plus) / 2
    d = math.tanh(s / 2)
    return {
        "route": "joint_known_normal_profile",
        "observed_contrasts": list(y),
        "covariance": covariance,
        "operator": op,
        "q_plus": q_plus,
        "q_minus": q_minus,
        "fit_plus": fit_plus,
        "fit_minus": fit_minus,
        "profile_log_ratio": s,
        "signed_value": d,
        "coordinate_value": max(0.0, d),
    }


formula = {"any_of": ["direct", {"all_of": ["first_step", "second_step"]}]}
values = {"direct": 0.72, "first_step": 0.84, "second_step": 0.42, "binding": 0.9604}
cases = {}
cases["complete_candidate"] = conventional(formula, values)
same(cases["complete_candidate"]["coordinate_value"], 0.72)
cases["required_both"] = conventional({"all_of": ["first_step", "second_step"]}, values)
same(cases["required_both"]["coordinate_value"], 0.42)
cases["either_sufficient"] = conventional({"any_of": ["first_step", "second_step"]}, values)
same(cases["either_sufficient"]["coordinate_value"], 0.84)

related_changed = {**values, "binding": -0.99}
cases["related_binding_cannot_substitute"] = conventional(formula, related_changed)
assert cases["related_binding_cannot_substitute"] == cases["complete_candidate"]
cases["direct_opposed_other_path_supported"] = conventional(formula, {**values, "direct": -0.72})
same(cases["direct_opposed_other_path_supported"]["coordinate_value"], 0.42)
cases["both_paths_opposed"] = conventional(formula, {**values, "direct": -0.72, "second_step": -0.42})
same(cases["both_paths_opposed"]["signed_value"], -0.42)
same(cases["both_paths_opposed"]["coordinate_value"], 0.0)

missing = {**values, "second_step": None}
cases["unavailable_required_statement"] = conventional({"all_of": ["first_step", "second_step"]}, missing)
assert cases["unavailable_required_statement"]["coordinate_value"] is None
assert cases["unavailable_required_statement"]["coordinate_identification_bounds"] == [0.0, 0.84]
cases["unavailable_alternative_path_member"] = conventional(formula, missing)
assert cases["unavailable_alternative_path_member"]["coordinate_value"] is None
assert cases["unavailable_alternative_path_member"]["coordinate_identification_bounds"] == [0.72, 0.84]
cases["no_data"] = conventional(formula, {x: None for x in values})
assert cases["no_data"]["coordinate_value"] is None
assert cases["no_data"]["coordinate_identification_bounds"] == [0.0, 1.0]
cases["opposed_requirement_with_other_missing"] = conventional({"all_of": ["first_step", "second_step"]}, {**missing, "first_step": -0.2})
assert cases["opposed_requirement_with_other_missing"]["signed_value"] is None
same(cases["opposed_requirement_with_other_missing"]["coordinate_value"], 0.0)

cases["synonym_repetition"] = conventional(
    {"all_of": ["first_step", "first_step_alias", "second_step"]},
    values,
    {"first_step_alias": "first_step"},
)
assert cases["synonym_repetition"] == cases["required_both"]
cases["whole_branch_repeated"] = conventional({"any_of": [formula, formula]}, values)
assert cases["whole_branch_repeated"] == cases["complete_candidate"]
cases["narrow_condition_scope"] = conventional("first_step", values)
same(cases["narrow_condition_scope"]["coordinate_value"], 0.84)
cases["broad_two_condition_scope"] = conventional({"all_of": ["first_step", "second_step"]}, values)
same(cases["broad_two_condition_scope"]["coordinate_value"], 0.42)

cases["same_statement_revised_after_contrary_data"] = conventional(formula, {**values, "direct": 0.10})
same(cases["same_statement_revised_after_contrary_data"]["coordinate_value"], 0.42)
cases["input_bounds"] = conventional(formula, {**values, "direct": [0.60, 0.78]})
assert cases["input_bounds"]["coordinate_value"] is None
assert cases["input_bounds"]["coordinate_identification_bounds"] == [0.60, 0.78]

identity = [[1.0, 0.0], [0.0, 1.0]]
cases["joint_independent_conjunction"] = joint_two([2, 3], identity, "all_of")
same(cases["joint_independent_conjunction"]["profile_log_ratio"], 2.0)
cases["joint_independent_disjunction"] = joint_two([2, 3], identity, "any_of")
same(cases["joint_independent_disjunction"]["profile_log_ratio"], 6.5)
cases["joint_one_opposed_conjunction"] = joint_two([-2, 3], identity, "all_of")
same(cases["joint_one_opposed_conjunction"]["profile_log_ratio"], -2.0)
cases["joint_one_opposed_disjunction"] = joint_two([-2, 3], identity, "any_of")
same(cases["joint_one_opposed_disjunction"]["profile_log_ratio"], 4.5)

# log(A/B) and log(A/C), sharing the SAME observed log(A):
# independent native log-rate estimates (3,1,0), each known variance 1.
shared = [[2.0, 1.0], [1.0, 2.0]]
cases["shared_numerator_joint_disjunction"] = joint_two([2, 3], shared, "any_of")
same(cases["shared_numerator_joint_disjunction"]["profile_log_ratio"], 7 / 3)
cases["shared_numerator_joint_conjunction"] = joint_two([2, 3], shared, "all_of")
same(cases["shared_numerator_joint_conjunction"]["profile_log_ratio"], 1.0)
cases["incorrect_independent_ratio_counterfactual"] = joint_two([2, 3], [[2.0, 0.0], [0.0, 2.0]], "any_of")
same(cases["incorrect_independent_ratio_counterfactual"]["profile_log_ratio"], 3.25)
cases["conventional_marginal_ratio_disjunction"] = conventional(
    {"any_of": ["ratio_ab", "ratio_ac"]},
    {"ratio_ab": math.tanh(1 / 2), "ratio_ac": math.tanh(2.25 / 2)},
)
assert cases["shared_numerator_joint_disjunction"]["coordinate_value"] < cases["incorrect_independent_ratio_counterfactual"]["coordinate_value"]
assert cases["shared_numerator_joint_disjunction"]["coordinate_value"] != cases["conventional_marginal_ratio_disjunction"]["coordinate_value"]

# Domain, monotonicity, idempotence, and direct endpoint propagation checks.
# These are exact properties of this proposed convention, not probability claims.
property_checks = 0
grid = [-1.0, -0.8, 0.0, 0.2, 0.8, 1.0]
for x, y in itertools.product(grid, repeat=2):
    for op in ("all_of", "any_of"):
        result = conventional({op: ["x", "y"]}, {"x": x, "y": y})
        assert 0 <= result["coordinate_value"] <= 1
        same(conventional({op: ["x", "x"]}, {"x": x})["signed_value"], x)
        for x2 in grid:
            if x2 >= x:
                result2 = conventional({op: ["x", "y"]}, {"x": x2, "y": y})
                assert result2["signed_value"] >= result["signed_value"]
                property_checks += 1

results = {
    "status": "synthetic_arithmetic_only_unadopted",
    "case_count": len(cases),
    "monotonicity_comparisons": property_checks,
    "cases": cases,
    "notes": [
        "Input statement indexes are synthetic upstream outputs, not paper measurements.",
        "The negative covariance counterfactual is not used; unknown covariance is not assumed zero.",
        "The incorrect independent-ratio case is labeled a counterfactual error, not a proposed route.",
        "No production reader/scorer or scientific run was executed.",
    ],
}
(OUT / "arithmetic_001.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps({"case_count": len(cases), "monotonicity_comparisons": property_checks, "status": "passed"}))
for name in ("complete_candidate", "unavailable_required_statement", "joint_independent_conjunction", "joint_independent_disjunction", "shared_numerator_joint_disjunction", "incorrect_independent_ratio_counterfactual", "conventional_marginal_ratio_disjunction"):
    print(name, json.dumps(cases[name]))
