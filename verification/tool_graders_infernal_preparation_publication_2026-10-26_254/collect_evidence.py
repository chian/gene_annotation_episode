"""Index retained verification bytes; no native algorithm or grader is invoked."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import xml.etree.ElementTree as ET


root = Path(__file__).resolve().parents[2]
destination = Path(__file__).resolve().parent
suite = destination / sys.argv[1]
tests = suite / "temporary/pytest"
suites = [destination / name for name in sys.argv[1:]]
test_roots = [item / "temporary/pytest" for item in suites]


def descriptor(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(root)), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def read(path):
    return json.loads(path.read_bytes())


cases = [
    ("consensus", "test_original252_capture_retai0"),
    ("calibration", "test_original252_capture_retai1"),
    ("partition_merge", "test_original252_capture_retai2"),
    ("failed_calibration", "test_original252_capture_retai3"),
    ("build", "test_actual_native_preparation0"),
    ("conversion", "test_actual_native_preparation1"),
    ("single_key", "test_actual_native_preparation2"),
    ("pressed_quartet", "test_actual_native_preparation3"),
    ("score_conversion", "test_actual_native_preparation4"),
    ("missing_key_rc0", "test_native_fetch_missing_key_0"),
    ("previous_ssi_unknown", "test_supplied_previous_ssi_sta0"),
]
examples = []
for name, case in cases:
    directory = tests / case / "grading/native-infernal-preparation-grading"
    prepared, grading = read(directory / "prepared.json"), read(directory / "grading.json")
    selected = []
    if name == "consensus":
        key = next(r["record_key"] for r in grading["sheet"]["output_records"] if r["kind"] == "generated_sequence")
        selected = [r for r in grading["calculations"]["rows"] if r["record_key"] == key]
    elif name in {"build", "calibration", "score_conversion"}:
        kinds = {"build": "build", "calibration": "calibration", "score_conversion": "model_statistic"}
        selected = [r for r in grading["sheet"]["native_rows"] if r["kind"] == kinds[name]]
        if name == "calibration":
            selected = [r for r in selected if r["identity"]["source"] == "model_header"]
        keys = {r["record_key"] for r in selected}
        selected += [r for r in grading["calculations"]["rows"] if r["record_key"] in keys]
    elif name in {"conversion", "single_key", "pressed_quartet", "missing_key_rc0", "previous_ssi_unknown"}:
        selected = grading["calculations"]["rows"]
    entry = {"name": name, "operation": grading["operation"], "prepared": prepared,
        "provenance": "unchanged_original252_capture" if name in {
            "consensus", "calibration", "partition_merge", "failed_calibration"} else "actual_selected251_native_operation_in_this_suite",
        "full_worker_output": descriptor(directory / "grading.json"),
        "full_sheet": descriptor(directory / "sheet.json"),
        "full_calculations": descriptor(directory / "calculations.json"),
        "grading_receipt": descriptor(directory / "grading-receipt.json"), "selected_populated_rows": selected}
    native_receipt = tests / case / "native-receipt.json"
    if native_receipt.is_file():
        entry["native_receipt"] = descriptor(native_receipt)
    projection = tests / case / "selection/native-infernal-preparation-projection/publication.json"
    if projection.is_file():
        entry["publication_receipt"] = descriptor(projection)
    if name == "partition_merge":
        partitions = [r for r in grading["sheet"]["native_rows"] if r["kind"] == "partition"]
        entry["retained_partition_arrays"] = [{"record_key": r["record_key"], "identity": r["identity"],
            "native_score_count": r["values"]["score_count"], "retained_array_length": len(r["series"])} for r in partitions]
    examples.append(entry)

stores = []
for database in sorted(path for test_root in test_roots for path in test_root.glob("*/store/state.sqlite3")):
    if database.parent.parent.is_symlink():
        continue
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
        counts = dict(connection.execute("SELECT record_type,count(*) FROM records GROUP BY record_type"))
        artifacts = connection.execute("SELECT count(*) FROM artifacts").fetchone()[0]
    stores.append({"store": str(database.parent.relative_to(root)), "record_counts": counts, "artifact_count": artifacts})
assert all(store["record_counts"].get("observation", 0) == 0 for store in stores)

contracts = root / "verification/tool_graders_infernal_preparation_2026-10-26_247"
test_cases = []
for item in suites:
    junit = ET.parse(item / "tests.xml").getroot()
    assert not list(junit.iter("failure")) and not list(junit.iter("error"))
    test_cases.extend({"suite": item.name, "class": r.attrib["classname"],
        "name": r.attrib["name"], "seconds": r.attrib["time"]} for r in junit.iter("testcase"))
failures = []
for receipt in sorted(path for test_root in test_roots for path in test_root.glob("*/grading/native-infernal-preparation-grading/prepared.json")):
    if receipt.parents[2].is_symlink():
        continue
    data = read(receipt)
    if data["failures"]:
        failures.append({"receipt": descriptor(receipt), "failures": data["failures"]})
replay = next(test_root / "test_grade_and_publication_rep0" for test_root in reversed(test_roots)
              if (test_root / "test_grade_and_publication_rep0").is_dir())
evidence = {"version": "infernal_preparation_publication_evidence_v1", "suite_receipt": descriptor(suite / "receipt.json"),
    "suite_junit": descriptor(suite / "tests.xml"), "examples": examples, "stores": stores,
    "supplemental_suites": [{"receipt": descriptor(item / "receipt.json"),
        "junit": descriptor(item / "tests.xml")} for item in suites[1:]],
    "tests": test_cases, "unique_test_count": len({(r["class"], r["name"]) for r in test_cases}),
    "retained_failure_examples": failures,
    "offline_replay": {"test": "test_grade_and_publication_replay_with_originals_and_all_work_forbidden",
        "prepared": descriptor(replay / "grading/native-infernal-preparation-grading/prepared.json"),
        "publication": descriptor(replay / "selection/native-infernal-preparation-projection/publication.json"),
        "forbidden": ["original_resource_file_reads", "native_subprocess", "network", "parsers",
            "calculators", "pure_projection", "full_numerical_host_hydration"]},
    "verification_kind": "bounded_engineering_checks_and_native_examples_not_episode_path_verification"}
(destination / "NUMERICAL_EXAMPLES_001.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
print(json.dumps({"examples": len(examples), "stores": len(stores), "observations": 0,
    "passed_test_executions": len(test_cases), "unique_test_count": evidence["unique_test_count"],
    "evidence": str(destination / "NUMERICAL_EXAMPLES_001.json")}))
