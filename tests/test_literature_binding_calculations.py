"""Synthetic normalized binding rows; no acquired paper or source packets."""
from copy import deepcopy
import json
import math

import pytest

from gene_annotation_episode.literature_binding_calculations import (
    COMPONENTS, FORMULAS, UNAVAILABLE_REASONS, populate_binding_contrast,
)
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def row(value, *, index=0, relation="eq", spread=None, ligand="reference"):
    prefix = {"eq": "", "gt": ">", "ge": ">=", "lt": "<", "le": "<="}
    expression = "n.d." if relation == "unreported" else prefix[relation] + str(value)
    if spread is not None:
        expression += " ± " + str(spread)
    return {
        "value": value, "relation": relation, "reported_spread": spread,
        "origin": "synthetic", "subject": "synthetic protein", "state": "apo",
        "experiment": "synthetic competition", "ligand": ligand,
        "source": {
            "source_ref": "synthetic source", "artifact_ref": "synthetic table",
            "representation": "synthetic_fixture", "table_id": "synthetic table 1",
            "row_index": index, "locator": {"row_index": index, "column": "IC50"},
            "expression": expression,
        },
    }


def extraction(reference=None, test=None):
    return {
        "version": "binding_parameter_extraction_v1", "parameter_kind": "ic50",
        "unit": "nM", "uncertainty_basis": "fit_to_averaged_curve",
        "minimum_experiment_count": 3,
        "reference_rows": [row(40, spread=4)] if reference is None else reference,
        "test_rows": [row(120, index=1, ligand="test")] if test is None else test,
    }


def test_point_cells_keep_raw_spread_and_minimum_count_without_statistical_claims():
    inputs = extraction()
    before = deepcopy(inputs)
    sheet = populate_binding_contrast(inputs)
    assert inputs == before
    assert set(sheet) == {
        "version", "parameter_kind", "unit", "reference_rows", "test_rows",
        "uncertainty_basis", "minimum_experiment_count", "independent_preparation_count",
        "cells", "annotation_credit",
    }
    assert sheet["version"] == "binding_parameter_sheet_v1"
    assert set(sheet["cells"]) == set(COMPONENTS)
    assert sheet["cells"]["reference_parameter"]["value"] == 40
    assert sheet["cells"]["reference_reported_spread"]["value"] == 4
    assert sheet["cells"]["reference_relative_spread"]["value"] == .1
    assert sheet["cells"]["native_parameter_ratio"]["value"] == 3
    assert sheet["cells"]["log_native_parameter_ratio"]["value"] == pytest.approx(math.log(3))
    assert sheet["cells"]["test_reported_spread"]["value"] is None
    assert sheet["cells"]["test_reported_spread"]["unavailable_reason"] == "reported_spread_unavailable"
    assert sheet["minimum_experiment_count"] == 3
    assert sheet["independent_preparation_count"] is None
    assert sheet["annotation_credit"] is None
    assert sheet["uncertainty_basis"] == "fit_to_averaged_curve"
    for name, cell in sheet["cells"].items():
        assert set(cell) == {
            "value", "relation", "unit", "status", "formula", "origin", "unavailable_reason",
            "bound_kind", "confidence_bound", "parameter_identification_bound",
        }
        assert cell["confidence_bound"] is cell["parameter_identification_bound"] is None
        assert cell["origin"] in ("derived", "proposed")
        assert cell["formula"] == FORMULAS[name]
        assert cell["unavailable_reason"] is None or cell["unavailable_reason"] in UNAVAILABLE_REASONS
        if name in ("source_profile_log_ratio", "source_signed_index"):
            assert cell["status"] == "unavailable"
            assert cell["unavailable_reason"] == "binding_observation_model_unimplemented"
        elif cell["value"] is not None:
            assert cell["status"] == "populated"
            assert cell["relation"] == "eq"
    sheet["reference_rows"][0]["source"]["expression"] = "detached output"
    assert inputs == before


