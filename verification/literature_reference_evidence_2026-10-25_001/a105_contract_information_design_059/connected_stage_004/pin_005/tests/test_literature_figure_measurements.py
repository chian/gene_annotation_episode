"""Synthetic native pixel fixtures; none are scientific measurements."""
from copy import deepcopy
from fractions import Fraction
import hashlib
from io import BytesIO
import math
import sys

from PIL import Image
import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_figure_measurements import (
    BOUND_KIND, compare_ordinate_cells, read_bar_ordinate,
)


def image_bytes(rows=(3, 4, 5, 6), *, mode="RGB", format="PNG", exif=None):
    image = Image.new(mode, (12, 12), 255 if mode == "L" else "white")
    for y in rows:
        for x in range(2, 10):
            image.putpixel((x, y), 30 if mode == "L" else ((20, 80, 160, 70) if mode == "RGBA" else (20, 80, 160)))
    output = BytesIO()
    options = {} if exif is None else {"exif": exif}
    if format == "JPEG":
        options.update(quality=100, subsampling=0)
    image.save(output, format=format, **options)
    return output.getvalue()


def selection():
    return {"roi": {"left": 2, "top": 0, "right": 10, "bottom": 10},
            "rgb_min": [20, 80, 160], "rgb_max": [20, 80, 160],
            "minimum_row_fraction": 1, "minimum_run_rows": 2,
            "edge_tolerance_pixels": 0,
            "calibration": {"first": {"pixel": 0, "value": 100},
                            "second": {"pixel": 10, "value": 0},
                            "unit": "relative_turnover_percent"}}


def cell(value=1, lower=0, upper=2, **changes):
    result = {"value": value, "lower": lower, "upper": upper,
              "unit": "arbitrary_signal", "origin": "graph_derived",
              "bound_kind": BOUND_KIND, "status": "populated", "unavailable_reason": None}
    result.update(changes)
    return result


def assert_error(code, function, *args):
    with pytest.raises(ContractError) as caught:
        function(*args)
    assert str(caught.value) == code
    assert set(caught.value.detail) == {"field_path"}


def test_native_pixels_axis_direction_dimensions_hash_and_detached_selection():
    data, recipe = image_bytes(), selection()
    result = read_bar_ordinate(data, recipe)
    assert set(result) == {"version", "image_sha256", "image_size", "selection", "qualifying_runs", "pixel_edge", "cell"}
    assert result["version"] == "literature_bar_ordinate_v1"
    assert result["image_sha256"] == hashlib.sha256(data).hexdigest()
    assert result["image_size"] == {"width": 12, "height": 12}
    assert result["selection"] == recipe
    recipe["rgb_min"][0] = 0
    assert result["selection"]["rgb_min"][0] == 20
    assert result["qualifying_runs"] == [{"top": 3, "bottom": 7}]
    assert result["pixel_edge"] == {"top_row": 3, "centre": 3.5, "lower": 3., "upper": 4.}
    assert result["cell"] == cell(65., 60., 70., unit="relative_turnover_percent")
    recipe = selection()
    recipe["calibration"]["first"]["value"] = 0
    recipe["calibration"]["second"]["value"] = 100
    assert read_bar_ordinate(data, recipe)["cell"] == cell(35., 30., 40., unit="relative_turnover_percent")
    recipe["calibration"]["first"], recipe["calibration"]["second"] = recipe["calibration"]["second"], recipe["calibration"]["first"]
    assert read_bar_ordinate(data, recipe)["cell"]["value"] == 35


