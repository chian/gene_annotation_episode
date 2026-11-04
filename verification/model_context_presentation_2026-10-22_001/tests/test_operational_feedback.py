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
    body = b'{"database":["unknown database"],"detail":"actual fixture bytes"}\n'
    calls = failing_http(monkeypatch, body=body)
    with Store(tmp_path) as store:
        tools, args = registered_tools(store)
        before = store.count('source'), store.count('observation')
        response = tools.execute('public.hmmer.search', args, operation_key='selected-attempt')
        feedback = response['feedback']
        assert response['status'] == 'failed' and not response['record_refs']
        assert feedback['code'] == 'provider_http_422'
        assert feedback['submission_state'] == 'submission_uncertain'
        assert feedback['remote_handle_known'] is False and feedback['collectable'] is False
        cause = feedback['cause']
        assert cause['code'] == 'provider_http_422' and cause['http_status'] == 422
        assert cause['phase'] == 'submission' and cause['client_phase'] == 'http_response'
        assert cause['submission_outcome'] == 'unknown' and cause['exception_type'] == 'HTTPError'
        assert feedback['retry_after'] == 7
        metadata = json.loads(store.get_artifact(feedback['diagnostic_ref']))
        assert store.get_artifact(metadata['content_ref']) == body
        assert metadata['request']['database'] == args['database']
        assert metadata['transport']['headers']['x-fixture-detail'] == 'retained-actual-header'
        assert metadata['transport']['status'] == 422
        assert metadata['transport']['request']['method'] == 'POST'
        assert json.loads(calls[0].data)['database'] == args['database']  # no alias substitution
        assert len(calls) == 1
        assert tools.remote_searches.describe(feedback['job_ref'])['cause'] == cause
        assert tools.remote_searches.jobs()[0]['cause'] == cause
        assert before == (store.count('source'), store.count('observation'))


def test_reopen_collect_page_and_exact_replay_keep_original_cause_without_post(tmp_path, monkeypatch):
    calls = failing_http(monkeypatch)
    with Store(tmp_path) as store:
        tools, args = registered_tools(store)
        response = tools.execute('public.hmmer.search', args, operation_key='one-intent')
        original = response['feedback']
    with Store(tmp_path) as store:
        tools = ToolRegistry(store, clients=PublicClients(), provider_poll_interval_seconds=0)
        assert tools.execute('public.hmmer.search', args, operation_key='one-intent') == response
        collected = tools.execute('public.hmmer.collect', {'job_ref': original['job_ref']}, operation_key='collect-attempt')
        assert collected['feedback'] == original
        paged = tools.execute('public.hmmer.page', {'job_ref': original['job_ref'], 'page': 1}, operation_key='page-attempt')
        assert paged['feedback'] == original
        # Bypass the tool-result cache to exercise the durable intent itself.
        with pytest.raises(AcquisitionError) as error:
            asyncio.run(tools.remote_searches.search('one-intent', subject_ref=args['subject_ref'],
                query_fasta=f">{args['subject_ref']}\nMACDEFGH", algorithm=args['algorithm'], database=args['database']))
        assert error.value.operational['cause'] == original['cause']
        assert len(calls) == 1
        # A different selected attempt is explicit and has its own identity.
        changed = {**args, 'database': 'swissprot'}
        second = tools.execute('public.hmmer.search', changed, operation_key='owner-changed-database')
        assert second['feedback']['job_ref'] != original['job_ref']
        assert len(calls) == 2 and json.loads(calls[-1].data)['database'] == 'swissprot'


def test_timeout_preserves_local_exception_as_local_not_http_diagnostic(tmp_path, monkeypatch):
    calls = []

    def timeout(request, **kwargs):
        calls.append(request)
        raise TimeoutError('fixture timeout after possible transmission')

    monkeypatch.setattr(urllib.request, 'urlopen', timeout)
    with Store(tmp_path) as store:
        tools, args = registered_tools(store)
        feedback = tools.execute('public.hmmer.search', args, operation_key='timeout')['feedback']
        assert feedback['code'] == 'provider_request_timeout'
        assert feedback['cause']['client_phase'] == 'http_request'
        assert feedback['cause']['submission_outcome'] == 'unknown'
        assert feedback['cause']['http_status'] is None and feedback['cause']['response_ref'] is None
        diagnostic = json.loads(store.get_artifact(feedback['diagnostic_ref']))
        assert diagnostic['representation'] == 'local_exception'
        assert diagnostic['exception_type'] == 'TimeoutError'
        assert 'content_ref' not in diagnostic and 'service' not in diagnostic
        assert tools.execute('public.hmmer.collect', {'job_ref': feedback['job_ref']})['feedback'] == feedback
        assert len(calls) == 1


