"""Local HTTP/protocol fixtures; no remote traffic or scientific model claims."""
import asyncio
from email.message import Message
import io
import json
import urllib.error
import urllib.request

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.provider_jobs import RemoteSearches
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_public_search import Client, JOB, snapshot


class HTTPResponse:
    status = 200

    def __init__(self, body, url):
        self.body, self.url = body, url
        self.headers = Message()
        self.headers['Content-Type'] = 'application/json'

    def read(self):
        return self.body

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def failing_http(monkeypatch, *, body=b'{"database":["unknown database"]}'):
    calls = []

    def urlopen(request, *, timeout):
        calls.append(request)
        headers = Message()
        headers['Content-Type'] = 'application/json; charset=utf-8'
        headers['Retry-After'] = '7'
        headers['X-Fixture-Detail'] = 'retained-actual-header'
        raise urllib.error.HTTPError(request.full_url, 422, 'fixture response', headers, io.BytesIO(body))

    monkeypatch.setattr(urllib.request, 'urlopen', urlopen)
    return calls


def registered_tools(store, client=None):
    problem = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
    tools = ToolRegistry(store, clients=client or PublicClients(), provider_poll_interval_seconds=0)
    args = {'subject_ref': problem['subject_refs'][0], 'algorithm': 'phmmer',
            'database': 'uniprotkb_swissprot'}
    return tools, args


def test_actual_http_error_response_is_retained_without_inferred_rejection(tmp_path, monkeypatch):
    from api_execution_fixture import APIHarness
    body = b'{"database":["unknown database"],"detail":"actual fixture bytes"}\n'
    calls = failing_http(monkeypatch, body=body)
    with Store(tmp_path) as store:
        tools, args = registered_tools(store)
        owner = APIHarness(tools, **args)
        before = store.count('source'), store.count('observation')
        response = owner.act('api.hmmer.submit')
        feedback = response['feedback']
        assert response['status'] == 'failed' and not response['record_refs']
        assert feedback['code'] == 'provider_http_422'
        assert feedback['submission_state'] == 'submission_uncertain'
        assert not feedback['remote_handle_known'] and not feedback['collectable']
        cause = feedback['cause']
        assert cause['http_status'] == 422 and cause['submission_outcome'] == 'unknown'
        assert cause['phase'] == 'submission' and cause['client_phase'] == 'http_response'
        assert cause['exception_type'] == 'HTTPError' and feedback['retry_after'] == 7
        metadata = json.loads(store.get_artifact(feedback['diagnostic_ref']))
        assert store.get_artifact(metadata['content_ref']) == body
        assert metadata['request']['database'] == args['database']
        assert metadata['transport']['headers']['x-fixture-detail'] == 'retained-actual-header'
        assert metadata['transport']['request']['method'] == 'POST'
        assert json.loads(calls[0].data)['database'] == args['database']
        assert len(calls) == 1
        assert tools.remote_searches.describe(feedback['job_ref'])['cause'] == cause
        assert before == (store.count('source'), store.count('observation'))


def test_reopen_selected_replay_and_explicit_status_keep_uncertainty_without_post(tmp_path, monkeypatch):
    from api_execution_fixture import APIHarness
    calls = failing_http(monkeypatch)
    with Store(tmp_path) as store:
        tools, args = registered_tools(store)
        owner = APIHarness(tools, **args)
        response = owner.act('api.hmmer.submit')
    with Store(tmp_path) as store:
        tools = ToolRegistry(store, clients=PublicClients())
        owner = APIHarness(tools, **args)
        assert owner.act('api.hmmer.submit', index=0) == response
        assert owner.act('api.hmmer.submit')['status'] == 'failed'
        assert owner.act('api.hmmer.status')['feedback']['code'] == 'remote_submission_uncertain'
        assert len(calls) == 1
        assert tools.execute('public.hmmer.collect', {'job_ref': response['feedback']['job_ref']})['feedback']['code'] == 'unknown_tool'


