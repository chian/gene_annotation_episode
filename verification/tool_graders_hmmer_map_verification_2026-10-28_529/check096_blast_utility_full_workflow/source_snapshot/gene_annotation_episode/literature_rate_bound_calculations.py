"""Images of reported point/limit rate constraints, without a noise model.

This additive calculator consumes the existing explicitly mapped summary-table
extraction. It preserves strict endpoints and never interprets a detection
threshold as an observed zero, confidence interval, or assay error probability.
"""
from __future__ import annotations

from copy import deepcopy
import csv
from decimal import Decimal
from fractions import Fraction
import math
import json

from .literature_experimental_contracts import ExperimentalContractError, RATE_UNITS, validate_rate_extraction
from .literature_rate_calculations import _select, _identity, _BASE_UNITS
from .literature_rate_reader import read_rate_table, _VALUE


VERSION = "a105_rate_constraint_cells_v1"


def _domain(row, data):
    if row is None or row["status"] not in ("observed", "censored"):
        return None
    # The existing extraction retains original table decimals. Recheck the
    # selected row, then operate on those decimals rather than already-rounded
    # float projections. No original artifact or source callback is opened.
    parsed = None
    for delimiter in (",", "\t"):
        source = row["source"]
        try:
            retained = read_rate_table({"source_ref":source["source_ref"],
                "artifact_ref":source["artifact_ref"], "representation":source["representation"],
                "delimiter":delimiter,"text":source["header"]+"\n"+source["raw_row"]+"\n"},
                expected_subject=data["subject"], expected_experiment=data["experiment"])
        except ExperimentalContractError:
            continue
        candidate = deepcopy(row);candidate["source"]["row_number"] = 2
        if json.dumps(candidate,sort_keys=True,allow_nan=False) != json.dumps(retained["rows"][0],sort_keys=True,allow_nan=False):
            raise ExperimentalContractError("source_operand_binding_mismatch", "row")
        fields = dict(zip(next(csv.reader([source["header"]],delimiter=delimiter)),
                          next(csv.reader([source["raw_row"]],delimiter=delimiter))))
        parsed = _VALUE.fullmatch(fields["value"])
        break
    if parsed is None:
        raise ExperimentalContractError("source_operand_binding_mismatch", "row")
    value = Fraction(parsed.group("number")) * Fraction(str(RATE_UNITS[row["unit"]][1]))
    relation = row["bound"]
    if relation == "none":
        return value, value, True, True
    if relation in ("lt", "le"):
        return None, value, False, relation == "le"
    return value, None, relation == "ge", False


def _contains_zero(domain):
    lower, upper, lc, uc = domain
    return ((lower is None or lower < 0 or lower == 0 and lc)
            and (upper is None or upper > 0 or upper == 0 and uc))


def _affine(domain, multiplier, offset=Fraction()):
    lower, upper, lc, uc = domain
    if multiplier == 0:
        return offset, offset, True, True
    if multiplier < 0:
        lower, upper, lc, uc = upper, lower, uc, lc
    return (None if lower is None else multiplier*lower+offset,
            None if upper is None else multiplier*upper+offset, lc, uc)


def _difference(a, b):
    return (None if a[0] is None or b[1] is None else a[0]-b[1],
            None if a[1] is None or b[0] is None else a[1]-b[0],
            a[2] and b[3], a[3] and b[2])


def _reciprocal(domain):
    lower, upper, lc, uc = domain
    return (Fraction() if upper is None else None if upper == 0 else 1/upper,
            Fraction() if lower is None else None if lower == 0 else 1/lower,
            uc if upper not in (None, 0) else False,
            lc if lower not in (None, 0) else False)


def _order(value):
    return (-1, 0) if value == "-inf" else (1, 0) if value == "inf" else (0, value)


def _product(a, b):
    """Extended interval multiplication, including attainable zero endpoints."""
    def multiply(x, y):
        if x == 0 or y == 0:
            return Fraction()
        if isinstance(x, Fraction) and isinstance(y, Fraction):
            return x*y
        sign = (-1 if x == "-inf" or isinstance(x, Fraction) and x < 0 else 1)
        sign *= (-1 if y == "-inf" or isinstance(y, Fraction) and y < 0 else 1)
        return "-inf" if sign < 0 else "inf"
    left = ((a[0] if a[0] is not None else "-inf", a[2]),
            (a[1] if a[1] is not None else "inf", a[3]))
    right = ((b[0] if b[0] is not None else "-inf", b[2]),
             (b[1] if b[1] is not None else "inf", b[3]))
    products = [(multiply(x, y), xc and yc) for x, xc in left for y, yc in right]
    lower = min((v for v, closed in products), key=_order)
    upper = max((v for v, closed in products), key=_order)
    zero_attainable = _contains_zero(a) or _contains_zero(b)
    def closed(value):
        return isinstance(value, Fraction) and (value == 0 and zero_attainable
            or any(v == value and c for v, c in products))
    return (lower if isinstance(lower, Fraction) else None,
            upper if isinstance(upper, Fraction) else None, closed(lower), closed(upper))


def _exact(value):
    return None if value is None else {"numerator": str(Decimal(value.numerator)),
                                      "denominator": str(Decimal(value.denominator))}