def test_outward_rounding_uses_exact_calibration_and_edge_domain():
    recipe = selection()
    recipe["calibration"] = {"first": {"pixel": 0, "value": 0},
                             "second": {"pixel": 9, "value": 1}, "unit": "arbitrary_signal"}
    recipe["edge_tolerance_pixels"] = 0.1
    result = read_bar_ordinate(image_bytes(), recipe)
    exact_low = (Fraction(3) - Fraction(0.1)) / 9
    exact_high = (Fraction(4) + Fraction(0.1)) / 9
    measured = result["cell"]
    assert measured["value"] == float(Fraction(7, 18))
    assert Fraction(measured["lower"]) <= exact_low
    assert Fraction(math.nextafter(measured["lower"], math.inf)) > exact_low
    assert Fraction(measured["upper"]) >= exact_high
    assert Fraction(math.nextafter(measured["upper"], -math.inf)) < exact_high
    assert Fraction(result["pixel_edge"]["lower"]) <= 3 - Fraction(0.1)
    assert Fraction(result["pixel_edge"]["upper"]) >= 4 + Fraction(0.1)


def test_thin_black_uncertainty_and_antialiased_rows_do_not_select_mean():
    image = Image.new("RGB", (12, 12), "white")
    for y in range(1, 7):
        image.putpixel((6, y), (0, 0, 0))
    for x in range(2, 10):
        image.putpixel((x, 3), (100, 130, 190))  # antialiased edge
        for y in (4, 5, 6):
            image.putpixel((x, y), (20, 80, 160))
    stream = BytesIO()
    image.save(stream, format="PNG")
    recipe = selection()
    recipe["edge_tolerance_pixels"] = 1
    result = read_bar_ordinate(stream.getvalue(), recipe)
    assert result["pixel_edge"] == {"top_row": 4, "centre": 4.5, "lower": 3., "upper": 6.}
    assert result["cell"]["value"] == 55
    assert (result["cell"]["lower"], result["cell"]["upper"]) == (40, 70)


def test_fraction_threshold_is_exact_and_channels_are_inclusive():
    recipe = selection()
    recipe["roi"]["right"] = 12  # 8 of 10 columns match.
    recipe["minimum_row_fraction"] = 0.8  # binary value is greater than 4/5.
    assert read_bar_ordinate(image_bytes(), recipe)["cell"]["unavailable_reason"] == "no_bar_pixels"
    recipe["minimum_row_fraction"] = math.nextafter(0.8, 0)
    assert read_bar_ordinate(image_bytes(), recipe)["cell"]["status"] == "populated"


@pytest.mark.parametrize("rows,runs,reason", [
    ((), [], "no_bar_pixels"), ((1, 3, 5), [], "no_bar_pixels"),
    ((1, 2, 4, 5), [{"top": 1, "bottom": 3}, {"top": 4, "bottom": 6}], "ambiguous_bar_runs"),
])
def test_missing_and_multiple_runs_preserve_context(rows, runs, reason):
    recipe = selection()
    result = read_bar_ordinate(image_bytes(rows), recipe)
    assert result["selection"] == recipe
    assert result["qualifying_runs"] == runs
    assert result["image_size"] == {"width": 12, "height": 12}
    assert result["pixel_edge"] is None
    assert result["cell"] == cell(None, None, None, unit="relative_turnover_percent", status="unavailable", unavailable_reason=reason)


def test_short_run_discarded_and_run_at_half_open_roi_end_retained():
    result = read_bar_ordinate(image_bytes((1, 8, 9, 10)), selection())
    assert result["qualifying_runs"] == [{"top": 8, "bottom": 10}]


def test_roi_starting_inside_bar_does_not_measure_artificial_mean_edge():
    recipe = selection()
    recipe["roi"]["top"] = 4  # Source fill starts at row 3, outside the ROI.
    result = read_bar_ordinate(image_bytes(), recipe)
    assert result["qualifying_runs"] == [{"top": 4, "bottom": 7}]
    assert result["selection"] == recipe
    assert result["pixel_edge"] is None
    assert result["cell"] == cell(None, None, None, unit="relative_turnover_percent",
        status="unavailable", unavailable_reason="truncated_mean_edge")
    # Even a true mean edge at the ROI boundary lacks a nonqualifying row.
    recipe["roi"]["top"] = 3
    assert read_bar_ordinate(image_bytes(), recipe)["cell"]["unavailable_reason"] == "truncated_mean_edge"
    recipe["roi"]["top"] = 2
    assert read_bar_ordinate(image_bytes(), recipe)["cell"]["status"] == "populated"


