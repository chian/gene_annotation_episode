"""Export supplied-byte parser examples; this script never runs CodonTree.

Run with the repository's absolute .venv Python, staging cwd, and staging
PYTHONPATH. This verification exporter performs local file I/O; the four native
reader functions do not. Current syntax fixtures are source-derived, not live.
"""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import gene_annotation_episode.bvbrc_codon_tree_native as native


EVIDENCE = Path(__file__).resolve().parent
STAGING = EVIDENCE.parent / "staging"
REPOSITORY = EVIDENCE.parents[2]
GOAL = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert Path(sys.executable) == REPOSITORY / ".venv/bin/python"
assert Path.cwd() == STAGING
assert Path(native.__file__).resolve() == STAGING / "gene_annotation_episode/bvbrc_codon_tree_native.py"
assert hashlib.sha256(GOAL.read_bytes()).hexdigest() == "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"
CONTRACT = EVIDENCE.parent / "CODON_NATIVE_TABLES_CONTRACT.md"
assert hashlib.sha256(CONTRACT.read_bytes()).hexdigest() == "c6021e7c0d5870efd2a0da0af11c9e83f7869ae2b4ae20d8e5bf7f6da36b4ee4"

spec = importlib.util.spec_from_file_location("owned_native_tests", STAGING / "tests/test_bvbrc_codon_tree_native.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def write_json(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def identity(path):
    data = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data)}


examples = []
specifications = [
    ("historical_membership", "official_historical_native_output", fixtures.HISTORICAL_MEMBERSHIP.read_bytes(),
     native.parse_codon_membership, {"dialect": "pgfams_legacy"}, fixtures.HISTORICAL_MEMBERSHIP),
    ("current_membership", "source_derived_syntax_fixture", fixtures.CURRENT_MEMBERSHIP,
     native.parse_codon_membership, {"dialect": "homologs_current"}, None),
    ("current_family_statistics", "source_derived_syntax_fixture", fixtures.CURRENT_FAMILY_STATISTICS,
     native.parse_codon_family_statistics, {"dialect": "current_missing_header_tab"}, None),
    ("current_genome_counts", "source_derived_syntax_fixture", fixtures.CURRENT_GENOME_COUNTS,
     native.parse_codon_genome_counts, {}, None),
    ("current_analysis_statistics", "source_derived_syntax_fixture", fixtures.CURRENT_ANALYSIS_STATISTICS,
     native.parse_codon_analysis_statistics, {"dialect": "retained_current_source"}, None),
]
for name, source_kind, data, parser, options, original in specifications:
    input_path = original or EVIDENCE / (name + ".txt")
    if original is None:
        input_path.write_bytes(data)
    artifact = {"raw_artifact_ref": "raw/" + name, "source_ref": "source/" + name,
                "sha256": hashlib.sha256(data).hexdigest()}
    result = parser(data, artifact=artifact, **options)
    assert result["status"] == "ok"
    result_name = name + ".parsed.json"
    write_json(result_name, result)
    value = result["value"]
    examples.append({
        "name": name, "source_kind": source_kind, "input": identity(input_path),
        "parsed_result": identity(EVIDENCE / result_name), "artifact": artifact,
        "stored_physical_rows": len(value["table"]["rows"]),
        "typed_rows": len(value.get("rows", [])),
        "native_observation_count": len(value.get("observations", [])),
        "diagnostic_codes": [d["code"] for d in result["diagnostics"]],
    })

# Input-only handoff with unselected, independent fixtures. No fictitious common
# run or analysis is manufactured by joining these five separate examples.
envelope = {
    "parsed": {"store": {"alignments": [], "tree_documents": [], "partitions": [],
                          "phyloxml": [], "source_records": [], "native_tables": []}, "analyses": []},
    "raxml_runs": [], "membership": [], "family_statistics": [], "genome_counts": [], "analysis_statistics": [],
}
for name, _, _, parser, _, _ in specifications:
    value = json.loads((EVIDENCE / (name + ".parsed.json")).read_text())["value"]
    field = {native.parse_codon_membership: "membership", native.parse_codon_family_statistics: "family_statistics",
             native.parse_codon_genome_counts: "genome_counts", native.parse_codon_analysis_statistics: "analysis_statistics"}[parser]
    envelope[field].append(value)
    envelope["parsed"]["store"]["native_tables"].append(value["table"])
for field in ("membership", "family_statistics", "genome_counts", "analysis_statistics"):
    for reader_value in envelope[field]:
        matching = [t for t in envelope["parsed"]["store"]["native_tables"] if t["table_id"] == reader_value["table"]["table_id"]]
        assert len(matching) == 1 and matching[0] == reader_value["table"]
write_json("UNSELECTED_PROVIDER_INPUT_EXAMPLE.json", envelope)
write_json("POPULATED_EXAMPLES.json", examples)

source_dir = REPOSITORY / "verification/tool_graders_bvbrc_application_artifacts_2026-10-24/sources/codon_trees"
boundary = REPOSITORY / "verification/tool_graders_bvbrc_phylogeny_boundaries_2026-10-24"
write_json("SOURCE_AND_CODE_HASHES.json", [identity(path) for path in [
    GOAL, CONTRACT, EVIDENCE.parent / "NATIVE_METADATA_CONTRACT.md",
    boundary / "BOUNDARY_PROPOSAL.md", boundary / "CONTRACT_SHAPES.md",
    source_dir / "scripts/p3x-build-codon-tree.py", source_dir / "lib/phylocode.py",
    fixtures.HISTORICAL_MEMBERSHIP,
    STAGING / "gene_annotation_episode/bvbrc_codon_tree_native.py",
    STAGING / "tests/test_bvbrc_codon_tree_native.py", Path(__file__),
]])

tests = []
for path in sorted(EVIDENCE.glob("pytest-*.xml")):
    root = ET.parse(path).getroot()
    suite = root.find("testsuite")
    tests.append({
        "report": identity(path), "tests": int(suite.get("tests")), "failures": int(suite.get("failures")),
        "errors": int(suite.get("errors")), "skipped": int(suite.get("skipped")), "seconds": suite.get("time"),
        "failure_cases": [{"name": row.get("name"), "message": row.find("failure").get("message")}
                          for row in suite.findall("testcase") if row.find("failure") is not None],
    })
write_json("TEST_RUNS.json", {
    "python": str(sys.executable), "cwd": str(Path.cwd()), "module_path": native.__file__,
    "command": "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=" + str(STAGING) + " " + str(sys.executable)
               + " -m pytest -q -p no:cacheprovider tests/test_bvbrc_codon_tree_native.py --junitxml=../codon-native-verification/pytest-<run>.xml",
    "runs": tests,
    "initial_failure_resolution": "Three truncation-preservation assertions incorrectly expected the old artifact digest after appending bytes. The assertions now require the new digest while preserving earlier values and positions. No parser change was needed for those three failures.",
    "ancillary_command_failure": "git status returned exit 128: the workspace has no .git repository. No VCS command or production modification followed.",
    "current_native_table_live_execution": "not_run",
    "official_historical_membership": "complete_retained_native_bytes_tested",
    "provider_extractor_or_grader_execution": "not_run",
    "C4_selected_tool_result_dispatch": "not_run",
    "episode_typed_return_path": "not_run",
})
print(json.dumps({"examples": len(examples), "imported_module": native.__file__,
                  "test_runs": [{"tests": t["tests"], "failures": t["failures"], "report": Path(t["report"]["path"]).name} for t in tests]}))
