"""Rfam selected-service and durable-handoff checks with controlled HTTP data.

No external scientific job or configured model runs here. Numerical grading and
complete receiving-episode integration have their own verification workloads.
"""
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.api_rfam import RfamBatchService
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.api_services import build_service
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.rfam_discovery import BASE_URL, result_url
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


JOB = "infernal_cmscan-CONTROLLED_ORIGINAL"
SEQUENCE = "ACGTTAGC"
SELECTOR = {"version": "rfam_batch_result_selector_v1", "representation": "json",
            "model_metadata_ref": None, "projection": None}


class Responses:
    timeout = 90

    def __init__(self):
        self.calls = []
        self.status_token = b"NOT_FOUND"
        self.submission_error = None
        self.result_body = {"jobId": JOB, "searchSequence": SEQUENCE, "numHits": 0, "hits": {}}

    def _snapshot(self, action, url, request, body, media_type="application/json"):
        self.calls.append((action, deepcopy(request)))
        return SourceSnapshot("rfam_batch", url, {"action": action, **request},
            f"2026-10-26T00:00:{len(self.calls):02d}+00:00",
            body if isinstance(body, bytes) else json.dumps(body).encode(), media_type,
            {"status": 200, "body_complete": True, "representation": "controlled_native_response"})

    def submit(self, sequence):
        if self.submission_error:
            self.calls.append(("submit", {"sequence": sequence}))
            raise self.submission_error
        return self._snapshot("submit", BASE_URL + "/submit-job",
            {"sequence_sha256": hashlib.sha256(sequence.encode("ascii")).hexdigest(),
             "sequence_length": len(sequence)}, {"jobId": JOB, "resultURL": result_url(JOB)})

    def status(self, job_id):
        return self._snapshot("status", BASE_URL + "/status/" + job_id,
                              {"job_id": job_id}, self.status_token, "text/plain")

    def submit_file(self, content, *, filename):
        return self._snapshot("submit", BASE_URL + "/submit-job", {
            "filename": filename, "file_sha256": hashlib.sha256(content).hexdigest(),
            "file_bytes": len(content), "file_base64": base64.b64encode(content).decode("ascii")},
            {"jobId": JOB, "resultURL": result_url(JOB)})

    def result(self, job_id, *, representation):
        suffix = "" if representation == "json" else "/" + representation
        return self._snapshot("fetch", result_url(job_id) + suffix,
            {"job_id": job_id, "representation": representation},
            self.result_body if representation == "json" else b"uninterpreted native bytes",
            "application/json" if representation == "json" else "text/plain")


@pytest.fixture
def harness(tmp_path):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence=SEQUENCE, molecule="dna")["subject_refs"]
        client = Responses()
        tools = ToolRegistry(store, clients=client)
        service = RfamBatchService(tools, client=client)
        request = {"version": "rfam_batch_request_v1", "mode": "single_sequence", "subject_ref": target}
        yield SimpleNamespace(store=store, tools=tools, client=client, service=service,
            request=request, scope={"subject_refs": [target]}, tmp_path=tmp_path)


def submitted(h):
    prepared = h.service.prepare("api.rfam.submit", h.request, {}, scope=h.scope, previous_events=[])
    snapshot = h.service.invoke(prepared)
    return prepared, snapshot, h.service.decode(prepared, snapshot)


def test_preparation_is_local_and_selected_submit_has_one_response(harness, monkeypatch):
    h = harness
    monkeypatch.setattr("time.sleep", lambda *a: pytest.fail("hidden sleep"))
    command = h.service.prepare("api.rfam.prepare", h.request, {}, scope=h.scope, previous_events=[])
    assert h.service.invoke(command) is None
    assert h.service.decode(command, None)["kind"] == "preparation"
    assert h.client.calls == []
    assert command["input_operand"]["submitted_sequence"] == SEQUENCE
    assert command["input_operand"]["input_to_submitted_transform"] == "unchanged"
    assert h.service.available_launch_catalog(h.request, []) == h.service.capabilities()[:2]
    _, snapshot, event = submitted(h)
    assert event["handoff_ready"] and not event["result_available"]
    assert event["native_handle"] == {"job_id": JOB, "result_url": result_url(JOB)}
    assert snapshot.request["input_operand"] == command["input_operand"]
    assert [call[0] for call in h.client.calls] == ["submit"]
    assert h.store.count("observation") == 0


