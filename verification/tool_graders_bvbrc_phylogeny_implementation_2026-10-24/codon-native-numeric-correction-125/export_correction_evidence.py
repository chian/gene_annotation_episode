"""Export supplied-byte counterexamples and additive verification identities.

This evidence script performs local file I/O. The imported readers operate on
supplied bytes only. No scientific program, service or model is invoked.
"""

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import gene_annotation_episode.bvbrc_codon_tree_native as native
import gene_annotation_episode.phylogeny_format_contracts as formats


EVIDENCE = Path(__file__).resolve().parent
IMPLEMENTATION = EVIDENCE.parent
STAGING = IMPLEMENTATION / "staging"
REPOSITORY = EVIDENCE.parents[2]
PRIOR = IMPLEMENTATION / "codon-native-verification"
GOAL = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
CONTRACT = IMPLEMENTATION / "CODON_NATIVE_TABLES_CONTRACT.md"


def identity(path):
    data = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data)}


def write_json(name, value):
    with (EVIDENCE / name).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


assert Path(sys.executable) == REPOSITORY / ".venv/bin/python"
assert Path.cwd() == STAGING
assert Path(native.__file__).resolve() == STAGING / "gene_annotation_episode/bvbrc_codon_tree_native.py"
assert Path(formats.__file__).resolve() == STAGING / "gene_annotation_episode/phylogeny_format_contracts.py"
assert identity(GOAL)["sha256"] == "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"
assert identity(CONTRACT)["sha256"] == "c6021e7c0d5870efd2a0da0af11c9e83f7869ae2b4ae20d8e5bf7f6da36b4ee4"

test_path = STAGING / "tests/test_bvbrc_codon_tree_native.py"
spec = importlib.util.spec_from_file_location("codon_correction_test_fixtures", test_path)
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)

labels = ("baseline-101", "regression-before-correction", "corrected-159")
receipts = [json.loads((EVIDENCE / (label + ".json")).read_text()) for label in labels]
prior_identities = receipts[0]["prior_receipt_identities"]
assert all(receipt["prior_receipt_identities"] == prior_identities for receipt in receipts)
assert all(identity(Path(row["path"])) == row for row in prior_identities)
baseline_nodes = set(receipts[0]["collected_nodeids"])
final_nodes = set(receipts[-1]["collected_nodeids"])
assert len(baseline_nodes) == 101 and len(final_nodes) == 159
assert baseline_nodes <= final_nodes
assert set(receipts[1]["collected_nodeids"]) == final_nodes

runs = []
for receipt in receipts:
    report = ET.parse(receipt["report"]["path"]).getroot().find("testsuite")
    failures = [{"name": row.get("name"), "message": row.find("failure").get("message")}
                for row in report.findall("testcase") if row.find("failure") is not None]
    runs.append({
        "label": receipt["label"], "exit_code": receipt["exit_code"],
        "tests": int(report.get("tests")), "failures": int(report.get("failures")),
        "errors": int(report.get("errors")), "skipped": int(report.get("skipped")),
        "seconds": report.get("time"), "failure_cases": failures,
        "receipt": identity(EVIDENCE / (receipt["label"] + ".json")),
        "junit": identity(Path(receipt["report"]["path"])),
    })
assert [(r["tests"], r["failures"], r["errors"]) for r in runs] == [(101, 0, 0), (159, 21, 0), (159, 0, 0)]

data = fixtures.FAMILY_HEADER + (
    "F_underflow\t0\t1e-999\t-0e-999\t3\t2\tna\tTrue\n"
    "bad seqs: {'valid': 9.0, 'tiny': -1e-999}\n"
    "F_small\t0\t5e-324\t-2.5\t3\t2\t+0\tFalse\n"
    "bad seqs: {'explicit_negative_zero': -0.000e-999, 'smallest_nonzero': 5e-324, 'signed': +9.5}\n"
).encode()
supplied = fixtures.artifact(data, "raw/codon-numeric-boundary-counterexample")
before = deepcopy(supplied)
result = fixtures.families(data, artifact=supplied)
assert result["status"] == "partial" and supplied == before
assert [(o["raw_token"], o["value"], o["state"]) for o in result["value"]["observations"]][1:3] == [
    ("1e-999", None, "failed"), ("-0e-999", -0.0, "available"),
]
assert result["value"]["observations"][5]["state"] == "missing"
assert result["value"]["rows"][0]["bad_sequence_values"] == []
assert result["value"]["rows"][1]["bad_sequence_values"] == [
    {"genome_id": "explicit_negative_zero", "value": -0.0},
    {"genome_id": "smallest_nonzero", "value": 5e-324},
    {"genome_id": "signed", "value": 9.5},
]
for record in result["value"]["table"]["rows"] + result["value"]["observations"]:
    location = record["location"]
    assert location["artifact"] == supplied
    start, end = location["byte_start_0based"], location["byte_end_0based_exclusive"]
    assert data[start:end].decode() == record.get("raw_text", record.get("raw_token"))
    assert location["line_start_1based"] == data[:start].count(b"\n") + 1
with (EVIDENCE / "numeric-boundary-counterexample.txt").open("xb") as stream:
    stream.write(data)
