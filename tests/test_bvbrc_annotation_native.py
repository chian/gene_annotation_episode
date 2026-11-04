"""Engineered GTO byte controls, not BV-BRC task/deployment evidence.

The descriptor names below are syntactic metadata for this pure reader. These
tests mint no Store Source, grant, original task, native producer or observation.
"""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode import bvbrc_annotation_native as native


def gto():
    return {"id": "900.1", "scientific_name": "engineered annotation fixture",
        "domain": "Viruses", "genetic_code": 11,
        "contigs": [{"id": "c", "original_id": "original c", "dna": "ACGTACGT"}],
        "features": [{"id": "f", "type": "mat_peptide",
            "location": [["c", "2", "+", 3], ["c", 8, "-", 2]],
            "protein_translation": "M*", "function": "native label",
            "quality": {"truncated_begin": 0, "truncated_end": 1},
            "annotations": [["native annotation", "native annotator", 0, "event"]],
            "feature_creation_event": "event"}],
        "analysis_events": [{"id": "event", "tool_name": "VIGOR4",
            "success": 0, "parameters": "native scalar parameters"}],
        "job_metadata": {"task_id": "engineered-task"}}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def document(value=None, *, raw=None, complete=True, representation="gto"):
    raw = encoded(gto() if value is None else value) if raw is None else raw
    digest = hashlib.sha256(raw).hexdigest()
    content = {"source_ref": "source_" + "a" * 24,
        "artifact_field": "artifact_ref", "artifact_ref": "artifact_" + digest,
        "sha256": digest, "byte_count": len(raw)}
    return native.parse_annotation_artifact(raw, content=content,
        representation=representation, capture_complete=complete,
        expected_task_id="engineered-task")


def member(node, name):
    return [row["value"] for row in node["members"] if row["name"] == name]


def test_literal_viral_tokens_segment_order_quality_and_unsuccessful_native_event_survive():
    value = document()
    assert native.validate_annotation_document(value) == value
    assert value["identity"] == {"state": "matched", "observed_task_id": "engineered-task"}
    feature, = value["records"]["features"]["rows"]
    first, second = feature["location"]["rows"]
    assert first["native_location"]["items"][1] == {"kind": "string", "value": "2"}
    assert first["begin"] == 2 and first["interval"] == [1, 4]
    assert second["begin"] == 8 and second["interval"] == [6, 8]
    quality, = member(feature["native_record"], "quality")
    assert member(quality, "truncated_begin") == [{"kind": "number", "token": "0"}]
    assert member(quality, "truncated_end") == [{"kind": "number", "token": "1"}]
    event, = value["records"]["analysis_events"]["rows"]
    assert member(event["native_record"], "success") == [{"kind": "number", "token": "0"}]
    assert event["success_state"] == "reported_failure"
    result = native.calculate_annotation_components(value)
    assert result["status"] == "partial"
    assert result["contigs"][0]["valid_retained_feature_union_nt"] == 5
    assert result["features"][0]["segments"][0]["interval_length_nt"] == 3
    assert result["features"][0]["protein_composition"]["sheet"]["sequence"] == "M*"
    assert result["definitions"]["annotation_confidence"] is None
    assert "native_confidence" not in result["features"][0]


def test_multicontig_feature_keeps_segment_order_and_separate_contig_populations():
    data = gto()
    data["contigs"].append({"id": "other", "dna": "AAAA"})
    data["features"][0]["location"] = [["other", 1, "+", 2], ["c", 4, "-", 2]]
    value = document(data)
    rows = value["records"]["features"]["rows"][0]["location"]["rows"]
    assert [row["contig_ordinal"] for row in rows] == [1, 0]
    assert [row["interval"] for row in rows] == [[0, 2], [2, 4]]
    components = native.calculate_annotation_components(value)
    assert [row["valid_retained_feature_union_nt"] for row in components["contigs"]] == [2, 2]


@pytest.mark.parametrize("begin", [True, False, 1.0, "1.0", "-1", 0, -1,
    "9" * 5000])
