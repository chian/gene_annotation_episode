"""Finite private molecular execution and saved-sheet calculation.

The selected request is read once under an explicit byte pin. The native helper
owns its call receipt; the existing scientific readers own their sheets and
calculations. This writer has no Store, launcher, retry or investigation loop.
Its declaration records output bytes, not authenticated producing-attempt
custody. A CLI success means processing returned, not scientific validity.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

from .glycosylation_measurements import (
    SHEET_SCHEMA as GLYCO_SHEET_SCHEMA,
    build_glycosylation_sheet,
    calculate_glycosylation_components,
)
from .molecular_sequence_native import execute_molecular_sequence_request
from .orf_measurements import (
    SHEET_SCHEMA as ORF_SHEET_SCHEMA,
    build_orf_sheet,
    calculate_orf_components,
)
from .primer_placement_measurements import (
    SHEET_SCHEMA as PLACEMENT_SHEET_SCHEMA,
    build_primer_placement_sheet,
    calculate_primer_placement_components,
)
from .protease_kinetics_measurements import (
    SHEET_SCHEMA as PROTEASE_SHEET_SCHEMA,
    MEASUREMENT_FIELDS as PROTEASE_MEASUREMENT_FIELDS,
    populate_protease_kinetics_sheet,
    calculate_protease_kinetics_components,
)


REQUEST_VERSION = "molecular_sequence_driver_request_v1"
DECLARATION_VERSION = "molecular_sequence_driver_declaration_v1"
REQUEST_VERSION_V2 = "molecular_sequence_driver_request_v2"
DECLARATION_VERSION_V2 = "molecular_sequence_driver_declaration_v2"
_PROTEASE = "analyze_protease_kinetics"
_ORF = "annotate_open_reading_frames"
_PLACEMENT = "align_sequences"
_GLYCO = {"find_n_glycosylation_motifs", "predict_o_glycosylation_hotspots"}
_OPERATIONS = {_ORF, _PLACEMENT, *_GLYCO}
_IDENTITY_FIELDS = {"run_id", "episode_id", "resource_id", "operation_key", "execution_id"}
_CAPTURE_FIELDS = {"version", "request", "request_canonical_sha256", "stage", "native_record",
    "native_call_state", "reference_data", "execution_receipt", "stdout", "stderr", "failure"}
_CAPTURE_FIELDS_V3 = _CAPTURE_FIELDS | {"observer", "verification_failures"}
_QUALIFICATION = (
    "Private output byte declaration only. Host-supplied run, episode, resource, operation and execution "
    "identities are assertions, not authenticated producing-attempt custody. The native helper receipt "
    "covers its own call stages; it does not authenticate full driver/calculator file or import closure. "
    "Scientific sheets preserve their own meanings and missingness. No installation, public registration, "
    "episode return, scientific validity, confidence or credit is established by this declaration."
)


def _require(condition, message):
    if not condition:
        raise ValueError("molecular_sequence_driver_" + message)


def _closed(value, fields, name):
    _require(type(value) is dict and set(value) == set(fields), name + "_fields_required")


def _path(value):
    _require(type(value) is str and value and not any(c in value for c in "\0\n\r\\"),
        "canonical_absolute_path_required")
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ".." not in path.parts
        and value != "/", "canonical_absolute_path_required")
    return Path(value)


def _file_pin(value):
    _closed(value, ("path", "sha256", "size_bytes"), "file_pin")
    _path(value["path"])
    _require(type(value["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["sha256"])
        and type(value["size_bytes"]) is int and value["size_bytes"] >= 0, "file_pin_required")
    return deepcopy(value)


def _read_pinned(value):
    pin = _file_pin(value)
    descriptor = os.open(pin["path"], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        details = os.fstat(stream.fileno())
        _require(stat.S_ISREG(details.st_mode), "regular_selected_file_required")
        _require(details.st_size == pin["size_bytes"], "selected_file_pin_mismatch")
        raw = stream.read(pin["size_bytes"] + 1)
    _require(len(raw) == pin["size_bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"],
        "selected_file_pin_mismatch")
    return raw


def _json(raw):
    def fields(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "duplicate_json_field")
            result[key] = value
        return result

    def nonfinite(token):
        raise ValueError("molecular_sequence_driver_nonfinite_json:" + token)

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=fields, parse_constant=nonfinite)
    # This also rejects floating-point overflow such as the JSON token 1e999.
    json.dumps(value, allow_nan=False)
    return value


def _reference(value):
    return value is None or type(value) is str and bool(value)


def _mapping(value):
    return value is None or type(value) is dict


def _request(value):
    if type(value) is dict and value.get("version") == REQUEST_VERSION_V2:
        return _request_v2(value)
    _closed(value, ("version", "mode", "attempt_identity", "selection", "scientific_context"), "request")
    _require(value["version"] == REQUEST_VERSION and value["mode"] in ("native", "saved_sheet"),
        "request_version_and_mode_required")
    _closed(value["attempt_identity"], _IDENTITY_FIELDS, "attempt_identity")
    _require(all(type(v) is str and v for v in value["attempt_identity"].values()),
        "explicit_host_attempt_identity_required")
    selection = value["selection"]
    _require(type(selection) is dict, "selection_required")
    operation = selection.get("operation")
    _require(type(operation) is str and operation in _OPERATIONS, "operation_required")
    context = value["scientific_context"]
    if value["mode"] == "saved_sheet":
        _closed(selection, ("operation", "sheet_file"), "saved_selection")
        _file_pin(selection["sheet_file"])
        _require(context is None, "saved_sheet_owns_scientific_operands")
    else:
        _closed(selection, ("version", "operation", "arguments", "deployment"), "native_selection")
        if operation == _ORF:
            _closed(context, ("subject_ref", "parent_mapping"), "orf_context")
            _require(_reference(context["subject_ref"]) and _mapping(context["parent_mapping"]),
                "orf_context_required")
        elif operation == _PLACEMENT:
            _closed(context, ("target_ref", "primer_refs", "target_mapping", "primer_mappings"),
                "placement_context")
            refs, mappings = context["primer_refs"], context["primer_mappings"]
            _require(_reference(context["target_ref"]) and _mapping(context["target_mapping"])
                and (refs is None or type(refs) is list and all(_reference(v) for v in refs))
                and (mappings is None or type(mappings) is list and all(_mapping(v) for v in mappings)),
                "placement_context_required")
        else:
            _closed(context, ("input_ref", "input_mapping"), "glyco_context")
            _require(_reference(context["input_ref"]) and _mapping(context["input_mapping"]),
                "glyco_context_required")
    return operation


def _request_v2(value):
    _closed(value, ("version", "mode", "attempt_identity", "selection", "scientific_context"), "request_v2")
    _require(value["version"] == REQUEST_VERSION_V2 and value["mode"] in ("native", "saved_sheet"), "request_version_and_mode_required")
    _closed(value["attempt_identity"], _IDENTITY_FIELDS, "attempt_identity")
    _require(all(type(v) is str and v for v in value["attempt_identity"].values()), "explicit_host_attempt_identity_required")
    selection = value["selection"]
    _require(type(selection) is dict and selection.get("operation") == _PROTEASE, "v2_protease_operation_required")
    if value["mode"] == "saved_sheet":
        _closed(selection, ("operation", "sheet_file"), "saved_selection")
        _file_pin(selection["sheet_file"])
        _require(value["scientific_context"] is None, "saved_sheet_owns_scientific_operands")
    else:
        _closed(selection, ("version", "operation", "arguments", "deployment", "output_workspace", "environment"), "native_v3_selection")
        _require(selection["version"] == "molecular_sequence_request_v3", "native_v3_selection_required")
        _closed(value["scientific_context"], ("assay_context",), "protease_context")
    return _PROTEASE


def _native_capture(capture, selection):
    if selection["version"] == "molecular_sequence_request_v3":
        _closed(capture, _CAPTURE_FIELDS_V3, "native_capture_v3")
        _require(capture["version"] == "molecular_sequence_execution_v3" and capture["native_call_state"] in
            ("not_started", "returned", "raised"), "native_capture_version_and_state_required")
        if capture["request"] is not None:
            _require(json.dumps(capture["request"], sort_keys=True, allow_nan=False) ==
                json.dumps(selection, sort_keys=True, allow_nan=False), "native_capture_input_conflict")
        else:
            _require(capture["native_call_state"] == "not_started" and capture["failure"] is not None,
                "native_capture_input_conflict")
        return
    _closed(capture, _CAPTURE_FIELDS, "native_capture")
    expected = ("molecular_sequence_execution_v2" if selection["version"] == "molecular_sequence_request_v2"
        else "molecular_sequence_execution_v1")
    _require(capture["version"] == expected and capture["native_call_state"] in
        ("not_started", "returned", "raised"), "native_capture_version_and_state_required")
    if capture["request"] is None:
        _require(capture["native_call_state"] == "not_started" and capture["native_record"] is None
            and type(capture["failure"]) is dict, "native_capture_input_conflict")
    else:
        canonical = lambda item: json.dumps(item, sort_keys=True, allow_nan=False)
        _require(canonical(capture["request"]) == canonical(selection), "native_capture_input_conflict")
    _require(capture["failure"] is None or type(capture["failure"]) is dict,
        "native_failure_record_required")


def _sheet(capture, selection, context):
    operation, arguments = selection["operation"], selection["arguments"]
    record = capture["native_record"]
    if operation == _PROTEASE:
        return populate_protease_kinetics_sheet(native_capture=capture,
            measurements={key: arguments[key] for key in PROTEASE_MEASUREMENT_FIELDS}, **context)
    if record is None:
        _require(capture["failure"] is not None, "native_record_unavailable")
        return None
    if operation == _ORF:
        reference = capture["reference_data"]
        return build_orf_sheet(record, input_sequence=arguments["sequence"], **context,
            request={key: arguments[key] for key in ("min_length", "search_reverse", "filter_subsets")},
            genetic_code=reference.get("genetic_code_snapshot") if type(reference) is dict else None)
    if operation == _PLACEMENT:
        return build_primer_placement_sheet(record, target_sequence=arguments["long_seq"],
            primers=arguments["short_seqs"], **context)
    return build_glycosylation_sheet(operation, record["result"], sequence=arguments["sequence"],
        parameters={key: value for key, value in arguments.items() if key != "sequence"},
        native_outcome=record["outcome"], **context)


def _saved_sheet(sheet, operation):
    _require(type(sheet) is dict, "saved_scientific_sheet_required")
    expected = PROTEASE_SHEET_SCHEMA if operation == _PROTEASE else ORF_SHEET_SCHEMA if operation == _ORF else (
        PLACEMENT_SHEET_SCHEMA if operation == _PLACEMENT else GLYCO_SHEET_SCHEMA)
    _require(sheet.get("schema") == expected, "saved_sheet_operation_conflict")
    if operation in _GLYCO:
        _require(type(sheet.get("inputs")) is dict and sheet["inputs"].get("operation") == operation,
            "saved_sheet_operation_conflict")


def _calculate(sheet, operation):
    if operation == _PROTEASE:
        return calculate_protease_kinetics_components(sheet)
    if operation == _ORF:
        return calculate_orf_components(sheet)
    if operation == _PLACEMENT:
        return calculate_primer_placement_components(sheet)
    return calculate_glycosylation_components(sheet)


def _write_bytes(path, raw):
    with path.open("xb") as stream:
        if stream.write(raw) != len(raw):
            raise OSError("molecular_sequence_driver_incomplete_write")
        stream.flush()
        os.fsync(stream.fileno())


def _write_json(path, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
    _write_bytes(path, raw)


def _declarations(directory):
    # These are exactly the existing NativeFileDeclaration fields/states.
    result = {}
    for role in ("capture", "sheet", "components"):
        path = directory / (role + ".json")
        raw = path.read_bytes() if path.is_file() else None
        result[role] = {"relative_path": path.name, "format": "json",
            "state": "absent" if raw is None else "present",
            "sha256": None if raw is None else hashlib.sha256(raw).hexdigest(),
            "size_bytes": None if raw is None else len(raw)}
    return result


def _protease_native_declarations(directory, selection, *, inspect_files=True, failures=None):
    """Exact selected destinations, never paths extracted from native prose."""
    arguments = selection["arguments"]
    _require(_path(selection["output_workspace"]).resolve() == directory.resolve(), "selected_output_workspace_conflict")
    output = _path(arguments["output_dir"]).resolve()
    _require(output.is_relative_to(directory.resolve()), "native_output_outside_workspace")
    prefix = arguments["output_prefix"]
    _require(type(prefix) is str and prefix and prefix not in {".", ".."}
        and not any(c in prefix for c in "/\\\0\n\r"), "native_output_basename_required")
    records = {}
    for role, suffix, format_name in (("native_results", "_results.txt", "text"), ("native_plot", "_mm_plot.png", "png")):
        path = output / (prefix + suffix)
        relative = str(path.relative_to(directory.resolve()))
        record = {"relative_path": relative, "format": format_name, "state": "absent", "sha256": None, "size_bytes": None}
        if not inspect_files:
            _require(not path.is_symlink(), "native_symlink_output_unsupported")
            records[role] = record
            continue
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(descriptor, "rb") as stream:
                details = os.fstat(stream.fileno())
                _require(stat.S_ISREG(details.st_mode), "native_regular_file_required")
                raw = stream.read()
            record.update(state="present", sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        except FileNotFoundError:
            pass
        except Exception as error:
            if failures is None:
                raise
            failures.append({"stage": "native_output_declaration", "role": role,
                "exception_type": type(error).__name__, "message": str(error)})
        records[role] = record
    return records


def run_molecular_sequence_driver(*, request_file: dict, output_directory: str) -> dict:
    """Process one selected input into a fresh, exclusively owned directory.

    Invalid/existing output locations raise before processing. Other failures
    are retained separately in the declaration; completed earlier artifacts
    survive. Saved mode retains the original sheet bytes and never calls the
    native helper. A file-pin check authenticates bytes, not host identities.
    """
    directory = _path(output_directory)
    directory.mkdir(mode=0o700)  # No overwrite, retry, parent creation or reuse.
    declaration = {"version": DECLARATION_VERSION, "mode": None, "operation": None,
        "request_file": None, "request_file_pin_verified": False, "attempt_identity": None,
        "native_call_state": None, "native_failure": None, "driver_failure": None,
        "files": None, "qualification": _QUALIFICATION}
    stage = "read_request"
    request = None
    try:
        declaration["request_file"] = _file_pin(request_file)
        raw = _read_pinned(request_file)
        declaration["request_file_pin_verified"] = True
        stage = "parse_request"
        request = _json(raw)
        if type(request) is dict and request.get("version") == REQUEST_VERSION_V2:
            declaration.update(version=DECLARATION_VERSION_V2, native_outcome=None,
                observer_state="not_requested", observer_failures=[], verification_failures=[], native_output_completion="not_requested")
        stage = "validate_request"
        operation = _request(request)
        declaration.update(mode=request["mode"], operation=operation,
            attempt_identity=deepcopy(request["attempt_identity"]))
        selection = request["selection"]
        if request["mode"] == "native":
            if operation == _PROTEASE:
                stage = "validate_native_destinations"
                # Resolve and validate before the genuine call; absence is fine.
                _protease_native_declarations(directory, selection, inspect_files=False)
            stage = "invoke_helper"
            declaration["native_call_state"] = "unknown"
            capture = execute_molecular_sequence_request(selection)
            stage = "validate_native_capture"
            _native_capture(capture, selection)
            declaration.update(native_call_state=capture["native_call_state"],
                native_failure=deepcopy(capture["failure"]))
            if operation == _PROTEASE:
                record = capture["native_record"]
                outcome = None if record is None else record["outcome"]
                declaration.update(native_outcome=outcome, observer_failures=deepcopy(capture["observer"]["failures"]),
                    observer_state=capture["observer"]["state"],
                    verification_failures=deepcopy(capture["verification_failures"]),
                    native_output_completion="source_completed" if outcome == "completed" else "source_error" if outcome == "source_error"
                        else "native_raised" if capture["native_call_state"] == "raised" else "not_called")
            stage = "write_capture"
            _write_json(directory / "capture.json", capture)
            stage = "build_sheet"
            sheet = _sheet(capture, selection, request["scientific_context"])
            if sheet is not None:
                stage = "write_sheet"
                _write_json(directory / "sheet.json", sheet)
        else:
            declaration["native_call_state"] = "not_requested"
            stage = "read_saved_sheet"
            saved_raw = _read_pinned(selection["sheet_file"])
            stage = "parse_saved_sheet"
            sheet = _json(saved_raw)
            stage = "write_sheet"
            _write_bytes(directory / "sheet.json", saved_raw)
            stage = "validate_saved_sheet"
            _saved_sheet(sheet, operation)
        if sheet is not None:
            stage = "calculate"
            components = _calculate(sheet, operation)
            stage = "write_components"
            _write_json(directory / "components.json", components)
    except Exception as error:
        declaration["driver_failure"] = {"stage": stage,
            "exception_type": type(error).__name__, "message": str(error)}
    # Failure to inspect/seal the output directory is a writer failure that the
    # caller must observe; it cannot be replaced by an invented declaration.
    declaration["files"] = _declarations(directory)
    if declaration["version"] == DECLARATION_VERSION_V2 and request is not None and request.get("mode") == "native":
        try:
            declaration["files"].update(_protease_native_declarations(directory, request["selection"],
                failures=declaration["verification_failures"]))
        except Exception as error:
            declaration["verification_failures"].append({"stage": "native_output_declaration",
                "exception_type": type(error).__name__, "message": str(error)})
    _write_json(directory / "declaration.json", declaration)
    return declaration


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-file", required=True)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--request-size-bytes", required=True, type=int)
    parser.add_argument("--output-directory", required=True)
    arguments = parser.parse_args(argv)
    try:
        declaration = run_molecular_sequence_driver(request_file={"path": arguments.request_file,
            "sha256": arguments.request_sha256, "size_bytes": arguments.request_size_bytes},
            output_directory=arguments.output_directory)
    except Exception as error:
        sys.stderr.write(json.dumps({"stage": "output_directory_or_seal", "exception_type": type(error).__name__,
            "message": str(error)}, allow_nan=False) + "\n")
        return 1
    sys.stdout.write(json.dumps(declaration, allow_nan=False) + "\n")
    unsuccessful = declaration["driver_failure"] is not None or declaration["native_failure"] is not None
    if declaration["version"] == DECLARATION_VERSION_V2:
        unsuccessful = unsuccessful or bool(declaration["observer_failures"] or declaration["verification_failures"])
        unsuccessful = unsuccessful or declaration["mode"] == "native" and declaration["native_outcome"] != "completed"
        unsuccessful = unsuccessful or declaration["mode"] == "native" and declaration["observer_state"] != "captured"
    return int(unsuccessful)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["REQUEST_VERSION", "DECLARATION_VERSION", "REQUEST_VERSION_V2", "DECLARATION_VERSION_V2",
    "run_molecular_sequence_driver", "main"]
