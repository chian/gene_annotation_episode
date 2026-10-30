"""Record reviewed contracts and active coding without adding verified tools."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_063.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(relative):
    path = ROOT / relative
    return {"path": relative, "sha256": sha(path)}


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = json.loads((HERE / "PROGRESS_UPDATE_062.json").read_text())
before_sha = sha(STATUS)
assert before_sha == previous["new_status_sha256"]
scope_sha = sha(HERE / "SCOPE.json")
assert scope_sha == previous["scope_sha256_unchanged"]
status = json.loads(STATUS.read_text())
row_ids = [r["id"] for r in status["rows"]]
binding_ids = [r["id"] for r in status["resource_bindings"]]
bindings_before = deepcopy(status["resource_bindings"])
assert len(row_ids) == 308 and len(binding_ids) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 99
assert status["verified_bound_local_tool_mode_rows"] == 40

contracts = [
    "verification/tool_graders_blast_iteration_contract_2026-10-26_308/PROPOSED_CONTRACT_001.md",
    "verification/tool_graders_blast_iteration_2026-10-26_311/CONTRACT_001.md",
    "verification/tool_graders_blast_vdb_contract_2026-10-26_309/PROPOSED_CONTRACT_001.md",
    "verification/tool_graders_blast_vdb_contract_2026-10-26_309/PROPOSED_CONTRACT_ADDENDUM_002.md",
    "verification/tool_graders_blast_vdb_2026-10-26_312/CONTRACT_001.md",
    "verification/tool_graders_blast_vdb_2026-10-26_312/CONTRACT_ADDENDUM_002.md",
]
expected_proposals = {
    contracts[0]: "a89e3c34d3c8c7f4474329cabf5e27268472635a981982b89b636815103a8a1a",
    contracts[2]: "6e19202184bfec7e370d2841382e04650bfa8f7bd32370ce7ba441728659a4d2",
    contracts[3]: "453837ded4338a155ba535552827b18e461ff3662f2120588dd6d8dd7e4ee362",
}
for path, expected in expected_proposals.items():
    assert sha(ROOT / path) == expected, path
evidence = {
    "id": "BLAST-ITERATION-VDB-CONTRACTS-063",
    "kind": "reviewed_implementation_contracts_not_test_verification",
    "reports": [descriptor(path) for path in contracts],
    "summary": "Exact iteration and VDB fields/function interfaces reviewed; fresh coding workloads311/312 started with separate ownership.",
    "qualification": "No new passing tests, native execution, resource binding or complete episode return is established by these contracts.",
}
assert not any(e["id"] == evidence["id"] for e in status["verification_evidence"])
status["verification_evidence"].append(evidence)
changes = []
for mode in ("psiblast", "deltablast", "blastn_vdb", "tblastn_vdb"):
    row = next(r for r in status["rows"] if r["id"] == "A-L070-" + mode + "-database")
    before = deepcopy(row)
    if mode in ("psiblast", "deltablast"):
        assert row["numerical_sheet"].endswith("iteration_contract_pending")
        row["numerical_sheet"] = row["numerical_sheet"].removesuffix("iteration_contract_pending") + "iteration_contract_reviewed_implementation_in_progress"
        row["deterministic_calculator"] = "per_search_components_verified_iteration_composition_implementation_in_progress"
    else:
        row.update(
            overall="contract_reviewed_fields_and_functions_implementation_in_progress",
            numerical_sheet="vdb_hsp_member_feature_population_fields_defined_implementation_in_progress",
            native_parser="three_source_format_parser_contracts_defined_implementation_not_yet_verified",
            metadata_extractor="explicit_parsed_record_binding_contract_defined_implementation_not_yet_verified",
            deterministic_calculator="vdb_component_formulas_defined_implementation_not_yet_verified",
            numerical_verification="no_new_vdb_implementation_tests_reviewed",
            production_result_binding="not_implemented_for_these_new_mode_components",
            integration_verification="new_mode_selected_execution_to_requested_episode_return_not_verified",
            live_resource_verification="no_new_mode_database_execution_no_authentic_mode_fixture_claim",
        )
    row["evidence_ids"].append(evidence["id"])
    row["note"] += " Update063: reviewed exact field/function contracts; fresh coding workload is in progress. No new numerical verification or completion is claimed. Populated examples will verify the implementation."
    changes.append({"group": "rows", "id": row["id"], "before": before, "after": deepcopy(row)})

assert [r["id"] for r in status["rows"]] == row_ids
assert [r["id"] for r in status["resource_bindings"]] == binding_ids
assert status["resource_bindings"] == bindings_before
assert sha(HERE / "SCOPE.json") == scope_sha
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {
    "schema": "tool_grader_progress_update_v1", "date": "2026-10-26",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "author": "root",
    "previous_status_sha256": before_sha,
    "new_status_sha256": hashlib.sha256(raw).hexdigest(),
    "scope_sha256_unchanged": scope_sha, "scope_changes": [],
    "changes": changes, "added_evidence": [evidence], "verification": [],
    "numerical_grader_progress_tally": {"before": 99, "after": 99, "added_row_ids": [],
        "meaning": "Contract review and active coding do not add verified tool rows."},
    "verified_bound_local_tool_mode_rows": {"before": 40, "after": 40},
    "remaining_fixed_rows_outside_tally": 209,
    "completed_work": [
        "Reviewed the full iteration contract and froze exact ownership/exports for fresh coding workload311.",
        "Reviewed the full VDB contract/addendum and froze parser, binding and calculator ownership for fresh coding workload312.",
        "Clarified pure supplied-data qualification versus external acquisition custody without inventing a native manifest parser."
    ],
    "unfinished_work": [
        "Iteration and VDB field/function implementation, tests and root review are in progress, not complete.",
        "Native database producer/HPC contract310 remains under preparation/review; no producer coding or deployment claim.",
        "Exact database result metric projections and authenticated episode integration remain unfinished. Existing paired result path was read, not repurposed.",
        "Authentic mode outputs and required metadata acquisitions remain unfinished.",
        "All other fixed308-row work remains as previously recorded."
    ],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"],
}
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.063.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps({"changed_progress_rows": 4, "scope_rows": 308, "resource_bindings": 288,
    "numerical_grader_progress_tally": 99, "new_status_sha256": sha(STATUS)}))