def test_previous_original_handle_is_resolved_without_provider_job_registry(harness):
    h = harness
    _, _, result = submitted(h)
    history = [{"name": "api.rfam.submit", "event": result}]
    prepared = h.service.prepare("api.rfam.status", h.request, {}, scope=h.scope, previous_events=history)
    assert prepared["native_handle"] == result["native_handle"]
    assert len(h.service.available_launch_catalog(h.request, history)) == 3
    observed = h.service.decode(prepared, h.service.invoke(prepared))
    assert observed["state"] == "unknown" and observed["failure_code"] == "rfam_job_not_found"
    assert observed["facts"]["native_status"] == "NOT_FOUND"
    assert not observed["result_available"] and not observed["handoff_ready"]
    assert h.store.db.execute("SELECT count(*) FROM provider_jobs").fetchone()[0] == 0
    with pytest.raises(ValueError, match="rfam_original_submission_already_exists"):
        h.service.prepare("api.rfam.submit", h.request, {}, scope=h.scope, previous_events=history)
    conflict = {"job_id": JOB + "_DIFFERENT", "result_url": result_url(JOB + "_DIFFERENT")}
    with pytest.raises(ValueError, match="rfam_original_handle_conflict"):
        h.service.prepare("api.rfam.status", h.request, {}, scope=h.scope,
                          previous_events=history, handle=conflict)


@pytest.mark.parametrize("mutation", ["wrong_input", "wrong_action", "wrong_job", "wrong_url", "wrong_format"])
def test_wrong_fetch_binding_is_rejected_before_numerical_publication(harness, mutation):
    h = harness
    _, _, result = submitted(h)
    prepared = h.service.prepare("api.rfam.fetch", h.request, {}, scope=h.scope,
        previous_events=[], handle=result["native_handle"], selector=SELECTOR)
    snapshot = h.service.invoke(prepared)
    request = deepcopy(snapshot.request)
    url = snapshot.url
    if mutation == "wrong_input":
        request["input_operand"]["submitted_sequence_sha256"] = "0" * 64
    elif mutation == "wrong_action":
        request["action"] = "status"
    elif mutation == "wrong_job":
        request["job_id"] = JOB + "OTHER"
    elif mutation == "wrong_url":
        url += "/out"
    else:
        request["representation"] = "out"
    with pytest.raises(ValueError):
        h.service.decode(prepared, replace(snapshot, request=request, url=url))
    assert h.store.count("observation") == 0


@pytest.mark.parametrize("status,complete,body,state,available,code", [
    (200, False, b"{", "unknown", True, "rfam_response_body_incomplete"),
    (302, True, b"", "unknown", False, "rfam_redirect_not_followed"),
    (503, True, b"HOLD", "failed", False, "rfam_http_error"),
    (202, True, b"PEND", "submitted", False, None),
    (202, True, b"RUN", "running", False, None),
    (200, True, b'{"searchSequence":"","numHits":0}', "completed", True, None),
    (200, True, b"malformed scientific content", "completed", True, None),
])
def test_response_acquisition_and_scientific_validation_are_separate(harness, status, complete, body, state, available, code):
    h = harness
    _, _, result = submitted(h)
    prepared = h.service.prepare("api.rfam.fetch", h.request, {}, scope=h.scope,
        previous_events=[], handle=result["native_handle"], selector=SELECTOR)
    snapshot = h.service.invoke(prepared)
    snapshot = replace(snapshot, content=body, transport={"status": status, "body_complete": complete})
    decoded = h.service.decode(prepared, snapshot)
    assert decoded["state"] == state and decoded["result_available"] is available
    assert decoded["failure_code"] == code
    assert not decoded["handoff_ready"]
    # Complete malformed/expired bytes are eligible for retained diagnostic
    # publication, never a scientific no-hit result merely from this event.
    assert h.store.count("observation") == 0


