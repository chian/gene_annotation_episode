"""One-off synthetic arithmetic check; not a reader, scorer or scientific run."""

from fractions import Fraction as F
from itertools import product
from math import isclose, sqrt
from pathlib import Path
from statistics import NormalDist
import json


def fraction_record(value):
    return {"exact": str(value), "decimal": float(value)}


def synthetic_row(w, k, r, c, bp, br, h):
    theta = (w - k) / (w + k)
    rescue = max(F(0), min(F(1), 1 - abs(r - w) / abs(w - k)))
    isolation = min(
        max(F(0), min(F(1), 1 - bp / abs(w - k))),
        max(F(0), min(F(1), 1 - br / abs(r - k))),
    )
    source_effect = theta * rescue * c * isolation
    return {
        "theta": theta,
        "rescue": rescue,
        "comparability": c,
        "isolation": isolation,
        "H": h,
        "a": source_effect,
        "q": h * source_effect,
    }


H = F(54, 125)
row_a1 = synthetic_row(F(100), F(20), F(90), F(9, 10), F(8), F(7), H)
row_b1 = synthetic_row(F(80), F(40), F(75), F(9, 10), F(4), F(7, 2), H)
row_a2 = synthetic_row(F(60), F(100), F(70), F(4, 5), F(0), F(0), F(4, 5))
assert row_a1["q"] == F(5103, 25000)
assert row_b1["q"] == F(5103, 50000)
assert row_a2["q"] == -F(3, 25)
assert row_a1["q"] == 2 * row_b1["q"]

total_H = H + F(4, 5)
denominator = max(F(1), total_H)
numerator = row_a1["q"] + row_a2["q"]
statement_a = numerator / denominator
statement_b = row_b1["q"]
candidate = min(statement_a, statement_b)
assert candidate == F(2103, 30800)
assert denominator == F(154, 125)
assert numerator == F(2103, 25000)
assert candidate < statement_b

zero_correspondence_append = (numerator + F(0)) / max(F(1), total_H + F(0))
assert zero_correspondence_append == candidate
measured_zero_append = row_a1["q"] / denominator
missing_lower = (row_a1["q"] - F(4, 5)) / denominator
missing_upper = (row_a1["q"] + F(4, 5)) / denominator
assert measured_zero_append == F(729, 4400)

theta_need = F(3, 197)
necessity_point = -(F(1, 3) - theta_need) * F(19, 20) * F(9, 10)
necessity_lower = -(F(1, 3) + F(1, 50)) * F(19, 20) * F(9, 10)
necessity_upper = -(F(1, 3) - F(1, 20)) * F(19, 20) * F(9, 10)
assert necessity_lower == -F(3021, 10000)
assert necessity_upper == -F(969, 4000)

raw_vectors = [
    [98, 18, 88, 78, 38, 73],
    [100, 20, 90, 80, 40, 75],
    [102, 22, 92, 82, 42, 77],
]
means_three = [sum(column) / 3 for column in zip(*raw_vectors)]
means_six = [sum(column) / 6 for column in zip(*(raw_vectors + raw_vectors))]
assert means_three == means_six == [100, 20, 90, 80, 40, 75]
z = NormalDist().inv_cdf(0.975)


def joint_fixture(h, delta):
    a1 = 56.7 * h / (120 + 2 * delta)
    b1 = 28.35 * h / (120 + 2 * delta)
    pooled_a = (a1 - 0.12) / max(1.0, h + 0.8)
    return {"a1_q": a1, "b1_q": b1, "A": pooled_a, "B": b1,
            "candidate": min(pooled_a, b1)}


bounds = {}
for n in (3, 6):
    halfwidth = z * 2 / sqrt(n)
    lower = joint_fixture(0.378, halfwidth)
    upper = joint_fixture(0.486, -halfwidth)
    # The document supplies the analytic proof. This grid is only a diagnostic.
    for hi, di in product(range(11), repeat=2):
        test_h = 0.378 + (0.486 - 0.378) * hi / 10
        test_delta = -halfwidth + 2 * halfwidth * di / 10
        observed = joint_fixture(test_h, test_delta)["candidate"]
        assert lower["candidate"] - 1e-14 <= observed <= upper["candidate"] + 1e-14
    bounds[str(n)] = {
        "n_biological": n,
        "known_block_variance": 4,
        "every_mean_covariance_entry": 4 / n,
        "z": z,
        "delta_halfwidth": halfwidth,
        "lower_corner": lower,
        "upper_corner": upper,
        "candidate_point": float(candidate),
        "coordinate": lower["candidate"],
    }

