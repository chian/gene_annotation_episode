"""Exact finite projections of authenticated, already saved alignment-site results.

Counts, ratios, selections and unavailable outcomes retain their original meaning.
Source acquisition and host receipt authentication remain separate responsibilities.
"""
from __future__ import annotations

from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.library.blast_search import PROGRAM_UNITS
from ..communication import ReportBoundaryError
from .alignment_site_projection_requests import (
    _require, _SOURCES, requested_site_projections, _object, _REFERENCE, _same,
    _ISSUES, _REFERENCE_RATIOS, _BLAST_RATIOS, _finite_json, _BLAST, _validate_value,
)

__all__ = ["project_reference_site_return", "project_blast_column_return",
           "project_site_action_return", "validate_frozen_site_return"]

def _requested(fields, source=None):
    _require(type(fields) is dict and fields.get("x-source") in _SOURCES, "projection_source_required")
    requested = requested_site_projections(_object({"value": fields}))
    actual = fields["x-source"]
    _require(source is None or source == actual, "projection_source_conflict")
    return actual, requested[actual]["selection"]


def _reference_selection(selection):
    _require(type(selection) is dict, "saved_selection_invalid")
    if selection.get("kind") == "reference_positions":
        values = selection.get("positions")
        _require(set(selection) == {"kind", "positions"} and type(values) is list and bool(values)
            and all(type(v) is int and v >= 0 for v in values), "saved_selection_invalid")
        return {"kind": "reference_positions", "positions": deepcopy(values), "start": None, "end": None}
    _require(set(selection) == {"kind", "start", "end"} and selection.get("kind") == "reference_window"
        and type(selection["start"]) is int and type(selection["end"]) is int
        and 0 <= selection["start"] < selection["end"], "saved_selection_invalid")
    return {"kind": "reference_window", "positions": None, "start": selection["start"], "end": selection["end"]}


def _matches(source, selector, alignment_ref, selected):
    refs = selector["alignment_refs"]
    _require(refs is None or alignment_ref in refs, "selection_mismatch")
    if selector["window"] is not None:
        keys = ("start", "end") if source == _REFERENCE else ("column_offset", "column_limit")
        _require((source != _REFERENCE or selected["kind"] == "reference_window") and
            _same({key: selected[key] for key in keys}, selector["window"]), "selection_mismatch")
    if selector["positions"] is not None:
        _require(selected["kind"] == "reference_positions" and set(selected["positions"]) ==
            set(selector["positions"]), "selection_mismatch")


def _project(value, schema):
    if value is None:
        return None
    if "properties" in schema:
        _require(type(value) is dict and set(schema["properties"]) <= set(value), "saved_field_unavailable")
        return {name: _project(value[name], child) for name, child in schema["properties"].items()}
    if "items" in schema:
        _require(type(value) is list, "saved_rows_invalid")
        return [_project(child, schema["items"]) for child in value]
    return deepcopy(value)


def _codes(*issues):
    result = []
    for values in issues:
        _require(type(values) is list, "saved_issues_invalid")
        for issue in values:
            code = issue.get("code") if type(issue) is dict else issue
            _require(type(code) is str and bool(code), "saved_issues_invalid")
            code = code if code in _ISSUES else "site_component_unavailable"
            if code not in result:
                result.append(code)
    return result


def _saved_components(scores, source, fields):
    if scores is None:
        return None
    _require(type(scores) is dict and scores.get("schema") == (
        "reference_site_components_v1" if source == _REFERENCE else "blast_hsp_column_components_v1"),
        "saved_scores_invalid")
    requested = fields["properties"]
    ratios = _REFERENCE_RATIOS if source == _REFERENCE else _BLAST_RATIOS
    result = {}
    for name in requested:
        if name in ratios:
            ratio = scores.get("ratios", {}).get(name)
            _require(type(ratio) is dict and set(ratio) == {"value", "numerator", "denominator"},
                "saved_ratio_invalid", name)
            result[name] = {**deepcopy(ratio), "unit": "fraction"}
        else:
            _require(type(scores.get("summary")) is dict and name in scores["summary"],
                "saved_component_missing", name)
            result[name] = deepcopy(scores["summary"][name])
    return result


