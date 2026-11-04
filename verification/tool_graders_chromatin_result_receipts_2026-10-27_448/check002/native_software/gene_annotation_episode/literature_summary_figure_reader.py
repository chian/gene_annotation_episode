"""Explicit image selections for linear/log-displayed means and error caps.

The selections identify ink, never the experimental meaning of an error bar.
Logarithmic display is independent of the statistic's underlying scale. Bounds
describe only the supplied pixel tolerance, not sampling uncertainty.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import math

from .domain import ContractError
from .literature_figure_measurements import read_bar_ordinate

VERSION = "literature_summary_figure_v1"
BOUND_KIND = "conditional_digitization_not_confidence_interval"
UNITS = ("events_per_100000_cells", "fraction", "CFU_per_mL", "minutes", "per_min",
         "molecules_per_cell", "normalized_signal", "mg_per_mL")


def _fail(code, field):
    raise ContractError(code, detail={"field_path": field})


def _closed(value, fields, field):
    if not isinstance(value, dict) or set(value) != set(fields):
        _fail("closed_summary_figure_fields_required", field)


def _number(value, field):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_summary_figure_number_required", field)
    return Fraction(value)


def _decimal(value):
    value = Fraction(value)
    return Decimal(value.numerator) / Decimal(value.denominator)


def _project(value, direction=0):
    out = float(value)
    if not math.isfinite(out) or out == 0 and value != 0:
        raise OverflowError
    # The transcendental result has 100 significant decimal digits. One extra
    # outward binary step also covers its decimal rounding; this is numerical
    # enclosure, separate from the selected digitization interval.
    if direction:
        out = math.nextafter(out, math.inf if direction > 0 else -math.inf)
    if not math.isfinite(out):
        raise OverflowError
    return out


def read_summary_figure(image_bytes, selection):
    """Read selected mean edges and optional cap centres from exact image bytes.

    Each feature uses the old bar reader's validated decoder/threshold counting
    with an identity pixel calibration. ``top_edge`` selects a fill edge;
    ``run_center`` selects the centre of one horizontal cap. Multiple runs,
    clipped selections and missing ink stay explicit; no preferred run is picked.
    """
    _closed(selection, ("calibration", "mean", "upper_error", "lower_error"), "selection")
    calibration = selection["calibration"]
    _closed(calibration, ("scale", "first", "second", "unit"), "calibration")
    if calibration["scale"] not in ("linear", "log10") or calibration["unit"] not in UNITS:
        _fail("unsupported_summary_figure_calibration", "calibration")
    points = []
    for key in ("first", "second"):
        point = calibration[key]
        _closed(point, ("pixel", "value"), "calibration." + key)
        p, v = (_number(point[k], "calibration." + key + "." + k) for k in ("pixel", "value"))
        if calibration["scale"] == "log10" and v <= 0:
            _fail("positive_log_tick_required", "calibration." + key + ".value")
        points.append((p, v))
    if points[0][0] == points[1][0] or points[0][1] == points[1][1]:
        _fail("degenerate_summary_figure_calibration", "calibration")
    features = {}
    identity_calibration = {"first": {"pixel": float(points[0][0]), "value": float(points[0][0])},
                            "second": {"pixel": float(points[1][0]), "value": float(points[1][0])},
                            "unit": "arbitrary_signal"}
    digest = size = None
    for key in ("mean", "upper_error", "lower_error"):
        feature = selection[key]
        if feature is None:
            if key == "mean":
                _fail("mean_feature_required", key)
            features[key] = None
            continue
        _closed(feature, ("kind", "roi", "rgb_min", "rgb_max", "minimum_row_fraction",
                         "minimum_run_rows", "edge_tolerance_pixels"), key)
        if feature["kind"] not in ("top_edge", "run_center"):
            _fail("unsupported_summary_figure_feature", key + ".kind")
        recipe = {k: deepcopy(v) for k, v in feature.items() if k != "kind"}
        recipe["calibration"] = deepcopy(identity_calibration)
        read = read_bar_ordinate(image_bytes, recipe)
        digest, size = read["image_sha256"], read["image_size"]
        item = {"pixel": None, "value": None, "lower": None, "upper": None,
                "decimal_value": None, "decimal_lower": None, "decimal_upper": None,
                "status": read["cell"]["status"], "unavailable_reason": read["cell"]["unavailable_reason"],
                "qualifying_runs": read["qualifying_runs"]}
        if read["cell"]["status"] == "populated":
            run = read["qualifying_runs"][0]
            if feature["kind"] == "run_center" and run["bottom"] == feature["roi"]["bottom"]:
                item.update(status="unavailable", unavailable_reason="truncated_error_cap")
                features[key] = item
                continue
            centre = (Fraction(run["top"]) + Fraction(1, 2) if feature["kind"] == "top_edge"
                      else Fraction(run["top"] + run["bottom"], 2))
            tolerance = Fraction(feature["edge_tolerance_pixels"])
            lo, hi = centre - Fraction(1, 2) - tolerance, centre + Fraction(1, 2) + tolerance
            if lo < 0 or hi > size["height"]:
                item.update(status="unavailable", unavailable_reason="pixel_tolerance_outside_image")
            else:
                item["pixel"] = {"value": float(centre), "lower": float(lo), "upper": float(hi)}
                try:
                    with localcontext() as ctx:
                        ctx.prec = 100
                        p1, v1 = map(_decimal, points[0]); p2, v2 = map(_decimal, points[1])
                        if calibration["scale"] == "log10":
                            v1, v2 = v1.log10(), v2.log10()
                        def ordinate(pixel):
                            q = v1 + (_decimal(pixel)-p1)*(v2-v1)/(p2-p1)
                            return Decimal(10) ** q if calibration["scale"] == "log10" else q
                        endpoints = sorted((ordinate(lo), ordinate(hi)))
                        central = ordinate(centre)
                        item.update(decimal_value=str(central), decimal_lower=str(endpoints[0]), decimal_upper=str(endpoints[1]))
                        item.update(value=_project(central), lower=_project(endpoints[0], -1),
                                    upper=_project(endpoints[1], 1))
                except (OverflowError, ArithmeticError, ValueError):
                    item.update(status="unavailable", unavailable_reason="numerical_model_range")
                    item.update(value=None, lower=None, upper=None)
        features[key] = item
    return {"version": VERSION, "image_sha256": digest, "image_size": size,
            "selection": deepcopy(selection), "unit": calibration["unit"],
            "bound_kind": BOUND_KIND, "features": features}


__all__ = ["VERSION", "BOUND_KIND", "read_summary_figure"]