@pytest.mark.parametrize('body', [b'not json', b'{}', b'{"id":"invalid-handle"}', b'[]'])
def test_http200_submission_entity_survives_json_and_handle_errors(tmp_path, monkeypatch, body):
    calls = []

    def malformed(request, **kwargs):
        calls.append(request)
        return HTTPResponse(body, request.full_url)

    monkeypatch.setattr(urllib.request, 'urlopen', malformed)
    with Store(tmp_path) as store:
        tools, args = registered_tools(store)
        failed = tools.execute('public.hmmer.search', args, operation_key='malformed-submission')
        feedback = failed['feedback']
        assert failed['status'] == 'failed' and feedback['code'] == 'provider_submission_response_invalid'
        assert feedback['cause']['client_phase'] == 'submission_response'
        assert feedback['cause']['http_status'] == 200
        assert feedback['cause']['submission_outcome'] == 'unknown'
        row = tools.remote_searches._get(feedback['job_ref'])
        assert tools.remote_searches._load_snapshot(row['submission']).content == body
        metadata = json.loads(store.get_artifact(feedback['diagnostic_ref']))
        assert store.get_artifact(metadata['content_ref']) == body
        assert not feedback['remote_handle_known'] and not feedback['collectable']
        assert tools.execute('public.hmmer.collect', {'job_ref': feedback['job_ref']})['feedback'] == feedback
        assert len(calls) == 1 and not store.count('observation')


