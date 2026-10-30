"""Admission of retained preparation/report payloads, without native execution.

The bounded result worker supplies authenticated bytes and original selections.
These helpers validate relationships with the existing P/R contracts and retain
unavailable declarations; they never decode events or calculate measurements.
"""
from copy import deepcopy
import re

from . import fluorescence_event_contracts as core
from .fluorescence_execution_common import require, same, unique
from .fluorescence_preparation_contracts import (
    SCALE_METHOD, assemble_prepared_parse, validate_preparation_outcome,
)
from .fluorescence_native_report_contracts import (
    CYTOKINE_CSV_PROFILE, _association, _binding, _field_shape,
    make_fluorescence_report_binding, validate_report_parse_result,
)
from .fluorescence_result_contracts import failure
from .native_fluorescence_contracts import (
    validate_fluorescence_prepared_batch, validate_fluorescence_report_batch,
)
from .native_fluorescence_storage import decode_json


def _file(role, captured, verified):
    row = captured.get(role)
    return (row["retained"]["file"] if row is not None and row["retained"] is not None
            and verified.get(role, False) else None)


def _selected_files(job):
    for prefix, items in (("event_input", job["inputs"]),
                          ("support_input", job["support_inputs"]),
                          ("report_input", job.get("report_inputs", []))):
        for index, item in enumerate(items):
            yield (item["source"]["file"] if prefix == "event_input" else item["file"],
                   f"{prefix}:{index}")


def _selected_role(file, job, captured, verified):
    """The same originally selected artifact can serve more than one input."""
    return next((role for selected, role in _selected_files(job)
                 if same(selected, file) and same(_file(role, captured, verified), file)), None)


def _document(raw):
    value = decode_json(raw)
    require(raw == core.canonical(value) + b"\n", "fluorescence_payload_noncanonical")
    return value


def _unavailable_preparation(request, parent, *, code):
    """Keep the selected lineage; missing bytes establish no applied operation."""
    output = request["output"]
    domain = deepcopy(parent["domain"])
    domain.update(key=output["key"], source_key=output["source_key"],
        parent_domain_key=parent["domain"]["key"], state="unavailable", correspondence=[],
        comparison_basis=deepcopy(output["comparison_basis"]))
    domain.setdefault("scaling", dict(state="unknown", method=None, parameters_file=None))
    field = "scaling" if request["recipe"]["method"] == SCALE_METHOD else "compensation"
    domain[field] = dict(state="unknown", method=request["recipe"]["method"], parameters_file=None)
    source = dict(key=output["source_key"], file=None, dataset_position=0,
        format_profile="fluorescence_prepared_event_data_v1", extent="unavailable",
        native_event_count=None, metadata=[])
    issues = [core.issue(code, "input", source_key=source["key"],
        sample_key=parent["sample"]["key"], domain_key=domain["key"])]
    return core.validate_event_parse_result(dict(schema=core.PARSE_SCHEMA, source=source,
        sample=deepcopy(parent["sample"]), domain=domain,
        channels=[dict(deepcopy(row), domain_key=domain["key"]) for row in output["channels"]],
        events=[], issues=issues))


