"""Literal presentation of existing ATAC selections and requested facts.

The result and return owners authenticate custody.  This module selects no
work, opens no artifacts and calculates no measurements.  Explicit input and
saved File identities remain complete operands rather than tracking labels.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
import re

from jsonschema import Draft202012Validator

from .atac_differential_contracts import (
    validate_atac_condition, validate_atac_reference, validate_atac_sample,
)
from .atac_differential_result_contracts import (
    SHEET_FORMAT, TABLE_FORMAT, canonical, validate_atac_result_record,
)
from .atac_differential_return_views import (
    FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE, validate_atac_fact_values,
)


_JOB_VIEW = "atac_scientific_job_view_v1"
_RECEIPT_VIEW = "atac_result_receipt_view_v1"
_RECEIPT = "native_atac_differential_acquired_result_v1"
_PROJECTION = "atac_differential_projection_v1"
_SELECTOR = "atac_differential_result_selector_v1"
_LABEL = "Selected ATAC projection "
_LABEL_PATTERN = re.compile(r"Selected ATAC projection [1-9][0-9]*\Z")
_CHANNELS = ("last_local_outcome", "child_reports", "current_report_update")
_OPAQUE_SLOTS = frozenset((
    "instructions", "schema", "schemas", "report_schema", "requested_form",
    "input_schema", "output_schema", "result_selector_schema", "schema_json",
    "tools", "tool_schema", "tool_schemas", "arguments", "request",
    "input", "inputs", "input_data", "assignment", "selected_task",
    "selected_execution_task",
))
_PEAK_UNITS = {
    "start1": "bp; one_based_inclusive", "end1": "bp; one_based_inclusive",
    "length_bp": "bp", "abs_summit1": "bp; one_based",
    "start0": "bp; zero_based_half_open", "end0": "bp; zero_based_half_open",
    "summit_offset0": "bp offset from start0", "pileup": "native pileup",
    "fold_enrichment": "fold", "minus_log10_pvalue": "-log10(p)",
    "minus_log10_qvalue": "-log10(q)", "display_score": "native display score",
    "signal_value": "native signal_value", "score": "native summit score",
}
_REGION_UNITS = {
    "start": "bp; zero_based_half_open", "end": "bp; zero_based_half_open",
    "span_bp": "bp", "qualifying_bp": "bp", "bridged_gap_bp": "bp",
    "score_numerator": "signed_log10_likelihood_ratio * bp",
    "score_denominator_bp": "qualifying bp",
    "mean_score": "signed_log10_likelihood_ratio",
    "native_float32_mean_score": "signed_log10_likelihood_ratio",
}


def _require(condition):
    if not condition:
        raise ValueError("atac_presentation_invalid")


def _closed(value, keys):
    _require(type(value) is dict and set(value) == set(keys))


def _same(left, right):
    return canonical(left) == canonical(right)


def _scientific_request(value):
    """Keep the original meaningful request relationships, without a prefix."""
    from .native_atac_differential_contracts import atac_execution_schema
    schema = atac_execution_schema("Request")
    del schema["properties"]["output_prefix"]
    schema["required"].remove("output_prefix")
    canonical(value)
    _require(Draft202012Validator(schema).is_valid(value))
    validate_atac_reference(value["reference"])
    for row in value["samples"]:
        validate_atac_sample(row)
    for row in value["conditions"]:
        validate_atac_condition(row)
    for rows, key in ((value["samples"], "sample_id"), (value["conditions"], "condition_id"),
            (value["inputs"], "input_key")):
        _require(len({row[key] for row in rows}) == len(rows))
    samples = {row["sample_id"]: row for row in value["samples"]}
    _require(set(samples) == {row["sample_id"] for row in value["inputs"]})
    for selected, condition in zip(value["inputs"], value["conditions"]):
        _require(selected["condition_id"] == condition["condition_id"]
            and condition["sample_ids"] == [selected["sample_id"]]
            and selected["reference_id"] == value["reference"]["reference_id"])
        sample = samples[selected["sample_id"]]
        _require(sample["reference_id"] == selected["reference_id"]
            and selected["file"]["artifact_ref"] in sample["input_artifact_refs"]
            and selected["file"]["artifact_ref"] == "artifact_" + selected["file"]["sha256"])
    argument = value["callpeak"]["genome_size_argument"]
    if argument not in ("hs", "mm", "ce", "dm"):
        try:
            numeric = Decimal(argument)
        except InvalidOperation as error:
            raise ValueError("atac_presentation_invalid") from error
        _require(re.fullmatch(r"[+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", argument)
            is not None and numeric.is_finite() and numeric > 0)
    parameters = value["bdgdiff"]
    _require(parameters["maximum_gap_bp"] < parameters["minimum_length_bp"])
    return deepcopy(value)


def _job_view(value):
    _closed(value, ("version", "request"))
    _require(value["version"] == _JOB_VIEW)
    return {"version": _JOB_VIEW, "request": _scientific_request(value["request"])}


def atac_scientific_job_view(job):
    """Remove private runtime/input paths, retaining exact selected operands."""
    from .native_atac_differential_contracts import validate_atac_native_job
    job = validate_atac_native_job(job)
    request = deepcopy(job["request"])
    del request["output_prefix"]
    return _job_view({"version": _JOB_VIEW, "request": request})


def _selector(value):
    return validate_atac_result_record("ResultSelector", value)


def _facts(value, *, labels=False):
    _closed(value, FACT_SOURCES)
    result = {}
    for source in FACT_SOURCES:
        rows = value[source]
        _require(type(rows) is list)
        if source == PROJECTION_SOURCE and labels:
            result[source] = [row if type(row) is str and _LABEL_PATTERN.fullmatch(row)
                else validate_atac_result_record("RequestedProjection", row) for row in rows]
        else:
            result[source] = validate_atac_fact_values(source, rows)
    return result


def _observation(value):
    if value is None:
        return None
    _require(type(value) is dict)
    return {name: deepcopy(value[name]) for name in
        ("state", "returncode", "failure_code", "result_available")}


def _receipt_fields(value, *, labels=False):
    _closed(value, ("version", "tool_name", "selector", "observation", "facts", "delivery_complete"))
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
        if type(projection) is str:
            continue
        _require(projection["comparison_key"] == selector["comparison_key"]
            and _same(projection["selected_intervals"], selector["intervals"])
            and _same(projection["parameters"], selector["parameters"])
            and projection["kind"] == selector["projection"]["kind"]
            and _same(projection["row_window"], selector["projection"]["row_window"]))
    if value["tool_name"] == "execution.results.status":
        _require(not value["delivery_complete"] and all(not rows for rows in facts.values()))
    return {"version": _RECEIPT_VIEW, "tool_name": value["tool_name"], "selector": selector,
        "observation": deepcopy(observation), "facts": facts,
        "delivery_complete": value["delivery_complete"]}


def _receipt_view(value):
    """Select public fields; private siblings never gate this UI projection."""
    from .atac_differential_result_receipts import (
        AtacDifferentialResultIntent, AtacDifferentialResultReceipt,
    )
    _closed(value, AtacDifferentialResultReceipt.__annotations__)
    _require(value["version"] == _RECEIPT)
    intent = value["intent"]
    _closed(intent, AtacDifferentialResultIntent.__annotations__)
    _require(intent["version"] == "atac_differential_result_intent_v1"
        and intent["tool_name"] in ("execution.results.status", "execution.results.collect"))
    assignment = intent["assignment"]
    _closed(assignment, ("version", "handoff_ref", "selector"))
    _require(assignment["version"] == "execution_results_assignment_v1")
    return _receipt_fields({"version": _RECEIPT_VIEW, "tool_name": intent["tool_name"],
        "selector": assignment["selector"], "observation": _observation(value["observation"]),
        "facts": value["facts"], "delivery_complete": value["delivery_complete"]})


def select_atac_execution_values(value):
    """Recognize exact records before generic execution tracking filters."""
    if not isinstance(value, Mapping):
        return None
    try:
        value = deepcopy(dict(value))
        if set(value) == {"argv", "environment", "native_atac_differential"}:
            from .native_atac_differential_contracts import validate_atac_requested_job
            requested = validate_atac_requested_job(value)
            return atac_scientific_job_view(requested["native_atac_differential"])
        if set(value) == {"request", "software", "input_bindings"}:
            return atac_scientific_job_view(value)
        version = value.get("version")
        if version == _JOB_VIEW:
            return _job_view(value)
        if version == _SELECTOR:
            return _selector(value)
        if version == _PROJECTION:
            return validate_atac_result_record("RequestedProjection", value)
        if version == _RECEIPT:
            return _receipt_view(value)
        if version == _RECEIPT_VIEW:
            return _receipt_fields(value, labels=True)
        if set(value) == {"sheet", "tables"}:
            return validate_atac_result_record("SavedSheetBundle", value)
        if set(value) == {"artifact_ref", "sha256", "size_bytes", "format"}:
            file = validate_atac_result_record("NativeFileIdentity", value)
            _require(file["format"] in ("bam", SHEET_FORMAT, TABLE_FORMAT))
            return file
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError):
        return None
    return None


def select_atac_presentation(state, *, lookup_results=()):
    """Gather requested projections only from existing report/outcome slots."""
    if not isinstance(state, Mapping):
        return {"context": state, "lookup_results": lookup_results, "projections": []}
    projections, identities = [], {}

    def project(value):
        if isinstance(value, Mapping):
            version = value.get("version")
            if version == _PROJECTION:
                selected = select_atac_execution_values(value)
                if selected is None:
                    return deepcopy(value)
                key = canonical(selected)
                if key not in identities:
                    identities[key] = len(projections) + 1
                    projections.append(selected)
                return _LABEL + str(identities[key])
            if version in (_RECEIPT, _RECEIPT_VIEW):
                selected = select_atac_execution_values(value)
                if selected is None:
                    return deepcopy(value)
                return {key: project(child) for key, child in selected.items()}
            if set(value) == {"sheet", "tables"}:
                selected = select_atac_execution_values(value)
                if selected is not None:
                    return selected
            if "version" in value:
                return deepcopy(value)
            return {key: deepcopy(child) if key in _OPAQUE_SLOTS else project(child)
                for key, child in value.items()}
        if isinstance(value, (list, tuple)):
            return [project(child) for child in value]
        return deepcopy(value)

    shown = deepcopy(dict(state))
    for channel in _CHANNELS:
        if channel in shown:
            shown[channel] = project(shown[channel])
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


def _properties(value, *, units=None):
    units = {} if units is None else units
    return _table(("Field", "Literal stored value", "Unit or meaning"),
        ((name, _literal(child), units.get(name, "declared field")) for name, child in value.items()))


def _issue_table(issues):
    return _table(("Code", "Binding", "Row ordinals", "Native locations", "Field", "Requirement"),
        ((row["code"], row["binding_key"], _literal(row["row_ordinals"]),
            _literal(row["locations"]), _literal(row["field"]), row["requirement"]) for row in issues))


def _qualifications(projection):
    return ["Recorded native/data qualifications", "", _issue_table(projection["qualifications"]),
        "", "Recorded located failures", "",
        _table(("Code", "Stage", "Step", "File role", "Binding", "Native location", "Field", "Requirement"),
            ((row["code"], row["stage"], _literal(row["step_key"]), _literal(row["file_key"]),
                _literal(row["binding_key"]), _literal(row["locator"]), _literal(row["field_path"]),
                row["requirement"]) for row in projection["failures"]))]


def _native_source(source):
    return {name: deepcopy(source[name]) for name in ("format", "supplied_extent", "producer_outcome",
        "writer_closed", "producer_name", "producer_version", "origin")}


def _peak_row(selected):
    row = selected["row"]
    return ["Native occurrence and representation", "", _properties({
        "callpeak_run_key": selected["callpeak_run_key"], "representation": selected["representation"],
        "row_ordinal": row["row_ordinal"], "locator": row["locator"], "original_fields": row["original_fields"]}),
        "", _properties({name: value for name, value in row.items()
            if name not in ("row_ordinal", "locator", "original_fields")}, units=_PEAK_UNITS),
        "", "Stored coordinate geometry", "", _literal(None) if selected["geometry"] is None else
        _properties(selected["geometry"], units={"start0": "bp; zero_based_half_open",
            "end0": "bp; zero_based_half_open", "summit0": "bp; zero_based", "span_bp": "bp"}),
        "", "Stored representation correspondence", "", _literal(None) if selected["peak_link"] is None
            else _properties(selected["peak_link"]), "", "Native source qualifications", "",
        _properties(_native_source(selected["source"]))]


def _differential_row(selected):
    return ["Native reported differential row", "", _properties({
        "category": selected["category"], "coordinate_qualification": selected["coordinate_qualification"]}),
        "", _properties(selected["row"], units={"reported_start0": "bp; zero_based_half_open_as_reported",
            "reported_end0": "bp; zero_based_half_open_as_reported", "reported_score": "native reported score"}),
        "", "Native source qualifications", "", _properties(_native_source(selected["source"]))]


def _measurements(values):
    return _table(("Field", "Literal value", "Unit", "State", "Reason"),
        ((name, _literal(value["value"]), value["unit"], value["state"], _literal(value["reason"]))
            for name, value in values.items()))


def _component_row(row):
    scores = row["scores"]
    parts = ["Stored calculation interval and input populations", "",
        _properties({name: value for name, value in row.items() if name != "scores"},
            units={"start": "bp; zero_based_half_open", "end": "bp; zero_based_half_open",
                "values": "original four-track values; no missing-to-zero conversion"}), "",
        "Recorded likelihood method and arithmetic precision", "",
        _properties({"method": scores["method"], "parameters": scores["parameters"],
            "inputs": scores["inputs"]}), "", "Native input values", "",
        _measurements(scores["native_input_values"]), "", "Recorded depth factors", "",
        _measurements(scores["depth_factors"]), "", "Depth-adjusted values", "",
        _measurements(scores["adjusted_values"]), "", "Separate likelihood comparisons", "",
        _table(("Comparison", "Operands", "Representation", "Literal value", "Unit", "State", "Reason"),
            ((name, _literal(likelihood["operands"]), representation, _literal(measurement["value"]),
                measurement["unit"], measurement["state"], _literal(measurement["reason"]))
                for name, likelihood in scores["likelihoods"].items()
                for representation in ("unrounded", "native_float32")
                for measurement in (likelihood[representation],))), "", "Numerical input qualifications", "",
        _table(("Field", "Reason"), ((value["field"], value["reason"]) for value in scores["input_issues"])),
        "", "Uncertainty", "", _literal(scores["uncertainty"])]
    return parts


def _depth_selection(value):
    parts = [_properties({name: value[name] for name in ("kind", "compatible_population")})]
    for row in value["conditions"]:
        parts.extend(["", _properties({name: child for name, child in row.items()
            if name != "source_artifact_ref"})])
    parts.extend(["", _issue_table(value["issues"])])
    return parts


def _summary(value):
    return ["Summary record availability does not upgrade any inner population extent or null.", "",
        "Recorded depth selection and count populations", "", *_depth_selection(value["depth_selection"]), "",
        "Stored depth operands", "", _properties(value["depth_operands"]), "",
        _properties({"selected_population_bp": value["selected_population_bp"]},
            units={"selected_population_bp": "bp in selected calculation intervals"}), "",
        "Four-track partition coverage", "", _properties(value["partition_coverage"],
            units={"all_four_observed_bp": "bp", "unavailable_or_invalid_bp": "bp"}), "",
        "Native peak occurrences by original representation", "",
        _table(("Run", "Representation", "Literal count", "Unit", "Extent"),
            ((row["run_key"], row["representation"], _literal(row["count"]), "native occurrences", row["extent"])
                for row in value["native_peak_counts"])), "",
        "Native reported differential populations", "",
        _table(("Category", "Literal count", "Unit", "Extent", "Coordinate qualification"),
            ((row["category"], _literal(row["count"]), "native reported rows", row["extent"],
                row["coordinate_qualification"]) for row in value["native_region_counts"])), "",
        "Derived calculation-region populations", "",
        _table(("Category", "Literal count", "Qualifying bp", "Span bp", "Extent"),
            ((row["category"], _literal(row["count"]), _literal(row["qualifying_bp"]),
                _literal(row["span_bp"]), row["extent"]) for row in value["derived_region_counts"])), "",
        "Recorded reference, normalization, coverage and uncertainty", "",
        _properties({name: value[name] for name in ("reference_relation", "normalization_compatibility",
            "coverage_completeness", "uncertainty")})]


def render_atac_projections(projections):
    """Render exact requested values without recalculating or rescanning."""
    parts = []
    for number, value in enumerate(projections, 1):
        projection = validate_atac_result_record("RequestedProjection", value)
        parts.extend([_LABEL + str(number), "", _properties({name: projection[name] for name in
            ("comparison_key", "reference_id", "condition_ids", "kind", "row_window", "total_rows", "row_extent")}),
            "", "Selected RESULT calculation parameters", "", _properties(projection["parameters"]), "",
            "Selected calculation intervals", "", _literal(projection["selected_intervals"]), "",
            "Calculation intervals and RESULT parameters govern derived calculations. They do not imply that "
            "native rows were interval-clipped or generated under these result parameters. Original native "
            "callpeak/bdgdiff settings remain the separate selected job request.", "",
            "Native rows use selected runs/categories and their original occurrence order. Native counts are "
            "original-report populations; XLS, narrowPeak and summit representations must not be summed as "
            "independent peaks. A null is unavailable, while an observed zero remains zero.", ""])
        kind = projection["kind"]
        if kind == "summary":
            parts.extend(_summary(projection["summary"]))
        else:
            if not projection["rows"]:
                parts.extend(["Stored selected rows", "", "[]"])
            for ordinal, row in enumerate(projection["rows"], 1):
                parts.extend(["", "Selected stored row " + str(ordinal), ""])
                if kind == "native_peak_rows":
                    parts.extend(_peak_row(row))
                elif kind == "native_differential_rows":
                    parts.extend(_differential_row(row))
                elif kind == "interval_components":
                    parts.extend(_component_row(row))
                else:
                    parts.extend(["Stored derived region", "", _properties(row, units=_REGION_UNITS), "",
                        "score_denominator_bp is qualifying bp; bridged_gap_bp is excluded from that denominator."])
        parts.extend(["", *_qualifications(projection)])
    return "\n".join(parts)


__all__ = ["atac_scientific_job_view", "select_atac_execution_values",
    "select_atac_presentation", "render_atac_projections"]
