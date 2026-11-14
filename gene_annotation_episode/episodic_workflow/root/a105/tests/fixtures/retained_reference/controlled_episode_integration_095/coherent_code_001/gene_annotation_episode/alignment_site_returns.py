"""Requested finite views of already saved alignment-site results.

The host authenticates original actions and artifact custody. These six pure
functions neither acquire results nor calculate scientific components. Counts
and ratios are copied from the saved calculator result; native whole-alignment
measurements never become selected-site measurements.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re

from .blast_search import PROGRAM_UNITS
from .communication import ReportBoundaryError, validate_closed_schema, validate_form


__all__ = ["alignment_site_fact_sources", "requested_site_projections",
    "project_reference_site_return", "project_blast_column_return",
    "project_site_action_return", "validate_frozen_site_return"]

_REFERENCE = "reference_site_rows"
_BLAST = "blast_hsp_column_rows"
_SOURCES = (_REFERENCE, _BLAST)
_POLICIES = ("all_own_completed_results", "matching_alignment",
    "matching_alignment_window", "matching_alignment_position_set")
_ISSUES = ("site_native_geometry_unavailable", "site_native_geometry_conflict",
    "site_operand_identity_conflict", "site_original_mapping_unavailable",
    "site_original_mapping_conflict", "site_quality_encoding_unspecified",
    "site_quality_length_conflict", "site_source_ordinal_join_unavailable",
    "site_component_unavailable", "site_grading_unavailable",
    "site_legacy_result_ungraded")
_MAPPING = ("available", "unavailable", "incompatible", "not_applicable")
_UNITS = ("aa", "nt", "symbol")
_OBSERVATION = re.compile(r"observation_[a-f0-9]{24,64}\Z")
_REFERENCE_COUNTS = {
    "requested_position_count": "Count of requested reference rows, including duplicates.",
    "unique_requested_position_count": "Count of distinct requested reference positions.",
    "duplicate_requested_position_count": "Count of repeated reference-position requests.",
    "identical_positions": "Count of distinct selected identical paired reference positions.",
    "substituted_positions": "Count of distinct selected substituted reference positions.",
    "paired_positions": "Count of distinct selected reference positions paired to query symbols.",
    "query_gap_positions": "Count of selected reference positions opposite query gaps.",
    "reference_skip_positions": "Count of selected reference positions in native reference skips.",
    "outside_alignment_positions": "Count of selected positions proven outside the alignment.",
    "unavailable_positions": "Count of selected positions with unavailable correspondence.",
    "aligned_reference_positions": "Count of selected reference positions represented in alignment columns.",
    "selected_insertion_events": "Count of distinct selected native query insertion runs.",
    "inserted_query_positions": "Count of query symbols in selected insertion runs.",
    "selected_query_paired_units": "Union length of paired query intervals in group query_unit.",
    "selected_reference_paired_units": "Union length of paired reference intervals in group reference_unit.",
}
_REFERENCE_RATIOS = {
    "selected_paired_identity": "Saved identical-position fraction of selected paired positions.",
    "selected_alignment_identity": "Saved identical-position fraction including selected gaps and insertions.",
    "selected_reference_aligned_fraction": "Saved aligned fraction of unique requested reference positions.",
    "selected_reference_paired_fraction": "Saved paired fraction of unique requested reference positions.",
    "selected_query_paired_coverage": "Saved selected paired query units divided by complete query length.",
    "selected_reference_paired_coverage": "Saved selected paired reference units divided by complete reference length.",
}
_BLAST_COUNTS = {
    "window_alignment_columns": "Count of realized selected alignment columns.",
    "paired_columns": "Count of selected columns with both symbols nongap.",
    "identical_pairs": "Count of identical paired native symbols in the selected window.",
    "substituted_pairs": "Count of substituted paired native symbols in the selected window.",
    "query_gap_columns": "Count of selected columns containing a query gap.",
    "reference_gap_columns": "Count of selected columns containing a reference gap.",
    "query_paired_units": "Union length of selected paired query intervals in group query_unit.",
    "reference_paired_units": "Union length of selected paired reference intervals in group reference_unit.",
}
_BLAST_RATIOS = {
    "paired_identity": "Saved identical-pair fraction of selected paired columns.",
    "alignment_identity": "Saved identical-pair fraction of all selected alignment columns.",
    "query_paired_coverage": "Saved selected paired query units divided by complete native query length.",
    "reference_paired_coverage": "Saved selected paired reference units divided by complete native reference length.",
}


def _error(code, field=None):
    raise ReportBoundaryError(code, code="alignment_site_" + code, field=field)


def _require(condition, code, field=None):
    if not condition:
        _error(code, field)


def _finite_json(value):
    stack, active = [(value, False)], set()
    while stack:
        item, leaving = stack.pop()
        if leaving:
            active.remove(id(item))
            continue
        kind = type(item)
        if item is None or kind in (str, bool, int) or kind is float and math.isfinite(item):
            continue
        _require(kind in (list, dict), "finite_json_required")
        _require(id(item) not in active, "finite_json_required")
        if kind is dict:
            _require(all(type(key) is str for key in item), "finite_json_required")
        active.add(id(item))
        stack.append((item, True))
        stack.extend((child, False) for child in (item.values() if kind is dict else item))


def _same(left, right):
    """JSON objects are unordered; arrays, duplicate entries and scalar types are exact."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _object(properties, *, nullable=False):
    return {"type": ["object", "null"] if nullable else "object",
        "properties": properties, "required": list(properties), "additionalProperties": False}


