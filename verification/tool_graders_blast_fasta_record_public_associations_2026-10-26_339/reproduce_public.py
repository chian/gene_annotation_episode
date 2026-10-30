"""Direct public boundary using unchanged retained synthetic M332 source bytes.

This does not call or certify the future M v2 validator, worker or E path.
"""
from copy import deepcopy
import builtins
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

from gene_annotation_episode.blast_fasta_record_identity import parse_blast_fasta_source_records
from gene_annotation_episode.blast_sequence_database import (
    populate_blast_sequence_database_sheet as populate,
    calculate_blast_sequence_database_components as calculate,
)
from gene_annotation_episode.blast_database_grader import calculate_database_probabilities

ROOT = Path(__file__).resolve().parents[2]
OUT = Path.cwd()
OLD = ROOT / "verification/tool_graders_blast_fasta_record_identity_plan_2026-10-26_337/check001"
BASE = ROOT / "verification/tool_graders_standard_blast_database_metadata_2026-10-26_332/check009/temporary/pytest"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def read_case(name):
    folder = BASE / name
    original, inventory = {}, []
    for name in ("supplied_inputs.json", "sheets.json", "components.json"):
        raw = (folder / name).read_bytes()
        inventory.append(dict(path=str(folder / name), sha256=sha(raw), size_bytes=len(raw)))
        original[name] = json.loads(raw)
    return original, inventory


old, old_hashes = read_case("test_M3_multiple_fasta_records0")
baseline, baseline_hashes = read_case("test_M1_real_standard_job_publ0")
supplied = old["supplied_inputs.json"]
assert supplied["evidence"] == "synthetic_only_not_native_database_measurements"
original_sheet = old["sheets.json"]["sequence"][0]["sheet"]
assert calculate(original_sheet) == old["components.json"]
direct_v1 = json.loads((OLD / "direct_public303_sheet.json").read_bytes())
assert calculate(direct_v1) == json.loads((OLD / "direct_public303_components.json").read_bytes())
assert calculate(baseline["sheets.json"]["sequence"][0]["sheet"]) == baseline["components.json"]

contents = {k:bytes.fromhex(v) for k,v in supplied["contents_hex"].items()}
fasta = contents["artifact-sequence-meta-records"]
assignments = contents["artifact-metadata"]
assert sha(fasta) == "84ae36a79e704b527256bdd454f360535de0517c7a7dffdf7927b4f67026aacc"
assert sha(assignments) == "98ac0d4aff3046d7cbf0d7a1db306674073549e60fd6a30844aaead894c3a7be"
records = parse_blast_fasta_source_records(fasta)
assert [r["record_ordinal"] for r in records["records"]] == [0,1]
assert all(r["status"] == "available" for r in records["records"])
save("parsed_original_fasta.json", records)
(OUT / "retained_inputs").mkdir()
for key, name in (("artifact-sequence-meta-records","original.fa"), ("artifact-metadata","original_assignments.json"),
                  ("artifact-report","original_report.json"), ("artifact-sequence-meta-links","original_links.json")):
    (OUT / "retained_inputs" / name).write_bytes(contents[key])

# Construct NEW explicitly versioned input, with no source aliases or invented
# FASTA pointers. The separate assignment document has its exact original bytes.
payload = json.loads(assignments)
payload["schema"] = "native_blast_database_sequence_metadata_v2"
payload["documents"].append(dict(document_key="original-supplied-assignments", format="json",
    artifact=dict(kind="received", source_ref="source-metadata", artifact_ref="artifact-metadata",
                  sha256=sha(assignments), size_bytes=len(assignments))))
for ordinal, row in enumerate(payload["searches"][0]["reference_metadata"]):
    row["record_locator"] = dict(kind="fasta_record", record_ordinal=ordinal)
    row["functions"][0]["source"] = "original-supplied-assignments"
    payload["searches"][0]["description_bindings"][ordinal]["binding"]["metadata_record_locator"] = deepcopy(row["record_locator"])
    payload["searches"][0]["sequence_identity_bindings"][ordinal]["binding"]["record_locator"] = deepcopy(row["record_locator"])
raw_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
(OUT / "new_wire_payload_v2.json").write_bytes(raw_payload)
descriptor = dict(input_key="metadata-v2-339", consumer="sequence_database", schema_id=payload["schema"],
    artifact_ref="artifact-metadata-v2-339", sha256=sha(raw_payload), size_bytes=len(raw_payload), origin="selected_results_input")
save("new_descriptor_v2.json", descriptor)
save("new_input_artifact_identity.json", dict(source_ref="source-metadata-v2-339", **{k:descriptor[k] for k in ("artifact_ref","sha256","size_bytes")}))

# Supply exact scientific rows directly. This is deliberately not presented as
# metadata-validator output; M owns source/format/proof qualification.
arguments = deepcopy(direct_v1)
arguments.pop("schema")
provenance = []
for ordinal, row in enumerate(arguments["reference_metadata"]):
    locator = dict(kind="fasta_record", record_ordinal=ordinal)
    row["record_locator"] = deepcopy(locator)
    row["functions"][0]["source"] = "source-metadata"
    arguments["description_bindings"][ordinal]["binding"]["metadata_record_locator"] = deepcopy(locator)
    binding = arguments["sequence_identity_bindings"][ordinal]["binding"]
    binding["record_locator"] = deepcopy(locator)
    parsed = records["records"][ordinal]
    assert binding["digest"] == parsed["sequence_sha256"] and binding["sequence_length"] == parsed["sequence_length"]
    assignment = json.loads(assignments)["searches"][0]["reference_metadata"][ordinal]["functions"][0]
    assert assignment["function"] == row["functions"][0]["function"]
    provenance.append(dict(function=assignment["function"], source_ref="source-metadata",
        artifact_ref="artifact-metadata", pointer=f"/searches/0/reference_metadata/{ordinal}/functions/0",
        original_assertion=assignment, scientific_row=row["functions"][0]))
