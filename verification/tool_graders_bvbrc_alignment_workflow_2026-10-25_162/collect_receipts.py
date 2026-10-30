"""Summarize actual retained test receipts without running package operations."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OWNED = Path(__file__).resolve().parent
RUNS = ROOT / "verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/runs"


def read(path):
    return json.loads(path.read_text())


def write_new(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def case_summary(directory, kind, passed_lines):
    archive = read(directory / "archive.json")
    scientific = archive["units"][0]["child"]
    launch, results = [unit["child"] for unit in scientific["units"] if isinstance(unit.get("child"), dict)]
    api = launch["units"][0]["child"]
    publication = read(directory / "publication.json")
    numerical = read(directory / "NUMERICAL_RETURN_CHECK.json")
    replay = read(directory / "saved-replay-verification.json")
    guard = read(directory / "SOURCE_GUARD_AFTER_TESTS.json")
    closure_guard = read(directory / "SOURCE_GUARD_WORKFLOW_CLOSED.json")
    provenance = read(directory / "PROVENANCE.json")
    cases = []
    with sqlite3.connect((directory / "state/state.sqlite3").as_uri() + "?mode=ro", uri=True) as database:
        for role, record in (("annotation", archive), ("scientific_process", scientific),
                             ("launch", launch), ("launch_api", api), ("results", results)):
            counts = {table: database.execute("SELECT count(*) FROM " + table + " WHERE episode_id=?",
                        (record["episode_id"],)).fetchone()[0]
                      for table in ("runtime_actions", "runtime_observations", "runtime_model_calls")}
            cases.append({"role": role, "episode_id": record["episode_id"],
                "units_consumed": record["units_consumed"], "counts": counts,
                "marginal_credit": [unit["controller_step"]["marginal_credit"] for unit in record["units"]],
                "final_estimate": record["controller_state"]["estimate"]})
    receipt_names = ("CONFIGURED_BINDINGS.json", "PROVENANCE.json", "SOURCE_HASHES_BEFORE.json",
        "SOURCE_HASHES_AFTER.json", "SOURCE_HASHES_AFTER_TESTS.json", "SOURCE_GUARD_WORKFLOW_CLOSED.json",
        "SOURCE_GUARD_AFTER_TESTS.json", "NUMERICAL_RETURN_CHECK.json", "results-return.json",
        "scientific-return.json", "sheet.json", "components.json", "publication.json", "archive.json",
        "native-http-calls.json", "saved-sheet-recalculation.json", "saved-sheet-changed-parameters.json",
        "saved-replay-verification.json")
    return {"case": kind, "recorded_at": datetime.now(timezone.utc).isoformat(),
        "run_directory": str(directory.relative_to(ROOT)), "passed_test_lines": passed_lines,
        "original_numbers": numerical["actual"], "expected_numbers": numerical["expected"],
        "optional_requirements_retained": numerical["retained_optional_requirements"],
        "episode_records": cases, "replay": replay,
        "guards": {"workflow_closed": closure_guard, "after_tests": guard},
        "adapter_pin": provenance["adapter_pin"], "scientific_binding_pin": provenance["scientific_binding_pin"],
        "http_calls": read(directory / "native-http-calls.json"),
        "artifact_provenance": [{key: artifact[key] for key in
            ("role", "sha256", "byte_count", "task_association", "transfer")}
            for artifact in publication["bundle"]["artifacts"]],
        "receipt_sha256": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in receipt_names},
        "limits": ["Controlled loopback HTTP replies and scripted choices", "Retained native bytes only",
            "No live BV-BRC or new native scientific execution", "No configured-model gene annotation",
            "Scientific renderer checks were separate from Choices.complete; other role prompts were not verified",
            "Original producer identity/version and original output-to-input relationships remain qualified"]}


def main():
    old = set(read(OWNED / "EXISTING_RUN_DIRECTORIES.json"))
    log = (OWNED / "pytest.log").read_text()
    for directory in sorted(RUNS.iterdir()):
        if not directory.is_dir() or directory.name in old:
            continue
        kind = directory.name.rsplit("-", 1)[0]
        destination = OWNED / ("case-" + kind + ".json")
        if destination.exists() or not (directory / "SOURCE_GUARD_AFTER_TESTS.json").exists():
            continue
        lines = [line for line in log.splitlines() if "[" + kind + "] PASSED " in line]
        if len(lines) == 4 and (directory / "saved-replay-verification.json").exists():
            summary = case_summary(directory, kind, lines)
            write_new(destination, summary)
            print(json.dumps({"case": kind, "receipt": str(destination.relative_to(ROOT)),
                "numbers": summary["original_numbers"], "used_source_count": len(summary["guards"]["after_tests"]["used_paths"]),
                "used_changes": summary["guards"]["after_tests"]["used_changes"],
                "used_without_before_hash": summary["guards"]["after_tests"]["used_without_before_hash"],
                "replay_counts_unchanged": summary["replay"]["counts_before"] == summary["replay"]["counts_after"]}))
    terminal = OWNED / "process-terminal.json"
    destination = OWNED / "assessment.json"
    if terminal.exists() and not destination.exists():
        cases = []
        for case in ET.parse(OWNED / "pytest.junit.xml").findall(".//testcase"):
            cases.append({"name": case.attrib["name"], "seconds": float(case.attrib["time"]),
                "status": "error" if case.find("error") is not None else "failed" if case.find("failure") is not None
                          else "skipped" if case.find("skipped") is not None else "passed"})
        before, after = (read(OWNED / ("SOURCE_HASHES_" + part + ".json")) for part in ("BEFORE", "AFTER"))
        summary = {"terminal": read(terminal), "test_cases": cases,
            "counts": {status: sum(case["status"] == status for case in cases)
                       for status in ("passed", "failed", "error", "skipped")},
            "case_receipts": sorted(path.name for path in OWNED.glob("case-*.json")),
            "broad_source_changes": sorted(name for name in before if before[name] != after.get(name)),
            "broad_source_additions": sorted(set(after) - set(before)),
            "independent_arithmetic_receipt": "independent-retained-numbers.json",
            "production_or_test_source_edits_by_worker": [],
            "process_launch_count": 1}
        write_new(destination, summary)
        print(json.dumps({"suite": summary["counts"], "returncode": summary["terminal"]["returncode"],
            "elapsed_seconds": summary["terminal"]["elapsed_seconds"], "receipt": str(destination.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
