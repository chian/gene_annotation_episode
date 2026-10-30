"""Offline qualification of retained native data, using existing Infernal code.

This is a verification artifact, not a production Rfam publisher or batch
adapter. It makes no HTTP request and changes no saved native response.
"""
import hashlib
import json
from pathlib import Path
import re
import socket

from gene_annotation_episode.infernal_search_inputs import populate_infernal_search_sheet
from gene_annotation_episode.infernal_search_grader import calculate_infernal_search_scores


def blocked(*args, **kwargs):
    raise AssertionError("network is forbidden during saved native verification")


socket.socket = blocked
directory = Path(__file__).resolve().parent
expected = [104.6, 104.6, 104.6, 51.3, 95.5, 95.2]
report = {"verification_kind": "retained_native_only_not_production_integration", "jobs": []}
for label in ("single", "multi"):
    job = directory / "live" / label
    handle = json.loads((job / "original_handle.json").read_bytes())
    inputs = json.loads((job / "input-manifest.json").read_bytes())
    body = (job / "004-fetch-tblout/response.body").read_bytes()
    capture = json.loads((job / "004-fetch-tblout/snapshot.json").read_bytes())
    out = (job / "005-fetch-out/response.body").read_text()
    native_json = json.loads((job / "003-fetch-json/response.body").read_bytes())
    assert capture["request"]["job_id"] == handle["job_id"]
    assert capture["content_sha256"] == hashlib.sha256(body).hexdigest()
    assert capture["transport"]["body_complete"] is True
    assert capture["transport"]["status"] == 200
    assert (job / "002-status/response.body").read_bytes() == b"FINISHED"
    assert body.decode().rstrip().endswith("# [ok]")
    assert out.rstrip().endswith("[ok]")
    assert handle["job_id"] + ".sequence" in body.decode()
    artifact = "retained-native-" + label + "-tblout-" + capture["content_sha256"]
    metadata = [{"name": record["original_header"] or "EMBOSS_001",
                 "length": record["submitted_length_nt"], "sequence": record["submitted_sequence"],
                 "artifact_id": artifact}
                for record in inputs["records"]]
    assert len({row["name"] for row in metadata}) == len(metadata)
    query_blocks = re.findall(r"^Query:\s+(\S+)\s+\[L=(\d+)\]$", out, re.M)
    assert {(name, int(length)) for name, length in query_blocks} == {
        (row["name"], row["length"]) for row in metadata}
    assert len(query_blocks) == len(metadata)
    sheet = populate_infernal_search_sheet([{"artifact_id": artifact, "format": "infernal_tblout",
        "table_format": 1, "complete": True, "content": body.decode("ascii")}],
        operation={"program": "cmscan", "native_version": "1.1.5", "settings": {}},
        sequence_metadata=metadata, model_metadata=None)
    score = calculate_infernal_search_scores(sheet, parameters={"hit_scope": "reported"})
    assert sheet["artifacts"][0]["effective_table_format"] == 1
    assert sheet["artifacts"][0]["native_program"] == "cmscan"
    assert sheet["artifacts"][0]["native_version"] == "1.1.5"
    assert sheet["artifacts"][0]["retained_population_complete"] is True
    assert [r["bitscore"] for r in sheet["hits"]] == (expected[:1] if label == "single" else expected)
    assert all(r["sequence"]["metadata_join"]["status"] == "matched" for r in sheet["hits"])
    assert all(r["components"]["sequence_span_fraction"] == 1.0 for r in score["hits"])
    assert all(r["components"]["model_span_fraction"] is None for r in score["hits"])
    if label == "single":
        assert native_json["jobId"] == handle["job_id"]
        assert native_json["searchSequence"] == inputs["records"][0]["submitted_sequence"]
    else:
        assert set(native_json) == {"opened", "hits"}
        assert len(native_json["hits"]) == 6
        assert all(set(row) == {"id", "acc", "start", "end", "strand", "GC", "score", "E"}
                   for row in native_json["hits"])
        assert sheet["hits"][0]["sequence"]["identity"] != sheet["hits"][1]["sequence"]["identity"]
        assert sheet["hits"][2]["strand"] == "-"
        assert sheet["hits"][3]["truncation"] == "3'"
    occurrence_bindings = [{"sequence_metadata_index": index,
                           "native_query_name": row["name"],
                           "query_occurrence_key": original["query_occurrence_key"],
                           "original_record_ordinal": original["original_record_ordinal"]}
                          for index, (row, original) in enumerate(zip(metadata, inputs["records"]))]
    report["jobs"].append({"label": label, "original_handle": handle,
                          "original_input": inputs, "artifact_capture": capture,
                          "occurrence_bindings": occurrence_bindings,
                          "query_report_membership": query_blocks, "sheet": sheet, "calculation": score})
    print(json.dumps({"job": label, "native_query_count": len(query_blocks),
                      "native_hit_count": len(sheet["hits"]), "format": "infernal_tblout_1",
                      "native_program": "cmscan", "native_version": "1.1.5",
                      "sequence_span_fractions": [r["components"]["sequence_span_fraction"] for r in score["hits"]],
                      "model_denominators": "unavailable", "parser_status": sheet["status"]}))
Path("native-format-reuse.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
print("Native qualification and direct existing Infernal parser/calculator checks passed; no network.")
