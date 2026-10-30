"""Record verified protein components; retain the fixed incomplete tool row."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_095.json"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / "PROGRESS_UPDATE_094.json")
before_sha, scope_sha = sha(STATUS), sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 112
assert status["verified_bound_local_tool_mode_rows"] == 42
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]
policy = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
reports = []
for suffix, check, code, summary, pin_key in (
    ("returns_2026-10-27_397", "check008", 0, "73 passed", "executed_snapshot_pins_unchanged"),
    ("publication_2026-10-27_400", "check002", 0, "78 passed", "executed_source_pins_unchanged"),
    ("preflight_2026-10-27_401", "check005", 1, "1 failed, 117 passed", "executed_snapshot_pins_unchanged"),
    ("preflight_2026-10-27_401", "check010", 1, "1 failed, 11 passed", "executed_snapshot_pins_unchanged"),
    ("source_boundaries_2026-10-27_402", "check001", 0, "26 passed", "executed_source_pins_unchanged"),
    ("projection_publication_2026-10-27_404", "check002", 0, "30 passed", "executed_source_pins_unchanged"),
):
    packet = ROOT / ("verification/tool_graders_protein_structure_" + suffix)
    directory = packet / check
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == code and receipt[pin_key] is True
    assert receipt["metadata"]["policy"] == policy
    assert summary in (directory / "stdout.txt").read_text()
    reports += [directory / "receipt.json", directory / "stdout.txt"]
    reports += [path for path in packet.iterdir() if path.is_file() and path.suffix in (".md", ".json")]
contracts = ROOT / "verification/tool_graders_protein_structure_shared_contract_2026-10-27_380"
reports += [contracts / name for name in (
    "PROJECTION_PUBLICATION_CONTRACT_017.md", "LOCAL_RESOURCE_INTEGRATION_CONTRACT_018.md",
    "RESOURCE_HANDOFF_NAME_CORRECTION_019.md")]

summary = ("Protein returns397 passed73 with injected host ports; ordinary Store publication400 passed78; "
    "preflight401 passed all79 new cases plus38 mother cases before an existing commission fixture failed, "
    "and11 actual ordinary alignment child cases before a separate legacy timing fixture exhausted its script. "
    "Source guards402 passed26; selected projection publication404 passed30 including real Store and typed forms. "
    "These are component results; no complete protein tool is claimed and112/308 remains unchanged.")
qualification = ("397 uses a narrow test host, not the missing production result host.400 and404 use actual "
    "retained synthetic native-format fixtures;404 custody is synthetic.401 has actual ordinary alignment "
    "regressions but injected protected-authority ports. Its common-snapshot check005 is NOT an all-green "
    "run:117 passes and one existing commission-fixture failure, reproduced with all three preflight "
    "files restored to their pre-edit versions. A retired CreditPolicy fixture also fails unchanged in "
    "a retained pre-edit comparison. check010 has11 passes then a legacy root-alignment timing fixture "
    "StopIteration; that failure is retained and not fixed or counted as a pass.402 proves only three "
    "source-version exclusions, not the earlier resolver's complete received authority.")
item = {"id": "PROTEIN-RETURNS-PUBLICATION-PREFLIGHT-GUARDS-095",
    "kind": "component_verification_with_full_episode_path_unfinished", "summary": summary,
    "qualification": qualification,
    "reports": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path)} for path in sorted(set(reports))],
    "source_pins": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path)} for path in (
        ROOT / "gene_annotation_episode/native_protein_structure_returns.py",
        ROOT / "gene_annotation_episode/protein_structure_publication.py",
        ROOT / "gene_annotation_episode/protein_structure_projection_publication.py",
        ROOT / "gene_annotation_episode/episode_services.py",
        ROOT / "gene_annotation_episode/episode_bindings.py",
        ROOT / "gene_annotation_episode/scientific_process_episodes.py",
        ROOT / "gene_annotation_episode/episode_receipts.py",
        ROOT / "gene_annotation_episode/execution_episodes.py")],
    "snapshot_note": "Every cited executed snapshot remained unchanged. Live checkout differences are "
        "preserved in each receipt. These suites share dependencies; pass counts are not summed into a global test tally."}
assert item["id"] not in {entry["id"] for entry in status["verification_evidence"]}
status["verification_evidence"].append(item)
protein_id = "B-L107-compare_protein_structures"
changes, binding_changes = [], []
for row in status["rows"]:
    if row["id"] != protein_id:
        continue
    before = deepcopy(row)
    row.update(overall="returns_publication_preflight_components_tested_production_host_unfinished",
        source_presence="native_components_returns_publication_and_preflight_present_host_integration_unfinished",
        production_result_binding="source_and_projection_publication_tested_original_result_host_unfinished",
        integration_verification="component_and_shared_boundary_only_no_complete_receiving_episode_proof")
    row["evidence_ids"].append(item["id"])
    row["note"] += (" Update095:397 returns73,400 Store publication78,401 new preflight79 and selected "
        "ordinary regressions,402 source guards26 and404 selected projection publication30 verified with "
        "the limitations in the evidence record.403 is defining the production result receipt/host contract; "
        "405 is implementing existing local resource operations. Full host, resource registry, authority, "
        "selected return, completion and message integration remain unfinished. No tool or binding count added.")
    changes.append({"id": row["id"], "before": before, "after": deepcopy(row)})
for row in status["resource_bindings"]:
    if row["id"] != protein_id + "::local":
        continue
    before = deepcopy(row)
    row.update(production_result_binding="retained_publication_and_return_components_tested_host_and_resource_path_unfinished",
        integration_verification="component_and_form_only_no_complete_resource_registry_receiving_episode_path")
    row["evidence_ids"].append(item["id"])
    binding_changes.append({"id": row["id"], "before": before, "after": deepcopy(row)})
assert len(changes) == len(binding_changes) == 1
assert all(a == b for a, b in zip(original["rows"], status["rows"]) if a["id"] != protein_id)
assert all(a == b for a, b in zip(original["resource_bindings"], status["resource_bindings"]) if a["id"] != protein_id + "::local")
checklist = deepcopy(previous["work_item_states"])
for entry in checklist:
    if entry["id"] == "U05":
        entry["current_evidence"] += (" Update095 records397/400/401/402/404 components; actual production "
            "host,405 local route, registry, full received use/return and message integration remain open. "
            "401 retained two reproduced pre-existing commission/policy failures and a separate legacy "
            "timing-script failure without claiming those suites passed. Prior eight historical receipt "
            "failures remain unchanged.112/308,42 local bindings and196 outside rows remain. W05/literature separate.")
assert [(x["id"], x["original_item"], x["status"]) for x in checklist] == [
    (x["id"], x["original_item"], x["status"]) for x in previous["work_item_states"]]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {"schema": "tool_grader_progress_update_v1", "date": "2026-10-27", "author": "root",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "previous_status_sha256": before_sha,
    "new_status_sha256": hashlib.sha256(raw).hexdigest(), "scope_sha256_unchanged": scope_sha,
    "scope_changes": [], "changes": changes, "resource_binding_changes": binding_changes,
    "added_evidence": [item], "numerical_grader_progress_tally": {"before": 112, "after": 112,
        "added_row_ids": [], "meaning": previous["numerical_grader_progress_tally"]["meaning"]},
    "verified_bound_local_tool_mode_rows": {"before": 42, "after": 42},
    "remaining_fixed_rows_outside_tally": 196, "completed_work": [summary],
    "findings_requiring_repair": [
        "Production protein result host, resource registration and full received-authority/form/completion path remain unfinished.",
        "403 host contract and405 local resource work are not accepted as completed tool integration.",
        "401's retained historical commission/policy/timing fixture failures are not fixed or counted as passing.",
        "Prior eight historical receipt failures remain under U05; U03 native/HPC and other fixed rows remain."],
    "work_item_states": checklist,
    "unfinished_work": [entry["current_evidence"] for entry in checklist if entry["status"] != "complete"],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"]}
assert sha(STATUS) == before_sha and sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.095.writing")
with temporary.open("xb") as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_tool_rows": 1, "updated_resource_bindings": 1,
    "numerical_grader_progress_tally": 112, "verified_bound_local_tool_mode_rows": 42,
    "remaining_fixed_rows_outside_tally": 196, "new_status_sha256": sha(STATUS)}))
