"""Finite private selection of stored molecular results or one saved calculation.

No native source/helper is invoked. An output digest declares produced bytes;
the result owner must independently retain them before typed publication.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

from .execution_contracts import canonical, digest
from .molecular_sequence_result_contracts import (
    FILE_ROLES, MODES, OUTPUTS, RESULT_VERSION, SCHEMAS, empty_file_state, failure,
    require, select_stored_molecular_sequence_values,
    validate_molecular_sequence_result_worker_plan, validate_molecular_sequence_result_worker_result,
    SUPPLIED_PLAN_VERSION, SUPPLIED_RESULT_VERSION, SUPPLIED_OUTPUTS, SUPPLIED_PROFILE,
    supplied_failure, validate_supplied_worker_plan,
)
from .native_flux_balance_storage import file_pin, immutable_bytes, read_bytes


def _json(raw):
    from .molecular_sequence_driver import _json as decode
    return decode(raw)


def _write(path, value):
    immutable_bytes(path, (canonical(value) + "\n").encode())


def _pinned(pin):
    observed = file_pin(pin["path"])
    require(observed == pin, "molecular_sequence_worker_input_identity_conflict")
    return read_bytes(pin["path"])


def _load_inputs(plan, failures):
    documents = {role: None for role in FILE_ROLES}
    sources = deepcopy(plan["source_files"])
    for row in plan["inputs"]:
        role, identity = row["role"], row["file"]
        try:
            raw = _pinned(dict(path=row["path"], **{k: identity[k] for k in ("sha256", "size_bytes")}))
        except (OSError, ValueError):
            issue = failure("artifact_identity_conflict", "load", role=role, source_ref=identity["artifact_ref"])
            failures.append(issue)
            sources[role] = empty_file_state("identity_conflict", declared=sources[role]["declared"], issue=issue)
            continue
        if role in ("sheet", "components"):
            try:
                document = _json(raw)
                expected = SCHEMAS[plan["selector"]["operation"]][0 if role == "sheet" else 1]
                require(type(document) is dict and (document.get("schema") == expected if role == "sheet" else document.get("schema") in expected))
                documents[role] = document
            except (ValueError, TypeError, KeyError, UnicodeError):
                failures.append(failure("schema_invalid", "load", role=role, source_ref=identity["artifact_ref"]))
    return documents, sources


def _calculate(sheet, operation):
    # The existing dispatch selects the existing scientific authority once.
    # Importing this finite dispatch does not invoke a native function.
    from .molecular_sequence_driver import _calculate as calculate
    return calculate(sheet, operation)


def _software(plan):
    software = plan["software"]
    if software is None:
        return {"state": "not_requested", "imported_files": [], "qualification": "engineering_control_without_selected_worker_deployment"}
    from .molecular_sequence_native import _manifest, _imports
    require(str(Path(sys.executable).resolve()) == software["python"]["path"] and str(Path(sys.prefix).resolve()) == software["python_home"]
        and sys.version == software["python_version"], "molecular_sequence_worker_runtime_conflict")
    require(all(os.environ.get(k) == v for k, v in plan["selected_environment"].items()), "molecular_sequence_worker_environment_conflict")
    index, _ = _manifest(software)
    require(index.get(software["python"]["path"]) == software["python"])
    for selected in index.values(): require(file_pin(selected["path"]) == selected, "molecular_sequence_worker_software_pin_conflict")
    imported = _imports(index, [Path(software["python_home"]), *map(Path, software["import_roots"])], Path(__file__).resolve())
    return {"state": "verified", "imported_files": imported, "qualification": "actual_worker_imports_and_selected_file_stability_not_complete_process_environment_observation"}


def read_molecular_sequence_result_worker_replay(*, plan, output_directory):
    plan = validate_molecular_sequence_result_worker_plan(plan)
    root = Path(output_directory)
    result = validate_molecular_sequence_result_worker_result(_json(read_bytes(root / "result.json")))
    require(result["plan_sha256"] == digest(plan) and result["selector"] == plan["selector"], "molecular_sequence_worker_replay_conflict")
    for row in result["outputs"]:
        declaration = row["declaration"]
        path = root / declaration["relative_path"]
        if declaration["state"] == "absent":
            require(not path.exists() and not path.is_symlink(), "molecular_sequence_worker_replay_conflict")
        else:
            observed = file_pin(path)
            require(all(observed[k] == declaration[k] for k in ("sha256", "size_bytes")), "molecular_sequence_worker_replay_conflict")
    return result


def run_molecular_sequence_result_worker(*, plan_file, output_directory):
    """One pinned request; sealed replay never reopens historical input paths."""
    raw_plan = _pinned(plan_file)
    candidate = json.loads(raw_plan)
    if type(candidate) is dict and candidate.get("version") == SUPPLIED_PLAN_VERSION:
        return _run_supplied_worker(plan=validate_supplied_worker_plan(_strict_json(raw_plan)), output_directory=output_directory)
    plan = validate_molecular_sequence_result_worker_plan(_json(raw_plan))
    root = Path(output_directory)
    require(str(root) == plan["directory"] and root.is_absolute(), "molecular_sequence_worker_directory_conflict")
    if root.exists():
        require((root / "result.json").is_file(), "molecular_sequence_worker_uncertain")
        return read_molecular_sequence_result_worker_replay(plan=plan, output_directory=str(root))
    root.mkdir(mode=0o700)
    _write(root / "started.json", {"version": "molecular_sequence_result_worker_started_v1", "plan_sha256": digest(plan)})
    failures = []
    before = _software(plan)
    documents, sources = _load_inputs(plan, failures)
    selector, operation = plan["selector"], plan["selector"]["operation"]
    calculation = {"kind": "original_stored", "calculator_id": None,
        "source_sheet_file": sources["sheet"]["file"], "source_components_file": sources["components"]["file"],
        "components_schema": None if documents["components"] is None else documents["components"]["schema"]}
    calculation_call_count = 0
    if selector["mode"] == MODES[1]:
        calculation.update(kind="selected_saved_calculation", source_components_file=None, components_schema=None)
        documents["components"] = None
    if selector["mode"] == MODES[1] and documents["sheet"] is not None:
        try:
            calculation_call_count = 1
            components = _calculate(documents["sheet"], operation)
            _write(root / "calculated_components.json", components)
            observed = file_pin(root / "calculated_components.json")
            sources["components"] = empty_file_state("produced_unretained")
            sources["components"]["observed_identity"] = {k: observed[k] for k in ("sha256", "size_bytes")}
            documents["components"] = components
            calculation = dict(kind="selected_saved_calculation", calculator_id={
                "annotate_open_reading_frames": "orf_measurements.calculate_orf_components",
                "align_sequences": "primer_placement_measurements.calculate_primer_placement_components",
                "find_n_glycosylation_motifs": "glycosylation_measurements.calculate_glycosylation_components",
                "predict_o_glycosylation_hotspots": "glycosylation_measurements.calculate_glycosylation_components",
                "analyze_protease_kinetics": "protease_kinetics_measurements.calculate_protease_kinetics_components"}[operation],
                source_sheet_file=sources["sheet"]["file"], source_components_file=None, components_schema=components["schema"])
        except Exception as error:
            failures.append(failure("calculation_failed", "calculation", role="sheet",
                source_ref=selector["saved_sheet_ref"]))
            _write(root / "calculation-error.json", {"exception_type": type(error).__module__ + "." + type(error).__name__, "message": str(error)})
    projection = select_stored_molecular_sequence_values(operation=operation, sheet=documents["sheet"],
        components=documents["components"], selection=selector, source_files=sources,
        association=plan["association"], calculation=calculation)
    _write(root / "projection.json", projection)
    after = None
    try:
        after = _software(plan)
    except (OSError, ValueError):
        failures.append(failure("worker_failed", "worker"))
    _write(root / "diagnostics.json", {"version": "molecular_sequence_result_worker_diagnostics_v1",
        "native_invocation": "not_requested", "calculation": calculation, "software_before": before,
        "software_after": after, "calculation_call_count": calculation_call_count, "failures": failures})
    outputs = []
    for role in OUTPUTS:
        path = root / (role + ".json")
        actual = file_pin(path) if path.exists() else None
        outputs.append({"role": role, "declaration": {"relative_path": path.name, "format": "json",
            "state": "present" if actual is not None else "absent", "sha256": None if actual is None else actual["sha256"],
            "size_bytes": None if actual is None else actual["size_bytes"]}})
    result = validate_molecular_sequence_result_worker_result(dict(version=RESULT_VERSION, plan_sha256=digest(plan),
        selector=selector, outputs=outputs, failures=failures))
    _write(root / "result.json", result)
    return result


def _strict_json(raw):
    from .molecular_sequence_input_contracts import decode_molecular_sequence_input
    decoded = decode_molecular_sequence_input(raw, tag_key="version")
    require(decoded["state"] == "decoded", "molecular_sequence_supplied_json_invalid")
    return decoded["value"]


def _run_supplied_worker(*, plan, output_directory):
    """One selected pure calculation; this records no native producing attempt."""
    from .calibrated_signal_contracts import validate_calibrated_signal_sheet, validate_calibrated_signal_selection
    from .calibrated_signal_calculations import calculate_calibrated_signal_components
    root = Path(output_directory)
    require(root.is_absolute() and str(root) == plan["directory"], "molecular_sequence_worker_directory_conflict")
    if root.exists():
        require((root / "result.json").is_file(), "molecular_sequence_worker_uncertain")
        return read_molecular_sequence_result_worker_replay(plan=plan, output_directory=str(root))
    root.mkdir(mode=0o700)
    _write(root / "started.json", {"version": "molecular_sequence_supplied_worker_started_v1", "plan_sha256": digest(plan)})
    failures, before, after = [], None, None
    state, count = "not_started", 0
    selector = plan["selector"]
    try:
        before = _software(plan)
        raw = _pinned(dict(path=plan["input_path"], **{key: plan["input_file"][key] for key in ("sha256", "size_bytes")}))
        sheet = validate_calibrated_signal_sheet(_strict_json(raw))
        immutable_bytes(root / "sheet.json", raw)
        selection = validate_calibrated_signal_selection(selector["calculation_selection"], sheet)
    except (OSError, ValueError, TypeError, KeyError):
        failures.append(supplied_failure("input_invalid" if before is not None else "worker_failed", "load", role="sheet",
            source_ref=plan["input_file"]["artifact_ref"]))
    else:
        try:
            components = calculate_calibrated_signal_components(sheet, selection=selection)
        except Exception as error:
            # A completed exception records an invocation only if the actual
            # selected callable's frame is present. Intent alone proves none.
            trace = error.__traceback__
            observed = False
            while trace is not None:
                observed |= trace.tb_frame.f_code is calculate_calibrated_signal_components.__code__
                trace = trace.tb_next
            count, state = (1 if observed else None), "calculation_failed"
            failures.append(supplied_failure("calculation_failed", "calculation", role="sheet", source_ref=plan["input_file"]["artifact_ref"]))
            _write(root / "calculation-error.json", {"exception_type": type(error).__module__ + "." + type(error).__name__, "message": str(error)})
        else:
            count, state = 1, "completed"  # Actual selected call returned.
            try:
                _write(root / "calculated_components.json", components)
            except (OSError, ValueError):
                state = "worker_failed"
                failures.append(supplied_failure("retention_failed", "worker", role="components"))
    try:
        after = _software(plan)
    except (OSError, ValueError):
        failures.append(supplied_failure("worker_failed", "worker"))
    _write(root / "diagnostics.json", dict(version="molecular_sequence_supplied_worker_diagnostics_v1",
        operation=SUPPLIED_PROFILE["operation"], calculator_id=SUPPLIED_PROFILE["calculator_id"],
        selection=selector["calculation_selection"], calculation_state=state, calculation_call_count=count,
        native_invocation="not_requested", software_before=before, software_after=after, failures=failures))
    outputs = []
    for role in SUPPLIED_OUTPUTS:
        path = root / (role + ".json"); observed = file_pin(path) if path.exists() else None
        outputs.append(dict(role=role, declaration=dict(relative_path=path.name, format="json",
            state="present" if observed is not None else "absent", sha256=None if observed is None else observed["sha256"],
            size_bytes=None if observed is None else observed["size_bytes"])))
    result = validate_molecular_sequence_result_worker_result(dict(version=SUPPLIED_RESULT_VERSION, plan_sha256=digest(plan),
        selector=selector, outputs=outputs, failures=failures))
    _write(root / "result.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--size-bytes", required=True, type=int)
    parser.add_argument("--output-directory", required=True)
    args = parser.parse_args(argv)
    try:
        result = run_molecular_sequence_result_worker(plan_file={"path": args.plan_file, "sha256": args.sha256,
            "size_bytes": args.size_bytes}, output_directory=args.output_directory)
    except Exception as error:
        sys.stderr.write(json.dumps({"version": "molecular_sequence_result_worker_error_v1",
            "exception_type": type(error).__name__, "message": str(error)}) + "\n")
        return 1
    sys.stdout.write(json.dumps(result, allow_nan=False) + "\n")
    return int(bool(result["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
