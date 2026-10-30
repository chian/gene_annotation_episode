"""Record the reviewed standard BLAST metadata implementation boundary."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_073.json"
M = ROOT / "verification/tool_graders_standard_blast_database_metadata_2026-10-26_332"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = read(HERE / "PROGRESS_UPDATE_072.json")
before_sha = sha(STATUS)
scope_sha = sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 103
assert status["verified_bound_local_tool_mode_rows"] == 40
for row in read(M / "check009/source_snapshot.json"):
    if row["path"] in {"gene_annotation_episode/native_blast_standard_database_metadata.py", "tests/test_native_blast_standard_database_metadata.py"}:
        path = ROOT / row["path"]
        assert sha(path) == row["sha256"] and path.stat().st_size == row["size_bytes"]
receipt = read(M / "check009/receipt.json")
assert receipt["returncode"] == 0
assert receipt["metadata"]["policy"] == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
assert "70 passed" in (M / "check009/stdout.txt").read_text()
paths = [M / name for name in ("check009/source_snapshot.json", "check009/receipt.json", "check009/stdout.txt")]
item = dict(id="BLAST-STANDARD-DATABASE-METADATA-073", kind="reviewed_implementation_component",
    reports=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p)) for p in paths],
    summary="Four supplied-data preparation/population functions and four saved-artifact validators implemented and root reviewed;70 cases passed with checkable existing303 numerical outputs.",
    qualification="Synthetic standard database inputs; one actual paired report used only for format/geometry. No resource acquisition, results-worker/episode completion or new formula. Shared FASTA source-address and database path/semantic-census limitations remain explicit.")
assert not any(r["id"] == item["id"] for r in status["verification_evidence"])
status["verification_evidence"].append(item)
ids = {"A-L069-" + p + "-database" for p in ("blastn", "blastp", "blastx", "tblastn", "tblastx")}
changes = []
for row in status["rows"]:
    if row["id"] not in ids:
        continue
    before = deepcopy(row)
    row["overall"] = "partial_standard_database_producer_and_pure_metadata_population_verified_results_and_episode_integration_in_progress"
    row["numerical_sheet"] = "direct_existing_sequence_database_and_supplied_pssm_sheet_population_verified_standard_result_worker_pending"
    row["native_parser"] = "supplied_standard_query_fasta_json_and_text_asn_parsing_with_public_json15_tabular6_tabular7_collection_verified_synthetically"
    row["metadata_extractor"] = "four_pure_supplied_data_ports_and_four_saved_validators_verified_original_sources_and_sparse_ordinals_retained_shared_fasta_record_address_limit_open"
    row["deterministic_calculator"] = "existing_public303_calculation_exercised_on_standard_prepared_sheets_separate_standard_R_worker_under_verification"
    row["numerical_verification"] = "70_M_cases_passed_full_selected_reported_geometry_source_identity_partial_metadata_duplicates_census_pssm_and_parser_free_saved_validation"
    row["evidence_ids"].append(item["id"])
    row["note"] += " Update073: root read complete332 implementation/tests, verified12 final source/dependency identities and inspected actual70-pass receipts and numerical artifacts. Full244nt versus reported186nt gives186/244 full-query coverage and186/186 selected coverage; no selection stays null. Existing conditional function kernel gives0.8/0.2 and matched-census-adjusted2/7,5/7 for the synthetic example. These are field/function checks, not new annotation results. Assembly linkage_source saved validation is corrected; original failures remain. Multi-record FASTA sequence/description provenance is a missing shared capability being planned in337, and path-versus-semantic database census equality remains separately limited. R333/E336 are unfinished. No grader tally increment or live HPC claim."
    changes.append(dict(group="rows", id=row["id"], before=before, after=deepcopy(row)))
for row in status["resource_bindings"]:
    if row["id"] not in {key + "::hpc" for key in ids}:
        continue
    before = deepcopy(row)
    row["evidence_ids"].append(item["id"])
    changes.append(dict(group="resource_bindings", id=row["id"], before=before, after=deepcopy(row)))
assert len(changes) == 10
for group in ("rows", "resource_bindings"):
    affected = {c["id"] for c in changes if c["group"] == group}
    assert [r["id"] for r in status[group]] == [r["id"] for r in original[group]]
    assert all(a == b for a, b in zip(original[group], status[group]) if a["id"] not in affected)
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = dict(schema="tool_grader_progress_update_v1", date="2026-10-26", author="root",
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=[item],
    numerical_grader_progress_tally=deepcopy(previous["numerical_grader_progress_tally"]),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=205,
    completed_work=["M332 supplied-data field population and saved validators root reviewed against complete source/tests,70 passing cases and retained numerical examples."],
    unfinished_work=[*previous["unfinished_work"][1:]],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status["complete_scientific_tools_claimed"])
assert sha(STATUS) == before_sha and sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.073.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=5, updated_resource_bindings=5, scope_rows=308,
    numerical_grader_progress_tally=103, remaining_fixed_rows_outside_tally=205,
    new_status_sha256=sha(STATUS))))
