"""Record applied submitted-input verification and the original closed Workflow."""
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
assert before == "82c3d750f6808ac80e1787f64ad21d80ef66afc5760647b569db6541908703e5"
assert not (HERE / "PROGRESS_UPDATE_033.json").exists()
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


applied = "verification/tool_graders_bvbrc_proteome_submission_apply_2026-10-25/"
closed = "verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25/"
receipt = read(applied + "APPLICATION_RECEIPT_001.json")
assert receipt["production_applied"] and receipt["applied_file_count"] == 14
for row in receipt["files"]:
    assert hashed(row["path"])["sha256"] == row["candidate_sha256"], row["path"]
tests = read(applied + "TEST_RECEIPT_001.json")
assert tests["exit_code"] == 0 and not tests["changed_sources"] and not tests["added_sources"]
suite = next(ET.parse(ROOT / (applied + "pytest_001.xml")).getroot().iter("testsuite"))
assert {k: int(suite.get(k)) for k in ("tests", "errors", "failures", "skipped")} == dict(tests=468, errors=0, failures=0, skipped=0)
terminal = read(closed + "TERMINAL_RECEIPT_001.json")
assert terminal["natural_exit_code"] == 1 and terminal["not_executed_because_x_stop"] == 4
assert not terminal["run_interrupted"] and not terminal["run_restarted"]
assert [r["result"] for r in terminal["test_cases"]] == ["passed", "failed"]
for guard in read(closed + "TERMINAL_SOURCE_AUDIT_001.json")["checks"]:
    assert guard["used_path_count"] == 299
    for name in ("all_original_changes", "current_used_source_changes_from_before", "independent_before_after_used_mismatches", "used_changes", "used_without_before_hash"):
        assert not guard[name], name
inspection = read(closed + "ORIGINAL_WORKFLOW_INSPECTION_001.json")
assert inspection["sheet_components_match"] and inspection["scientific_form_exactly_forwards_selected_result_families"]

added = [
    dict(id="BVBRC-PROTEOME-SUBMITTED-INPUT-APPLIED-033",
         kind="reviewed_request_binding_applied_and_verified_in_production_checkout",
         summary="Reviewed175 delta applied to14 exact files after the original protected Workflow ended and all299 used paths were independently rehashed.468 focused tests passed in172.46seconds against the applied checkout; the complete captured source set stayed unchanged.",
         qualification="This repairs actual retained submitted-parameter content binding. It does not register the proteome provider or complete native artifact publication, its new pre-acquisition selector, full directional calculations, episode presentation or live-resource verification. Historical run and fixture bytes remain unchanged.",
         reports=[hashed(name) for name in (applied + "APPLICATION_RECEIPT_001.json", applied + "PREFLIGHT_001.json", applied + "TEST_COMMAND_001.json", applied + "TEST_RECEIPT_001.json", applied + "pytest_001.xml")]),
    dict(id="GENOME-ALIGNMENT-ORIGINAL-WORKFLOW-TERMINAL-033",
         kind="original_controlled_Workflow_closed_with_partial_test_suite_failure",
         summary="Original selected-tool/three-slot/child-owned HTTP-route test passed. Workflow closed naturally with690/693coverage and observed0gaps reaching both original parent forms. Original pytest ended1passed/1failed in15998.186seconds; wrong model-role versus episode-role filter caused the failure and -x left fourlater tests unrun. All299used and814original tracked paths were unchanged during the run.",
         qualification="Saved-record inspection additionally checks26actions/26observations/27scripted calls and original typed returns, but is not execution of the four skipped-by-x cases. The separately recorded candidate006 has6passes and strict replay; those passes are not attributed to the original run. Both use controlled native transport and retained output, not live BV-BRC/new aligner/configured-model science. Known missing action_yields and long tracking-heavy steering remain unresolved.",
         reports=[hashed(name) for name in (closed + "VERIFICATION_001.md", closed + "TERMINAL_RECEIPT_001.json", closed + "TERMINAL_SOURCE_AUDIT_001.json", closed + "ORIGINAL_WORKFLOW_INSPECTION_001.json", closed + "pytest_001.xml", closed + "FROZEN_TEST_SOURCE_001.py", closed + "PRESENTATION_LIMIT_002.md")]),
]
ids = [r["id"] for r in added]
assert not set(ids) & {r["id"] for r in work["verification_evidence"]}
work["verification_evidence"].extend(added)
for row in work["rows"]:
    if row["id"] == "C-L206-GenomeComparison":
        row["invocation_contract"] = "actual_submitted_request_binding_applied_and468focused_checks_passed_provider_registration_unfinished"
        row["integration_verification"] = "applied_request_binding468checks_library_and_returns_verified_separately_actual_host_and_episode_path_unfinished"
        row["evidence_ids"].append(ids[0])
        row["note"] += " Update033: reviewed175 request-binding delta is now applied to production after161natural terminal and independent source rehash.468focused applied-checkout tests pass with no source changes.176continues isolated native-host/publication integration and019selection correction; no such integration completion is claimed. Full directional scientific calculations, producer/input witnesses, episode presentation and live verification remain unfinished."
    elif row["id"] == "C-L202-GenomeAlignment":
        row["overall"] = "controlled_Workflow_closed_original1pass1fixture_failure_candidate6passes_live_and_presentation_unverified"
        row["integration_verification"] = "original_selected_child_path_test_passed_closed_records_inspected_fourlater_tests_unrun_separate_candidate6passes"
        row["evidence_ids"].append(ids[1])
        row["note"] += " Update033: original161run ended naturally,1passed/1fixturefailure in4h26m38s; fourremaining tests did notrun due-x. Wrongmodel-role filter caused failure after Workflowclosure; no historical result repaired or replaced.299used/814original sources unchanged duringrun. Saved original forms preserve690/693and0,26actions/26observations/27scripted calls. Separatecandidate6passes remain separate. Fresh178prepares prospective performance/fixture integration. Known action_yields/steering gaps and live/configured execution remain unfinished."
