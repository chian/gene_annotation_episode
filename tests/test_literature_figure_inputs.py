"""Synthetic native image/custody checks; fixtures are not scientific findings."""
from copy import deepcopy
import hashlib
from io import BytesIO
import json

from PIL import Image
import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode import literature_figure_inputs as reader


SOURCE, DATA, FIRST, SECOND, TEXT_SOURCE = ("source_" + str(i) * 24 for i in range(1, 6))
TEXT = "µ synthetic subject A; partner B; final product; same preparation."


def png(rows=(3, 4, 5, 6)):
    image = Image.new("RGB", (12, 12), "white")
    for y in rows:
        for x in range(2, 10):
            image.putpixel((x, y), (20, 80, 160))
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def selection():
    return {"roi": {"left": 2, "top": 0, "right": 10, "bottom": 10},
        "rgb_min": [20, 80, 160], "rgb_max": [20, 80, 160],
        "minimum_row_fraction": 1, "minimum_run_rows": 2, "edge_tolerance_pixels": 0,
        "calibration": {"first": {"pixel": 0, "value": 100},
            "second": {"pixel": 10, "value": 0}, "unit": "relative_turnover_percent"}}


def witness(quote="subject A", reference=SOURCE, representation="original"):
    start = TEXT.encode().index(quote.encode())
    return {"source_ref": reference, "representation": representation,
        "start": start, "end": start + len(quote.encode()), "quote": quote}


def fixture(*, second=True):
    repeat = {"reported_n": 3, "repeat_kind": "biological",
        "independent_preparation_count": None, "spread_kind": "SD",
        "spread_numeric_status": "not_extracted"}
    recipe = {"version": reader.DATA_VERSION,
        "first": {"image_source_ref": FIRST, "image_origin": "synthetic",
            "axis_scale": "linear", "selection": selection()},
        "second": {"image_source_ref": SECOND, "image_origin": "synthetic",
            "axis_scale": "linear", "selection": selection()} if second else None,
        "design": {"arrangement": "coexisting_sequential_catalysts",
            "contrast_kind": "source_representation", "endpoint_scope": "coupled_final_product",
            "normalization_basis": "reported_relative_turnover",
            "measurement_relation": "same_physical_measurement",
            "first_repeat": repeat, "second_repeat": deepcopy(repeat) if second else None}}
    args = {"source_ref": SOURCE, "data_source_ref": DATA, "source_kind": "synthetic_fixture",
        "literals": dict.fromkeys(reader.LITERAL_FIELDS), "interpretation_witnesses": []}
    payloads = {reference: {"artifact_ref": "artifact_" + str(i) * 24, "content": content}
        for i, (reference, content) in enumerate(((SOURCE, TEXT.encode()), (DATA, b""),
            (FIRST, png()), (SECOND, png((2, 3, 4, 5))), (TEXT_SOURCE, TEXT.encode())), start=1)}
    calls = []

    def read_source(reference, representation):
        calls.append((reference, representation))
        return payloads[reference]

    fix = (args, recipe, payloads, calls, read_source)
    retain(fix)
    return fix


def retain(fix):
    fix[2][DATA]["content"] = json.dumps(fix[1], allow_nan=True).encode()


def read(fix):
    return reader.read_figure_inputs(fix[0], read_source=fix[4])


def check_error(fix, code, *, native=False):
    with pytest.raises(ContractError if native else ExperimentalContractError) as caught:
        read(fix)
    assert (str(caught.value) if native else caught.value.code) == code


