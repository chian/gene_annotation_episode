"""Independent research arithmetic, not a production scorer or reader.

Preserves the worker's historical script and outputs. Writes one new parent
receipt next to this file. All cohort values below are synthetic.
"""
import ast
import json
from fractions import Fraction as Q
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKER = HERE.parent / "a103_numerical_sheet_011"
checks = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def contrast(p, background):
    if not 0 <= p <= 1 or not 0 <= background <= 1:
        raise ValueError("frequency outside [0,1]")
    if p == background:
        return Q(0)
    return ((p - background) / (1 - background)
            if p > background else (p - background) / background)


def cohort_cell(strata):
    # Tuples: foreground positive/total, background positive/total.
    for k, n, k0, n0 in strata:
        if not (0 <= k <= n and 0 <= k0 <= n0):
            raise ValueError("invalid counts")
    n_total = sum(s[1] for s in strata)
    n0_total = sum(s[3] for s in strata)
    if not n_total or not n0_total:
        return {"overlap": None, "matched_contrast": None,
                "contribution": None, "reason": "empty_population"}
    overlap = Q(0)
    contribution = Q(0)
    for k, n, k0, n0 in strata:
        common_share = min(Q(n, n_total), Q(n0, n0_total))
        overlap += common_share
        if common_share == 0:
            # Neither the unknown frequency nor the unknown contrast is set
            # to zero. There is zero common mass to contribute to this index.
            continue
        contribution += common_share * contrast(Q(k, n), Q(k0, n0))
    return {"overlap": overlap,
            "matched_contrast": contribution / overlap if overlap else None,
            "contribution": contribution,
            "reason": None if overlap else "no_common_strata"}


def coordinate(contributions, weights):
    if not contributions:
        return None
    if len(contributions) != len(weights) or sum(weights) != 1:
        raise ValueError("weights must match questions and sum to one")
    if any(w < 0 for w in weights) or any(abs(t) > 1 for t in contributions):
        raise ValueError("invalid weight or contribution")
    supporting = sum(w * max(t, 0) for t, w in zip(contributions, weights))
    opposing = sum(w * max(-t, 0) for t, w in zip(contributions, weights))
    return supporting, opposing, supporting * (1 - opposing)


q1 = cohort_cell([(2, 3, 0, 3), (2, 3, 1, 3)])
q2 = cohort_cell([(3, 3, 1, 2), (0, 1, 0, 2)])
q3 = cohort_cell([(0, 2, 1, 2), (1, 2, 1, 2)])
ts = [r["contribution"] for r in (q1, q2, q3)]
w = [Q(1, 3)] * 3
check("three published synthetic cells reproduced", ts == [Q(7, 12), Q(1, 2), Q(-1, 2)])
check("comparison extent distinct from within-stratum contrast",
      q2["overlap"] == Q(3, 4) and q2["matched_contrast"] == Q(2, 3))
check("support and opposition retained", coordinate(ts, w) == (Q(13, 36), Q(1, 6), Q(65, 216)))
lower = coordinate([ts[0], Q(-1), ts[2]], w)[2]
upper = coordinate([ts[0], Q(1), ts[2]], w)[2]
check("missing question bound reproduced", (lower, upper) == (Q(7, 72), Q(95, 216)))
check("empty question list not an observed zero", coordinate([], []) is None)

# Native score and combined score are distinct actual recorded input fields.
native = json.loads((WORKER / "string_ribk_pair.json").read_text())["selected_pair_rows"]
check("one exact pair retained", len(native) == 1)
check("exact unordered pair", {native[0]["stringId_A"], native[0]["stringId_B"]}
      == {"243232.MJ_0055", "243232.MJ_0056"})
nscore = Q(str(native[0]["nscore"]))
check("native neighborhood field only", nscore == Q(956, 1000)
      and nscore != Q(str(native[0]["score"])))
check("one question native compilation", coordinate([nscore], [Q(1)])[2] == nscore)

# Confirm the historical checker's missing edge case without running its writes.
tree = ast.parse((WORKER / "check_arithmetic.py").read_text())
function_nodes = [node for node in tree.body
                  if isinstance(node, ast.FunctionDef) and node.name in {"g", "count_question"}]
namespace = {"F": Q}
exec(compile(ast.Module(body=function_nodes, type_ignores=[]),
             "historical_a103_checker_functions", "exec"), namespace)
disjoint = [{"k": 1, "n": 1, "k0": 0, "n0": 0},
            {"k": 0, "n": 0, "k0": 1, "n0": 1}]
historical_failure = None
try:
    namespace["count_question"](disjoint)
except ZeroDivisionError:
    historical_failure = "ZeroDivisionError"
check("historical zero-overlap execution gap reproduced", historical_failure == "ZeroDivisionError")
disjoint_result = cohort_cell([(1, 1, 0, 0), (0, 0, 1, 1)])
check("zero overlap keeps contrast unestimated", disjoint_result == {
    "overlap": Q(0), "matched_contrast": None,
    "contribution": Q(0), "reason": "no_common_strata"})
check("empty background is unknown rather than zero", cohort_cell([(1, 1, 0, 0)])[
    "contribution"] is None)
check("partial overlap skips unobserved frequency", cohort_cell([
    (1, 2, 0, 2), (1, 2, 0, 0)])["contribution"] == Q(1, 4))
check("empty stratum adds no contribution", cohort_cell([
    (2, 3, 0, 3), (2, 3, 1, 3), (0, 0, 0, 0)]) == q1)

# Meaningful formula checks: corners, sign, arbitrary fixed unequal weights,
# and joint bounds. This does not prove biological calibration.
grid = [Q(i, 10) for i in range(-10, 11)]
for weights in ([Q(1, 3)] * 3, [Q(1, 2), Q(1, 3), Q(1, 6)]):
    bounded = True
    monotone = True
    for a in grid:
        for b in grid:
            values = [coordinate([a, t, b], weights)[2] for t in grid]
            bounded &= all(0 <= v <= 1 for v in values)
            monotone &= all(x <= y for x, y in zip(values, values[1:]))
    check(f"bounded coordinate for fixed weights {weights}", bounded)
    check(f"monotone coordinate for fixed weights {weights}", monotone)
check("frequency complement reverses direction", all(
    contrast(1 - Q(i, 10), 1 - Q(j, 10)) == -contrast(Q(i, 10), Q(j, 10))
    for i in range(11) for j in range(11)))


def encode(x):
    if isinstance(x, Q):
        return {"fraction": str(x), "decimal": float(x)}
    if isinstance(x, dict):
        return {k: encode(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [encode(v) for v in x]
    return x


receipt = {
    "kind": "parent_research_arithmetic_not_production_verification",
    "checks_passed": len(checks), "checks": checks,
    "synthetic_cells": [q1, q2, q3],
    "synthetic_totals": coordinate(ts, w),
    "missing_question_bounds": [lower, upper],
    "native_score": nscore,
    "historical_checker_edge_case": historical_failure,
    "zero_overlap": disjoint_result,
}
(HERE / "a103_parent_arithmetic_002.json").write_text(json.dumps(encode(receipt), indent=2) + "\n")
print(json.dumps({"checks_passed": len(checks), "synthetic_coordinate": str(coordinate(ts, w)[2]),
                  "native_coordinate": str(nscore), "historical_edge_case": historical_failure}))
