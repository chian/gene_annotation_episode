"""Engineered selected-action custody controls, with no HTTP or scientific fit.

The owner uses actual APIServiceExecution manifest, selected-action and snapshot
methods over a real Store. Runtime action rows are explicit engineering setup;
these controls do not establish a Workflow, typed return or live Enrichr result.
"""
import asyncio
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import io
import json
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.api_enrichr import (EnrichrService, PROTOCOL_VERSION,
    QUERY, WIRE_PROFILE)
from gene_annotation_episode import api_enrichr, api_enrichr_host as host_module
from gene_annotation_episode.api_enrichr_host import EnrichrProtocolHost
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.practical_execution_state import _immutable, _read
from gene_annotation_episode.state import Store


RUN, EPISODE, RESOURCE = "enrichr-host-run", "selected-api-episode", "selected-enrichr"
LIBRARY = "Literal library / α"


def request(profile="standard_enrichr_v1", supplied=False):
    return {"version": "enrichr_request_v1", "protocol_profile": profile,
        "library": LIBRARY, "genes": ["ENSG000001.7", "X", "X"],
        "identifier_policy": "literal_no_mapping", "species_context": None,
        "description": "Literal engineering input", "background": {
            "policy": "supplied" if supplied else "service_native",
            "genes": ["X", "Y", "X"] if supplied else None},
        "native_statistic_profile": "documented_odds_v1"}


def configuration(profile="standard_enrichr_v1"):
    return {"kind": "api", "service": "enrichr", "protocol_profile": profile,
        "base_url": "https://example.invalid/original", "timeout": 0.75,
        "response_byte_limit": 4096}


class EngineeredHTTP:
    def __init__(self):
        self.owner_thread = threading.get_ident()
        self.calls = []
        self.responses = {}
        self.before = None

    def _http(self, service, url, params, media_type, **kwargs):
        assert threading.get_ident() != self.owner_thread
        code = ("query_upload" if url.endswith("/addList") else
            "background_upload" if url.endswith("/addbackground") else "enrichment")
        self.calls.append(code)
        if self.before is not None:
            self.before(code)
        selected = self.responses.get(code, {})
        if selected.get("exception") is not None:
            raise selected["exception"]
        wire = {"method": "POST" if kwargs["body"] is not None else "GET", "url": url,
            "headers": {"Accept": kwargs["accept"]}}
        if kwargs["body"] is not None:
            wire["headers"]["Content-Type"] = kwargs["content_type"]
            import base64
            wire.update(body_base64=base64.b64encode(kwargs["body"]).decode(),
                body_sha256=hashlib.sha256(kwargs["body"]).hexdigest())
        default = {"query_upload": b'{"userListId":21}',
            "background_upload": b'{"backgroundid":"opaque+/ ="}',
            "enrichment": json.dumps({LIBRARY: [[1, "Native term", 0.01, 2.5,
                7.0, ["X", "X"], 0.04, 0, 0]]}, ensure_ascii=False).encode()}[code]
        transport = {"status": selected.get("status", 200), "request": wire,
            "headers": {"content-type": "application/json"}, "effective_url": url,
            "body_complete": selected.get("complete", True), "request_policy": {
                "timeout_seconds": kwargs["timeout_seconds"], "automatic_redirects": False}}
        if "capture_failure" in selected:
            transport["body_capture_failure"] = selected["capture_failure"]
        content = selected.get("content", default)
        if selected.get("bounded_capture"):
            response = io.BytesIO(content)
            response.headers = {"Content-Length": str(len(content))}
            content, capture, failure = PublicClients._read_bounded_response(
                response, kwargs["max_bytes"])
            assert failure == selected["error"] == "provider_response_byte_limit"
            transport.update(capture)
        if selected.get("omit_complete"):
            transport.pop("body_complete")
        snapshot = SourceSnapshot(service, url, params, "2026-10-30T00:00:00+00:00",
            content, media_type, transport)
        if "error" in selected:
            raise AcquisitionError(selected["error"], snapshot=snapshot, phase="http_response",
                retry_after=2, submission_outcome=selected.get("submission_outcome"),
                diagnostic={"native_error": "preserved literal diagnostic"},
                operational={"native_attempt": 1})
        return snapshot


