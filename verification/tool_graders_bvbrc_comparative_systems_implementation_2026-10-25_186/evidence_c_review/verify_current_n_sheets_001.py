"""Compare 27 current N→C values with the immutable root pre-review receipt."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import hashlib
import json

from gene_annotation_episode.bvbrc_comparative_systems_calculators import calculate_comparative_systems_components
from gene_annotation_episode.bvbrc_comparative_systems_calculation_contracts import validate_components
from gene_annotation_episode.bvbrc_comparative_systems_handoff_contracts import canonical_sha256

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
reference = BASE / "ROOT_N_TO_C_CHECK_001.json"
baseline = json.loads(reference.read_text())
receipt = {"basis": "current actual N sheets from retained source-executed synthetic inputs; no live service",
           "baseline_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(), "comparisons": [], "checks": 0}
for case in baseline:
    name = case["name"]
    path = BASE / "evidence_n" / (name + "_sheet_actual.json")
    native_bytes = path.read_bytes()
    sheet = json.loads(native_bytes)
    before = deepcopy(sheet)
    previous_path = BASE / "evidence_c" / (name + "_actual_builder_components_002.json")
    previous_bytes = previous_path.read_bytes()
    parameters = json.loads(previous_bytes)["parameters"]
    result = calculate_comparative_systems_components(sheet, parameters=parameters)
    # Root's pre-review receipt stores the file-byte digest; C stores canonical
    # JSON identity. They are intentionally different hash conventions.
    assert result["sheet_sha256"] == canonical_sha256(sheet)
    assert hashlib.sha256(native_bytes).hexdigest() == case["sheet_sha256"]
    by_id = {row["component_id"]: row for row in result["components"]}
    comparisons = []
    for expected in case["comparisons"]:
        component = by_id[expected["component_id"]]
        actual = component["value"]
        assert actual["state"] == expected["expected_state"]
        assert actual["value"] == expected["expected_value"]
        comparisons.append({"component_id": expected["component_id"], "expected_state": expected["expected_state"],
            "expected_value": expected["expected_value"], "actual_state": actual["state"], "actual_value": actual["value"],
            "qualification_codes": component["qualification_codes"]})
        receipt["checks"] += 1
    result_path = HERE / (name + "_current_n_components_001.json")
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    saved = json.loads(result_path.read_text())
    with patch("gene_annotation_episode.bvbrc_comparative_systems_calculators.calculate_comparative_systems_components",
               side_effect=AssertionError("saved validation must not recalculate")), \
         patch("gene_annotation_episode.bvbrc_comparative_systems_calculators._reported_formula",
               side_effect=AssertionError("saved validation must not rerun formulas")):
        assert validate_components(saved, sheet=sheet) == saved
    assert sheet == before
    assert path.read_bytes() == native_bytes and previous_path.read_bytes() == previous_bytes
    receipt["comparisons"].append({"name": name, "sheet_file_sha256": hashlib.sha256(native_bytes).hexdigest(),
        "canonical_sheet_sha256": result["sheet_sha256"], "previous_components_sha256": hashlib.sha256(previous_bytes).hexdigest(),
        "saved_components_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(), "values": comparisons,
        "saved_validation_without_recalculation": True, "original_sheet_and_components_unchanged": True,
        "source_documents": [{key: row[key] for key in ("document_id", "sha256", "byte_count", "basis")}
                             for row in sheet["source_documents"]]})
receipt["runtime_sources"] = [{"path": str(path.relative_to(BASE)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    for path in sorted((BASE / "candidate/gene_annotation_episode").glob("bvbrc_comparative_systems*.py"))
    if any(key in path.name for key in ("calculator", "calculation_contract", "sheet", "native", "handoff"))]
assert receipt["checks"] == 27
(HERE / "CURRENT_N_TO_C_CHECK_001.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("27 current N→C values exactly match the preserved root baseline; saved validation did not calculate.")
for case in receipt["comparisons"]:
    print(case["name"], {row["component_id"]: row["actual_value"] for row in case["values"]})
