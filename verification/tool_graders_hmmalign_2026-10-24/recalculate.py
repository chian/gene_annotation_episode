"""Recalculate saved sheets; prohibit file I/O/network/subprocess inside scores."""
from pathlib import Path
import builtins
import json
import socket
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import gene_annotation_episode.hmmalign_inputs as readers
from gene_annotation_episode.hmmalign_grader import calculate_hmmalign_scores

HERE = Path(__file__).resolve().parent
saved = [(path.parent.name, json.loads(path.read_text()), json.loads(path.with_name("scores.json").read_text()))
         for path in sorted((HERE/"saved").glob("*/sheet.json"))]
assert len(saved) == 5


def forbidden(*args, **kwargs):
    raise AssertionError("calculator attempted I/O, acquisition, native execution or reparsing")


with (patch.object(builtins, "open", forbidden), patch.object(socket, "socket", forbidden),
      patch.object(subprocess, "Popen", forbidden), patch.object(readers, "parse_hmmalign_stockholm", forbidden),
      patch.object(readers, "build_hmmalign_sheet", forbidden)):
    for mode, sheet, expected in saved:
        before = json.dumps(sheet, sort_keys=True, allow_nan=False)
        actual = calculate_hmmalign_scores(sheet)
        assert actual == expected, mode
        assert json.dumps(sheet, sort_keys=True, allow_nan=False) == before, mode
        print(mode+": exact saved-score equality, no sheet mutation")
