"""Research-only synthetic checks; no reader or native program execution."""
from itertools import product
from math import isclose
from pathlib import Path
import json


def check_equal(actual, expected):
    assert isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), (actual, expected)


# Included HMMER result is unavailable. Enclose every possible M/O pair.
lower = 0.5 * 0.6
upper = 0.5 * 0.6 + 0.5
for own, opposing in product([0.0, 0.1, 0.5, 0.9, 1.0], repeat=2):
    value = 0.5 * 0.6 + 0.5 * own * (1.0 - opposing)
    assert lower <= value <= upper
check_equal(lower, 0.3)
check_equal(upper, 0.8)
qualified_bounds = [lower * 0.8, upper * 0.8]
check_equal(qualified_bounds[0], 0.24)
check_equal(qualified_bounds[1], 0.64)

# One disputed label has two mutually exclusive interpretations.
label_assignments = {
    "ambiguous_reference_supports_F": max(0.4, 0.7),
    "ambiguous_reference_supports_G": 0.4 * (1.0 - 0.7),
}
label_bounds = [0.4 * (1.0 - 0.7), max(0.4, 0.7)]
check_equal(min(label_assignments.values()), label_bounds[0])
check_equal(max(label_assignments.values()), label_bounds[1])

# A complete report with no recorded hit is an empty observed set, not
# an unknown included analysis and not proof of biological absence.
empty_observed_maximum = max([0.0])
check_equal(empty_observed_maximum, 0.0)

receipt = {
    "status": "passed_synthetic_research_arithmetic_only",
    "origin": "synthetic",
    "native_programs_or_production_readers_executed": False,
    "included_unavailable_channel": {
        "point": None,
        "C_bounds": [lower, upper],
        "A": 0.8,
        "V": 1.0,
        "qualified_bounds": qualified_bounds,
        "enclosed_sampled_M_O_pairs": 25,
        "separate_blast_only_C": 0.6,
        "separate_blast_only_Q": 0.48,
    },
    "mutually_exclusive_label_assignments": label_assignments,
    "ambiguous_label_C_bounds": label_bounds,
    "empty_complete_report_observed_set_index": empty_observed_maximum,
    "checks": [
        "unavailable included channel conservative enclosure",
        "exclusive uncertain-label assignments",
        "empty complete report is recorded-set zero only",
    ],
}
output = Path(__file__).with_name("missing_membership_arithmetic_003.json")
if output.exists():
    raise SystemExit("Refusing to overwrite an existing research receipt")
output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": receipt["status"], "receipt": str(output),
                  "check_groups": len(receipt["checks"])}))
