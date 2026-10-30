"""Populate supplied measurements and interpret already decoded input records."""
from __future__ import annotations

from copy import deepcopy

from .domain import ContractError, obj, validate_schema
from .calibrated_signal_contracts import SHEET_VERSION, validate_calibrated_signal_sheet
from .calibrated_signal_contracts import (CalibratedSignalContractError, array, association_schema,
    calibration_schema, calibrated_signal_sheet_schema, copy_json, nullable, sample_schema, species_schema)
from .molecular_sequence_input_contracts import (NAMESPACES, molecular_sequence_received_input_schema,
    validate_molecular_sequence_received_input)


INPUT_READ_VERSION = "calibrated_signal_input_read_v1"
_ROLES = ("samples", "species", "calibrations", "association")
_STATES = ("present", "empty", "missing", "invalid", "unavailable")
_FAILURES = ("input_unavailable", "decode_failed", "document_tag_conflict", "document_shape_invalid",
    "role_missing", "role_invalid", "cross_role_conflict")
_CONTRACT_CODES = ("closed_calibrated_signal_shape_required", "duplicate_identity",
    "unknown_analysis_species_identity", "representation_signal_kind_conflict", "unknown_species_identity")


def populate_calibrated_signal_sheet(*, samples, species, calibrations, association):
    """Copy supplied facts only; numerical association belongs to the calculator."""
    return validate_calibrated_signal_sheet({"version": SHEET_VERSION, "samples": samples,
        "species": species, "calibrations": calibrations, "association": association})


def _role_schemas():
    return {"samples": array(sample_schema()), "species": array(species_schema()),
        "calibrations": array(calibration_schema()), "association": association_schema()}


def _failure_schema():
    return obj({"code": {"enum": list(_FAILURES)}, "role": {"enum": [None, *_ROLES]},
        "source_pointer": {"type": "string", "pattern": r"^(?:$|/(?:[^~]|~[01])*)$"},
        "contract_code": {"enum": [None, *_CONTRACT_CODES]},
        "common_failure": deepcopy(molecular_sequence_received_input_schema()["properties"]["failure"])})


def calibrated_signal_input_read_schema():
    """Private input evidence; these shapes do not grant source permissions."""
    role_schemas = _role_schemas()
    return obj({"version": {"const": INPUT_READ_VERSION}, "state": {"enum": ["complete", "partial", "unavailable"]},
        "received_input": molecular_sequence_received_input_schema(),
        "roles": obj({name: obj({"state": {"enum": list(_STATES)},
            "value": nullable(schema), "source_pointer": {"const": "/" + name},
            "failures": array(_failure_schema())}) for name, schema in role_schemas.items()}),
        "sheet": nullable(calibrated_signal_sheet_schema()), "failures": array(_failure_schema())})


def _failure(code, *, role=None, pointer="", contract_code=None, common=None):
    return {"code": code, "role": role, "source_pointer": pointer,
        "contract_code": contract_code, "common_failure": deepcopy(common)}


def _pointer(path):
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in path)


def _interpret_received_input(received):
    """Interpret supplied JSON only, retaining independent roles on failure."""
    received = validate_molecular_sequence_received_input(received)
    roles = {name: {"state": "unavailable", "value": None, "source_pointer": "/" + name,
        "failures": []} for name in _ROLES}
    result = {"version": INPUT_READ_VERSION, "state": "unavailable", "received_input": received,
        "roles": roles, "sheet": None, "failures": []}
    admitted = received["input"]
    if admitted is None or admitted["byte_verification"] != "verified":
        result["failures"].append(_failure("input_unavailable", common=received["failure"]))
        return result
    content = admitted["content"]
    if content["state"] != "decoded":
        result["failures"].append(_failure("decode_failed", common=received["failure"]))
        return result
    document = content["value"]
    if type(document) is not dict:
        result["failures"].append(_failure("document_shape_invalid"))
        return result
    if admitted["tag_key"] != "version" or document.get("version") != SHEET_VERSION:
        result["failures"].append(_failure("document_tag_conflict", pointer="/version"))
    if set(document) != {"version", *_ROLES}:
        result["failures"].append(_failure("document_shape_invalid"))
    for name, schema in _role_schemas().items():
        role = roles[name]
        if name not in document:
            role["state"] = "missing"
            issue = _failure("role_missing", role=name, pointer="/" + name)
        else:
            try:
                validate_schema(document[name], schema)
            except ContractError as error:
                role["state"] = "invalid"
                issue = _failure("role_invalid", role=name,
                    pointer="/" + name + _pointer(error.detail.get("field_path", [])),
                    contract_code="closed_calibrated_signal_shape_required")
            else:
                role.update(state="empty" if type(document[name]) is list and not document[name] else "present",
                    value=deepcopy(document[name]))
                continue
        role["failures"].append(issue)
        result["failures"].append(deepcopy(issue))
    valid_roles = [name for name, role in roles.items() if role["state"] in {"present", "empty"}]
    if len(valid_roles) == len(_ROLES) and not result["failures"]:
        try:
            result["sheet"] = validate_calibrated_signal_sheet(document)
        except CalibratedSignalContractError as error:
            if error.code not in _CONTRACT_CODES:
                raise
            result["failures"].append(_failure("cross_role_conflict", pointer=error.field,
                contract_code=error.code))
        else:
            result["state"] = "complete"
    if result["state"] != "complete" and valid_roles:
        result["state"] = "partial"
    return result


def read_calibrated_signal_inputs(reference, *, namespace, read_input):
    """Read one whole supplied sheet through the host's authenticated callback.

    ``read_input(reference, namespace)`` is owned by the actual receiving host.
    This pure reader neither creates custody nor validates a supplied claim of
    permission. Role states describe decoded closed shapes; only a non-null
    sheet passed all cross-role rules. File evidence and source assertions stay
    separate, and incomplete source data is never replaced with empty arrays.
    """
    if (type(reference) is not str or not reference or namespace not in NAMESPACES
            or not callable(read_input)):
        raise CalibratedSignalContractError("calibrated_signal_input_selection_invalid", "/selection")
    received = validate_molecular_sequence_received_input(read_input(reference, namespace))
    if received["selection"] != {"reference": reference, "namespace": namespace}:
        raise CalibratedSignalContractError("calibrated_signal_input_selection_conflict", "/selection")
    result = _interpret_received_input(received)
    validate_schema(result, calibrated_signal_input_read_schema())
    return result


def validate_calibrated_signal_input_read(value):
    """Check deterministic input interpretation, not source authentication."""
    result = copy_json(value)
    validate_schema(result, calibrated_signal_input_read_schema())
    expected = _interpret_received_input(result["received_input"])
    if result != expected:
        raise CalibratedSignalContractError("calibrated_signal_input_interpretation_conflict", "/")
    return expected


__all__ = ["populate_calibrated_signal_sheet", "read_calibrated_signal_inputs",
    "calibrated_signal_input_read_schema", "validate_calibrated_signal_input_read"]