@pytest.mark.parametrize("arm,relation,expected", [
    ("test", "gt", "gt"), ("test", "ge", "ge"),
    ("test", "lt", "lt"), ("test", "le", "le"),
    ("reference", "gt", "lt"), ("reference", "ge", "le"),
    ("reference", "lt", "gt"), ("reference", "le", "ge"),
])
def test_all_one_limit_directions_are_reported_arithmetic(arm, relation, expected):
    inputs = extraction()
    inputs[arm + "_rows"][0].update(relation=relation, reported_spread=None)
    cells = populate_binding_contrast(inputs)["cells"]
    assert cells[arm + "_parameter"]["relation"] == relation
    for name, value in (("native_parameter_ratio", 3),
                        ("log_native_parameter_ratio", math.log(3))):
        cell = cells[name]
        assert cell["relation"] == expected
        assert cell["value"] == pytest.approx(value)
        assert cell["status"] == "reported_limit"
        assert cell["bound_kind"] == "reported_limit_arithmetic"
        assert cell["confidence_bound"] is cell["parameter_identification_bound"] is None
    assert cells[arm + "_reported_spread"]["unavailable_reason"] == "reported_spread_requires_point_operand"


@pytest.mark.parametrize("reference_relation,test_relation", [
    (a, b) for a in ("gt", "ge", "lt", "le") for b in ("gt", "ge", "lt", "le")
])
def test_two_limits_preserve_native_partial_cells(reference_relation, test_relation):
    inputs = extraction([row(4, relation=reference_relation)],
                        [row(8, relation=test_relation, index=1)])
    cells = populate_binding_contrast(inputs)["cells"]
    assert cells["reference_parameter"]["value"] == 4
    assert cells["test_parameter"]["value"] == 8
    for name in ("native_parameter_ratio", "log_native_parameter_ratio"):
        assert cells[name]["value"] is None
        assert cells[name]["status"] == "unavailable"
        assert cells[name]["relation"] == "unreported"
        assert cells[name]["unavailable_reason"] == "two_censored_operands_unsupported"


@pytest.mark.parametrize("rows,reason", [([], "missing_reference_arm"),
    ([row(None, relation="unreported")], "source_measurement_unavailable")])
def test_missing_and_unreported_operands_preserve_other_arm(rows, reason):
    cells = populate_binding_contrast(extraction(reference=rows))["cells"]
    assert cells["reference_parameter"]["value"] is None
    assert cells["native_parameter_ratio"]["unavailable_reason"] == reason
    assert cells["test_parameter"]["value"] == 120
    assert cells["test_parameter"]["status"] == "populated"


def test_exact_copies_collapse_but_distinct_locations_are_ambiguous():
    inputs = extraction()
    inputs["reference_rows"].append(deepcopy(inputs["reference_rows"][0]))
    sheet = populate_binding_contrast(inputs)
    assert len(sheet["reference_rows"]) == 1
    assert sheet["cells"]["native_parameter_ratio"]["value"] == 3
    different_location = deepcopy(inputs["reference_rows"][0])
    different_location["source"]["locator"]["column"] = "IC50 repeated in figure"
    inputs["reference_rows"].append(different_location)
    sheet = populate_binding_contrast(inputs)
    assert len(sheet["reference_rows"]) == 2
    assert sheet["cells"]["reference_parameter"]["status"] == "conflicting"
    assert sheet["cells"]["native_parameter_ratio"]["unavailable_reason"] == "ambiguous_reference_arm"
    assert sheet["cells"]["test_parameter"]["value"] == 120


def test_conflicting_reading_at_same_physical_locator_is_not_duplicate():
    inputs = extraction()
    changed = deepcopy(inputs["reference_rows"][0])
    changed["value"] = 45
    inputs["reference_rows"].append(changed)
    sheet = populate_binding_contrast(inputs)
    assert len(sheet["reference_rows"]) == 2
    assert sheet["cells"]["reference_parameter"]["unavailable_reason"] == "conflicting_source_identity"
    assert sheet["cells"]["native_parameter_ratio"]["status"] == "conflicting"
    assert sheet["cells"]["test_parameter"]["value"] == 120


