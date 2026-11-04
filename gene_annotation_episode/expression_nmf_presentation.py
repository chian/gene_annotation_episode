"""Pure literal presentation of selected, already-recorded NMF results.

This module neither authenticates a producer nor loads a numerical sheet.  It
does not fit, calculate, acquire, or grant a reference.  Existing result owners
retain those responsibilities; saved File identities remain callable operands.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import re

from jsonschema import Draft202012Validator

from .expression_nmf_common import canonical, validate_parameters
from .expression_nmf_result_contracts import (
    validate_expression_nmf_result_selector, validate_file, validate_projection,
)
from .expression_nmf_return_views import (
    FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE,
    validate_expression_nmf_fact_values,
)


_JOB_VIEW = "expression_nmf_scientific_job_view_v1"
_RECEIPT_VIEW = "expression_nmf_result_receipt_view_v1"
_NATIVE_JOB = "native_expression_nmf_job_v1"
_RECEIPT = "native_expression_nmf_acquired_result_v1"
_PROJECTION = "expression_nmf_result_view_v1"
_SELECTOR = "expression_nmf_result_selector_v1"
_LABEL = "Selected NMF projection "
_LABEL_PATTERN = re.compile(r"Selected NMF projection [1-9][0-9]*\Z")
_CHANNELS = ("last_local_outcome", "child_reports", "current_report_update")
_OPAQUE_SLOTS = frozenset((
    "instructions", "schema", "schemas", "report_schema", "requested_form",
    "input_schema", "output_schema", "result_selector_schema", "schema_json",
    "tools", "tool_schema", "tool_schemas", "arguments", "request",
    "input", "inputs", "input_data", "assignment", "selected_task",
    "selected_execution_task",
))
# These are the existing closed carrier/intent keysets, not new receipt types.
# Their private values are deliberately not inspected by a public presenter.
_RECEIPT_KEYS = (
    "version", "intent", "handoff_proof", "original_origins", "observation",
    "native", "source_action_file", "writer_closure_file", "capture",
    "worker_plan", "worker_capture", "worker_execution", "qualified_files",
    "projection", "host_failures", "facts", "acquired_population",
    "delivery_complete",
)
_INTENT_KEYS = (
    "version", "run_id", "episode_id", "path", "scope", "assignment",
    "original_request_sha256", "operation_key", "tool_name", "arguments",
    "target",
)
_FILE_KEYS = ("artifact_ref", "sha256", "size_bytes", "format")
_DIAGNOSTIC_BASIS = {
    "native_reconstruction_error": "Native reported residual norm",
    "native_n_iter": "Native reported solver iteration count",
    "fit_call_count": "Recorded original native fit count",
    "sse": "Calculated sum of squared residuals",
    "cell_count": "Calculated fitted-matrix cell population",
    "frobenius_residual": "Calculated residual Frobenius norm",
    "rmse": "Calculated root mean squared residual",
    "mae": "Calculated mean absolute residual",
    "relative_frobenius_residual": "Calculated relative residual norm",
    "native_minus_calculated_frobenius": "Calculated difference: native minus calculated residual norm",
}


def _require(condition):
    if not condition:
        raise ValueError("expression_nmf_presentation_invalid")


def _closed(value, keys):
    _require(type(value) is dict and set(value) == set(keys))


def _same(left, right):
    return canonical(left) == canonical(right)


def _scientific_request(value):
    """Validate the original scientific fields without inventing host paths."""
    from .native_expression_nmf_contracts import JOB_SCHEMA
    schema = deepcopy(JOB_SCHEMA)
    for name in ("software", "output_prefix"):
        del schema["properties"][name]
        schema["required"].remove(name)
    input_schema = schema["properties"]["input"]
    del input_schema["properties"]["path"]
    input_schema["required"].remove("path")
    canonical(value)
    _require(Draft202012Validator(schema).is_valid(value))
    validate_parameters(value["parameters"])
    _require(type(value["input"]["size_bytes"]) is int)
    return deepcopy(value)


def _job_view(value):
    _closed(value, ("version", "request"))
    _require(value["version"] == _JOB_VIEW)
    return {"version": _JOB_VIEW, "request": _scientific_request(value["request"])}


def expression_nmf_scientific_job_view(job):
    """Preserve selected input identity and settings, without host machinery."""
    from .native_expression_nmf_contracts import validate_expression_nmf_job
    job = validate_expression_nmf_job(job)
    request = {name: deepcopy(job[name]) for name in
        ("version", "operation", "mode", "input", "parameters")}
    del request["input"]["path"]
    # The input has no declared format; its nullable artifact_ref and original
    # byte identity are retained literally rather than made into a new File.
    return _job_view({"version": _JOB_VIEW, "request": request})


def _selector(value):
    return validate_expression_nmf_result_selector(value)


def _facts(value, *, labels=False):
    _closed(value, FACT_SOURCES)
    result = {}
    for source in FACT_SOURCES:
        rows = value[source]
        _require(type(rows) is list)
        if source == PROJECTION_SOURCE and labels:
            result[source] = [row if type(row) is str and _LABEL_PATTERN.fullmatch(row)
                else validate_projection(row) for row in rows]
        else:
            result[source] = validate_expression_nmf_fact_values(source, rows)
    return result


def _observation(value):
    if value is None:
        return None
    _require(type(value) is dict)
    return {name: deepcopy(value[name]) for name in
        ("state", "returncode", "failure_code", "result_available")}


def _receipt_fields(value, *, labels=False):
    """Check public selection and values, without reading receipt controls."""
    _closed(value, ("version", "tool_name", "selector", "observation", "facts",
        "delivery_complete"))
    _require(value["version"] == _RECEIPT_VIEW
        and value["tool_name"] in ("execution.results.status", "execution.results.collect")
        and type(value["delivery_complete"]) is bool)
    selector = _selector(value["selector"])
    facts = _facts(value["facts"], labels=labels)
    observation = value["observation"]
    if observation is not None:
        from .progress_records import RESOURCE_OBSERVATION_SCHEMA
        names = ("state", "returncode", "failure_code", "result_available")
        _closed(observation, names)
        schema = {"type": "object", "properties": {name:
            deepcopy(RESOURCE_OBSERVATION_SCHEMA["properties"][name]) for name in names},
            "required": list(names), "additionalProperties": False}
        canonical(observation)
        _require(Draft202012Validator(schema).is_valid(observation))
    for projection in facts[PROJECTION_SOURCE]:
        if type(projection) is not str:
            _require(_same(projection["selector"], selector["projection"]))
    if value["tool_name"] == "execution.results.status":
        _require(not value["delivery_complete"] and all(not rows for rows in facts.values()))
    return {"version": _RECEIPT_VIEW, "tool_name": value["tool_name"],
        "selector": selector, "observation": deepcopy(observation), "facts": facts,
        "delivery_complete": value["delivery_complete"]}


def _receipt_view(value):
    """Select requested public facts; private siblings are not UI authority."""
    _closed(value, _RECEIPT_KEYS)
    _require(value["version"] == _RECEIPT)
    intent = value["intent"]
    _closed(intent, _INTENT_KEYS)
    _require(intent["version"] == "expression_nmf_result_intent_v1"
        and intent["tool_name"] in ("execution.results.status", "execution.results.collect")
        and type(intent["arguments"]) is dict and intent["arguments"] == {})
    assignment = intent["assignment"]
    _closed(assignment, ("version", "handoff_ref", "selector"))
    _require(assignment["version"] == "execution_results_assignment_v1")
    return _receipt_fields({"version": _RECEIPT_VIEW, "tool_name": intent["tool_name"],
        "selector": assignment["selector"], "observation": _observation(value["observation"]),
        "facts": value["facts"], "delivery_complete": value["delivery_complete"]})


def select_expression_nmf_execution_values(value):
    """Recognize only the existing finite NMF records and these safe views."""
    if not isinstance(value, Mapping):
        return None
    try:
        value = deepcopy(dict(value))
        if set(value) == {"argv", "environment", "native_expression_nmf"}:
            from .native_expression_nmf_contracts import validate_expression_nmf_requested_job
            requested = validate_expression_nmf_requested_job(value)
            return {"native_expression_nmf":
                expression_nmf_scientific_job_view(requested["native_expression_nmf"])}
        if set(value) == {"native_expression_nmf"}:
            return {"native_expression_nmf": _job_view(value["native_expression_nmf"])}
        version = value.get("version")
        if version == _NATIVE_JOB:
            return expression_nmf_scientific_job_view(value)
        if version == _JOB_VIEW:
            return _job_view(value)
        if version == _SELECTOR:
            return _selector(value)
        if version == _RECEIPT:
            return _receipt_view(value)
        if version == _RECEIPT_VIEW:
            return _receipt_fields(value, labels=True)
        if value.get("schema") == _PROJECTION:
            return validate_projection(value)
        if set(value) == set(_FILE_KEYS):
            return validate_file(value, saved=True)
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError):
        return None
    return None


def select_expression_nmf_presentation(state, *, lookup_results=()):
    """Detach literal projections from declared outcome/report channels only."""
    if not isinstance(state, Mapping):
        return {"context": deepcopy(state), "lookup_results": deepcopy(lookup_results),
            "projections": []}
    projections, keys = [], []

    def project(value):
        if isinstance(value, Mapping):
            if value.get("schema") == _PROJECTION:
                selected = select_expression_nmf_execution_values(value)
                if selected is None:
                    return deepcopy(value)
                key = canonical(selected)
                if key not in keys:
                    keys.append(key)
                    projections.append(selected)
                return _LABEL + str(keys.index(key) + 1)
            if value.get("version") in (_RECEIPT, _RECEIPT_VIEW):
                selected = select_expression_nmf_execution_values(value)
                if selected is None:
                    return deepcopy(value)
                return {name: project(child) for name, child in selected.items()}
            if set(value) == set(_FILE_KEYS):
                selected = select_expression_nmf_execution_values(value)
                if selected is not None:
                    return selected
            if "version" in value or isinstance(value.get("schema"), str):
                return deepcopy(value)
            return {name: deepcopy(child) if name in _OPAQUE_SLOTS else project(child)
                for name, child in value.items()}
        if isinstance(value, (list, tuple)):
            return [project(child) for child in value]
        return deepcopy(value)

    shown = deepcopy(dict(state))
    for field in _CHANNELS:
        if field in shown:
            shown[field] = project(shown[field])
    return {"context": shown, "lookup_results": [project(row) for row in lookup_results],
        "projections": projections}


def _literal(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _table(headers, rows):
    rows = list(rows)
    if not rows:
        return "[]"

    def cell(value):
        return str(value).replace("|", "\\|").replace("\r", "<br>").replace("\n", "<br>")

    return "\n".join(["| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)])


def _diagnostics(rows):
    return _table(("Field", "Measurement basis", "Literal value", "Stored unit", "Stored denominator"),
        ((row["field"], _DIAGNOSTIC_BASIS[row["field"]], _literal(row["value"]),
            _literal(row["units"]), _literal(row["denominator"])) for row in rows))


def _gene_loadings(rows):
    return "\n\n".join([
        "W loadings and loading sums have arbitrary factor scale; normalized loadings are dimensionless.",
        _table(("Gene position", "Gene key", "Original label", "Gene metadata", "Component position",
            "Component key", "Raw loading (arbitrary factor scale)", "Normalized loading (dimensionless)",
            "Loading-sum denominator (arbitrary factor scale)"),
            ((row["gene_position"], row["gene_key"], _literal(row["gene_label"]),
                _literal(row["gene_metadata"]), row["component_position"], row["component_key"],
                _literal(row["raw_loading"]), _literal(row["normalized_loading"]),
                _literal(row["loading_sum"])) for row in rows)),
    ])


def _sample_contributions(rows):
    return "\n\n".join([
        "H coefficients have arbitrary factor scale. Contribution fractions are dimensionless; "
        "the stored fit unit applies to component contribution and reconstructed sample total only.",
        _table(("Sample position", "Sample key", "Original label", "Sample metadata", "Component position",
            "Component key", "Raw coefficient (arbitrary factor scale)", "Component contribution",
            "Contribution fraction (dimensionless)", "Reconstructed-sample-total denominator",
            "Fit unit (contribution and total only)"),
            ((row["sample_position"], row["sample_key"], _literal(row["sample_label"]),
                _literal(row["sample_metadata"]), row["component_position"], row["component_key"],
                _literal(row["raw_coefficient"]), _literal(row["component_contribution"]),
                _literal(row["contribution_fraction"]), _literal(row["reconstructed_sample_total"]),
                _literal(row["units"])) for row in rows)),
    ])


def _residual_cells(rows):
    return "\n\n".join([
        "The raw input unit is not supplied by this projection. The stored fit unit applies "
        "to fitted, reconstructed and signed residual values only.",
        _table(("Gene position", "Gene key", "Original gene label", "Sample position", "Sample key",
            "Original sample label", "Raw input value (unit not supplied)", "Fitted input value",
            "Reconstructed value", "Signed residual", "Fit unit (fitted/reconstructed/residual only)"),
            ((row["gene_position"], row["gene_key"], _literal(row["gene_label"]),
                row["sample_position"], row["sample_key"], _literal(row["sample_label"]),
                _literal(row["raw_value"]), _literal(row["fit_value"]), _literal(row["reconstructed_value"]),
                _literal(row["signed_residual"]), _literal(row["units"])) for row in rows)),
    ])


def _issues(rows):
    return _table(("Code", "Stage", "Field", "Gene position", "Sample position", "Component position"),
        ((row["code"], row["stage"], _literal(row["field"]), _literal(row["gene_position"]),
            _literal(row["sample_position"]), _literal(row["component_position"])) for row in rows))


def render_expression_nmf_projections(projections):
    """Render only stored selected values, populations, operands and limits."""
    renderers = {"fit_diagnostics": _diagnostics, "gene_loadings": _gene_loadings,
        "sample_contributions": _sample_contributions, "residual_cells": _residual_cells}
    parts = []
    for index, value in enumerate(projections, 1):
        projection = validate_projection(value)
        parts.extend([_LABEL + str(index), "",
            _table(("Projection property", "Literal value"), ((name, _literal(projection[name]))
                for name in ("schema", "view", "selector", "status", "native_outcome",
                    "total_available_rows", "selected_row_count", "filtered_row_count",
                    "row_offset", "returned_row_count", "has_more"))), "",
            "Stored selected rows", "", renderers[projection["view"]](projection["rows"]), "",
            "Stored calculation qualifications", "", _issues(projection["qualifications"]), "",
            "Recorded located failures", "", _issues(projection["failures"]), "",
            "Recorded native warning codes", "", _literal(projection["warning_codes"])])
    return "\n".join(parts)


__all__ = ["expression_nmf_scientific_job_view", "select_expression_nmf_execution_values",
    "select_expression_nmf_presentation", "render_expression_nmf_projections"]
