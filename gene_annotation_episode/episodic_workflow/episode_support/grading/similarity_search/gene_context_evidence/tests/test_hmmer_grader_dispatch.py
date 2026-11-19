"""The A103 native HMMER dispatch (restored at 97308b94c text) against saved actual native numerical examples: nhmmer
goes through the shared full ``nhmmer_grader.calculate_nhmmer_scores``; a log is never graded as an alignment."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.gene_context_evidence.hmmer_graders import grade_hmmer_native_artifacts


SEARCH = Path(__file__).resolve().parents[7] / "gene_annotation_episode/episodic_workflow/episode_support/readers/similarity_search/tests/fixtures/hmmer_search"
NHMMER = Path(__file__).resolve().parents[7] / "gene_annotation_episode/episodic_workflow/episode_support/grading/similarity_search/sequence_homology_evidence/tests/fixtures/nhmmer"
CASES = [
    ("phmmer", SEARCH / "phmmer.sheet.json"),
    ("hmmscan", SEARCH / "hmmscan.sheet.json"),
    ("hmmsearch", SEARCH / "hmmsearch.sheet.json"),
    ("jackhmmer", SEARCH / "jackhmmer.sheet.json"),
    ("nhmmer", NHMMER / "nhmmer_sequence/sheet.json"),
    ("nhmmscan", NHMMER / "nhmmscan/sheet.json"),
    ("hmmalign", Path(__file__).resolve().parents[7] / "gene_annotation_episode/episodic_workflow/episode_support/grading/similarity_search/sequence_homology_evidence/tests/fixtures/hmmalign_native/saved/ordinary/sheet.json"),
]


@pytest.mark.parametrize("program,path", CASES, ids=[row[0] for row in CASES])
def test_dispatch_reproduces_saved_native_numerical_components(program, path):
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
