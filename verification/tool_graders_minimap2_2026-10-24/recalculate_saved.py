"""Recalculate retained numerical sheets without any network/native execution."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.minimap2_grader import calculate_minimap2_placement_scores, calculate_minimap2_query_scores


def forbidden(*args, **kwargs):
    raise AssertionError("saved-sheet recalculation forbids network and native execution")


def main():
    socket.create_connection = forbidden
    socket.socket = forbidden
    subprocess.run = forbidden
    subprocess.Popen = forbidden
    directory = Path(__file__).resolve().parent
    report = {"network_and_native_execution_prohibited": True, "sheet_mutation": False,
              "placement_count": 0, "query_count": 0, "presets": []}
    for placements in sorted(directory.glob("native_*/placements.jsonl")):
        groups = {}
        for line in placements.read_text().splitlines():
            graded = json.loads(line)
            saved = deepcopy(graded["sheet"])
            recalculated = calculate_minimap2_placement_scores(graded["sheet"])
            assert recalculated == graded["scores"]
            assert saved == graded["sheet"]
            name = saved["native_facts"]["query_name"]
            groups.setdefault(name, []).append(saved)
            report["placement_count"] += 1
        query_scores = []
        for name, sheets in groups.items():
            before = deepcopy(sheets)
            metadata = {"name": name, "length": sheets[0]["native_facts"]["query_length"]}
            query_scores.append(calculate_minimap2_query_scores(iter(sheets), query_metadata=metadata, output_complete=True))
            assert before == sheets
            report["query_count"] += 1
        (placements.parent/"query_scores.json").write_text(json.dumps(query_scores, indent=2, sort_keys=True, allow_nan=False)+"\n")
        report["presets"].append(next(iter(groups.values()))[0]["preset"])
    (directory/"recalculation_report.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False)+"\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