def test_same_actual_measurement_can_have_descriptive_identity_contrast():
    same = row(5)
    sheet = populate_binding_contrast(extraction([same], [deepcopy(same)]))
    assert sheet["cells"]["native_parameter_ratio"]["value"] == 1
    assert sheet["cells"]["log_native_parameter_ratio"]["value"] == 0
    assert sheet["independent_preparation_count"] is None
    inputs = extraction([same], [deepcopy(same)])
    inputs["test_rows"][0]["value"] = 6
    cells = populate_binding_contrast(inputs)["cells"]
    assert cells["reference_parameter"]["status"] == "conflicting"
    assert cells["test_parameter"]["status"] == "conflicting"


@pytest.mark.parametrize("field", ["subject", "state", "experiment"])
@pytest.mark.parametrize("relation", ["eq", "gt"])
def test_different_comparison_contexts_preserve_arms_without_contrast(field, relation):
    inputs = extraction()
    inputs["test_rows"][0][field] = "a different " + field
    inputs["test_rows"][0]["relation"] = relation
    sheet = populate_binding_contrast(inputs)
    cells = sheet["cells"]
    assert sheet["reference_rows"] == inputs["reference_rows"]
    assert sheet["test_rows"] == inputs["test_rows"]
    assert cells["reference_parameter"]["value"] == 40
    assert cells["reference_reported_spread"]["value"] == 4
    assert cells["reference_relative_spread"]["value"] == .1
    assert cells["test_parameter"]["value"] == 120
    assert cells["test_parameter"]["relation"] == relation
    for name in ("native_parameter_ratio", "log_native_parameter_ratio"):
        assert cells[name]["value"] is None
        assert cells[name]["relation"] == "unreported"
        assert cells[name]["status"] == "unavailable"
        assert cells[name]["unavailable_reason"] == "comparison_context_mismatch"
        assert cells[name]["bound_kind"] is None


@pytest.mark.parametrize("field", ["subject", "state", "experiment"])
def test_different_contexts_within_one_arm_remain_ambiguous(field):
    inputs = extraction()
    additional = row(40, index=2, spread=4)
    additional[field] = "another " + field
    inputs["reference_rows"].append(additional)
    cells = populate_binding_contrast(inputs)["cells"]
    assert cells["reference_parameter"]["status"] == "conflicting"
    assert cells["reference_parameter"]["unavailable_reason"] == "ambiguous_reference_arm"
    assert cells["native_parameter_ratio"]["unavailable_reason"] == "ambiguous_reference_arm"
    assert cells["test_parameter"]["value"] == 120


def visual_row(value, *, alias="alias-1"):
    result = row(value)
    result["origin"] = "visual_transcription"
    result["source"].update(
        representation="retained_visual_transcription", artifact_ref=alias,
        locator={"original_source_ref": "synthetic original", "original_artifact_ref": "synthetic image",
                 "image_region": [0, 1, 10, 20]},
    )
    return result


def test_visual_aliases_preserve_provenance_and_share_physical_conflict_identity():
    first, alias = visual_row(4), visual_row(4, alias="alias-2")
    alias["source"]["row_index"] = 3
    alias["source"]["source_ref"] = "another transcription source"
    alias["value"] = 4.0
    sheet = populate_binding_contrast(extraction([first, alias]))
    assert len(sheet["reference_rows"]) == 2
    assert sheet["cells"]["reference_parameter"]["status"] == "populated"
    assert sheet["cells"]["native_parameter_ratio"]["value"] == 30
    assert sheet["reference_rows"][0]["source"]["artifact_ref"] == "alias-1"
    assert sheet["reference_rows"][1]["source"]["artifact_ref"] == "alias-2"
    reversed_sheet = populate_binding_contrast(extraction([alias, first]))
    assert reversed_sheet["cells"] == sheet["cells"]
    alias["value"] = 6
    cells = populate_binding_contrast(extraction([first, alias]))["cells"]
    assert cells["reference_parameter"]["unavailable_reason"] == "conflicting_source_identity"


def test_visual_alias_conflicting_scientific_meaning_is_not_canonicalized():
    first, alias = visual_row(4), visual_row(4, alias="alias-2")
    alias["subject"] = "another source preparation"
    cells = populate_binding_contrast(extraction([first, alias]))["cells"]
    assert cells["reference_parameter"]["status"] == "conflicting"
    assert cells["reference_parameter"]["unavailable_reason"] == "conflicting_source_identity"


