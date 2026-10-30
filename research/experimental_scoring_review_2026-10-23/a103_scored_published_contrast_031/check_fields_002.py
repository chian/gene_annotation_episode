"""Additive field-format correction; preserves the first research output."""
import copy
import datetime
import json
from pathlib import Path

root = Path(__file__).resolve().parent
original = json.loads((root / "filled_cells.json").read_text())
record = copy.deepcopy(original)
formula = "../a103_complete_deliverable_023/NUMERICAL_SHEET.md#the-numerical-sheet"
printed = "FILLED_CONTRAST.md#actual-filled-sheet-cells"
output = "filled_cells_002.json"
manifest = json.loads((root / "request_manifest.json").read_text())

def update_cells(node):
    if isinstance(node, dict):
        if {"state", "point", "lower", "upper", "calculation_ref"} <= node.keys():
            node["calculation_ref"] = formula
            node["input_refs"] = [
                printed if x in {"t", "S", "O", "w=1", "direction=+1"} else x
                for x in node["input_refs"]
            ]
        for value in node.values():
            update_cells(value)
    elif isinstance(node, list):
        for value in node:
            update_cells(value)

update_cells(record)
native = record["context_questions"][0]["native"]
native["program_version"] = native["database_version"] = "12.5"
native["retrieval"]["timestamp"] = manifest["requests"]["network_002"]["response_saved_utc"]
result = record["result"]
q = result["question_results"][0]
q["E"]["units"] = "signed_index"
q["t"]["input_refs"] = [output + "#/context_questions/0/native/score", output + "#/context_questions/0/native/direction"]
result["supporting_total"]["input_refs"] = [output + "#/result/question_results/0/t", output + "#/result/question_results/0/weight"]
result["opposing_total"]["input_refs"] = list(result["supporting_total"]["input_refs"])
result["coordinate"]["input_refs"] = [output + "#/result/supporting_total", output + "#/result/opposing_total"]
result["source_component_links"][0]["coverage"] = "own_cross_case_read"
record["field_format_correction_ref"] = "FIELD_CORRECTIONS_002.md"

assert result["coordinate"]["point"] == original["result"]["coordinate"]["point"] == .844
assert q["E"]["state"] == "not_applicable" and q["E"]["units"] == "signed_index"
assert native["database_version"] == "12.5"
assert native["retrieval"]["timestamp"] == "2026-10-24T05:44:52.053162+00:00"
assert result["source_component_links"][0]["coverage"] in {
    "inherited_primary_review", "inherited_program_review", "own_cross_case_read", "own_synthetic_check"
}

numeric_tuples = []
def check_cells(node, path="$"):
    if isinstance(node, dict):
        if {"state", "point", "lower", "upper", "calculation_ref"} <= node.keys():
            assert node["calculation_ref"] == formula
            state, point, lo, hi = (node[k] for k in ("state", "point", "lower", "upper"))
            if state == "point":
                assert point == lo == hi
            elif state == "bounded":
                assert point is None and lo <= hi
            elif state == "not_applicable":
                assert point is lo is hi is None
            else:
                raise AssertionError(path)
            numeric_tuples.append([path, state, point, lo, hi])
        for key, value in node.items():
            check_cells(value, path + "/" + key)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            check_cells(value, path + "/" + str(i))

check_cells(record)
(root / output).write_text(json.dumps(record, indent=2) + "\n")
receipt = {
    "executed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "result": "passed", "numerical_cells_checked": len(numeric_tuples),
    "checked_cells": numeric_tuples, "coordinate_unchanged": .844,
    "corrected_fields": ["E units", "exact version label", "actual response-save timestamp",
                         "retained calculation/input references", "existing coverage enum"],
    "scope": "Typed formatting only. No new measurement, formula, source claim or biological validation."
}
(root / "field_check_receipt_002.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"result": "passed", "numerical_cells_checked": len(numeric_tuples), "coordinate": .844}))
