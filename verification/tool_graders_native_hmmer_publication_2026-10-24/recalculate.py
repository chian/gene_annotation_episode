"""Recalculate the saved numerical sheets without acquisition or execution."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

from gene_annotation_episode.hmmer_search_grader import calculate_hmmer_search_scores
from gene_annotation_episode.nhmmer_grader import calculate_nhmmer_scores
from gene_annotation_episode.hmmalign_grader import calculate_hmmalign_scores


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
calculators = {"hmmer_search_sheet_v1": calculate_hmmer_search_scores,
    "nhmmer_sheet_v1": calculate_nhmmer_scores, "hmmalign_sheet_v1": calculate_hmmalign_scores}
loaded = []
for example in json.loads((HERE / "EXAMPLES.json").read_text()):
    directory = ROOT / example["path"]
    loaded.append((example["path"], json.loads((directory / "sheet.json").read_text()),
                   json.loads((directory / "scores.json").read_text())))


def prohibit(*args, **kwargs):
    raise AssertionError("recalculation attempted acquisition or execution")


results = []
with patch.object(socket, "socket", prohibit), patch.object(subprocess, "Popen", prohibit), \
        patch("builtins.open", prohibit), patch.object(Path, "open", prohibit):
    for name, sheet, expected in loaded:
        before = deepcopy(sheet)
        actual = calculators[sheet["schema"]](sheet, parameters={})
        assert actual == expected, name
        assert sheet == before, name
        results.append({"case": name, "exact_saved_score_equality": True, "saved_sheet_unchanged": True})
print(json.dumps({"network_process_and_file_acquisition_prohibited": True, "results": results}, indent=2))
