"""Record reviewed field/population/calculation components, with no tally gain."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_069.json"
PACKETS = ROOT / "verification"
M = PACKETS / "tool_graders_native_blast_database_metadata_2026-10-26_317"
R = PACKETS / "tool_graders_native_blast_result_review_2026-10-26_324"
C = PACKETS / "tool_graders_native_blast_fact_form_2026-10-26_323"
K = PACKETS / "tool_graders_native_blast_database_knowledge_2026-10-26_326"
E = PACKETS / "tool_graders_native_blast_database_episode_binding_2026-10-26_321"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def descriptor(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path))


def passed(directory, summary):
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == 0
    assert receipt["metadata"]["policy"] == policy
    assert summary in (directory / "stdout.txt").read_text()


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = read(HERE / "PROGRESS_UPDATE_068.json")
before_sha = sha(STATUS)
assert before_sha == previous["new_status_sha256"]
scope_sha = sha(HERE / "SCOPE.json")
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 99
assert status["verified_bound_local_tool_mode_rows"] == 40
authority = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert sha(authority) == status["authority_sha256"]
policy = dict(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
for row in read(M / "SOURCE_HASHES_001.json")["owned"]:
    path = ROOT / row["path"]
    assert sha(path) == row["sha256"] and path.stat().st_size == row["size_bytes"]
examples = read(M / "EXAMPLES_001.json")["examples"]
assert len(examples) == 5
example_count = 0
for example in examples:
    for row in example["artifacts"] + example["captured_inputs"]:
        path = ROOT / row["path"]
        assert sha(path) == row["sha256"] and path.stat().st_size == row["size_bytes"]
        example_count += 1
assert example_count == 41
expected = {
    "gene_annotation_episode/native_blast_database_result_worker.py": "f5779805bdfaa49fcf1d7f0d1e52d66400f9b0799cee174918369ef7795de619",
    "gene_annotation_episode/native_blast_database_result_views.py": "0d3ad104b8d26249ff79806a586fa332a6fedd3b892bb991bbb56c232e3aa80d",
    "tests/test_native_blast_result_review.py": "2519bb6b79244b548c9ce585573977ffc92b1401d6a3e137da108c5d64a66362",
    "gene_annotation_episode/communication.py": "655bc1025b3b609bdae55cb46ec7ac4ba6d72ec7d790ff30bf430e6683a241cb",
    "tests/test_native_blast_fact_forms.py": "ebc1a27ac3059d0840c1872ee3417155edc961154edec2df125ec5270a60c2a4",
}
for path, digest in expected.items():
    assert sha(ROOT / path) == digest
passed(M / "check_011", "525 passed")
passed(R / "check001", "69 passed")
passed(C / "check_20261026T194407751970Z", "102 passed")
passed(K / "check001", "13 passed")
passed(E / "check_20261026T193639339498Z", "6 passed")
regression = C / "check_20261026T193930339501Z"
baseline = C / "reference_baseline_20261026T194315277694Z"
assert read(regression / "receipt.json")["returncode"] == 1
assert "4 failed, 652 passed" in (regression / "stdout.txt").read_text()
assert read(baseline / "receipt.json")["returncode"] == 1
assert "4 failed" in (baseline / "stdout.txt").read_text()
registration = read(K / "registration001/receipt.json")
assert registration["status"] == "verified" and registration["all_prior_entries_unchanged"]
assert registration["scientific_operations_executed"] == 0
for row in registration["files"]:
    path = ROOT / row["path"]
    assert sha(path) == row["sha256"] and path.stat().st_size == row["size_bytes"]

evidence = []


def add(identity, summary, qualification, files):
    item = dict(id=identity, kind="reviewed_implementation_component",
        reports=[descriptor(path) for path in files], summary=summary, qualification=qualification)
    assert not any(r["id"] == identity for r in status["verification_evidence"])
    status["verification_evidence"].append(item)
    evidence.append(item)


add("BLAST-DATABASE-METADATA-069", "Five closed metadata schemas and source-qualified field-population functions implemented and root-reviewed.",
    "525 metadata/dependency cases passed; five synthetic numerical groups and41 saved input/output files checked. No native search or full episode claim.",
    [M / name for name in ("HANDOFF_001.md", "ROOT_REVIEW_001.md", "SOURCE_HASHES_001.json", "EXAMPLES_001.json", "check_011/receipt.json")])
add("BLAST-DATABASE-WORKER-VIEWS-069", "Combined parser/population/calculator worker and requested saved-value views reviewed; stable failure order and constrained unavailable-address diagnostics corrected.",
    "69 joined tests passed with finalM007; hash-seed1/2/91 worker diagnostics and rows identical. Scientific publication and native convergence binding remain in progress.",
    [R / name for name in ("CONTRACT_001.md", "ROOT_REVIEW_001.md", "check001/receipt.json")]
    + [ROOT / path for path in list(expected)[:3]])
add("BLAST-DATABASE-FACT-FORMS-069", "Exact registered recorded-field schemas, conditional/reference traversal and tuple uniqueness implemented and root-reviewed.",
    "102 dedicated cases passed. Broader652 passed with4 existing stub failures reproduced against original communication; broader run is not fully passing.",
    [C / name for name in ("HANDOFF_001.md", "ROOT_REVIEW_001.md", "SOURCE_AND_RECEIPT_HASHES_001.json", "check_20261026T194407751970Z/receipt.json", "check_20261026T193930339501Z/receipt.json", "reference_baseline_20261026T194315277694Z/receipt.json")])
add("BLAST-DATABASE-KNOWLEDGE-069", "Six conditional HPC tool names registered with existing operation/monitoring manual and numerical-results instructions.",
    "Actual frozen discovery/read verified;14 prior entries unchanged;13 existing instruction-runtime/descriptor tests passed. No deployment or capability inferred from index.",
    [K / name for name in ("CONTRACT_001.md", "HANDOFF_001.md", "registration001/receipt.json", "check001/receipt.json")])
add("BLAST-DATABASE-CONTROLLED-CHILD-069", "Retained six-mode controlled PBS-to-capture-to-worker-to-original-child-return receipt passed.",
    "These earlier source-only fixtures use synthetic emitted reports, not native BLAST. Later scientific-record consumer changes are still under implementation/test and root full-path review.",
    [E / "check_20261026T193639339498Z" / name for name in ("receipt.json", "stdout.txt", "stderr.txt")])

modes = ("psiblast", "deltablast", "rpsblast", "rpstblastn", "blastn_vdb", "tblastn_vdb")
selected = {"A-L070-" + mode + "-database" for mode in modes}
changes = []
for row in status["rows"]:
    if row["id"] not in selected:
        continue
    before = deepcopy(row)
    row["tool_information"] = "four_field_conditional_hpc_descriptors_and_registered_frozen_instruction_sections_verified"
    row["invocation_contract"] = "selected_native_compiler_producer_and_controlled_pbs_child_receipt_verified_real_hpc_deployment_pending"
    row["metadata_extractor"] += "_captured_metadata_source_validation_and_sheet_population_reviewed"
    row["production_result_binding"] = "combined_numerical_worker_views_and_fact_forms_reviewed_scientific_episode_consumer_integration_under_verification"
    row["numerical_verification"] += "_525_metadata_dependency_69_joined_worker_102_dedicated_form_13_instruction_tests_passed_counts_overlap"
    row["integration_verification"] = "six_controlled_source_only_child_paths_passed_new_scientific_record_hooks_and_full_root_review_pending"
    row["evidence_ids"].extend(item["id"] for item in evidence)
    row["note"] += " Update069: field definitions and deterministic field-population/calculator/view functions are reviewed and tested. Filled sheets are synthetic test outputs. Actual instruction registration is verified. Six earlier controlled child-return paths passed; new scientific record hooks remain under test/review, native convergence extraction remains to be connected, and actual native HPC execution is unverified. Broader communication regressions include4 reproduced baseline fixture failures. No tally increment."
    changes.append(dict(group="rows", id=row["id"], before=before, after=deepcopy(row)))
for row in status["resource_bindings"]:
    if row["id"] not in {key + "::hpc" for key in selected}:
        continue
    before = deepcopy(row)
    row["invocation_contract"] = "selected_native_compiler_producer_and_controlled_pbs_child_receipt_verified_real_hpc_deployment_pending"
    row["production_result_binding"] = "numerical_worker_views_reviewed_shared_episode_scientific_consumers_under_verification"
    row["integration_verification"] = "six_controlled_source_only_child_return_receipts_passed_new_scientific_hooks_and_full_root_review_pending"
    row["evidence_ids"].extend(item["id"] for item in evidence)
    changes.append(dict(group="resource_bindings", id=row["id"], before=before, after=deepcopy(row)))
assert len(changes) == 12
for group in ("rows", "resource_bindings"):
    affected = {c["id"] for c in changes if c["group"] == group}
    assert [r["id"] for r in status[group]] == [r["id"] for r in original[group]]
    assert all(a == b for a, b in zip(original[group], status[group]) if a["id"] not in affected)
assert sha(HERE / "SCOPE.json") == scope_sha
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = dict(schema="tool_grader_progress_update_v1", date="2026-10-26", author="root",
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=evidence,
    numerical_grader_progress_tally=dict(before=99, after=99, added_row_ids=[],
        meaning="Reviewed components and controlled partial paths do not complete additional tool graders."),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=209,
    completed_work=["M317 field-population/source-qualification functions root-reviewed;525 tests passed.",
        "R324 combined worker/views root-reviewed;69 joined tests passed.",
        "323 fact-form boundary root-reviewed;102 dedicated tests passed;4 broader baseline failures retained.",
        "326 actual instruction registration verified;13 existing tests passed.",
        "Six earlier controlled source-only child-return cases passed; this is specific partial-path evidence."],
    unfinished_work=["E321 scientific publication/received-source authority and all consumer paths remain under test and full root review.",
        "325 is planning the native convergence extraction bridge, occurrence identity and unchanged frozen-form compatibility; no coding authorized yet.",
        "Authentic native PSI/DELTA/RPS/RPST/VDB fixtures and real HPC deployment/execution remain unverified.",
        "327 is planning the five fixed standard native database BLAST rows; no production edits authorized yet.",
        "Remaining fixed308 scope, literature exclusion and separateW05 boundary remain unchanged."],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status["complete_scientific_tools_claimed"])
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.069.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=6, updated_resource_bindings=6, scope_rows=308,
    numerical_grader_progress_tally=99, new_status_sha256=sha(STATUS))))
