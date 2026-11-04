"""Engineered native-artifact bindings, never a BV-BRC task or custody claim.

Actual task/receipt/Source authentication remains the existing AppService host.
These tests exercise byte binding, literal native data and saved projection.
"""
from copy import deepcopy
import ast
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import bvbrc_annotation_bundle_adapter as adapter
from gene_annotation_episode import bvbrc_annotation_contracts as contracts
from gene_annotation_episode import bvbrc_annotation_native as native
from test_bvbrc_annotation_native import encoded, gto, member


def selection(kind="features", *, ordinals=None, members=None, offset=0, limit=50, document_id="genome"):
    return {"version": contracts.SELECTION_VERSION, "document_id": document_id,
        "kind": kind, "ordinals": ordinals, "offset": offset, "limit": limit, "member_names": members}


def arguments(*, data=None, raw=None, selections=None):
    data = gto() if data is None else data
    data = deepcopy(data)
    if "analysis_events" in data and type(data["analysis_events"]) is list and data["analysis_events"]:
        data["analysis_events"][0]["success"] = 1
    raw = encoded(data) if raw is None else raw
    sha = hashlib.sha256(raw).hexdigest()
    source = "source_" + "a" * 24
    task = {"resource_id": "engineered-appservice", "task_id": "engineered-task",
        "required_application_id": "GenomeAnnotation", "native_application_id": "GenomeAnnotation",
        "submitted_parameters": {"scientific_name": "engineered fixture"},
        "submitted_start_parameters": {}, "scheduler_returned_parameters": None,
        "effective_parameters": None, "submission_receipt_ref": "source_" + "b" * 24,
        "submission_operation_key": "engineered:original:0", "submission_source_ref": "source_" + "c" * 24}
    artifact = {"role": "caller_selected_gto", "source_ref": source,
        "raw_artifact_ref": "artifact_" + sha, "sha256": sha, "byte_count": len(raw),
        "workspace_object": {"path": "/engineered/output.genome", "uuid": "engineered-output-object",
            "type": "genome", "metadata_receipt_ref": "source_" + "d" * 24},
        "task_association": {"kind": "task_info_object", "evidence_ref": "source_" + "e" * 24,
            "pointer": "/result_files/0", "task_id": task["task_id"],
            "output_path": "/engineered/output.genome", "output_uuid": "engineered-output-object",
            "byte_version_status": "current_bytes_observed", "version_evidence": []},
        "transfer": {"receipt_ref": source, "body_complete": True, "requested_range": None,
            "observed_range": None, "total_size": len(raw), "object_complete": "yes"},
        "declared_format": {"format": "gto", "version": None, "mode": None,
            "producer_source_ref": None, "transformation_evidence": []}, "requirement_ids": ["native-genome"]}
    bundle = {"version": "bvbrc_appservice_artifact_bundle_v1", "original_task": task,
        "artifacts": [artifact], "input_bindings": [], "query_bindings": [],
        "supplied_scientific_metadata": [], "supplied_contents": [],
        "acquisition_receipt_refs": [source], "requested_selector_sha256": "f" * 64,
        "status": "ok", "missing_requirements": [], "diagnostics": []}
    parameters = {"version": contracts.PARAMETERS_VERSION, "analysis_id": "selected-engineered-annotation",
        "application_id": "GenomeAnnotation", "documents": [{"document_id": "genome",
            "requirement_id": "native-genome", "representation": "gto"}]}
    fields = selections if selections is not None else [{"field": "genes", "selection": selection()}]
    return {"bundle": bundle, "artifact_bytes": {artifact["raw_artifact_ref"]: raw}, "supplied_values": [],
        "requested_form": contracts.requested_form_schema(fields), "parameters": parameters}


def project(result, args, fields=None):
    form = args["requested_form"] if fields is None else contracts.requested_form_schema(fields)
    return adapter.project_annotation_facts(result["sheet"], result["components"],
        parameters=args["parameters"], requested_form=form)


def test_bound_native_records_and_existing_components_survive_literal_selected_return():
    args = arguments(selections=[{"field": "genes", "selection": selection()},
        {"field": "math", "selection": selection("components", members=["reported_feature_count", "features"])}])
    original = deepcopy(args)
    result = adapter.consume_bundle(**args)
    assert args == original and result["status"] == "ok"
    record, = result["facts"]["genes"]["records"]
    assert member(record["value"], "id") == [{"kind": "string", "value": "f"}]
    assert result["facts"]["math"]["records"][0]["value"]["reported_feature_count"] == 1
    assert result["components"]["documents"][0]["components"]["contigs"][0]["valid_retained_feature_union_nt"] == 5
    assert result["facts"]["genes"]["record_accounting"]["intended_population_complete"] is None
    assert adapter.validate_saved_annotation_facts(result["facts"], sheet=result["sheet"],
        components=result["components"], parameters=args["parameters"], requested_form=args["requested_form"]) == result["facts"]


