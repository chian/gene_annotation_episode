"""Record the reviewed producer; do not count it as six complete graders."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_066.json"
PACKET = "verification/tool_graders_native_blast_database_producer_2026-10-26_313/"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(relative):
    return {"path": relative, "sha256": sha(ROOT / relative)}


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = json.loads((HERE / "PROGRESS_UPDATE_065.json").read_text())
before_sha = sha(STATUS)
assert before_sha == previous["new_status_sha256"]
scope_sha = sha(HERE / "SCOPE.json")
assert scope_sha == previous["scope_sha256_unchanged"]
status = json.loads(STATUS.read_text())
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 99
assert status["verified_bound_local_tool_mode_rows"] == 40
authority = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert sha(authority) == status["authority_sha256"]
expected_sources = {
    "gene_annotation_episode/native_blast_database_contracts.py": "a2a8256445a5a25a98cd7f0771d7d554a7fc19153d509187177acf2deea8ee0b",
    "gene_annotation_episode/native_blast_database_driver.py": "e62bb6f6def146d35a1b649018283c5ff5677101d1b9c98ed8c0928386013502",
    "gene_annotation_episode/native_blast_database_tool_info.py": "7db9f17d12f857ee6f154f150cdd4a33332c70deb2a57c3eb2003ea64370fd3c",
}
for path, expected in expected_sources.items():
    assert sha(ROOT / path) == expected, path
policy = {"memory_bytes": 20 * 1024**3, "scratch_bytes": 4 * 1024**3, "wall_seconds": None}
for check, oracle in (("check005", "149 passed"), ("check006", "1 passed"),
                      ("check_008", "7 passed"), ("examples002", '"examples": 15')):
    directory = ROOT / PACKET / check
    receipt = json.loads((directory / "receipt.json").read_text())
    assert receipt["returncode"] == 0 and receipt["policy"] == policy
    assert oracle in (directory / "stdout.txt").read_text()
examples_root = ROOT / PACKET / "examples002"
examples = json.loads((examples_root / "examples.json").read_text())
assert len(examples) == 15 and sum(e["invocations"] for e in examples) == 13
artifact_count = byte_count = 0
for example in examples:
    bundle_path = examples_root / example["bundle_path"]
    bundle = json.loads(bundle_path.read_text())
    assert len(bundle["artifacts"]) == example["retained_artifact_count"]
    for artifact in bundle["artifacts"]:
        path = bundle_path.parent / artifact["relative_path"]
        assert sha(path) == artifact["sha256"] and path.stat().st_size == artifact["size_bytes"]
        artifact_count += 1
        byte_count += artifact["size_bytes"]
    # Retained actual deployed producer copies are identical to reviewed code.
    deployment = examples_root / example["example"] / "deployment"
    for source in list(expected_sources)[:2]:
        assert sha(deployment / source) == expected_sources[source]
assert (artifact_count, byte_count) == (191, 13705770)

evidence = {
    "id": "BLAST-NATIVE-DATABASE-PRODUCER-066",
    "kind": "producer_field_function_and_synthetic_execution_verification",
    "reports": [descriptor(PACKET + p) for p in (
        "CONTRACT_001.md", "CONTRACT_ADDENDUM_002.md", "CONTRACT_ADDENDUM_003.md",
        "CONTRACT_ADDENDUM_004.md", "CONTRACT_ADDENDUM_005.md", "CONTRACT_ADDENDUM_006.md",
        "ROOT_REVIEW_001.md", "check005/receipt.json", "check005/stdout.txt",
        "check006/receipt.json", "check006/stdout.txt", "check_008/receipt.json",
        "check_008/stdout.txt", "examples002/receipt.json", "examples002/examples.json")]
        + [descriptor(p) for p in expected_sources],
    "summary": "Six-program producer fields, validators, compiler, single selected command/capture and tool-info functions reviewed;150 distinct synthetic/pure cases and15 retained examples verified.",
    "qualification": "No actual BLAST database search, configured HPC deployment, shared PBS/episode result binding or authenticated typed return verified. This supporting producer does not complete the six scientific graders.",
}
assert not any(e["id"] == evidence["id"] for e in status["verification_evidence"])
status["verification_evidence"].append(evidence)
modes = ("psiblast", "deltablast", "rpsblast", "rpstblastn", "blastn_vdb", "tblastn_vdb")
changes = []
for mode in modes:
    rid = "A-L070-" + mode + "-database"
    for group, identifier in (("rows", rid), ("resource_bindings", rid + "::hpc")):
        row = next(r for r in status[group] if r["id"] == identifier)
        before = deepcopy(row)
        row["invocation_contract"] = "explicit_selected_native_database_job_compiler_and_producer_synthetic_verified_shared_hpc_binding_pending"
        if group == "rows":
            row["tool_information"] = "four_field_hpc_tool_info_and_library_freeze_resolve_verified_runtime_resource_registration_pending"
            row["note"] += " Update066: selected native database producer fields/functions and six HPC descriptors verified with150 distinct cases and15 synthetic examples. Missing metadata associations, PBS directory reuse and unselected PSSM-parser fallback fixed. Shared PBS/result/episode integration and actual HPC execution remain unfinished; no grader tally increment."
        else:
            row.update(
                prerequisites_present="actual_hpc_software_databases_runtime_and_authentication_not_verified",
                native_format_observed="synthetic_producer_outputs_only_actual_native_database_output_pending",
                production_result_binding="shared_pbs_episode_and_numerical_result_path_not_implemented",
                integration_verification="single_simulated_command_capture_replay_verified_full_episode_path_pending",
                live_resource_verification="no_actual_hpc_database_search_executed",
            )
        row["evidence_ids"].append(evidence["id"])
        changes.append({"group": group, "id": identifier, "before": before, "after": deepcopy(row)})
for group in ("rows", "resource_bindings"):
    affected = {c["id"] for c in changes if c["group"] == group}
    assert [r["id"] for r in status[group]] == [r["id"] for r in original[group]]
    assert all(a == b for a, b in zip(original[group], status[group]) if a["id"] not in affected)
assert sha(HERE / "SCOPE.json") == scope_sha
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {
    "schema": "tool_grader_progress_update_v1", "date": "2026-10-26",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "author": "root",
    "previous_status_sha256": before_sha, "new_status_sha256": hashlib.sha256(raw).hexdigest(),
    "scope_sha256_unchanged": scope_sha, "scope_changes": [], "changes": changes,
    "added_evidence": [evidence],
    "verification": [{"packet": PACKET, "distinct_passing_cases": 150,
        "focused_tool_info_rechecks": 7, "synthetic_examples": 15,
        "verified_retained_artifacts": artifact_count, "verified_retained_bytes": byte_count,
        "native_mode_search_executed": False, "episode_path_verified": False}],
    "numerical_grader_progress_tally": {"before": 99, "after": 99, "added_row_ids": [],
        "meaning": "Producer and invocation work is a required supporting component, not six complete numerical graders."},
    "verified_bound_local_tool_mode_rows": {"before": 40, "after": 40},
    "remaining_fixed_rows_outside_tally": 209,
    "completed_work": [
        "Six-program native database producer field definitions and validation/compilation/capture/tool-info functions implemented and reviewed.",
        "150 distinct cases and15 synthetic examples verified;191 retained artifacts match their recorded lengths and hashes.",
        "Original metadata association, prepared PBS directory and unselected parser import defects corrected."
    ],
    "unfinished_work": [
        "Native database result/metadata/projection contract314 is being finalized before fresh parallel integration coding.",
        "Native convergence parser316 is in implementation; genuine marker fixtures and collector integration remain pending.",
        "Shared PBS selected execution, native artifact acquisition, numerical worker and authenticated typed episode returns remain unfinished.",
        "Actual native searches, configured HPC deployment, required metadata acquisition and remaining numerical-model work remain unverified or unfinished.",
        "All other fixed308-row work remains as recorded; literature graders and W05 are outside this goal."
    ],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"],
}
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.066.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_tool_rows": 6, "updated_resource_rows": 6,
    "scope_rows": 308, "resource_bindings": 288, "numerical_grader_progress_tally": 99,
    "new_status_sha256": sha(STATUS)}))
