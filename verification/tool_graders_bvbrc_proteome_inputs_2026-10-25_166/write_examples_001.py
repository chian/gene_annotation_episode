"""Run supplied-input examples; no BV-BRC/native scientific output is fabricated."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.bvbrc_proteome_inputs import (
    index_original_inputs, read_feature_metadata, read_feature_sequences,
    read_genome_metadata, read_protein_fasta,
)

OUT = Path(__file__).resolve().parent


def source(raw, label, complete="yes"):
    return {"content": {"source_ref": "synthetic-" + label, "artifact_field": "artifact_ref",
                       "artifact_ref": "synthetic-" + label + "-bytes",
                       "sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)},
            "body_complete": True, "object_complete": complete}


def source_field(binding, pointer):
    return {"source_ref": binding["source_ref"], "sha256": binding["sha256"],
            "pointer": pointer, "row_ordinal": None, "field_name": None}


def population():
    return {"origin": "supplied_snapshot", "query_source": None, "selected_fields": [],
            "offset": None, "requested_limit": None, "reported_total_count": None,
            "population_complete": "yes", "completeness_evidence": []}


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


examples = []


def save(name, raw, arguments, reader):
    examples.append({"case": name, "origin": "synthetic_supplied_input",
                     "content_utf8": raw.decode("utf-8"), "arguments": deepcopy(arguments),
                     "actual_reader_result": reader(raw, **arguments)})


correction = json.loads((ROOT / "verification/tool_graders_bvbrc_proteome_sheet_contract_2026-10-25_165/B1_PRECISION_EXAMPLES_002.json").read_text())
raw = correction["raw_input_utf8"].encode()
save("correction002_input_run_through_B1", raw,
     {"source": correction["expected_inventory"]["source"], "inventory_key": "synthetic-input-002",
      "declared_format": "protein_fasta_utf8_v1"}, read_protein_fasta)
raw = b">first\nACDE\n>last\nACD\n"
save("unknown_object_complete_keeps_last_sequence_null", raw,
     {"source": source(raw, "partial-fasta", "unknown"), "inventory_key": "synthetic-partial",
      "declared_format": "protein_fasta_utf8_v1"}, read_protein_fasta)
digest = hashlib.md5(b"ACD").hexdigest()
records = [
    {"feature_id": "f1", "aa_length": 0, "start": -2, "end": 0},
    {"patric_id": "p2", "aa_sequence_md5": digest, "product": "supplied source assignment"}, None,
]
raw = encode(records)
save("feature_id_or_patric_id_and_malformed_neighbor", raw,
     {"source": source(raw, "features"), "snapshot_key": "synthetic-features",
      "declared_format": "bvbrc_genome_feature_json_array_v1", "population": population(),
      "coordinate_convention": {"value": "unknown", "source_fields": []}}, read_feature_metadata)
raw = encode([{"genome_id": "g1", "taxon_id": "562.0"}, {"genome_id": "g2"}, {"genome_name": "name only"}])
save("optional_taxon_and_missing_identity", raw,
     {"source": source(raw, "genomes"), "snapshot_key": "synthetic-genomes",
      "declared_format": "bvbrc_genome_json_array_v1", "population": population()}, read_genome_metadata)
raw = encode([{"md5": digest.upper(), "sequence": "a cd"},
              {"md5": "0" * 32, "sequence": "ACD"},
              {"md5": hashlib.md5(b"").hexdigest(), "sequence": ""}])
save("sequence_case_digest_conflict_and_complete_empty_sequence", raw,
     {"source": source(raw, "sequences"), "snapshot_key": "synthetic-sequences",
      "declared_format": "bvbrc_feature_sequence_json_array_v1", "population": population()}, read_feature_sequences)

submitted = {"genome_ids": ["G1", "G2"], "user_genomes": ["/F1"], "user_feature_groups": ["/FG1"],
             "reference_genome_index": 3, "min_ident": 0, "min_seq_cov": None, "max_e_val": 1e-5}
observed_effective = {**submitted, "min_ident": 0.1, "min_seq_cov": 0.3, "min_positives": 0.2}
submitted_raw = encode({"parameters": submitted})
effective_raw = encode({"effective": observed_effective})
submitted_binding = source(submitted_raw, "submitted")["content"]
effective_binding = source(effective_raw, "effective")["content"]
original = {"resource_id": "synthetic-api", "task_id": "synthetic-task",
            "required_application_id": "GenomeComparison", "native_application_id": "GenomeComparison",
            "submitted_parameters": submitted, "submitted_start_parameters": {},
            "scheduler_returned_parameters": None,
            "effective_parameters": {"value": observed_effective,
                "evidence": {"content": effective_binding, "pointer": "/effective"}},
            "submission_receipt_ref": "synthetic-receipt", "submission_operation_key": "synthetic-operation",
            "submission_source_ref": submitted_binding["source_ref"]}
submitted_source = {"kind": "submitted", "source_field": source_field(submitted_binding, "/parameters")}
effective_source = {"kind": "effective", "source_field": source_field(effective_binding, "/effective")}
contract = {"id": "GenomeComparison_inspected_source_v1",
            "application_tree": "5c365e1dca2b3a8c311d7d352e862ff1442eefc9",
            "application_sha256": "4267b35bdd5ad858b833fa2b84eb794c91e95b7f5abc0628b90ec4d6a0a33c14",
            "dependency_tree": "18196fe0df123702457e4af2e0b1e0707d5f5281",
            "deployment_match": "unobserved", "deployment_evidence": []}
for label, selected, additional in [
    ("submitted_selection_keeps_effective_thresholds_separate", submitted_source, None),
    ("effective_selection_missing_submitted_locator", effective_source, None),
    ("effective_selection_with_supplied_submitted_locator", effective_source, [submitted_source]),
]:
    arguments = {"parameter_source": selected, "source_contract": contract, "additional_parameter_sources": additional}
    examples.append({"case": label, "origin": "synthetic_supplied_record",
                     "submitted_source_utf8": submitted_raw.decode(), "effective_source_utf8": effective_raw.decode(),
                     "original_task": original, "arguments": arguments,
                     "actual_reader_result": index_original_inputs(original, **arguments)})

target = OUT / "FILLED_SUPPLIED_INPUT_EXAMPLES_001.json"
with target.open("x", encoding="utf-8") as handle:
    json.dump({"origin": "synthetic_inputs_processed_by_actual_B1_readers",
               "native_GenomeComparison_execution": False, "examples": examples},
              handle, indent=2, ensure_ascii=False, allow_nan=False)
    handle.write("\n")
print(json.dumps({"artifact": str(target.relative_to(ROOT)), "examples": len(examples),
                  "statuses": {item["case"]: item["actual_reader_result"]["status"] for item in examples}}, indent=2))
