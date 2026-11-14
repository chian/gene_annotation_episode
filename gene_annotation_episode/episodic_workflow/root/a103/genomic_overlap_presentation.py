"""Literal views of already calculated genomic-overlap results.

These views neither authenticate a result nor calculate measurements.  The
existing closed record validators own the scientific shapes.  Presentation
selection is restricted to result/report channels, and retains callable saved
File identities without turning provenance into reference permissions.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re

from jsonschema import FormatChecker

from .genomic_overlap_contracts import (
    _StrictValidator, _finite_json_copy, genomic_overlap_schema,
    validate_genomic_overlap_record,
)
from .genomic_overlap_return_views import (
    FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE,
    validate_genomic_overlap_fact_values,
)
from .native_genomic_overlap_contracts import (
    validate_genomic_overlap_job, validate_genomic_overlap_requested_job,
)


_JOB_VIEW = "genomic_overlap_scientific_job_view_v1"
_RECEIPT_VIEW = "genomic_overlap_result_receipt_view_v1"
_RECEIPT = "native_genomic_overlap_acquired_result_v1"
_LABEL = "Selected genomic overlap result "
_LABEL_PATTERN = re.compile(r"Selected genomic overlap result [1-9][0-9]*\Z")
_RECEIPT_KEYS = frozenset((
    "version", "intent", "handoff_proof", "original_origins", "observation",
    "native", "source_action_file", "writer_closure_file", "capture",
    "worker_plan", "worker_capture", "worker_execution", "qualified_files",
    "projection", "host_failures", "facts", "acquisition_evidence",
    "acquired_population", "delivery_complete",
))
_INTENT_KEYS = frozenset((
    "version", "run_id", "episode_id", "path", "scope", "assignment",
    "original_request_sha256", "operation_key", "tool_name", "arguments", "target",
))
_VIEW_KEYS = frozenset((
    "version", "tool_name", "selector", "observation", "delivery_complete", "facts",
))
_OBSERVATION_KEYS = frozenset((
    "state", "returncode", "result_available", "failure_code", "terminal", "quiescent",
))
_OPAQUE_SLOTS = frozenset((
    "instructions", "schema", "schemas", "report_schema", "requested_form",
    "input_schema", "output_schema", "result_selector_schema", "schema_json",
    "tools", "tool_schema", "tool_schemas", "arguments", "input", "inputs",
    "input_data", "request", "assignment", "selected_execution_task",
))


def _require(condition):
    if not condition:
        raise ValueError("genomic_overlap_presentation_shape")


def _selector(value):
    value = validate_genomic_overlap_record("Selector", value)
    _require(len(set(value["comparison_keys"])) == len(value["comparison_keys"]))
    for name in ("minimum_a_fraction", "minimum_b_fraction"):
        fraction = value["parameters"][name]
        _require(fraction["numerator"] <= fraction["denominator"])
    projection = value["projection"]
    occurrences = [(row["set_key"], row["occurrence_key"])
        for row in projection["occurrence_keys"]]
    _require(len(set(occurrences)) == len(occurrences))
    _require(projection["kind"] == "occurrence_rows" or not occurrences)
    if value["saved_sheet_file"] is not None:
        validate_genomic_overlap_fact_values(SAVED_SOURCE, [value["saved_sheet_file"]])
    return value


def _scientific_request(value):
    """Validate the original scientific fields, without output-file naming."""
    value = _finite_json_copy(value)
    schema = genomic_overlap_schema("Request")
    definition = schema["$defs"]["Request"]
    del definition["properties"]["output_prefix"]
    definition["required"].remove("output_prefix")
    _require(_StrictValidator(schema, format_checker=FormatChecker()).is_valid(value))
    specs, comparisons = value["region_sets"], value["comparisons"]
    keys = [row["set_key"] for row in specs]
    _require(len(keys) == len(set(keys)))
    endpoints = [(a, b) for i, a in enumerate(keys) for b in keys[i + 1:]]
    _require(len(comparisons) == len(endpoints)
        and len({row["comparison_key"] for row in comparisons}) == len(comparisons))
    for ordinal, (row, ends) in enumerate(zip(comparisons, endpoints)):
        _require(row["ordinal"] == ordinal and (row["a_set_key"], row["b_set_key"]) == ends)
    artifacts = {}
    for row in specs:
        source = row["source"]
        kind = "bed_artifact" if row["format"] == "bed_outer_span_v1" else "coordinate_rows_artifact"
        _require(source["kind"] == kind and source["file"]["format"] == row["format"])
        identity = source["file"]
        prior = artifacts.setdefault(identity["artifact_ref"], identity)
        _require(prior == identity)
    return value


def genomic_overlap_scientific_job_view(job):
    """Keep scientific inputs/settings, omitting the native output-file prefix."""
    job = validate_genomic_overlap_job(job)
    request = deepcopy(job["request"])
    del request["output_prefix"]
    return {"version": _JOB_VIEW, "request": _scientific_request(request)}


def _facts(value, *, labels=False):
    _require(type(value) is dict and set(value) == set(FACT_SOURCES))
    result = {}
    for source in FACT_SOURCES:
        rows = value[source]
        _require(type(rows) is list)
        if source == PROJECTION_SOURCE and labels:
            result[source] = []
            for row in rows:
                if type(row) is str and _LABEL_PATTERN.fullmatch(row):
                    result[source].append(row)
                else:
                    result[source].append(validate_genomic_overlap_record("Projection", row))
        else:
            result[source] = validate_genomic_overlap_fact_values(source, rows)
    return result


def _observation(value, *, public=False):
    if value is None:
        return None
    _require(type(value) is dict)
    if public:
        _require(set(value) == _OBSERVATION_KEYS)
        result = deepcopy(value)
    else:
        native = value.get("native")
        _require(type(native) is dict)
        result = {name: deepcopy(value.get(name)) for name in
            ("state", "returncode", "result_available", "failure_code")}
        result.update({name: deepcopy(native.get(name)) for name in ("terminal", "quiescent")})
    _require(type(result["state"]) is str and bool(result["state"]))
    _require(result["returncode"] is None or type(result["returncode"]) is int)
    _require(type(result["result_available"]) is bool)
    _require(result["failure_code"] is None or type(result["failure_code"]) is str)
    _require(all(type(result[name]) is bool for name in ("terminal", "quiescent")))
    return result


def _receipt_view(value):
    """Select public facts, never private receipt controls or worker envelopes.

    This is a presentation shape check, not the result owner's authentication.
    Only the public fact lists are validated or traversed as scientific values.
    """
    _require(type(value) is dict)
    if value.get("version") == _RECEIPT_VIEW:
        _require(set(value) == _VIEW_KEYS)
        selector = _selector(value["selector"])
        observation = _observation(value["observation"], public=True)
        facts = _facts(value["facts"], labels=True)
        tool_name = value["tool_name"]
    else:
        _require(value.get("version") == _RECEIPT and set(value) == _RECEIPT_KEYS)
        intent = value["intent"]
        _require(type(intent) is dict and set(intent) == _INTENT_KEYS
            and intent["version"] == "genomic_overlap_result_intent_v1"
            and intent["arguments"] == {})
        assignment = intent["assignment"]
        _require(type(assignment) is dict
            and set(assignment) == {"version", "handoff_ref", "selector"}
            and assignment["version"] == "execution_results_assignment_v1")
        selector = _selector(assignment["selector"])
        observation = _observation(value["observation"])
        facts = _facts(value["facts"])
        tool_name = intent["tool_name"]
    _require(tool_name in ("execution.results.status", "execution.results.collect")
        and type(value["delivery_complete"]) is bool)
    return {"version": _RECEIPT_VIEW, "tool_name": tool_name, "selector": selector,
        "observation": observation, "delivery_complete": value["delivery_complete"],
        "facts": facts}


def select_genomic_overlap_execution_values(value):
    """Recognize exact safe values before generic execution tracking filters."""
    if type(value) is not dict:
        return None
    try:
        version = value.get("version")
        if version == "native_genomic_overlap_job_v1":
            return genomic_overlap_scientific_job_view(value)
        if "native_genomic_overlap" in value:
            job = validate_genomic_overlap_requested_job(value)
            return genomic_overlap_scientific_job_view(job["native_genomic_overlap"])
        if version == _JOB_VIEW:
            _require(set(value) == {"version", "request"})
            return {"version": _JOB_VIEW, "request": _scientific_request(value["request"])}
        if version == "genomic_overlap_result_selector_v1":
            return _selector(value)
        if version == "genomic_overlap_projection_v1":
            return validate_genomic_overlap_record("Projection", value)
        if version in (_RECEIPT, _RECEIPT_VIEW):
            return _receipt_view(value)
        if set(value) == {"artifact_ref", "sha256", "size_bytes", "format"}:
            return validate_genomic_overlap_fact_values(SAVED_SOURCE, [value])[0]
    except (ValueError, TypeError, KeyError):
        return None
    return None


def select_genomic_overlap_presentation(state, *, lookup_results=()):
    """Gather existing projections only in actual result/report channels.

    Unknown versioned records and request/schema/input slots are opaque.  A
    receiving root needs no scientific ToolInfo: a validated Projection in one
    of these declared public channels is sufficient for literal presentation.
    """
    context = deepcopy(state)
    lookups = deepcopy(list(lookup_results))
    projections, identities = [], {}

    def projection_label(value):
        projection = validate_genomic_overlap_record("Projection", value)
        identity = json.dumps(projection, sort_keys=True, ensure_ascii=False,
            allow_nan=False, separators=(",", ":"))
        if identity not in identities:
            identities[identity] = len(projections) + 1
            projections.append(projection)
        return _LABEL + str(identities[identity])

    def walk(value):
        if type(value) is list:
            return [walk(row) for row in value]
        if type(value) is not dict:
            return deepcopy(value)
        version = value.get("version")
        if version == "genomic_overlap_projection_v1":
            try:
                return projection_label(value)
            except (ValueError, TypeError, KeyError):
                return deepcopy(value)
        if version in (_RECEIPT, _RECEIPT_VIEW):
            try:
                view = _receipt_view(value)
            except (ValueError, TypeError, KeyError):
                return deepcopy(value)
            view["facts"][PROJECTION_SOURCE] = [
                projection_label(row) if type(row) is dict else row
                for row in view["facts"][PROJECTION_SOURCE]]
            return view
        if "version" in value:
            return deepcopy(value)
        return {key: deepcopy(child) if key in _OPAQUE_SLOTS else walk(child)
            for key, child in value.items()}

    if type(context) is dict:
        for channel in ("last_local_outcome", "child_reports", "current_report_update"):
            if channel in context:
                context[channel] = walk(context[channel])
    lookups = [walk(value) for value in lookups]
    return {"context": context, "lookup_results": lookups, "projections": projections}


def _literal(value):
    if value is None:
        return "null"
    if type(value) is str:
        return value
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _table(headers, rows):
    rows = list(rows)
    if not rows:
        return "No retained rows in this table."

    def cell(value):
        return _literal(value).replace("|", "\\|").replace("\r", "\\r").replace("\n", "<br>")

    return "\n".join(["| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)])


def _unit(field):
    if field == "input_data_row_count":
        return "input data rows"
    if field == "partner_count":
        return "partner occurrences"
    if field == "coordinate_locus_count":
        return "coordinate loci"
    if field in ("span_bp", "covered_bp") or field.endswith("_bp") or "bp_sum" in field:
        return "bp"
    if "fraction" in field or field == "jaccard_bp":
        return "fraction"
    if "pair" in field and field != "pair_keys":
        return "occurrence pairs"
    if field == "pair_keys":
        return "pair identities"
    return "region occurrences"


def _measurement(value):
    if type(value) is dict:
        return (value["value"], value["numerator"], value["denominator"], value["missing_reason"])
    return (value, None, None, None)


def _reference_text(reference):
    if reference is None:
        return "No supplied reference metadata"
    parts = ["assembly_accession_version=" + _literal(reference["assembly_accession_version"]),
        "assembly_label=" + _literal(reference["assembly_label"]),
        "source_refs=" + _literal(reference["source_refs"])]
    if reference["sequence_dictionary"] is not None:
        parts.append("sequence_dictionary=" + _literal(reference["sequence_dictionary"]))
    for contig in reference["contigs"]:
        parts.append("contig " + contig["chromosome"] + ": " + "; ".join(
            name + "=" + _literal(contig[name]) for name in
            ("length_bp", "sequence_accession_version", "sequence_sha256", "source_refs")))
    return "; ".join(parts)


def _failure_rows(failures):
    return [(row["code"], row["stage"], row["set_key"], row["comparison_key"],
        row["locator"], row["field_path"], row["expected_value"], row["observed_value"],
        row["requirement"]) for row in failures]


def render_genomic_overlap_projections(projections):
    """Render stored values and operands; never recompute a ratio or overlap."""
    sections = []
    for ordinal, value in enumerate(projections, 1):
        projection = validate_genomic_overlap_record("Projection", value)
        parameters, page = projection["parameters"], projection["page"]
        lines = [_LABEL + str(ordinal),
            "Kind: " + projection["kind"] + "; result extent: " + projection["result_extent"] + ".",
            _table(("Minimum overlap (bp)", "Minimum A fraction numerator", "A denominator",
                "Minimum B fraction numerator", "B denominator"), [(
                parameters["minimum_overlap_bp"], parameters["minimum_a_fraction"]["numerator"],
                parameters["minimum_a_fraction"]["denominator"],
                parameters["minimum_b_fraction"]["numerator"],
                parameters["minimum_b_fraction"]["denominator"])]),
            _table(("Page offset", "Limit", "Retained total rows", "Returned rows"), [(
                page["offset"], page["limit"], page["total_rows"], page["returned_rows"])]),
            "Requested measurement fields (ordered): " + "; ".join(projection["measurement_fields"]) + ".",
            "Page counts describe the retained projection population; paging does not establish completeness. "
            "Null remains unavailable, and observed zero remains zero. "
            "Pairwise overlap sums count occurrence pairs; union lengths count unique covered bases. "
            "Selected shared-union fractions retain the original combined-union denominator. "
            "Lower-bound subsets do not establish complete absence or reference equivalence."]
        if projection["kind"] == "pair_metrics":
            lines.append(_table(("Comparison", "A set", "B set", "Extent", "Interpretation", "Reference"),
                [(row["comparison_key"], row["a_set_key"], row["b_set_key"], row["result_extent"],
                    row["observed_interpretation"], row["reference_relation"])
                    for row in projection["pair_rows"]]))
            rows = []
            for row in projection["pair_rows"]:
                for qualified in projection["measurement_fields"]:
                    population, separator, field = qualified.partition(".")
                    measured = row["measurements"]
                    if separator and qualified in measured:
                        number, numerator, denominator, reason = _measurement(measured[qualified])
                        rows.append((row["comparison_key"], population, field, number,
                            "fraction" if type(measured[qualified]) is dict else _unit(field),
                            numerator, denominator, reason, row["result_extent"], row["reference_relation"]))
            lines.append(_table(("Comparison", "Population", "Measurement", "Value", "Unit",
                "Numerator", "Denominator", "Missing reason", "Extent", "Reference"), rows))
        elif projection["kind"] == "set_metrics":
            rows = []
            for row in projection["set_rows"]:
                for field in projection["measurement_fields"]:
                    if field in row["measurements"]:
                        number, numerator, denominator, reason = _measurement(row["measurements"][field])
                        rows.append((row["set_key"], field, number, _unit(field), reason, row["result_extent"]))
            lines.append(_table(("Set", "Measurement", "Value", "Unit", "Missing reason", "Extent"), rows))
        else:
            rows = []
            for row in projection["occurrence_rows"]:
                for field in projection["measurement_fields"]:
                    if field in row["measurements"]:
                        number, numerator, denominator, reason = _measurement(row["measurements"][field])
                        rows.append((row["comparison_key"], row["population"], row["set_key"],
                            row["occurrence_key"], field, number,
                            "fraction" if type(row["measurements"][field]) is dict else _unit(field),
                            numerator, denominator, reason, row["result_extent"]))
            lines.append(_table(("Comparison", "Population", "Set", "Occurrence", "Measurement", "Value",
                "Unit", "Numerator", "Denominator", "Missing reason", "Extent"), rows))
        lines.append(_table(("Comparison", "A set", "B set", "Reference relation", "Basis",
            "Supplied A reference", "Supplied B reference"), [(row["comparison_key"],
            row["a_set_key"], row["b_set_key"], row["relation"], row["basis"],
            _reference_text(row["a_reference"]), _reference_text(row["b_reference"]))
            for row in projection["reference_relations"]]))
        failures = list(projection["failures"])
        for row in (*projection["pair_rows"], *projection["set_rows"], *projection["reference_relations"]):
            for failure in row["issues"]:
                if failure not in failures:
                    failures.append(failure)
        if failures:
            lines.append(_table(("Qualification", "Stage", "Set", "Comparison", "Original locator",
                "Field", "Expected", "Observed", "Requirement"), _failure_rows(failures)))
        sections.append("\n\n".join(lines))
    return "\n\n".join(sections)


__all__ = ["genomic_overlap_scientific_job_view", "select_genomic_overlap_execution_values",
    "select_genomic_overlap_presentation", "render_genomic_overlap_projections"]
