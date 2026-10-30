"""Parent-selected views of saved restriction supporting results.

The host authenticates actions and source custody. This module only validates
that supplied joins agree and copies the parent's requested fields. The saved
MappingResult remains the sole authority for numerical values.
"""
from copy import deepcopy

from jsonschema import Draft202012Validator

from .communication import CODE, ReportBoundaryError, validate_closed_schema
from .restriction_mapping_contracts import (
    restriction_canonical, restriction_schema, validate_restriction_record,
)


_SOURCE = "restriction_mapping_results"
_POLICIES = ("all_own_completed_results", "matching_sequence")
_TOOLS = ("find_restriction_sites", "find_restriction_enzymes")
_FAILURES = ("native_unavailable", "reader_unavailable", "mapping_invalid")
_ISSUES = tuple(restriction_schema("Issue")["properties"]["code"]["enum"]) + _FAILURES
_DNA = frozenset("ACGTRYSWKMBDHVNacgtryswkmbdhvn")
_ACTION_FIELDS = frozenset(("decision_index", "operation_ref", "tool_name", "work_mode",
    "operation_status", "sequence_ref", "namespace", "input_source_ref", "source_ref",
    "native_artifact_ref", "mapping_artifact_ref", "mapping", "failure_code"))


def _require(condition, code, field=None):
    if not condition:
        raise ReportBoundaryError(code, code="restriction_" + code, field=field)


def _finite(value):
    try:
        restriction_canonical(value)
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ReportBoundaryError("Finite JSON required", code="restriction_finite_json_required") from error


def _same(left, right):
    return restriction_canonical(left) == restriction_canonical(right)


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


def _reference(namespace=None):
    return {"type": "string", "format": "reference",
        **({"x-reference-namespace": namespace} if namespace else {})}


def _position_schema():
    fields = {"position_ordinal": _integer(), "native_position": _integer(minimum=None)}
    fields.update({name: _integer(nullable=True, minimum=None) for name in
        ("watson_boundary_0based", "crick_boundary_0based")})
    fields.update({name: _integer(nullable=True) for name in
        ("watson_canonical_boundary_0based", "crick_canonical_boundary_0based")})
    fields.update(geometry_state=_enum(("known", "unknown", "unavailable")),
        recognition_association={"type": "string", "const": "not_recorded"},
        recognition_event_ordinal={"type": "null"})
    return _object(fields)


def _event_schema():
    return _object({"match_call_ordinal": _integer(), "match_ordinal": _integer(),
        "native_start_1based": _integer(minimum=None),
        "orientation": _enum(("forward", "reverse", "palindromic", "unknown")),
        "unwrapped_span_0based": _array(_integer(minimum=None), nullable=True, minItems=2, maxItems=2),
        "segments": _array(_object({"start": _integer(minimum=None),
            "end": _integer(minimum=None)}), nullable=True),
        "crosses_origin": {"type": ["boolean", "null"]}})


def _row_schema():
    return _object({"catalog_ordinal": _integer(), "name": {"type": "string", "format": "identifier",
            "x-reference-namespace": "restriction_enzyme"},
        "search_state": _enum(("not_started", "returned", "failed", "invalid")),
        "position_meaning": _enum(("first_base_after_cut_1based", "recognition_start_1based", "unknown")),
        "native_search_positions_1based": _array(_integer(minimum=None), nullable=True),
        "returned_position_count": _integer(nullable=True),
        "recognition_match_count": _integer(nullable=True),
        "positions": _array(_position_schema(), nullable=True),
        "recognition_events": _array(_event_schema(), nullable=True),
        "recognition_motif": {"type": ["string", "null"], "format": "dna_sequence"},
        "issue_codes": _array(_enum(_ISSUES), uniqueItems=True)})