def test_order_duplicate_occurrences_paging_and_empty_view_do_not_change_retained_population():
    data = gto(); data["features"].append({**deepcopy(data["features"][0]), "id": "other"})
    args = arguments(data=data, selections=[{"field": "genes", "selection": selection(ordinals=[1, 0, 1], offset=1, limit=2)}])
    result = adapter.consume_bundle(**args)
    fact = result["facts"]["genes"]
    assert [row["requested_ordinal"] for row in fact["records"]] == [0, 1]
    assert fact["record_accounting"] == {"retained_total": 2, "requested_occurrences": 3,
        "matched_occurrences": 3, "returned_occurrences": 2,
        "population_scope": "retained_native_records_only", "intended_population_complete": None}
    empty = project(result, args, [{"field": "none", "selection": selection(ordinals=[])}])["none"]
    assert empty["records"] == [] and empty["record_accounting"]["retained_total"] == 2
    assert empty["context"]["definitions"] == fact["context"]["definitions"]


@pytest.mark.parametrize("change", ["missing", "ambiguous", "unverified-path", "wrong-format", "bytes-missing"])
def test_no_first_artifact_fallback_for_missing_ambiguous_or_incompatible_selected_requirement(change):
    args = arguments(); bundle = args["bundle"]; artifact = bundle["artifacts"][0]
    if change == "missing": artifact["requirement_ids"] = ["another-requirement"]
    elif change == "ambiguous": bundle["artifacts"].append(deepcopy(artifact))
    elif change == "unverified-path": artifact["task_association"]["kind"] = "unverified_original_path"
    elif change == "wrong-format": artifact["declared_format"]["format"] = "html"
    else: args["artifact_bytes"] = {}
    result = adapter.consume_bundle(**args)
    assert result["status"] == "partial" and result["missing_requirements"]
    assert result["sheet"]["documents"][0]["document"] is None
    assert result["facts"]["genes"]["records"][0]["state"] == "source_unavailable"
    assert result["components"]["documents"][0]["components"] is None


def test_conflicting_bundle_task_is_rejected_by_the_existing_contract_before_adapter_consumption():
    args = arguments()
    args["bundle"]["artifacts"][0]["task_association"]["task_id"] = "another-task"
    with pytest.raises(ValueError, match="original_task_mismatch"):
        adapter.consume_bundle(**args)


@pytest.mark.parametrize("complete,object_complete", [(False, "no"), (True, "unknown"), (True, "no")])
def test_observed_complete_json_is_retained_but_never_promoted_over_incomplete_object_capture(complete, object_complete):
    args = arguments(); transfer = args["bundle"]["artifacts"][0]["transfer"]
    transfer.update(body_complete=complete, object_complete=object_complete)
    result = adapter.consume_bundle(**args)
    assert result["status"] == "partial" and result["facts"]["genes"]["records"][0]["state"] == "available"
    assert result["facts"]["genes"]["context"]["capture_complete"] is False
    assert result["components"]["documents"][0]["components"]["contigs"][0]["retained_feature_locations_complete"] is False


@pytest.mark.parametrize("native_task", ["other-task", "unknown"])
def test_native_task_conflict_is_retained_distinct_from_authenticated_bundle_task(native_task):
    data = gto(); data["job_metadata"]["task_id"] = native_task
    result = adapter.consume_bundle(**arguments(data=data))
    assert result["facts"]["genes"]["context"]["original_task"]["task_id"] == "engineered-task"
    assert result["facts"]["genes"]["context"]["native_task_identity"]["observed_task_id"] == native_task
    assert (result["status"] == "partial") is (native_task == "other-task")


def test_native_failed_event_is_inspectable_and_does_not_become_annotation_success():
    args = arguments(raw=encoded(gto()))
    result = adapter.consume_bundle(**args)
    assert result["status"] == "partial"
    assert any(row["code"] == "native_analysis_reported_failure" for row in result["diagnostics"])
    assert result["facts"]["genes"]["records"]


@pytest.mark.parametrize("raw", [b"{", b"null", b"[]"])
def test_unavailable_or_nonobject_native_data_keeps_unknown_components_inspectable(raw):
    args = arguments(raw=raw, selections=[{"field": "math", "selection": selection("components")}])
    result = adapter.consume_bundle(**args)
    assert result["status"] == "partial"
    components = result["facts"]["math"]["records"][0]["value"]
    assert components["reported_feature_count"] is None and components["features"] is None
    assert components["definitions"]["annotation_confidence"] is None


@pytest.mark.parametrize("kind", ["contigs", "features", "analysis_events"])
def test_missing_native_array_empty_selection_preserves_unknown_not_one_placeholder(kind):
    data = gto(); del data[kind]
    args = arguments(data=data, selections=[{"field": "empty", "selection": selection(kind, ordinals=[])}])
    fact = adapter.consume_bundle(**args)["facts"]["empty"]
    assert fact["records"] == [] and fact["record_accounting"]["retained_total"] is None
    assert fact["record_accounting"]["requested_occurrences"] == 0


