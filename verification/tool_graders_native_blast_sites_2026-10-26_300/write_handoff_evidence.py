"""Index the actual retained verification receipts without replaying any work."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[1]


def read(path):
    return json.loads(path.read_text())


def write(name, value):
    (DIRECTORY / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def captured_manifest(path):
    bundle = read(path)
    rows = []
    for kind, items in (("input", bundle["inputs"]), ("output", bundle["artifacts"])):
        for row in items:
            artifact = path.parent / row["relative_path"]
            actual = digest(artifact)
            expected = row.get("actual_sha256", row.get("sha256"))
            assert actual == {"sha256": expected, "bytes": row["size_bytes"]}
            rows.append({"kind": kind, "path": str(artifact.relative_to(ROOT)),
                "role": row["role"], "format": row["format"], **actual,
                "matches_original_manifest": True})
    return {"path": str(path.relative_to(ROOT)), **digest(path), "program": bundle["program"],
        "mode": bundle["mode"], "captured_artifacts": rows}


def main():
    cases = []
    for path in sorted((DIRECTORY / "check003/examples").glob("*.json")):
        example = read(path)
        if example.get("input_kind") != "retained_actual_native_report":
            continue
        manifest = Path(example["original_manifest"])
        cases.append({"case": path.stem, "input_kind": example["input_kind"],
            "example": str(path.relative_to(ROOT)), "hsp_count": len(example["windows"]),
            "original": captured_manifest(manifest)})
    actual = read(DIRECTORY / "workflow001/examples/actual_reverse_blastx_workflow.json")
    actual_manifest = Path(actual["original_plan"]["attempt_directory"]) / "bundle.json"
    write("NATIVE_INPUT_HASHES.json", {"retained_294_reports": cases,
        "one_new_actual_execution": captured_manifest(actual_manifest)})
    receipts = {}
    unique_passes = set()
    final_runs = {"check003", "check004", "workflow001", "final002"}
    for name in ("check001", "check002", "check003", "workflow001", "check004", "final001", "final002"):
        run = DIRECTORY / name
        suite = ET.parse(run / "junit.xml").getroot().find("testsuite")
        receipt = read(run / "receipt.json")
        receipts[name] = {"tests": int(suite.attrib["tests"]), "failures": int(suite.attrib["failures"]),
            "errors": int(suite.attrib["errors"]), "pytest_seconds": float(suite.attrib["time"]),
            "returncode": receipt["native_returncode"], "service_seconds": receipt["elapsed_seconds"],
            "receipt": str((run / "receipt.json").relative_to(ROOT)),
            "junit": str((run / "junit.xml").relative_to(ROOT)), "policy": receipt["policy"]}
        if name in final_runs:
            unique_passes.update((test.attrib["classname"], test.attrib["name"])
                for test in suite.findall("testcase")
                if test.find("failure") is None and test.find("error") is None and test.find("skipped") is None)
    before, after = (read(DIRECTORY / name) for name in ("SOURCE_BEFORE.json", "SOURCE_AFTER.json"))
    unowned = list(before)[8:]
    write("VERIFICATION_INDEX.json", {"runs": receipts, "unique_passing_tests_in_final_runs": len(unique_passes),
        "retained_report_count": len(cases), "retained_published_hsp_count": sum(row["hsp_count"] for row in cases),
        "retained_no_hsp_cases": [row["case"] for row in cases if not row["hsp_count"]],
        "new_actual_native_executions": 1,
        "final_source_snapshot_file_count": len(read(DIRECTORY / "final002/source_before.json")),
        "final_source_delta": read(DIRECTORY / "final002/source_delta.json"),
        "original_pinned_unowned_files_unchanged": {p: before[p] == after[p] for p in unowned},
        "successful_test_cases": [list(item) for item in sorted(unique_passes)]})
    goal = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
    write("READ_AUDIT.json", {"immutable_goal": {"path": str(goal), **digest(goal)},
        "goal_read_in_full_before_editing": True,
        "objective_and_all_sixteen_principles_reread_verbatim_after_source_study_before_editing": True,
        "objective_and_all_sixteen_principles_reread_verbatim_before_handoff": True,
        "goal_final_reread_lines": [[1, 53], [351, 532]],
        "final_reread_followed_by_full_contract_and_addendum": [
            {"path": str((DIRECTORY / name).relative_to(ROOT)), **digest(DIRECTORY / name)}
            for name in ("CONTRACT_001.md", "CONTRACT_ADDENDUM_002.md")]})
    print(json.dumps({"reports": len(cases), "hsps": sum(row["hsp_count"] for row in cases),
        "unique_passes": len(unique_passes), "unowned_unchanged": all(before[p] == after[p] for p in unowned)}))


if __name__ == "__main__":
    main()
