"""Finalize receipts after the original frozen cohort exits; never runs tests."""
from collections import Counter
from pathlib import Path
import datetime
import hashlib
import json
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def read(name):
    return json.loads((HERE / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (HERE / name).open("x") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")


result = read("FROZEN_RESULT_003.json")
assert result["exit_code"] == 0, result["exit_code"]
assert not result["imports_outside_pin"]
assert not result["changed_pinned_files"]
root = ET.parse(HERE / "FROZEN_TESTS_003.xml").getroot()
cases = list(root.iter("testcase"))
assert cases
assert not list(root.iter("failure"))
assert not list(root.iter("error"))
assert not list(root.iter("skipped"))
by_module = dict(sorted(Counter(case.attrib["classname"] for case in cases).items()))
assert by_module["tests.test_literature_common_assessment_binding_223"] == 26
suites = list(root.iter("testsuite"))
pytest_seconds = sum(float(s.attrib["time"]) for s in suites)
pin = read("PIN_003.json")
assert len(pin["hashes"]) == 2023
changed_pin = [name for name, expected in pin["hashes"].items()
               if sha(HERE / "pin_003" / name) != expected]
assert not changed_pin, changed_pin
changed_owned = [name for name, expected in pin["owned_code_hashes"].items()
                 if sha(REPO / name) != expected]
protected = read("PROTECTED_PRESERVATION_001.json")
changed_protected = [name for name, expected in protected["sha256"].items()
                     if sha(REPO / name) != expected]
assert all(sha(HERE / "pin_003" / name) == expected
           for name, expected in protected["sha256"].items())
accepted_pure = {
    "gene_annotation_episode/literature_compiled_assay_inputs.py":
        "f158d01f14b7b57c60665a1508f729c5e2b04bc2cf3d5a07e560851c287b1ada",
    "gene_annotation_episode/literature_compiled_assay_calculations.py":
        "b629a9d519a350514b6c3de7171bf0d1de0e4477350a54bbc9d145fbf4ead0c6",
    "tests/test_literature_common_assessment_221.py":
        "222185a93bfabfb2f8653ee9d96c8c77c8b1052732607c8f4e2056824415405e",
}
assert all(sha(HERE / "pin_003" / name) == expected for name, expected in accepted_pure.items())
old = read("OLD_STATE_BASELINE_001.json")
old_state = Path(old["proof_directory"]) / "state"
assert all(sha(old_state / name) == expected for name, expected in old["state_files"].items())
assert len(old["state_files"]) == 25
cold = read("COLD_PROOFS_001.json")
assert len(cold["unique_current_cold_proofs"]) == 9
for entry in cold["unique_current_cold_proofs"]:
    proof_path = HERE / entry["proof"]
    assert sha(proof_path) == entry["sha256"]
    original_proof = json.loads(proof_path.read_text())
    assert all(sha(proof_path.parent / "state" / name) == expected
               for name, expected in original_proof["state_files"].items())
review_dir = HERE.parent / "a105_common_assessment_binding_review_229"
independent = json.loads((review_dir / "ROOT_RESULT_001.json").read_text())
assert independent["exit_code"] == 0
assert not independent["imports_outside_pin"]
assert not independent["changed_pinned_files"]

summary = {
    "exit_code": 0,
    "passed_cases": len(cases),
    "passed_by_module": by_module,
    "pytest_seconds": pytest_seconds,
    "runner_seconds": result["elapsed_seconds"],
    "imports_inside_pin": len(result["imports"]),
    "imports_outside_pin": {},
    "changed_pinned_files": [],
    "pinned_files_reverified": 2023,
    "live_owned_changes_since_owner_release": changed_owned,
    "live_protected_changes_since_owner_release": changed_protected,
    "frozen_protected_paths_reverified": len(protected["sha256"]),
    "accepted_pure_sha256": accepted_pure,
    "old_state_files_reverified": 25,
    "unique_cold_proofs": 9,
    "independent_root_new_cases": 26,
    "independent_root_result": "../a105_common_assessment_binding_review_229/ROOT_RESULT_001.json",
    "counts_are_not_added_to_overlapping_runs": True,
    "scope": "Controlled engineering compatibility and scientific component regression evidence; no A105 adequacy or actual-model execution claim.",
}
write("TEST_SUMMARY_001.json", summary)

draft = (HERE / "HANDOFF_DRAFT_001.md").read_text()
draft = draft.replace("implementation handoff draft", "implementation handoff")
draft = draft.replace("## Verification status when this draft was written", "## Completed verification")
old_paragraph = (
    "The owner final full compatibility cohort remains running on its original process handle. "
    "Its result must be read from `FROZEN_RESULT_003.json` and `FROZEN_TESTS_003.xml` after termination; "
    "this draft does not declare that run successful."
)
assert old_paragraph in draft
draft = draft.replace(old_paragraph,
    f"The final frozen pin003 compatibility cohort completed with **{len(cases)} passing checks**, "
    f"zero failures/errors/skips, in {pytest_seconds:.3f} pytest seconds "
    f"({result['elapsed_seconds']:.3f} runner seconds), exit 0. All {len(result['imports'])} "
    "recorded scientific/runtime/test imports stayed inside the pin; all 2,023 pin files are unchanged. "
    "`TEST_SUMMARY_001.json` records the per-module counts and final preservation checks. "
    "The original runner was retained throughout; earlier interrupted cohorts are separate.")
with (HERE / "HANDOFF_002.md").open("x") as output:
    output.write(draft)

write("PROGRESS_002.json", {
    "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "bounded_223_integration_complete_and_released",
    "production_paths": 9,
    "new_test_paths": 1,
    "frozen_pin": "PIN_003.json",
    "verification": "TEST_SUMMARY_001.json",
    "handoff": "HANDOFF_002.md",
    "external_contribution": "EXTERNAL_SHARED_CHANGE_001.json",
    "full_A105_adequacy": False,
    "immutable_goal_achieved": False,
    "actual_model_execution": False,
    "new_complex_biology_software": 0,
    "new_goal_or_scoring_policy": False,
})

artifact_hashes = {
    path.name: sha(path) for path in HERE.iterdir()
    if path.is_file() and path.name != "RELEASE_MANIFEST_002.json"
}
write("RELEASE_MANIFEST_002.json", {
    "status": "released_for_parent_integration",
    "approved_production_path_count": 9,
    "new_test_path_count": 1,
    "owned_code_sha256": pin["owned_code_hashes"],
    "external_shared_consumer_contribution": "EXTERNAL_SHARED_CHANGE_001.json",
    "final_pin_manifest_sha256": sha(HERE / "PIN_003.json"),
    "accepted_pure_sha256": accepted_pure,
    "protected_sha256": protected["sha256"],
    "artifacts_sha256": artifact_hashes,
    "test_summary": summary,
    "full_A105_adequacy": False,
    "no_goal_amendment": True,
    "no_runtime203_or_method_loop_changes": True,
    "no_228_future_work_in_frozen_pin": True,
})
print(json.dumps({"passed": len(cases), "pytest_seconds": pytest_seconds,
                  "imports_inside_pin": len(result["imports"]),
                  "owned_paths": len(pin["owned_code_hashes"]),
                  "release_manifest": "RELEASE_MANIFEST_002.json"}))
