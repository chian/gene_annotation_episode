from copy import deepcopy
import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.native_protein_structure_contracts import (
    validate_protein_structure_job, validate_protein_structure_request,
    validate_native_protein_structure_result, validate_protein_structure_requested_job,
    validate_protein_structure_run_plan, validate_protein_structure_bundle,
    validate_protein_structure_bindings, compile_protein_structure_job,
    requested_job_from_protein_structure, NATIVE_PROTEIN_STRUCTURE_REQUESTED_JOB_SCHEMA,
)
from importlib import import_module
_f = import_module("verification.tool_graders_protein_structure_execution_2026-10-27_390.fixture_helpers")
job, requests, software, plan = _f.job, _f.requests, _f.software, _f.plan


@pytest.mark.parametrize("kind", ["inspect", "extract_sequence", "compare"])
def test_requested_job_exact_command_and_detached(tmp_path, kind):
    original = job(tmp_path, kind=kind)
    requested = requested_job_from_protein_structure(original)
    checked = validate_protein_structure_requested_job(requested)
    assert checked == requested and checked is not requested
    assert requested["argv"] == [original["software"]["python_executable"], "-B", "-m", original["software"]["worker_module"],
        "--request-json", "worker-input.json", "--output-json", "result.json"]
    assert Draft202012Validator(NATIVE_PROTEIN_STRUCTURE_REQUESTED_JOB_SCHEMA).is_valid(requested)
    altered = deepcopy(requested)
    altered["argv"][0] = "/unselected/python"
    with pytest.raises(ValueError, match="original_commission_mismatch"):
        validate_protein_structure_requested_job(altered)


@pytest.mark.parametrize("change", ["role", "duplicate_path", "extra", "input_id", "staged", "output", "environment", "float_length", "bool_length"])
def test_reject_wrong_inputs_and_outputs(tmp_path, change):
    value = job(tmp_path)
    if change == "role": value["inputs"][0]["role"] = "single_structure"
    if change == "duplicate_path": value["inputs"][1]["path"] = value["inputs"][0]["path"]
    if change == "extra": value["inputs"].append(deepcopy(value["inputs"][0]))
    if change == "input_id": value["inputs"][0]["input_id"] = "input_9"
    if change == "staged": value["inputs"][0]["staged_relative_path"] = "../outside"
    if change == "output": value["outputs"][0]["relative_path"] = "preview.json"
    if change == "environment": value["environment"]["TMPDIR"] = "/tmp"
    if change == "float_length": value["inputs"][0]["file_identity"]["byte_length"] = 1.0
    if change == "bool_length": value["inputs"][0]["file_identity"]["byte_length"] = True
    with pytest.raises(ValueError): validate_protein_structure_job(value)


def test_mode_selection_and_software_binding(tmp_path):
    value = job(tmp_path)
    value["request"]["fixed_selection"]["structure_role"] = "moving"
    with pytest.raises(ValueError, match="conflicting_identity"): validate_protein_structure_job(value)
    selected = {"operation": "compare", "scientific_mode": "fit_then_evaluate_ca", "software": software()}
    assert validate_protein_structure_bindings([selected]) == [selected]
    with pytest.raises(ValueError): validate_protein_structure_bindings([selected, selected])
    with pytest.raises(ValueError): validate_protein_structure_bindings([{**selected, "scientific_mode": None}])
    with pytest.raises(ValueError): validate_protein_structure_bindings([])


def test_compile_confined_inputs_and_original_plan(tmp_path):
    value = job(tmp_path)
    selected = plan(tmp_path, value)
    validate_protein_structure_run_plan(selected)
    root = selected["attempt_directory"]
    mapping = {r["input_id"]: root + "/" + r["staged_relative_path"] for r in value["inputs"]}
    actual = compile_protein_structure_job(value, input_paths=mapping, output_directory=root)
    assert actual["argv"][-1] == root + "/result.json"
    with pytest.raises(ValueError): compile_protein_structure_job(value, input_paths={}, output_directory=root)
    mapping["input_0"] = "/elsewhere/data"
    with pytest.raises(ValueError): compile_protein_structure_job(value, input_paths=mapping, output_directory=root)
    selected["identity"]["attempt_id"] = "0" * 64
    with pytest.raises(ValueError, match="original_commission_mismatch"): validate_protein_structure_run_plan(selected)


def test_native_envelope_rejects_wrong_tag_and_unlisted_fields():
    request, _ = requests()
    native = {"version": "protein_structure_native_v1", "producer": software(), "request": request,
        "sheet": None, "state": "invalid", "issues": [{"stage": "native", "code": "native_process_failed",
            "structure_role": None, "position_key": None, "atom_row_key": None, "correspondence_id": None,
            "field": None, "artifact_role": None}]}
    assert validate_native_protein_structure_result(native) == native
    for changed in [{**native, "unexpected": "x"}, {**native, "version": "protein_structure_sequence_native_v1"},
                    {**native, "state": "complete"}, {**native, "issues": []}]:
        with pytest.raises(ValueError): validate_native_protein_structure_result(changed)


def test_pure_plan_rejects_noncanonical_action_identity_path(tmp_path):
    selected = plan(tmp_path, job(tmp_path))
    selected["identity"]["execution_id"] = str(tmp_path / "arbitrary-action-root" / "native.json")
    selected["attempt_directory"] = str(tmp_path / "arbitrary-action-root" / "protein-structure-attempt")
    with pytest.raises(ValueError, match="original_commission_mismatch"):
        validate_protein_structure_run_plan(selected)