@pytest.fixture
def harness(tmp_path, monkeypatch):
    monkeypatch.setattr(api_enrichr, "parse_enrichr_response", forbidden)
    monkeypatch.setattr(api_enrichr, "calculate_enrichr_components", forbidden)
    with Store(tmp_path / "store") as store:
        store.db.execute("CREATE TABLE runtime_actions(run_id TEXT,episode_id TEXT,"
            "decision_index INTEGER,action TEXT,result TEXT)")
        owner_thread = threading.get_ident()
        store_threads = []
        for name in ("artifact", "get_artifact"):
            original = getattr(store, name)
            def observed(*args, _original=original, _name=name, **kwargs):
                store_threads.append((_name, threading.get_ident()))
                assert threading.get_ident() == owner_thread
                return _original(*args, **kwargs)
            monkeypatch.setattr(store, name, observed)
        def build(profile="standard_enrichr_v1", supplied=False):
            client = EngineeredHTTP()
            tools = SimpleNamespace(store=store, clients=client)
            service = EnrichrService(tools, configuration(profile))
            owner = APIServiceExecution.__new__(APIServiceExecution)
            owner.store, owner.run_id = store, RUN
            owner.directory = tmp_path / "api-service-execution"
            owner.services = {RESOURCE: service}
            owner.configuration = {RESOURCE: configuration(profile)}
            assignment = {"version": "api_service_assignment_v1", "resource_id": RESOURCE,
                "service": "enrichr", "request": request(profile, supplied),
                "endpoint": "usable_handoff", "constraints": {}}
            context = BindingContext(RUN, EPISODE, "launch_api", (("launch_api", "original"),),
                {}, assignment, {})
            key = f"{RUN}:{EPISODE}:0"
            action = {"kind": "tool", "tool": QUERY, "arguments": {}}
            store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,?)",
                (RUN, EPISODE, 0, canonical(action), None))
            directory = owner._manifest(context) / "actions" / digest(key)
            directory.mkdir()
            prepared = service.prepare(QUERY, assignment["request"], {}, scope={}, previous_events=[])
            intent = {"run_id": RUN, "episode_id": EPISODE, "name": QUERY, "arguments": {},
                "assignment_sha256": digest(assignment), "operation_key": key,
                "prepared": prepared, "started_at": "2026-10-30T00:00:00+00:00"}
            _immutable(directory / "intent.json", intent)
            return SimpleNamespace(store=store, owner=owner, context=context, directory=directory,
                client=client, service=service, intent=intent, host=EnrichrProtocolHost(owner),
                store_threads=store_threads)
        yield build


def acquire(h):
    return asyncio.run(h.host.acquire(h.context, h.service, h.intent, h.directory))


def forbidden(*args, **kwargs):
    raise AssertionError("saved custody must not invoke, prepare, acquire or calculate")


def files(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
        for path in directory.rglob("*") if path.is_file()}


def rewrite(path, value):
    path.write_text(canonical(value) + "\n")


@pytest.mark.parametrize("profile,supplied,length", [
    ("standard_enrichr_v1", False, 2), ("speedrichr_v1", False, 2),
    ("speedrichr_v1", True, 3)])
def test_selected_protocol_retains_before_each_call_and_store_stays_on_owner_thread(
        harness, monkeypatch, profile, supplied, length):
    h = harness(profile, supplied)
    def before(code):
        ordinal = len(h.client.calls) - 1
        stage_dir = h.directory / "protocol-stages" / str(ordinal)
        intent = _read(stage_dir / "intent.json")
        assert intent["operation_key"] == h.intent["operation_key"]
        assert intent["main_intent_sha256"] == digest(h.intent)
        assert intent["prepared"]["stage_code"] == code
        for prior in range(ordinal):
            assert (h.directory / "protocol-stages" / str(prior) / "snapshot.json").exists()
    h.client.before = before
    actual = acquire(h)
    assert len(h.client.calls) == length
    protocol = actual.transport["enrichr_protocol"]
    assert set(protocol) == {"version", "wire_profile", "prepared", "stages"}
    assert protocol["version"] == PROTOCOL_VERSION and protocol["wire_profile"] == WIRE_PROFILE
    assert canonical(protocol["prepared"]) == canonical(h.intent["prepared"])
    assert len(protocol["stages"]) == length
    assert all("enrichr_protocol" not in row["snapshot"]["transport"] for row in protocol["stages"])
    text = canonical(protocol)
    assert RUN not in text and EPISODE not in text and str(h.directory) not in text
    final_raw = h.owner._load_snapshot(protocol["stages"][-1]["snapshot"])
    expected = asdict(final_raw)
    observed = asdict(actual)
    observed["transport"].pop("enrichr_protocol")
    assert observed.pop("content") == expected.pop("content")
    assert canonical(observed) == canonical(expected)
    assert h.store_threads and all(thread == threading.get_ident() for _, thread in h.store_threads)
    assert not (h.directory / "snapshot.json").exists()  # Only the owner publishes the main snapshot.
    before_files = files(h.directory)
    before_rows = list(map(tuple, h.store.db.execute("SELECT * FROM artifacts ORDER BY id")))
    monkeypatch.setattr(h.service, "invoke", forbidden)
    monkeypatch.setattr(h.service, "prepare", forbidden)
    monkeypatch.setattr(h.owner, "_context", forbidden)
    monkeypatch.setattr(h.store, "artifact", forbidden)
    h.host.validate(h.context, h.service, h.intent, h.directory, actual)
    assert canonical(asdict_without_content(acquire(h))) == canonical(asdict_without_content(actual))
    assert files(h.directory) == before_files
    assert list(map(tuple, h.store.db.execute("SELECT * FROM artifacts ORDER BY id"))) == before_rows


