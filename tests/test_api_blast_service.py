"""Single-request BLAST service fixtures; no network or scientific conclusions."""
import hashlib
import json
import asyncio
from dataclasses import replace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.api_blast import NCBIBlastService, blast_wait_forecast
from gene_annotation_episode.api_services import build_service
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.episode_monitoring import _blast_monitor_yield, MonitorEpisodes
from gene_annotation_episode.numerical import YieldParameters, STATUS_UNIDENTIFIABLE
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


RID = "FIXTURE_ORIGINAL_RID"


def test_waiting_forecast_conditions_on_actual_waiting_observations():
    handle = {'rid': RID, 'rtoe_seconds': 40,
              'submitted_at': '2026-10-23T00:00:00+00:00'}
    two = blast_wait_forecast(handle, '2026-10-23T00:02:00+00:00', 'WAITING')
    ten = blast_wait_forecast(handle, '2026-10-23T00:10:00+00:00', 'WAITING')
    assert two['elapsed_since_submission_seconds'] == 120
    assert two['estimated_remaining_seconds'] == pytest.approx(60)
    assert ten['elapsed_since_submission_seconds'] == 600
    assert ten['estimated_remaining_seconds'] == pytest.approx(600)
    assert blast_wait_forecast(handle, '2026-10-23T00:10:00+00:00', 'READY')[
        'estimated_remaining_seconds'] == 0


def test_scientific_parent_sees_same_saved_rid_and_updated_waiting_estimate(tmp_path, monkeypatch):
    clock_now = ['2026-10-23T00:00:00+00:00']
    monkeypatch.setattr('gene_annotation_episode.api_service_execution._now',
        lambda: clock_now[0])
    class TimedClient(Client):
        def __init__(self):
            super().__init__()
            self.status_count = 0

        def blast(self, action, **arguments):
            response = super().blast(action, **arguments)
            if action == 'status':
                self.status_count += 1
                return replace(response, retrieved_at=(
                    '2026-10-23T00:02:00+00:00' if self.status_count == 1
                    else '2026-10-23T00:10:00+00:00'))
            return response

    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        client = TimedClient()
        journal = Journal(store, 'blast-parent-status')
        family = ExecutionEpisodes(None, store=store, directory=tmp_path/'run',
            run_id=journal.run_id, resources={'blast': {'kind': 'api', 'service': 'ncbi_blast'}},
            initial_information={}, tool_registry=ToolRegistry(store, clients=client),
            handoff_unit=1, acquired_record_unit=1, log_window_bytes=8192,
            log_roles=['stdout', 'stderr'])
        science_path = (('annotation', 'root'), ('scientific_process', 'a101'))
        science_assignment = {'proposed_annotation_ref': 'hypothesis_fixture',
            'selection': {'evidence_axis': {'option_id': 'A101'}}}
        api_assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'blast',
            'service': 'ncbi_blast', 'request': {'subject_ref': target,
                'program': 'blastp', 'database': 'swissprot'},
            'endpoint': 'usable_handoff', 'constraints': {}}
        api_path = (*science_path, ('launch', 'launch'), ('launch_api', 'api'))

        def episode(episode_id, path, assignment):
            request = {'message': {'scope': scope, 'episode_assignment': assignment}}
            journal.save('runtime_episodes', {'episode_id': episode_id,
                'path': canonical(path), 'request': canonical(request),
                'initial_credit': 0, 'state': 'running'})
            return BindingContext(journal.run_id, episode_id, path[-1][0],
                path, scope, assignment, request)

        root = episode('root', (('annotation', 'root'),), {})
        owner = episode('a101-owner', science_path, science_assignment)
        episode('launch-owner', (*science_path, ('launch', 'launch')),
            {'version': 'execution_launch_assignment_v1',
             'requests': {'blast': api_assignment},
             'immutable_input_versions': [], 'constraints': {}})
        launch = episode('blast-launch', api_path, api_assignment)
        selection = {'kind': 'tool', 'tool': 'api.blast.submit', 'arguments': {}}
        journal.save('runtime_actions', {'episode_id': launch.episode_id,
            'decision_index': 0, 'action': canonical(selection), 'result': None, 'credit': None})
        result = asyncio.run(family.execute(launch, 'api.blast.submit', {},
            f'{journal.run_id}:{launch.episode_id}:0'))
        assert result['status'] == 'completed'
        store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND '
            'episode_id=? AND decision_index=0',
            (canonical(result), journal.run_id, launch.episode_id))
        handoff, = result['record_refs']
        root = replace(root, received_record_refs=(handoff,))
        owner = replace(owner, received_record_refs=(handoff,))
        submitted, = family.initial_decision_context(owner)['received_blast_jobs']
        assert submitted['rid'] == RID and submitted['native_state'] == 'accepted'
        assert submitted['proposed_annotation_ref'] == 'hypothesis_fixture'
        assert submitted['evidence_axis'] == 'A101'
        provider = family.job_progress_provider
        provider.observe(handoff, ['execution_status'], scope, operation_key='status-1')
        clock_now[0] = '2026-10-23T00:02:00+00:00'
        two, = family.initial_decision_context(owner)['received_blast_jobs']
        assert two['rid'] == RID and two['native_state'] == 'WAITING'
        assert two['wait_forecast']['estimated_remaining_seconds'] == pytest.approx(60)
        clock_now[0] = '2026-10-23T00:10:00+00:00'
        aged, = family.initial_decision_context(owner)['received_blast_jobs']
        assert aged['observed_at'] == '2026-10-23T00:02:00+00:00'
        assert aged['forecast_as_of'] == clock_now[0]
        assert aged['wait_forecast']['estimated_remaining_seconds'] == pytest.approx(600)
        assert [name for name, _ in client.calls] == ['submit', 'status']
        client.refuse = True
        provider.observe(handoff, ['execution_status'], scope, operation_key='spacing-refusal')
        refused, = family.initial_decision_context(owner)['received_blast_jobs']
        assert refused['native_state'] == 'WAITING'
        assert refused['observed_at'] == '2026-10-23T00:02:00+00:00'
        assert refused['latest_progress_failure_code'] == 'provider_spacing_required'
        refused_root, = family.initial_decision_context(root)['received_blast_jobs']
        assert refused_root['waiting_count'] == 1
        assert refused_root['latest_progress_failure_code'] == 'provider_spacing_required'
        client.refuse = False
        provider.observe(handoff, ['execution_status'], scope, operation_key='status-2')
        ten, = family.initial_decision_context(owner)['received_blast_jobs']
        assert ten['rid'] == RID and ten['native_state'] == 'WAITING'
        assert ten['wait_forecast']['estimated_remaining_seconds'] == pytest.approx(600)
        root_view, = family.initial_decision_context(root)['received_blast_jobs']
        assert root_view['actionable_handoff_ref'] == handoff
        assert root_view['evidence_axis'] == 'A101' and root_view['waiting_count'] == 1
        assert root_view['estimated_remaining_seconds'] == pytest.approx(600)
        arm = {'proposed_annotation_ref': 'hypothesis_fixture', 'subject_ref': target,
            'scope': scope, 'axis': 'A101', 'credit': 0,
            'status': 'unscored', 'transfer': {}}
        opportunity, = family.annotation_axis_yield_context(root, {'arms': [arm]})[
            'unresolved_annotation_axis_credit']
        assert opportunity['handoff_ref'] == handoff
        results = episode('blast-results', (*science_path, ('results', 'result')),
            {'version': 'execution_results_assignment_v1',
             'handoff_ref': handoff, 'selector': {}})
        journal.save('runtime_actions', {'episode_id': results.episode_id,
            'decision_index': 0, 'action': canonical({'kind': 'tool',
                'tool': 'api.blast.fetch', 'arguments': {}}), 'result': None, 'credit': None})
        acquired = asyncio.run(family.execute(results, 'api.blast.fetch', {},
            f'{journal.run_id}:{results.episode_id}:0'))
        assert acquired['status'] == 'completed'
        store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND '
            'episode_id=? AND decision_index=0',
            (canonical(acquired), journal.run_id, results.episode_id))
        root = replace(root, received_record_refs=(handoff, *acquired['record_refs']))
        completed, = family.initial_decision_context(root)['received_blast_jobs']
        assert completed['result_received_count'] == 1
        assert completed['actionable_handoff_ref'] is None
        assert family.annotation_axis_yield_context(root, {'arms': [arm]})[
            'unresolved_annotation_axis_credit'] == []
        assert [name for name, _ in client.calls] == ['submit', 'status', 'status', 'status', 'fetch']


