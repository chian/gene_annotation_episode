"""Finite provider selections, separate from the parent's communication schema.

The marker freezes a selector, cardinality and availability meaning. Rendering
does not calculate a value or establish possession of a scientific result.
"""
from __future__ import annotations

from copy import deepcopy

from .bvbrc_comparative_systems_handoff_contracts import canonical_sha256, schema, validate_shape

MARKER = "x-bvbrc-comparative-systems"
FACT_SOURCES = {
    "measurement": "bvbrc_comparative_systems_measurements",
    "computed_measurement": "bvbrc_comparative_systems_measurements",
    "ratio": "bvbrc_comparative_systems_ratios",
    "population": "bvbrc_comparative_systems_populations",
    "membership": "bvbrc_comparative_systems_memberships",
    "requirement": "bvbrc_comparative_systems_requirements",
    "qualification": "bvbrc_comparative_systems_qualifications",
    "request_status": "bvbrc_comparative_systems_request_status",
}
_KINDS = {"measurement": "NumericCellV1", "computed_measurement": "NumericCellV1",
          "ratio": "RatioComponentV1", "population": "PopulationFactV1",
          "membership": "MembershipFactV1", "requirement": "RequirementV1",
          "qualification": "DiagnosticV1"}
_ENTITY_ALLOWED = {
    "family": {"family_kind", "family_id"}, "pathway": {"pathway_id"},
    "pathway_ec": {"pathway_id", "ec_number"},
    "subsystem": {"subsystem_id", "superclass_native", "superclass_aggregation", "class_name", "subclass", "subsystem_name"},
    "subsystem_role": {"subsystem_id", "role_id", "superclass_native", "superclass_aggregation", "class_name", "subclass", "subsystem_name"},
    "overview": {"superclass_native", "superclass_aggregation", "class_name", "subclass"},
    "variant": {"superclass_native", "superclass_aggregation", "class_name", "subclass", "subsystem_name"},
}


def require(condition, code):
    if not condition:
        raise ValueError("comparative_systems_" + code)


def _expanded(name):
    closure = schema(name)
    definitions = closure["$defs"]

    def expand(node):
        if type(node) is list:
            return [expand(item) for item in node]
        if type(node) is not dict:
            return node
        if "$ref" in node:
            return expand(definitions[node["$ref"].split("/")[-1]])
        return {key: expand(item) for key, item in node.items()}

    return expand(definitions[name])


def validate_entity(value, *, membership=False):
    entity = validate_shape("EntityV1", value)
    kind = entity["kind"]
    require(kind in _ENTITY_ALLOWED, "selector_entity_kind_invalid")
    allowed = _ENTITY_ALLOWED[kind]
    require(all(item is None for key, item in entity.items() if key not in allowed | {"kind"}),
            "selector_entity_field_invalid")
    needed = {"family": ("family_kind", "family_id"), "pathway": ("pathway_id",),
              "pathway_ec": ("pathway_id", "ec_number"), "subsystem": ("subsystem_id",),
              "subsystem_role": ("subsystem_id", "role_id"), "overview": ("superclass_native",),
              "variant": ("superclass_native", "class_name", "subclass", "subsystem_name")}[kind]
    require(all(type(entity[key]) is str and bool(entity[key].strip()) for key in needed),
            "selector_entity_identifier_required")
    if entity["superclass_native"] is not None:
        require(entity["superclass_aggregation"] == entity["superclass_native"].upper(),
                "selector_entity_hierarchy_mismatch")
    if membership:
        require(kind in {"family", "pathway", "pathway_ec", "subsystem", "subsystem_role"},
                "membership_entity_kind_invalid")
    return entity


def validate_requested_selection(value):
    selection = validate_shape("RequestedSelectionV1", value)
    ids = [field["field_id"] for field in selection["fields"]]
    require(len(ids) == len(set(ids)), "duplicate_requested_field")
    for field in selection["fields"]:
        selector = field["selector"]
        if "entity" in selector:
            validate_entity(selector["entity"], membership=selector["kind"] == "membership")
        if selector["kind"] in {"requirement", "qualification", "request_status"}:
            require(field["availability_requirement"] == "typed_state", "selector_availability_invalid")
    return selection


def value_schema(selector):
    kind = selector["kind"]
    if kind == "request_status":
        return deepcopy(schema("FactValueV1")["$defs"]["FactValueV1"]["oneOf"][-1])
    result = _expanded(_KINDS[kind])
    # Exact semantic identifiers are constrained in the provider schema as well
    # as checked against the selected original saved values during projection.
    if kind == "membership":
        for key in ("entity", "genome_id", "member_id", "population_id"):
            result["properties"][key] = {"const": deepcopy(selector[key])}
    elif kind == "population":
        result["properties"]["population_id"] = {"const": selector["population_id"]}
    elif kind == "requirement":
        result["properties"]["required_input_role"] = {"const": selector["required_input_role"]}
    elif kind == "qualification":
        result["properties"]["code"] = {"const": selector["code"]}
    return result


def requested_form_schema(selection):
    """Render a RequestedSelectionV1 to the provider's canonical JSON Schema.

    I renders its separate parent form using the communication keyword set.
    Internal JSON Schema conditionals/references are not a parent prompt.
    """
    selected = validate_requested_selection(selection)
    properties = {}
    for field in sorted(selected["fields"], key=lambda item: item["field_id"]):
        count = field["expected_cardinality"]
        properties[field["field_id"]] = {
            "type": "object", "additionalProperties": False,
            "required": ["field_id", "values", "status"],
            "properties": {"field_id": {"const": field["field_id"]},
                           "values": {"type": "array", "items": value_schema(field["selector"]),
                                      "minItems": 0, "maxItems": count},
                           "status": {"type": "string", "enum": ["satisfied", "partial", "invalid", "unavailable"]}},
            MARKER: deepcopy(field),
        }
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def requested_selection(form):
    require(type(form) is dict and type(form.get("properties")) is dict, "requested_form_invalid")
    fields = []
    for key, node in sorted(form["properties"].items()):
        require(type(node) is dict and MARKER in node, "requested_form_marker_missing")
        field = validate_shape("RequestedFieldV1", node[MARKER])
        require(field["field_id"] == key, "requested_field_identity_mismatch")
        fields.append(field)
    return validate_requested_selection({"version": "bvbrc_comparative_systems_requested_selection_v1", "fields": fields})


def validate_requested_form(value):
    selection = requested_selection(value)
    expected = requested_form_schema(selection)
    require(canonical_sha256(value) == canonical_sha256(expected), "requested_form_noncanonical")
    return deepcopy(expected)


__all__ = ["MARKER", "FACT_SOURCES", "requested_form_schema", "validate_requested_form",
           "requested_selection", "validate_requested_selection", "value_schema"]
