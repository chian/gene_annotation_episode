"""Closed selection and literal-value contracts for BV-BRC annotation results.

These are native-observation/selection contracts, not a new annotation score.
Only the existing AppService return owner may attach an authentic publication
Source. Native JSON strings and nested input/Artifact identities are opaque.
"""
from __future__ import annotations

from copy import deepcopy

from jsonschema import Draft202012Validator

from .bvbrc_annotation_native import MAX_NATIVE_DEPTH, _canonical, _finite_json


PARAMETERS_VERSION = "bvbrc_annotation_parameters_v1"
SELECTION_VERSION = "bvbrc_annotation_selection_v1"
VALUE_VERSION = "bvbrc_annotation_selected_field_v1"
# CGA publishes its component and final GTOs separately. The existing reader
# preserves each selected document and its native task identity; membership
# here does not equate the component job with its enclosing CGA task.
APPLICATIONS = ("GenomeAnnotation", "ComprehensiveGenomeAnalysis")
KINDS = ("native_document", "contigs", "features", "analysis_events", "quality", "components")


def _require(condition, code="bvbrc_annotation_contract_invalid"):
    if not condition:
        raise ValueError(code)


def _object(properties):
    return {"type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False}


def _text():
    return {"type": "string", "minLength": 1}


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


def selection_schema():
    result = _object({"version": {"const": SELECTION_VERSION}, "document_id": _text(),
        "kind": {"enum": list(KINDS)},
        "ordinals": {"type": ["array", "null"], "items": {"type": "integer", "minimum": 0}},
        "offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 0},
        "member_names": {"type": ["array", "null"], "items": {"type": "string"}, "uniqueItems": True}})
    return deepcopy(result)


def validate_selection(value):
    _finite_json(value)
    _require(type(value) is dict and set(value) == set(selection_schema()["properties"]))
    _require(value["version"] == SELECTION_VERSION and type(value["kind"]) is str and value["kind"] in KINDS
        and type(value["document_id"]) is str and bool(value["document_id"])
        and type(value["offset"]) is int and value["offset"] >= 0
        and type(value["limit"]) is int and value["limit"] >= 0)
    ordinals = value["ordinals"]
    _require(ordinals is None or type(ordinals) is list
        and all(type(item) is int and item >= 0 for item in ordinals))
    names = value["member_names"]
    _require(names is None or type(names) is list and all(type(item) is str for item in names)
        and len(set(names)) == len(names))
    _require(value["kind"] not in {"native_document", "quality", "components"} or ordinals is None)
    return deepcopy(value)


def parameters_schema():
    return _object({"version": {"const": PARAMETERS_VERSION}, "analysis_id": _text(),
        "application_id": {"enum": list(APPLICATIONS)}, "documents": {"type": "array", "minItems": 1,
            "items": _object({"document_id": _text(), "requirement_id": _text(),
                "representation": {"enum": ["gto", "quality_json"]}})}})


def validate_parameters(value):
    _finite_json(value)
    try:
        Draft202012Validator(parameters_schema()).validate(value)
    except Exception as error:
        raise ValueError("bvbrc_annotation_parameters_invalid") from error
    documents = value["documents"]
    _require(len({row["document_id"] for row in documents}) == len(documents),
        "bvbrc_annotation_document_identity_ambiguous")
    return deepcopy(value)


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


def requested_form_schema(fields):
    """Build the private adapter's exact selected-field schema, in caller order."""
    _finite_json(fields)
    _require(type(fields) is list)
    names, properties = [], {}
    for field in fields:
        _require(type(field) is dict and set(field) == {"field", "selection"}
            and type(field["field"]) is str and bool(field["field"]) and field["field"] not in names)
        name, selection = field["field"], validate_selection(field["selection"])
        names.append(name)
        properties[name] = {**_field_schema(selection), "x-bvbrc-annotation-selection": selection}
    return {"type": "object", "properties": properties, "required": names,
        "additionalProperties": False, "$defs": _definitions()}


def selected_field_schema():
    """Whole retained field grammar; its selection-specific validator is mandatory.

    Native JSON is opaque data. The only reference implication is attached by
    the actual AppService return owner's separate top-level Source field.
    """
    placeholder = {"version": SELECTION_VERSION, "document_id": "schema-only",
        "kind": "features", "ordinals": None, "offset": 0, "limit": 0, "member_names": None}
    result = _field_schema(placeholder)
    result["properties"]["selection"] = selection_schema()
    record = result["properties"]["records"]["items"]
    literal = {"anyOf": [{"$ref": "#/$defs/AnnotationJSON" + str(MAX_NATIVE_DEPTH)},
        {"$ref": "#/$defs/AnnotationNative" + str(MAX_NATIVE_DEPTH)}]}
    null = {"anyOf": [{"type": "null"}, {"const": {"kind": "null", "value": None}}]}
    record["properties"]["value"] = literal
    record["allOf"][1]["then"]["properties"]["value"] = null
    record["allOf"][2]["then"]["properties"]["value"] = {"allOf": [literal, {"not": null}]}
    result["$defs"] = _definitions()
    return result


def validate_selected_field(value):
    _finite_json(value)
    _require(type(value) is dict and "selection" in value)
    selection = validate_selection(value["selection"])
    form = requested_form_schema([{"field": "selected", "selection": selection}])
    return validate_facts({"selected": value}, requested_form=form)["selected"]


def validate_requested_form(value):
    _finite_json(value)
    _require(type(value) is dict and set(value) == {"type", "properties", "required", "additionalProperties", "$defs"}
        and type(value["properties"]) is dict and type(value["required"]) is list)
    fields = []
    for name in value["required"]:
        _require(type(name) is str and name in value["properties"]
            and type(value["properties"][name]) is dict)
        fields.append({"field": name, "selection": value["properties"][name].get("x-bvbrc-annotation-selection")})
    _require(_canonical(value) == _canonical(requested_form_schema(fields)),
        "bvbrc_annotation_requested_form_invalid")
    return deepcopy(value)


def validate_facts(value, *, requested_form):
    form = validate_requested_form(requested_form)
    _finite_json(value)
    try:
        Draft202012Validator(form).validate(value)
    except Exception as error:
        raise ValueError("bvbrc_annotation_facts_invalid") from error
    for field in value.values():
        accounting = field["record_accounting"]
        _require(all(accounting[key] is None or type(accounting[key]) is int for key in
            ("retained_total", "requested_occurrences", "matched_occurrences"))
            and type(accounting["returned_occurrences"]) is int
            and accounting["returned_occurrences"] == len(field["records"]),
            "bvbrc_annotation_facts_invalid")
        _require(all(row["requested_ordinal"] is None or type(row["requested_ordinal"]) is int
            for row in field["records"]), "bvbrc_annotation_facts_invalid")
        requested, matched = accounting["requested_occurrences"], accounting["matched_occurrences"]
        _require(matched is None or requested is not None and matched <= requested,
            "bvbrc_annotation_facts_invalid")
    return deepcopy(value)


__all__ = ["PARAMETERS_VERSION", "SELECTION_VERSION", "VALUE_VERSION", "APPLICATIONS", "KINDS",
    "parameters_schema", "validate_parameters", "selection_schema", "validate_selection",
    "requested_form_schema", "validate_requested_form", "validate_facts",
    "selected_field_schema", "validate_selected_field"]
