"""Readers of supplied RNA result bytes and deterministic numerical-sheet population.

No function here obtains data or executes a native scientific program. The JSON
format is the declared RNA record; the only legacy format is Biomni's exact
three-line predictor file. Its prose feature log is deliberately unsupported.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re

from .rna_structure_contracts import (
    COORDINATE_SYSTEM, INPUT_SCHEMAS, MODES, NATIVE_FORMATS, OPERATIONS, SHEET_SCHEMAS,
    RNA_ISSUE_CODES, _id, _require, _same, _validate_analysis, _validate_energy, _validate_structure,
    analyze_rna_input_sequence, issue, make_rna_structure, native_uncertainty, sequence_pair_rows,
    unavailable_energy, validate_rna_effective_model_shape, validate_rna_input,
    validate_rna_native_parse, validate_rna_native_record, validate_rna_sheet, validate_topology,
)
from .rna_structure_topology import parse_rna_topology


def _parse_container(raw, format, mode):
    return {"schema": "rna_native_parse_v1", "format": format, "expected_mode": mode,
        "raw_sha256": hashlib.sha256(raw).hexdigest() if raw is not None else None,
        "raw_byte_count": len(raw) if raw is not None else None,
        "status": "invalid", "record": None, "issues": []}


def _unique_issues(rows):
    out = []
    for row in rows:
        if row not in out:
            out.append(deepcopy(row))
    return out


def _strict_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("rna_invalid_native_schema")
        value[key] = item
    return value


def _nonfinite(_):
    raise ValueError("rna_nonfinite_energy")


def _parse_failure(result, code, key):
    result["issues"] = [issue(code, stage="parse", record_key=key, artifact_role="native_result")]
    return result


def _recover_record(value, *, mode, record_key, cause):
    """Keep independently validated fields in a qualified, closed partial record.

    Only a shape-valid original native input with matching identity permits this
    recovery. Untrusted tables and energies are not repaired. Their original
    bytes remain identified by the NativeParse digest for caller custody.
    """
    if type(value) is not dict or value.get("schema") != "rna_native_record_v1" or value.get("mode") != mode or value.get("operation") != OPERATIONS[mode]:
        return None
    try:
        request = validate_rna_input(value.get("input"), mode=mode)
        _require(value.get("record_key") == record_key == request["record_key"], "rna_input_identity_mismatch")
    except (ValueError, TypeError):
        return None
    errors = [issue(cause, stage="parse", record_key=record_key, artifact_role="native_result")]
    _, sequence_errors = analyze_rna_input_sequence(request, mode=mode)
    errors.extend(sequence_errors)
    analysis = None
    try:
        _validate_analysis(value.get("analysis_sequence"), mode=mode, request=request)
        analysis = deepcopy(value.get("analysis_sequence"))
    except ValueError:
        errors.append(issue("rna_input_identity_mismatch", stage="parse", record_key=record_key, field="/analysis_sequence"))
    structure = topology = None
    try:
        _validate_structure(value.get("structure"), value.get("topology"), mode=mode, record_key=record_key, request=request)
        if mode == "mfe_prediction" and value.get("structure") is not None:
            _require(analysis is not None and value["topology"]["status"] == "valid" and
                analysis["length_nt"] == value["topology"]["length_nt"], "rna_input_identity_mismatch")
        structure, topology = deepcopy(value.get("structure")), deepcopy(value.get("topology"))
        if topology is not None:
            errors.extend({**row, "record_key": record_key} for row in topology["issues"])
    except ValueError as error:
        code = str(error) if str(error) in RNA_ISSUE_CODES else "rna_topology_table_mismatch"
        errors.append(issue(code, stage="parse", record_key=record_key, field="/topology"))
    model = None
    if value.get("model") is not None:
        try:
            model = validate_rna_effective_model_shape(value["model"])
        except (ValueError, TypeError):
            errors.append(issue("rna_native_result_incompatible", stage="parse", record_key=record_key, field="/model"))
    energies = {"native_mfe": unavailable_energy(), "native_evaluation": unavailable_energy()}
    requested_field = "native_mfe" if mode == "mfe_prediction" else "native_evaluation"
    if mode == "mfe_prediction" or request["energy_mode"] == "viennarna_evaluate":
        energy = value.get(requested_field)
        try:
            _validate_energy(energy, structure=structure, model=model)
            if energy["state"] == "present":
                _require(topology is not None and topology["status"] == "valid" and analysis is not None and
                    analysis["length_nt"] == topology["length_nt"] and not analysis["ambiguous_indices"], "rna_energy_structure_mismatch")
                if model is None:
                    errors.append(issue("rna_model_snapshot_missing", stage="parse", record_key=record_key, field="/model"))
            _require(energy["state"] not in ("not_requested", "not_produced"), "rna_native_result_incompatible")
            energies[requested_field] = deepcopy(energy)
            if energy["state"] not in ("present", "not_requested", "not_produced"):
                errors.append(issue(energy["reason"], stage="native", record_key=record_key, field="/" + requested_field))
        except (ValueError, TypeError):
            energies[requested_field] = unavailable_energy("incompatible", cause,
                structure_key=structure["structure_key"] if structure else None)
    result = {"schema": "rna_native_record_v1", "operation": OPERATIONS[mode], "mode": mode,
        "record_key": record_key, "input": request, "analysis_sequence": analysis,
        "structure": structure, "topology": topology, **energies,
        "native_uncertainty": native_uncertainty(), "model": model, "status": "partial",
        "issues": _unique_issues(errors)}
    try:
        return validate_rna_native_record(result, expected_mode=mode)
    except ValueError:
        return None


def parse_rna_native_record(raw: bytes | None, *, format: str, expected_mode: str,
        record_key: str, expected_sequence: str | None = None) -> dict:
    """Parse one declared artifact with the original caller-owned record identity.

    ``None`` denotes an actually absent artifact and has no digest or byte count.
    Actual empty bytes have their actual zero length and SHA-256. JSON never
    recovers a missing prediction from a sequence. Legacy dispatch requires the
    independently retained sequence and never guesses it from its own output.
    """
    _require(raw is None or type(raw) is bytes)
    _require(format in NATIVE_FORMATS and expected_mode in MODES and _id(record_key))
    result = _parse_container(raw, format, expected_mode)
    if raw is None:
        return _parse_failure(result, "rna_native_result_missing", record_key)
    if format == "biomni_rna_structure_text_v0":
        if expected_mode != "mfe_prediction":
            return _parse_failure(result, "rna_native_result_incompatible", record_key)
        if expected_sequence is None:
            return _parse_failure(result, "rna_legacy_context_missing", record_key)
        return parse_biomni_rna_prediction_text(raw, record_key=record_key, expected_sequence=expected_sequence)
    _require(expected_sequence is None, "rna_invalid_input_schema")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_pairs, parse_constant=_nonfinite)
    except UnicodeDecodeError:
        return _parse_failure(result, "rna_invalid_native_schema", record_key)
    except json.JSONDecodeError as error:
        # Only an incomplete token/container at EOF is described as truncated.
        code = "rna_output_truncated" if raw and (error.pos >= len(error.doc.rstrip()) or error.msg.startswith("Unterminated string")) else "rna_invalid_native_schema"
        return _parse_failure(result, code, record_key)
    except ValueError as error:
        code = str(error) if str(error) in RNA_ISSUE_CODES else "rna_invalid_native_schema"
        return _parse_failure(result, code, record_key)
    if type(value) is dict and value.get("record_key") != record_key:
        return _parse_failure(result, "rna_input_identity_mismatch", record_key)
    if type(value) is dict and value.get("input") is None and value.get("analysis_sequence") is not None:
        # Only the explicitly selected legacy reader has authority to interpret
        # a reported sequence without an original JSON input container.
        return _parse_failure(result, "rna_native_result_incompatible", record_key)
    try:
        record = validate_rna_native_record(value, expected_mode=expected_mode)
    except (ValueError, TypeError) as error:
        code = str(error) if str(error) in RNA_ISSUE_CODES else "rna_invalid_native_schema"
        record = _recover_record(value, mode=expected_mode, record_key=record_key, cause=code)
        if record is None:
            return _parse_failure(result, code, record_key)
        result.update(status="partial", record=record, issues=deepcopy(record["issues"]))
        return result
    result.update(status="valid", record=record, issues=deepcopy(record["issues"]))
    return result


def parse_biomni_rna_prediction_text(raw: bytes, *, record_key: str, expected_sequence: str) -> dict:
    """Read only Biomni's retained Sequence/Structure/Minimum Free Energy file.

    Native numerical text is kept without rounding. The legacy file contains no
    structured original request, engine version or model snapshot; those remain
    explicitly unknown. This reader does not claim a local native execution.
    """
    _require(type(raw) is bytes and _id(record_key) and type(expected_sequence) is str)
    result = _parse_container(raw, "biomni_rna_structure_text_v0", "mfe_prediction")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return _parse_failure(result, "rna_invalid_native_schema", record_key)
    match = re.fullmatch(r"Sequence: ([^\r\n]*)\nStructure: ([^\r\n]*)\nMinimum Free Energy: ([^\r\n]*) kcal/mol\n?", text)
    if match is None:
        return _parse_failure(result, "rna_invalid_native_schema", record_key)
    sequence, dot_bracket, numeric_text = match.groups()
    if sequence != expected_sequence:
        return _parse_failure(result, "rna_input_identity_mismatch", record_key)
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", numeric_text) is None:
        code = "rna_nonfinite_energy" if numeric_text.lower() in ("nan", "inf", "-inf", "+inf", "infinity", "-infinity") else "rna_invalid_native_schema"
        return _parse_failure(result, code, record_key)
    energy_value = float(numeric_text)
    if not math.isfinite(energy_value):
        return _parse_failure(result, "rna_nonfinite_energy", record_key)
    validation_request = {"schema": INPUT_SCHEMAS["mfe_prediction"], "record_key": record_key,
        "sequence_id": None, "sequence": sequence, "normalization": "exact", "subject_binding": None}
    analysis, errors = analyze_rna_input_sequence(validation_request, mode="mfe_prediction")
    topology = parse_rna_topology(dot_bracket, coordinate_system=COORDINATE_SYSTEM)
    if errors or topology["status"] != "valid":
        result["issues"] = errors + [{**row, "record_key": record_key} for row in topology["issues"]]
        return result
    if len(sequence) != len(dot_bracket):
        return _parse_failure(result, "rna_sequence_structure_length_mismatch", record_key)
    # The legacy native fold returns parentheses only; extended supplied grammar
    # is not evidence of this predictor's actual native output format.
    if any(symbol not in ".()" for symbol in dot_bracket):
        return _parse_failure(result, "rna_native_result_incompatible", record_key)
    structure = make_rna_structure(validation_request, dot_bracket, for_energy=True)
    energy = {"value": energy_value, "numeric_text": numeric_text, "unit": "kcal/mol",
        "state": "present", "reason": None, "structure_key": structure["structure_key"],
        "engine": "ViennaRNA", "engine_version": None, "model_key": None}
    errors = [issue("native_metadata_not_retained", stage="parse", record_key=record_key, field="/model")]
    record = {"schema": "rna_native_record_v1", "operation": OPERATIONS["mfe_prediction"],
        "mode": "mfe_prediction", "record_key": record_key, "input": None,
        "analysis_sequence": analysis, "structure": structure, "topology": topology,
        "native_mfe": energy, "native_evaluation": unavailable_energy(),
        "native_uncertainty": native_uncertainty(), "model": None, "status": "partial", "issues": errors}
    result.update(status="valid", record=validate_rna_native_record(record, expected_mode="mfe_prediction"), issues=errors)
    return result


def _populate(native, *, mode, record_key, original_input, model_metadata, subject_binding):
    native = validate_rna_native_parse(native)
    _require(_id(record_key) and native["expected_mode"] == mode, "rna_input_identity_mismatch")
    record = native["record"]
    if record is not None:
        _require(record["record_key"] == record_key, "rna_input_identity_mismatch")
    original = validate_rna_input(original_input, mode=mode) if original_input is not None else None
    if original is not None:
        _require(original["record_key"] == record_key, "rna_input_identity_mismatch")
    errors = deepcopy(native["issues"])
    analysis = None
    trusted = record is not None
    if original is None:
        trusted = False
        errors.append(issue("rna_invalid_input_schema", stage="input", record_key=record_key, field="/original_input"))
    else:
        analysis, sequence_errors = analyze_rna_input_sequence(original, mode=mode)
        errors.extend(sequence_errors)
        if record is not None:
            if record["input"] is not None and not _same(record["input"], original):
                trusted = False
            elif record["input"] is None and native["format"] == "biomni_rna_structure_text_v0":
                trusted = analysis is not None and record["analysis_sequence"] is not None and (
                    analysis["analysis_sequence"] == record["analysis_sequence"]["analysis_sequence"])
            elif record["input"] is None:
                trusted = False
            if not trusted:
                errors.append(issue("rna_input_identity_mismatch", stage="parse", record_key=record_key, field="/input"))
    if subject_binding is not None:
        _require(original is not None and _same(subject_binding, original["subject_binding"]), "rna_subject_binding_conflict")
    structure = topology = None
    if original is not None and mode == "supplied_features":
        structure = make_rna_structure(original, original["dot_bracket"], for_energy=original["energy_mode"] == "viennarna_evaluate")
        topology = parse_rna_topology(original["dot_bracket"], coordinate_system=COORDINATE_SYSTEM)
        errors.extend({**row, "record_key": record_key} for row in topology["issues"])
    elif original is not None and trusted:
        structure, topology = deepcopy(record["structure"]), deepcopy(record["topology"])
    model = deepcopy(record["model"]) if trusted else None
    if model_metadata is not None:
        supplied_model = validate_rna_effective_model_shape(model_metadata)
        _require(model is None or _same(model, supplied_model), "rna_native_result_incompatible")
        model = supplied_model
    energies = {"native_mfe": unavailable_energy(), "native_evaluation": unavailable_energy()}
    requested = "native_mfe" if mode == "mfe_prediction" else "native_evaluation"
    energy_requested = mode == "mfe_prediction" or original is None or original["energy_mode"] == "viennarna_evaluate"
    if energy_requested:
        if trusted:
            energies[requested] = deepcopy(record[requested])
        else:
            cause = ("rna_invalid_input_schema" if original is None else
                "rna_input_identity_mismatch" if record is not None else
                errors[0]["code"] if errors else "rna_native_result_missing")
            state = "invalid_input" if original is None else "truncated" if cause == "rna_output_truncated" else "missing_input" if cause == "rna_native_result_missing" else "incompatible"
            energies[requested] = unavailable_energy(state, cause,
                structure_key=structure["structure_key"] if structure else None)
    if record is not None:
        errors.extend(record["issues"])
    errors = _unique_issues(errors)
    valid_topology = topology is not None and topology["status"] == "valid"
    status = "invalid" if not valid_topology else "partial" if any(row["code"] != "no_sequence_supplied" for row in errors) else "complete"
    sheet = {"schema": SHEET_SCHEMAS[mode], "operation": OPERATIONS[mode], "mode": mode,
        "record_key": record_key, "original_input": original, "coordinate_system": COORDINATE_SYSTEM,
        "analysis_sequence": analysis, "structure": structure, "topology": topology,
        "sequence_pairs": sequence_pair_rows(topology, analysis), **energies,
        "native_uncertainty": native_uncertainty(), "model": model,
        "subject_binding": deepcopy(subject_binding) if original is not None else None,
        "status": status, "issues": errors,
        "native_input": None if native["raw_sha256"] is None else {"format": native["format"],
            "sha256": native["raw_sha256"], "byte_count": native["raw_byte_count"]}, "legacy_quantities": None}
    return validate_rna_sheet(sheet)


def populate_rna_prediction_sheet(native: dict, *, record_key: str, original_input: dict | None,
        model_metadata: dict | None, subject_binding: dict | None) -> dict:
    """Populate prediction data only from a compatible retained native prediction."""
    return _populate(native, mode="mfe_prediction", record_key=record_key, original_input=original_input,
        model_metadata=model_metadata, subject_binding=subject_binding)


def populate_rna_feature_sheet(native: dict, *, record_key: str, original_input: dict | None,
        model_metadata: dict | None, subject_binding: dict | None) -> dict:
    """Preserve supplied topology independently of missing/failed native energy."""
    return _populate(native, mode="supplied_features", record_key=record_key, original_input=original_input,
        model_metadata=model_metadata, subject_binding=subject_binding)