def test_timeout_preserves_actual_local_exception_diagnostic(tmp_path, monkeypatch):
    from api_execution_fixture import APIHarness
    calls = []
    def timeout(request, **kwargs):
        calls.append(request)
        raise TimeoutError('fixture timeout after possible transmission')
    monkeypatch.setattr(urllib.request, 'urlopen', timeout)
    with Store(tmp_path) as store:
        tools, args = registered_tools(store)
        owner = APIHarness(tools, **args)
        feedback = owner.act('api.hmmer.submit')['feedback']
        assert feedback['code'] == 'provider_request_timeout'
        assert feedback['cause']['client_phase'] == 'http_request'
        assert feedback['cause']['http_status'] is None and feedback['cause']['response_ref'] is None
        diagnostic = json.loads(store.get_artifact(feedback['diagnostic_ref']))
        assert diagnostic['representation'] == 'local_exception' and diagnostic['exception_type'] == 'TimeoutError'
        assert 'content_ref' not in diagnostic and 'service' not in diagnostic
        owner.act('api.hmmer.submit', index=0)
        assert len(calls) == 1


@pytest.mark.parametrize('body', [b'not json', b'{}', b'{"id":"invalid-handle"}', b'[]'])
def test_http200_submission_entity_survives_json_and_handle_errors(tmp_path, monkeypatch, body):
    from api_execution_fixture import APIHarness
    calls = []
    def malformed(request, **kwargs):
        calls.append(request)
        return HTTPResponse(body, request.full_url)
    monkeypatch.setattr(urllib.request, 'urlopen', malformed)
    with Store(tmp_path) as store:
        tools, args = registered_tools(store)
        owner = APIHarness(tools, **args)
        failed = owner.act('api.hmmer.submit')
        feedback = failed['feedback']
        assert failed['status'] == 'failed' and feedback['code'] == 'provider_submission_response_invalid'
        assert feedback['cause']['client_phase'] == 'submission_response'
        assert feedback['cause']['http_status'] == 200
        row = tools.remote_searches._get(feedback['job_ref'])
        assert tools.remote_searches._load_snapshot(row['submission']).content == body
        metadata = json.loads(store.get_artifact(feedback['diagnostic_ref']))
        assert store.get_artifact(metadata['content_ref']) == body
        assert owner.act('api.hmmer.submit', index=0) == failed
        assert len(calls) == 1 and not store.count('observation')


def test_explicit_client_preflight_is_the_only_known_not_sent_case(tmp_path, monkeypatch):
    from api_execution_fixture import APIHarness
    monkeypatch.setattr(urllib.request, 'urlopen', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('HTTP forbidden')))
    with Store(tmp_path) as store:
        tools, args = registered_tools(store)
        owner = APIHarness(tools, **args, parameters={'unsupported': 1})
        response = owner.act('api.hmmer.submit')
        feedback = response['feedback']
        assert response['status'] == 'failed' and feedback['code'] == 'unsupported_hmmer_search_parameter'
        assert feedback['submission_state'] == 'not_submitted'
        assert feedback['cause']['client_phase'] == 'local_preflight'
        assert feedback['cause']['submission_outcome'] == 'not_sent'
        assert tools.remote_searches.jobs() == []


