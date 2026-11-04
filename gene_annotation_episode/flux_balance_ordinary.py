"""Fixed ordinary FBA compilation/execution ports, without episode authority.

The caller authenticates and locks its actual selected action, resolves received
inputs and freezes their existing FBA receipt before dispatch. These ports own
no commissions, publication, receipt grants, solver mathematics or decisions.
"""
from copy import deepcopy
from pathlib import Path

from . import native_lifecycle as native
from .acquisition import AcquisitionError
from .execution_contracts import canonical, checked
from .flux_balance_contracts import validate_flux_balance_record
from .flux_balance_request_binding import _files, scientific_request_schema
from .flux_balance_worker_contracts import validate_flux_balance_worker_plan
from .molecular_measurement_tools import MolecularOperationUnpublished
from .native_flux_balance_bindings import validate_flux_balance_bindings
from .native_flux_balance_contracts import (ATTEMPT_DIRECTORY_NAME, DRIVER_MODULE,
    RUN_PLAN_FILENAME, SOURCE_FUNCTION_SHA256, STARTED_FILENAME, flux_balance_environment,
    path_value, validate_flux_balance_requested_job, validate_flux_balance_software)
from .native_flux_balance_local import prepare_selected_local_flux_balance, local_flux_balance_plan
from .native_flux_balance_preparation import prepare_flux_balance_result_worker


EXECUTION_VERSION = "ordinary_flux_balance_execution_v1"
SELECTION_VERSION = "ordinary_flux_balance_selection_v1"


def _require(condition, code):
    if not condition:
        raise ValueError("ordinary_fba_" + code)


def compile_flux_balance_requested_job(scientific_request, *, binding, resolved_files, lifecycle_directory):
    """Compile only explicitly resolved values; inspect no Store or File bytes.

    Each resolved row has exactly selection/file/path. Selection is the original
    FileSelection, file is the existing FBA File descriptor, and path is the
    caller-resolved canonical artifact path. This supplies no authority to read.
    """
    request = checked(scientific_request, scientific_request_schema(), "ordinary_fba_request_invalid")
    selected, = validate_flux_balance_bindings([binding])
    _require(type(resolved_files) is list, "resolved_files_invalid")
    expected = {canonical(selection): selection for selection in _files(request)}
    resolved = {}
    for row in resolved_files:
        _require(type(row) is dict and set(row) == {"selection", "file", "path"}, "resolved_files_invalid")
        key = canonical(row["selection"])
        _require(key in expected, "unselected_file")
        file = validate_flux_balance_record("File", row["file"])
        path = str(path_value(row["path"], absolute=True))
        _require(file["artifact_ref"] == "artifact_" + file["sha256"]
            and file["format"] == expected[key]["format"], "resolved_file_identity_conflict")
        normalized = {"file": file, "path": path}
        _require(key not in resolved or canonical(resolved[key]) == canonical(normalized), "resolved_file_conflict")
        resolved[key] = normalized
    _require(set(resolved) == set(expected), "resolved_file_missing")

    def file_for(selection):
        return resolved[canonical(selection)]["file"]

    def bound(value):
        source = value.get("source")
        return validate_flux_balance_record("Bound", {"kind": value["kind"], "value": value["value"],
            "native_token": value.get("native_token"), "float_hex": value.get("float_hex"),
            "source": None if source is None else {"file": file_for(source["file"]), "pointer": source["pointer"]}})

    model = request["model_input"]
    selected_model = resolved[canonical(model["file"])]
    file = selected_model["file"]
    _require(file["format"] in selected["model_formats"], "model_format_not_bound")
    software = selected["software"]
    lifecycle = str(path_value(lifecycle_directory, absolute=True))
    job = {"version": "native_flux_balance_job_v1", "operation": request["operation"], "mode": request["mode"],
        "source_alias": "biomni.tool.systems_biology.perform_flux_balance_analysis",
        "model_input": {"file": {"path": selected_model["path"], **{key: file[key] for key in ("sha256", "size_bytes")}},
            "artifact_ref": file["artifact_ref"], "format": file["format"],
            "original_loader_selection": model["original_loader_selection"],
            "repository_identifier": model["repository_identifier"],
            "acquisition_receipt_file": None if model["acquisition_receipt_file"] is None else file_for(model["acquisition_receipt_file"])},
        "constraints": None if request["constraints"] is None else [{"reaction_id": row["reaction_id"],
            "lower": bound(row["lower"]), "upper": bound(row["upper"])} for row in request["constraints"]],
        "objective": deepcopy(request["objective"]), "solver_options": deepcopy(request["solver_options"]),
        "software": software, "output_prefix": "fba-output", "flux_output_name": "fluxes.csv",
        "source_function_sha256": SOURCE_FUNCTION_SHA256}
    return validate_flux_balance_requested_job({"argv": [software["python"]["path"], "-B", "-S", "-m",
        DRIVER_MODULE, RUN_PLAN_FILENAME], "environment": flux_balance_environment(software,
            attempt_directory=str(Path(lifecycle) / ATTEMPT_DIRECTORY_NAME), lifecycle_directory=lifecycle),
        "native_flux_balance": job})


