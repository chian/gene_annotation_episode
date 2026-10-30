"""Replay saved synthetic inputs through current B1, without acquisition."""
from datetime import datetime, timezone
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
input_path = OUT / "FILLED_SUPPLIED_INPUT_EXAMPLES_001.json"
examples = json.loads(input_path.read_text())["examples"]
readers = {
    "protein_fasta_utf8_v1": read_protein_fasta,
    "bvbrc_genome_feature_json_array_v1": read_feature_metadata,
    "bvbrc_genome_json_array_v1": read_genome_metadata,
    "bvbrc_feature_sequence_json_array_v1": read_feature_sequences,
}
checks = []
for example in examples:
    arguments = example["arguments"]
    if "content_utf8" in example:
        result = readers[arguments["declared_format"]](example["content_utf8"].encode(), **arguments)
    else:
        result = index_original_inputs(example["original_task"], **arguments)
    checks.append({"case": example["case"], "identical_to_saved_result": result == example["actual_reader_result"]})

receipt = {
    "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    "kind": "replay_of_synthetic_supplied_inputs",
    "source_sha256": hashlib.sha256((ROOT / "gene_annotation_episode/bvbrc_proteome_inputs.py").read_bytes()).hexdigest(),
    "B0_dependency_sha256": hashlib.sha256((ROOT / "gene_annotation_episode/bvbrc_proteome_data_contracts.py").read_bytes()).hexdigest(),
    "saved_examples_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
    "checks": checks,
    "native_execution": False,
    "network_acquisition": False,
}
with (OUT / "EXAMPLE_REPLAY_002.json").open("x", encoding="utf-8") as handle:
    json.dump(receipt, handle, indent=2, allow_nan=False)
    handle.write("\n")
print(json.dumps({"cases": len(checks), "identical": sum(row["identical_to_saved_result"] for row in checks)}))
if not all(row["identical_to_saved_result"] for row in checks):
    raise SystemExit(1)