def _sheet_group(sheet, scores, fields, source, selector):
    _finite_json(sheet)
    _finite_json(scores)
    _require(type(sheet) is dict and sheet.get("schema") == ("reference_site_comparison_sheet_v1"
        if source == _REFERENCE else "blast_hsp_column_sheet_v1"), "saved_sheet_invalid")
    _require(type(scores) is dict and scores.get("schema") == ("reference_site_components_v1"
        if source == _REFERENCE else "blast_hsp_column_components_v1"), "saved_scores_invalid")
    try:
        origin, operands = sheet["source"], sheet["operands"]
        alignment_ref = origin["alignment_ref"]
        units = {role: operands[role]["unit"] for role in ("query", "reference")}
        if source == _REFERENCE:
            selection = _reference_selection(sheet["selection"])
        else:
            native_units = PROGRAM_UNITS[sheet["program"]]
            for index, role in enumerate(("query", "reference")):
                _require(units[role] in ("symbol", native_units[index]), "saved_unit_conflict")
                units[role] = native_units[index]
            selection = {**sheet["requested_window"],
                "column_end": None if sheet["realized_window"] is None else sheet["realized_window"]["column_end"],
                "total_columns": sheet["total_columns"], "next_column_offset": sheet["next_column_offset"]}
        _matches(source, selector, alignment_ref, selection)
        props = fields["items"]["properties"]
        result = {"selection_policy": selector["policy"], "alignment_ref": alignment_ref,
            "selection": selection, "data_status": sheet["status"]}
        for name in props:
            if name in result:
                continue
            if name in ("query_ref", "reference_ref"):
                result[name] = operands[name.removesuffix("_ref")]["subject_ref"]
            elif name in ("query_unit", "reference_unit"):
                result[name] = units[name.removesuffix("_unit")]
            elif name == "source_ref":
                result[name] = origin["source_ref"]
            elif name == "operation_status":
                result[name] = None
            elif name == "components":
                result[name] = _saved_components(scores, source, props[name])
            elif name == "issue_codes":
                result[name] = _codes(sheet["issues"], scores["issues"])
            elif name in ("rows", "insertions"):
                rows = sheet["insertions" if name == "insertions" else "sites" if source == _REFERENCE else "columns"]
                if rows is None or (source == _BLAST and sheet["realized_window"] is None):
                    result[name] = None
                    continue
                _require(type(rows) is list, "saved_rows_invalid")
                result[name] = []
                for row in rows:
                    _require(type(row) is dict, "saved_rows_invalid")
                    row = dict(row)
                    if source == _REFERENCE:
                        row.update({"query_unit": units["query"], "reference_unit": units["reference"]})
                    else:
                        _require(all(row[role + "_unit"] == units[role] for role in units), "saved_unit_conflict")
                    if name == "insertions":
                        for key in ("query_sequence", "query_quality_characters"):
                            if key in props[name]["items"]["properties"]:
                                _require(row[key] is None or type(row[key]) is str, "saved_symbols_invalid")
                                row[key] = None if row[key] is None else list(row[key])
                    result[name].append(_project(row, props[name]["items"]))
        return _project(result, fields["items"])
    except (KeyError, TypeError, AttributeError) as error:
        raise ReportBoundaryError("Saved site structure invalid", code="alignment_site_saved_structure_invalid") from error


def project_reference_site_return(sheet: dict, scores: dict, requested_fields: dict) -> dict:
    """Copy one reference selection; operational status is unknown at sheet level."""
    source, selector = _requested(requested_fields, _REFERENCE)
    result = _sheet_group(sheet, scores, requested_fields, source, selector)
    _validate_value(result, requested_fields["items"])
    return result


def project_blast_column_return(sheet: dict, scores: dict, requested_fields: dict) -> dict:
    """Copy one BLAST window with the saved ratios and actual native coordinate units."""
    source, selector = _requested(requested_fields, _BLAST)
    result = _sheet_group(sheet, scores, requested_fields, source, selector)
    _validate_value(result, requested_fields["items"])
    return result


