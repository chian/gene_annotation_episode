"""Pure typed-return checks with symbolic data, not native or receipt evidence."""
from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
import pytest

from gene_annotation_episode.chromatin_interaction_contracts import chromatin_record_schema
from gene_annotation_episode.chromatin_interaction_return_views import (
    FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE,
    chromatin_fact_sources, requested_chromatin_sources,
    select_chromatin_return_facts, validate_chromatin_fact_values,
)
from gene_annotation_episode.communication import (
    form_with_facts, interpretation_schema, validate_closed_schema, validate_form,
)


EXAMPLES = Path(__file__).resolve().parents[1] / (
    "verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json")


@pytest.fixture(scope="module")
def records():
    return json.loads(EXAMPLES.read_bytes())["records"]


def form(*sources):
    definitions = chromatin_fact_sources()
    properties = {"requested_" + str(index): definitions[source]["report_schema"]
                  for index, source in enumerate(sources)}
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def identity(digit, format):
    sha = digit * 64
    return {"artifact_ref": "artifact_" + sha, "sha256": sha, "size_bytes": 23, "format": format}


@pytest.fixture
def saved():
    return {"sheet": identity("1", "chromatin_interaction_sheet_v1"),
        "tables": [identity("2", "chromatin_contact_tables_v1:bins"),
                   identity("3", "chromatin_contact_tables_v1:contacts")]}


@pytest.mark.parametrize("kind", ["contact_pairs", "distance_expectations", "insulation_windows",
                                   "domains", "population_metrics"])
def test_each_projection_variant_keeps_exact_requested_rows(records, kind):
    candidates = [row["record"] for row in records if row["schema_definition"] == "RequestedProjection"
                  and row["record"]["kind"] == kind]
    assert candidates, kind
    for original in candidates:
        before = deepcopy(original)
        actual = validate_chromatin_fact_values(PROJECTION_SOURCE, [original])
        assert actual == [before]
        assert original == before and actual[0] is not original
        Draft202012Validator(chromatin_fact_sources()[PROJECTION_SOURCE]["report_schema"]).validate(actual)


def test_parent_form_embeds_all_three_independent_local_schemas(saved, records):
    schema = validate_closed_schema(form(*FACT_SOURCES))
    projection = next(row["record"] for row in records if row["schema_definition"] == "RequestedProjection")
    failure = next(row["record"] for row in records if row["schema_definition"] == "Failure")
    actual = {"requested_0": [projection], "requested_1": [saved], "requested_2": [failure]}
    Draft202012Validator(schema).validate(actual)
    assert requested_chromatin_sources(schema) == FACT_SOURCES


def test_actual_form_builder_requires_requested_saved_artifact_references(saved):
    schema = validate_closed_schema(form(SAVED_SOURCE))
    facts = select_chromatin_return_facts({SAVED_SOURCE: [saved]}, schema=schema)
    actual = form_with_facts({}, schema, facts)
    allowed = {saved["sheet"]["artifact_ref"], *(row["artifact_ref"] for row in saved["tables"])}
    seen = []

    def resolve(reference, namespace):
        seen.append((reference, namespace))
        return reference in allowed and namespace == "artifact"

    assert validate_form(actual, schema, resolve) == actual
    assert set(seen) == {(reference, "artifact") for reference in allowed}
    assert interpretation_schema(schema)["properties"] == {}


def test_only_requested_sources_are_selected_and_full_order_is_kept(records, saved):
    projections = [row["record"] for row in records if row["schema_definition"] == "RequestedProjection"]
    groups = {PROJECTION_SOURCE: projections, SAVED_SOURCE: [saved], FAILURE_SOURCE: []}
    actual = select_chromatin_return_facts(groups, schema=form(PROJECTION_SOURCE))
    assert actual == {PROJECTION_SOURCE: projections}
    assert actual[PROJECTION_SOURCE] is not projections
    assert all(a is not b for a, b in zip(actual[PROJECTION_SOURCE], projections))