def run_selected_flux_balance_native(compiled_selection, operation_key, *, run_id, episode_id,
        root, policy, input_binding_receipt, input_binding_file, cancel_event=None):
    """Run/collect one original solve handle under the caller's actual lock.

    Terminal operational failures remain original observations. An unconfirmed
    original attempt stays unpublished; it is never replaced or counted as zero
    optimizations. Scientific solve counts belong solely to retained driver data.
    """
    _require(type(compiled_selection) is dict and compiled_selection.get("version") == SELECTION_VERSION
        and compiled_selection.get("mode") == "solve", "selected_solve_required")
    handle = prepare_selected_local_flux_balance(compiled_selection, operation_key,
        run_id=run_id, episode_id=episode_id, root=root, policy=policy,
        input_binding_receipt=input_binding_receipt, input_binding_file=input_binding_file)
    plan = local_flux_balance_plan(compiled_selection, str(handle.path))
    result, failure = None, None
    try:
        view = native.status(handle)
        if view["terminal"] and view["quiescent"]:
            result = native.collect(handle)
        else:
            native.resume_start(handle, cancel_event=cancel_event)
            result = native.wait_job(handle, cancel_event=cancel_event)
    except AcquisitionError as error:
        view = native.status(handle)
        if not (view["terminal"] and view["quiescent"]):
            raise MolecularOperationUnpublished("ordinary_fba_original_attempt_unconfirmed") from error
        failure = {"code": error.code, "phase": error.phase,
            "diagnostic": deepcopy(error.diagnostic), "operational": deepcopy(error.operational)}
    view = native.status(handle)
    if not (view["terminal"] and view["quiescent"]):
        raise MolecularOperationUnpublished("ordinary_fba_original_attempt_unconfirmed")
    _require(canonical(local_flux_balance_plan(compiled_selection, str(handle.path))) == canonical(plan),
        "original_plan_conflict")
    metadata = deepcopy(view["metadata"])
    code = result.returncode if result is not None else metadata.get("native_returncode")
    _require(code is None or type(code) is int, "native_returncode_invalid")
    return {"version": EXECUTION_VERSION, "plan": plan, "handle": handle.read(),
        "terminal": True, "quiescent": True, "returncode": code, "metadata": metadata,
        "failure": failure, "driver_started": True if (Path(plan["attempt_directory"]) / STARTED_FILENAME).is_file() else None}


def run_selected_flux_balance_result_worker(store, *, plan, software, policy):
    """Use explicit software for the existing finite native/saved result worker.

    The caller keeps Store access on its owning thread. The returned capture is
    unchanged: no projection, sheet, calculator or publication runs in this host.
    """
    plan = validate_flux_balance_worker_plan(plan)
    software = validate_flux_balance_software(software)
    if plan["mode"] == "native_result":
        _require(canonical(plan["original_plan"]["requested_job"]["native_flux_balance"]["software"]) == canonical(software),
            "result_software_conflict")
    return prepare_flux_balance_result_worker(store, plan=plan, policy=policy, software=software)


__all__ = ["EXECUTION_VERSION", "SELECTION_VERSION", "compile_flux_balance_requested_job",
    "run_selected_flux_balance_native", "run_selected_flux_balance_result_worker"]
