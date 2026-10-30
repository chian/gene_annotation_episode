"""Generate immutable native projections and arithmetic inspection receipts.

Run with PYTHONPATH=. .venv/bin/python <this file>. This script reads retained
fixtures; the production parser itself takes bytes and performs no IO.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

from gene_annotation_episode.bvbrc_proteome_directional import parse_genome_comparison_directional_report
from gene_annotation_episode.bvbrc_proteome_directional_contracts import validate_directional_report


BASE = Path(__file__).parent
FIXTURES = Path("tests/fixtures/bvbrc_proteome_directional")
FORMAT = "ncbi_blastall_blastp_pairwise_text_v1"


def write(name, value):
    with (BASE / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def digest(data):
    return hashlib.sha256(data).hexdigest()


projections = {}
inputs = []
for key, filename in (
    ("2011", "biopython_text_2011L_blastp_002.txt"),
    ("2202", "biopython_text_2202L_blastp_001.txt"),
    ("2221", "biopython_text_2221L_blastp_001.txt"),
):
    data = (FIXTURES / filename).read_bytes()
    supplied = {
        "content": {"source_ref": "retained-public-native-" + key,
                    "artifact_ref": str(FIXTURES / filename), "artifact_field": "artifact_ref",
                    "sha256": digest(data), "byte_count": len(data)},
        "body_complete": True, "object_complete": "yes",
    }
    result = parse_genome_comparison_directional_report(
        data, source=supplied, declared_format=FORMAT, report_key="public-native-" + key)
    assert result["parse_state"] == "ok"
    projections[key] = result
    write("FILLED_NATIVE_" + key + "_001.json", result)
    inputs.append({"file": str(FIXTURES / filename), "source": supplied,
                   "evidence_kind": "retained_public_native_report",
                   "bvbrc_deployment_or_task_evidence": False})
write("SOURCE_INPUTS_001.json", inputs)


def union_coordinates(hsps, side):
    # Example arithmetic, not a general correspondence calculator or task-input
    # coverage denominator: the native blocks in these examples are consistent.
    return len({position for hsp in hsps for block in hsp["traceback_blocks"]
                for position in range(block[side + "_start"]["value"], block[side + "_end"]["value"] + 1)})


def inspect(saved):
    numerical = {"meaning": "Independent inspection of parsed native occurrences; no annotation confidence or task/input association."}
    r = saved["2221"]
    q = r["queries"][1]
    hsps = q["subjects"][0]["hsps"]
    numerical["2221"] = {
        "query_lengths": [q["length"]["value"] for q in r["queries"]],
        "displayed_description_rows": sum(len(q["descriptions"]) for q in r["queries"]),
        "aligned_subject_blocks": sum(len(q["subjects"]) for q in r["queries"]),
        "hsp_blocks": sum(len(s["hsps"]) for q in r["queries"] for s in q["subjects"]),
        "second_query_hsp_identity_counts": [h["identity_count"]["value"] for h in hsps],
        "second_query_hsp_identity_denominators": [h["identity_denominator"]["value"] for h in hsps],
        "second_query_query_union": {"numerator": union_coordinates(hsps, "query"), "native_report_length_denominator": q["length"]["value"]},
        "second_query_subject_union": {"numerator": union_coordinates(hsps, "subject"), "native_report_length_denominator": q["subjects"][0]["length"]["value"]},
        "second_query_disjoint_observed_identity_sum": {"numerator": sum(h["identity_count"]["value"] for h in hsps), "denominator": sum(h["identity_denominator"]["value"] for h in hsps)},
        "first_hsp_inclusive_query_span": {"numerator": 414, "denominator": 600},
        "legacy_first_hsp_endpoint_subtraction": {"numerator": 413, "denominator": 600},
        "statistic_records_by_query": [len(q["statistics"]) for q in r["queries"]],
    }
    r = saved["2202"]
    q = r["queries"][0]
    hsps = q["subjects"][0]["hsps"]
    numerical["2202"] = {
        "query_lengths": [q["length"]["value"] for q in r["queries"]],
        "subject_blocks_by_query": [len(q["subjects"]) for q in r["queries"]],
        "hsp_blocks_by_query": [sum(len(s["hsps"]) for s in q["subjects"]) for q in r["queries"]],
        "first_subject_identity_counts": [h["identity_count"]["value"] for h in hsps],
        "first_subject_identity_denominators": [h["identity_denominator"]["value"] for h in hsps],
        "query_union": {"numerator": union_coordinates(hsps, "query"), "native_report_length_denominator": q["length"]["value"]},
        "subject_union": {"numerator": union_coordinates(hsps, "subject"), "native_report_length_denominator": q["subjects"][0]["length"]["value"]},
        "second_hsp_native_gap_count": hsps[1]["gap_count"],
        "qualification": "Subject intervals overlap at different query positions; no independent combined correspondence is asserted.",
    }
    q = saved["2011"]["queries"][0]
    statistics = {s["kind"]: s for s in q["statistics"]}
    numerical["2011"] = {
        "no_hits_marker": q["no_hits_marker"]["value"],
        "query_length": q["length"]["value"],
        "database_sequences": q["database_headers"][0]["sequence_count"]["value"],
        "database_letters": q["database_headers"][0]["letter_count"]["value"],
        "sequences_better_than": {"count": statistics["sequences_better_than"]["integer_value"]["value"], "threshold": statistics["sequences_better_than"]["threshold"]["value"]},
    }
    assert numerical["2221"]["displayed_description_rows"] == 30
    assert numerical["2221"]["aligned_subject_blocks"] == 3
    assert numerical["2221"]["hsp_blocks"] == 4
    assert numerical["2221"]["second_query_hsp_identity_counts"] == [353, 115]
    assert numerical["2221"]["second_query_query_union"]["numerator"] == 529
    assert numerical["2221"]["second_query_disjoint_observed_identity_sum"] == {"numerator": 468, "denominator": 529}
    assert numerical["2202"]["query_union"]["numerator"] == 219
    assert numerical["2202"]["subject_union"]["numerator"] == 144
    assert numerical["2011"]["sequences_better_than"] == {"count": 0, "threshold": "10.0"}
    return numerical


numerical = inspect(projections)
write("NUMERICAL_CHECKS_001.json", numerical)
loaded = {key: json.loads((BASE / ("FILLED_NATIVE_" + key + "_001.json")).read_text()) for key in projections}


def prohibited(*args, **kwargs):
    raise AssertionError("IO_not_permitted_during_saved_projection_replay")


with patch("builtins.open", prohibited), patch.object(Path, "open", prohibited), patch.object(socket, "socket", prohibited), patch.object(subprocess, "Popen", prohibited):
    replayed = {key: validate_directional_report(value) for key, value in loaded.items()}
    assert replayed == projections
    assert inspect(replayed) == numerical
    detached = validate_directional_report(loaded["2221"])
    detached["queries"][1]["length"]["value"] = 0
    assert loaded["2221"]["queries"][1]["length"]["value"] == 600

write("SAVED_REPLAY_001.json", {"passed": True, "projection_count": len(loaded),
                               "file_access_disabled_during_validation": True,
                               "sockets_disabled": True, "subprocesses_disabled": True,
                               "numerical_inspection_reproduced": True, "detached_copy_checked": True,
                               "scientific_algorithm_reexecuted": False})
print(json.dumps(numerical, indent=2))
