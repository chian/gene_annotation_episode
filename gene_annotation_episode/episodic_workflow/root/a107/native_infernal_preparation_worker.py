"""Grade supplied Infernal preparation artifacts without executing any work.

Acquisition and native invocation are separate owners. This boundary checks the
supplied bytes against their descriptors before calling a format reader. It
returns complete saved data; it does not publish scientific observations or
construct an episode report.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .infernal_preparation_schema import (
    issue, new_calculations, new_sheet, require_finite_json, validate_artifact,
    validate_common_sheet, validate_operation,
)


GRADING_SCHEMA = "native_infernal_preparation_grading_v1"
ISSUE_CODES = frozenset({"preparation_model_operand_missing",
                         "preparation_generated_output_missing"})


def _payloads(role_map):
    """Check every supplied byte without a filesystem or network read."""
    if type(role_map) is not dict:
        raise ValueError("infernal_preparation_role_map_required")
    result = {}
    for role, members in role_map.items():
        if type(role) is not str or not role or type(members) is not list or not members:
            raise ValueError("infernal_preparation_nonempty_role_payload_list_required")
        result[role] = []
        for member in members:
            if type(member) is not dict or set(member) != {"artifact", "content"}:
                raise ValueError("infernal_preparation_payload_fields_invalid")
            artifact, content = member["artifact"], member["content"]
            validate_artifact(artifact)
            if artifact["role"] != role:
                raise ValueError("infernal_preparation_payload_role_mismatch")
            if type(content) is str:
                raw = content.encode("utf-8")
            elif type(content) is bytes:
                raw = content
            else:
                raise ValueError("infernal_preparation_payload_text_or_bytes_required")
            if len(raw) != artifact["size_bytes"] or hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
                raise ValueError("infernal_preparation_payload_bytes_mismatch")
            result[role].append({"artifact": deepcopy(artifact), "content": content})
    return result


def _one(role_map, role):
    members = role_map.get(role, [])
    if len(members) > 1:
        raise ValueError("infernal_preparation_single_artifact_role_required:" + role)
    return members[0] if members else None


def _all_artifacts(inputs, outputs):
    artifacts = [deepcopy(payload["artifact"]) for mapping in (inputs, outputs)
                 for payloads in mapping.values() for payload in payloads]
    refs = [artifact["artifact_ref"] for artifact in artifacts]
    if len(refs) != len(set(refs)):
        raise ValueError("infernal_preparation_duplicate_artifact_reference")
    return artifacts


def _validate_key_request(operation, inputs):
    """A supplied key locator must name the actual validated selected request."""
    if (operation["program"], operation["mode"]) != ("cmfetch", "single_key"):
        return
    member = _one(inputs, "request")
    if member is None:
        # The sheet already has an explicit missing-provenance issue for this.
        return
    from .native_infernal_preparation_contracts import (
        JOB_VERSION, compile_native_infernal_preparation_job,
        validate_native_infernal_preparation_requested_job,
    )
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("infernal_preparation_request_duplicate_key")
            result[key] = value
        return result
    try:
        request = json.loads(member["content"], object_pairs_hook=unique)
    except (ValueError, UnicodeError, TypeError) as error:
        raise ValueError("infernal_preparation_key_request_invalid") from error
    if type(request) is not dict:
        raise ValueError("infernal_preparation_key_request_invalid")
    if request.get("version") == JOB_VERSION:
        job = request
    else:
        job = validate_native_infernal_preparation_requested_job(request)["native_infernal_preparation"]
    compiled = compile_native_infernal_preparation_job(job)
    if compiled["operation"] != operation:
        raise ValueError("infernal_preparation_key_request_operation_conflict")


def grade_infernal_preparation(*, operation, inputs, outputs, parameters):
    """Return an independently retained sheet and recalculable components.

    ``inputs``/``outputs`` are explicit role -> list[Payload] maps as frozen in
    work247. No filename inference, automatic conversion, repair or resubmission
    is performed. Native parsing can return partial useful records and issues;
    a wrong custody envelope is rejected before any result is interpreted.
    """
    validate_operation(operation)
    if type(parameters) is not dict:
        raise ValueError("infernal_preparation_parameters_object_required")
    require_finite_json(parameters)
    operation, parameters = deepcopy(operation), deepcopy(parameters)
    inputs, outputs = _payloads(inputs), _payloads(outputs)
    artifacts = _all_artifacts(inputs, outputs)
    _validate_key_request(operation, inputs)
    program = operation["program"]
    if program in {"cmconvert", "cmfetch", "cmpress"}:
        from .infernal_preparation_artifacts import (
            populate_infernal_artifact_sheet, validate_infernal_artifact_sheet,
        )
        sheet = populate_infernal_artifact_sheet(operation=operation, artifacts=artifacts,
                                                 inputs=inputs, outputs=outputs)
        calculations = validate_infernal_artifact_sheet(sheet, parameters=parameters)
    elif program in {"cmbuild", "cmcalibrate", "cmstat"}:
        from .infernal_preparation_statistics import populate_infernal_statistics_sheet
        from .infernal_preparation_calculations import calculate_infernal_statistics
        sheet = populate_infernal_statistics_sheet(operation=operation, artifacts=artifacts,
                                                   inputs=inputs, outputs=outputs)
        calculations = calculate_infernal_statistics(sheet, parameters=parameters)
    else:
        from .infernal_preparation_models import extract_infernal_models
        from .infernal_preparation_emission import populate_cmemit_sheet
        from .infernal_preparation_emission_calculations import calculate_cmemit_components
        model = _one(inputs, "models")
        role = "generated_alignment" if operation["mode"] == "sample_aligned" else "generated_sequences"
        output, trace = _one(outputs, role), _one(outputs, "trace")
        if model is None or output is None:
            sheet = new_sheet(operation, artifacts)
            if model is None:
                sheet["issues"].append(issue("preparation_model_operand_missing", stage="association"))
            else:
                parsed = extract_infernal_models(model["content"], artifact=model["artifact"],
                    format=model["artifact"]["format"], engine_version=operation["engine_version"])
                sheet["input_records"] = parsed["records"]
                sheet["issues"].extend(parsed["issues"])
            if output is None:
                sheet["issues"].append(issue("preparation_generated_output_missing", stage="association"))
            # Absent output is not an empty, successfully measured population.
            calculations = new_calculations(operation, parameters)
            calculations["issues"] = deepcopy(sheet["issues"])
        else:
            models = extract_infernal_models(model["content"], artifact=model["artifact"],
                format=model["artifact"]["format"], engine_version=operation["engine_version"])
            sheet = populate_cmemit_sheet(operation=operation, artifacts=artifacts,
                                         models=models, output=output, trace=trace)
            calculations = calculate_cmemit_components(sheet, parameters=parameters)
    validate_common_sheet(sheet)
    if (calculations.get("operation") != operation or calculations.get("parameters") != parameters
            or sheet["operation"] != operation):
        raise ValueError("infernal_preparation_grading_original_selection_changed")
    result = {"version": GRADING_SCHEMA, "operation": operation,
              "sheet": sheet, "calculations": calculations}
    require_finite_json(result)
    return result


def recalculate_infernal_preparation(sheet, *, parameters):
    """Recompute from a saved sheet; no native parser or acquisition is needed."""
    validate_common_sheet(sheet)
    sheet = deepcopy(sheet)
    program = sheet["operation"]["program"]
    if program in {"cmconvert", "cmfetch", "cmpress"}:
        from .infernal_preparation_artifacts import validate_infernal_artifact_sheet
        result = validate_infernal_artifact_sheet(sheet, parameters=parameters)
    elif program in {"cmbuild", "cmcalibrate", "cmstat"}:
        from .infernal_preparation_calculations import calculate_infernal_statistics
        result = calculate_infernal_statistics(sheet, parameters=parameters)
    else:
        if any(item.get("code") in ISSUE_CODES for item in sheet["issues"]):
            result = new_calculations(sheet["operation"], parameters)
            result["issues"] = deepcopy(sheet["issues"])
        else:
            from .infernal_preparation_emission_calculations import calculate_cmemit_components
            result = calculate_cmemit_components(sheet, parameters=parameters)
    require_finite_json(result)
    if result.get("operation") != sheet["operation"] or result.get("parameters") != parameters:
        raise ValueError("infernal_preparation_recalculation_parameters_changed")
    return result


__all__ = ["grade_infernal_preparation", "recalculate_infernal_preparation"]