@pytest.mark.parametrize("body", [
    b'{"jobId":"infernal_cmscan-A","jobId":"infernal_cmscan-B","resultURL":"x"}',
    b'{"jobId":"infernal_cmscan-A","resultURL":"https://other.invalid/x"}',
    b'{"jobId":"../wrong","resultURL":"https://batch.rfam.org/result/../wrong"}',
    b'{"jobId":"infernal_cmscan-A","resultURL":"https://batch.rfam.org/result/infernal_cmscan-A?extra=1"}',
    b'{"jobId":NaN}', b'[]', b'broken',
])
def test_invalid_submission_never_becomes_a_usable_handoff(harness, body):
    h = harness
    prepared, snapshot, _ = submitted(h)
    with pytest.raises((ValueError, TypeError)):
        h.service.decode(prepared, replace(snapshot, content=body))


def test_unsupplied_handle_unknown_operand_and_protein_cannot_invoke(harness):
    h = harness
    with pytest.raises(ValueError, match="rfam_original_handle_required"):
        h.service.prepare_observation(h.request, None, scope=h.scope)
    with pytest.raises(Exception):
        h.service.prepare("api.rfam.submit", {**h.request, "subject_ref": "missing"}, {},
                          scope=h.scope, previous_events=[])
    with Store(h.tmp_path / "protein") as store:
        subject, = store.create_problem(raw_sequence="ACGTTAGC", molecule="protein")["subject_refs"]
        service = RfamBatchService(ToolRegistry(store, clients=h.client), client=h.client)
        with pytest.raises(ValueError, match="rfam_sequence_invalid"):
            service.prepare("api.rfam.submit", {**h.request, "subject_ref": subject}, {},
                            scope={"subject_refs": [subject]}, previous_events=[])
    assert h.client.calls == []


def test_observed_finished_status_is_job_information_not_scientific_publication(harness):
    h = harness
    _, _, result = submitted(h)
    prepared = h.service.prepare_observation(h.request, result["native_handle"], scope=h.scope)
    h.client.status_token = b"FINISHED"
    finished = h.service.decode(prepared, h.service.invoke(prepared))
    assert finished["kind"] == "job" and finished["state"] == "completed"
    assert finished["result_available"] and not finished["handoff_ready"]
    assert h.store.count("observation") == 0
    h.client.status_token = b"SUCCESS"
    unknown = h.service.decode(prepared, h.service.invoke(prepared))
    assert unknown["state"] == "unknown" and unknown["failure_code"] == "rfam_status_unknown"
    assert [call[0] for call in h.client.calls] == ["submit", "status", "status"]


def _execution(h):
    journal = Journal(h.store, "rfam-selected-fixture")
    execution = APIServiceExecution(h.store, run_id=journal.run_id, directory=h.tmp_path / "run",
        configuration={"rfam": {"kind": "api", "service": "rfam_batch", "timeout": 90}},
        tool_registry=h.tools, handoff_unit=3, acquired_record_unit=2)
    execution.services["rfam"].client = h.client
    assignment = {"version": "api_service_assignment_v1", "resource_id": "rfam",
        "service": "rfam_batch", "request": h.request, "endpoint": "usable_handoff", "constraints": {}}
    request = {"message": {"scope": h.scope, "episode_assignment": assignment}}
    ctx = BindingContext(journal.run_id, "api", "launch_api", (("launch_api", "api"),),
                         h.scope, assignment, request)
    with h.store.transaction():
        journal.save("runtime_episodes", {"episode_id": ctx.episode_id, "path": canonical(ctx.path),
            "request": canonical(request), "initial_credit": 0, "state": "running"})
    return journal, execution, ctx


def _selected(h, journal, ctx, index, name="api.rfam.submit"):
    with h.store.transaction():
        journal.save("runtime_actions", {"episode_id": ctx.episode_id, "decision_index": index,
            "action": canonical({"kind": "tool", "tool": name, "arguments": {}}),
            "result": None, "credit": None})
    return f"{ctx.run_id}:{ctx.episode_id}:{index}"


