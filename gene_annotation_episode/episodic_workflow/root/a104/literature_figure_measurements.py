"""Deterministic native bar ordinates and representation differences.

Selections, calibration and tolerance are caller-supplied digitization
assumptions. These functions make no experimental or biological inference.
Error codes are stable; ``ContractError.detail['field_path']`` locates invalid
input. Only decoded RGB, RGBA and L PNG/JPEG images are supported.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
from io import BytesIO
import math
import warnings

from PIL import Image, UnidentifiedImageError

from .domain import ContractError


BAR_VERSION = "literature_bar_ordinate_v1"
DIFFERENCE_VERSION = "literature_ordinate_difference_v1"
BOUND_KIND = "conditional_digitization_not_confidence_interval"
UNITS = ("relative_turnover_percent", "arbitrary_signal", "nanomolar")
_CELL_KEYS = ("value", "lower", "upper", "unit", "origin", "bound_kind",
              "status", "unavailable_reason")
_REASONS = ("no_bar_pixels", "ambiguous_bar_runs", "truncated_mean_edge", "numerical_model_range")


def _fail(code, path):
    raise ContractError(code, detail={"field_path": path})


def _closed(value, keys, code, path):
    if not isinstance(value, dict) or set(value) != set(keys):
        _fail(code, path)


def _number(value, code, path):
    # Integers are finite regardless of whether they fit a binary float.
    if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
        _fail(code, path)
    return Fraction(value)


def _validate_selection(selection):
    _closed(selection, ("roi", "rgb_min", "rgb_max", "minimum_row_fraction",
        "minimum_run_rows", "edge_tolerance_pixels", "calibration"),
        "malformed_selection", "selection")
    roi = selection["roi"]
    _closed(roi, ("left", "top", "right", "bottom"), "malformed_roi", "roi")
    for key, value in roi.items():
        if type(value) is not int:
            _fail("malformed_roi", "roi." + key)
    if roi["left"] < 0 or roi["top"] < 0 or roi["right"] <= roi["left"] or roi["bottom"] <= roi["top"]:
        _fail("invalid_roi_bounds", "roi")
    for name in ("rgb_min", "rgb_max"):
        values = selection[name]
        if not isinstance(values, list) or len(values) != 3:
            _fail("malformed_selection", name)
        if any(type(v) is not int or not 0 <= v <= 255 for v in values):
            _fail("malformed_selection", name)
    if any(a > b for a, b in zip(selection["rgb_min"], selection["rgb_max"])):
        _fail("invalid_rgb_range", "rgb_max")
    fraction = _number(selection["minimum_row_fraction"], "malformed_selection", "minimum_row_fraction")
    if not 0 < fraction <= 1:
        _fail("malformed_selection", "minimum_row_fraction")
    run_rows = selection["minimum_run_rows"]
    if type(run_rows) is not int or run_rows <= 0:
        _fail("malformed_selection", "minimum_run_rows")
    tolerance = _number(selection["edge_tolerance_pixels"], "malformed_selection", "edge_tolerance_pixels")
    if tolerance < 0:
        _fail("malformed_selection", "edge_tolerance_pixels")
    calibration = selection["calibration"]
    _closed(calibration, ("first", "second", "unit"), "malformed_calibration", "calibration")
    points = []
    for name in ("first", "second"):
        point = calibration[name]
        path = "calibration." + name
        _closed(point, ("pixel", "value"), "malformed_calibration", path)
        points.append(tuple(_number(point[key], "malformed_calibration", path + "." + key)
                            for key in ("pixel", "value")))
    if calibration["unit"] not in UNITS:
        _fail("unsupported_calibration_unit", "calibration.unit")
    if points[0][0] == points[1][0] or points[0][1] == points[1][1]:
        _fail("degenerate_calibration", "calibration")
    return fraction, tolerance, points


def _float(exact, direction=0):
    """Nearest float, optionally moved outward to contain an exact rational."""
    value = float(exact)  # May raise OverflowError; callers retain unknown cells.
    if not math.isfinite(value):
        raise OverflowError
    if direction < 0 and Fraction(value) > exact:
        value = math.nextafter(value, -math.inf)
    elif direction > 0 and Fraction(value) < exact:
        value = math.nextafter(value, math.inf)
    if not math.isfinite(value):
        raise OverflowError
    return value


def _cell(unit, origin, *, value=None, lower=None, upper=None, reason=None):
    return {"value": value, "lower": lower, "upper": upper, "unit": unit,
            "origin": origin, "bound_kind": BOUND_KIND,
            "status": "populated" if reason is None else "unavailable",
            "unavailable_reason": reason}


def _numerical_cell(unit, origin, value, lower, upper):
    try:
        return _cell(unit, origin, value=_float(value), lower=_float(lower, -1),
                     upper=_float(upper, 1))
    except OverflowError:
        return _cell(unit, origin, reason="numerical_model_range")


def read_bar_ordinate(image_bytes, selection):
    """Count native thresholded rows and map one retained fill edge to an ordinate.

    Closed selection validation precedes pixel decoding/counting. Calibration
    coordinates must lie in [0, image height), including fractional positions.
    Neither EXIF orientation nor alpha compositing changes native coordinates
    or colours; RGBA conversion simply removes alpha for RGB counting.
    """
    fraction, tolerance, points = _validate_selection(selection)
    if not isinstance(image_bytes, bytes) or not image_bytes:
        _fail("image_bytes_required", "image_bytes")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_bytes)) as source:
                if source.format not in ("PNG", "JPEG"):
                    _fail("unsupported_image_format", "image_bytes")
                if source.mode not in ("RGB", "RGBA", "L"):
                    _fail("unsupported_image_mode", "image_bytes")
                if getattr(source, "n_frames", 1) != 1:
                    _fail("unsupported_image_frames", "image_bytes")
                width, height = source.size
                roi = selection["roi"]
                if roi["right"] > width or roi["bottom"] > height:
                    _fail("roi_outside_image", "roi")
                for name, (pixel, _) in zip(("first", "second"), points):
                    if not 0 <= pixel < height:
                        _fail("calibration_outside_image", "calibration." + name + ".pixel")
                # Pillow's PNG verify stops before checking IEND's CRC and can
                # accept a truncated IEND. Require the complete terminal chunk.
                if source.format == "PNG" and not image_bytes.endswith(b"\x00\x00\x00\x00IEND\xaeB\x60\x82"):
                    _fail("malformed_image", "image_bytes")
                source.verify()
            # verify invalidates the decoder; reopen the same immutable bytes.
            with Image.open(BytesIO(image_bytes)) as source:
                orientation = source.getexif().get(274, 1)
                if type(orientation) is not int or orientation != 1:
                    _fail("unsupported_image_orientation", "image_bytes")
                source.load()
                rgb = source.convert("RGB")
    except ContractError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ContractError("malformed_image", detail={"field_path": "image_bytes"}) from exc

    runs, start = [], None
    low, high = selection["rgb_min"], selection["rgb_max"]
    roi_width = roi["right"] - roi["left"]
    try:
        pixels = rgb.load()
        for y in range(roi["top"], roi["bottom"]):
            count = sum(all(low[c] <= pixels[x, y][c] <= high[c] for c in range(3))
                        for x in range(roi["left"], roi["right"]))
            qualifies = count * fraction.denominator >= roi_width * fraction.numerator
            if qualifies and start is None:
                start = y
            if not qualifies and start is not None:
                if y - start >= selection["minimum_run_rows"]:
                    runs.append({"top": start, "bottom": y})
                start = None
        if start is not None and roi["bottom"] - start >= selection["minimum_run_rows"]:
            runs.append({"top": start, "bottom": roi["bottom"]})
    finally:
        rgb.close()

    unit = selection["calibration"]["unit"]
    result = {"version": BAR_VERSION, "image_sha256": hashlib.sha256(image_bytes).hexdigest(),
              "image_size": {"width": width, "height": height},
              "selection": deepcopy(selection), "qualifying_runs": runs,
              "pixel_edge": None, "cell": None}
    if len(runs) != 1:
        result["cell"] = _cell(unit, "graph_derived", reason=(
            "no_bar_pixels" if not runs else "ambiguous_bar_runs"))
        return result

    y = runs[0]["top"]
    if y == roi["top"]:
        result["cell"] = _cell(unit, "graph_derived", reason="truncated_mean_edge")
        return result
    centre, lower, upper = Fraction(y) + Fraction(1, 2), Fraction(y) - tolerance, Fraction(y + 1) + tolerance
    try:
        result["pixel_edge"] = {"top_row": y, "centre": _float(centre),
                                "lower": _float(lower, -1), "upper": _float(upper, 1)}
    except OverflowError:
        result["cell"] = _cell(unit, "graph_derived", reason="numerical_model_range")
        return result
    (p1, v1), (p2, v2) = points

    def ordinate(pixel):
        return v1 + (pixel - p1) * (v2 - v1) / (p2 - p1)

    endpoints = sorted((ordinate(lower), ordinate(upper)))
    result["cell"] = _numerical_cell(unit, "graph_derived", ordinate(centre), *endpoints)
    return result


def _validate_cell(cell, path):
    _closed(cell, _CELL_KEYS, "malformed_ordinate_cell", path)
    if cell["unit"] not in UNITS:
        _fail("unsupported_ordinate_unit", path + ".unit")
    if cell["origin"] != "graph_derived":
        _fail("invalid_ordinate_origin", path + ".origin")
    if cell["bound_kind"] != BOUND_KIND:
        _fail("invalid_ordinate_bound_kind", path + ".bound_kind")
    if cell["status"] == "unavailable":
        if cell["unavailable_reason"] not in _REASONS or any(cell[k] is not None for k in ("value", "lower", "upper")):
            _fail("invalid_ordinate_availability", path)
        return
    if cell["status"] != "populated" or cell["unavailable_reason"] is not None:
        _fail("invalid_ordinate_availability", path)
    for key in ("value", "lower", "upper"):
        _number(cell[key], "malformed_ordinate_cell", path + "." + key)
    if not cell["lower"] <= cell["value"] <= cell["upper"]:
        _fail("invalid_ordinate_bounds", path)


def compare_ordinate_cells(first, second):
    """Subtract graph ordinates; the caller establishes scientific comparability."""
    _validate_cell(first, "first")
    _validate_cell(second, "second")
    if first["unit"] != second["unit"]:
        _fail("ordinate_unit_mismatch", "second.unit")
    difference_unit = ("relative_turnover_percentage_points"
                       if first["unit"] == "relative_turnover_percent" else first["unit"])
    if first["status"] == "unavailable" or second["status"] == "unavailable":
        cell = _cell(difference_unit, "derived", reason="missing_ordinate")
    else:
        cell = _numerical_cell(difference_unit, "derived",
            Fraction(first["value"]) - Fraction(second["value"]),
            Fraction(first["lower"]) - Fraction(second["upper"]),
            Fraction(first["upper"]) - Fraction(second["lower"]))
    return {"version": DIFFERENCE_VERSION, "cell": cell}


__all__ = ["read_bar_ordinate", "compare_ordinate_cells"]
