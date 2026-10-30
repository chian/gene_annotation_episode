"""The exact recorded Enrichr contracts cross the shared form grammar."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.communication import (
    ReportBoundaryError, form_with_facts, interpretation_schema,
    validate_closed_schema, validate_form,
)
from gene_annotation_episode.enrichr_contracts import (
    calculate_enrichr_components, enrichr_fact_sources, parse_enrichr_response,
    project_enrichr_return,
)


SOURCE = "source_" + "a" * 24
SOURCES = ("execution_enrichr_tables", "execution_enrichr_rows")


def recorded():
    request = {"version": "enrichr_request_v1", "protocol_profile": "standard_enrichr_v1",
        "library": "Literal library / α", "genes": ["X"],
        "identifier_policy": "literal_no_mapping", "species_context": None,
        "description": "", "background": {"policy": "service_native", "genes": None},
        "native_statistic_profile": "documented_odds_v1"}
    body = json.dumps({request["library"]: [[1, "Literal term / α", 0, 2, 3, ["X", "X"], 0.5, 0, 0]]}).encode()
    sheet = parse_enrichr_response(body, request=request, response_complete=True)
    components = calculate_enrichr_components(sheet,
        selector={"version": "enrichr_selector_v1", "offset": 0, "limit": 10})
    return project_enrichr_return(components, source_ref=SOURCE)


def form_schema(source):
    return {"type": "object", "properties": {
        "values": deepcopy(enrichr_fact_sources()[source]["report_schema"])},
        "required": ["values"], "additionalProperties": False}


@pytest.mark.parametrize("source", SOURCES)
def test_exact_native_contract_preserves_literal_data_and_checks_source(source):
    schema = form_schema(source)
    assert validate_closed_schema(schema) == schema
    facts = recorded()
    payload = form_with_facts({}, schema, facts)
    assert interpretation_schema(schema)["properties"] == {}
    calls = []
    def resolver(value, namespace):
        calls.append((value, namespace))
        return value == SOURCE and namespace == "source"
    assert validate_form(payload, schema, resolver) == {"values": facts[source]}
    assert calls and set(calls) == {(SOURCE, "source")}
    assert "Literal" in json.dumps(payload, ensure_ascii=False)
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form(payload, schema, lambda *_: False)
    assert caught.value.diagnostic["code"] == "unknown_reference"


@pytest.mark.parametrize("source", SOURCES)
@pytest.mark.parametrize("change", ("description", "source_format", "required"))
def test_modified_native_schema_cannot_admit_uncontrolled_strings(source, change):
    schema = form_schema(source)
    node = schema["properties"]["values"]
    if change == "description":
        node["description"] = "Unregistered altered contract"
    elif change == "source_format":
        node["items"]["properties"]["source_ref"]["format"] = "identifier"
    else:
        node["items"]["required"].remove("source_ref")
    with pytest.raises(ReportBoundaryError) as caught:
        validate_closed_schema(schema)
    assert caught.value.diagnostic["code"] == "invalid_schema"


@pytest.mark.parametrize("source", SOURCES)
def test_recorded_binding_must_occupy_a_whole_top_level_field(source):
    inner = form_schema(source)
    schema = {"type": "object", "properties": {"nested": inner},
        "required": ["nested"], "additionalProperties": False}
    with pytest.raises(ReportBoundaryError) as caught:
        validate_closed_schema(schema)
    assert caught.value.diagnostic["code"] == "invalid_schema"


def test_registration_does_not_relax_generic_string_contracts():
    schema = {"type": "object", "properties": {"text": {"type": "string"}},
        "required": ["text"], "additionalProperties": False}
    with pytest.raises(ReportBoundaryError) as caught:
        validate_closed_schema(schema)
    assert caught.value.diagnostic["code"] == "unrestricted_string"