def asdict_without_content(snapshot):
    value = asdict(snapshot)
    value["content_sha256"] = hashlib.sha256(value.pop("content")).hexdigest()
    return value


@pytest.mark.parametrize("profile,supplied,prefix", [
    ("standard_enrichr_v1", False, 1), ("speedrichr_v1", True, 2)])
def test_captured_prefix_resumes_only_unissued_fixed_stages_with_original_wire_configuration(
        harness, monkeypatch, profile, supplied, prefix):
    h = harness(profile, supplied)
    immutable = host_module._immutable
    class BetweenStages(BaseException):
        pass
    def paused(path, value):
        if path.name == "intent.json" and path.parent.name == str(prefix):
            raise BetweenStages()
        return immutable(path, value)
    monkeypatch.setattr(host_module, "_immutable", paused)
    with pytest.raises(BetweenStages):
        acquire(h)
    assert len(h.client.calls) == prefix
    assert not (h.directory / "protocol-stages" / str(prefix) / "intent.json").exists()
    monkeypatch.setattr(host_module, "_immutable", immutable)
    h.service.configuration = configuration("speedrichr_v1")
    h.service.configuration["base_url"] = "https://changed.invalid/new-route"
    h.owner.configuration = {RESOURCE: deepcopy(h.service.configuration)}
    actual = acquire(h)
    assert h.client.calls.count("query_upload") == 1
    if supplied:
        assert h.client.calls.count("background_upload") == 1
    assert h.client.calls.count("enrichment") == 1
    for entry in actual.transport["enrichr_protocol"]["stages"]:
        assert entry["snapshot"]["request"]["http"]["url"].startswith(
            "https://example.invalid/original/")


@pytest.mark.parametrize("stage", ["query_upload", "enrichment"])
def test_issued_stage_without_reply_is_unknown_and_never_reissued(harness, monkeypatch, stage):
    h = harness()
    h.client.responses[stage] = {"exception": RuntimeError("engineered lost response")}
    with pytest.raises(AcquisitionError) as caught:
        acquire(h)
    assert caught.value.code == "enrichr_protocol_stage_response_unknown"
    ordinal = 0 if stage == "query_upload" else 1
    assert caught.value.diagnostic == {"stage_ordinal": ordinal, "stage_code": stage,
        "captured_prefix_count": ordinal, "http_status": None,
        "response_retained": False, "all_stage_responses_captured": False}
    assert caught.value.submission_outcome == ("unknown" if ordinal == 0 else "response_received")
    original_calls, original_files = list(h.client.calls), files(h.directory)
    monkeypatch.setattr(h.service, "invoke", forbidden)
    with pytest.raises(AcquisitionError, match="stage_response_unknown"):
        acquire(h)
    assert h.client.calls == original_calls and files(h.directory) == original_files
    assert not (h.directory / "snapshot.json").exists()


@pytest.mark.parametrize("case,expected", [
    ("missing_id", "enrichr_upload_id_missing"), ("http_error", "provider_http_503"),
    ("incomplete", "provider_response_byte_limit")])
