"""Single-request BLAST service fixtures; no network or scientific conclusions."""
import hashlib
import json
from dataclasses import replace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.api_blast import NCBIBlastService
from gene_annotation_episode.api_services import build_service
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


RID = "FIXTURE_ORIGINAL_RID"


def snapshot(content, request):
    if isinstance(content, dict):
        content = json.dumps(content).encode()
    return SourceSnapshot("ncbi_blast", "https://blast.ncbi.nlm.nih.gov/Blast.cgi", request,
        "2026-10-23T00:00:00+00:00", content, "application/json",
        {"representation": "synthetic_native_protocol_fixture", "status": 200})


class Client:
    ncbi_email = "synthetic-fixture@example.invalid"

    def __init__(self):
        self.calls = []
        self.subject = None
        self.program = "blastp"
        self.refuse = False
        self.wrong_subject = False

    def blast_delay(self, action, rid=None):
        return 60. if action == "status" else 10.

    def blast(self, action, **arguments):
        self.calls.append((action, arguments))
        if self.refuse:
            raise AcquisitionError("provider_spacing_required", retry_after=12.,
                                   phase="local_preflight", submission_outcome="not_sent")
        request = {"action": action, **{k: v for k, v in arguments.items() if k != "query_fasta"}}
        if action == "submit":
            self.subject = arguments["query_fasta"].splitlines()[0][1:]
            self.program = arguments["program"]
            request["query_sha256"] = hashlib.sha256(arguments["query_fasta"].encode()).hexdigest()
            return snapshot(b"    RID = FIXTURE_ORIGINAL_RID\n    RTOE = 17\n", request)
        assert arguments["rid"] == RID
        if action == "status":
            return snapshot(b"Status=WAITING\n", request)
        assert action == "fetch"
        return snapshot({"BlastOutput2": [{"report": {"program": self.program,
            "version": "BLASTP fixture", "search_target": {"db": "swissprot"},
            "results": {"search": {"query_title": "wrong" if self.wrong_subject else self.subject,
                "query_len": 8, "hits": [{"len": 8,
                    "description": [{"accession": "REF_FIXTURE", "title": "Reference protein", "taxid": 83333}],
                    "hsps": [{"query_from": 1, "query_to": 8, "hit_from": 1, "hit_to": 8,
                        "bit_score": 31.5, "score": 60, "evalue": 1e-5, "identity": 6,
                        "align_len": 8}]}]}}}}]}, request)


