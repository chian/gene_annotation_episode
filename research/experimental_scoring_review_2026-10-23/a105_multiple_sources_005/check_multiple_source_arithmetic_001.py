"""Research arithmetic only: synthetic, unadopted A105 cross-source convention.

No project scorer/reader/runtime imports. Run with Python 3's standard library.
The written JSON contains only this file's declared synthetic inputs/results.
"""

import json
import math
from pathlib import Path


def close(actual, expected, tolerance=1e-12):
    assert math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance), (
        actual,
        expected,
    )


def mean(values):
    assert values
    return math.fsum(values) / len(values)


def source_score(effect, variance):
    assert variance > 0
    s = math.copysign(effect * effect / (2 * variance), effect)
    return {"effect": effect, "variance": variance, "S": s, "B": math.tanh(s / 2)}


def two_common_effects(y1, y2, v1, v2, covariance):
    """Known-normal GLS, not a generic real-data pooling reader."""
    determinant = v1 * v2 - covariance * covariance
    assert determinant > 0
    precision = (v1 + v2 - 2 * covariance) / determinant
    effect = ((v2 - covariance) * y1 + (v1 - covariance) * y2) / (
        v1 + v2 - 2 * covariance
    )
    result = source_score(effect, 1 / precision)
    inverse = ((v2 / determinant, -covariance / determinant),
               (-covariance / determinant, v1 / determinant))

    def log_likelihood(theta):
        d = (y1 - theta, y2 - theta)
        return -0.5 * sum(d[i] * inverse[i][j] * d[j]
                          for i in range(2) for j in range(2))

    delta = log_likelihood(effect) - log_likelihood(0)
    close(abs(result["S"]), delta)
    return result


def cumulative_convention(ds):
    assert ds and all(-1 < d < 1 for d in ds)
    p = math.prod(1 + d for d in ds)
    q = math.prod(1 - d for d in ds)
    return (p - q) / (p + q)


def candidates(ds):
    return {"D": ds, "mean_M": mean(ds), "cumulative_K": cumulative_convention(ds)}


def product_interval(a, b):
    products = [x * y for x in a for y in b]
    return [min(products), max(products)]


def mean_interval(intervals):
    return [mean([x[0] for x in intervals]), mean([x[1] for x in intervals])]


def unique_originals(representations):
    """Checks declared synthetic identities; does not infer real identity."""
    originals = {}
    for row in representations:
        key = row["original_observation"]
        value = (row["source"], row["effect"], row["variance"])
        if key in originals:
            if originals[key] != value:
                raise ValueError("Conflicting representations of one original observation")
        originals[key] = value
    return originals


originals = [
    {"original_observation": "h1-preparation-1", "source": "H1", "effect": 2.0, "variance": 1.0},
    {"original_observation": "h1-preparation-2", "source": "H1", "effect": 2.0, "variance": 1.0},
    {"original_observation": "h2-preparation-1", "source": "H2", "effect": -2.0, "variance": 1.0},
]
h1 = two_common_effects(2, 2, 1, 1, 0)
h2 = source_score(-2, 1)

correspondence_inputs = {
    "H1": {
        "pair_score": 240, "source_self_score": 300, "target_self_score": 300,
        "TM_directions": [0.92, 0.9], "matching_sites": 7, "declared_sites": 10,
        "placement_support": 60, "tree_replicates": 100,
        "temperature_source_C": 25, "temperature_target_C": 25,
        "temperature_variance_scale_C_squared": 100,
    },
    "H2": {
        "pair_score": 90, "source_self_score": 300, "target_self_score": 300,
        "TM_directions": [0.45, 0.4], "matching_sites": 2, "declared_sites": 10,
        "placement_support": 10, "tree_replicates": 100,
        "temperature_source_C": 25, "temperature_target_C": 25,
        "temperature_variance_scale_C_squared": 100,
    },
}


def correspondence(inputs):
    components = {
        "sequence": 2 * inputs["pair_score"] / (inputs["source_self_score"] + inputs["target_self_score"]),
        "structure": min(inputs["TM_directions"]),
        "site": inputs["matching_sites"] / inputs["declared_sites"],
        "evolution": inputs["placement_support"] / inputs["tree_replicates"],
        "system": math.exp(-0.5 * (inputs["temperature_target_C"] - inputs["temperature_source_C"]) ** 2
                           / inputs["temperature_variance_scale_C_squared"]),
    }
    return {"components": components, "weights": {k: 1 for k in components},
            "R": mean(list(components.values()))}