def test_saved_return_preserves_repeated_bytes_without_granting_unrequested_bundle(saved):
    saved["tables"].append(deepcopy(saved["tables"][0]))
    actual = select_chromatin_return_facts({SAVED_SOURCE: [saved]}, schema=form(SAVED_SOURCE))
    assert actual == {SAVED_SOURCE: [saved]}
    actual[SAVED_SOURCE][0]["tables"].clear()
    assert len(saved["tables"]) == 3
    assert select_chromatin_return_facts({SAVED_SOURCE: [saved]}, schema=form()) == {}


@pytest.mark.parametrize("target,field,value", [
    ("sheet", "format", "application/json"),
    ("sheet", "artifact_ref", "artifact_" + "4" * 64),
    ("table", "format", "chromatin_interaction_sheet_v1"),
    ("table", "artifact_ref", "artifact_" + "4" * 64),
    ("table", "size_bytes", True),
])
def test_saved_identity_and_format_relationships_reject(saved, target, field, value):
    file = saved["sheet"] if target == "sheet" else saved["tables"][0]
    file[field] = value
    with pytest.raises(ValueError):
        validate_chromatin_fact_values(SAVED_SOURCE, [saved])


def test_saved_source_schema_has_distinct_sheet_and_table_formats(saved):
    schema = chromatin_fact_sources()[SAVED_SOURCE]["report_schema"]
    Draft202012Validator(schema).validate([saved])
    saved["tables"][0]["format"] = "chromatin_interaction_sheet_v1"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate([saved])
    # Export customization cannot mutate the shared C1 record definitions.
    identity_schema = chromatin_record_schema("NativeFileIdentity")["$defs"]["NativeFileIdentity"]
    assert "const" not in identity_schema["properties"]["format"]
    assert "enum" not in identity_schema["properties"]["format"]


@pytest.mark.parametrize("source,value", [
    ("chromatin_interaction_unknown", []), (None, []), (SAVED_SOURCE, {}), (PROJECTION_SOURCE, None),
])
def test_unknown_sources_and_nonarrays_reject(source, value):
    with pytest.raises(ValueError):
        validate_chromatin_fact_values(source, value)


def test_unknown_family_source_and_missing_requested_data_reject():
    schema = form(PROJECTION_SOURCE)
    schema["properties"]["requested_0"]["x-source"] = "chromatin_interaction_unknown"
    with pytest.raises(ValueError, match="unknown_source"):
        requested_chromatin_sources(schema)
    with pytest.raises(ValueError, match="requested_source_unavailable"):
        select_chromatin_return_facts({}, schema=form(PROJECTION_SOURCE))


def test_distinct_parent_field_names_can_request_same_source_once():
    schema = form(FAILURE_SOURCE, PROJECTION_SOURCE, FAILURE_SOURCE)
    schema["properties"]["unrelated"] = {"type": "boolean", "x-source": "execution_completed"}
    assert requested_chromatin_sources(schema) == (FAILURE_SOURCE, PROJECTION_SOURCE)


def test_schema_exports_do_not_share_mutable_definitions():
    first = chromatin_fact_sources()
    first[SAVED_SOURCE]["report_schema"]["$defs"]["NativeFileIdentity"]["properties"].clear()
    second = chromatin_fact_sources()
    assert second[SAVED_SOURCE]["report_schema"]["$defs"]["NativeFileIdentity"]["properties"]


@pytest.mark.parametrize("change", ["unrequested_field", "foreign_row", "foreign_measurement", "wrong_count"])
def test_projection_relationships_reject_unrequested_or_misassociated_facts(records, change):
    projection = deepcopy(next(row["record"] for row in records
        if row["schema_definition"] == "RequestedProjection" and row["record"]["kind"] == "contact_pairs"))
    row = projection["rows"][0]
    if change == "unrequested_field":
        projection["requested_fields"].remove("raw_contact")
    elif change == "foreign_row":
        row["population_key"] = "other"
    elif change == "foreign_measurement":
        row["fields"]["raw_contact"]["population_key"] = "other"
    else:
        projection["page"]["returned_count"] += 1
    with pytest.raises(ValueError):
        validate_chromatin_fact_values(PROJECTION_SOURCE, [projection])