def test_intermediate_failure_preserves_raw_prefix_without_enrichment_or_main_snapshot(
        harness, monkeypatch, case, expected):
    h = harness()
    options = {"missing_id": {"content": b'{}'}, "http_error": {
        "content": b'raw provider failure', "status": 503, "error": "provider_http_503"},
        "incomplete": {"content": b'{"userListId":', "complete": False,
            "capture_failure": "provider_response_byte_limit", "error": "provider_response_byte_limit"}}
    h.client.responses["query_upload"] = options[case]
    with pytest.raises(AcquisitionError) as caught:
        acquire(h)
    assert caught.value.code == expected and caught.value.submission_outcome == "response_received"
    assert caught.value.diagnostic["stage_ordinal"] == 0
    assert caught.value.diagnostic["response_retained"] is True
    assert caught.value.diagnostic["captured_prefix_count"] == 1
    saved = _read(h.directory / "protocol-stages" / "0" / "snapshot.json")
    assert h.store.get_artifact(saved["content_ref"]) == options[case]["content"]
    assert h.client.calls == ["query_upload"] and not (h.directory / "snapshot.json").exists()
    monkeypatch.setattr(h.service, "invoke", forbidden)
    with pytest.raises(AcquisitionError) as recovered:
        acquire(h)
    assert recovered.value.code == expected and h.client.calls == ["query_upload"]


@pytest.mark.parametrize("error,status,complete,accepted", [
    ("provider_response_byte_limit", 200, False, True),
    ("provider_body_capture_failed", 200, False, False),
    ("provider_response_byte_limit", 503, False, False),
    ("provider_response_byte_limit", 200, True, False)])
def test_final_partial_acceptance_keeps_actual_error_and_requires_exact_bounded_failure(
        harness, monkeypatch, error, status, complete, accepted):
    h = harness()
    content = b'{"Literal' + b"x" * 4096 if accepted else b'{"Literal'
    h.client.responses["enrichment"] = {"content": content, "complete": complete,
        "status": status, "capture_failure": error, "error": error, "bounded_capture": accepted}
    if accepted:
        actual = acquire(h)
        assert actual.content == content[:4096] and actual.transport["body_complete"] is False
        assert actual.transport["body_capture_failure"] == "provider_response_byte_limit"
        assert actual.transport["observed_body_bytes"] == 4097
        assert actual.transport["retained_body_bytes"] == 4096
        h.host.validate(h.context, h.service, h.intent, h.directory, actual)
    else:
        with pytest.raises(AcquisitionError) as caught:
            acquire(h)
        assert caught.value.code == error
        assert caught.value.submission_outcome == "response_received"
        assert set(caught.value.diagnostic) == {"stage_ordinal", "stage_code", "captured_prefix_count",
            "http_status", "response_retained", "all_stage_responses_captured"}
    failure = _read(h.directory / "protocol-stages" / "1" / "failure.json")
    assert failure["acquisition_error"] == {"code": error, "retry_after": 2, "job_ref": None,
        "phase": "http_response", "submission_outcome": None,
        "diagnostic": {"native_error": "preserved literal diagnostic"}, "operational": {"native_attempt": 1}}
    assert failure["snapshot_sha256"] == digest(_read(
        h.directory / "protocol-stages" / "1" / "snapshot.json"))
    monkeypatch.setattr(h.service, "invoke", forbidden)
    if accepted:
        assert acquire(h).content == actual.content
    else:
        with pytest.raises(AcquisitionError):
            acquire(h)
    assert h.client.calls == ["query_upload", "enrichment"]


@pytest.mark.parametrize("stage,aggregate", [("query_upload", "not_sent"),
    ("enrichment", "response_received")])
def test_stage_not_sent_does_not_erase_an_already_captured_upload(harness, monkeypatch, stage, aggregate):
    h = harness()
    error = AcquisitionError("engineered_not_sent", phase="local_preflight", submission_outcome="not_sent")
    h.client.responses[stage] = {"exception": error}
    with pytest.raises(AcquisitionError) as caught:
        acquire(h)
    assert caught.value.submission_outcome == aggregate
    ordinal = 0 if stage == "query_upload" else 1
    failure = _read(h.directory / "protocol-stages" / str(ordinal) / "failure.json")
    assert failure["acquisition_error"]["submission_outcome"] == "not_sent"
    assert failure["snapshot_sha256"] is None
    calls = list(h.client.calls)
    monkeypatch.setattr(h.service, "invoke", forbidden)
    with pytest.raises(AcquisitionError) as recovered:
        acquire(h)
    assert recovered.value.submission_outcome == aggregate and h.client.calls == calls


