"""Closed finite FBA result-worker records, without I/O or scientific scoring."""
from copy import deepcopy
from pathlib import PurePosixPath
import re

from .execution_contracts import canonical
from .flux_balance_contracts import validate_flux_balance_record
from .flux_balance_native_capture_contracts import validate_flux_balance_native_capture
from .flux_balance_result_contracts import validate_fba_saved_sheet_reference
from .flux_balance_result_selection import validate_flux_balance_result_selector
from .native_flux_balance_contracts import path_value, validate_flux_balance_run_plan

__all__ = ["build_native_flux_balance_worker_plan", "build_saved_flux_balance_worker_plan",
    "validate_flux_balance_worker_plan", "validate_flux_balance_worker_result"]

PLAN_VERSION = "flux_balance_worker_plan_v1"
RESULT_VERSION = "flux_balance_worker_result_v1"
OUTPUTS = (("sheet", "sheet.json", "flux_balance_sheet_v1"),
    ("calculations", "calculations.json", "flux_balance_calculations_v1"),
    ("projection", "projection.json", "flux_balance_result_view_v1"),
    ("diagnostics", "diagnostics.json", "flux_balance_result_diagnostics_v1"))
EVIDENCE_ROLES = ("effective_model", "effective_problem", "solution", "native_log", "manifest")
_SHA = re.compile(r"[0-9a-f]{64}")


def _require(condition, code, field=""):
    if not condition:
        raise ValueError("fba_worker_" + code + ":" + field)


def _finite(value):
    # The shared validator rejects non-JSON containers, non-string keys and all
    # nonfinite numbers recursively, including inside otherwise raw records.
    canonical(value)
    def visit(item):
        _require(item is None or type(item) in (str, bool, int, float, list, dict), "invalid")
        if type(item) is dict:
            _require(all(type(k) is str for k in item), "invalid")
            for child in item.values():
                visit(child)
        elif type(item) is list:
            for child in item:
                visit(child)
    visit(value)


def _retained(value, field):
    _require(type(value) is dict and set(value) == {"file", "path"}, "retained_invalid", field)
    file = validate_fba_saved_sheet_reference(value["file"])
    path = path_value(value["path"], absolute=True)
    sha = file["sha256"]
    _require(path.name == sha and path.parent.name == sha[:2] and path.parent.parent.name == "artifacts",
        "retained_path_invalid", field + "/path")
    return {"file": file, "path": value["path"]}


def _overlap(left, right):
    left, right = PurePosixPath(left), PurePosixPath(right)
    return left == right or left in right.parents or right in left.parents


def _input_paths(value):
    if type(value) is dict:
        if "path" in value and type(value["path"]) is str and value["path"].startswith("/"):
            yield value["path"]
        for child in value.values():
            yield from _input_paths(child)
    elif type(value) is list:
        for child in value:
            yield from _input_paths(child)


def build_native_flux_balance_worker_plan(*, directory: str, original_plan: dict,
        capture: dict, selector: dict) -> dict:
    return validate_flux_balance_worker_plan({"version": PLAN_VERSION, "mode": "native_result",
        "directory": directory, "original_plan": original_plan, "capture": capture, "selector": selector})


def build_saved_flux_balance_worker_plan(*, directory: str, sheet: dict, selector: dict) -> dict:
    return validate_flux_balance_worker_plan({"version": PLAN_VERSION, "mode": "saved_sheet_recalculation",
        "directory": directory, "sheet": sheet, "selector": selector})


def validate_flux_balance_worker_plan(value: dict) -> dict:
    _finite(value)
    _require(type(value) is dict and value.get("version") == PLAN_VERSION
        and type(value.get("mode")) is str and value["mode"] in ("native_result", "saved_sheet_recalculation"), "plan_invalid")
    native = value["mode"] == "native_result"
    _require(set(value) == {"version", "mode", "directory", "selector"} |
        ({"original_plan", "capture"} if native else {"sheet"}), "plan_invalid")
    path_value(value["directory"], absolute=True)
    selector = validate_flux_balance_result_selector(value["selector"])
    _require(selector["mode"] == value["mode"], "mode_mismatch", "/selector/mode")
    if native:
        original = validate_flux_balance_run_plan(value["original_plan"])
        validate_flux_balance_native_capture(value["capture"], original_plan=original)
        inputs = [original["attempt_directory"], *_input_paths(original), *_input_paths(value["capture"])]
    else:
        retained = _retained(value["sheet"], "/sheet")
        _require(retained["file"] == selector["saved_sheet_file"], "saved_sheet_mismatch", "/sheet/file")
        inputs = [retained["path"]]
    _require(not any(_overlap(value["directory"], p) for p in inputs), "directory_overlap", "/directory")
    return deepcopy(value)


def validate_flux_balance_worker_result(value: dict) -> dict:
    _finite(value)
    _require(type(value) is dict and set(value) == {"version", "mode", "plan_sha256", "selector", "outputs",
        "failures", "native_association", "new_attempt_evidence_roles", "requested_projection_valid"}, "result_invalid")
    _require(value["version"] == RESULT_VERSION and type(value["mode"]) is str
        and value["mode"] in ("native_result", "saved_sheet_recalculation")
        and type(value["plan_sha256"]) is str and _SHA.fullmatch(value["plan_sha256"]) is not None, "result_invalid")
    selector = validate_flux_balance_result_selector(value["selector"])
    _require(selector["mode"] == value["mode"], "mode_mismatch")
    _require(type(value["native_association"]) is str and value["native_association"] in
        ("verified", "unavailable", "conflict", "not_applicable"), "association_invalid")
    roles = value["new_attempt_evidence_roles"]
    _require(type(roles) is list and all(type(r) is str for r in roles)
        and roles == [r for r in EVIDENCE_ROLES if r in roles], "evidence_roles_invalid")
    if value["mode"] == "saved_sheet_recalculation":
        _require(value["native_association"] == "not_applicable" and not roles, "saved_association_invalid")
    else:
        _require(value["native_association"] != "not_applicable", "association_invalid")
    _require(type(value["outputs"]) is list and len(value["outputs"]) == len(OUTPUTS), "outputs_invalid")
    for row, (role, name, format_) in zip(value["outputs"], OUTPUTS):
        _require(type(row) is dict and set(row) == {"role", "declaration"} and row["role"] == role, "outputs_invalid")
        declaration = row["declaration"]
        _require(type(declaration) is dict and set(declaration) == {"relative_path", "format", "state", "sha256", "size_bytes"}
            and declaration["relative_path"] == name and declaration["format"] == format_
            and type(declaration["state"]) is str and declaration["state"] in ("present", "absent"), "outputs_invalid")
        if declaration["state"] == "present":
            validate_flux_balance_record("File", {"artifact_ref": "artifact_" + str(declaration["sha256"]),
                **{k: declaration[k] for k in ("sha256", "size_bytes", "format")}})
        else:
            _require(declaration["sha256"] is None and declaration["size_bytes"] is None, "absent_pin_invalid")
    _require(type(value["requested_projection_valid"]) is bool and value["requested_projection_valid"] ==
        (value["outputs"][2]["declaration"]["state"] == "present"), "projection_flag_invalid")
    _require(type(value["failures"]) is list, "failures_invalid")
    for issue in value["failures"]:
        checked = validate_flux_balance_record("Issue", issue)
        _require(checked["stage"] in ("capture", "parse", "project"), "issue_stage_invalid")
    return deepcopy(value)
