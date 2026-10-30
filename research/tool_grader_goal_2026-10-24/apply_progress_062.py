"""Record verified BLAST field/function components without claiming integration."""
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
UPDATE = HERE / "PROGRESS_UPDATE_062.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}


def load(path):
    return json.loads(path.read_text())


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = load(HERE / "PROGRESS_UPDATE_061.json")
before_sha = sha(STATUS)
assert before_sha == previous["new_status_sha256"]
scope_sha = sha(HERE / "SCOPE.json")
assert scope_sha == previous["scope_sha256_unchanged"]
status = load(STATUS)
row_ids = [r["id"] for r in status["rows"]]
binding_ids = [r["id"] for r in status["resource_bindings"]]
assert len(row_ids) == 308 and len(binding_ids) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 99
assert status["verified_bound_local_tool_mode_rows"] == 40

packets = {
    "sequence": ROOT / "verification/tool_graders_blast_sequence_database_2026-10-26_303",
    "profile": ROOT / "verification/tool_graders_blast_profiles_2026-10-26_305",
    "pssm": ROOT / "verification/tool_graders_blast_pssm_2026-10-26_306",
    "layout": ROOT / "verification/tool_graders_blast_table_layout_2026-10-26_307",
}
verification = []
for kind, label, expected, xml in (
    ("sequence", "check005", 454, "junit.xml"),
    ("profile", "check005", 288, "junit.xml"),
    ("pssm", "alphabet_review001", 72, "pytest.xml"),
    ("layout", "check_001", 338, "pytest.xml"),
):
    directory = packets[kind] / label
    receipt = load(directory / "receipt.json")
    cases = list(ET.parse(directory / xml).getroot().iter("testcase"))
    assert receipt["returncode"] == 0 and len(cases) == expected
    assert not any(c.find(tag) is not None for c in cases for tag in ("failure", "error", "skipped"))
    policy = receipt["metadata"]["policy"]
    assert policy == {"memory_bytes": 20 * 1024**3, "scratch_bytes": 4 * 1024**3, "wall_seconds": None}
    verification.append({"kind": kind, "passing_checks": expected,
        "receipt": descriptor(directory / "receipt.json"),
        "test_outcome": descriptor(directory / xml),
        "meaning": "supplied-data field population/calculation and declared regressions; suites overlap"})

sequence = load(packets["sequence"] / "check005/source_hashes_after.json")
assert sequence == load(packets["sequence"] / "check005/source_hashes_before.json")
owned_sequence = load(packets["sequence"] / "FINAL_MANIFEST.json")["owned_files"]
for name, expected in owned_sequence.items():
    assert sha(ROOT / name) == expected == sequence[name], name
superseded = {"gene_annotation_episode/blast_profile_calculators.py",
              "gene_annotation_episode/blast_pssm_calculators.py"}
sequence_differences = [name for name, expected in sequence.items() if sha(ROOT / name) != expected]
assert set(sequence_differences) <= superseded
profile = load(packets["profile"] / "check005/source_hashes.json")
for name, expected in profile.items():
    assert sha(ROOT / name) == expected, name
pssm = load(packets["pssm"] / "alphabet_review001/receipt.json")
assert pssm["source_sha256_before"] == pssm["source_sha256_after"]
for name, expected in pssm["source_sha256_after"].items():
    assert sha(ROOT / name) == expected, name
layout = load(packets["layout"] / "check_001/receipt.json")
for name in ("gene_annotation_episode/blast_report_collection.py", "tests/test_blast_table_layout.py"):
    assert sha(ROOT / name) == layout["source_sha256_before"][name] == layout["source_sha256_after"][name]

exports = []
for kind, label, index in (
    ("sequence", "example_export003", "EXAMPLE_SUMMARY.json"),
    ("profile", "examples003", "filled/INDEX.json"),
    ("pssm", "examples003", "examples/MANIFEST.json"),
):
    directory = packets[kind] / label
    assert load(directory / "receipt.json")["returncode"] == 0
    exports.append({"kind": kind, "receipt": descriptor(directory / "receipt.json"),
                    "index": descriptor(directory / index)})

reports = [("sequence", "VERIFICATION.md"), ("sequence", "FIELDS_AND_FUNCTIONS.md"),
           ("profile", "HANDOFF.md"), ("profile", "FIELD_DEFINITIONS.md"),
           ("pssm", "HANDOFF_001.md"), ("pssm", "HANDOFF_ADDENDUM_004.md"),
           ("pssm", "CONTRACT_ADDENDUM_003.md"), ("layout", "VERIFICATION_001.md")]