def test_explicit_client_preflight_is_the_only_known_not_sent_case(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('preflight must not issue HTTP')

    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs'][0]
        jobs = RemoteSearches(store, PublicClients())
        with pytest.raises(AcquisitionError) as failure:
            asyncio.run(jobs.search('preflight', subject_ref=target, query_fasta='>q\nMACDEFGH',
                algorithm='phmmer', database='swissprot', parameters={'unsupported': 1}))
        error = failure.value
        assert error.code == 'unsupported_hmmer_search_parameter'
        assert error.operational['submission_state'] == 'not_submitted'
        assert error.operational['cause']['client_phase'] == 'local_preflight'
        assert error.operational['cause']['submission_outcome'] == 'not_sent'
        assert not error.operational['collectable']
        assert jobs.jobs() == []
        assert jobs.jobs(active_only=False) == [jobs.describe(error.job_ref)]
        assert jobs.describe(error.job_ref)['state'] == 'not_submitted'


@pytest.mark.parametrize('phase,body,code', [
    ('status', b'not json', 'provider_status_response_invalid'),
    ('status', b'{"task":{"status":[]}}', 'provider_status_response_invalid'),
    ('result', b'not json', 'provider_result_response_invalid'),
    ('result', b'{"status":[],"result":null}', 'provider_result_response_invalid'),
])
def test_post_acceptance_bad_provider_response_is_not_caller_input_error(tmp_path, phase, body, code):
    client = Client()
    if phase == 'status':
        client.hmmer_status = lambda *args, **kwargs: SourceSnapshot(
            'ebi_hmmer', 'https://fixture.invalid/status', {}, '2026-10-20T00:00:00Z', body,
            'application/json', {'status': 200, 'representation': 'local_protocol_fixture'})
    else:
        client.hmmer_result = lambda *args, **kwargs: SourceSnapshot(
            'ebi_hmmer', 'https://fixture.invalid/result', {}, '2026-10-20T00:00:00Z', body,
            'application/json', {'status': 200, 'representation': 'local_protocol_fixture'})
    with Store(tmp_path) as store:
        tools, args = registered_tools(store, client)
        response = tools.execute('public.hmmer.search', {**args, 'database': 'swissprot'})
        feedback = response['feedback']
        assert response['status'] == 'failed' and feedback['category'] == 'provider'
        assert feedback['code'] == code and feedback['cause']['phase'] == phase
        assert feedback['remote_handle_known'] and feedback['collectable']
        assert feedback['cause']['submission_outcome'] == 'remote_handle_returned'
        metadata = json.loads(store.get_artifact(feedback['diagnostic_ref']))
        assert store.get_artifact(metadata['content_ref']) == body
        assert client.submissions == 1 and not store.count('observation')
        # Explicit collection can address this accepted job and clears CURRENT
        # failure on success; prior tool feedback/diagnostic stays durable.
        client.hmmer_status = Client().hmmer_status
        client.hmmer_result = Client().hmmer_result
        recovered = tools.execute('public.hmmer.collect', {'job_ref': feedback['job_ref']})
        assert recovered['status'] == 'completed'
        description = tools.remote_searches.describe(feedback['job_ref'])
        assert description['cause'] is None and description['error_code'] is None
        assert description['state'] == 'returned' and description['remote_handle_known']
        assert store.get_artifact(metadata['content_ref']) == body


@pytest.mark.parametrize('exception_type', [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
def test_submission_interruption_marks_unknown_and_rethrows_original_type(tmp_path, exception_type):
    class Interrupted(Client):
        def hmmer_submit(self, *args, **kwargs):
            self.submissions += 1
            raise exception_type()

    async def check():
        with Store(tmp_path) as store:
            target = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs'][0]
            client = Interrupted()
            jobs = RemoteSearches(store, client)
            with pytest.raises(exception_type):
                await jobs.search('interrupted', subject_ref=target, query_fasta='>q\nMACDEFGH',
                    algorithm='phmmer', database='swissprot')
            job = jobs.jobs()[0]
            assert job['state'] == 'submission_uncertain'
            assert job['cause']['submission_outcome'] == 'unknown'
            assert job['cause']['exception_type'] == exception_type.__name__
            assert not job['remote_handle_known'] and not job['collectable']
            with pytest.raises(AcquisitionError):
                await jobs.collect(job['job_ref'])
            assert client.submissions == 1

    asyncio.run(check())


def test_later_submission_failure_preserves_previous_partial_source(tmp_path, monkeypatch):
    class Both(PublicClients):
        def uniprot_record(self, accession):
            return snapshot({})  # exact fixture acquisition survives a failed import

    calls = failing_http(monkeypatch)
    with Store(tmp_path) as store:
        tools, args = registered_tools(store, Both())
        partial = tools.execute('public.uniprot.record', {'accession': 'fixture-only'}, operation_key='partial-source')
        assert partial['status'] == 'partial' and len(partial['record_refs']) == 1
        retained = store.get(partial['record_refs'][0])
        failed = tools.execute('public.hmmer.search', args, operation_key='later-failure')
        assert failed['status'] == 'failed' and not failed['record_refs']
        assert store.get(retained['id']) == retained
        assert tools.execute('public.uniprot.record', {'accession': 'fixture-only'}, operation_key='partial-source') == partial
        assert len(calls) == 1


def test_successful_cached_collect_clears_current_failure_keeps_history(tmp_path):
    client = Client()
    with Store(tmp_path) as store:
        tools, args = registered_tools(store, client)
        accepted = tools.execute('public.hmmer.search', {**args, 'database': 'swissprot'}, operation_key='accepted')
        job_ref = accepted['result']['job_ref']
        client.hmmer_result = lambda *args, **kwargs: snapshot({'status': 'PENDING', 'result': None})
        failed = tools.execute('public.hmmer.page', {'job_ref': job_ref, 'page': 2}, operation_key='unready-page')
        diagnostic_ref = failed['feedback']['diagnostic_ref']
        assert tools.remote_searches.describe(job_ref)['cause']
        recovered = tools.execute('public.hmmer.collect', {'job_ref': job_ref}, operation_key='cached-collect')
        assert recovered['status'] == 'completed' and recovered['result']['page'] == 1
        current = tools.remote_searches.describe(job_ref)
        assert current['cause'] is None and current['error_code'] is None
        assert current['remote_handle_known'] and current['collectable']
        assert store.get_artifact(diagnostic_ref)
        assert tools.execute('public.hmmer.page', {'job_ref': job_ref, 'page': 2}, operation_key='unready-page') == failed
        assert client.submissions == 1 and client.status_calls == 1


def test_actual_tools_failure_reaches_episode_without_yield_observation(tmp_path, monkeypatch):
    from test_runtime import FixtureController, ScriptedProvider
    from gene_annotation_episode.runtime import run_workflow

    calls = failing_http(monkeypatch)
    with Store(tmp_path / 'state') as store:
        tools, args = registered_tools(store)

        def collect_known_failure(context):
            assert context['feedback']['code'] == 'provider_http_422'
            assert not context['feedback']['collectable']
            assert context['controller']['scores'] == []
            return {'selection': {'kind': 'tool', 'tool': 'public.hmmer.collect',
                    'arguments': {'job_ref': context['feedback']['job_ref']}}, 'report_update': {}}

        provider = ScriptedProvider([
            {'selection': {'kind': 'tool', 'tool': 'public.hmmer.search', 'arguments': args}, 'report_update': {}},
            collect_known_failure,
            {'selection': {'kind': 'tool', 'tool': 'public.search.jobs', 'arguments': {}}, 'report_update': {}},
        ])
        result = asyncio.run(run_workflow(store, tools, provider=provider, run_dir=tmp_path / 'run',
            project_credit=lambda store, scope: 0.,
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 1)))
        assert result['completed_actions'] == 1
        assert len(calls) == 1 and len(provider.contexts) == 3
        assert provider.contexts[1]['feedback'] == provider.contexts[2]['feedback']
        assert provider.contexts[2]['controller']['scores'] == []
        rows = store.db.execute('SELECT observation FROM runtime_observations').fetchall()
        assert [json.loads(row[0])['label'] for row in rows] == ['tool:2']
        assert not store.count('observation') and not store.current_annotations()
