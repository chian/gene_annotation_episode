"""Representation checks only; these do not assess biological conclusions."""
import json
import math
import pytest

from gene_annotation_episode import runtime
from gene_annotation_episode.boundary_validation import parse_json_object
from gene_annotation_episode.communication import (
    ReportBoundaryError, validate_closed_schema, validate_form,
    interpretation_schema, form_with_facts, generation_schema, reference_resolver,
)


def form(fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def test_legacy_child_return_fields_gain_closed_outer_form_automatically():
    compact = {"properties": {"score": {"type": "number", "x-source": "credit"}}}
    compiled = runtime._compile_form(json.dumps(compact))
    assert compiled == form(compact['properties'])
    assert compact == {"properties": {"score": {"type": "number", "x-source": "credit"}}}


def test_freeform_and_schema_escape_rejected_recursively():
    for fields in ({"findings": {"type": "string"}},
                   {"nested": {"type": "array", "items": {"type": "object"}}},
                   {"findings": {"type": "string", "pattern": ".*"}}):
        with pytest.raises(ReportBoundaryError):
            validate_closed_schema(form(fields))


def test_live_reference_namespace_not_merely_identifier_syntax():
    schema = form({"target": {"type": "string", "format": "reference", "x-reference-namespace": "subject"}})
    resolve = reference_resolver({"subject": {"input_1"}, "observation": {"observation_1"}})
    assert validate_form({"target": "input_1"}, schema, resolve)
    for unknown in ("input_2", "observation_1", "a_plausible_identifier"):
        with pytest.raises(ReportBoundaryError):
            validate_form({"target": unknown}, schema, resolve)


def test_facts_inserted_from_state_not_child_values():
    schema = form({"score": {"type": "number", "x-source": "credit"},
                   "trend": {"type": "string", "enum": ["agreement", "conflict", "undetermined"]}})
    assert set(interpretation_schema(schema)["properties"]) == {"trend"}
    payload = form_with_facts({"trend": "conflict"}, schema, {"credit": 1.25})
    assert validate_form(payload, schema) == {"trend": "conflict", "score": 1.25}
    with pytest.raises(ReportBoundaryError):
        form_with_facts({"trend": "conflict", "score": 99}, schema, {"credit": 1.25})
    assert "x-source" not in generation_schema(schema)["properties"]["score"]


def test_nonfinite_and_prose_do_not_cross_form():
    schema = form({"score": {"type": "number"}, "trend": {"type": "string", "enum": ["agreement"]}})
    for payload in ({"score": math.nan, "trend": "agreement"},
                    {"score": 1, "trend": "Here are instructions for the parent"}):
        with pytest.raises(ReportBoundaryError):
            validate_form(payload, schema)


def test_model_json_rejects_duplicate_keys_nonobjects_and_nonfinite():
    for value in ('{"x":1,"x":2}', '[1]', '{"x":NaN}', '{"x":1e999}'):
        with pytest.raises(ValueError):
            parse_json_object(value)
    assert parse_json_object('{"x":null}') == {"x": None}


def test_nested_fact_binding_is_explicitly_not_an_available_contract():
    schema = form({"nested": form({"score": {"type": "number", "x-source": "credit"}})})
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(schema)
