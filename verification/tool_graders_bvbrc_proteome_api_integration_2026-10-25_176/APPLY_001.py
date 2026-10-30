"""Apply the reviewed frozen176 delta, preserving013's original failed receipt."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = HERE / "candidate"
NUMERICAL = ROOT / "verification/tool_graders_bvbrc_proteome_directional_build_2026-10-25_179"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text())


def save(name, data):
    with (HERE / name).open("x") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


manifest = read("DELTA_MANIFEST_002.json")
assert len(manifest["files"]) == 20 and not manifest["unexpected_original_changes"]
assert sha(HERE / "DELTA_002.patch") == manifest["patch_sha256"]
before13, after13 = read("TEST_013_BEFORE.json"), read("TEST_013_AFTER.json")
before14, after14 = read("TEST_014_BEFORE.json"), read("TEST_014_AFTER.json")
for before, after in ((before13, after13), (before14, after14)):
    assert before["files"] == after["files"] and not after["source_changes_during_run"]
    assert before["runner_sha256"] == after["runner_before_sha256"] == after["runner_after_sha256"]
assert after13["returncodes"] == {"core": 1, "host": 0}
assert after14["returncode"] == 0
changed = [name for name in before14["files"] if before14["files"][name] != after13["files"][name]]
assert changed == before14["changes_from_013"] == ["tests/test_execution_episodes_family.py"]
expected = (("TEST_013_core.xml",455,1),("TEST_013_host.xml",11,0),("TEST_014.xml",10,0))
test_receipts = []
passed_cases = set()
for name, total, failures in expected:
    document = ET.parse(HERE / name).getroot()
    suites = list(document.iter("testsuite"))
    assert len(suites) == 1
    suite = suites[0]
    assert (int(suite.attrib["tests"]),int(suite.attrib["failures"]),int(suite.attrib["errors"]),int(suite.attrib["skipped"])) == (total,failures,0,0)
    failed = []
    for case in document.iter("testcase"):
        identity = (case.attrib["classname"],case.attrib["name"])
        if case.find("failure") is not None or case.find("error") is not None:
            failed.append(identity)
        else:
            passed_cases.add(identity)
    if failures:
        assert failed == [("tests.test_execution_episodes_family", "test_one_owner_and_data_descriptor_reconstruct_all_operands")]
    test_receipts.append({"path":name,"sha256":sha(HERE/name),"tests":total,"failures":failures})
assert len(passed_cases) == 466
numerical = json.loads((NUMERICAL / "APPLICATION_RECEIPT_001.json").read_text())
assert sha(NUMERICAL / "APPLICATION_RECEIPT_001.json") == manifest["root179_application_receipt_sha256"]
numerical_files = {row["path"]:row["after_sha256"] for row in numerical["files"]}
for name, value in numerical_files.items():
    assert sha(ROOT/name) == value, name
delta = {row["path"]:row for row in manifest["files"]}
assert not set(delta).intersection(numerical_files)
root_before = {}
for name, item in after14["files"].items():
    assert sha(CANDIDATE/name) == item["sha256"], name
    if name in delta:
        expected_sha = delta[name]["before_sha256"]
    elif name in numerical_files:
        expected_sha = numerical_files[name]
    else:
        expected_sha = item["sha256"]
    actual = sha(ROOT/name) if (ROOT/name).exists() else None
    assert actual == expected_sha, (name,actual,expected_sha)
    root_before[name] = actual
for name,row in delta.items():
    assert row["candidate_sha256"] == after14["files"][name]["sha256"]
receipt = {
    "recorded_at":datetime.now(timezone.utc).isoformat(),
    "delta_manifest_sha256":sha(HERE/"DELTA_MANIFEST_002.json"),
    "delta_patch_sha256":manifest["patch_sha256"],
    "provider_implementation_sha256":manifest["provider_implementation_sha256"],
    "files":manifest["files"],
    "unchanged_candidate_files":len(after14["files"]),
    "candidate_test_receipts":test_receipts,
    "distinct_passing_cases_across013_and014":len(passed_cases),
    "preserved013_failure":"descriptor test passed None instead of actual launch BindingContext",
    "only014_change":"tests/test_execution_episodes_family.py fixture supplies actual launch BindingContext",
    "full_workflow_verified":False,
    "live_service_execution_verified":False,
    "directional_numerical_provider_return_integration":"unfinished",
}
if sys.argv[1:] == ["--apply"]:
    assert not (HERE/"APPLICATION_RECEIPT_001.json").exists()
    save("ROOT_BEFORE_APPLICATION_001.json",root_before)
    for name,row in delta.items():
        destination = ROOT/name
        mode = "xb" if row["before_sha256"] is None else "wb"
        with destination.open(mode) as stream:
            stream.write((CANDIDATE/name).read_bytes())
        assert sha(destination) == row["candidate_sha256"]
    for name, value in root_before.items():
        if name not in delta:
            assert sha(ROOT/name) == value, name
    assert all(sha(ROOT/name) == value for name,value in numerical_files.items())
    receipt.update(production_applied=True, applied_checkout_verification="pending",
                   unchanged_numerical179_files=len(numerical_files))
    save("APPLICATION_RECEIPT_001.json",receipt)
else:
    assert not sys.argv[1:]
    receipt["production_applied"] = False
    save("PREFLIGHT_001.json",receipt)
print(json.dumps({"production_applied":receipt["production_applied"],"files":len(delta),
                  "distinct_passed_cases":len(passed_cases),"original013_failure_preserved":True}))