@pytest.mark.parametrize("change", ["run", "scope", "selected_action", "main_arguments",
    "anchored_main_configuration", "stage_prepared", "prior_metadata_hash", "raw_metadata",
    "raw_artifact", "final_bytes", "final_metadata", "final_protocol"])
def test_saved_validation_rejects_changed_original_custody_without_invoking(harness, monkeypatch, change):
    h = harness()
    actual = acquire(h)
    intent, context = h.intent, h.context
    stage_dir = h.directory / "protocol-stages" / "1"
    if change == "run":
        context = replace(context, run_id="foreign-run")
    elif change == "scope":
        context = replace(context, scope={"foreign": True})
    elif change == "selected_action":
        h.store.db.execute("UPDATE runtime_actions SET action=?", (canonical({
            "kind": "tool", "tool": QUERY, "arguments": {"foreign": True}}),))
    elif change in ("main_arguments", "anchored_main_configuration"):
        intent = deepcopy(intent)
        if change == "main_arguments":
            intent["arguments"] = {"foreign": True}
        else:
            intent["prepared"]["configuration"]["base_url"] = "https://forged.invalid"
        rewrite(h.directory / "intent.json", intent)
    elif change in ("stage_prepared", "prior_metadata_hash"):
        path = stage_dir / "intent.json"
        value = _read(path)
        if change == "stage_prepared":
            value["prepared"]["http"]["url"] = "https://forged.invalid"
        else:
            value["prior_responses"][0]["snapshot_sha256"] = "0" * 64
        rewrite(path, value)
    elif change == "raw_metadata":
        path = stage_dir / "snapshot.json"
        value = _read(path)
        value["retrieved_at"] = "2026-10-31T00:00:00+00:00"
        rewrite(path, value)
    elif change == "raw_artifact":
        metadata = _read(stage_dir / "snapshot.json")
        sha = metadata["content_ref"].removeprefix("artifact_")
        (h.store.path / "artifacts" / sha[:2] / sha).write_bytes(b"forged response")
    elif change == "final_bytes":
        actual = replace(actual, content=b"forged response")
    else:
        transport = deepcopy(actual.transport)
        if change == "final_metadata":
            transport["status"] = 200.0
        else:
            transport["enrichr_protocol"]["prepared"]["configuration"]["timeout"] = 99
        actual = replace(actual, transport=transport)
    monkeypatch.setattr(h.service, "invoke", forbidden)
    with pytest.raises((ValueError, OSError)):
        h.host.validate(context, h.service, intent, h.directory, actual)
    assert h.client.calls == ["query_upload", "enrichment"]


def test_missing_response_after_existing_intent_blocks_even_without_failure_record(harness, monkeypatch):
    h = harness()
    stage = h.service.protocol_request(h.intent["prepared"], stage=0, retained_responses=[])
    stage_directory = h.directory / "protocol-stages" / "0"
    stage_directory.mkdir(parents=True)
    _immutable(stage_directory / "intent.json", h.host._stage_intent(h.intent, 0, stage, [], []))
    monkeypatch.setattr(h.service, "invoke", forbidden)
    with pytest.raises(AcquisitionError) as caught:
        acquire(h)
    assert caught.value.code == "enrichr_protocol_stage_response_unknown"
    assert caught.value.submission_outcome == "unknown" and h.client.calls == []


def test_later_record_without_preceding_intent_is_not_permission_to_start(harness, monkeypatch):
    h = harness()
    later = h.directory / "protocol-stages" / "1"
    later.mkdir(parents=True)
    _immutable(later / "intent.json", {"forged": "not an issued prefix"})
    monkeypatch.setattr(h.service, "invoke", forbidden)
    with pytest.raises(ValueError, match="custody_conflict"):
        acquire(h)
    assert h.client.calls == []


@pytest.mark.parametrize("options,code", [({"status": 503}, "enrichr_stage_http_failed"),
    ({"omit_complete": True}, "enrichr_stage_capture_state_missing")])