def restriction_mapping_fact_sources():
    """Return a detached available schema; the parent chooses its own subset."""
    meanings = {
        "selected_enzyme_count": "Enzymes in the full validated selected catalog; no prevalence denominator.",
        "attempted_enzyme_count": "Validated returned or failed enzyme searches in the selected population.",
        "returned_enzyme_count": "Validated returned enzyme searches in the selected population.",
        "complete_empty_enzyme_count": "Returned enzyme searches whose complete native position list is empty.",
        "recognition_match_count": "Actual validated uniquely owned observed recognition matches; unavailable is null.",
    }
    population = {name: {**_integer(nullable=name in ("selected_enzyme_count", "recognition_match_count")),
        "description": meaning} for name, meaning in meanings.items()}
    fields = {"selection_policy": _enum(_POLICIES), "sequence_ref": _reference(),
        "namespace": _enum(("subject", "reference")), "tool_name": _enum(_TOOLS),
        "work_mode": _enum(("native", "saved")), "operation_status": _enum(("completed", "partial")),
        "source_ref": _reference("source"), "input_source_ref": _reference("source"),
        "topology": _enum(("linear", "circular"), nullable=True),
        "data_status": _enum(("complete", "partial", "invalid", "unavailable")),
        "coordinate_unit": {"type": "string", "const": "nt"},
        "population_scope": {"type": "string", "const": "full_selected_native_enzyme_population"},
        "population": _object(population, nullable=True),
        "enzyme_rows": _array(_row_schema(), nullable=True),
        "issue_codes": _array(_enum(_ISSUES), uniqueItems=True)}
    return {_SOURCE: {"type": "array", "meaning":
        "Parent-selected saved conditional restriction predictions, with original population, coordinates and missingness; no function-confidence score.",
        "report_schema": {**_array(_object(fields)), "x-source": _SOURCE}}}


def _types(node):
    declared = node["type"]
    return set(declared if type(declared) is list else [declared])


def _strict_values(value, schema, path):
    if value is None:
        return
    kinds = _types(schema)
    if "integer" in kinds:
        _require(type(value) is int, "integer_required", path)
    elif "boolean" in kinds:
        _require(type(value) is bool, "boolean_required", path)
    elif "string" in kinds:
        _require(type(value) is str, "string_required", path)
        if schema.get("format") in ("reference", "identifier"):
            _require(bool(value), "reference_required", path)
        if schema.get("format") == "identifier":
            _require(CODE.fullmatch(value) is not None, "identifier_invalid", path)
        if schema.get("format") == "dna_sequence":
            _require(bool(value) and set(value) <= _DNA, "motif_invalid", path)
    elif "object" in kinds:
        _require(type(value) is dict, "object_required", path)
        for name, child in value.items():
            _strict_values(child, schema["properties"][name], path + "." + name)
    elif "array" in kinds:
        _require(type(value) is list, "array_required", path)
        for index, child in enumerate(value):
            _strict_values(child, schema["items"], f"{path}[{index}]")


def _validate_value(value, schema, path="value"):
    """Check local structure and scalar semantics; grant no reference authority."""
    _finite(value)
    _require(Draft202012Validator(schema).is_valid(value), "projection_value_invalid", path)
    _strict_values(value, schema, path)


