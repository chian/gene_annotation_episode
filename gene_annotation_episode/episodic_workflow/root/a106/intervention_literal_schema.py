"""A106 original retained literal-value grammar."""
from copy import deepcopy

MAX_NATIVE_DEPTH = 32
VALUE_VERSION = "bvbrc_intervention_selected_field_v1"

def _object(properties):
    return {"type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False}

def _definitions():
    definitions = {}
    scalar = [{"type": "null"}, {"type": "boolean"}, {"type": "number"}, {"type": "string"}]
    for depth in range(MAX_NATIVE_DEPTH + 1):
        choices = deepcopy(scalar)
        native = [_object({"kind": {"const": "null"}, "value": {"type": "null"}}),
            _object({"kind": {"const": "boolean"}, "value": {"type": "boolean"}}),
            _object({"kind": {"const": "string"}, "value": {"type": "string"}}),
            _object({"kind": {"const": "number"}, "token": {"type": "string",
                "pattern": r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?(?![\s\S])"}})]
        if depth:
            child = {"$ref": "#/$defs/AnnotationJSON" + str(depth - 1)}
            choices += [{"type": "array", "items": child},
                {"type": "object", "additionalProperties": child}]
            native_child = {"$ref": "#/$defs/AnnotationNative" + str(depth - 1)}
            native += [_object({"kind": {"const": "array"},
                "items": {"type": "array", "items": native_child}}),
                _object({"kind": {"const": "object"}, "members": {"type": "array",
                    "items": _object({"name": {"type": "string"}, "value": native_child})}})]
        else:
            choices += [{"type": "array", "items": False},
                {"type": "object", "additionalProperties": False}]
            native += [_object({"kind": {"const": "array"}, "items": {"type": "array", "items": False}}),
                _object({"kind": {"const": "object"}, "members": {"type": "array", "items": False}})]
        definitions["AnnotationJSON" + str(depth)] = {"anyOf": choices}
        definitions["AnnotationNative" + str(depth)] = {"oneOf": native}
    return definitions

def _field_schema(selection):
    value_type = {"$ref": "#/$defs/AnnotationJSON" + str(MAX_NATIVE_DEPTH)} if selection["kind"] == "components" else {
        "$ref": "#/$defs/AnnotationNative" + str(MAX_NATIVE_DEPTH)}
    json_type = {"$ref": "#/$defs/AnnotationJSON" + str(MAX_NATIVE_DEPTH)}
    record = _object({"requested_ordinal": {"type": ["integer", "null"], "minimum": 0},
        "source_pointer": {"type": ["string", "null"]},
        "state": {"enum": ["available", "stored_null", "path_missing", "source_unavailable", "incompatible"]},
        "value": {"anyOf": [{"type": "null"}, value_type]}})
    null_value = {"type": "null"} if selection["kind"] == "components" else {
        "const": {"kind": "null", "value": None}}
    record["allOf"] = [{"if": {"properties": {"state": {"enum": ["path_missing", "source_unavailable", "incompatible"]}}},
        "then": {"properties": {"value": {"type": "null"}}}},
        {"if": {"properties": {"state": {"const": "stored_null"}}},
         "then": {"properties": {"value": null_value}}},
        {"if": {"properties": {"state": {"const": "available"}}},
         "then": {"properties": {"value": {"allOf": [value_type, {"not": null_value}]},
            "source_pointer": {"type": "string", "minLength": 1}}}}]
    return _object({"version": {"const": VALUE_VERSION}, "selection": {"const": deepcopy(selection)},
        "records": {"type": "array", "items": record},
        "record_accounting": _object({"retained_total": {"type": ["integer", "null"], "minimum": 0},
            "requested_occurrences": {"type": ["integer", "null"], "minimum": 0},
            "matched_occurrences": {"type": ["integer", "null"], "minimum": 0},
            "returned_occurrences": {"type": "integer", "minimum": 0},
            "population_scope": {"const": "retained_native_records_only"},
            "intended_population_complete": {"type": "null"}}),
        "context": json_type, "issues": json_type})

def selected_field_schema():
    """Whole retained field grammar; its selection-specific validator is mandatory.

    Native JSON is opaque data. The only reference implication is attached by
    the actual AppService return owner's separate top-level Source field.
    """
    placeholder = {"version": "bvbrc_intervention_selection_v1", "document_id": "schema-only",
        "kind": "records", "ordinals": None, "offset": 0, "limit": 0, "member_names": None}
    result = _field_schema(placeholder)
    result["properties"]["selection"] = {}
    record = result["properties"]["records"]["items"]
    literal = {"anyOf": [{"$ref": "#/$defs/AnnotationJSON" + str(MAX_NATIVE_DEPTH)},
        {"$ref": "#/$defs/AnnotationNative" + str(MAX_NATIVE_DEPTH)}]}
    null = {"anyOf": [{"type": "null"}, {"const": {"kind": "null", "value": None}}]}
    record["properties"]["value"] = literal
    record["allOf"][1]["then"]["properties"]["value"] = null
    record["allOf"][2]["then"]["properties"]["value"] = {"allOf": [literal, {"not": null}]}
    result["$defs"] = _definitions()
    return result

