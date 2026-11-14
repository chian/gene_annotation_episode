"""Pure composition of the HMMER preparation sheets and calculators (261/D1).

The caller owns acquisition, custody, native execution and publication. This
port consumes supplied bytes and explicit original declarations only. Complete
component sheets retain partial native data; an issue is not a universal failure
flag. Recalculation consumes saved numerical sheets without invoking any reader.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import math
import re

from . import hmmer_alignment_preparation_data as alignment_data
from . import hmmer_alignment_preparation_calculations as alignment_calculations
from . import hmmer_artifact_data as artifact_data
from . import hmmer_artifact_calculations as artifact_calculations
from . import hmmer_emission_data as emission_data
from . import hmmer_emission_calculations as emission_calculations
from . import hmmer_fm_data as fm_data
from . import hmmer_fm_calculations as fm_calculations
from . import hmmer_model_data as model_data
from . import hmmer_simulation_data as simulation_data
from . import hmmer_simulation_calculations as simulation_calculations
from . import hmmer_statistics_data as statistics_data
from . import hmmer_statistics_calculations as statistics_calculations
from .native_hmmer_preparation_contracts import (
    FORMAT_ARGUMENTS, PROGRAM_MODES, operand_contract, output_contract,
)


VERSION = "native_hmmer_preparation_grading_v1"
GRADING_FIELDS = frozenset({"version", "operation", "formats", "metadata", "native_abi",
                            "requested_parameters", "sheet", "calculations"})
_ABI_FIELDS = frozenset({"byte_order", "float_format", "bytes_per_float", "uint8_bytes",
    "uint16_bytes", "uint32_bytes", "uint64_bytes", "int32_bytes", "c_int_bytes",
    "c_long_bytes", "c_float_bytes"})
_ARTIFACT_PROGRAMS = frozenset({"hmmconvert", "hmmfetch", "hmmpress"})
_ALIGNMENT_PROGRAMS = frozenset({"hmmbuild", "alimask"})
_FM_PROGRAMS = frozenset({"makehmmerdb", "hmmerfm-exactmatch"})
_SCHEMAS = {
    **dict.fromkeys(_ARTIFACT_PROGRAMS, "hmmer_artifact_sheet_v1"),
    **dict.fromkeys(_ALIGNMENT_PROGRAMS, "hmmer_alignment_preparation_sheet_v1"),
    **dict.fromkeys(_FM_PROGRAMS, "hmmer_fm_sheet_v1"),
    "hmmemit": "hmmer_emission_sheet_v1", "hmmsim": "hmmer_simulation_sheet_v1",
    "hmmstat": "hmmer_statistics_sheet_v1",
}
_COMMON_SHEET_FIELDS = frozenset({"schema", "operation", "artifact_occurrences",
                                  "native_rows", "associations", "issues"})
_SHEET_FIELDS = {
    "hmmer_artifact_sheet_v1": _COMMON_SHEET_FIELDS | {
        "model_extractions", "input_records", "output_records", "artifact_bindings"},
    "hmmer_alignment_preparation_sheet_v1": _COMMON_SHEET_FIELDS | {
        "input_records", "output_records", "model_extraction"},
    "hmmer_emission_sheet_v1": _COMMON_SHEET_FIELDS | {"model_extraction", "output_records"},
    "hmmer_simulation_sheet_v1": _COMMON_SHEET_FIELDS | {"input_records", "native_abi"},
    "hmmer_statistics_sheet_v1": _COMMON_SHEET_FIELDS | {"model_extraction", "summary"},
    "hmmer_fm_sheet_v1": _COMMON_SHEET_FIELDS | {
        "producer_contract", "source_binding", "database", "input_records"},
}
_PARAMETER_FIELDS = {
    "hmmer_artifact_sheet_v1": {"probability_tolerance", "expected_revision"},
    "hmmer_alignment_preparation_sheet_v1": {
        "background", "probability_tolerance", "summary_rounding_tolerance"},
    "hmmer_emission_sheet_v1": {"consensus_thresholds", "probability_rounding_tolerance"},
    "hmmer_simulation_sheet_v1": {"fixed_lambda", "fit_tolerance", "solver_iteration_limit",
        "rounding_tolerance", "tail_masses", "filter_criterion"},
    "hmmer_statistics_sheet_v1": {
        "background", "length_probability", "probability_tolerance", "summary_rounding_tolerance"},
    "hmmer_fm_sheet_v1": {"alphabet_normalization", "coordinate_policy", "exhaustive_literal_check"},
}


class ContractError(ValueError):
    """A malformed dispatch handoff, distinct from a component's native issues."""


