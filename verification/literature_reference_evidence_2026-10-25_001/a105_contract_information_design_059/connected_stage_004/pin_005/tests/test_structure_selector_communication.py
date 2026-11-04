"""Structure selector representation at typed boundaries, using synthetic values."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import (
    FORMATS, REFERENCE_FORMATS, ReportBoundaryError, form_with_facts,
    generation_schema, interpretation_schema, validate_closed_schema, validate_form,
)


FORMATS_UNDER_TEST = (
    "structure_identifier", "structure_residue_number", "structure_insertion_code",
)


def form(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
        "additionalProperties": False}


def selector_schema():
    return form({
        "auth_chain": {"type": "string", "format": "structure_identifier"},
        "auth_seq_id": {"type": "string", "format": "structure_residue_number"},
        "comp_id": {"type": "string", "format": "structure_identifier"},
        "insertion_code": {"type": "string", "format": "structure_insertion_code"},
        "alt_id": {"type": "string", "format": "structure_identifier"},
        "atom_names": {"type": "array", "minItems": 1, "uniqueItems": True,
            "items": {"type": "string", "format": "structure_identifier"}},
    })


def selector():
    return {"auth_chain": "A_1", "auth_seq_id": "-0012", "comp_id": "LIG",
        "insertion_code": "", "alt_id": ".", "atom_names": ["O5'", 'C1*']}


def no_reference_resolution(*_args):
    raise AssertionError("Structure selectors are values, not custody references")


@pytest.mark.parametrize("kind", FORMATS_UNDER_TEST)
@pytest.mark.parametrize("nullable", [False, True])
def test_selector_semantic_formats_compile_direct_and_nested_nullable(kind, nullable):
    node = {"type": ["string", "null"] if nullable else "string", "format": kind}
    schema = form({"direct": node, "nested": {"type": "array", "items": form({"value": node})}})
    assert validate_closed_schema(schema) == schema
    assert kind in FORMATS and kind not in REFERENCE_FORMATS
    value = "-0012" if kind == "structure_residue_number" else "A_1"
    payload = {"direct": value, "nested": [{"value": value}]}
    assert validate_form(payload, schema, no_reference_resolution) == payload
    nulls = {"direct": None, "nested": [{"value": None}]}
    if nullable:
        assert validate_form(nulls, schema, no_reference_resolution) == nulls
    else:
        with pytest.raises(ReportBoundaryError) as error:
            validate_form(nulls, schema, no_reference_resolution)
        assert error.value.diagnostic["code"] == "type"


@pytest.mark.parametrize("kind,value", [
    ("structure_identifier", "A"), ("structure_identifier", "auth-chain_2"),
    ("structure_identifier", "O5'"), ("structure_identifier", "."),
    ("structure_identifier", "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"),
    ("structure_residue_number", "0"), ("structure_residue_number", "-0"),
    ("structure_residue_number", "0012"), ("structure_residue_number", "-0012"),
    ("structure_residue_number", "123456789012345678901234567890"),
    ("structure_insertion_code", ""), ("structure_insertion_code", "A"),
    ("structure_insertion_code", "AB_2"), ("structure_insertion_code", "!~"),
])
def test_exact_selector_spelling_survives_without_normalization(kind, value):
    schema = form({"value": {"type": "string", "format": kind}})
    assert validate_form({"value": value}, schema, no_reference_resolution) == {"value": value}


INVALID_TOKENS = [" ", "A B", " A", "A ", "A\n", "A\r", "A\t", "\x00", "A\x1f", "A\x7f",
    "Å", "A\u00a0B", "A\u200bB", "A\u2028B"]
INVALID_VALUES = [
    *((kind, value) for kind in ("structure_identifier", "structure_insertion_code")
        for value in INVALID_TOKENS),
    ("structure_identifier", ""),
    *(("structure_residue_number", value) for value in [
        "", "-", "+1", "1.0", "1e2", "1A", "residue_1", "1 2", " 1", "1 ",
        "1\n", "1\r", "1\t", "1\x00", "1\x7f", "١", "１", "−1"]),
]


@pytest.mark.parametrize("kind,value", INVALID_VALUES)
@pytest.mark.parametrize("nested", [False, True])
def test_invalid_selectors_fail_in_direct_and_nested_nullable_fields(kind, value, nested):
    node = {"type": ["string", "null"], "format": kind}
    if nested:
        schema = form({"rows": {"type": "array", "items": form({"selector": node})}})
        payload, field = {"rows": [{"selector": value}]}, "report.rows[0].selector"
    else:
        schema, payload, field = form({"selector": node}), {"selector": value}, "report.selector"
    with pytest.raises(ReportBoundaryError) as error:
        validate_form(payload, schema, no_reference_resolution)
    assert error.value.diagnostic == {"category": "report_format", "code": "invalid_" + kind, "field": field}


@pytest.mark.parametrize("kind", FORMATS_UNDER_TEST)
@pytest.mark.parametrize("value", [1, 1.5, True, [], {}])
def test_selector_formats_remain_strings(kind, value):
    with pytest.raises(ReportBoundaryError) as error:
        validate_form({"selector": value}, form({"selector": {"type": "string", "format": kind}}))
    assert error.value.diagnostic["code"] == "type"


@pytest.mark.parametrize("kind", FORMATS_UNDER_TEST)
def test_selector_formats_do_not_allow_reference_namespaces(kind):
    with pytest.raises(ReportBoundaryError) as error:
        validate_closed_schema(form({"selector": {"type": "string", "format": kind,
            "x-reference-namespace": "source"}}))
    assert error.value.diagnostic["code"] == "invalid_schema"


@pytest.mark.parametrize("node", [
    {"type": "string"}, {"type": "string", "minLength": 1},
    {"type": "string", "pattern": "[!-~]+"},
    {"type": "string", "format": "arbitrary_token"},
    {"type": "string", "format": "structure_identifier", "minLength": 1},
    {"type": "string", "format": "structure_identifier", "pattern": "[!-~]+"},
    {"type": "integer", "format": "structure_residue_number"},
])
def test_schema_escape_hatches_remain_closed(node):
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(form({"nested": {"type": "array", "items": form({"selector": node})}}))


def test_generation_keeps_panel_shapes_and_host_checks_selector_values():
    endpoint = selector_schema()
    endpoint["properties"]["alt_id"]["type"] = ["string", "null"]
    schema = form({"panels": {"type": "array", "minItems": 1, "maxItems": 2,
        "items": form({"endpoint": endpoint,
            "positive_max_A": {"type": "number", "minimum": 0},
            "incompatible_min_A": {"type": ["number", "null"], "minimum": 0}})}})
    original = deepcopy(schema)
    transport = generation_schema(schema)
    panel = transport["properties"]["panels"]
    assert panel["minItems"] == 1 and panel["maxItems"] == 2
    row = panel["items"]
    assert row["additionalProperties"] is False
    assert set(row["required"]) == {"endpoint", "positive_max_A", "incompatible_min_A"}
    fields = row["properties"]["endpoint"]["properties"]
    assert set(fields) == set(endpoint["properties"])
    assert fields["auth_seq_id"] == {"type": "string"}
    assert fields["alt_id"] == {"type": ["string", "null"]}
    assert fields["atom_names"] == {"type": "array", "minItems": 1, "items": {"type": "string"}}
    assert row["properties"]["positive_max_A"] == {"type": "number", "minimum": 0}
    assert row["properties"]["incompatible_min_A"]["type"] == ["number", "null"]
    payload = {"panels": [{"endpoint": selector(), "positive_max_A": 3.5, "incompatible_min_A": None}]}
    assert Draft202012Validator(transport).is_valid(payload)
    assert validate_form(payload, schema, no_reference_resolution) == payload
    payload["panels"][0]["endpoint"]["alt_id"] = None
    assert Draft202012Validator(transport).is_valid(payload)
    assert validate_form(payload, schema, no_reference_resolution) == payload
    payload["panels"][0]["endpoint"]["atom_names"][0] = "O5'\n"
    assert Draft202012Validator(transport).is_valid(payload)
    with pytest.raises(ReportBoundaryError) as error:
        validate_form(payload, schema, no_reference_resolution)
    assert error.value.diagnostic["field"] == "report.panels[0].endpoint.atom_names[0]"
    assert schema == original


def test_recorded_selector_panels_are_bound_from_facts_then_validated():
    schema = form({"selected": {"type": "string", "enum": ["conditional_geometry"]},
        "panels": {"type": "array", "items": selector_schema(), "x-source": "structure_panels"}})
    assert interpretation_schema(schema) == form({"selected": schema["properties"]["selected"]})
    facts = {"structure_panels": [selector()]}
    result = form_with_facts({"selected": "conditional_geometry"}, schema, facts)
    assert validate_form(result, schema, no_reference_resolution) == {
        "selected": "conditional_geometry", "panels": [selector()]}
    result["panels"][0]["atom_names"].append("C2")
    assert facts["structure_panels"] == [selector()]
    with pytest.raises(ReportBoundaryError) as error:
        form_with_facts({"selected": "conditional_geometry", "panels": []}, schema, facts)
    assert error.value.diagnostic["code"] == "interpretation_fields"
    facts["structure_panels"][0]["auth_seq_id"] = "1.0"
    result = form_with_facts({"selected": "conditional_geometry"}, schema, facts)
    with pytest.raises(ReportBoundaryError) as error:
        validate_form(result, schema, no_reference_resolution)
    assert error.value.diagnostic["code"] == "invalid_structure_residue_number"


@pytest.mark.parametrize("kind,value", [("structure_identifier", "A"),
    ("structure_residue_number", "-001"), ("structure_insertion_code", "")])
def test_nullable_recorded_selectors_preserve_unknown_and_present_spellings(kind, value):
    schema = form({"selector": {"type": ["string", "null"], "format": kind,
        "x-source": "recorded_selector"}})
    assert interpretation_schema(schema) == form({})
    assert generation_schema(schema) == form({"selector": {"type": ["string", "null"]}})
    for actual in (None, value):
        payload = form_with_facts({}, schema, {"recorded_selector": actual})
        assert validate_form(payload, schema, no_reference_resolution) == {"selector": actual}