def _array(items, *, nullable=False, **bounds):
    return {"type": ["array", "null"] if nullable else "array", "items": items, **bounds}


def _integer(*, nullable=False, minimum=0):
    return {"type": ["integer", "null"] if nullable else "integer",
        **({"minimum": minimum} if minimum is not None else {})}


def _enum(values, *, nullable=False):
    return {"type": ["string", "null"] if nullable else "string",
        "enum": [*values, None] if nullable else list(values)}


def _reference(namespace=None, *, nullable=False):
    return {"type": ["string", "null"] if nullable else "string", "format": "reference",
        **({"x-reference-namespace": namespace} if namespace else {})}


def _symbol(*, nullable=True):
    return {"type": ["string", "null"] if nullable else "string", "format": "alignment_symbol"}


def _strand(*, nullable=True):
    return {"type": ["string", "null"] if nullable else "string", "format": "alignment_strand"}


def _interval(*, nullable=True):
    return _array(_integer(), nullable=nullable, minItems=2, maxItems=2)


def _segments():
    return _array(_object({"subject_ref": _reference(), "start": _integer(),
        "end": _integer(), "unit": _enum(_UNITS), "strand": _strand(nullable=False)}), nullable=True)


def _mapping_fields():
    return {role + "_" + name: deepcopy(node) for role in ("query", "reference")
        for name, node in {
            "original_intervals": _segments(), "mapping_status": _enum(_MAPPING),
            "mapping_reason": _enum(("site_original_mapping_unavailable",
                "site_original_mapping_conflict"), nullable=True)}.items()}


def _reference_row():
    return _object({"request_ordinal": _integer(), "reference_position": _integer(),
        "reference_interval": _interval(nullable=False), "query_interval": _interval(),
        "query_position": _integer(nullable=True), "reference_symbol": _symbol(),
        "query_symbol": _symbol(), "query_original_symbol": _symbol(),
        "relationship": _enum(("identical", "substituted", "query_gap", "reference_skip",
            "outside_alignment", "unavailable")),
        "alignment_column": _integer(nullable=True), "native_operation": _symbol(),
        "query_strand": _strand(), "query_quality_character": _symbol(),
        "query_quality_score": _integer(nullable=True, minimum=None),
        "quality_encoding": _enum(("unspecified", "phred33", "phred64", "solexa64")),
        "quality_scale": _enum(("phred", "solexa_log_odds"), nullable=True),
        **_mapping_fields(),
        "unavailable_reason": _enum(("site_native_geometry_unavailable",
            "site_native_geometry_conflict", "site_operand_identity_conflict"), nullable=True),
        "query_unit": _enum(_UNITS), "reference_unit": _enum(_UNITS)})


def _insertion_row():
    mapping = _mapping_fields()
    return _object({"event_ordinal": _integer(), "reference_boundary": _integer(),
        "query_interval": _interval(nullable=False), "query_strand": _strand(nullable=False),
        "query_sequence": _array(_symbol(nullable=False), minItems=1),
        "query_quality_characters": _array(_symbol(nullable=False), nullable=True),
        "alignment_column_interval": _interval(),
        **{key: value for key, value in mapping.items() if key.startswith("query_")},
        "query_unit": _enum(_UNITS), "reference_unit": _enum(_UNITS)})


