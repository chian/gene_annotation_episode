"""Record reviewed VDB metadata and the independent census counterexamples."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_078.json"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = read(HERE / "PROGRESS_UPDATE_077.json")
before_sha = sha(STATUS)
scope_sha = sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 108
assert status["verified_bound_local_tool_mode_rows"] == 40
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]

metadata = ROOT / "verification/tool_graders_blast_vdb_function_metadata_2026-10-26_345"
review = ROOT / "verification/tool_graders_blast_vdb_function_calculator_review_2026-10-26_348"
pins = read(metadata / "SOURCE_PINS_FINAL_001.json")
records = (read(metadata / "RETAINED_INPUTS_AND_EXAMPLES_001.json")["records"]
           + pins["owned"] + pins["input_fixtures"]
           + [pins["helper_before"], pins["helper_released"]])
assert len(records) == 77
for record in records:
    path = Path(record["path"])
    assert sha(path) == record["sha256"] and path.stat().st_size == record["size_bytes"]
for packet, run, count in [(metadata, "run_009", 235), (metadata, "run_010", 55),
                           (review, "run_001", None)]:
    receipt = read(packet / run / "receipt.json")
    assert receipt["native_returncode"] == 0
    assert receipt["policy"] == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
    if count is not None:
        assert f"{count} passed" in (packet / run / "stdout.txt").read_text()

specs = [
    ("BLAST-VDB-FUNCTION-METADATA-078", metadata,
     ["ROOT_REVIEW_001.md", "HANDOFF_001.md", "SOURCE_PINS_FINAL_001.json",
      "RETAINED_INPUTS_AND_EXAMPLES_001.json", "run_009/receipt.json", "run_009/stdout.txt",
      "run_010/receipt.json", "run_010/stdout.txt"],
     "345 supplied-metadata component accepted at its recorded source generation. Root verified77 byte identities and inspected merged feature associations, native GBSeq labels, sparse HSP locations and actual235/55-pass overlapping receipts. Complete VDB acceptance remains pending."),
    ("BLAST-VDB-CENSUS-COUNTEREXAMPLES-078", review,
     ["FINDINGS_001.md", "HANDOFF_001.md", "run_001/receipt.json",
      "run_001/artifacts/review_results.json"],
     "348 reproduced two input-qualification defects: conflicting available sample relationships change corrected weights, and unresolved optional dependence incorrectly prevents baseline/qualify_separate correction.350 owns repairs; this records findings, not repaired behavior."),
]
evidence = []
for identity, packet, names, summary in specs:
    item = dict(id=identity, kind="reviewed_component", summary=summary,
                reports=[dict(path=str((packet/name).relative_to(ROOT)), sha256=sha(packet/name)) for name in names],
                qualification="Supplied/synthetic data only; final repaired integration and live native execution remain unfinished.")
    assert not any(r["id"] == identity for r in status["verification_evidence"])
    status["verification_evidence"].append(item)
    evidence.append(item)

vdb = {"A-L070-blastn_vdb-database", "A-L070-tblastn_vdb-database"}
changes = []
for row in status["rows"]:
    if row["id"] not in vdb:
        continue
    before = deepcopy(row)
    row["metadata_extractor"] += "_function_wire_component_reviewed_at_recorded_generation"
    row["overall"] = "partial_vdb_function_metadata_reviewed_census_relation_repairs_and_final_integration_pending"
    row["evidence_ids"].extend(e["id"] for e in evidence)
    row["note"] += " Update078:345 supplied-metadata component accepted after complete source/test/helper review,77 byte checks and actual235/55-pass overlapping receipts.348 reproduced two census relation defects at input78e0491b;350 owns exact input-only repair.347 continues selected captured/saved result integration. No final VDB acceptance or count increase; live execution and source-locator coverage remain separately limited."
    changes.append(dict(group="rows", id=row["id"], before=before, after=deepcopy(row)))
assert len(changes) == 2
assert status["resource_bindings"] == original["resource_bindings"]
assert [r["id"] for r in status["rows"]] == [r["id"] for r in original["rows"]]
assert all(a == b for a, b in zip(original["rows"], status["rows"]) if a["id"] not in vdb)

checklist = deepcopy(previous["work_item_states"])
for item in checklist:
    if item["id"] == "U02":
        item["current_evidence"] = "345 metadata component reviewed and accepted at recorded generation.348 reproduced two census relation defects;350 owns repair.347 captured/saved worker and typed-return verification continues. Both VDB rows remain outside108."
    if item["id"] == "U05":
        item["current_evidence"] = "All remaining fixed308 rows and resource bindings stay in scope.349 has drafted the two RNA scientific contracts; exact cross-lane interfaces still need completion before coding. W05 and literature grading remain separate."
assert [(i["id"], i["original_item"], i["status"]) for i in checklist] == [(i["id"], i["original_item"], i["status"]) for i in previous["work_item_states"]]

raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = dict(schema="tool_grader_progress_update_v1", date="2026-10-26", author="root",
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=evidence,
    numerical_grader_progress_tally=dict(before=108, after=108, added_row_ids=[], meaning=previous["numerical_grader_progress_tally"]["meaning"]),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=200,
    completed_work=[evidence[0]["summary"]], findings_requiring_repair=[evidence[1]["summary"]],
    work_item_states=checklist,
    unfinished_work=[i["current_evidence"] for i in checklist if i["status"] != "complete"],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status["complete_scientific_tools_claimed"])
assert sha(STATUS) == before_sha and sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.078.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=2, updated_resource_bindings=0, scope_rows=308,
    numerical_grader_progress_tally=108, remaining_fixed_rows_outside_tally=200,
    new_status_sha256=sha(STATUS))))
