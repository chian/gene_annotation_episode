"""Source-free arithmetic checks; not a scorer, reader, or production import.

Every observation, allocation, missing-value range, and model here is synthetic.
Writes only the arithmetic artifact beside this file.
"""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path


CHECKS: list[str] = []


def check(condition: bool, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def close(actual: float, expected: float, name: str, tol: float = 3e-13) -> None:
    check(math.isclose(actual, expected, rel_tol=tol, abs_tol=tol), name)


def q_from_s_r(s: float, r: float) -> float:
    """atanh(r*tanh(s/2)), retaining the finite original s at saturation."""
    if not math.isfinite(s) or not math.isfinite(r) or not 0 <= r <= 1:
        raise ValueError("finite original S and R in [0,1] required")
    if r == 0 or s == 0:
        return 0.0
    if r == 1:
        return s / 2
    a = abs(s)
    if a < 20:
        return math.atanh(r * math.tanh(s / 2))
    t = math.exp(-a)
    magnitude = 0.5 * (
        math.log((1 + r) + (1 - r) * t)
        - math.log((1 - r) + (1 + r) * t)
    )
    return math.copysign(magnitude, s)


def q_cell(s: float | None, r_bounds: tuple[float, float]) -> dict:
    """Exact box-domain bounds, not a probability or uncertainty imputation."""
    lo, hi = r_bounds
    if not (0 <= lo <= hi <= 1):
        raise ValueError("invalid R interval")
    if s is not None:
        a, b = q_from_s_r(s, lo), q_from_s_r(s, hi)
        lower, upper = min(a, b), max(a, b)
    else:
        upper = math.inf if hi == 1 else math.atanh(hi)
        lower = -upper
    return {
        "source_S": s,
        "R_bounds": [lo, hi],
        "q": lower if lower == upper else None,
        "q_lower": lower,
        "q_upper": upper,
    }


def validate_partition(blocks: list[list[int]], n: int) -> None:
    if n <= 0 or not blocks or any(not block for block in blocks):
        raise ValueError("a nonempty declared roster and partition are required")
    if sorted(i for block in blocks for i in block) != list(range(n)):
        raise ValueError("every distinct source must occur exactly once")


def combine(cells: list[dict], blocks: list[list[int]]) -> dict:
    validate_partition(blocks, len(cells))
    weights = [0.0] * len(cells)
    for block in blocks:
        for i in block:
            weights[i] = 1 / len(block)
    qlo = math.fsum(w * c["q_lower"] for w, c in zip(weights, cells))
    qhi = math.fsum(w * c["q_upper"] for w, c in zip(weights, cells))
    klo, khi = math.tanh(qlo), math.tanh(qhi)
    point = klo if qlo == qhi else None
    return {
        "blocks": blocks,
        "weights": weights,
        "Q": qlo if qlo == qhi else None,
        "K": point,
        "c": None if point is None else max(0.0, point),
        "Q_bounds": [qlo, qhi],
        "K_bounds": [klo, khi],
        "c_bounds": [max(0.0, klo), max(0.0, khi)],
        "sampling_variance": None,
        "sampling_variance_status": "joint sampling covariance not supplied",
    }


def partitions(n: int):
    """All set partitions; enumeration is a research check, not a reader."""
    if n == 0:
        yield []
        return
    for prior in partitions(n - 1):
        yield prior + [[n - 1]]
        for j in range(len(prior)):
            yield [block + [n - 1] if i == j else block[:] for i, block in enumerate(prior)]


def unknown_allocation(cells: list[dict]) -> dict:
    alternatives = [combine(cells, block) for block in partitions(len(cells))]
    lo = min(a["K_bounds"][0] for a in alternatives)
    hi = max(a["K_bounds"][1] for a in alternatives)
    return {
        "K": lo if lo == hi else None,
        "c": max(0.0, lo) if lo == hi else None,
        "K_bounds": [lo, hi],
        "c_bounds": [max(0.0, lo), max(0.0, hi)],
        "alternatives": alternatives,
        "bound_meaning": "hull of all partition-specific allowed values; no selected partition",
    }


def common_normal(rows: list[tuple[str, float, float]]) -> dict:
    """Canonicalize actual observation IDs, then fit one known-normal effect.

The zero between-observation covariance is an explicit synthetic model input.
"""
    observations: dict[str, tuple[float, float]] = {}
    for identity, value, variance in rows:
        if identity in observations and observations[identity] != (value, variance):
            raise ValueError("conflicting representations of one original observation")
        if not variance > 0:
            raise ValueError("positive known variance required")
        observations[identity] = (value, variance)
    precision = math.fsum(1 / v for _, v in observations.values())
    variance = 1 / precision
    mean = math.fsum(y / v for y, v in observations.values()) / precision
    s = math.copysign(mean * mean / (2 * variance), mean) if mean else 0.0
    return {"n_original": len(observations), "mean": mean, "variance": variance, "S": s, "B": math.tanh(s / 2)}


def safe_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        return "+infinity" if value > 0 else "-infinity"
    if isinstance(value, dict):
        return {k: safe_json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [safe_json(v) for v in value]
    return value


def main() -> None:
    base_h1 = [("h1-prep-1", 2.0, 1.0), ("h1-prep-2", 2.0, 1.0)]
    fit1 = common_normal(base_h1)
    fit2 = common_normal([("h2-prep-1", -2.0, 1.0)])
    close(fit1["S"], 4, "H1 source fit before combining sources")
    close(fit2["S"], -2, "H2 source fit before combining sources")
    r1 = math.fsum([2 * 240 / 600, min(.92, .90), 7 / 10, 60 / 100, 1]) / 5
    r2 = math.fsum([2 * 90 / 600, min(.45, .40), 2 / 10, 10 / 100, 1]) / 5
    close(r1, .8, "H1 five numerical correspondence components")
    close(r2, .4, "H2 five numerical correspondence components")
    h1, h2 = q_cell(fit1["S"], (r1, r1)), q_cell(fit2["S"], (r2, r2))
    d1, d2 = r1 * fit1["B"], r2 * fit2["B"]
    separate = combine([h1, h2], [[0], [1]])
    shared = combine([h1, h2], [[0, 1]])
    unknown_blocks = unknown_allocation([h1, h2])
    close(separate["K"], (d1 + d2) / (1 + d1 * d2), "two-singleton rational identity")
    close(shared["Q"], separate["Q"] / 2, "one-block coefficient is exactly one half")
    close(shared["K"], .34023335299867896, "opposing one-block checked value")
    check(unknown_blocks["K"] is None, "unknown allocation does not select a point")
    check(len(unknown_blocks["alternatives"]) == 2, "two sources have exactly two partitions")
    close(unknown_blocks["K_bounds"][0], shared["K"], "unknown allocation lower endpoint")
    close(unknown_blocks["K_bounds"][1], separate["K"], "unknown allocation upper endpoint")

    h2_positive = q_cell(2, (.4, .4))
    h2_weak = q_cell(.02, (.4, .4))
    weak_new_block = combine([h1, h2_weak], [[0], [1]])
    weak_same_block = combine([h1, h2_weak], [[0, 1]])
    h1_only = combine([h1], [[0]])
    check(weak_new_block["K"] > h1_only["K"], "positive new unit increases this convention")
    check(weak_same_block["K"] < h1_only["K"], "positive member can dilute its shared allocation")

    repeated_fit = common_normal(base_h1 + [base_h1[0]])
    check(repeated_fit == fit1, "same observation representation counts once")
    duplicated_input = combine([q_cell(repeated_fit["S"], (.8, .8)), h2], [[0], [1]])
    check(duplicated_input == separate, "duplicate cannot create a new cross-source contribution")
    distinct_equal = common_normal(base_h1 + [("h1-prep-3", 2.0, 1.0)])
    check(distinct_equal["n_original"] == 3, "equal numerical measurements are not duplicate identity")
    close(distinct_equal["S"], 6, "genuine extra preparation enters the source fit")
    try:
        common_normal(base_h1 + [("h1-prep-1", 3.0, 1.0)])
    except ValueError:
        check(True, "representation conflict is not averaged")
    else:
        check(False, "representation conflict is not averaged")

    cluster = [h1] * 10 + [h2]
    cluster_allocated = combine(cluster, [list(range(10)), [10]])
    all_singletons = combine(cluster, [[i] for i in range(11)])
    close(cluster_allocated["K"], separate["K"], "ten same-index members share one proposed unit")
    close(all_singletons["K"], .999999995150243, "separate-unit count amplification is exposed")

    opposite = q_cell(-4, (.8, .8))
    cancel = combine([h1, opposite], [[0], [1]])
    close(cancel["K"], 0, "opposing measurements retained then cancel")
    stronger_opposition = combine([h1, q_cell(-4, (1, 1))], [[0], [1]])
    check(stronger_opposition["K"] < 0 and stronger_opposition["c"] == 0, "negative K retained before nonnegative projection")

    known_r_zero = q_cell(None, (0, 0))
    close(known_r_zero["q"], 0, "known zero R annihilates unknown bounded B")
    zero_new_block = combine([h1, known_r_zero], [[0], [1]])
    zero_same_block = combine([h1, known_r_zero], [[0, 1]])
    close(zero_new_block["K"], h1_only["K"], "zero new block is inert")
    check(zero_same_block["K"] < h1_only["K"], "zero member dilutes a within-block mean")

    missing_r2 = combine([h1, q_cell(-2, (0, 1))], [[0], [1]])
    missing_s2 = combine([h1, q_cell(None, (.4, .4))], [[0], [1]])
    missing_family = combine([q_cell(4, (.68, .88)), h2], [[0], [1]])
    missing_family_available = combine([q_cell(4, (.85, .85)), h2], [[0], [1]])
    all_unknown = combine([q_cell(None, (0, 1)), q_cell(None, (0, 1))], [[0], [1]])
    all_unknown_allocations = unknown_allocation([q_cell(None, (0, 1)), q_cell(None, (0, 1))])
    check(all_unknown["K"] is None and all_unknown["K_bounds"] == [-1., 1.], "all-unknown exact closed bounds")
    check(all_unknown["c"] is None and all_unknown["c_bounds"] == [0., 1.], "all-unknown coordinate not imputed zero")
    check(all_unknown_allocations["K"] is None and all_unknown_allocations["K_bounds"] == [-1., 1.], "all-unknown including allocation")
    for name, result in [("R", missing_r2), ("source S", missing_s2), ("family", missing_family)]:
        check(result["K"] is None, f"missing {name} yields no full-basis point")
        check(result["K_bounds"][0] <= result["K_bounds"][1], f"missing {name} bounds ordered")
    for r in [0, .1, .4, .8, 1]:
        candidate = combine([h1, q_cell(-2, (r, r))], [[0], [1]])["K"]
        check(missing_r2["K_bounds"][0] - 1e-14 <= candidate <= missing_r2["K_bounds"][1] + 1e-14, f"missing R enclosure {r}")
    close(missing_r2["K_bounds"][0], math.tanh(h1["q"] - 1), "missing negative-source R exact lower")
    close(missing_r2["K_bounds"][1], d1, "missing negative-source R exact upper")

    source_first = common_normal([("p1", .8, .25)])
    source_second = common_normal([("p1", .8, .25), ("p2", .1, .25)])
    close(source_first["S"], 1.28, "first positive common-effect score")
    close(source_second["S"], .81, "second positive can lower common-effect directional evidence")
    check(source_second["B"] < source_first["B"], "no universal positive-observation monotonicity claim")
    separate_molecules = combine([q_cell(1.28, (1, 1)), q_cell(.02, (1, 1))], [[0], [1]])
    check(not math.isclose(separate_molecules["K"], source_second["B"]), "cross-source convention is not common-effect likelihood")

    saturated = [q_cell(1000, (1, 1)), q_cell(-1000, (1, 1))]
    saturation_cancel = combine(saturated, [[0], [1]])
    check(math.tanh(500) == 1 and math.tanh(-500) == -1, "double-precision B display saturation reproduced")
    close(saturated[0]["q"], 500, "original finite S retained at positive saturation")
    close(saturated[1]["q"], -500, "original finite S retained at negative saturation")
    close(saturation_cancel["K"], 0, "opposing saturated displays cancel using finite originals")
    q_saturation_r08 = q_from_s_r(1000, .8)
    close(q_saturation_r08, math.atanh(.8), "R below one has finite limiting q")

    for s, r in itertools.product([-1000, -40, -4, -2, 0, 2, 4, 40, 1000], [0, .1, .4, .8, 1]):
        q = q_from_s_r(s, r)
        check(math.isfinite(q), f"finite q for finite S={s}, R={r}")
        close(q, -q_from_s_r(-s, r), f"q sign symmetry S={s}, R={r}")
        if abs(s) <= 4:
            close(math.tanh(q), r * math.tanh(s / 2), f"single-source consistency S={s}, R={r}")
    for bad_s, bad_r in [(math.inf, .8), (math.nan, .8), (1, -1), (1, 1.1)]:
        try:
            q_from_s_r(bad_s, bad_r)
        except ValueError:
            check(True, f"invalid operands rejected {bad_s}, {bad_r}")
        else:
            check(False, f"invalid operands rejected {bad_s}, {bad_r}")
    for bad_blocks in [[[0], [0, 1]], [[0]], [[], [0, 1]]]:
        try:
            combine([h1, h2], bad_blocks)
        except ValueError:
            check(True, f"invalid partition rejected {bad_blocks}")
        else:
            check(False, f"invalid partition rejected {bad_blocks}")
    reverse = combine([q_cell(-4, (.8, .8)), q_cell(2, (.4, .4))], [[0], [1]])
    close(reverse["K"], -separate["K"], "full-statement sign reversal")
    permuted = combine([h2, h1], [[1], [0]])
    close(permuted["K"], separate["K"], "source and block permutation")

    # Verify interval endpoint monotonicity over a finite grid, distinct from
    # claiming statistical independence of the rectangular allowed input set.
    grid_cells = [q_cell(4, (.6, .9)), q_cell(-2, (.2, .7)), q_cell(.5, (.1, .8))]
    for block in [[[0], [1], [2]], [[0, 1], [2]], [[0, 1, 2]]]:
        envelope = combine(grid_cells, block)["K_bounds"]
        for r1g, r2g, r3g in itertools.product([.6, .75, .9], [.2, .45, .7], [.1, .45, .8]):
            value = combine([q_cell(4, (r1g, r1g)), q_cell(-2, (r2g, r2g)), q_cell(.5, (r3g, r3g))], block)["K"]
            check(envelope[0] - 1e-14 <= value <= envelope[1] + 1e-14, f"three-source interval grid {block}: {r1g}, {r2g}, {r3g}")

    artifact = {
        "status": "unadopted source-free arithmetic proposal; all inputs synthetic",
        "source_fits": {"H1": fit1, "H2": fit2, "genuinely_new_H1_preparation": distinct_equal},
        "source_correspondence": {"H1_components": [.8, .9, .7, .6, 1], "H2_components": [.3, .4, .2, .1, 1], "R1": r1, "R2": r2, "D1": d1, "D2": d2, "q1": h1["q"], "q2": h2["q"]},
        "examples": {
            "H1_only": h1_only, "opposing_separate_blocks": separate,
            "opposing_same_block": shared, "unknown_allocation": unknown_blocks,
            "positive_H2_separate": combine([h1, h2_positive], [[0], [1]]),
            "weak_positive_new_block": weak_new_block, "weak_positive_same_block": weak_same_block,
            "duplicate_representation": duplicated_input,
            "ten_positive_one_negative_two_blocks": cluster_allocated,
            "ten_positive_one_negative_eleven_blocks": all_singletons,
            "equal_opposition": cancel, "stronger_opposition": stronger_opposition,
            "known_zero_R_new_block": zero_new_block, "known_zero_R_same_block": zero_same_block,
            "unknown_R2": missing_r2, "unknown_source_S2": missing_s2,
            "unknown_one_family_full_basis": missing_family,
            "unknown_one_family_available_basis": missing_family_available,
            "all_unknown": all_unknown, "all_unknown_allocation": all_unknown_allocations,
            "saturated_display_cancellation": saturation_cancel,
        },
        "same_effect_positive_counterexample": {"first": source_first, "both": source_second, "different_molecule_convention": separate_molecules},
        "checks_passed": len(CHECKS), "checks": CHECKS,
    }
    path = Path(__file__).with_name("arithmetic_001.json")
    path.write_text(json.dumps(safe_json(artifact), indent=2, allow_nan=False) + "\n")
    print(f"PASS: {len(CHECKS)} arithmetic/domain checks; wrote {path.name}")
    for name in ["H1_only", "opposing_separate_blocks", "opposing_same_block", "weak_positive_new_block", "weak_positive_same_block", "ten_positive_one_negative_two_blocks", "ten_positive_one_negative_eleven_blocks", "stronger_opposition", "known_zero_R_same_block", "unknown_R2", "unknown_source_S2", "all_unknown", "saturated_display_cancellation"]:
        row = artifact["examples"][name]
        print(name, "K=", row["K"], "K_bounds=", row["K_bounds"], "c=", row["c"])


if __name__ == "__main__":
    main()
