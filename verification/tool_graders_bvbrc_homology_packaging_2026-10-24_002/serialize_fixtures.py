"""Serialize labeled synthetic inputs; never used by the installed verifier.

The repository test module is used only to construct C4 test data. All scientific
calculations in this verification run happen separately from the extracted wheel.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_bvbrc_homology_bundle_adapter import (
    adapter, c4_fixture, encoded, program_document, refresh_metadata,
)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


previous = ROOT / "verification/tool_graders_bvbrc_homology_bundle_adapter_2026-10-24"
database = HERE / "retained_database"
database.mkdir()
copied = {}
for name in ("SYNTHETIC_INPUTS.json", "SYNTHETIC_RESULT.json", "SYNTHETIC_RECALCULATED_T1.json"):
    source = previous / name
    destination = database / ("EXPECTED_" + name if name != "SYNTHETIC_INPUTS.json" else name)
    shutil.copyfile(source, destination)
    copied[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()
shutil.copytree(previous / "native", database / "native")
for source in sorted((previous / "native").iterdir()):
    copied[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()

selections = {
    "hits": {"metric": "reported_hit_count", "report_index": 0},
    "query_length": {"metric": "query_length", "report_index": 0},
    "reference_length": {"metric": "reference_length", "report_index": 0, "hit_index": 0},
    "pairs": {"metric": "pairwise_distinct_pairs", "report_index": 0},
    "query_coverage": {"metric": "pairwise_query_coverage", "report_index": 0},
    "reference_coverage": {"metric": "pairwise_reference_coverage", "report_index": 0},
    "identity": {"metric": "pairwise_identity", "report_index": 0},
    "native_evalue": {"metric": "hsp_evalue", "report_index": 0, "hit_index": 0, "hsp_index": 0},
    "missing": {"metric": "missing_requirements"},
}
form = adapter.requested_form_schema(selections)
document = program_document("blastx")
truthful = c4_fixture(document, mode="pairwise_correspondence", extras=False)
contradictory = deepcopy(truthful)
contradictory[2][0]["value"]["subject_binding"]["sequence_sha256"] = "0" * 64
refresh_metadata(contradictory[0], contradictory[2], contradictory[3])
changed_evalue_document = deepcopy(document)
changed_evalue_document["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][0]["evalue"] = 1000000.0
changed_evalue = c4_fixture(changed_evalue_document, mode="pairwise_correspondence", extras=False)

case_manifest = {}
for name, fixture in (("pairwise_valid", truthful), ("pairwise_conflicting_subject_sha256", contradictory),
                      ("pairwise_evalue_only", changed_evalue)):
    destination = HERE / name
    destination.mkdir()
    native = destination / "native"
    native.mkdir()
    supplied_sources = destination / "supplied_sources"
    supplied_sources.mkdir()
    bundle, contents, values, parameters = fixture
    for index, value in enumerate(values):
        # These fixtures use complete JSON source values at the source root.
        assert value["evidence"]["pointer"] == ""
        body = encoded(value["value"])
        assert hashlib.sha256(body).hexdigest() == value["evidence"]["content"]["sha256"]
        assert len(body) == value["evidence"]["content"]["byte_count"]
        (supplied_sources / (str(index) + ".json")).write_bytes(body)
    save(destination / "SYNTHETIC_INPUTS.json", {
        "provenance": "SYNTHETIC corrected C4 blastx fixture; no live service or authenticated custody claim",
        "source_fixture": "tests/test_bvbrc_homology_bundle_adapter.py::c4_fixture(program_document('blastx'), mode='pairwise_correspondence', extras=False)",
        "case": name, "bundle": bundle, "supplied_values": values,
        "parameters": parameters, "requested_form": form,
    })
    native_hashes = {}
    for artifact in bundle["artifacts"]:
        body = contents[artifact["raw_artifact_ref"]]
        (native / (artifact["role"] + ".bytes")).write_bytes(body)
        native_hashes[artifact["role"]] = hashlib.sha256(body).hexdigest()
    case_manifest[name] = {"artifact_count": len(contents), "native_sha256": native_hashes,
                           "scientific_source": values[0]["evidence"],
                           "reference_source": values[1]["evidence"]}

sources = [ROOT / "tests" / name for name in (
    "test_bvbrc_homology_bundle_adapter.py", "test_bvbrc_homology_grader.py", "test_bvbrc_homology_inputs.py")]
save(HERE / "FIXTURE_PROVENANCE.json", {
    "description": "Inputs only; no adapter.consume_bundle or score calculator is called by this serializer.",
    "prior_retained_files_sha256": copied,
    "construction_source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
    "cases": case_manifest,
})
print(json.dumps({"status": "serialized", "pairwise_cases": list(case_manifest),
                  "database_expected_result_copied_as_comparison_only": True}, sort_keys=True))