assert isclose(bounds["3"]["coordinate"], 0.04423852311606068, abs_tol=1e-15)
assert isclose(bounds["6"]["coordinate"], 0.04581073927568406, abs_tol=1e-15)
assert bounds["6"]["coordinate"] > bounds["3"]["coordinate"]
assert bounds["6"]["upper_corner"]["candidate"] < bounds["3"]["upper_corner"]["candidate"]
duplicate_report_coordinate = bounds["3"]["coordinate"]
assert duplicate_report_coordinate == bounds["3"]["coordinate"]
unobserved_h_upper = joint_fixture(0.54, -bounds["3"]["delta_halfwidth"])["candidate"]
assert isclose(unobserved_h_upper, 0.10832192844881446, abs_tol=1e-15)

# Exact check of the proposed finite vertex/hyperplane enumeration on a box
# spanning T=1. This is a numerical checker for the documented equation only.
h_boxes = [(F(1, 5), F(3, 5)), (F(1, 5), F(4, 5))]
a_fixed = [F(1, 2), -F(1, 4)]
vertices = set(product(*h_boxes))
for free in range(2):
    other = 1 - free
    for fixed in h_boxes[other]:
        remaining = F(1) - fixed
        if h_boxes[free][0] <= remaining <= h_boxes[free][1]:
            entry = [F(0), F(0)]
            entry[other] = fixed
            entry[free] = remaining
            vertices.add(tuple(entry))
vertex_values = [
    sum(hh * aa for hh, aa in zip(v, a_fixed)) / max(F(1), sum(v))
    for v in vertices
]
vertex_lo, vertex_hi = min(vertex_values), max(vertex_values)
assert vertex_lo == -F(1, 10)
assert vertex_hi == F(1, 4)
for i, j in product(range(21), repeat=2):
    h1 = h_boxes[0][0] + (h_boxes[0][1] - h_boxes[0][0]) * F(i, 20)
    h2 = h_boxes[1][0] + (h_boxes[1][1] - h_boxes[1][0]) * F(j, 20)
    val = (h1*a_fixed[0] + h2*a_fixed[1])/max(F(1), h1+h2)
    assert vertex_lo <= val <= vertex_hi

results = {
    "status": "checked_synthetic_arithmetic_only",
    "production_reader_status": "unimplemented",
    "row_a1": {k: fraction_record(v) for k, v in row_a1.items()},
    "row_b1": {k: fraction_record(v) for k, v in row_b1.items()},
    "row_a2": {k: fraction_record(v) for k, v in row_a2.items()},
    "candidate_point": fraction_record(candidate),
    "statement_A_numerator": fraction_record(numerator),
    "statement_A_denominator": fraction_record(denominator),
    "zero_correspondence_append": fraction_record(zero_correspondence_append),
    "old_mean_irrelevant_append": fraction_record(row_a1["q"] / 2),
    "measured_zero_append": fraction_record(measured_zero_append),
    "missing_result_bounds": [fraction_record(missing_lower), fraction_record(missing_upper)],
    "necessity": {
        "point": fraction_record(necessity_point),
        "lower": fraction_record(necessity_lower),
        "upper": fraction_record(necessity_upper),
    },
    "sampling_and_candidate_bounds": bounds,
    "missing_shared_H": {
        "point": None, "candidate_lower": -0.12,
        "candidate_upper": unobserved_h_upper,
        "coordinate": None, "coordinate_bounds": [0, unobserved_h_upper],
    },
    "finite_box_enumeration": {
        "vertex_count": len(vertices),
        "lower": fraction_record(vertex_lo), "upper": fraction_record(vertex_hi),
    },
    "limitations": [
        "All data and the known sampling model are synthetic.",
        "Grid checks are diagnostics; analytic extrema are proved in the document.",
        "No primary-source inspection, biological calibration or runtime execution.",
        "No proposed pooling convention has been adopted.",
    ],
}
destination = Path(__file__).with_name("ARITHMETIC_RESULTS_001.json")
if destination.exists():
    raise SystemExit("Preserve the existing result: choose a new additive result filename.")
destination.write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps({
    "checked": True,
    "output": str(destination),
    "candidate_point": float(candidate),
    "three_block_coordinate": bounds["3"]["coordinate"],
    "six_block_coordinate": bounds["6"]["coordinate"],
    "finite_box_vertices": len(vertices),
}))
