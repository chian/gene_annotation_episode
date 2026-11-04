"""Strict binding-token and custody tests over invented synthetic tables only."""
from copy import deepcopy
import json
from unittest.mock import patch

import pytest

from gene_annotation_episode.literature_binding_reader import read_binding_parameter_table
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def row(expression="8 ± 1", *, ligand="self", **changes):
    return {"subject": "ProteinFixture", "state": "apo", "experiment": "competition-fixture",
            "ligand": ligand, "expression": expression,
            "locator": {"row_index": 4, "column": "parameter"}, **changes}


_DEFAULT_ROWS = object()


def source(rows=_DEFAULT_ROWS, *, representation="synthetic_fixture", **changes):
    table = {"version": "binding_parameter_table_v1", "table_id": "T-fixture",
             "parameter_kind": "ic50", "unit": "nM", "uncertainty_basis": "fit_to_averaged_curve",
             "minimum_experiment_count": 2,
             "rows": [row(), row(">80", ligand="alternate")] if rows is _DEFAULT_ROWS else rows,
             **changes}
    return {"source_ref": "source:fixture", "artifact_ref": "artifact:fixture",
            "representation": representation, "text": json.dumps(table, ensure_ascii=False)}


def read(value=None, **changes):
    selectors = {"expected_subject": "ProteinFixture", "expected_state": "apo",
                 "expected_experiment": "competition-fixture", "reference_ligand": "self",
                 "test_ligand": "alternate", "parameter_kind": "ic50", **changes}
    return read_binding_parameter_table(source() if value is None else value, **selectors)


def test_exact_normalized_contract_preserves_literal_and_uncertainty_without_inference():
    value = source()
    before = deepcopy(value)
    result = read(value)
    assert result == {
        "version": "binding_parameter_extraction_v1", "parameter_kind": "ic50", "unit": "nM",
        "uncertainty_basis": "fit_to_averaged_curve", "minimum_experiment_count": 2,
        "reference_rows": [{"value": 8., "relation": "eq", "reported_spread": 1.,
            "origin": "synthetic", "subject": "ProteinFixture", "state": "apo",
            "experiment": "competition-fixture", "ligand": "self",
            "source": {"source_ref": "source:fixture", "artifact_ref": "artifact:fixture",
                "representation": "synthetic_fixture", "table_id": "T-fixture", "row_index": 0,
                "locator": {"row_index": 4, "column": "parameter"}, "expression": "8 ± 1"}}],
        "test_rows": [{"value": 80., "relation": "gt", "reported_spread": None,
            "origin": "synthetic", "subject": "ProteinFixture", "state": "apo",
            "experiment": "competition-fixture", "ligand": "alternate",
            "source": {"source_ref": "source:fixture", "artifact_ref": "artifact:fixture",
                "representation": "synthetic_fixture", "table_id": "T-fixture", "row_index": 1,
                "locator": {"row_index": 4, "column": "parameter"}, "expression": ">80"}}]}
    assert result == json.loads(json.dumps(result))
    result["reference_rows"][0]["source"]["locator"]["column"] = "changed"
    assert value == before


@pytest.mark.parametrize("token,value,relation,spread", [
    ("1", 1., "eq", None), ("  +.25e+2  ", 25., "eq", None),
    ("8±0", 8., "eq", 0.), ("8.0 ± +1e-2", 8., "eq", .01),
    (">1", 1., "gt", None), (">= 1", 1., "ge", None), ("≥1", 1., "ge", None),
    ("<1", 1., "lt", None), ("<=1", 1., "le", None), ("≤ 1", 1., "le", None),
    (" n.d. ", None, "unreported", None),
])
def test_finite_complete_tokens_and_literal_limit_meanings(token, value, relation, spread):
    parsed, = read(source([row(token)]))["reference_rows"]
    assert (parsed["value"], parsed["relation"], parsed["reported_spread"]) == (value, relation, spread)
    assert parsed["source"]["expression"] == token


@pytest.mark.parametrize("token", [
    "", " ", "~8", "≈8", "about 8", "8-9", "8 to 9", "[8,9]", "8 nM", "8*", "8;",
    "8foo", "foo8", "n.d", "ND", "nan", "NaN", "Infinity", "-inf", "8 +/- 1", "8 ±",
    "8 ± 1 ± 2", "8 ± NaN", "8 ± 1e999", ">8 ± 1", "≤8 ± 0", ">>8", "=<8", "1,000",
    "1_000", "1/2", "0x10", "8e", "8.2.3", "８", "١", "True", "8\x00", "0", "-8",
    "8 ± -1", "1e999", "1e-999", "8 ± 1e-999",
])
def test_unsupported_partial_nonfinite_underflow_and_nonpositive_tokens_fail(token):
    with pytest.raises(ExperimentalContractError) as error:
        read(source([row(token)]))
    assert error.value.code and error.value.field.startswith("table.rows[0].expression")