def _blast_row():
    fields = {"column": _integer(), "query_symbol": _symbol(), "reference_symbol": _symbol(),
        "query_interval": _interval(), "reference_interval": _interval(),
        "query_unit": _enum(("aa", "nt")), "reference_unit": _enum(("aa", "nt")),
        "alignment_unit": _enum(("aa", "nt"))}
    for role in ("query", "reference"):
        fields[role + "_direction"] = {"type": ["integer", "null"], "enum": [-1, 1, None]}
        fields[role + "_frame"] = _integer(nullable=True, minimum=None)
        fields[role + "_strand"] = _enum(("Plus", "Minus"), nullable=True)
    fields.update({"relationship": _enum(("identical", "substituted", "query_gap",
        "reference_gap", "unavailable")), **_mapping_fields()})
    return _object(fields)


def _selection_schema(source):
    if source == _REFERENCE:
        return _object({"kind": _enum(("reference_positions", "reference_window")),
            "positions": _array(_integer(), nullable=True, minItems=1),
            "start": _integer(nullable=True), "end": _integer(nullable=True, minimum=1)})
    return _object({"column_offset": _integer(), "column_limit": {**_integer(minimum=1), "maximum": 4096},
        "column_end": _integer(nullable=True), "total_columns": _integer(nullable=True),
        "next_column_offset": _integer(nullable=True)})


def _components(source):
    counts, ratios = ((_REFERENCE_COUNTS, _REFERENCE_RATIOS) if source == _REFERENCE
        else (_BLAST_COUNTS, _BLAST_RATIOS))
    fields = {name: {**_integer(nullable=True), "description": meaning + " Missing remains null."}
        for name, meaning in counts.items()}
    for name, meaning in ratios.items():
        fields[name] = {**_object({"value": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
            "numerator": {"type": ["number", "null"], "minimum": 0},
            "denominator": {"type": ["number", "null"], "minimum": 0},
            "unit": {"type": "string", "const": "fraction"}}), "description": meaning}
    return _object(fields, nullable=True)


def alignment_site_fact_sources() -> dict:
    """Return detached available schemas; a parent must declare its own policy/subset."""
    result = {}
    for source in _SOURCES:
        fields = {"selection_policy": _enum(_POLICIES if source == _REFERENCE else _POLICIES[:3]),
            "alignment_ref": _reference("observation"), "selection": _selection_schema(source),
            "data_status": _enum(("complete", "partial", "no_alignment", "unavailable")),
            "rows": _array(_reference_row() if source == _REFERENCE else _blast_row(), nullable=True),
            **({"insertions": _array(_insertion_row(), nullable=True)} if source == _REFERENCE else {}),
            "components": _components(source), "issue_codes": _array(_enum(_ISSUES)),
            "query_ref": _reference(nullable=True), "reference_ref": _reference(nullable=True),
            "source_ref": _reference("source"),
            "operation_status": _enum(("completed", "partial"), nullable=True),
            "query_unit": _enum(_UNITS if source == _REFERENCE else ("aa", "nt"), nullable=True),
            "reference_unit": _enum(_UNITS if source == _REFERENCE else ("aa", "nt"), nullable=True)}
        result[source] = {"type": "array", "meaning": (
            "Explicitly selected completed own reference-position results, with requested order and duplicates retained."
            if source == _REFERENCE else
            "Explicitly selected completed own BLAST column-window reads, with native units and actual realized extent."),
            "report_schema": {**_array(_object(fields)), "x-source": source}}
    return result


def _types(node):
    declared = node["type"]
    return set(declared if type(declared) is list else [declared])


def _strict_values(value, node, path):
    """JSON Schema treats 1.0 as integer; these scientific integer cells do not."""
    if value is None:
        return
    kinds = _types(node)
    if "integer" in kinds:
        _require(type(value) is int, "integer_required", path)
    elif "number" in kinds:
        _require(type(value) in (int, float), "number_required", path)
    elif "string" in kinds and node.get("format") == "reference":
        _require(type(value) is str and bool(value), "reference_required", path)
    elif "object" in kinds and type(value) is dict:
        for name, child in value.items():
            _strict_values(child, node["properties"][name], path + "." + name)
        if "native_operation" in value:
            _require(value["native_operation"] in (None, "M", "=", "X", "D", "N"),
                "native_operation_invalid", path)
        for name in ("strand", "query_strand"):
            if name in value and node["properties"][name].get("format") == "alignment_strand":
                _require(value[name] in (None, "+", "-"), "strand_invalid", path + "." + name)
    elif "array" in kinds and type(value) is list:
        for index, child in enumerate(value):
            _strict_values(child, node["items"], f"{path}[{index}]")


