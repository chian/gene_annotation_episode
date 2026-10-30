"""Exact arithmetic for an unadopted A105 sensitivity study.

All operands are SYNTHETIC. This is a research calculation, not a reader,
production scorer, annotation-coordinate mapping, or scientific experiment.
Run with Python 3. Output is confined to this script's directory.
"""

from fractions import Fraction as F
from itertools import product
import json
import math
from pathlib import Path


FAMILIES = ("sequence", "structure", "placement", "site", "system")
DELTA = F(1, 10)  # Proposed continuous shape constant, not a measured effect.
SIGNED_B = (F(9, 10), F(-9, 10))


def arithmetic(values):
    observed = [x for x in values if x is not None]
    return None if not observed else sum(observed, F(0)) / len(observed)


def shifted_harmonic(values):
    observed = [x for x in values if x is not None]
    return (
        None
        if not observed
        else F(len(observed)) / sum((1 / (DELTA + x) for x in observed), F(0))
        - DELTA
    )


def interval_image(function, bounds):
    # Both functions are increasing in every component on [0,1].
    return function([p[0] for p in bounds]), function([p[1] for p in bounds])


def encoded(value):
    if value is None:
        return None
    if isinstance(value, F):
        return {"exact": str(value), "decimal": float(value)}
    if isinstance(value, (tuple, list)):
        return [encoded(x) for x in value]
    if isinstance(value, dict):
        return {key: encoded(x) for key, x in value.items()}
    return value


def case(name, values, *, interval_overrides=None, scope="full_declared_set", note=""):
    intervals = [(F(0), F(1)) if x is None else (x, x) for x in values]
    if interval_overrides:
        for index, interval in interval_overrides.items():
            intervals[index] = interval
    result = {
        "case": name,
        "synthetic": True,
        "scope": scope,
        "note": note,
        "values_in_family_order": list(values),
        "component_full_scope_identification_intervals": intervals,
        "observed_family_weight_fraction": F(sum(x is not None for x in values), len(values)),
    }
    for label, function in (("arithmetic", arithmetic), ("shifted_harmonic", shifted_harmonic)):
        point = function(values)
        low, high = interval_image(function, intervals)
        assert F(0) <= low <= high <= F(1)
        if point is not None:
            assert low <= point <= high
        signed = []
        for b in SIGNED_B:
            endpoints = sorted((b * low, b * high))
            signed.append({"B_source": b, "C_point": None if point is None else b * point,
                           "C_full_bounds": endpoints})
        result[label] = {"R_point": point, "R_full_bounds": (low, high), "signed": signed}
    return result


high = F(19, 20)
cases = [
    case("high_global_low_site", (high, high, high, F(1, 10), F(1))),
    case("high_global_zero_site_identity", (high, high, high, F(0), F(1)),
         note="Zero exact site identity is observed correspondence, not measured loss of activity."),
    case("site_unknown", (high, high, high, None, F(1)),
         note="Counterfactual loss of access to the site observation; not permission to discard a known low result."),
    case("unknown_site_removed_from_declared_scope", (high, high, high, F(1)),
         scope="different_four_family_scope",
         note="Fourth operand here is system. Scope-change diagnostic only; not the same five-family result."),
    case("high_global_low_system_similarity", (high, high, high, F(1), F(1, 10))),
    case("sequence_full_span_only", (F(180, 200), None, None, None, None),
         note="180 identical residues in the compared known 200-residue source and target spans."),
    case("sequence_small_region_known_full_lengths", (F(20, 200), None, None, None, None),
         note="20/20 identical observed positions, but both complete lengths are known to be 200; index is 20/200."),
    case("snippet_only_full_molecule_unknown", (None, None, None, None, None),
         note="20/20 identity supplies a snippet-scope index of 1. Full molecule length/coverage is unknown; no whole-molecule point."),
    case("site_full_ten_two_matches", (high, high, high, F(2, 10), F(1))),
    case("site_two_observed_both_match", (high, high, high, F(2, 2), F(1)),
         interval_overrides={3: (F(2, 10), F(1))},
         note="Two of ten predefined sites are observed and match; point uses 2/2, coverage is 2/10, full-site bounds [2/10,10/10]."),
    case("one_sequence_method", (F(9, 10), F(8, 10), F(7, 10), F(6, 10), F(9, 10))),
    case("two_sequence_methods", ((F(9, 10) + F(5, 10)) / 2, F(8, 10), F(7, 10), F(6, 10), F(9, 10))),
    case("two_sequence_methods_plus_duplicate", ((F(9, 10) + F(5, 10)) / 2, F(8, 10), F(7, 10), F(6, 10), F(9, 10)),
         note="Repeated representation of method A is deduplicated by measurement provenance, not numeric equality."),
    case("invalid_duplicate_counted_as_third_method", ((F(9, 10) + F(9, 10) + F(5, 10)) / 3,
                                                    F(8, 10), F(7, 10), F(6, 10), F(9, 10)),
         scope="invalid_duplicate_diagnostic",
         note="Deliberately wrong handling shown to quantify duplicate inflation; not a proposed alternative."),
]

