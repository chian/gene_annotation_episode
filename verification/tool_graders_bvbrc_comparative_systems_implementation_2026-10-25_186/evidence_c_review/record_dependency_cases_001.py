"""Record actual N→C results; synthetic/source-executed fixtures, no service."""
from pathlib import Path
from copy import deepcopy
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
label = sys.argv[1]
assert label in {"before", "after"}
output = HERE / label
output.mkdir(exist_ok=False)
test_path = BASE / "candidate/tests/test_bvbrc_comparative_systems_calculators.py"
spec = importlib.util.spec_from_file_location("dependency_precision_cases", test_path)
test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test)
examples = json.loads(test._FIXTURE.read_text())["examples"]
records = []

def record(name, sheet, formula, basis):
    request = test.request(examples, "reported_formula_check", formula=formula)
    before = test.canonical_sha256(sheet)
    parameters = test.parameters([request])
    result = test.calculate(sheet, parameters=parameters)
    assert before == test.canonical_sha256(sheet) == result["sheet_sha256"]
    for kind, value in (("sheet", sheet), ("components", result)):
        (output / (name + "_" + kind + ".json")).write_text(json.dumps(value, indent=2) + "\n")
    cell = result["components"][0]["value"]
    records.append({"name": name, "basis": basis, "formula": formula,
        "expected": {"state": "available", "value": 0},
        "actual": {"state": cell["state"], "value": cell["value"], "qualification_codes": cell["qualification_codes"]},
        "matches_expected": cell["state"] == "available" and cell["value"] == 0,
        "canonical_sheet_sha256": before,
        "source_documents": [{key: source[key] for key in ("document_id", "basis", "sha256", "byte_count")}
                             for source in sheet["source_documents"]]})

record("joined_feature_metadata", test.dependency_sheet(joined_witness=True), "subsystem_role_conservation",
       "actual_N_on_unchanged_producer_source_executed_synthetic_feature_join")
for formula in test._FORMULAS:
    subsystem = formula.startswith("subsystem")
    document, table = ("subsystems", "subsystems") if subsystem else ("pathways", "pathway")
    for defect in ("unidentified_width", "unrelated_number"):
        def unrelated(rows):
            if defect == "unidentified_width":
                rows.append(["synthetic_unidentified_malformed_summary"])
            else:
                other = list(rows[1])
                other[rows[0].index("subsystem_id" if subsystem else "pathway_id")] = "UNRELATED_SYNTHETIC_ID"
                if subsystem:
                    other[rows[0].index("subsystem_name")] = "Other synthetic subsystem"
                other[rows[0].index("genome_count")] = "not_a_number"
                rows.append(other)
        record(defect + "_" + formula,
               test.dependency_sheet(edits={document: test.edit_embedded_table(table, unrelated)}),
               formula, "actual_N_on_explicit_synthetic_malformed_artifact")
receipt = {"stage": label, "real_service_job": False, "cases": records,
    "runtime_sources": [{"path": str(path.relative_to(BASE)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                        for path in sorted((BASE / "candidate/gene_annotation_episode").glob("bvbrc_comparative_systems*.py"))
                        if any(key in path.name for key in ("calculator", "calculation_contract", "sheet", "native", "handoff"))]}
(HERE / ("DEPENDENCY_CASES_" + label.upper() + "_001.json")).write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps([{"case": r["name"], "expected": r["expected"], "actual": r["actual"]} for r in records], indent=2))
if label == "after":
    assert all(r["matches_expected"] for r in records)
