"""Verify the agreed frozen provider/return composition; retain every attempt.

Usage: python VERIFY_TESTS_001.py unit|host 001
No source is changed, no job is submitted, and no incomplete test is counted as
a pass. The two groups may run independently against the same frozen candidate.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE / "candidate"
GROUPS = {
    "unit": [
        "test_bvbrc_proteome_bundle_v2_contracts.py",
        "test_bvbrc_proteome_bundle_v2_resolution.py",
        "test_bvbrc_proteome_directional_saved_validation.py",
        "test_bvbrc_proteome_directional_fact_contracts.py",
        "test_bvbrc_proteome_directional_projection.py",
        "test_bvbrc_proteome_directional_tool_info.py",
        "test_bvbrc_proteome_bundle_contracts.py",
        "test_bvbrc_proteome_bundle_resolution.py",
        "test_bvbrc_proteome_bundle_projection.py",
        "test_bvbrc_proteome_fact_contracts.py",
        "test_bvbrc_proteome_document_selection.py",
        "test_bvbrc_proteome_tool_info.py",
        "test_bvbrc_proteome_catalog_integration.py",
        "test_bvbrc_appservice_adapter_binding.py",
        "test_bvbrc_appservice_contracts.py",
        "test_bvbrc_appservice_bundle_values.py",
        "test_api_bvbrc_appservice.py",
    ],
    "host": [
        "test_bvbrc_proteome_directional_publication.py",
        "test_bvbrc_proteome_directional_returns.py",
        "test_bvbrc_proteome_directional_episode_path.py",
        "test_bvbrc_proteome_returns.py",
        "test_bvbrc_proteome_returns_original.py",
        "test_bvbrc_proteome_return_frames.py",
        "test_bvbrc_proteome_host_integration.py",
        "test_bvbrc_appservice_publication.py",
        "test_bvbrc_appservice_saved_results.py",
        "test_execution_episodes_family.py",
    ],
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(group):
    paths = {CANDIDATE / "pyproject.toml"}
    for directory in ("gene_annotation_episode", "method_loop", "tests", "research", "verification"):
        paths.update(p for p in (CANDIDATE / directory).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts
                     and p.suffix not in (".pyc", ".pyo"))
    # The Workflow test is an independent host-only consumer. Its final root
    # admission assertion can be completed while the frozen unit closure runs.
    excluded = {"tests/test_bvbrc_proteome_directional_episode_path.py"} if group == "unit" else set()
    return {str(p.relative_to(CANDIDATE)): sha(p) for p in sorted(paths)
            if str(p.relative_to(CANDIDATE)) not in excluded}


def main():
    assert len(sys.argv) == 3 and sys.argv[1] in GROUPS
    group, attempt = sys.argv[1:]
    assert re.fullmatch(r"[0-9]{3}", attempt)
    freeze_path = HERE / ("FREEZE_INDEPENDENT_001.json" if group == "unit" else "FREEZE_001.json")
    frozen = json.loads(freeze_path.read_text())
    before = snapshot(group)
    assert before == frozen["sources"], "candidate differs from agreed final-source freeze"
    tests = ["tests/" + name for name in GROUPS[group]]
    assert all((CANDIDATE / path).is_file() for path in tests)
    out = HERE / ("final_" + group + "_" + attempt)
    out.mkdir(exist_ok=False)

    def save(name, value):
        with (out / name).open("x") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")

    save("source_before.json", before)
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
               "--basetemp=" + str(out / "temporary"),
               "--junitxml=" + str(out / "pytest.xml"), *tests]
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(CANDIDATE))
    save("command.json", {"argv": command, "cwd": str(CANDIDATE),
                          "environment": {k: environment[k] for k in ("PYTHONDONTWRITEBYTECODE", "PYTHONPATH")}})
    receipt = {"group": group, "passed": False, "started_at": datetime.now(timezone.utc).isoformat(),
               "freeze_file": freeze_path.name, "freeze_sha256": sha(freeze_path),
               "live_service_execution_verified": False,
               "verification_scope": "real provider, publication and communication code; controlled transport and decisions"}
    clock = time.monotonic()
    try:
        with (out / "pytest.log").open("x") as log:
            result = subprocess.run(command, cwd=CANDIDATE, env=environment, stdout=log, stderr=subprocess.STDOUT)
        receipt["exit_code"] = result.returncode
        tree = ET.parse(out / "pytest.xml").getroot()
        cases = [{**case.attrib, "outcome": "failed" if case.find("failure") is not None else
                  "error" if case.find("error") is not None else "skipped" if case.find("skipped") is not None else "passed"}
                 for case in tree.iter("testcase")]
        save("cases.json", cases)
        receipt["testsuites"] = [suite.attrib for suite in tree.iter("testsuite")]
        receipt["case_counts"] = {status: sum(c["outcome"] == status for c in cases)
                                  for status in ("passed", "failed", "error", "skipped")}
        receipt["passed"] = result.returncode == 0 and bool(cases) and all(c["outcome"] == "passed" for c in cases)
    except Exception as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
    finally:
        after = snapshot(group)
        save("source_after.json", after)
        changes = [p for p in sorted(set(before) | set(after)) if before.get(p) != after.get(p)]
        receipt.update(ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - clock,
                       source_count=len(before), changed_sources=changes)
        receipt["passed"] = receipt["passed"] and not changes
        save("receipt.json", receipt)
        print(json.dumps(receipt))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
