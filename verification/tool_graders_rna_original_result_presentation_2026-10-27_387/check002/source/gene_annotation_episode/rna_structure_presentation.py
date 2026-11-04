"""Text for supplied original RNA rows, operands and own action outcomes.

Admission owns authority. These functions select detached display copies only:
no source expansion, receipt authentication, scientific parsing or calculation.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import json

from jsonschema import Draft202012Validator, ValidationError

from .rna_structure_result_views import (
    FAMILY_SOURCES, ISSUE_SCHEMA, REFERENCE_SOURCE, SAVED_SOURCE,
    validate_rna_structure_row, validate_saved_rna_input,
)


_RECEIVED = "received_rna_structure_values"
_RECEIPT = "native_rna_structure_acquired_result_v1"
_SELECTORS = {
    "native_rna_structure_result_selector_v1": "complete_bound_bundle",
    "native_rna_structure_saved_sheet_selector_v1": "retained_sheet_only",
}
_OPERATIONS = {
    "mfe_prediction": "predict_rna_secondary_structure",
    "supplied_features": "analyze_rna_secondary_structure_features",
}
_SOURCES = (*FAMILY_SOURCES.values(), REFERENCE_SOURCE, SAVED_SOURCE)
_SOURCE_FAMILIES = {source: family for family, source in FAMILY_SOURCES.items()}
_RECEIPT_FIELDS = {
    "version", "run_id", "episode_id", "scope", "assignment", "operation_key",
    "tool_name", "arguments", "target", "observation", "capture", "prepared",
    "source_ref", "record_refs", "rows", "failures", "failure_selection",
    "native_success", "capture_complete", "delivery_complete",
}
_OBSERVATION_FIELDS = (
    "observed_at", "state", "returncode", "failure_code", "result_available",
    "measurements", "outputs",
)
_TEXT = {"type": "string", "minLength": 1}


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
        "additionalProperties": False}


_OBSERVATION_SCHEMA = _object({
    "observed_at": _TEXT,
    "state": {"enum": ["submitted", "running", "completed", "failed", "unknown"]},
    "returncode": {"type": ["integer", "null"]},
    "failure_code": {"type": ["string", "null"], "minLength": 1},
    "result_available": {"type": "boolean"},
    "measurements": {"type": "array", "items": _object({
        "measure": _TEXT, "seconds": {"type": "number", "minimum": 0}})},
    "outputs": {"type": "array", "items": _object({
        "role": _TEXT, "available": {"type": "boolean"},
        "bytes": {"type": ["integer", "null"], "minimum": 0},
        "writer_closed": {"type": "boolean"}})},
})
_OWN_SCHEMA = _object({
    "status": {"type": ["string", "null"]},
    "operation": {"enum": ["execution.results.status", "execution.results.collect"]},
    "acquisition": {"enum": list(_SELECTORS.values())},
    "mode": {"enum": list(_OPERATIONS)},
    "native_success": {"type": "boolean"}, "capture_complete": {"type": "boolean"},
    "delivery_complete": {"type": "boolean"},
    "observation_basis": {"enum": ["original_attempt_observation", "retained_original_observation"]},
    "observation": _OBSERVATION_SCHEMA,
    "issues": {"type": "array", "items": ISSUE_SCHEMA},
})
_ORIGIN_SCHEMA = _object({
    "content_location": {"const": "retained_complete_producer_bundle"},
    "attempt_output_version": {"const": "original_producer_manifest_and_verified_file_digests"},
    "window_consistency": {"const": "complete_files_matched_to_original_manifest"},
    "completion_basis": {"const": "requested_acquisition_and_observed_successful_attempt"},
})
_PROGRESS_SCHEMA = _object({
    "execution_completed": {"type": "boolean"},
    "execution_result_origin": {"anyOf": [_ORIGIN_SCHEMA, {"type": "null"}]},
})
_SAVED_FIELDS = ("schema", "result_receipt_key", "handoff_ref", "source_ref",
    "bundle_artifact_ref", "sheet_artifact_ref", "sheet_sha256", "record_key", "operation", "mode")
_FAILURE_FIELDS = ("family", "record_key", "row_key", "source_ref", "operation", "mode",
    "result_receipt_key", "issue_ordinal")
_ISSUE_FIELDS = ("stage", "code", "record_key", "field", "index", "artifact_role")


def _key(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _checked(value, schema, code):
    try:
        _key(value)  # JSON Schema alone accepts non-finite Python floats.
        Draft202012Validator(schema).validate(value)
    except (TypeError, ValueError, ValidationError) as error:
        raise ValueError(code) from error
    return deepcopy(value)


def _checked_fact(source, value):
    try:
        _key(value)
        if source in _SOURCE_FAMILIES:
            if not isinstance(value, Mapping) or value.get("family") != _SOURCE_FAMILIES[source]:
                raise ValueError("wrong RNA family")
            # This validator checks only the supplied closed row and its internal
            # relationships. It never validates a sheet or recomputes its cells.
            return validate_rna_structure_row(value)
        if source == SAVED_SOURCE:
            return validate_saved_rna_input(value)
        if source == REFERENCE_SOURCE and isinstance(value, str) and value and "\x00" not in value:
            return value
    except (TypeError, ValueError, KeyError, AttributeError) as error:
        raise ValueError("rna_structure_fact_shape_invalid") from error
    raise ValueError("rna_structure_fact_shape_invalid")


def _append_group(groups, source, facts, *, include_empty=True):
    if source not in _SOURCES or not isinstance(facts, list):
        raise ValueError("rna_structure_group_shape_invalid")
    checked = [_checked_fact(source, value) for value in facts]
    group = next((group for group in groups if group["fact_source"] == source), None)
    if group is None:
        if not checked and not include_empty:
            return
        group = {"fact_source": source, "facts": []}
        groups.append(group)
    seen = {_key(value) for value in group["facts"]}
    for value in checked:
        identity = _key(value)
        if identity not in seen:
            group["facts"].append(value)
            seen.add(identity)


def _group_shape(group):
    return (isinstance(group, Mapping) and set(group) == {"fact_source", "facts"}
        and group["fact_source"] in _SOURCES and isinstance(group["facts"], list))


def is_rna_structure_results_context(state: Mapping) -> bool:
    """Recognize the two original selectors, independently of comparison work."""
    assignment = state.get("execution_assignment") if isinstance(state, Mapping) else None
    return (isinstance(assignment, Mapping)
        and assignment.get("version") == "execution_results_assignment_v1"
        and isinstance(assignment.get("selector"), Mapping)
        and isinstance(assignment["selector"].get("version"), str)
        and assignment["selector"].get("version") in _SELECTORS)


def has_rna_structure_receiver_context(state: Mapping) -> bool:
    """An explicitly supplied empty marker establishes capability, not facts."""
    return (isinstance(state, Mapping) and _RECEIVED in state
        and isinstance(state[_RECEIVED], list) and all(_group_shape(group) for group in state[_RECEIVED]))


def _is_receipt(value):
    return isinstance(value, Mapping) and value.get("version") == _RECEIPT


def _own_outcome(body, status):
    """Select original saved fields without consulting any authority or bytes."""
    try:
        if set(body) != _RECEIPT_FIELDS:
            raise ValueError("closed original receipt required")
        selector = body["assignment"]["selector"]
        if (body["assignment"].get("version") != "execution_results_assignment_v1"
                or _SELECTORS.get(selector["version"]) != selector["acquisition"]):
            raise ValueError("original selector required")
        job = body["target"]["assignment"]["requested_job"]["native_rna_structure"]
        if job["mode"] not in _OPERATIONS or job["operation"] != _OPERATIONS[job["mode"]]:
            raise ValueError("original RNA mode required")
        family = selector["projection"]["family"]
        if family not in FAMILY_SOURCES or not isinstance(body["rows"], list):
            raise ValueError("original family required")
        for row in body["rows"]:
            _checked_fact(FAMILY_SOURCES[family], row)
        issues = _checked(body["failures"], {"type": "array", "items": ISSUE_SCHEMA},
            "rna_structure_own_outcome_shape_invalid")
        if family == "failure":
            selection = body["failure_selection"]
            if (not isinstance(selection, Mapping) or set(selection) != {"version", "population_count",
                    "selected_ordinals", "supplemental_issue_ordinals", "requested_rows_accounted_for"}
                    or selection["version"] != "rna_structure_failure_selection_v1"):
                raise ValueError("recorded failure selection required")
            ordinals = selection["selected_ordinals"] + selection["supplemental_issue_ordinals"]
            if any(type(i) is not int or not 0 <= i < len(issues) for i in ordinals):
                raise ValueError("invalid failure ordinal")
            issues = [issues[i] for i in ordinals]
        acquisition = selector["acquisition"]
        result = {"status": status, "operation": body["tool_name"], "acquisition": acquisition,
            "mode": job["mode"], **{name: body[name] for name in
                ("native_success", "capture_complete", "delivery_complete")},
            "observation_basis": "retained_original_observation" if acquisition == "retained_sheet_only"
                else "original_attempt_observation",
            "observation": {name: deepcopy(body["observation"][name]) for name in _OBSERVATION_FIELDS},
            "issues": issues}
        return _checked(result, _OWN_SCHEMA, "rna_structure_own_outcome_shape_invalid")
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("rna_structure_own_outcome_shape_invalid") from error


def _without_received_duplicates(reports, received):
    known = {_key(value) for group in received for value in group["facts"]}
    if not isinstance(reports, list) or not known:
        return reports
    def duplicate(value):
        try:
            return _key(value) in known
        except (TypeError, ValueError):
            return False
    result = []
    for report in reports:
        if not isinstance(report, Mapping):
            result.append(report)
            continue
        item = dict(report)
        for name, values in report.items():
            if isinstance(values, list):
                kept = [value for value in values if not duplicate(value)]
                if len(kept) != len(values):
                    if kept:
                        item[name] = kept
                    else:
                        item.pop(name)
        if item or not report:
            result.append(item)
    return result


def select_rna_structure_presentation(state: Mapping) -> dict:
    """Extract only named received facts and this original results owner's work."""
    context, groups = deepcopy(dict(state)), []
    received = context.get(_RECEIVED)
    if isinstance(received, list):
        remaining = []
        for group in received:
            if isinstance(group, Mapping) and group.get("fact_source") in _SOURCES:
                if not _group_shape(group):
                    raise ValueError("rna_structure_group_shape_invalid")
                _append_group(groups, group["fact_source"], group["facts"])
            else:
                remaining.append(group)
        if remaining:
            context[_RECEIVED] = remaining
        else:
            context.pop(_RECEIVED, None)
    if "child_reports" in context:
        context["child_reports"] = _without_received_duplicates(context["child_reports"], groups)

    own_outcome = own_progress = None
    if is_rna_structure_results_context(state):
        progress = context.get("execution_progress")
        if isinstance(progress, dict):
            original_refs = progress.get(REFERENCE_SOURCE)
            for source in _SOURCES:
                if source in progress:
                    _append_group(groups, source, progress.pop(source), include_empty=False)
            if (original_refs is not None and "execution_result_refs" in progress
                    and _key(progress["execution_result_refs"]) == _key(original_refs)):
                progress.pop("execution_result_refs")
            if "execution_completed" in progress or "execution_result_origin" in progress:
                own_progress = _checked({name: progress.pop(name) for name in
                    ("execution_completed", "execution_result_origin") if name in progress},
                    _PROGRESS_SCHEMA, "rna_structure_own_progress_shape_invalid")
        outcome = context.get("last_local_outcome")
        if isinstance(outcome, Mapping) and _is_receipt(outcome.get("result")):
            body = outcome["result"]
            own_outcome = _own_outcome(body, outcome.get("status"))
            family = body["assignment"]["selector"]["projection"]["family"]
            if family != "failure":
                _append_group(groups, FAMILY_SOURCES[family], body["rows"],
                    include_empty=body["tool_name"] == "execution.results.collect")
            # Keep all unrelated envelope data and non-null actionable feedback.
            rest = {name: value for name, value in outcome.items() if name not in
                {"result", "status", "record_refs", "changed_record_refs"}
                and not (name == "feedback" and value is None)}
            if rest:
                context["last_local_outcome"] = rest
            else:
                context.pop("last_local_outcome", None)
    return {"context": context, "groups": groups, "own_outcome": own_outcome, "own_progress": own_progress}