r1 = correspondence(correspondence_inputs["H1"])
r2 = correspondence(correspondence_inputs["H2"])
close(r1["R"], 0.8)
close(r2["R"], 0.4)
d1 = r1["R"] * h1["B"]
d2 = r2["R"] * h2["B"]
main = candidates([d1, d2])
close(main["mean_M"], 0.2332922008391738)
close(main["cumulative_K"], (d1 + d2) / (1 + d1 * d2))

repeated = originals + [dict(originals[0], representation="second paper")]
assert unique_originals(repeated) == unique_originals(originals)
assert len(unique_originals(repeated)) == 3
assert len({row["source"] for row in repeated}) == 2
conflict_detected = False
try:
    unique_originals(originals + [dict(originals[0], effect=3)])
except ValueError:
    conflict_detected = True
assert conflict_detected

for ds in ([d1], [d2], [d1, d2], [d1, -d2], [d1, -d1]):
    close(mean([-d for d in ds]), -mean(ds))
    close(cumulative_convention([-d for d in ds]), -cumulative_convention(ds))
    assert -1 <= mean(ds) <= 1
    assert -1 <= cumulative_convention(ds) <= 1
close(mean([d1]), d1)
close(cumulative_convention([d1]), d1)
close(mean([d1, -d1]), 0)
close(cumulative_convention([d1, -d1]), 0)

h1_first = source_score(2, 1)
one_preparation = candidates([0.8 * h1_first["B"], d2])
assert main["mean_M"] > one_preparation["mean_M"]
different_estimates = two_common_effects(2, 3, 1, 1, 0)
close(different_estimates["S"], 6.25)
assert different_estimates["S"] != source_score(2, 1)["S"] + source_score(3, 1)["S"]

h1_shared = two_common_effects(2, 2, 1, 1, 0.75)
close(h1_shared["variance"], 0.875)
close(h1_shared["S"], 16 / 7)
d1_shared = 0.8 * h1_shared["B"]
shared = candidates([d1_shared, d2])
close(shared["mean_M"], 0.17383074580700864)
g1 = 0.8 * (1 - h1_shared["B"] ** 2) * 2 / (4 * 0.875)
g2 = 0.4 * (1 - h2["B"] ** 2) * 2 / 4
v_diagonal = g1 * g1 * 0.875 + g2 * g2
v_shared = v_diagonal + 2 * g1 * g2 * 0.75
close(v_diagonal, 0.027596541524764595)
close(v_shared, 0.046900885356027)
for index, effect, variance, r, expected_derivative in (
    (0, 2.0, 0.875, 0.8, g1), (1, -2.0, 1.0, 0.4, g2)
):
    delta = 1e-6
    derivative = r * (source_score(effect + delta, variance)["B"] -
                      source_score(effect - delta, variance)["B"]) / (4 * delta)
    close(derivative, expected_derivative, 1e-9)

weak_inputs = {
    "pair_score": 60, "source_self_score": 300, "target_self_score": 300,
    "TM_directions": [0.2, 0.2], "matching_sites": 2, "declared_sites": 10,
    "placement_support": 20, "tree_replicates": 100,
    "temperature_source_C": 25, "temperature_target_C": 25 + math.sqrt(200 * math.log(5)),
    "temperature_variance_scale_C_squared": 100,
}
weak_r = correspondence(weak_inputs)
weak_source = source_score(math.sqrt(2 * math.log(3)), 1)
close(weak_source["B"], 0.5)
close(weak_r["R"], 0.2)
weak_d = weak_r["R"] * weak_source["B"]
close(weak_d, 0.1)
weak_ten = candidates([weak_d] * 10)

unknown_R2_D_bounds = product_interval([h2["B"], h2["B"]], [0, 1])
unknown_R2_M = mean_interval([[d1, d1], unknown_R2_D_bounds])
unknown_B2_D_bounds = product_interval([-1, 1], [0.4, 0.4])
unknown_B2_M = mean_interval([[d1, d1], unknown_B2_D_bounds])
observed_r1 = [value for family, value in r1["components"].items() if family != "evolution"]
missing_tree_R_available = mean(observed_r1)
missing_tree_R_full = [sum(observed_r1) / 5, (sum(observed_r1) + 1) / 5]
missing_tree_D_full = product_interval([h1["B"], h1["B"]], missing_tree_R_full)
missing_tree_M_full = mean_interval([missing_tree_D_full, [d2, d2]])
missing_tree_M_conditional = mean([h1["B"] * missing_tree_R_available, d2])
close(missing_tree_R_available, 0.85)
close(missing_tree_M_conditional, 0.2573928903410692)
assert unknown_R2_D_bounds[0] < 0 and unknown_R2_D_bounds[1] == 0
assert missing_tree_M_full[0] < main["mean_M"] < missing_tree_M_full[1]

