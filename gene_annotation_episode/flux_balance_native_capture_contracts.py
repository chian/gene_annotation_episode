"""Closed FBA byte-custody handoff; no parsing, scoring or receipt authority."""
from copy import deepcopy
from pathlib import PurePosixPath
import re

from .execution_contracts import canonical, digest
from .flux_balance_contracts import validate_flux_balance_record
from .native_flux_balance_contracts import validate_flux_balance_run_plan

__all__ = ["validate_flux_balance_native_capture"]

CONTROL_FORMATS = {
    "owner": "flux_balance_owner_plan_v1",
    "started": "flux_balance_started_control_v1",
    "environment": "flux_balance_environment_observation_v1",
}
_KEYS = {"version", "original_plan_sha256", "files", "controls",
    "source_action_receipt_ref", "writer_closure_receipt_ref", "input_binding_file",
    "prior_sources", "driver_started", "failures"}
_REF = re.compile(r"artifact_[0-9a-f]{64}")


def _require(condition, code, field=""):
    if not condition:
        raise ValueError("fba_capture_" + code + (":" + field if field else ""))


def _original_plan(value):
    try:
        return validate_flux_balance_run_plan(value)
    except (ValueError, TypeError) as error:
        raise ValueError("fba_capture_original_plan_invalid") from error


def _artifact_reference(value, field):
    _require(type(value) is str and _REF.fullmatch(value) is not None, "reference_invalid", field)
    return value


def _file(value, field):
    try:
        result = validate_flux_balance_record("File", value)
    except (ValueError, TypeError) as error:
        raise ValueError("fba_capture_file_invalid:" + field) from error
    _artifact_reference(result["artifact_ref"], field)
    _require(result["artifact_ref"] == "artifact_" + result["sha256"], "file_invalid", field)
    return result


def _retained(value, field):
    _require(type(value) is dict and set(value) == {"file", "path"}, "retained_invalid", field)
    result = {"file": _file(value["file"], field + "/file"), "path": value["path"]}
    path = result["path"]
    _require(type(path) is str and path and not any(c in path for c in "\0\r\n\\"), "retained_path_invalid", field)
    parsed = PurePosixPath(path)
    sha = result["file"]["sha256"]
    _require(parsed.is_absolute() and str(parsed) == path and ".." not in parsed.parts
        and not path.startswith("//") and parsed.name == sha and parsed.parent.name == sha[:2]
        and parsed.parent.parent.name == "artifacts", "retained_path_invalid", field)
    return result


def _selected_prior_files(plan):
    job = plan["requested_job"]["native_flux_balance"]
    rows = []
    receipt = job["model_input"]["acquisition_receipt_file"]
    if receipt is not None:
        rows.append(_file(receipt, "/requested_job/native_flux_balance/model_input/acquisition_receipt_file"))
    for index, change in enumerate(job["constraints"] or []):
        for side in ("lower", "upper"):
            source = change[side]["source"]
            if type(source) is dict and "file" in source:
                rows.append(_file(source["file"], f"/requested_job/native_flux_balance/constraints/{index}/{side}/source/file"))
    result = []
    for row in rows:
        if row not in result:
            result.append(row)
    return result


def _prior_inputs(value, plan):
    _require(type(value) is list, "prior_sources_invalid", "/prior_sources")
    selected = _selected_prior_files(plan)
    rows, refs = [], set()
    for index, row in enumerate(value):
        retained = _retained(row, f"/prior_sources/{index}")
        _require(retained["file"] in selected, "prior_source_unselected", f"/prior_sources/{index}")
        reference = retained["file"]["artifact_ref"]
        _require(reference not in refs, "prior_source_duplicate_or_conflict", f"/prior_sources/{index}")
        refs.add(reference)
        rows.append(retained)
    return [next(row for row in rows if row["file"] == file) for file in selected
            if any(row["file"] == file for row in rows)]


def _issue(code, field, detail_file=None):
    return validate_flux_balance_record("Issue", {"code": code, "stage": "capture", "field": field,
        "detail_file": deepcopy(detail_file), "source_row_index": None, "reaction_position": None,
        "metabolite_position": None, "variable_position": None, "constraint_position": None})