@pytest.mark.parametrize("unit,scale", [("nM", 1), ("uM", 1000), ("µM", 1000),
                                      ("μM", 1000), ("mM", 1000000)])
def test_both_point_and_reported_spread_convert_to_nm(unit, scale):
    parsed, = read(source([row(".25 ± .01")], unit=unit))["reference_rows"]
    assert parsed["value"] == .25 * scale
    assert parsed["reported_spread"] == .01 * scale


@pytest.mark.parametrize("token", ["1e308", "1 ± 1e308"])
def test_unit_conversion_overflow_returns_specific_range_error(token):
    with pytest.raises(ExperimentalContractError, match="numerical_model_range"):
        read(source([row(token)], unit="mM"))


def test_underflowing_zero_spread_rejected_but_literal_zero_with_extreme_exponent_allowed():
    parsed, = read(source([row("8 ± 0e-9999")]))["reference_rows"]
    assert parsed["reported_spread"] == 0
    with pytest.raises(ExperimentalContractError, match="numerical_model_range"):
        read(source([row("8 ± 1e-9999")]))


def test_exact_selectors_filter_every_dimension_without_alias_or_first_row_choice():
    rows = [row("1", subject="Other"), row("2", state="holo"),
            row("3", experiment="other"), row("4", ligand="self_extra"),
            row("5"), row("6"), row("7", ligand="alternate")]
    result = read(source(rows))
    assert [r["value"] for r in result["reference_rows"]] == [5., 6.]
    assert [r["source"]["row_index"] for r in result["reference_rows"]] == [4, 5]
    assert [r["value"] for r in result["test_rows"]] == [7.]


def test_duplicates_equal_values_and_conflicts_remain_separate_source_records():
    rows = [row(), row(), row("9"), row(locator={"row_index": 5, "column": "parameter"})]
    parsed = read(source(rows))["reference_rows"]
    assert len(parsed) == 4
    assert [r["value"] for r in parsed] == [8., 8., 9., 8.]
    assert [r["source"]["row_index"] for r in parsed] == [0, 1, 2, 3]


def test_missing_arms_empty_table_and_unreported_do_not_fabricate_points():
    assert read(source([]))["reference_rows"] == []
    assert read(source([]))["test_rows"] == []
    result = read(source([row("n.d.")]))
    assert result["test_rows"] == []
    assert result["reference_rows"][0]["value"] is None
    assert result["reference_rows"][0]["reported_spread"] is None
    assert read(expected_subject="absent")["reference_rows"] == []


def test_identical_ligand_selectors_produce_detached_copies_of_actual_measurement():
    result = read(source([row()]), test_ligand="self")
    assert result["reference_rows"] == result["test_rows"]
    result["reference_rows"][0]["source"]["locator"]["column"] = "changed"
    assert result["test_rows"][0]["source"]["locator"]["column"] == "parameter"


@pytest.mark.parametrize("basis", ["fit_to_averaged_curve", "between_independent_fitted_parameters", "unknown"])
@pytest.mark.parametrize("count", [None, 1, 3])
def test_uncertainty_basis_and_minimum_count_preserved_without_adding_sample_metadata(basis, count):
    result = read(source(uncertainty_basis=basis, minimum_experiment_count=count))
    assert result["uncertainty_basis"] == basis
    assert result["minimum_experiment_count"] == count
    assert "independent_preparation_count" not in result
    assert "uncertainty_kind" not in result["reference_rows"][0]


@pytest.mark.parametrize("representation,origin", [("primary_table", "reported"),
                                                   ("synthetic_fixture", "synthetic")])
def test_source_representation_defines_origin(representation, origin):
    parsed, = read(source([row()], representation=representation))["reference_rows"]
    assert parsed["origin"] == origin
    assert parsed["source"]["representation"] == representation


def visual_locator():
    return {"original_source_ref": "source:image-fixture", "original_artifact_ref": "artifact:image-fixture",
            "image_region": [0, 0, 20, 10]}


def test_retained_visual_coordinates_and_original_lineage_are_preserved_without_pixel_claims():
    locator = visual_locator()
    value = source([row(locator=locator)], representation="retained_visual_transcription")
    parsed, = read(value)["reference_rows"]
    assert parsed["origin"] == "visual_transcription"
    assert parsed["source"]["locator"] == locator
    assert parsed["source"]["artifact_ref"] == "artifact:fixture"


