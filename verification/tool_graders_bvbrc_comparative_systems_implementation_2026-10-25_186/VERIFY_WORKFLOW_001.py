"""Root-owned final Workflow verification of a source-frozen candidate.

Usage: python VERIFY_WORKFLOW_001.py ATTEMPT EXPECTED_PROVIDER_SHA256
Run only after P and I release their source ownership. Observation timeouts do
not stop this process. The faulthandler option prints a diagnostic stack only.
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
TEST = ("tests/test_bvbrc_comparative_systems_episode_flow.py::"
        "test_actual_selected_tool_shared_workflow_native_publication_and_typed_parent_return")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    paths = {CANDIDATE / "pyproject.toml"}
    for directory in ("gene_annotation_episode", "method_loop", "tests", "research", "verification"):
        paths.update(p for p in (CANDIDATE / directory).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts
                     and p.suffix not in (".pyc", ".pyo"))
    return {str(p.relative_to(CANDIDATE)): sha(p) for p in sorted(paths)}


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main():
    assert len(sys.argv) == 3
    attempt, expected_pin = sys.argv[1:]
    assert re.fullmatch(r"[0-9]{3}", attempt)
    assert re.fullmatch(r"[0-9a-f]{64}", expected_pin)
    out = HERE / ("final_workflow_" + attempt)
    out.mkdir(exist_ok=False)
    before = snapshot()
    save(out / "source_before.json", before)
    sys.path.insert(0, str(CANDIDATE))
    from gene_annotation_episode import bvbrc_comparative_systems_bundle_adapter as provider
    assert Path(provider.__file__).resolve().is_relative_to(CANDIDATE)
    assert provider.implementation_sha256() == expected_pin
    assert snapshot() == before, "source changed during freeze"
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
               "-o", "faulthandler_timeout=300", "--durations=5",
               "--basetemp=" + str(out / "temporary"),
               "--junitxml=" + str(out / "pytest.xml"), TEST]
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(CANDIDATE))
    save(out / "command.json", {"argv": command, "cwd": str(CANDIDATE),
         "environment": {key: environment[key] for key in ("PYTHONDONTWRITEBYTECODE", "PYTHONPATH")}})
    receipt = {"passed": False, "started_at": datetime.now(timezone.utc).isoformat(),
               "harness_sha256": sha(Path(__file__)), "provider_sha256": expected_pin,
               "source_before_sha256": sha(out / "source_before.json"),
               "live_service_execution_verified": False,
               "verification_scope": "actual selected-tool shared Workflow; controlled transport and decisions"}
    clock = time.monotonic()
    try:
        with (out / "pytest.log").open("x") as log:
            result = subprocess.run(command, cwd=CANDIDATE, env=environment,
                                    stdout=log, stderr=subprocess.STDOUT)
        receipt["exit_code"] = result.returncode
        tree = ET.parse(out / "pytest.xml").getroot()
        cases = [{**case.attrib, "outcome": "failed" if case.find("failure") is not None else
                  "error" if case.find("error") is not None else
                  "skipped" if case.find("skipped") is not None else "passed"}
                 for case in tree.iter("testcase")]
        save(out / "cases.json", cases)
        receipt["case_counts"] = {status: sum(case["outcome"] == status for case in cases)
                                  for status in ("passed", "failed", "error", "skipped")}
        receipt["passed"] = (result.returncode == 0 and len(cases) == 1
                             and cases[0]["name"] == TEST.split("::")[1]
                             and cases[0]["outcome"] == "passed")
    except Exception as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
    finally:
        after = snapshot()
        save(out / "source_after.json", after)
        changes = [name for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)]
        receipt.update(ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - clock,
                       source_count=len(before), changed_sources=changes)
        receipt["passed"] = receipt["passed"] and not changes
        save(out / "receipt.json", receipt)
        print(json.dumps(receipt))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