def test_blast_monitor_one_status_completes_local_task_without_waiting():
    handle = 'source_original_blast'
    params = YieldParameters()
    before = _blast_monitor_yield([], params, [], handle)
    assert before.expected_next_gain.status_code == STATUS_UNIDENTIFIABLE
    context = {'current_completion_evidence': {'progress_records': [{
        'target_handle': handle, 'execution_status': {'native': {'native': {
            'service': 'ncbi_blast'}}}}]}}
    after = _blast_monitor_yield([1], params, [context], handle)
    assert after.expected_next_gain.upper == 0
    owner = MonitorEpisodes.__new__(MonitorEpisodes)
    owner.private_yield_binding = True
    owner.yield_settings = {'kind': 'information_accumulation', 'cutoff': 0.75,
        'uncertainty_alpha': 0.05}
    owner.information_unit = 1.
    owner.services = type('Services', (), {'describe_progress_target': lambda self, *_: {
        'resource_kind': 'api', 'service_or_program': 'ncbi_blast'}})()
    selected = BindingContext('run', 'monitor', 'monitor', (('monitor', 'child'),),
        {'subject_refs': ['input']}, {'target_handle': handle}, {})
    assert 'wait' not in owner.permitted_common_actions(selected)
    controller = owner.yield_controller(selected, 0, 'blast-monitor')
    assert not controller.state().decision.stop
    assert controller.observe('status', {'credit': 1, 'estimation_context': context}).stop


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
    assert result["native_handle"] == {"rid": RID, "rtoe_seconds": 17,
                                       "submitted_at": "2026-10-23T00:00:00+00:00"}
    assert result["handoff_ready"] and not result["result_available"]
    assert result["facts"]["earliest_request_after_seconds"] == 60.
    assert len(client.calls) == 1
    check = service.prepare_observation(request, result["native_handle"], scope=scope)
    observed = service.decode(check, service.invoke(check))
    assert observed["kind"] == "job"
    assert observed["state"] == "submitted" and observed["facts"]["native_state"] == "WAITING"
    assert observed['facts']['wait_forecast']['estimated_remaining_seconds'] == 17
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