def _value(value):
    if value is None:
        return "unavailable"
    if type(value) is bool:
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return "; ".join(_value(item) for item in value) or "empty"
    return str(value) if value != "" else '""'


def _escape(value):
    return (_value(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace("|", "&#124;").replace("\r", "&#13;").replace("\n", "&#10;"))


def _table(headers, rows):
    rows = list(rows)
    if not rows:
        return "No selected rows supplied."
    return "\n".join(["| " + " | ".join(_escape(value) for value in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(_escape(value) for value in row) + " |" for row in rows)])


def _measurements(row):
    cells = [*row["measurements"], *row["unavailable"]]
    operands = [name for name in ("numerator", "denominator") if any(cell[name] is not None for cell in cells)]
    return _table(["Field", "Value", "Unit", *(name.title() for name in operands), "State", "Reason", "Origin"],
        ([cell["name"], cell.get("value"), cell["unit"], *(cell[name] for name in operands),
          cell.get("state", "present"), cell.get("reason", "none"), cell["origin"]] for cell in cells))


def _parameter_table(parameters):
    return _table(("Calculation parameter", "Supplied value"), [
        ("topology.long_stem_min_pairs", parameters["topology"]["long_stem_min_pairs"]),
        ("topology.include_exterior_in_loop_size_statistics", parameters["topology"]["include_exterior_in_loop_size_statistics"]),
        ("pair_composition.accepted_ordered_pair_types", parameters["pair_composition"]["accepted_ordered_pair_types"]),
        ("pair_composition.denominator", parameters["pair_composition"]["denominator"]),
        ("energy.normalization", parameters["energy"]["normalization"]),
    ])


def _operand_table(fields):
    def kind(value):
        return "null" if value is None else "integer" if type(value) is int else "string"
    return _table(("Operand field", "Type", "Exact supplied value"),
        ((name, kind(value), "null" if value is None else value) for name, value in fields))


def _numeric_row(row, parameter_number, multiple_parameters):
    parts = ["Selected " + row["family"] + " row: " + _escape(row["row_key"])]
    for fields in (("record_key", "sequence_id", "structure_id", "structure_key"),
                   ("source_ref", "subject_ref"), ("operation", "mode", "structure_origin", "status")):
        parts.append("; ".join(name + ": " + _escape(row[name]) for name in fields) + ".")
    if multiple_parameters:
        parts.append("Calculation parameter set: " + str(parameter_number) + ".")
    family = row["family"]
    if family == "pair":
        parts.append(_table(("pair_key", "indices (zero based)", "symbol_i", "symbol_j", "ordered_pair"),
            [(row["pair_key"], "(" + ", ".join(map(str, row["indices"])) + ")",
              row["symbol_i"], row["symbol_j"], row["ordered_pair"])]))
    elif family == "stem":
        parts += ["stem_key: " + _escape(row["stem_key"]),
            _table(("pair_key", "Pair endpoints (zero based)"),
                ((key, "(" + ", ".join(map(str, pair)) + ")")
                    for key, pair in zip(row["pair_keys"], row["pair_indices"], strict=True)))]
    elif family == "region":
        intervals = "; ".join(f"[{start}, {end})" for start, end in row["unpaired_intervals"]) or "empty"
        parts.append(_table(("region_key", "region_kind", "closing_pair_key",
            "immediate_branch_pair_keys", "unpaired_intervals (half open)"),
            [(row["region_key"], row["region_kind"], row["closing_pair_key"],
              row["immediate_branch_pair_keys"], intervals)]))
    parts.append(_measurements(row))
    if row["qualification_codes"]:
        parts.append("Qualification codes: " + _escape(row["qualification_codes"]) + ".")
    return "\n\n".join(parts)


def render_rna_structure_groups(groups: Sequence[Mapping]) -> str:
    """Render selected rows and complete callable operands, never whole sheets."""
    selected = []
    for group in groups:
        if not _group_shape(group):
            raise ValueError("rna_structure_group_shape_invalid")
        _append_group(selected, group["fact_source"], group["facts"])
    parameters, parameter_ids = [], {}
    for group in selected:
        if group["fact_source"] in _SOURCE_FAMILIES and _SOURCE_FAMILIES[group["fact_source"]] != "failure":
            for row in group["facts"]:
                key = _key(row["calculation_parameters"])
                if key not in parameter_ids:
                    parameters.append(row["calculation_parameters"])
                    parameter_ids[key] = len(parameters)
    parts = []
    if parameters:
        parts.append("RNA sequence indices are zero based; intervals are half open.")
        for index, value in enumerate(parameters, 1):
            parts += ["Calculation parameters" + (" — set " + str(index) if len(parameters) > 1 else ""),
                _parameter_table(value)]
    for group in selected:
        source, facts = group["fact_source"], group["facts"]
        if source == REFERENCE_SOURCE:
            parts += ["Requested RNA result sources; no numerical rows or auxiliary bytes supplied.",
                _table(("Result source operand",), ((value,) for value in facts))]
        elif source == SAVED_SOURCE:
            parts.append("Copyable retained-input operands (exact received objects).")
            if not facts:
                parts.append("No retained-input operands supplied.")
            for row in facts:
                parts.append(_operand_table((name, row[name]) for name in _SAVED_FIELDS))
        elif source == FAMILY_SOURCES["failure"]:
            parts.append("Copyable received-failure operands (exact received rows; no numerical score).")
            if not facts:
                parts.append("No selected failure rows supplied.")
            for row in facts:
                parts.append(_operand_table([*((name, row[name]) for name in _FAILURE_FIELDS),
                    *(("issue." + name, row["issue"][name]) for name in _ISSUE_FIELDS)]))
        else:
            parts.append("Requested RNA " + _SOURCE_FAMILIES[source] + " rows")
            if not facts:
                parts.append("No selected rows supplied; this does not establish the full population size.")
            parts.extend(_numeric_row(row, parameter_ids[_key(row["calculation_parameters"])], len(parameters) > 1)
                for row in facts)
    return "\n\n".join(parts)


def _issues(issues):
    return _table(("Stage", "Code", "Record", "Field", "Index", "Artifact role"),
        (tuple(issue[name] for name in _ISSUE_FIELDS) for issue in issues))


def _output_role(role, index):
    # A resource observation may use its private path as the output role.
    # The detached record keeps it exact. This status label is no callable
    # alias and assigns no scientific semantics to the supplied basename.
    if role.startswith("requested_output:"):
        basename = role[len("requested_output:"):].rstrip("/").rsplit("/", 1)[-1]
        return "requested output " + str(index) + (" (" + basename + ")" if basename else "")
    return role


def render_rna_structure_own_outcome(outcome: Mapping | None) -> str | None:
    if outcome is None:
        return None
    value = _checked(outcome, _OWN_SCHEMA, "rna_structure_own_outcome_shape_invalid")
    saved = value["acquisition"] == "retained_sheet_only"
    original_status = not saved and value["operation"] == "execution.results.status"
    parts = [_table(("Selected operation", "Action outcome", "Acquisition", "Mode", "Requested delivery complete"),
        [(value["operation"], value["status"], value["acquisition"], value["mode"], value["delivery_complete"])])]
    parts.append(_table(("Recorded flag", "Value", "Meaning for this action"), [
        ("native_success", value["native_success"], "not established by this status action" if original_status
            else "retained original native success" if saved else "original native success"),
        ("capture_complete", value["capture_complete"], "not established by this status action" if original_status
            else "retained original capture completeness" if saved else "original capture completeness"),
    ]))
    observation = value["observation"]
    parts += ["Retained original observation; no fresh native observation." if saved else "Original attempt observation.",
        _table(("Original observed_at", "State", "Return code", "Failure code", "Result available"),
            [(observation["observed_at"], observation["state"], observation["returncode"],
              observation["failure_code"], observation["result_available"])])]
    if observation["measurements"]:
        parts.append(_table(("Original measured interval", "Seconds"),
            ((row["measure"], row["seconds"]) for row in observation["measurements"])))
    if observation["outputs"]:
        parts.append(_table(("Original output role", "Available", "Bytes", "Writer closed"),
            ((_output_role(row["role"], index), row["available"], row["bytes"], row["writer_closed"])
                for index, row in enumerate(observation["outputs"], 1))))
    if value["issues"]:
        parts += ["Own selected repair qualifications (not received-failure operands)", _issues(value["issues"])]
    return "\n\n".join(parts)


def render_rna_structure_own_progress(progress: Mapping | None) -> str | None:
    if progress is None:
        return None
    value = _checked(progress, _PROGRESS_SCHEMA, "rna_structure_own_progress_shape_invalid")
    parts = [_table(("Own requested RNA delivery complete",), [(value["execution_completed"],)])]
    origin = value["execution_result_origin"]
    if origin is not None:
        parts += ["Recorded original acquisition basis", _table(("Field", "Recorded value"), origin.items())]
    return "\n\n".join(parts)


def _candidate_source(value):
    if not isinstance(value, Mapping):
        return None
    if value.get("schema") == "rna_structure_saved_sheet_input_v1":
        return SAVED_SOURCE
    if isinstance(value.get("family"), str) and value.get("family") in FAMILY_SOURCES and (value.get("operation") in _OPERATIONS.values()
            or value.get("coordinate_system") == "zero_based_sequence_indices_and_half_open_intervals"):
        return FAMILY_SOURCES[value["family"]]
    return None


def render_rna_structure_lookup(result: Mapping | list) -> str | None:
    """Recognize only an explicit reply, optionally under one result envelope."""
    content = result.get("result", result) if isinstance(result, Mapping) else result
    if _is_receipt(content):
        status = result.get("status") if isinstance(result, Mapping) and content is not result else None
        own = _own_outcome(content, status)
        groups = []
        family = content["assignment"]["selector"]["projection"]["family"]
        if family != "failure":
            _append_group(groups, FAMILY_SOURCES[family], content["rows"],
                include_empty=own["operation"] == "execution.results.collect")
        return "\n\n".join(filter(None, (render_rna_structure_own_outcome(own), render_rna_structure_groups(groups))))
    source = _candidate_source(content)
    if source is not None:
        return render_rna_structure_groups([{"fact_source": source, "facts": [content]}])
    if isinstance(content, Mapping) and content.get("fact_source") in _SOURCES:
        return render_rna_structure_groups([content])
    if isinstance(content, list) and content:
        if all(isinstance(row, Mapping) and row.get("fact_source") in _SOURCES for row in content):
            return render_rna_structure_groups(content)
        sources = [_candidate_source(row) for row in content]
        if sources[0] is not None and all(source == sources[0] for source in sources):
            return render_rna_structure_groups([{"fact_source": sources[0], "facts": content}])
    return None


def rna_structure_return_schema_view(form: Mapping) -> dict:
    """Compact original top-level recorded nodes only; retain other constraints."""
    shown = deepcopy(dict(form))
    descriptions = {source: "Automatically supplied selected RNA " + family +
        " numerical cells and required qualifications." for family, source in FAMILY_SOURCES.items() if family != "failure"}
    descriptions.update({
        FAMILY_SOURCES["failure"]: "Automatically supplied requested RNA failure rows, preserving exact received-failure operands.",
        REFERENCE_SOURCE: "Automatically supplied requested RNA result references; no numerical rows or auxiliary bytes are supplied.",
        SAVED_SOURCE: "Automatically supplied exact original saved-sheet operands for explicitly selected retained-data work.",
    })
    for name, node in shown.get("properties", {}).items():
        if isinstance(node, Mapping) and node.get("x-source") in _SOURCES:
            shallow = {key: deepcopy(value) for key, value in node.items() if key != "items"}
            shallow["description"] = (node.get("description", "") + ("; " if node.get("description") else "")
                + descriptions[node["x-source"]])
            shown["properties"][name] = shallow
    return shown


__all__ = ["is_rna_structure_results_context", "has_rna_structure_receiver_context",
    "select_rna_structure_presentation", "render_rna_structure_groups",
    "render_rna_structure_own_outcome", "render_rna_structure_own_progress",
    "render_rna_structure_lookup", "rna_structure_return_schema_view"]