@pytest.mark.parametrize("path,value,code", [
    (("extra",), 0, "malformed_selection"),
    (("roi", "left"), True, "malformed_roi"),
    (("roi", "left"), -1, "invalid_roi_bounds"),
    (("roi", "right"), 2, "invalid_roi_bounds"),
    (("roi", "bottom"), 13, "roi_outside_image"),
    (("roi", "extra"), 0, "malformed_roi"),
    (("rgb_min",), [True, 80, 160], "malformed_selection"),
    (("rgb_max",), [256, 80, 160], "malformed_selection"),
    (("rgb_min",), (20, 80, 160), "malformed_selection"),
    (("rgb_min",), [20, 80], "malformed_selection"),
    (("rgb_max",), [19, 80, 160], "invalid_rgb_range"),
    (("minimum_row_fraction",), True, "malformed_selection"),
    (("minimum_row_fraction",), 0, "malformed_selection"),
    (("minimum_row_fraction",), 1.01, "malformed_selection"),
    (("minimum_run_rows",), 1., "malformed_selection"),
    (("minimum_run_rows",), False, "malformed_selection"),
    (("minimum_run_rows",), 0, "malformed_selection"),
    (("edge_tolerance_pixels",), -1, "malformed_selection"),
    (("edge_tolerance_pixels",), math.nan, "malformed_selection"),
    (("calibration", "extra"), 0, "malformed_calibration"),
    (("calibration", "first", "extra"), 0, "malformed_calibration"),
    (("calibration", "first", "pixel"), True, "malformed_calibration"),
    (("calibration", "first", "value"), math.inf, "malformed_calibration"),
    (("calibration", "first", "pixel"), 12, "calibration_outside_image"),
    (("calibration", "first", "pixel"), -0.1, "calibration_outside_image"),
    (("calibration", "second", "pixel"), 0, "degenerate_calibration"),
    (("calibration", "second", "value"), 100, "degenerate_calibration"),
    (("calibration", "unit"), [], "unsupported_calibration_unit"),
])
def test_closed_selection_errors(path, value, code):
    recipe = selection()
    target = recipe
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert_error(code, read_bar_ordinate, image_bytes(), recipe)


