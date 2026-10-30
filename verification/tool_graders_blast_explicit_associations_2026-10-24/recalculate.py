"""Recalculate the saved synthetic H1 sheet without analysis or acquisition.

Run with .venv/bin/python verification/tool_graders_blast_explicit_associations_2026-10-24/recalculate.py
"""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(DIRECTORY.parents[1]))

from gene_annotation_episode import blast_database_grader, blast_grading_inputs


def forbidden(*args, **kwargs):
    raise AssertionError("Recalculation cannot rebuild, reparse, execute, or acquire inputs")


def main():
    content = (DIRECTORY / "synthetic_sheet.json").read_bytes()
    sheet = json.loads(content)
    with patch.object(blast_database_grader, "build_database_sheet", forbidden), \
         patch.object(blast_grading_inputs, "parse_blast_json", forbidden), \
         patch.object(blast_grading_inputs, "parse_blast_tabular", forbidden), \
         patch.object(socket, "socket", forbidden), \
         patch.object(socket, "create_connection", forbidden), \
         patch.object(subprocess, "Popen", forbidden), \
         patch.object(subprocess, "run", forbidden):
        calculated = {str(temperature): blast_database_grader.calculate_database_probabilities(
            sheet, model={"temperature_bits": temperature}) for temperature in (2, 1)}
    assert calculated["2"]["unadjusted_probabilities"] == {"F": 2 / 3, "G": 1 / 3}
    assert calculated["1"]["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert json.loads(content) == sheet
    assert (DIRECTORY / "synthetic_sheet.json").read_bytes() == content
    evidence = {"input_kind": "synthetic", "input_sheet_sha256": hashlib.sha256(content).hexdigest(),
        "reparsed_or_reacquired": False, "sheet_unchanged": True, "calculations": calculated}
    (DIRECTORY / "recalculated.json").write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"input_kind": "synthetic", "sheet_unchanged": True,
        "temperature_2": calculated["2"]["unadjusted_probabilities"],
        "temperature_1": calculated["1"]["unadjusted_probabilities"]}))


if __name__ == "__main__":
    main()
