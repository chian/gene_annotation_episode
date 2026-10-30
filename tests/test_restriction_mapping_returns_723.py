"""Pure requested-return checks over retained718/719 data.

Action/source references are labelled engineering fixtures, not receipt or Store
authority. No native analysis is performed. Application execution uses529 only.
"""
import builtins
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, validate_closed_schema, validate_form
from gene_annotation_episode import restriction_mapping_returns as views


pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")
SOURCE = "restriction_mapping_results"
MANDATORY = ("selection_policy", "sequence_ref", "namespace", "topology", "data_status",
             "coordinate_unit", "population_scope")


def object_schema(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def fields(*, selected=None, names=None):
    node = views.restriction_mapping_fact_sources()[SOURCE]["report_schema"]
    props = node["items"]["properties"]
    props["selection_policy"] = {"type": "string", "const":
        "all_own_completed_results" if selected is None else "matching_sequence"}
    if selected is not None:
        props["sequence_ref"]["const"] = selected
    if names is not None:
        node["items"] = object_schema({name: props[name] for name in names})
    return node


def record(mapping, *, name="find_restriction_sites", mode="native"):
    """Synthetic host metadata around an unchanged retained scientific result."""
    selected = mapping["selected_sequence"]
    return {"decision_index": 2, "operation_ref": "operation_synthetic723", "tool_name": name,
        "work_mode": mode, "operation_status": "partial" if mapping["status"] == "partial" else "completed",
        "sequence_ref": selected["sequence_ref"], "namespace": selected["namespace"],
        "input_source_ref": selected["source_ref"], "source_ref": "source_synthetic723",
        "native_artifact_ref": "artifact_synthetic_native723", "mapping_artifact_ref": "artifact_synthetic_mapping723",
        "mapping": deepcopy(mapping), "failure_code": None}


@pytest.fixture(scope="module")
def retained():
    root = Path(__file__).resolve().parents[1]
    pins = json.loads((root / "verification/tool_graders_restriction_mapping_readers_2026-10-29_719/RETAINED_RESULT_PINS_001.json").read_text())
    directory = root / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check183b_reader719_native/retained-reader719"
    values = {}
    for pin in pins:
        p = directory / Path(pin["path"]).name
        raw = p.read_bytes()
        assert len(raw) == pin["size_bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"]
        values[p.stem] = json.loads(raw)
    assert len(values) == 13
    destination = Path(os.environ["HMMER529_ATTEMPT"]) / "retained-returns723"
    destination.mkdir(exist_ok=False)
    for name, mapping in values.items():
        projected = views.project_restriction_action_return(record(mapping,
            name="find_restriction_enzymes" if name == "commercial_linear_internal" else "find_restriction_sites"), fields())
        (destination / (name + ".json")).write_text(json.dumps(projected, sort_keys=True, allow_nan=False) + "\n")
    return values


def fixture_resolver(action):
    """Resolve only actual fixture identities/catalog names; grant no Store scope."""
    refs = {action[name] for name in ("sequence_ref", "source_ref", "input_source_ref")}
    names = {row["name"] for row in action["mapping"]["enzyme_rows"]} if action["mapping"] else set()
    def resolve(value, namespace):
        return value in names if namespace == "restriction_enzyme" else value in refs
    return resolve


def test_full_available_schema_is_closed_and_enzyme_namespace_is_explicit(retained):
    action = record(retained["ecori_linear_internal"])
    node = fields();schema = object_schema({"results": node})
    validate_closed_schema(schema)
    value = views.project_restriction_action_return(action, node)
    validate_form({"results": [value]}, schema, fixture_resolver(action))
    assert node["items"]["properties"]["enzyme_rows"]["items"]["properties"]["name"]["x-reference-namespace"] == "restriction_enzyme"
    with pytest.raises(ReportBoundaryError):
        validate_form({"results": [value]}, schema,
            lambda value, namespace: False if namespace == "restriction_enzyme" else value in {
                action["sequence_ref"], action["source_ref"], action["input_source_ref"]})


def test_all_retained_results_copy_source_values_and_omit_internal_native_material(retained):
    for name, mapping in retained.items():
        action = record(mapping)
        actual = views.project_restriction_action_return(action, fields())
        assert actual["population"] == mapping["population"]
        assert actual["topology"] == mapping["topology"] and actual["data_status"] == mapping["status"]
        assert len(actual["enzyme_rows"]) == len(mapping["enzyme_rows"])
        for row, saved in zip(actual["enzyme_rows"], mapping["enzyme_rows"]):
            assert row["positions"] == saved["positions"]
            assert row["native_search_positions_1based"] == saved["native_search_positions_1based"]
            assert row["recognition_match_count"] == saved["recognition_match_count"]
            assert row["returned_position_count"] == saved["returned_position_count"]
            assert row["recognition_motif"] == saved["catalog_row"]["native_site"]
            assert row["recognition_events"] is None or all("native_groups" not in event for event in row["recognition_events"])
            assert "catalog_row" not in row and "elucidate_text" not in row
        assert not {"operation_ref", "decision_index", "native_artifact_ref", "mapping_artifact_ref",
            "native_sha256", "mapping", "exception", "dictionary_entry_json"}.intersection(actual)


def test_actual_commercial_population_remains_full_population_not_returned_nonempty_rows(retained):
    mapping = retained["commercial_linear_internal"]
    actual = views.project_restriction_action_return(record(mapping, name="find_restriction_enzymes"), fields())
    assert actual["population"]["selected_enzyme_count"] == actual["population"]["returned_enzyme_count"] == 623
    assert actual["population"]["complete_empty_enzyme_count"] == 616
    assert actual["population"]["recognition_match_count"] == 9
    assert len(actual["enzyme_rows"]) == 623


def test_duplicate_cuts_nocut_reverse_and_short_circle_qualifications_are_copied(retained):
    duplicate = views.project_restriction_action_return(record(retained["duplicate_bcgi"]), fields())["enzyme_rows"][0]
    assert duplicate["native_search_positions_1based"] == [41, 75, 75, 109]
    assert (duplicate["returned_position_count"], duplicate["recognition_match_count"]) == (4, 2)
    assert all(position["recognition_event_ordinal"] is None for position in duplicate["positions"])
    no_cut = views.project_restriction_action_return(record(retained["nocut_snai"]), fields())["enzyme_rows"][0]
    assert no_cut["native_search_positions_1based"] == [5] and no_cut["position_meaning"] == "recognition_start_1based"
    assert no_cut["positions"][0]["watson_boundary_0based"] is None
    reverse = views.project_restriction_action_return(record(retained["reverse_bsai"]), fields())["enzyme_rows"][0]
    assert reverse["recognition_events"][0]["orientation"] == "reverse"
    assert reverse["recognition_events"][0]["unwrapped_span_0based"] == [30, 36]
    short = views.project_restriction_action_return(record(retained["short_circle_bcgi"]), fields())["enzyme_rows"][0]
    assert short["native_search_positions_1based"] == [3, 13]
    assert [p["watson_boundary_0based"] for p in short["positions"]] == [2, 12]
    assert [p["watson_canonical_boundary_0based"] for p in short["positions"]] == [2, 0]


def test_partial_missing_and_completed_empty_results_remain_distinct(retained):
    partial = views.project_restriction_action_return(record(retained["engineering_partial_search"]), fields())
    assert partial["data_status"] == "partial" and partial["population"]["recognition_match_count"] is None
    assert sorted(row["search_state"] for row in partial["enzyme_rows"]) == ["failed", "not_started", "returned"]
    empty = views.project_restriction_action_return(record(retained["empty_explicit"]), fields())
    assert empty["enzyme_rows"] == [] and set(empty["population"].values()) == {0}
    observer = views.project_restriction_action_return(record(retained["engineering_observer_failure"]), fields())
    assert observer["enzyme_rows"][0]["returned_position_count"] == 1
    assert observer["enzyme_rows"][0]["recognition_match_count"] is None


def test_parent_subset_is_exact_detached_and_uses_matching_sequence(retained):
    action = record(retained["duplicate_bcgi"], mode="saved")
    node = fields(selected=action["sequence_ref"], names=(*MANDATORY, "population", "enzyme_rows"))
    pop = node["items"]["properties"]["population"]
    pop["properties"] = {"recognition_match_count": pop["properties"]["recognition_match_count"]};pop["required"] = list(pop["properties"])
    row = node["items"]["properties"]["enzyme_rows"]["items"]
    keep = ("catalog_ordinal", "name", "search_state", "position_meaning", "native_search_positions_1based")
    row["properties"] = {key: row["properties"][key] for key in keep};row["required"] = list(keep)
    actual = views.project_restriction_action_return(action, node)
    assert set(actual) == set((*MANDATORY, "population", "enzyme_rows"))
    assert actual["population"] == {"recognition_match_count": 2}
    assert set(actual["enzyme_rows"][0]) == set(keep)
    actual["enzyme_rows"][0]["native_search_positions_1based"].pop()
    assert action["mapping"]["enzyme_rows"][0]["native_search_positions_1based"] == [41, 75, 75, 109]


def test_mapping_unavailable_preserves_null_population_and_explicit_failure(retained):
    action = record(retained["ecori_linear_internal"])
    action.update(mapping=None, mapping_artifact_ref=None, failure_code="reader_unavailable", operation_status="partial")
    actual = views.project_restriction_action_return(action, fields())
    assert actual["population"] is actual["enzyme_rows"] is actual["topology"] is None
    assert actual["data_status"] == "unavailable" and actual["issue_codes"] == ["reader_unavailable"]


@pytest.mark.parametrize("fault", ["policy_missing", "all_const", "all_enum", "matching_no_ref", "namespace_widened",
    "unit_changed", "source_unknown", "field_unknown", "weak_bound", "population_nonnullable", "wrong_namespace"])
def test_invalid_parent_selectors_and_semantics_fail_before_projection(fault):
    node = fields();props = node["items"]["properties"]
    if fault == "policy_missing": props["selection_policy"] = {"type": "string", "enum": ["all_own_completed_results", "matching_sequence"]}
    elif fault == "all_const": props["sequence_ref"]["const"] = "subject_other723"
    elif fault == "all_enum": props["sequence_ref"]["enum"] = ["subject_other723"]
    elif fault == "matching_no_ref": props["selection_policy"]["const"] = "matching_sequence"
    elif fault == "namespace_widened": props["namespace"]["enum"].append("derivative")
    elif fault == "unit_changed": props["coordinate_unit"]["const"] = "aa"
    elif fault == "source_unknown": node["x-source"] = "restriction_mapping_unknown"
    elif fault == "field_unknown": props["annotation_confidence"] = {"type": "number"};node["items"]["required"].append("annotation_confidence")
    elif fault == "weak_bound": props["population"]["properties"]["attempted_enzyme_count"].pop("minimum")
    elif fault == "population_nonnullable": props["population"]["type"] = "object"
    else: props["enzyme_rows"]["items"]["properties"]["name"]["x-reference-namespace"] = "subject"
    with pytest.raises(ReportBoundaryError): views.requested_restriction_projections(object_schema({"results": node}))


@pytest.mark.parametrize("field", MANDATORY)
def test_required_group_identity_meanings_cannot_be_omitted(field):
    node = fields();node["items"]["properties"].pop(field);node["items"]["required"].remove(field)
    with pytest.raises(ReportBoundaryError): views.requested_restriction_projections(object_schema({"results": node}))


@pytest.mark.parametrize("path,key", [("row", "name"), ("positions", "geometry_state"),
    ("events", "orientation"), ("segments", "end")])
def test_nested_coordinate_and_native_identity_fields_are_required(path, key):
    node = fields();row = node["items"]["properties"]["enzyme_rows"]["items"]
    target = row if path == "row" else row["properties"]["positions"]["items"] if path == "positions" else row["properties"]["recognition_events"]["items"]
    if path == "segments": target = target["properties"]["segments"]["items"]
    target["properties"].pop(key);target["required"].remove(key)
    with pytest.raises(ReportBoundaryError): views.requested_restriction_projections(object_schema({"results": node}))


def test_multiple_requested_fields_require_identical_selection_and_subsets():
    first = fields(names=MANDATORY);second = fields(names=(*MANDATORY, "population"))
    with pytest.raises(ReportBoundaryError): views.requested_restriction_projections(object_schema({"first": first, "second": second}))
    schema = object_schema({"first": first, "second": deepcopy(first), "other": {"type": "integer"}})
    original = deepcopy(schema);result = views.requested_restriction_projections(schema)
    assert list(result) == [SOURCE] and schema == original
    result[SOURCE]["fields"]["items"]["properties"].clear()
    assert schema == original


@pytest.mark.parametrize("fault", ["bool_decision", "float_decision", "wrong_source", "wrong_sequence", "wrong_namespace",
    "missing_native", "missing_mapping", "mapping_and_failure", "null_without_failure", "extra_field"])
def test_action_metadata_and_saved_binding_mismatches_fail(retained, fault):
    action = record(retained["ecori_linear_internal"])
    if fault == "bool_decision": action["decision_index"] = True
    elif fault == "float_decision": action["decision_index"] = 2.0
    elif fault == "wrong_source": action["input_source_ref"] = "source_other723"
    elif fault == "wrong_sequence": action["sequence_ref"] = "subject_other723"
    elif fault == "wrong_namespace": action["namespace"] = "reference"
    elif fault == "missing_native": action["native_artifact_ref"] = None
    elif fault == "missing_mapping": action["mapping_artifact_ref"] = None
    elif fault == "mapping_and_failure": action["failure_code"] = "reader_unavailable"
    elif fault == "null_without_failure": action.update(mapping=None, mapping_artifact_ref=None)
    else: action["narrative_findings"] = "synthetic forbidden field"
    with pytest.raises(ReportBoundaryError): views.project_restriction_action_return(action, fields())


def test_matching_reference_mismatch_is_error_and_shared_result_is_validated_once(retained, monkeypatch):
    action = record(retained["ecori_linear_internal"])
    with pytest.raises(ReportBoundaryError): views.project_restriction_action_return(action, fields(selected="subject_other723"))
    original = views.validate_restriction_record;calls = []
    def validate(kind, value): calls.append(kind);return original(kind, value)
    monkeypatch.setattr(views, "validate_restriction_record", validate)
    views.project_restriction_action_return(action, fields())
    assert calls == ["MappingResult"]


@pytest.mark.parametrize("fault", ["number", "source", "reorder", "drop_duplicate", "integer_float", "missing_frozen", "missing_form"])
def test_frozen_form_requires_exact_original_values_order_and_scalar_types(retained, fault):
    action = record(retained["duplicate_bcgi"]);node = fields();schema = object_schema({"results": node})
    actual = views.project_restriction_action_return(action, node);facts = {SOURCE: [deepcopy(actual)]};form = {"results": [deepcopy(actual)]}
    views.validate_frozen_restriction_return(form, schema, facts)
    if fault == "number": form["results"][0]["population"]["recognition_match_count"] = 3
    elif fault == "source": form["results"][0]["source_ref"] = "source_other723"
    elif fault == "reorder": form["results"][0]["enzyme_rows"][0]["positions"].reverse()
    elif fault == "drop_duplicate": form["results"][0]["enzyme_rows"][0]["native_search_positions_1based"].pop(2)
    elif fault == "integer_float": form["results"][0]["population"]["recognition_match_count"] = 2.0
    elif fault == "missing_frozen": facts.clear()
    else: form.clear()
    with pytest.raises(ReportBoundaryError): views.validate_frozen_restriction_return(form, schema, facts)


def test_projection_and_frozen_validation_require_no_io_native_reader_or_network(retained, monkeypatch):
    action = record(retained["duplicate_bcgi"]);node = fields();expected = views.project_restriction_action_return(action, node)
    schema = object_schema({"results": node});original_import = builtins.__import__
    def imports(name, *args, **kwargs):
        if name == "Bio" or name.startswith("Bio.") or name.endswith(("restriction_mapping_native", "restriction_mapping_readers")):
            raise AssertionError("projection tried native or reader import")
        return original_import(name, *args, **kwargs)
    def denied(*args, **kwargs): raise AssertionError("projection attempted I/O or dispatch")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "__import__", imports)
        patch.setattr(builtins, "open", denied);patch.setattr(io, "open", denied);patch.setattr(Path, "open", denied)
        patch.setattr(socket.socket, "connect", denied);patch.setattr(socket, "create_connection", denied)
        patch.setattr(subprocess, "Popen", denied);patch.setattr(subprocess, "run", denied)
        actual = views.project_restriction_action_return(action, node)
        views.validate_frozen_restriction_return({"results": [actual]}, schema, {SOURCE: [expected]})
    assert actual == expected


def test_nonfinite_cyclic_and_invalid_saved_scalar_data_are_rejected(retained):
    action = record(retained["ecori_linear_internal"])
    for wrong in [True, 1.0, float("nan")]:
        invalid = deepcopy(action);invalid["mapping"]["population"]["recognition_match_count"] = wrong
        with pytest.raises(ReportBoundaryError): views.project_restriction_action_return(invalid, fields())
    cyclic = {};cyclic["self"] = cyclic
    with pytest.raises(ReportBoundaryError): views.requested_restriction_projections(cyclic)