def test_invalid_coordinate_tokens_remain_native_without_authorizing_geometry(begin):
    data = gto()
    data["features"][0]["location"] = [["c", begin, "+", 2]]
    value = document(data)
    row, = value["records"]["features"]["rows"][0]["location"]["rows"]
    assert row["state"] == "invalid" and row["interval"] is None
    assert native.validate_annotation_document(value) == value
    components = native.calculate_annotation_components(value)
    assert components["features"][0]["segments"][0]["interval_length_nt"] is None
    assert components["contigs"][0]["retained_feature_locations_complete"] is False


@pytest.mark.parametrize("location", [[["c", 8, "+", 2]], [["c", 1, "-", 2]],
    [["c", 1, "?", 2]], [["absent", 1, "+", 2]], [["c", 1, "+", 0]],
    [["c", 1, "+"]], [None], []])
def test_missing_invalid_outside_and_empty_locations_are_qualified_not_zero_extent(location):
    data = gto()
    data["features"][0]["location"] = location
    value = document(data)
    components = native.calculate_annotation_components(value)
    assert components["features"][0]["location_complete"] is False
    assert components["contigs"][0]["retained_feature_locations_complete"] is False
    assert value["issues"]


def test_duplicate_native_ids_preserve_every_occurrence_and_withhold_contig_association():
    data = gto()
    data["contigs"].append(deepcopy(data["contigs"][0]))
    data["features"].append(deepcopy(data["features"][0]))
    data["analysis_events"].append(deepcopy(data["analysis_events"][0]))
    value = document(data)
    for name in ("contigs", "features", "analysis_events"):
        assert [row["ordinal"] for row in value["records"][name]["rows"]] == [0, 1]
        assert [row["identity_state"] for row in value["records"][name]["rows"]] == ["ambiguous"] * 2
    assert all(row["state"] == "ambiguous_contig" for feature in value["records"]["features"]["rows"]
        for row in feature["location"]["rows"])
    assert native.calculate_annotation_components(value)["reported_feature_count"] == 2


def test_duplicate_object_members_and_noncanonical_number_lexemes_are_reversible():
    raw = b'{"contigs":[],"contigs":[{"id":"unselected"}],"features":[],"analysis_events":[],"n":1e+02,"n":-0}'
    value = document(raw=raw)
    assert value["records"]["contigs"]["state"] == "ambiguous"
    assert member(value["native_document"], "n") == [
        {"kind": "number", "token": "1e+02"}, {"kind": "number", "token": "-0"}]
    assert native.validate_annotation_document(value) == value
    assert native.calculate_annotation_components(value)["reported_contig_count"] is None


@pytest.mark.parametrize("replacement,state", [(None, "null"), ({}, "invalid"), ("wrong", "invalid")])
def test_null_and_wrong_collection_shapes_are_distinct_from_explicit_empty(replacement, state):
    data = gto()
    data["features"] = replacement
    value = document(data)
    assert value["records"]["features"]["state"] == state
    assert native.calculate_annotation_components(value)["reported_feature_count"] is None


def test_missing_collection_is_unknown_while_explicit_empty_is_observed_zero():
    data = gto()
    del data["features"]
    missing = document(data)
    assert missing["records"]["features"]["state"] == "missing"
    missing_components = native.calculate_annotation_components(missing)
    assert missing_components["reported_feature_count"] is None
    assert missing_components["contigs"][0]["valid_retained_feature_union_nt"] is None
    data["features"] = []
    empty = native.calculate_annotation_components(document(data))
    assert empty["reported_feature_count"] == 0
    assert empty["contigs"][0]["valid_retained_feature_union_nt"] == 0
    assert empty["contigs"][0]["retained_feature_locations_complete"] is True


@pytest.mark.parametrize("native_task,state", [("engineered-task", "matched"), ("different", "conflict"),
    ("unknown", "unavailable"), (None, "unavailable"), (0, "unavailable")])
