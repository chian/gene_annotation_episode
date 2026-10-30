"""Record actual Workflow/helper/native evidence without accepting another tool."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_100.json"
POLICY = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296,
          "wall_seconds": None}


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reports(paths):
    return [{"path": str(path.relative_to(ROOT)), "sha256": sha(path)}
            for path in sorted(set(paths))]


def receipt(directory, expected=0):
    value = read(directory / "receipt.json")
    assert value["returncode"] == expected
    assert value["metadata"]["policy"] == POLICY
    assert value["metadata"]["verified_cgroup"]["memory_max"] == POLICY["memory_bytes"]
    assert value["metadata"]["verified_cgroup"]["memory_swap_max"] == 0
    assert value["metadata"]["verified_cgroup"]["runtime_max"] == "infinity"
    return value


assert not UPDATE.exists()
previous = read(HERE / "PROGRESS_UPDATE_099.json")
before_sha, scope_sha = sha(STATUS), sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 112
assert status["verified_bound_local_tool_mode_rows"] == 42
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]

protein = ROOT / "verification/tool_graders_protein_structure_workflow_2026-10-27_410"
pr = receipt(protein / "check011")
assert pr["executed_source_pins_unchanged"]
before_pins = read(protein / "check011/source_pins_before.json")
assert len(before_pins) == 888
assert before_pins == read(protein / "check011/source_pins_after.json")
suite = ET.parse(protein / "check011/junit.xml").getroot().find("testsuite")
assert suite is not None
assert {key: suite.attrib[key] for key in ("tests", "errors", "failures", "skipped")} == {
    "tests": "4", "errors": "0", "failures": "0", "skipped": "0"}
assert len(pr["checkout_source_drift"]) == 1
drift = pr["checkout_source_drift"][0]
assert drift["before"]["path"] == "gene_annotation_episode/native_protein_structure_contracts.py"
assert drift["before"]["sha256"] == "13e1f7c4e9e60fed6283ab66aea03dd3b54de4767941d6509f496c2188cdaea0"
assert drift["after"]["sha256"] == "44e7308e77e0e6fdcc25cdf4bfa1448037150875c40284ae13ecfe668fc81774"
measured = read(protein / "MEASURED_EXAMPLE.json")
assert measured["actions"] == measured["observations"] == 22
assert measured["native_producer_plan_count"] == 3
assert measured["saved_worker_dispatch_count"] == 1

capture = ROOT / "verification/tool_graders_native_file_capture_2026-10-27_420"
cr = receipt(capture / "check001")
assert cr["executed_source_pins_unchanged"] and not cr["checkout_source_drift"]
assert "125 passed in 122.14s" in (capture / "check001/stdout.txt").read_text()
assert sha(ROOT / "gene_annotation_episode/native_file_capture.py") == "889f9a370faac34d1d4e973b14e52866a461895fe2a6716b141e7ae3d54eda7b"
assert sha(ROOT / "tests/test_native_file_capture.py") == "e13fecbac5fc006f28313360e890766450931aa4efd8b6764ff4cdb6341ee925"

native = ROOT / "verification/tool_graders_genomic_overlap_native_2026-10-27_421"
for attempt, expected in (("run001", 1), ("run002", 0)):
    nr = receipt(native / attempt, expected)
    assert nr["executed_source_unchanged"] and nr["checkout_source_unchanged"]
    assert all(nr["infrastructure_source_unchanged"].values())
cases = read(native / "run002/work/NATIVE_CHECKS.json")
assert cases["original_input_pins_unchanged"] and len(cases["cases"]) == 7
assert all(row["returncode"] == 0 and row["exact_match"] for row in cases["cases"])
assert [(row["native_pair_count"], row["native_pairwise_width_sum"]) for row in cases["cases"]] == [
    (2, 8), (3, 13), (4, 20), (0, 0), (0, 0), (1, 1), (1, 1)]
software = ROOT / "software/bedtools/ubuntu-2.31.1+dfsg-2/SOFTWARE.json"
assert read(software)["binary_sha256"] == cases["binary_sha256"]

planning = ROOT / "verification/tool_graders_genomic_overlap_contract_2026-10-27_418"
for filename, expected in {
    "CONTRACT.md": "85e9a3756d35a253e3329135ac67d777f9577b3f31a4aced282dbec3ac0e5bb7",
    "HANDOFF.md": "f235f4ae9c84616a9efb534ba3ef5c1d10eaaaf6afdd4db19dfe5e0318542a15",
    "DATA_CONTRACT.json": "feb53c29f02ac3c1663c998e37bc6cd399a28179a055af39a4175aab66f44b66",
    "WORKED_EXAMPLE.json": "bdc01b2febd6f87cc8a488e4fc6677ce8d0c097122ccb387fef61d4ac9a2a6da",
}.items():
    assert sha(planning / filename) == expected
accepted = ROOT / "verification/tool_graders_genomic_overlap_implementation_2026-10-27_422"

protein_summary = (
    "410 check011 passed all four scripted full-Workflow tests in 5007.26 seconds. "
    "Actual structure extraction, sequence alignment, native comparison, saved recalculation and "
    "six requested numerical fields reached the scientific receiver, coordinator and root. "
    "Alignment score19/4pairs, held-out RMSD2A/1pair, saved RMSD1A/4pairs; original data and history "
    "unchanged. 22 actions produced22 observations and all10 practical episodes closed with exact-zero "
    "future expectations. All888 executed pins unchanged; later417 checkout schema optimization is "
    "separately qualified. Receiver text and decision-operand integration remain unfinished.")
overlap_summary = (
    "418 exact pure data/numerical/projection contracts accepted in422; fresh423 and424 coding "
    "is active and425 defines the still-unassigned native binding contract. The reusable420 complete-file "
    "capture helper passed125 tests with actual Store files. Project-local bedtools v2.31.1 deployment "
    "passed421/run002 seven real native synthetic-input cases with plain -wo -sorted. Run001's false "
    "default-fraction expectation is preserved and corrected. No overlap grader, library binding or "
    "full episode integration is accepted yet.")
items = [
    {"id": "PROTEIN-FULL-SCRIPTED-WORKFLOW-100", "kind": "full_selected_scripted_workflow_on_pinned_sources",
     "summary": protein_summary,
     "qualification": "Synthetic structures, actual local numerical execution, scripted choices; no configured-model scientific annotation. Check011 executed the pre416/417 schema pin, not the later optimized checkout. No additional whole-tool count until outstanding receiver integration is completed.",
     "reports": reports([protein / name for name in (
         "REPORT.md", "MEASURED_EXAMPLE.json", "ROOT_RECEIVED_CONTEXT_FIXTURE.json",
         "check011/receipt.json", "check011/junit.xml", "check011/stdout.txt",
         "check011/source_pins_before.json", "check011/source_pins_after.json",
         "check011/temporary/pytest/protein-workflow4100/CASE.json",
         "check011/temporary/pytest/protein-workflow4100/SAVED_CHECK.json")])},
    {"id": "GENOMIC-OVERLAP-CONTRACT-NATIVE-PREREQUISITE-100",
     "kind": "accepted_pure_contract_mechanical_helper_and_native_prerequisite_no_tool_completion",
     "summary": overlap_summary,
     "qualification": "420 verifies mechanical byte retention, not scientific grading or original-action authority. 421 verifies real native BED4 outputs with A1/B1 tokens; canonical G1-token parser and complete episode integration remain unverified. Pairwise sums are not unique shared bases. Planning is not implementation, and no native API/HPC binding is claimed.",
     "reports": reports([planning / name for name in (
         "CONTRACT.md", "HANDOFF.md", "DATA_CONTRACT.json", "WORKED_EXAMPLE.json", "DOCUMENT_VALIDATION.json")]
         + [accepted / "ROOT_CONTRACT.md", accepted / "PROJECTION_CLARIFICATIONS_001.md"]
         + [capture / name for name in ("REPORT_001.md", "check001/receipt.json",
             "check001/stdout.txt", "check001/example_capture.json")]
         + [native / name for name in ("REPORT_001.md", "run001/receipt.json", "run002/receipt.json",
             "run002/work/NATIVE_CHECKS.json")]
         + [software, ROOT / "gene_annotation_episode/native_file_capture.py",
            ROOT / "tests/test_native_file_capture.py"])},
]
assert not {item["id"] for item in items} & {item["id"] for item in status["verification_evidence"]}
status["verification_evidence"].extend(items)
protein_id = "B-L107-compare_protein_structures"
overlap_id = "B-L123-analyze_genomic_region_overlap"
changes, binding_changes = [], []
for row in status["rows"]:
    if row["id"] not in (protein_id, overlap_id):
        continue
    before = deepcopy(row)
    if row["id"] == protein_id:
        row.update(overall="pinned_full_workflow_verified_receiver_text_and_operands_open",
                   invocation_contract="local_registration_and_scripted_full_workflow_verified",
                   production_result_binding="actual_full_scripted_workflow_to_root_verified_check011_sources",
                   integration_verification="full_scripted_workflow_verified_receiver_text_and_operands_open",
                   live_resource_verification="actual_local_structure_extraction_alignment_comparison_and_saved_recalculation_synthetic_inputs")
        row["evidence_ids"].append(items[0]["id"])
        row["note"] += " Update100: " + protein_summary + " Tool count unchanged."
    else:
        row.update(overall="contracts_accepted_native_prerequisite_verified_implementation_in_progress",
                   source_presence="upstream_operation_and_project_local_bedtools_present",
                   tool_information="planned_exact_operation_and_resource_information_not_published",
                   invocation_contract="plain_bedtools_native_format_verified_episode_binding_contract_in_progress",
                   numerical_sheet="exact_contract_accepted_pure_implementation_in_progress",
                   native_parser="exact_contract_accepted_pure_implementation_in_progress",
                   metadata_extractor="exact_contract_accepted_pure_implementation_in_progress",
                   deterministic_calculator="exact_contract_accepted_pure_implementation_in_progress",
                   live_resource_verification="seven_native_synthetic_input_cases_no_episode_binding")
        row["evidence_ids"].append(items[1]["id"])
        row["note"] += " Update100: " + overlap_summary
    changes.append({"id": row["id"], "before": before, "after": deepcopy(row)})
for row in status["resource_bindings"]:
    if row["id"] not in (protein_id + "::local", overlap_id + "::local"):
        continue
    before = deepcopy(row)
    if row["id"] == protein_id + "::local":
        row.update(production_result_binding="full_scripted_workflow_verified_check011_sources",
                   integration_verification="full_scripted_workflow_verified_receiver_text_and_operands_open",
                   live_resource_verification="actual_native_alignment_comparison_saved_recalculation_synthetic_inputs")
        row["evidence_ids"].append(items[0]["id"])
    else:
        row.update(invocation_contract="plain_native_invocation_verified_episode_binding_unimplemented",
                   prerequisites_present="explicit_project_local_bedtools_v2_31_1_verified",
                   native_format_observed="seven_exact_native_bed4_intersect_wo_cases",
                   live_resource_verification="native_synthetic_input_fixtures_only_no_episode_path")
        row["evidence_ids"].append(items[1]["id"])
    binding_changes.append({"id": row["id"], "before": before, "after": deepcopy(row)})
assert len(changes) == len(binding_changes) == 2
assert all(a == b for a, b in zip(original["rows"], status["rows"])
           if a["id"] not in (protein_id, overlap_id))
assert all(a == b for a, b in zip(original["resource_bindings"], status["resource_bindings"])
           if a["id"] not in (protein_id + "::local", overlap_id + "::local"))
checklist = deepcopy(previous["work_item_states"])
for row in checklist:
    if row["id"] == "U05":
        row["current_evidence"] += (
            " Update100: 410 complete scripted Workflow passed4 tests on its immutable pre416/417 "
            "schema snapshot; receiver text/operand integration remains open. 420 complete-file "
            "helper passed125 tests; 421 corrected native overlap invocation passed7 real cases. "
            "418/422 exact pure overlap contracts are accepted;423/424 implementation and425 native "
            "contract work continue. No complete tool added:112/308,42 local bindings,196 remaining "
            "rows. All prior historical failures and W05/literature separation remain.")
assert [(x["id"], x["original_item"], x["status"]) for x in checklist] == [
    (x["id"], x["original_item"], x["status"]) for x in previous["work_item_states"]]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {
    "schema": "tool_grader_progress_update_v1", "date": "2026-10-27", "author": "root",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "previous_status_sha256": before_sha,
    "new_status_sha256": hashlib.sha256(raw).hexdigest(), "scope_sha256_unchanged": scope_sha,
    "scope_changes": [], "changes": changes, "resource_binding_changes": binding_changes,
    "added_evidence": items,
    "numerical_grader_progress_tally": {"before": 112, "after": 112, "added_row_ids": [],
        "meaning": previous["numerical_grader_progress_tally"]["meaning"]},
    "verified_bound_local_tool_mode_rows": {"before": 42, "after": 42},
    "remaining_fixed_rows_outside_tally": 196,
    "completed_work": [protein_summary, overlap_summary],
    "findings_requiring_repair": deepcopy(previous["findings_requiring_repair"]),
    "work_item_states": checklist,
    "unfinished_work": [x["current_evidence"] for x in checklist if x["status"] != "complete"],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"],
}
assert sha(STATUS) == before_sha and sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.100.writing")
with temporary.open("xb") as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_tool_rows": 2, "updated_resource_bindings": 2,
    "grader_tally": 112, "verified_local_bindings": 42, "remaining_rows": 196,
    "new_status_sha256": sha(STATUS)}))