@pytest.mark.parametrize('phase,body,code', [
    ('status', b'not json', 'provider_status_response_invalid'),
    ('status', b'{"task":{"status":[]}}', 'provider_status_response_invalid'),
    ('result', b'not json', 'provider_result_response_invalid'),
    ('result', b'{"status":[],"result":null}', 'provider_result_response_invalid'),
])
def test_post_acceptance_bad_response_retained_and_explicit_next_action_repairs(tmp_path, phase, body, code):
    from api_execution_fixture import APIHarness
    client = Client()
    bad = lambda *args, **kwargs: SourceSnapshot('ebi_hmmer', 'https://fixture.invalid/'+phase,
        {}, '2026-10-20T00:00:00Z', body, 'application/json', {'status': 200})
    with Store(tmp_path) as store:
        tools, args = registered_tools(store, client)
        owner = APIHarness(tools, **{**args, 'database': 'swissprot'})
        if phase == 'status':
            owner.act('api.hmmer.submit')
            client.hmmer_status = bad
            failed = owner.act('api.hmmer.check_handoff')
            client.hmmer_status = Client().hmmer_status
            recovered = owner.act('api.hmmer.check_handoff')
        else:
            handoff = owner.handoff()
            receiver = owner.results(handoff)
            client.hmmer_result = bad
            failed = receiver.act('api.hmmer.result')
            client.hmmer_result = Client().hmmer_result
            recovered = receiver.act('api.hmmer.result')
        feedback = failed['feedback']
        assert failed['status'] == 'failed' and feedback['category'] == 'provider' and feedback['code'] == code
        metadata = json.loads(store.get_artifact(feedback['diagnostic_ref']))
        assert store.get_artifact(metadata['content_ref']) == body
        assert feedback['remote_handle_known'] and feedback['status_addressable']
        assert feedback['cause']['submission_outcome'] == 'remote_handle_returned'
        assert recovered['status'] == 'completed' and client.submissions == 1
        assert store.get_artifact(metadata['content_ref']) == body


@pytest.mark.parametrize('exception_type', [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
def test_submission_interruption_marks_unknown_and_rethrows_original_type(tmp_path, exception_type):
    from api_execution_fixture import APIHarness
    class Interrupted(Client):
        def hmmer_submit(self, *args, **kwargs):
            self.submissions += 1
            raise exception_type()
    async def check():
        with Store(tmp_path) as store:
            tools, args = registered_tools(store, Interrupted())
            owner = APIHarness(tools, **args)
            with pytest.raises(exception_type):
                await owner.act_async('api.hmmer.submit')
            job = tools.remote_searches.jobs()[0]
            assert job['state'] == 'submission_uncertain' and not job['remote_handle_known']
            replay = await owner.act_async('api.hmmer.submit', index=0)
            assert replay['status'] == 'failed' and tools.clients.submissions == 1
    asyncio.run(check())


def test_later_submission_failure_preserves_previous_partial_source(tmp_path, monkeypatch):
    from api_execution_fixture import APIHarness
    class Both(PublicClients):
        def uniprot_record(self, accession):
            return snapshot({})
    calls = failing_http(monkeypatch)
    with Store(tmp_path) as store:
        tools, args = registered_tools(store, Both())
        partial = tools.execute('public.uniprot.record', {'accession': 'fixture-only'}, operation_key='partial-source')
        assert partial['status'] == 'partial' and len(partial['record_refs']) == 1
        retained = store.get(partial['record_refs'][0])
        failed = APIHarness(tools, **args).act('api.hmmer.submit')
        assert failed['status'] == 'failed' and not failed['record_refs']
        assert store.get(retained['id']) == retained and len(calls) == 1


def test_deleted_ordinary_bypass_feedback_reaches_runtime_without_observation(tmp_path):
    from test_runtime import FixtureController, ScriptedProvider
    from gene_annotation_episode.runtime import run_workflow
    with Store(tmp_path/'state') as store:
        tools, args = registered_tools(store, Client())
        def see_removed(context):
            assert context['feedback']['status'] == 'invalid'
            assert context['feedback']['category'] == 'action_contract'
            assert context['controller']['scores'] == []
            return {'selection': {'kind': 'tool', 'tool': 'public.search.jobs', 'arguments': {}}, 'report_update': {}}
        provider = ScriptedProvider([{'selection': {'kind': 'tool', 'tool': 'public.hmmer.search',
            'arguments': args}, 'report_update': {}}, see_removed])
        result = asyncio.run(run_workflow(store, tools, provider=provider, run_dir=tmp_path/'run',
            project_credit=lambda store, scope: 0.,
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 1)))
        assert result['completed_actions'] == 1 and tools.clients.submissions == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