def _compatible(requested, available, path):
    _require(_types(requested) == _types(available), "projection_type_conflict", path)
    for name in ("format", "x-reference-namespace", "x-source"):
        _require(requested.get(name) == available.get(name), "projection_meaning_conflict", path)
    if "description" in requested:
        _require(requested["description"] == available.get("description"), "projection_meaning_conflict", path)
    if "const" in available:
        _require("const" in requested and _same(requested["const"], available["const"]), "projection_meaning_conflict", path)
    if "enum" in available:
        literals = requested.get("enum", [requested["const"]] if "const" in requested else None)
        _require(type(literals) is list and bool(literals) and all(
            any(_same(v, allowed) for allowed in available["enum"]) for v in literals),
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
        _validate_value(literal, available, path)
    if "const" in requested:
        _validate_value(requested["const"], available, path)
        _validate_value(requested["const"], requested, path)


def _mandatory(node, names, path):
    _require(set(names) <= set(node["properties"]), "projection_fields_required", path)


def _dependencies(fields):
    group = fields["items"]
    _mandatory(group, ("selection_policy", "sequence_ref", "namespace", "topology", "data_status",
        "coordinate_unit", "population_scope"), _SOURCE)
    rows = group["properties"].get("enzyme_rows")
    if rows is None:
        return
    row = rows["items"]
    _mandatory(row, ("catalog_ordinal", "name", "search_state", "position_meaning"), _SOURCE + ".enzyme_rows")
    if "positions" in row["properties"]:
        _mandatory(row["properties"]["positions"]["items"], ("position_ordinal", "native_position",
            "geometry_state", "recognition_association", "recognition_event_ordinal"), _SOURCE + ".positions")
    events = row["properties"].get("recognition_events")
    if events is not None:
        _mandatory(events["items"], ("match_call_ordinal", "match_ordinal", "native_start_1based", "orientation"),
            _SOURCE + ".recognition_events")
        segments = events["items"]["properties"].get("segments")
        if segments is not None:
            _mandatory(segments["items"], ("start", "end"), _SOURCE + ".segments")


def _signature(value):
    if type(value) is dict:
        return {key: sorted(child) if key in ("required", "type") and type(child) is list
            else _signature(child) for key, child in value.items() if key != "description"}
    return [_signature(v) for v in value] if type(value) is list else value


def requested_restriction_projections(original_schema):
    """Validate the parent's exact source selection and closed field subset."""
    _finite(original_schema)
    try:
        schema = validate_closed_schema(original_schema)
    except (ValueError, TypeError, KeyError, RecursionError) as error:
        raise ReportBoundaryError("Invalid requested schema", code="restriction_projection_schema_invalid") from error
    available = restriction_mapping_fact_sources()[_SOURCE]["report_schema"]
    result = {}
    for field, node in schema["properties"].items():
        source = node.get("x-source")
        if source != _SOURCE:
            _require(not (type(source) is str and source.startswith("restriction_mapping_")),
                "projection_source_unknown", field)
            continue
        try:
            _compatible(node, available, field)
            _dependencies(node)
            props = node["items"]["properties"]
            policy = props["selection_policy"].get("const")
            _require(type(policy) is str and policy in _POLICIES, "explicit_selection_required", field)
            selected = props["sequence_ref"]
            if policy == "matching_sequence":
                reference = selected.get("const")
                _require(type(reference) is str and bool(reference), "selection_reference_required", field)
            else:
                _require("const" not in selected and "enum" not in selected, "selection_conflict", field)
                reference = None
            projection = {"selection": {"policy": policy, "sequence_ref": reference}, "fields": deepcopy(node)}
            if _SOURCE in result:
                _require(_same(_signature(result[_SOURCE]), _signature(projection)), "projection_conflict", field)
            else:
                result[_SOURCE] = projection
        except (KeyError, TypeError, AttributeError) as error:
            raise ReportBoundaryError("Invalid projection structure", code="restriction_projection_schema_invalid", field=field) from error
    return result


def _project(value, schema):
    if value is None:
        return None
    if "properties" in schema:
        return {name: _project(value[name], child) for name, child in schema["properties"].items()}
    if "items" in schema:
        return [_project(child, schema["items"]) for child in value]
    return deepcopy(value)


def _codes(issues):
    return list(dict.fromkeys(issue["code"] for issue in issues))


def _action(record):
    _finite(record)
    _require(type(record) is dict and set(record) == _ACTION_FIELDS, "action_record_invalid")
    _require(type(record["decision_index"]) is int and record["decision_index"] >= 0
        and record["tool_name"] in _TOOLS and record["work_mode"] in ("native", "saved")
        and record["operation_status"] in ("completed", "partial")
        and record["namespace"] in ("subject", "reference"), "action_record_invalid")
    for name in ("operation_ref", "sequence_ref", "input_source_ref", "source_ref"):
        _require(type(record[name]) is str and bool(record[name]), "action_reference_invalid", name)
    for name in ("native_artifact_ref", "mapping_artifact_ref"):
        _require(record[name] is None or type(record[name]) is str and bool(record[name]),
            "action_reference_invalid", name)
    if record["mapping"] is None:
        _require(record["mapping_artifact_ref"] is None and record["failure_code"] in _FAILURES,
            "action_availability_conflict")
        return None
    _require(record["failure_code"] is None and record["native_artifact_ref"] is not None
        and record["mapping_artifact_ref"] is not None, "action_availability_conflict")
    try:
        mapping = validate_restriction_record("MappingResult", record["mapping"])
    except (ValueError, TypeError, KeyError, RecursionError) as error:
        raise ReportBoundaryError("Invalid saved MappingResult", code="restriction_mapping_record_invalid") from error
    selected = mapping["selected_sequence"]
    _require((selected["sequence_ref"], selected["namespace"], selected["source_ref"]) ==
        (record["sequence_ref"], record["namespace"], record["input_source_ref"]), "action_binding_conflict")
    return mapping


def project_restriction_action_return(record, requested_fields):
    """Copy one authenticated own result; do not calculate or grant authority."""
    projections = requested_restriction_projections(_object({"value": requested_fields}))
    _require(_SOURCE in projections, "projection_source_required")
    selected = projections[_SOURCE]["selection"]
    mapping = _action(record)
    _require(selected["sequence_ref"] is None or selected["sequence_ref"] == record["sequence_ref"],
        "selection_mismatch")
    value = {name: record[name] for name in ("sequence_ref", "namespace", "tool_name", "work_mode",
        "operation_status", "source_ref", "input_source_ref")}
    value.update(selection_policy=selected["policy"], coordinate_unit="nt",
        population_scope="full_selected_native_enzyme_population", topology=None,
        data_status="unavailable", population=None, enzyme_rows=None, issue_codes=[record["failure_code"]])
    if mapping is not None:
        rows = []
        for saved in mapping["enzyme_rows"]:
            row = {name: deepcopy(saved[name]) for name in ("catalog_ordinal", "name", "search_state",
                "position_meaning", "native_search_positions_1based", "returned_position_count",
                "recognition_match_count", "positions")}
            row.update(recognition_motif=None if saved["catalog_row"] is None else saved["catalog_row"]["native_site"],
                recognition_events=None if saved["recognition_events"] is None else
                [{k: deepcopy(v) for k, v in event.items() if k != "native_groups"}
                    for event in saved["recognition_events"]], issue_codes=_codes(saved["issues"]))
            rows.append(row)
        value.update(topology=mapping["topology"], data_status=mapping["status"],
            population=deepcopy(mapping["population"]), enzyme_rows=rows, issue_codes=_codes(mapping["issues"]))
    result = _project(value, requested_fields["items"])
    _validate_value(result, requested_fields["items"])
    return result


def validate_frozen_restriction_return(form, original_schema, frozen_facts):
    """Require exact original saved source arrays without a model restatement."""
    projections = requested_restriction_projections(original_schema)
    if not projections:
        return
    _finite(form)
    _finite(frozen_facts)
    _require(type(form) is dict, "form_required")
    _require(type(frozen_facts) is dict, "frozen_facts_unavailable")
    _require(_SOURCE in frozen_facts and type(frozen_facts[_SOURCE]) is list, "frozen_source_missing")
    for field, node in original_schema["properties"].items():
        if node.get("x-source") != _SOURCE:
            continue
        _require(field in form, "form_field_missing", field)
        _validate_value(form[field], node, field)
        _validate_value(frozen_facts[_SOURCE], node, field)
        _require(_same(form[field], frozen_facts[_SOURCE]), "frozen_source_mismatch", field)


__all__ = ["restriction_mapping_fact_sources", "requested_restriction_projections",
    "project_restriction_action_return", "validate_frozen_restriction_return"]
