"""Present the supplied ordinary API launch task in its existing conversation.

This module reads only detached model state. It neither authenticates inputs,
loads instructions, selects work nor calculates an expectation. Results and
other execution roles keep their existing presentation.
"""
from __future__ import annotations

from collections.abc import Mapping
import math
import re

from .scientific_process_prompt import _bounded_inputs, _scalar, _schema, _section, _table, _values, text_instructions


def is_api_launch_context(value):
    if not isinstance(value, Mapping):
        return False
    assignment = value.get("execution_assignment")
    return (isinstance(assignment, Mapping)
        and assignment.get("version") == "api_service_assignment_v1"
        and isinstance(assignment.get("request"), Mapping)
        and isinstance(assignment.get("service"), str)
        and value.get("api_service") == assignment["service"]
        and isinstance(value.get("api_request"), Mapping))


def _scope(scope):
    """Name the assigned set without exposing its opaque Store handles."""
    if not isinstance(scope, Mapping):
        return "Not supplied."
    subjects = scope.get("subject_refs", ())
    names = {reference: "assigned subject " + str(index + 1)
        for index, reference in enumerate(subjects)}
    rows = [("Subject", name) for name in names.values()]
    if "segments" in scope:
        for index, segment in enumerate(scope["segments"]):
            if not isinstance(segment, Mapping):
                continue
            subject = segment.get("target_ref", segment.get("subject_ref"))
            prefix = "Region " + str(index + 1)
            rows.append((prefix + " subject", names.get(subject, "assigned subject")))
            for field in ("start", "end", "unit", "strand"):
                if field in segment:
                    rows.append((prefix + " " + field, segment[field]))
            if "member_ref" in segment:
                rows.append((prefix + " member", "explicitly assigned original member"))
    else:
        rows.append(("Region", "The assigned subject set; no narrower interval supplied."))
    for index, _ in enumerate(scope.get("read_selection_refs", ())):
        rows.append(("Read selection", "assigned original-read selection " + str(index + 1)))
    return _table(("Scope item", "Supplied value"), rows)


def _requested_sources(schema):
    if isinstance(schema, Mapping):
        source = schema.get("x-source")
        if isinstance(source, str):
            yield source
        for child in schema.values():
            yield from _requested_sources(child)
    elif isinstance(schema, (list, tuple)):
        for child in schema:
            yield from _requested_sources(child)


def _task(state, instructions):
    assignment = state["execution_assignment"]
    goal = state.get("goal", {})
    goal = goal if isinstance(goal, Mapping) else {}
    context = goal.get("task_context", {})
    question = context.get("root_objective") if isinstance(context, Mapping) else None
    parts = ["TASK"]
    _section(parts, "Scientific QUESTION", question if isinstance(question, str) and question
        else "Not supplied in this recorded input.")
    _section(parts, "Assigned job", goal.get("objective", "Not supplied."))
    _section(parts, "Assigned scope", _scope(state.get("scope")))
    selected = {key: assignment[key] for key in ("resource_id", "service", "endpoint") if key in assignment}
    _section(parts, "Selected API work", _values(selected))
    _section(parts, "Parent constraints", _values(assignment.get("constraints", {})))
    resources = [row for row in state.get("execution_resource_capabilities", ())
        if isinstance(row, Mapping) and row.get("resource_id") == assignment.get("resource_id")]
    for resource in resources:
        _section(parts, "Configured resource", _values({key: resource[key] for key in
            ("resource_id", "resource_kind", "service", "base_url", "availability", "api_configuration_facts")
            if key in resource}))
    # Request values are scientific/native operands, not a host-state dump.
    # Their literal identifiers, order, omissions and processing profile stay
    # intact; they are never replaced with a rewritten query or guessed policy.
    _section(parts, "Exact assigned scientific request", _values(assignment["request"]))
    _section(parts, "Execution method and decision rules", text_instructions(instructions))
    for tool in state.get("tools", ()):
        if not isinstance(tool, Mapping) or "name" not in tool:
            continue
        _section(parts, "Callable operation: " + str(tool["name"]), tool.get("description", ""))
        if "instructions" in tool:
            _section(parts, "Supplied instructions for " + str(tool["name"]), tool["instructions"])
        if "input_schema" in tool:
            _section(parts, "Arguments for " + str(tool["name"]), _schema(tool["input_schema"], "arguments"))
    manuals = state.get("selected_launch_instructions") or {}
    for section in manuals.get("sections", ()):
        _section(parts, "Selected resource instructions: " + section["entry_id"] + " / " + section["section_id"],
            section["text"])
    _section(parts, "Information requested by the parent", state.get("requested_report_purpose"))
    form = state.get("requested_form")
    if form is not None:
        _section(parts, "Requested controlled JSON return", _schema(form, "return"))
        wanted = set(_requested_sources(form))
        sources = state.get("available_report_facts", {})
        meanings = [(name, row.get("meaning", "")) for name, row in sources.items()
            if name in wanted and isinstance(row, Mapping)]
        if meanings:
            _section(parts, "Meaning of requested recorded facts", _table(("Fact source", "Meaning"), meanings))
    return "\n".join(parts)