def test_native_task_identity_is_independent_of_parse_and_task_completion(native_task, state):
    data = gto()
    data["job_metadata"]["task_id"] = native_task
    value = document(data)
    assert value["parsing_state"] == "available" and value["identity"]["state"] == state
    if state == "conflict":
        assert any(issue["severity"] == "error" for issue in value["issues"])
        assert native.calculate_annotation_components(value)["contigs"][0]["retained_feature_locations_complete"] is False


def test_complete_json_capture_does_not_hide_truncated_transfer_qualification():
    value = document(complete=False)
    assert value["parsing_state"] == "available"
    assert value["records"]["features"]["rows"]
    result = native.calculate_annotation_components(value)
    assert result["capture_complete"] is False
    assert result["contigs"][0]["retained_feature_locations_complete"] is False
    assert any(row["code"] == "native_capture_incomplete" for row in result["issues"])


@pytest.mark.parametrize("raw", [b"", b"\xff", b"{", b'{"bad":NaN}', b'{"bad":"\\ud800"}'])
def test_invalid_native_bytes_keep_descriptor_and_unknown_counts(raw):
    value = document(raw=raw)
    assert value["parsing_state"] == "unavailable" and value["native_document"] is None
    assert value["content"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert native.validate_annotation_document(value) == value
    assert native.calculate_annotation_components(value)["reported_feature_count"] is None


def test_private_descriptor_is_checked_before_any_native_parser(monkeypatch):
    raw = encoded(gto())
    digest = hashlib.sha256(raw).hexdigest()
    def forbidden(*args, **kwargs):
        raise AssertionError("parser reached before byte association")
    monkeypatch.setattr(native, "_parse", forbidden)
    with pytest.raises(ValueError, match="bvbrc_annotation_bytes_conflict"):
        native.parse_annotation_artifact(raw, content={"source_ref": "source_" + "a" * 24,
            "artifact_field": "artifact_ref", "artifact_ref": "artifact_" + digest,
            "sha256": digest, "byte_count": len(raw) + 1}, representation="gto",
            capture_complete=True, expected_task_id="engineered-task")


def test_saved_components_delegate_to_shared_authorities_without_raw_parser_or_io(monkeypatch):
    value = document()
    original = deepcopy(value)
    calls = []
    width, union, composition = native.interval_length, native.interval_union_length, native.calculate_sequence_composition_scores
    def forbidden(*args, **kwargs):
        raise AssertionError("raw parser or file access during saved calculation")
    def measured_width(arg):
        calls.append(("interval", deepcopy(arg)))
        return width(arg)
    def measured_union(arg):
        calls.append(("union", deepcopy(arg)))
        return union(arg)
    def measured_composition(arg, **kwargs):
        calls.append(("composition", arg["molecule"]))
        return composition(arg, **kwargs)
    monkeypatch.setattr(native, "_parse", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(native, "interval_length", measured_width)
    monkeypatch.setattr(native, "interval_union_length", measured_union)
    monkeypatch.setattr(native, "calculate_sequence_composition_scores", measured_composition)
    result = native.calculate_annotation_components(value)
    assert value == original
    assert calls == [("interval", [1, 4]), ("interval", [6, 8]), ("composition", "protein"),
        ("composition", "dna"), ("union", [[1, 4], [6, 8]])]
    assert result["features"][0]["protein_composition"]["sheet"]["sequence"] == "M*"


@pytest.mark.parametrize("mutation", ["coordinate", "identity", "qualifier", "added_issue", "removed_issue"])
def test_saved_normalized_or_qualified_data_cannot_contradict_native_document(mutation):
    value = document(complete=False)
    if mutation == "coordinate":
        value["records"]["features"]["rows"][0]["location"]["rows"][0]["interval"] = [0, 3]
    elif mutation == "identity":
        value["identity"]["state"] = "conflict"
    elif mutation == "qualifier":
        value["issues"][0]["severity"] = "error"
    elif mutation == "added_issue":
        value["issues"].append({"code": "invented", "path": "/", "severity": "qualification"})
    else:
        value["issues"].clear()
    with pytest.raises(ValueError, match="bvbrc_annotation_document_invalid"):
        native.validate_annotation_document(value)


@pytest.mark.parametrize("level,available", [(31, True), (32, False)])
def test_native_json_depth_is_explicit_and_never_truncated(level, available):
    data, nested = gto(), None
    for _ in range(level):
        nested = [nested]
    data["opaque"] = nested
    value = document(data)
    assert (value["parsing_state"] == "available") is available
    assert native.validate_annotation_document(value) == value


def test_native_quality_is_data_without_invented_gene_population_or_probability():
    value = document({"coarse_consistency": 0, "completeness": None,
        "native_label": "uninterpreted", "source_ref": "source_" + "b" * 24}, representation="quality_json")
    assert member(value["native_document"], "coarse_consistency") == [{"kind": "number", "token": "0"}]
    result = native.calculate_annotation_components(value)
    assert result["reported_feature_count"] is None and result["features"] is None
    assert result["definitions"]["annotation_confidence"] is None
    assert result["definitions"]["native_quality"] == "retained_only_no_unit_or_calibration_inferred"


@pytest.mark.parametrize("success,state", [(0, "reported_failure"), (1, "reported_success"),
    (None, "null"), ("0", "unavailable"), (False, "unavailable"), (1.0, "unavailable")])
def test_analysis_event_success_requires_explicit_native_integer_flag(success, state):
    data = gto()
    data["analysis_events"][0]["success"] = success
    value = document(data)
    event, = value["records"]["analysis_events"]["rows"]
    assert event["success_state"] == state
    assert any(row["code"] == "native_analysis_reported_failure" for row in value["issues"]) is (state == "reported_failure")
    assert native.validate_annotation_document(value) == value


@pytest.mark.parametrize("field", ["records_tuple", "bool_count", "cycle", "nonfinite"])
def test_saved_document_remains_strict_finite_json_without_python_aliases(field):
    value = document()
    if field == "records_tuple":
        value["records"]["features"]["rows"] = tuple(value["records"]["features"]["rows"])
    elif field == "bool_count":
        value["records"]["features"]["rows"][0]["ordinal"] = False
    elif field == "cycle":
        value["issues"].append(value["issues"])
    else:
        value["records"]["features"]["rows"][0]["ordinal"] = float("nan")
    with pytest.raises(ValueError, match="bvbrc_annotation_document_invalid"):
        native.validate_annotation_document(value)


@pytest.mark.parametrize("begin", ["2", "02", "0" * 100 + "2"])
def test_native_digit_string_coordinate_normalization_retains_original_token(begin):
    data = gto()
    data["features"][0]["location"] = [["c", begin, "+", 2]]
    value = document(data)
    row, = value["records"]["features"]["rows"][0]["location"]["rows"]
    assert row["state"] == "available" and row["interval"] == [1, 3]
    assert row["native_location"]["items"][1] == {"kind": "string", "value": begin}
    assert native.validate_annotation_document(value) == value


def test_depth_failure_keeps_prior_native_lexical_diagnostics_in_a_valid_unavailable_document():
    raw = b'{"n":1e+02,"n":-0,"deep":' + b'[' * 32 + b'null' + b']' * 32 + b'}'
    value = document(raw=raw)
    assert value["native_document"] is None and value["parsing_state"] == "unavailable"
    assert {row["code"] for row in value["issues"]} == {
        "native_duplicate_member", "native_number_token_required", "native_document_depth_or_shape_invalid"}
    assert native.validate_annotation_document(value) == value
    assert native.calculate_annotation_components(value)["reported_contig_count"] is None


@pytest.mark.parametrize("field", ["state_list", "state_object", "severity_list", "severity_object"])
def test_wrong_json_state_and_severity_types_have_controlled_validation_errors(field):
    value = document(complete=False)
    wrong = [] if field.endswith("list") else {}
    if field.startswith("state"):
        value["parsing_state"] = wrong
    else:
        value["issues"][0]["severity"] = wrong
    with pytest.raises(ValueError, match="bvbrc_annotation_document_invalid"):
        native.validate_annotation_document(value)
