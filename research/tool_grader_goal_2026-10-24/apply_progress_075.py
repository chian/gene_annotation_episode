"""Record the reviewed standard-five numerical grader and episode integration."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_075.json"
E = ROOT / "verification/tool_graders_standard_blast_database_episode_binding_2026-10-26_336"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = read(HERE / "PROGRESS_UPDATE_074.json")
before_sha, scope_sha = sha(STATUS), sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 103
assert status["verified_bound_local_tool_mode_rows"] == 40
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]
evidence = read(E / "HANDOFF_EVIDENCE_001.json")
for group in ("source_new", "source_shared", "source_tests", "knowledge", "frozen_source_copies"):
    for row in evidence[group]:
        path = ROOT / row["path"]
        assert sha(path) == row["sha256"] and path.stat().st_size == row["size_bytes"]
run_names = ("check_20261026T221431853348Z", "check_20261026T221431853335Z")
for name, count in zip(run_names, (98, 15)):
    receipt = read(E / name / "receipt.json")
    assert receipt["returncode"] == 0
    assert receipt["metadata"]["policy"] == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
    assert f"{count} passed" in (E / name / "stdout.txt").read_text()
paths = [E / name for name in ("ROOT_REVIEW_001.md", "HANDOFF_001.md", "HANDOFF_EVIDENCE_001.json",
    "VERIFICATION_001.md", "ROOT_REVIEW_FINDINGS_001.md", "ROOT_REVIEW_CORRECTIONS_001.md",
    "LOCAL_JOB_FAILURE_HANDOFF_001.md", "VERIFICATION_MATRIX_001.md")]
paths += [E / name / part for name in run_names for part in ("receipt.json", "stdout.txt")]
item = dict(id="BLAST-STANDARD-DATABASE-EPISODE-INTEGRATION-075", kind="reviewed_integrated_grader",
    reports=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p)) for p in paths],
    summary="Standard five numerical graders now have verified original-attempt production acquisition, actual M/R worker binding, scoped numerical publication and typed episode returns;113 final-source checks passed.",
    qualification="Fake PBS and synthetic native-file emitter through real production code; frozen pre339 public dependencies. Earlier251 regression is a separate source window. Live HPC/deployment and remaining FASTA/census/format obligations remain unfinished.")
assert not any(row["id"] == item["id"] for row in status["verification_evidence"])
status["verification_evidence"].append(item)
ids = {"A-L069-" + p + "-database" for p in ("blastn", "blastp", "blastx", "tblastn", "tblastx")}
changes = []
for row in status["rows"]:
    if row["id"] not in ids:
        continue
    before = deepcopy(row)
    row["overall"] = "numerical_grader_and_declared_episode_path_verified_live_resource_unverified"
    row["source_presence"] = "integrated_source_present"
    row["tool_information"] = "explicit_standard_database_hpc_catalog_contracts_library_and_shared_discovery_verified"
    row["invocation_contract"] = "closed_standard_database_request_selected_hpc_child_original_plan_and_one_command_producer_synthetically_verified"
    row["production_result_binding"] = "original_attempt_capture_actual_metadata_and_numerical_worker_scoped_publication_and_typed_parent_return_verified"
    row["integration_verification"] = "113_final_source_checks_passed_actual_production_path_with_fake_pbs_and_synthetic_native_emitter"
    row["evidence_ids"].append(item["id"])
    row["note"] += " Update075: root accepted E336 after complete new-module/test and shared-consumer review, actual98+15 passing final receipts and independent2642-identity evidence check (two current public dependencies changed only after339 release; all frozen copies match). The five rows enter the numerical-grader tally. Failure handling preserves original typed lifecycle facts; selected native failure retains partial rows without completion, and valid practical completion sets future gain to exact zero. Received-cell union uses only actually delivered cells. Earlier251 regression is separate. No live database/HPC execution or full-goal completion claim; FASTA v2 integration, native-path/census association, native format coverage and resource deployment remain open."
    changes.append(dict(group="rows", id=row["id"], before=before, after=deepcopy(row)))
for row in status["resource_bindings"]:
    if row["id"] not in {key + "::hpc" for key in ids}:
        continue
    before = deepcopy(row)
    row["invocation_contract"] = "selected_hpc_child_original_pbs_attempt_plan_and_producer_synthetically_verified"
    row["production_result_binding"] = "actual_capture_metadata_worker_publication_and_typed_return_code_verified_with_synthetic_native_emitter"
    row["integration_verification"] = "113_final_source_checks_passed_including_standard_hpc_dispatch_authority_and_returns"
    row["native_format_observed"] = "synthetic_standard_database_outputs_retained_paired_format_evidence_labelled_separately"
    row["evidence_ids"].append(item["id"])
    changes.append(dict(group="resource_bindings", id=row["id"], before=before, after=deepcopy(row)))
assert len(changes) == 10
for group in ("rows", "resource_bindings"):
    affected = {c["id"] for c in changes if c["group"] == group}
    assert [r["id"] for r in status[group]] == [r["id"] for r in original[group]]
    assert all(a == b for a, b in zip(original[group], status[group]) if a["id"] not in affected)
assert previous["unfinished_work"][0].startswith("Fresh E336")
remaining = list(previous["unfinished_work"][1:])
remaining.append("339 public FASTA record support is implemented with927 compatibility tests;340 owns exact wire/proof/saved metadata integration. Actual worker/typed-return propagation and distinct record-quality row identities remain unfinished.")
remaining.append("341 is correcting the independently confirmed native-six lifecycle exception/misclassification defect; no scientific calculator changes or tally increment are assigned to that repair.")
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = dict(schema="tool_grader_progress_update_v1", date="2026-10-26", author="root",
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=[item],
    numerical_grader_progress_tally=dict(before=103, after=108, added_row_ids=sorted(ids),
        meaning="Implemented numerical fields/functions/calculators with verified declared episode result paths. Live-resource and further format coverage remain separate fields; this is not full-goal completion."),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=200,
    completed_work=["E336 standard five database BLAST production result integration root accepted with113 final-source passing checks; five fixed rows added to numerical-grader tally."],
    unfinished_work=remaining, inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status["complete_scientific_tools_claimed"])
assert sha(STATUS) == before_sha and sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.075.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=5, updated_resource_bindings=5, scope_rows=308,
    numerical_grader_progress_tally=108, remaining_fixed_rows_outside_tally=200,
    new_status_sha256=sha(STATUS))))