def _cell(domain, unit, formula, rows, *, reason=None):
    point = domain is not None and domain[0] is not None and domain[0] == domain[1]
    numeric = []
    for index, value in enumerate(domain[:2] if domain is not None else (None, None)):
        try:
            projected = float(value) if value is not None else None
            if projected is not None and (not math.isfinite(projected) or projected == 0 and value != 0):
                projected, reason = None, "numerical_model_range"
            elif projected is not None and not point:
                # A finite float endpoint must not tighten the exact constraint.
                if index == 0 and Fraction(projected) > value:
                    projected = math.nextafter(projected, -math.inf)
                if index == 1 and Fraction(projected) < value:
                    projected = math.nextafter(projected, math.inf)
        except (OverflowError, ValueError):
            projected, reason = None, "numerical_model_range"
        numeric.append(projected)
    return {"value": numeric[0] if point and reason is None else None,
            "lower": numeric[0], "upper": numeric[1],
            "lower_closed": bool(domain and domain[0] is not None and domain[2]),
            "upper_closed": bool(domain and domain[1] is not None and domain[3]),
            "exact_lower": _exact(domain[0]) if domain else None,
            "exact_upper": _exact(domain[1]) if domain else None,
            "status": "unavailable" if reason or domain is None else "point" if point else
                      "unbounded" if domain[0] is None and domain[1] is None else "bounded",
            "unavailable_reason": reason, "unit": unit, "formula": formula,
            "origin": "derived", "approximate": any(row["approximate"] for row in rows),
            "float_bound_projection": "outward_when_rounded; exact rational endpoints retained",
            "bound_kind": "reported_constraint_image_outer_bound",
            "input_rows": [_identity(row) for row in rows],
            "input_origins": list(dict.fromkeys(row["origin"] for row in rows))}


def populate_rate_table_bounds(extraction, *, reference_arm, test_arm,
                               reference_condition, test_condition):
    """Populate signed differences and normalized contrasts from v1 table rows.

    Domains are marginal reported constraints. Their rectangular image is an
    outer bound if additional dependence exists; no independence is assumed.
    A denominator admitting zero returns an explicit unavailable ratio because
    one interval cannot generally represent its image. Point and individual
    limit cells remain available. Approximation qualifiers remain qualifiers.
    Native-span v2 population remains a separate unimplemented binding here.
    """
    if not isinstance(extraction, dict) or extraction.get("version") != "a105_rate_extraction_v1":
        raise ExperimentalContractError("table_v1_extraction_required", "extraction")
    data = validate_rate_extraction(extraction)
    for name, value in (("reference_arm", reference_arm), ("test_arm", test_arm),
                        ("reference_condition", reference_condition), ("test_condition", test_condition)):
        if not isinstance(value, str) or not value.strip():
            raise ExperimentalContractError("nonempty_selection_required", name)
    if reference_arm == test_arm:
        raise ExperimentalContractError("distinct_arms_required", "test_arm")
    a, ar, arows = _select(data["rows"], reference_arm, reference_condition, "reference")
    b, br, brows = _select(data["rows"], test_arm, test_condition, "test")
    if ar == "censored_measurement": ar = None
    if br == "censored_measurement": br = None
    ad, bd = _domain(a, data) if not ar else None, _domain(b, data) if not br else None
    au = _BASE_UNITS[RATE_UNITS[a["unit"]][0]] if a else None
    bu = _BASE_UNITS[RATE_UNITS[b["unit"]][0]] if b else None
    reason = ar or br
    if a and b:
        if au != bu: reason = "incompatible_rate_dimensions"
        elif a["endpoint"] != b["endpoint"]: reason = "endpoint_mismatch"
        elif a["normalization"] != b["normalization"]: reason = "normalization_mismatch"
    rows = [*arows, *brows]
    unit = au if au == bu else None
    difference = _difference(ad, bd) if reason is None else None
    ratio_reason = reason or ("reference_domain_includes_zero" if _contains_zero(ad) else None)
    ratio = _product(bd, _reciprocal(ad)) if ratio_reason is None else None
    cells = {
        "reference_rate": _cell(ad, au, "source_reference_constraint*unit_multiplier", arows, reason=ar),
        "test_rate": _cell(bd, bu, "source_test_constraint*unit_multiplier", brows, reason=br),
        "rate_difference": _cell(difference, unit, "reference_rate-test_rate", rows, reason=reason),
        "retained_fraction": _cell(ratio, "fraction", "test_rate/reference_rate", rows, reason=ratio_reason),
        "fractional_decrease": _cell(_affine(ratio, Fraction(-1), Fraction(1)) if ratio is not None else None,
            "fraction", "1-test_rate/reference_rate", rows, reason=ratio_reason),
    }
    return {"version": VERSION, "axis": "A105", "scope": "source_preparation_endpoint",
            "subject": data["subject"], "experiment": data["experiment"],
            "comparison": {"reference_arm": reference_arm, "test_arm": test_arm,
                "reference_condition": reference_condition, "test_condition": test_condition,
                "endpoint": a["endpoint"] if a else b["endpoint"] if b else None,
                "normalization": a["normalization"] if a else b["normalization"] if b else None},
            "extraction": data, "cells": cells,
            "source_uncertainty": {"reference": deepcopy(a["uncertainty"]) if a else None,
                                   "test": deepcopy(b["uncertainty"]) if b else None},
            "sampling_confidence_interval": None, "assay_error_probability": None, "annotation_credit": None}


__all__ = ["VERSION", "populate_rate_table_bounds"]