@pytest.mark.parametrize("batch", [False, True])
def test_actual_selected_handoff_replays_and_resolves_native_job_id(harness, batch):
    h = harness
    if batch:
        h.request = {"version": "rfam_batch_request_v2", "mode": "sequence_batch",
                     "subject_refs": [h.request["subject_ref"], h.request["subject_ref"]]}
    journal, execution, ctx = _execution(h)
    assert "api.rfam.status" not in {row["name"] for row in execution.catalog(ctx)}
    key = _selected(h, journal, ctx, 0)
    first = asyncio.run(execution.execute(ctx, "api.rfam.submit", {}, key))
    assert first["status"] == "completed", first
    assert asyncio.run(execution.execute(ctx, "api.rfam.submit", {}, key)) == first
    assert len(h.client.calls) == 1
    ref, = first["record_refs"]
    target = execution.read_target(ref, h.scope)
    assert target["execution_id"] == JOB
    proof = execution.completion_for_action(ctx, key)
    assert proof and execution.verify_completion(ctx, proof)
    assert "api.rfam.status" in {row["name"] for row in execution.catalog(ctx)}
    observed = execution.observe_target(target, operation_key="explicit-status-1")
    assert observed["failure_code"] == "rfam_job_not_found"
    assert execution.observe_target(target, operation_key="explicit-status-1") == observed
    assert [row[0] for row in h.client.calls] == ["submit", "status"]
    assert execution.verify_completion(ctx, proof)  # Historical handoff stays fixed.
    assert h.store.db.execute("SELECT count(*) FROM provider_jobs").fetchone()[0] == 0


def test_interrupted_decode_reuses_retained_response_without_resubmitting(harness, monkeypatch):
    h = harness
    journal, execution, ctx = _execution(h)
    service = execution.services["rfam"]
    original = service.decode
    key = _selected(h, journal, ctx, 0)
    def interrupted(*args):
        raise asyncio.CancelledError()
    monkeypatch.setattr(service, "decode", interrupted)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(execution.execute(ctx, "api.rfam.submit", {}, key))
    assert len(h.client.calls) == 1
    monkeypatch.setattr(service, "decode", original)
    restored = asyncio.run(execution.execute(ctx, "api.rfam.submit", {}, key))
    assert restored["status"] == "completed" and len(h.client.calls) == 1
    assert execution.read_target(restored["record_refs"][0], h.scope)["execution_id"] == JOB


def test_uncertain_submission_is_not_repeated_on_replay_or_later_action(harness):
    h = harness
    journal, execution, ctx = _execution(h)
    h.client.submission_error = AcquisitionError("rfam_transport_error", phase="transport", submission_outcome="unknown")
    key = _selected(h, journal, ctx, 0)
    first = asyncio.run(execution.execute(ctx, "api.rfam.submit", {}, key))
    assert first["status"] == "failed" and first["feedback"]["submission_outcome"] == "unknown"
    assert asyncio.run(execution.execute(ctx, "api.rfam.submit", {}, key)) == first
    second = _selected(h, journal, ctx, 1)
    refusal = asyncio.run(execution.execute(ctx, "api.rfam.submit", {}, second))
    assert refusal["status"] == "invalid" and refusal["feedback"]["code"] == "api_original_submission_already_exists"
    assert len(h.client.calls) == 1 and execution.completion_for_action(ctx, key) is None


def test_configuration_uses_explicit_actual_transport_timeout(harness):
    h = harness
    service = build_service("rfam_batch", {"kind": "api", "service": "rfam_batch", "timeout": 12.5}, h.tools)
    assert service.service == "rfam_batch"
    with pytest.raises(ValueError):
        build_service("rfam_batch", {"kind": "api", "service": "rfam_batch", "timeout": 0}, h.tools)
    with pytest.raises(ValueError):
        build_service("rfam_batch", {"kind": "api", "service": "rfam_batch", "base_url": "https://other.invalid"}, h.tools)