def _band(band):
    """Display recorded forecasts, never their unavailable code coordinates."""
    if not isinstance(band, Mapping):
        return "unavailable", "unavailable"
    status = band.get("status_code")
    if status not in (None, 0):
        return "unavailable", {-1: "insufficient completed actions", -2: "unidentifiable"}.get(status, "unavailable")
    if "value" not in band or band["value"] is None:
        return "unavailable", "unavailable"
    code = band.get("uncertainty_code")
    if code not in (0, 1, 2):
        return _scalar(band["value"]), "unavailable"
    qualification = {0: "exact", 1: "Chebyshev bound", 2: "approximate Laplace model band"}[code]
    bounds = [name + "=" + _scalar(band[name]) for name in ("lower", "upper") if name in band]
    if code in (1, 2) and "alpha" in band:
        bounds.append("alpha=" + _scalar(band["alpha"]))
    return _scalar(band["value"]), "; ".join([qualification, *bounds])


_CODE = re.compile(r"[A-Za-z_][A-Za-z0-9_.:+/\-]{0,127}\Z")
_CODE_FIELDS = frozenset({"state", "status", "kind", "lifecycle_state", "liveness", "submission_outcome",
    "failure_code", "code", "category", "reason", "unavailable_reason", "parse_status", "qualification",
    "population_coverage", "bucket_window_status", "count_exactness", "count_availability",
    "fraction_unavailable_reason", "response_profile", "representation", "size_unit", "progress_unit"})
_NUMBER_FIELDS = frozenset({"http_status", "returncode", "retry_after_seconds", "elapsed_seconds",
    "captured_bytes", "bytes_captured", "size_bytes", "reported_total", "returned_count", "returned_row_count",
    "valid_row_count", "invalid_row_count", "requested_offset", "requested_limit", "next_offset", "offset", "limit",
    "completed_rows", "total_rows", "completed_sequences", "total_sequences", "completed_queries", "total_queries",
    "completed_bytes", "total_bytes", "percent_complete", "progress_fraction"})
_BOOLEAN_FIELDS = frozenset({"response_complete", "body_complete", "handoff_ready", "result_available",
    "return_available", "retry_selected", "request_sent", "submission_attempted", "complete"})
_MEASUREMENT_NAMES = frozenset({"completed_rows", "total_rows", "completed_sequences", "total_sequences",
    "completed_queries", "total_queries", "completed_bytes", "total_bytes", "captured_bytes", "size_bytes",
    "percent_complete", "progress_fraction", "elapsed_seconds"})
_MEASUREMENT_UNITS = frozenset({"rows", "sequences", "queries", "bytes", "percent", "fraction", "seconds"})


def _number(value):
    return type(value) is int or type(value) is float and math.isfinite(value)


def _operational_scalars(value):
    """Select only named, typed operational facts; never traverse other data."""
    if not isinstance(value, Mapping):
        return {}
    result = {}
    for name in sorted(_CODE_FIELDS | _NUMBER_FIELDS | _BOOLEAN_FIELDS):
        if name not in value:
            continue
        item = value[name]
        if (item is None or name in _CODE_FIELDS and type(item) is str and _CODE.fullmatch(item)
                or name in _NUMBER_FIELDS and _number(item)
                or name in _BOOLEAN_FIELDS and type(item) is bool):
            result[name] = item
    return result


def _measurements(value):
    if not isinstance(value, (list, tuple)):
        return None
    result = []
    for row in value:
        if (not isinstance(row, Mapping) or type(row.get("name")) is not str or row["name"] not in _MEASUREMENT_NAMES
                or type(row.get("unit")) is not str or row["unit"] not in _MEASUREMENT_UNITS
                or "value" not in row or not (row["value"] is None or _number(row["value"]))):
            continue
        result.append({key: row[key] for key in ("name", "value", "unit")})
    return result if result or not value else None


def _qualifications(value):
    if value is None or type(value) is str and _CODE.fullmatch(value):
        return value
    if isinstance(value, Mapping):
        return _operational_scalars(value) or None
    if isinstance(value, (list, tuple)):
        return [_qualifications(item) if not isinstance(item, (list, tuple)) else None for item in value]
    return None


def _operational_facts(value):
    """A finite fact projection, independent of arbitrary result/control trees."""
    result = _operational_scalars(value)
    if not isinstance(value, Mapping):
        return result
    for name in ("page", "pagination", "progress", "failure"):
        if name in value:
            selected = _operational_scalars(value[name])
            if selected:
                result[name] = selected
    for name in ("qualification", "qualifications"):
        if name in value:
            result[name] = _qualifications(value[name])
    if "measurements" in value:
        result["measurements"] = _measurements(value["measurements"])
    return result


def _api_progress(value):
    if not isinstance(value, Mapping):
        return {}
    result = {}
    for operation, row in value.items():
        if (type(operation) is not str or not operation.startswith("api.") or not _CODE.fullmatch(operation)
                or not isinstance(row, Mapping)):
            continue
        selected = _operational_scalars(row)
        facts = _operational_facts(row.get("facts"))
        if facts:
            selected["facts"] = facts
        if selected:
            result[operation] = selected
    return result


