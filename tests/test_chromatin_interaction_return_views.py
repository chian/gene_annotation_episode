"""Pure typed-return checks with symbolic data, not native or receipt evidence."""

from jsonschema import Draft202012Validator, ValidationError
import pytest

from gene_annotation_episode.chromatin_interaction_contracts import chromatin_record_schema
from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_return_views import SAVED_SOURCE, chromatin_fact_sources, select_chromatin_return_facts
from gene_annotation_episode.episodic_workflow.root.communication import (
    ReportBoundaryError, form_with_facts, interpretation_schema, validate_closed_schema, validate_form,
)


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
    with pytest.raises(ReportBoundaryError, match="reference is unavailable"):
        validate_form(actual, schema, lambda reference, namespace: reference != saved["tables"][0]["artifact_ref"])


def test_parent_boundary_rejects_rewritten_registered_schema():
    schema = form(SAVED_SOURCE)
    schema["properties"]["requested_0"]["$defs"]["NativeFileIdentity"]["properties"]["artifact_ref"].pop("format")
    with pytest.raises(ReportBoundaryError, match="schema must match"):
        validate_closed_schema(schema)


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


