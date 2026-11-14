"""Read retained A106 source measurements and literal experimental context.

The selected operation supplies source references and witnessed interpretations,
never numerical measurements. The finite JSON dataset is an explicit retained
data boundary, not a gel reader or a calibration procedure. Literal custody does
not establish the scientific truth of the selected experimental meanings.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .domain import REF, obj
from .literature_assay_inputs import (
    SOURCE_KINDS, _Sources, _fail, _finite, _keys, _nullable, _numeric,
    _text, _witness_schema,
)
from .literature_experimental_contracts import ExperimentalContractError


VERSION = "a106_perturbation_inputs_v1"
DATA_VERSION = "a106_source_measurements_v1"
PRIMITIVE_ORDER = ("W", "K", "R", "A_reference", "A_restored", "B_pert", "B_rest")
LITERAL_FIELDS = ("molecule", "recipient", "donor", "experiment", "reference_arm",
                  "perturbed_arm", "restored_arm", "partner", "endpoint",
                  "normalization", "condition", "intended_change")
DESIGNS = ("native_deletion_restoration", "selective_perturbation_restoration",
           "cas_free_reconstitution", "variant_replacement", "other_explicit",
           "unknown", "conflicting")
MEASUREMENT_STATUSES = ("validated_ratio_scale", "qualitative_only", "unknown", "conflicting")
ENDPOINT_SCOPES = ("yes", "no", "unknown", "conflicting")
AMOUNT_ROLES = ("nuisance", "intended_change", "unknown")
ENDPOINT_UNITS = ("events_per_100000_cells", "fraction", "CFU_per_mL", "minutes", "per_min")
EXPOSURE_UNITS = ("molecules_per_cell", "normalized_signal", "fraction", "mg_per_mL")
_INTERPRETATIONS = {"design": DESIGNS, "measurement_status": MEASUREMENT_STATUSES,
                    "same_endpoint_scope": ENDPOINT_SCOPES, "amount_role": AMOUNT_ROLES}
_ARGS = ("source_ref", "data_source_ref", "source_kind", "literals", "design",
         "measurement_status", "same_endpoint_scope", "amount_role", "orientation",
         "interpretation_witnesses")
_DATA_FIELDS = ("version", "endpoint_unit", "exposure_unit", "origin",
                "uncertainty_basis", "measurements")


def perturbation_population_schema():
    """Closed operation arguments; point operands occur only in retained bytes."""
    witness = _witness_schema()
    return obj({
        "source_ref": deepcopy(REF), "data_source_ref": _nullable(deepcopy(REF)),
        "source_kind": {"enum": list(SOURCE_KINDS)},
        "literals": obj({field: _nullable(deepcopy(witness)) for field in LITERAL_FIELDS}),
        **{field: {"enum": list(allowed)} for field, allowed in _INTERPRETATIONS.items()},
        "orientation": _nullable({"type": "integer", "enum": [-1, 1]}),
        "interpretation_witnesses": {"type": "array", "items": deepcopy(witness)},
    })


def _json_measurements(raw):
    field = "data_source_ref"
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail("duplicate_json_key", field)
            result[key] = value
        return result
    def constant(_token):
        _fail("finite_number_required", field)
    def integer(token):
        value = int(token)
        _finite(value, field)
        return value
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=constant, parse_int=integer,
                          parse_float=lambda token: _numeric(token, field))
    except ExperimentalContractError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise ExperimentalContractError("malformed_perturbation_measurements_source", field) from error


def _measurement_key(reference, artifact_ref, measurement_id):
    owner = {"source_ref": reference, "artifact_ref": artifact_ref,
             "measurement_id": measurement_id}
    encoded = json.dumps(owner, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return "literature_measurement_" + hashlib.sha256(encoded).hexdigest()


def _measurements(reference, sources, status):
    observations = dict.fromkeys(PRIMITIVE_ORDER)
    if reference is None:
        # These are absent dimensional declarations, not assumed measured units.
        return observations, "unreported", "unreported", None, "unreported"
    source = sources.source(reference, "original")
    data = _json_measurements(source["content"])
    _keys(data, _DATA_FIELDS, "data_source")
    if data["version"] != DATA_VERSION:
        _fail("unsupported_perturbation_measurements_version", "data_source.version")
    if data["endpoint_unit"] not in ENDPOINT_UNITS:
        _fail("unsupported_endpoint_unit", "data_source.endpoint_unit")
    if data["exposure_unit"] not in EXPOSURE_UNITS:
        _fail("unsupported_exposure_unit", "data_source.exposure_unit")
    if data["origin"] not in ("reported", "graph_derived", "synthetic"):
        _fail("unknown_measurement_origin", "data_source.origin")
    if data["uncertainty_basis"] != "unreported":
        _fail("unsupported_uncertainty_basis", "data_source.uncertainty_basis")
    _keys(data["measurements"], PRIMITIVE_ORDER, "data_source.measurements")
    owners = {}
    for role in PRIMITIVE_ORDER:
        field = "data_source.measurements." + role
        entry = data["measurements"][role]
        _keys(entry, ("value", "measurement_id"), field)
        value, measurement_id = entry["value"], entry["measurement_id"]
        if measurement_id is not None:
            _text(measurement_id, field + ".measurement_id")
        unit = data["exposure_unit"] if role in ("A_reference", "A_restored") else data["endpoint_unit"]
        key = None
        if value is not None:
            _finite(value, field + ".value")
            if value < 0:
                _fail("nonnegative_measurement_required", field + ".value")
            if measurement_id is None:
                _fail("known_measurement_id_required", field + ".measurement_id")
            if status == "qualitative_only" and role in ("W", "K", "R"):
                _fail("qualitative_endpoint_has_no_numeric_values", field + ".value")
            key = _measurement_key(reference, source["artifact_ref"], measurement_id)
            if key in owners and owners[key] != (value, unit):
                _fail("shared_measurement_value_or_unit_mismatch", field)
            owners[key] = (value, unit)
        observations[role] = {
            "role": role, "value": value, "unit": unit,
            "raw_entry": deepcopy(entry), "source_ref": reference,
            "artifact_ref": source["artifact_ref"], "measurement_key": key,
        }
    return observations, data["endpoint_unit"], data["exposure_unit"], data["origin"], data["uncertainty_basis"]


def read_perturbation_inputs(arguments, *, read_source):
    """Validate source custody and preserve source meanings without arithmetic.

    ``read_source(ref, representation)`` authorizes scope/receipt and returns
    ``{artifact_ref, content}`` with exact bytes. Callback failures propagate;
    this reader never reacquires, calibrates, infers independence or repairs data.
    """
    _keys(arguments, _ARGS, "arguments")
    if arguments["source_kind"] not in SOURCE_KINDS:
        _fail("unknown_source_kind", "source_kind")
    for field, allowed in _INTERPRETATIONS.items():
        if arguments[field] not in allowed:
            _fail("unknown_interpretation_value", field)
    orientation = arguments["orientation"]
    if orientation is not None and (type(orientation) is not int or orientation not in (-1, 1)):
        _fail("orientation_integer_sign_required", "orientation")
    sources = _Sources(read_source)
    sources.source(arguments["source_ref"], "original")
    _keys(arguments["literals"], LITERAL_FIELDS, "literals")
    literals = {}
    for field in LITERAL_FIELDS:
        item = arguments["literals"][field]
        witness = sources.witness(item, "literals." + field) if item is not None else None
        literals[field] = {"value": witness["quote"], "witness": witness} if witness else None
    if not isinstance(arguments["interpretation_witnesses"], list):
        _fail("witness_list_required", "interpretation_witnesses")
    witnesses = [sources.witness(item, f"interpretation_witnesses[{i}]")
                 for i, item in enumerate(arguments["interpretation_witnesses"])]
    if (orientation is not None or any(arguments[field] != "unknown" for field in _INTERPRETATIONS)) and not witnesses:
        _fail("interpretation_witness_required", "interpretation_witnesses")
    observations, endpoint_unit, exposure_unit, origin, uncertainty = _measurements(
        arguments["data_source_ref"], sources, arguments["measurement_status"])
    return {
        "version": VERSION, "source_ref": arguments["source_ref"],
        "source_kind": arguments["source_kind"], "data_source_ref": arguments["data_source_ref"],
        "literals": literals, **{field: arguments[field] for field in _INTERPRETATIONS},
        "orientation": orientation, "interpretation_witnesses": witnesses,
        "primitive_order": list(PRIMITIVE_ORDER),
        "values": {role: item["value"] if item is not None else None for role, item in observations.items()},
        "measurement_keys": {role: item["measurement_key"] if item is not None else None
                             for role, item in observations.items()},
        "primitive_observations": observations, "endpoint_unit": endpoint_unit,
        "exposure_unit": exposure_unit, "data_origin": origin,
        "uncertainty_basis": uncertainty, "source_refs": list(sources.references),
    }


__all__ = ["VERSION", "DATA_VERSION", "PRIMITIVE_ORDER", "LITERAL_FIELDS", "SOURCE_KINDS", "DESIGNS",
           "MEASUREMENT_STATUSES", "ENDPOINT_SCOPES", "AMOUNT_ROLES", "ENDPOINT_UNITS",
           "EXPOSURE_UNITS", "perturbation_population_schema", "read_perturbation_inputs"]