def test_missing_fields_and_validation_precedes_decoding(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid selection attempted image decoding")
    monkeypatch.setattr(Image, "open", forbidden)
    for key in selection():
        recipe = selection()
        del recipe[key]
        assert_error("malformed_selection", read_bar_ordinate, b"not image", recipe)


@pytest.mark.parametrize("data,code", [(b"", "image_bytes_required"), (bytearray(b"abc"), "image_bytes_required"),
    ("abc", "image_bytes_required"), (b"not an image", "malformed_image")])
def test_image_input_errors(data, code):
    assert_error(code, read_bar_ordinate, data, selection())


def test_malformed_truncated_unsupported_mode_format_and_frames():
    data = image_bytes()
    for malformed in (data[:45], data[:-1], data[:-8], data[:-12]):
        assert_error("malformed_image", read_bar_ordinate, malformed, selection())
    corrupted = bytearray(data)
    idat = corrupted.index(b"IDAT")
    corrupted[idat + 5] ^= 1
    assert_error("malformed_image", read_bar_ordinate, bytes(corrupted), selection())
    for mode, format, code in (("P", "PNG", "unsupported_image_mode"),
                               ("RGB", "GIF", "unsupported_image_format"),
                               ("CMYK", "JPEG", "unsupported_image_mode")):
        stream = BytesIO()
        Image.new(mode, (12, 12)).save(stream, format=format)
        assert_error(code, read_bar_ordinate, stream.getvalue(), selection())
    stream = BytesIO()
    Image.new("RGB", (12, 12), "red").save(stream, format="PNG", save_all=True,
        append_images=[Image.new("RGB", (12, 12), "blue")])
    assert_error("unsupported_image_frames", read_bar_ordinate, stream.getvalue(), selection())


@pytest.mark.parametrize("format", ["PNG", "JPEG"])
def test_nontrivial_exif_orientation_rejected(format):
    exif = Image.Exif()
    exif[274] = 6
    assert_error("unsupported_image_orientation", read_bar_ordinate,
                 image_bytes(format=format, exif=exif), selection())
    exif[274] = 1
    assert read_bar_ordinate(image_bytes(format=format, exif=exif), selection())["image_size"] == {"width": 12, "height": 12}


@pytest.mark.parametrize("mode", ["RGBA", "L"])
def test_explicit_mode_conversion_retains_coordinates(mode):
    recipe = selection()
    if mode == "L":
        recipe["rgb_min"] = recipe["rgb_max"] = [30, 30, 30]
    result = read_bar_ordinate(image_bytes(mode=mode), recipe)
    assert result["qualifying_runs"] == [{"top": 3, "bottom": 7}]


def test_jpeg_native_bytes_with_explicit_threshold():
    recipe = selection()
    recipe["rgb_min"], recipe["rgb_max"] = [15, 75, 155], [25, 85, 165]
    result = read_bar_ordinate(image_bytes(format="JPEG"), recipe)
    assert result["qualifying_runs"] == [{"top": 3, "bottom": 7}]


def test_no_clipping_and_large_finite_exact_intermediates():
    recipe = selection()
    recipe["calibration"]["first"]["value"] = 200
    recipe["calibration"]["second"]["value"] = 300
    assert read_bar_ordinate(image_bytes(), recipe)["cell"]["value"] == 235
    recipe["calibration"]["first"]["value"] = -sys.float_info.max
    recipe["calibration"]["second"]["value"] = sys.float_info.max
    result = read_bar_ordinate(image_bytes(), recipe)
    exact = -Fraction(sys.float_info.max) + Fraction(7, 20) * 2 * Fraction(sys.float_info.max)
    assert result["cell"]["value"] == float(exact)
    assert result["cell"]["status"] == "populated"
    recipe["calibration"]["first"]["value"] = 10 ** 400
    recipe["calibration"]["second"]["value"] = 10 ** 400 + 1
    result = read_bar_ordinate(image_bytes(), recipe)
    assert result["cell"]["unavailable_reason"] == "numerical_model_range"
    assert result["pixel_edge"] is not None


def test_unrepresentable_pixel_tolerance_and_ordinate_bounds():
    recipe = selection()
    recipe["edge_tolerance_pixels"] = 10 ** 400
    result = read_bar_ordinate(image_bytes(), recipe)
    assert result["pixel_edge"] is None
    assert result["qualifying_runs"] == [{"top": 3, "bottom": 7}]
    assert result["cell"]["unavailable_reason"] == "numerical_model_range"
    recipe = selection()
    recipe["edge_tolerance_pixels"] = sys.float_info.max
    result = read_bar_ordinate(image_bytes(), recipe)
    assert result["cell"]["unavailable_reason"] == "numerical_model_range"


def test_signed_comparison_exact_difference_and_outer_domain():
    first, second = cell(65, 60, 70), cell(75, 70, 80)
    before = deepcopy((first, second))
    assert compare_ordinate_cells(first, second) == {
        "version": "literature_ordinate_difference_v1", "cell": cell(-10., -20., 0., origin="derived")}
    assert compare_ordinate_cells(second, first)["cell"] == cell(10., 0., 20., origin="derived")
    assert (first, second) == before
    result = compare_ordinate_cells(cell(0.1, 0.1, 0.1), cell(0.3, 0.3, 0.3))["cell"]
    exact = Fraction(0.1) - Fraction(0.3)
    assert result["value"] == float(exact)
    assert Fraction(result["lower"]) <= exact <= Fraction(result["upper"])


@pytest.mark.parametrize("reason", ["no_bar_pixels", "ambiguous_bar_runs", "truncated_mean_edge", "numerical_model_range"])
def test_unavailable_comparison(reason):
    unknown = cell(None, None, None, status="unavailable", unavailable_reason=reason)
    for first, second in ((unknown, cell()), (cell(), unknown), (unknown, unknown)):
        result = compare_ordinate_cells(first, second)["cell"]
        assert result == cell(None, None, None, status="unavailable", unavailable_reason="missing_ordinate", origin="derived")


@pytest.mark.parametrize("changes,code", [
    ({"extra": 0}, "malformed_ordinate_cell"),
    ({"value": True}, "malformed_ordinate_cell"),
    ({"lower": math.nan}, "malformed_ordinate_cell"),
    ({"upper": math.inf}, "malformed_ordinate_cell"),
    ({"lower": 2}, "invalid_ordinate_bounds"),
    ({"unit": "wrong"}, "unsupported_ordinate_unit"),
    ({"origin": "derived"}, "invalid_ordinate_origin"),
    ({"bound_kind": "ci"}, "invalid_ordinate_bound_kind"),
    ({"status": "unknown"}, "invalid_ordinate_availability"),
    ({"unavailable_reason": "no_bar_pixels"}, "invalid_ordinate_availability"),
    ({"status": "unavailable", "unavailable_reason": "no_bar_pixels"}, "invalid_ordinate_availability"),
])
def test_comparison_rejects_malformed_cells(changes, code):
    assert_error(code, compare_ordinate_cells, cell(**changes), cell())
    assert_error(code, compare_ordinate_cells, cell(), cell(**changes))


def test_unit_mismatch_even_if_unavailable_and_closed_cell_fields():
    assert_error("ordinate_unit_mismatch", compare_ordinate_cells, cell(), cell(unit="nanomolar"))
    unknown = cell(None, None, None, unit="nanomolar", status="unavailable", unavailable_reason="no_bar_pixels")
    assert_error("ordinate_unit_mismatch", compare_ordinate_cells, cell(), unknown)
    for key in cell():
        malformed = cell()
        del malformed[key]
        assert_error("malformed_ordinate_cell", compare_ordinate_cells, malformed, cell())


def test_comparison_overflow_and_large_cancelling_intermediates():
    largest = sys.float_info.max
    assert compare_ordinate_cells(cell(largest, largest, largest), cell(-largest, -largest, -largest))["cell"] == cell(
        None, None, None, status="unavailable", unavailable_reason="numerical_model_range", origin="derived")
    assert compare_ordinate_cells(cell(largest, largest, largest), cell(largest, largest, largest))["cell"] == cell(0., 0., 0., origin="derived")
    # A representable centre does not excuse an unrepresentable outer bound.
    assert compare_ordinate_cells(cell(0, -largest, largest), cell(0, -largest, largest))["cell"]["unavailable_reason"] == "numerical_model_range"


def test_percent_difference_is_percentage_points_and_cannot_be_graph_input():
    first = cell(65, 60, 70, unit="relative_turnover_percent")
    second = cell(75, 70, 80, unit="relative_turnover_percent")
    result = compare_ordinate_cells(first, second)["cell"]
    assert result == cell(-10., -20., 0., origin="derived", unit="relative_turnover_percentage_points")
    unknown = cell(None, None, None, unit="relative_turnover_percent", status="unavailable", unavailable_reason="truncated_mean_edge")
    assert compare_ordinate_cells(first, unknown)["cell"]["unit"] == "relative_turnover_percentage_points"
    assert_error("unsupported_ordinate_unit", compare_ordinate_cells, result, first)
    assert_error("unsupported_calibration_unit", read_bar_ordinate, image_bytes(),
        {**selection(), "calibration": {**selection()["calibration"], "unit": "relative_turnover_percentage_points"}})


def test_underflow_is_enclosed_outward_without_inventing_zero_precision():
    recipe = selection()
    recipe["calibration"]["first"]["value"] = 0
    recipe["calibration"]["second"]["value"] = math.ulp(0.0)
    result = read_bar_ordinate(image_bytes(), recipe)["cell"]
    assert result["value"] == result["lower"] == 0
    assert result["upper"] == math.ulp(0.0)
    assert result["status"] == "populated"
