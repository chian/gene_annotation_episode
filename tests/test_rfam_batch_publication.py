"""Real Store publication of retained Rfam bytes and qualified counterexamples.

No HTTP or scientific program is run. The single native response/submission are
unchanged retained captures, with a fresh local service operand binding. Batch
service tests deliberately adapt names/job IDs and are synthetic fixtures; they
do not claim the old native submission used the new generated-name contract.
"""
from copy import deepcopy
from dataclasses import replace
import base64
import hashlib
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.api_rfam import RfamBatchService
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.rfam_batch_contracts import RFAM_CALCULATION_PARAMETERS
from gene_annotation_episode.rfam_batch_grader import calculate_rfam_batch_components
from gene_annotation_episode.rfam_batch_publication import publish_rfam_batch_result
from gene_annotation_episode.rfam_discovery import BASE_URL, result_url
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "verification/tool_graders_rfam_transport_2026-10-26_234/live"
RESULT_FIELDS = {"source_ref", "submission_source_ref", "artifact_ref", "format",
    "sheet_ref", "calculation_ref", "projection", "projection_errors", "grading_source_ref"}
MANIFEST_FIELDS = {"version", "request", "selector", "source_ref", "submission_source_ref",
    "artifact_ref", "input_identity", "format", "parse_ref", "sheet_ref", "calculation_ref",
    "projection", "projection_errors", "parse_digest", "sheet_schema", "sheet_digest",
    "calculation_schema", "calculation_digest"}


