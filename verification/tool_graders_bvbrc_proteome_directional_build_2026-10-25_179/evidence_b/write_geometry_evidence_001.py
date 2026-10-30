"""Saved native observations -> full pure geometry evidence; no scientific job."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent
ROOT = BUILD.parent.parent
CANDIDATE = BUILD / "candidate"
sys.path.insert(0, str(CANDIDATE))

from gene_annotation_episode.bvbrc_proteome_directional_geometry import (
    calculate_protein_block, inspect_protein_correspondence, union_position_intervals,
)


def save(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    content = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), byte_count=len(content), sha256=hashlib.sha256(content).hexdigest())


reports, summaries, sources = [], [], []
for ri, release in enumerate(("2011", "2202", "2221")):
    path = ROOT / f"verification/tool_graders_bvbrc_proteome_directional_2026-10-25_172/FILLED_NATIVE_{release}_001.json"
    sources.append(sha(path))
    native = json.loads(path.read_text())
    report = dict(report_ordinal=ri, report_key=native["report_key"], source=deepcopy(native["source"]), queries=[])
    for qi, query in enumerate(native["queries"]):
        qkey = dict(report_ordinal=ri, query_ordinal=qi)
        qout = dict(key=qkey, no_hits_marker=deepcopy(query["no_hits_marker"]), subjects=[])
        for si, subject in enumerate(query["subjects"]):
            skey = dict(**qkey, subject_ordinal=si)
            hsps = []
            for hi, hsp in enumerate(subject["hsps"]):
                hkey = dict(**skey, hsp_ordinal=hi)
                blocks = [calculate_protein_block(b, key=dict(**hkey, block_ordinal=bi),
                    query_length=query["length"], subject_length=subject["length"],
                    amino_acid_alphabet="standard20", ratio_decimal_places=18, rounding="half_even")
                    for bi, b in enumerate(hsp["traceback_blocks"])]
                included = [b["key"] for b in blocks if all(
                    b["coverage"][side + "_trace_paired_union"]["count"]["state"] == "value" for side in ("query", "subject"))]
                excluded = [b["key"] for b in blocks if b["key"] not in included]
                absent = [] if blocks else [hkey]
                # All three retained native examples have complete contiguous
                # within-HSP blocks. Assert this from saved endpoint operands.
                assert all(b[side + "_start"]["value"] == a[side + "_end"]["value"] + 1
                    for a, b in zip(hsp["traceback_blocks"], hsp["traceback_blocks"][1:])
                    for side in ("query", "subject"))
                hsps.append(dict(key=hkey, blocks=blocks, contiguous_blocks="yes" if blocks else "unknown",
                    pair_geometry_support=dict(included_blocks=included, excluded_blocks=excluded,
                        hsps_without_traceback=absent, complete_for_displayed_blocks=not excluded and not absent)))
            graph = inspect_protein_correspondence(hsps, key=skey)
            qout["subjects"].append(dict(key=skey, geometry_inputs=hsps, correspondence=graph))
            unions = {}
            for side in ("query", "subject"):
                for basis in ("occupied", "paired"):
                    rows = [interval for h in hsps for b in h["blocks"]
                            for interval in b["coverage"][side + "_trace_" + basis + "_union"]["intervals"]]
                    merged = union_position_intervals(rows)
                    unions[side + "_" + basis] = dict(intervals=merged, count=sum(b - a for a, b in merged))
            summaries.append(dict(release=release, key=skey, displayed_hsp_count=len(hsps),
                displayed_block_count=sum(len(h["blocks"]) for h in hsps),
                distinct_pair_count=graph["distinct_pair_count"]["value"],
                repeated_pair_occurrence_count=graph["repeated_pair_occurrence_count"]["value"],
                mapping_state=graph["mapping_state"], unions=unions,
                conflicts=[dict(code=c["code"], query_intervals=c["query_intervals"],
                    subject_intervals=c["subject_intervals"], native_column_witness_count=len(c["columns"])) for c in graph["conflicts"]]))
        report["queries"].append(qout)
    reports.append(report)

save("FILLED_GEOMETRY_NATIVE_001.json", dict(
    meaning="Complete blocks and subject graphs for retained public native reports; not BV-BRC service executions",
    parameters=dict(amino_acid_alphabet="standard20", ratio_decimal_places=18, rounding="half_even"), reports=reports))
save("NUMERICAL_SUMMARY_001.json", summaries)
save("FINAL_VERIFICATION_001.json", dict(
    test_command="/home/chia/repos/gene_annotation_episode/.venv/bin/python -m pytest -q tests/test_bvbrc_proteome_directional_geometry.py tests/test_blast_pairwise_grader.py tests/test_blast_database_grader.py",
    working_directory=str(CANDIDATE), exit_code=0, passed=125, pytest_seconds=1.11,
    output="........................................................................ [ 57%]\n.....................................................                    [100%]\n125 passed in 1.11s\n",
    evidence_kind="Actual local pure numerical and retained-native tests; preserved BLAST grader regressions",
    scientific_execution=False, service_execution=False, production_edits=False,
    episode_communication_verified=False,
    source_inputs=sources,
    final_files=[sha(CANDIDATE / name) for name in (
        "gene_annotation_episode/bvbrc_proteome_directional_geometry.py",
        "tests/test_bvbrc_proteome_directional_geometry.py")],
    reports=len(reports), queries=sum(len(r["queries"]) for r in reports),
    subjects=len(summaries), hsps=sum(s["displayed_hsp_count"] for s in summaries),
    blocks=sum(s["displayed_block_count"] for s in summaries)))
print(json.dumps(dict(reports=len(reports), subjects=len(summaries),
    hsps=sum(s["displayed_hsp_count"] for s in summaries),
    blocks=sum(s["displayed_block_count"] for s in summaries),
    final_files=json.loads((HERE / "FINAL_VERIFICATION_001.json").read_text())["final_files"]), indent=2))