by_name = {c["case"]: c for c in cases}
assert by_name["high_global_low_site"]["arithmetic"]["R_point"] == F(79, 100)
assert by_name["high_global_low_site"]["shifted_harmonic"]["R_point"] == F(127, 270)
assert by_name["site_unknown"]["arithmetic"]["R_point"] == F(77, 80)
assert by_name["site_unknown"]["arithmetic"]["R_full_bounds"] == (F(77, 100), F(97, 100))
for method in ("arithmetic", "shifted_harmonic"):
    assert by_name["two_sequence_methods"][method] == by_name["two_sequence_methods_plus_duplicate"][method]
    assert by_name["snippet_only_full_molecule_unknown"][method]["R_point"] is None
    assert by_name["snippet_only_full_molecule_unknown"][method]["R_full_bounds"] == (F(0), F(1))
    assert by_name["site_two_observed_both_match"][method]["R_full_bounds"][0] == by_name["site_full_ten_two_matches"][method]["R_point"]

# Useful algebraic properties, checked exactly on a finite grid; the report
# supplies the algebra rather than claiming that a grid proves them generally.
checked_vectors = 0
for values in product((F(0), F(1, 10), F(1, 2), F(1)), repeat=5):
    a = arithmetic(values)
    h = shifted_harmonic(values)
    assert F(0) <= h <= a <= F(1)
    checked_vectors += 1
for value in (F(0), F(1, 10), F(1, 2), F(9, 10), F(1)):
    assert shifted_harmonic((value,) * 5) == value
assert shifted_harmonic((F(1), F(1), F(1), F(0), F(1))) == F(4, 15)

ceilings = []
for site in (F(0), F(1, 10), F(1)):
    values = (F(1), F(1), F(1), site, F(1))
    ceilings.append({"fixed_site": site, "other_four_maximum": F(1),
                     "arithmetic": arithmetic(values), "shifted_harmonic": shifted_harmonic(values)})

artifact = {
    "status": "unadopted_research_sensitivity_only",
    "all_inputs": "SYNTHETIC; no published or target measurements supplied",
    "families": list(FAMILIES),
    "family_weights": [1, 1, 1, 1, 1],
    "shift_delta": DELTA,
    "system_similarity_native_illustrations": [
        {"r_system": str(value), "source_pH": 7.0,
         "target_pH": 7.0 + math.sqrt(-2.0 * math.log(float(value))),
         "proposed_reference_scale_pH_squared": 1.0,
         "squared_scaled_distance": -2.0 * math.log(float(value))}
        for value in (F(1), F(9, 10), F(1, 10))
    ],
    "cases": cases,
    "local_correspondence_ceilings": ceilings,
    "verification": {"rational_arithmetic": True, "finite_grid_vectors": checked_vectors,
                     "properties_checked": ["bounds", "H_not_above_A", "idempotence",
                                            "zero_site_is_not_veto", "duplicate_invariance",
                                            "positive_and_negative_source_index_interval_order"]},
}
destination = Path(__file__).with_name("sensitivity_arithmetic_001.json")
destination.write_text(json.dumps(encoded(artifact), indent=2) + "\n", encoding="utf-8")
print("SYNTHETIC exact-rational arithmetic: passed; 1024 grid vectors checked.")
for c in cases:
    columns = []
    for name in ("arithmetic", "shifted_harmonic"):
        point = c[name]["R_point"]
        low, high = c[name]["R_full_bounds"]
        point_text = "unknown" if point is None else f"{float(point):.9f} ({point})"
        columns.append(f"{name}: {point_text}; bounds [{float(low):.9f},{float(high):.9f}]")
    print(c["case"] + " | " + " | ".join(columns))
print("Output:", destination)