def _validate_value(value, schema):
    wrapper = _object({"value": schema})
    validate_form({"value": value}, wrapper, lambda *_: True)
    _strict_values(value, schema, "value")


def _compatible(requested, available, path):
    _require(_types(requested) == _types(available), "projection_type_conflict", path)
    for name in ("format", "x-reference-namespace", "x-source"):
        _require(requested.get(name) == available.get(name), "projection_meaning_conflict", path)
    # The existing string grammar has no CODE spelling for '=' or '+'. Their
    # reusable symbol/strand formats therefore need this finite semantic check.
    semantic_values = ((None, "M", "=", "X", "D", "N") if path.endswith(".native_operation") else
        (None, "+", "-") if available.get("format") == "alignment_strand" else None)
    if semantic_values is not None:
        literals = requested.get("enum", []) + ([requested["const"]] if "const" in requested else [])
        _require(all(any(_same(value, allowed) for allowed in semantic_values) for value in literals),
            "projection_meaning_conflict", path)
    if "description" in requested:
        _require(requested["description"] == available.get("description"), "projection_meaning_conflict", path)
    if "const" in available:
        _require("const" in requested and _same(requested["const"], available["const"]),
            "projection_meaning_conflict", path)
    if "enum" in available:
        literals = requested.get("enum", [requested["const"]] if "const" in requested else None)
        _require(type(literals) is list and bool(literals) and all(
            any(_same(value, allowed) for allowed in available["enum"]) for value in literals),
            "projection_meaning_conflict", path)
    for name in ("minimum", "exclusiveMinimum", "minItems"):
        if name in available:
            _require(name in requested and type(requested[name]) in (int, float)
                and requested[name] >= available[name], "projection_bounds_conflict", path)
    for name in ("maximum", "exclusiveMaximum", "maxItems"):
        if name in available:
            _require(name in requested and type(requested[name]) in (int, float)
                and requested[name] <= available[name], "projection_bounds_conflict", path)
    if available.get("uniqueItems"):
        _require(requested.get("uniqueItems") is True, "projection_bounds_conflict", path)
    if "properties" in available:
        _require(set(requested["properties"]) <= set(available["properties"]), "projection_field_unknown", path)
        for name, child in requested["properties"].items():
            _compatible(child, available["properties"][name], path + "." + name)
    elif "items" in available:
        _compatible(requested["items"], available["items"], path + "[]")
    for literal in requested.get("enum", []):
        _validate_value(literal, {key: value for key, value in available.items() if key != "x-source"})
    if "const" in requested:
        _validate_value(requested["const"], {key: value for key, value in available.items() if key != "x-source"})
        # Contradictory selector literals must fail at construction, not after
        # their selected operation has already completed.
        _validate_value(requested["const"], {key: value for key, value in requested.items() if key != "x-source"})


def _mandatory(node, names, path):
    _require(set(names) <= set(node["properties"]), "projection_fields_required", path)


def _dependencies(source, fields):
    group = fields["items"]
    _mandatory(group, ("selection_policy", "alignment_ref", "selection", "data_status"), source)
    props = group["properties"]
    _mandatory(props["selection"], _selection_schema(source)["properties"], source + ".selection")
    if "rows" in props:
        row = props["rows"]["items"]
        _mandatory(row, ("request_ordinal", "reference_position", "reference_unit", "relationship")
            if source == _REFERENCE else ("column", "relationship"), source + ".rows")
        names = row["properties"]
        for role in ("query", "reference"):
            if role + "_interval" in names or role + "_position" in names:
                _mandatory(row, (role + "_unit",), source + ".rows")
    if "insertions" in props:
        _mandatory(props["insertions"]["items"], ("event_ordinal", "reference_boundary", "reference_unit",
            "query_interval", "query_unit", "query_strand"), source + ".insertions")
    for rows_name in ("rows", "insertions"):
        if rows_name in props:
            for name, node in props[rows_name]["items"]["properties"].items():
                if name.endswith("_original_intervals"):
                    _mandatory(node["items"], ("subject_ref", "start", "end", "unit", "strand"), source + "." + name)
    if "components" in props:
        components = props["components"]["properties"]
        ratios = _REFERENCE_RATIOS if source == _REFERENCE else _BLAST_RATIOS
        for name, node in components.items():
            if name in ratios:
                _mandatory(node, ("value", "numerator", "denominator", "unit"), source + "." + name)
        for role in ("query", "reference"):
            count = ("selected_" if source == _REFERENCE else "") + role + "_paired_units"
            if count in components:
                _mandatory(group, (role + "_unit",), source + ".components")


