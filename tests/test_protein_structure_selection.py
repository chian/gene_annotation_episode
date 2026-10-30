"""Closed result requests, independent of episode authority or science execution."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.protein_structure_contracts import issue
from gene_annotation_episode.protein_structure_result_views import protein_structure_fact_sources
from gene_annotation_episode.protein_structure_selection import (
    protein_structure_result_selector_schema, validate_protein_structure_result_selector,
)

FIXTURES = Path(__file__).resolve().parents[1] / "verification/tool_graders_protein_structure_result_worker_2026-10-27_393/fixtures"


def native(name="held_out"):
    return json.loads((FIXTURES / (name + ".json")).read_bytes())


def file_identity(value, format):
    raw = canonical(value).encode("utf-8")
    checksum = hashlib.sha256(raw).hexdigest()
    return {"artifact_ref": "artifact_" + checksum, "sha256": checksum, "byte_length": len(raw), "format": format}


def projection(family="comparison_summary", *, name="requested"):
    members, fields = {
        "comparison_summary": ({"kind": "comparison"}, ["evaluation_rmsd"]),
        "structure_inventory": ({"kind": "all_inventory_rows"}, ["model"]),
        "extracted_sequence": ({"kind": "extracted_sequence", "residue_positions": {"kind": "all"}}, ["sequence_length"]),
        "native_uncertainty": ({"kind": "atom_uncertainty", "structure_role": "single", "atom_row_keys": ["atom_0"]}, ["plddt"]),
    }[family]
    return {"projection_id": name, "family": family, "members": members, "fields": fields,
        "window": None, "delivery_kind": "values"}


def selector(family="comparison_summary"):
    return {"version": "protein_structure_result_selector_v1", "acquisition": "complete_bound_bundle",
        "saved_sheet": None, "parameters": None, "projections": [projection(family)],
        "return_saved_sheet": False, "sequence_allowed_uses": []}


def saved():
    result = native()
    sheet = result["sheet"]
    value = selector()
    value.update(acquisition="retained_sheet_only", parameters=deepcopy(sheet["native_request"]),
        saved_sheet={"version": "protein_structure_saved_sheet_v1", "custody": {
            "run_id": "synthetic-selector-run", "result_episode_id": "synthetic-result",
            "result_operation_key": "synthetic-operation", "result_receipt_key": "protein_structure_result_receipt:" + digest({
                "run_id": "synthetic-selector-run", "episode_id": "synthetic-result", "operation_key": "synthetic-operation"}),
            "handoff_ref": "source_" + "1" * 24, "source_ref": "source_" + "2" * 24,
            "bundle_artifact_ref": "artifact_" + "3" * 64, "original_request_sha256": "4" * 64},
            "sheet_file": file_identity(sheet, "protein_structure_comparison_sheet_v1"),
            "original_components_file": file_identity(sheet["native_baseline"], "protein_structure_components_v1"),
            "operation": "compare_protein_structures", "original_mode": sheet["scientific_mode"],
            "allowed_uses": ["recalculate", "select_projection", "use_transform"]})
    return value, result["request"]


@pytest.mark.parametrize("fixture,family", [("held_out", "comparison_summary"),
    ("inspect", "structure_inventory"), ("extract", "extracted_sequence"), ("extract", "native_uncertainty")])
def test_each_original_operation_accepts_its_requested_fields(fixture, family):
    value = selector(family)
    original = deepcopy(value)
    result = validate_protein_structure_result_selector(value, request=native(fixture)["request"])
    assert result == original and result is not value
    result["projections"].clear()
    assert value == original


def test_original_parameters_are_exact_and_new_calculation_is_explicit():
    request = native()["request"]
    original = selector()
    original["parameters"] = deepcopy(request["parameters"])
    assert validate_protein_structure_result_selector(original, request=request) == original
    original["parameters"]["distance_threshold_A"] = 7.5
    with pytest.raises(ValueError, match="original_commission_mismatch"):
        validate_protein_structure_result_selector(original, request=request)
    later, request = saved()
    later["parameters"]["distance_threshold_A"] = 7.5
    assert validate_protein_structure_result_selector(later, request=request) == later
    assert request["parameters"]["distance_threshold_A"] != 7.5


@pytest.mark.parametrize("change", ["no_sheet", "no_parameters", "no_use", "sequence_use", "inventory", "extraction", "single_uncertainty"])
def test_saved_request_rejects_missing_inputs_and_noncomparison_fields(change):
    value, _ = saved()
    assert validate_protein_structure_result_selector(value) == value
    if change == "no_sheet": value["saved_sheet"] = None
    elif change == "no_parameters": value["parameters"] = None
    elif change == "no_use": value["saved_sheet"]["allowed_uses"] = ["select_projection"]
    elif change == "sequence_use": value["sequence_allowed_uses"] = ["sequence_align"]
    else:
        family = {"inventory": "structure_inventory", "extraction": "extracted_sequence", "single_uncertainty": "native_uncertainty"}[change]
        value["projections"] = [projection(family)]
    with pytest.raises(ValueError):
        validate_protein_structure_result_selector(value)


@pytest.mark.parametrize("fixture,family", [("inspect", "comparison_summary"),
    ("extract", "structure_inventory"), ("held_out", "extracted_sequence"), ("held_out", "structure_inventory")])
def test_original_operation_rejects_unrelated_projection_family(fixture, family):
    with pytest.raises(ValueError):
        validate_protein_structure_result_selector(selector(family), request=native(fixture)["request"])


@pytest.mark.parametrize("fixture,role", [("extract", "fixed"), ("held_out", "single")])
def test_uncertainty_has_original_operation_role(fixture, role):
    value = selector("native_uncertainty")
    value["projections"][0]["members"]["structure_role"] = role
    with pytest.raises(ValueError, match="conflicting_identity"):
        validate_protein_structure_result_selector(value, request=native(fixture)["request"])


@pytest.mark.parametrize("change", ["unknown", "tuple", "count_float", "count_bool", "unknown_field", "duplicate_id", "bool_flag", "nan", "huge_real"])
def test_strict_shape_and_numerical_meaning(change):
    value = selector()
    if change == "unknown": value["findings"] = "extra"
    elif change == "tuple": value["projections"] = tuple(value["projections"])
    elif change in {"count_float", "count_bool"}:
        value["projections"][0]["window"] = {"offset_0based": 0.0 if change == "count_float" else False, "limit": 2}
    elif change == "unknown_field": value["projections"][0]["fields"] = ["annotation_confidence"]
    elif change == "duplicate_id": value["projections"].append(deepcopy(value["projections"][0]))
    elif change == "bool_flag": value["return_saved_sheet"] = 1
    else:
        value["parameters"] = deepcopy(native()["request"]["parameters"])
        value["parameters"]["distance_threshold_A"] = float("nan") if change == "nan" else 10 ** 1000
    with pytest.raises(ValueError):
        validate_protein_structure_result_selector(value)


def test_descriptor_only_return_and_extraction_uses_remain_explicit():
    value = selector()
    value.update(projections=[], return_saved_sheet=True)
    assert validate_protein_structure_result_selector(value, request=native()["request"]) == value
    extracted = selector("extracted_sequence")
    extracted["sequence_allowed_uses"] = ["structure_correspondence", "sequence_align"]
    assert validate_protein_structure_result_selector(extracted, request=native("extract")["request"]) == extracted
    for fixture in ("held_out", "inspect"):
        with pytest.raises(ValueError):
            validate_protein_structure_result_selector(extracted, request=native(fixture)["request"])


def test_saved_original_mode_and_structure_selection_cannot_change():
    value, request = saved()
    value["saved_sheet"]["original_mode"] = "evaluate_declared_transform_ca"
    with pytest.raises(ValueError, match="original_commission_mismatch"):
        validate_protein_structure_result_selector(value, request=request)
    with pytest.raises(ValueError, match="original_commission_mismatch"):
        validate_protein_structure_result_selector(saved()[0], request=native("inspect")["request"])


def test_schema_contains_exact_reachable_definitions_only():
    schema = protein_structure_result_selector_schema()
    Draft202012Validator.check_schema(schema)
    original = protein_structure_fact_sources()["execution_protein_structure_projections"]["report_schema"]["$defs"]
    assert len(schema["$defs"]) < len(original)
    assert all(value == original[name] for name, value in schema["$defs"].items())
    assert "ProteinStructureComponents" not in schema["$defs"]
    assert schema["$id"] == "urn:gene-annotation:protein-structure:schema:" + digest({k:v for k,v in schema.items() if k != "$id"})
    schema["$defs"]["ProteinResultSelector"]["additionalProperties"] = True
    assert protein_structure_result_selector_schema()["$defs"]["ProteinResultSelector"]["additionalProperties"] is False


def test_pure_validation_uses_neither_io_nor_calculators(monkeypatch):
    from gene_annotation_episode import protein_structure_calculations as calculations
    value, request = saved()
    def forbidden(*args, **kwargs):
        raise AssertionError("selector validation attempted I/O or calculation")
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(calculations, "calculate_protein_structure_components", forbidden)
    monkeypatch.setattr(calculations, "fit_ca_transform", forbidden)
    assert validate_protein_structure_result_selector(value, request=request) == value


def test_structured_operand_error_preserves_exact_issue_and_detached_detail():
    problem = issue("sequence_not_received", stage="authority", field="descriptor")
    error = ProteinStructureOperandError(problem)
    assert str(error) == "sequence_not_received"
    assert error.issue == problem and error.detail == {"protein_structure_issue": problem}
    problem["code"] = "invalid_schema"
    assert error.issue["code"] == "sequence_not_received"
    error.issue["code"] = "invalid_schema"
    assert error.detail["protein_structure_issue"]["code"] == "sequence_not_received"
    with pytest.raises(ValueError, match="invalid_schema"):
        ProteinStructureOperandError({"code": "made_up"})
