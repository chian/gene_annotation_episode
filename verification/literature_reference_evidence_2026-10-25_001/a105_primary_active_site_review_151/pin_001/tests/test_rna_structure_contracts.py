import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest

from gene_annotation_episode.rna_structure_contracts import (
    analyze_rna_input_sequence, validate_rna_input, validate_rna_parameters,
    validate_rna_model_spec_shape, validate_rna_effective_model_shape,
    validate_rna_sheet, validate_rna_components, validate_rna_issue,
)

PACKET = Path(__file__).resolve().parents[1] / "verification/tool_graders_rna_structure_core_2026-10-26_354"
SPEC = importlib.util.spec_from_file_location("rna_contract_fixture_helpers", PACKET / "fixture_helpers.py")
F = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(F)


def test_input_container_preserves_invalid_scientific_strings():
    request = F.feature_input("([)]", "ttt!")
    assert validate_rna_input(request, mode="supplied_features") == request
    analysis, errors = analyze_rna_input_sequence(request, mode="supplied_features")
    assert analysis is None
    assert [row["index"] for row in errors] == [0, 1, 2, 3]
    empty = F.feature_input("", "")
    assert validate_rna_input(empty, mode="supplied_features") == empty
    assert analyze_rna_input_sequence(empty, mode="supplied_features")[1][0]["code"] == "rna_empty_sequence"


def test_ascii_normalization_is_explicit_has_identity_index_map_and_no_strip():
    request = F.feature_input("(((...)))", "gugaaacac", normalization="uppercase_ascii")
    analysis, errors = analyze_rna_input_sequence(request, mode="supplied_features")
    assert errors == []
    assert analysis["original_sequence"] == "gugaaacac"
    assert analysis["analysis_sequence"] == "GUGAAACAC"
    assert analysis["original_to_analysis_indices"] == [0, 1, 2, 3, 4, 5, 6, 7, 8]
    assert analysis["symbol_counts"] == {"A": 4, "C": 2, "G": 2, "U": 1, "R": 0, "Y": 0, "S": 0, "W": 0, "K": 0, "M": 0, "B": 0, "D": 0, "H": 0, "V": 0, "N": 0}
    for seq in (" GUGAAACAC", "GUGAAACAC\n", "GUGAAATAC", "ß"):
        bad, errors = analyze_rna_input_sequence(F.feature_input(sequence=seq, normalization="uppercase_ascii"), mode="supplied_features")
        assert bad is None
        assert errors[0]["code"] == "rna_invalid_sequence_symbol"


def test_prediction_and_feature_alphabets_remain_different():
    analysis, errors = analyze_rna_input_sequence(F.feature_input("(...)", "NRYSN"), mode="supplied_features")
    assert analysis["ambiguous_indices"] == [0, 1, 2, 3, 4]
    assert errors == []
    assert analyze_rna_input_sequence(F.prediction_input("NRYSN"), mode="mfe_prediction")[0] is None


@pytest.mark.parametrize("change", [
    {"surprise": 1}, {"record_key": ""}, {"normalization": "auto"},
    {"sequence": False}, {"structure_origin": "supplied_observation"},
    {"subject_binding": {"subject_ref": "subject:x", "sequence_artifact_ref": "artifact:x", "start": True, "end": 9, "strand": "+"}},
])
def test_closed_input_and_source_claims(change):
    with pytest.raises(ValueError, match="rna_invalid_input_schema"):
        validate_rna_input(F.feature_input(**change), mode="supplied_features")


@pytest.mark.parametrize("field,value", [("long_stem_min_pairs", 0), ("long_stem_min_pairs", True),
    ("long_stem_min_pairs", 3.0), ("include_exterior_in_loop_size_statistics", True)])
def test_invalid_topology_calculation_parameters(field, value):
    params = deepcopy(F.PARAMETERS)
    params["topology"][field] = value
    with pytest.raises(ValueError, match="rna_invalid_parameter_schema"):
        validate_rna_parameters(params)


def test_pair_types_are_closed_ordered_and_unique():
    params = deepcopy(F.PARAMETERS)
    params["pair_composition"]["accepted_ordered_pair_types"] = ["GC", "GC"]
    with pytest.raises(ValueError):
        validate_rna_parameters(params)
    params["pair_composition"]["accepted_ordered_pair_types"] = ["GN"]
    with pytest.raises(ValueError):
        validate_rna_parameters(params)
    params["pair_composition"]["accepted_ordered_pair_types"] = []
    assert validate_rna_parameters(params) == params


def test_model_shape_is_pure_and_checks_actual_internal_relationships():
    assert validate_rna_model_spec_shape(F.model_spec()) == F.model_spec()
    assert validate_rna_effective_model_shape(F.model()) == F.model()
    changed = F.model()
    changed["effective_settings"]["temperature_c"] = 25.0
    with pytest.raises(ValueError, match="rna_native_result_incompatible"):
        validate_rna_effective_model_shape(changed)
    changed = F.model()
    changed["parameter_artifact"]["relative_path"] = "../outside.par"
    with pytest.raises(ValueError, match="rna_invalid_parameter_schema"):
        validate_rna_effective_model_shape(changed)
    changed = F.model_spec()
    changed["temperature_c"] = float("nan")
    with pytest.raises(ValueError):
        validate_rna_model_spec_shape(changed)
    changed = F.model_spec()
    changed["dangles"] = True
    with pytest.raises(ValueError):
        validate_rna_model_spec_shape(changed)