@pytest.fixture(autouse=True)
def no_external_operations(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Publication must not acquire, execute or wait")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr("time.sleep", forbidden)


def retained_snapshot(mode, action):
    directory = LIVE / mode / action
    record = json.loads((directory / "snapshot.json").read_text())
    content = (directory / "response.body").read_bytes()
    assert hashlib.sha256(content).hexdigest() == record.pop("content_sha256")
    return SourceSnapshot(**record, content=content)


class RetainedSingle:
    """Transport seam returning saved bytes; calls are fixture reads, not HTTP."""
    timeout = 90

    def __init__(self):
        self.calls = []

    def submit(self, sequence):
        self.calls.append("retained_submission")
        snapshot = retained_snapshot("single", "001-submit")
        assert hashlib.sha256(sequence.encode("ascii")).hexdigest() == snapshot.request["sequence_sha256"]
        return snapshot

    def result(self, job_id, *, representation):
        self.calls.append("retained_result:" + representation)
        action = {"json": "003-fetch-json", "tblout": "004-fetch-tblout", "out": "005-fetch-out"}[representation]
        snapshot = retained_snapshot("single", action)
        assert job_id == snapshot.request["job_id"]
        return snapshot


def selection(*metrics, family="hit", representation="json", projection=True, version=1, rows=None):
    return {"version": "rfam_batch_result_selector_v" + str(version),
        "representation": representation, "model_metadata_ref": None,
        "projection": {"family": family, "rows": rows or {"offset": 0, "limit": 12},
            "metrics": list(metrics or ("native_score_bits", "native_evalue", "query_span_fraction"))}
        if projection else None}


@pytest.fixture
def single(tmp_path):
    native = json.loads(retained_snapshot("single", "003-fetch-json").content)
    inputs = tmp_path / "original-inputs.fa"
    inputs.write_text(">selected\n" + native["searchSequence"] + "\n>outside_selected_scope\nACGT\n")
    with Store(tmp_path / "state") as store:
        subject, outside = store.create_problem(inputs, molecule="dna")["subject_refs"]
        client = RetainedSingle()
        tools = ToolRegistry(store, clients=client)
        service = RfamBatchService(tools, client=client)
        scope = {"subject_refs": [subject]}
        request = {"version": "rfam_batch_request_v1", "mode": "single_sequence", "subject_ref": subject}
        prepared = service.prepare("api.rfam.submit", request, {}, scope=scope, previous_events=[])
        submission = service.invoke(prepared)
        handle = service.decode(prepared, submission)["native_handle"]
        prepared = service.prepare("api.rfam.fetch", request, {}, scope=scope, previous_events=[],
            handle=handle, selector=selection())
        snapshot = service.invoke(prepared)
        yield SimpleNamespace(store=store, tools=tools, service=service, request=request,
            scope=scope, handle=handle, submission=submission, snapshot=snapshot, client=client,
            original_source_count=store.count("source"), outside_subject=outside)


def publish(h, selected=None, *, snapshot=None, key="publication", submission=None, handle=None):
    return publish_rfam_batch_result(h.tools, request=h.request, selector=selected or selection(),
        snapshot=snapshot or h.snapshot, scope=h.scope, operation_key=key,
        submission_snapshot=submission or h.submission, handle=handle or h.handle)


def saved(h, outcome):
    result = outcome["result"]
    manifest = json.loads(h.store.get_artifact(h.store.get(result["grading_source_ref"])["artifact_ref"]))
    parsed = json.loads(h.store.get_artifact(manifest["parse_ref"]))
    sheet = None if result["sheet_ref"] is None else json.loads(h.store.get_artifact(result["sheet_ref"]))
    calc = None if result["calculation_ref"] is None else json.loads(h.store.get_artifact(result["calculation_ref"]))
    return manifest, parsed, sheet, calc


def synthetic(h, body=None, *, complete=True, status=200):
    content = canonical(body).encode() if body is not None and not isinstance(body, bytes) else body
    return replace(h.snapshot, content=h.snapshot.content if content is None else content,
        transport={**h.snapshot.transport, "evidence_kind": "synthetic_fixture",
            "body_complete": complete, "status": status})


def values(outcome, index=0):
    row = outcome["result"]["projection"]["rows"][index]
    return {cell["name"]: cell["value"] for cell in row["measured"]}


def test_retained_native_service_inputs_three_sources_full_values_and_alignment(single):
    h = single
    selected = selection("native_score_bits", "native_evalue", "native_gc_fraction", "query_span_nt",
        "query_span_fraction", "represented_model_positions", "model_coverage_fraction",
        "model_consensus_equal_count", "model_consensus_compared_count")
    outcome = h.service.publish(h.request, selected, h.snapshot, h.scope, "retained-native",
        submission_snapshot=h.submission, handle=h.handle)
    assert outcome["status"] == "completed", outcome
    assert set(outcome["result"]) == RESULT_FIELDS
    result = outcome["result"]
    assert outcome["record_refs"] == [result["submission_source_ref"], result["source_ref"], result["grading_source_ref"]]
    assert outcome["changed_record_refs"] == outcome["record_refs"]
    original, source, grading = [h.store.get(ref) for ref in outcome["record_refs"]]
    assert original["origin"] == source["origin"] == "external"
    assert grading["origin"] == "tool" and grading["provider"] == "rfam_batch.grading"
    assert source["parent_source_refs"] == [original["id"]]
    assert grading["parent_source_refs"] == [original["id"], source["id"]]
    assert h.store.get_artifact(original["artifact_ref"]) == h.submission.content
    assert h.store.get_artifact(source["artifact_ref"]) == h.snapshot.content
    manifest, parsed, sheet, calc = saved(h, outcome)
    assert set(manifest) == MANIFEST_FIELDS and parsed["sheet"] == sheet
    assert sheet["source_context"]["capture"]["evidence_kind"] == "native_response"
    assert manifest["input_identity"] == sheet["source_context"]["input_identity"]
    assert manifest["request"] == h.request and manifest["selector"] == selected
    assert calc["parameters"] == {"hit_scope": "reported"}
    assert calculate_rfam_batch_components(sheet, parameters=RFAM_CALCULATION_PARAMETERS) == calc
    measured = values(outcome)
    assert measured["native_score_bits"] == 104.6 and measured["native_evalue"] == 1.4e-24
    assert measured["native_gc_fraction"] == 0.49 and measured["native_gc_fraction"] != 58 / 119
    assert measured["query_span_nt"] == 119 and measured["query_span_fraction"] == 1
    assert measured["represented_model_positions"] == 120
    component = sheet["hits"][0]["correspondence"]
    assert component["query_insert_count"] == 1 and component["model_delete_count"] == 2
    assert len(component["paired_positions"]) == measured["model_consensus_compared_count"] == 118
    native = json.loads(h.snapshot.content)["hits"]["5S_rRNA"][0]["alignment"]
    pairs = [(a.upper().replace("T", "U"), b.upper().replace("T", "U"))
        for a, b in zip(native["hit_seq"].split()[2], native["user_seq"].split()[2])
        if a.upper() in "ACGTU" and b.upper() in "ACGTU"]
    assert measured["model_consensus_equal_count"] == sum(a == b for a, b in pairs)
    assert sheet["hits"][0]["source_details"]["alignment_identity"]["raw_alignment_ref"] == {"artifact_ref": result["artifact_ref"],
        "json_pointer": "/hits/5S_rRNA/0/alignment"}
    assert result["projection"]["rows"][0]["unavailable"] == [
        {"name": "model_coverage_fraction", "reason": "model_length_unavailable"}]
    assert h.store.count("observation") == h.store.count("reference") == 0
    assert h.store.db.execute("SELECT count(*) FROM provider_jobs").fetchone()[0] == 0
    assert h.client.calls == ["retained_submission", "retained_result:json"]


def test_exact_original_replay_does_not_reparse_and_changed_selector_cannot_reuse_key(single, monkeypatch):
    h = single
    first = publish(h)
    def forbidden(*args, **kwargs):
        pytest.fail("replay reparsed original data")
    monkeypatch.setattr("gene_annotation_episode.rfam_batch_publication.populate_rfam_batch_json_sheet", forbidden)
    assert publish(h) == first
    assert h.store.count("source") == h.original_source_count + 3
    with pytest.raises(ContractError, match="operation_key_reused_for_different_work"):
        publish(h, selection("query_span_fraction"))
    with pytest.raises(ContractError, match="operation_key_reused_for_different_work"):
        publish(h, submission=replace(h.submission, retrieved_at="2026-10-26T09:00:00+00:00"))


def test_saved_store_reopens_and_recalculates_without_acquisition_or_republication(single):
    h = single
    outcome = publish(h)
    _, _, original_sheet, original_calculation = saved(h, outcome)
    with Store(h.store.path) as reopened:
        sheet = json.loads(reopened.get_artifact(outcome["result"]["sheet_ref"]))
        assert sheet == original_sheet
        assert calculate_rfam_batch_components(sheet, parameters=RFAM_CALCULATION_PARAMETERS) == original_calculation
        registry = ToolRegistry(reopened, clients=h.client)
        replay = publish_rfam_batch_result(registry, request=h.request, selector=selection(),
            snapshot=h.snapshot, scope=h.scope, operation_key="publication",
            submission_snapshot=h.submission, handle=h.handle)
        assert replay == outcome
        assert reopened.count("source") == h.original_source_count + 3
    assert h.client.calls == ["retained_submission", "retained_result:json"]


@pytest.mark.parametrize("mutation", ["submission_operand", "submission_handle", "result_operand", "result_job", "result_url"])
def test_wrong_original_custody_rejected_before_publication(single, mutation):
    h = single
    submission, snapshot = h.submission, h.snapshot
    if mutation == "submission_operand":
        submission = replace(submission, request={**submission.request, "input_operand": {}})
    elif mutation == "submission_handle":
        job = h.handle["job_id"] + "OTHER"
        submission = replace(submission, content=canonical({"jobId": job, "resultURL": result_url(job)}).encode())
    elif mutation == "result_operand":
        snapshot = replace(snapshot, request={**snapshot.request, "input_operand": {}})
    elif mutation == "result_job":
        snapshot = replace(snapshot, request={**snapshot.request, "job_id": h.handle["job_id"] + "OTHER"})
    else:
        snapshot = replace(snapshot, url=snapshot.url + "/out")
    with pytest.raises(ValueError):
        publish(h, submission=submission, snapshot=snapshot)
    assert h.store.count("source") == h.original_source_count
    assert h.store.count("observation") == 0


@pytest.mark.parametrize("mutation,code", [("job", "rfam_result_job_identity_conflict"),
    ("query", "rfam_result_sequence_identity_conflict"), ("empty", "rfam_result_sequence_identity_empty"),
    ("malformed", "rfam_json_invalid"), ("duplicates", "rfam_json_duplicate_key")])
def test_rejected_scientific_identity_preserves_all_native_sources(single, mutation, code):
    h = single
    body = json.loads(h.snapshot.content)
    if mutation == "job":
        body["jobId"] += "OTHER"
    elif mutation == "query":
        body["searchSequence"] = "A" * 119
    elif mutation == "empty":
        body.update(searchSequence="", numHits=0, hits={})
    elif mutation == "malformed":
        body = b'{"not complete'
    else:
        body = b'{"jobId":1,"jobId":2}'
    snapshot = synthetic(h, body)
    outcome = publish(h, snapshot=snapshot)
    assert outcome["status"] == "partial", outcome
    manifest, parsed, sheet, calculation = saved(h, outcome)
    assert sheet is calculation is outcome["result"]["projection"] is None
    assert parsed["status"] == "rejected"
    assert code in {item["code"] for item in outcome["result"]["projection_errors"]}
    assert h.store.get_artifact(outcome["result"]["artifact_ref"]) == snapshot.content
    assert set(manifest) == MANIFEST_FIELDS and len(outcome["record_refs"]) == 3
    artifact_only = publish(h, selection(projection=False), snapshot=snapshot, key="artifact-only")
    assert artifact_only["status"] == "completed" and artifact_only["result"]["projection_errors"] == []


def test_complete_empty_has_zero_reported_rows_and_both_strands(single):
    body = json.loads(single.snapshot.content)
    body.update(numHits=0, hits={})
    snapshot = synthetic(single, body)
    outcome = publish(single, snapshot=snapshot)
    assert outcome["status"] == "completed" and outcome["result"]["projection"]["rows"] == []
    empty = publish(single, selection("query_strand_union_span_nt", "query_strand_union_fraction",
        family="query_strand"), snapshot=snapshot, key="empty-strands")
    assert empty["result"]["projection"]["population_complete"]
    assert [values(empty, i) for i in range(2)] == [
        {"query_strand_union_span_nt": 0, "query_strand_union_fraction": 0},
        {"query_strand_union_span_nt": 0, "query_strand_union_fraction": 0}]


def test_partial_population_and_invalid_optional_cells_are_accurate_delivered_returns(single):
    h = single
    body = json.loads(h.snapshot.content)
    body["numHits"] = 2
    body["hits"]["5S_rRNA"][0].update(score="bad", start=0, alignment="unsupported display")
    outcome = publish(h, selection("native_score_bits", "native_evalue", "query_span_fraction",
        "represented_model_positions", "model_coverage_fraction"), snapshot=synthetic(h, body))
    assert outcome["status"] == "completed" and outcome["result"]["projection_errors"] == []
    _, parsed, sheet, _ = saved(h, outcome)
    assert parsed["status"] == "partial" and sheet["source_context"]["capture"]["evidence_kind"] == "synthetic_fixture"
    assert not outcome["result"]["projection"]["population_complete"]
    assert values(outcome) == {"native_evalue": 1.4e-24}
    unavailable = {row["name"]: row["reason"] for row in outcome["result"]["projection"]["rows"][0]["unavailable"]}
    assert unavailable["native_score_bits"] == "invalid_native_value"
    assert unavailable["query_span_fraction"] == "coordinates_invalid"
    assert unavailable["represented_model_positions"] == "alignment_conflict"


def test_preview_does_not_truncate_saved_rows_and_foreign_requested_key_is_partial(single):
    h = single
    body = json.loads(h.snapshot.content)
    body["hits"]["5S_rRNA"] *= 3
    body["numHits"] = 3
    snapshot = synthetic(h, body)
    outcome = publish(h, selection(rows={"offset": 1, "limit": 1}), snapshot=snapshot)
    _, _, sheet, calc = saved(h, outcome)
    assert len(sheet["hits"]) == len(calc["hits"]) == 3
    assert len({row["hit_id"] for row in sheet["hits"]}) == 3
    assert calc["sequence_populations"][0]["exact_source_duplicate_row_count"] == 2
    assert outcome["result"]["projection"]["rows"][0]["record_key"] == sheet["hits"][1]["hit_id"]
    assert outcome["result"]["projection"]["more_rows"]
    wrong = publish(h, selection(rows={"record_keys": ["foreign:hit"]}), snapshot=snapshot, key="wrong-key")
    assert wrong["status"] == "partial" and wrong["result"]["sheet_ref"]
    assert wrong["result"]["projection_errors"][0]["code"] == "rfam_projection_reference_conflict"


@pytest.mark.parametrize("body", [None, b'{"truncated'])
def test_incomplete_body_is_partial_but_preserves_usable_cells_and_bytes(single, body):
    snapshot = synthetic(single, body, complete=False)
    outcome = publish(single, snapshot=snapshot)
    assert outcome["status"] == "partial"
    assert "rfam_response_body_incomplete" in {e["code"] for e in outcome["result"]["projection_errors"]}
    assert single.store.get_artifact(outcome["result"]["artifact_ref"]) == snapshot.content
    if body is None:
        assert values(outcome)["native_score_bits"] == 104.6
        assert not outcome["result"]["projection"]["population_complete"]


@pytest.mark.parametrize("representation", ["tblout", "out"])
def test_single_text_artifact_only_never_invents_query_mapping(single, representation):
    h = single
    selected = selection(representation=representation, projection=False)
    prepared = h.service.prepare("api.rfam.fetch", h.request, {}, scope=h.scope,
        previous_events=[], handle=h.handle, selector=selected)
    snapshot = h.service.invoke(prepared)
    outcome = publish(h, selected, snapshot=snapshot)
    assert outcome["status"] == "completed" and outcome["result"]["sheet_ref"] is None
    assert h.store.get_artifact(outcome["result"]["artifact_ref"]) == snapshot.content
    if representation == "tblout":
        requested = publish(h, selection("native_score_bits", representation="tblout", version=2),
            snapshot=snapshot, key="numeric-single-table")
        assert requested["status"] == "partial"
        assert requested["result"]["projection_errors"][0]["code"] == "rfam_text_format_unverified"


def caller_source(store, value, *, provider="controlled_metadata", operand_refs=(), parent_source_refs=(),
        query_selection_ref=None):
    artifact = store.artifact(canonical(value), "application/json")
    return store.put("source", {"provider": provider, "accession": None, "uri": None,
        "artifact_ref": artifact, "text_ref": None, "request_ref": None,
        "version": None, "retrieved_at": None, "operand_refs": list(operand_refs),
        "parent_source_refs": list(parent_source_refs),
        **({"query_selection_ref": query_selection_ref} if query_selection_ref is not None else {})}, origin="caller")


def test_selected_metadata_is_retained_with_real_source_lineage_but_unbound(single):
    h = single
    original = caller_source(h.store, {"model_length_positions": 120})
    bundle = {"version": "rfam_model_metadata_v1", "records": [{
        "metadata_ref": original["artifact_ref"], "source_ref": original["id"],
        "accession": "RF00001", "model_name": "5S_rRNA", "model_length_positions": 120,
        "model_sha256": None, "model_release": "explicit_fixture_release"}], "bindings": []}
    selected_source = caller_source(h.store, bundle)
    selected = selection("model_coverage_fraction", "native_score_bits")
    selected["model_metadata_ref"] = selected_source["id"]
    outcome = publish(h, selected)
    assert outcome["status"] == "completed"
    assert saved(h, outcome)[2]["source_context"]["supplied_model_metadata"] == bundle
    assert selected_source["id"] in h.store.get(outcome["result"]["grading_source_ref"])["parent_source_refs"]
    assert outcome["result"]["projection"]["rows"][0]["unavailable"] == [
        {"name": "model_coverage_fraction", "reason": "model_binding_unverified"}]
    selected["model_metadata_ref"] = selected_source["artifact_ref"]
    invalid = publish(h, selected, key="not-source")
    assert invalid["status"] == "completed" and values(invalid)["native_score_bits"] == 104.6
    assert selected["model_metadata_ref"] not in h.store.get(invalid["result"]["grading_source_ref"])["parent_source_refs"]
    assert invalid["result"]["projection"]["rows"][0]["unavailable"] == [
        {"name": "model_coverage_fraction", "reason": "model_metadata_conflict"}]


@pytest.mark.parametrize("case", ["absent", "invalid_bundle", "invalid_inner_record", "wrong_evidence", "unreadable"])
def test_invalid_optional_metadata_preserves_native_measurements_and_failure(single, case):
    h = single
    retained = case != "absent"
    if case == "absent":
        reference = "source_" + "0" * 24
    else:
        value = {"version": "invalid_metadata_fixture"}
        if case in {"wrong_evidence", "invalid_inner_record"}:
            value = {"version": "rfam_model_metadata_v1", "bindings": [], "records": [
                {"source_ref": "source_" + "0" * 24, "metadata_ref": "artifact_" + "0" * 64,
                 "accession": "RF00001", "model_name": "5S_rRNA", "model_length_positions": 120,
                 "model_sha256": None, "model_release": None}]}
        if case == "invalid_inner_record":
            original = caller_source(h.store, {"model_length_positions": 120})
            value["records"][0].update(source_ref=original["id"], metadata_ref=original["artifact_ref"],
                model_length_positions="not a measured length")
        source = caller_source(h.store, value)
        reference = source["id"]
        if case == "unreadable":
            sha = h.store.get(source["artifact_ref"])["sha256"]
            (h.store.path / "artifacts" / sha[:2] / sha).write_bytes(b"deliberately corrupted fixture")
    selected = selection("native_score_bits", "model_length_positions", "model_coverage_fraction")
    selected["model_metadata_ref"] = reference
    outcome = publish(h, selected)
    assert outcome["status"] == "completed" and outcome["result"]["projection_errors"] == []
    assert values(outcome) == {"native_score_bits": 104.6}
    assert outcome["result"]["projection"]["rows"][0]["unavailable"] == [
        {"name": "model_length_positions", "reason": "model_metadata_conflict"},
        {"name": "model_coverage_fraction", "reason": "model_metadata_conflict"}]
    manifest, parsed, sheet, _ = saved(h, outcome)
    assert manifest["selector"] == selected and sheet["model_metadata"] is None
    parents = h.store.get(outcome["result"]["grading_source_ref"])["parent_source_refs"]
    assert (reference in parents) == retained
    code = "rfam_source_identity_conflict" if case == "unreadable" else "rfam_model_metadata_conflict"
    field = "model_metadata" if retained else "model_metadata_ref"
    assert any(item["code"] == code and item["scope"] == "metadata" and item["field"] == field
        for item in parsed["issues"])
    assert h.store.get_artifact(outcome["result"]["artifact_ref"]) == h.snapshot.content


@pytest.mark.parametrize("through_parent", [False, True])
def test_out_of_scope_metadata_source_bytes_are_never_read(single, monkeypatch, through_parent):
    h = single
    outside = caller_source(h.store, {"outside_metadata": True}, operand_refs=[h.outside_subject])
    selected_source = (caller_source(h.store, {"version": "invalid_but_must_not_be_read"},
        parent_source_refs=[outside["id"]]) if through_parent else outside)
    real_read = h.store.get_artifact
    def checked(reference):
        if reference in {outside["artifact_ref"], selected_source["artifact_ref"]}:
            pytest.fail("read out-of-scope metadata bytes")
        return real_read(reference)
    monkeypatch.setattr(h.store, "get_artifact", checked)
    selected = selection("native_score_bits", "model_coverage_fraction")
    selected["model_metadata_ref"] = selected_source["id"]
    outcome = publish(h, selected)
    assert outcome["status"] == "completed" and values(outcome)["native_score_bits"] == 104.6
    assert selected_source["id"] not in h.store.get(outcome["result"]["grading_source_ref"])["parent_source_refs"]
    assert any(item["code"] == "rfam_subject_out_of_scope" and item["field"] == "model_metadata_ref"
        for item in saved(h, outcome)[1]["issues"])
    assert outcome["result"]["projection"]["rows"][0]["unavailable"] == [
        {"name": "model_coverage_fraction", "reason": "model_metadata_conflict"}]


def test_metadata_read_selection_scope_is_checked_without_reading_bytes(tmp_path, monkeypatch):
    from gene_annotation_episode import library_targets
    from gene_annotation_episode.rfam_batch_publication import validate_rfam_metadata_source_scope

    reads = tmp_path / "outside-selection.fastq"
    reads.write_text("@original-read\nACGT\n+\nIIII\n")
    manifest = tmp_path / "inputs.json"
    manifest.write_text(canonical({"schema_version": 2, "entries": [
        {"sequence": "ACGT", "format": "raw", "molecule": "dna", "name": "selected"},
        {"path": reads.name, "molecule": "dna", "name": "outside_library"}]}))
    with Store(tmp_path / "state") as store:
        selected, library = store.create_problem(manifest_path=manifest)["subject_refs"]
        choice = library_targets.select(store, library, ordinal_ranges=[{"start": 0, "end": 1}])
        source = caller_source(store, {"outside_metadata": True}, query_selection_ref=choice["id"])
        assert store.roots(source["id"]) == [] and store.roots(choice["id"]) == [library]
        def forbidden(*args, **kwargs):
            pytest.fail("scope validation must not read artifact bytes")
        monkeypatch.setattr(store, "get_artifact", forbidden)
        assert validate_rfam_metadata_source_scope(store, source["id"],
            {"subject_refs": [selected, library]}) == source
        with pytest.raises(ContractError, match="rfam_subject_out_of_scope"):
            validate_rfam_metadata_source_scope(store, source["id"], {"subject_refs": [selected]})


def test_http_failure_keeps_bytes_and_has_specific_partial_result(single):
    snapshot = synthetic(single, b"HOLD", status=503)
    outcome = publish(single, selection(projection=False), snapshot=snapshot)
    assert outcome["status"] == "partial"
    assert outcome["result"]["projection_errors"][0]["code"] == "rfam_http_error"
    assert single.store.get_artifact(outcome["result"]["artifact_ref"]) == b"HOLD"


class SyntheticBatch:
    """Disclosed adaptation of native table names, under a synthetic job ID."""
    timeout = 90
    job = "infernal_cmscan-SYNTHETIC_GENERATED_NAMES"

    def __init__(self):
        self.calls = []
        self.table = retained_snapshot("multi", "004-fetch-tblout").content
        native_job = retained_snapshot("multi", "004-fetch-tblout").request["job_id"]
        self.table = self.table.replace(native_job.encode(), self.job.encode())
        manifest = json.loads((LIVE / "multi/input-manifest.json").read_text())
        for index, record in enumerate(manifest["records"]):
            self.table = self.table.replace(record["original_header"].encode(),
                f"rfam_query_{index:08d}".encode())

    def snapshot(self, action, url, request, content, media_type="application/json"):
        return SourceSnapshot("rfam_batch", url, {"action": action, **request},
            "2026-10-26T00:00:00+00:00", content, media_type,
            {"status": 200, "body_complete": True, "evidence_kind": "synthetic_fixture"})

    def submit_file(self, content, *, filename):
        self.calls.append("synthetic_submission")
        return self.snapshot("submit", BASE_URL + "/submit-job", {"filename": filename,
            "file_base64": base64.b64encode(content).decode("ascii"), "file_bytes": len(content),
            "file_sha256": hashlib.sha256(content).hexdigest()},
            canonical({"jobId": self.job, "resultURL": result_url(self.job)}).encode())

    def result(self, job_id, *, representation):
        assert job_id == self.job
        self.calls.append("synthetic_result:" + representation)
        content = (retained_snapshot("multi", "003-fetch-json").content
            if representation == "json" else self.table)
        return self.snapshot("fetch", result_url(job_id) + ("" if representation == "json" else "/" + representation),
            {"job_id": job_id, "representation": representation}, content,
            "application/json" if representation == "json" else "text/plain")


@pytest.fixture
def batch(tmp_path):
    path = tmp_path / "selected-originals.fa"
    path.write_bytes((LIVE / "multi/input.seq").read_bytes())
    with Store(tmp_path / "state") as store:
        subjects = store.create_problem(path, molecule="dna")["subject_refs"]
        assert len(subjects) == 6
        client = SyntheticBatch()
        tools = ToolRegistry(store, clients=client)
        service = RfamBatchService(tools, client=client)
        scope = {"subject_refs": subjects}
        # Select the first subject again as a seventh distinct input occurrence
        # with no row in the synthetic complete table. Nothing is deduplicated.
        request = {"version": "rfam_batch_request_v2", "mode": "sequence_batch",
            "subject_refs": [*subjects, subjects[0]]}
        prepared = service.prepare("api.rfam.submit", request, {}, scope=scope, previous_events=[])
        submission = service.invoke(prepared)
        handle = service.decode(prepared, submission)["native_handle"]
        selected = selection(representation="tblout", version=2)
        prepared = service.prepare("api.rfam.fetch", request, {}, scope=scope, previous_events=[],
            handle=handle, selector=selected)
        snapshot = service.invoke(prepared)
        yield SimpleNamespace(store=store, tools=tools, service=service, request=request,
            scope=scope, handle=handle, submission=submission, snapshot=snapshot, client=client,
            original_source_count=store.count("source"))


def test_synthetic_generated_batch_service_publication_full_infernal_saved_data(batch):
    from gene_annotation_episode.infernal_search_grader import calculate_infernal_search_scores
    from gene_annotation_episode.rfam_batch_table_grader import calculate_rfam_batch_table_components
    h = batch
    selected = selection("native_score_bits", "native_evalue", "query_span_fraction",
        "model_coverage_fraction", representation="tblout", version=2)
    outcome = h.service.publish(h.request, selected, h.snapshot, h.scope, "synthetic-batch",
        submission_snapshot=h.submission, handle=h.handle)
    assert outcome["status"] == "completed", outcome
    manifest, parsed, sheet, calculation = saved(h, outcome)
    assert parsed["version"] == "rfam_batch_parse_result_v2"
    assert sheet["schema"] == "infernal_search_sheet_v2"
    assert len(sheet["source_context"]["input_identity"]["queries"]) == len(sheet["source_context"]["query_population"]) == 7
    assert len(sheet["hits"]) == len(calculation["hits"]) == 6
    assert sheet["source_context"]["capture"]["evidence_kind"] == "synthetic_fixture"
    assert calculation == calculate_rfam_batch_table_components(parsed, parameters={"hit_scope": "reported"})
    assert calculation == calculate_infernal_search_scores(sheet, parameters={"hit_scope": "reported"})
    projected = outcome["result"]["projection"]
    assert projected["available_row_count"] == projected["selected_row_count"] == 6
    assert [values(outcome, i)["native_score_bits"] for i in range(6)] == [104.6, 104.6, 104.6, 51.3, 95.5, 95.2]
    assert all(values(outcome, i)["query_span_fraction"] == 1 for i in range(6))
    assert all(row["unavailable"] == [{"name": "model_coverage_fraction", "reason": "model_length_unavailable"}]
        for row in projected["rows"])
    first, repeated = projected["rows"][:2]
    assert first["query_occurrence_key"] != repeated["query_occurrence_key"]
    assert projected["rows"][2]["strand"] == "-"
    assert manifest["input_identity"] == sheet["source_context"]["input_identity"]
    assert h.store.get_artifact(outcome["result"]["artifact_ref"]) == h.snapshot.content
    assert h.store.count("observation") == h.store.count("reference") == 0
    assert h.store.db.execute("SELECT count(*) FROM provider_jobs").fetchone()[0] == 0
    assert h.client.calls == ["synthetic_submission", "synthetic_result:tblout"]


def test_batch_complete_input_returns_zero_for_no_hit_occurrence_and_opposite_strands(batch):
    h = batch
    selected = selection("query_length_nt", "selected_row_count", "query_strand_union_span_nt",
        "query_strand_union_fraction", "query_strand_sum_span_nt", "query_strand_overlap_excess_nt",
        family="query_strand", representation="tblout", version=2, rows={"offset": 0, "limit": 14})
    outcome = publish(h, selected)
    assert outcome["status"] == "completed", outcome
    assert outcome["result"]["projection"]["selected_row_count"] == 14
    assert outcome["result"]["projection"]["population_complete"]
    for index in (1, 3, 4, 7, 9, 11, 12, 13):
        measured = values(outcome, index)
        assert measured["selected_row_count"] == measured["query_strand_union_span_nt"] == 0
        assert measured["query_strand_union_fraction"] == 0
    assert values(outcome, 5)["query_strand_union_span_nt"] == 119
    assert values(outcome, 12)["query_length_nt"] == 119
    assert all(values(outcome, i)["query_strand_overlap_excess_nt"] == 0 for i in range(14))


def test_batch_json_never_joins_hits_by_order_and_artifact_only_can_complete(batch):
    h = batch
    selected = selection(version=2)
    prepared = h.service.prepare("api.rfam.fetch", h.request, {}, scope=h.scope, previous_events=[],
        handle=h.handle, selector=selected)
    snapshot = h.service.invoke(prepared)
    requested = publish(h, selected, snapshot=snapshot)
    assert requested["status"] == "partial" and requested["result"]["sheet_ref"] is None
    assert requested["result"]["format"] == "rfam_multiple_sequences_json_untyped"
    assert requested["result"]["projection_errors"][0]["code"] == "rfam_multiple_sequences_schema_unestablished"
    assert h.store.get_artifact(requested["result"]["artifact_ref"]) == snapshot.content
    artifact = publish(h, selection(version=2, projection=False), snapshot=snapshot, key="batch-json-artifact")
    assert artifact["status"] == "completed" and artifact["result"]["projection_errors"] == []


@pytest.mark.parametrize("mutation,code", [("job", "rfam_batch_native_query_file_conflict"),
    ("version", "rfam_batch_native_version_unsupported")])
def test_batch_rejected_table_keeps_specific_closed_failure_and_full_bytes(batch, mutation, code):
    h = batch
    content = h.snapshot.content
    if mutation == "job":
        content = content.replace(h.handle["job_id"].encode(), b"infernal_cmscan-OTHER")
    else:
        content = content.replace(b"1.1.5 (Sep 2023)", b"2.0.0 (Synthetic)")
    outcome = publish(h, selection(representation="tblout", version=2),
        snapshot=synthetic(h, content))
    assert outcome["status"] == "partial", outcome
    assert outcome["result"]["sheet_ref"] is outcome["result"]["calculation_ref"] is None
    assert code in {item["code"] for item in outcome["result"]["projection_errors"]}
    assert all(set(row) == {"code", "scope", "hit_key", "field", "source_pointer"}
        for row in outcome["result"]["projection_errors"])
    assert h.store.get_artifact(outcome["result"]["artifact_ref"]) == content


def test_batch_wrong_original_file_cannot_publish_and_replay_is_exact(batch):
    h = batch
    selected = selection(representation="tblout", version=2)
    request = {**h.submission.request, "file_base64": base64.b64encode(b">changed\nACG\n").decode()}
    with pytest.raises(ValueError, match="rfam_result_sequence_identity_conflict"):
        publish(h, selected, submission=replace(h.submission, request=request))
    first = publish(h, selected)
    assert publish(h, selected) == first
    assert h.store.count("source") == h.original_source_count + 3
    with pytest.raises(ContractError, match="operation_key_reused_for_different_work"):
        publish(h, selection("query_span_nt", representation="tblout", version=2))


def test_batch_partial_native_population_and_incomplete_body_keep_valid_calculations(batch):
    h = batch
    content = h.snapshot.content.replace(b"# [ok]\n", b"")
    selected = selection("native_score_bits", representation="tblout", version=2)
    partial = publish(h, selected, snapshot=synthetic(h, content))
    assert partial["status"] == "completed", partial
    assert not partial["result"]["projection"]["population_complete"]
    assert values(partial)["native_score_bits"] == 104.6
    interrupted = publish(h, selected, snapshot=synthetic(h, content, complete=False), key="interrupted")
    assert interrupted["status"] == "partial"
    assert values(interrupted)["native_score_bits"] == 104.6
    assert "rfam_response_body_incomplete" in {i["code"] for i in interrupted["result"]["projection_errors"]}


def test_synthetic_complete_zero_batch_keeps_every_original_input_and_zero_strands(batch):
    h = batch
    content = b"".join(line for line in h.snapshot.content.splitlines(keepends=True) if line.startswith(b"#"))
    selected = selection("query_length_nt", "selected_row_count", "query_strand_union_span_nt",
        "query_strand_union_fraction", family="query_strand", representation="tblout", version=2,
        rows={"offset": 0, "limit": 14})
    outcome = publish(h, selected, snapshot=synthetic(h, content))
    assert outcome["status"] == "completed", outcome
    _, parsed, sheet, calculation = saved(h, outcome)
    assert sheet["hits"] == calculation["hits"] == []
    assert len(sheet["source_context"]["query_population"]) == 7
    assert all(row["reported_row_count"] == 0 and row["reported_set_complete"] for row in sheet["source_context"]["query_population"])
    assert outcome["result"]["projection"]["selected_row_count"] == 14
    assert all(values(outcome, i)["selected_row_count"] == values(outcome, i)["query_strand_union_span_nt"] == 0
        and values(outcome, i)["query_strand_union_fraction"] == 0 for i in range(14))


@pytest.mark.parametrize("case", ["missing_source", "invalid_inner_record"])
def test_batch_invalid_optional_metadata_keeps_native_table_and_qualified_unavailable(batch, case):
    h = batch
    selected = selection("native_score_bits", "model_length_positions", "model_coverage_fraction",
        representation="tblout", version=2)
    selected["model_metadata_ref"] = "source_" + "0" * 24
    if case == "invalid_inner_record":
        original = caller_source(h.store, {"model_length_positions": 120})
        source = caller_source(h.store, {"version": "rfam_model_metadata_v1", "bindings": [],
            "records": [{"source_ref": original["id"], "metadata_ref": original["artifact_ref"]}]})
        selected["model_metadata_ref"] = source["id"]
    outcome = publish(h, selected)
    assert outcome["status"] == "completed", outcome
    assert values(outcome)["native_score_bits"] == 104.6
    manifest, parsed, _, _ = saved(h, outcome)
    assert manifest["selector"] == selected and parsed["sheet"]["source_context"]["supplied_model_metadata"] is None
    field = "model_metadata_ref" if case == "missing_source" else "supplied_model_metadata"
    assert {"code": "rfam_batch_model_metadata_invalid", "severity": "error",
        "field": field, "native_query_name": None, "source_line": None} in parsed["issues"]
    parents = h.store.get(outcome["result"]["grading_source_ref"])["parent_source_refs"]
    assert (selected["model_metadata_ref"] in parents) == (case == "invalid_inner_record")
    assert outcome["result"]["projection"]["rows"][0]["unavailable"] == [
        {"name": "model_length_positions", "reason": "model_metadata_conflict"},
        {"name": "model_coverage_fraction", "reason": "model_metadata_conflict"}]