@pytest.mark.parametrize("box", [None, [], [0, 0, 1], [0, 0, 1, 2, 3],
    [-1, 0, 2, 3], [0, 0, 0, 3], [0, 1, 2, 1], [2, 0, 1, 3],
    [False, 0, 2, 3], [0, 0, 2., 3], [0, 0, "2", 3]])
def test_visual_locator_requires_integer_nonnegative_origins_and_positive_extent(box):
    locator = {**visual_locator(), "image_region": box}
    with pytest.raises(ExperimentalContractError, match="positive_integer_image_region_required"):
        read(source([row(locator=locator)], representation="retained_visual_transcription"))


@pytest.mark.parametrize("locator", [{"row_index": -1, "column": "p"},
    {"row_index": True, "column": "p"}, {"row_index": 0., "column": "p"},
    {"row_index": 0, "column": " "}, {"row_index": 0},
    {"row_index": 0, "column": "p", "extra": 1}, visual_locator()])
def test_primary_and_synthetic_locators_have_closed_typed_fields(locator):
    with pytest.raises(ExperimentalContractError):
        read(source([row(locator=locator)]))


@pytest.mark.parametrize("changes", [{"original_source_ref": ""}, {"original_artifact_ref": None},
                                     {"extra": 1}])
def test_visual_lineage_fields_are_required_and_closed(changes):
    with pytest.raises(ExperimentalContractError):
        read(source([row(locator={**visual_locator(), **changes})],
                    representation="retained_visual_transcription"))


@pytest.mark.parametrize("changes", [{"version": "v2"}, {"table_id": ""},
    {"parameter_kind": "kd"}, {"unit": "M"}, {"unit": []}, {"uncertainty_basis": "sd"},
    {"minimum_experiment_count": True}, {"minimum_experiment_count": 0},
    {"minimum_experiment_count": 2.}, {"minimum_experiment_count": -1},
    {"rows": {}}, {"rows": None}, {"extra": 1}])
def test_table_contract_rejects_unsupported_metadata(changes):
    with pytest.raises(ExperimentalContractError):
        read(source(**changes))


def test_reported_hill_kd_is_preserved_and_kind_mismatch_is_explicit():
    value = source(parameter_kind="reported_hill_kd")
    assert read(value, parameter_kind="reported_hill_kd")["parameter_kind"] == "reported_hill_kd"
    with pytest.raises(ExperimentalContractError, match="binding_parameter_kind_mismatch"):
        read(value)


@pytest.mark.parametrize("selector", ["expected_subject", "expected_state", "expected_experiment",
                                      "reference_ligand", "test_ligand", "parameter_kind"])
@pytest.mark.parametrize("invalid", [None, "", " ", 1, []])
def test_selector_values_are_validated(selector, invalid):
    with pytest.raises(ExperimentalContractError):
        read(**{selector: invalid})


@pytest.mark.parametrize("mutation", [lambda x: x.pop("artifact_ref"),
    lambda x: x.update(extra=1), lambda x: x.update(representation="graph"),
    lambda x: x.update(representation=[]), lambda x: x.update(text=b"{}"),
    lambda x: x.update(source_ref=" ")])
def test_source_metadata_is_closed_and_typed(mutation):
    value = source()
    mutation(value)
    with pytest.raises(ExperimentalContractError):
        read(value)


@pytest.mark.parametrize("text", ["{", "[]", "null", "true", "{} trailing",
    '{"version":"binding_parameter_table_v1","version":"binding_parameter_table_v1"}',
    '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}',
    '{"rows":[{"expression":"8","expression":"9"}]}'])
def test_json_is_strict_including_nested_duplicate_keys_and_nonfinite_constants(text):
    value = source()
    value["text"] = text
    with pytest.raises(ExperimentalContractError):
        read(value)


@pytest.mark.parametrize("bad_row", [None, [], {**row(), "extra": 1},
    {**row(), "subject": ""}, {**row(), "state": None}, {**row(), "experiment": 1},
    {**row(), "ligand": " "}, {**row(), "expression": 8}])
def test_all_rows_require_closed_nonempty_fields(bad_row):
    with pytest.raises(ExperimentalContractError):
        read(source([bad_row]))


def test_unselected_malformed_rows_are_not_silently_ignored():
    with pytest.raises(ExperimentalContractError, match="invalid_binding_parameter_token"):
        read(source([row(), row("approximately 8", subject="Other")]))


def test_reader_has_no_file_network_or_model_side_effects():
    value = source()
    with patch("builtins.open", side_effect=AssertionError("unexpected source read")), \
            patch("io.open", side_effect=AssertionError("unexpected source read")), \
            patch("urllib.request.urlopen", side_effect=AssertionError("unexpected source acquisition")), \
            patch("socket.create_connection", side_effect=AssertionError("unexpected connection")):
        assert read(value)["reference_rows"][0]["value"] == 8.
