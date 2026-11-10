"""Byte custody of every original ATAC output occurrence after writer closure.

The caller authenticates the original selected action and terminal/quiescent
writer. This function does not poll, launch, calculate, or confer return access.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from . import native_file_capture as capture
from .terminal_native_file_capture import capture_execution_file, capture_execution_declarations
from .native_atac_differential_contracts import (
    STEP_KEYS, canonical, failure, path_value, require, unique_failures,
    validate_atac_record, validate_atac_run_plan, validate_atac_command_seal, validate_atac_native_bundle,
)
from .native_atac_differential_driver import decode_json


def _retained(store, identity):
    return {"file": deepcopy(identity), "path": str(capture.retained_native_file(store, identity))}


def _problem(spec, index, code, *, artifact_ref=None, requirement="complete_native_output"):
    return failure(code, "capture", step_key=spec["step_key"], file_key=spec["file_key"], artifact_ref=artifact_ref,
        field_path=f"/files/{index}", requirement=requirement)


def _undeclared(store, plan, spec, command_proof=None):
    try:
        value = capture_execution_file(store, directory=plan["attempt_directory"],
            relative_path=spec["relative_path"], format=spec["format"], command_proof=command_proof)
    except capture.NativeFileCaptureError as error:
        if error.code != "capture_file_unavailable":
            raise
        return None
    return _retained(store, value)


def _control(retained, validate):
    if retained is None:
        return None
    raw = Path(retained["path"]).read_bytes()
    value = decode_json(raw)
    require(raw in (canonical(value), canonical(value) + b"\n"))
    return validate(value)


def validate_atac_native_capture(value, *, original_plan):
    plan = validate_atac_run_plan(original_plan)
    value = validate_atac_record("NativeCapture", value)
    require([r["specification"] for r in value["files"]] == plan["outputs"], "invalid_atac_native_capture")
    paths = {}
    for row in value["files"]:
        spec, declaration, retained = row["specification"], row["declared"], row["retained"]
        if declaration is not None:
            capture._declaration(declaration)
            require(all(declaration[k] == spec[k] for k in ("relative_path", "format")), "invalid_atac_native_capture")
        if retained is not None:
            identity = capture._identity(retained["file"])
            require(identity["format"] == spec["format"], "invalid_atac_native_capture")
            path = path_value(retained["path"], absolute=True)
            require(path.name == identity["sha256"] and path.parent.name == identity["sha256"][:2]
                and path.parent.parent.name == "artifacts", "invalid_atac_native_capture")
            content = tuple(identity[k] for k in ("artifact_ref", "sha256", "size_bytes"))
            require(path not in paths or paths[path] == content, "invalid_atac_native_capture")
            paths[path] = content
        equal = declaration is not None and retained is not None and all(
            declaration[k] == retained["file"][k] for k in ("sha256", "size_bytes", "format"))
        outcome = row["outcome"]
        require((outcome == "verified" and declaration is not None and declaration["state"] == "present" and equal)
            or (outcome == "declared_absent" and declaration is not None and declaration["state"] == "absent" and retained is None)
            or (outcome == "unavailable" and retained is None and (declaration is None or declaration["state"] == "present"))
            or (outcome == "digest_mismatch" and declaration is not None and declaration["state"] == "present" and retained is not None and not equal)
            or (outcome == "unsealed" and declaration is None and retained is not None), "invalid_atac_native_capture")
        require(row["supplied_extent"] != "complete" or outcome == "verified", "invalid_atac_native_capture")
        require(outcome != "unsealed" or row["supplied_extent"] in ("partial", "unknown"), "invalid_atac_native_capture")
    bundle_row = value["files"][-1]
    require(value["bundle"] is None or value["bundle"] == bundle_row["retained"]
        and bundle_row["outcome"] == "verified", "invalid_atac_native_capture")
    require(value["driver_state"] not in ("succeeded", "failed") or value["bundle"] is not None, "invalid_atac_native_capture")
    if value["driver_state"] == "not_run":
        require(value["bundle"] is None and all(r["retained"] is None for r in value["files"]), "invalid_atac_native_capture")
    keys = {r["file_key"] for r in plan["outputs"]}
    for problem in value["failures"]:
        require(problem["file_key"] is None or problem["file_key"] in keys, "invalid_atac_native_capture")
        require(problem["step_key"] is None or problem["step_key"] in STEP_KEYS, "invalid_atac_native_capture")
    return value


def capture_atac_native_files(store, *, original_plan, source_action_receipt_ref,
        writer_closure_receipt_ref, driver_started, command_proof=None):
    """Capture one caller-qualified closed attempt, including absent roles.

    A missing marker never establishes not-run. Only the caller's affirmative
    driver_started=False permits that state. Storage failures propagate with
    shared custody error codes instead of masquerading as native absence.
    """
    plan = validate_atac_run_plan(original_plan)
    require(type(source_action_receipt_ref) is str and bool(source_action_receipt_ref)
        and type(writer_closure_receipt_ref) is str and bool(writer_closure_receipt_ref)
        and (driver_started is None or type(driver_started) is bool), "invalid_atac_native_capture")
    specs = plan["outputs"]
    rows = [{"specification": spec, "declared": None, "retained": None, "outcome": "unavailable",
        "producer_outcome": "not_run" if driver_started is False else "unknown", "supplied_extent": "unknown"} for spec in specs]
    result = dict(version="atac_native_capture_v1", bundle=None, files=rows,
        source_action_receipt_ref=source_action_receipt_ref, writer_closure_receipt_ref=writer_closure_receipt_ref,
        driver_state="not_run" if driver_started is False else "unknown", failures=[])
    if driver_started is False:
        for i, spec in enumerate(specs):
            result["failures"].append(_problem(spec, i, "native_output_unavailable"))
        return validate_atac_native_capture(result, original_plan=plan)
    bundle_retained = _undeclared(store, plan, specs[-1], command_proof)
    bundle = None
    try:
        bundle = _control(bundle_retained, lambda value: validate_atac_native_bundle(value, plan=plan))
    except ValueError:
        result["failures"].append(_problem(specs[-1], len(specs) - 1, "original_attempt_mismatch",
            artifact_ref=bundle_retained["file"]["artifact_ref"], requirement="original_native_outcome"))
    declared, producers, seals = {}, {}, {}
    if bundle is not None:
        result["bundle"] = bundle_retained
        result["driver_state"] = "succeeded" if all(s["outcome"] == "succeeded" for s in bundle["steps"]) and not bundle["failures"] else "failed"
        result["failures"].extend(bundle["failures"])
        declared = {r["specification"]["file_key"]: r["declaration"] for r in bundle["outputs"]}
        declared["bundle"] = {"relative_path": specs[-1]["relative_path"], "format": specs[-1]["format"],
            "state": "present", **{k: bundle_retained["file"][k] for k in ("sha256", "size_bytes")}}
        for inspection, key in zip(bundle["input_inspections"], ("header1", "header2")):
            producers[key] = (inspection["producer_outcome"], inspection["supplied_extent"])
        # The validated bundle retains each original step outcome even when
        # that step's separate seal file is later unavailable.
        for seal in bundle["steps"]:
            for output in seal["outputs"]:
                producers[output["specification"]["file_key"]] = (seal["outcome"],
                    "complete" if seal["outcome"] == "succeeded" else "partial")
    # Authenticate each independent seal, even when a bundle is present.
    for step_key in STEP_KEYS:
        index = next(i for i,spec in enumerate(specs) if spec["file_key"] == step_key + ".seal")
        spec = specs[index]
        retained = _undeclared(store, plan, spec, command_proof)
        rows[index]["retained"] = retained
        try:
            seal = _control(retained, lambda value: validate_atac_command_seal(value, plan=plan, step_key=step_key))
            if seal is not None and bundle is not None:
                require(seal == bundle["steps"][STEP_KEYS.index(step_key)])
            if seal is not None and step_key == "bdgdiff":
                for operand in seal["inputs"]:
                    declaration = declared.get(operand["file_key"])
                    require(declaration is not None and declaration["state"] == "present"
                        and all(operand["file"][key] == declaration[key] for key in ("sha256", "size_bytes", "format")))
        except ValueError:
            seal = None
            result["failures"].append(_problem(spec, index, "original_attempt_mismatch",
                artifact_ref=retained["file"]["artifact_ref"] if retained else None, requirement="original_native_outcome"))
        if seal is not None:
            seals[step_key] = seal
            result["failures"].extend(seal["failures"])
            for row in seal["outputs"]:
                key = row["specification"]["file_key"]
                declared[key] = row["declaration"]
                producers[key] = (seal["outcome"], "complete" if seal["outcome"] == "succeeded" else "partial")
            if bundle is None:
                declared[spec["file_key"]] = {"relative_path": spec["relative_path"], "format": spec["format"], "state": "present",
                    **{k: retained["file"][k] for k in ("sha256", "size_bytes")}}
            producers[spec["file_key"]] = (seal["outcome"], "complete")
    for i, row in enumerate(rows):
        spec, key = row["specification"], row["specification"]["file_key"]
        declaration = declared.get(key)
        row["declared"] = declaration
        if declaration is not None:
            observed = capture_execution_declarations(store, directory=plan["attempt_directory"],
                declarations=[declaration], command_proof=command_proof)[0]
            row["retained"] = _retained(store, observed["observed"]) if observed["observed"] is not None else None
            row["outcome"] = observed["outcome"]
            if row["outcome"] in ("digest_mismatch", "unavailable"):
                result["failures"].append(_problem(spec, i, "artifact_digest_mismatch" if row["outcome"] == "digest_mismatch" else "native_output_unavailable",
                    artifact_ref=row["retained"]["file"]["artifact_ref"] if row["retained"] else None, requirement="matching_file_identity"))
            producer, extent = producers.get(key, ("succeeded", "complete"))
            row["producer_outcome"] = producer
            row["supplied_extent"] = extent if row["outcome"] == "verified" else "unknown"
        else:
            retained = bundle_retained if key == "bundle" else row["retained"] or _undeclared(store, plan, spec, command_proof)
            row.update(retained=retained, outcome="unsealed" if retained is not None else "unavailable",
                supplied_extent="partial" if retained is not None else "unknown")
            result["failures"].append(_problem(spec, i, "native_output_unavailable",
                artifact_ref=retained["file"]["artifact_ref"] if retained else None, requirement="original_native_outcome"))
    result["failures"] = unique_failures(result["failures"])
    return validate_atac_native_capture(result, original_plan=plan)


__all__ = ["capture_atac_native_files", "validate_atac_native_capture"]
