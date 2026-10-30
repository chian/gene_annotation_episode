"""Record reviewed standard producer and the two-comparison metadata fix."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_072.json"
N = ROOT / "verification/tool_graders_standard_blast_database_producer_2026-10-26_331"
FIX = ROOT / "verification/tool_graders_blast_sidecar_metadata_contract_fix_2026-10-26_335"
PLAN = ROOT / "verification/tool_graders_standard_blast_database_plan_2026-10-26_327"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def descriptor(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path))


def result(directory, returncode, summary):
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == returncode
    policy = receipt.get("policy", receipt.get("metadata", {}).get("policy"))
    assert policy == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
    assert summary in (directory / "stdout.txt").read_text()


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = read(HERE / "PROGRESS_UPDATE_071.json")
before_sha = sha(STATUS)
assert before_sha == previous["new_status_sha256"]
scope_sha = sha(HERE / "SCOPE.json")
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 103
assert status["verified_bound_local_tool_mode_rows"] == 40
authority = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert sha(authority) == status["authority_sha256"]
for row in read(N / "FINAL_SOURCE_HASHES_001.json")["sources"]:
    path = ROOT / row["path"]
    assert sha(path) == row["sha256"] and path.stat().st_size == row["size_bytes"]
source = ROOT / "gene_annotation_episode/native_blast_database_metadata.py"
old = (FIX / "source_before/native_blast_database_metadata.py").read_bytes()
expected = old.replace(
    b'_metadata_capture_key(selected["database_key"], address["role"], expected)',
    b'_metadata_capture_key(selected["database_key"], "metadata", expected)').replace(
    b'_metadata_capture_key(selected["database_key"], role, expected)',
    b'_metadata_capture_key(selected["database_key"], "metadata", expected)')
assert source.read_bytes() == expected
assert sha(source) == "398d992c4d9841bdbe4b2414f51fdacea2a757c3cd6c5d0e9d9019440c8cfcec"
result(N / "check003", 0, "196 passed")
result(N / "check004", 0, "137 passed")
result(FIX / "check002_before", 1, "51 failed, 24 passed")
result(FIX / "check003_after", 0, "144 passed")
added = []


def add(identity, summary, qualification, paths):
    item = dict(id=identity, kind="reviewed_implementation_component",
        reports=[descriptor(p) for p in paths], summary=summary, qualification=qualification)
    assert not any(r["id"] == identity for r in status["verification_evidence"])
    status["verification_evidence"].append(item)
    added.append(item)


add("BLAST-STANDARD-DATABASE-PRODUCER-072",
    "Five standard database program contracts, one-command producer and explicit HPC tool information implemented, synthetically tested and root reviewed.",
    "196 combined cases passed;137 final contract cases passed after a defensive invalid-type guard. Counts overlap. Synthetic file-writing subprocesses, not native BLAST or HPC submissions. Actual M/R/E path and deployment remain unfinished.",
    [N / name for name in ("ROOT_REVIEW_001.md", "VERIFICATION_001.md", "INTERFACE_HANDOFF_002.md", "FINAL_SOURCE_HASHES_001.json", "TEST_RECEIPT_INDEX_001.json")])
add("BLAST-DATABASE-SIDECAR-COMPATIBILITY-072",
    "Two public-validator/native6-resolver capture-key comparisons corrected to the producer's metadata role; logical sidecar roles and original identities remain unchanged.",
    "51 failures before correction;144 checks pass after correction including75 new and69 existing native metadata cases. Root reconstructed exact two-line edit and verified60 original/pinned fixture descriptors. No new science, formula, schema, episode or historical-generation change.",
    [FIX / name for name in ("ROOT_REVIEW_001.md", "CONTRACT_001.md", "VERIFICATION_001.md", "SOURCE_DIFF.patch", "SOURCE_AFTER.json", "EXAMPLES_001.json", "check002_before/receipt.json", "check002_before/stdout.txt", "check003_after/receipt.json", "check003_after/stdout.txt")])
standard_ids = {"A-L069-" + p + "-database" for p in ("blastn", "blastp", "blastx", "tblastn", "tblastx")}
native_ids = {"A-L070-" + p + "-database" for p in ("psiblast", "deltablast", "rpsblast", "rpstblastn", "blastn_vdb", "tblastn_vdb")}
changes = []
for row in status["rows"]:
    if row["id"] not in standard_ids | native_ids:
        continue
    before = deepcopy(row)
    if row["id"] in standard_ids:
        row["tool_information"] = "explicit_standard_database_hpc_catalog_contracts_and_library_freeze_resolution_verified_shared_discovery_in_progress"
        row["invocation_contract"] = "closed_standard_database_request_compilation_and_one_command_producer_verified_shared_dispatch_in_progress"
        row["overall"] = "partial_standard_database_producer_verified_population_calculation_and_episode_integration_in_progress"
        row["evidence_ids"].append(added[0]["id"])
        row["note"] += " Update072: N331 full source/tests/receipts reviewed;196 combined and137 final contract checks passed with overlapping coverage. Synthetic file-writer tests establish selected invocation and byte retention, not native science or a deployed resource. Standard M332 and R333 field-population/calculator work is still being tested; fresh E336 owns original-attempt, actual-worker and typed-return integration under327/addendum003. Existing API evidence remains unchanged. No tally increment."
    row["evidence_ids"].append(added[1]["id"])
    row["note"] += " Update072: the335 selected-sidecar capture-key defect is fixed in both actual consumers and root reviewed.144 metadata tests passed; logical roles, selected identities, schemas and original histories are preserved. This is compatibility verification, not another tool or a new full episode test."
    changes.append(dict(group="rows", id=row["id"], before=before, after=deepcopy(row)))
for row in status["resource_bindings"]:
    if row["id"] not in {key + "::hpc" for key in standard_ids | native_ids}:
        continue
    before = deepcopy(row)
    if row["id"] in {key + "::hpc" for key in standard_ids}:
        row["invocation_contract"] = "closed_standard_database_hpc_request_and_one_command_producer_synthetically_verified_shared_dispatch_in_progress"
        row["evidence_ids"].append(added[0]["id"])
    row["evidence_ids"].append(added[1]["id"])
    changes.append(dict(group="resource_bindings", id=row["id"], before=before, after=deepcopy(row)))
assert len(changes) == 22
for group in ("rows", "resource_bindings"):
    affected = {c["id"] for c in changes if c["group"] == group}
    assert [r["id"] for r in status[group]] == [r["id"] for r in original[group]]
    assert all(a == b for a, b in zip(original[group], status[group]) if a["id"] not in affected)
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = dict(schema="tool_grader_progress_update_v1", date="2026-10-26", author="root",
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=added,
    numerical_grader_progress_tally=dict(before=103, after=103, added_row_ids=[],
        meaning=previous["numerical_grader_progress_tally"]["meaning"]),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=205,
    completed_work=[
        "Root accepted the five standard database N producer/tool-information boundary after complete source/test and original receipt review.",
        "335 fixed the two sidecar capture-key comparisons; before/after and original metadata tests verified, root reviewed."],
    unfinished_work=[
        "M332 reports70 final tests passed and its assembly linkage-source validation omission fixed; final supplied-byte preparation and saved-validator source/receipts still await root review.",
        "R333 separate calculations, full numerical rows and worker are under numerical/partial-input/saved-recalculation verification.",
        "Fresh E336 is implementing standard original-attempt acquisition, actual worker integration and typed episode returns against accepted327 plus additive003; not yet verified.",
        "M332 identified a shared303 limitation: multiple FASTA records sharing one original source/pointer lack a distinct original-record identity in the current sequence provenance contract. Preserve the counterexample; do not invent aliases to bypass it.",
        "Both VDB candidate-function calculations remain unimplemented; other numerical components and declared synthetic episode paths stay verified.",
        "Authentic native-mode input coverage and actual HPC deployment/execution remain separately unfinished.",
        "Nine broader regression failures remain: eight retired categorical-scorer calls and one BV-BRC operation declaration mismatch.",
        "All other fixed308 rows and resource bindings remain in scope. SeparateW05 and literature grading are not included in this tool-grader work."],
    active_contract=descriptor(PLAN / "CONTRACT_ADDENDUM_003.md"),
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status["complete_scientific_tools_claimed"])
assert sha(HERE / "SCOPE.json") == scope_sha and sha(STATUS) == before_sha
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.072.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=11, updated_resource_bindings=11, scope_rows=308,
    numerical_grader_progress_tally=103, remaining_fixed_rows_outside_tally=205,
    new_status_sha256=sha(STATUS))))