snippet = {
    "source_full_length": 200, "source_compared_span": 50, "target_supplied_span": 50,
    "target_full_length": None, "pair_score": 90, "source_span_self_score": 100,
    "target_span_self_score": 100, "declared_source_sites": 10,
    "observed_mapped_sites": 3, "exact_matches": 3,
}
snippet_r_sequence = 2 * 90 / (100 + 100)
snippet_r_site_observed = 3 / 3
snippet_r_site_full_bounds = [3 / 10, (3 + 10 - 3) / 10]
snippet_R = mean([snippet_r_sequence, snippet_r_site_observed])
snippet_D = snippet_R * h1["B"]
close(snippet_D, 0.915826201072026)

results = {
    "status": "all calculations synthetic; unadopted; no empirical calibration",
    "original_observations": originals,
    "source_H1": h1, "source_H2": h2,
    "native_ratios": {"H1": math.exp(2), "H2": math.exp(-2)},
    "correspondence_native_inputs": correspondence_inputs,
    "correspondence_H1": r1, "correspondence_H2": r2,
    "main_opposition": main,
    "positive_projection_after_combination": max(0, main["mean_M"]),
    "incorrect_per_source_clipping": mean([max(0, d1), max(0, d2)]),
    "concordant": candidates([d1, -d2]),
    "one_H1_preparation": one_preparation,
    "unequal_same_source_estimates_check": different_estimates,
    "duplicate_originals_unchanged": True,
    "conflicting_representation_detected": conflict_detected,
    "shared_calibration": {
        "common_calibration_variance": 0.75, "independent_noise_variance": 0.25,
        "original_observation_covariance": [[1, 0.75, 0.75], [0.75, 1, 0.75], [0.75, 0.75, 1]],
        "source_H1": h1_shared, "source_H2": h2, "candidates": shared,
        "pooled_source_covariance": [[0.875, 0.75], [0.75, 1]],
        "delta_gradient": [g1, g2], "delta_variance_without_cross_covariance": v_diagonal,
        "delta_variance_with_cross_covariance": v_shared,
    },
    "weak_source": {"assay": weak_source, "native_correspondence_inputs": weak_inputs,
                    "correspondence": weak_r, "ten_sources": weak_ten},
    "dense_cluster": {"positive_cluster_size": 10, "negative_cluster_size": 1,
                      "candidates": candidates([d1] * 10 + [d2]),
                      "leave_positive_cluster_out_mean": d2,
                      "leave_negative_cluster_out_mean": d1},
    "zero_relevance_dilution": {"H1_alone": d1, "with_zero_R_source": mean([d1, 0])},
    "missing_R2": {"full_point": None, "D2_domain_bounds": unknown_R2_D_bounds,
                   "complete_roster_mean_bounds": unknown_R2_M,
                   "known_source_subset_mean": d1},
    "missing_H2_uncertainty": {"full_point": None, "B2": None,
                              "complete_roster_mean_domain_bounds": unknown_B2_M},
    "missing_H1_evolution": {"R_available": missing_tree_R_available,
                             "R_full_bounds": missing_tree_R_full,
                             "conditional_mean": missing_tree_M_conditional,
                             "hypothetical_full_mean_bounds": missing_tree_M_full},
    "partial_target": {"inputs": snippet, "sequence_snippet": snippet_r_sequence,
                       "observed_site_fraction": snippet_r_site_observed,
                       "full_site_bounds": snippet_r_site_full_bounds,
                       "R_snippet": snippet_R, "D_snippet": snippet_D,
                       "R_whole_molecule": None},
}
destination = Path(__file__).with_name("arithmetic_001.json")
if destination.exists():
    raise FileExistsError("Preserve existing research output; use a new output name for another run")
destination.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")
print("Synthetic arithmetic checks passed; wrote", destination)
print("M:", main["mean_M"], "K:", main["cumulative_K"])
print("One-preparation comparison:", one_preparation)
