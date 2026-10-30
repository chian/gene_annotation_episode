"""Independently rehash endpoint244 evidence and aggregate actual JUnit cases."""
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PACKET = HERE.parent / "a105_endpoint_signal_binding_244"
manifest = json.loads((PACKET / "FINAL_MANIFEST_001.json").read_text())
manifest_sha = sha256((PACKET / "FINAL_MANIFEST_001.json").read_bytes()).hexdigest()
assert manifest_sha == "f3b5ef1d1ee175a7047e4789ebea96a3eaba381b1f76305e921396e57bf4693a"
for name, digest in manifest["files"].items():
    assert sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
pin_checks = []
for number in range(1, 6):
    name = f"PIN_{number:03d}.json"
    pin = json.loads((PACKET / name).read_text())
    for relative, digest in pin["hashes"].items():
        assert sha256((PACKET / name[:-5].lower() / relative).read_bytes()).hexdigest() == digest, (name, relative)
    pin_checks.append({"pin": name, "files": len(pin["hashes"])})
final_pin = json.loads((PACKET / "PIN_005.json").read_text())
for name in [*manifest["production_owned"], manifest["test_owned"]]:
    assert sha256((ROOT / name).read_bytes()).hexdigest() == final_pin["hashes"][name]
verification = json.loads((PACKET / "FINAL_VERIFICATION_001.json").read_text())
case_results = {}
cohorts = []
for cohort in verification["cohorts"]:
    cases = ET.parse(PACKET / cohort["junit"]).getroot().findall(".//testcase")
    failures = []
    for case in cases:
        identity = case.attrib["classname"] + "::" + case.attrib["name"]
        assert case.find("skipped") is None and case.find("error") is None
        status = "failed" if case.find("failure") is not None else "passed"
        case_results[identity] = status
        if status == "failed":
            failures.append(identity)
    assert len(cases) == cohort["cases"]
    assert len(failures) == cohort["failed"]
    cohorts.append({"label": cohort["label"], "cases": len(cases), "failed": failures})
assert len(case_results) == verification["unique_checks"] == 732
assert sum(value == "passed" for value in case_results.values()) == verification["unique_passed"] == 730
endpoint_cases = {key: value for key, value in case_results.items()
                  if key.startswith("tests.test_literature_endpoint_signal_binding_244::")}
assert len(endpoint_cases) == 47 and set(endpoint_cases.values()) == {"passed"}
assert {key for key, value in case_results.items() if value == "failed"} == set(verification["remaining_failures"])
cold = json.loads((PACKET / "COLD_PROOF_INDEX_001.json").read_text())
for proof in cold["proofs"]:
    for name, digest in proof["original_saved_files"].items():
        assert sha256((PACKET / name).read_bytes()).hexdigest() == digest
    for name, digest in proof["state_hashes"].items():
        assert sha256((PACKET / proof["directory"] / "state" / name).read_bytes()).hexdigest() == digest
    count = proof["durable_counts"]
    assert count["runtime_actions"] == count["runtime_observations"]
result = {"status": "pass", "manifest_sha256": manifest_sha,
          "manifest_entries_rehashed": len(manifest["files"]), "pins_rehashed": pin_checks,
          "owned_workspace_paths_equal_final_pin": 10, "cohorts": cohorts,
          "unique_checks": len(case_results), "unique_passed": 730,
          "endpoint_checks": len(endpoint_cases), "cold_proof_saved_bytes_verified": len(cold["proofs"]),
          "evidence_limit": "JUnit/hash inspection, not an independent model-backed scientific investigation or full A105 completion."}
(HERE / "ROOT_FINAL_PACKET_CHECK_003.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