def admit_preparations(*, original_plan, captured, verified, raw_values,
                       originals, original_batch_files, started, operand_problems):
    """Validate each selected envelope against its actual admitted parent.

    No preparation backend or reader is imported here. A reconstructed outcome
    must assemble byte-for-byte to the retained parse, including its issues.
    """
    job = original_plan["requested_job"]["native_fluorescence"]
    parsed, batch_files, statuses, failures = [], [], [], []
    for index, request in enumerate(job.get("preparations", [])):
        parents, files = ((originals, original_batch_files) if request["input"]["kind"] == "event_input"
                          else (parsed, batch_files))
        parent = parents[request["input"]["index"]]
        parent_file = files[request["input"]["index"]]
        role = f"prepared_batch:{index}"
        parameter_role, data_role = f"preparation_parameters:{index}", f"prepared_data:{index}"
        accepted, rejected = None, None
        if not started or parent_file is None or role not in raw_values:
            rejected = "preparation_unavailable"
        else:
            try:
                batch = validate_fluorescence_prepared_batch(_document(raw_values[role]),
                    original_plan=original_plan, preparation_index=index, parent_batch_file=parent_file)
                recipe_role = _selected_role(request["recipe_file"], job, captured, verified)
                if recipe_role is None or recipe_role not in raw_values or parameter_role not in raw_values:
                    rejected = "preparation_unavailable"
                else:
                    require(core.canonical(decode_json(raw_values[recipe_role])) == core.canonical(request["recipe"]),
                            "fluorescence_recipe_payload_mismatch")
                    require(same(batch["parameters_file"], _file(parameter_role, captured, verified)),
                            "fluorescence_parameters_payload_mismatch")
                    parameters = _document(raw_values[parameter_role])
                    data = None
                    if batch["prepared_file"] is not None:
                        if data_role not in raw_values:
                            rejected = "preparation_unavailable"
                        else:
                            require(same(batch["prepared_file"], _file(data_role, captured, verified)),
                                    "fluorescence_prepared_payload_mismatch")
                            data = _document(raw_values[data_role])
                    else:
                        require(_file(data_role, captured, verified) is None, "fluorescence_prepared_payload_mismatch")
                    if data is not None and request["recipe"]["method"] != SCALE_METHOD:
                        matrix = request["recipe"]["parameters"]["matrix_file"]
                        if _selected_role(matrix, job, captured, verified) is None:
                            rejected = "preparation_unavailable"
                    if rejected is None:
                        outcome = dict(version="fluorescence_preparation_outcome_v1", status=batch["status"],
                            data=data, parameters=parameters, issues=deepcopy(batch["parse"]["issues"]))
                        validate_preparation_outcome(outcome, request=request, parent=parent)
                        require(same(parameters["problems"], batch["problems"]), "fluorescence_preparation_problems_mismatch")
                        assembled = assemble_prepared_parse(outcome, request=request, parent=parent,
                            data_file=batch["prepared_file"], parameters_file=batch["parameters_file"])
                        require(core.canonical(assembled) == core.canonical(batch["parse"]),
                                "fluorescence_prepared_parse_mismatch")
                        accepted = assembled
            except (ValueError, UnicodeError):
                rejected = "preparation_incompatible"
        if accepted is None:
            failures.append(failure(rejected, "capture", input_index=index, role=role))
            mismatched = rejected == "preparation_incompatible" or any(
                operand_problems.get(key) in {"capture_file_digest_mismatch", "input_identity_mismatch"}
                for key in (role, parameter_role, data_role))
            parsed.append(_unavailable_preparation(request, parent,
                code="retained_artifact_mismatch" if mismatched else "source_unavailable"))
            batch_files.append(None)
            statuses.append("unavailable")
        else:
            parsed.append(accepted)
            batch_files.append(deepcopy(_file(role, captured, verified)))
            statuses.append(batch["status"])
            if batch["status"] not in {"complete", "partial"}:
                code = {"failed": "preparation_failed", "incompatible": "preparation_incompatible",
                        "unavailable": "preparation_unavailable"}[batch["status"]]
                failures.append(failure(code, "worker", input_index=index, role=role))
    return parsed, batch_files, statuses, failures


def _report_spans(parsed, raw, *, profile):
    """Authenticate recorded lexical spans; do not locate or parse report fields."""
    for row in parsed["reports"]:
        if row["raw"] is None:
            continue
        location = row["location"]
        start, end = location["byte_start"], location["byte_end"]
        token = raw[start:end].decode("utf-8")
        if profile == CYTOKINE_CSV_PROFILE:
            token = token.replace('""', '"')
        require(token == row["raw"], "fluorescence_report_span_mismatch")
        line_start = 1 + len(re.findall(rb"\r\n|\r|\n", raw[:start]))
        line_end = 1 + len(re.findall(rb"\r\n|\r|\n", raw[:end]))
        require((location["line_start"], location["line_end"]) == (line_start, line_end),
                "fluorescence_report_span_mismatch")
        if profile != CYTOKINE_CSV_PROFILE:
            require(location["record_ordinal"] == line_start - 1, "fluorescence_report_span_mismatch")


