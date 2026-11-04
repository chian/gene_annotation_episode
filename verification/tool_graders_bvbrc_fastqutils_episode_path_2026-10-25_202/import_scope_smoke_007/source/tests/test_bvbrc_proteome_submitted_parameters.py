"""Actual host-retained request bytes into real pure A/B1/B2/B3/B4 routines.

The remote submission response is controlled and scientific output fixtures are
explicitly synthetic native-format bytes. No constructor or numeric success is
stubbed. The pure decoder checks content/shape; actual custody remains separate.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_proteome_bundle_contracts as c
from gene_annotation_episode import bvbrc_proteome_bundle_resolution as provider
from gene_annotation_episode.bvbrc_proteome_bundle_projection import validate_saved_projection
from gene_annotation_episode.bvbrc_proteome_calculators import calculate_native_components
from test_bvbrc_appservice_request_content import PARAMETER_POINTER, submitted, retained_submission
from test_bvbrc_proteome_bundle_resolution import fixture, consume, codes, sync_supplied


def submitted_case(s):
    case = fixture(effective=False)
    old = case["supplied_values"][0]["value"]["original_input_index"]["parameter_source"]["source_field"]["source_ref"]
    case["bundle"]["supplied_contents"] = [b for b in case["bundle"]["supplied_contents"] if b["source_ref"] != old]
    case["artifact_bytes"].pop(old)
    case["bundle"]["original_task"] = deepcopy(s.task)
    for artifact in case["bundle"]["artifacts"]:
        artifact["task_association"]["task_id"] = s.task["task_id"]
    for binding in case["bundle"]["input_bindings"]:
        ordinal = int(binding["parameter_pointer"].rsplit("/", 1)[1])
        binding["workspace_path"] = s.task["submitted_parameters"]["user_genomes"][ordinal]
    case["bundle"]["supplied_contents"].append(deepcopy(s.binding))
    case["artifact_bytes"][s.binding["artifact_ref"]] = s.raw
    selected = case["supplied_values"][0]["value"]["original_input_index"]
    selected["parameter_source"] = dict(kind="submitted", source_field=dict(source_ref=s.binding["source_ref"],
        sha256=s.binding["sha256"], pointer=PARAMETER_POINTER, row_ordinal=None, field_name=None))
    sync_supplied(case)
    return case


def selected_source(case):
    return case["supplied_values"][0]["value"]["original_input_index"]["parameter_source"]["source_field"]


def request_binding(case):
    return next(b for b in case["bundle"]["supplied_contents"] if b["artifact_field"] == "request_ref")


def replace_request_bytes(case, raw):
    """Create a pure negative fixture, never pretend modified bytes have custody."""
    binding = request_binding(case)
    case["artifact_bytes"].pop(binding["artifact_ref"])
    sha = hashlib.sha256(raw).hexdigest()
    binding.update(sha256=sha, byte_count=len(raw), artifact_ref="artifact_" + sha)
    selected_source(case)["sha256"] = sha
    case["artifact_bytes"][binding["artifact_ref"]] = raw
    sync_supplied(case)


def assert_native_means(result):
    assert result["facts"]["identity_mean"]["cell"]["value"] == .4375
    assert result["facts"]["endpoint_mean"]["cell"]["value"] == .625
    assert result["facts"]["selected"]["cell"]["value"] == 1


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("submitted-parameter calculation attempted acquisition")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)


def test_actual_source_to_b1_preserves_original_order_reference_and_exact_fields(submitted, monkeypatch):
    s = submitted
    assert s.driver.custody.content(s.context, s.binding) == s.raw
    assert s.driver.custody.evidence(s.context, s.evidence) == s.task["submitted_parameters"]
    case = submitted_case(s)
    actual = provider.index_original_inputs
    calls = []
    def record(*args, **kwargs):
        result = actual(*args, **kwargs)
        calls.append(deepcopy((args, kwargs, result)))
        return result
    monkeypatch.setattr(provider, "index_original_inputs", record)
    result = consume(case)
    assert len(calls) == 1 and result["sheet"]["input_index_result"] == calls[0][2]
    index = result["sheet"]["input_index_result"]["value"]
    assert result["sheet"]["input_index_result"]["status"] == "ok"
    assert index["reference_original_index"] == 2
    assert [row["original_index"] for row in index["inputs"]] == [2, 1, 3]
    assert [row["value"] for row in index["inputs"]] == [s.task["submitted_parameters"]["user_genomes"][i] for i in [1, 0, 2]]
    assert [row["expected_track_key"] for row in index["inputs"]] == ["ref_genome", "comp_genome_1", "comp_genome_2"]
    for row in index["inputs"]:
        assert row["source_field"]["source_ref"] == s.task["submission_source_ref"]
        assert row["source_field"]["sha256"] == s.binding["sha256"]
        assert row["source_field"]["pointer"] == PARAMETER_POINTER + row["parameter_pointer"]
    snapshots = index["run_parameter_snapshots"]
    assert len(snapshots) == 1 and snapshots[0]["kind"] == "submitted"
    assert snapshots[0]["min_ident"]["value"] == .1
    assert snapshots[0]["max_e_val"]["source_field"]["pointer"] == PARAMETER_POINTER + "/max_e_val"
    outcome = next(r for r in result["sheet"]["input_resolution"] if r["selector_kind"] == "original_input_index")
    assert outcome["content"] == s.binding and outcome["state"] == "resolved"
    assert result["sheet"]["original_task"] == s.task
    assert "proteome_parameter_source_unbound" not in codes(result)
    assert_native_means(result)
    assert len(s.driver.client.calls) == 1


@pytest.mark.parametrize("change,code", [
    ("binding_missing", "proteome_parameter_source_unbound"),
    ("bytes_missing", "proteome_input_bytes_missing"),
    ("source", "proteome_parameter_source_conflict"),
    ("source_binding", "proteome_parameter_source_unbound"),
    ("source_digest", "proteome_parameter_source_conflict"),
    ("bytes_digest", "proteome_artifact_digest_mismatch"),
    ("length", "proteome_artifact_digest_mismatch"),
    ("artifact", "proteome_parameter_source_conflict"),
    ("field", "proteome_parameter_source_unbound"),
    ("pointer", "proteome_parameter_source_conflict"),
    ("request_copy_pointer", "proteome_parameter_source_conflict"),
    ("snapshot_copy_pointer", "proteome_parameter_source_conflict"),
])
def test_missing_and_conflicting_submitted_sources_preserve_independent_native_values(submitted, change, code):
    case = submitted_case(submitted)
    binding, source = request_binding(case), selected_source(case)
    if change == "binding_missing":
        case["bundle"]["supplied_contents"].remove(binding)
    elif change == "bytes_missing":
        case["artifact_bytes"].pop(binding["artifact_ref"])
    elif change == "source":
        source["source_ref"] = "wrong-submission-source"
    elif change == "source_binding":
        binding["source_ref"] = "wrong-submission-source"
    elif change == "source_digest":
        source["sha256"] = "0" * 64
    elif change == "bytes_digest":
        case["artifact_bytes"][binding["artifact_ref"]] += b" "
    elif change == "length":
        binding["byte_count"] += 1
    elif change == "artifact":
        binding["artifact_ref"] = "artifact_alias"
    elif change == "field":
        binding["artifact_field"] = "artifact_ref"
    else:
        source["pointer"] = {"pointer": "/parameters", "request_copy_pointer": "/prepared/native_operands/request/parameters",
                             "snapshot_copy_pointer": "/snapshot/request/rpc/params/1"}[change]
    sync_supplied(case)
    result = consume(case)
    assert result["sheet"]["input_index_result"] is None and code in codes(result)
    assert_native_means(result)


@pytest.mark.parametrize("change", ["version", "extra", "origin_operation", "prepared_operation", "operation_key",
    "request_parameters", "rpc_method", "rpc_version", "rpc_id", "rpc_value", "rpc_start",
    "snapshot_request", "snapshot_shape", "transport_digest", "preparation", "effect"])
def test_pure_retained_wrapper_validation_rejects_corrupt_native_shapes(submitted, change):
    case = submitted_case(submitted)
    record = deepcopy(submitted.retained)
    prepared = record["prepared"]
    rpc = prepared["native_operands"]["call"]["rpc_request"]
    if change == "version":
        record["version"] = "wrong-version"
    elif change == "extra":
        record["parameters"] = deepcopy(submitted.task["submitted_parameters"])
    elif change == "origin_operation":
        record["origin"]["name"] = "api.bvbrc_appservice.status"
    elif change == "prepared_operation":
        prepared["operation"] = "api.bvbrc_appservice.status"
    elif change == "operation_key":
        record["origin"]["operation_key"] += "0"
    elif change == "request_parameters":
        prepared["native_operands"]["request"]["parameters"]["reference_genome_index"] = 1
    elif change == "rpc_method":
        rpc["method"] = "AppService.query_tasks"
    elif change == "rpc_version":
        rpc["version"] = "2.0"
    elif change == "rpc_id":
        rpc["id"] += "wrong"
    elif change == "rpc_value":
        rpc["params"][1]["reference_genome_index"] = 1
    elif change == "rpc_start":
        rpc["params"][2]["workspace"] = "different"
    elif change == "snapshot_request":
        record["snapshot"]["request"]["rpc"]["method"] = "AppService.query_tasks"
    elif change == "snapshot_shape":
        record["snapshot"].pop("content_ref")
    elif change == "transport_digest":
        record["snapshot"]["transport"]["request"]["body_sha256"] = "0" * 64
    elif change == "preparation":
        prepared["bound_inputs"]["resolved"]["preparation"]["native_parameters"]["reference_genome_index"] = 1
    else:
        prepared["effects"][0]["payload_sha256"] = "0" * 64
    replace_request_bytes(case, c.canonical(record).encode())
    result = consume(case)
    assert result["sheet"]["input_index_result"] is None and "proteome_parameter_source_conflict" in codes(result)
    assert_native_means(result)


@pytest.mark.parametrize("raw_kind", ["whitespace", "duplicate_member", "truncated", "response_echo"])
def test_malformed_record_and_equal_response_echo_are_not_submitted_parameter_evidence(submitted, raw_kind):
    case = submitted_case(submitted)
    raw = {"whitespace": submitted.raw + b"\n",
           "duplicate_member": b'{"version":"bvbrc_appservice_native_source_v1",' + submitted.raw[1:],
           "truncated": submitted.raw[:-1], "response_echo": submitted.snapshot.content}[raw_kind]
    replace_request_bytes(case, raw)
    result = consume(case)
    assert result["sheet"]["input_index_result"] is None and "proteome_parameter_source_conflict" in codes(result)
    assert_native_means(result)


def test_equal_response_echo_with_actual_response_binding_remains_unbound(submitted):
    case = submitted_case(submitted)
    case["bundle"]["supplied_contents"].remove(request_binding(case))
    evidence = submitted.task["scheduler_returned_parameters"]["evidence"]
    assert submitted.driver.custody.evidence(submitted.context, evidence) == submitted.task["submitted_parameters"]
    case["bundle"]["supplied_contents"].append(deepcopy(evidence["content"]))
    case["artifact_bytes"][evidence["content"]["artifact_ref"]] = submitted.snapshot.content
    selected_source(case).update(sha256=evidence["content"]["sha256"], pointer=evidence["pointer"])
    sync_supplied(case)
    result = consume(case)
    assert result["sheet"]["input_index_result"] is None and "proteome_parameter_source_unbound" in codes(result)
    assert_native_means(result)


@pytest.mark.parametrize("later_state", ["failed_task", "incomplete_response"])
def test_newer_failed_or_partial_response_does_not_replace_original_submission(tmp_path, later_state):
    s = retained_submission(tmp_path)
    try:
        d = s.driver
        receiving = d.results(s.handoff)
        d.client.value = {"123": {"id": "123", "app": "GenomeComparison", "status": "failed",
                                   "parameters": deepcopy(s.task["submitted_parameters"])}}
        original_rpc = d.client.rpc
        def later_response(rpc):
            snapshot = original_rpc(rpc)
            transport = deepcopy(snapshot.transport)
            if later_state == "incomplete_response":
                transport["body_complete"] = False
            return replace(snapshot, retrieved_at="2026-10-25T12:00:00+00:00", transport=transport)
        d.client.rpc = later_response
        observed = d.call("status", {"handoff_ref": s.handoff["source_ref"]}, context=receiving)
        common = observed["value"] if observed["contract"] == "CommonReceipt" else observed["value"]["receipt"]
        later = common["snapshot"]["content"]
        later_raw = d.custody.content(receiving, later)
        assert common["snapshot"]["retrieved_at"] > s.snapshot.retrieved_at
        assert later["source_ref"] != s.task["submission_source_ref"]
        if later_state == "failed_task":
            assert observed["contract"] == "TaskObservation" and observed["value"]["state"] == "failed"
        else:
            assert observed["contract"] == "CommonReceipt" and common["status"] == "failed"
        case = submitted_case(s)
        case["bundle"]["supplied_contents"].append(deepcopy(later))
        case["artifact_bytes"][later["artifact_ref"]] = later_raw
        valid = consume(case)
        assert valid["sheet"]["input_index_result"]["value"]["parameter_source"]["source_field"]["source_ref"] == s.task["submission_source_ref"]
        selected_source(case).update(source_ref=later["source_ref"], sha256=later["sha256"], pointer="/result/0/123/parameters")
        sync_supplied(case)
        rejected = consume(case)
        assert rejected["sheet"]["input_index_result"] is None and "proteome_parameter_source_conflict" in codes(rejected)
        assert_native_means(rejected)
        assert d.records.read(s.handoff["source_ref"])["value"]["original_task"] == s.task
        assert len(d.client.calls) == 2
    finally:
        s.store.close()


@pytest.mark.parametrize("field,value", [("resource_id", "unrelated-resource"), ("submission_operation_key", "unrelated-operation"),
    ("submitted_start_parameters", {"workspace": "unrelated"})])
def test_pure_original_task_correspondence_checks_available_wrapper_fields(submitted, field, value):
    case = submitted_case(submitted)
    case["bundle"]["original_task"][field] = value
    result = consume(case)
    assert result["sheet"]["input_index_result"] is None and "proteome_parameter_source_conflict" in codes(result)
    assert_native_means(result)


def test_task_id_is_preserved_and_still_requires_independent_host_authentication(submitted):
    case = submitted_case(submitted)
    # No response body is required by the parameter decoder. Make explicit what
    # this pure supplied-data boundary cannot prove; host rejection is tested in
    # test_bvbrc_appservice_request_content using the actual retained response.
    case["bundle"]["original_task"]["task_id"] = "456"
    for row in case["bundle"]["artifacts"]:
        row["task_association"]["task_id"] = "456"
    result = consume(case)
    assert result["sheet"]["original_task"]["task_id"] == "456"
    assert result["sheet"]["input_index_result"]["value"] is not None
    assert submitted.driver.api.appservice.read_handoff(submitted.handoff["source_ref"])["task_handoff"]["original_task"]["task_id"] == "123"


def test_exact_duplicate_parameter_descriptions_do_not_duplicate_index(submitted):
    case = submitted_case(submitted)
    selected = case["supplied_values"][0]["value"]["original_input_index"]
    selected["additional_parameter_sources"].append(deepcopy(selected["parameter_source"]))
    sync_supplied(case)
    result = consume(case)
    assert len(result["sheet"]["input_index_result"]["value"]["run_parameter_snapshots"]) == 1
    assert len(result["sheet"]["input_index_result"]["value"]["inputs"]) == 3
    assert_native_means(result)


@pytest.mark.parametrize("conflicting", [False, True])
def test_duplicate_same_field_bindings_are_closed_bundle_errors(submitted, conflicting):
    case = submitted_case(submitted)
    changed = deepcopy(request_binding(case))
    if conflicting:
        changed["byte_count"] += 1
    case["bundle"]["supplied_contents"].append(changed)
    with pytest.raises(c.ProteomeBundleError, match="proteome_bundle_invalid"):
        provider.consume_bundle(**case)


def test_effective_selection_and_submitted_threshold_provenance_remain_separate(submitted):
    case = submitted_case(submitted)
    selected = case["supplied_values"][0]["value"]["original_input_index"]
    selected["additional_parameter_sources"] = [deepcopy(selected["parameter_source"])]
    # An explicit synthetic effective-parameter record tests this conditional
    # pure path. The actual host handoff still has effective_parameters=None.
    params = {**deepcopy(submitted.task["submitted_parameters"]), "min_ident": .5}
    raw = c.canonical({"effective": params}).encode()
    sha = hashlib.sha256(raw).hexdigest()
    content = dict(source_ref="synthetic-effective-record", artifact_field="artifact_ref", artifact_ref="artifact_" + sha,
                   sha256=sha, byte_count=len(raw))
    evidence = dict(content=content, pointer="/effective")
    case["bundle"]["original_task"]["effective_parameters"] = dict(value=params, evidence=evidence)
    case["bundle"]["supplied_contents"].append(content)
    case["artifact_bytes"][content["artifact_ref"]] = raw
    case["supplied_values"].append(dict(evidence=evidence, value=params))
    selected["parameter_source"] = dict(kind="effective", source_field=dict(source_ref=content["source_ref"], sha256=sha,
        pointer="/effective", row_ordinal=None, field_name=None))
    sync_supplied(case)
    result = consume(case)
    index = result["sheet"]["input_index_result"]["value"]
    assert index["parameter_source"]["kind"] == "effective"
    assert [(row["kind"], row["min_ident"]["value"]) for row in index["run_parameter_snapshots"]] == [("submitted", .1), ("effective", .5)]
    assert index["run_parameter_snapshots"][0]["source_field"]["source_ref"] == submitted.task["submission_source_ref"]
    assert submitted.task["effective_parameters"] is None
    assert_native_means(result)


def test_request_and_response_fields_of_same_actual_source_are_distinct(submitted):
    case = submitted_case(submitted)
    response = deepcopy(submitted.handoff["value"]["receipt"]["snapshot"]["content"])
    case["bundle"]["supplied_contents"].append(response)
    case["artifact_bytes"][response["artifact_ref"]] = submitted.snapshot.content
    supplied = case["supplied_values"][0]["value"]
    extra = deepcopy(supplied["genome_snapshots"][0])
    extra.update(snapshot_key="response-is-not-genome-data", source=dict(kind="supplied_snapshot", content=response, completeness_evidence=None))
    supplied["genome_snapshots"].append(extra)
    sync_supplied(case)
    result = consume(case)
    assert result["sheet"]["input_index_result"]["value"] is not None
    assert result["sheet"]["genome_results"][-1]["status"] == "invalid"
    assert "proteome_supplied_source_conflict" not in codes(result)
    assert_native_means(result)


def test_saved_submitted_sheet_recalculates_without_source_store_network_or_constructor(submitted, monkeypatch):
    case = submitted_case(submitted)
    result = consume(case)
    before = deepcopy(result)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved calculation attempted acquisition or construction")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(submitted.store, "get_artifact", forbidden)
    for name in ("parse_genome_comparison", "index_original_inputs", "build_native_joins", "build_native_sheet"):
        monkeypatch.setattr(provider, name, forbidden)
    native_sheet = result["sheet"]["native_sheet_result"]["value"]
    revised = calculate_native_components(native_sheet, parameters={**case["parameters"]["calculation_parameters"], "minimum_identity_fraction": .9})
    assert revised["value"]["tracks"][0]["selection_counts"]["pass"]["value"] == 0
    assert revised["value"]["sheet_sha256"] == result["components"]["value"]["sheet_sha256"]
    checked = validate_saved_projection(result["sheet"], result["components"], facts=result["facts"], status=result["status"],
        missing_requirements=tuple(result["missing_requirements"]), diagnostics=tuple(result["diagnostics"]),
        requested_form=case["requested_form"], parameters=case["parameters"], original_task=case["bundle"]["original_task"],
        bundle_sha256=c.digest(case["bundle"]))
    assert checked["facts"] == result["facts"] and result == before


@pytest.mark.parametrize("field,value", [("artifact_field", "artifact_ref"), ("sha256", "0" * 64)])
def test_saved_submitted_resolution_content_cannot_be_relabelled(submitted, field, value):
    saved = consume(submitted_case(submitted))["sheet"]
    row = next(r for r in saved["input_resolution"] if r["selector_kind"] == "original_input_index")
    row["content"][field] = value
    with pytest.raises(c.ProteomeBundleError, match="saved_identity_conflict"):
        c.validate_provider_sheet(saved)


def test_saved_submitted_pointer_cannot_be_consistently_relabelled(submitted):
    saved = consume(submitted_case(submitted))["sheet"]
    # Change every duplicated pointer consistently, preserving schema/relative
    # child-field checks; the exact retained request location must still hold.
    saved = json.loads(c.canonical(saved).replace(PARAMETER_POINTER, "/parameters"))
    with pytest.raises(c.ProteomeBundleError, match="saved_identity_conflict"):
        c.validate_provider_sheet(saved)
