"""Record the verified collector correction without increasing finished-tool totals."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_068.json"
PACKET = ROOT / "verification/tool_graders_blast_tabular_control_lines_2026-10-26_322"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def descriptor(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path))


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = read(HERE / "PROGRESS_UPDATE_067.json")
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
for row in read(PACKET / "SOURCE_HASHES.json"):
    path = ROOT / row["path"]
    assert sha(path) == row["sha256"] and path.stat().st_size == row["size_bytes"]
policy = dict(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
for label, text in (("check001", "43 passed"), ("check002", "470 passed"),
                    ("examples001", '"all_extractor_results_unchanged": true')):
    receipt = read(PACKET / label / "receipt.json")
    assert receipt["returncode"] == 0 and receipt["policy"] == policy
    assert text in (PACKET / label / "stdout.txt").read_text()
examples = PACKET / "examples001"
manifest = read(examples / "MANIFEST.json")
assert len(manifest) == 40
for row in manifest:
    path = examples / row["path"]
    assert sha(path) == row["sha256"] and path.stat().st_size == row["size_bytes"]
sources = read(examples / "ORIGINAL_SOURCES.json")
assert sources["verified_before_and_after"] and len(sources["files"]) == 60
for row in sources["files"]:
    path = Path(sources["directory"]) / row["path"]
    assert sha(path) == row["sha256"] and path.stat().st_size == row["size_bytes"]
summary = read(examples / "NUMERICAL_SUMMARY.json")
assert len(summary) == 10 and all(r["extractor_unchanged"] for r in summary)
for name in ("psi_positive", "delta_positive"):
    row = next(r for r in summary if r["example"] == name)
    assert row["before_counts"][0]["observed_hsp_count"] == 3
    assert set(row["after_counts"][0].values()) == {2}
    assert row["query_native_converged"] == [True] and row["search_native_converged"] == [None]

files = [PACKET / name for name in ("CONTRACT_001.md", "HANDOFF_001.md", "SOURCE_HASHES.json",
    "check001/receipt.json", "check002/receipt.json", "examples001/receipt.json",
    "examples001/MANIFEST.json", "examples001/NUMERICAL_SUMMARY.json", "examples001/ORIGINAL_SOURCES.json")]
files += [ROOT / row["path"] for row in read(PACKET / "SOURCE_HASHES.json")]
evidence = dict(id="BLAST-COLLECTOR-CONTROL-LINES-068", kind="verified_native_parser_field_population_correction",
    reports=[descriptor(path) for path in files],
    summary="Supported source-defined PSI/DELTA convergence messages remain in original text and bytes but no longer populate alignment rows/counts.",
    qualification="470 regression cases include43 focused cases. Ten retained source-derived synthetic cases produce40 new verification artifacts;60 originals and all separate extractor results are unchanged. No native search or complete episode-path claim.")
assert not any(row["id"] == evidence["id"] for row in status["verification_evidence"])
status["verification_evidence"].append(evidence)
changes = []
for mode in ("psiblast", "deltablast"):
    row = next(r for r in status["rows"] if r["id"] == "A-L070-" + mode + "-database")
    before = deepcopy(row)
    row["native_parser"] = "shared_tabular7_control_line_classification_corrected_and_verified_authentic_mode_native_search_pending"
    row["numerical_verification"] += "_470_collector_and_consumer_regressions_ten_new_retained_byte_interpretations"
    row["evidence_ids"].append(evidence["id"])
    row["note"] += " Update068: shared collector field-population function corrected and verified; two alignments plus a supported control message now yield two observed/reported rows. Forty new test artifacts retain ten complete interpretations; all60 original files and separate extractor outputs are unchanged. M/R/E integration remains under review and testing; full result-path and live execution are not claimed. No tally increment."
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
        meaning="A corrected parser component does not complete additional scientific tools."),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=209,
    completed_work=["322 exact control-line parser correction verified by470 cases and ten retained-byte examples; original records preserved."],
    unfinished_work=["317 is implementing007 source-locator qualification; final connected review/tests remain.",
        "318's field/calculation/view functions passed67 tests; root review and stable-M007 connected verification remain.",
        "321 is testing actual selected HPC child, capture, preparation, numerical returns and scientific observation consumers; complete path not yet verified.",
        "Fresh323 owns the exact registered-fact communication repair; no generic form grammar relaxation is authorized.",
        "316 convergence extraction still needs the exact complete result-path connection; authentic native positive fixtures/live HPC execution remain unverified.",
        "The fixed308-row scope is unchanged; remaining required tool families, literature exclusions and separate W05 boundary are preserved."],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status["complete_scientific_tools_claimed"])
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.068.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_rows=2, scope_rows=308, resource_bindings=288,
    numerical_grader_progress_tally=99, new_status_sha256=sha(STATUS))))