for row in work["resource_bindings"]:
    if row["id"] == "C-L206-GenomeComparison::api":
        row["invocation_contract"] = "actual_retained_submitted_request_binding_applied_and468checks_passed"
        row["evidence_ids"].append(ids[0])
    elif row["id"] == "C-L202-GenomeAlignment::api":
        row["integration_verification"] = "original_selected_child_path_test_passed_closed_records_inspected_fourlater_tests_unrun_separate_candidate6passes"
        row["evidence_ids"].append(ids[1])

changes = []
for group, count in (("rows", 308), ("resource_bindings", 288)):
    assert len(work[group]) == count
    assert [r["id"] for r in work[group]] == [r["id"] for r in original[group]] == [r["id"] for r in scope[group]]
    prior = {r["id"]: r for r in original[group]}
    changes.extend(dict(group=group, id=r["id"], before=prior[r["id"]], after=deepcopy(r)) for r in work[group] if r != prior[r["id"]])
assert len(changes) == 4
assert work["complete_scientific_tools_claimed"] == 0
assert hashlib.sha256((HERE / work["scope_file"]).read_bytes()).hexdigest() == scope_hash
updated = (json.dumps(work, indent=2) + "\n").encode()
record = dict(schema="tool_grader_progress_update_v1", date="2026-10-25", recorded_at=datetime.now(timezone.utc).isoformat(),
    author="root", previous_status_sha256=before, new_status_sha256=hashlib.sha256(updated).hexdigest(), scope_sha256_unchanged=scope_hash,
    previous_goal_turn_classification="progress", previous_goal_turn_evidence="Checkpoint032 accepted library/return components and candidate submitted-input repair; actual host inspection established the circular artifact-selection defect and a concrete correction. Inventory wording itself is not implementation progress.",
    this_goal_turn_classification="progress", current_progress="Applied reviewed request-binding repair and verified468cases with clean source capture. Recorded natural original Workflow completion and its exact test failure. Independent native-host, directional-contract and prospective form-validation work continues.",
    changes=changes, added_evidence=added, scope_changes=False, specific_pending_NCBI_job_verification_included=False, complete_scientific_tools_claimed=0)
with (HERE / "PROGRESS_UPDATE_033.json").open("x") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
path.write_bytes(updated)
print(json.dumps(dict(checkpoint=33, changed_rows_and_bindings=len(changes), scope_rows=308, resource_bindings=288, status_sha256=record["new_status_sha256"])))