def test_batch_freezes_selected_occurrences_without_collapsing_equal_sequences(harness):
    h = harness
    original = h.request["subject_ref"]
    h.request = {"version": "rfam_batch_request_v2", "mode": "sequence_batch",
                 "subject_refs": [original, original]}
    prepared, snapshot, event = submitted(h)
    operand = prepared["input_operand"]
    a, b = operand["queries"]
    assert a["subject_ref"] == b["subject_ref"] == original
    assert a["submitted_sequence"] == b["submitted_sequence"] == SEQUENCE
    assert a["query_occurrence_key"] != b["query_occurrence_key"]
    assert a["native_query_name"] != b["native_query_name"]
    assert [a["selected_occurrence_ordinal"], b["selected_occurrence_ordinal"]] == [0, 1]
    expected = f">rfam_query_00000000\n{SEQUENCE}\n>rfam_query_00000001\n{SEQUENCE}\n".encode()
    assert base64.b64decode(snapshot.request["file_base64"]) == expected
    assert operand["submitted_file_bytes"] == len(expected)
    assert operand["submitted_file_sha256"] == hashlib.sha256(expected).hexdigest()
    assert event["facts"]["query_length_nt"] is None
    assert event["handoff_ready"] and len(h.client.calls) == 1
    assert h.store.count("observation") == 0


@pytest.mark.parametrize("field", ["file_base64", "file_sha256", "file_bytes", "filename"])
def test_batch_submission_response_must_match_exact_original_file(harness, field):
    h = harness
    h.request = {"version": "rfam_batch_request_v2", "mode": "sequence_batch",
                 "subject_refs": [h.request["subject_ref"]]}
    prepared, snapshot, _ = submitted(h)
    request = deepcopy(snapshot.request)
    request[field] = 1 if field == "file_bytes" else "foreign"
    with pytest.raises(ValueError, match="rfam_result_sequence_identity_conflict"):
        h.service.decode(prepared, replace(snapshot, request=request))


def test_batch_request_and_table_projection_have_explicit_versioned_contracts(harness):
    h = harness
    request = {"version": "rfam_batch_request_v2", "mode": "sequence_batch",
               "subject_refs": [h.request["subject_ref"]]}
    for invalid in ({**request, "subject_refs": []}, {**request, "version": "rfam_batch_request_v1"},
                    {**request, "subject_ref": h.request["subject_ref"]}):
        with pytest.raises(ValueError, match="rfam_request_invalid"):
            h.service.validate_request(invalid, h.scope)
    selector = {**SELECTOR, "version": "rfam_batch_result_selector_v2", "representation": "tblout",
                "projection": {"family": "hit", "rows": {"offset": 0, "limit": 2},
                               "metrics": ["native_score_bits", "query_span_fraction"]}}
    assert h.service.result_catalog(request, selector)
    with pytest.raises(ValueError, match="rfam_text_format_unverified"):
        h.service.result_catalog(request, {**selector, "version": "rfam_batch_result_selector_v1"})
    with pytest.raises(ValueError, match="rfam_text_format_unverified"):
        h.service.result_catalog(request, {**selector, "representation": "out"})
    assert h.client.calls == []


@pytest.mark.parametrize("field", ["file_sha256", "file_bytes", "file_base64", "filename"])
def test_single_submission_checks_retained_file_metadata_when_present(harness, field):
    h = harness
    prepared, snapshot, _ = submitted(h)
    request = {**snapshot.request, field: 900 if field == "file_bytes" else "wrong"}
    with pytest.raises(ValueError, match="rfam_result_sequence_identity_conflict"):
        h.service.decode(prepared, replace(snapshot, request=request))


def test_single_submission_authenticates_actual_multipart_bytes(harness):
    h = harness
    prepared, snapshot, _ = submitted(h)
    prefix = b'--boundary\r\nContent-Disposition: form-data; name="sequence_file"; filename="sequence.seq"\r\nContent-Type: text/plain\r\n\r\n'
    raw = prefix + SEQUENCE.encode() + b'\n\r\n--boundary--\r\n'
    transport = {**snapshot.transport, "request": {"method": "POST", "url": BASE_URL + "/submit-job",
        "headers": {"Content-Type": "multipart/form-data; boundary=boundary"},
        "body_base64": base64.b64encode(raw).decode(), "body_sha256": hashlib.sha256(raw).hexdigest(), "body_bytes": len(raw)}}
    assert h.service.decode(prepared, replace(snapshot, transport=transport))["handoff_ready"]
    changed = raw.replace(SEQUENCE.encode(), b"AAAAAAGC")
    transport["request"].update(body_base64=base64.b64encode(changed).decode(),
                                body_sha256=hashlib.sha256(changed).hexdigest(), body_bytes=len(changed))
    with pytest.raises(ValueError, match="rfam_result_sequence_identity_conflict"):
        h.service.decode(prepared, replace(snapshot, transport=transport))


