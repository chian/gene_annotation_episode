"""Record accepted FASTA/lifecycle components and corrected VDB input work."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_076.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = read(HERE / "PROGRESS_UPDATE_075.json")
before_sha, scope_sha = sha(STATUS), sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 108
assert status["verified_bound_local_tool_mode_rows"] == 40
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]

specs = [
    ("BLAST-FASTA-PUBLIC-ASSOCIATIONS-076", "tool_graders_blast_fasta_record_public_associations_2026-10-26_339",
     ["ROOT_REVIEW_001.md", "HANDOFF_EVIDENCE_001.json", "check007/receipt.json", "check007/stdout.txt", "check008/receipt.json"],
     "Public original-record identity and sequence/metadata associations accepted;927 compatibility checks and saved numerical replay. No formula change or full worker-return claim."),
    ("BLAST-FASTA-METADATA-076", "tool_graders_blast_fasta_record_metadata_2026-10-26_340",
     ["ROOT_REVIEW_001.md", "HANDOFF_001.md", "check003/receipt.json", "check003/stdout.txt", "check004/receipt.json"],
     "Native and standard metadata v2 source/proof/record relationships accepted;649 checks and saved replay.343 worker/return review remains separate."),
    ("BLAST-NATIVE-LIFECYCLE-076", "tool_graders_native_blast_lifecycle_failures_2026-10-26_341",
     ["ROOT_REVIEW_001.md", "EVIDENCE_INDEX_001.json", "VERIFICATION_001.md",
      "contract_check_20261026T223543602934Z/receipt.json", "success_return_check_20261026T223714614770Z/receipt.json"],
     "Typed lifecycle failures retain diagnostics/partial sealed results and distinguish resource-limit from ordinary worker failure;9 failure-path checks plus1 successful return, with earlier overlap not added."),
    ("BLAST-VDB-FUNCTION-INPUTS-076", "tool_graders_blast_vdb_function_inputs_2026-10-26_342",
     ["ROOT_REVIEW_001.md", "HANDOFF_001.md", "ARTIFACT_HASHES_001.txt", "run_007/receipt.json", "run_007/stdout.txt"],
     "Full VDB FunctionSheet and per-HSP qualification accepted with346 saved membership/sample correction;81 original checks plus16 new checks pass. Candidate-function calculator and actual new episode delivery remain unfinished."),
]
evidence = []
for identity, packet, names, summary in specs:
    paths = [ROOT / "verification" / packet / name for name in names]
    if identity == "BLAST-VDB-FUNCTION-INPUTS-076":
        extra = ROOT / "verification/tool_graders_blast_vdb_saved_relations_2026-10-26_346"
        paths += [extra / name for name in ("VERIFICATION_001.md", "EVIDENCE_INDEX_001.json", "ROOT_DIFF_001.patch",
            "probe_result_001.json", "probe_run_001/receipt.json", "run_001/receipt.json", "run_001/stdout.txt")]
    item = dict(id=identity, kind="reviewed_component", summary=summary,
        reports=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p)) for p in paths],
        qualification="Synthetic/supplied and retained-format verification through the stated component paths; no new native database execution, live deployment or full scientific-tool completion.")
    assert not any(r["id"] == identity for r in status["verification_evidence"])
    status["verification_evidence"].append(item)
    evidence.append(item)

repair = ROOT / "verification/tool_graders_blast_vdb_saved_relations_2026-10-26_346"
receipt = read(repair / "run_001/receipt.json")
assert receipt["returncode"] == 0
assert receipt["metadata"]["policy"] == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
assert "97 passed" in (repair / "run_001/stdout.txt").read_text()
assert sha(ROOT / "gene_annotation_episode/blast_vdb_function_inputs.py") == "8c6b6ad052aecb3410c97d93a2ad2b690c9d232b5e9089f2c8dae6cf369a1dab"
assert read(repair / "run_001/source_before.json") == read(repair / "run_001/source_after.json")
for item in read(repair / "EVIDENCE_INDEX_001.json"):
    p = ROOT / item["path"]
    assert sha(p) == item["sha256"] and p.stat().st_size == item["size_bytes"]

standard = {"A-L069-" + p + "-database" for p in ("blastn", "blastp", "blastx", "tblastn", "tblastx")}
native = {"A-L070-" + p + "-database" for p in ("psiblast", "deltablast", "rpsblast", "rpstblastn", "blastn_vdb", "tblastn_vdb")}
sequence = standard | {"A-L070-psiblast-database", "A-L070-deltablast-database"}
vdb = {"A-L070-blastn_vdb-database", "A-L070-tblastn_vdb-database"}
changes = []
for group in ("rows", "resource_bindings"):
    for row in status[group]:
        key = row["id"]
        tool = key.removesuffix("::hpc") if group == "resource_bindings" else key
        if tool not in standard | native or group == "resource_bindings" and key != tool + "::hpc":
            continue
        before = deepcopy(row)
        if tool in sequence:
            row["evidence_ids"].extend([evidence[0]["id"], evidence[1]["id"]])
            if group == "rows":
                row["metadata_extractor"] = "original_fasta_record_v2_public_and_metadata_proofs_verified_worker_and_parent_return_review_pending"
                row["note"] += " Update076:339 public associations and340 metadata accepted after complete root review, actual927/649 test receipts and saved replay. Original record ordinals survive without aliases; full-sequence grouping and formulas stay unchanged.343 worker/quality/typed-return handoff is delivered but root review remains pending. No count change."
        if tool in native:
            row["evidence_ids"].append(evidence[2]["id"])
            if group == "rows":
                row["note"] += " Update076:341 lifecycle correction accepted: real typed resource-limit versus ordinary worker failures, preserved diagnostics and valid partial sealed results. Ten distinct focused cases; no new native database/live-resource test or grader increment."
        if tool in vdb:
            row["evidence_ids"].append(evidence[3]["id"])
            if group == "rows":
                row["overall"] = "partial_vdb_function_inputs_verified_calculator_and_versioned_episode_integration_in_progress"
                row["numerical_sheet"] += "_additive_function_sheet_per_hsp_qualification_census_and_saved_relationships_verified"
                row["deterministic_calculator"] = "v1_geometry_codons_membership_taxonomy_quality_population_verified_new_function_calculator_in_verification"
                row["numerical_verification"] += "_342_81_original_and346_16_saved_relation_checks_passed_97_combined"
                row["note"] += " Update076:342 input component accepted with root346 repair. A reproduced saved-sample relabeling defect is rejected using original membership/sample relationships;97 checks pass and frozen fixtures remain unchanged.344 formula verification and345 wire completion continue; fresh347 owns the new versioned worker, exact received saved-input authority and typed-return integration. Both VDB rows remain uncounted; no live-format/deployment claim."
        changes.append(dict(group=group, id=key, before=before, after=deepcopy(row)))
assert len(changes) == 22
for group in ("rows", "resource_bindings"):
    affected = {c["id"] for c in changes if c["group"] == group}
    assert [r["id"] for r in status[group]] == [r["id"] for r in original[group]]
    assert all(a == b for a, b in zip(original[group], status[group]) if a["id"] not in affected)
assert status["complete_scientific_tools_claimed"] == original["complete_scientific_tools_claimed"]

details = [
    ("in_progress", "Original-record representation and metadata components339/340 accepted;343 actual-worker/typed-return review is pending."),
    ("in_progress", "342 input sheet accepted with346 repair;344 calculation,345 metadata and347 episode integration remain unfinished. Neither VDB row counted."),
    ("open", previous["unfinished_work"][2]),
    ("open", previous["unfinished_work"][3]),
    ("open", previous["unfinished_work"][4]),
    ("open", previous["unfinished_work"][5]),
    ("complete", "338 complete accepted contract now includes explicit source/validation/population/schema handoffs; implementation assigned against it."),
    ("in_progress", "339/340 accepted;343 delivered314 tests plus56 producer checks and32 repeated integration checks against345 helper dependency; root review pending."),
    ("complete", "341 lifecycle correction accepted with exact original typed failures and retained partial work; no scientific formula/count change."),
]
checklist = [dict(id=f"U{i+1:02d}", original_item=text, status=state, current_evidence=detail)
             for i, (text, (state, detail)) in enumerate(zip(previous["unfinished_work"], details))]
assert len(checklist) == len(previous["unfinished_work"]) == 9
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = dict(schema="tool_grader_progress_update_v1", date="2026-10-26", author="root",
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=evidence,
    numerical_grader_progress_tally=dict(before=108, after=108, added_row_ids=[], meaning=previous["numerical_grader_progress_tally"]["meaning"]),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=200,
    completed_work=[e["summary"] for e in evidence],
    work_item_states=checklist,
    unfinished_work=[i["current_evidence"] for i in checklist if i["status"] != "complete"],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status["complete_scientific_tools_claimed"])
assert sha(STATUS) == before_sha and sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False); stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.076.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=11, updated_resource_bindings=11, scope_rows=308,
    numerical_grader_progress_tally=108, remaining_fixed_rows_outside_tally=200,
    new_status_sha256=sha(STATUS))))
