"""Retain final source bytes and summarize existing verification receipts only."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from run_checks import PACKET, ROOT, SOURCES


def main():
    destination = PACKET / "final_source"
    destination.mkdir()
    manifest = []
    earlier = {row["path"]: row for row in json.loads(
        (PACKET / "checks_005/source_manifest.json").read_text())}
    for name in SOURCES:
        source = ROOT / name
        raw = source.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == earlier[name]["sha256"], name
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        manifest.append({"path": name, "sha256": digest, "size_bytes": len(raw),
                         "matches_checks_005_source": True})
    (PACKET / "final_source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    groups = {}
    passing = set()
    for label in ("baseline_001", "checks_001", "checks_002", "checks_004", "checks_005", "binding_failure_001"):
        receipt = json.loads((PACKET / label / "receipt.json").read_text())
        suites = ET.parse(PACKET / label / "junit.xml").getroot()
        cases = list(suites.iter("testcase"))
        failed = [case for case in cases if case.find("failure") is not None or case.find("error") is not None]
        skipped = [case for case in cases if case.find("skipped") is not None]
        groups[label] = {"tests": len(cases), "passed": len(cases) - len(failed) - len(skipped),
                         "failed": len(failed), "skipped": len(skipped), "returncode": receipt["returncode"],
                         "receipt": f"{label}/receipt.json", "junit": f"{label}/junit.xml"}
        if label in {"checks_004", "checks_005"}:
            assert not failed and not skipped
            passing.update((case.attrib.get("classname"), case.attrib["name"]) for case in cases)
    summary = {"recorded_at": datetime.now(timezone.utc).isoformat(),
               "groups": groups,
               "unique_passing_tests_in_final_focused_groups": len(passing),
               "final_sources_match_last_targeted_run": True,
               "expanded_run": {"label": "checks_003", "status_at_handoff": "pending",
                   "monitoring_owner": "root", "launcher_pid": 1674728,
                   "worker_pid": 1674733, "pytest_pid": 1674741,
                   "worker_request": "checks_003/.local-job-aad2cc438504498bb55a64d08b1610e8.request",
                   "unified_exec_session": 38742,
                   "session_scope": "295 only; root monitors original PIDs and retained native files",
                   "stdout": "checks_003/stdout.txt", "stderr": "checks_003/stderr.txt"},
               "new_native_searches_this_workload": 0,
               "full_workflow_integration_claimed": False}
    (PACKET / "verification_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"final_source_files": len(manifest), "unique_passing_tests": len(passing),
                      "expanded_run": "pending; root monitors original process"}))


if __name__ == "__main__":
    main()
