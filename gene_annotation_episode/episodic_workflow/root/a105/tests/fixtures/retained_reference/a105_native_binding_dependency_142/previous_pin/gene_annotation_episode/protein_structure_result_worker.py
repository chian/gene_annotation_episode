"""Qualify retained protein results, or explicitly recalculate a saved sheet.

This Store-free worker reads only its supplied retained files. Original native
calculations are checked without refitting. Only saved_sheet_recalculation calls
the calculator, once, with the selected parameters. Diagnostic retained files
are not published scientific authority: the host owns custody and qualification
of the complete result before constructing any descriptor or requested return.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat
import sys
from typing import Literal, TypeAlias, TypedDict, get_args

from jsonschema import Draft202012Validator, validators

from .execution_contracts import canonical
from .protein_structure_contracts import (
    CalculationParameters, FileIdentity, IssueCode, State, StructuredIssue,
    issue, protein_structure_schema_definitions, same,
    validate_calculation_parameters, validate_file_identity,
    validate_protein_structure_sheet,
)
from .native_protein_structure_contracts import (
    NATIVE_FORMATS, ScientificRequest, Software,
    validate_native_protein_structure_result, validate_protein_structure_request,
    validate_protein_structure_software,
)
from .protein_structure_sheet import parse_native_protein_comparison
from .protein_structure_calculations import (
    calculate_protein_structure_components,
    validate_recorded_protein_structure_components,
)


class RetainedProteinInput(TypedDict):
    file_identity: FileIdentity
    path: str


class NativeProteinResultWorkerPlan(TypedDict):
    version: Literal["protein_structure_result_worker_plan_v1"]
    mode: Literal["original_native_result"]
    directory: str
    expected_request: ScientificRequest
    expected_software: Software
    native_result: RetainedProteinInput | None


class SavedProteinResultWorkerPlan(TypedDict):
    version: Literal["protein_structure_result_worker_plan_v1"]
    mode: Literal["saved_sheet_recalculation"]
    directory: str
    sheet: RetainedProteinInput
    original_components: RetainedProteinInput
    parameters: CalculationParameters


ProteinResultWorkerPlan: TypeAlias = NativeProteinResultWorkerPlan | SavedProteinResultWorkerPlan


class ProteinWorkerOutput(TypedDict):
    relative_path: str
    file_identity: FileIdentity


class ProteinResultWorkerResult(TypedDict):
    version: Literal["protein_structure_result_worker_result_v1"]
    mode: Literal["original_native_result", "saved_sheet_recalculation"]
    operation: Literal["inspect", "extract_sequence", "compare"]
    native_result_file: ProteinWorkerOutput | None
    sheet_file: ProteinWorkerOutput | None
    components_file: ProteinWorkerOutput | None
    state: State
    issues: list[StructuredIssue]


_PLAN_VERSION = "protein_structure_result_worker_plan_v1"
_RESULT_VERSION = "protein_structure_result_worker_result_v1"
_SHEET_FORMAT = "protein_structure_comparison_sheet_v1"
_COMPONENTS_FORMAT = "protein_structure_components_v1"
_OUTPUT_NAMES = {"native_result_file": "native-result.json",
                 "sheet_file": "sheet.json", "components_file": "components.json"}
_RESULT_NAME = "worker-result.json"
_MODES = ("original_native_result", "saved_sheet_recalculation")
_CODES = frozenset(get_args(IssueCode))
_ISSUE_VALIDATOR = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER
    .redefine("integer", lambda _, value: type(value) is int)
    .redefine("number", lambda _, value: type(value) in (int, float) and math.isfinite(value)))(
        {"$defs": protein_structure_schema_definitions(), "$ref": "#/$defs/StructuredIssue"})


def _require(condition, code="invalid_schema"):
    if not condition:
        raise ValueError(code)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields))


def _checked(function, value):
    """Normalize malformed-data exceptions at shared validator boundaries."""
    try:
        return function(value)
    except (TypeError, KeyError, IndexError, OverflowError, RecursionError) as error:
        raise ValueError("invalid_schema") from error


def _path(value):
    """Lexical validation only; plan validation never consults the filesystem."""
    _require(type(value) is str and value and not any(c in value for c in "\0\r\n\\"), "invalid_output_path")
    result = PurePosixPath(value)
    _require(result.is_absolute() and str(result) == value and ".." not in result.parts
             and value != "/", "invalid_output_path")
    return result


def _retained(value):
    _closed(value, RetainedProteinInput.__annotations__)
    validate_file_identity(value["file_identity"])
    return _path(value["path"])


def validate_protein_structure_result_worker_plan(value: ProteinResultWorkerPlan) -> ProteinResultWorkerPlan:
    """Validate a detached execution plan; no I/O or scientific calculation.

    Operation-specific formats are qualified when the retained input is read,
    so a contradictory retained format produces a typed result failure.
    """
    _checked(_plain, value)
    _require(type(value) is dict and type(value.get("mode")) is str and value["mode"] in _MODES)
    native = value["mode"] == "original_native_result"
    _closed(value, (NativeProteinResultWorkerPlan if native else SavedProteinResultWorkerPlan).__annotations__)
    _require(value["version"] == _PLAN_VERSION)
    directory = _path(value["directory"])
    if native:
        _checked(validate_protein_structure_request, value["expected_request"])
        _checked(validate_protein_structure_software, value["expected_software"])
        inputs = [] if value["native_result"] is None else [value["native_result"]]
    else:
        validate_calculation_parameters(value["parameters"])
        inputs = [value["sheet"], value["original_components"]]
    paths = [_retained(row) for row in inputs]
    for path in paths:
        _require(path != directory and directory not in path.parents and path not in directory.parents,
                 "invalid_output_path")
    for index, path in enumerate(paths):
        _require(all(path != other and path not in other.parents and other not in path.parents
                     for other in paths[index + 1:]), "invalid_output_path")
    return deepcopy(value)


def validate_protein_structure_result_worker_result(value: ProteinResultWorkerResult) -> ProteinResultWorkerResult:
    """Validate closed output shape and relationships without reading its files."""
    _checked(_plain, value)
    _closed(value, ProteinResultWorkerResult.__annotations__)
    _require(value["version"] == _RESULT_VERSION and type(value["mode"]) is str and value["mode"] in _MODES)
    _require(type(value["operation"]) is str and value["operation"] in NATIVE_FORMATS)
    _require(type(value["state"]) is str and value["state"] in get_args(State))
    _require(type(value["issues"]) is list)
    try:
        _require(all(_ISSUE_VALIDATOR.is_valid(row) for row in value["issues"]))
        # Check plain JSON data as well as the shared shape; no tuple coercion.
        _plain(value["issues"])
    except (TypeError, OverflowError, RecursionError) as error:
        raise ValueError("invalid_schema") from error
    formats = {"native_result_file": NATIVE_FORMATS[value["operation"]],
               "sheet_file": _SHEET_FORMAT, "components_file": _COMPONENTS_FORMAT}
    for field, filename in _OUTPUT_NAMES.items():
        row = value[field]
        if row is not None:
            _closed(row, ProteinWorkerOutput.__annotations__)
            _require(row["relative_path"] == filename, "invalid_output_path")
            identity = validate_file_identity(row["file_identity"])
            _require(identity["format"] == formats[field], "unsupported_format")
            _require(identity["byte_length"] > 0, "conflicting_identity")
    if value["mode"] == "saved_sheet_recalculation":
        _require(value["operation"] == "compare" and value["native_result_file"] is None)
    elif value["native_result_file"] is None:
        _require(value["sheet_file"] is None and value["components_file"] is None)
    if value["operation"] != "compare":
        _require(value["sheet_file"] is None and value["components_file"] is None)
    _require(value["components_file"] is None or value["sheet_file"] is not None)
    if value["mode"] == "original_native_result":
        _require((value["sheet_file"] is None) == (value["components_file"] is None))
    if value["state"] == "complete":
        _require(value["components_file"] is not None if value["operation"] == "compare"
                 else value["native_result_file"] is not None)
    if all(value[field] is None for field in _OUTPUT_NAMES):
        _require(value["state"] in ("unavailable", "invalid") and bool(value["issues"]))
    if value["operation"] == "compare" and value["components_file"] is None:
        _require(value["state"] != "complete" and bool(value["issues"]))
    return deepcopy(value)


def _plain(value):
    if type(value) is dict:
        _require(all(type(key) is str and "\0" not in key for key in value))
        for item in value.values():
            _plain(item)
    elif type(value) is list:
        for item in value:
            _plain(item)
    elif type(value) is str:
        _require("\0" not in value)
    elif type(value) is float:
        _require(math.isfinite(value))
    else:
        _require(value is None or type(value) in (bool, int))


def _decode(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            _require(key not in value)
            value[key] = item
        return value

    def nonfinite(_):
        raise ValueError("invalid_schema")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
        _plain(value)
        _require(canonical(value).encode("utf-8") == raw)
    except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError("invalid_schema") from error
    return value


def _safe_path(path):
    path = Path(path)
    _path(str(path))
    _require(not path.is_symlink() and path.resolve() == path, "invalid_output_path")
    return path


def _read(path):
    path = _safe_path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        _require(stat.S_ISREG(os.fstat(descriptor).st_mode), "invalid_output_path")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            return stream.read()
    finally:
        os.close(descriptor)


def _load(retained, expected_format):
    _require(retained["file_identity"]["format"] == expected_format, "unsupported_format")
    try:
        raw = _read(retained["path"])
    except FileNotFoundError as error:
        raise ValueError("retained_artifact_missing") from error
    except OSError as error:
        raise ValueError("capture_incomplete") from error
    identity = retained["file_identity"]
    _require(len(raw) == identity["byte_length"] and hashlib.sha256(raw).hexdigest() == identity["sha256"],
             "input_digest_mismatch")
    return raw, _decode(raw)


def _output(raw, filename, format):
    sha = hashlib.sha256(raw).hexdigest()
    return {"relative_path": filename, "file_identity": {
        "artifact_ref": "artifact_" + sha, "sha256": sha, "byte_length": len(raw), "format": format}}


def _failure(result, error, *, stage="input", field=None, artifact_role=None):
    code = str(error) if str(error) in _CODES else "invalid_schema"
    result["state"] = "unavailable" if code in (
        "native_result_missing", "retained_artifact_missing", "capture_incomplete") else "invalid"
    result["issues"].append(issue(code, stage=stage, field=field, artifact_role=artifact_role))


def _original(plan, result, outputs):
    retained = plan["native_result"]
    if retained is None:
        _failure(result, ValueError("native_result_missing"), stage="native", artifact_role="native_result")
        return
    field = "file_identity"
    try:
        raw, native = _load(retained, NATIVE_FORMATS[result["operation"]])
        _require(type(native) is dict and native.get("version") == NATIVE_FORMATS[result["operation"]], "unsupported_format")
        field = None
        native = _checked(validate_native_protein_structure_result, native)
        field = "request"
        _require(same(native["request"], plan["expected_request"]), "original_commission_mismatch")
        field = "software"
        _require(same(native["producer"], plan["expected_software"]), "software_identity_mismatch")
    except ValueError as error:
        _failure(result, error, stage="native", field=field, artifact_role="native_result")
        return
    outputs["native-result.json"] = raw
    result["native_result_file"] = _output(raw, "native-result.json", native["version"])
    result["state"], result["issues"] = native["state"], deepcopy(native["issues"])
    if result["operation"] != "compare":
        return
    try:
        sheet = parse_native_protein_comparison(native, expected_request=plan["expected_request"])
        if sheet is None:
            return
        components = validate_recorded_protein_structure_components(sheet, components=sheet["native_baseline"])
    except ValueError as error:
        # The C-valid native envelope remains diagnostic evidence. It does not
        # authorize projecting comparison numbers after B rejects its sheet.
        _failure(result, error, stage="native", artifact_role="native_result")
        return
    for field, value, format in (("sheet_file", sheet, _SHEET_FORMAT),
                                 ("components_file", components, _COMPONENTS_FORMAT)):
        raw = canonical(value).encode("utf-8")
        filename = _OUTPUT_NAMES[field]
        outputs[filename] = raw
        result[field] = _output(raw, filename, format)


def _saved(plan, result, outputs):
    field = "file_identity"
    try:
        raw, sheet = _load(plan["sheet"], _SHEET_FORMAT)
        field = "descriptor"
        sheet = validate_protein_structure_sheet(sheet)
    except ValueError as error:
        _failure(result, error, field=field)
        return
    # Preserve independently valid sheet bytes even when the separately
    # required baseline record fails. The host must qualify the complete result
    # before publishing any usable saved-sheet descriptor or numerical facts.
    outputs["sheet.json"] = raw
    result["sheet_file"] = _output(raw, "sheet.json", _SHEET_FORMAT)
    try:
        field = "file_identity"
        _, original = _load(plan["original_components"], _COMPONENTS_FORMAT)
        field = "descriptor"
        _require(sheet["native_baseline"] is not None, "conflicting_identity")
        _require(same(sheet["native_baseline"], original), "conflicting_identity")
        field = "request"
        _require(same(original["parameters"], sheet["native_request"]), "original_commission_mismatch")
        field = "descriptor"
        validate_recorded_protein_structure_components(sheet, components=original)
        field = "numerical_parameters"
        components = calculate_protein_structure_components(sheet, parameters=plan["parameters"])
        validate_recorded_protein_structure_components(sheet, components=components)
    except ValueError as error:
        _failure(result, error, field=field)
        return
    raw = canonical(components).encode("utf-8")
    outputs["components.json"] = raw
    result["components_file"] = _output(raw, "components.json", _COMPONENTS_FORMAT)
    result["state"], result["issues"] = components["state"], deepcopy(components["issues"])


def _publish(directory, outputs):
    # Check the entire public layout before writing anything: stale files from
    # a conflicting previous result cannot survive a newly unavailable field.
    for filename in (*_OUTPUT_NAMES.values(), _RESULT_NAME):
        path = _safe_path(directory / filename)
        if path.exists():
            _require(filename in outputs and _read(path) == outputs[filename], "original_commission_mismatch")
        _require(not _safe_path(directory / ("." + filename + ".writing")).exists(), "invalid_output_path")
    for filename, raw in outputs.items():
        path = _safe_path(directory / filename)
        if path.exists():
            continue
        temporary = _safe_path(directory / ("." + filename + ".writing"))
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError as error:
            raise ValueError("invalid_output_path") from error
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fchmod(descriptor, 0o444)
                os.fsync(descriptor)
            try:
                os.link(temporary, path)
            except FileExistsError as error:
                raise ValueError("original_commission_mismatch") from error
        finally:
            os.close(descriptor)
            temporary.unlink()
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run_protein_structure_result_worker(plan: ProteinResultWorkerPlan) -> ProteinResultWorkerResult:
    """Read the selected retained bytes and write one immutable closed result."""
    plan = validate_protein_structure_result_worker_plan(plan)
    directory = _safe_path(plan["directory"])
    _require(not directory.exists() or directory.is_dir(), "invalid_output_path")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for filename in (*_OUTPUT_NAMES.values(), _RESULT_NAME):
        path = _safe_path(directory / filename)
        _require(not path.exists() or stat.S_ISREG(path.lstat().st_mode), "invalid_output_path")
        if path.exists():
            inputs = ([plan["native_result"]] if plan["mode"] == "original_native_result"
                      else [plan["sheet"], plan["original_components"]])
            for retained in inputs:
                if retained is not None:
                    try:
                        original = Path(retained["path"]).lstat()
                    except FileNotFoundError:
                        continue
                    _require((original.st_dev, original.st_ino) != (path.stat().st_dev, path.stat().st_ino),
                             "invalid_output_path")
    result = {"version": _RESULT_VERSION, "mode": plan["mode"],
        "operation": plan["expected_request"]["operation"] if plan["mode"] == "original_native_result" else "compare",
        "native_result_file": None, "sheet_file": None, "components_file": None,
        "state": "unavailable", "issues": []}
    outputs = {}
    if plan["mode"] == "original_native_result":
        _original(plan, result, outputs)
    else:
        _saved(plan, result, outputs)
    result = validate_protein_structure_result_worker_result(result)
    outputs[_RESULT_NAME] = canonical(result).encode("utf-8")
    _publish(directory, outputs)
    return result


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    _require(type(arguments) is list and len(arguments) == 1)
    plan = validate_protein_structure_result_worker_plan(_decode(_read(arguments[0])))
    run_protein_structure_result_worker(plan)
    return 0


__all__ = ["RetainedProteinInput", "NativeProteinResultWorkerPlan", "SavedProteinResultWorkerPlan",
    "ProteinResultWorkerPlan", "ProteinWorkerOutput", "ProteinResultWorkerResult",
    "validate_protein_structure_result_worker_plan", "validate_protein_structure_result_worker_result",
    "run_protein_structure_result_worker"]


if __name__ == "__main__":
    raise SystemExit(main())