@pytest.mark.parametrize("a,b,reason", [
    (1e-308, 1e308, "nonfinite_calculation"),
    (1e308, 1e-308, "calculation_underflow"),
])
def test_extreme_ratio_failure_does_not_remove_finite_log(a, b, reason):
    cells = populate_binding_contrast(extraction([row(a)], [row(b, index=1)]))["cells"]
    assert cells["native_parameter_ratio"]["value"] is None
    assert cells["native_parameter_ratio"]["unavailable_reason"] == reason
    assert cells["log_native_parameter_ratio"]["status"] == "populated"
    assert cells["log_native_parameter_ratio"]["value"] == math.log(b) - math.log(a)


def test_relative_spread_underflow_and_zero_spread_are_distinct():
    cells = populate_binding_contrast(extraction([row(1e308, spread=5e-324)]))["cells"]
    assert cells["reference_reported_spread"]["value"] == 5e-324
    assert cells["reference_relative_spread"]["unavailable_reason"] == "calculation_underflow"
    cells = populate_binding_contrast(extraction([row(4, spread=0)]))["cells"]
    assert cells["reference_relative_spread"]["value"] == 0
    assert cells["reference_relative_spread"]["status"] == "populated"
    assert cells["source_profile_log_ratio"]["value"] is None


def test_nearby_large_points_do_not_become_equal_through_log_rounding():
    a = 1e300
    b = math.nextafter(a, math.inf)
    assert math.log(a) == math.log(b)
    cells = populate_binding_contrast(extraction([row(a)], [row(b, index=1)]))["cells"]
    assert cells["log_native_parameter_ratio"]["value"] == math.log1p((b-a)/a)
    assert cells["log_native_parameter_ratio"]["value"] > 0


def test_serialized_recalculation_preserves_kind_basis_and_source_indices():
    inputs = extraction()
    inputs["parameter_kind"] = "reported_hill_kd"
    inputs["uncertainty_basis"] = "between_independent_fitted_parameters"
    inputs["minimum_experiment_count"] = None
    inputs["reference_rows"][0]["source"]["locator"]["row_index"] = 42
    expected = populate_binding_contrast(inputs)
    assert populate_binding_contrast(json.loads(json.dumps(inputs))) == expected
    assert expected["parameter_kind"] == "reported_hill_kd"
    assert expected["reference_rows"][0]["source"]["locator"]["row_index"] == 42
    assert expected["independent_preparation_count"] is None


def test_synthetic_reader_to_calculator_normalizes_without_reinterpreting_tokens():
    from gene_annotation_episode.literature_binding_reader import read_binding_parameter_table

    table = {
        "version": "binding_parameter_table_v1", "table_id": "synthetic source table",
        "parameter_kind": "ic50", "unit": "µM",
        "uncertainty_basis": "fit_to_averaged_curve", "minimum_experiment_count": 2,
        "rows": [
            {"subject": "synthetic protein", "state": "apo", "experiment": "competition",
             "ligand": "reference", "expression": ".04 ± .004",
             "locator": {"row_index": 20, "column": "IC50"}},
            {"subject": "synthetic protein", "state": "apo", "experiment": "competition",
             "ligand": "test", "expression": "> .12",
             "locator": {"row_index": 21, "column": "IC50"}},
        ],
    }
    source = {"source_ref": "synthetic source", "artifact_ref": "synthetic JSON",
              "text": json.dumps(table), "representation": "synthetic_fixture"}
    normalized = read_binding_parameter_table(source, expected_subject="synthetic protein",
        expected_state="apo", expected_experiment="competition", reference_ligand="reference",
        test_ligand="test", parameter_kind="ic50")
    sheet = populate_binding_contrast(normalized)
    assert sheet["parameter_kind"] == "ic50"
    assert sheet["cells"]["reference_parameter"]["value"] == 40
    assert sheet["cells"]["reference_reported_spread"]["value"] == 4
    assert sheet["cells"]["reference_relative_spread"]["value"] == .1
    assert sheet["cells"]["native_parameter_ratio"]["value"] == 3
    assert sheet["cells"]["native_parameter_ratio"]["relation"] == "gt"
    assert sheet["test_rows"][0]["source"]["expression"] == "> .12"
    assert sheet["reference_rows"][0]["source"]["row_index"] == 0
    assert sheet["reference_rows"][0]["source"]["locator"]["row_index"] == 20