def test_missing_duplicate_and_null_native_members_remain_distinct_and_callable_looking_strings_opaque():
    raw = b'{"features":[{"id":"f","source_ref":"source_aaaaaaaaaaaaaaaaaaaaaaaa","q":null,"q":-0}],"contigs":[],"analysis_events":[]}'
    args = arguments(raw=raw, selections=[{"field": "native", "selection": selection(members=["q", "source_ref", "absent"])}])
    result = adapter.consume_bundle(**args)
    value = result["facts"]["native"]["records"][0]["value"]
    assert [row["name"] for row in value["members"]] == ["source_ref", "q", "q"]
    assert member(value, "q") == [{"kind": "null", "value": None}, {"kind": "number", "token": "-0"}]
    assert any(row["code"] == "native_selected_member_missing" for row in result["facts"]["native"]["issues"])
    assert result["status"] == "partial"
    assert "x-reference-namespace" not in json.dumps(args["requested_form"])


def test_saved_view_reads_no_native_bytes_or_parser_or_calculator(monkeypatch):
    args = arguments(); result = adapter.consume_bundle(**args); before = deepcopy(result)
    def forbidden(*a, **k): raise AssertionError("saved projection performed acquisition/parsing/calculation")
    for owner, name in [(native, "_parse"), (adapter, "parse_annotation_artifact"),
            (adapter, "calculate_annotation_components"), (native, "calculate_sequence_composition_scores"),
            (native, "interval_length"), (native, "interval_union_length")]:
        monkeypatch.setattr(owner, name, forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    fact = project(result, args, [{"field": "other", "selection": selection("native_document", members=["quality"])}])["other"]
    assert fact["records"][0]["value"]["kind"] == "object" and result == before


@pytest.mark.parametrize("change", ["document-digest", "original-task", "row-id", "count-float", "capture", "fact-value", "fact-count-float"])
def test_saved_content_and_selected_facts_cannot_silently_contradict_original_observations(change):
    args = arguments(); result = adapter.consume_bundle(**args)
    value = result["components"]["documents"][0]["components"]
    if change == "document-digest": value["document_sha256"] = "0" * 64
    elif change == "original-task": result["sheet"]["original_task"]["task_id"] = "different"
    elif change == "row-id": value["features"][0]["id"] = "different"
    elif change == "count-float": value["reported_feature_count"] = 1.0
    elif change == "capture": value["capture_complete"] = False
    elif change == "fact-value": result["facts"]["genes"]["records"][0]["value"] = {"kind": "null", "value": None}
    else: result["facts"]["genes"]["record_accounting"]["returned_occurrences"] = 1.0
    with pytest.raises(ValueError):
        adapter.validate_saved_annotation_facts(result["facts"], sheet=result["sheet"], components=result["components"],
            parameters=args["parameters"], requested_form=args["requested_form"])


@pytest.mark.parametrize("schema", [contracts.parameters_schema, contracts.selection_schema,
    lambda: contracts.requested_form_schema([]),
    lambda: contracts.requested_form_schema([{"field": "x", "selection": selection()}])])
def test_exported_schema_is_valid_draft202012(schema):
    Draft202012Validator.check_schema(schema())


@pytest.mark.parametrize("mutation", ["bool-offset", "float-ordinal", "duplicate-member", "root-ordinal", "unknown-kind", "extra"])
def test_selections_are_explicit_strict_ordered_occurrences_not_automatic_first_rows(mutation):
    value = selection()
    if mutation == "bool-offset": value["offset"] = False
    elif mutation == "float-ordinal": value["ordinals"] = [0.0]
    elif mutation == "duplicate-member": value["member_names"] = ["id", "id"]
    elif mutation == "root-ordinal": value.update(kind="components", ordinals=[0])
    elif mutation == "unknown-kind": value["kind"] = "annotation_probability"
    else: value["default_first"] = True
    with pytest.raises(ValueError): contracts.validate_selection(value)


def test_empty_return_schema_and_zero_view_keep_all_qualifications_without_native_recalculation():
    args = arguments(selections=[]); result = adapter.consume_bundle(**args)
    assert result["facts"] == {} and result["sheet"]["documents"][0]["document"] is not None
    assert contracts.validate_facts({}, requested_form=args["requested_form"]) == {}


def test_adapter_pin_covers_selected_pure_sources_and_import_time_dependencies_exactly():
    base = Path(adapter.__file__).parent
    pending, seen = ["bvbrc_annotation_bundle_adapter"], set()
    while pending:
        name = pending.pop()
        if name in seen: continue
        seen.add(name)
        for node in ast.parse((base / (name + ".py")).read_text()).body:
            names = [node.module] if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module else (
                [item.name for item in node.names] if isinstance(node, ast.ImportFrom) and node.level == 1 else [])
            pending.extend(name for name in names if name not in seen and (base / (name + ".py")).is_file())
    expected = {name + ".py" for name in seen} | {"__init__.py", "bvbrc_appservice_schemas.json"}
    assert set(adapter._DEPENDENCIES) == expected and len(adapter._DEPENDENCIES) == len(expected)
    digest = hashlib.sha256()
    for name in sorted(expected):
        data = (base / name).read_bytes()
        digest.update(name.encode() + b"\0" + str(len(data)).encode() + b"\0" + data)
    assert adapter.implementation_sha256() == digest.hexdigest()
