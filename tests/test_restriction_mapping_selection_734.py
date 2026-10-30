"""Bounded pure selection checks; genuine saved728 values are read-only inputs."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.communication import ReportBoundaryError
from gene_annotation_episode.restriction_mapping_contracts import restriction_canonical
from gene_annotation_episode.restriction_mapping_returns import (
    project_restriction_action_return, requested_restriction_projections,
    restriction_mapping_fact_sources,
)
from gene_annotation_episode.restriction_mapping_selection import restriction_selected_return_schema


pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")
SOURCE = "restriction_mapping_results"
GROUP = ["selection_policy", "sequence_ref", "namespace", "topology", "data_status",
    "coordinate_unit", "population_scope"]
ROW = ["enzyme_rows." + name for name in
    ("catalog_ordinal", "name", "search_state", "position_meaning")]
POSITION = ["enzyme_rows.positions." + name for name in
    ("position_ordinal", "native_position", "geometry_state", "recognition_association",
     "recognition_event_ordinal")]
EVENT = ["enzyme_rows.recognition_events." + name for name in
    ("match_call_ordinal", "match_ordinal", "native_start_1based", "orientation")]
SEGMENT = ["enzyme_rows.recognition_events.segments.start", "enzyme_rows.recognition_events.segments.end"]
ALL = GROUP + ["tool_name", "work_mode", "operation_status", "source_ref", "input_source_ref",
    "population.selected_enzyme_count", "population.attempted_enzyme_count",
    "population.returned_enzyme_count", "population.complete_empty_enzyme_count",
    "population.recognition_match_count", "issue_codes"] + ROW + [
    "enzyme_rows.native_search_positions_1based", "enzyme_rows.returned_position_count",
    "enzyme_rows.recognition_match_count", "enzyme_rows.recognition_motif", "enzyme_rows.issue_codes"
    ] + POSITION + ["enzyme_rows.positions.watson_boundary_0based",
    "enzyme_rows.positions.crick_boundary_0based", "enzyme_rows.positions.watson_canonical_boundary_0based",
    "enzyme_rows.positions.crick_canonical_boundary_0based"] + EVENT + SEGMENT + [
    "enzyme_rows.recognition_events.unwrapped_span_0based", "enzyme_rows.recognition_events.crosses_origin"]
SAVED = Path("verification/tool_graders_hmmer_map_verification_2026-10-28_529/check191_registry728/restriction728-saved/published.json")


def _selection(fields=None, *, policy="all_own_completed_results", reference=None):
    return {"version": "restriction_return_selection_v1", "policy": policy,
        "sequence_ref": reference, "fields": list(GROUP if fields is None else fields)}


def _base():
    return restriction_mapping_fact_sources()[SOURCE]["report_schema"]


def _wrapper(schema):
    return {"type": "object", "properties": {"selected": schema},
        "required": ["selected"], "additionalProperties": False}


def _saved_action():
    saved = json.loads((Path(__file__).resolve().parents[1] / SAVED).read_text())
    assert set(saved) == {"body", "catalog", "input_source", "mapping", "native",
        "sequence_binding", "source", "witness"}
    body, binding = saved["body"], saved["sequence_binding"]
    return {"decision_index": 0, "operation_ref": body["operation_ref"],
        "tool_name": body["tool_name"], "work_mode": body["work_mode"],
        "operation_status": body["status"], "sequence_ref": binding["sequence_ref"],
        "namespace": binding["namespace"], "input_source_ref": body["input_source_ref"],
        "source_ref": saved["source"]["id"],
        "native_artifact_ref": body["files"]["native"]["artifact_ref"],
        "mapping_artifact_ref": body["files"]["mapping"]["artifact_ref"],
        "mapping": saved["mapping"], "failure_code": body["failure_code"]}


@pytest.mark.parametrize("policy,reference", [
    ("all_own_completed_results", None), ("matching_sequence", "input:734+matching")],
    ids=["S734-01-all-own", "S734-02-matching"])
def test_all_explicit_leaves_equal_existing_literal_schema(policy, reference):
    expected = _base()
    props = expected["items"]["properties"]
    props["selection_policy"] = {"type": "string", "const": policy}
    if reference is not None:
        props["sequence_ref"]["const"] = reference
    actual = restriction_selected_return_schema(_selection(ALL, policy=policy, reference=reference))
    assert actual == expected
    assert requested_restriction_projections(_wrapper(actual))[SOURCE]["fields"] == expected
    assert "x-restriction-selection" not in restriction_canonical(actual)


def test_manual_nested_subset_equivalence_and_source_order():
    """S734-03: equivalent hand-selected723 literal form, not a new schema policy."""
    fields = GROUP + ROW + ["population.selected_enzyme_count", "enzyme_rows.native_search_positions_1based"]
    expected = _base()
    props = expected["items"]["properties"]
    keep = set(GROUP + ["population", "enzyme_rows"])
    expected["items"]["properties"] = props = {k: v for k, v in props.items() if k in keep}
    expected["items"]["required"] = list(props)
    props["selection_policy"] = {"type": "string", "const": "all_own_completed_results"}
    pop = props["population"]
    pop["properties"] = {"selected_enzyme_count": pop["properties"]["selected_enzyme_count"]}
    pop["required"] = ["selected_enzyme_count"]
    row = props["enzyme_rows"]["items"]
    keep_row = {"catalog_ordinal", "name", "search_state", "position_meaning", "native_search_positions_1based"}
    row["properties"] = {k: v for k, v in row["properties"].items() if k in keep_row}
    row["required"] = list(row["properties"])
    actual = restriction_selected_return_schema(_selection(list(reversed(fields))))
    assert actual == expected
    assert list(actual["items"]["properties"]) == list(props)
    assert actual["items"]["required"] == list(props)
    assert restriction_canonical(actual) == restriction_canonical(restriction_selected_return_schema(_selection(fields)))


def test_input_output_and_public_schema_are_detached():
    """S734-04: selector and separately returned schema retain no mutable aliases."""
    selection = _selection(ALL)
    before, base_before = deepcopy(selection), _base()
    first = restriction_selected_return_schema(selection)
    assert selection == before
    first["items"]["properties"]["population"]["properties"]["selected_enzyme_count"]["description"] = "changed copy"
    selection["fields"].clear()
    assert _base() == base_before
    assert restriction_selected_return_schema(before) != first


@pytest.mark.parametrize("missing", GROUP + ROW + POSITION + EVENT + SEGMENT,
    ids=lambda missing: "S734-05-missing-" + missing)
def test_existing_dependencies_reject_without_adding_fields(missing):
    selection = _selection([field for field in ALL if field != missing])
    before = deepcopy(selection)
    with pytest.raises(ReportBoundaryError) as error:
        restriction_selected_return_schema(selection)
    assert error.value.diagnostic["code"] == "restriction_projection_fields_required"
    assert selection == before


@pytest.mark.parametrize("path", ["", ".sequence_ref", "population.", "population..selected_enzyme_count",
    "population", "enzyme_rows", "enzyme_rows.positions", "enzyme_rows.recognition_events",
    "enzyme_rows.recognition_events.segments", "enzyme_rows.*", "enzyme_rows[0].name",
    "enzyme_rows[].name", "enzyme_rows.0.name", "unknown", "population.unknown"],
    ids=lambda path: "S734-06-invalid-path-" + repr(path))
def test_unknown_nonleaf_and_syntax_paths_reject(path):
    with pytest.raises(ReportBoundaryError) as error:
        restriction_selected_return_schema(_selection(GROUP + [path]))
    assert error.value.diagnostic["code"] == "restriction_selection_field_unknown"


@pytest.mark.parametrize("change", [
    {"version": "restriction_return_selection_v2"}, {"version": True}, {"version": None},
    {"policy": "automatic"}, {"policy": 1}, {"policy": None},
    {"sequence_ref": "not-null"}, {"sequence_ref": False}, {"sequence_ref": 0},
    {"policy": "matching_sequence", "sequence_ref": None},
    {"policy": "matching_sequence", "sequence_ref": ""},
    {"policy": "matching_sequence", "sequence_ref": True},
    {"fields": []}, {"fields": "sequence_ref"}, {"fields": ("sequence_ref",)},
    {"fields": [True]}, {"fields": [1]}, {"fields": [None]}, {"fields": [{}]},
    {"fields": GROUP + ["sequence_ref"]}, {"extra": 1}, {"type": "array"},
    {"fields": float("nan")}, {"sequence_ref": float("inf")}],
    ids=["S734-07-invalid-%02d" % index for index in range(24)])
def test_strict_selection_rejects_malformed_types_extra_keys_and_nonfinite(change):
    selection = _selection()
    selection.update(change)
    with pytest.raises(ReportBoundaryError) as error:
        restriction_selected_return_schema(selection)
    assert error.value.diagnostic["code"].startswith("restriction_")


@pytest.mark.parametrize("missing", ["version", "policy", "sequence_ref", "fields"],
    ids=lambda missing: "S734-08-required-" + missing)
def test_all_four_keys_are_required(missing):
    selection = _selection()
    del selection[missing]
    with pytest.raises(ReportBoundaryError) as error:
        restriction_selected_return_schema(selection)
    assert error.value.diagnostic["code"] == "restriction_selection_keys_required"


@pytest.mark.parametrize("value", [None, [], True, 1, "selection"],
    ids=["S734-09-null", "S734-09-list", "S734-09-bool", "S734-09-int", "S734-09-string"])
def test_nonobject_selection_rejects(value):
    with pytest.raises(ReportBoundaryError):
        restriction_selected_return_schema(value)


def test_cyclic_selection_rejects_as_finite_json():
    """S734-10: cycles fail without traversing or retaining the schema tree."""
    selection = _selection()
    selection["fields"].append(selection)
    with pytest.raises(ReportBoundaryError) as error:
        restriction_selected_return_schema(selection)
    assert error.value.diagnostic["code"] == "restriction_selection_finite_json_required"


def test_actual_saved_values_and_measured_zero_survive_both_selected_views():
    """S734-11: copy original728 values; no native or719 calculations run."""
    action = _saved_action()
    original = deepcopy(action)
    for policy, reference in [("all_own_completed_results", None),
        ("matching_sequence", action["sequence_ref"])]:
        selected = restriction_selected_return_schema(_selection(ALL, policy=policy, reference=reference))
        value = project_restriction_action_return(action, selected)
        mapping = action["mapping"]
        assert value["population"] == mapping["population"]
        assert value["population"]["complete_empty_enzyme_count"] == 0
        row = value["enzyme_rows"][0]
        assert row["native_search_positions_1based"] == [6]
        assert row["positions"] == mapping["enzyme_rows"][0]["positions"]
        assert row["positions"][0]["watson_boundary_0based"] == 5
        assert row["positions"][0]["crick_boundary_0based"] == 9
        assert row["recognition_events"][0]["segments"] == [{"start": 4, "end": 10}]
        assert row["recognition_events"][0]["unwrapped_span_0based"] == [4, 10]
        assert row["recognition_match_count"] == 1
        assert row["positions"][0]["recognition_event_ordinal"] is None
        value["enzyme_rows"][0]["positions"].clear()
    assert action == original


def test_engineering_unavailable_record_keeps_null_separate_from_actual_zero():
    """S734-12: engineering availability fixture, no invented measurement."""
    action = _saved_action()
    action.update(mapping=None, mapping_artifact_ref=None, failure_code="reader_unavailable")
    selected = restriction_selected_return_schema(_selection(ALL))
    value = project_restriction_action_return(action, selected)
    assert value["population"] is None
    assert value["enzyme_rows"] is None
    assert value["topology"] is None
    assert value["data_status"] == "unavailable"
    assert value["issue_codes"] == ["reader_unavailable"]
    assert _saved_action()["mapping"]["population"]["complete_empty_enzyme_count"] == 0


def test_matching_reference_uses_existing_literal_form_semantics():
    """S734-13: inherit723's closed-form reference check without inventing one."""
    reference = "reference with spaces"
    literal = _base()
    props = literal["items"]["properties"]
    props["selection_policy"] = {"type": "string", "const": "matching_sequence"}
    props["sequence_ref"]["const"] = reference
    with pytest.raises(ReportBoundaryError) as existing:
        requested_restriction_projections(_wrapper(literal))
    with pytest.raises(ReportBoundaryError) as selected:
        restriction_selected_return_schema(_selection(ALL, policy="matching_sequence", reference=reference))
    assert selected.value.diagnostic["code"] == existing.value.diagnostic["code"]
