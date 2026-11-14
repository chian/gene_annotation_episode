"""Read an explicit retained binding observation model without inferring one.

The caller supplies already acquired bytes and the actual selected measurement
owners. This parser checks their declared representation and relationships;
source receipt, scope and scientific interpretation remain the caller's work.
Positive definiteness and numerical model calculations belong to the calculator.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math

from .literature_experimental_contracts import ExperimentalContractError


MODEL_VERSION = "known_normal_log_binding_v1"
_KINDS = ("ic50", "reported_hill_kd")
_ORDER = ("reference", "test")
_FIELDS = ("version", "parameter_kind", "measurement_order", "measurement_keys",
           "log_covariance", "variance_status", "censoring_model", "log_basis", "origin")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, names, field):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail("closed_fields_required", field)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_source_token_required", field)


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_json_key", "source.content")
        result[key] = value
    return result


def _json_constant(_token):
    _fail("nonfinite_json_constant", "source.content")


def _json_float(token):
    value = float(token)
    if not math.isfinite(value):
        _fail("finite_number_required", "source.content")
    # Retaining a mathematically nonzero covariance as exact zero would change
    # the declared model, even before the calculator tests positive definiteness.
    if value == 0 and any(c in "123456789" for c in token.lower().split("e", 1)[0]):
        _fail("numerical_model_range", "source.content")
    return value


def _finite(value, field):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)


def read_binding_model(source, *, parameter_kind, measurement_keys):
    """Return a detached normalized model and its exact retained source refs.

    ``measurement_keys`` is the closed mapping ``{reference: key, test: key}``
    obtained from the binding sheet's selected physical operands. Missing or
    ambiguous owners cannot authorize a covariance. The model source JSON uses
    the corresponding ordered two-element list. An absent source is handled by
    the caller with ``model=None``; a supplied source must contain a model object.
    No values, units, covariance or censoring mechanism are inferred or repaired.
    """
    _keys(source, ("source_ref", "artifact_ref", "content"), "source")
    for field in ("source_ref", "artifact_ref"):
        _text(source[field], "source." + field)
    if type(source["content"]) is not bytes:
        _fail("source_bytes_required", "source.content")
    if parameter_kind not in _KINDS:
        _fail("unsupported_binding_parameter_kind", "parameter_kind")
    _keys(measurement_keys, _ORDER, "measurement_keys")
    for arm in _ORDER:
        if measurement_keys[arm] is None:
            _fail("complete_covariance_owners_required", "measurement_keys." + arm)
        _text(measurement_keys[arm], "measurement_keys." + arm)
    try:
        model = json.loads(source["content"].decode("utf-8"),
                           object_pairs_hook=_json_object, parse_constant=_json_constant,
                           parse_float=_json_float)
    except ExperimentalContractError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise ExperimentalContractError("malformed_binding_model_source", "source.content") from error
    _keys(model, _FIELDS, "model")
    if model["version"] != MODEL_VERSION:
        _fail("unsupported_binding_model_version", "model.version")
    if model["parameter_kind"] not in _KINDS:
        _fail("unsupported_binding_parameter_kind", "model.parameter_kind")
    if model["parameter_kind"] != parameter_kind:
        _fail("binding_parameter_kind_mismatch", "model.parameter_kind")
    if model["measurement_order"] != list(_ORDER):
        _fail("binding_model_measurement_order_mismatch", "model.measurement_order")
    if model["measurement_keys"] != [measurement_keys[arm] for arm in _ORDER]:
        _fail("binding_model_measurement_owner_mismatch", "model.measurement_keys")
    if model["log_basis"] != "natural_log_nM":
        _fail("unsupported_binding_log_basis", "model.log_basis")
    if model["variance_status"] not in ("known", "estimated", "unknown"):
        _fail("unsupported_binding_variance_status", "model.variance_status")
    if model["censoring_model"] not in ("none", "threshold_of_log_estimate", "unknown"):
        _fail("unsupported_binding_censoring_model", "model.censoring_model")
    if model["origin"] not in ("reported", "derived", "synthetic"):
        _fail("unknown_binding_model_origin", "model.origin")
    matrix = model["log_covariance"]
    if (not isinstance(matrix, list) or len(matrix) != 2
            or any(not isinstance(row, list) or len(row) != 2 for row in matrix)):
        _fail("two_by_two_covariance_required", "model.log_covariance")
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            _finite(value, f"model.log_covariance[{i}][{j}]")
    if matrix[0][1] != matrix[1][0]:
        _fail("asymmetric_log_covariance", "model.log_covariance")
    if (measurement_keys["reference"] == measurement_keys["test"]
            and (matrix[0] != matrix[1] or any(row[0] != row[1] for row in matrix))):
        _fail("shared_measurement_covariance_mismatch", "model.log_covariance")
    return {"model": deepcopy(model),
            "source": {"source_ref": source["source_ref"], "artifact_ref": source["artifact_ref"]}}


__all__ = ["MODEL_VERSION", "read_binding_model"]