def _own_outcome(value):
    selected = _operational_scalars(value)
    if isinstance(value, Mapping):
        for name in ("result", "feedback"):
            facts = _operational_facts(value.get(name))
            if facts:
                selected[name] = facts
    return selected


def _lookup(value):
    if not isinstance(value, Mapping):
        return _values(value)
    if value.get("view") == "own_attempts":
        rows = [(row.get("decision_index"), row.get("category"), row.get("status"), row.get("completed_gain"))
            for row in value.get("records", ())]
        parts = [_table(("Own attempt", "Category", "Status", "Completed gain"), rows)]
        for row in value.get("records", ()):
            # Explicitly requested selected inputs remain literal operands.
            # Bounded-value envelopes keep their continuation, not their hash.
            selected = {"inputs": _bounded_inputs(row["inputs"])} if "inputs" in row else {}
            fields = row.get("input_fields", {})
            if fields.get("complete") is False:
                selected["more_input_query"] = fields.get("detail_query")
            if selected:
                _section(parts, "Requested own attempt " + str(row.get("decision_index")), _values(selected))
        for key in ("next_query", "unavailable_reasons"):
            if value.get(key):
                selected = ({name: value[key][name] for name in ("view", "category", "decision_indices", "offset", "limit")
                    if name in value[key]} if key == "next_query" and isinstance(value[key], Mapping)
                    else _qualifications(value[key]))
                _section(parts, "Requested history " + key, _values(selected))
        return "\n".join(parts)
    if value.get("view") == "own_attempt_detail":
        return _values(_bounded_inputs({key: value[key] for key in ("decision_index", "pointer", "slice_unit",
            "offset", "total", "included", "values", "has_more", "next_query") if key in value}))
    content = value.get("result", value)
    if isinstance(content, Mapping) and "text" in content:
        parts = [str(content["text"])]
        page = {key: content[key] for key in ("entry_id", "section_id", "coordinate_unit", "offset",
            "returned_lines", "total_lines", "next_query") if key in content}
        if page:
            _section(parts, "Selected instruction window", _values(page))
        return "\n".join(parts)
    return _values(_own_outcome(value))


def _steering(state, lookup_results):
    parts = ["STEERING"]
    table = state.get("action_yields", {})
    rows = []
    for row in table.get("rows", ()):
        expected = row.get("expected_yield", {})
        point, uncertainty = _band(expected.get("band"))
        if expected.get("status") == "unavailable":
            point, uncertainty = "unavailable", expected.get("unavailable_reason") or "unavailable"
        rows.append((row.get("category"), row.get("completed_actions"), row.get("total_yield"), point,
            uncertainty, row.get("attempted_uncompleted")))
    _section(parts, "Own action categories", _table(("Category", "Completed", "Observed signed yield",
        "Expected next yield", "Uncertainty or limitation", "Uncompleted attempts"), rows))
    controller = state.get("controller", {})
    estimate, decision = controller.get("estimate", {}), controller.get("decision", {})
    if estimate or decision or "current_credit" in state:
        point, uncertainty = _band(estimate.get("expected_next_gain"))
        stop = decision.get("stop")
        choice = "stop" if stop is True else "continue" if stop is False else "not supplied"
        _section(parts, "Current operational continuation", _table(("Completed own actions", "Current operational credit",
            "Expected next gain", "Uncertainty", "Continuation cost", "Controller decision"),
            [(estimate.get("turns"), state.get("current_credit"), point, uncertainty,
                decision.get("continuation_cost"), choice)]))
    if table.get("unavailable_reasons"):
        _section(parts, "Yield information limits", _values(table["unavailable_reasons"]))
    if "api_execution_completed" in state:
        _section(parts, "Original handoff completion", _scalar(state["api_execution_completed"]))
    progress = _api_progress(state.get("api_received_progress"))
    if progress:
        _section(parts, "Recorded own API outcomes", _values(progress))
    outcome = state.get("last_local_outcome")
    if isinstance(outcome, Mapping):
        _section(parts, "Latest own action", _values(_own_outcome(outcome)))
    feedback = state.get("feedback")
    if feedback is not None and (not isinstance(outcome, Mapping) or feedback != outcome.get("feedback")):
        _section(parts, "Actionable feedback", _values(_operational_facts(feedback)))
    pending = state.get("pending_work", {})
    if pending.get("items"):
        _section(parts, "Own pending work", _values([_operational_scalars(row) for row in pending["items"]]))
    for value in lookup_results:
        _section(parts, "Requested information; continue the same decision", _lookup(value))
    return "\n".join(parts)


def render_api_launch_prompt(state, instructions, *, lookup_results=()):
    """Repeat the complete assigned TASK with supplied current own STEERING."""
    if not is_api_launch_context(state):
        raise ValueError("ordinary_api_launch_context_required")
    return _task(state, instructions) + "\n\n" + _steering(state, lookup_results)


__all__ = ["is_api_launch_context", "render_api_launch_prompt"]