@pytest.mark.parametrize("path,value,code", [
    (("version",), "old", "unsupported_extraction_version"),
    (("parameter_kind",), "kd", "unsupported_parameter_kind"),
    (("unit",), "uM", "normalized_nM_required"),
    (("uncertainty_basis",), "sem", "unsupported_uncertainty_basis"),
    (("minimum_experiment_count",), True, "positive_integer_count_required"),
    (("minimum_experiment_count",), 0, "positive_integer_count_required"),
    (("minimum_experiment_count",), 1.5, "positive_integer_count_required"),
    (("reference_rows",), {}, "rows_required"),
    (("reference_rows", 0, "value"), 0, "positive_parameter_required"),
    (("reference_rows", 0, "value"), -1, "positive_parameter_required"),
    (("reference_rows", 0, "value"), None, "finite_number_required"),
    (("reference_rows", 0, "value"), True, "finite_number_required"),
    (("reference_rows", 0, "value"), float("nan"), "finite_number_required"),
    (("reference_rows", 0, "value"), float("inf"), "finite_number_required"),
    (("reference_rows", 0, "value"), 10**1000, "finite_number_required"),
    (("reference_rows", 0, "reported_spread"), -1, "nonnegative_spread_required"),
    (("reference_rows", 0, "reported_spread"), True, "finite_number_required"),
    (("reference_rows", 0, "reported_spread"), float("inf"), "finite_number_required"),
    (("reference_rows", 0, "relation"), "approx", "unknown_censor_relation"),
    (("reference_rows", 0, "relation"), "gt", "censored_spread_unsupported"),
    (("reference_rows", 0, "relation"), "unreported", "unreported_value_and_spread_must_be_null"),
    (("reference_rows", 0, "subject"), " ", "nonempty_source_token_required"),
    (("reference_rows", 0, "state"), None, "nonempty_source_token_required"),
    (("reference_rows", 0, "experiment"), "", "nonempty_source_token_required"),
    (("reference_rows", 0, "ligand"), {}, "nonempty_source_token_required"),
    (("reference_rows", 0, "origin"), "reported", "source_origin_mismatch"),
    (("reference_rows", 0, "source", "source_ref"), "", "nonempty_source_token_required"),
    (("reference_rows", 0, "source", "artifact_ref"), None, "nonempty_source_token_required"),
    (("reference_rows", 0, "source", "representation"), "unknown", "unknown_source_representation"),
    (("reference_rows", 0, "source", "row_index"), True, "nonnegative_integer_offset_required"),
    (("reference_rows", 0, "source", "locator", "row_index"), -1, "nonnegative_integer_offset_required"),
    (("reference_rows", 0, "source", "locator", "column"), "", "nonempty_source_token_required"),
    (("reference_rows", 0, "source", "expression"), "", "nonempty_source_token_required"),
])
def test_invalid_inputs_fail_with_specific_repairable_field(path, value, code):
    inputs = extraction()
    current = inputs
    for part in path[:-1]:
        current = current[part]
    current[path[-1]] = value
    with pytest.raises(ExperimentalContractError) as caught:
        populate_binding_contrast(inputs)
    assert caught.value.code == code
    assert caught.value.field


@pytest.mark.parametrize("path", [(), ("reference_rows", 0),
    ("reference_rows", 0, "source"), ("reference_rows", 0, "source", "locator")])
def test_closed_shapes_reject_undeclared_fields(path):
    inputs = extraction()
    current = inputs
    for part in path:
        current = current[part]
    current["unexpected"] = None
    with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
        populate_binding_contrast(inputs)


@pytest.mark.parametrize("region", [None, [1, 2, 3], [0, 0, 0, 4],
    [1, 4, 2, 4], [-1, 0, 2, 3], [False, 0, 2, 3], [0, .5, 2, 3]])
def test_invalid_visual_coordinate_witnesses_are_rejected(region):
    inputs = extraction([visual_row(4)])
    inputs["reference_rows"][0]["source"]["locator"]["image_region"] = region
    with pytest.raises(ExperimentalContractError):
        populate_binding_contrast(inputs)