def _unavailable_report(binding, *, code):
    """Retain requested keys without inventing extracted tokens or execution."""
    selected, context = binding["report_input"], _binding(binding)
    source = dict(key=selected["source_key"], file=deepcopy(selected["file"]), dataset_position=0,
        format_profile=selected["profile"], extent="unavailable", native_event_count=None, metadata=[])
    reports = []
    for field in selected["fields"]:
        unit, precision, _ = _field_shape(field, selected["profile"], context)
        reports.append(dict(key=field["key"], file=deepcopy(selected["file"]), source_key=selected["source_key"],
            location={name: None for name in ("record_ordinal", "line_start", "line_end", "byte_start", "byte_end")},
            label=None, value=None, raw=None, unit=unit, component_request=deepcopy(field["component_request"]),
            decimal_places=precision))
    issues = [core.issue(code, "input", source_key=selected["source_key"])]
    if any(field["component_request"] is not None for field in selected["fields"]):
        issues.append(core.issue("native_population_unknown", "input", source_key=selected["source_key"]))
    return source, reports, issues


def admit_reports(*, original_plan, captured, verified, raw_values, started, operand_problems):
    """Admit closed report records; retain native values if support is missing."""
    job = original_plan["requested_job"]["native_fluorescence"]
    sources, reports, issues, accepted_files, extents, failures = [], [], [], [], [], []
    for index, selected in enumerate(job.get("report_inputs", [])):
        binding = make_fluorescence_report_binding(selected, definitions=job["definitions"],
            event_inputs=job["inputs"], preparations=job.get("preparations", []))
        role, input_role = f"report_batch:{index}", f"report_input:{index}"
        accepted, rejected = None, None
        if not started or role not in raw_values or not verified.get(input_role, False):
            rejected = "report_batch_unavailable"
        else:
            try:
                batch = validate_fluorescence_report_batch(_document(raw_values[role]),
                    original_plan=original_plan, report_index=index)
                accepted = validate_report_parse_result(batch["parse"], binding=binding)
                _report_spans(accepted, raw_values[input_role], profile=selected["profile"])
            except (ValueError, UnicodeError):
                accepted, rejected = None, "report_batch_invalid"
        if accepted is None:
            failures.append(failure(rejected, "capture", input_index=index, role=role))
            mismatched = rejected == "report_batch_invalid" or any(
                operand_problems.get(key) in {"capture_file_digest_mismatch", "input_identity_mismatch"}
                for key in (role, input_role))
            source, rows, problems = _unavailable_report(binding,
                code="retained_artifact_mismatch" if mismatched else "source_unavailable")
            accepted_files.append(None)
        else:
            source, rows, problems = accepted["source"], accepted["reports"], accepted["issues"]
            linked = any(field["component_request"] is not None for field in selected["fields"])
            supported = not linked
            if linked and selected["association_file"] is not None and batch["association_file"] is not None:
                support_role = _selected_role(selected["association_file"], job, captured, verified)
                if support_role is not None and support_role in raw_values:
                    try:
                        _association(decode_json(raw_values[support_role]), binding=binding, context=_binding(binding))
                        supported = True
                    except (ValueError, UnicodeError, TypeError, KeyError, RecursionError):
                        pass
            if not supported:
                problems = unique([*problems, core.issue("native_population_unknown", "input", source_key=source["key"])])
            accepted_files.append(deepcopy(_file(role, captured, verified)))
        sources.append(source)
        reports.extend(rows)
        issues.extend(problems)
        extents.append(source["extent"])
    return sources, reports, unique(issues), accepted_files, extents, failures
