"""Additional source-free projection checks; no reader/production imports."""
import json
import math
from pathlib import Path


def projected(bounds):
    lo, hi = bounds
    if not (-1 <= lo <= hi <= 1):
        raise ValueError("invalid bounded signed interval")
    clo, chi = max(0.0, lo), max(0.0, hi)
    return {"K": lo if lo == hi else None, "K_bounds": [lo, hi],
            "c": clo if clo == chi else None, "c_bounds": [clo, chi]}


negative = projected([math.tanh(-2-math.atanh(.4)), math.tanh(-2+math.atanh(.4))])
crossing = projected([-.2, .3])
unknown = projected([-1, 1])
point = projected([.2, .2])
assert negative["K"] is None
assert negative["c"] == 0 and negative["c_bounds"] == [0, 0]
assert crossing["K"] is None
assert crossing["c"] is None and crossing["c_bounds"] == [0, .3]
assert unknown["K"] is None
assert unknown["c"] is None and unknown["c_bounds"] == [0, 1]
assert point["K"] == .2
assert point["c"] == .2 and point["c_bounds"] == [.2, .2]

artifact = {"all_inputs": "synthetic", "checks_passed": 8,
            "entirely_negative": negative, "crossing": crossing,
            "all_unknown": unknown, "known_point": point}
output = Path(__file__).with_name("projection_boundary_002.json")
output.write_text(json.dumps(artifact, indent=2, allow_nan=False) + "\n")
print("PASS: 8 projection-boundary assertions; wrote " + output.name)