def project_site_action_return(record: dict, requested_fields: dict) -> dict:
    """Join an authenticated host record's original selection and saved availability."""
    source, selector = _requested(requested_fields)
    _finite_json(record)
    _require(type(record) is dict and set(record) == {"decision_index", "operation_ref", "tool_name",
        "operation_status", "arguments", "binding", "grading_artifact_ref", "grading", "availability",
        "feedback_code"}, "action_record_invalid")
    _require(type(record["decision_index"]) is int and record["decision_index"] >= 0
        and type(record["operation_ref"]) is str and bool(record["operation_ref"])
        and record["tool_name"] == ("sequence.sites" if source == _REFERENCE else "result.blast.hsp")
        and record["operation_status"] in ("completed", "partial"), "action_record_invalid")
    try:
        binding, arguments = record["binding"], record["arguments"]
        _require(type(binding) is dict and set(binding) == {"alignment_ref", "native_source_ref",
            "native_artifact_ref", "result_source_ref", "result_observation_ref", "native_locator"}, "action_binding_invalid")
        if source == _REFERENCE:
            _require(type(arguments) is dict and (set(arguments) == {"alignment_ref", "positions"}
                or set(arguments) == {"alignment_ref", "window"}), "action_arguments_invalid")
            alignment_ref = arguments["alignment_ref"]
            selected = _reference_selection({"kind": "reference_positions", "positions": arguments["positions"]}
                if "positions" in arguments else {"kind": "reference_window", **arguments["window"]})
        else:
            _require(type(arguments) is dict and set(arguments) == {"observation_ref", "column_offset", "column_limit"},
                "action_arguments_invalid")
            alignment_ref = arguments["observation_ref"]
            selected = {"column_offset": arguments["column_offset"], "column_limit": arguments["column_limit"],
                "column_end": None, "total_columns": None, "next_column_offset": None}
        _require(_same(alignment_ref, binding["alignment_ref"]), "action_binding_conflict")
        _matches(source, selector, alignment_ref, selected)
        availability, grading = record["availability"], record["grading"]
        _require(availability in ("bound", "legacy_result_ungraded", "grading_unavailable"), "action_availability_invalid")
        if availability == "bound":
            _require(type(grading) is dict and set(grading) == {"sheet", "scores", "failure"}
                and grading["failure"] is None, "action_grading_invalid")
            sheet = grading["sheet"]
            origin = sheet["source"]
            _require(_same(origin["alignment_ref"], alignment_ref) and
                _same(origin["source_ref"], binding["native_source_ref"]) and
                _same(origin["native_artifact_ref"], binding["native_artifact_ref"]), "action_binding_conflict")
            locator = origin["native_locator"]
            _require(_same(locator, binding["native_locator"]) or (locator == {} and binding["native_locator"] is None
                and origin["format"] in ("biopython_pairwise_json", "native_phmmer_alignment_json")), "action_binding_conflict")
            original_selection = (_reference_selection(sheet["selection"]) if source == _REFERENCE
                else sheet["requested_window"])
            expected_selection = selected if source == _REFERENCE else {
                key: selected[key] for key in ("column_offset", "column_limit")}
            _require(_same(original_selection, expected_selection), "action_selection_conflict")
            result = _sheet_group(sheet, grading["scores"], requested_fields, source, selector)
        else:
            _require(grading is None if availability == "legacy_result_ungraded" else grading is None or
                type(grading) is dict and set(grading) == {"sheet", "scores", "failure"}, "action_grading_invalid")
            codes = ["site_legacy_result_ungraded" if availability == "legacy_result_ungraded" else "site_grading_unavailable"]
            if grading is not None and grading.get("failure") is not None:
                failure = grading["failure"]
                _require(type(failure) is dict and "code" in failure, "action_grading_invalid")
                codes.extend(_codes([failure["code"]]))
            if record["feedback_code"] is not None:
                codes.extend(_codes([record["feedback_code"]]))
            result = _project({"selection_policy": selector["policy"], "alignment_ref": alignment_ref,
                "selection": selected, "data_status": "unavailable", "rows": None, "insertions": None,
                "components": None, "issue_codes": list(dict.fromkeys(codes)), "query_ref": None,
                "reference_ref": None, "source_ref": binding["native_source_ref"], "operation_status": None,
                "query_unit": None, "reference_unit": None}, requested_fields["items"])
        if "operation_status" in result:
            result["operation_status"] = record["operation_status"]
        _validate_value(result, requested_fields["items"])
        return result
    except (KeyError, TypeError, AttributeError) as error:
        raise ReportBoundaryError("Saved action structure invalid", code="alignment_site_action_structure_invalid") from error


def validate_frozen_site_return(form: dict, original_schema: dict, frozen_facts: dict | None) -> None:
    """Compare only requested source fields to their exact already frozen arrays."""
    projections = requested_site_projections(original_schema)
    if not projections:
        return
    _finite_json(form)
    _finite_json(frozen_facts)
    _require(type(form) is dict, "form_required")
    _require(type(frozen_facts) is dict, "frozen_facts_unavailable")
    for field, node in original_schema["properties"].items():
        source = node.get("x-source")
        if source not in projections:
            continue
        _require(source in frozen_facts, "frozen_source_missing", field)
        _require(type(frozen_facts[source]) is list, "frozen_source_invalid", field)
        _require(field in form, "form_field_missing", field)
        _validate_value(form[field], node)
        _validate_value(frozen_facts[source], node)
        _require(_same(form[field], frozen_facts[source]), "frozen_source_mismatch", field)
