"""Explicit verification-only current software preparation, contract030.

This prepares a new selection. It never replaces a commissioned job's software.
No model is loaded and no scientific work is dispatched by this module.
"""
from copy import deepcopy
import importlib.metadata
import os
from pathlib import Path
import subprocess
import sys

from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.flux_balance_contracts import validate_flux_balance_record
from gene_annotation_episode.native_flux_balance_contracts import (
    flux_balance_environment, path_value, validate_flux_balance_software,
)
from gene_annotation_episode.native_flux_balance_storage import (
    directory, file_pin, immutable_bytes, immutable_json, read_json, retain_input,
)


VERSION = "explicit_current_fba_software_preparation_v1"
REQUIRED = {
    "__init__.py", "execution_contracts.py", "flux_balance_contracts.py",
    "native_flux_balance_contracts.py", "native_flux_balance_storage.py",
    "native_flux_balance_cobra_glpk.py", "native_flux_balance_driver.py",
    "communication.py", "launch_instructions.py",
}


class PreparationFailure(ValueError):
    def __init__(self, code, field):
        super().__init__(code + ":" + field)
        self.code, self.field = code, field


def _require(condition, code, field):
    if not condition:
        raise PreparationFailure(code, field)


def _rows(value, field):
    _require(type(value) is list and value, "selected_pins_missing", field)
    result, by_path = [], {}
    for index, row in enumerate(value):
        row = validate_flux_balance_record("FilePin", row)
        _require(row["path"] not in by_path, "duplicate_selected_pin", field + "/" + str(index))
        by_path[row["path"]] = row
        result.append(row)
    return result


def _verify(rows):
    observations = []
    for row in rows:
        try:
            actual = file_pin(row["path"])
            observations.append({"selected": row, "observed": actual,
                "state": "unchanged" if actual == row else "changed", "error": None})
        except (OSError, ValueError) as error:
            observations.append({"selected": row, "observed": None,
                "state": "unavailable", "error": type(error).__name__ + ":" + str(error)})
    return observations


def _verified(rows, *, destination, name, receipt):
    observed = _verify(rows)
    path = destination / name
    immutable_json(path, observed)
    receipt["verified_inputs"].append(file_pin(path))
    _require(all(row["state"] == "unchanged" for row in observed),
        "selected_file_unavailable_or_changed", name)


def _join(rows):
    by_path = {}
    for row in rows:
        prior = by_path.get(row["path"])
        _require(prior is None or prior == row, "conflicting_selected_pin", row["path"])
        by_path[row["path"]] = row
    return list(by_path.values())


# This executes once under the selected interpreter, with no site processing.
# It observes import dependencies, explicitly selects actually mapped additional
# native files for this NEW descriptor, then uses the real unmodified verifier.
_PROBE = r'''
import json
from pathlib import Path
import sys

report_path, candidate_path, selected_path = map(Path, sys.argv[1:])
report = {"version": "fba_software_import_probe_v1", "ready": False,
    "model_load_calls": 0, "model_optimize_calls": 0, "failure": None,
    "imported_files": [], "executable_mappings": [], "additional_native_files": [],
    "python": sys.executable, "python_version": sys.version}
try:
    import cobra
    def forbidden_model_load(*args, **kwargs):
        report["model_load_calls"] += 1
        raise AssertionError("software_preparation_must_not_load_a_model")
    def forbidden_optimize(*args, **kwargs):
        report["model_optimize_calls"] += 1
        raise AssertionError("software_preparation_must_not_optimize")
    cobra.Model.optimize = forbidden_optimize
    cobra.io.load_json_model = forbidden_model_load
    cobra.io.read_sbml_model = forbidden_model_load
    import optlang.glpk_interface
    import swiglpk
    import libsbml
    from gene_annotation_episode import native_flux_balance_driver as driver
    from gene_annotation_episode.native_flux_balance_contracts import validate_flux_balance_software
    from gene_annotation_episode.native_flux_balance_storage import file_pin, immutable_json, read_json
    software = read_json(candidate_path)
    known = {row["path"] for row in [software["python"], *software["implementation_files"],
        *software["runtime_files"], *software["solver_runtime_files"]]}
    mapped = set()
    for line in Path("/proc/self/maps").read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) == 6 and fields[5].startswith("/") and "x" in fields[1]:
            mapped.add(str(Path(fields[5]).resolve(strict=True)))
    report["executable_mappings"] = [file_pin(path) for path in sorted(mapped)]
    report["additional_native_files"] = [row for row in report["executable_mappings"]
        if row["path"] not in known]
    software["solver_runtime_files"].extend(report["additional_native_files"])
    validate_flux_balance_software(software)
    report["verified_distributions"] = driver._verify_software(software, native_loaded=True)
    report["imported_files"] = sorted({str(Path(module.__file__).resolve(strict=True))
        for module in list(sys.modules.values()) if getattr(module, "__file__", None)
        and Path(module.__file__).is_file()})
    if report["model_load_calls"] or report["model_optimize_calls"]:
        raise AssertionError("scientific_execution_during_software_preparation")
    immutable_json(selected_path, software)
    report["ready"] = True
except BaseException as error:
    report["failure"] = {"class": type(error).__name__, "message": str(error)}
finally:
    with report_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")
raise SystemExit(0 if report["ready"] else 2)
'''