write_json("numeric-boundary-counterexample.parsed.json", result)

hash_examples = []
for parse, content, name in fixtures.PARSERS:
    supplied = fixtures.artifact(content)
    supplied["sha256"] = supplied["sha256"].upper()
    before = deepcopy(supplied)
    invalid = parse(content, artifact=supplied)
    assert supplied == before
    assert invalid["status"] == "invalid" and invalid["value"] is None
    assert fixtures.codes(invalid) == {"codon_artifact_invalid"}
    hash_examples.append({"parser": name, "supplied_artifact": supplied,
                          "caller_metadata_unchanged": supplied == before, "read_result": invalid})
write_json("UPPERCASE_HASH_EXAMPLES.json", hash_examples)

# Reparse the old retained specimens and compare with their saved values. The
# original receipts/artifacts are read only and retain their original hashes.
replayed = []
for example in json.loads((PRIOR / "POPULATED_EXAMPLES.json").read_text()):
    name = example["name"]
    if name == "historical_membership":
        parse, options = native.parse_codon_membership, {"dialect": "pgfams_legacy"}
    else:
        parse, options = {
            "current_membership": (native.parse_codon_membership, {"dialect": "homologs_current"}),
            "current_family_statistics": (native.parse_codon_family_statistics, {"dialect": "current_missing_header_tab"}),
            "current_genome_counts": (native.parse_codon_genome_counts, {}),
            "current_analysis_statistics": (native.parse_codon_analysis_statistics, {"dialect": "retained_current_source"}),
        }[name]
    content = Path(example["input"]["path"]).read_bytes()
    parsed = parse(content, artifact=example["artifact"], **options)
    expected = json.loads(Path(example["parsed_result"]["path"]).read_text())
    assert parsed == expected
    replayed.append({"name": name, "source_kind": example["source_kind"],
                     "artifact": example["artifact"], "unchanged_parsed_result": True,
                     "stored_physical_rows": len(parsed["value"]["table"]["rows"]),
                     "typed_rows": len(parsed["value"].get("rows", []))})

original_runs = json.loads((PRIOR / "TEST_RUNS.json").read_text())
summary = {
    "scope": "Two staged native-reader review corrections; no scientific execution, production integration or score changes.",
    "new_runs": runs,
    "new_test_count": len(final_nodes - baseline_nodes),
    "all_prior_test_nodes_retained": True,
    "corrected_prior_expectation": "Four parameter cases now reject uppercase supplied hashes; the prior test expected acceptance contrary to shared ArtifactRef.",
    "pre_correction_failures": {"float_underflow": 6, "scalar_map_underflow": 9,
                                "hash_contract": 6, "total": 21,
                                "in_corrected_prior_tests": 4, "in_added_tests": 17},
    "historical_prior_workload_runs": original_runs["runs"],
    "historical_prior_failure_resolution": original_runs["initial_failure_resolution"],
    "ancillary_exporter_failure": json.loads((EVIDENCE / "exporter-initial-failure.json").read_text()),
    "prior_receipts_unchanged": True, "prior_receipt_count": len(prior_identities),
    "replayed_prior_examples": replayed,
    "numeric_example": {"source_kind": "synthetic_boundary_counterexample_using_source_derived_table_syntax",
                        "input": identity(EVIDENCE / "numeric-boundary-counterexample.txt"),
                        "parsed": identity(EVIDENCE / "numeric-boundary-counterexample.parsed.json"),
                        "artifact": fixtures.artifact(data, "raw/codon-numeric-boundary-counterexample"),
                        "observations": [{"field": o["field"], "subject_id": o["subject_id"],
                                          "raw_token": o["raw_token"], "value": o["value"], "state": o["state"]}
                                         for o in result["value"]["observations"]]},
    "verification_limits": {
        "current_native_table_live_execution": "not_run",
        "upstream_scientific_program_import_or_execution": "not_run",
        "provider_extractor_or_grader_execution": "not_run",
        "C4_selected_tool_result_dispatch": "not_run",
        "episode_typed_return_path": "not_run",
    },
}
write_json("VALIDATION.json", summary)
source = REPOSITORY / "verification/tool_graders_bvbrc_application_artifacts_2026-10-24/sources/codon_trees"
boundary = REPOSITORY / "verification/tool_graders_bvbrc_phylogeny_boundaries_2026-10-24"
write_json("SOURCE_AND_CODE_HASHES.json", [identity(path) for path in [
    GOAL, CONTRACT, IMPLEMENTATION / "NATIVE_METADATA_CONTRACT.md",
    boundary / "BOUNDARY_PROPOSAL.md", boundary / "CONTRACT_SHAPES.md",
    source / "scripts/p3x-build-codon-tree.py", source / "lib/phylocode.py",
    Path(native.__file__), test_path, Path(formats.__file__),
    EVIDENCE / "run_verification.py", Path(__file__),
]])
print(json.dumps({"tests": runs[-1]["tests"], "failures": runs[-1]["failures"],
                  "new_tests": summary["new_test_count"], "prior_receipts_unchanged": True,
                  "replayed_examples": len(replayed),
                  "module_sha256": identity(Path(native.__file__))["sha256"],
                  "tests_sha256": identity(test_path)["sha256"]}))
