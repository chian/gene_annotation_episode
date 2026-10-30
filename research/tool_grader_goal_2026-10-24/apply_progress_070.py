"""Record implemented convergence field/binding/worker functions, no tally gain."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_070.json"
B = ROOT / "verification/tool_graders_native_blast_convergence_bridge_2026-10-26_328"
R = ROOT / "verification/tool_graders_native_blast_convergence_worker_2026-10-26_329"
E = ROOT / "verification/tool_graders_native_blast_database_episode_binding_2026-10-26_321"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def descriptor(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path))


def passed(directory, summary):
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == 0
    assert receipt["metadata"]["policy"] == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
    assert summary in (directory / "stdout.txt").read_text()


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = read(HERE / "PROGRESS_UPDATE_069.json")
before_sha = sha(STATUS)
assert before_sha == previous["new_status_sha256"]
scope_sha = sha(HERE / "SCOPE.json")
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS); original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 99
assert status["verified_bound_local_tool_mode_rows"] == 40
authority = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert sha(authority) == status["authority_sha256"]
for row in read(R / "SOURCE_HASHES_001.json"):
    path = ROOT / row["path"]
    assert sha(path) == row["sha256"] and path.stat().st_size == row["size_bytes"]
for example in read(R / "EXAMPLES_001.json"):
    for row in example["artifacts"]:
        path = ROOT / row["path"]
        assert sha(path) == row["sha256"] and path.stat().st_size == row["size_bytes"]
for legacy in read(R / "LEGACY_GENERATIONS_001.json"):
    for row in legacy["files"]:
        assert sha(ROOT / row["path"]) == row["sha256"]
passed(B / "check003", "235 passed")
passed(B / "check004", "117 passed")
passed(B / "check005", "74 passed")
passed(R / "check003", "73 passed")
passed(R / "check005", "2 passed")
assert read(R / "check004/receipt.json")["returncode"] == 1
assert "1 failed, 28 passed" in (R / "check004/stdout.txt").read_text()
passed(E / "check_20261026T203635271636Z", "5 passed")
added = []


def add(identity, summary, qualification, paths):
    item = dict(id=identity, kind="reviewed_implementation_component", reports=[descriptor(p) for p in paths],
        summary=summary, qualification=qualification)
    assert not any(r["id"] == identity for r in status["verification_evidence"])
    status["verification_evidence"].append(item); added.append(item)


add("BLAST-NATIVE-CONVERGENCE-BINDING-070",
    "Closed captured-input/native-convergence fields and pure binding/saved-validation functions implemented; M optionalv2 field population preserves legacyv1.",
    "74 focused and235 existing regression cases passed;43 control-line cases also passed. Counts overlap. Root inspected complete bridge and M population; independent330 review pending. No live native search.",
    [B / name for name in ("HANDOFF_001.md", "ROOT_REVIEW_001.md", "SOURCE_HASHES_002.json", "TEST_RECEIPTS_002.json", "EXAMPLE_INDEX_002.json")])
add("BLAST-NATIVE-CONVERGENCE-WORKER-070",
    "Actual captured bytes connect316 to M/311 and frozen numeric rows; exact native extraction artifact, occurrence identity and v1/v2 saved recalculation implemented.",
    "73 joined cases passed;28 later focused cases passed with1 invalid fixture assumption corrected in the2 passing follow-up cases. All6 legacy generations and60 original files preserved; artifact bytes stable across hash seeds1/2/91. No E completion or new formula claimed.",
    [R / name for name in ("HANDOFF_001.md", "SOURCE_HASHES_001.json", "TEST_RECEIPTS_001.json", "EXAMPLES_001.json", "LEGACY_GENERATIONS_001.json", "FACT_SCHEMAS_BEFORE_001.json")])
add("BLAST-NATIVE-CONVERGENCE-CHILD-CHECK-070",
    "Five focused actual controlled child-return cases passed, covering received-cell unions, oldv1 replay and PSI/DELTA duplicate convergence delivery.",
    "E321 broader consolidation and root full-path acceptance remain pending. Failed native attempt delivery exposed a separate handoff filtering defect; accepted314/010 correction is under test. No live PBS or native BLAST execution.",
    [E / "check_20261026T203635271636Z" / name for name in ("receipt.json", "stdout.txt", "stderr.txt")]
    + [ROOT / "verification/tool_graders_native_blast_database_result_contract_2026-10-26_314/CONTRACT_ADDENDUM_009.md",
       ROOT / "verification/tool_graders_native_blast_database_result_contract_2026-10-26_314/CONTRACT_ADDENDUM_010.md"])

selected = {"A-L070-" + mode + "-database" for mode in ("psiblast", "deltablast", "rpsblast", "rpstblastn", "blastn_vdb", "tblastn_vdb")}
native = {"A-L070-psiblast-database", "A-L070-deltablast-database"}
changes = []
for row in status["rows"]:
    if row["id"] not in selected:
        continue
    before = deepcopy(row)
    row["production_result_binding"] = "worker_views_and_fact_forms_reviewed_legacy_recalculation_verified_scientific_episode_consumer_consolidation_pending"
    row["numerical_verification"] += "_329_worker_regressions_and_six_retained_v1_recalculations_passed_counts_overlap"
    if row["id"] in native:
        row["metadata_extractor"] = "captured_source_qualification_native_convergence_binding_and_optional_v2_sheet_population_implemented_and_verified_authentic_native_execution_pending"
        row["numerical_sheet"] += "_native_convergence_binding_v2_with_full_retained_extraction"
        row["production_result_binding"] = "native_convergence_connected_through_actual_worker_and_focused_child_returns_final_shared_path_acceptance_pending"
        row["numerical_verification"] += "_74_bridge_235_regression_73_joined_worker_cases_passed_followup_conflict_hashseed_and_partial_cases_verified_counts_overlap"
    row["evidence_ids"].extend(r["id"] for r in added)
    row["note"] += " Update070: implementation means field definitions and executable field-population/calculation functions; generated sheets are test outputs. PSI/DELTA native convergence is now connected through the actual worker and focused child returns, with source-specific occurrence identities and exact saved-v2 reuse. Legacyv1 remains unchanged. Four fresh non-PSI workers also verify their declared dependency inventory. E321 consolidation, failed-attempt partial handoff010 and independent330 review remain pending. All receipts, including corrected failures, are retained. Native HPC execution remains unverified; no tally increment."
    changes.append(dict(group="rows", id=row["id"], before=before, after=deepcopy(row)))
for row in status["resource_bindings"]:
    if row["id"] not in {key + "::hpc" for key in selected}:
        continue
    before = deepcopy(row)
    row["production_result_binding"] = "controlled_numerical_worker_and_focused_child_returns_verified_final_shared_consumer_and_partial_handoff_acceptance_pending"
    row["evidence_ids"].extend(r["id"] for r in added)
    changes.append(dict(group="resource_bindings", id=row["id"], before=before, after=deepcopy(row)))
assert len(changes) == 12
for group in ("rows", "resource_bindings"):
    affected = {c["id"] for c in changes if c["group"] == group}
    assert [r["id"] for r in status[group]] == [r["id"] for r in original[group]]
    assert all(a == b for a,b in zip(original[group],status[group]) if a["id"] not in affected)
raw = (json.dumps(status,indent=2,ensure_ascii=False) + "\n").encode()
update = dict(schema="tool_grader_progress_update_v1", date="2026-10-26", author="root",
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=added,
    numerical_grader_progress_tally=dict(before=99,after=99,added_row_ids=[],meaning="Implementation components and controlled partial paths do not complete additional tool graders."),
    verified_bound_local_tool_mode_rows=dict(before=40,after=40), remaining_fixed_rows_outside_tally=209,
    completed_work=["328 captured-input and native-convergence field/binding functions implemented and root-reviewed.",
        "329 worker connection, native occurrence rows, legacyv1/v2 saved recalculation and program-specific dependency validation implemented and tested.",
        "Five focused E received-cell/legacy replay/native convergence child-return cases passed; specific boundary evidence only."],
    unfinished_work=["Independent330 review and E321 consolidated shared-consumer/credit/full-path acceptance remain pending.",
        "Actual failed native partial-result delivery correction314/010 is implemented by E and under verification.",
        "Authentic native mode fixtures and actual HPC deployment/execution remain unverified.",
        "327 standard-five interfaces accepted; fresh331 implements only new producer/contracts/tool information. Its work is unverified and has no tally credit.",
        "Remaining308 scope, separateW05 work and literature exclusion stay unchanged."],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status["complete_scientific_tools_claimed"])
assert sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as stream:
    json.dump(update,stream,indent=2,ensure_ascii=False);stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.070.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=6,updated_resource_bindings=6,scope_rows=308,
    numerical_grader_progress_tally=99,new_status_sha256=sha(STATUS))))