def test_actual_native_reads_exact_output_signed_percentage_points_and_no_renormalizing(monkeypatch):
    fix = fixture()
    calls = []
    original = reader.read_bar_ordinate

    def measured(data, selected):
        calls.append((data, deepcopy(selected)))
        return original(data, selected)

    monkeypatch.setattr(reader, "read_bar_ordinate", measured)
    out = read(fix)
    assert set(out) == {"version", "arguments", "sources", "literals", "interpretations",
        "recipe", "measurements", "cells"}
    assert out["version"] == reader.VERSION
    assert out["arguments"] == fix[0] and out["recipe"] == fix[1]
    assert out["sources"] == [SOURCE, DATA, FIRST, SECOND]
    assert fix[3] == [(ref, "original") for ref in out["sources"]]
    assert calls == [(fix[2][ref]["content"], fix[1][side]["selection"])
        for ref, side in ((FIRST, "first"), (SECOND, "second"))]
    assert set(out["measurements"]) == {"first", "second"}
    for side, reference, top in (("first", FIRST, 3), ("second", SECOND, 2)):
        measurement = out["measurements"][side]
        assert measurement == original(fix[2][reference]["content"], fix[1][side]["selection"])
        assert measurement["image_sha256"] == hashlib.sha256(fix[2][reference]["content"]).hexdigest()
        assert measurement["image_size"] == {"width": 12, "height": 12}
        assert measurement["pixel_edge"]["top_row"] == top
        assert measurement["cell"] == out["cells"][side + "_ordinate"]
    first, second, difference = (out["cells"][c] for c in reader.COMPONENTS)
    assert (first["value"], second["value"], difference["value"]) == (65, 75, -10)
    assert (difference["lower"], difference["upper"]) == (-20, 0)
    assert difference["unit"] == "relative_turnover_percentage_points"
    assert difference["origin"] == "derived"
    assert all(cell["bound_kind"] == "conditional_digitization_not_confidence_interval"
        for cell in out["cells"].values())
    assert out["recipe"]["design"]["first_repeat"]["independent_preparation_count"] is None
    json.dumps(out, allow_nan=False)
    fix[0]["source_kind"] = "graph_extraction"
    out["cells"]["first_ordinate"]["value"] = 1234
    out["recipe"]["first"]["selection"]["roi"]["top"] = 11
    assert out["arguments"]["source_kind"] == "synthetic_fixture"
    assert out["measurements"]["first"]["cell"]["value"] == 65
    assert out["measurements"]["first"]["selection"]["roi"]["top"] == 0


def test_exact_byte_witnesses_all_field_meanings_and_manifest_deduplication():
    fix = fixture()
    for name in reader.LITERAL_FIELDS:
        fix[0]["literals"][name] = witness(reference=TEXT_SOURCE, representation="text")
    fix[0]["interpretation_witnesses"] = [witness("same preparation.", reference=TEXT_SOURCE,
        representation="text"), witness("partner B")]
    out = read(fix)
    for name in reader.LITERAL_FIELDS:
        assert out["literals"][name] == {"value": "subject A", "witness": {
            **fix[0]["literals"][name], "artifact_ref": fix[2][TEXT_SOURCE]["artifact_ref"]}}
    assert out["interpretations"][0]["quote"] == "same preparation."
    assert out["sources"] == [SOURCE, DATA, FIRST, SECOND, TEXT_SOURCE]
    assert fix[3].count((TEXT_SOURCE, "text")) == 1
    assert fix[3].count((SOURCE, "original")) == 1


def test_binary_original_paper_custody_does_not_require_text_or_witnesses():
    fix = fixture(second=False)
    fix[2][SOURCE]["content"] = b"\xff\x00PDF original bytes"
    out = read(fix)
    assert out["literals"] == dict.fromkeys(reader.LITERAL_FIELDS)
    assert out["interpretations"] == []
    assert out["sources"] == [SOURCE, DATA, FIRST]
    assert out["measurements"]["second"] is None
    for component, origin in (("second_ordinate", "graph_derived"), ("ordinate_difference", "derived")):
        assert out["cells"][component] == {"value": None, "lower": None, "upper": None,
            "unit": None, "origin": origin,
            "bound_kind": "conditional_digitization_not_confidence_interval",
            "status": "unavailable", "unavailable_reason": "second_ordinate_unreported"}


def test_valid_unit_mismatch_keeps_native_raw_cells():
    fix = fixture()
    fix[1]["second"]["selection"]["calibration"]["unit"] = "nanomolar"
    retain(fix)
    out = read(fix)
    assert out["cells"]["first_ordinate"]["value"] == 65
    assert out["cells"]["second_ordinate"]["value"] == 75
    assert out["cells"]["second_ordinate"]["unit"] == "nanomolar"
    difference = out["cells"]["ordinate_difference"]
    assert difference["unit"] is None
    assert difference["unavailable_reason"] == "ordinate_unit_mismatch"


