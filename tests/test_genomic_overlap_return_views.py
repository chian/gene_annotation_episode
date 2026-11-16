"""Typed supplied facts only; these tests do not establish episode authority."""

import pytest

from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError, validate_closed_schema
from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_return_views import FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE, genomic_overlap_fact_sources, validate_genomic_overlap_fact_values


def form_schema(*sources):
    descriptors = genomic_overlap_fact_sources()
    properties = {"field_" + str(index): descriptors[source]["report_schema"]
                  for index, source in enumerate(sources)}
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


@pytest.mark.parametrize("source", FACT_SOURCES)
def test_empty_arrays_mean_no_returned_values_not_a_complete_empty_projection(source):
    assert validate_genomic_overlap_fact_values(source, []) == []
    with pytest.raises(ValueError):
        validate_genomic_overlap_fact_values(source, [{}])


@pytest.mark.parametrize("mutation", ["unknown_source", "changed_definition", "changed_items", "extra_keyword"])
def test_registered_source_cannot_open_a_free_form_schema(mutation):
    schema = form_schema(PROJECTION_SOURCE)
    node = schema["properties"]["field_0"]
    if mutation == "unknown_source":
        node["x-source"] = "genomic_overlap_invented"
    elif mutation == "changed_definition":
        node["$defs"]["Projection"]["additionalProperties"] = True
    elif mutation == "changed_items":
        node["items"] = {}
    else:
        node["description"] = "an unregistered replacement"
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(schema)


def test_registered_source_cannot_be_nested_to_bypass_the_form_grammar():
    nested = form_schema(PROJECTION_SOURCE)
    schema = {"type": "object", "additionalProperties": False,
        "properties": {"nested": nested}, "required": ["nested"]}
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(schema)


@pytest.mark.parametrize("value", [{}, (), "values", None])
def test_fact_collections_are_explicit_arrays(value):
    with pytest.raises(ValueError, match="array_required"):
        validate_genomic_overlap_fact_values(PROJECTION_SOURCE, value)


def test_source_descriptors_are_detached():
    original = genomic_overlap_fact_sources()
    changed = genomic_overlap_fact_sources()
    changed[SAVED_SOURCE]["report_schema"]["$defs"]["NativeFileIdentity"]["properties"].clear()
    assert genomic_overlap_fact_sources() == original
