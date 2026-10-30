"""Retain original FBA bytes independently; the caller owns execution authority."""
from copy import deepcopy

from .execution_contracts import digest
from .flux_balance_native_capture_contracts import (
    CONTROL_FORMATS, _artifact_reference, _file, _issue, _original_plan, _prior_inputs, _require,
    _selected_prior_files, validate_flux_balance_native_capture,
)
from .native_file_capture import (
    NativeFileCaptureError, _metadata, capture_native_file, retained_native_file,
)
from .native_flux_balance_contracts import (
    OWNER_FILENAME, STARTED_FILENAME, ENVIRONMENT_FILENAME,
)

__all__ = ["capture_flux_balance_native_files"]

_CONTROL_PATHS = {"owner": OWNER_FILENAME, "started": STARTED_FILENAME,
                  "environment": ENVIRONMENT_FILENAME}


def _failure_code(error):
    if error.code in {"capture_file_unavailable", "retained_artifact_unavailable"}:
        return "artifact_missing"
    if error.code == "retained_artifact_mismatch":
        return "artifact_identity_conflict"
    # Invalid primitive identities/declarations indicate a programming error.
    raise error


def capture_flux_balance_native_files(store, *, original_plan: dict,
        source_action_receipt_ref: str, writer_closure_receipt_ref: str,
        input_binding_file: dict, prior_sources: list[dict], driver_started: bool | None) -> dict:
    """Capture actual files, keeping native siblings after located I/O failures.

    The caller authenticates the original selected start and closed writer first.
    Metadata checks here establish neither receipt authority nor scientific success.
    """
    plan = _original_plan(original_plan)
    _artifact_reference(source_action_receipt_ref, "/source_action_receipt_ref")
    _artifact_reference(writer_closure_receipt_ref, "/writer_closure_receipt_ref")
    binding = _file(input_binding_file, "/input_binding_file")
    _require(binding["format"] == "flux_balance_input_binding_receipt_v1", "input_binding_format_invalid")
    _require(driver_started is None or type(driver_started) is bool, "driver_started_invalid")
    # Finish all selection validation before opening any producer file.
    supplied_priors = _prior_inputs(prior_sources, plan)
    failures = []
    for field, reference, file in (
        ("/source_action_receipt_ref", source_action_receipt_ref, None),
        ("/writer_closure_receipt_ref", writer_closure_receipt_ref, None),
        ("/input_binding_file", binding["artifact_ref"], binding),
    ):
        try:
            metadata = _metadata(store, reference)
            if file is not None and (metadata["sha256"] != file["sha256"] or metadata["size"] != file["size_bytes"]):
                failures.append(_issue("artifact_identity_conflict", field))
        except NativeFileCaptureError as error:
            failures.append(_issue(_failure_code(error), field))

    def capture(relative_path, format_, field, *, missing_required=True):
        try:
            file = capture_native_file(store, directory=plan["attempt_directory"],
                                       relative_path=relative_path, format=format_)
            return {"file": file, "path": str(retained_native_file(store, file))}
        except NativeFileCaptureError as error:
            code = _failure_code(error)
            if code != "artifact_missing" or missing_required:
                failures.append(_issue(code, field))
            return None

    files = [{**declaration, "retained": capture(declaration["relative_path"], declaration["format"],
              "/files/" + declaration["role"])} for declaration in plan["outputs"]]
    controls = {}
    for role, relative_path in _CONTROL_PATHS.items():
        required = driver_started is True if role in {"owner", "started"} else plan["version"] == "flux_balance_run_plan_v2"
        controls[role] = capture(relative_path, CONTROL_FORMATS[role], "/controls/" + role,
                                 missing_required=required)
    if plan["version"] == "flux_balance_run_plan_v1" and controls["environment"] is not None:
        failures.append(_issue("artifact_identity_conflict", "/controls/environment", controls["environment"]["file"]))
    priors = []
    selected = _selected_prior_files(plan)
    for index, file in enumerate(selected):
        row = next((row for row in supplied_priors if row["file"] == file), None)
        field = f"/prior_sources/{index}"
        if row is None:
            failures.append(_issue("artifact_missing", field))
            continue
        try:
            actual_path = str(retained_native_file(store, row["file"]))
            if actual_path != row["path"]:
                failures.append(_issue("artifact_identity_conflict", field))
                continue
        except NativeFileCaptureError as error:
            failures.append(_issue(_failure_code(error), field))
            continue
        priors.append(deepcopy(row))
    return validate_flux_balance_native_capture({"version": "flux_balance_native_capture_v1",
        "original_plan_sha256": digest(plan), "files": files, "controls": controls,
        "source_action_receipt_ref": source_action_receipt_ref,
        "writer_closure_receipt_ref": writer_closure_receipt_ref,
        "input_binding_file": binding, "prior_sources": priors,
        "driver_started": driver_started, "failures": failures}, original_plan=plan)
