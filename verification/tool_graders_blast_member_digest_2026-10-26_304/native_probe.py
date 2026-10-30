"""Retained NCBI byte and numerical evidence; no BLAST execution or acquisition."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

from gene_annotation_episode.blast_grading_inputs import parse_blast_json
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "verification/w04_blast_graders_2026-10-24_001/live_api/result.body"


def main():
    raw = SOURCE.read_bytes()
    old = parse_blast_json(raw, mode="database", resource="api")
    invocation = {"execution_program": "blastp", "scientific_mode": "database", "resource_kind": "api",
        "query_kind": "sequence", "reference_kind": "sequence", "request": {},
        "effective_options": {"requested_hit_limit": None, "requested_hsp_limit": None},
        "operands": [{"role": "query", "artifact_key": "query.fa", "record_ordinal": 0,
            "native_id": "gene_001", "native_title": "gene_001", "subject_ref": "actual-query",
            "molecule": "protein", "length": 253, "selected_interval": None, "identity": None}],
        "completion": {"native_returncode": None, "producer_complete": None}}
    collection = parse_blast_report_collection({"retained-ncbi": raw}, artifacts=[
        {"artifact_key": "retained-ncbi", "role": "primary_report", "format": "json2_archive",
         "fields": None, "delimiter": None}], invocation=invocation)
    members = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for ordinal, info in enumerate(archive.infolist()):
            payload = archive.read(info)
            members.append({"member_ordinal": ordinal, "name": info.filename,
                "size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    assert collection["artifacts"][0]["members"] == members
    item, = collection["searches"]
    assert item["normalized"]["hits"] == old["hits"]
    assert item["normalized"]["query"]["length"] == 253
    assert len(old["hits"]) == 7
    assert old["hits"][0]["hsps"][0]["identity"] == 253
    assert not collection["issues"] and not item["issues"]
    for name, value in (("collection.json", collection), ("legacy-single-query.json", old)):
        Path(name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    evidence = {"source_path": str(SOURCE), "container_size_bytes": len(raw),
        "container_sha256": hashlib.sha256(raw).hexdigest(), "members": members,
        "query": old["query"], "hit_count": len(old["hits"]),
        "hsps": [{"hit_index": hit["hit_index"], "accessions": [d["accession"] for d in hit["descriptions"]],
                  "hsps": [{key: hsp[key] for key in ("bit_score", "score", "evalue", "identity", "align_len", "gaps")}
                           for hsp in hit["hsps"]]} for hit in old["hits"]]}
    Path("native-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    if len(sys.argv) == 2:
        baseline = Path(sys.argv[1])
        previous = json.loads((baseline / "collection.json").read_text())
        stripped = deepcopy(collection)
        for current, original in zip(stripped["searches"], previous["searches"], strict=True):
            member = current["normalized"]["native"]["archive_member"]
            assert member.pop("sha256") == members[member["ordinal"]]["sha256"]
            assert current == original
        assert stripped == previous
        assert Path("legacy-single-query.json").read_bytes() == (baseline / "legacy-single-query.json").read_bytes()
        assert Path("native-evidence.json").read_bytes() == (baseline / "native-evidence.json").read_bytes()
        comparison = {"baseline_directory": str(baseline),
            "only_collection_change": "searches[0].normalized.native.archive_member.sha256",
            "full_collection_equal_after_removing_only_added_member_sha256": True,
            "legacy_single_query_output_byte_identical": True,
            "native_evidence_byte_identical": True}
        Path("comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
        print(json.dumps(comparison, indent=2))
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
