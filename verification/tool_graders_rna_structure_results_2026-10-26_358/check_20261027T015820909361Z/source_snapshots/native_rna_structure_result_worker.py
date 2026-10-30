"""Bounded, Store-free RNA data population and saved-sheet calculation worker.

No native scientific library, network client or episode is invoked. The saved
route consumes only the exact retained sheet and explicit calculator parameters.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import sys

from .execution_contracts import canonical
from .native_rna_structure_acquisition import decode_json, require
from .practical_execution_state import _immutable, _read
from .rna_structure_contracts import (OPERATIONS, RNA_ISSUE_CODES, issue, validate_rna_input,
    validate_rna_sheet, validate_rna_parameters, validate_rna_effective_model_shape)
from .rna_structure_calculations import calculate_rna_feature_components, calculate_rna_prediction_components
from .rna_structure_result_views import merge_issues, project_rna_prepublication, validate_rna_structure_result_selector


def _bytes(path, sha, size=None):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == sha and (size is None or len(raw) == size), "rna_capture_digest_mismatch")
    return raw


def _error(error, *, stage, key, role=None):
    code = str(error) if str(error) in RNA_ISSUE_CODES else "rna_capture_unavailable" if isinstance(error, OSError) else "rna_invalid_native_schema"
    return issue(code, stage=stage, record_key=key, artifact_role=role)


def _finish(plan, *, sheet, sheet_raw, parameters, diagnostics, original_failures):
    directory, key = Path(plan["directory"]), plan["record_key"]
    directory.mkdir(parents=True, exist_ok=True)
    components = None
    if sheet is not None:
        try:
            calculate = calculate_rna_prediction_components if sheet["mode"] == "mfe_prediction" else calculate_rna_feature_components
            components = calculate(sheet, parameters=parameters)
        except ValueError as error:
            diagnostics["calculation_issues"].append(_error(error, stage="calculate", key=key))
    failures = merge_issues(original_failures, diagnostics["capture_failures"], diagnostics["parse_issues"],
        diagnostics["sheet_issues"], diagnostics["calculation_issues"])
    components_sha = None
    if components is not None:
        _immutable(directory / "components.json", components)
        components_sha = hashlib.sha256((canonical(components) + "\n").encode()).hexdigest()
        document, selection = project_rna_prepublication(sheet, components, selector=plan["selector"],
            components_sha256=components_sha, failures=failures)
        diagnostics["selection_issues"] = selection
    else:
        selection = []
        projection = plan["selector"]["projection"]
        if projection["family"] != "failure":
            choice = projection["rows"]
            indices = range(len(choice["record_keys"])) if "record_keys" in choice else [None]
            for i in indices:
                selection.append(issue("rna_requested_row_missing", stage="selection", record_key=key,
                    field="/selector/projection/rows" if i is None else f"/selector/projection/rows/record_keys/{i}", index=i))
        diagnostics["selection_issues"] = selection
        document = {"schema": "rna_structure_prepublication_v1", "record_key": key,
            "operation": plan["operation"], "mode": plan["mode"], "selector": plan["selector"],
            "sheet_schema": None if sheet is None else sheet["schema"], "components_sha256": None,
            "parameters": parameters, "population_count": None, "rows": [],
            "failures": merge_issues(failures, selection), "requested_cells_accounted_for": projection["family"] != "failure"}
    if sheet is not None:
        if sheet_raw is None:
            _immutable(directory / "sheet.json", sheet)
        else:
            require(sheet_raw == (canonical(sheet) + "\n").encode(), "rna_invalid_sheet_schema")
            _immutable(directory / "sheet.json", sheet)
            require((directory / "sheet.json").read_bytes() == sheet_raw, "rna_capture_digest_mismatch")
    _immutable(directory / "selected-rows.json", document)
    _immutable(directory / "diagnostics.json", diagnostics)
    result = {"version": "native_rna_structure_grading_worker_result_v1",
        "sheet_schema": None if sheet is None else sheet["schema"],
        "components_schema": None if components is None else components["schema"],
        "sheet_file": None if sheet is None else "sheet.json",
        "components_file": None if components is None else "components.json",
        "projected_rows_file": "selected-rows.json", "diagnostics_file": "diagnostics.json",
        "requested_cells_accounted_for": document["requested_cells_accounted_for"], "failures": document["failures"]}
    _immutable(directory / "worker-result.json", result)
    return result


def _diagnostics(key, capture):
    return {"schema": "rna_structure_grading_diagnostics_v1", "record_key": key,
        "capture_failures": deepcopy(capture), "parse_issues": [], "sheet_issues": [],
        "calculation_issues": [], "selection_issues": []}


def run_rna_structure_grading_worker(plan):
    from .rna_structure_native import parse_rna_native_record, populate_rna_feature_sheet, populate_rna_prediction_sheet
    require(set(plan) == {"version", "bundle", "bundle_artifact_ref", "artifacts", "selector", "directory", "capture_failures"}
        and plan["version"] == "native_rna_structure_grading_plan_v1", "rna_invalid_input_schema")
    bundle, files = plan["bundle"], {row["role"]: row for row in plan["artifacts"]}
    require(len(files) == len(plan["artifacts"]), "rna_input_identity_mismatch")
    key, mode = bundle["record_key"], bundle["mode"]
    selector = validate_rna_structure_result_selector(plan["selector"], mode=mode)
    require(selector["acquisition"] == "complete_bound_bundle", "rna_invalid_input_schema")
    parameters = validate_rna_parameters(bundle["requested_job"]["native_rna_structure"]["grading_parameters"])
    diagnostics = _diagnostics(key, plan["capture_failures"])
    original = model = None
    for role in ("input", "model"):
        if role not in files:
            continue
        try:
            row = files[role]
            value = decode_json(_bytes(row["path"], row["sha256"], row["size_bytes"]))
            if role == "input":
                original = validate_rna_input(value, mode=mode)
                require(original["record_key"] == key, "rna_input_identity_mismatch")
            else:
                model = validate_rna_effective_model_shape(value)
        except (ValueError, OSError) as error:
            if role == "input":
                original = None
            diagnostics["parse_issues"].append(_error(error, stage="parse", key=key, role=role))
    raw, native_format = None, "rna_native_record_json_v1"
    if "native_result" in files:
        row = files["native_result"]
        native_format = row["format"]
        try:
            raw = _bytes(row["path"], row["sha256"], row["size_bytes"])
        except (ValueError, OSError) as error:
            diagnostics["parse_issues"].append(_error(error, stage="parse", key=key, role="native_result"))
    options = {"expected_sequence": None if original is None else original["sequence"]} if native_format == "biomni_rna_structure_text_v0" else {}
    parsed = parse_rna_native_record(raw, format=native_format, expected_mode=mode, record_key=key, **options)
    diagnostics["parse_issues"].extend(parsed["issues"])
    # Effective settings and their retained parameter association must describe
    # the original requested model, never another successful native run. Losing
    # a present file is already a distinct capture qualification; compare the
    # saved expected manifest even when its bytes could not be acquired.
    native_model = None if parsed["record"] is None else parsed["record"]["model"]
    try:
        for candidate in (model, native_model):
            if candidate is None:
                continue
            require(candidate["selected"] == bundle["requested_job"]["native_rna_structure"]["model"], "rna_native_result_incompatible")
            parameter = candidate["parameter_artifact"]
            matches = [row for row in bundle["files"] if row["role"] == "effective_parameters"]
            require(len(matches) == 1 and matches[0]["state"] == "present" and all(
                parameter[field] == matches[0][field] for field in ("relative_path", "sha256", "size_bytes")), "rna_energy_structure_mismatch")
        require(model is None or native_model is None or model == native_model, "rna_native_result_incompatible")
    except ValueError as error:
        diagnostics["parse_issues"].append(_error(error, stage="parse", key=key, role="model"))
        parsed = {**parsed, "status": "invalid", "record": None}
        model = None
    parsed["issues"] = merge_issues(parsed["issues"], diagnostics["parse_issues"])
    sheet = None
    try:
        populate = populate_rna_prediction_sheet if mode == "mfe_prediction" else populate_rna_feature_sheet
        sheet = populate(parsed, record_key=key, original_input=original, model_metadata=model,
            subject_binding=None if original is None else original["subject_binding"])
        diagnostics["sheet_issues"] = deepcopy(sheet["issues"])
    except ValueError as error:
        diagnostics["sheet_issues"].append(_error(error, stage="parse", key=key))
    return _finish({**plan, "record_key": key, "operation": bundle["operation"], "mode": mode},
        sheet=sheet, sheet_raw=None, parameters=parameters, diagnostics=diagnostics, original_failures=bundle["failures"])


def run_saved_rna_structure_grading_worker(plan):
    require(set(plan) == {"version", "sheet_path", "sheet_sha256", "record_key", "operation", "mode", "parameters",
        "selector", "directory", "capture_failures"} and plan["version"] == "native_rna_structure_saved_grading_plan_v1",
        "rna_invalid_input_schema")
    key, mode = plan["record_key"], plan["mode"]
    selector = validate_rna_structure_result_selector(plan["selector"], mode=mode)
    parameters = validate_rna_parameters(plan["parameters"])
    require(selector["acquisition"] == "retained_sheet_only" and parameters == selector["parameters"] and
        plan["operation"] == OPERATIONS[mode], "rna_input_identity_mismatch")
    diagnostics = _diagnostics(key, plan["capture_failures"])
    sheet = raw = None
    try:
        raw = _bytes(plan["sheet_path"], plan["sheet_sha256"])
        sheet = validate_rna_sheet(decode_json(raw, canonical_bytes=True))
        require(all(sheet[field] == plan[field] for field in ("record_key", "operation", "mode")), "rna_input_identity_mismatch")
        diagnostics["sheet_issues"] = deepcopy(sheet["issues"])
    except (ValueError, OSError) as error:
        sheet = raw = None
        diagnostics["parse_issues"].append(_error(error, stage="parse", key=key))
    return _finish(plan, sheet=sheet, sheet_raw=raw, parameters=parameters,
        diagnostics=diagnostics, original_failures=[])


if __name__ == "__main__":
    plan = _read(Path(sys.argv[1]))
    (run_saved_rna_structure_grading_worker if plan.get("version") == "native_rna_structure_saved_grading_plan_v1"
        else run_rna_structure_grading_worker)(plan)
