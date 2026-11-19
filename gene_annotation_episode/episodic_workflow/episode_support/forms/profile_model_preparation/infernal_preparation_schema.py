"""Pure data contracts for Infernal model preparation and inspection.

These helpers define numerical cells and artifact provenance. They do not
execute programs, interpret scientific confidence, or decide episode actions.
Program-specific parsing and calculation live in the three owning modules.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re


SHEET_SCHEMA = "infernal_preparation_sheet_v1"
CALCULATIONS_SCHEMA = "infernal_preparation_calculations_v1"
PROGRAM_MODES = {
    "cmbuild": frozenset({"build", "refine"}),
    "cmcalibrate": frozenset({"calibrate", "forecast", "memory_estimate",
                              "split_commands", "partition_scores", "merge_scores"}),
    "cmconvert": frozenset({"ascii", "binary", "legacy_ascii",
                            "maximum_likelihood_hmm", "filter_hmm"}),
    "cmemit": frozenset({"sample_unaligned", "sample_aligned", "consensus"}),
    "cmfetch": frozenset({"single_key", "key_file", "index"}),
    "cmpress": frozenset({"press"}),
    "cmstat": frozenset({"summary", "scores_at_evalue", "scores_at_pvalue",
                         "evalues_at_score", "evalues_at_ga", "evalues_at_nc",
                         "evalues_at_tc"}),
}
VALUE_STATES = frozenset({"present", "missing", "not_measured", "failed",
                          "truncated", "incompatible", "invalid"})
VALUE_BASES = frozenset({"native_reported", "model_header", "derived",
                         "native_prediction"})
UNITS = frozenset({"count", "nt", "column", "bit", "bit_per_position",
                   "inverse_bit", "fraction", "second", "MB", "Mnt", "byte",
                   "log2_odds", "dimensionless", "index", "expected_count"})
ISSUE_STAGES = frozenset({"format", "extraction", "association", "validation",
                          "calculation"})
RELATIONS = frozenset({"built_from", "calibrated_from", "converted_from",
                       "fetched_from", "indexed_from", "generated_from", "inspected"})
ARTIFACT_FIELDS = frozenset({"role", "format", "artifact_ref", "sha256",
                            "size_bytes", "completeness"})
LOCATOR_FIELDS = frozenset({"artifact_ref", "record_ordinal", "line_start",
                           "line_end", "byte_start", "byte_end"})
VALUE_FIELDS = frozenset({"value", "state", "basis", "unit", "inputs", "native_token"})


def _text(item, field, *, nullable=False):
    if item is None and nullable:
        return
    if type(item) is not str or not item or "\x00" in item:
        raise ValueError("infernal_preparation_invalid_" + field)


def _integer(item, field, *, minimum=0, nullable=False):
    if item is None and nullable:
        return
    if type(item) is not int or item < minimum:
        raise ValueError("infernal_preparation_invalid_" + field)


def _fields(item, fields, name):
    if type(item) is not dict or set(item) != set(fields):
        raise ValueError("infernal_preparation_invalid_" + name + "_fields")


def require_finite_json(item):
    """Accept JSON data only, without coercing keys, tuples or NaN/Infinity."""
    if type(item) is dict:
        if any(type(key) is not str for key in item):
            raise ValueError("infernal_preparation_json_key")
        for child in item.values():
            require_finite_json(child)
    elif type(item) is list:
        for child in item:
            require_finite_json(child)
    elif type(item) is float:
        if not math.isfinite(item):
            raise ValueError("infernal_preparation_nonfinite_number")
    elif item is not None and type(item) not in (str, int, bool):
        raise ValueError("infernal_preparation_non_json_value")


def validate_operation(operation):
    _fields(operation, {"program", "mode", "engine_version", "settings"}, "operation")
    program = operation["program"]
    if type(program) is not str or program not in PROGRAM_MODES:
        raise ValueError("infernal_preparation_unsupported_program")
    if type(operation["mode"]) is not str or operation["mode"] not in PROGRAM_MODES[program]:
        raise ValueError("infernal_preparation_unsupported_mode")
    _text(operation["engine_version"], "engine_version", nullable=True)
    if type(operation["settings"]) is not dict:
        raise ValueError("infernal_preparation_settings_object_required")
    require_finite_json(operation["settings"])
    for flag, setting in operation["settings"].items():
        # 'key' is cmfetch's explicit positional selector, not a fabricated file.
        if not flag.startswith("-") and not (program == "cmfetch" and flag == "key"):
            raise ValueError("infernal_preparation_setting_not_native_argument")
        if type(setting) not in (str, bool, int, float):
            raise ValueError("infernal_preparation_setting_not_scalar")


def validate_artifact(artifact):
    _fields(artifact, ARTIFACT_FIELDS, "artifact")
    for name in ("role", "format", "artifact_ref"):
        _text(artifact[name], name)
    if type(artifact["sha256"]) is not str or re.fullmatch(r"[a-f0-9]{64}", artifact["sha256"]) is None:
        raise ValueError("infernal_preparation_invalid_sha256")
    _integer(artifact["size_bytes"], "size_bytes")
    if artifact["completeness"] not in {"complete", "partial", "unknown"}:
        raise ValueError("infernal_preparation_invalid_completeness")


def locator(artifact_ref, record_ordinal=None, *, line_start=None, line_end=None,
            byte_start=None, byte_end=None):
    result = {"artifact_ref": artifact_ref, "record_ordinal": record_ordinal,
              "line_start": line_start, "line_end": line_end,
              "byte_start": byte_start, "byte_end": byte_end}
    validate_locator(result)
    return result


def validate_locator(location):
    _fields(location, LOCATOR_FIELDS, "locator")
    _text(location["artifact_ref"], "artifact_ref")
    _integer(location["record_ordinal"], "record_ordinal", nullable=True)
    for start_name, end_name, minimum in (("line_start", "line_end", 1),
                                          ("byte_start", "byte_end", 0)):
        start, end = location[start_name], location[end_name]
        _integer(start, start_name, minimum=minimum, nullable=True)
        _integer(end, end_name, minimum=minimum, nullable=True)
        if (start is None) != (end is None) or (start is not None and end < start):
            raise ValueError("infernal_preparation_invalid_locator_interval")


def field_input(location, field):
    validate_locator(location)
    _text(field, "input_field")
    return {"locator": deepcopy(location), "field": field}


def _validate_field_inputs(inputs):
    if type(inputs) is not list:
        raise ValueError("infernal_preparation_field_inputs_list_required")
    for item in inputs:
        _fields(item, {"locator", "field"}, "field_input")
        validate_locator(item["locator"])
        _text(item["field"], "input_field")


def value(number=None, *, state=None, basis="native_reported", unit="count",
          inputs=(), native_token=None):
    result = {"value": number, "state": ("missing" if number is None else "present") if state is None else state,
              "basis": basis, "unit": unit, "inputs": deepcopy(list(inputs)),
              "native_token": native_token}
    validate_value(result)
    return result


def validate_value(cell):
    _fields(cell, VALUE_FIELDS, "value")
    if (type(cell["state"]) is not str or type(cell["basis"]) is not str or type(cell["unit"]) is not str
            or cell["state"] not in VALUE_STATES or cell["basis"] not in VALUE_BASES or cell["unit"] not in UNITS):
        raise ValueError("infernal_preparation_invalid_value_qualification")
    number = cell["value"]
    if cell["state"] == "present":
        if type(number) not in (int, float) or (type(number) is float and not math.isfinite(number)):
            raise ValueError("infernal_preparation_present_value_not_finite_number")
    elif number is not None:
        raise ValueError("infernal_preparation_unavailable_value_has_number")
    if cell["native_token"] is not None and type(cell["native_token"]) is not str:
        raise ValueError("infernal_preparation_invalid_native_token")
    _validate_field_inputs(cell["inputs"])


def issue(code, *, stage="extraction", severity="error", artifact_ref=None,
          record_key=None, field=None):
    _text(code, "issue_code")
    if stage not in ISSUE_STAGES or severity not in {"error", "warning", "information"}:
        raise ValueError("infernal_preparation_invalid_issue_qualification")
    for name, item in (("artifact_ref", artifact_ref), ("record_key", record_key), ("field", field)):
        _text(item, name, nullable=True)
    return {"stage": stage, "code": code, "severity": severity,
            "artifact_ref": artifact_ref, "record_key": record_key, "field": field}


def record_key(artifact_ref, kind, ordinal):
    _text(artifact_ref, "artifact_ref")
    _text(kind, "record_kind")
    _integer(ordinal, "record_ordinal")
    return f"{artifact_ref}#{kind}/{ordinal}"


def new_sheet(operation, artifacts):
    validate_operation(operation)
    retained = deepcopy(list(artifacts))
    for artifact in retained:
        validate_artifact(artifact)
    return {"schema": SHEET_SCHEMA, "operation": deepcopy(operation),
            "artifacts": retained, "input_records": [], "output_records": [],
            "native_rows": [], "associations": [], "issues": []}


def new_calculations(operation, parameters):
    validate_operation(operation)
    if type(parameters) is not dict:
        raise ValueError("infernal_preparation_parameters_object_required")
    require_finite_json(parameters)
    return {"schema": CALCULATIONS_SCHEMA, "operation": deepcopy(operation),
            "parameters": deepcopy(parameters), "rows": [], "issues": []}


def check(name, outcome, inputs=()):
    _text(name, "check_name")
    if outcome not in {"pass", "fail", "unknown", "not_applicable"}:
        raise ValueError("infernal_preparation_invalid_check_outcome")
    retained = deepcopy(list(inputs))
    _validate_field_inputs(retained)
    return {"check": name, "outcome": outcome, "inputs": retained}


def validate_common_sheet(sheet):
    """Validate envelope/cells, not a program's grammar or biological meaning."""
    _fields(sheet, {"schema", "operation", "artifacts", "input_records", "output_records",
                    "native_rows", "associations", "issues"}, "sheet")
    if sheet["schema"] != SHEET_SCHEMA:
        raise ValueError("infernal_preparation_sheet_schema_mismatch")
    validate_operation(sheet["operation"])
    for name in ("artifacts", "input_records", "output_records", "native_rows", "associations", "issues"):
        if type(sheet[name]) is not list:
            raise ValueError("infernal_preparation_sheet_list_required")
    for artifact in sheet["artifacts"]:
        validate_artifact(artifact)
    refs = [a["artifact_ref"] for a in sheet["artifacts"]]
    if len(refs) != len(set(refs)):
        raise ValueError("infernal_preparation_duplicate_artifact_reference")
    require_finite_json(sheet)

    def walk(item):
        if type(item) is dict:
            if {"state", "basis", "unit", "native_token", "inputs"}.issubset(item):
                validate_value(item)
            if set(item) == LOCATOR_FIELDS:
                validate_locator(item)
                if item["artifact_ref"] not in refs:
                    raise ValueError("infernal_preparation_locator_artifact_unknown")
            for child in item.values():
                walk(child)
        elif type(item) is list:
            for child in item:
                walk(child)

    walk(sheet)
    for relation in sheet["associations"]:
        _fields(relation, {"relation", "input_keys", "output_keys", "status"}, "association")
        if relation["relation"] not in RELATIONS or relation["status"] not in {"validated", "unresolved", "conflicting"}:
            raise ValueError("infernal_preparation_invalid_association")
        for name in ("input_keys", "output_keys"):
            if type(relation[name]) is not list:
                raise ValueError("infernal_preparation_association_keys_list_required")
            for key in relation[name]:
                _text(key, "association_key")
    # Independent of JSON serializer coercions; keep this check in the public path.
    json.dumps(sheet, allow_nan=False)
