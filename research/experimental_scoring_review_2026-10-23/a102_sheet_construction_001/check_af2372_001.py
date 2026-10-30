"""Research arithmetic only; no production scorer or scientific execution."""
from fractions import Fraction
import json
import math
from pathlib import Path


def descriptor(n, target_length, reference_length, rmsd, distance):
    values = (n, target_length, reference_length, rmsd, distance)
    if not all(math.isfinite(float(x)) for x in values):
        raise ValueError("Finite numerical inputs are required")
    if target_length <= 0 or reference_length <= 0 or distance <= 0:
        raise ValueError("Lengths and distance scale must be positive")
    if n < 0 or n > min(target_length, reference_length) or rmsd < 0:
        raise ValueError("Extent and RMSD are outside their domains")
    return (n / max(target_length, reference_length)) / (1 + (rmsd / distance) ** 2)


checks = []


def close(name, actual, expected):
    assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), name
    checks.append({"check": name, "passed": True, "value": actual})


close("target coverage", 209 / 252, float(Fraction(209, 252)))
close("distance 1 angstrom", descriptor(209, 252, 252, 1.5, 1), float(Fraction(209, 819)))
close("distance 2 angstrom", descriptor(209, 252, 252, 1.5, 2), float(Fraction(836, 1575)))
close("distance 3 angstrom", descriptor(209, 252, 252, 1.5, 3), float(Fraction(209, 315)))
close("unit invariance", descriptor(209, 252, 252, .15, .2), descriptor(209, 252, 252, 1.5, 2))
close("zero extent", descriptor(0, 252, 252, 1.5, 2), 0)
close("perfect full extent", descriptor(252, 252, 252, 0, 2), 1)
close("symmetric lengths", descriptor(209, 252, 300, 1.5, 2), descriptor(209, 300, 252, 1.5, 2))
for work, free, expected in [(.215, .273, .058), (.188, .212, .024), (.201, .288, .087), (.213, .244, .031), (.175, .210, .035)]:
    close(f"Rfree gap {work}/{free}", free - work, expected)

for bad in [(253, 252, 252, 1.5, 2), (209, 252, 252, -1.5, 2), (209, 252, 252, 1.5, 0), (209, 0, 252, 1.5, 2)]:
    try:
        descriptor(*bad)
    except ValueError:
        checks.append({"check": "reject out-of-domain input", "input": bad, "passed": True})
    else:
        raise AssertionError(bad)

result = {
    "kind": "research_arithmetic_receipt",
    "passed": len(checks),
    "checks": checks,
    "missing_factor_example": {
        "point": None,
        "bounds": [0, descriptor(209, 252, 252, 1.5, 2)],
        "meaning": "Conditional bound under an explicitly proposed multiplicative rule; not a confidence interval"
    }
}
target = Path(__file__).with_name("parent_arithmetic_001.json")
with target.open("x") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print(json.dumps({"passed": len(checks), "receipt": str(target)}))
