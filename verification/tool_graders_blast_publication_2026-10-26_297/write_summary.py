"""Retain compact filled numerical examples from the completed bounded checks."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
check = HERE / sys.argv[1]
prefix = sys.argv[2] if len(sys.argv) > 2 else ""
examples = []
for path in sorted((check / "temporary/pytest").glob("test_twenty_native_examples_pr[0-9]*/filled-publication.json")):
    example = json.loads(path.read_text())
    ref = example["prepared"]["scores_artifact_ref"]
    digest = ref.removeprefix("artifact_")
    raw = (path.parent / "store/artifacts" / digest[:2] / digest).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    scores = json.loads(raw)
    examples.append({"case": example["case"], "original_manifest": example["original_manifest"],
        "original_report_artifacts": example["original_report_artifacts"],
        "numerical_complete": example["prepared"]["numerical_complete"],
        "failures": example["publication"]["failures"],
        "requested_publication": example["publication"],
        "complete_hsp_values": [{"record_key": row["record_key"], "native_status": row["native_status"],
            "search_key": row["search_key"], "hit_ordinal": row["hit_ordinal"], "hsp_ordinal": row["hsp_ordinal"],
            "values": row["values"], "unavailable": row["unavailable"], "intervals": row["intervals"]}
            for row in scores["rows"]["pairwise_hsp"]],
        "complete_union_values": [{"record_key": row["record_key"], "native_status": row["native_status"],
            "values": row["values"], "unavailable": row["unavailable"]} for row in scores["rows"]["pairwise_union"]]})
assert len(examples) == 20
(HERE / (prefix + "FILLED_EXAMPLES.json")).write_text(json.dumps({"version": "native_blast_publication_examples_v1",
    "qualification": "Twenty unchanged retained native reports with explicit synthetic Store-handle rebinding in copied manifests; no new scientific execution.",
    "examples": sorted(examples, key=lambda row: row["case"])}, indent=2) + "\n")
paths = ["gene_annotation_episode/blast_pairwise_result_views.py", "gene_annotation_episode/native_blast_result_publication.py",
         "gene_annotation_episode/native_blast_result_worker.py", "gene_annotation_episode/domain.py", "gene_annotation_episode/state.py",
         "tests/test_blast_pairwise_result_views.py", "tests/test_blast_pairwise_publication.py"]
(HERE / (prefix + "SOURCE_HASHES.json")).write_text(json.dumps({name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                                   for name in paths}, indent=2) + "\n")
print(json.dumps({"retained_examples": len(examples), "source_files_hashed": len(paths)}))