def _error(code, field):
    raise ContractError("native_hmmer_preparation_grading_" + code + ":" + field)


def _json_copy(value, field):
    """Require finite JSON without silently coercing tuples or object keys."""
    def validate(item):
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                validate(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                validate(child)
            return
        _error("finite_json_required", field)
    try:
        validate(value)
        return deepcopy(value)
    except RecursionError as exc:
        raise ContractError("native_hmmer_preparation_grading_finite_json_required:" + field) from exc


def _object(value, field, fields=None):
    if type(value) is not dict or fields is not None and set(value) != fields:
        _error("object_fields", field)


def _text(value, field):
    if type(value) is not str or not value:
        _error("text_required", field)


def _digest(value, field):
    if type(value) is not str or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        _error("digest_invalid", field)


def _operation(value):
    operation = _json_copy(value, "operation")
    _object(operation, "operation", {"program", "mode", "engine_version", "settings"})
    program, mode = operation["program"], operation["mode"]
    if (type(program) is not str or program not in PROGRAM_MODES or
            type(mode) is not str or mode not in PROGRAM_MODES[program]):
        _error("program_mode_invalid", "operation")
    if operation["engine_version"] != "3.4":
        _error("engine_version_invalid", "operation.engine_version")
    _object(operation["settings"], "operation.settings")
    return operation


def _parameters(parameters, schema):
    result = _json_copy(parameters, "parameters")
    _object(result, "parameters")
    if set(result) - _PARAMETER_FIELDS[schema]:
        _error("parameters_unknown", "parameters")
    return result


def _abi(value):
    result = _json_copy(value, "native_abi")
    if result is None:
        return None
    _object(result, "native_abi", _ABI_FIELDS)
    if (result["byte_order"] not in ("little", "big") or
            result["float_format"] not in ("ieee754_binary64", "unsupported") or
            any(type(result[key]) is not int or result[key] <= 0
                for key in _ABI_FIELDS - {"byte_order", "float_format"}) or
            result["float_format"] == "ieee754_binary64" and result["bytes_per_float"] != 8):
        _error("native_abi_invalid", "native_abi")
    return result


def _metadata(value, program):
    result = _json_copy(value, "metadata")
    _object(result, "metadata")
    allowed = ({"artifact_bindings"} if program in _ARTIFACT_PROGRAMS else
               {"producer_contract", "source_binding"} if program in _FM_PROGRAMS else set())
    if set(result) - allowed:
        _error("metadata_unrelated", "metadata")
    bindings = result.get("artifact_bindings")
    if bindings is not None:
        if type(bindings) is not list:
            _error("metadata_invalid", "metadata.artifact_bindings")
        for binding in bindings:
            _object(binding, "metadata.artifact_bindings", artifact_data.BINDING_FIELDS)
            for field, item in binding.items():
                _text(item, "metadata.artifact_bindings." + field)
            _digest(binding["source_sha256"], "metadata.artifact_bindings.source_sha256")
    producer = result.get("producer_contract")
    if producer is not None:
        _object(producer, "metadata.producer_contract", fm_data.PRODUCER_FIELDS)
        for field in ("format", "engine_version", "byte_order"):
            _text(producer[field], "metadata.producer_contract." + field)
        for field in fm_data.PRODUCER_FIELDS - {"format", "engine_version", "byte_order"}:
            if type(producer[field]) is not int or producer[field] <= 0:
                _error("metadata_invalid", "metadata.producer_contract." + field)
        # Unsupported recorded versions/representations remain F1 diagnostics.
    source = result.get("source_binding")
    if source is not None:
        _object(source, "metadata.source_binding", fm_data.SOURCE_BINDING_FIELDS)
        for field in ("database_occurrence_id", "producer_attempt_id"):
            _text(source[field], "metadata.source_binding." + field)
        ids, hashes = source["source_occurrence_ids"], source["source_sha256s"]
        if type(ids) is not list or type(hashes) is not list or not ids or len(ids) != len(hashes):
            _error("metadata_invalid", "metadata.source_binding.population")
        for oid, digest in zip(ids, hashes):
            _text(oid, "metadata.source_binding.source_occurrence_ids")
            _digest(digest, "metadata.source_binding.source_sha256s")
    return result


def _payloads(inputs, outputs, formats, operation):
    declared = _json_copy(formats, "formats")
    _object(declared, "formats")
    seen, copied = set(), []
    program, mode = operation["program"], operation["mode"]
    for direction, mapping, contract in (("input", inputs, operand_contract),
                                          ("output", outputs, output_contract)):
        _object(mapping, direction + "s")
        required, optional = contract(program, mode)
        allowed, result = {**required, **optional}, {}
        for role, items in mapping.items():
            if type(role) is not str or role not in allowed or type(items) is not list:
                _error("payload_role_invalid", direction + "s")
            result[role], previous = [], -1
            for payload in items:
                field = direction + "." + role
                _object(payload, field, {"occurrence", "content"})
                content = payload["content"]
                if type(content) is not bytes:
                    _error("content_bytes_required", field)
                occurrence = _json_copy(payload["occurrence"], field + ".occurrence")
                if not model_data._occurrence_valid(occurrence):
                    _error("occurrence_invalid", field)
                oid = occurrence["occurrence_id"]
                if occurrence["direction"] != direction or occurrence["role"] != role:
                    _error("occurrence_role_mismatch", field)
                if oid in seen:
                    _error("occurrence_id_duplicate", oid)
                if occurrence["ordinal"] <= previous:
                    _error("occurrence_order_invalid", field)
                previous = occurrence["ordinal"]
                if len(content) != occurrence["size_bytes"]:
                    _error("occurrence_size_mismatch", oid)
                if hashlib.sha256(content).hexdigest() != occurrence["sha256"].lower():
                    _error("occurrence_digest_mismatch", oid)
                fmt = declared.get(oid)
                if type(fmt) is not str or fmt not in allowed[role]:
                    _error("format_role_mismatch", oid)
                # These readers consume original native format flags. Reject a
                # contrary/missing declaration rather than enable autodetection.
                flag = ("--informat" if direction == "input" and role in {"alignment", "sequences"}
                        else "--outformat" if direction == "output" and role == "masked_alignment" else None)
                if flag is not None and operation["settings"].get(flag) != FORMAT_ARGUMENTS[fmt]:
                    _error("format_setting_mismatch", oid)
                seen.add(oid)
                result[role].append({"occurrence": occurrence, "content": content})
        copied.append(result)
    if set(declared) != seen:
        _error("format_occurrences_mismatch", "formats")
    return copied[0], copied[1], declared


def _models(mapping, formats, roles):
    return [model_data.extract_hmmer_models(payload["content"], occurrence=payload["occurrence"],
                format=formats[payload["occurrence"]["occurrence_id"]])
            for role, payloads in mapping.items() if role in roles for payload in payloads]


def _single_model(extractions):
    if len(extractions) > 1:
        _error("model_occurrence_cardinality", "models")
    return extractions[0] if extractions else None


def recalculate_hmmer_preparation(sheet, *, parameters):
    """Invoke only the saved schema's calculator, with new explicit parameters."""
    saved = _json_copy(sheet, "sheet")
    _object(saved, "sheet")
    operation = _operation(saved.get("operation"))
    schema = _SCHEMAS[operation["program"]]
    if saved.get("schema") != schema or set(saved) != _SHEET_FIELDS[schema]:
        _error("sheet_schema_operation_mismatch", "sheet")
    selected = _parameters(parameters, schema)
    try:
        if schema == "hmmer_artifact_sheet_v1":
            result = artifact_calculations.calculate_hmmer_artifact_components(saved, parameters=selected)
        elif schema == "hmmer_alignment_preparation_sheet_v1":
            result = alignment_calculations.calculate_hmmer_alignment_preparation_components(saved, parameters=selected)
        elif schema == "hmmer_emission_sheet_v1":
            result = emission_calculations.calculate_hmmemit_components(saved, parameters=selected)
        elif schema == "hmmer_simulation_sheet_v1":
            result = simulation_calculations.calculate_hmmsim_components(saved, parameters=selected)
        elif schema == "hmmer_statistics_sheet_v1":
            result = statistics_calculations.calculate_hmmstat_components(saved, **selected)
        else:
            result = fm_calculations.calculate_hmmer_fm_components(saved, parameters=selected)
    except (KeyError, TypeError, IndexError, AttributeError, OverflowError) as exc:
        raise ContractError("native_hmmer_preparation_grading_saved_sheet_invalid:sheet") from exc
    return _json_copy(result, "calculations")


def grade_hmmer_preparation(*, operation, inputs, outputs, formats, metadata,
                             parameters, native_abi=None):
    """Validate and compose the requested pure reader/calculator pair.

    Missing roles stay absent. Original occurrence ordinals are preserved even
    after a missing earlier artifact. All actual model occurrences are extracted
    using their declared formats; conversion stdout is retained without adding
    a second model population. Neither ABI nor statistical defaults come from
    the machine performing grading.
    """
    operation = _operation(operation)
    program = operation["program"]
    requested = _parameters(parameters, _SCHEMAS[program])
    metadata, native_abi = _metadata(metadata, program), _abi(native_abi)
    inputs, outputs, formats = _payloads(inputs, outputs, formats, operation)
    common = {"operation": operation, "inputs": inputs, "outputs": outputs}
    if program in _ARTIFACT_PROGRAMS:
        extractions = (_models(inputs, formats, artifact_data.MODEL_ROLES) +
                       _models(outputs, formats, artifact_data.MODEL_ROLES))
        sheet = artifact_data.populate_hmmer_artifact_sheet(**common, model_extractions=extractions,
                    artifact_bindings=metadata.get("artifact_bindings"))
    elif program in _ALIGNMENT_PROGRAMS:
        extraction = _single_model(_models(outputs, formats, {"models"})) if program == "hmmbuild" else None
        sheet = alignment_data.populate_hmmer_alignment_preparation_sheet(**common, model_extraction=extraction)
    elif program == "hmmemit":
        sheet = emission_data.populate_hmmemit_sheet(**common,
                    model_extraction=_single_model(_models(inputs, formats, {"models"})))
    elif program == "hmmsim":
        score_abi = ({key: native_abi[key] for key in ("byte_order", "float_format", "bytes_per_float")}
                     if native_abi is not None else None)
        sheet = simulation_data.populate_hmmsim_sheet(**common,
                    model_extraction=_models(inputs, formats, {"models"}), native_abi=score_abi)
    elif program == "hmmstat":
        sheet = statistics_data.populate_hmmstat_sheet(**common,
                    model_extraction=_single_model(_models(inputs, formats, {"models"})))
    else:
        sheet = fm_data.populate_hmmer_fm_sheet(**common,
                    producer_contract=metadata.get("producer_contract"), source_binding=metadata.get("source_binding"))
    calculations = recalculate_hmmer_preparation(sheet, parameters=requested)
    return _json_copy({"version": VERSION, "operation": operation, "formats": formats,
        "metadata": metadata, "native_abi": native_abi, "requested_parameters": requested,
        "sheet": sheet, "calculations": calculations}, "grading")


__all__ = ["VERSION", "GRADING_FIELDS", "ContractError", "grade_hmmer_preparation",
           "recalculate_hmmer_preparation"]
