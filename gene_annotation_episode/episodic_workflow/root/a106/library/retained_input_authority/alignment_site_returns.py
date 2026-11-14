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

from gene_annotation_episode.episodic_workflow.root.a106.communication import ReportBoundaryError, validate_closed_schema, validate_form

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
