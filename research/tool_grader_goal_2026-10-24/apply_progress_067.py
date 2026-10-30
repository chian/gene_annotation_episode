"""Record reviewed field/function components without claiming finished tools."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_067.json"
P316 = "verification/tool_graders_blast_native_iteration_parser_2026-10-26_316/"
P319 = "verification/tool_graders_blast_pssm_master_port_2026-10-26_319/"
P320 = "verification/tool_graders_blast_iteration_target_context_2026-10-26_320/"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(path):
    return dict(path=path, sha256=sha(ROOT / path))


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = json.loads((HERE / "PROGRESS_UPDATE_066.json").read_text())
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
expected = {
    "gene_annotation_episode/blast_native_iteration_records.py": "e70be3ece3661aa4144a19e2e98e3f7bd235b17544f222f580345ba2b7c948d6",
    "gene_annotation_episode/blast_pssm_master_inputs.py": "021cb9c32f0dab90ae42986b125a467d5094e73faef7a7186c604ddc9ee8eba0",
    "gene_annotation_episode/blast_pssm_calculators.py": "59cddfe4ebe15f0b0c5368113a3a3669ca95e187d175eeaf1976c883f398bf3f",
    "gene_annotation_episode/blast_iteration_inputs.py": "84b78c47f07e3fecfa7edd1d5e1387aca52a76c674c36332bab826a8a0bb1446",
    "gene_annotation_episode/blast_iteration_calculators.py": "9a89bd78741f8a3e8807bf76f4f84a90ac66f6456b878d29ee2f36f2cfbf7fdd",
}
for path, digest in expected.items():
    assert sha(ROOT / path) == digest, path
policy = dict(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
for packet, label, output in ((P316, "check005", "91 passed"),
        (P319, "regression002", "236 passed"), (P319, "comparison001", '"mismatches": []'),
        (P320, "check002", "352 passed"), (P320, "examples001", '"exact_old_v1_replays": 10')):
    directory = ROOT / packet / label
    receipt = json.loads((directory / "receipt.json").read_text())
    assert receipt["returncode"] == 0 and receipt["policy"] == policy
    assert output in (directory / "stdout.txt").read_text()
for packet, directory in ((P316, "examples002"), (P320, "examples001")):
    base = ROOT / packet / directory
    manifest = json.loads((base / "MANIFEST.json").read_text())
    for row in manifest:
        path = base / row["path"]
        assert sha(path) == row["sha256"] and path.stat().st_size == row["size_bytes"]
    assert len(manifest) == (60 if packet == P316 else 9)
comparison = json.loads((ROOT / P319 / "calculator_comparison.json").read_text())
assert comparison["case_count"] == 53 and comparison["mismatches"] == []
baseline = comparison["baseline_identity"]
assert sha(ROOT / baseline["path"]) == baseline["sha256"]
examples = json.loads((ROOT / P319 / "metadata_examples.json").read_text())
assert len(examples) == 5
master = examples[0]["metadata"]["records"][0]["master"]
assert master["reported_length"] == master["decoded_length"] == len(master["column_to_residue"]) == 232
replay = json.loads((ROOT / P320 / "examples001/V1_REPLAY.json").read_text())
assert replay["exact_equal"] and len(replay["examples"]) == 10

paths = [P316 + p for p in ("ROOT_REVIEW_001.md", "HANDOFF_001.md", "check005/receipt.json", "examples002/MANIFEST.json")]
paths += [P319 + p for p in ("ROOT_REVIEW_001.md", "REPORT.md", "regression002/receipt.json", "calculator_comparison.json", "metadata_examples.json")]
paths += [P320 + p for p in ("HANDOFF_001.md", "check002/receipt.json", "SOURCE_HASHES.json", "examples001/MANIFEST.json", "examples001/V1_REPLAY.json")]
paths += ["verification/tool_graders_native_blast_database_result_contract_2026-10-26_314/" + p
          for p in ("CONTRACT_ADDENDUM_002.md", "CONTRACT_ADDENDUM_003.md", "CONTRACT_ADDENDUM_004.md", "CONTRACT_ADDENDUM_005.md")]
evidence = dict(id="BLAST-INPUT-EXTRACTION-PORTS-067", kind="reviewed_field_definition_and_population_function_components",
    reports=[descriptor(path) for path in paths + list(expected)],
    summary="Query-only native positive-message extractor, shared PSSM master extractor and per-search target input/calculation port reviewed and verified.",
    qualification="Tests use source-derived synthetic reports and retained upstream PSSM inputs. Full native execution/episode integration is unfinished; overlapping test suites are not added as distinct counts.")
assert not any(row["id"] == evidence["id"] for row in status["verification_evidence"])
status["verification_evidence"].append(evidence)
changes = []
for mode in ("psiblast", "deltablast"):
    row = next(r for r in status["rows"] if r["id"] == "A-L070-" + mode + "-database")
    before = deepcopy(row)
    row["numerical_sheet"] += "_per_search_target_context_v2_added"
    row["metadata_extractor"] = "query_only_positive_marker_and_public_pssm_master_extractors_tested_native_fixture_acquisition_and_result_binding_pending"
    row["deterministic_calculator"] = "existing_sequence_profile_pssm_iteration_calculations_preserved_per_search_target_context_composition_verified"
    row["numerical_verification"] = "352_iteration_sequence_profile_parser_tests_and236_pssm_port_tests_overlap_three_new_target_examples_ten_v1_replays_53_pssm_comparisons_unchanged"
    row["evidence_ids"].append(evidence["id"])
    row["note"] += " Update067: field definitions and deterministic population functions for native positive messages, PSSM masters and per-search target context are implemented and reviewed. Filled sheets are test outputs. Collector control-line count correction, M/R integration, HPC/result/typed-return wiring and actual native execution remain unfinished. No numerical-grader tally increment."
    changes.append(dict(group="rows", id=row["id"], before=before, after=deepcopy(row)))
affected = {r["id"] for r in changes}
assert [r["id"] for r in status["rows"]] == [r["id"] for r in original["rows"]]
assert all(a == b for a, b in zip(original["rows"], status["rows"]) if a["id"] not in affected)
assert status["resource_bindings"] == original["resource_bindings"]
assert sha(HERE / "SCOPE.json") == scope_sha
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = dict(schema="tool_grader_progress_update_v1", date="2026-10-26",
    recorded_at=datetime.now(timezone.utc).isoformat(), author="root",
    previous_status_sha256=before_sha, new_status_sha256=hashlib.sha256(raw).hexdigest(),
    scope_sha256_unchanged=scope_sha, scope_changes=[], changes=changes, added_evidence=[evidence],
    numerical_grader_progress_tally=dict(before=99, after=99, added_row_ids=[],
        meaning="Reviewed extraction/input components do not complete additional scientific tools."),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=209,
    completed_work=["316 query-only positive-message extraction fields/function reviewed; 91 parser tests pass.",
        "319 shared PSSM master extraction port reviewed; 236-test regression and53-case unchanged-calculator comparison pass.",
        "320 per-search target fields/population/calculation connection verified; 352-test regression,three complete examples andten identical v1 replays.",
        "Exact M/R interfaces for report addresses, partial lowering, canonical calculation identities, reuse and exception diagnostics defined additively."],
    unfinished_work=["317 metadata and318 numerical worker/views are in integration testing; root has not accepted their final implementations.",
        "Fresh321 is implementing selected HPC execution, capture, frozen publication and authenticated immediate-child returns under314.",
        "Standalone native convergence control-line count correction and extractor-to-result wiring remain unfinished.",
        "Actual native mode searches/deployment/access, authentic positive-message fixtures and complete native membership data remain unavailable or unverified.",
        "The remaining fixed308-row scope remains unchanged; literature graders and W05 stay outside this goal."],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status["complete_scientific_tools_claimed"])
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.067.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_rows=2, scope_rows=308, resource_bindings=288,
    numerical_grader_progress_tally=99, new_status_sha256=sha(STATUS))))
