from __future__ import annotations

from copy import deepcopy
from . import literature_controlled_response_declarations as _old
from .literature_rate_return_schema import RATE_UNITS

_INPUT_VERSION = "controlled_response_owner_inputs_v2"

_ROLES = _old.PRIMITIVE_ORDER

def _obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def _schema():
    text, number = {"type": "string", "minLength": 1}, {"type": "number"}
    def enum(values):
        return {"enum": list(values)}
    def nullable(value):
        return {"anyOf": [value, {"type": "null"}]}
    def array(value, **kwargs):
        return {"type": "array", "items": value, **kwargs}
    def reference(name):
        return {"$ref": "#/$defs/" + name}
    state = enum(("known", "unknown", "conflicting"))
    arm = _obj({"value": nullable(number), "threshold": nullable(number),
        "relation": enum(("eq", "lt", "le", "gt", "ge", "interval", "none")),
        "approximate": {"type": "boolean"}, "unit": nullable(enum(RATE_UNITS)),
        "status": enum(("point", "bound", "missing", "ambiguous", "conflicting", "unsupported")),
        **{name + "_id": nullable(text) for name in _old._MEANINGS},
        "source_observation_id": nullable(text), "origin": enum(("reported", "graph_derived", "synthetic")),
        "digitization_interval": nullable(_obj({"lower": number, "upper": number})),
        "protein_arrangement": enum(_old._ARRANGEMENTS),
        "meaning_statuses": _obj({name: state for name in _old._MEANINGS})})
    target = _obj({"status": state, "canonical_id": nullable(text)})
    relationships = _obj({"condition1_target": target, "condition0_target": target,
        "condition_levels_relation": enum(("same", "different", "unknown", "conflicting")),
        "subject_construct_across_conditions": enum(("same", "different", "unknown", "conflicting")),
        **{name: enum(_old._APPLICATIONS) for name in
           ("condition1_control_application", "condition0_control_application")},
        "control_reference_reuse": enum(_old._REUSE),
        "nonintended_conditions": enum(("matched", "different", "unknown", "conflicting")),
        "intended_factor": nullable(text)})
    role_covariance = _obj({"primitive_order": {"const": list(_ROLES)},
        "physical_observation_ids": array(text, minItems=4, maxItems=4),
        "units": array(enum(RATE_UNITS), minItems=4, maxItems=4),
        "matrix": array(array(number, minItems=4, maxItems=4), minItems=4, maxItems=4)})
    owner_covariance = _obj({"physical_observation_ids": array(text, minItems=1, maxItems=4, uniqueItems=True),
        "units": array(enum(RATE_UNITS), minItems=1, maxItems=4),
        "matrix": array(array(number, minItems=1, maxItems=4), minItems=1, maxItems=4)})
    schema = _obj({"version": {"const": _INPUT_VERSION},
        "arms": _obj({name: nullable(reference("Arm")) for name in _ROLES}),
        "relationships": reference("Relationships"),
        "covariance": nullable({"oneOf": [reference("RoleCovariance"), reference("OwnerCovariance")]}),
        "variance_status": enum(("known", "estimated", "unknown")),
        "model_kind": enum(("none", "known_joint_normal_source_means"))})
    schema["$defs"] = {"Arm": arm, "Relationships": relationships,
                       "RoleCovariance": role_covariance, "OwnerCovariance": owner_covariance}
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return schema


def controlled_response_owner_arguments_schema():
    """Return the detached closed PARSED-input type, not a model tool schema."""
    return deepcopy(_schema())