def _constraint(node):
    return "const" in node or "enum" in node


def _selection(source, fields):
    props = fields["items"]["properties"]
    policy = props.get("selection_policy", {}).get("const")
    _require(type(policy) is str and policy in (_POLICIES if source == _REFERENCE else _POLICIES[:3]),
        "explicit_selection_required")
    result = {"policy": policy, "alignment_refs": None, "positions": None, "window": None}
    ref = props["alignment_ref"]
    if policy == "all_own_completed_results":
        _require(not _constraint(ref), "selection_conflict")
    else:
        refs = [ref["const"]] if "const" in ref else ref.get("enum")
        _require(type(refs) is list and bool(refs) and all(type(value) is str
            and _OBSERVATION.fullmatch(value) for value in refs), "selection_reference_required")
        if "const" in ref and "enum" in ref:
            _require(any(_same(ref["const"], value) for value in ref["enum"]), "selection_conflict")
        result["alignment_refs"] = list(dict.fromkeys(refs))
    selection = props["selection"]["properties"]
    if source == _REFERENCE:
        kind = selection["kind"]
        positions = selection["positions"]
        start, end = selection["start"], selection["end"]
        if policy == "matching_alignment_window":
            _require(kind.get("const") == "reference_window" and not _constraint(positions["items"]),
                "selection_conflict")
            a, b = start.get("const"), end.get("const")
            _require(type(a) is int and type(b) is int and 0 <= a < b, "selection_window_required")
            result["window"] = {"start": a, "end": b}
        elif policy == "matching_alignment_position_set":
            _require(kind.get("const") == "reference_positions", "selection_conflict")
            _require(not _constraint(positions), "selection_conflict")
            values = positions["items"].get("enum")
            _require(type(values) is list and bool(values) and all(type(v) is int and v >= 0 for v in values)
                and len(values) == len(set(values)), "selection_positions_required")
            _require("const" not in positions["items"] and all(
                not _constraint(node) or node.get("const", 1) is None for node in (start, end)), "selection_conflict")
            result["positions"] = list(values)
        else:
            _require("const" not in kind and not _constraint(positions["items"])
                and not _constraint(positions) and not _constraint(start) and not _constraint(end)
                and set(kind.get("enum", [])) == {"reference_positions", "reference_window"}, "selection_conflict")
    else:
        offset, limit = selection["column_offset"], selection["column_limit"]
        if policy == "matching_alignment_window":
            a, b = offset.get("const"), limit.get("const")
            _require(type(a) is int and type(b) is int and a >= 0 and 1 <= b <= 4096,
                "selection_window_required")
            result["window"] = {"column_offset": a, "column_limit": b}
        else:
            _require(not _constraint(offset) and not _constraint(limit), "selection_conflict")
    return result


def _schema_signature(value):
    if type(value) is dict:
        return {key: sorted(child) if key in ("required", "type") and type(child) is list
            else _schema_signature(child) for key, child in value.items() if key != "description"}
    if type(value) is list:
        return [_schema_signature(child) for child in value]
    return value


def requested_site_projections(original_schema: dict) -> dict:
    """Validate each requested source and return its exact selector and field tree."""
    _finite_json(original_schema)
    schema = validate_closed_schema(original_schema)
    available = alignment_site_fact_sources()
    result = {}
    for field, node in schema["properties"].items():
        source = node.get("x-source")
        if source not in _SOURCES:
            continue
        _require(type(node.get("items")) is dict, "projection_type_conflict", field)
        policy = node["items"].get("properties", {}).get("selection_policy", {}).get("const")
        _require(type(policy) is str and policy in (_POLICIES if source == _REFERENCE else _POLICIES[:3]),
            "explicit_selection_required", field)
        _compatible(node, available[source]["report_schema"], field)
        _dependencies(source, node)
        projection = {"selection": _selection(source, node), "fields": deepcopy(node)}
        if source in result:
            _require(_same(projection["selection"], result[source]["selection"])
                and _same(_schema_signature(projection["fields"]), _schema_signature(result[source]["fields"])),
                "projection_conflict", field)
        else:
            result[source] = projection
    return result


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
