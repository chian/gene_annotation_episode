"""Numerical handoffs over retained actual compiled outputs; no episode claim."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from gene_annotation_episode.episodic_workflow.root.library import infernal_preparation_models as models
from gene_annotation_episode.episodic_workflow.root.library import infernal_preparation_statistics as statistics
from gene_annotation_episode.episodic_workflow.root.library import infernal_preparation_emission as emission
from gene_annotation_episode.episodic_workflow.root.library import infernal_preparation_artifacts as artifacts
from gene_annotation_episode.episodic_workflow.root.library.infernal_preparation_schema import field_input, locator, value
from gene_annotation_episode.episodic_workflow.root.library.native_infernal_preparation_worker import (
    grade_infernal_preparation, recalculate_infernal_preparation,
)


ROOT = Path(__file__).resolve().parents[1]
INDEX = json.loads((ROOT / "gene_annotation_episode/episodic_workflow/root/a107/tests/fixtures/infernal_preparation/compiled/NATIVE_COMPILED_INDEX_001.json").read_text())
CASES = INDEX["cases"]


def payload(raw, role, fmt, ref, completeness="complete"):
    return {"artifact": {"role": role, "format": fmt, "artifact_ref": ref,
                          "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
                          "completeness": completeness}, "content": raw}


def prepared(case):
    request_raw = (ROOT / case["request_path"]).read_bytes()
    command_raw = (ROOT / case["compiled_path"]).read_bytes()
    assert hashlib.sha256(request_raw).hexdigest() == case["request_sha256"]
    assert hashlib.sha256(command_raw).hexdigest() == case["compiled_sha256"]
    request, command = json.loads(request_raw), json.loads(command_raw)
    inputs, outputs = {}, {}
    for direction, mapping in (("inputs", inputs), ("outputs", outputs)):
        for record in case[direction]:
            raw = (ROOT / record.get("retained_path", record["path"])).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == record["sha256"] and len(raw) == record["size_bytes"]
            mapping.setdefault(record["role"], []).append(payload(raw, record["role"], record["format"],
                direction + ":" + record["role"] + ":" + str(record.get("ordinal", 0))))
    if case["program"] == "cmfetch" and case["mode"] == "single_key":
        inputs["request"] = [payload(request_raw, "request", "infernal_request_json", "original_request")]
    return {"operation": command["operation"], "inputs": inputs, "outputs": outputs,
            "parameters": request["grading_parameters"]}


def deny(*args, **kwargs):
    pytest.fail("a supplied-data grader attempted an unrelated execution or parser")


def all_cells(calculation, name):
    return [row["components"][name] for row in calculation["rows"] if name in row["components"]]


def numbers(calculation, name):
    return [cell["value"] for cell in all_cells(calculation, name) if cell["state"] == "present"]


def case_for(program, mode):
    return next(c for c in CASES if (c["program"], c["mode"]) == (program, mode))


@pytest.mark.parametrize("state", ["missing", "not_measured", "failed", "truncated", "incompatible", "invalid"])
def test_value_qualification_does_not_coerce_unavailability_to_zero(state):
    where = locator("source", 0, line_start=1, line_end=1)
    missing = value(state=state, inputs=[field_input(where, "native_cell")])
    assert missing["state"] == state and missing["value"] is None
    zero = value(0, inputs=[field_input(where, "native_cell")], native_token="0")
    assert zero["state"] == "present" and zero["value"] == 0
    with pytest.raises(ValueError):
        value(0, state=state)


@pytest.mark.parametrize("number", [True, float("nan"), float("inf")])
def test_numeric_cell_rejects_booleans_and_nonfinite(number):
    with pytest.raises(ValueError):
        value(number)


def test_cell_invalid_explicit_state_and_unknown_units():
    with pytest.raises(ValueError):
        value(1, state="")
    with pytest.raises(ValueError):
        value(1, unit="biological_confidence")
