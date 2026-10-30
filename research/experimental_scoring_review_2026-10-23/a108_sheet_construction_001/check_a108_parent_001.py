"""Independent arithmetic for the explicitly synthetic A108 fixture."""
from fractions import Fraction as F
from pathlib import Path
import itertools
import json
import math

rows = [
    (1, 1, 5, .5), (2, 1, 4, .3), (3, 1, 2, .4),
    (4, 1, 5, 5), (5, 1, 3, .5), (6, 1, 1, .5),
    (7, 1, 6, .6), (8, 1, 9, .9), (9, 0, 5, .5), (10, 0, 4, .4),
]
events = {i: (bool(access), 2.5 <= concentration <= 10, 0 <= oxygen <= 1) for i, access, concentration, oxygen in rows}
checks = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


joint = F(sum(all(event) for event in events.values()), len(events))
check("actual joint fraction", joint == F(1, 2))
for order in itertools.permutations(range(3)):
    numerator = len(events)
    product = F(1)
    passed = set(events)
    for variable in order:
        denominator = numerator
        passed = {i for i in passed if events[i][variable]}
        numerator = len(passed)
        product *= F(numerator, denominator)
    check(f"conditional-chain identity {order}", product == joint)

marginals = [F(sum(row[j] for row in events.values()), len(events)) for j in range(3)]
check("marginal product differs", math.prod(marginals) == F(72, 125) != joint)
joint_marginal_bounds = [max(F(0), sum(marginals) - 2), min(marginals)]
check("unpaired marginal bounds", joint_marginal_bounds == [F(1, 2), F(4, 5)])
measurement = (F(42, 10) - F(2, 10)) / F(8, 10)
measurement_bounds = [(F(41, 10) - F(21, 100)) / F(82, 100), (F(43, 10) - F(19, 100)) / F(78, 100)]
check("measurement point", measurement == 5)
check("measurement exact bounds", measurement_bounds == [F(389, 82), F(137, 26)])
check("measurement uncertainty stays supported", F(5, 2) < measurement_bounds[0] < measurement_bounds[1] < 10)

base = {i: (int(all(event)), int(all(event))) for i, event in events.items()}
scenarios = {}
for label, replacements in {
    "complete": {},
    "unit_3_boundary_unknown": {3: (0, 1)},
    "unit_2_conflict": {2: (0, 1)},
    "all_missing": {i: (0, 1) for i in events},
}.items():
    observed = base | replacements
    lower, upper = (F(sum(v[j] for v in observed.values()), len(observed)) for j in range(2))
    masses = [lower, upper-lower, 1-upper]
    check(f"mass conservation {label}", sum(masses) == 1 and all(value >= 0 for value in masses))
    scenarios[label] = {"lower": float(lower), "upper": float(upper), "point": float(lower) if lower == upper else None}
check("missing boundary bounds", scenarios["unit_3_boundary_unknown"] == {"lower": .5, "upper": .6, "point": None})
check("conflict bounds", scenarios["unit_2_conflict"] == {"lower": .4, "upper": .5, "point": None})
check("all missing is no point", scenarios["all_missing"] == {"lower": 0., "upper": 1., "point": None})
deduplicated = {row[0]: row for row in rows + [rows[0], rows[0]]}
check("duplicate neutrality", len(deduplicated) == len(rows) and list(deduplicated.values()) == rows)
epsilon = math.sqrt(math.log(40)/20)
interval = [.5-epsilon, .5+epsilon]
check("sampling interval", all(math.isclose(a,b,abs_tol=1e-12) for a,b in zip(interval,[.07053059165326242,.9294694083467376])))

output = {
    "origin": "synthetic_fixture_only",
    "source_inspection": "No new primary paper or paper-specific packet; mathematical review of the joined proposal",
    "joint_fraction": float(joint), "unpaired_marginal_product_not_a_score": float(math.prod(marginals)),
    "unpaired_joint_bounds": list(map(float, joint_marginal_bounds)),
    "concentration_mM": float(measurement), "concentration_bounds_mM": list(map(float,measurement_bounds)),
    "conditional_sampling_interval": interval, "scenarios": scenarios,
    "assertions_passed": len(checks), "checks": checks,
}
with Path(__file__).with_name("parent_arithmetic_001.json").open("x") as stream:
    json.dump(output, stream, indent=2, allow_nan=False)
    stream.write("\n")
print(json.dumps(output, indent=2))
