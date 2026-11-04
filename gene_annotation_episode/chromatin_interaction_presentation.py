"""Pure literal views of the existing selected chromatin records.

These views do not authenticate a producer, acquire a File, calculate a value,
or change a report.  The result owners retain those responsibilities.  Saved
File identities remain complete because they are operands for later calls.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import re

from .chromatin_interaction_contracts import (
    _STRICT_VALIDATOR, canonical_chromatin_record, chromatin_record_schema,
    validate_chromatin_record,
)
from .chromatin_interaction_return_views import (
    FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE, validate_chromatin_fact_values,
)


_JOB_VIEW = "chromatin_scientific_job_view_v1"
_RECEIPT_VIEW = "chromatin_result_receipt_view_v1"
_PROJECTION = "chromatin_interaction_projection_v1"
_SELECTOR = "chromatin_interaction_result_selector_v1"
_RECEIPT = "native_chromatin_interaction_acquired_result_v1"
_LABEL = "Selected chromatin projection "
_LABEL_PATTERN = re.compile(r"Selected chromatin projection [1-9][0-9]*\Z")
_CHANNELS = ("last_local_outcome", "child_reports", "current_report_update")
_OPAQUE_SLOTS = frozenset((
    "instructions", "schema", "schemas", "report_schema", "requested_form",
    "input_schema", "output_schema", "result_selector_schema", "schema_json",
    "tools", "tool_schema", "tool_schemas", "arguments", "request",
    "input", "inputs", "input_data", "assignment", "selected_task",
    "selected_execution_task",
))


def _require(condition):
    if not condition:
        raise ValueError("chromatin_presentation_invalid")


def _closed(value, keys):
    _require(type(value) is dict and set(value) == set(keys))


def _same(left, right):
    return canonical_chromatin_record(left) == canonical_chromatin_record(right)


def _scientific_request(value):
    """Validate the original request fields apart from output-file naming."""
    schema = chromatin_record_schema("ChromatinRequest")
    definition = schema["$defs"]["ChromatinRequest"]
    del definition["properties"]["output_prefix"]
    definition["required"].remove("output_prefix")
    canonical_chromatin_record(value)
    _require(_STRICT_VALIDATOR(schema).is_valid(value))
    # Reuse the original structural relationships that do not concern the
    # omitted output name.  No replacement request or output path is invented.
    populations = value["populations"]
    _require(len({row["population_key"] for row in populations}) == len(populations))
    for row in populations:
        validate_chromatin_record("PopulationSpec", row)
    validate_chromatin_record("MetadataSpec", value["supplied_metadata"])
    if value["elements"] is not None:
        validate_chromatin_record("ElementSpec", value["elements"])
    _require(all(row["contact_input_key"] == value["contact"]["input_key"]
        for row in value["supplied_metadata"]["contact_sample_links"]))
    _require(not (value["contact"]["format"] == "hic_binary_v9"
        and value["normalization"]["kind"] == "precomputed_weighted")
        or value["normalization"]["convention"] == "divisive")
    return deepcopy(value)


def _job_view(value):
    _closed(value, ("version", "request", "inputs"))
    _require(value["version"] == _JOB_VIEW)
    request = _scientific_request(value["request"])
    specs = [request["contact"]] + ([] if request["elements"] is None else [request["elements"]])
    _require(len({row["input_key"] for row in specs}) == len(specs))
    _require(all(row["file"]["format"] == row["format"] for row in specs))
    expected = [{"input_key": row["input_key"], "file": row["file"]} for row in specs]
    _require(_same(value["inputs"], expected))
    return {"version": _JOB_VIEW, "request": request, "inputs": deepcopy(expected)}


def chromatin_scientific_job_view(job):
    """Select scientific inputs and settings from a validated native job."""
    from .native_chromatin_interaction_contracts import validate_chromatin_job
    job = validate_chromatin_job(job)
    request = deepcopy(job["request"])
    del request["output_prefix"]
    return _job_view({"version": _JOB_VIEW, "request": request,
        "inputs": [{"input_key": row["input_key"], "file": deepcopy(row["file"])}
            for row in job["input_bindings"]]})


def _selector(value):
    value = validate_chromatin_record("ResultSelector", value)
    if value["saved_sheet_bundle"] is not None:
        validate_chromatin_fact_values(SAVED_SOURCE, [value["saved_sheet_bundle"]])
    return value


def _facts(value, *, labels=False):
    _closed(value, FACT_SOURCES)
    result = {}
    for source in FACT_SOURCES:
        rows = value[source]
        _require(type(rows) is list)
        if source == PROJECTION_SOURCE and labels:
            result[source] = [row if type(row) is str and _LABEL_PATTERN.fullmatch(row)
                else validate_chromatin_record("RequestedProjection", row) for row in rows]
        else:
            result[source] = validate_chromatin_fact_values(source, rows)
    return result


def _observation(value):
    """Retain the observed outcome, without the native control envelope."""
    if value is None:
        return None
    _require(type(value) is dict)
    return {key: deepcopy(value[key]) for key in
        ("state", "returncode", "failure_code", "result_available")}


def _receipt_fields(value, *, labels=False):
    """Check the public part of a receipt view, without receipt-owner I/O."""
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
        _require(_STRICT_VALIDATOR(schema).is_valid(observation))
    for projection in facts[PROJECTION_SOURCE]:
        if type(projection) is str:
            # Only an already-selected presentation label can occur here;
            # labels are never admitted as raw scientific fact records.
            continue
        _require(_same(projection["parameters"], selector["parameters"])
            and projection["kind"] == selector["projection"]["kind"]
            and projection["requested_fields"] == selector["projection"]["fields"]
            and projection["population_keys"] == selector["population_keys"])
        selection = selector["projection"].get("selection", {})
        if selection.get("by") == "page":
            page = projection["page"]
            _require(type(page) is dict and page["offset"] == selection["page"]["offset"]
                and page["returned_count"] <= selection["page"]["limit"])
        else:
            _require(projection["page"] is None)
    if value["tool_name"] == "execution.results.status":
        _require(not value["delivery_complete"] and all(not rows for rows in facts.values()))
    return {"version": _RECEIPT_VIEW, "tool_name": value["tool_name"], "selector": selector,
        "observation": deepcopy(observation), "facts": facts,
        "delivery_complete": value["delivery_complete"]}


def _receipt_view(value):
    """Select public facts from an exact carrier; do not verify its controls."""
    from .chromatin_interaction_result_receipts import (
        ChromatinInteractionResultIntent, ChromatinInteractionResultReceipt,
    )
    _closed(value, ChromatinInteractionResultReceipt.__annotations__)
    _require(value["version"] == _RECEIPT)
    intent = value["intent"]
    _closed(intent, ChromatinInteractionResultIntent.__annotations__)
    _require(intent["version"] == "chromatin_interaction_result_intent_v1"
        and intent["tool_name"] in ("execution.results.status", "execution.results.collect"))
    assignment = intent["assignment"]
    _closed(assignment, ("version", "handoff_ref", "selector"))
    _require(assignment["version"] == "execution_results_assignment_v1")
    return _receipt_fields({"version": _RECEIPT_VIEW, "tool_name": intent["tool_name"],
        "selector": assignment["selector"], "observation": _observation(value["observation"]),
        "facts": value["facts"], "delivery_complete": value["delivery_complete"]})


def select_chromatin_execution_values(value):
    """Recognize only existing chromatin records and this finite safe view."""
    if not isinstance(value, Mapping):
        return None
    try:
        value = deepcopy(dict(value))
        if set(value) == {"argv", "environment", "native_chromatin_interactions"}:
            from .native_chromatin_interaction_contracts import validate_chromatin_requested_job
            requested = validate_chromatin_requested_job(value)
            return {"native_chromatin_interactions":
                chromatin_scientific_job_view(requested["native_chromatin_interactions"])}
        if set(value) == {"request", "software", "input_bindings"}:
            return chromatin_scientific_job_view(value)
        if set(value) == {"native_chromatin_interactions"}:
            return {"native_chromatin_interactions": _job_view(value["native_chromatin_interactions"])}
        version = value.get("version")
        if version == _JOB_VIEW:
            return _job_view(value)
        if version == _SELECTOR:
            return _selector(value)
        if version == _PROJECTION:
            return validate_chromatin_record("RequestedProjection", value)
        if version == _RECEIPT:
            return _receipt_view(value)
        if version == _RECEIPT_VIEW:
            return _receipt_fields(value, labels=True)
        if set(value) == {"sheet", "tables"}:
            return validate_chromatin_fact_values(SAVED_SOURCE, [value])[0]
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError):
        return None
    return None


def select_chromatin_presentation(state, *, lookup_results=()):
    """Detach exact projections from supplied outcome/report channels only."""
    if not isinstance(state, Mapping):
        return {"context": state, "lookup_results": lookup_results, "projections": []}
    projections, keys = [], []

    def project(value):
        if isinstance(value, Mapping):
            if value.get("version") == _PROJECTION:
                selected = select_chromatin_execution_values(value)
                if selected is None:
                    return deepcopy(value)
                key = canonical_chromatin_record(selected)
                if key not in keys:
                    keys.append(key)
                    projections.append(selected)
                return _LABEL + str(keys.index(key) + 1)
            if value.get("version") in (_RECEIPT, _RECEIPT_VIEW):
                selected = select_chromatin_execution_values(value)
                if selected is None:
                    return deepcopy(value)
                # The private projection sibling is not an additional requested
                # fact.  Only the receipt's already-published facts enter here.
                return {key: project(child) for key, child in selected.items()}
            if set(value) == {"sheet", "tables"}:
                selected = select_chromatin_execution_values(value)
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


def render_chromatin_projections(projections):
    """Render literal stored cells, including nulls and ratio operands."""
    parts = []
    for index, value in enumerate(projections, 1):
        projection = validate_chromatin_record("RequestedProjection", value)
        parts.extend([_LABEL + str(index), "",
            _table(("Projection property", "Literal value"), ((name, _literal(projection[name]))
                for name in ("kind", "population_keys", "requested_fields", "parameters", "page"))), "",
            "Stored selected rows", "",
            _table(("Row", "Original associations", "Qualifications"),
                ((str(number), _literal({key: child for key, child in row.items()
                    if key not in ("fields", "qualifications")}), _literal(row["qualifications"]))
                    for number, row in enumerate(projection["rows"], 1))), "",
            _table(("Row", "Population", "Field", "Literal value", "Unit (numeric)", "State", "Reason",
                    "Numerator", "Denominator", "Uncertainty (numeric)"),
                ((str(number), component["population_key"], name, _literal(component["value"]),
                    _literal(component.get("unit")), component["state"], _literal(component["reason"]),
                    _literal(component.get("numerator")), _literal(component.get("denominator")),
                    _literal(component.get("uncertainty")))
                    for number, row in enumerate(projection["rows"], 1)
                    for name in projection["requested_fields"]
                    for component in (row["fields"][name],))), "",
            "Stored population qualifications", "",
            _table(("Property", "Literal value"), ((str(number), _literal(row))
                for number, row in enumerate(projection["qualifications"], 1))), "",
            "Recorded located failures", "",
            _table(("Code", "Stage", "Input", "Population", "Element", "Pair", "Artifact", "Native location",
                    "Field", "Partial artifacts", "Requirement"),
                ((row["code"], row["stage"], _literal(row["input_key"]), _literal(row["population_key"]),
                    _literal(row["element_key"]), _literal(row["pair_key"]), _literal(row["artifact_ref"]),
                    _literal(row["locator"]), _literal(row["field_path"]), _literal(row["partial_artifact_refs"]),
                    row["requirement"]) for row in projection["failures"]))])
    return "\n".join(parts)


__all__ = ["chromatin_scientific_job_view", "select_chromatin_execution_values",
    "select_chromatin_presentation", "render_chromatin_projections"]
