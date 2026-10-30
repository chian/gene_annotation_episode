"""Record verified HMMER component progress without claiming tool integration."""
raise SystemExit('Historical progress mutation retired; current progress is not reconstructed from old goal attachments or notes.')
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
TRACKER = ROOT / "research/tool_grader_goal_2026-10-24"
STATUS = TRACKER / "WORK_STATUS.json"
EXPECTED_STATUS = "8ffe95d10e767c0dda5e0389e38caf95b83826126284c40fbfadd68fddf470aa"
AUTHORITY = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
AUTHORITY_SHA = "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"
SCOPE_SHA = "2f2d6670e3f89ecb980f87857b44d129751bad26471213b8bada9115960c1719"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(path):
    path = ROOT / path
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}


def verified_receipt(directory, attempt, expected_passed):
    path = ROOT / "verification" / directory / attempt / "receipt.json"
    receipt = json.loads(path.read_text())
    assert receipt["returncode"] == 0
    assert receipt["policy"] == {"memory_bytes": 20 * 1024**3, "scratch_bytes": 4 * 1024**3, "wall_seconds": None}
    stdout = Path(receipt["stdout_path"]).read_text()
    assert re.search(r"\b" + str(expected_passed) + r" passed\b", stdout)
    if "source_hashes_before" in receipt:
        source_hashes = receipt["source_hashes_before"]
        assert receipt["source_hashes_after"] == source_hashes
    else:
        source_hashes = receipt["source_sha256"]
    assert source_hashes, "missing_source_hash_evidence"
    for source, digest in source_hashes.items():
        assert sha(ROOT / source) == digest, source
    if "source_sha256_after" in receipt:
        assert receipt["source_sha256_after"] == receipt["source_sha256"]
    return {"directory": str(path.parent.relative_to(ROOT)), "passed": expected_passed, "failed": 0,
        "receipt": report(path), "checked_source_hash_count": len(source_hashes),
        "scope": "pure numerical component using retained native data; production episode integration pending"}


