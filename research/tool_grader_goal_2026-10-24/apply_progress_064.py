"""Record verified iteration field/functions, preserving all unfinished rows."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_064.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(relative):
    return {"path": relative, "sha256": sha(ROOT / relative)}


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = json.loads((HERE / "PROGRESS_UPDATE_063.json").read_text())
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
authority = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert sha(authority) == "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"
packet = "verification/tool_graders_blast_iteration_2026-10-26_311/"
for filename in ("IMPLEMENTATION_HASHES.sha256", "AUTHORITY_AND_INPUT_HASHES.sha256", "SOURCE_HASHES_AFTER.sha256"):
    for line in (ROOT / packet / filename).read_text().splitlines():
        expected, path = line.split(maxsplit=1)
        assert sha(ROOT / path) == expected, path
receipt = json.loads((ROOT / packet / "check004/receipt.json").read_text())
assert receipt["returncode"] == 0
assert receipt["policy"] == {"memory_bytes": 20 * 1024**3, "scratch_bytes": 4 * 1024**3, "wall_seconds": None}
suites = list(ET.parse(ROOT / packet / "check004/junit.xml").getroot().iter("testsuite"))
assert len(suites) == 1
assert {k: int(suites[0].get(k)) for k in ("tests", "failures", "errors", "skipped")} == {
    "tests": 324, "failures": 0, "errors": 0, "skipped": 0}
assert json.loads((ROOT / packet / "examples001/receipt.json").read_text())["returncode"] == 0
examples = json.loads((ROOT / packet / "examples001/filled/MANIFEST.json").read_text())
assert len(examples) == 9
for example in examples:
    for item in example["files"].values():
        assert sha(ROOT / item["path"]) == item["sha256"]

evidence = {
    "id": "BLAST-ITERATION-FIELDS-FUNCTIONS-064",
    "kind": "pure_component_implementation_and_verification",
    "reports": [descriptor(packet + p) for p in (
        "CONTRACT_001.md", "HANDOFF.md", "ROOT_REVIEW_001.md", "IMPLEMENTATION_HASHES.sha256",
        "SOURCE_HASHES_AFTER.sha256", "check004/receipt.json", "check004/junit.xml",
        "examples001/receipt.json", "examples001/filled/MANIFEST.json",
        "examples001/filled/NUMERICAL_SUMMARY.json")],
    "summary": "Iteration fields and pure population/calculation functions implemented; 98 focused plus226 dependency tests passed. Root reviewed fixes, receipts, hashes and examples.",
    "qualification": "Synthetic searches/supplied membership observations and retained upstream PSSM inputs do not establish native membership/convergence extraction, new database searches, deployment or episode result integration.",
}
assert not any(e["id"] == evidence["id"] for e in status["verification_evidence"])
status["verification_evidence"].append(evidence)
changes = []
for mode in ("psiblast", "deltablast"):
    row = next(r for r in status["rows"] if r["id"] == "A-L070-" + mode + "-database")
    before = deepcopy(row)
    assert row["numerical_sheet"].endswith("iteration_contract_reviewed_implementation_in_progress")
    row["numerical_sheet"] = row["numerical_sheet"].removesuffix("iteration_contract_reviewed_implementation_in_progress") + "iteration_fields_implemented_and_verified"
    row["deterministic_calculator"] = "per_search_sequence_profile_pssm_components_and_pure_iteration_composition_verified"
    row["metadata_extractor"] = "explicit_source_identity_checkpoint_membership_convergence_ports_verified_native_acquisition_and_extractors_pending"
    row["numerical_verification"] = "324_passing_iteration_and_dependency_cases_nine_examples_reviewed_authentic_mode_search_pending"
    row["evidence_ids"].append(evidence["id"])
    row["note"] += " Update064: iteration field definitions and population/calculation functions verified. Filled sheets are test outputs. Native membership/convergence extractors, real execution and episode returns remain unfinished; no tally increment."
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
    "changes": changes, "added_evidence": [evidence],
    "verification": [{"packet": packet, "test_receipt": packet + "check004/receipt.json",
        "tests_passed": 324, "focused_iteration_cases": 98, "dependency_cases": 226,
        "native_mode_search_executed": False, "episode_path_verified": False}],
    "numerical_grader_progress_tally": {"before": 99, "after": 99, "added_row_ids": [],
        "meaning": "Pure iteration composition adds verified components; missing native extraction and full mode work remain outside the tool tally."},
    "verified_bound_local_tool_mode_rows": {"before": 40, "after": 40},
    "remaining_fixed_rows_outside_tally": 209,
    "completed_work": [
        "Iteration field definitions and functions to populate/calculate them implemented and reviewed with324 passing tests.",
        "Source-qualified empty membership, exact checkpoint-axis comparison and native iteration label conflict regressions verified.",
        "Native producer310 contract and additive seams reviewed;313 exact owned-file implementation commissioned with a fresh subagent."
    ],
    "unfinished_work": [
        "VDB312 verification remains open: root identified unavailable-report population zeros and duplicate-feature aggregation errors; fixes/tests are in progress.",
        "Native producer313 is coding; no deployment or selected HPC job has been verified.",
        "Exact database result/metadata/projection contract314 is being defined from actual consumers before integration coding.",
        "Native membership/convergence extraction, authentic mode outputs, metadata acquisition, complete execution and typed episode integration remain unfinished.",
        "All other fixed308-row work remains recorded; no scope or resource-binding row was removed."
    ],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"],
}
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.064.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps({"changed_progress_rows": 2, "scope_rows": 308, "resource_bindings": 288,
    "numerical_grader_progress_tally": 99, "new_status_sha256": sha(STATUS)}))
