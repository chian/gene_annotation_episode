from copy import deepcopy
from gene_annotation_episode.domain import obj

ROLES = ("numerator", "denominator")

LITERAL_FIELDS = ("subject", "construct", "preparation", "condition", "endpoint", "measurement_identity")
QUALIFICATIONS = ("reported_point", "source_qualified_approximate", "unknown", "conflicting")
RELATIONS = ("same", "different", "unknown", "conflicting")
PAIR_RELATIONS = ("supported", "unknown", "conflicting")
CHANGE_STATUSES = ("described", "partial", "unknown", "conflicting")
COMPARISON_FIELDS = ("endpoint_relation", "preparation_relation", "pair_relationship", "other_changes_status")
COMPARISON_VALUES = (RELATIONS, RELATIONS, PAIR_RELATIONS, CHANGE_STATUSES)

COMPONENTS = ("numerator_time", "denominator_time", "completion_time_ratio", "inverse_completion_time_ratio")
REASONS = ("source_measurement_unavailable", "source_time_unit_unreported", "unsupported_source_time_unit",
    "source_time_unit_conflicting", "nonpositive_physical_time", "endpoint_relation_unknown", "endpoint_relation_conflicting", "different_endpoints",
    "preparation_relation_unknown", "preparation_relation_conflicting", "pair_relationship_unknown",
    "pair_relationship_conflicting", "source_meaning_unavailable", "qualification_unknown", "qualification_conflicting",
    "reused_source_observation", "numerical_model_range")
CONDITIONS = ("strictly_positive_physical_completion_time", "source_endpoint_and_pair_interpretations",
    "reported_operand_cartesian_enclosure", "preparation_protocol_comparison_only")

NAMESPACE = "literature_completion_time_cells"

def completion_time_cells_schema():
    def ref(namespace):
        return {"type": "string", "format": "reference", "x-reference-namespace": namespace}
    witness = obj({"source_ref": ref("source"), "artifact_ref": ref("artifact"),
        "representation": {"type": "string", "enum": ["original", "text"]},
        "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1},
        "quote": {"type": "string", "minLength": 1}})
    meaning = obj({"status": {"type": "string", "enum": ["selected", "not_selected", "withheld_time_operand"]},
        "witness": {"anyOf": [witness, {"type": "null"}]}})
    def interpretation(values):
        return obj({"value": {"type": "string", "enum": list(values)},
            "support": {"type": "array", "items": deepcopy(meaning)}})
    nullable_number = {"type": ["number", "null"]}
    exact_number = {"anyOf": [obj({"numerator": {"type": "string", "pattern": "^-?[0-9]+$"},
        "denominator": {"type": "string", "pattern": "^[1-9][0-9]*$"}}), {"type": "null"}]}
    exact_domain = {"anyOf": [obj({"lower": deepcopy(exact_number), "upper": deepcopy(exact_number),
        "lower_inclusive": {"type": "boolean"}, "upper_inclusive": {"type": "boolean"}}), {"type": "null"}]}
    domain = obj({"kind": {"type": "string", "enum": ["point", "finite_interval", "lower_bounded", "upper_bounded", "unbounded", "unavailable"]},
        "lower": deepcopy(nullable_number), "upper": deepcopy(nullable_number),
        "lower_inclusive": {"type": "boolean"}, "upper_inclusive": {"type": "boolean"},
        "projection": {"type": "string", "enum": ["none", "exact", "outward"]},
        "basis": {"type": "string", "enum": ["reported_operand_algebra", "reported_time_operand"]},
        "conditioning": {"type": "string", "const": "strictly_positive_physical_completion_time"},
        "failure": {"type": ["string", "null"], "enum": [*REASONS, None]}})
    reading = {"anyOf": [obj({"number": deepcopy(witness), "raw_unit": {"type": ["string", "null"]},
        "bound": {"type": "string", "enum": ["none", "lt", "le", "gt", "ge"]},
        "canonical_minutes": {"type": ["string", "null"]}}), {"type": "null"}]}
    operand = obj({"role": {"type": "string", "enum": list(ROLES)},
        "meanings": obj({field: deepcopy(meaning) for field in LITERAL_FIELDS}),
        "qualification": interpretation(QUALIFICATIONS), "reading": reading})
    return {"type": "array", "items": obj({"sheet_ref": ref("source"), "evidence_source_ref": ref("source"),
        "component": {"type": "string", "enum": list(COMPONENTS)}, "value": deepcopy(nullable_number),
        "unit": {"type": ["string", "null"], "enum": ["min", "dimensionless", None]},
        "status": {"type": "string", "enum": ["point", "bounded", "unavailable"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [*REASONS, None]},
        "origin": {"type": "string", "enum": ["reported", "synthetic", "derived"]}, "approximate": {"type": "boolean"},
        "conditional_on": {"type": "array", "uniqueItems": True, "items": {"type": "string", "enum": list(CONDITIONS)}},
        "reported_domain": domain, "exact_domain": exact_domain,
        "evaluation_scope": {"type": "string", "const": "source_preparation_completion_time"},
        "experiment": deepcopy(meaning), "intended_change": deepcopy(meaning),
        "other_changes": {"type": "array", "items": deepcopy(meaning)},
        "comparison": obj({field: interpretation(values) for field, values in zip(COMPARISON_FIELDS, COMPARISON_VALUES)}),
        "operands": {"type": "array", "minItems": 1, "maxItems": 2, "items": operand}}), "x-source": NAMESPACE}

