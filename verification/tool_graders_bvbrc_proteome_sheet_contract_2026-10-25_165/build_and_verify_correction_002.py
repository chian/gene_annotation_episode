"""Build only additive review artifacts. Preserve every proposal001 byte."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

def hash_bytes(data): return hashlib.sha256(data).hexdigest()
def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")

old_hashes = json.loads((HERE / "ARTIFACT_HASHES_001.json").read_text())["artifacts"]
check_names = []
def check(name, value):
    if not value: raise AssertionError(name)
    check_names.append(name)

for row in old_hashes:
    check("unchanged001:" + Path(row["path"]).name, hash_bytes((ROOT / row["path"]).read_bytes()) == row["sha256"])

schema = json.loads((HERE / "DATA_SHAPES_PROPOSAL_001.json").read_text())
schema["$id"] = "urn:gene-annotation:genome-comparison:sheet-contract:proposal-002-165"
schema["title"] = "GenomeComparison modular data-shape proposal 002; additive review correction; not installed"
schema["$comment"] += " Additive correction002 adds unavailable-witness-interface codes and permits null for an unavailable incomplete header. See REVIEW_CORRECTION_002.md."
schema["$defs"]["PReason"]["enum"].extend(["execution_witness_interface_unavailable", "occurrence_witness_interface_unavailable"])
schema["$defs"]["FastaRecord"]["properties"]["header"] = {"anyOf": [{"type": "string"}, {"type": "null"}]}
Draft202012Validator.check_schema(schema)
write("DATA_SHAPES_PROPOSAL_002.json", schema)
check("draft2020_12_schema_valid", True)

refs, open_objects = [], []
def inspect(node, path=""):
    if isinstance(node, dict):
        if "$ref" in node: refs.append(node["$ref"])
        if node.get("type") == "object" and node.get("additionalProperties") is not False: open_objects.append(path)
        for k,v in node.items(): inspect(v, path + "/" + k)
    elif isinstance(node,list):
        for i,v in enumerate(node): inspect(v, path + "/" + str(i))
inspect(schema)
check("all_object_shapes_closed", not open_objects)
check("all_references_local_resolved", all(v.startswith("#/$defs/") and v[8:] in schema["$defs"] for v in refs))
native = json.loads((ROOT / "gene_annotation_episode/bvbrc_proteome_native_schemas.json").read_text())
check("all_native_definitions_unchanged", all(schema["$defs"][k] == v for k,v in native["$defs"].items()))

# Constructed supplied input, never a GenomeComparison output fixture.
raw = b">  dup  first description\t\r\nacde\r\n>dup second\nAA-?1\n>empty\n"
source_ref = "synthetic-input-source-for-contract-002"
content = {"source_ref": source_ref, "artifact_field": "artifact_ref", "artifact_ref": "synthetic-input-bytes-for-contract-002",
    "sha256": hash_bytes(raw), "byte_count": len(raw)}
starts = [0, raw.index(b">dup second"), raw.index(b">empty")]
ends = [starts[1], starts[2], len(raw)]
headers = ["  dup  first description\t", "dup second", "empty"]
identifiers = ["dup", "dup", "empty"]
descriptions = ["  first description\t", " second", ""]
sequences = ["ACDE", "AA-?1", ""]
scope = {k:None for k in ("track_key", "reference_row_ordinal", "association_key", "protein_key", "report_key", "query_ordinal", "hit_ordinal", "hsp_ordinal")}
records = []
for i in range(3):
    field = {"source_ref": source_ref, "sha256": content["sha256"], "pointer": "/records/" + str(i), "row_ordinal": i, "field_name": None}
    ds = [] if i == 0 else [{"code": "fasta_sequence_invalid" if i == 1 else "fasta_empty_sequence", "severity": "error", "path": "/records/" + str(i), "scope": scope, "source_fields": [field]}]
    records.append({"record_ordinal": i, "byte_start": starts[i], "byte_end_exclusive": ends[i],
        "header": headers[i], "identifier": identifiers[i], "description": descriptions[i],
        "sequence": sequences[i], "sequence_symbol_count": len(sequences[i]),
        "sequence_sha256": hash_bytes(sequences[i].encode()), "sequence_md5": hashlib.md5(sequences[i].encode()).hexdigest(),
        "record_complete": True, "valid_sequence": i == 0, "source_field": field, "diagnostics": ds})
inventory = {"version": "bvbrc_proteome_inventory_proposal_v1", "inventory_key": "synthetic-input-002",
    "format": "protein_fasta_utf8_v1", "source": {"content": content, "body_complete": True, "object_complete": "yes"},
    "molecule": "aa", "normalization": "ascii_whitespace_removed_uppercase_no_symbol_substitution_v1",
    "records": records, "observed_header_count": 3, "complete_record_count": 3, "valid_complete_record_count": 1,
    "duplicate_identifier_groups": [{"identifier": "dup", "record_ordinals": [0,1]}],
    "sequence_groups": [{"molecule":"aa", "normalization":"ascii_whitespace_removed_uppercase_no_symbol_substitution_v1",
        "sequence_sha256": records[0]["sequence_sha256"], "sequence_symbol_count": 4,
        "members":[{"inventory_key":"synthetic-input-002", "record_ordinal":0}]}],
    "diagnostics": [d for r in records for d in r["diagnostics"]]}
def validate(name,value):
    Draft202012Validator({"$schema":schema["$schema"],"$ref":"#/$defs/"+name,"$defs":schema["$defs"]}).validate(value)
    check_names.append("shape:"+name)
validate("ProteinInventory",inventory)
check("physical_record_byte_offsets_include_marker", all(raw[a:a+1] == b">" for a in starts))
check("physical_intervals_partition_received_records", b"".join(raw[a:b] for a,b in zip(starts,ends)) == raw)
check("header_excludes_crlf_preserves_whitespace", raw[:raw.index(b"\r\n")].decode()[1:] == headers[0])
check("identifier_and_description_are_exact_header_parts", headers[0] == "  " + identifiers[0] + descriptions[0])
check("complete_invalid_retains_string_count_digest", records[1]["sequence"] == "AA-?1" and records[1]["sequence_symbol_count"] == 5 and records[1]["sequence_sha256"] == hash_bytes(b"AA-?1") and not records[1]["valid_sequence"])
check("complete_empty_retains_empty_digests", records[2]["sequence"] == "" and records[2]["sequence_symbol_count"] == 0 and records[2]["sequence_sha256"] == hash_bytes(b"") and not records[2]["valid_sequence"])
check("invalid_records_not_sequence_grouped", inventory["sequence_groups"][0]["members"] == [{"inventory_key":"synthetic-input-002","record_ordinal":0}])
partial = deepcopy(records[2])
partial.update(header=None,identifier=None,description=None,sequence=None,sequence_symbol_count=None,sequence_sha256=None,sequence_md5=None,record_complete=False,valid_sequence=False)
validate("FastaRecord", partial)
validate("PReason", "execution_witness_interface_unavailable")
validate("PReason", "occurrence_witness_interface_unavailable")

metadata_cases = [
    {"case":"feature_id_only", "supplied":{"feature_id":"feature:1"}, "expected_identity_usable":True},
    {"case":"patric_id_only", "supplied":{"patric_id":"fig|1.1.peg.1"}, "expected_identity_usable":True},
    {"case":"neither_feature_id", "supplied":{"product":"source assignment"}, "expected_identity_usable":False},
    {"case":"zero_length", "field":"aa_length", "value":0, "expected_valid":True},
    {"case":"negative_length", "field":"aa_length", "value":-1, "expected_valid":False},
    {"case":"fractional_taxon", "field":"taxon_id", "value":562.5, "expected_valid":False},
    {"case":"zero_taxon", "field":"taxon_id", "value":0, "expected_valid":False},
    {"case":"unknown_coordinate", "field":"start", "value":-2, "convention":"unknown", "expected_valid":True, "qualification":"coordinate_convention_unknown"},
    {"case":"known_one_based_negative_coordinate", "field":"start", "value":-2, "convention":"one_based_closed", "expected_valid":False},
]
write("B1_PRECISION_EXAMPLES_002.json", {"origin":"constructed_supplied_input_and_expected_contract_values_not_production_reader_output",
    "raw_input_utf8":raw.decode(), "expected_inventory":inventory, "incomplete_header_record_shape":partial,
    "metadata_validity_cases":metadata_cases,
    "witness_outcomes":{"locator_only_exact_execution":"execution_witness_interface_unavailable", "locator_only_occurrence_mapping":"occurrence_witness_interface_unavailable"}})
for row in old_hashes:
    check("still_unchanged001:" + Path(row["path"]).name, hash_bytes((ROOT / row["path"]).read_bytes()) == row["sha256"])
write("VERIFICATION_002.json",{"recorded_at":datetime.now(timezone.utc).isoformat(),"scope":"additive_contract_correction_only",
    "checks_passed":len(check_names),"failed_checks":0,"checks":check_names,
    "native_definitions_unchanged":16,"proposal001_artifacts_unchanged":len(old_hashes),
    "B1_reader_implemented_or_run":False,"B2_join_implemented_or_run":False,"production_changed":False,
    "new_jobs_or_native_output_fixtures":False,"decoded_execution_witness_interface":"not_defined_links_remain_unqualified"})
artifacts=[]
for p in sorted(HERE.iterdir()):
    if p.is_file() and p.name.endswith(("_002.md","_002.py","_002.json")) and p.name!="ARTIFACT_HASHES_002.json":
        b=p.read_bytes();artifacts.append({"path":str(p.relative_to(ROOT)),"sha256":hash_bytes(b),"byte_count":len(b)})
write("ARTIFACT_HASHES_002.json",{"recorded_at":datetime.now(timezone.utc).isoformat(),"artifacts":artifacts})
print(json.dumps({"checks_passed":len(check_names),"failed":0,"proposal001_unchanged":True,"new_artifact_hashes":artifacts},indent=2))