@pytest.fixture
def harness(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        client = Client()
        tools = ToolRegistry(store, clients=client)
        scope = store.validate_scope(None)
        request = {"subject_ref": store.targets()[0]["id"], "program": "blastp", "database": "swissprot"}
        yield store, tools, client, scope, request


def submit(service, request, scope):
    prepared = service.prepare("api.blast.submit", request, {}, scope=scope, previous_events=[])
    response = service.invoke(prepared)
    result = service.decode(prepared, response)
    return response, result


def test_prepare_submit_and_status_are_separate_selected_requests(harness):
    _, tools, client, scope, request = harness
    service = build_service("ncbi_blast", {"kind": "api", "service": "ncbi_blast"}, tools)
    assert {row["name"] for row in service.capabilities()} == {
        "api.blast.prepare", "api.blast.submit", "api.blast.status"}
    assert service.validate_request(request, None) == request
    prepared = service.prepare("api.blast.prepare", request, {}, scope=scope, previous_events=[])
    assert not prepared["mutates_remote"] and prepared["native_arguments"]["hitlist_size"] == 50
    assert service.invoke(prepared) is None
    local = service.decode(prepared, None)
    assert local["kind"] == "preparation" and not local["handoff_ready"]
    assert client.calls == []
    native, result = submit(service, request, scope)
    assert result["native_handle"] == {"rid": RID, "rtoe_seconds": 17}
    assert result["handoff_ready"] and not result["result_available"]
    assert result["facts"]["earliest_request_after_seconds"] == 60.
    assert len(client.calls) == 1
    check = service.prepare_observation(request, result["native_handle"], scope=scope)
    observed = service.decode(check, service.invoke(check))
    assert observed["kind"] == "job"
    assert observed["state"] == "submitted" and observed["facts"]["native_state"] == "WAITING"
    assert len(client.calls) == 2  # No protocol loop, fetch or automatic retry.
    with pytest.raises(ValueError, match="already_recorded"):
        service.prepare("api.blast.submit", request, {}, scope=scope,
            previous_events=[{"name": "api.blast.submit", "event": result}])


def test_fetch_publication_uses_actual_submission_without_provider_job_rows(harness):
    store, tools, client, scope, request = harness
    service = NCBIBlastService(tools)
    submitted, event = submit(service, request, scope)
    handle = event["native_handle"]
    prepared = service.prepare("api.blast.fetch", request, {}, scope=scope,
                               previous_events=[], handle=handle, selector={})
    fetched = service.invoke(prepared)
    decoded = service.decode(prepared, fetched)
    assert decoded["result_available"] and decoded["kind"] == "response"
    assert {row["name"] for row in service.result_catalog(request, {})} == {
        "api.blast.status", "api.blast.fetch"}
    published = service.publish(request, {}, fetched, scope, "blast-result",
                                submission_snapshot=submitted, handle=handle)
    assert published["status"] == "completed", published
    result = published["result"]
    assert result["rid"] == RID and result["job_ref"] is None
    assert result["projected_hsp_count"] == 1
    observation = store.get(result["records"][0]["observation_ref"])
    assert observation["subject_refs"] == [request["subject_ref"]]
    assert observation["source_subject_refs"] != observation["subject_refs"]
    assert result["records"][0]["measurements"]["bitscore"] == 31.5
    assert store.db.execute("SELECT COUNT(*) FROM provider_jobs").fetchone()[0] == 0
    assert service.publish(request, {}, fetched, scope, "blast-result",
                           submission_snapshot=submitted, handle=handle) == published
    assert len(client.calls) == 2  # Publication/recovery never invokes BLAST.


def test_identity_conflict_is_retained_as_error_not_published_for_target(harness):
    store, tools, client, scope, request = harness
    service = NCBIBlastService(tools)
    submitted, event = submit(service, request, scope)
    handle = event["native_handle"]
    prepared = service.prepare("api.blast.fetch", request, {}, scope=scope,
                               previous_events=[], handle=handle)
    client.wrong_subject = True
    fetched = service.invoke(prepared)
    with pytest.raises(ValueError, match="query_title_conflicts"):
        service.decode(prepared, fetched)
    with pytest.raises(ValueError, match="query_title_conflicts"):
        service.publish(request, {}, fetched, scope, "wrong-result",
                        submission_snapshot=submitted, handle=handle)
    assert store.db.execute("SELECT COUNT(*) FROM tool_operations").fetchone()[0] == 0


def test_spacing_is_returned_without_hidden_sleep_or_retry(harness, monkeypatch):
    _, tools, client, scope, request = harness
    service = NCBIBlastService(tools)
    prepared = service.prepare("api.blast.submit", request, {}, scope=scope, previous_events=[])
    client.refuse = True
    def no_sleep(*args):
        raise AssertionError("service_must_not_sleep")
    monkeypatch.setattr("time.sleep", no_sleep)
    with pytest.raises(AcquisitionError, match="provider_spacing_required") as failure:
        service.invoke(prepared)
    assert failure.value.retry_after == 12.
    assert len(client.calls) == 1


def test_unknown_operand_cannot_reach_provider(harness):
    _, tools, client, scope, request = harness
    service = NCBIBlastService(tools)
    invalid = {**request, "subject_ref": "not-a-registered-subject"}
    with pytest.raises(Exception):
        service.prepare("api.blast.submit", invalid, {}, scope=scope, previous_events=[])
    assert not client.calls


def test_valid_native_hsp_survives_an_invalid_neighbor(harness):
    store, tools, client, scope, request = harness
    service = NCBIBlastService(tools)
    submitted, result = submit(service, request, scope)
    handle = result["native_handle"]
    prepared = service.prepare("api.blast.fetch", request, {}, scope=scope,
                               previous_events=[], handle=handle)
    fetched = service.invoke(prepared)
    body = json.loads(fetched.content)
    hsps = body["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"]
    hsps.append({**hsps[0], "query_to": 999})
    fetched = replace(fetched, content=json.dumps(body).encode())
    published = service.publish(request, {}, fetched, scope, "partial-result",
                                submission_snapshot=submitted, handle=handle)
    assert published["status"] == "partial"
    assert published["result"]["projected_hsp_count"] == 1
    assert published["result"]["projection_errors"][0]["code"] == "blast_hsp_interval_outside_actual_operand"
    source = store.get(published["result"]["source_ref"])
    assert store.get_artifact(source["artifact_ref"]) == fetched.content