save("function_assignment_provenance.json", provenance)
save("public_inputs_v2.json", arguments)
sheet = populate(**arguments)
out = calculate(sheet)
assert sheet["schema"] == "blast_sequence_database_result_sheet_v2"
database = out["components"]["database_sheet"]
assert database["schema"] == "blast_database_sheet_v2" and database["association_mode"] == "explicit_bindings_v2"
assert database["coverage"]["matched_metadata_row_count"] == 2
assert [g["maximum_bit_score"] for g in database["sequence_groups"]] == [20,18]
weights = out["components"]["function_weights"]
assert weights["function_masses"] == {"F":1,"G":.25}
assert weights["unadjusted_probabilities"] == {"F":.8,"G":.2}
for hit, valid_hit in zip(database["hits"], baseline["components.json"]["components"]["database_sheet"]["hits"]):
    assert hit["measurements"] == valid_hit["measurements"]
    assert hit["hsp_components"] == valid_hit["hsp_components"]
save("public_sheet_v2.json", sheet)
save("public_components_v2_T1.json", out)

reopened = json.loads(json.dumps(sheet))
before = deepcopy(reopened)
def forbidden(*args, **kwargs):
    raise AssertionError("public saved calculation must not acquire, execute or reprove FASTA")
with patch("builtins.open", forbidden), patch("io.open", forbidden), patch.object(Path,"read_bytes",forbidden), \
     patch.object(Path,"read_text",forbidden), patch.object(socket,"socket",forbidden), \
     patch.object(socket,"create_connection",forbidden), patch.object(subprocess,"Popen",forbidden), \
     patch.object(subprocess,"run",forbidden), \
     patch("gene_annotation_episode.blast_fasta_record_identity.parse_blast_fasta_source_records", forbidden), \
     patch("gene_annotation_episode.domain.parse_sequences", forbidden), \
     patch("gene_annotation_episode.blast_grading_inputs.parse_blast_json", forbidden), \
     patch("gene_annotation_episode.blast_report_collection.parse_blast_report_collection", forbidden):
    assert populate(**arguments) == sheet
    t2 = calculate(reopened, model={"temperature_bits":2})
    direct_weights = calculate_database_probabilities(database, model={"temperature_bits":2})
assert reopened == before
assert t2["components"]["function_weights"] == direct_weights
assert direct_weights["unadjusted_probabilities"] == {"F":2/3,"G":1/3}
save("public_components_v2_T2.json", t2)

census_args = deepcopy(arguments)
census_args["database_profile"] = baseline["sheets.json"]["sequence"][0]["sheet"]["database_profile"]
census_raw = bytes.fromhex(baseline["supplied_inputs.json"]["contents_hex"]["artifact-sequence-meta-census"])
(OUT / "retained_inputs/original_census.json").write_bytes(census_raw)
census = calculate(populate(**census_args))
assert census["components"]["function_weights"]["representation_adjusted_probabilities"] == {"F":2/7,"G":5/7}
save("public_inputs_v2_with_census.json", census_args)
save("public_components_v2_with_census.json", census)
no_assignments = deepcopy(arguments)
for row in no_assignments["reference_metadata"]:
    row["functions"] = []
unassigned = calculate(populate(**no_assignments))
assert unassigned["components"]["function_weights"]["unadjusted_probabilities"] is None
assert unassigned["components"]["database_sheet"]["coverage"]["matched_metadata_row_count"] == 2
save("public_inputs_v2_without_functions.json", no_assignments)
save("public_components_v2_without_functions.json", unassigned)

inventory = old_hashes + baseline_hashes
assert all(sha(Path(row["path"]).read_bytes()) == row["sha256"] for row in inventory)
summary = dict(evidence="retained_synthetic_only_not_native_database_measurements", original_hashes=inventory,
    v1_saved_failure_value_identical=True, v1_direct_counterexample_value_identical=True,
    v1_valid_json_baseline_value_identical=True, original_fasta_sha256=sha(fasta), original_fasta_size_bytes=len(fasta),
    original_record_ordinals=[0,1], matched_metadata_rows=database["coverage"]["matched_metadata_row_count"],
    bit_scores=[20,18], T1_masses=weights["function_masses"], T1_weights=weights["unadjusted_probabilities"],
    T2_weights=direct_weights["unadjusted_probabilities"],
    census_weights=census["components"]["function_weights"]["representation_adjusted_probabilities"],
    no_function_weights=unassigned["components"]["function_weights"]["unadjusted_probabilities"],
    geometry_value_identical_to_valid_json_baseline=True, forbidden_io_recalculation=True,
    new_wire_payload_validation="not_run_pending_M_v2_implementation", full_worker_and_episode_path="not_run_by_339")
save("summary.json", summary)
print(json.dumps(summary, indent=2))
