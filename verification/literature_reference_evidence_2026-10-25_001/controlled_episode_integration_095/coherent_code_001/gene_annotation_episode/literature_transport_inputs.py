"""Read selected, source-bound transport operands without scientific inference.

The episode supplies the biological meanings and kinetic-curve interpretations.
Witness checks establish literal custody only. The authoritative quantity callback
supplies an already committed Km operand; this reader never reacquires its paper,
fits a curve, infers covariance from a spread, or calculates response cells.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math

from .domain import REF, obj
from .literature_assay_inputs import (
    SOURCE_KINDS, VARIANCE_STATUSES, _Sources, _fail, _finite, _keys,
    _nullable, _numeric, _text, _witness_schema,
)
from .literature_experimental_contracts import ExperimentalContractError
from .literature_transport_calculations import PRIMITIVE_ORDER


VERSION = "a105_transport_inputs_v1"
CONTEXT_FIELDS = ("molecule", "analyte", "preparation", "experimental_system", "endpoint", "curve")
_LITERAL_ROLES = PRIMITIVE_ORDER[:2]
_OBSERVATION_MODELS = ("michaelis_menten", "unknown")
_ARGS = ("source_ref", "source_kind", "primitives", "km_sheet_ref", "curve_contexts",
         "covariance_source_ref", "variance_status", "observation_model", "model_witnesses")
_QUANTITY_FIELDS = ("sheet_ref", "input_source_ref", "value", "unit", "origin",
                    "reported_uncertainty_kind", "measurement_key", "reported_subject_ref", "analyte_ref")
_COVARIANCE_FIELDS = ("version", "primitive_order", "primitive_measurement_keys",
                      "primitive_units", "covariance", "origin")


def transport_response_population_schema():
    """Closed selected-operation input; numerical operands are not caller values."""
    witness = _witness_schema()
    measurement = obj({"witness": deepcopy(witness), **{field: {"type": "integer", "minimum": 0}
        for field in ("number_start", "number_end", "unit_start", "unit_end")}})
    context = obj({field: deepcopy(witness) if field == "curve" else _nullable(deepcopy(witness))
                   for field in CONTEXT_FIELDS})
    return obj({"source_ref": deepcopy(REF), "source_kind": {"enum": list(SOURCE_KINDS)},
        "primitives": obj({role: _nullable(deepcopy(measurement)) for role in _LITERAL_ROLES}),
        "km_sheet_ref": _nullable(deepcopy(REF)),
        "curve_contexts": obj({role: _nullable(deepcopy(context)) for role in PRIMITIVE_ORDER}),
        "covariance_source_ref": _nullable(deepcopy(REF)),
        "variance_status": {"enum": list(VARIANCE_STATUSES)},
        "observation_model": {"enum": list(_OBSERVATION_MODELS)},
        "model_witnesses": {"type": "array", "items": deepcopy(witness)}})


def _context(value, sources, field):
    if value is None:
        return None, None
    _keys(value, CONTEXT_FIELDS, field)
    if value["curve"] is None:
        _fail("kinetic_curve_witness_required", field + ".curve")
    context = {name: sources.witness(item, field + "." + name) if item is not None else None
               for name, item in value.items()}
    # Representation aliases of the same retained artifact/span have one identity.
    # Different anchors, even with equal literal text, remain distinct contexts.
    canonical = {name: {key: item[key] for key in ("source_ref", "artifact_ref", "start", "end", "quote")}
                 if item is not None else None for name, item in context.items()}
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return context, "transport_curve_" + hashlib.sha256(encoded).hexdigest()


def _quantity(reference, read_quantity):
    if reference is None:
        return None
    _text(reference, "km_sheet_ref")
    quantity = read_quantity(reference)
    _keys(quantity, _QUANTITY_FIELDS, "km_quantity")
    if quantity["sheet_ref"] != reference:
        _fail("quantity_sheet_ref_mismatch", "km_quantity.sheet_ref")
    for name in ("sheet_ref", "input_source_ref", "origin", "reported_uncertainty_kind", "measurement_key"):
        _text(quantity[name], "km_quantity." + name)
    for name in ("reported_subject_ref", "analyte_ref"):
        if quantity[name] is not None:
            _text(quantity[name], "km_quantity." + name)
    _finite(quantity["value"], "km_quantity.value")
    if quantity["unit"] != "uM":
        _fail("quantity_unit_mismatch", "km_quantity.unit")
    return deepcopy(quantity)


def _json_covariance(raw):
    field = "covariance_source_ref"
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail("duplicate_json_key", field)
            result[key] = value
        return result
    def constant(_value):
        _fail("finite_number_required", field)
    # Detect JSON lexical underflow before json.loads can silently make it zero.
    def point(token):
        return _numeric(token, field)
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=constant, parse_float=point)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ExperimentalContractError("covariance_json_required", field) from error


def _covariance(reference, observations, sources):
    if reference is None:
        return None, None
    _text(reference, "covariance_source_ref")
    if any(observations[role] is None for role in PRIMITIVE_ORDER):
        _fail("complete_covariance_owners_required", "covariance_source_ref")
    value = _json_covariance(sources.source(reference, "original")["content"])
    _keys(value, _COVARIANCE_FIELDS, "covariance_source")
    if value["version"] != "a105_transport_covariance_v1":
        _fail("covariance_version_mismatch", "covariance_source.version")
    if value["primitive_order"] != list(PRIMITIVE_ORDER):
        _fail("covariance_primitive_order_mismatch", "covariance_source.primitive_order")
    if value["primitive_measurement_keys"] != [observations[r]["measurement_key"] for r in PRIMITIVE_ORDER]:
        _fail("covariance_measurement_owner_mismatch", "covariance_source.primitive_measurement_keys")
    if value["primitive_units"] != ["uM"] * 3:
        _fail("covariance_primitive_unit_mismatch", "covariance_source.primitive_units")
    if value["origin"] not in ("reported", "derived", "synthetic"):
        _fail("unknown_covariance_origin", "covariance_source.origin")
    matrix = value["covariance"]
    if (not isinstance(matrix, list) or len(matrix) != 3
            or any(not isinstance(row, list) or len(row) != 3 for row in matrix)):
        _fail("three_by_three_covariance_required", "covariance_source.covariance")
    result = []
    for i, row in enumerate(matrix):
        converted = []
        for j, operand in enumerate(row):
            field = f"covariance_source.covariance[{i}][{j}]"
            _finite(operand, field)
            number = float(operand)
            if not math.isfinite(number) or number == 0 and operand != 0:
                _fail("numerical_model_range", field)
            converted.append(number)
        result.append(converted)
    # Symmetry, PSD and physical aliases belong to the response calculator.
    return result, value["origin"]


def read_transport_inputs(arguments, *, read_source, read_quantity):
    """Read authorized retained inputs; preserve unknown scientific relationships.

    ``read_source`` authorizes direct reads and returns exact artifact bytes.
    ``read_quantity`` separately validates an actually received selected apparent
    Km sheet, its source custody and scoped provenance. It returns the committed
    canonical operand and physical key without inference or original-paper reads.
    """
    _keys(arguments, _ARGS, "arguments")
    if arguments["source_kind"] not in SOURCE_KINDS:
        _fail("unknown_source_kind", "source_kind")
    if not callable(read_quantity):
        _fail("quantity_reader_required", "read_quantity")
    sources = _Sources(read_source)
    sources.source(arguments["source_ref"], "original")
    _keys(arguments["primitives"], _LITERAL_ROLES, "primitives")
    observations = {}
    for role in _LITERAL_ROLES:
        item = arguments["primitives"][role]
        observation = sources.measurement(item, "E", "primitives." + role) if item is not None else None
        if observation is not None:
            observation["role"] = role
        observations[role] = observation
    quantity = _quantity(arguments["km_sheet_ref"], read_quantity)
    observations["km"] = quantity
    _keys(arguments["curve_contexts"], PRIMITIVE_ORDER, "curve_contexts")
    contexts, curve_keys = {}, {}
    for role in PRIMITIVE_ORDER:
        contexts[role], curve_keys[role] = _context(arguments["curve_contexts"][role], sources, "curve_contexts." + role)
    if arguments["variance_status"] not in VARIANCE_STATUSES:
        _fail("unsupported_variance_status", "variance_status")
    if arguments["observation_model"] not in _OBSERVATION_MODELS:
        _fail("unsupported_observation_model", "observation_model")
    if not isinstance(arguments["model_witnesses"], list):
        _fail("witness_list_required", "model_witnesses")
    witnesses = [sources.witness(item, f"model_witnesses[{i}]")
                 for i, item in enumerate(arguments["model_witnesses"])]
    if (arguments["variance_status"] != "unknown" or arguments["observation_model"] != "unknown") and not witnesses:
        _fail("model_witness_required", "model_witnesses")
    covariance, covariance_origin = _covariance(arguments["covariance_source_ref"], observations, sources)
    source_refs = list(sources.references)
    if quantity is not None and quantity["sheet_ref"] not in source_refs:
        source_refs.append(quantity["sheet_ref"])
    return {"version": VERSION, "source_ref": arguments["source_ref"], "source_kind": arguments["source_kind"],
        "primitive_order": list(PRIMITIVE_ORDER),
        "values": {role: item["value"] if item is not None else None for role, item in observations.items()},
        "curve_keys": curve_keys,
        "measurement_keys": {role: item["measurement_key"] if item is not None else None
                             for role, item in observations.items()},
        "primitive_observations": deepcopy(observations), "curve_contexts": contexts,
        "covariance": covariance, "covariance_origin": covariance_origin,
        "variance_status": arguments["variance_status"], "observation_model": arguments["observation_model"],
        "model_witnesses": witnesses, "source_refs": source_refs, "km_quantity": deepcopy(quantity)}


__all__ = ["VERSION", "CONTEXT_FIELDS", "transport_response_population_schema", "read_transport_inputs"]