def test_uncertain_submission_retains_exact_transport_diagnostic(harness):
    h = harness
    journal, execution, ctx = _execution(h)
    detail = {"request": {"body_base64": "QUJD", "method": "POST"}, "response_received": False}
    h.client.submission_error = AcquisitionError("rfam_transport_error", phase="http_response_headers",
        submission_outcome="unknown", diagnostic=detail)
    key = _selected(h, journal, ctx, 0)
    result = asyncio.run(execution.execute(ctx, "api.rfam.submit", {}, key))
    assert result["status"] == "failed" and result["feedback"]["phase"] == "response"
    assert result["feedback"]["submission_outcome"] == "unknown"
    assert json.loads(h.store.get_artifact(result["feedback"]["diagnostic_ref"])) == {
        "transport_phase": "http_response_headers", "diagnostic": detail}
    assert asyncio.run(execution.execute(ctx, "api.rfam.submit", {}, key)) == result
    assert len(h.client.calls) == 1


def test_compound_rfam_tools_cannot_create_new_work_but_saved_outcomes_replay(harness):
    h = harness
    assert not {"public.rfam.search", "public.rfam.collect"} & set(h.tools.catalog(h.scope))
    for name, args in (("public.rfam.search", {"subject_ref": h.request["subject_ref"]}),
                       ("public.rfam.collect", {"job_ref": "old-job"})):
        outcome = asyncio.run(h.tools.execute_async(name, args, scope=h.scope, operation_key=name))
        assert outcome["status"] == "invalid"
        assert outcome["feedback"]["code"] == "rfam_requires_api_execution_episode"
    original = {"status": "completed", "operation_ref": "old-operation", "record_refs": [],
                "result": {"historical": True}, "feedback": None}
    args = {"job_ref": "old-job"}
    with h.store.transaction():
        h.tools._save("old-result", "public.rfam.collect", args, h.scope, original)
    assert asyncio.run(h.tools.execute_async("public.rfam.collect", args, scope=h.scope,
        operation_key="old-result")) == original
    assert h.client.calls == []


@pytest.mark.parametrize("batch", [False, True])
def test_original_target_information_requires_selected_format_without_acquisition(harness, batch):
    from gene_annotation_episode.execution_progress import ExecutionTargetReader

    h = harness
    if batch:
        h.request = {"version": "rfam_batch_request_v2", "mode": "sequence_batch",
                     "subject_refs": [h.request["subject_ref"], h.request["subject_ref"]]}
    journal, execution, ctx = _execution(h)
    key = _selected(h, journal, ctx, 0)
    outcome = asyncio.run(execution.execute(ctx, "api.rfam.submit", {}, key))
    reference, = outcome["record_refs"]
    reader = ExecutionTargetReader(h.store, run_id=journal.run_id, directory=h.tmp_path / "run",
        resources=execution.configuration, api_execution=execution)
    descriptor = reader.describe_target(reference, h.scope)
    assert descriptor["called_operation"] == "api.rfam.submit"
    assert descriptor["operation"] == h.request["mode"]
    assert descriptor["output_format"] is None
    assert descriptor["available_representations"] == ["json", "tblout", "out"]
    assert descriptor["native_status_meanings"] == {"FINISHED": "completed", "NOT_FOUND": "unknown"}
    assert descriptor["acquisition_operations"] == []
    selector = {**SELECTOR, "version": "rfam_batch_result_selector_v2" if batch else SELECTOR["version"],
        "representation": "tblout" if batch else "json", "projection": {
            "family": "hit", "rows": {"offset": 0, "limit": 1}, "metrics": ["native_score_bits"]}}
    selected = reader.describe_target(reference, h.scope, selector=selector)
    fetch, = [row for row in selected["extractors"] if row["operation"] == "api.rfam.fetch"]
    assert selected["output_format"] == selector["representation"]
    assert selected["projection"] == selector["projection"]
    assert fetch["parser"].endswith("populate_rfam_batch_tblout_sheet" if batch else "populate_rfam_batch_json_sheet")
    assert fetch["calculators"] == [
        "gene_annotation_episode.infernal_search_grader.calculate_infernal_search_scores"]
    assert fetch["calculator_parameters"] == {"hit_scope": "reported"}
    assert fetch["return_fact_sources"] == ["execution_result_refs", "rfam_result_rows", "rfam_result_populations"]
    assert [row[0] for row in h.client.calls] == ["submit"]
    assert h.store.count("observation") == 0


