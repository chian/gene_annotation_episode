"""D1 composition against retained native259/267/270 bytes, without native calls."""
from copy import deepcopy
import builtins
import hashlib
import json
import math
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.jobs.profile_model_preparation.sequence_homology_evidence import native_hmmer_preparation_worker as worker
from gene_annotation_episode.episodic_workflow.episode_support.forms.profile_model_preparation.sequence_homology_evidence.native_hmmer_preparation_contracts import PROGRAM_MODES
from gene_annotation_episode.episodic_workflow.episode_support.calculations.profile_model_preparation.sequence_homology_evidence.hmmer_statistics_calculations import native_hmmstat_parameters


ROOT = Path(__file__).resolve().parents[7]
NATIVE = ROOT / "gene_annotation_episode/episodic_workflow/episode_support/readers/profile_model_preparation/tests/fixtures/hmmer_preparation_contracts/native"


def payload(content, role, direction, ordinal=0, identity=None, completeness="complete"):
    oid = identity or direction + "/" + role + "/" + str(ordinal)
    return {"occurrence": {"occurrence_id": oid, "direction": direction, "role": role,
        "ordinal": ordinal, "artifact_ref": "retained:" + oid,
        "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content),
        "completeness": completeness}, "content": content}


def arguments(operation, inputs, outputs, role_formats, *, metadata=None, parameters=None, abi=None):
    return {"operation": operation, "inputs": inputs, "outputs": outputs,
        "formats": {p["occurrence"]["occurrence_id"]: role_formats[(direction, role)]
                    for direction, mapping in (("input", inputs), ("output", outputs))
                    for role, values in mapping.items() for p in values},
        "metadata": {} if metadata is None else metadata,
        "parameters": {} if parameters is None else parameters, "native_abi": deepcopy(abi)}


def dna_statistics():
    model = payload((NATIVE / "hmmbuild_dna/profile.hmm").read_bytes(), "models", "input")
    summary = payload((NATIVE / "hmmstat_dna/stdout.log").read_bytes(), "stdout", "output")
    return arguments({"program": "hmmstat", "mode": "summary", "engine_version": "3.4", "settings": {}},
        {"models": [model]}, {"stdout": [summary]},
        {("input", "models"): "hmmer3_ascii", ("output", "stdout"): "hmmer_stdout"},
        parameters=native_hmmstat_parameters("3.4", "DNA"))


def rows(grading, kind):
    return [row for row in grading["calculations"]["rows"] if row.get("kind") == kind]


def test_statistics_independent_kl_and_no_implicit_background():
    args = dna_statistics()
    result = worker.grade_hmmer_preparation(**args)
    component = result["calculations"]["rows"][0]["components"]["mean_match_relative_entropy"]
    assert component["value"] == pytest.approx(1.0074921672642938, abs=1e-13)
    # Direct calculation from the retained native tokens, independent of M1/H1 arithmetic.
    model = args["inputs"]["models"][0]["content"].decode().splitlines()
    costs = [list(map(float, line.split()[1:5])) for line in model
             if line.split() and line.split()[0].isdigit()]
    manual = sum(sum(math.exp(-x) * math.log2(math.exp(-x) / .25) for x in p) for p in costs) / 12
    assert component["value"] == pytest.approx(manual, abs=1e-13)
    assert {o["role"] for o in result["sheet"]["artifact_occurrences"]} == {"models", "stdout"}
    args["parameters"] = {}
    unknown = worker.grade_hmmer_preparation(**args)
    assert unknown["requested_parameters"] == {}
    assert unknown["calculations"]["parameters"]["background"] is None
    assert unknown["calculations"]["rows"][0]["components"]["mean_match_relative_entropy"]["value"] is None


def test_negative_parameters_keep_unaffected_statistics_and_original_request():
    args = dna_statistics()
    args["parameters"]["length_probability"] = -1
    result = worker.grade_hmmer_preparation(**args)
    c = result["calculations"]["rows"][0]["components"]
    assert c["position_relative_entropy"]["state"] == "incompatible"
    assert c["mean_match_relative_entropy"]["value"] == pytest.approx(1.0074921672642938)
    assert result["requested_parameters"]["length_probability"] == -1


@pytest.mark.parametrize("change", ["schema", "program", "extra_field", "unknown_parameter", "infinite_parameter"])
def test_recalculation_rejects_wrong_saved_contract(change):
    result = worker.grade_hmmer_preparation(**dna_statistics())
    parameters = {}
    if change == "schema": result["sheet"]["schema"] = "hmmer_emission_sheet"
    elif change == "program": result["sheet"]["operation"].update(program="hmmemit", mode="consensus_simple")
    elif change == "extra_field": result["sheet"]["score_rules"] = {}
    elif change == "unknown_parameter": parameters["confidence"] = .5
    elif change == "infinite_parameter": parameters["length_probability"] = float("inf")
    with pytest.raises(worker.ContractError):
        worker.recalculate_hmmer_preparation(result["sheet"], parameters=parameters)