evidence = {
    "id": "BLAST-DATABASE-PROFILE-PSSM-COMPONENTS-062",
    "kind": "implemented_fields_population_functions_and_separate_calculators",
    "summary": "Sequence-database, profile and PSSM/MSA supplied-data components verified; original member/table/report associations preserved. Native mode execution and receiving-episode paths remain unfinished.",
    "reports": [descriptor(packets[kind] / name) for kind, name in reports],
    "qualification": "Synthetic PSI/DELTA/profile contexts, retained ordinary BLAST output and genuine upstream PSSM/MSA input fixtures are distinct. No new database search or HPC deployment is claimed.",
}
assert not any(e["id"] == evidence["id"] for e in status["verification_evidence"])
status["verification_evidence"].append(evidence)
changes = []
for mode in ("psiblast", "deltablast", "rpsblast", "rpstblastn"):
    row_id = "A-L070-" + mode + "-database"
    row = next(r for r in status["rows"] if r["id"] == row_id)
    before = deepcopy(row)
    iterative = mode in ("psiblast", "deltablast")
    row.update(
        overall="partial_fields_and_functions_verified_execution_and_episode_integration_pending",
        source_presence="new_mode_specific_pure_population_and_calculation_functions_inspected",
        numerical_sheet=("per_search_sequence_and_pssm_fields_implemented_iteration_contract_pending" if iterative
            else "profile_hsp_model_coverage_threshold_and_dependence_fields_implemented"),
        native_parser=("shared_original_report_parser_and_pssm_asn_clustal_inputs_verified_mode_native_search_pending" if iterative
            else "shared_report_parser_verified_synthetic_profile_context_actual_profile_search_fixture_pending"),
        metadata_extractor="supplied_original_source_and_identity_links_validated_native_metadata_acquisition_pending",
        deterministic_calculator=("per_search_existing_sequence_model_geometry_and_pssm_components_verified_iteration_pending" if iterative
            else "separate_profile_position_unions_coverage_and_same_model_threshold_margins_verified"),
        production_result_binding="not_implemented_for_these_new_mode_components",
        numerical_verification="synthetic_context_and_retained_shared_format_checks_passed_with_declared_native_limits",
        integration_verification="new_mode_selected_execution_to_requested_episode_return_not_verified",
        live_resource_verification="no_new_mode_database_execution_no_authentic_mode_fixture_claim",
        evidence_ids=[*row["evidence_ids"], evidence["id"]],
    )
    if mode == "deltablast":
        row["numerical_sheet"] = "per_search_sequence_explicit_domain_and_pssm_fields_implemented_iteration_contract_pending"
    row["note"] += (" Update062: field definitions and functions to populate/calculate them are implemented for the stated components; filled sheets are verification examples."
        " Full mode execution, actual required metadata acquisition and typed episode return remain unfinished; this row does not enter the numerical progress tally yet.")
    changes.append({"group": "rows", "id": row_id, "before": before, "after": deepcopy(row)})

assert [r["id"] for r in status["rows"]] == row_ids
assert [r["id"] for r in status["resource_bindings"]] == binding_ids
assert sha(HERE / "SCOPE.json") == scope_sha
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {
    "schema": "tool_grader_progress_update_v1", "date": "2026-10-26",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "author": "root",
    "previous_status_sha256": before_sha, "new_status_sha256": hashlib.sha256(raw).hexdigest(),
    "scope_sha256_unchanged": scope_sha, "scope_changes": [], "changes": changes,
    "added_evidence": [evidence], "verification": verification, "verification_examples": exports,
    "source_qualification": {"sequence_snapshot_current_differences": sequence_differences,
        "meaning": "Only separately verified profile/PSSM components changed after sequence checks; sequence-owned files and other captured dependencies still match. No whole-checkout stable snapshot is claimed."},
    "numerical_grader_progress_tally": {"before": 99, "after": 99, "added_row_ids": [],
        "meaning": "New standalone components do not meet the existing declared-episode-path tally criterion."},
    "verified_bound_local_tool_mode_rows": {"before": 40, "after": 40},
    "remaining_fixed_rows_outside_tally": 209,
    "completed_work": [
        "Defined and implemented sequence-database per-search fields and separate calculations, preserving the existing model.",
        "Defined and implemented profile HSP/model fields and separate geometry/threshold/dependence calculations.",
        "Defined and implemented PSSM ASN and CLUSTAL input population plus deterministic matrix/master calculations.",
        "Retained exact BLAST table layouts and corrected explicit PSSM alphabet failure handling."
    ],
    "unfinished_work": [
        "PSI/DELTA iteration composition and VDB member/feature calculations; exact contracts under read-only refinement.",
        "Native database execution/capture and receiving episode integration; concrete existing HPC hooks under read-only review.",
        "Actual required database/model/member metadata acquisition and authentic mode verification.",
        "Previously recorded HMMER and remaining fixed308-row field/function/resource/integration work."
    ],
    "excluded_claims": ["Whole-goal completion", "New mode native execution", "HPC deployment",
        "New mode production episode return", "W05 or annotation scoring", "Literature graders"],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"],
}
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.062.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_partial_rows": 4, "scope_rows": 308, "resource_bindings": 288,
                  "numerical_grader_progress_tally": 99, "new_status_sha256": sha(STATUS)}))
