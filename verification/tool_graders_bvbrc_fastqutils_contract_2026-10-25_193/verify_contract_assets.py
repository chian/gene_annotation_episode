"""Review-artifact verification only; no production grader is exercised."""
from pathlib import Path
import hashlib
import json
import math

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent
schema = json.loads((ROOT / "SCHEMAS_001.json").read_text())
examples = json.loads((ROOT / "NUMERICAL_EXAMPLES_001.json").read_text())
Draft202012Validator.check_schema(schema)
checks = []
request = json.loads((ROOT / "REQUEST_EXAMPLE_001.json").read_text())
Draft202012Validator.check_schema(request["requested_schema"])
for value in request["selections"].values():
    Draft202012Validator({**schema, "$ref": "#/$defs/FactSelection"}).validate(value)
checks.append("closed_actual_requested_schema_example")
for kind, value in (("Sheet", examples["shape_only_sheet"]), ("Components", examples["oracle_components"])):
    Draft202012Validator({**schema, "$ref": "#/$defs/" + kind}).validate(value)
    checks.append("finite_schema_" + kind)

def finite(node):
    if isinstance(node, float):
        assert math.isfinite(node)
    elif isinstance(node, dict):
        for v in node.values():
            finite(v)
    elif isinstance(node, list):
        for v in node:
            finite(v)

finite(examples)
checks.append("no_nonfinite_example_numbers")
components = {c["metric"]: c for c in examples["oracle_components"]["components"]}
for name, a, b in (("read_retention_fraction", 6, 8), ("base_retention_fraction", 108, 160), ("pair_retention_fraction", 3, 4)):
    assert components[name]["value"] == a / b
assert math.isclose(components["phred_implied_expected_errors"]["value"], 20 * 10**(-2) + 20 * 10**(-3))
assert math.isclose(components["phred_implied_error_fraction"]["value"], (20 * 10**(-2) + 20 * 10**(-3)) / 40)
assert components["mean_phred"]["value"] == (20 * 20 + 20 * 30) / 40
assert components["q_ge_threshold_fraction"]["value"] == 20 / 40
assert examples["zero_case"]["derived_retention"] is None
checks.append("hand_computed_numerical_oracle")

# Structural failures should not quietly become zeros or new metric names.
cell = dict(examples["shape_only_sheet"]["measurements"][0])
validator = Draft202012Validator({**schema, "$ref": "#/$defs/Cell"})
for updates in ({"state": "missing", "value": 0}, {"value": True}, {"metric": "annotation_confidence"}, {"extra": "invented"}):
    assert not validator.is_valid({**cell, **updates})
checks.append("reject_missing_zero_bool_arbitrary_metric_and_extra_field")
sources_checked = 0
for filename in ("SOURCE_RECEIPTS_001.json", "DOWNSTREAM_SOURCE_RECEIPTS_001.json", "HOSTILE_SOURCE_RECEIPTS_001.json", "HOSTILE_V110_RECEIPTS_001.json", "SAM_SOURCE_RECEIPTS_001.json"):
    value = json.loads((ROOT / filename).read_text())
    rows = value if isinstance(value, list) else value.get("sources", value.get("receipts", []))
    for row in rows:
        file = row.get("file") or row.get("retained_path")
        if file and row.get("sha256"):
            path = ROOT / file
            assert path.is_file()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
            sources_checked += 1
checks.append("retained_original_source_hashes")
receipt = {"identity": "review_artifact_validation_not_production_verification", "status": "passed",
    "checks": checks, "source_hashes_checked": sources_checked, "production_tests_run": 0,
    "genuine_service_artifact_tests": 0, "live_jobs": 0, "episode_path_verified": False,
    "limitations": ["Numerical sheet is an explicit shape-only controlled oracle.",
        "Schema validation does not establish scientific joins/custody.",
        "No production parser, calculator or provider exists from this task."]}
(ROOT / "VERIFICATION_001.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
print(json.dumps(receipt))
