"""One selected topology, MFE, or supplied-structure evaluation primitive.

There is no job submission, retry, resource choice, sheet population or scoring
here. Only this module imports ViennaRNA, and topology-only calls never do so.
The CLI's bound Software operand is checked before a native scientific call.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sys
import traceback

from .execution_contracts import canonical, digest
from .native_rna_structure_contracts import (WORKER_MODULE, validate_rna_structure_software)
from .practical_execution_state import _immutable
from .rna_structure_contracts import (COORDINATE_SYSTEM, OPERATIONS, analyze_rna_input_sequence,
    issue, make_rna_structure, native_uncertainty, unavailable_energy, validate_rna_input,
    validate_rna_model_spec_shape, validate_rna_effective_model_shape, validate_rna_native_record)
from .rna_structure_topology import parse_rna_topology

_MD_FIELDS = {"temperature_c": "temperature", **{key: key for key in
    ("dangles", "noLP", "noGU", "noGUclosure", "special_hp", "logML", "min_loop_size", "max_bp_span", "circ", "gquad")}}
_BOOL_FIELDS = {"noLP", "noGU", "noGUclosure", "special_hp", "logML", "circ", "gquad"}


class _NativeFailure(Exception):
    def __init__(self, code, field=None):
        self.code, self.field = code, field
        super().__init__(code)


def _checksum(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _diagnostic(value):
    print(canonical(value), flush=True)


def _software(rna=None):
    observed = {"python_executable": sys.executable, "python_sha256": _checksum(sys.executable),
        "python_version": platform.python_version(), "worker_module": WORKER_MODULE,
        "worker_source_sha256": _checksum(__file__), "viennarna_distribution_version": None,
        "rna_module_sha256": None, "rna_extension_sha256": None}
    if rna is not None:
        observed["rna_module_sha256"] = _checksum(rna.__file__)
        extension = getattr(rna, "_RNA", None)
        if extension is None or not getattr(extension, "__file__", None):
            raise _NativeFailure("rna_native_api_unsupported", "/software/rna_extension_sha256")
        observed["rna_extension_sha256"] = _checksum(extension.__file__)
        try:
            observed["viennarna_distribution_version"] = importlib.metadata.version("ViennaRNA")
        except importlib.metadata.PackageNotFoundError:
            pass
    return observed


def _check_software(selected, *, rna=None, native=False):
    observed = _software(rna)
    _diagnostic({"schema": "rna_software_observation_v1", "software": observed,
        "engine_version": getattr(rna, "__version__", None) if rna is not None else None})
    if selected is not None:
        selected = validate_rna_structure_software(selected)
        names = tuple(observed) if native else tuple(observed)[:5]
        for name in names:
            if selected[name] is not None and selected[name] != observed[name]:
                raise _NativeFailure("rna_software_identity_mismatch", "/software/" + name)


def _load_native(software):
    try:
        rna = importlib.import_module("RNA")
    except ImportError as error:
        raise _NativeFailure("rna_native_dependency_missing", "/software/rna_module_sha256") from error
    _check_software(software, rna=rna, native=True)
    version = getattr(rna, "__version__", None)
    if type(version) is not str or not version:
        raise _NativeFailure("rna_native_api_unsupported", "/model/engine_version")
    for name in ("md", "fold_compound", "params_save", "params_load", "params_load_RNA_Turner2004"):
        if not callable(getattr(rna, name, None)):
            raise _NativeFailure("rna_native_api_unsupported", "/model")
    if type(getattr(rna, "INF", None)) is not int or rna.INF <= 0:
        raise _NativeFailure("rna_native_api_unsupported", "/model")
    return rna


def _model(rna, selected, parameter_input, directory, parameter_path):
    selected = validate_rna_model_spec_shape(selected)
    use_file = selected["parameters"]["kind"] == "supplied_parameter_file"
    if use_file != (parameter_input is not None):
        raise _NativeFailure("rna_invalid_parameter_schema", "/model/parameters")
    # The documented RNA loader resets geometric defaults. It MUST run first.
    loaded = rna.params_load(str(parameter_input)) if use_file else rna.params_load_RNA_Turner2004()
    _diagnostic({"schema": "rna_parameter_operation_v1", "operation": "load", "return_repr": repr(loaded)})
    if type(loaded) is not int or loaded == 0:
        raise _NativeFailure("rna_parameter_load_failed", "/model/parameter_load_return")
    md = rna.md()
    effective = {}
    for name, native_name in _MD_FIELDS.items():
        if not hasattr(md, native_name):
            raise _NativeFailure("rna_native_api_unsupported", "/model/selected/" + name)
        setattr(md, native_name, selected[name])
        value = getattr(md, native_name)
        if name in _BOOL_FIELDS:
            if type(value) not in (bool, int) or value not in (0, 1):
                raise _NativeFailure("rna_native_api_unsupported", "/model/effective_settings/" + name)
            value = bool(value)
        if value != selected[name]:
            raise _NativeFailure("rna_unknown_native_setting", "/model/effective_settings/" + name)
        effective[name] = value
    others = []
    for name in sorted(set(dir(md)) - set(_MD_FIELDS.values()) - {"this", "thisown"}):
        if name.startswith("_"):
            continue
        try:
            value = getattr(md, name)
        except Exception:
            others.append({"name": name, "value": None, "state": "unavailable"})
            continue
        if callable(value):
            continue
        scalar = value is None or type(value) in (str, bool, int) or type(value) is float and math.isfinite(value)
        others.append({"name": name, "value": value if scalar else None, "state": "observed" if scalar else "unavailable"})
        if not scalar and type(value) in (list, tuple):
            # ModelSpec's snapshot uses scalar values. Preserve native arrays
            # separately as diagnostics, without pretending they were scalar.
            _diagnostic({"schema": "rna_model_array_observation_v1", "name": name, "value": value})
    parameter_path.parent.mkdir(parents=True, exist_ok=True)
    if parameter_path.exists():
        raise _NativeFailure("rna_output_path_conflict", "/model/parameter_artifact")
    saved = rna.params_save(str(parameter_path))
    _diagnostic({"schema": "rna_parameter_operation_v1", "operation": "save", "return_repr": repr(saved)})
    if type(saved) is not int or saved == 0 or not parameter_path.is_file():
        raise _NativeFailure("rna_parameter_load_failed", "/model/parameter_save_return")
    snapshot = {"schema": "vienna_rna_effective_model_v1", "model_key": "pending", "selected": selected,
        "engine": "ViennaRNA", "engine_version": rna.__version__, "effective_settings": effective,
        "other_observed_settings": others, "parameter_artifact": {
            "relative_path": str(parameter_path.relative_to(directory)), "sha256": _checksum(parameter_path),
            "size_bytes": parameter_path.stat().st_size}, "parameter_load_return": loaded, "parameter_save_return": saved}
    snapshot["model_key"] = "rna_model:" + digest({k: v for k, v in snapshot.items() if k != "model_key"})
    return md, validate_rna_effective_model_shape(snapshot)


def _empty(mode, record_key):
    return {"schema": "rna_native_record_v1", "operation": OPERATIONS[mode], "mode": mode,
        "record_key": record_key, "input": None, "analysis_sequence": None, "structure": None,
        "topology": None, "native_mfe": unavailable_energy(), "native_evaluation": unavailable_energy(),
        "native_uncertainty": native_uncertainty(), "model": None, "status": "failed", "issues": []}


def _produce(request, *, mode, record_key, model, parameter_input, output_directory,
        parameter_output=None, model_output=None, software=None, input_failure=None):
    record = _empty(mode, record_key)
    requested_field = "native_mfe" if mode == "mfe_prediction" else "native_evaluation"
    energy_requested = mode == "mfe_prediction" or model is not None
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    parameter_output = Path(parameter_output or directory / "effective-parameters.par")
    model_output = Path(model_output or directory / "model.json")
    try:
        if input_failure is not None:
            raise ValueError(input_failure)
        original = validate_rna_input(request, mode=mode)
        if original["record_key"] != record_key:
            raise ValueError("rna_input_identity_mismatch")
        record["input"] = original
    except (ValueError, TypeError) as error:
        code = "rna_input_identity_mismatch" if str(error) == "rna_input_identity_mismatch" else "rna_invalid_input_schema"
        record["issues"].append(issue(code, stage="input", record_key=record_key, field="/input"))
        if energy_requested:
            record[requested_field] = unavailable_energy("invalid_input", code)
        return validate_rna_native_record(record, expected_mode=mode)
    analysis, errors = analyze_rna_input_sequence(original, mode=mode)
    record["analysis_sequence"] = analysis
    record["issues"].extend(errors)
    if mode == "supplied_features":
        energy_requested = original["energy_mode"] == "viennarna_evaluate"
        record["structure"] = make_rna_structure(original, original["dot_bracket"], for_energy=energy_requested)
        record["topology"] = parse_rna_topology(original["dot_bracket"], coordinate_system=COORDINATE_SYSTEM)
        record["issues"].extend({**row, "record_key": record_key} for row in record["topology"]["issues"])
    structure_key = record["structure"]["structure_key"] if record["structure"] else None
    failure = None
    try:
        _check_software(software)
        if energy_requested != (model is not None):
            raise _NativeFailure("rna_invalid_parameter_schema", "/model")
        if not energy_requested and parameter_input is not None:
            raise _NativeFailure("rna_invalid_parameter_schema", "/model/parameters")
        if energy_requested:
            if model is not None:
                validate_rna_model_spec_shape(model)
            blocking = [row for row in record["issues"] if row["code"] != "no_sequence_supplied"]
            if analysis is None or blocking:
                cause = blocking[0]["code"] if blocking else "no_sequence_supplied"
                failure = ("missing_input" if cause == "no_sequence_supplied" else "invalid_input", cause)
            elif analysis["ambiguous_indices"]:
                for index in analysis["ambiguous_indices"]:
                    record["issues"].append(issue("rna_invalid_sequence_symbol", stage="input", record_key=record_key,
                        field="/sequence", index=index))
                failure = ("invalid_input", "rna_invalid_sequence_symbol")
            else:
                rna = _load_native(software)
                md, snapshot = _model(rna, model, parameter_input, directory, parameter_output)
                record["model"] = snapshot
                model_output.parent.mkdir(parents=True, exist_ok=True)
                _immutable(model_output, snapshot)
                fc = rna.fold_compound(analysis["analysis_sequence"], md)
                method = "mfe" if mode == "mfe_prediction" else "eval_structure"
                if not callable(getattr(fc, method, None)):
                    raise _NativeFailure("rna_native_api_unsupported", "/model")
                if mode == "mfe_prediction":
                    returned_structure, energy = fc.mfe()
                else:
                    returned_structure = None
                    energy = fc.eval_structure(record["structure"]["energy_dot_bracket"])
                # The actual return is written BEFORE interpreting its value.
                _diagnostic({"schema": "rna_raw_native_return_v1", "record_key": record_key,
                    "call": "fold_compound." + method, "structure_value": returned_structure,
                    "energy_repr": repr(energy)})
                if mode == "mfe_prediction":
                    if type(returned_structure) is not str or len(returned_structure) != analysis["length_nt"] or any(c not in ".()" for c in returned_structure):
                        raise _NativeFailure("rna_native_result_incompatible", "/structure")
                    topology = parse_rna_topology(returned_structure, coordinate_system=COORDINATE_SYSTEM)
                    if topology["status"] != "valid":
                        raise _NativeFailure("rna_native_result_incompatible", "/topology")
                    record["structure"] = make_rna_structure(original, returned_structure, for_energy=True)
                    record["topology"] = topology
                    structure_key = record["structure"]["structure_key"]
                if type(energy) not in (int, float) or not math.isfinite(energy):
                    raise _NativeFailure("rna_nonfinite_energy", "/" + requested_field)
                # RNAlib's single-sequence float API returns INF / 100 on
                # failure (params/constants.h and mfe/eval sources), in kcal/mol.
                if energy == rna.INF / 100.0:
                    raise _NativeFailure("rna_native_failed", "/" + requested_field)
                record[requested_field] = {"value": energy, "numeric_text": repr(energy), "unit": "kcal/mol",
                    "state": "present", "reason": None, "structure_key": structure_key,
                    "engine": "ViennaRNA", "engine_version": snapshot["engine_version"], "model_key": snapshot["model_key"]}
    except Exception as error:
        traceback.print_exc(file=sys.stderr)
        code = error.code if isinstance(error, _NativeFailure) else (
            "rna_invalid_parameter_schema" if isinstance(error, ValueError) and str(error) == "rna_invalid_parameter_schema" else "rna_native_failed")
        field = error.field if isinstance(error, _NativeFailure) else "/model"
        record["issues"].append(issue(code, stage="native", record_key=record_key, field=field))
        failure = ("failed", code)
    if energy_requested and failure is not None:
        record[requested_field] = unavailable_energy(*failure, structure_key=structure_key)
    good_topology = record["topology"] is not None and record["topology"]["status"] == "valid"
    bad = any(row["code"] != "no_sequence_supplied" for row in record["issues"])
    record["status"] = "complete" if good_topology and not bad and (not energy_requested or record[requested_field]["state"] == "present") else "partial" if good_topology else "failed"
    return validate_rna_native_record(record, expected_mode=mode)


def predict_rna_secondary_structure(request: dict, *, model: dict, parameter_input: Path | None,
        output_directory: Path) -> dict:
    return _produce(request, mode="mfe_prediction", record_key=request["record_key"], model=model,
        parameter_input=parameter_input, output_directory=output_directory)


def analyze_rna_secondary_structure_features(request: dict, *, energy_model: dict | None,
        parameter_input: Path | None, output_directory: Path) -> dict:
    return _produce(request, mode="supplied_features", record_key=request["record_key"], model=energy_model,
        parameter_input=parameter_input, output_directory=output_directory)


def _strict_json(raw):
    if isinstance(raw, bytes):
        # The supplied operand is explicitly UTF-8. json.loads(bytes) would
        # otherwise silently accept UTF-16/32 as a different input format.
        raw = raw.decode("utf-8")
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate_json_member")
            value[key] = item
        return value
    def nonfinite(value):
        raise ValueError("nonfinite_json_number:" + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("operation", "input-json", "model-json", "output-json", "record-key", "software-json"):
        parser.add_argument("--" + name, required=True)
    for name in ("parameter-input", "model-output", "parameter-output"):
        parser.add_argument("--" + name)
    args = parser.parse_args(argv)
    mode = next((mode for mode, operation in OPERATIONS.items() if operation == args.operation), None)
    if mode is None:
        parser.error("unsupported RNA operation")
    software = validate_rna_structure_software(_strict_json(args.software_json))
    model = _strict_json(args.model_json)
    original, input_failure = None, None
    try:
        original = _strict_json(Path(args.input_json).read_bytes())
    except Exception:
        traceback.print_exc(file=sys.stderr)
        input_failure = "rna_invalid_input_schema"
    result = _produce(original, mode=mode, record_key=args.record_key, model=model,
        parameter_input=Path(args.parameter_input) if args.parameter_input else None,
        output_directory=Path.cwd(), parameter_output=args.parameter_output, model_output=args.model_output,
        software=software, input_failure=input_failure)
    destination = Path(args.output_json)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _immutable(destination, result)
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
