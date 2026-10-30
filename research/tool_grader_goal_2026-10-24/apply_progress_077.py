"""Accept FASTA result integration and preserve the additional VDB repair."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_077.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = read(HERE / "PROGRESS_UPDATE_076.json")
before_sha, scope_sha = sha(STATUS), sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 108
assert status["verified_bound_local_tool_mode_rows"] == 40
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]

fasta = ROOT / "verification/tool_graders_blast_fasta_record_integration_2026-10-26_343"
repair = ROOT / "verification/tool_graders_blast_vdb_saved_relations_2026-10-26_346"
for item in read(fasta / "EVIDENCE_INDEX_001.json")["evidence"]:
    p = ROOT / item["path"]
    assert sha(p) == item["sha256"] and p.stat().st_size == item["size_bytes"]
for name, digest in read(fasta / "EVIDENCE_INDEX_001.json")["source_hashes"].items():
    assert sha(fasta / "final_sources" / name) == digest
for item in read(repair / "EVIDENCE_INDEX_002.json"):
    p = ROOT / item["path"]
    assert sha(p) == item["sha256"] and p.stat().st_size == item["size_bytes"]
for packet, run, count in [(fasta, "check012", 314), (fasta, "check013", 56),
                           (fasta, "check015", 32), (repair, "run_002", 103)]:
    receipt = read(packet / run / "receipt.json")
    assert receipt["returncode"] == 0
    assert receipt["metadata"]["policy"] == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
    assert f"{count} passed" in (packet / run / "stdout.txt").read_text()
request = read(repair / "run_002/request.json")
assert request["source_before"] == request["source_after"]
assert sha(ROOT / "gene_annotation_episode/blast_vdb_function_inputs.py") == "78e0491b2d52cfed4bc013b04f2f3487fb86a65691dd3b10a4c97541f6d71b84"

specs = [
    ("BLAST-FASTA-WORKER-RETURN-077", fasta,
     ["ROOT_REVIEW_001.md", "ROOT_INSPECTION_001.json", "EVIDENCE_INDEX_001.json", "ROOT_DIFF_001.patch",
      "check012/receipt.json", "check012/stdout.txt", "check013/receipt.json", "check013/stdout.txt",
      "check015/receipt.json", "check015/stdout.txt"],
     "343 FASTA ordinal, worker, saved recalculation and requested typed-return integration accepted;314 checks plus56 producer checks and32 overlapping repeated integration checks. Four actual received forms retain0.9/0.6 separately. Synthetic emitters/fake PBS, no live deployment."),
    ("BLAST-VDB-SAVED-ASSIGNMENT-RELATIONS-077", repair,
     ["VERIFICATION_002.md", "EVIDENCE_INDEX_002.json", "ROOT_DIFF_002.patch", "probe_run_002/receipt.json",
      "probe_run_002/stdout.txt", "run_002/receipt.json", "run_002/request.json", "run_002/stdout.txt"],
     "346 repaired global-key versus entity-specific saved validation after two reproduced failures.103 checks pass; incompatible assignments stay explicit and independent valid observations remain unchanged. Neither VDB tool counted."),
]
evidence = []
for identity, packet, names, summary in specs:
    paths = [packet / name for name in names]
    item = dict(id=identity, kind="reviewed_component", summary=summary,
        reports=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p)) for p in paths],
        qualification="Verified at the stated synthetic/supplied-data paths; live native database execution and resource deployment are separately unfinished.")
    assert not any(r["id"] == identity for r in status["verification_evidence"])
    status["verification_evidence"].append(item)
    evidence.append(item)

sequence = {"A-L069-" + p + "-database" for p in ("blastn", "blastp", "blastx", "tblastn", "tblastx")}
sequence |= {"A-L070-psiblast-database", "A-L070-deltablast-database"}
vdb = {"A-L070-blastn_vdb-database", "A-L070-tblastn_vdb-database"}
changes = []
for group in ("rows", "resource_bindings"):
    for row in status[group]:
        key = row["id"]
        tool = key.removesuffix("::hpc") if group == "resource_bindings" else key
        if tool not in sequence | vdb or group == "resource_bindings" and key != tool + "::hpc":
            continue
        before = deepcopy(row)
        entry = evidence[0] if tool in sequence else evidence[1]
        row["evidence_ids"].append(entry["id"])
        if group == "rows" and tool in sequence:
            row["metadata_extractor"] = "original_fasta_record_v2_public_metadata_worker_saved_recalculation_and_requested_parent_return_verified"
            row["note"] += " Update077:343 scoped source/tests and actual receipts reviewed;230 artifacts and14 frozen source identities independently match. Distinct FASTA ordinals survive source-only quality rows and four actual typed parent returns with0.9/0.6.314 checks plus56 producer checks;32 repeated integration checks against345 helper are overlapping. Old values/forms and341 failure handlers unchanged.347 owns later shared-file edits and must preserve this regression. No count increase or live-resource claim."
        if group == "rows" and tool in vdb:
            row["numerical_verification"] += "_346_cross_entity_assignment_conflict_repair_103_combined_checks"
            row["note"] += " Update077:346 reproduced and repaired cross-entity duplicate assignment-key validation. Complete conflicting declarations remain incompatible; exact key plus entity address permits their retained observations and preserves independent valid features.103 original/saved checks pass, including6 new cases.344 calculator delivered for review,345 metadata completion/review and347 integrated versioned results remain separate. Both VDB rows stay outside108."
        changes.append(dict(group=group, id=key, before=before, after=deepcopy(row)))
assert len(changes) == 18
for group in ("rows", "resource_bindings"):
    affected = {c["id"] for c in changes if c["group"] == group}
    assert [r["id"] for r in status[group]] == [r["id"] for r in original[group]]
    assert all(a == b for a, b in zip(original[group], status[group]) if a["id"] not in affected)
assert status["complete_scientific_tools_claimed"] == original["complete_scientific_tools_claimed"]

checklist = deepcopy(previous["work_item_states"])
by_id = {item["id"]: item for item in checklist}
by_id["U01"].update(status="complete", current_evidence="339/340 original-record representation and metadata plus343 actual worker, saved recalculation and requested typed-return integration accepted. Original FASTA ordinals remain distinct.")
by_id["U02"].update(status="in_progress", current_evidence="342 input component plus346 sample and cross-entity assignment repairs verified;103 input/saved checks pass.344 calculator delivered for review;345 metadata review and347 episode integration remain unfinished. Neither VDB row counted.")
by_id["U08"].update(status="complete", current_evidence="343 accepted after source/test/receipt review and230 artifact plus14 frozen-source identity checks;314 tests plus56 producer checks, with32 overlapping repeated integration checks. Four actual typed returns retain distinct record-quality values0.9/0.6.")
assert [(i["id"], i["original_item"]) for i in checklist] == [(i["id"], i["original_item"]) for i in previous["work_item_states"]]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = dict(schema="tool_grader_progress_update_v1", date="2026-10-26", author="root",
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=evidence,
    numerical_grader_progress_tally=dict(before=108, after=108, added_row_ids=[], meaning=previous["numerical_grader_progress_tally"]["meaning"]),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=200,
    completed_work=[e["summary"] for e in evidence], work_item_states=checklist,
    unfinished_work=[i["current_evidence"] for i in checklist if i["status"] != "complete"],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status["complete_scientific_tools_claimed"])
assert sha(STATUS) == before_sha and sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False); stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.077.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=9, updated_resource_bindings=9, scope_rows=308,
    numerical_grader_progress_tally=108, remaining_fixed_rows_outside_tally=200,
    new_status_sha256=sha(STATUS))))