@pytest.mark.parametrize("rows,top,reason", [
    ((), 0, "no_bar_pixels"), ((1, 2, 5, 6), 0, "ambiguous_bar_runs"),
    ((3, 4, 5, 6), 3, "truncated_mean_edge"),
])
def test_native_partial_results_preserve_actual_runs_and_do_not_manufacture_comparison(rows, top, reason):
    fix = fixture()
    fix[2][FIRST]["content"] = png(rows)
    fix[1]["first"]["selection"]["roi"]["top"] = top
    retain(fix)
    out = read(fix)
    assert out["cells"]["first_ordinate"]["unavailable_reason"] == reason
    assert out["measurements"]["first"]["pixel_edge"] is None
    assert out["cells"]["second_ordinate"]["status"] == "populated"
    difference = out["cells"]["ordinate_difference"]
    assert difference["unavailable_reason"] == "missing_ordinate"
    assert difference["unit"] == "relative_turnover_percentage_points"


def test_finite_but_unrepresentable_native_result_is_partial_not_json_infinity():
    fix = fixture()
    fix[1]["first"]["selection"]["calibration"]["first"]["value"] = 10 ** 400
    fix[1]["first"]["selection"]["calibration"]["second"]["value"] = 10 ** 400 + 1
    retain(fix)
    out = read(fix)
    assert out["cells"]["first_ordinate"]["unavailable_reason"] == "numerical_model_range"
    assert out["cells"]["ordinate_difference"]["unavailable_reason"] == "missing_ordinate"
    json.dumps(out, allow_nan=False)


@pytest.mark.parametrize("path,value,code,native", [
    (("extra",), 1, "closed_fields_required", False),
    (("first", "extra"), 1, "closed_fields_required", False),
    (("first", "axis_scale"), "logarithmic", "unsupported_axis_scale", False),
    (("first", "axis_scale"), "unknown", "unsupported_axis_scale", False),
    (("first", "image_origin"), "unknown", "unsupported_image_origin", False),
    (("first", "image_source_ref"), None, "nonempty_source_token_required", False),
    (("first", "selection", "extra"), 0, "malformed_selection", True),
    (("first", "selection", "minimum_run_rows"), True, "malformed_selection", True),
    (("first", "selection", "calibration", "unit"), "unknown", "unsupported_calibration_unit", True),
    (("design", "arrangement"), "necessity", "unsupported_arrangement", False),
    (("design", "contrast_kind"), [], "unsupported_contrast_kind", False),
    (("design", "endpoint_scope"), "molar_flux", "unsupported_endpoint_scope", False),
    (("design", "normalization_basis"), "automatic", "unsupported_normalization_basis", False),
    (("design", "measurement_relation"), "independent", "unsupported_measurement_relation", False),
    (("design", "second_repeat"), None, "second_repeat_presence_mismatch", False),
    (("design", "first_repeat", "reported_n"), True, "positive_integer_count_required", False),
    (("design", "first_repeat", "reported_n"), 0, "positive_integer_count_required", False),
    (("design", "first_repeat", "independent_preparation_count"), 1.5, "positive_integer_count_required", False),
    (("design", "first_repeat", "repeat_kind"), "independent", "unsupported_repeat_kind", False),
    (("design", "first_repeat", "spread_kind"), "variance", "unsupported_spread_kind", False),
    (("design", "first_repeat", "spread_numeric_status"), "measured", "spread_numeric_status_mismatch", False),
    (("design", "first_repeat", "sd"), 3, "closed_fields_required", False),
])
def test_strict_recipe_fields_and_meanings(path, value, code, native):
    fix = fixture()
    target = fix[1]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    retain(fix)
    check_error(fix, code, native=native)


@pytest.mark.parametrize("spread", reader.SPREAD_KINDS)
def test_repeat_spread_is_retained_without_extracting_statistics(spread):
    fix = fixture(second=False)
    repeat = fix[1]["design"]["first_repeat"]
    repeat.update(reported_n=None, repeat_kind="unknown", spread_kind=spread,
        spread_numeric_status="unreported" if spread == "unreported" else "not_extracted")
    retain(fix)
    assert read(fix)["recipe"]["design"]["first_repeat"] == repeat
    repeat["spread_numeric_status"] = "not_extracted" if spread == "unreported" else "unreported"
    retain(fix)
    check_error(fix, "spread_numeric_status_mismatch")