def prepare_selected_flux_balance_software(*, source_root, basis_attempt, destination):
    """Return an inspectable preparation receipt; readiness requires real guards.

    Selection is explicit and verification-only. All unsuccessful fresh
    preparations retain their receipt and partial files without software.json.
    An existing destination is rejected before changing any of its contents.
    """
    source_root = Path(path_value(str(source_root), absolute=True))
    basis_attempt = Path(path_value(str(basis_attempt), absolute=True))
    destination = Path(path_value(str(destination), absolute=True))
    directory(destination.parent)
    destination.mkdir(mode=0o700, exist_ok=False)
    receipt = {"version": VERSION, "source_root": str(source_root),
        "basis_attempt": str(basis_attempt), "destination": str(destination),
        "ready": False, "basis_records": [], "source_relocations_file": None,
        "verified_inputs": [], "import_probe_file": None, "software_file": None,
        "failures": [], "model_load_calls": 0, "model_optimize_calls": 0}
    try:
        directory(source_root)
        directory(basis_attempt)
        documents = {}
        for name in ("selected_request.json", "source_pins_before.json",
                "stdlib_pins_before.json", "dependency_pins_before.json",
                "binary_pins_before.json", "native_library_pins_before.json"):
            documents[name] = read_json(basis_attempt / name)
            receipt["basis_records"].append(file_pin(basis_attempt / name))
        declared = _rows(documents["source_pins_before.json"], "/source_pins")
        source_pins, relative_sources = [], []
        for row in declared:
            path = Path(row["path"])
            _require(path.is_relative_to(basis_attempt / "source_snapshot"),
                "source_pin_outside_basis", row["path"])
            relative = path.relative_to(basis_attempt / "source_snapshot")
            if relative.parts[0] in ("gene_annotation_episode", "method_loop"):
                source_pins.append({**row, "path": str(source_root / relative)})
                relative_sources.append(relative)
        selected_names = {str(path) for path in relative_sources}
        _require({"gene_annotation_episode/" + name for name in REQUIRED} <= selected_names,
            "current_implementation_closure_incomplete", "/source_pins")
        _verified(source_pins, destination=destination, name="source-verification.json", receipt=receipt)
        module_root = destination / "modules"
        source_relocations, implementation = [], []
        for original, relative in zip(source_pins, relative_sources, strict=True):
            copied = module_root / relative
            retained = retain_input(original["path"], copied, max_bytes=4294967296)
            _require(retained == {key: original[key] for key in ("sha256", "size_bytes")},
                "source_changed_during_copy", original["path"])
            new_pin = file_pin(copied)
            implementation.append(new_pin)
            source_relocations.append({"original": original, "selected": new_pin})
        immutable_json(destination / "source-relocations.json", source_relocations)
        receipt["source_relocations_file"] = file_pin(destination / "source-relocations.json")
        request = documents["selected_request.json"]
        _require(request["policy"] == {"memory_bytes": 21474836480,
            "scratch_bytes": 4294967296, "wall_seconds": None} and request["swap_bytes"] == 0,
            "basis_allocation_mismatch", "/selected_request/policy")
        selected_python = str(basis_attempt / "runtime/bin/python")
        _require(request["argv"][0] == selected_python
            and request["environment"]["PYTHONHOME"] == str(basis_attempt / "runtime")
            and request["environment"]["PYTHONPATH"].split(os.pathsep) == [
                str(basis_attempt / "source_snapshot"), str(basis_attempt / "dependencies")],
            "basis_runtime_selection_mismatch", "/selected_request")
        binary = _rows(documents["binary_pins_before.json"], "/binary_pins")
        python = next((row for row in binary if row["path"] == selected_python), None)
        _require(python is not None, "selected_interpreter_pin_missing", "/binary_pins")
        _require(str(Path(sys.executable).resolve()) == selected_python,
            "preparation_requires_selected_basis_interpreter", "/python")
        runtime = _join([*_rows(documents["stdlib_pins_before.json"], "/stdlib_pins"),
            *_rows(documents["dependency_pins_before.json"], "/dependency_pins"),
            *[row for row in binary if row != python]])
        native = _rows(documents["native_library_pins_before.json"], "/native_pins")
        _verified(_join([python, *runtime, *native]), destination=destination,
            name="runtime-verification.json", receipt=receipt)
        known = {row["path"] for row in [python, *implementation, *runtime]}
        native = [row for row in native if row["path"] not in known]
        distributions = sorted(({"name": row.metadata["Name"], "version": row.version}
            for row in importlib.metadata.distributions(path=[str(basis_attempt / "dependencies")])),
            key=lambda row: row["name"].lower())
        software = {"version": "fba_software_v1", "python": python,
            "python_version": sys.version, "python_home": str(basis_attempt / "runtime"),
            "module_root": str(module_root), "dependency_roots": [str(basis_attempt / "dependencies")],
            "implementation_files": implementation, "runtime_files": runtime,
            "solver_runtime_files": native, "distributions": distributions,
            "solver_interface": "optlang.glpk_interface"}
        validate_flux_balance_software(software)
        immutable_json(destination / "candidate-software.json", software)
        probe_root = destination / "import-probe"
        directory(probe_root, create=True)
        environment = flux_balance_environment(software,
            attempt_directory=str(probe_root / "flux-balance-attempt"), lifecycle_directory=str(probe_root))
        for path in (probe_root / "flux-balance-attempt/cache/pip", probe_root / "tmp"):
            directory(path, create=True)
        probe_path = destination / "import-probe.json"
        checked_path = destination / "verified-software.json"
        completed = subprocess.run([selected_python, "-B", "-S", "-c", _PROBE,
            str(probe_path), str(destination / "candidate-software.json"), str(checked_path)],
            cwd=probe_root, env=environment, capture_output=True, check=False)
        immutable_bytes(destination / "import-probe.stdout", completed.stdout)
        immutable_bytes(destination / "import-probe.stderr", completed.stderr)
        _require(probe_path.is_file(), "import_probe_report_missing", "/probe")
        observed = read_json(probe_path)
        probe_path.chmod(0o444)
        receipt["import_probe_file"] = file_pin(probe_path)
        receipt["model_load_calls"] = observed["model_load_calls"]
        receipt["model_optimize_calls"] = observed["model_optimize_calls"]
        _require(completed.returncode == 0 and observed["ready"] is True,
            "selected_software_import_probe_failed", "/probe")
        selected = validate_flux_balance_software(read_json(checked_path))
        _verified([selected["python"], *selected["implementation_files"], *selected["runtime_files"],
            *selected["solver_runtime_files"]], destination=destination,
            name="final-verification.json", receipt=receipt)
        _require(not receipt["model_load_calls"] and not receipt["model_optimize_calls"],
            "scientific_work_during_preparation", "/probe")
        immutable_json(destination / "software.json", selected)
        receipt["software_file"] = file_pin(destination / "software.json")
        receipt["ready"] = True
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as error:
        receipt["failures"].append({"code": getattr(error, "code", type(error).__name__),
            "field": getattr(error, "field", None), "message": str(error)})
    immutable_json(destination / "preparation-receipt.json", receipt)
    return deepcopy(receipt)
