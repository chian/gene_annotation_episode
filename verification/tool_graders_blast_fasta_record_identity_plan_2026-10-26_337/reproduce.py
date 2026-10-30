"""Planning evidence only: retained synthetic bytes, existing public consumers."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from gene_annotation_episode import native_blast_standard_database_metadata as metadata
from gene_annotation_episode import native_blast_standard_database_calculators as calculators
from gene_annotation_episode import native_blast_database_metadata as public_metadata
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from gene_annotation_episode.blast_sequence_database import (
    populate_blast_sequence_database_sheet, calculate_blast_sequence_database_components,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = Path.cwd()
BASE = ROOT / "verification/tool_graders_standard_blast_database_metadata_2026-10-26_332/check009/temporary/pytest"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def load(name):
    folder = BASE / name
    original = {}
    hashes = []
    for filename in ("supplied_inputs.json", "sheets.json", "components.json"):
        raw = (folder / filename).read_bytes()
        hashes.append(dict(path=str(folder / filename), sha256=digest(raw), size_bytes=len(raw)))
        original[filename] = json.loads(raw)
    supplied = original["supplied_inputs.json"]
    assert supplied["evidence"] == "synthetic_only_not_native_database_measurements"
    inputs = supplied["inputs"]
    inputs["contents"] = {k: bytes.fromhex(v) for k, v in supplied["contents_hex"].items()}
    inputs["subject_contents"] = {k: bytes.fromhex(v) for k, v in supplied["subject_contents_hex"].items()}
    return inputs, original["sheets.json"], original["components.json"], hashes


inputs, original_sheets, original_components, hashes = load("test_M3_multiple_fasta_records0")
before = deepcopy(inputs)
prepared = metadata.prepare_standard_blast_database_inputs(**inputs)
reports = [r for r in inputs["artifact_catalog"]["entries"] if r["role"] == "primary_report"]
collection = parse_blast_report_collection(
    {r["artifact_key"]: inputs["contents"][r["artifact_ref"]] for r in reports},
    artifacts=[dict(artifact_key=r["artifact_key"], role=r["role"], format=r["format"],
        fields=None if r["format"] == "json15" else r["fields"], delimiter=r["delimiter"]) for r in reports],
    invocation=prepared["invocation"])
sheets = metadata.populate_standard_blast_database_sheets(collection, prepared_inputs=prepared)
metadata.validate_standard_blast_database_sheet_set(sheets)
components = calculate_blast_sequence_database_components(sheets["sequence"][0]["sheet"])
assert sheets == original_sheets
assert components == original_components
assert inputs == before

proofs = sheets["prepared_inputs"]["sequence_proofs"]
assert [p["proof"]["record_ordinal"] for p in proofs] == [0, 1]
assert [p["status"] for p in proofs] == ["available", "available"]
assert sheets["sequence"][0]["sheet"]["sequence_identity_bindings"] == []

# Supply the already-proven, unchanged original links directly to public303.
# No aliases, JSON pointers, sequence fields, scores, or source bytes are invented.
arguments = deepcopy(sheets["sequence"][0]["sheet"])
arguments.pop("schema")
arguments["sequence_identity_bindings"] = [deepcopy(p["binding"]) for p in proofs]
direct_sheet = populate_blast_sequence_database_sheet(**arguments)
direct = calculate_blast_sequence_database_components(direct_sheet)
codes = sorted({r["code"] for r in direct["issues"]})
assert "blast_sequence_binding_source_identity_conflict" in codes
assert "blast_description_binding_metadata_record_conflict" in codes
assert direct["components"]["function_weights"]["unadjusted_probabilities"] is None

full = calculators.calculate_standard_blast_database_sheets(sheets, sequence_model=None)
rows = calculators.build_standard_blast_database_rows(bundle_identity=inputs["bundle"]["identity"],
    calculation_id="0" * 64, sheet_set=sheets, calculations=full)
assert full["sequence"][0]["components"] == original_components

# Existing v1 accepts no arbitrary ordinal field. A nonempty FASTA pointer is
# also rejected by the actual public wire validator, before any calculation.
validation = prepared["metadata"][0]
documents = []
for document in validation["normalized"]["documents"]:
    documents.append(dict(document, contents=inputs["contents"][document["artifact_ref"]]))
primary = [{k: r[k] for k in ("output_key", "artifact_key", "artifact_ref", "source_ref", "sha256", "size_bytes", "format")} for r in reports]
invalids = {}
for case in ("new_ordinal_field", "fictional_fasta_json_pointer"):
    payload = deepcopy(validation["payload"])
    b = payload["searches"][0]["sequence_identity_bindings"][0]["binding"]
    if case == "new_ordinal_field":
        b["source_record"] = {"kind": "fasta_record", "record_ordinal": 0}
    else:
        b["pointer"] = "/records/0"
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    descriptor = dict(validation["descriptor"], sha256=digest(raw), size_bytes=len(raw))
    catalog = dict(descriptor=descriptor, documents=documents, primary_reports=primary,
        bundle_source_ref=inputs["artifact_catalog"]["bundle_source_ref"],
        bundle_artifact_ref=inputs["artifact_catalog"]["bundle_artifact_ref"])
    result = public_metadata.validate_native_blast_database_metadata_payload(payload,
        descriptor=descriptor, document_catalog=catalog, job=inputs["job"])
    assert result["status"] == "invalid"
    invalids[case] = result

baseline_inputs, baseline_sheets, baseline_components, baseline_hashes = load("test_M1_real_standard_job_publ0")
baseline = calculate_blast_sequence_database_components(baseline_sheets["sequence"][0]["sheet"])
assert baseline == baseline_components
assert baseline["components"]["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}

summary = dict(evidence="retained_synthetic_only_not_native_database_measurements",
    original_hashes=hashes, baseline_hashes=baseline_hashes,
    exact_current_reproduction=True, unchanged_inputs=True,
    fasta_sources=[dict(document=p["document"], proof=p["proof"], symbols=p["symbols"],
        binding=p["binding"], raw_text=inputs["contents"][p["document"]["artifact_ref"]].decode()) for p in proofs],
    standard_qualification_details=[i["detail_code"] for i in sheets["metadata_binding_results"][0]["issues"]],
    direct_public303_codes=codes,
    direct_public303_group_count=direct["components"]["database_sheet"]["dependence"]["group_count"],
    direct_public303_groups=direct["components"]["database_sheet"]["sequence_groups"],
    direct_public303_maximum_bit_scores=[h["measurements"]["maximum_bit_score"] for h in direct["components"]["database_sheet"]["hits"]],
    direct_public303_matched_metadata_count=direct["components"]["database_sheet"]["coverage"]["matched_metadata_row_count"],
    current_functions=direct["components"]["function_weights"]["unadjusted_probabilities"],
    standard_R_uses_same_public303_components=True, standard_R_numerical_row_count=len(rows),
    json_baseline_weights=baseline["components"]["function_weights"],
    prospective_payloads_invalid={k: v["issues"] for k, v in invalids.items()})
save("summary.json", summary)
save("direct_public303_sheet.json", direct_sheet)
save("direct_public303_components.json", direct)
save("standard_R_calculations.json", full)
save("standard_R_rows.json", rows)
save("prospective_v1_rejections.json", invalids)
for row in hashes + baseline_hashes:
    assert digest(Path(row["path"]).read_bytes()) == row["sha256"]
print(json.dumps({k: summary[k] for k in ("evidence", "exact_current_reproduction", "unchanged_inputs",
    "standard_qualification_details", "direct_public303_codes", "direct_public303_group_count",
    "direct_public303_matched_metadata_count", "direct_public303_maximum_bit_scores",
    "current_functions", "standard_R_uses_same_public303_components", "standard_R_numerical_row_count")}, indent=2))