def test_final_returned_invalid_transport_has_structured_retained_failure(
        harness, monkeypatch, options, code):
    h = harness()
    h.client.responses["enrichment"] = options
    with pytest.raises(AcquisitionError) as caught:
        acquire(h)
    assert caught.value.code == code and caught.value.phase == "protocol_response"
    assert caught.value.submission_outcome == "response_received"
    assert caught.value.diagnostic == {"stage_ordinal": 1, "stage_code": "enrichment",
        "captured_prefix_count": 2, "http_status": options.get("status", 200),
        "response_retained": True, "all_stage_responses_captured": True}
    assert not (h.directory / "snapshot.json").exists()
    snapshot_path = h.directory / "protocol-stages" / "1" / "snapshot.json"
    raw = h.owner._load_snapshot(_read(snapshot_path))
    assert raw.transport.get("status") == options.get("status", 200)
    calls = list(h.client.calls)
    monkeypatch.setattr(h.service, "invoke", forbidden)
    with pytest.raises(AcquisitionError, match=code):
        acquire(h)
    assert h.client.calls == calls


def test_first_transport_error_without_submission_evidence_has_unknown_aggregate(harness, monkeypatch):
    h = harness()
    h.client.responses["query_upload"] = {"exception": AcquisitionError(
        "provider_connection_failed", phase="http_request", submission_outcome=None)}
    with pytest.raises(AcquisitionError) as caught:
        acquire(h)
    assert caught.value.code == "provider_connection_failed"
    assert caught.value.submission_outcome == "unknown"
    assert caught.value.diagnostic["captured_prefix_count"] == 0
    assert caught.value.diagnostic["response_retained"] is False
    failure = _read(h.directory / "protocol-stages" / "0" / "failure.json")
    assert failure["acquisition_error"]["submission_outcome"] is None
    monkeypatch.setattr(h.service, "invoke", forbidden)
    with pytest.raises(AcquisitionError) as saved:
        acquire(h)
    assert saved.value.submission_outcome == "unknown" and h.client.calls == ["query_upload"]


def closed_metadata_case(harness, monkeypatch, profile="standard_enrichr_v1", supplied=False, partial=False):
    """Captured stage identities, not proof of a closed Workflow publication.

    Request/grade blobs are explicitly opaque denied-read sentinels. Actual
    Source/request/grading custody and successful closure belong to Returns'
    caller guard, not this metadata verifier or these engineered action rows.
    """
    from gene_annotation_episode.enrichr_returns import EnrichrReturns
    h = harness(profile, supplied)
    if partial:
        h.client.responses["enrichment"] = {"content": b'{"Literal' + b"x" * 4096,
            "error": "provider_response_byte_limit", "bounded_capture": True}
    actual = acquire(h)
    metadata = h.owner._snapshot(actual)
    h.owner.__dict__["_enrichr_returns"] = EnrichrReturns(h.owner)
    owner = h.owner.enrichr_returns
    artifacts = owner._protocol_artifacts(metadata["transport"], metadata["content_ref"], verify_bytes=False)
    sentinels = [h.store.artifact(b"opaque request-payload read sentinel", "application/octet-stream"),
        h.store.artifact(b"opaque grading-payload read sentinel; no scientific grade", "application/octet-stream")]
    withdrawn = set(sentinels) | {row["artifact_ref"] for row in artifacts}
    for reference in withdrawn:
        catalog = owner._artifact_metadata(reference)
        payload = h.store.path / "artifacts" / catalog["sha256"][:2] / catalog["sha256"]
        assert payload.is_file()
        payload.unlink()
    monkeypatch.setattr(h.store, "get_artifact", forbidden)
    monkeypatch.setattr(h.store, "artifact", forbidden)
    monkeypatch.setattr(h.service, "invoke", forbidden)
    monkeypatch.setattr(h.service, "prepare", forbidden)
    monkeypatch.setattr(h.service, "protocol_request", forbidden)
    monkeypatch.setattr(h.service, "decode", forbidden)
    monkeypatch.setattr(h.owner, "_load_snapshot", forbidden)
    monkeypatch.setattr(api_enrichr, "project_enrichr_return", forbidden)
    return h, metadata, artifacts, withdrawn


@pytest.mark.parametrize("profile,supplied,partial", [
    ("standard_enrichr_v1", False, False), ("speedrichr_v1", False, False),
    ("speedrichr_v1", True, False), ("standard_enrichr_v1", False, True)])
