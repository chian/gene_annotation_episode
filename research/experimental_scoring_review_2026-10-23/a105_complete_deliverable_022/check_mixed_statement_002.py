"""One additional check for the explicitly proposed mixed-input statement join."""
from math import isclose, tanh
from pathlib import Path
import json

p = Path(__file__).resolve().parent
base = json.loads((p / "ARITHMETIC_RESULTS_001.json").read_text())
calibrated_B = base["specificity"]["B"]
uncalibrated_D = -.4*tanh(1)
P = max(0, calibrated_B, uncalibrated_D)
N = max(0, -calibrated_B, -uncalibrated_D)
D = P-N
assert isclose(D, .4409930421246242, rel_tol=0, abs_tol=3e-15)
result = {
    "origin": "synthetic; newly stipulated same-statement compatibility; no new measurements",
    "meaning": "conventional strongest-support minus strongest-opposition; not a likelihood",
    "inputs": {"one_complete_calibrated_block": calibrated_B, "one_distinct_uncalibrated_source": uncalibrated_D},
    "strongest_support": P, "strongest_opposition": N, "signed_statement_index": D,
    "profile_log_ratio": None, "checks_passed": 1,
    "scope": "Existing calibrated block and distinct source are stipulated to address the same target A/B contrast. Duplicate or competing model representations are not new inputs."
}
(p / "MIXED_STATEMENT_ARITHMETIC_002.json").write_text(json.dumps(result, indent=2)+"\n")
print(f"1 additional arithmetic check passed: conventional mixed-input statement index {D:.12f}")
