"""Public grading dispatch against saved actual native numerical examples."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.hmmer_graders import grade_hmmer_native_artifacts


ROOT = Path(__file__).resolve().parents[1] / "verification"
CASES = [
    ("phmmer", ROOT / "tool_graders_hmmer_search_2026-10-24/phmmer.sheet.json"),
    ("hmmscan", ROOT / "tool_graders_hmmer_search_2026-10-24/hmmscan.sheet.json"),
    ("hmmsearch", ROOT / "tool_graders_hmmer_search_2026-10-24/hmmsearch.sheet.json"),
    ("jackhmmer", ROOT / "tool_graders_hmmer_search_2026-10-24/jackhmmer.sheet.json"),
    ("nhmmer", ROOT / "tool_graders_nhmmer_2026-10-24/nhmmer_sequence/sheet.json"),
    ("nhmmscan", ROOT / "tool_graders_nhmmer_2026-10-24/nhmmscan/sheet.json"),
    ("hmmalign", ROOT / "tool_graders_hmmalign_2026-10-24/saved/ordinary/sheet.json"),
]


@pytest.mark.parametrize("program,path", CASES, ids=[row[0] for row in CASES])
def test_dispatch_reproduces_saved_native_numerical_components(program, path, monkeypatch):
    saved = json.loads(path.read_text())
    scores_path = path.with_name(path.name.replace("sheet.json", "scores.json"))
    expected = json.loads(scores_path.read_text())
    if program == "hmmalign":
        native = saved["native_result"]
        artifacts, refs = native["artifacts"], native["artifact_refs"]
        keys = ("sequences", "columns", "summary")
    else:
        native = saved.get("native", saved)
        artifacts = {role: value["text"] for role, value in native["artifacts"].items()}
        refs = {role: value["artifact_ref"] for role, value in native["artifacts"].items()}
        keys = ("loci", "queries") if program.startswith("nhmm") else ("hits", "domains", "queries")
    inputs = deepcopy(saved["inputs"])
    before = deepcopy((artifacts, refs, inputs))
    def prohibited(*args, **kwargs):
        pytest.fail("A supplied native grading request attempted acquisition or execution")
    monkeypatch.setattr(socket, "socket", prohibited)
    monkeypatch.setattr(subprocess, "Popen", prohibited)
    monkeypatch.setattr(Path, "read_text", prohibited)
    monkeypatch.setattr(Path, "read_bytes", prohibited)
    actual = grade_hmmer_native_artifacts(program=program, artifacts=artifacts,
        artifact_refs=refs, engine_version="3.4", inputs=inputs)
    assert actual["sheet"]["operation"]["program"] == program
    assert actual["scores"]["schema"] == expected["schema"]
    for key in keys:
        assert actual["scores"][key] == expected[key]
    assert (artifacts, refs, inputs) == before


def test_profile_alignment_rejects_a_log_mislabeled_as_an_alignment():
    with pytest.raises(ValueError, match="hmmalign_stockholm_artifact_required"):
        grade_hmmer_native_artifacts(program="hmmalign", artifacts={"stdout": "log"},
            artifact_refs={"stdout": "original-log"}, engine_version="3.4", inputs={})


def test_unknown_program_does_not_select_another_algorithm():
    with pytest.raises(ValueError, match="hmmer_grading_program_unsupported"):
        grade_hmmer_native_artifacts(program="other", artifacts={},
            artifact_refs={}, engine_version=None, inputs={})