def validate_flux_balance_native_capture(value: dict, *, original_plan: dict) -> dict:
    """Validate selected byte identities and shape without opening any artifact."""
    plan = _original_plan(original_plan)
    try:
        canonical(value)
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError("fba_capture_invalid") from error
    _require(type(value) is dict and set(value) == _KEYS
        and value["version"] == "flux_balance_native_capture_v1", "invalid")
    _require(value["original_plan_sha256"] == digest(plan), "original_plan_mismatch")
    _artifact_reference(value["source_action_receipt_ref"], "/source_action_receipt_ref")
    _artifact_reference(value["writer_closure_receipt_ref"], "/writer_closure_receipt_ref")
    binding = _file(value["input_binding_file"], "/input_binding_file")
    _require(binding["format"] == "flux_balance_input_binding_receipt_v1", "input_binding_format_invalid")
    _require(value["driver_started"] is None or type(value["driver_started"]) is bool, "driver_started_invalid")
    _require(type(value["files"]) is list and len(value["files"]) == len(plan["outputs"]), "files_invalid")
    for index, (row, declaration) in enumerate(zip(value["files"], plan["outputs"])):
        pointer = f"/files/{index}"
        _require(type(row) is dict and set(row) == {"role", "relative_path", "format", "retained"}
            and all(row[k] == declaration[k] for k in declaration), "output_declaration_mismatch", pointer)
        if row["retained"] is not None:
            retained = _retained(row["retained"], pointer + "/retained")
            _require(retained["file"]["format"] == row["format"], "output_format_mismatch", pointer)
    controls = value["controls"]
    _require(type(controls) is dict and set(controls) == set(CONTROL_FORMATS), "controls_invalid")
    for role, format_ in CONTROL_FORMATS.items():
        if controls[role] is not None:
            retained = _retained(controls[role], "/controls/" + role)
            _require(retained["file"]["format"] == format_, "control_format_mismatch", "/controls/" + role)
    priors = _prior_inputs(value["prior_sources"], plan)
    _require(priors == value["prior_sources"], "prior_source_order_mismatch")
    _require(type(value["failures"]) is list, "failures_invalid")
    verified_files = [row["retained"]["file"] for row in value["files"] if row["retained"] is not None]
    verified_files.extend(row["file"] for row in controls.values() if row is not None)
    verified_files.extend(row["file"] for row in priors)
    located_fields = {"/source_action_receipt_ref", "/writer_closure_receipt_ref", "/input_binding_file"}
    located_fields.update("/files/" + row["role"] for row in value["files"])
    located_fields.update("/controls/" + role for role in controls)
    located_fields.update(f"/prior_sources/{index}" for index, _ in enumerate(_selected_prior_files(plan)))
    for index, issue in enumerate(value["failures"]):
        try:
            checked = validate_flux_balance_record("Issue", issue)
        except (ValueError, TypeError) as error:
            raise ValueError(f"fba_capture_issue_invalid:/failures/{index}") from error
        _require(checked["stage"] == "capture", "issue_stage_invalid", f"/failures/{index}")
        _require(checked["field"] in located_fields, "issue_field_invalid", f"/failures/{index}")
        _require(all(checked[k] is None for k in ("source_row_index", "reaction_position", "metabolite_position",
            "variable_position", "constraint_position")), "issue_locator_invalid", f"/failures/{index}")
        _require(checked["detail_file"] is None or checked["detail_file"] in verified_files,
                 "issue_file_unverified", f"/failures/{index}")
    # An absent capture is qualified, never an invented zero or successful read.
    def qualified(field, codes=("artifact_missing", "artifact_identity_conflict")):
        return any(r["field"] == field and r["code"] in codes for r in value["failures"])
    for row in value["files"]:
        if row["retained"] is None:
            _require(qualified("/files/" + row["role"]), "missing_file_qualification", "/files/" + row["role"])
    for role in ("owner", "started"):
        if value["driver_started"] is True and controls[role] is None:
            _require(qualified("/controls/" + role), "missing_control_qualification", "/controls/" + role)
    if plan["version"] == "flux_balance_run_plan_v2" and controls["environment"] is None:
        _require(qualified("/controls/environment"), "missing_control_qualification", "/controls/environment")
    if plan["version"] == "flux_balance_run_plan_v1" and controls["environment"] is not None:
        _require(qualified("/controls/environment", ("artifact_identity_conflict",)), "unexpected_control_qualification")
    for index, file in enumerate(_selected_prior_files(plan)):
        if not any(row["file"] == file for row in priors):
            _require(qualified(f"/prior_sources/{index}"), "missing_prior_qualification", f"/prior_sources/{index}")
    return deepcopy(value)
