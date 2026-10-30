"""Pure conditional selected-model geometry components for A111.

The caller binds source identities and physical selections. These calculations
do not measure population occupancy, causal isolation, target correspondence or
annotation credit. Bounds enclose conditional arithmetic, not measurement
uncertainty, probabilities or independent observations.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import math

from .literature_experimental_contracts import ExperimentalContractError


VERSION = "a111_source_geometry_v1"
COMPONENTS = (
    "local_fit_index", "geometry_support_fraction", "geometry_opposition_fraction",
    "source_geometry_positive", "source_geometry_opposing", "source_geometry_signed",
)
_GEOMETRY_REASONS = (
    "endpoint_unmodeled", "ambiguous_atom_selection", "endpoint_identity_mismatch",
    "coordinate_unreported",
)
_LOCAL_REASONS = (
    "local_rscc_unreported", "local_endpoint_unmodeled", "ambiguous_local_selection",
    "local_identity_mismatch",
)
REASONS = (
    "local_panel_empty", "geometry_panel_empty", "validation_not_joined",
    "geometry_inputs_unreported", "numerical_model_range",
    *_GEOMETRY_REASONS, *_LOCAL_REASONS,
)
_CONDITIONS = (
    "selected_model_assignment", "proposed_geometry_predicates",
    "unreported_coordinate_uncertainty",
)
_PRODUCT_CONDITIONS = (
    "conditional_state_unit_occupancy", "single_state_no_causal_comparison",
    "assignment_conditioned_isolation", "source_geometry_convention",
)
CONDITIONAL_CODES = (
    *_CONDITIONS, *_PRODUCT_CONDITIONS, "residue_rscc_squared_minimum",
)
_BINDINGS = (
    "matching_entry_revision", "entry_mismatch", "revision_mismatch",
    "binding_unreported", "not_supplied",
)
_SCOPE = "conditional_deposited_model_geometry"
_ZERO, _ONE = Fraction(0), Fraction(1)


class StructureCalculationError(ExperimentalContractError):
    """A repairable structural calculation field or relationship failure."""


def _fail(code, field):
    raise StructureCalculationError(code, field)


def _fields(value, names, field):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail("closed_fields_required", field)


def _number(value, field):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)


def _endpoint(value, field):
    if value is None:
        return
    if not isinstance(value, list) or not value:
        _fail("nonempty_coordinate_group_required", field)
    for index, xyz in enumerate(value):
        if not isinstance(xyz, list) or len(xyz) != 3:
            _fail("xyz_triple_required", f"{field}[{index}]")
        for axis, coordinate in enumerate(xyz):
            _number(coordinate, f"{field}[{index}][{axis}]")


def _validate(inputs):
    _fields(inputs, ("geometry_members", "local_members", "validation_binding",
                     "origin", "evaluation_scope"), "inputs")
    for field, choices in (("validation_binding", _BINDINGS),
                           ("origin", ("reported", "synthetic")),
                           ("evaluation_scope", (_SCOPE,))):
        if not isinstance(inputs[field], str) or inputs[field] not in choices:
            _fail("unsupported_" + field, field)
    for field in ("geometry_members", "local_members"):
        if not isinstance(inputs[field], list):
            _fail("panel_list_required", field)
    for index, member in enumerate(inputs["geometry_members"]):
        field = f"geometry_members[{index}]"
        _fields(member, ("endpoint_a", "endpoint_b", "positive_max_A",
                         "incompatible_min_A", "unavailable_reason"), field)
        for endpoint in ("endpoint_a", "endpoint_b"):
            _endpoint(member[endpoint], field + "." + endpoint)
        for cutoff in ("positive_max_A", "incompatible_min_A"):
            _number(member[cutoff], field + "." + cutoff)
        if member["positive_max_A"] < 0:
            _fail("nonnegative_positive_cutoff_required", field + ".positive_max_A")
        if member["incompatible_min_A"] <= member["positive_max_A"]:
            _fail("disjoint_geometry_cutoffs_required", field + ".incompatible_min_A")
        missing = member["endpoint_a"] is None or member["endpoint_b"] is None
        reason = member["unavailable_reason"]
        if missing:
            if not isinstance(reason, str) or reason not in _GEOMETRY_REASONS:
                _fail("geometry_missing_reason_required", field + ".unavailable_reason")
        elif reason is not None:
            _fail("known_geometry_has_no_missing_reason", field + ".unavailable_reason")
    for index, member in enumerate(inputs["local_members"]):
        field = f"local_members[{index}]"
        _fields(member, ("rscc", "unavailable_reason"), field)
        if member["rscc"] is None:
            if (not isinstance(member["unavailable_reason"], str)
                    or member["unavailable_reason"] not in _LOCAL_REASONS):
                _fail("local_missing_reason_required", field + ".unavailable_reason")
        else:
            _number(member["rscc"], field + ".rscc")
            if not -1 <= member["rscc"] <= 1:
                _fail("rscc_out_of_range", field + ".rscc")
            if member["unavailable_reason"] is not None:
                _fail("known_rscc_has_no_missing_reason", field + ".unavailable_reason")


def _representable(value):
    """Return a float or None, preserving nonzero underflow as a failure."""
    try:
        converted = float(value)
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(converted) or (converted == 0 and value != 0):
        return None
    return converted


def _bound(value, *, lower):
    # Components have bounded domains. Outward rounding keeps a logical
    # enclosure even when the exact bound lies between adjacent floats.
    converted = float(value)
    represented = Fraction(converted)
    if lower and represented > value:
        converted = math.nextafter(converted, -math.inf)
    elif not lower and represented < value:
        converted = math.nextafter(converted, math.inf)
    return converted


def _cell(name, bounds, reason):
    low, high = bounds
    exact = low if low == high else None
    value = None if exact is None else _representable(exact)
    if exact is not None:
        reason = None if value is not None else "numerical_model_range"
    conditions = (*_CONDITIONS, "residue_rscc_squared_minimum") if name == COMPONENTS[0] else _CONDITIONS
    if name in COMPONENTS[3:]:
        conditions = (*conditions, *_PRODUCT_CONDITIONS)
    return {
        "value": value, "lower": _bound(low, lower=True),
        "upper": _bound(high, lower=False), "unit": "dimensionless",
        "status": "unavailable" if value is None else "populated",
        "origin": "proposed", "unavailable_reason": reason,
        "conditional_on": list(conditions), "formula_code": f"structure_{name}_v1",
    }


def _distance(a, b):
    # Exact subtraction avoids loss of small distances between large integer
    # coordinates before the stable Euclidean norm. No squared-float overflow.
    differences = [Fraction(x) - Fraction(y) for x, y in zip(a, b)]
    converted = [_representable(value) for value in differences]
    if any(value is None for value in converted):
        return None
    distance = math.dist(converted, (0, 0, 0))
    if not math.isfinite(distance) or (distance == 0 and any(differences)):
        return None
    return distance


def _local_bounds(inputs):
    panel = inputs["local_members"]
    if not panel:
        return (_ZERO, _ONE), "local_panel_empty"
    if inputs["validation_binding"] != "matching_entry_revision":
        return (_ZERO, _ONE), "validation_not_joined"
    known = [max(_ZERO, Fraction(member["rscc"])) ** 2
             for member in panel if member["rscc"] is not None]
    missing = [member for member in panel if member["rscc"] is None]
    upper = min(known, default=_ONE)
    lower = _ZERO if missing else upper
    return (lower, upper), missing[0]["unavailable_reason"] if missing else None


def _geometry(inputs):
    native, positive, opposing, missing = [], 0, 0, 0
    for index, member in enumerate(inputs["geometry_members"]):
        a, b = member["endpoint_a"], member["endpoint_b"]
        reason = member["unavailable_reason"]
        # Flat order is endpoint_a outer, endpoint_b inner. Missing endpoints
        # have no enumerable pair list; failing pairs retain their null slot.
        distances = [] if a is None or b is None else [_distance(x, y) for x in a for y in b]
        if any(value is None for value in distances):
            reason = "numerical_model_range"
        distance = min(distances) if distances and reason is None else None
        native.append({"member_index": index, "distance_A": distance,
                       "all_pair_distances_A": distances, "unavailable_reason": reason})
        if distance is None:
            missing += 1
        else:
            positive += distance <= member["positive_max_A"]
            opposing += distance >= member["incompatible_min_A"]
    count = len(native)
    if not count:
        return native, (_ZERO, _ONE), (_ZERO, _ONE), (-_ONE, _ONE), "geometry_panel_empty"
    reason = ("numerical_model_range" if any(row["unavailable_reason"] == "numerical_model_range" for row in native)
              else "geometry_inputs_unreported") if missing else None
    support = (Fraction(positive, count), Fraction(positive + missing, count))
    opposition = (Fraction(opposing, count), Fraction(opposing + missing, count))
    # Paired predicates are disjoint, so an unavailable member contributes
    # [-1,1], never the independent difference of two marginal intervals.
    direction = (Fraction(positive - opposing - missing, count),
                 Fraction(positive - opposing + missing, count))
    return native, support, opposition, direction, reason


def _product(a, b):
    corners = [x * y for x in a for y in b]
    return min(corners), max(corners)


def populate_source_geometry(inputs):
    """Populate six proposed components for one explicitly selected model.

    Counts, RSCC transforms and products use exact rational arithmetic. Each
    final point independently reports numerical range failure; representable
    zero products and shared-factor signed cancellation remain available.
    Physical duplicate selections are the source reader's responsibility:
    coincident coordinates alone cannot establish physical identity.
    """
    _validate(inputs)
    local, local_reason = _local_bounds(inputs)
    native, support, opposition, direction, geometry_reason = _geometry(inputs)
    products_reason = local_reason or geometry_reason
    bounds = (local, support, opposition, _product(local, support),
              _product(local, opposition), _product(local, direction))
    reasons = (local_reason, geometry_reason, geometry_reason,
               products_reason, products_reason, products_reason)
    cells = {name: _cell(name, interval, reason)
             for name, interval, reason in zip(COMPONENTS, bounds, reasons)}
    return {"version": VERSION, "inputs": deepcopy(inputs),
            "native_geometry": native, "cells": cells}


__all__ = ["VERSION", "COMPONENTS", "REASONS", "CONDITIONAL_CODES",
           "ExperimentalContractError", "StructureCalculationError",
           "populate_source_geometry"]