def main():
    output = TRACKER / "PROGRESS_UPDATE_055.json"
    assert not output.exists(), "immutable_update_already_exists"
    assert sha(STATUS) == EXPECTED_STATUS, "status_changed_reconcile_before_mutation"
    assert sha(AUTHORITY) == AUTHORITY_SHA
    assert sha(TRACKER / "SCOPE.json") == SCOPE_SHA
    original = json.loads(STATUS.read_text())
    updated = deepcopy(original)
    assert len(original["rows"]) == 308 and len(original["resource_bindings"]) == 288
    specifications = [
        ("HMMER-MODEL-DATA-055", "tool_graders_hmmer_model_data_2026-10-26_262", "check004", 85),
        ("HMMER-SIMULATION-DATA-055", "tool_graders_hmmer_simulation_data_2026-10-26_263", "check006", 97),
        ("HMMER-STATISTICS-DATA-055", "tool_graders_hmmer_statistics_2026-10-26_265", "check001", 34),
        ("HMMER-EMISSION-DATA-055", "tool_graders_hmmer_emission_data_2026-10-26_266", "check005", 75),
    ]
    verification = []
    evidence = []
    for identity, directory, attempt, count in specifications:
        checked = verified_receipt(directory, attempt, count)
        verification.append(checked)
        evidence.append({"id": identity, "kind": "pure_numerical_component_verified_integration_pending",
            "summary": f"{directory}: {count} passing numerical/native-format/partial/recalculation tests.",
            "qualification": "Retained native data and exact component source checkpoint; no production execution/library/typed episode return claim.",
            "reports": [report(f"verification/{directory}/README.md"), checked["receipt"]]})
    native_id = "HMMER-PREPARATION-NATIVE-055"
    evidence.append({"id": native_id, "kind": "native_format_and_invocation_evidence",
        "summary": "Ten actual HMMER preparation programs; 90 retained native invocations including10help and80tiny cases.",
        "qualification": "259 native examples establish actual formats and invocations, not new producer/capture/episode integration.",
        "reports": [report("verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/REPORT.md"),
                    report("verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/EVIDENCE_MANIFEST.json")]})
    tool_evidence = {"hmmsim": "HMMER-SIMULATION-DATA-055", "hmmstat": "HMMER-STATISTICS-DATA-055",
                     "hmmemit": "HMMER-EMISSION-DATA-055"}
    changes = []
    for row in updated["rows"]:
        if not row["id"].startswith("A-L076-"):
            continue
        before = deepcopy(row)
        program = row["id"].removeprefix("A-L076-")
        row.update(overall="native_formats_observed_preparation_implementation_in_progress",
            source_presence="native_source_and_executable_inspected",
            invocation_contract="native_examples_observed_production_binding_pending",
            live_resource_verification="retained_tiny_native_local_examples_not_new_production_path")
        row["evidence_ids"].append(native_id)
        row["note"] += " Update055: actual native formats/options/examples were inspected; production preparation binding and complete episode returns remain pending."
        if program in tool_evidence:
            row.update(overall="numerical_components_verified_production_integration_pending",
                numerical_sheet="implemented_full_native_numerical_sheet_verified",
                native_parser="retained_native_formats_and_partial_states_verified",
                metadata_extractor="explicit_occurrence_and_model_associations_verified",
                deterministic_calculator="independent_values_and_saved_sheet_recalculation_verified",
                numerical_verification="pure_component_native_and_synthetic_cases_passed",
                production_result_binding="not_yet_bound_to_preparation_results",
                integration_verification="pure_M1_consumer_verified_episode_path_pending")
            row["evidence_ids"] += ["HMMER-MODEL-DATA-055", tool_evidence[program]]
            row["note"] += " The implemented sheet/calculator consumes actual M1 model data. Full child-owned execution/capture/projection and typed returns are not established; HMMER2/binary decoder limitations remain explicit."
        changes.append({"group": "rows", "id": row["id"], "before": before, "after": deepcopy(row)})
    assert len(changes) == 10
    updated["verification_evidence"].extend(evidence)
    assert [r["id"] for r in updated["rows"]] == [r["id"] for r in original["rows"]]
    assert updated["resource_bindings"] == original["resource_bindings"]
    for key in ("verified_bound_local_tool_mode_rows", "complete_scientific_tools_claimed"):
        assert updated[key] == original[key]
    serialized = (json.dumps(updated, indent=2, ensure_ascii=False) + "\n").encode()
    update = {"schema": "tool_grader_progress_update_v1", "date": "2026-10-26",
        "recorded_at": datetime.now(timezone.utc).isoformat(), "author": "root",
        "previous_status_sha256": EXPECTED_STATUS, "new_status_sha256": hashlib.sha256(serialized).hexdigest(),
        "scope_sha256_unchanged": SCOPE_SHA, "scope_changes": [], "changes": changes,
        "added_evidence": evidence, "verification": verification, "count_change": {},
        "numerical_grader_progress_tally": {"before": 79, "after": 79, "added_row_ids": [],
            "meaning": "Carried-forward tally unchanged; new HMMER pure components have explicit pending production integration."},
        "remaining_fixed_rows_outside_tally": 229,
        "completed_work": ["Shared full HMMER3 model data/calculations and hmmsim,hmmemit,hmmstat numerical sheets/calculators verified against retained native outputs.",
            "Actual complete HMMER preparation native contracts and ten-tool mode/format evidence retained.",
            "Exact nonoverlapping producer,FM,artifact and alignment-workload contracts fixed before fresh coding assignments."],
        "unfinished_work": ["HMMER production execution,capture,tool information,result projection and typed episode-return wiring.",
            "FM structural validation, model artifact operations and model build/mask sheets; current coding ownership is recorded in261contracts.",
            "HMMER2/native binary body/index decoders and exact unsupported native mode/format subcases.",
            "Remaining fixed308-row goal, general TASK/STEERING/resource instructions and previous qualified integration/resource gaps.",
            "Eight obsolete shared receipt expectations remain unresolved as recorded in054."],
        "excluded_claims": ["Production HMMER preparation episode integration", "HPC deployment", "W05 or annotation scoring changes",
            "Literature grader implementation", "Whole-checkout frozen verification", "Full308-goal completion"],
        "inventory_maintenance_counted_as_implementation_progress": False,
        "specific_pending_NCBI_job_verification_included": False,
        "complete_scientific_tools_claimed": updated["complete_scientific_tools_claimed"],
        "closure_reset": {"original_goal": str(AUTHORITY), "sha256": AUTHORITY_SHA,
            "objective_and_all16_read_verbatim": True, "root_contract": report("verification/tool_graders_hmmer_preparation_2026-10-26_261/STATISTICS_CONTRACT_001.md")}}
    # Save the immutable change record before replacing the sole mutable progress table.
    with output.open("x") as stream:
        json.dump(update, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    temporary = STATUS.with_name(".WORK_STATUS.update055.tmp")
    with temporary.open("xb") as stream:
        stream.write(serialized)
    temporary.replace(STATUS)
    assert sha(STATUS) == update["new_status_sha256"]
    print(json.dumps({"update": str(output.relative_to(ROOT)), "rows": len(updated["rows"]),
        "resource_bindings": len(updated["resource_bindings"]), "tally": 79, "pending": 229,
        "components": [item["passed"] for item in verification], "status_sha256": sha(STATUS)}))


if __name__ == "__main__":
    main()
