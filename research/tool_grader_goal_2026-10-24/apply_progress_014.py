"""Append actual repaired pairwise returns and installed phylogeny components."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = HERE / "WORK_STATUS.json"
raw = path.read_bytes()
before_hash = hashlib.sha256(raw).hexdigest()
prior = json.loads((HERE / "PROGRESS_UPDATE_013.json").read_text())
assert before_hash == prior["new_status_sha256"] == "3edf86d85847962a4e5e304116eb639bcfdf9d950bbd0dc20850f9c5bbdcba24"
assert not (HERE / "PROGRESS_UPDATE_014.json").exists()
work = json.loads(raw)
old = deepcopy(work)
evidence = []
pair_dir = "verification/tool_graders_bvbrc_homology_pairwise_workflow_2026-10-24/"
phy_dir = "verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24/"
pair = json.loads((ROOT / pair_dir / "FINAL_VERIFICATION.json").read_text())
phy = json.loads((ROOT / phy_dir / "PRODUCTION_VERIFICATION_001.json").read_text())
assert pair["actual_results_measurements"] == pair["actual_scientific_forwarded_measurements"] == {
    "aligned_pairs": 3, "identity": 1.0, "query_coverage": .6, "reference_coverage": .6}
assert pair["counts"] == {"runtime_actions": 16, "runtime_model_calls": 16,
                         "runtime_observations": 16, "runtime_report_attempts": 4}
assert pair["full_run"]["passed"] == 76 and pair["full_run"]["failed"] == 1
assert pair["focused_replay"]["passed"] == 1
assert phy["tests"] == {"passed": 150, "failed": 0, "errors": 0, "subtests_passed": 9}


def add(identity, passed, failed, summary, qualification, paths):
    assert identity not in {row["id"] for row in work["verification_evidence"]}
    evidence.append({"id": identity, "kind": "component_or_path_verification",
        "passed": passed, "failed": failed, "summary": summary, "qualification": qualification,
        "reports": [{"path": name, "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
                    for name in paths]})


add("BVBRC-HOMOLOGY-PAIRWISE-REPAIRED-FULL-PATH", 76, 1,
    "Repaired controlled Workflow delivered aligned_pairs=3, identity=1, coverage=.6/.6 through results, scientific parent and root; all four report admissions succeeded.",
    "The 77-test invocation had one test assertion failure comparing the six-field host outcome with the seven-field Workflow result. Scientific returns passed. Sixteen actions/observations, 355 original sources unchanged. Synthetic native bytes and scripted decisions; no live service or native program execution.",
    [pair_dir + "FINAL_VERIFICATION.json", pair_dir + "pytest-integrated-repaired.xml",
     pair_dir + "pytest-integrated-repaired.log"])
add("BVBRC-HOMOLOGY-PAIRWISE-RETAINED-REPLAY", 1, 0,
    "Corrected retained-run replay passes: original host outcome matches, Workflow pending-work field and complete saved action remain unchanged; zero new native/model calls or observations.",
    "Separate focused test on the same retained run, not a second all-green 77-test invocation. Saved sheet recalculation matches. Earlier failed results are preserved.",
    [pair_dir + "pytest-retained-replay.xml", pair_dir + "pytest-retained-replay.log",
     pair_dir + "runs/pairwise-ih4zrdlw/saved-replay-verification.json"])
add("PHYLOGENY-SHARED-PRODUCTION-150", 150, 0,
    "Five shared phylogeny format, validation, calculation and RAxML-log modules installed; 150 production tests and 9 subtests pass, including retained native artifacts and offline saved-data arithmetic.",
    "Shared components only; provider sheet assembly, application result binding and episode returns remain unfinished. Initial production run had 147 passes and three fixture-location errors; corrected lookup without changing numerical assertions. RAxML token correction has 26 passing cases. No new BV-BRC job or HPC execution.",
    [phy_dir + "PRODUCTION_VERIFICATION_001.json", phy_dir + "production-shared-tests-001.log",
     phy_dir + "production-shared-tests-002.xml", phy_dir + "production-shared-tests-002.log",
     phy_dir + "native-metadata-verification/VALIDATION_002.json",
     phy_dir + "formats-verification/VERIFICATION.json",
     phy_dir + "calculators-verification/VERIFICATION_REPORT.json"])

rows = {row["id"]: row for row in work["rows"]}
bindings = {row["id"]: row for row in work["resource_bindings"]}
pair_ids = ["C-L190-Homology", "C-L226-parsing-and-grading", "C-L227-return"]
for identity in pair_ids:
    row = rows[identity]
    row["overall"] = "homology_controlled_database_and_repaired_pairwise_paths_verified_live_and_other_applications_unfinished"
    row["integration_verification"] = "prior_database_paths_preserved_pairwise_actual_parent_values_and_separate_saved_replay_verified"
    row["evidence_ids"] = list(dict.fromkeys([*row["evidence_ids"], evidence[0]["id"], evidence[1]["id"]]))
    row["note"] += (" Update014: repaired full pairwise Workflow delivered 3 aligned residues, identity 1, "
        "query/reference coverage .6/.6 to both receiving parents, with four successful admissions and "
        "16 actions/observations. The invocation had 76 passes and one incorrect replay assertion; "
        "the corrected separate retained-run replay passes without new work. This is controlled "
        "synthetic verification, not live service execution or completion of other applications.")
row = rows["C-L224-artifact-acquisition"]
row["integration_verification"] = "prior_database_and_repaired_pairwise_actual_artifact_to_parent_paths_with_saved_replay_verified"
row["evidence_ids"] = list(dict.fromkeys([*row["evidence_ids"], evidence[0]["id"], evidence[1]["id"]]))
row["note"] += (" Update014: the separate repaired pairwise Workflow now returns the actual completed "
    "publication through both scientific boundaries; old partial records remain intact. Corrected "
    "retained replay adds no native/model calls, sources or observations.")

for identity in ["C-L193-CodonTree", "C-L194-GeneTree"]:
    row = rows[identity]
    row["overall"] = "shared_native_formats_calculations_installed_provider_and_episode_path_unfinished"
    row["source_presence"] = "retained_native_definitions_and_examples_with_five_installed_shared_phylogeny_modules"
    row["numerical_sheet"] = "shared_numeric_component_shapes_verified_provider_sheet_assembly_unfinished"
    row["native_parser"] = "newick_fasta_relaxed_phylip_raxml_partitions_phyloxml_and_raxml8_log_verified"
    row["metadata_extractor"] = "native_raxml_log_values_retained_provider_identity_and_metadata_joins_unfinished"
    row["deterministic_calculator"] = "eight_shared_pure_calculations_verified_provider_grader_unfinished"
    row["numerical_verification"] = "150_production_shared_tests_9_subtests_retained_native_examples_and_saved_arithmetic_verified"
    row["evidence_ids"] = list(dict.fromkeys([*row["evidence_ids"], evidence[2]["id"]]))
    row["note"] += (" Update014: shared modules installed and tested from production. Retained native "
        "example has 9x15300=137700 cells, 17308 gaps, four 3825-site partitions and six splits present "
        "in 100/100 explicit bootstrap mappings; RAxML final likelihood -56958.397755 is retained "
        "separately from its native 12.57% gap/undetermined statistic. Shared calculators preserve "
        "unknown units, exact original-coordinate requirements, function/taxon denominators and "
        "restricted split definitions. Provider sheets, metadata assembly, library/adapter binding, "
        "complete episode returns and live resource verification remain unfinished.")

changed_ids = {*pair_ids, "C-L224-artifact-acquisition", "C-L193-CodonTree", "C-L194-GeneTree"}
for identity in changed_ids:
    row, binding = rows[identity], bindings[identity + "::api"]
    for key in ("invocation_contract", "production_result_binding", "integration_verification", "live_resource_verification"):
        binding[key] = row[key]
    binding["evidence_ids"] = deepcopy(row["evidence_ids"])
    if identity in {"C-L193-CodonTree", "C-L194-GeneTree"}:
        binding["native_format_observed"] = "retained_official_repository_formats_verified_not_live_task_artifacts"
work["verification_evidence"].extend(evidence)
assert len(work["rows"]) == len(old["rows"]) == 308
assert len(work["resource_bindings"]) == len(old["resource_bindings"]) == 288
assert work["complete_scientific_tools_claimed"] == old["complete_scientific_tools_claimed"] == 0
changes = []
for group in ("rows", "resource_bindings"):
    original = {row["id"]: row for row in old[group]}
    assert set(original) == {row["id"] for row in work[group]}
    for row in work[group]:
        if row != original[row["id"]]:
            changes.append({"group": group, "id": row["id"], "before": original[row["id"]], "after": deepcopy(row)})
after = (json.dumps(work, indent=2) + "\n").encode()
update = {"schema": "tool_grader_progress_update_v1", "date": "2026-10-24",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "author": "root",
    "previous_status_sha256": before_hash, "new_status_sha256": hashlib.sha256(after).hexdigest(),
    "previous_goal_turn_classification": "progress: completed pairwise/replay evidence and new staged phylogeny modules; intervening bug explanation alone did not change state",
    "changes": changes, "added_evidence": evidence, "scope_changes": False,
    "specific_pending_NCBI_job_verification_included": False, "complete_scientific_tools_claimed": 0}
with (HERE / "PROGRESS_UPDATE_014.json").open("x") as record:
    record.write(json.dumps(update, indent=2) + "\n")
path.write_bytes(after)
print(json.dumps({"checkpoint": 14, "changes": len(changes), "added_evidence": len(evidence),
    "scope_rows": 308, "resource_bindings": 288, "complete_scientific_tools_claimed": 0,
    "new_status_sha256": update["new_status_sha256"]}))