@pytest.mark.parametrize("raw,code", [
    (b'{"version":1,"version":2}', "duplicate_json_key"),
    (b'{"nested":{"x":1,"x":2}}', "duplicate_json_key"),
    (b'{"x":NaN}', "finite_number_required"),
    (b'{"x":Infinity}', "finite_number_required"),
    (b'{"x":1e999}', "finite_number_required"),
    (b'{"x":1e-999}', "numerical_model_range"),
    (b'\xff', "malformed_figure_selection_source"),
    (b'{', "malformed_figure_selection_source"),
    (b'null', "closed_fields_required"),
])
def test_strict_retained_json(raw, code):
    fix = fixture()
    fix[2][DATA]["content"] = raw
    check_error(fix, code)


@pytest.mark.parametrize("field,value,code", [
    ("source_ref", None, "nonempty_source_token_required"),
    ("data_source_ref", None, "nonempty_source_token_required"),
    ("source_kind", "reviewed_true", "unsupported_source_kind"),
    ("interpretation_witnesses", {}, "array_required"),
    ("literals", {}, "closed_fields_required"),
    ("measurement", 65, "closed_fields_required"),
])
def test_closed_selected_args_exclude_numeric_operands(field, value, code):
    fix = fixture()
    fix[0][field] = value
    check_error(fix, code)


def test_required_args_missing_fields_and_schema():
    fix = fixture()
    validate_schema(fix[0], reader.figure_population_schema())
    for field in fix[0]:
        args = deepcopy(fix[0])
        del args[field]
        with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
            reader.read_figure_inputs(args, read_source=fix[4])
    assert set(reader.figure_population_schema()["properties"]) == set(fix[0])
    assert reader.figure_population_schema()["additionalProperties"] is False
    assert tuple(read(fix)["cells"]) == reader.COMPONENTS
    assert set(reader.REASONS) == {"no_bar_pixels", "ambiguous_bar_runs", "truncated_mean_edge",
        "numerical_model_range", "missing_ordinate", "second_ordinate_unreported", "ordinate_unit_mismatch"}


def test_selected_schema_rejects_extra_numerical_argument():
    args = fixture()[0]
    args["first_ordinate"] = 65
    with pytest.raises(ContractError, match="representation_error") as caught:
        validate_schema(args, reader.figure_population_schema())
    assert caught.value.detail["schema_keyword"] == "additionalProperties"


@pytest.mark.parametrize("changes,code", [
    ({"quote": "wrong"}, "source_quote_mismatch"),
    ({"start": True}, "nonnegative_integer_offset_required"),
    ({"end": 999}, "source_span_out_of_bounds"),
    ({"representation": "inferred"}, "unknown_source_representation"),
    ({"extra": 1}, "closed_fields_required"),
])
def test_literal_and_interpretation_witnesses_are_exact(changes, code):
    for interpretation in (False, True):
        fix = fixture()
        selected = {**witness(), **changes}
        if interpretation:
            fix[0]["interpretation_witnesses"] = [selected]
        else:
            fix[0]["literals"]["first_subject"] = selected
        check_error(fix, code)


def test_callback_failures_propagate_and_original_image_bytes_required():
    fix = fixture()

    def denied(ref, representation):
        if ref == FIRST:
            raise RuntimeError("unreceived image")
        return fix[4](ref, representation)

    with pytest.raises(RuntimeError, match="unreceived image"):
        reader.read_figure_inputs(fix[0], read_source=denied)
    fix[2][FIRST]["content"] = b"not image bytes"
    check_error(fix, "malformed_image", native=True)
    fix[2][FIRST]["content"] = bytearray(png())
    check_error(fix, "source_bytes_required")


def test_same_image_source_read_once_but_both_selected_ordinates_measured():
    fix = fixture()
    fix[1]["second"]["image_source_ref"] = FIRST
    fix[1]["second"]["selection"]["roi"]["top"] = 3
    retain(fix)
    out = read(fix)
    assert out["sources"] == [SOURCE, DATA, FIRST]
    assert fix[3].count((FIRST, "original")) == 1
    assert out["cells"]["first_ordinate"]["value"] == 65
    assert out["cells"]["second_ordinate"]["unavailable_reason"] == "truncated_mean_edge"
