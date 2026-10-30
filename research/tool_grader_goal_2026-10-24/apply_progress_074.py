"""Record the reviewed standard BLAST calculator and immutable worker boundary."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_074.json"
R = ROOT / "verification/tool_graders_standard_blast_database_results_2026-10-26_333"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = read(HERE / "PROGRESS_UPDATE_073.json")
before_sha = sha(STATUS)
scope_sha = sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 103
assert status["verified_bound_local_tool_mode_rows"] == 40
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]
evidence = read(R / "HANDOFF_EVIDENCE_003.json")
for row in evidence["source_files"]:
    path = ROOT / row["path"]
    assert sha(path) == row["sha256"] and path.stat().st_size == row["size_bytes"]
receipt = read(R / "check007/receipt.json")
assert receipt["returncode"] == 0
assert receipt["metadata"]["policy"] == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
assert "78 passed" in (R / "check007/stdout.txt").read_text()
paths = [R / name for name in ("ROOT_REVIEW_001.md", "INTERFACE_HANDOFF_002.md", "INTERFACE_HANDOFF_003.md",
    "VERIFICATION_002.md", "HANDOFF_EVIDENCE_003.json", "check007/receipt.json", "check007/stdout.txt")]
paths.append(ROOT / "verification/tool_graders_standard_blast_database_plan_2026-10-26_327/CONTRACT_ADDENDUM_004.md")
item = dict(id="BLAST-STANDARD-DATABASE-CALCULATORS-WORKER-074", kind="reviewed_implementation_component",
    reports=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p)) for p in paths],
    summary="All three R modules and tests root reviewed;78 cases passed,249 final evidence file identities checked,30 distinct worker generations retained. Separate calculations, complete rows, bounded projections and saved recalculation verified.",
    qualification="Synthetic standard database inputs and unchanged retained paired-format evidence only. E336 episode integration and live resource verification remain separate unfinished obligations. No new annotation formula or grader tally increment.")
assert not any(r["id"] == item["id"] for r in status["verification_evidence"])
status["verification_evidence"].append(item)
ids = {"A-L069-" + p + "-database" for p in ("blastn", "blastp", "blastx", "tblastn", "tblastx")}
changes = []
for row in status["rows"]:
    if row["id"] not in ids:
        continue
    before = deepcopy(row)
    row["overall"] = "partial_standard_database_producer_metadata_calculators_and_worker_verified_episode_integration_in_progress"
    row["numerical_sheet"] = "standard_sequence_and_actual_input_pssm_fields_population_complete_rows_and_saved_artifacts_verified"
    row["deterministic_calculator"] = "separate_direct_sequence_pssm_calculations_full_axis_pointer_copy_and_saved_recalculation_verified"
    row["numerical_verification"] = "78_R_cases_passed_all_five_modes_pssm_kernel_taxa_quality_geometry_partial_failures_and_recalculation_70_M_cases_retained_separately"
    row["evidence_ids"].append(item["id"])
    row["note"] += " Update074: root accepted R333 after complete source/test review, actual78-pass receipt and independent verification of249 final recorded file identities. The actual-file worker verifies all five modes and tblastn PSSM; saved calculations preserve original inputs and row identities. Known bits20/18 give0.8/0.2 then2/3,1/3 after parameter change; census100/10 gives2/7,5/7. Malformed HSPs preserve measured12/15 lengths while scores/geometry remain unavailable. PSSM calculator exceptions retain valid sequence results with artifact-qualified failure and diagnostics under additive004. The30 retained worker generations are test outputs, not implementation substitutes or tools. E336 complete episode verification is still running; multi-record FASTA provenance and native-path/semantic-census qualification remain unfinished. No count increment or live HPC claim."
    changes.append(dict(group="rows", id=row["id"], before=before, after=deepcopy(row)))
for row in status["resource_bindings"]:
    if row["id"] not in {key + "::hpc" for key in ids}:
        continue
    before = deepcopy(row)
    row["evidence_ids"].append(item["id"])
    changes.append(dict(group="resource_bindings", id=row["id"], before=before, after=deepcopy(row)))
assert len(changes) == 10
for group in ("rows", "resource_bindings"):
    affected = {c["id"] for c in changes if c["group"] == group}
    assert [r["id"] for r in status[group]] == [r["id"] for r in original[group]]
    assert all(a == b for a, b in zip(original[group], status[group]) if a["id"] not in affected)
assert previous["unfinished_work"][0].startswith("R333 separate calculations")
remaining = list(previous["unfinished_work"][1:])
remaining.append("Native database path versus semantic census identity still uses exact equality; a separately scoped explicit association is needed, without rewriting original native fields.")
remaining.append("Fresh338 is defining the exact VDB candidate-function sheet/calculator/integration contract before coding; this planning does not complete either VDB grader.")
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = dict(schema="tool_grader_progress_update_v1", date="2026-10-26", author="root",
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=[item],
    numerical_grader_progress_tally=dict(before=103, after=103, added_row_ids=[],
        meaning="Implemented numerical fields/functions/validation with verified declared episode paths; R component acceptance alone does not complete standard episode integration."),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=205,
    completed_work=["R333 standard BLAST field definitions, separate calculations, rows/projections and immutable worker root reviewed against78 passing tests and retained numerical/failure examples."],
    unfinished_work=remaining, inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status["complete_scientific_tools_claimed"])
assert sha(STATUS) == before_sha and sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.074.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=5, updated_resource_bindings=5, scope_rows=308,
    numerical_grader_progress_tally=103, remaining_fixed_rows_outside_tally=205,
    new_status_sha256=sha(STATUS))))