def test_rfam_instructions_and_numerical_sources_reach_only_actual_owners(harness):
    from gene_annotation_episode.execution_episodes import ExecutionEpisodes
    from gene_annotation_episode.tool_information import make_tool_info, workflow_execution_catalogs

    h = harness
    binding = ExecutionEpisodes(None, store=h.store, directory=h.tmp_path / "run",
        run_id="rfam-owner-information", resources={"rfam": {"kind": "api", "service": "rfam_batch", "timeout": 90}},
        initial_information={}, tool_registry=h.tools, handoff_unit=3, acquired_record_unit=2,
        log_window_bytes=512, log_roles=("stdout", "stderr"))
    families = {"rfam_result_rows", "rfam_result_populations"}
    assert families <= set(binding.fact_sources("results"))
    for role in ("launch", "launch_api", "launch_local", "launch_hpc"):
        assert not families & set(binding.fact_sources(role))
    for role in ("annotation", "scientific_process"):
        assert families <= set(binding.received_report_sources(role))
    global_rows = {row["name"]: row for row in workflow_execution_catalogs()["api"]}
    for role in ("launch_api", "results"):
        for contract in binding.api_execution.operation_contracts("rfam", role):
            info = make_tool_info(contract, "api")
            assert set(info) == {"name", "description", "resources", "instructions"}
            assert info["resources"] == "api"
            assert contract["instructions"] == global_rows[contract["name"]]["instructions"]
            assert contract["instructions"] in info["instructions"]
    assert h.client.calls == []


def test_report_selection_is_explicit_and_old_report_selection_stays_artifact_only(harness):
    h = harness
    original = h.request["subject_ref"]
    batch = {"version": "rfam_batch_request_v2", "mode": "sequence_batch", "subject_refs": [original]}
    report = {"version": "rfam_batch_result_selector_v3", "representation": "out",
        "model_metadata_ref": None, "projection": {"family": "hit", "rows": {"offset": 0, "limit": 1},
            "metrics": ["native_bias_bits", "native_alignment_accuracy", "query_insert_count"]}}
    assert h.service.result_catalog(batch, report)
    for version in ("rfam_batch_result_selector_v1", "rfam_batch_result_selector_v2"):
        assert h.service.result_catalog(batch, {**SELECTOR, "version": version, "representation": "out"})
        with pytest.raises(ValueError):
            h.service.result_catalog(batch, {**report, "version": version})
    with pytest.raises(ValueError, match="rfam_report_batch_request_required"):
        h.service.result_catalog(h.request, report)
    with pytest.raises(ValueError, match="rfam_projection_invalid"):
        h.service.result_catalog(batch, {**report, "model_metadata_ref": "unverified-model-source"})
    assert h.client.calls == []


def test_table_only_native_metrics_do_not_change_json_metric_meanings(harness):
    h = harness
    selected = {**SELECTOR, "version": "rfam_batch_result_selector_v2", "representation": "tblout",
        "projection": {"family": "hit", "rows": {"offset": 0, "limit": 1},
            "metrics": ["native_bias_bits", "native_model_span_positions", "native_model_span_fraction"]}}
    batch = {"version": "rfam_batch_request_v2", "mode": "sequence_batch",
        "subject_refs": [h.request["subject_ref"]]}
    assert h.service.result_catalog(batch, selected)
    with pytest.raises(ValueError, match="rfam_projection_invalid"):
        h.service.result_catalog(h.request, {**selected, "representation": "json"})
    assert h.client.calls == []
