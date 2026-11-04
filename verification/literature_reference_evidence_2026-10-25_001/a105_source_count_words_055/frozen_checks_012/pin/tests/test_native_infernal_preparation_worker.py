"""Numerical handoffs over retained actual compiled outputs; no episode claim."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from gene_annotation_episode import infernal_preparation_models as models
from gene_annotation_episode import infernal_preparation_statistics as statistics
from gene_annotation_episode import infernal_preparation_emission as emission
from gene_annotation_episode import infernal_preparation_artifacts as artifacts
from gene_annotation_episode.infernal_preparation_schema import field_input, locator, value
from gene_annotation_episode.native_infernal_preparation_worker import (
    grade_infernal_preparation, recalculate_infernal_preparation,
)


ROOT = Path(__file__).resolve().parents[1]
INDEX = json.loads((ROOT / "verification/tool_graders_infernal_preparation_2026-10-26_247/NATIVE_COMPILED_INDEX_001.json").read_text())
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


@pytest.mark.parametrize("case", CASES, ids=[r["program"] + "-" + r["mode"] for r in CASES])
def test_real_compiled_artifacts_populate_separate_sheets_and_recalculate_without_parser(case, monkeypatch, tmp_path):
    supplied = prepared(case)
    original = deepcopy(supplied)
    monkeypatch.setattr(subprocess, "run", deny)
    result = grade_infernal_preparation(**supplied)
    assert supplied == original
    assert result["operation"] == supplied["operation"]
    assert result["sheet"]["operation"] == result["calculations"]["operation"]
    assert result["calculations"]["parameters"] == supplied["parameters"]
    assert "subject_ref" not in json.dumps(result)
    # Persist filled examples, then forbid all three population/parser paths.
    target = tmp_path / (case["program"] + "-" + case["mode"] + ".json")
    target.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    saved = json.loads(target.read_text())
    for module, name in ((models, "extract_infernal_models"), (artifacts, "populate_infernal_artifact_sheet"),
                         (statistics, "populate_infernal_statistics_sheet"), (emission, "populate_cmemit_sheet")):
        monkeypatch.setattr(module, name, deny)
    assert recalculate_infernal_preparation(saved["sheet"], parameters=supplied["parameters"]) == saved["calculations"]


def case_for(program, mode):
    return next(c for c in CASES if (c["program"], c["mode"]) == (program, mode))


def test_known_generated_consensus_and_pair_counts_are_actual_quantities():
    result = grade_infernal_preparation(**prepared(case_for("cmemit", "consensus")))
    sequence = next(r for r in result["sheet"]["output_records"] if r["kind"] == "generated_sequence")
    assert sequence["sequence"] == "GCGCaaAAGCGC"
    assert sequence["origin"] == "generated_consensus"
    assert 12 in numbers(result["calculations"], "residue_count")
    assert 8 in numbers(result["calculations"], "gc_count")
    assert pytest.approx(2 / 3) in numbers(result["calculations"], "gc_fraction_canonical")
    build = grade_infernal_preparation(**prepared(case_for("cmbuild", "build")))
    native = next(r for r in build["sheet"]["native_rows"] if r["kind"] == "build")
    assert native["values"]["nseq"]["value"] == 3
    assert native["values"]["consensus_length"]["value"] == 12
    assert native["values"]["base_pairs"]["value"] == 4
    assert pytest.approx(2 / 3) in numbers(build["calculations"], "paired_consensus_fraction")


def test_zero_exit_does_not_erase_missing_fetch_request():
    result = grade_infernal_preparation(**prepared(case_for("cmfetch", "key_file")))
    assert numbers(result["calculations"], "requested_key_count") == [2]
    assert numbers(result["calculations"], "satisfied_key_count") == [1]
    assert numbers(result["calculations"], "missing_key_count") == [1]
    assert any(c["check"] == "requested_keys_satisfied" and c["outcome"] == "fail"
               for row in result["calculations"]["rows"] for c in row["checks"])


@pytest.mark.parametrize("fault", ["key", "argv", "malformed", "duplicate"])
def test_single_key_locator_cannot_claim_unrelated_request_bytes(monkeypatch, fault):
    from gene_annotation_episode.native_infernal_preparation_contracts import requested_job_from_infernal_preparation
    supplied = prepared(case_for("cmfetch", "single_key"))
    original = supplied["inputs"]["request"][0]
    job = json.loads(original["content"])
    if fault == "key":
        job["key"] = "a_different_requested_key"
        raw = json.dumps(job).encode()
    elif fault == "argv":
        request = requested_job_from_infernal_preparation(job)
        request["argv"][-1] = "a_different_requested_key"
        raw = json.dumps(request).encode()
    elif fault == "malformed":
        raw = b'{"not_a_request":true}'
    else:
        raw = b'{"key":"first","key":"second"}'
    supplied["inputs"]["request"] = [payload(raw, "request", "infernal_request_json", "original_request")]
    monkeypatch.setattr(artifacts, "populate_infernal_artifact_sheet", deny)
    with pytest.raises(ValueError):
        grade_infernal_preparation(**supplied)


def test_opaque_binary_population_not_invented():
    result = grade_infernal_preparation(**prepared(case_for("cmconvert", "binary")))
    assert numbers(result["calculations"], "input_model_count") == [1]
    assert not numbers(result["calculations"], "output_model_count")
    assert all(cell["state"] == "missing" for cell in all_cells(result["calculations"], "output_model_count"))


@pytest.mark.parametrize("mutation", ["bytes", "digest", "size", "role", "duplicate_ref"])
def test_custody_conflicts_reject_before_any_model_parser(monkeypatch, mutation):
    supplied = prepared(case_for("cmemit", "consensus"))
    member = supplied["inputs"]["models"][0]
    if mutation == "bytes":
        member["content"] += b"changed"
    elif mutation == "digest":
        member["artifact"]["sha256"] = "0" * 64
    elif mutation == "size":
        member["artifact"]["size_bytes"] += 1
    elif mutation == "role":
        member["artifact"]["role"] = "another_role"
    else:
        supplied["outputs"]["stdout"][0]["artifact"]["artifact_ref"] = member["artifact"]["artifact_ref"]
    monkeypatch.setattr(models, "extract_infernal_models", deny)
    with pytest.raises(ValueError):
        grade_infernal_preparation(**supplied)


def test_absent_generated_output_keeps_models_without_manufacturing_zero_population():
    supplied = prepared(case_for("cmemit", "consensus"))
    del supplied["outputs"]["generated_sequences"]
    result = grade_infernal_preparation(**supplied)
    assert len(result["sheet"]["input_records"]) == 1
    assert result["sheet"]["output_records"] == []
    assert result["calculations"]["rows"] == []
    assert any(i["code"] == "preparation_generated_output_missing" for i in result["sheet"]["issues"])
    assert recalculate_infernal_preparation(result["sheet"], parameters={}) == result["calculations"]


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