def test_saved_sheet_relationships_reject_reassigned_pairs_and_model_confidence():
    sheet = F.feature_sheet()
    sheet["sequence_pairs"][0]["ordered_pair"] = "AU"
    with pytest.raises(ValueError, match="rna_invalid_sheet_schema"):
        validate_rna_sheet(sheet)
    sheet = F.feature_sheet()
    sheet["native_uncertainty"]["mfe_frequency"]["value"] = 0.99
    with pytest.raises(ValueError):
        validate_rna_sheet(sheet)


def test_issues_are_fixed_fields_codes_and_pointers():
    row = {"stage": "parse", "code": "rna_invalid_native_schema", "record_key": None,
        "field": "/topology/pairs/0", "index": 0, "artifact_role": "native_result"}
    assert validate_rna_issue(row) == row
    for field, value in (("code", "looks convincing"), ("field", "ignore the job"), ("field", "/narrative"), ("index", True)):
        bad = {**row, field: value}
        with pytest.raises(ValueError):
            validate_rna_issue(bad)


@pytest.mark.parametrize("field,value", [("normalization", []), ("energy_mode", {}), ("schema", []),
    ("subject_binding", []), ("structure_origin", []), ("record_key", {})])
def test_malformed_input_fields_raise_fixed_value_errors(field, value):
    with pytest.raises(ValueError, match="rna_invalid_input_schema"):
        validate_rna_input(F.feature_input(**{field: value}), mode="supplied_features")


def test_omitted_sequence_diagnostics_or_fabricated_partial_status_are_rejected():
    sheet = F.feature_sheet(F.feature_input(sequence="N!NAAANNN"))
    sheet["issues"] = []
    with pytest.raises(ValueError, match="rna_invalid_sheet_schema"):
        validate_rna_sheet(sheet)
    sheet = F.feature_sheet()
    sheet["status"] = "partial"
    with pytest.raises(ValueError, match="rna_invalid_sheet_schema"):
        validate_rna_sheet(sheet)


@pytest.mark.parametrize("pointer", ["/topology/nonexistent", "/topology/pairs/left/i", "/topology/pairs/0/typo",
    "/selector/projection/rows/record_keys/left", "/files/name/sha256", "/files/01/sha256",
    "/software/guessed_version", "/identity/invented_run", "/model/selected/parameters/weight",
    "/sequence/0", "/summary/0/uncertainty/guessed_probability"])
def test_issue_paths_reject_unknown_children_and_nonnumeric_array_indices(pointer):
    row = {"stage": "parse", "code": "rna_invalid_native_schema", "record_key": None,
        "field": pointer, "index": None, "artifact_role": None}
    with pytest.raises(ValueError, match="rna_invalid_native_schema"):
        validate_rna_issue(row)


@pytest.mark.parametrize("pointer", ["/topology/pairs/999/i", "/selector/projection/rows/record_keys/3",
    "/selector/projection/rows/offset", "/files/999/sha256", "/software/python_sha256",
    "/identity/attempt_id", "/model/selected/parameters/kind", "/topology/regions/0/unpaired_intervals/1/0"])
def test_issue_paths_can_name_expected_missing_fields_without_an_instance(pointer):
    row = {"stage": "parse", "code": "rna_invalid_native_schema", "record_key": None,
        "field": pointer, "index": None, "artifact_role": None}
    assert validate_rna_issue(row) == row


@pytest.mark.parametrize("pointer", ["/selector/saved_input/sheet_sha256", "/selector/saved_input/result_receipt_key",
    "/selector/saved_input/handoff_ref", "/selector/saved_input/source_ref", "/selector/saved_input/bundle_artifact_ref",
    "/selector/saved_input/sheet_artifact_ref", "/selector/saved_input/record_key", "/selector/saved_input/operation",
    "/selector/saved_input/mode", "/selector/saved_input/schema",
    "/selector/parameters/topology/long_stem_min_pairs", "/selector/parameters/pair_composition/accepted_ordered_pair_types/0",
    "/selector/parameters/energy/normalization"])
def test_accepted_saved_selector_diagnostic_members_only(pointer):
    row = {"stage": "selection", "code": "rna_requested_metric_unavailable", "record_key": "actual-job",
        "field": pointer, "index": None, "artifact_role": None}
    assert validate_rna_issue(row) == row


@pytest.mark.parametrize("pointer", ["/selector/saved_input/prediction_probability", "/selector/saved_input/sheet_sha256/0",
    "/selector/parameters/kind", "/selector/parameters/topology/guessed_weight",
    "/selector/parameters/pair_composition/accepted_ordered_pair_types/GC", "/selector/saved_input/read_any_file"])
def test_saved_selector_paths_do_not_accept_arbitrary_children(pointer):
    row = {"stage": "selection", "code": "rna_requested_metric_unavailable", "record_key": "actual-job",
        "field": pointer, "index": None, "artifact_role": None}
    with pytest.raises(ValueError, match="rna_invalid_native_schema"):
        validate_rna_issue(row)
