"""Conditional source binding likelihoods; no acquisition or annotation credit.

Native rows are revalidated by the existing descriptive calculator. Supplied
joint natural-log covariance belongs to those exact physical measurements;
reported fit spread and experiment counts never stand in for that covariance.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import json
import math

from scipy.optimize import brentq
from scipy.special import erfcx, log_ndtr

from . import literature_binding_calculations as native
from .literature_experimental_contracts import ExperimentalContractError

VERSION = "binding_model_sheet_v2"
MODEL_VERSION = "known_normal_log_binding_v1"
COMPONENTS = (
    "log_parameter_contrast", "log_contrast_noise_variance", "log_contrast_noise_sd",
    "source_profile_log_ratio", "source_signed_index",
)
FORMULAS = {
    "log_parameter_contrast": "ln(test_parameter)-ln(reference_parameter)",
    "log_contrast_noise_variance": "Crr+Ctt-2*Crt",
    "log_contrast_noise_sd": "sqrt(log_contrast_noise_variance)",
    "source_profile_log_ratio": "sup_mu_test_ge_reference_log_likelihood-sup_mu_test_le_reference_log_likelihood",
    "source_signed_index": "tanh(source_profile_log_ratio/2)",
}
REASONS = tuple(dict.fromkeys((*native.REASONS,
    "binding_sampling_model_unreported", "binding_sampling_model_not_supplied", "known_log_covariance_required",
    "covariance_status_unknown", "binding_censoring_mechanism_unreported",
    "two_censored_observations_unsupported", "numerical_model_range")))
CONDITIONAL_CODES = ("supplied_log_covariance", "known_normal_log_parameters",
                     "threshold_censoring_of_log_estimate")
_MODEL_KEYS = ("version", "parameter_kind", "measurement_order", "measurement_keys",
               "log_covariance", "variance_status", "censoring_model", "log_basis", "origin")
_SHEET_KEYS = ("version", "parameter_kind", "unit", "reference_rows", "test_rows",
               "uncertainty_basis", "minimum_experiment_count", "independent_preparation_count",
               "cells", "annotation_credit")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, names, field):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail("closed_fields_required", field)


def _validated_sheet(binding_sheet):
    _keys(binding_sheet, _SHEET_KEYS, "binding_sheet")
    if binding_sheet["version"] != native.VERSION:
        _fail("unsupported_binding_sheet_version", "binding_sheet.version")
    extraction = {name: deepcopy(binding_sheet[name]) for name in native._EXTRACTION_KEYS
                  if name != "version"}
    extraction["version"] = "binding_parameter_extraction_v1"
    rebuilt = native.populate_binding_contrast(extraction)
    try:
        identical = native._serialized(rebuilt) == native._serialized(binding_sheet)
    except (TypeError, ValueError, OverflowError, RecursionError):
        identical = False
    if not identical:
        _fail("binding_sheet_recalculation_mismatch", "binding_sheet")
    return rebuilt


def _selected(sheet):
    conflicts = native._conflicting_identities(sheet)
    return {arm: native._select(sheet[arm + "_rows"], arm, conflicts)
            for arm in ("reference", "test")}


def _operand_keys(sheet, selected):
    result = {}
    for arm, (row, reason, _conflict) in selected.items():
        if reason is not None:
            result[arm] = None
            continue
        identity = {"parameter_kind": sheet["parameter_kind"],
                    "physical": json.loads(native._physical_identity(row))}
        encoded = json.dumps(identity, sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(",", ":")).encode("utf-8")
        result[arm] = "binding_measurement_" + hashlib.sha256(encoded).hexdigest()
    return result


def binding_model_operand_keys(binding_sheet):
    """Canonical physical owners, or null for unresolved/unreported operands."""
    sheet = _validated_sheet(binding_sheet)
    return _operand_keys(sheet, _selected(sheet))


def _decimal(value):
    return Decimal(value) if type(value) is int else Decimal.from_float(value)


def _validate_model(model, sheet, keys):
    if model is None:
        return None
    _keys(model, _MODEL_KEYS, "model")
    choices = {
        "version": (MODEL_VERSION,), "parameter_kind": (sheet["parameter_kind"],),
        "variance_status": ("known", "estimated", "unknown"),
        "censoring_model": ("none", "threshold_of_log_estimate", "unknown"),
        "log_basis": ("natural_log_nM",), "origin": ("reported", "derived", "synthetic"),
    }
    for field, allowed in choices.items():
        if not isinstance(model[field], str) or model[field] not in allowed:
            _fail("unsupported_binding_model_" + field, "model." + field)
    if model["measurement_order"] != ["reference", "test"]:
        _fail("binding_model_measurement_order_mismatch", "model.measurement_order")
    owners = model["measurement_keys"]
    expected = [keys["reference"], keys["test"]]
    if (not isinstance(owners, list) or len(owners) != 2
            or any(not isinstance(key, str) or not key.strip() for key in owners)
            or owners != expected):
        _fail("binding_model_measurement_owner_mismatch", "model.measurement_keys")
    if owners[0] == owners[1]:
        _fail("binding_covariance_owner_conflict", "model.measurement_keys")
    covariance = model["log_covariance"]
    if (not isinstance(covariance, list) or len(covariance) != 2
            or any(not isinstance(row, list) or len(row) != 2 for row in covariance)):
        _fail("binding_covariance_shape_required", "model.log_covariance")
    for i, row in enumerate(covariance):
        for j, value in enumerate(row):
            try:
                valid = type(value) in (int, float) and math.isfinite(value)
            except OverflowError:
                valid = False
            if not valid:
                _fail("finite_number_required", f"model.log_covariance[{i}][{j}]")
    if covariance[0][1] != covariance[1][0]:
        _fail("symmetric_binding_covariance_required", "model.log_covariance")
    # Exact float-input decimal products distinguish valid tiny/large matrices
    # from singular/indefinite models without jitter or a tolerance window.
    with localcontext() as context:
        context.prec = 2200
        vr, c, vt = map(_decimal, (covariance[0][0], covariance[0][1], covariance[1][1]))
        if vr <= 0 or vt <= 0 or vr * vt - c * c <= 0:
            _fail("positive_definite_binding_covariance_required", "model.log_covariance")
    return deepcopy(model)


def _cell(name, value=None, *, reason=None, relation="eq", conflict=False, conditional=()):
    limit = value is not None and relation != "eq"
    return {
        "value": value, "relation": relation if value is not None else "unreported",
        "unit": "log_parameter_squared" if name == "log_contrast_noise_variance" else "dimensionless",
        "status": ("conflicting" if conflict else "unavailable" if value is None
                   else "reported_limit" if limit else "populated"),
        "formula": FORMULAS[name],
        "origin": "proposed" if name == "source_signed_index" else "derived",
        "unavailable_reason": reason, "bound_kind": "reported_limit_arithmetic" if limit else None,
        "confidence_bound": None, "parameter_identification_bound": None,
        "conditional_on": list(conditional),
    }


class _RangeError(ArithmeticError):
    pass


def _finite_float(value, *, nonzero=False):
    try:
        number = float(value)
    except (OverflowError, ValueError) as error:
        raise _RangeError from error
    if not math.isfinite(number) or nonzero and number == 0:
        raise _RangeError
    return number


def _mills(x):
    """phi(x)/Phi(x) using scaled erfc in the negative normal tail."""
    if not math.isfinite(x):
        raise _RangeError
    if x < 0:
        result = math.sqrt(2 / math.pi) / float(erfcx(-x / math.sqrt(2)))
    else:
        result = math.exp(-0.5 * x * x - 0.5 * math.log(2 * math.pi) - float(log_ndtr(x)))
    if not math.isfinite(result):
        raise _RangeError
    return result


def _censored_profile(e, covariance, censored_index, relation):
    """Global concave equality fit on a standardized, unbounded real mean.

    q follows the sign of the CDF slope. Its derivative is strictly decreasing:
    -q+h*Mills(a+h*q), h>=0. Adaptive bracketing therefore finds the unique
    global maximum without restricting the nuisance parameter to a window.
    """
    d, cindex = 1 - censored_index, censored_index
    s = 1 if relation in ("gt", "ge") else -1
    with localcontext() as context:
        context.prec = 2200
        vd = _decimal(covariance[d][d])
        vc = _decimal(covariance[cindex][cindex])
        c = _decimal(covariance[d][cindex])
        sd = vd.sqrt()
        sc = (vc - c * c / vd).sqrt()
        a = _finite_float(Decimal(s) * _decimal(e if censored_index == 0 else -e) / sc)
        slope = (Decimal(s) * (vd - c) / (sd * sc))
        b = _finite_float(slope, nonzero=slope != 0)
        conditional_sd = _finite_float(sc, nonzero=True)
        detected_sd = _finite_float(sd, nonzero=True)
    h = abs(b)
    if h == 0:
        q = 0.0
    else:
        def derivative(q):
            argument = a + h * q
            value = (0.0 if argument == math.inf else h * _mills(argument)) - q
            if not math.isfinite(value):
                raise _RangeError
            return value
        upper = 1.0
        while derivative(upper) > 0:
            upper *= 2
            if not math.isfinite(upper):
                raise _RangeError
        q = brentq(derivative, 0.0, upper, xtol=math.ulp(0.0),
                   rtol=8 * math.ulp(1.0), maxiter=2048)
    z = math.copysign(q, b) if b else 0.0
    argument = _finite_float(a + h * q)
    log_cdf = float(log_ndtr(argument))
    loss = _finite_float(q * (q / 2) - log_cdf, nonzero=True)
    if loss < 0 or not math.isfinite(log_cdf):
        raise _RangeError
    direction = s if censored_index == 1 else -s
    shift = _finite_float(detected_sd * z, nonzero=z != 0)
    return direction * loss, {
        "boundary_log_likelihood": -loss,
        "boundary_standardized_detected_mean_shift": z,
        "boundary_detected_mean_shift": shift,
        "boundary_log_cdf": log_cdf,
        "conditional_censored_noise_sd": conditional_sd,
    }


def populate_binding_model(binding_sheet, model=None):
    """Populate conditional source components, preserving partial native facts."""
    sheet = _validated_sheet(binding_sheet)
    selected = _selected(sheet)
    keys = _operand_keys(sheet, selected)
    model = _validate_model(model, sheet, keys)
    native_e = sheet["cells"]["log_native_parameter_ratio"]
    base_reason = native_e["unavailable_reason"]
    if base_reason == "two_censored_operands_unsupported":
        base_reason = "two_censored_observations_unsupported"
    conflict = native_e["status"] == "conflicting"
    cells = {name: _cell(name, reason=base_reason) for name in COMPONENTS}
    cells["log_parameter_contrast"] = _cell("log_parameter_contrast", native_e["value"],
        relation=native_e["relation"], reason=base_reason, conflict=conflict)
    diagnostics = {
        "likelihood_case": "none", "boundary_log_likelihood": None,
        "boundary_standardized_detected_mean_shift": None,
        "boundary_detected_mean_shift": None, "boundary_log_cdf": None,
        "conditional_censored_noise_sd": None,
    }
    result = {
        "version": VERSION, "parameter_kind": sheet["parameter_kind"],
        "contrast_meaning": "test_parameter_exceeds_reference", "measurement_keys": keys,
        "model": model, "source_uncertainty_basis": sheet["uncertainty_basis"],
        "minimum_experiment_count": sheet["minimum_experiment_count"],
        "independent_preparation_count": None, "cells": cells,
        "diagnostics": diagnostics, "annotation_credit": None,
    }
    two_censored = base_reason == "two_censored_observations_unsupported"
    if two_censored:
        diagnostics["likelihood_case"] = "two_censored"
    if base_reason and not two_censored:
        for name in COMPONENTS[1:]:
            cells[name] = _cell(name, reason=base_reason, conflict=conflict)
        return result
    reason = ("binding_sampling_model_not_supplied" if model is None else
              "covariance_status_unknown" if model["variance_status"] == "unknown" else None)
    if reason:
        for name in COMPONENTS[1:]:
            cells[name] = _cell(name, reason=(base_reason if two_censored and name in COMPONENTS[3:] else reason))
        return result
    conditions = ["supplied_log_covariance"]
    covariance = model["log_covariance"]
    try:
        with localcontext() as context:
            context.prec = 2200
            vr, c, vt = map(_decimal, (covariance[0][0], covariance[0][1], covariance[1][1]))
            variance_decimal = vr + vt - 2 * c
            variance = _finite_float(variance_decimal, nonzero=True)
            noise_sd = _finite_float(variance_decimal.sqrt(), nonzero=True)
    except ArithmeticError:
        for name in COMPONENTS[1:]:
            cells[name] = _cell(name, reason="numerical_model_range", conditional=conditions)
        return result
    cells["log_contrast_noise_variance"] = _cell("log_contrast_noise_variance", variance, conditional=conditions)
    cells["log_contrast_noise_sd"] = _cell("log_contrast_noise_sd", noise_sd, conditional=conditions)
    relations = [selected[arm][0]["relation"] for arm in ("reference", "test")]
    censored = [index for index, relation in enumerate(relations) if relation != "eq"]
    diagnostics["likelihood_case"] = ("two_censored" if two_censored else
                                      "one_threshold_censored" if censored else "two_points")
    reason = None
    if two_censored:
        reason = "two_censored_observations_unsupported"
    elif model["variance_status"] != "known":
        reason = "known_log_covariance_required"
    elif censored and model["censoring_model"] != "threshold_of_log_estimate":
        reason = "binding_censoring_mechanism_unreported"
    if reason:
        for name in COMPONENTS[3:]:
            cells[name] = _cell(name, reason=reason, conditional=conditions)
        return result
    conditions.append("known_normal_log_parameters")
    if censored:
        conditions.append("threshold_censoring_of_log_estimate")
    try:
        e = native_e["value"]
        if censored:
            score, fitted = _censored_profile(e, covariance, censored[0], relations[censored[0]])
            diagnostics.update(fitted)
        else:
            with localcontext() as context:
                context.prec = 2200
                score = _finite_float(_decimal(e) * abs(_decimal(e)) / (2 * variance_decimal),
                                      nonzero=e != 0)
        cells["source_profile_log_ratio"] = _cell("source_profile_log_ratio", score, conditional=conditions)
        index = math.tanh(score / 2)
        # A rounded endpoint is not exact certainty; nonzero information cannot
        # disappear into an exact zero either. Preserve S if only B is out of range.
        if abs(index) == 1 or index == 0 and score != 0:
            raise _RangeError
        cells["source_signed_index"] = _cell("source_signed_index", index, conditional=conditions)
    except (ArithmeticError, ValueError, RuntimeError):
        for name in COMPONENTS[3:]:
            if cells[name]["value"] is None:
                cells[name] = _cell(name, reason="numerical_model_range", conditional=conditions)
    return result


__all__ = ["VERSION", "MODEL_VERSION", "COMPONENTS", "FORMULAS", "REASONS",
           "CONDITIONAL_CODES", "binding_model_operand_keys", "populate_binding_model"]