def test_closed_metadata_checks_original_identity_without_any_withdrawn_payload(
        harness, monkeypatch, profile, supplied, partial):
    h, metadata, artifacts, withdrawn = closed_metadata_case(harness, monkeypatch, profile, supplied, partial)
    before_files, before_changes = files(h.directory), h.store.db.total_changes
    h.host.validate_closed_metadata(h.context, h.service, h.intent, h.directory, metadata,
        protocol_artifacts=artifacts)
    assert files(h.directory) == before_files and h.store.db.total_changes == before_changes
    for reference in withdrawn:
        sha = reference.removeprefix("artifact_")
        assert not (h.store.path / "artifacts" / sha[:2] / sha).exists()
    assert h.client.calls == (["query_upload", "background_upload", "enrichment"]
        if supplied else ["query_upload", "enrichment"])


@pytest.mark.parametrize("change", ["protocol_version", "protocol_prepared", "stage_ordinal_bool",
    "stage_code", "raw_extra_field", "stage_intent", "prefix_metadata_hash", "prefix_content_hash",
    "catalog_sha", "catalog_size", "catalog_media_type", "wire_redirect_alias", "wire_timeout_alias",
    "status_alias", "complete_alias", "final_outer_metadata"])
def test_closed_metadata_rejects_stage_prefix_catalog_and_wire_tampering_without_payloads(
        harness, monkeypatch, change):
    h, metadata, artifacts, _ = closed_metadata_case(harness, monkeypatch)
    protocol = metadata["transport"]["enrichr_protocol"]
    raw = protocol["stages"][0]["snapshot"]
    if change == "protocol_version":
        protocol["version"] = "unknown"
    elif change == "protocol_prepared":
        protocol["prepared"]["configuration"]["base_url"] = "https://foreign.invalid"
    elif change == "stage_ordinal_bool":
        protocol["stages"][0]["ordinal"] = False
    elif change == "stage_code":
        protocol["stages"][0]["stage_code"] = "background_upload"
    elif change == "raw_extra_field":
        raw["invented"] = "not a recorded Snapshot field"
    elif change in ("stage_intent", "prefix_metadata_hash"):
        path = h.directory / "protocol-stages" / "1" / "intent.json"
        value = _read(path)
        if change == "stage_intent":
            value["main_intent_sha256"] = "0" * 64
        else:
            value["prior_responses"][0]["snapshot_sha256"] = "0" * 64
        rewrite(path, value)
    elif change == "prefix_content_hash":
        protocol["stages"][1]["snapshot"]["request"]["prior_response_sha256"][0] = "0" * 64
    elif change.startswith("catalog_"):
        field = {"catalog_sha": "sha256", "catalog_size": "size", "catalog_media_type": "media_type"}[change]
        original = h.owner.enrichr_returns._artifact_metadata(artifacts[0]["artifact_ref"])
        value = "0" * 64 if field == "sha256" else original["size"] + 1 if field == "size" else "text/plain"
        h.store.db.execute("UPDATE artifacts SET " + field + "=? WHERE id=?", (value, artifacts[0]["artifact_ref"]))
    elif change == "final_outer_metadata":
        metadata["retrieved_at"] = "2026-10-31T00:00:00+00:00"
    else:
        if change == "wire_redirect_alias":
            raw["transport"]["request_policy"]["automatic_redirects"] = 0
        elif change == "wire_timeout_alias":
            raw["transport"]["request_policy"]["timeout_seconds"] = True
        elif change == "status_alias":
            raw["transport"]["status"] = 200.0
        else:
            raw["transport"]["body_complete"] = 1
        # Match the recorded raw metadata to target its typed wire validation.
        rewrite(h.directory / "protocol-stages" / "0" / "snapshot.json", raw)
    with pytest.raises(ValueError):
        h.host.validate_closed_metadata(h.context, h.service, h.intent, h.directory, metadata,
            protocol_artifacts=artifacts)
    assert h.client.calls == ["query_upload", "enrichment"]


@pytest.mark.parametrize("change", ["missing_failure", "different_failure"])
def test_closed_incomplete_metadata_requires_original_narrow_partial_failure(
        harness, monkeypatch, change):
    h, metadata, artifacts, _ = closed_metadata_case(harness, monkeypatch, partial=True)
    path = h.directory / "protocol-stages" / "1" / "failure.json"
    if change == "missing_failure":
        path.unlink()
    else:
        failure = _read(path)
        failure["acquisition_error"]["code"] = "provider_body_capture_failed"
        rewrite(path, failure)
    with pytest.raises(ValueError):
        h.host.validate_closed_metadata(h.context, h.service, h.intent, h.directory, metadata,
            protocol_artifacts=artifacts)
    assert h.client.calls == ["query_upload", "enrichment"]
