"""Retain explicitly synthetic C4 examples using the actual adapter/calculators.

No scientific executable, network, model, Store or episode is invoked. Test
fixture helpers construct declared C4/H2 records; they claim no live custody.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from gene_annotation_episode import bvbrc_homology_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_homology_grader import calculate_homology_scores
from test_bvbrc_homology_bundle_adapter import c4_fixture, consume, F, G


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


fixture = c4_fixture()
bundle, content, values, parameters = fixture
selections = {
    "hits": {"metric": "reported_hit_count", "report_index": 0},
    "no_hit_query": {"metric": "reported_hit_count", "report_index": 1},
    "query_coverage": {"metric": "query_paired_coverage", "report_index": 0, "hit_index": 0},
    "reference_coverage": {"metric": "reference_paired_coverage", "report_index": 0, "hit_index": 0},
    "weights": {"metric": "conditional_function_weights", "report_index": 0},
    "missing": {"metric": "missing_requirements"},
}
form = adapter.requested_form_schema(selections)
result = consume(fixture, selections)
save("SYNTHETIC_INPUTS.json", {"provenance": "SYNTHETIC records and native-shaped fixture bytes; no live custody claim",
    "bundle": bundle, "supplied_values": values, "parameters": parameters, "requested_form": form})
native = HERE / "native"
native.mkdir(exist_ok=True)
for artifact in bundle["artifacts"]:
    (native / (artifact["role"] + ".bytes")).write_bytes(content[artifact["raw_artifact_ref"]])
save("SYNTHETIC_RESULT.json", result)
save("PARAMETERS_SCHEMA.json", adapter.PARAMETERS_SCHEMA)
recalculated = calculate_homology_scores(json.loads(json.dumps(result["sheet"])), database_model={"temperature_bits": 1})
save("SYNTHETIC_RECALCULATED_T1.json", recalculated)
early = deepcopy(fixture)
early[0]["artifacts"] = [a for a in early[0]["artifacts"] if a["role"] == "blast_json15_raw"]
early[1].clear()
raw = early[0]["artifacts"][0]
early[1][raw["raw_artifact_ref"]] = content[raw["raw_artifact_ref"]]
partial = consume(early, selections)
save("SYNTHETIC_PARTIAL_RESULT.json", partial)
checks = {
    "fixture_identity": "SYNTHETIC; actual pure parser/calculator code, no service or native program execution",
    "implementation_sha256": adapter.implementation_sha256(),
    "status": result["status"], "facts": result["facts"],
    "saved_sheet_temperature_1": recalculated["queries"][0]["conditional_function_weights"]["unadjusted_probabilities"],
    "before_metadata_status": partial["status"], "before_metadata_weights": partial["facts"]["weights"],
    "native_bytes_sha256": {a["role"]: hashlib.sha256(content[a["raw_artifact_ref"]]).hexdigest() for a in bundle["artifacts"]},
    "live_execution": False, "episode_path_verified_by_this_harness": False,
}
assert checks["status"] == "ok"
assert checks["facts"]["query_coverage"] == .6 and checks["facts"]["reference_coverage"] == .75
assert checks["facts"]["weights"] == [{"function": F, "weight": 2 / 3}, {"function": G, "weight": 1 / 3}]
assert checks["saved_sheet_temperature_1"] == {F: .8, G: .2}
assert checks["before_metadata_status"] == "partial" and checks["before_metadata_weights"] is None
save("CHECK_RESULTS.json", checks)
save("SOURCE_SHA256.json", {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in [
    *(ROOT / "gene_annotation_episode" / name for name in adapter._DEPENDENCIES),
    ROOT / "tests/test_bvbrc_homology_bundle_adapter.py",
    ROOT / "docs/TOOL_GRADER_BVBRC_HOMOLOGY_BUNDLE_ADAPTER_2026-10-24_001.md",
]})
print(json.dumps(checks, indent=2, sort_keys=True))
