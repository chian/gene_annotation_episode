"""Record the reviewed form-validation application and its completed checks."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = HERE / "WORK_STATUS.json"
raw = path.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == "4d3cf3c4944694d40cd703a3d921be0d3440e675d2b23e4d2a19db7068926c04"
assert not (HERE / "PROGRESS_UPDATE_034.json").exists()
work = json.loads(raw)
original = deepcopy(work)
scope_raw = (HERE / work["scope_file"]).read_bytes()
scope_hash = hashlib.sha256(scope_raw).hexdigest()
scope = json.loads(scope_raw)
authority = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert hashlib.sha256(authority.read_bytes()).hexdigest() == work["authority_sha256"]


def read(name):
    return json.loads((ROOT / name).read_text())


def hashed(name):
    return dict(path=name, sha256=hashlib.sha256((ROOT / name).read_bytes()).hexdigest())


applied = "verification/tool_graders_form_reference_apply_2026-10-25/"
receipt = read(applied + "APPLICATION_RECEIPT_001.json")
assert receipt["production_applied"] and len(receipt["files"]) == 7
assert receipt["historical_files_unchanged"] == 4641
for row in receipt["files"]:
    assert hashed(row["path"])["sha256"] == row["after_sha256"], row["path"]
tests = read(applied + "TEST_RECEIPT_001.json")
assert tests["exit_code"] == 0 and not tests["changed_sources"] and not tests["added_sources"]
suite = next(ET.parse(ROOT / (applied + "pytest_001.xml")).getroot().iter("testsuite"))
assert {k: int(suite.get(k)) for k in ("tests", "errors", "failures", "skipped")} == dict(tests=23, errors=0, failures=0, skipped=0)
assert len(tests["new_runs"]) == 1
run = tests["new_runs"][0] + "/"
guard = read(run + "SOURCE_GUARD_AFTER_TESTS.json")
assert len(guard["used_paths"]) == 310
for field in ("all_additions", "all_changes", "outside_used_additions", "outside_used_changes", "used_changes", "used_without_before_hash"):
    assert not guard[field], field
numerical = read(run + "NUMERICAL_RETURN_CHECK.json")
coverage = numerical["numbers"]["coverage"]
assert (coverage["numerator"], coverage["denominator"]) == (690, 693)
assert numerical["numbers"]["zero_gaps"]["value"] == 0
assert numerical["original_source_mapping"] == "missing"

evidence = dict(
    id="GENOME-ALIGNMENT-APPLIED-WORKFLOW-034",
    kind="reviewed_form_validation_and_prospective_fixtures_applied_controlled_Workflow_verified",
    summary="Reviewed178 changes applied to seven production/test files. All23 checks passed in993.246seconds, including six controlled Workflow checks and17 form-frame/public-validator checks. All310 used paths and the complete captured source set remained unchanged. The original requested native690/693coverage and measured0gaps reached receiving episodes; saved recalculation and immutable prior publication were tested.",
    qualification="This is controlled HTTP transport, scripted episode decisions and retained native Mauve v4 data. It is not live BV-BRC, a new aligner execution, a configured model or HPC verification. Original source mapping remains missing. Missing action_yields and excessive tracking in steering remain open presentation work. Original failed-run receipts remain unchanged; unchanged inventory identities are not new implementation progress.",
    reports=[hashed(name) for name in (
        applied + "APPLICATION_RECEIPT_001.json", applied + "PREFLIGHT_001.json",
        applied + "TEST_COMMAND_001.json", applied + "TEST_RECEIPT_001.json",
        applied + "pytest_001.xml", run + "SOURCE_GUARD_AFTER_TESTS.json",
        run + "NUMERICAL_RETURN_CHECK.json")])
assert evidence["id"] not in {r["id"] for r in work["verification_evidence"]}
work["verification_evidence"].append(evidence)
for row in work["rows"]:
    if row["id"] == "C-L202-GenomeAlignment":
        row["overall"] = "applied_controlled_Workflow_six_cases_and17_form_checks_pass_live_and_presentation_unverified"
        row["integration_verification"] = "applied_checkout23passes_six_Workflow_cases_saved_replay_and_parent_returns_verified"
        row["evidence_ids"].append(evidence["id"])
        row["note"] += " Update034: reviewed178 form-local validation reuse and prospective fixture corrections are applied to seven files. Applied-checkout23checks pass (six complete controlled Workflow checks and17 focused form checks) in993.246seconds, with310used paths and complete captured source set unchanged. Native690/693coverage and measured0gaps pass through receiving forms; changed-parameter saved recalculation and immutable earlier publication are verified.4641historical files were unchanged at application. Original source mapping remains missing. Controlled transport/scripted decisions/retained native output do not establish live service, new aligner, configured model or HPC execution. Missing action_yields and excessive tracking in steering remain unfinished. Original033 failure evidence is preserved."
for row in work["resource_bindings"]:
    if row["id"] == "C-L202-GenomeAlignment::api":
        row["integration_verification"] = "applied_checkout23passes_six_Workflow_cases_saved_replay_and_parent_returns_verified"
        row["evidence_ids"].append(evidence["id"])

changes = []
for group, count in (("rows", 308), ("resource_bindings", 288)):
    assert len(work[group]) == count
    assert [r["id"] for r in work[group]] == [r["id"] for r in original[group]] == [r["id"] for r in scope[group]]
    prior = {r["id"]: r for r in original[group]}
    changes.extend(dict(group=group, id=r["id"], before=prior[r["id"]], after=deepcopy(r))
                   for r in work[group] if r != prior[r["id"]])
assert len(changes) == 2
assert work["complete_scientific_tools_claimed"] == 0
assert hashlib.sha256((HERE / work["scope_file"]).read_bytes()).hexdigest() == scope_hash
updated = (json.dumps(work, indent=2) + "\n").encode()
record = dict(
    schema="tool_grader_progress_update_v1", date="2026-10-25",
    recorded_at=datetime.now(timezone.utc).isoformat(), author="root",
    previous_status_sha256=before, new_status_sha256=hashlib.sha256(updated).hexdigest(),
    scope_sha256_unchanged=scope_hash,
    previous_goal_turn_classification="progress",
    previous_goal_turn_evidence="Applied submitted-input binding and468 focused checks; original controlled Workflow closed and its exact fixture failure was recorded.",
    this_goal_turn_classification="progress",
    current_progress="Applied reviewed form-local fact reuse and prospective fixture corrections; all23 applied-checkout checks passed with unchanged sources. Independent proteome integration and directional numerical work remain candidates, not completed scientific tools.",
    changes=changes, added_evidence=[evidence], scope_changes=False,
    specific_pending_NCBI_job_verification_included=False, complete_scientific_tools_claimed=0)
with (HERE / "PROGRESS_UPDATE_034.json").open("x") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
path.write_bytes(updated)
print(json.dumps(dict(checkpoint=34, changed_rows_and_bindings=len(changes),
                     scope_rows=308, resource_bindings=288,
                     status_sha256=record["new_status_sha256"])))
