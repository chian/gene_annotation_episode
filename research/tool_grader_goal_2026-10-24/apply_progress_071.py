"""Record verified episode paths and correct the implemented-grader tally."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_071.json"
E = ROOT / "verification/tool_graders_native_blast_database_episode_binding_2026-10-26_321"
REVIEW = ROOT / "verification/tool_graders_native_blast_convergence_review_2026-10-26_330"
COUNT = ROOT / "verification/tool_graders_blast_grader_completion_check_2026-10-26_334"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def descriptor(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path))


def passed(directory, summary):
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == 0
    policy = receipt["policy"] if "policy" in receipt else receipt["metadata"]["policy"]
    assert policy == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
    assert summary in (directory / "stdout.txt").read_text()


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = read(HERE / "PROGRESS_UPDATE_070.json")
before_sha = sha(STATUS)
assert before_sha == previous["new_status_sha256"]
scope_sha = sha(HERE / "SCOPE.json")
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 99
assert status["verified_bound_local_tool_mode_rows"] == 40
authority = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert sha(authority) == status["authority_sha256"]
assert sha(COUNT / "ASSESSMENT_001.md") == "61fc8f1921c29b5f5ebd48a90a6d0cefdccdcca29c10b713fbd45bbfae2c8a76"
passed(E / "check_20261026T203930751718Z", "110 passed")
passed(E / "check_20261026T205513699967Z", "1 passed")
passed(REVIEW / "check001", "111 passed")
broad = E / "check_20261026T201410099321Z"
assert read(broad / "receipt.json")["returncode"] == 1
assert "9 failed, 394 passed" in (broad / "stdout.txt").read_text()
# E's own final implementation snapshot still matches. Its dependency hashes
# remain facts of that run; later separately verified fixes do not reprice it.
evidence = read(E / "HANDOFF_EVIDENCE_001.json")
for group in ("owned_production", "shared_integration", "tests"):
    for record in evidence[group]:
        path = ROOT / record["path"]
        assert sha(path) == record["sha256"] and path.stat().st_size == record["size_bytes"]

added = []


def add(identity, summary, qualification, paths):
    item = dict(id=identity, kind="reviewed_implementation_component",
        reports=[descriptor(p) for p in paths], summary=summary, qualification=qualification)
    assert not any(r["id"] == identity for r in status["verification_evidence"])
    status["verification_evidence"].append(item)
    added.append(item)


add("BLAST-DATABASE-EPISODE-PATH-071",
    "Six-mode original-attempt capture, actual field-population/calculation worker, frozen numerical rows and requested typed child returns connected and synthetically verified; original received-cell unions and failed-attempt delivery verified.",
    "Final110 integration cases plus1 disjoint retained-history case passed. Root reviewed source/receipts and verified762 evidence descriptors. Broader394passed/9failed run remains failed. No live native database execution or every-optional-metadata-family end-to-end claim.",
    [E / name for name in ("HANDOFF_001.md", "HANDOFF_EVIDENCE_001.json", "SHARED_CHANGES_001.md", "WIRING_001.md", "ROOT_REVIEW_001.md")])
add("BLAST-CONVERGENCE-INDEPENDENT-REVIEW-071",
    "Independent review found no defect in captured convergence binding, field population, actual worker connection, original occurrence identities and saved-sheet recalculation.",
    "111 tests passed in the separate330 review; this count overlaps prior component checks and is not added to tool counts. Source-derived synthetic bytes only; live execution remains unverified.",
    [REVIEW / "REVIEW_001.md", REVIEW / "check001/receipt.json", REVIEW / "check001/stdout.txt"])
add("BLAST-IMPLEMENTED-GRADER-COUNT-CORRECTION-071",
    "Four additional fixed rows now meet the existing numerical-fields/functions plus verified-declared-episode-path criterion: PSI, DELTA, RPS and RPST. Both VDB modes remain excluded for a missing candidate-function calculation.",
    "Corrects stale accounting after E completion, not a change in goal, scope or tally criterion. Native-input extensions and live resources stay separately qualified. Read-only334 assessment did not execute tests or implement graders.",
    [COUNT / "ASSESSMENT_001.md", ROOT / "gene_annotation_episode/knowledge/native-blast-database-results.md"])

modes = ("psiblast", "deltablast", "rpsblast", "rpstblastn", "blastn_vdb", "tblastn_vdb")
selected = {"A-L070-" + mode + "-database" for mode in modes}
newly_counted = {"A-L070-" + mode + "-database" for mode in modes[:4]}
changes = []
for row in status["rows"]:
    if row["id"] not in selected:
        continue
    before = deepcopy(row)
    row["overall"] = (
        "numerical_grader_implemented_declared_synthetic_episode_path_verified_live_and_extended_native_inputs_unfinished"
        if row["id"] in newly_counted else
        "partial_vdb_numerical_components_and_synthetic_episode_path_verified_candidate_function_calculation_missing")
    row["production_result_binding"] = "actual_population_calculation_worker_frozen_rows_and_original_typed_child_return_connected"
    row["integration_verification"] = "110_focused_E_checks_and1_retained_history_check_passed_source_only_and_query_bound_hsp_returns_verified_optional_family_coverage_separately_qualified"
    row["evidence_ids"].extend(item["id"] for item in added)
    row["note"] += (
        " Update071: E321 consolidation and root review are complete for the declared synthetic path;110 focused checks and1 separate old-history check passed. Independent330 bridge/worker review passed111 tests; counts are separate and overlap earlier checks. Actual HSP/query-subject and convergence returns, received-cell unions, failed partial handoffs, frozen history and practical completion behavior were verified. The broader394passed/9failed run remains unresolved. No native HPC execution or every optional metadata family is claimed. "
        + ("This row now enters the existing implemented-grader tally; its missing episode-path blocker was stale after these checks. Remaining native-input coverage and live-resource status are separate. "
           if row["id"] in newly_counted else
           "This row remains outside the tally because the query-to-candidate-function statistical calculation is not implemented; native counts, fractions, geometry and associations are implemented. ")
        + "A newly reproduced selected-sidecar capture-key validation defect is assigned to335 as a narrow compatibility fix; existing producer roles and historical results must remain unchanged.")
    changes.append(dict(group="rows", id=row["id"], before=before, after=deepcopy(row)))
for row in status["resource_bindings"]:
    if row["id"] not in {key + "::hpc" for key in selected}:
        continue
    before = deepcopy(row)
    row["production_result_binding"] = "original_attempt_capture_actual_numerical_worker_frozen_rows_and_typed_child_returns_connected"
    row["integration_verification"] = "synthetic_PBS_selected_child_path_verified_110_E_cases_plus1_retained_history_case_live_execution_unverified"
    row["evidence_ids"].extend(item["id"] for item in added)
    changes.append(dict(group="resource_bindings", id=row["id"], before=before, after=deepcopy(row)))
assert len(changes) == 12
for group in ("rows", "resource_bindings"):
    affected = {c["id"] for c in changes if c["group"] == group}
    assert [r["id"] for r in status[group]] == [r["id"] for r in original[group]]
    assert all(a == b for a, b in zip(original[group], status[group]) if a["id"] not in affected)
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = dict(schema="tool_grader_progress_update_v1", date="2026-10-26", author="root",
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=added,
    numerical_grader_progress_tally=dict(before=99, after=103, added_row_ids=sorted(newly_counted),
        meaning="Existing criterion: implemented numerical fields/functions/validation with verified declared episode paths; not every-resource, every-native-format or whole-goal completion."),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=205,
    completed_work=[
        "Six-mode actual result path and declared child returns implemented and synthetically verified.",
        "Independent convergence bridge/population/worker/replay review completed with111 passing tests.",
        "Four additional grader entries meet the existing implementation tally criterion; stale count corrected from99 to103.",
        "Results-library information now describes the implemented native2.17.0+ convergence extraction and the components used or unused by the existing function kernel."],
    unfinished_work=[
        "Both VDB candidate-function calculations remain unimplemented; their other numerical components and declared synthetic episode paths are verified.",
        "Remaining native-input coverage, authentic native-mode fixtures and actual HPC deployment/execution remain separately unverified.",
        "Nine broader regression failures remain: eight retired categorical-scorer calls and one BV-BRC operation declaration mismatch.",
        "335 is correcting a reproduced selected-sidecar key mismatch in the public metadata validator; no rewrite of producer semantics or old results is authorized.",
        "Standard-five N331 reports196 combined tests and137 final contract tests; root source review remains. M332 and R333 implement the new supplied-byte population and calculation/result functions. Standard E integration is unassigned.",
        "The other fixed308 scope, separateW05 work and literature exclusion remain unchanged."],
    accounting_correction="Earlier same-turn claim that the six modes were already included in99 was wrong. Four now qualify; two still lack a required calculation.",
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status["complete_scientific_tools_claimed"])
assert sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.071.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=6, updated_resource_bindings=6, scope_rows=308,
    numerical_grader_progress_tally=103, newly_counted=sorted(newly_counted),
    remaining_fixed_rows_outside_tally=205, new_status_sha256=sha(STATUS))))
