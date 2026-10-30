"""Typed supplied facts only; these tests do not establish episode authority."""
from copy import deepcopy
import hashlib
import json

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import (
    ReportBoundaryError, form_with_facts, interpretation_schema,
    validate_closed_schema, validate_form,
)
from gene_annotation_episode.genomic_overlap_return_views import (
    FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE,
    genomic_overlap_fact_sources, requested_genomic_overlap_sources,
    select_genomic_overlap_return_facts, validate_genomic_overlap_fact_values,
)
from test_genomic_overlap_result_views import worked, _project, _failure


def form_schema(*sources):
    descriptors = genomic_overlap_fact_sources()
    properties = {"field_" + str(index): descriptors[source]["report_schema"]
                  for index, source in enumerate(sources)}
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


@pytest.fixture
def groups(worked):
    raw = json.dumps(worked["sheet"], sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode()
    sha = hashlib.sha256(raw).hexdigest()
    saved = {"artifact_ref": "artifact_" + sha, "sha256": sha,
        "size_bytes": len(raw), "format": "genomic_region_overlap_sheet_v1"}
    return {PROJECTION_SOURCE: [_project(worked)], SAVED_SOURCE: [saved],
            FAILURE_SOURCE: [_failure()]}


@pytest.mark.parametrize("source", FACT_SOURCES)
def test_exact_registered_source_embeds_in_an_actual_closed_form(groups, source):
    schema = form_schema(source)
    assert validate_closed_schema(schema) == schema
    facts = select_genomic_overlap_return_facts(groups, schema=schema)
    form = form_with_facts({}, schema, facts)
    seen = []
    def resolve(reference, namespace):
        seen.append((reference, namespace))
        return reference == groups[SAVED_SOURCE][0]["artifact_ref"] and namespace == "artifact"
    assert validate_form(form, schema, resolve) == {"field_0": groups[source]}
    assert interpretation_schema(schema)["properties"] == {}
    assert seen == ([(groups[SAVED_SOURCE][0]["artifact_ref"], "artifact")] if source == SAVED_SOURCE else [])


def test_nested_self_contained_schemas_resolve_their_own_definitions(groups):
    schema = form_schema(*FACT_SOURCES)
    form = form_with_facts({}, schema, select_genomic_overlap_return_facts(groups, schema=schema))
    assert validate_form(form, schema, lambda *_: True) == form
    Draft202012Validator(schema).validate(form)
    for node in schema["properties"].values():
        assert "Sheet" not in node["$defs"] and "Components" not in node["$defs"]


def test_requested_only_selection_keeps_distinct_results_and_detaches(groups):
    first = deepcopy(groups[PROJECTION_SOURCE][0])
    second = deepcopy(first)
    second["parameters"]["minimum_overlap_bp"] = 4
    groups[PROJECTION_SOURCE] = [first, second]
    groups[SAVED_SOURCE] = "unrequested value is not inspected"
    schema = form_schema(PROJECTION_SOURCE, PROJECTION_SOURCE)
    assert requested_genomic_overlap_sources(schema) == (PROJECTION_SOURCE,)
    selected = select_genomic_overlap_return_facts(groups, schema=schema)
    assert set(selected) == {PROJECTION_SOURCE}
    assert selected[PROJECTION_SOURCE] == [first, second]
    assert selected[PROJECTION_SOURCE][0]["pair_rows"][0]["measurements"]["unfiltered.jaccard_bp"]["value"] == 1 / 3
    selected[PROJECTION_SOURCE][1]["parameters"]["minimum_overlap_bp"] = 9
    assert second["parameters"]["minimum_overlap_bp"] == 4


def test_no_source_is_selected_merely_because_a_group_exists(groups):
    assert select_genomic_overlap_return_facts(groups, schema=form_schema()) == {}
    with pytest.raises(ValueError, match="requested_source_unavailable"):
        select_genomic_overlap_return_facts({}, schema=form_schema(PROJECTION_SOURCE))


@pytest.mark.parametrize("source", FACT_SOURCES)
def test_empty_arrays_mean_no_returned_values_not_a_complete_empty_projection(source):
    assert validate_genomic_overlap_fact_values(source, []) == []
    with pytest.raises(ValueError):
        validate_genomic_overlap_fact_values(source, [{}])


@pytest.mark.parametrize("mutation", ["extra", "nonfinite", "bool_integer", "wrong_extent"])
def test_projection_records_remain_strict(groups, mutation):
    rows = groups[PROJECTION_SOURCE]
    if mutation == "extra":
        rows[0]["freehand_finding"] = "invented"
    elif mutation == "nonfinite":
        rows[0]["pair_rows"][0]["measurements"]["unfiltered.jaccard_bp"]["value"] = float("nan")
    elif mutation == "bool_integer":
        rows[0]["page"]["offset"] = True
    else:
        rows[0]["result_extent"] = "successful_annotation"
    with pytest.raises(ValueError):
        validate_genomic_overlap_fact_values(PROJECTION_SOURCE, rows)
    with pytest.raises(ReportBoundaryError):
        validate_form({"field_0": rows}, form_schema(PROJECTION_SOURCE), lambda *_: True)


@pytest.mark.parametrize("mutation", ["format", "artifact", "size", "extra"])
def test_saved_operand_shape_does_not_accept_an_arbitrary_artifact(groups, mutation):
    row = groups[SAVED_SOURCE][0]
    if mutation == "format":
        row["format"] = "genomic_region_overlap_components_v1"
    elif mutation == "artifact":
        row["artifact_ref"] = "artifact_" + "0" * 64
    elif mutation == "size":
        row["size_bytes"] = True
    else:
        row["permission"] = "all_child_files"
    with pytest.raises(ValueError):
        validate_genomic_overlap_fact_values(SAVED_SOURCE, [row])
    with pytest.raises(ReportBoundaryError):
        validate_form({"field_0": [row]}, form_schema(SAVED_SOURCE), lambda *_: True)


def test_saved_operand_still_requires_boundary_reference_resolution(groups):
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form({"field_0": groups[SAVED_SOURCE]}, form_schema(SAVED_SOURCE), lambda *_: False)
    assert caught.value.diagnostic["code"] == "unknown_reference"


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
